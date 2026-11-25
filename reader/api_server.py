#!/usr/bin/env python3
"""
Servidor de la app NexoEscolar (corre en la PC donde está PostgreSQL).

El teléfono NO abre la base de datos: le habla a este servidor, que sí la consulta.

  python api_server.py                       # escucha en 0.0.0.0:8000
  python api_server.py --host 127.0.0.1 --port 8000

Endpoints (los que ya espera la app):
  GET  /salud                 -> {"ok": true}
  POST /auth/login            {"matricula","usuario_password"}
                              200 {"token","uid","alumno":{...}} | 401 | 429
  GET  /credencial/estado     Authorization: Bearer <token>
                              200 {"activa","telegram_vinculado"} | 401 (token ya no vigente)

Login:
  * Busca en usuarios_alumnos por usuario_login (o por la matrícula del alumno), sin distinguir
    mayúsculas, y valida usuario_password_hash.
  * uid = matrícula del alumno (distinto para cada alumno).
  * Crea/actualiza SU fila en credenciales_digitales con un token NUEVO: guarda
    credencial_token_hash = SHA-256(token). El teléfono firma con ese mismo hash, así el sensor puede
    verificar la firma. Un login nuevo invalida el teléfono anterior (un solo teléfono por cuenta).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import sys
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from sqlalchemy import func, insert, or_, select, update

from access_logic import estatus_activo
from db import LoginTables, SchemaError, load_login_tables, make_engine
from passwords import DUMMY_HASH, UnsupportedHash, hash_kind, verify_password

MAX_BODY = 4096
MAX_FAILS = 5                 # intentos fallidos por usuario+IP
LOCK_SECONDS = 300            # bloqueo tras MAX_FAILS
CREDENTIAL_DAYS = 365         # vigencia de la credencial desde cada inicio de sesión
NO_REGISTRADO = "No registrado"
BAD_LOGIN = {"mensaje": "Matrícula o contraseña incorrectas."}
SERVER_ERROR = {"mensaje": "Error del servidor."}


def _log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)


def token_hash(token: str) -> str:
    """Lo que se guarda en credencial_token_hash (y con lo que firma el teléfono)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class Api:
    """Lógica sin HTTP (se prueba directo)."""

    def __init__(self, engine, tables: LoginTables, time_fn=time.time):
        self._engine = engine
        self._t = tables
        self._time = time_fn
        self._fails: dict[tuple[str, str], tuple[int, float]] = {}
        self._lock = threading.Lock()

    # ----------------------------------------------------------- límite de intentos
    def _blocked(self, key) -> bool:
        with self._lock:
            count, since = self._fails.get(key, (0, 0.0))
            if count >= MAX_FAILS and self._time() - since < LOCK_SECONDS:
                return True
            if count >= MAX_FAILS:
                del self._fails[key]
            return False

    def _fail(self, key) -> None:
        with self._lock:
            count, _ = self._fails.get(key, (0, 0.0))
            self._fails[key] = (count + 1, self._time())

    def _clear(self, key) -> None:
        with self._lock:
            self._fails.pop(key, None)

    # ----------------------------------------------------------- login
    def login(self, body: object, ip: str) -> tuple[int, dict]:
        if not isinstance(body, dict):
            return 400, {"mensaje": "Solicitud inválida."}
        login, password = body.get("matricula"), body.get("usuario_password")
        if not (isinstance(login, str) and isinstance(password, str)):
            return 400, {"mensaje": "Faltan matrícula o contraseña."}
        login = login.strip()
        if not login or len(login) > 64 or len(password) > 128:
            return 401, BAD_LOGIN

        key = (login.upper(), ip)
        if self._blocked(key):
            return 429, {"mensaje": "Demasiados intentos. Espera unos minutos."}

        t, u, a = self._t, self._t.usuarios, self._t.alumnos
        optional = [a.c[name] for name in (
            "alumno_curp", "alumno_carrera_id", "alumno_grupo_id", "alumno_grupo", "alumno_especialidad",
        ) if name in a.c]

        with self._engine.begin() as conn:
            row = conn.execute(
                select(
                    u.c.usuario_alumno_id, u.c.usuario_password_hash, u.c.usuario_activo,
                    a.c.alumno_id, a.c.alumno_matricula, a.c.alumno_nombre,
                    a.c.alumno_estatus, a.c.baja_fecha, *optional,
                )
                .select_from(u.join(a, a.c.alumno_id == u.c.alumno_id))
                .where(or_(
                    func.upper(u.c.usuario_login) == login.upper(),
                    func.upper(a.c.alumno_matricula) == login.upper(),
                ))
                .order_by(u.c.usuario_activo.desc(), u.c.usuario_alumno_id)
                .limit(1)
            ).mappings().first()

            stored = row["usuario_password_hash"] if row is not None else None
            try:
                # Siempre se calcula un hash (tiempo parecido exista o no el usuario).
                valid = verify_password(password, stored or DUMMY_HASH)
            except UnsupportedHash as exc:
                _log(f"ERROR: formato de contraseña no soportado ({hash_kind(stored or '')}): {exc}")
                return 500, SERVER_ERROR
            if row is None or not stored or not valid or not row["usuario_activo"]:
                self._fail(key)
                return 401, BAD_LOGIN

            self._clear(key)
            matricula = row["alumno_matricula"]
            alumno_vigente = row["baja_fecha"] is None and estatus_activo(row["alumno_estatus"])

            # --- credencial nueva (invalida el teléfono anterior) -------------------------
            token = secrets.token_urlsafe(32)
            now = datetime.now().astimezone()
            c = t.credenciales
            values = dict(
                alumno_id=row["alumno_id"],
                credencial_uid=matricula,
                credencial_token_hash=token_hash(token),
                credencial_fecha_emision=now,
                credencial_fecha_expiracion=now + timedelta(days=CREDENTIAL_DAYS),
                credencial_activa=alumno_vigente,
            )
            existing = conn.execute(
                select(c.c.credencial_id).where(
                    or_(c.c.alumno_id == row["alumno_id"], c.c.credencial_uid == matricula)
                )
            ).all()
            if len(existing) > 1:
                _log(f"ERROR: el uid {matricula!r} y el alumno {row['alumno_id']} están en filas "
                     "distintas de credenciales_digitales; revisa la tabla.")
                return 500, SERVER_ERROR
            if existing:
                conn.execute(update(c).where(c.c.credencial_id == existing[0][0]).values(**values))
            else:
                conn.execute(insert(c).values(**values))

            conn.execute(
                update(u).where(u.c.usuario_alumno_id == row["usuario_alumno_id"])
                .values(usuario_ultimo_acceso=now)
            )

            carrera = self._lookup(conn, t.carreras.c.carrera_nombre, t.carreras.c.carrera_id,
                                   row.get("alumno_carrera_id")) or row.get("alumno_especialidad")
            grupo = self._lookup(conn, t.grupos.c.grupo_nombre, t.grupos.c.grupo_id,
                                 row.get("alumno_grupo_id")) or row.get("alumno_grupo")

        return 200, {
            "token": token,
            "uid": matricula,
            "alumno": {
                "matricula": matricula,
                "nombre_completo": row["alumno_nombre"],
                "curp": row.get("alumno_curp") or NO_REGISTRADO,
                "carrera": carrera or NO_REGISTRADO,
                "grupo": grupo or NO_REGISTRADO,
                "credencial_activa": alumno_vigente,
                "telegram_vinculado": False,   # paso siguiente: vinculaciones_telegram
            },
        }

    @staticmethod
    def _lookup(conn, name_col, id_col, value) -> Optional[str]:
        if value is None:
            return None
        result = conn.execute(select(name_col).where(id_col == value)).scalar()
        return str(result) if result else None

    # ----------------------------------------------------------- estado
    def estado(self, authorization: str | None) -> tuple[int, dict]:
        token = _bearer(authorization)
        if token is None:
            return 401, {"mensaje": "Sesión no válida."}
        c, a = self._t.credenciales, self._t.alumnos
        with self._engine.connect() as conn:
            row = conn.execute(
                select(c.c.credencial_activa, c.c.credencial_fecha_expiracion,
                       a.c.baja_fecha, a.c.alumno_estatus)
                .select_from(c.join(a, a.c.alumno_id == c.c.alumno_id))
                .where(c.c.credencial_token_hash == token_hash(token))
            ).mappings().first()
        if row is None:
            return 401, {"mensaje": "Tu sesión ya no es válida."}
        exp = row["credencial_fecha_expiracion"]
        vigente = exp is None or _naive(exp) >= datetime.now()
        return 200, {
            "activa": bool(row["credencial_activa"]) and vigente
            and row["baja_fecha"] is None and estatus_activo(row["alumno_estatus"]),
            "telegram_vinculado": False,
        }


