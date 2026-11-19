
import os
import secrets
import string
import requests

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from database.conexion import ConexionDB

load_dotenv()


def generar_password_temporal(longitud=12):
    """Genera una contraseña temporal aleatoria."""
    caracteres = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(caracteres) for _ in range(longitud))


def _obtener_chat_tutor(cursor, alumno_id):
    """Obtiene el chat de Telegram del tutor principal vinculado."""
    cursor.execute("""
        SELECT t.tutor_telegram_chat_id
        FROM public.alumnos_tutores AS at
        INNER JOIN public.tutores AS t
            ON t.tutor_id = at.tutor_id
        WHERE at.alumno_id = %s
          AND at.es_tutor_principal = TRUE
          AND t.tutor_telegram_vinculado = TRUE
          AND t.tutor_telegram_chat_id IS NOT NULL
        LIMIT 1
    """, (alumno_id,))

    resultado = cursor.fetchone()
    return resultado[0] if resultado else None


def _enviar_mensaje_telegram(chat_id, mensaje):
    """Envía un mensaje usando el bot de Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        return {
            "enviado": False,
            "mensaje": "No está configurado TELEGRAM_BOT_TOKEN."
        }

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        respuesta = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": mensaje
            },
            timeout=15
        )

        datos = respuesta.json()

        if respuesta.ok and datos.get("ok"):
            return {"enviado": True, "mensaje": "Mensaje enviado correctamente."}

        return {
            "enviado": False,
            "mensaje": datos.get("description", "Telegram no pudo enviar el mensaje.")
        }

    except requests.RequestException as error:
        return {
            "enviado": False,
            "mensaje": f"No se pudo conectar con Telegram: {error}"
        }


def crear_credenciales_alumno(alumno_id):
    """
    Crea una cuenta para el alumno.
    El usuario será su matrícula y la contraseña será temporal.
    """
    conn = ConexionDB.conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT alumno_matricula, alumno_nombre
            FROM public.alumnos
            WHERE alumno_id = %s
        """, (alumno_id,))

        alumno = cursor.fetchone()

        if not alumno:
            raise ValueError("No se encontró el alumno.")

        matricula, nombre = alumno

        cursor.execute("""
            SELECT usuario_alumno_id
            FROM public.usuarios_alumnos
            WHERE alumno_id = %s
        """, (alumno_id,))

        if cursor.fetchone():
            raise ValueError("Este alumno ya tiene una cuenta de acceso.")

        password_temporal = generar_password_temporal()
        password_hash = generate_password_hash(password_temporal)

        cursor.execute("""
            INSERT INTO public.usuarios_alumnos (
                alumno_id,
                usuario_login,
                usuario_password_hash,
                usuario_activo,
                debe_cambiar_password
            )
            VALUES (%s, %s, %s, TRUE, TRUE)
            RETURNING usuario_alumno_id
        """, (alumno_id, str(matricula), password_hash))

        usuario_id = cursor.fetchone()[0]
        conn.commit()

        return {
            "usuario_alumno_id": usuario_id,
            "alumno_id": alumno_id,
            "alumno": nombre,
            "usuario": str(matricula),
            "password_temporal": password_temporal
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


def enviar_credenciales_por_telegram(alumno_id, credenciales):
    """Envía las credenciales al tutor principal del alumno."""
    conn = ConexionDB.conectar()
    cursor = conn.cursor()

    try:
        chat_id = _obtener_chat_tutor(cursor, alumno_id)

        if not chat_id:
            return {
                "enviado": False,
                "mensaje": "No se encontró un tutor principal vinculado a Telegram."
            }

    finally:
        cursor.close()
        conn.close()

    mensaje = (
        "¡Hola! Se ha creado la cuenta escolar del alumno.\n\n"
        f"Alumno: {credenciales['alumno']}\n\n"
        "DATOS DE ACCESO:\n"
        f"Usuario: {credenciales['usuario']}\n"
        f"Contraseña temporal: {credenciales['password_temporal']}\n\n"
        "El alumno deberá cambiar su contraseña cuando inicie sesión "
        "por primera vez.\n\n"
        "Por seguridad, comparte estos datos únicamente con el alumno."
    )

    return _enviar_mensaje_telegram(chat_id, mensaje)


def obtener_usuarios_alumnos():
    """Obtiene las cuentas de acceso junto con los datos de sus alumnos."""
    conn = ConexionDB.conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                ua.usuario_alumno_id,
                ua.alumno_id,
                a.alumno_matricula,
                a.alumno_nombre,
                ua.usuario_login,
                ua.usuario_activo,
                ua.debe_cambiar_password,
                ua.usuario_fecha_creacion,
                ua.usuario_ultimo_acceso
            FROM public.usuarios_alumnos AS ua
            INNER JOIN public.alumnos AS a
                ON a.alumno_id = ua.alumno_id
            ORDER BY ua.usuario_fecha_creacion DESC
        """)

        columnas = [columna.name for columna in cursor.description]
        resultados = cursor.fetchall()

        usuarios = []

        for fila in resultados:
            usuario = dict(zip(columnas, fila))

            for campo, valor in usuario.items():
                if hasattr(valor, "isoformat"):
                    usuario[campo] = valor.isoformat()

            usuarios.append(usuario)

        return usuarios

    finally:
        cursor.close()
        conn.close()


def restablecer_password_alumno(alumno_id):
    """Genera una nueva contraseña temporal y la envía al tutor."""
    conn = ConexionDB.conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT usuario_login
            FROM public.usuarios_alumnos
            WHERE alumno_id = %s
        """, (alumno_id,))

        resultado = cursor.fetchone()

        if not resultado:
            raise ValueError("El alumno no tiene una cuenta de acceso.")

        usuario_login = resultado[0]
        password_temporal = generar_password_temporal()
        password_hash = generate_password_hash(password_temporal)

        cursor.execute("""
            UPDATE public.usuarios_alumnos
            SET usuario_password_hash = %s,
                debe_cambiar_password = TRUE
            WHERE alumno_id = %s
        """, (password_hash, alumno_id))

        conn.commit()

        chat_id = _obtener_chat_tutor(cursor, alumno_id)

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

    if not chat_id:
        return {
            "usuario": usuario_login,
            "password_actualizada": True,
            "telegram_enviado": False,
            "mensaje": "La contraseña se actualizó, pero no se encontró un tutor principal vinculado a Telegram."
        }

    mensaje = (
        "Se ha restablecido la contraseña de acceso del alumno.\n\n"
        f"Usuario: {usuario_login}\n"
        f"Nueva contraseña temporal: {password_temporal}\n\n"
        "El alumno deberá cambiarla al iniciar sesión."
    )

    envio = _enviar_mensaje_telegram(chat_id, mensaje)

    return {
        "usuario": usuario_login,
        "password_actualizada": True,
        "telegram_enviado": envio["enviado"],
        "mensaje": envio["mensaje"]
    }
