
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token
from database.conexion import ConexionDB
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

auth_api = Blueprint(
    "auth_api",
    __name__,
    url_prefix="/api"
)


@auth_api.route("/login", methods=["POST"])
def iniciar_sesion():

    datos = request.get_json(silent=True) or {}

    login = datos.get("usuario", "").strip()
    password = datos.get("password", "")

    if not login or not password:
        return jsonify({
            "exito": False,
            "mensaje": "Ingresa usuario y contraseña."
        }), 400

    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:

                cursor.execute("""
                    SELECT
                        usuario_id,
                        usuario_login,
                        usuario_nombre,
                        usuario_password_hash,
                        usuario_rol,
                        usuario_activo
                    FROM usuarios_administradores
                    WHERE usuario_login = %s
                """, (login,))

                usuario = cursor.fetchone()

                if not usuario:
                    return jsonify({
                        "exito": False,
                        "mensaje": "Usuario o contraseña incorrectos."
                    }), 401

                (
                    usuario_id,
                    usuario_login,
                    usuario_nombre,
                    password_hash,
                    usuario_rol,
                    usuario_activo
                ) = usuario

                if not usuario_activo or not check_password_hash(
                    password_hash, password
                ):
                    return jsonify({
                        "exito": False,
                        "mensaje": "Usuario o contraseña incorrectos."
                    }), 401

                cursor.execute("""
                    UPDATE usuarios_administradores
                    SET usuario_ultimo_acceso = CURRENT_TIMESTAMP
                    WHERE usuario_id = %s
                """, (usuario_id,))

        token = create_access_token(
            identity=str(usuario_id),
            additional_claims={
                "rol": usuario_rol,
                "login": usuario_login
            }
        )

        return jsonify({
            "exito": True,
            "mensaje": "Inicio de sesión correcto.",
            "token": token,
            "usuario": {
                "id": usuario_id,
                "login": usuario_login,
                "nombre": usuario_nombre,
                "rol": usuario_rol
            }
        }), 200

    except Exception as error:
        print("ERROR API LOGIN:", repr(error))

        return jsonify({
            "exito": False,
            "mensaje": "No se pudo iniciar sesión."
        }), 500
# Alumnos login 

@auth_api.route("/login/alumno", methods=["POST"])
def iniciar_sesion_alumno():

    datos = request.get_json(silent=True) or {}

    login = datos.get("usuario", "")
    password = datos.get("password", "")

    if not isinstance(login, str) or not isinstance(password, str):
        return jsonify({
            "exito": False,
            "mensaje": "Datos de acceso inválidos."
        }), 400

    login = login.strip()

    if not login or not password:
        return jsonify({
            "exito": False,
            "mensaje": "Ingresa matrícula y contraseña."
        }), 400

    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:

                cursor.execute("""
                    SELECT
                        ua.usuario_alumno_id,
                        ua.alumno_id,
                        ua.usuario_login,
                        ua.usuario_password_hash,
                        ua.usuario_activo,
                        ua.debe_cambiar_password,
                        a.alumno_nombre
                    FROM usuarios_alumnos ua
                    INNER JOIN alumnos a
                        ON a.alumno_id = ua.alumno_id
                    WHERE ua.usuario_login = %s
                """, (login,))

                alumno = cursor.fetchone()

                if not alumno:
                    return jsonify({
                        "exito": False,
                        "mensaje": "Matrícula o contraseña incorrectas."
                    }), 401

                (
                    usuario_id,
                    alumno_id,
                    usuario_login,
                    password_hash,
                    usuario_activo,
                    debe_cambiar_password,
                    alumno_nombre
                ) = alumno

                if not usuario_activo or not check_password_hash(
                    password_hash, password
                ):
                    return jsonify({
                        "exito": False,
                        "mensaje": "Matrícula o contraseña incorrectas."
                    }), 401

        token = create_access_token(
            identity=str(usuario_id),
            additional_claims={
                "rol": "alumno",
                "login": usuario_login,
                "alumno_id": alumno_id
            }
        )

        return jsonify({
            "exito": True,
            "mensaje": "Inicio de sesión correcto.",
            "token": token,
            "debe_cambiar_password": debe_cambiar_password,
            "usuario": {
                "id": usuario_id,
                "alumno_id": alumno_id,
                "matricula": usuario_login,
                "nombre": alumno_nombre,
                "rol": "alumno"
            }
        }), 200

    except Exception as error:
        print("ERROR API LOGIN ALUMNO:", repr(error))

        return jsonify({
            "exito": False,
            "mensaje": "No se pudo iniciar sesión."
        }), 500


@auth_api.route("/alumno/cambiar-password", methods=["POST"])
@jwt_required()
def cambiar_password_alumno():

    # Obtener los datos enviados desde Flutter
    datos = request.get_json(silent=True) or {}

    password_actual = datos.get("password_actual", "")
    password_nueva = datos.get("password_nueva", "")

    if not isinstance(password_actual, str) or not isinstance(password_nueva, str):
        return jsonify({
            "exito": False,
            "mensaje": "Los datos enviados no son válidos."
        }), 400

    if not password_actual or not password_nueva:
        return jsonify({
            "exito": False,
            "mensaje": "Debes proporcionar la contraseña actual y la nueva."
        }), 400

    if len(password_nueva) < 8:
        return jsonify({
            "exito": False,
            "mensaje": "La nueva contraseña debe tener al menos 8 caracteres."
        }), 400

    # Comprobar que el token pertenece a un alumno
    claims = get_jwt()

    if claims.get("rol") != "alumno":
        return jsonify({
            "exito": False,
            "mensaje": "No tienes permisos para realizar esta operación."
        }), 403

    usuario_id = get_jwt_identity()

    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:

                # Buscar la cuenta del alumno
                cursor.execute("""
                    SELECT usuario_password_hash
                    FROM usuarios_alumnos
                    WHERE usuario_alumno_id = %s
                      AND usuario_activo = TRUE
                """, (usuario_id,))

                usuario = cursor.fetchone()

                if not usuario:
                    return jsonify({
                        "exito": False,
                        "mensaje": "No se encontró la cuenta del alumno."
                    }), 404

                password_hash = usuario[0]

                # Verificar contraseña actual
                if not check_password_hash(password_hash, password_actual):
                    return jsonify({
                        "exito": False,
                        "mensaje": "La contraseña actual es incorrecta."
                    }), 401

                # Generar nuevo hash
                nuevo_hash = generate_password_hash(password_nueva)

                # Actualizar contraseña y quitar cambio obligatorio
                cursor.execute("""
                    UPDATE usuarios_alumnos
                    SET usuario_password_hash = %s,
                        debe_cambiar_password = FALSE
                    WHERE usuario_alumno_id = %s
                """, (nuevo_hash, usuario_id))

            conexion.commit()

        return jsonify({
            "exito": True,
            "mensaje": "Contraseña actualizada correctamente.",
            "debe_cambiar_password": False
        }), 200

    except Exception as error:
        print("ERROR CAMBIAR PASSWORD ALUMNO:", repr(error))

        return jsonify({
            "exito": False,
            "mensaje": "No se pudo actualizar la contraseña."
        }), 500
