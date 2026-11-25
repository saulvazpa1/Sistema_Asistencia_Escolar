"""
Lógica de acceso del sensor de la puerta.

Recibe lo que el teléfono entregó por NFC/HCE  {"v":1,"uid","ts","sig"}  y decide:

  1. Formato válido y código reciente (ts dentro de ±90 s).
  2. No repetido (anti-replay en memoria).
  3. El `uid` EXISTE en credenciales_digitales.credencial_uid.
  4. La credencial está activa y no ha expirado.
  5. La firma HMAC-SHA256 es válida. La llave es `credencial_token_hash` (el teléfono firma
     con SHA-256(token), que es justo lo que guarda la base de datos).
  6. El alumno no está dado de baja (baja_fecha IS NULL y alumno_estatus activo).
  7. ENTRADA/SALIDA: se ALTERNA según su último registro (el primer toque del día es ENTRADA).
  8. INSERTA la fila en `asistencias` (con la hora) y actualiza credencial_ultimo_uso.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Optional

from sqlalchemy import Enum as SAEnum
from sqlalchemy import desc, insert, select, update
from sqlalchemy.engine import Engine

from db import Tables, load_tables

MAX_CLOCK_SKEW_S = 90      # antigüedad máxima aceptada de "ts"
DEBOUNCE_S = 10            # un segundo toque en <10 s se ignora (evita invertir entrada/salida)
REPLAY_TTL_S = 300         # cuánto se recuerda un código ya usado

import os

# Valor de asistencias.asistencia_metodo. Cámbialo en .env con ASISTENCIA_METODO=... si tu
# restricción CHECK (asistencias_asistencia_metodo_check) acepta otro texto.
METODO = os.environ.get("ASISTENCIA_METODO", "nfc")

# alumnos.alumno_estatus: se rechaza si dice una de estas cosas (si es NULL o cualquier otra, pasa).
ESTATUS_INACTIVOS = {
    "baja", "inactivo", "inactiva", "suspendido", "suspendida", "bloqueado", "bloqueada",
    "egresado", "egresada", "false", "0", "no",
}

_HEX64 = re.compile(r"[0-9a-fA-F]{64}")


class Outcome(str, Enum):
    ACCEPTED = "accepted"
    MALFORMED = "malformed"
    STALE = "stale"
    REPLAY = "replay"
    UNKNOWN = "unknown"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    NO_TOKEN = "no_token"
    BAD_SIGNATURE = "bad_signature"
    BAJA = "baja"
    DUPLICATE = "duplicate"


@dataclass(frozen=True)
class Decision:
    outcome: Outcome
    message: str
    tipo: Optional[str] = None          # 'entrada' | 'salida' (solo si ACCEPTED)
    nombre: Optional[str] = None
    matricula: Optional[str] = None
    alumno_id: Optional[int] = None
    hora: Optional[datetime] = None     # hora que se insertó en asistencias

    @property
    def accepted(self) -> bool:
        return self.outcome is Outcome.ACCEPTED


def expected_signature(key: str, uid: str, ts: int) -> str:
    return hmac.new(key.encode("utf-8"), f"{uid}.{ts}".encode("utf-8"), hashlib.sha256).hexdigest()


def signing_key_from_token(token: str) -> str:
    """Llave que usa el teléfono: SHA-256(token) en hex minúsculas (= credencial_token_hash)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def estatus_activo(valor: object) -> bool:
    if valor is None:
        return True
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower() not in ESTATUS_INACTIVOS


