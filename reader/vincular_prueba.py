#!/usr/bin/env python3
"""
Prepara UNA credencial de prueba en tu tabla credenciales_digitales (para probar el sensor
con la app en modo simulación, antes de tener el login real).

  python vincular_prueba.py --listar                         # ver alumnos (id, matrícula, nombre)
  python vincular_prueba.py --matricula 20258TTH89           # vincula ese alumno
  python vincular_prueba.py --alumno-id 3

Deja la credencial con:
  credencial_uid         = uid-20258TTH89            (el uid del login simulado de la app)
  credencial_token_hash  = SHA-256("mock-token-20258TTH89")   (la llave con la que firma el teléfono)
  credencial_activa      = true, emisión = ahora, expiración = dentro de 1 año
Si el alumno (o el uid) ya tenía fila en credenciales_digitales, la ACTUALIZA; no duplica.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import insert, or_, select, update

from access_logic import signing_key_from_token
from db import SchemaError, load_tables, make_engine

MOCK_UID = "uid-20258TTH89"
MOCK_TOKEN = "mock-token-20258TTH89"


def main() -> None:
    from nexo_reader import load_env_file

    load_env_file(Path(__file__).with_name(".env"))
    parser = argparse.ArgumentParser(description="Vincula una credencial de prueba")
    parser.add_argument("--listar", action="store_true")
    parser.add_argument("--matricula")
    parser.add_argument("--alumno-id", type=int)
    parser.add_argument("--uid", default=MOCK_UID)
    parser.add_argument("--token", default=MOCK_TOKEN, help="token de la app (se guarda su SHA-256)")
    args = parser.parse_args()

    engine = make_engine()
    try:
        t = load_tables(engine)
    except SchemaError as exc:
        sys.exit(f"Error: {exc}")
    a, c = t.alumnos, t.credenciales

    with engine.begin() as conn:
        if args.listar:
            print(f"{'ID':>4}  {'MATRÍCULA':<14} {'NOMBRE':<30} ESTATUS  CREDENCIAL")
            rows = conn.execute(
                select(a.c.alumno_id, a.c.alumno_matricula, a.c.alumno_nombre, a.c.alumno_estatus,
                       c.c.credencial_uid)
                .select_from(a.outerjoin(c, c.c.alumno_id == a.c.alumno_id))
                .order_by(a.c.alumno_id)
            ).all()
            for r in rows:
                print(f"{r[0]:>4}  {str(r[1]):<14} {str(r[2])[:30]:<30} {str(r[3]):<8} {r[4] or '-'}")
            return

        if args.alumno_id is None and not args.matricula:
            sys.exit("Indica --matricula o --alumno-id (o usa --listar).")
        cond = (a.c.alumno_id == args.alumno_id) if args.alumno_id is not None \
            else (a.c.alumno_matricula == args.matricula)
        alumno = conn.execute(select(a.c.alumno_id, a.c.alumno_nombre).where(cond)).first()
        if alumno is None:
            sys.exit("No existe ese alumno. Usa --listar para ver los disponibles.")

        now = datetime.now()
        values = dict(
            alumno_id=alumno[0],
            credencial_uid=args.uid,
            credencial_token_hash=signing_key_from_token(args.token),
            credencial_activa=True,
            credencial_fecha_emision=now,
            credencial_fecha_expiracion=now + timedelta(days=365),
        )
        existing = conn.execute(
            select(c.c.credencial_id).where(
                or_(c.c.alumno_id == alumno[0], c.c.credencial_uid == args.uid)
            )
        ).all()
        if len(existing) > 1:
            sys.exit("El alumno y el uid pertenecen a filas distintas de credenciales_digitales; revísalo.")
        if existing:
            conn.execute(update(c).where(c.c.credencial_id == existing[0][0]).values(**values))
            accion = "actualizada"
        else:
            conn.execute(insert(c).values(**values))
            accion = "creada"
    print(f"Credencial {accion}: alumno {alumno[0]} ({alumno[1]}) uid={args.uid}")


if __name__ == "__main__":
    main()
