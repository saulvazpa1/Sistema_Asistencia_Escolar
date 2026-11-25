"""Pruebas del sensor (sin hardware): usa SQLite con las MISMAS columnas que tus tablas de PostgreSQL."""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta

from sqlalchemy import Column, Enum as SAEnum, MetaData, Table, create_engine, select, text, update

import nexo_reader
from access_logic import (
    DEBOUNCE_S, AccessProcessor, Outcome, _tipo_value, estatus_activo, expected_signature,
    signing_key_from_token,
)
from db import SchemaError, load_tables
from telegram_notifier import TelegramNotifier

UID = "uid-20258TTH89"
TOKEN = "mock-token-20258TTH89"            # lo que tiene la app
KEY = signing_key_from_token(TOKEN)         # lo que guarda la BD (credencial_token_hash) y firma el teléfono

DDL = [
    """CREATE TABLE credenciales_digitales (
        credencial_id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER NOT NULL,
        credencial_uid VARCHAR(128) UNIQUE NOT NULL, credencial_token_hash VARCHAR(128),
        credencial_fecha_emision TIMESTAMP, credencial_fecha_expiracion TIMESTAMP,
        credencial_activa BOOLEAN NOT NULL DEFAULT 1, credencial_ultimo_uso TIMESTAMP)""",
    """CREATE TABLE alumnos (
        alumno_id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_matricula VARCHAR(40) NOT NULL,
        alumno_nombre VARCHAR(150) NOT NULL, alumno_estatus VARCHAR(20), baja_motivo VARCHAR(255),
        baja_fecha TIMESTAMP)""",
    """CREATE TABLE asistencias (
        asistencia_id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER NOT NULL,
        asistencia_tipo VARCHAR(10) NOT NULL, asistencia_fechahora TIMESTAMP NOT NULL,
        asistencia_metodo VARCHAR(20), asistencia_dispositivo VARCHAR(100),
        asistencia_observaciones TEXT, usuario_id INTEGER)""",
]


class Clock:
    def __init__(self):
        self.now = datetime(2026, 11, 24, 7, 50, 0)

    def advance(self, **kw):
        self.now += timedelta(**kw)

    def datetime(self):
        return self.now

    def epoch(self):
        return self.now.timestamp()


def payload(clock, uid=UID, key=KEY, ts_offset=0):
    ts = int(clock.epoch()) + ts_offset
    return {"v": 1, "uid": uid, "ts": ts, "sig": expected_signature(key, uid, ts)}


class AccessLogicTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(f"sqlite:///{self.path}")
        with self.engine.begin() as conn:
            for stmt in DDL:
                conn.execute(text(stmt))
            conn.execute(text(
                "INSERT INTO alumnos (alumno_matricula, alumno_nombre, alumno_estatus) "
                "VALUES ('20258TTH89', 'Bot Sanchez Perez', 'activo')"))
        self.clock = Clock()
        self.tables = load_tables(self.engine)          # misma ruta de código que con PostgreSQL
        self.set_cred(credencial_token_hash=KEY)
        self.proc = AccessProcessor(self.engine, self.tables,
                                    now_fn=self.clock.datetime, time_fn=self.clock.epoch)

    def set_cred(self, **values):
        c = self.tables.credenciales
        base = dict(alumno_id=1, credencial_uid=UID, credencial_activa=True,
                    credencial_fecha_expiracion=datetime(2027, 11, 24))
        with self.engine.begin() as conn:
            row = conn.execute(select(c.c.credencial_id)).first()
            if row is None:
                conn.execute(c.insert().values(**{**base, **values}))
            else:
                conn.execute(update(c).values(**values))

    def alumno_update(self, **values):
        with self.engine.begin() as conn:
            conn.execute(update(self.tables.alumnos).values(**values))

    def tearDown(self):
        self.proc.close()
        self.engine.dispose()
        os.remove(self.path)

    def asist(self):
        with self.engine.connect() as conn:
            return conn.execute(select(self.tables.asistencias).order_by(
                self.tables.asistencias.c.asistencia_id)).mappings().all()

    # ---- caso feliz --------------------------------------------------------------------
    def test_alterna_entrada_salida_e_inserta_la_hora(self):
        d1 = self.proc.process(payload(self.clock), "PUERTA")
        self.assertTrue(d1.accepted)
        self.assertEqual(d1.tipo, "entrada")
        self.assertEqual(d1.hora, self.clock.now)

        self.clock.advance(hours=7)
        self.assertEqual(self.proc.process(payload(self.clock), "PUERTA").tipo, "salida")
        self.clock.advance(minutes=30)
        self.assertEqual(self.proc.process(payload(self.clock), "PUERTA").tipo, "entrada")

        rows = self.asist()
        self.assertEqual([r["asistencia_tipo"] for r in rows], ["entrada", "salida", "entrada"])
        self.assertEqual(rows[0]["asistencia_fechahora"], datetime(2026, 11, 24, 7, 50, 0))
        self.assertEqual(rows[0]["alumno_id"], 1)
        self.assertEqual(rows[0]["asistencia_metodo"], "NFC")
        self.assertEqual(rows[0]["asistencia_dispositivo"], "PUERTA")
        self.assertIsNone(rows[0]["usuario_id"])

    def test_actualiza_ultimo_uso(self):
        self.proc.process(payload(self.clock), "P")
        with self.engine.connect() as conn:
            uso = conn.execute(select(self.tables.credenciales.c.credencial_ultimo_uso)).scalar_one()
        self.assertEqual(uso, self.clock.now)

    def test_primer_toque_de_cada_dia_es_entrada(self):
        self.proc.process(payload(self.clock), "P")           # entrada
        self.clock.advance(days=1)                             # olvidó marcar salida ayer
        self.assertEqual(self.proc.process(payload(self.clock), "P").tipo, "entrada")

    # ---- rechazos (ninguno inserta nada) -----------------------------------------------
    def test_uid_inexistente(self):
        d = self.proc.process(payload(self.clock, uid="uid-NO-EXISTE"), "P")
        self.assertEqual(d.outcome, Outcome.UNKNOWN)
        self.assertEqual(self.asist(), [])

    def test_credencial_inactiva_expirada_y_sin_token(self):
        self.set_cred(credencial_activa=False)
        self.assertEqual(self.proc.process(payload(self.clock), "P").outcome, Outcome.INACTIVE)
        self.set_cred(credencial_activa=True, credencial_fecha_expiracion=datetime(2026, 11, 1))
        self.assertEqual(self.proc.process(payload(self.clock, ts_offset=1), "P").outcome, Outcome.EXPIRED)
        self.set_cred(credencial_fecha_expiracion=None, credencial_token_hash=None)
        self.assertEqual(self.proc.process(payload(self.clock, ts_offset=2), "P").outcome, Outcome.NO_TOKEN)
        self.assertEqual(self.asist(), [])

    def test_baja_por_fecha_y_por_estatus(self):
        self.alumno_update(baja_fecha=self.clock.now)
        self.assertEqual(self.proc.process(payload(self.clock), "P").outcome, Outcome.BAJA)
        self.alumno_update(baja_fecha=None, alumno_estatus="Baja")
        self.assertEqual(self.proc.process(payload(self.clock, ts_offset=1), "P").outcome, Outcome.BAJA)
        self.assertEqual(self.asist(), [])
        self.alumno_update(alumno_estatus="Activo")
        self.assertTrue(self.proc.process(payload(self.clock, ts_offset=2), "P").accepted)

    def test_firma_con_el_token_crudo_o_de_otro_telefono_no_pasa(self):
        # El teléfono debe firmar con SHA-256(token); firmar con el token en claro NO es válido.
        self.assertEqual(self.proc.process(payload(self.clock, key=TOKEN), "P").outcome, Outcome.BAD_SIGNATURE)
        # Otro teléfono (la BD ya guarda el hash de otro token)
        self.set_cred(credencial_token_hash=signing_key_from_token("token-del-telefono-nuevo"))
        self.assertEqual(self.proc.process(payload(self.clock, ts_offset=1), "P").outcome, Outcome.BAD_SIGNATURE)
        ok = self.proc.process(payload(self.clock, ts_offset=2, key=signing_key_from_token("token-del-telefono-nuevo")), "P")
        self.assertTrue(ok.accepted)
        self.assertEqual(len(self.asist()), 1)

    def test_codigo_caducado_y_formato(self):
        self.assertEqual(self.proc.process(payload(self.clock, ts_offset=-600), "P").outcome, Outcome.STALE)
        self.assertEqual(self.proc.process({"uid": UID}, "P").outcome, Outcome.MALFORMED)
        self.assertEqual(self.proc.process({"uid": UID, "ts": "x", "sig": "y"}, "P").outcome, Outcome.MALFORMED)

    def test_replay_y_doble_toque(self):
        p = payload(self.clock)
        self.assertTrue(self.proc.process(p, "P").accepted)
        self.assertEqual(self.proc.process(p, "P").outcome, Outcome.REPLAY)      # mismo código
        self.clock.advance(seconds=2)
        self.assertEqual(self.proc.process(payload(self.clock), "P").outcome, Outcome.DUPLICATE)
        self.clock.advance(seconds=DEBOUNCE_S)
        self.assertEqual(self.proc.process(payload(self.clock), "P").tipo, "salida")
        self.assertEqual(len(self.asist()), 2)

    def test_gancho_on_accepted_y_su_fallo_no_frena(self):
        seen = []
        proc = AccessProcessor(self.engine, self.tables, now_fn=self.clock.datetime,
                               time_fn=self.clock.epoch, on_accepted=lambda d: seen.append(d.tipo))
        self.assertTrue(proc.process(payload(self.clock), "P").accepted)
        self.assertEqual(seen, ["entrada"])
        boom = AccessProcessor(self.engine, self.tables, now_fn=self.clock.datetime,
                               time_fn=self.clock.epoch, on_accepted=lambda d: 1 / 0)
        self.clock.advance(seconds=30)
        self.assertTrue(boom.process(payload(self.clock), "P").accepted)

    # ---- utilidades --------------------------------------------------------------------
    def test_enum_de_postgres_usa_su_propia_mayuscula(self):
        t = Table("x", MetaData(), Column("tipo", SAEnum("Entrada", "Salida", name="tipo_asistencia")))
        self.assertEqual(_tipo_value(t.c.tipo, "salida"), "Salida")
        bad = Table("y", MetaData(), Column("tipo", SAEnum("IN", "OUT", name="t2")))
        with self.assertRaises(ValueError):
            _tipo_value(bad.c.tipo, "entrada")
        self.assertEqual(_tipo_value(self.tables.asistencias.c.asistencia_tipo, "entrada"), "entrada")

    def test_estatus_activo(self):
        for v in (None, True, "activo", "Activo", "vigente", "ACTIVA"):
            self.assertTrue(estatus_activo(v), v)
        for v in (False, "baja", "Inactivo", "SUSPENDIDO", "0"):
            self.assertFalse(estatus_activo(v), v)

    def test_la_llave_es_sha256_del_token(self):
        self.assertEqual(len(KEY), 64)
        self.assertNotEqual(KEY, TOKEN)

    def test_tabla_incompleta_da_error_claro(self):
        with self.engine.begin() as conn:
            conn.execute(text("ALTER TABLE alumnos RENAME COLUMN alumno_estatus TO estatus"))
        with self.assertRaises(SchemaError) as ctx:
            load_tables(self.engine)
        self.assertIn("alumno_estatus", str(ctx.exception))


