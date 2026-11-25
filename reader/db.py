"""
Conexión a PostgreSQL y acceso a TUS tablas (sin redefinirlas ni modificarlas).

El sensor usa solo 3 tablas de `public`:
  credenciales_digitales  credencial_uid, credencial_token_hash, credencial_activa,
                          credencial_fecha_expiracion, credencial_ultimo_uso, alumno_id
  alumnos                 alumno_id, alumno_matricula, alumno_nombre, alumno_estatus, baja_fecha
  asistencias             alumno_id, asistencia_tipo, asistencia_fechahora, asistencia_metodo,
                          asistencia_dispositivo, asistencia_observaciones, usuario_id

Las tablas se LEEN de la propia base de datos (reflexión), así los tipos (boolean, enum,
timestamp...) son exactamente los tuyos.

DATABASE_URL (variable de entorno o archivo .env junto a estos scripts):
  postgresql+psycopg2://usuario:clave@localhost:5432/nombre_de_tu_bd
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from sqlalchemy import MetaData, Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoSuchTableError

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "credenciales_digitales": (
        "credencial_id", "alumno_id", "credencial_uid", "credencial_token_hash",
        "credencial_activa", "credencial_fecha_expiracion", "credencial_ultimo_uso",
    ),
    "alumnos": (
        "alumno_id", "alumno_matricula", "alumno_nombre", "alumno_estatus", "baja_fecha",
    ),
    "asistencias": (
        "asistencia_id", "alumno_id", "asistencia_tipo", "asistencia_fechahora",
        "asistencia_metodo", "asistencia_dispositivo", "asistencia_observaciones", "usuario_id",
    ),
}

# Tablas extra que usa el SERVIDOR de la app (login). El sensor no las necesita.
LOGIN_COLUMNS: dict[str, tuple[str, ...]] = {
    "usuarios_alumnos": (
        "usuario_alumno_id", "alumno_id", "usuario_login", "usuario_password_hash",
        "usuario_activo", "usuario_ultimo_acceso",
    ),
    "carreras": ("carrera_id", "carrera_nombre"),
    "grupos": ("grupo_id", "grupo_nombre"),
}


class SchemaError(Exception):
    """La base de datos no tiene lo que el sensor necesita."""


@dataclass(frozen=True)
class Tables:
    credenciales: Table
    alumnos: Table
    asistencias: Table


@dataclass(frozen=True)
class LoginTables(Tables):
    usuarios: Table
    carreras: Table
    grupos: Table


def make_engine(url: str | None = None) -> Engine:
    url = url or os.environ.get("DATABASE_URL", "")
    if not url:
        sys.exit(
            "Falta DATABASE_URL. Crea el archivo .env junto a nexo_reader.py con:\n"
            "  DATABASE_URL=postgresql+psycopg2://usuario:clave@localhost:5432/nombre_de_tu_bd"
        )
    return create_engine(url, pool_pre_ping=True)


def _reflect(engine: Engine, required: dict[str, tuple[str, ...]], metadata: MetaData) -> dict[str, Table]:
    loaded: dict[str, Table] = {}
    for name, columns in required.items():
        try:
            table = Table(name, metadata, autoload_with=engine)
        except NoSuchTableError as exc:
            raise SchemaError(f"No existe la tabla {name!r} en la base de datos.") from exc
        missing = [c for c in columns if c not in table.c]
        if missing:
            raise SchemaError(f"A la tabla {name!r} le faltan las columnas: {', '.join(missing)}")
        loaded[name] = table
    return loaded


def load_tables(engine: Engine) -> Tables:
    """Refleja las 3 tablas del sensor y comprueba que tengan las columnas esperadas."""
    loaded = _reflect(engine, REQUIRED_COLUMNS, MetaData())
    return Tables(loaded["credenciales_digitales"], loaded["alumnos"], loaded["asistencias"])


def load_login_tables(engine: Engine) -> LoginTables:
    """Las 3 del sensor + usuarios_alumnos, carreras y grupos (servidor de la app)."""
    metadata = MetaData()
    base = _reflect(engine, REQUIRED_COLUMNS, metadata)
    extra = _reflect(engine, LOGIN_COLUMNS, metadata)
    return LoginTables(
        base["credenciales_digitales"], base["alumnos"], base["asistencias"],
        extra["usuarios_alumnos"], extra["carreras"], extra["grupos"],
    )
