
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from services.credenciales_alumnos import (
    crear_credenciales_alumno,
    enviar_credenciales_por_telegram,
    obtener_usuarios_alumnos,
    restablecer_password_alumno
)

credenciales_api = Blueprint("credenciales_api", __name__)


@credenciales_api.route(
    "/api/alumnos/<int:alumno_id>/credenciales",
    methods=["POST"]
)
@jwt_required()
def crear_cuenta_alumno(alumno_id):
    try:
        credenciales = crear_credenciales_alumno(alumno_id)

        envio = enviar_credenciales_por_telegram(
            alumno_id,
            credenciales
        )

        return jsonify({
            "exito": True,
            "mensaje": "Cuenta del alumno creada correctamente.",
            "usuario": credenciales["usuario"],
            "telegram_enviado": envio["enviado"],
            "mensaje_telegram": envio["mensaje"]
        }), 201

    except ValueError as error:
        return jsonify({
            "exito": False,
            "mensaje": str(error)
        }), 400

    except Exception as error:
        return jsonify({
            "exito": False,
            "mensaje": f"Error al crear la cuenta: {str(error)}"
        }), 500


@credenciales_api.route(
    "/api/usuarios-alumnos",
    methods=["GET"]
)
@jwt_required()
def listar_usuarios_alumnos():
    try:
        usuarios = obtener_usuarios_alumnos()

        return jsonify({
            "exito": True,
            "usuarios": usuarios
        }), 200

    except Exception as error:
        return jsonify({
            "exito": False,
            "mensaje": f"Error al consultar las cuentas: {str(error)}"
        }), 500


@credenciales_api.route(
    "/api/alumnos/<int:alumno_id>/restablecer-password",
    methods=["POST"]
)
@jwt_required()
def restablecer_password(alumno_id):
    try:
        resultado = restablecer_password_alumno(alumno_id)

        return jsonify({
            "exito": True,
            "mensaje": "Contraseña restablecida correctamente.",
            **resultado
        }), 200

    except ValueError as error:
        return jsonify({
            "exito": False,
            "mensaje": str(error)
        }), 400

    except Exception as error:
        return jsonify({
            "exito": False,
            "mensaje": f"Error al restablecer la contraseña: {str(error)}"
        }), 500
