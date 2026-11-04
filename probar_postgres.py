
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

try:
    with psycopg.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
    ) as conexion:
        print("¡Conexión exitosa con PostgreSQL!")
        print("Base de datos:", conexion.info.dbname)

except Exception as error:
    print("No se pudo conectar:")
    print(error)
