#!/usr/bin/env python3
"""
Crea o cambia el usuario de la app de un alumno (tabla usuarios_alumnos).

  python crear_usuario.py --listar                 # alumnos y si ya tienen usuario/contraseña
  python crear_usuario.py 20252DSM010              # pide la contraseña (no se muestra)
  python crear_usuario.py 20252DSM010 --password MiClave123

usuario_login = la matrícula. Si el alumno ya tenía usuario, solo cambia su contraseña y lo reactiva.
La contraseña se guarda con hash (PBKDF2); nunca en texto plano.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, insert, select, update

from db import SchemaError, load_login_tables, make_engine
from passwords import hash_kind, hash_password

MIN_PASSWORD = 8


def main() -> None:
    from nexo_reader import load_env_file

    load_env_file(Path(__file__).with_name(".env"))
    parser = argparse.ArgumentParser(description="Usuarios de la app NexoEscolar")
    parser.add_argument("matricula", nargs="?")
    parser.add_argument("--password")
    parser.add_argument("--listar", action="store_true")
    args = parser.parse_args()

    engine = make_engine()
    try:
        t = load_login_tables(engine)
    except SchemaError as exc:
        sys.exit(f"Error: {exc}")
    a, u = t.alumnos, t.usuarios

    with engine.begin() as conn:
        if args.listar:
            print(f"{'ID':>4}  {'MATRÍCULA':<18} {'NOMBRE':<28} {'USUARIO':<8} FORMATO CLAVE")
            rows = conn.execute(
                select(a.c.alumno_id, a.c.alumno_matricula, a.c.alumno_nombre,
                       u.c.usuario_activo, u.c.usuario_password_hash)
                .select_from(a.outerjoin(u, u.c.alumno_id == a.c.alumno_id))
                .order_by(a.c.alumno_id)
            ).all()
            for r in rows:
                estado = "-" if r[3] is None else ("activo" if r[3] else "INACTIVO")
                formato = hash_kind(r[4]) if r[4] else "-"
                print(f"{r[0]:>4}  {str(r[1]):<18} {str(r[2])[:28]:<28} {estado:<8} {formato}")
            return

        if not args.matricula:
            sys.exit("Indica la matrícula (o usa --listar).")
        alumno = conn.execute(
            select(a.c.alumno_id, a.c.alumno_matricula, a.c.alumno_nombre)
            .where(func.upper(a.c.alumno_matricula) == args.matricula.upper())
        ).first()
        if alumno is None:
            sys.exit("No existe ese alumno. Usa --listar para ver los disponibles.")

        password = args.password
        if not password:
            password = getpass.getpass("Nueva contraseña: ")
            if password != getpass.getpass("Repite la contraseña: "):
                sys.exit("Las contraseñas no coinciden.")
        if len(password) < MIN_PASSWORD:
            sys.exit(f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres.")

        hashed = hash_password(password)
        existing = conn.execute(
            select(u.c.usuario_alumno_id).where(u.c.alumno_id == alumno[0])
        ).first()
        if existing:
            conn.execute(update(u).where(u.c.usuario_alumno_id == existing[0]).values(
                usuario_password_hash=hashed, usuario_activo=True, debe_cambiar_password=False))
            accion = "actualizado"
        else:
            conn.execute(insert(u).values(
                alumno_id=alumno[0], usuario_login=alumno[1], usuario_password_hash=hashed,
                usuario_activo=True, debe_cambiar_password=False,
                usuario_fecha_creacion=datetime.now().astimezone()))
            accion = "creado"
    print(f"Usuario {accion}: {alumno[1]} ({alumno[2]}). Ya puede iniciar sesión en la app.")


if __name__ == "__main__":
    main()