class AccessProcessor:
    def __init__(
        self,
        engine: Engine,
        tables: Optional[Tables] = None,
        *,
        now_fn: Callable[[], datetime] = datetime.now,
        time_fn: Callable[[], float] = time.time,
        on_accepted: Optional[Callable[[Decision], None]] = None,
    ) -> None:
        self._engine = engine
        self._t = tables or load_tables(engine)
        self._now = now_fn
        self._time = time_fn
        self._on_accepted = on_accepted   # gancho para el aviso de Telegram (siguiente paso)
        self._seen: dict[tuple[str, str], float] = {}

    # ------------------------------------------------------------------ API pública

    def process(self, payload: dict, point_id: str) -> Decision:
        uid, ts, sig = payload.get("uid"), payload.get("ts"), payload.get("sig")
        if not (
            isinstance(uid, str) and 0 < len(uid) <= 128
            and isinstance(ts, int) and not isinstance(ts, bool)
            and isinstance(sig, str) and _HEX64.fullmatch(sig)
        ):
            return Decision(Outcome.MALFORMED, "Código con formato inválido")

        now_ts = self._time()
        if abs(now_ts - ts) > MAX_CLOCK_SKEW_S:
            return Decision(Outcome.STALE, "Código caducado (revisa la hora del teléfono y de la PC)")

        self._purge_seen(now_ts)
        if (uid, sig.lower()) in self._seen:
            return Decision(Outcome.REPLAY, "Código ya utilizado")

        c, a, s = self._t.credenciales, self._t.alumnos, self._t.asistencias
        now = self._now().replace(microsecond=0)

        with self._engine.begin() as conn:
            row = conn.execute(
                select(
                    c.c.credencial_id,
                    c.c.alumno_id,
                    c.c.credencial_token_hash,
                    c.c.credencial_activa,
                    c.c.credencial_fecha_expiracion,
                    a.c.alumno_matricula,
                    a.c.alumno_nombre,
                    a.c.alumno_estatus,
                    a.c.baja_fecha,
                )
                .select_from(c.join(a, a.c.alumno_id == c.c.alumno_id))
                .where(c.c.credencial_uid == uid)
            ).mappings().first()

            if row is None:
                return Decision(Outcome.UNKNOWN, f"ID de credencial no registrado ({uid})")

            who = dict(
                nombre=row["alumno_nombre"],
                matricula=row["alumno_matricula"],
                alumno_id=row["alumno_id"],
            )
            if not row["credencial_activa"]:
                return Decision(Outcome.INACTIVE, "Credencial inactiva", **who)
            exp = row["credencial_fecha_expiracion"]
            if exp is not None and _naive(exp) < now:
                return Decision(Outcome.EXPIRED, f"Credencial expirada ({exp:%Y-%m-%d})", **who)
            key = row["credencial_token_hash"]
            if not key:
                return Decision(Outcome.NO_TOKEN, "La credencial no tiene teléfono vinculado", **who)
            if not hmac.compare_digest(expected_signature(key, uid, ts), sig.lower()):
                return Decision(
                    Outcome.BAD_SIGNATURE,
                    "Firma inválida (¿otro teléfono o llave distinta?)",
                    **who,
                )

            self._seen[(uid, sig.lower())] = now_ts  # firma válida: este código ya no se acepta otra vez

            if row["baja_fecha"] is not None:
                return Decision(Outcome.BAJA, "Alumno dado de baja", **who)
            if not estatus_activo(row["alumno_estatus"]):
                return Decision(
                    Outcome.BAJA, f"Alumno no activo (estatus: {row['alumno_estatus']})", **who
                )

            last = conn.execute(
                select(s.c.asistencia_tipo, s.c.asistencia_fechahora)
                .where(s.c.alumno_id == row["alumno_id"])
                .order_by(desc(s.c.asistencia_fechahora), desc(s.c.asistencia_id))
                .limit(1)
            ).mappings().first()

            last_tipo = _tipo_text(last["asistencia_tipo"]) if last else None
            last_time = _naive(last["asistencia_fechahora"]) if last else None

            if last_time is not None and 0 <= (now - last_time).total_seconds() < DEBOUNCE_S:
                return Decision(Outcome.DUPLICATE, "Toque repetido, ignorado", tipo=last_tipo, **who)

            tipo = _next_tipo(last_tipo, last_time, now)
            conn.execute(
                insert(s).values(
                    alumno_id=row["alumno_id"],
                    asistencia_tipo=_tipo_value(s.c.asistencia_tipo, tipo),
                    asistencia_fechahora=now,
                    asistencia_metodo=METODO,
                    asistencia_dispositivo=point_id[:100],
                    asistencia_observaciones=None,
                    usuario_id=None,
                )
            )
            conn.execute(
                update(c)
                .where(c.c.credencial_id == row["credencial_id"])
                .values(credencial_ultimo_uso=now)
            )

        decision = Decision(
            Outcome.ACCEPTED, f"{tipo.capitalize()} registrada", tipo=tipo, hora=now, **who
        )
        if self._on_accepted is not None:
            try:
                self._on_accepted(decision)
            except Exception:  # noqa: BLE001 - un fallo del aviso no debe frenar la puerta
                pass
        return decision

    def close(self) -> None:
        """Sin recursos propios todavía (el aviso de Telegram los usará en el siguiente paso)."""

    # ------------------------------------------------------------------ internos

    def _purge_seen(self, now_ts: float) -> None:
        expired = [k for k, t in self._seen.items() if now_ts - t > REPLAY_TTL_S]
        for key in expired:
            del self._seen[key]


def _naive(value: datetime) -> datetime:
    """Compara siempre en hora local sin zona (timestamp o timestamptz)."""
    if value.tzinfo is not None:
        return value.astimezone().replace(tzinfo=None)
    return value


def _tipo_text(value: object) -> str:
    return str(getattr(value, "value", value)).strip().lower()


def _tipo_value(column, tipo: str):
    """Si la columna es un ENUM de PostgreSQL usa el valor con SU mayúscula/minúscula."""
    if isinstance(column.type, SAEnum) and column.type.enums:
        for option in column.type.enums:
            if option.lower() == tipo:
                return option
        raise ValueError(
            f"asistencia_tipo no acepta {tipo!r}; valores permitidos: {column.type.enums}"
        )
    return tipo


def _next_tipo(last_tipo: Optional[str], last_time: Optional[datetime], now: datetime) -> str:
    """Alterna entrada/salida. El primer toque de cada día es entrada."""
    if last_tipo is None or last_time is None or last_time.date() != now.date():
        return "entrada"
    return "salida" if last_tipo == "entrada" else "entrada"