import subprocess
import sys
import time

print("Iniciando sistema escolar...")

# Iniciar Flask
app = subprocess.Popen([
    sys.executable,
    "app.py"
])

# Iniciar bot de Telegram
bot = subprocess.Popen([
    sys.executable,
    "bot.py"
])

print("Sistema web iniciado.")
print("Bot de Telegram iniciado.")
print("Ambos servicios están funcionando.")

try:
    while True:
        # Comprobar que ambos procesos sigan activos
        if app.poll() is not None:
            print("El servidor Flask se ha detenido.")
            break

        if bot.poll() is not None:
            print("El bot de Telegram se ha detenido.")
            break

        time.sleep(2)

except KeyboardInterrupt:
    print("\nCerrando el sistema...")

finally:
    app.terminate()
    bot.terminate()

    app.wait()
    bot.wait()

    print("Sistema detenido.")