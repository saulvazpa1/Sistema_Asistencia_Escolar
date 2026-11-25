"""
API para la app móvil NexoEscolar (credencial digital del alumno).

Archivo NUEVO: no modifica alumnos.py ni ningún otro archivo de api/.

  POST /api/app/auth/login          { "matricula": "...", "usuario_password": "..." }
  GET  /api/app/credencial/estado   Authorization: Bearer <token>

Seguridad:
  * No usa JWT de flask_jwt_extended: tus rutas @jwt_required() editan y dan de baja alumnos,
    y un JWT de alumno las abriría. Aquí el "token" es el de la credencial NFC; en la base solo
    se guarda su SHA-256 (credenciales_digitales.credencial_token_hash), que es lo que el sensor
    usa para validar la firma.
  * Cada login genera un token nuevo (el teléfono anterior queda invalidado).
  * uid de la credencial = matrícula.
"""

import hashlib
import hmac
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from database.conexion import ConexionDB

app_alumnos_api = Blueprint("app_alumnos_api", __name__, url_prefix="/api/app")

CREDENCIAL_DIAS = 365
MAX_INTENTOS = 5
VENTANA_SEG = 300
NO_REGISTRADO = "No registrado"
ESTATUS_ACTIVOS = {"activo", "activa", "alta"}

_MSG_LOGIN = "Matrícula o contraseña incorrectas."
_MSG_ERROR = "No fue posible iniciar sesión. Intenta más tarde."

# Hash de relleno: se verifica siempre una contraseña, exista o no la matrícula.
_HASH_RELLENO = generate_password_hash(secrets.token_hex(8))

_intentos: dict = {}
_lock = threading.Lock()


# ----------------------------------------------------------------- utilidades
def _verificar_password(password: str, guardado: str) -> bool:
    """Acepta hashes de werkzeug (scrypt/pbkdf2) y los de crear_usuario.py (nexo-pbkdf2)."""
    try:
        if guardado.startswith("nexo-pbkdf2$"):
            _, iteraciones, sal_hex, hash_hex = guardado.split("$")
            calculado = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), bytes.fromhex(sal_hex), int(iteraciones))
            return hmac.compare_digest(calculado.hex(), hash_hex)
        return check_password_hash(guardado, password)
    except (ValueError, TypeError, IndexError):
        return False


