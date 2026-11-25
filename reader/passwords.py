"""
Contraseñas: crea hashes nuevos y VERIFICA los formatos más comunes.

  hash_password(p)        -> "nexo-pbkdf2$240000$<sal hex>$<hash hex>"   (formato propio, solo stdlib)
  verify_password(p, h)   -> True/False. Reconoce:
        nexo-pbkdf2$...           (este módulo)
        $2a$ / $2b$ / $2y$        bcrypt           (necesita:  pip install bcrypt)
        $argon2...                argon2           (necesita:  pip install argon2-cffi)
        pbkdf2:sha256:N$sal$hex   Werkzeug / Flask
        scrypt:N:r:p$sal$hex      Werkzeug / Flask
        pbkdf2_sha256$N$sal$b64   Django
        64 caracteres hex         SHA-256 simple (sin sal; poco seguro, solo por compatibilidad)

Si el formato no se reconoce o falta una librería, lanza UnsupportedHash con el motivo.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets

ITERATIONS = 240_000
_NEXO = "nexo-pbkdf2"
_HEX64 = re.compile(r"[0-9a-fA-F]{64}")


class UnsupportedHash(Exception):
    """El hash guardado tiene un formato que no se puede verificar."""


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"{_NEXO}${ITERATIONS}${salt.hex()}${digest.hex()}"


def hash_kind(stored: str) -> str:
    """Nombre corto del formato (para registros del servidor; nunca muestra el hash)."""
    if stored.startswith(_NEXO + "$"):
        return "nexo-pbkdf2"
    if stored[:4] in ("$2a$", "$2b$", "$2y$"):
        return "bcrypt"
    if stored.startswith("$argon2"):
        return "argon2"
    if stored.startswith("pbkdf2:"):
        return "werkzeug-pbkdf2"
    if stored.startswith("scrypt:"):
        return "werkzeug-scrypt"
    if stored.startswith("pbkdf2_sha256$"):
        return "django-pbkdf2"
    if _HEX64.fullmatch(stored):
        return "sha256-simple"
    return "desconocido"


def verify_password(password: str, stored: str) -> bool:
    kind = hash_kind(stored)
    pw = password.encode("utf-8")
    try:
        if kind == "nexo-pbkdf2":
            _, iterations, salt_hex, digest_hex = stored.split("$")
            digest = hashlib.pbkdf2_hmac("sha256", pw, bytes.fromhex(salt_hex), int(iterations))
            return hmac.compare_digest(digest.hex(), digest_hex)

        if kind == "bcrypt":
            try:
                import bcrypt
            except ImportError as exc:
                raise UnsupportedHash("hash bcrypt: instala la librería con  pip install bcrypt") from exc
            return bcrypt.checkpw(pw[:72], stored.encode("utf-8"))

        if kind == "argon2":
            try:
                from argon2 import PasswordHasher
                from argon2.exceptions import InvalidHashError, VerificationError
            except ImportError as exc:
                raise UnsupportedHash("hash argon2: instala  pip install argon2-cffi") from exc
            try:
                return PasswordHasher().verify(stored, password)
            except (VerificationError, InvalidHashError):
                return False

        if kind == "werkzeug-pbkdf2":
            method, salt, digest_hex = stored.split("$")
            parts = method.split(":")           # pbkdf2:sha256[:iteraciones]
            algo = parts[1]
            iterations = int(parts[2]) if len(parts) > 2 else 600_000
            digest = hashlib.pbkdf2_hmac(algo, pw, salt.encode("utf-8"), iterations)
            return hmac.compare_digest(digest.hex(), digest_hex)

        if kind == "werkzeug-scrypt":
            method, salt, digest_hex = stored.split("$")
            _, n, r, p = method.split(":")
            n, r, p = int(n), int(r), int(p)
            digest = hashlib.scrypt(
                pw, salt=salt.encode("utf-8"), n=n, r=r, p=p, maxmem=132 * n * r * p,
                dklen=len(digest_hex) // 2,
            )
            return hmac.compare_digest(digest.hex(), digest_hex)

        if kind == "django-pbkdf2":
            _, iterations, salt, b64 = stored.split("$")
            digest = hashlib.pbkdf2_hmac("sha256", pw, salt.encode("utf-8"), int(iterations))
            return hmac.compare_digest(base64.b64encode(digest).decode("ascii"), b64)

        if kind == "sha256-simple":
            return hmac.compare_digest(hashlib.sha256(pw).hexdigest(), stored.lower())
    except UnsupportedHash:
        raise
    except (ValueError, TypeError, IndexError):
        return False   # hash mal formado: no inicia sesión

    raise UnsupportedHash("formato de hash desconocido")


# Para gastar un tiempo parecido cuando la matrícula no existe (no revela qué matrículas hay).
DUMMY_HASH = hash_password(secrets.token_hex(8))
