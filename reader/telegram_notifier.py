"""Envío de mensajes con la API del Bot de Telegram (solo biblioteca estándar)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Callable

API_URL = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier:
    """
    send(chat_id, text) -> (ok, detalle)

    Reintenta SOLO errores de red / 5xx / 429. Los errores definitivos (chat no encontrado,
    bot bloqueado por el tutor, token inválido) no se reintentan.
    El token del bot nunca se imprime ni se incluye en los mensajes de error.
    """

    def __init__(
        self,
        bot_token: str,
        timeout: float = 5.0,
        retries: int = 2,
        opener: Callable = urllib.request.urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not bot_token:
            raise ValueError("Falta TELEGRAM_BOT_TOKEN")
        self._url = API_URL.format(token=bot_token)
        self._timeout = timeout
        self._retries = retries
        self._opener = opener
        self._sleep = sleep

    def send(self, chat_id: str, text: str) -> tuple[bool, str]:
        body = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
        last_detail = "sin intentos"

        for attempt in range(self._retries + 1):
            request = urllib.request.Request(
                self._url,
                data=body,
                method="POST",
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            try:
                with self._opener(request, timeout=self._timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                if data.get("ok"):
                    return True, "enviado"
                return False, f"Telegram rechazó el mensaje: {data.get('description', '?')}"
            except urllib.error.HTTPError as exc:
                description = _error_description(exc)
                if exc.code == 429 or exc.code >= 500:
                    last_detail = f"HTTP {exc.code}: {description}"
                else:
                    return False, f"HTTP {exc.code}: {description}"  # definitivo
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_detail = f"sin conexión con Telegram ({type(exc).__name__})"

            if attempt < self._retries:
                self._sleep(1.5 * (attempt + 1))

        return False, last_detail


def _error_description(exc: urllib.error.HTTPError) -> str:
    try:
        return str(json.loads(exc.read().decode("utf-8")).get("description", exc.reason))
    except Exception:  # noqa: BLE001 - cuerpo no JSON
        return str(exc.reason)
