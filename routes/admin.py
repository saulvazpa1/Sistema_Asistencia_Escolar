
from flask import Blueprint, render_template, request, redirect, url_for,flash
from psycopg.rows import dict_row
import traceback
import re
from database.conexion import ConexionDB
from services.validaciones import (
    validar_nombre,
    validar_telefono,
    validar_ine,
    validar_correo,
)
from psycopg import errors
admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
def panel_admin():
    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor(row_factory=dict_row) as cursor:

                cursor.execute("SELECT COUNT(*) AS total FROM alumnos")
                total_alumnos = cursor.fetchone()["total"]

                cursor.execute("SELECT COUNT(*) AS total FROM tutores")
                total_tutores = cursor.fetchone()["total"]

                cursor.execute("""
                    SELECT COUNT(*) AS total
                    FROM tutores
                    WHERE tutor_telegram_vinculado = TRUE
                """)
                tutores_vinculados = cursor.fetchone()["total"]

                cursor.execute("""
                    SELECT COUNT(*) AS total
                    FROM alumnos
                    WHERE LOWER(TRIM(alumno_estatus)) = 'activo'
                """)
                alumnos_activos = cursor.fetchone()["total"]

                # Alumnos y tutor principal
                cursor.execute("""
                    SELECT
                        a.alumno_id,
                        a.alumno_matricula,
                        a.alumno_nombre,
                        a.alumno_curp,
                        a.alumno_grado,
                        a.alumno_grupo,
                        a.alumno_especialidad,
                        a.alumno_fecha_registro,
                        a.alumno_estatus,
                        t.tutor_nombre,
                        t.tutor_telefono,
                        t.tutor_correo,
                        t.tutor_telegram_vinculado,
                        CASE WHEN t.tutor_telegram_vinculado
                             THEN 'Vinculado' ELSE 'Pendiente'
                        END AS telegram_estado
                    FROM alumnos a
                    LEFT JOIN alumnos_tutores at
                        ON a.alumno_id = at.alumno_id
                        AND at.es_tutor_principal = TRUE
                    LEFT JOIN tutores t
                        ON at.tutor_id = t.tutor_id
                    ORDER BY a.alumno_id DESC
                """)
                alumnos = cursor.fetchall()

                # Tutores
                cursor.execute("""
                    SELECT
                        tutor_id,
                        tutor_nombre,
                        tutor_ine,
                        tutor_telefono,
                        tutor_correo,
                        tutor_telegram_vinculado,
                        tutor_activo,
                        CASE WHEN tutor_telegram_vinculado
                             THEN 'Vinculado' ELSE 'Pendiente'
                        END AS telegram_estado
                    FROM tutores
                    ORDER BY tutor_id DESC
                """)
                tutores = cursor.fetchall()

        return render_template(
            "admin.html",
            total_alumnos=total_alumnos,
            total_tutores=total_tutores,
            tutores_vinculados=tutores_vinculados,
            alumnos_activos=alumnos_activos,
            alumnos=alumnos,
            tutores=tutores
        )

    except Exception as error:
        print("ERROR EN PANEL ADMINISTRADOR:", repr(error))
        traceback.print_exc()
        return "Ocurrió un error al cargar el panel administrador.", 500

# EDITAR ALUMNO
@admin_bp.route("/admin/alumno/<int:alumno_id>/editar", methods=["POST"])
def editar_alumno(alumno_id):

    matricula = request.form.get("matricula", "").strip()
    nombre = " ".join(request.form.get("nombre", "").split())
    curp = request.form.get("curp", "").strip().upper()
    grado = request.form.get("grado", "").strip()
    grupo = request.form.get("grupo", "").strip().upper()
    especialidad = request.form.get("especialidad", "").strip()

    def error(mensaje):
        flash(mensaje, "error")
        return redirect(url_for("admin.panel_admin"))

    if not matricula:
        return error("Ingresa la matrícula del alumno.")

    if not nombre:
        return error("Ingresa el nombre completo del alumno.")
    if not validar_nombre(nombre):
        return error("Ingresa un nombre válido para el alumno.")

    if not re.fullmatch(r"[A-Z0-9]{18}", curp):
        return error("La CURP debe contener exactamente 18 caracteres.")

    if not grado.isdigit() or not 1 <= int(grado) <= 25:
        return error("El grado debe ser un número entre 1 y 25.")

    if not re.fullmatch(r"[A-Z0-9]{1,10}", grupo):
        return error("Ingresa un grupo válido (máximo 10 caracteres).")

    if len(especialidad) > 100:
        return error("La especialidad no puede pasar de 100 caracteres.")

    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    UPDATE alumnos
                    SET
                        alumno_matricula = %s,
                        alumno_nombre = %s,
                        alumno_curp = %s,
                        alumno_grado = %s,
                        alumno_grupo = %s,
                        alumno_especialidad = %s
                    WHERE alumno_id = %s
                """, (
                    matricula,
                    nombre,
                    curp,
                    int(grado),
                    grupo,
                    especialidad or None,
                    alumno_id
                ))

                if cursor.rowcount == 0:
                    flash("No se encontró el alumno.", "error")
                else:
                    flash("Alumno actualizado correctamente.", "success")

    except errors.UniqueViolation:
        flash("Esa matrícula ya está registrada en otro alumno.", "error")

    except Exception as e:
        print("ERROR AL EDITAR ALUMNO:", repr(e))
        traceback.print_exc()
        flash("No se pudo actualizar el alumno. Intenta de nuevo.", "error")

    return redirect(url_for("admin.panel_admin"))


# EDITAR TUTOR
@admin_bp.route("/admin/tutor/<int:tutor_id>/editar", methods=["POST"])
def editar_tutor(tutor_id):

    nombre = " ".join(request.form.get("nombre", "").split())
    ine = request.form.get("ine", "").strip().upper()
    telefono = request.form.get("telefono", "").strip()
    correo = request.form.get("correo", "").strip()

    def error(mensaje):
        flash(mensaje, "error")
        return redirect(url_for("admin.panel_admin"))

    if not nombre:
        return error("Ingresa el nombre completo del tutor.")
    if not validar_nombre(nombre):
        return error("Ingresa un nombre válido para el tutor.")

    if not ine:
        return error("Ingresa la clave de elector.")
    if not validar_ine(ine):
        return error("La clave de elector debe tener 18 caracteres.")

    if not telefono:
        return error("Ingresa el teléfono del tutor.")
    if not validar_telefono(telefono):
        return error("El teléfono debe tener exactamente 10 dígitos.")

    if not validar_correo(correo):
        return error("Ingresa un correo válido.")

    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    UPDATE tutores
                    SET
                        tutor_nombre = %s,
                        tutor_ine = %s,
                        tutor_telefono = %s,
                        tutor_correo = %s
                    WHERE tutor_id = %s
                """, (
                    nombre,
                    ine,
                    telefono,
                    correo or None,
                    tutor_id
                ))

                if cursor.rowcount == 0:
                    flash("No se encontró el tutor.", "error")
                else:
                    flash("Tutor actualizado correctamente.", "success")

    except errors.UniqueViolation:
        flash("Ese INE ya está registrado en otro tutor.", "error")

    except Exception as e:
        print("ERROR AL EDITAR TUTOR:", repr(e))
        traceback.print_exc()
        flash("No se pudo actualizar el tutor. Intenta de nuevo.", "error")

    return redirect(url_for("admin.panel_admin"))