class TelegramNotifierTest(unittest.TestCase):
    class _Resp:
        def __init__(self, body):
            self.body = body

        def read(self):
            return self.body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def test_envio_ok_y_url(self):
        seen = {}

        def opener(req, timeout):
            seen["url"], seen["body"] = req.full_url, json.loads(req.data)
            return self._Resp(b'{"ok": true}')

        ok, _ = TelegramNotifier("123:ABC", opener=opener).send("555", "hola")
        self.assertTrue(ok)
        self.assertEqual(seen["url"], "https://api.telegram.org/bot123:ABC/sendMessage")
        self.assertEqual(seen["body"], {"chat_id": "555", "text": "hola"})

    def test_error_definitivo_no_reintenta_y_no_filtra_token(self):
        import io
        import urllib.error

        calls = []

        def opener(req, timeout):
            calls.append(1)
            raise urllib.error.HTTPError(
                req.full_url, 403, "Forbidden", {}, io.BytesIO(b'{"description": "bot was blocked by the user"}'))

        ok, detail = TelegramNotifier("123:SECRETO", opener=opener, sleep=lambda s: None).send("1", "x")
        self.assertFalse(ok)
        self.assertEqual(len(calls), 1)
        self.assertIn("blocked", detail)
        self.assertNotIn("SECRETO", detail)

    def test_reintenta_errores_de_red(self):
        import urllib.error

        calls = []

        def opener(req, timeout):
            calls.append(1)
            raise urllib.error.URLError("sin red")

        ok, _ = TelegramNotifier("t", opener=opener, retries=2, sleep=lambda s: None).send("1", "x")
        self.assertFalse(ok)
        self.assertEqual(len(calls), 3)


class PhoneProtocolTest(unittest.TestCase):
    """read_credential con un teléfono simulado (SELECT AID + respuesta fragmentada)."""

    def test_lee_payload_fragmentado(self):
        import time

        ts = int(time.time())
        body = json.dumps({"v": 1, "uid": "uid-" + "X" * 40, "ts": ts,
                           "sig": expected_signature("t", "c", ts)}).encode()

        class Phone:
            pending = b""

            def transmit(self, apdu):
                if apdu[:4] == [0, 0xA4, 4, 0]:
                    assert bytes(apdu[5:11]) == nexo_reader.AID
                    self.pending = body
                head, self.pending = self.pending[:60], self.pending[60:]
                return list(head), *((0x90, 0) if not self.pending else (0x61, min(len(self.pending), 255)))

        out = nexo_reader.read_credential(Phone())
        self.assertEqual(out["ts"], ts)


if __name__ == "__main__":
    unittest.main()
