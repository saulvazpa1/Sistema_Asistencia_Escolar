import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

usuario = os.getenv("ADMIN_USER")

if not usuario:
    print("No se encontró ADMIN_USER en el archivo .env")
    exit()

nueva_password = input("Escribe tu nueva contraseña: ")

if len(nueva_password) < 8:
    print("La contraseña debe tener al menos 8 caracteres.")
    exit()

nuevo_hash = generate_password_hash(nueva_password)

ruta_env = ".env"

with open(ruta_env, "r", encoding="utf-8") as archivo:
    lineas = archivo.readlines()

with open(ruta_env, "w", encoding="utf-8") as archivo:
    encontrada = False

    for linea in lineas:
        if linea.strip().startswith("ADMIN_PASS_HASH="):
            archivo.write(f"ADMIN_PASS_HASH={nuevo_hash}\n")
            encontrada = True
        else:
            archivo.write(linea)

    if not encontrada:
        archivo.write(f"\nADMIN_PASS_HASH={nuevo_hash}\n")

print("\nContraseña del login web actualizada.")
print("Usuario:", usuario)