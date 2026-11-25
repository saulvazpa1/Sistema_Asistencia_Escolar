from werkzeug.security import generate_password_hash
from database.conexion import ConexionDB

nueva_password = input("Escribe tu nueva contraseña: ")

password_hash = generate_password_hash(nueva_password)

try:
    with ConexionDB.conectar() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("""
                UPDATE usuarios_administradores
                SET usuario_password_hash = %s
                WHERE usuario_id = %s
            """, (password_hash, 1))

        conexion.commit()

    print("Contraseña de administrador actualizada correctamente.")

except Exception as error:
    print("Error:", error)