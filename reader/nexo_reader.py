#!/usr/bin/env python3
"""
NexoEscolar - Sensor de puerta (ACR122U por PC/SC + base de datos PostgreSQL).

Corre en la PC conectada por USB al lector NFC. Cuando un alumno acerca su teléfono:
  1. Envía SELECT AID  F0 4E 45 58 4F 01  al teléfono (HCE).
  2. Recibe  {"v":1,"uid","ts","sig"}  (juntando fragmentos con GET RESPONSE si hace falta).
  3. Busca el `uid` en credenciales_digitales y valida: activa, no expirada, firma, alumno sin baja.
  4. Alterna ENTRADA / SALIDA e INSERTA la hora en la tabla asistencias  (ver access_logic.py).

Instalación (una vez):
  pip install -r requirements.txt
  copy .env.example .env          # y escribe tu DATABASE_URL de PostgreSQL

Uso:
  python nexo_reader.py --list                        # lectores PC/SC detectados
  python nexo_reader.py --check-db                    # prueba la conexión y las 3 tablas
  python nexo_reader.py --dry-run --debug             # imprime lo que manda el teléfono (sin BD)
  python nexo_reader.py --point PUERTA_PRINCIPAL      # modo normal: registra en asistencias
  python nexo_reader.py --test-telegram 123456789     # (siguiente paso) prueba el bot de Telegram

Configuración (variables de entorno o archivo .env junto a este script; ver .env.example):
  DATABASE_URL
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

AID = bytes.fromhex("F04E45584F01")
SELECT_APDU = [0x00, 0xA4, 0x04, 0x00, len(AID), *AID, 0x00]

MAX_CLOCK_SKEW_S = 90        # el "ts" del teléfono no puede ser más viejo que esto
COOLDOWN_S = 2.0             # pausa tras cada lectura para no registrar doble
POLL_S = 0.25                # frecuencia de sondeo del lector


class CredentialError(Exception):
    """El teléfono no respondió con una credencial válida."""


# --------------------------------------------------------------------------- .env

def load_env_file(path: Path) -> None:
    """Carga KEY=VALUE de un .env sin pisar variables ya definidas."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


# --------------------------------------------------------------------------- APDU

SELECT_ATTEMPTS = 3          # el servicio HCE puede tardar en arrancar en el primer SELECT


def _hex(data) -> str:
    return " ".join(f"{b:02X}" for b in data)


