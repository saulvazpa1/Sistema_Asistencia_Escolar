#!/usr/bin/env python3
"""
Diagnóstico de "bad_signature": dice con QUÉ llave firmó el teléfono.

  1) python nexo_reader.py --dry-run          (acerca el teléfono; copia la línea PAYLOAD: {...})
  2) python probar_firma.py '{"v": 1, "uid": "...", "ts": 123, "sig": "..."}'

Usa el token de la app de prueba (mock-token-20258TTH89) y, si hay DATABASE_URL, también compara
con el credencial_token_hash que tiene la base de datos para ese uid.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from access_logic import expected_signature, signing_key_from_token

MOCK_TOKEN = "mock-token-20258TTH89"


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    payload = json.loads(sys.argv[1].removeprefix("PAYLOAD:").strip())
    uid, ts, sig = payload["uid"], payload["ts"], payload["sig"]
    token = sys.argv[2] if len(sys.argv) > 2 else MOCK_TOKEN

    candidates = {
        "token SIN hash (app VIEJA)": token,
        "SHA-256(token) (app NUEVA, correcto)": signing_key_from_token(token),
    }

    try:
        from sqlalchemy import select

        from db import load_tables, make_engine
        from nexo_reader import load_env_file

        load_env_file(Path(__file__).with_name(".env"))
        engine = make_engine()
        t = load_tables(engine)
        with engine.connect() as conn:
            row = conn.execute(
                select(t.credenciales.c.credencial_token_hash).where(
                    t.credenciales.c.credencial_uid == uid
                )
            ).first()
        if row and row[0]:
            candidates["credencial_token_hash de la BD"] = row[0]
            print(f"BD guarda para {uid}: {row[0][:12]}...  (SHA-256 del token de prueba: "
                  f"{signing_key_from_token(token)[:12]}...)")
        elif row is None:
            print(f"AVISO: la BD no tiene el uid {uid}")
    except (Exception, SystemExit) as exc:  # noqa: BLE001 - el diagnóstico sigue sin BD
        print(f"(sin comparar con la BD: {type(exc).__name__})")

    matched = [name for name, key in candidates.items() if expected_signature(key, uid, ts) == sig]
    if matched:
        print("El teléfono firmó con:", ", ".join(matched))
    else:
        print("La firma no coincide con ninguna llave conocida (¿otro token? pásalo como 2.º argumento).")


if __name__ == "__main__":
    main()