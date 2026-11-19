
import os
import time
import hashlib
import requests
import psycopg

from dotenv import load_dotenv
from database.conexion import ConexionDB

from services.credenciales_alumnos import (
    crear_credenciales_alumno,
    enviar_credenciales_por_telegram
)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"


class BotTelegram:

    def responder(self, chat_id, texto):

        respuesta = requests.post(
            f"{BASE_URL}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": texto
            },
            timeout=15
        )

        respuesta.raise_for_status()

    def procesar_start(self, chat_id, telegram_id, texto):

        partes = texto.split(maxsplit=1)

        if len(partes) != 2 or not partes[1].startswith("link_"):
            self.responder(
                chat_id,
                "¡Hola! Registra al alumno en el formulario "
                "web y utiliza el botón Vincular Telegram."
            )
            return

        codigo = partes[1][5:]

        # Convertir el código en un hash
        codigo_hash = hashlib.sha256(
            codigo.encode()
        ).hexdigest()

        with ConexionDB.conectar() as db:

            with db.cursor() as cursor:

                # Buscar la vinculación
                cursor.execute("""
                    SELECT
                        v.vinculacion_id,
                        v.tutor_id
                    FROM vinculaciones_telegram v
                    WHERE v.vinculacion_token_hash = %s
                      AND v.vinculacion_activa = TRUE
                      AND v.vinculacion_fecha_uso IS NULL
                      AND v.vinculacion_fecha_expiracion > CURRENT_TIMESTAMP
                    FOR UPDATE
                """, (codigo_hash,))

                vinculacion = cursor.fetchone()

                if not vinculacion:
                    self.responder(
                        chat_id,
                        "Este enlace no es válido o ya fue utilizado. "
                        "Genera uno nuevo desde el formulario."
                    )
                    return

                vinculacion_id, tutor_id = vinculacion

                # Vincular Telegram con el tutor
                cursor.execute("""
                    UPDATE tutores
                    SET tutor_telegram_id = %s,
                        tutor_telegram_chat_id = %s,
                        tutor_telegram_vinculado = TRUE
                    WHERE tutor_id = %s
                """, (
                    str(telegram_id),
                    str(chat_id),
                    tutor_id
                ))

                # Marcar enlace como utilizado
                cursor.execute("""
                    UPDATE vinculaciones_telegram
                    SET vinculacion_fecha_uso = CURRENT_TIMESTAMP,
                        vinculacion_activa = FALSE
                    WHERE vinculacion_id = %s
                """, (vinculacion_id,))

                # Consultar el alumno relacionado con el tutor
                cursor.execute("""
                    SELECT
                        a.alumno_id,
                        a.alumno_nombre
                    FROM alumnos_tutores at
                    INNER JOIN alumnos a
                        ON at.alumno_id = a.alumno_id
                    WHERE at.tutor_id = %s
                    ORDER BY at.es_tutor_principal DESC
                    LIMIT 1
                """, (tutor_id,))

                resultado = cursor.fetchone()

        # Verificar que exista un alumno relacionado
        if not resultado:

            self.responder(
                chat_id,
                "✅ Telegram se vinculó correctamente, pero no "
                "se encontró un alumno relacionado con el tutor."
            )
            return

        alumno_id, nombre_alumno = resultado

        # Crear automáticamente la cuenta del alumno
        try:

            credenciales = crear_credenciales_alumno(alumno_id)

            # Enviar las credenciales al tutor
            envio = enviar_credenciales_por_telegram(
                alumno_id,
                credenciales
            )

            if envio["enviado"]:

                self.responder(
                    chat_id,
                    "✅ ¡Telegram vinculado correctamente!\n\n"
                    f"Alumno: {nombre_alumno}\n\n"
                    "🎓 La cuenta escolar del alumno fue creada "
                    "correctamente.\n\n"
                    "Te hemos enviado los datos de acceso en "
                    "un mensaje separado.\n\n"
                    "El alumno deberá cambiar su contraseña "
                    "en su primer inicio de sesión."
                )

            else:

                self.responder(
                    chat_id,
                    "✅ Telegram se vinculó correctamente.\n\n"
                    f"Alumno: {nombre_alumno}\n\n"
                    "⚠️ La cuenta escolar fue creada, pero no "
                    "se pudieron enviar las credenciales.\n\n"
                    f"Motivo: {envio['mensaje']}"
                )

        except ValueError as error:

            self.responder(
                chat_id,
                "✅ Telegram se vinculó correctamente.\n\n"
                f"Alumno: {nombre_alumno}\n\n"
                f"⚠️ No se creó una cuenta nueva: {error}"
            )

        except Exception as error:

            print(
                "Error al crear la cuenta del alumno:",
                error
            )

            self.responder(
                chat_id,
                "✅ Telegram se vinculó correctamente.\n\n"
                f"Alumno: {nombre_alumno}\n\n"
                "⚠️ Ocurrió un error al crear la cuenta escolar. "
                "Será necesario revisarlo desde el panel administrativo."
            )

    def iniciar(self):

        if not TOKEN:
            print("Falta TELEGRAM_BOT_TOKEN en el archivo .env")
            return

        try:

            requests.post(
                f"{BASE_URL}/deleteWebhook",
                json={"drop_pending_updates": False},
                timeout=15
            ).raise_for_status()

        except requests.RequestException as error:

            print("Error al conectar con Telegram:", error)
            return

        offset = None

        print("Bot activo. Esperando mensajes...")

        while True:

            try:

                parametros = {"timeout": 25}

                if offset is not None:
                    parametros["offset"] = offset

                respuesta = requests.get(
                    f"{BASE_URL}/getUpdates",
                    params=parametros,
                    timeout=35
                )

                respuesta.raise_for_status()

                for update in respuesta.json().get("result", []):

                    offset = update["update_id"] + 1

                    mensaje = update.get("message")

                    if not mensaje or "text" not in mensaje:
                        continue

                    chat_id = mensaje["chat"]["id"]
                    telegram_id = mensaje["from"]["id"]
                    texto = mensaje["text"].strip()

                    try:

                        if texto.startswith("/start"):

                            self.procesar_start(
                                chat_id,
                                telegram_id,
                                texto
                            )

                        else:

                            self.responder(
                                chat_id,
                                "Para vincular tu cuenta, utiliza "
                                "el botón Vincular Telegram "
                                "del formulario."
                            )

                    except (requests.RequestException, psycopg.Error) as error:

                        print(
                            "Error al procesar mensaje:",
                            error
                        )

                    except Exception as error:

                        print(
                            "Error inesperado al procesar mensaje:",
                            error
                        )

            except requests.RequestException as error:

                print(
                    "Error de conexión con Telegram:",
                    error
                )

                time.sleep(3)

            except psycopg.Error as error:

                print(
                    "Error de conexión con PostgreSQL:",
                    error
                )

                time.sleep(3)


if __name__ == "__main__":

    bot = BotTelegram()
    bot.iniciar()
