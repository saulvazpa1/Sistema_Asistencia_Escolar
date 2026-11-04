import secrets
import hashlib

from config import BOT_USERNAME
from database.conexion import ConexionDB


class RegistroService:

    # Registrar alumno
    def registrar_alumno(self, alumno):

        try:
            with ConexionDB.conectar() as db:
                with db.cursor() as cursor:

                    cursor.execute("""
                        INSERT INTO alumnos (
                            alumno_matricula,
                            alumno_nombre,
                            alumno_carrera_id,
                            alumno_grupo_id
                        )
                        VALUES (%s, %s, %s, %s)
                        RETURNING alumno_id
                    """, (
                        alumno.alumno_matricula,
                        alumno.alumno_nombre,
                        alumno.alumno_carrera_id,
                        alumno.alumno_grupo_id
                    ))

                    return cursor.fetchone()[0]

        except Exception as error:
            print("Error al registrar alumno:", error)
            raise

    # Registrar tutor
    def registrar_tutor(self, tutor):

        try:
            with ConexionDB.conectar() as db:
                with db.cursor() as cursor:

                    cursor.execute("""
                        INSERT INTO tutores (
                            tutor_nombre,
                            tutor_ine,
                            tutor_telefono,
                            tutor_correo
                        )
                        VALUES (%s, %s, %s, %s)
                        RETURNING tutor_id
                    """, (
                        tutor.get_tutor_nombre(),
                        tutor.get_tutor_ine(),
                        tutor.get_tutor_telefono(),
                        tutor.get_tutor_correo()
                    ))

                    return cursor.fetchone()[0]

        except Exception as error:
            print("Error al registrar tutor:", error)
            raise

    # Relacionar alumno con tutor
    def relacionar_alumno_tutor(
        self,
        alumno_id,
        tutor_id,
        relacion=None,
        es_tutor_principal=False
    ):

        try:
            with ConexionDB.conectar() as db:
                with db.cursor() as cursor:

                    cursor.execute("""
                        INSERT INTO alumnos_tutores (
                            alumno_id,
                            tutor_id,
                            relacion,
                            es_tutor_principal
                        )
                        VALUES (%s, %s, %s, %s)
                    """, (
                        alumno_id,
                        tutor_id,
                        relacion,
                        es_tutor_principal
                    ))

                    return True

        except Exception as error:
            print("Error al relacionar alumno y tutor:", error)
            raise

    # Generar enlace de Telegram
    def generar_enlace_telegram(self, tutor_id):

        codigo = secrets.token_urlsafe(32)

        codigo_hash = hashlib.sha256(
            codigo.encode()
        ).hexdigest()

        try:
            with ConexionDB.conectar() as db:
                with db.cursor() as cursor:

                    cursor.execute("""
                        UPDATE vinculaciones_telegram
                        SET vinculacion_activa = FALSE
                        WHERE tutor_id = %s
                          AND vinculacion_activa = TRUE
                    """, (tutor_id,))

                    cursor.execute("""
                        INSERT INTO vinculaciones_telegram (
                            tutor_id,
                            vinculacion_token_hash,
                            vinculacion_fecha_expiracion
                        )
                        VALUES (
                            %s,
                            %s,
                            CURRENT_TIMESTAMP + INTERVAL '15 minutes'
                        )
                    """, (tutor_id, codigo_hash))

            return f"https://t.me/{BOT_USERNAME}?start=link_{codigo}"

        except Exception as error:
            print("Error al generar enlace de Telegram:", error)
            raise