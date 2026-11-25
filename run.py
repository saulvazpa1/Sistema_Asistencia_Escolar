
import subprocess
import sys
import time

procesos = []

def iniciar(nombre, archivo):
    proceso = subprocess.Popen([sys.executable, archivo])
    procesos.append((nombre, proceso))
    print(f"{nombre} iniciado.")

if __name__ == "__main__":
    print("Iniciando sistema escolar...")

    try:
        iniciar("Servidor Flask", "app.py")
        time.sleep(2)

        iniciar("Bot de Telegram", "bot.py")
        time.sleep(2)

        iniciar("Panel de escritorio", "escritorio.py")

        print("Sistema completo funcionando.")

        while True:
            for nombre, proceso in procesos:
                if proceso.poll() is not None:
                    raise RuntimeError(f"{nombre} se ha detenido.")

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nCerrando sistema...")

    except RuntimeError as error:
        print(error)

    finally:
        for nombre, proceso in reversed(procesos):
            if proceso.poll() is None:
                proceso.terminate()

        for nombre, proceso in reversed(procesos):
            proceso.wait()

        print("Sistema detenido.")