def _naive(value: datetime) -> datetime:
    return value.astimezone().replace(tzinfo=None) if value.tzinfo else value


def _bearer(header: str | None) -> str | None:
    if not header or not header.startswith("Bearer "):
        return None
    token = header[7:].strip()
    return token if 20 <= len(token) <= 255 else None


def make_server(api: Api, host: str, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        server_version = "NexoApi"
        protocol_version = "HTTP/1.1"

        def _send(self, status: int, payload: dict) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _body(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length < 0 or length > MAX_BODY:
                return None
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None

        def do_GET(self):  # noqa: N802
            try:
                if self.path == "/salud":
                    self._send(200, {"ok": True})
                elif self.path == "/credencial/estado":
                    status, payload = api.estado(self.headers.get("Authorization"))
                    self._send(status, payload)
                else:
                    self._send(404, {"mensaje": "No encontrado."})
            except Exception as exc:  # noqa: BLE001 - nunca filtrar detalles al teléfono
                _log(f"ERROR estado: {type(exc).__name__}: {exc}")
                self._send(500, SERVER_ERROR)

        def do_POST(self):  # noqa: N802
            if self.path != "/auth/login":
                self._send(404, {"mensaje": "No encontrado."})
                return
            body = self._body()
            if body is None:
                self._send(400, {"mensaje": "Solicitud inválida."})
                return
            try:
                status, payload = api.login(body, self.client_address[0])
            except Exception as exc:  # noqa: BLE001
                _log(f"ERROR login: {type(exc).__name__}: {exc}")
                self._send(500, SERVER_ERROR)
                return
            who = str(body.get("matricula", ""))[:64] if isinstance(body, dict) else "?"
            print(f"[{time.strftime('%H:%M:%S')}] login {who} -> {status}", flush=True)
            self._send(status, payload)

        def log_message(self, fmt, *args):  # silencia el log por defecto
            pass

    return ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    from nexo_reader import load_env_file

    load_env_file(Path(__file__).with_name(".env"))
    parser = argparse.ArgumentParser(description="Servidor de la app NexoEscolar")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    engine = make_engine()
    try:
        tables = load_login_tables(engine)
    except SchemaError as exc:
        sys.exit(f"Error en la base de datos: {exc}")
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"No se pudo conectar a la base de datos: {type(exc).__name__}: {exc}")

    print(f"Base de datos: {engine.url.render_as_string(hide_password=True)}")
    server = make_server(Api(engine, tables), args.host, args.port)
    print(f"Servidor en http://{args.host}:{args.port}  (Ctrl+C para salir)")
    if args.host == "0.0.0.0":
        print("AVISO: HTTP sin cifrar. Úsalo solo en tu red de pruebas (o con 'adb reverse').")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSaliendo.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
