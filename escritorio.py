import socket
import subprocess
import sys
import threading
import time

import webview
from app import app

PUERTO = 5001


def iniciar_flask():
    app.run(host="127.0.0.1", port=PUERTO, debug=False, use_reloader=False)


def esperar_servidor():
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", PUERTO), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)


if __name__ == "__main__":
    bot = subprocess.Popen([sys.executable, "bot.py"])  # el bot de Telegram sigue corriendo

    threading.Thread(target=iniciar_flask, daemon=True).start()
    esperar_servidor()

    webview.create_window(
        "Panel Administrador",
        f"http://127.0.0.1:{PUERTO}/admin",
        width=1200,
        height=800,
    )
    webview.start()  # se queda aquí hasta que cierres la ventana

    bot.terminate()  # al cerrar la ventana, también se apaga el bot