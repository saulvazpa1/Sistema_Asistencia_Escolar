
from werkzeug.security import generate_password_hash
from database.conexion import ConexionDB

def crear_admin():
    print("=== REGISTRO DE ADMINISTRADOR ===")

    login = input("Usuario: ").strip()
    nombre = input("Nombre completo: ").strip()
    correo = input("Correo: ").strip()
    password = input("Contraseña: ")

    if not login or not nombre or not correo or not password:
        print("Todos los campos son obligatorios.")
        return

    password_hash = generate_password_hash(password)

    try:
        with ConexionDB.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO usuarios_administradores (
                        usuario_login,
                        usuario_nombre,
                        usuario_password_hash,
                        usr_correo,
                        usuario_rol
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING usuario_id
                """, (
                    login,
                    nombre,
                    password_hash,
                    correo,
                    "administrador"
                ))

                usuario_id = cursor.fetchone()[0]

        print(f"\nAdministrador creado correctamente.")
        print(f"ID: {usuario_id}")
        print(f"Usuario: {login}")

    except Exception as error:
        print("Error al crear administrador:", error)


if __name__ == "__main__":
    crear_admin()