def read_credential(connection, log=None) -> dict:
    """SELECT AID + GET RESPONSE encadenado. `connection` expone transmit(list[int]).
    `log(msg)` (opcional) imprime cada APDU: se usa con --debug."""
    say = log or (lambda _m: None)

    data, sw1, sw2 = [], 0, 0
    last_exc: Exception | None = None
    for attempt in range(1, SELECT_ATTEMPTS + 1):
        try:
            say(f"-> SELECT  {_hex(SELECT_APDU)}  (intento {attempt})")
            data, sw1, sw2 = connection.transmit(SELECT_APDU)
            say(f"<- {len(data)} bytes  SW={sw1:02X}{sw2:02X}")
            last_exc = None
        except Exception as exc:  # noqa: BLE001 - pyscard lanza varios tipos
            last_exc = exc
            say(f"<- ERROR de transmisión: {exc}")
            time.sleep(0.15)
            continue
        if (sw1, sw2) != (0x6A, 0x82) or attempt == SELECT_ATTEMPTS:
            break
        time.sleep(0.15)  # 6A82 en frío: el servicio aún no estaba listo
    if last_exc is not None:
        raise last_exc
    buffer = bytes(data)

    # 61 xx: quedan xx bytes -> GET RESPONSE
    chunks = 0
    while sw1 == 0x61:
        chunks += 1
        if chunks > 8:
            raise CredentialError("Respuesta demasiado fragmentada")
        say(f"-> GET RESPONSE Le={sw2}")
        data, sw1, sw2 = connection.transmit([0x00, 0xC0, 0x00, 0x00, sw2])
        say(f"<- {len(data)} bytes  SW={sw1:02X}{sw2:02X}")
        buffer += bytes(data)

    if (sw1, sw2) == (0x69, 0x85):
        raise CredentialError(
            "6985: el teléfono respondió pero NO tiene credencial activa. "
            "Abre la app NexoEscolar, inicia sesión y revisa que 'Tarjeta lista' salga en verde"
        )
    if (sw1, sw2) == (0x6A, 0x82):
        raise CredentialError(
            "6A82: el teléfono no tiene el servicio NexoEscolar (AID no encontrado). "
            "Reinstala la app y revisa AndroidManifest.xml + res/xml/apduservice.xml"
        )
    if (sw1, sw2) != (0x90, 0x00):
        raise CredentialError(f"Estado inesperado {sw1:02X}{sw2:02X}")

    say(f"payload: {buffer!r}")
    try:
        payload = json.loads(buffer.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CredentialError("Respuesta no es JSON válido") from exc

    return validate_payload(payload)


def validate_payload(payload: object, now: float | None = None) -> dict:
    """Validación de forma y frescura. La firma y la base de datos las evalúa access_logic."""
    if not isinstance(payload, dict):
        raise CredentialError("Formato inválido")
    uid, ts, sig = payload.get("uid"), payload.get("ts"), payload.get("sig")
    if not (isinstance(uid, str) and uid and isinstance(sig, str) and len(sig) == 64):
        raise CredentialError("Faltan campos uid/sig")
    if not isinstance(ts, int):
        raise CredentialError("Campo ts inválido")
    diff = (now if now is not None else time.time()) - ts
    if abs(diff) > MAX_CLOCK_SKEW_S:
        horas = abs(diff) / 3600
        lado = "ADELANTADO" if diff > 0 else "ATRASADO"
        raise CredentialError(
            f"Código caducado: el reloj de esta PC está {lado} {horas:.1f} h ({abs(diff):.0f} s) "
            "respecto al teléfono. Sincroniza la hora de la PC (Configuración > Hora e idioma > "
            "Sincronizar ahora) y verifica la zona horaria"
        )
    return payload


# --------------------------------------------------------------------------- Lector

def pick_reader(index: int):
    from smartcard.System import readers

    available = readers()
    if not available:
        sys.exit("No se detectó ningún lector PC/SC. ¿Está conectado el ACR122U?")
    if index >= len(available):
        sys.exit(f"--reader {index} fuera de rango (hay {len(available)}). Usa --list.")
    return available[index]


def try_connect(reader, on_error=None, on_atr=None):
    """Devuelve una conexión abierta o None si no hay tarjeta/teléfono.

    Prueba el protocolo por defecto y luego T=1 y T=0 (algunos teléfonos solo conectan con uno).
    `on_error(exc)` se llama cuando el lector DETECTA algo pero la conexión falla
    (teléfono mal acomodado, pantalla apagada, NFC del teléfono en modo lector...).
    """
    from smartcard.CardConnection import CardConnection
    from smartcard.Exceptions import CardConnectionException, NoCardException

    last_exc = None
    for protocol in (None, CardConnection.T1_protocol, CardConnection.T0_protocol):
        connection = reader.createConnection()
        try:
            if protocol is None:
                connection.connect()
            else:
                connection.connect(protocol)
            if on_atr is not None:
                try:
                    on_atr(bytes(connection.getATR()))
                except Exception:  # noqa: BLE001
                    pass
            return connection
        except NoCardException:
            return None
        except CardConnectionException as exc:
            last_exc = exc
    if on_error is not None and last_exc is not None:
        on_error(last_exc)
    return None


def wait_until_removed(reader) -> None:
    while True:
        connection = try_connect(reader)
        if connection is None:
            return
        try:
            connection.disconnect()
        except Exception:  # noqa: BLE001 - desconexión best-effort
            pass
        time.sleep(0.3)


def stamp() -> str:
    return time.strftime("%H:%M:%S")


def build_processor(args):
    """Crea el procesador (conexión a PostgreSQL). Importa aquí para no exigir las
    dependencias a quien solo usa --list / --dry-run."""
    from access_logic import AccessProcessor
    from db import SchemaError, load_tables, make_engine

    engine = make_engine()
    try:
        tables = load_tables(engine)
    except SchemaError as exc:
        sys.exit(f"Error en la base de datos: {exc}")
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"No se pudo conectar a la base de datos: {type(exc).__name__}: {exc}")
    print(f"Base de datos: {engine.url.render_as_string(hide_password=True)}")
    return AccessProcessor(engine, tables)


def check_db() -> None:
    """--check-db: comprueba conexión, columnas y cuántas credenciales hay."""
    from sqlalchemy import func, select

    from db import SchemaError, load_tables, make_engine

    engine = make_engine()
    print(f"Conectando a: {engine.url.render_as_string(hide_password=True)}")
    try:
        tables = load_tables(engine)
    except SchemaError as exc:
        sys.exit(f"FALLO: {exc}")
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"FALLO de conexión: {type(exc).__name__}: {exc}")
    with engine.connect() as conn:
        for name, table in (
            ("credenciales_digitales", tables.credenciales),
            ("alumnos", tables.alumnos),
            ("asistencias", tables.asistencias),
        ):
            n = conn.execute(select(func.count()).select_from(table)).scalar_one()
            print(f"  OK  {name}: {n} fila(s)")
        tipo = tables.asistencias.c.asistencia_tipo.type
        print(f"  asistencia_tipo es {type(tipo).__name__}" + (f" {list(tipo.enums)}" if getattr(tipo, "enums", None) else ""))
    print("Base de datos lista para el sensor.")


