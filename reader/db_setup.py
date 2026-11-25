#!/usr/bin/env python3
"""
Crea las tablas del lector y, opcionalmente, siembra un alumno de prueba.

  python db_setup.py                       # crea tablas (no borra nada existente)
  python db_setup.py --demo --chat-id 123456789
  python db_setup.py --demo --baja         # alumno de prueba DADO DE BAJA
  python db_setup.py --demo --chat-id 123456789 --token otro-token

El alumno demo coincide con el login simulado de la app (USE_MOCK):
  matrícula 20258TTH89 / contraseña nexo1234 / uid uid-20258TTH89 / token mock-token-20258TTH89

DATABASE_URL (variable de entorno o .env):
  sqlite:///nexo_demo.db                                   (por defecto, para pruebas)
  postgresql+psycopg2://usuario:clave@localhost:5432/nexo  (pip install psycopg2-binary)
  mysql+pymysql://usuario:clave@localhost:3306/nexo        (MariaDB; pip install pymysql)
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

from sqlalchemy import create_engine, delete, insert, select

from db_schema import alumno, metadata

DEFAULT_URL = "sqlite:///nexo_demo.db"


def make_engine(url: str | None = None):
    return create_engine(url or os.environ.get("DATABASE_URL", DEFAULT_URL), pool_pre_ping=True)


def seed_demo(engine, *, chat_id: str | None, baja: bool, token: str) -> None:
    now = datetime.now()
    with engine.begin() as conn:
        existing = conn.execute(
            select(alumno.c.alumno_id).where(alumno.c.uid == "uid-20258TTH89")
        ).first()
        if existing:
            conn.execute(delete(alumno).where(alumno.c.alumno_id == existing[0]))
        conn.execute(
            insert(alumno).values(
                alumno_matricula="20258TTH89",
                alumno_nombre="Bot Sanchez Perez",
                alumno_carrera="TTH",
                alumno_grupo="4A",
                tutor_nombre="Tutor de prueba",
                tutor_telegram_id=chat_id,
                baja_motivo="Prueba de baja" if baja else None,
                baja_fecha=now if baja else None,
                uid="uid-20258TTH89",
                credencial_token=token,
                credencial_actualizada=now,
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepara la base de datos del lector")
    parser.add_argument("--url", help="DATABASE_URL (por defecto la variable de entorno)")
    parser.add_argument("--demo", action="store_true", help="siembra el alumno de prueba")
    parser.add_argument("--chat-id", help="chat_id de Telegram del tutor de prueba")
    parser.add_argument("--baja", action="store_true", help="el alumno demo queda dado de baja")
    parser.add_argument("--token", default="mock-token-20258TTH89")
    args = parser.parse_args()

    engine = make_engine(args.url)
    metadata.create_all(engine)
    print(f"Tablas listas en: {engine.url.render_as_string(hide_password=True)}")

    if args.demo:
        seed_demo(engine, chat_id=args.chat_id, baja=args.baja, token=args.token)
        print(
            "Alumno demo sembrado: uid-20258TTH89"
            f" | baja={'sí' if args.baja else 'no'} | telegram={args.chat_id or 'sin chat_id'}"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"Error: {exc}")