@admin_bp.route("/admin/alumno/<int:alumno_id>/baja", methods=["POST"])
def dar_baja_alumno(alumno_id):
    print(">>> RUTA NUEVA dar_baja_alumno, id:", alumno_id)
    motivo = request.form.get("motivo", "").strip()
    print(">>> Motivo recibido:", repr(motivo))

    if not motivo:
        flash("Debes escribir el motivo de la baja.", "error")
        return redirect(url_for("admin.panel_admin"))

    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:

                # Diagnóstico: qué base y qué alumno ve Flask
                cursor.execute("SELECT current_database(), inet_server_port()")
                print(">>> BD de Flask:", cursor.fetchone())

                cursor.execute("""
                    SELECT alumno_id, alumno_estatus
                    FROM alumnos
                    WHERE alumno_id = %s
                """, (alumno_id,))
                print(">>> Alumno visto por Flask:", cursor.fetchone())

                cursor.execute("""
                    UPDATE alumnos
                    SET alumno_estatus = 'baja',
                        baja_motivo = %s,
                        baja_fecha = CURRENT_TIMESTAMP
                    WHERE alumno_id = %s
                      AND LOWER(TRIM(alumno_estatus)) = 'activo'
                """, (motivo, alumno_id))

                print(">>> Filas actualizadas:", cursor.rowcount)

                if cursor.rowcount == 0:
                    flash("No se encontró un alumno activo.", "error")
                else:
                    flash("Alumno dado de baja correctamente.", "success")

    except Exception as error:
        print("ERROR AL DAR DE BAJA:", repr(error))
        traceback.print_exc()
        flash("Ocurrió un error al dar de baja al alumno.", "error")

    return redirect(url_for("admin.panel_admin"))


@admin_bp.route("/admin/tutor/<int:tutor_id>/baja", methods=["POST"])
def dar_baja_tutor(tutor_id):
    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    UPDATE tutores
                    SET tutor_activo = FALSE
                    WHERE tutor_id = %s AND tutor_activo = TRUE
                """, (tutor_id,))

                if cursor.rowcount == 0:
                    flash("No se encontró un tutor activo.", "error")
                else:
                    flash("Tutor dado de baja correctamente.", "success")

    except Exception as error:
        print("ERROR AL DAR DE BAJA AL TUTOR:", repr(error))
        traceback.print_exc()
        flash("Ocurrió un error al dar de baja al tutor.", "error")

    return redirect(url_for("admin.panel_admin"))



# DAR DE ALTA (REACTIVAR) ALUMNO
@admin_bp.route("/admin/alumno/<int:alumno_id>/alta", methods=["POST"])
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
                      AND LOWER(TRIM(alumno_estatus)) <> 'activo'
                """, (alumno_id,))

                if cursor.rowcount == 0:
                    flash("No se encontró un alumno dado de baja.", "error")
                else:
                    flash("Alumno reactivado correctamente.", "success")

    except Exception as error:
        print("ERROR AL REACTIVAR ALUMNO:", repr(error))
        traceback.print_exc()
        flash("Ocurrió un error al reactivar al alumno.", "error")

    return redirect(url_for("admin.panel_admin"))


# DAR DE ALTA (REACTIVAR) TUTOR
@admin_bp.route("/admin/tutor/<int:tutor_id>/alta", methods=["POST"])
def dar_alta_tutor(tutor_id):
    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    UPDATE tutores
                    SET tutor_activo = TRUE
                    WHERE tutor_id = %s AND tutor_activo = FALSE
                """, (tutor_id,))

                if cursor.rowcount == 0:
                    flash("No se encontró un tutor dado de baja.", "error")
                else:
                    flash("Tutor reactivado correctamente.", "success")

    except Exception as error:
        print("ERROR AL REACTIVAR TUTOR:", repr(error))
        traceback.print_exc()
        flash("Ocurrió un error al reactivar al tutor.", "error")

    return redirect(url_for("admin.panel_admin"))