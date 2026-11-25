
import socket
import threading
import time

import webview
from app import app

PUERTO = 5001


def iniciar_flask():
    app.run(
        host="127.0.0.1",
        port=PUERTO,
        debug=False,
        use_reloader=False
    )


def esperar_servidor():
    for _ in range(50):
        try:
            with socket.create_connection(
                ("127.0.0.1", PUERTO),
                timeout=0.5
            ):
                return True
        except OSError:
            time.sleep(0.2)

    return False


if __name__ == "__main__":
    threading.Thread(
        target=iniciar_flask,
        daemon=True
    ).start()

    if not esperar_servidor():
        print("No se pudo iniciar el servidor Flask.")
        raise SystemExit(1)

    webview.create_window(
        "Panel Administrador",
        f"http://127.0.0.1:{PUERTO}/admin",
        width=1200,
        height=800,
    )

    webview.start()
