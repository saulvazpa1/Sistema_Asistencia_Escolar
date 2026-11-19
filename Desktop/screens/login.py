
import flet as ft
import requests
from screens.admin import admin_view


API_URL = "http://127.0.0.1:5001/api/login"


def login_view(page: ft.Page):

    usuario = ft.TextField(
        label="Usuario",
        prefix_icon=ft.Icons.PERSON,
        border=ft.OutlineInputBorder(
            border_radius=10
        ),
        width=320
    )

    password = ft.TextField(
        label="Contraseña",
        prefix_icon=ft.Icons.LOCK,
        password=True,
        can_reveal_password=True,
        border=ft.OutlineInputBorder(
            border_radius=10
        ),
        width=320
    )

    mensaje = ft.Text(
        "",
        color="red",
        size=13
    )

    def iniciar_sesion(e):

        login = usuario.value.strip()
        clave = password.value

        if not login or not clave:
            mensaje.value = "Ingresa usuario y contraseña."
            mensaje.color = "red"
            page.update()
            return

        boton_login.disabled = True
        boton_login.content = "Validando..."
        mensaje.value = ""
        page.update()

        try:
            respuesta = requests.post(
                API_URL,
                json={
                    "usuario": login,
                    "password": clave
                },
                timeout=10
            )

            datos = respuesta.json()

            if respuesta.status_code == 200 and datos.get("exito"):

                token = datos["token"]

                # Guardamos el token para las consultas a la API.
                page.session.store.set("token", token)

                nombre = datos["usuario"]["nombre"]

                # Abrimos el panel de administración.
                page.clean()
                page.add(admin_view(page, nombre))
                page.update()
                return

            else:
                mensaje.value = datos.get(
                    "mensaje",
                    "Usuario o contraseña incorrectos."
                )
                mensaje.color = "red"

        except requests.exceptions.ConnectionError:
            mensaje.value = "No se pudo conectar con el servidor Flask."
            mensaje.color = "red"

        except requests.exceptions.Timeout:
            mensaje.value = "El servidor tardó demasiado en responder."
            mensaje.color = "red"

        except Exception as error:
            print("ERROR LOGIN:", repr(error))
            mensaje.value = "Ocurrió un error al iniciar sesión."
            mensaje.color = "red"

        finally:
            boton_login.disabled = False
            boton_login.content = "Iniciar sesión"
            page.update()

    boton_login = ft.Button(
        content="Iniciar sesión",
        width=320,
        height=45,
        on_click=iniciar_sesion,
        style=ft.ButtonStyle(
            bgcolor="#0B3A70",
            color="white"
        )
    )

    return ft.Container(
        expand=True,
        alignment=ft.Alignment.CENTER,
        bgcolor="#F3F6FA",
        content=ft.Column(
            [
                ft.Icon(
                    ft.Icons.SCHOOL,
                    size=65,
                    color="#0B3A70"
                ),

                ft.Text(
                    "CONTROL ESCOLAR",
                    size=25,
                    weight=ft.FontWeight.BOLD,
                    color="#082D59"
                ),

                ft.Text(
                    "Sistema de asistencia escolar",
                    color="#65758A"
                ),

                ft.Container(
                    width=400,
                    padding=30,
                    bgcolor="white",
                    border_radius=15,
                    content=ft.Column(
                        [
                            ft.Text(
                                "Iniciar sesión",
                                size=23,
                                weight=ft.FontWeight.BOLD
                            ),
                            usuario,
                            password,
                            boton_login,
                            mensaje
                        ],
                        spacing=20
                    )
                ),

                ft.Text(
                    "Acceso exclusivo para personal autorizado",
                    size=12,
                    color="#738196"
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12
        )
    )