def _sha256(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _bloqueado(clave) -> bool:
    with _lock:
        ahora = time.time()
        vivos = [t for t in _intentos.get(clave, []) if ahora - t < VENTANA_SEG]
        _intentos[clave] = vivos
        return len(vivos) >= MAX_INTENTOS


def _fallo(clave) -> None:
    with _lock:
        _intentos.setdefault(clave, []).append(time.time())


def _limpiar(clave) -> None:
    with _lock:
        _intentos.pop(clave, None)


def _alumno_vigente(estatus, baja_fecha) -> bool:
    return baja_fecha is None and str(estatus or "").strip().lower() in ESTATUS_ACTIVOS


def _bearer(cabecera):
    if not cabecera or not cabecera.lower().startswith("bearer "):
        return None
    token = cabecera[7:].strip()
    return token or None


# ---------------------------------------------------------------------- login
@app_alumnos_api.route("/auth/login", methods=["POST"])
@app_alumnos_api.route("/login", methods=["POST"])
def login_alumno():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify({"exito": False, "mensaje": "Solicitud inválida."}), 400

    usuario = datos.get("matricula")
    password = datos.get("usuario_password")
    if not isinstance(usuario, str) or not isinstance(password, str):
        return jsonify({"exito": False, "mensaje": "Faltan matrícula o contraseña."}), 400

    usuario = usuario.strip()
    if not usuario or len(usuario) > 64 or len(password) > 128:
        return jsonify({"exito": False, "mensaje": _MSG_LOGIN}), 401

    clave = (usuario.upper(), request.remote_addr)
    if _bloqueado(clave):
        return jsonify({"exito": False,
                        "mensaje": "Demasiados intentos. Espera unos minutos."}), 429

    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    SELECT u.usuario_alumno_id, u.usuario_password_hash, u.usuario_activo,
                           a.alumno_id, a.alumno_matricula, a.alumno_nombre, a.alumno_curp,
                           a.alumno_estatus, a.baja_fecha,
                           a.alumno_carrera_id, a.alumno_grupo_id,
                           a.alumno_grupo, a.alumno_especialidad
                    FROM usuarios_alumnos u
                    JOIN alumnos a ON a.alumno_id = u.alumno_id
                    WHERE UPPER(u.usuario_login) = UPPER(%s)
                       OR UPPER(a.alumno_matricula) = UPPER(%s)
                    ORDER BY u.usuario_activo DESC, u.usuario_alumno_id
                    LIMIT 1
                """, (usuario, usuario))
                fila = cursor.fetchone()

                guardado = fila[1] if fila else None
                valido = _verificar_password(password, guardado or _HASH_RELLENO)

                if fila is None or not guardado or not valido or not fila[2]:
                    _fallo(clave)
                    return jsonify({"exito": False, "mensaje": _MSG_LOGIN}), 401

                _limpiar(clave)
                (usuario_id, _h, _act, alumno_id, matricula, nombre, curp,
                 estatus, baja_fecha, carrera_id, grupo_id,
                 grupo_txt, especialidad_txt) = fila
                vigente = _alumno_vigente(estatus, baja_fecha)

                # --- credencial nueva (invalida el teléfono anterior) ---
                token = secrets.token_urlsafe(32)
                ahora = datetime.now(timezone.utc)
                expira = ahora + timedelta(days=CREDENCIAL_DIAS)

                cursor.execute("""
                    SELECT credencial_id FROM credenciales_digitales
                    WHERE alumno_id = %s OR credencial_uid = %s
                """, (alumno_id, matricula))
                existentes = cursor.fetchall()
                if len(existentes) > 1:
                    print("ERROR LOGIN APP: uid/alumno en filas distintas de "
                          "credenciales_digitales:", matricula, alumno_id)
                    return jsonify({"exito": False, "mensaje": _MSG_ERROR}), 500

                if existentes:
                    cursor.execute("""
                        UPDATE credenciales_digitales
                        SET alumno_id = %s, credencial_uid = %s, credencial_token_hash = %s,
                            credencial_fecha_emision = %s, credencial_fecha_expiracion = %s,
                            credencial_activa = %s
                        WHERE credencial_id = %s
                    """, (alumno_id, matricula, _sha256(token), ahora, expira,
                          vigente, existentes[0][0]))
                else:
                    cursor.execute("""
                        INSERT INTO credenciales_digitales
                            (alumno_id, credencial_uid, credencial_token_hash,
                             credencial_fecha_emision, credencial_fecha_expiracion,
                             credencial_activa)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (alumno_id, matricula, _sha256(token), ahora, expira, vigente))

                cursor.execute(
                    "UPDATE usuarios_alumnos SET usuario_ultimo_acceso = %s "
                    "WHERE usuario_alumno_id = %s", (ahora, usuario_id))

                carrera = None
                if carrera_id is not None:
                    cursor.execute("SELECT carrera_nombre FROM carreras WHERE carrera_id = %s",
                                   (carrera_id,))
                    r = cursor.fetchone()
                    carrera = r[0] if r else None
                grupo = None
                if grupo_id is not None:
                    cursor.execute("SELECT grupo_nombre FROM grupos WHERE grupo_id = %s",
                                   (grupo_id,))
                    r = cursor.fetchone()
                    grupo = r[0] if r else None

        return jsonify({
            "token": token,
            "uid": matricula,
            "alumno": {
                "matricula": matricula,
                "nombre_completo": nombre,
                "curp": curp or NO_REGISTRADO,
                "carrera": carrera or especialidad_txt or NO_REGISTRADO,
                "grupo": grupo or grupo_txt or NO_REGISTRADO,
                "credencial_activa": vigente,
                "telegram_vinculado": False,  # siguiente paso: vinculaciones_telegram
            },
        }), 200

    except Exception as error:
        print("ERROR LOGIN APP:", repr(error))
        return jsonify({"exito": False, "mensaje": _MSG_ERROR}), 500


# --------------------------------------------------------------------- estado
@app_alumnos_api.route("/credencial/estado", methods=["GET"])
def estado_credencial():
    token = _bearer(request.headers.get("Authorization"))
    if token is None:
        return jsonify({"exito": False, "mensaje": "Sesión no válida."}), 401

    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    SELECT c.credencial_activa, c.credencial_fecha_expiracion,
                           a.baja_fecha, a.alumno_estatus
                    FROM credenciales_digitales c
                    JOIN alumnos a ON a.alumno_id = c.alumno_id
                    WHERE c.credencial_token_hash = %s
                """, (_sha256(token),))
                fila = cursor.fetchone()

        if fila is None:
            return jsonify({"exito": False, "mensaje": "Tu sesión ya no es válida."}), 401

        activa, expira, baja_fecha, estatus = fila
        if expira is not None:
            if expira.tzinfo is None:
                expira = expira.astimezone()  # hora local del servidor
            vigente = expira >= datetime.now(timezone.utc)
        else:
            vigente = True

        return jsonify({
            "activa": bool(activa) and vigente and _alumno_vigente(estatus, baja_fecha),
            "telegram_vinculado": False,
        }), 200

    except Exception as error:
        print("ERROR ESTADO CREDENCIAL:", repr(error))
        return jsonify({"exito": False, "mensaje": "No se pudo consultar el estado."}), 500