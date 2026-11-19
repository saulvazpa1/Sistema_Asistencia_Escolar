
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from database.conexion import ConexionDB

tutores_api = Blueprint("tutores_api", __name__, url_prefix="/api")


@tutores_api.route("/tutores", methods=["GET"])
@jwt_required()
def obtener_tutores():
    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        tutor_id,
                        tutor_nombre,
                        tutor_ine,
                        tutor_telefono,
                        tutor_correo,
                        tutor_telegram_vinculado,
                        tutor_activo
                    FROM tutores
                    ORDER BY tutor_id
                """)

                columnas = [col.name for col in cursor.description]
                tutores = [
                    dict(zip(columnas, fila))
                    for fila in cursor.fetchall()
                ]

        return jsonify({
            "exito": True,
            "tutores": tutores
        }), 200

    except Exception as error:
        print("ERROR API TUTORES:", repr(error))
        return jsonify({
            "exito": False,
            "mensaje": "No se pudieron consultar los tutores."
        }), 500


@tutores_api.route("/tutores/<int:tutor_id>", methods=["PUT"])
@jwt_required()
def editar_tutor(tutor_id):
    datos = request.get_json() or {}

    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    UPDATE tutores
                    SET tutor_nombre = %s,
                        tutor_ine = %s,
                        tutor_telefono = %s,
                        tutor_correo = %s
                    WHERE tutor_id = %s
                    RETURNING tutor_id
                """, (
                    datos.get("tutor_nombre"),
                    datos.get("tutor_ine"),
                    datos.get("tutor_telefono"),
                    datos.get("tutor_correo"),
                    tutor_id
                ))

                if not cursor.fetchone():
                    return jsonify({
                        "exito": False,
                        "mensaje": "Tutor no encontrado."
                    }), 404

        return jsonify({
            "exito": True,
            "mensaje": "Tutor actualizado correctamente."
        }), 200

    except Exception as error:
        print("ERROR EDITAR TUTOR:", repr(error))
        return jsonify({
            "exito": False,
            "mensaje": "No se pudo actualizar el tutor."
        }), 500


@tutores_api.route("/tutores/<int:tutor_id>/baja", methods=["PUT"])
@jwt_required()
def dar_baja_tutor(tutor_id):
    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    UPDATE tutores
                    SET tutor_activo = FALSE
                    WHERE tutor_id = %s
                    RETURNING tutor_id
                """, (tutor_id,))

                if not cursor.fetchone():
                    return jsonify({
                        "exito": False,
                        "mensaje": "Tutor no encontrado."
                    }), 404

        return jsonify({
            "exito": True,
            "mensaje": "Tutor dado de baja correctamente."
        }), 200

    except Exception as error:
        print("ERROR BAJA TUTOR:", repr(error))
        return jsonify({
            "exito": False,
            "mensaje": "No se pudo dar de baja al tutor."
        }), 500


@tutores_api.route("/tutores/<int:tutor_id>/alta", methods=["PUT"])
@jwt_required()
def dar_alta_tutor(tutor_id):
    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    UPDATE tutores
                    SET tutor_activo = TRUE
                    WHERE tutor_id = %s
                    RETURNING tutor_id
                """, (tutor_id,))

                if not cursor.fetchone():
                    return jsonify({
                        "exito": False,
                        "mensaje": "Tutor no encontrado."
                    }), 404

        return jsonify({
            "exito": True,
            "mensaje": "Tutor reactivado correctamente."
        }), 200

    except Exception as error:
        print("ERROR ALTA TUTOR:", repr(error))
        return jsonify({
            "exito": False,
            "mensaje": "No se pudo reactivar al tutor."
        }), 500