def run(args: argparse.Namespace) -> None:
    from smartcard.Exceptions import CardConnectionException

    processor = None if args.dry_run else build_processor(args)
    reader = pick_reader(args.reader)
    print(f"Lector: {reader}  |  Punto: {args.point}  |  {'DRY-RUN' if args.dry_run else 'REGISTRANDO'}")
    print("Esperando teléfonos... (Ctrl+C para salir)")

    last_sig = None
    last_warn = 0.0
    debug = (lambda m: print(f"[{stamp()}]   {m}")) if args.debug else None
    on_atr = (lambda atr: debug(f"ATR {_hex(atr)}")) if debug else None
    if debug:
        debug("Modo --debug: se imprimen ATR y cada APDU")

    def warn_connect(exc: Exception) -> None:
        nonlocal last_warn
        if time.time() - last_warn >= 3:  # no inundar la consola
            last_warn = time.time()
            print(
                f"[{stamp()}] El lector detectó algo pero no pudo conectar ({exc}). "
                "Acomoda el teléfono, con la pantalla encendida y SIN estar en modo lectura de etiquetas."
            )

    try:
        while True:
            connection = try_connect(reader, on_error=warn_connect, on_atr=on_atr)
            if connection is None:
                time.sleep(POLL_S)
                continue

            try:
                payload = read_credential(connection, log=debug)
                if payload["sig"] == last_sig:
                    pass  # mismo código ya procesado (el teléfono sigue pegado)
                elif processor is None:
                    print("PAYLOAD:", json.dumps(payload, ensure_ascii=False))
                    last_sig = payload["sig"]
                else:
                    last_sig = payload["sig"]
                    decision = processor.process(payload, args.point)
                    if decision.accepted:
                        print(
                            f"[{stamp()}] {decision.tipo.upper():7} {decision.nombre} "
                            f"({decision.matricula}) | hora registrada: {decision.hora:%Y-%m-%d %H:%M:%S}"
                        )
                    else:
                        who = f" - {decision.nombre} ({decision.matricula})" if decision.nombre else ""
                        print(f"[{stamp()}] RECHAZADO [{decision.outcome.value}] {decision.message}{who}")
            except CredentialError as exc:
                print(f"[{stamp()}] Lectura inválida: {exc}")
            except CardConnectionException as exc:
                print(f"[{stamp()}] Se perdió la conexión con el teléfono: {exc}")
                try:
                    connection.disconnect()
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(0.4)
                continue  # reintenta solo, sin pedir que alejes el teléfono
            except Exception as exc:  # noqa: BLE001 - la puerta no debe caerse por un error de BD
                print(f"[{stamp()}] ERROR: {type(exc).__name__}: {exc}")
            finally:
                try:
                    connection.disconnect()
                except Exception:  # noqa: BLE001
                    pass

            time.sleep(COOLDOWN_S)
            wait_until_removed(reader)
    finally:
        if processor is not None:
            processor.close()


def test_telegram(chat_id: str) -> None:
    from telegram_notifier import TelegramNotifier

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        sys.exit("Define TELEGRAM_BOT_TOKEN (variable de entorno o .env).")
    ok, detail = TelegramNotifier(token).send(chat_id, "✅ Prueba de NexoEscolar: el bot funciona.")
    print("Enviado." if ok else f"Falló: {detail}")


def main() -> None:
    load_env_file(Path(__file__).with_name(".env"))

    parser = argparse.ArgumentParser(description="Sensor de puerta NexoEscolar (PC/SC + PostgreSQL)")
    parser.add_argument("--list", action="store_true", help="lista los lectores PC/SC y sale")
    parser.add_argument("--reader", type=int, default=0, help="índice del lector (default 0)")
    parser.add_argument("--point", default="PUERTA_PRINCIPAL", help="identificador del punto de acceso")
    parser.add_argument("--dry-run", action="store_true", help="no usa la BD; imprime lo recibido")
    parser.add_argument("--debug", action="store_true", help="imprime ATR y cada APDU (diagnóstico)")
    parser.add_argument("--check-db", action="store_true", help="prueba la conexión y las tablas y sale")
    parser.add_argument("--test-telegram", metavar="CHAT_ID", help="envía un mensaje de prueba y sale")
    args = parser.parse_args()

    if args.test_telegram:
        test_telegram(args.test_telegram)
        return

    if args.check_db:
        check_db()
        return

    if args.list:
        from smartcard.System import readers

        for i, r in enumerate(readers()):
            print(f"{i}: {r}")
        return

    try:
        run(args)
    except KeyboardInterrupt:
        print("\nSaliendo.")


if __name__ == "__main__":
    main()
