
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from database.conexion import ConexionDB

alumnos_api = Blueprint("alumnos_api", __name__, url_prefix="/api")


@alumnos_api.route("/alumnos", methods=["GET"])
@jwt_required()
def obtener_alumnos():
    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        alumno_id,
                        alumno_matricula,
                        alumno_nombre,
                        alumno_curp,
                        alumno_grado,
                        alumno_grupo,
                        alumno_especialidad,
                        alumno_estatus,
                        baja_motivo,
                        baja_fecha
                    FROM alumnos
                    ORDER BY alumno_id
                """)

                columnas = [col.name for col in cursor.description]
                alumnos = [
                    dict(zip(columnas, fila))
                    for fila in cursor.fetchall()
                ]

        return jsonify({
            "exito": True,
            "alumnos": alumnos
        }), 200

    except Exception as error:
        print("ERROR API ALUMNOS:", repr(error))
        return jsonify({
            "exito": False,
            "mensaje": "No se pudieron consultar los alumnos."
        }), 500


@alumnos_api.route("/alumnos/<int:alumno_id>", methods=["PUT"])
@jwt_required()
def editar_alumno(alumno_id):
    datos = request.get_json() or {}

    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    UPDATE alumnos
                    SET alumno_matricula = %s,
                        alumno_nombre = %s,
                        alumno_curp = %s,
                        alumno_grado = %s,
                        alumno_grupo = %s,
                        alumno_especialidad = %s
                    WHERE alumno_id = %s
                    RETURNING alumno_id
                """, (
                    datos.get("alumno_matricula"),
                    datos.get("alumno_nombre"),
                    datos.get("alumno_curp"),
                    datos.get("alumno_grado"),
                    datos.get("alumno_grupo"),
                    datos.get("alumno_especialidad"),
                    alumno_id
                ))

                if not cursor.fetchone():
                    return jsonify({
                        "exito": False,
                        "mensaje": "Alumno no encontrado."
                    }), 404

        return jsonify({
            "exito": True,
            "mensaje": "Alumno actualizado correctamente."
        }), 200

    except Exception as error:
        print("ERROR EDITAR ALUMNO:", repr(error))
        return jsonify({
            "exito": False,
            "mensaje": "No se pudo actualizar el alumno."
        }), 500


@alumnos_api.route("/alumnos/<int:alumno_id>/baja", methods=["PUT"])
@jwt_required()
def dar_baja_alumno(alumno_id):
    datos = request.get_json() or {}
    motivo = datos.get("motivo", "").strip()

    if not motivo:
        return jsonify({
            "exito": False,
            "mensaje": "Debes indicar el motivo de la baja."
        }), 400

    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    UPDATE alumnos
                    SET alumno_estatus = 'baja',
                        baja_motivo = %s,
                        baja_fecha = CURRENT_TIMESTAMP
                    WHERE alumno_id = %s
                    RETURNING alumno_id
                """, (motivo, alumno_id))

                if not cursor.fetchone():
                    return jsonify({
                        "exito": False,
                        "mensaje": "Alumno no encontrado."
                    }), 404

        return jsonify({
            "exito": True,
            "mensaje": "Alumno dado de baja correctamente."
        }), 200

    except Exception as error:
        print("ERROR BAJA ALUMNO:", repr(error))
        return jsonify({
            "exito": False,
            "mensaje": "No se pudo dar de baja al alumno."
        }), 500


@alumnos_api.route("/alumnos/<int:alumno_id>/alta", methods=["PUT"])
@jwt_required()
def dar_alta_alumno(alumno_id):
    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    UPDATE alumnos
                    SET alumno_estatus = 'activo',
                        baja_motivo = NULL,
                        baja_fecha = NULL
                    WHERE alumno_id = %s
                    RETURNING alumno_id
                """, (alumno_id,))

                if not cursor.fetchone():
                    return jsonify({
                        "exito": False,
                        "mensaje": "Alumno no encontrado."
                    }), 404

        return jsonify({
            "exito": True,
            "mensaje": "Alumno reactivado correctamente."
        }), 200

    except Exception as error:
        print("ERROR ALTA ALUMNO:", repr(error))
        return jsonify({
            "exito": False,
            "mensaje": "No se pudo reactivar al alumno."
        }), 500
