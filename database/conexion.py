import psycopg
from config import DB_CONFIG


class ConexionDB:

    @staticmethod
    def conectar():
        """
        Establece una conexión con PostgreSQL.
        """

        try:
            conexion = psycopg.connect(**DB_CONFIG)
            return conexion

        except psycopg.Error as error:
            print(f"Error al conectar con PostgreSQL: {error}")
            raise