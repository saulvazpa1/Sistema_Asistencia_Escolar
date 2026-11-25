"""
Esquema MÍNIMO que usa el lector de la puerta (SQLAlchemy Core).

Los nombres de columna son los del documento del proyecto (alumno_*, tutor_*, baja_*,
asistencia_*, notificacion_*). Se escriben en minúsculas para que funcionen igual en PostgreSQL
(que pliega a minúsculas lo que no va entre comillas) y en MariaDB.

AJUSTAR a las tablas reales de la base de datos central. Lo que este módulo agrega a `alumno`:
  - uid               ID de credencial ÚNICO e inmutable de la cuenta (es lo que viaja por NFC).
  - credencial_token  Token del ÚNICO teléfono vinculado. El servidor lo REGENERA en cada login,
                      por eso un segundo teléfono invalida al primero.
  - credencial_actualizada  Cuándo se regeneró el token.
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

metadata = MetaData()

alumno = Table(
    "alumno",
    metadata,
    Column("alumno_id", Integer, primary_key=True, autoincrement=True),
    Column("alumno_matricula", String(20), nullable=False, unique=True),
    Column("alumno_nombre", String(150), nullable=False),
    Column("alumno_carrera", String(80)),
    Column("alumno_grupo", String(20)),
    Column("tutor_nombre", String(150)),
    Column("tutor_telegram_id", String(40)),  # chat_id de Telegram del tutor
    Column("baja_motivo", String(255)),
    Column("baja_fecha", DateTime),  # NULL = activo; con fecha = dado de baja
    Column("uid", String(64), nullable=False, unique=True),
    Column("credencial_token", String(255)),
    Column("credencial_actualizada", DateTime),
)

asistencia = Table(
    "asistencia",
    metadata,
    Column("asistencia_id", Integer, primary_key=True, autoincrement=True),
    Column("alumno_id", Integer, ForeignKey("alumno.alumno_id"), nullable=False),
    Column("asistencia_tipo", String(10), nullable=False),  # 'entrada' | 'salida'
    Column("asistencia_fechahora", DateTime, nullable=False),
    Column("punto_id", String(128)),
    Index("ix_asistencia_alumno_fecha", "alumno_id", "asistencia_fechahora"),
)

notificacion = Table(
    "notificacion",
    metadata,
    Column("notificacion_id", Integer, primary_key=True, autoincrement=True),
    Column("alumno_id", Integer, ForeignKey("alumno.alumno_id"), nullable=False),
    Column("tutor_telegram_id", String(40), nullable=False),
    Column("notificacion_tipo", String(10), nullable=False),
    Column("notificacion_mensaje", Text, nullable=False),
    Column("notificacion_fechahora", DateTime, nullable=False),
    Column("notificacion_estatus", String(200), nullable=False),  # pendiente | enviado | error: ...
)
