
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token
from database.conexion import ConexionDB

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
