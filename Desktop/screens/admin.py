import flet as ft
import requests
import re
from services.validaciones import (
    validar_matricula,
    validar_nombre,
    validar_telefono,
    validar_ine,
    validar_correo,
    validar_curp
)
API_BASE = "http://127.0.0.1:5001/api"


def admin_view(page: ft.Page, nombre="Administrador"):

    token = page.session.store.get("token")

    alumnos = []
    tutores = []
    usuarios = []

    filtro_alumnos = "todos"
    filtro_tutores = "todos"

    mensaje_estado = ft.Text("", size=13, color="#65758A")

    total_alumnos = ft.Text("--", size=28, weight=ft.FontWeight.BOLD, color="#082D59")
    total_tutores = ft.Text("--", size=28, weight=ft.FontWeight.BOLD, color="#082D59")
    alumnos_activos = ft.Text("--", size=28, weight=ft.FontWeight.BOLD, color="#082D59")

    tabla_alumnos = ft.Column(spacing=5)
    tabla_tutores = ft.Column(spacing=5)
    tabla_usuarios = ft.Column(spacing=5)

    buscar_alumnos = ft.TextField(
        hint_text="Buscar por matrícula o nombre...",
        prefix_icon=ft.Icons.SEARCH,
        width=330,
        height=45,
        text_size=13
    )

    buscar_tutores = ft.TextField(
        hint_text="Buscar por nombre o teléfono...",
        prefix_icon=ft.Icons.SEARCH,
        width=330,
        height=45,
        text_size=13
    )

    buscar_usuarios = ft.TextField(
        hint_text="Buscar por matrícula o alumno...",
        prefix_icon=ft.Icons.SEARCH,
        width=330,
        height=45,
        text_size=13
    )

   
    def abrir_dialogo(dialogo):
        page.show_dialog(dialogo)

    def cerrar_dialogo(dialogo=None):
        page.pop_dialog()

    

    def mostrar_mensaje(texto, color="#287A45"):
        mensaje_estado.value = texto
        mensaje_estado.color = color
        page.update()

    def consultar_api(endpoint):
        respuesta = requests.get(
            f"{API_BASE}/{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        respuesta.raise_for_status()
        return respuesta.json()

    def enviar_api(endpoint, metodo="PUT", datos=None):
        respuesta = requests.request(
            metodo,
            f"{API_BASE}/{endpoint}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json=datos,
            timeout=10
        )

        try:
            resultado = respuesta.json()
        except ValueError:
            resultado = {}

        if not respuesta.ok or not resultado.get("exito"):
            raise Exception(
                resultado.get("mensaje", "No se pudo completar la operación.")
            )

        return resultado

  

    def crear_tarjeta(titulo, cantidad, descripcion, icono, color):
        return ft.Container(
            width=230,
            padding=20,
            bgcolor="white",
            border_radius=12,
            content=ft.Column(
                [
                    ft.Icon(icono, color=color, size=32),
                    ft.Text(titulo, color="#65758A"),
                    cantidad,
                    ft.Text(descripcion, size=12, color="#8290A0")
                ],
                spacing=8
            )
        )

    def cargar_datos(e=None):
        try:
            datos_alumnos = consultar_api("alumnos")
            datos_tutores = consultar_api("tutores")

            if not datos_alumnos.get("exito"):
                raise Exception("No se pudieron consultar los alumnos.")

            if not datos_tutores.get("exito"):
                raise Exception("No se pudieron consultar los tutores.")

            alumnos.clear()
            tutores.clear()

            alumnos.extend(datos_alumnos.get("alumnos", []))
            tutores.extend(datos_tutores.get("tutores", []))

            total_alumnos.value = str(len(alumnos))
            total_tutores.value = str(len(tutores))

            activos = sum(
                1 for alumno in alumnos
                if str(alumno.get("alumno_estatus", "")).lower() == "activo"
            )

            alumnos_activos.value = str(activos)

            mostrar_alumnos()
            mostrar_tutores()

            mostrar_mensaje("Datos actualizados correctamente.")

        except requests.exceptions.ConnectionError:
            mostrar_mensaje("No se pudo conectar con Flask.", "red")

        except requests.exceptions.Timeout:
            mostrar_mensaje("El servidor tardó demasiado en responder.", "red")

        except requests.exceptions.HTTPError as error:
            mostrar_mensaje(f"Error de API: {error}", "red")

        except Exception as error:
            print("ERROR AL CARGAR DATOS:", repr(error))
            mostrar_mensaje(str(error), "red")

        page.update()


    def crear_boton_filtro(texto, grupo, valor):
        return ft.Button(
            content=texto,
            on_click=lambda e: cambiar_filtro(grupo, valor),
            style=ft.ButtonStyle(
                bgcolor="#DCE8F5",
                color="#082D59"
            )
        )

    def cambiar_filtro(grupo, valor):
        nonlocal filtro_alumnos, filtro_tutores

        if grupo == "alumnos":
            filtro_alumnos = valor
            mostrar_alumnos()
        else:
            filtro_tutores = valor
            mostrar_tutores()

        page.update()

  

    def mostrar_alumnos(e=None):
        texto = (buscar_alumnos.value or "").strip().lower()
        filas = []

        for alumno in alumnos:
            estatus = str(alumno.get("alumno_estatus", "")).lower()

            if filtro_alumnos == "activos" and estatus != "activo":
                continue

            if filtro_alumnos == "bajas" and estatus != "baja":
                continue

            contenido = (
                str(alumno.get("alumno_matricula", "")) + " " +
                str(alumno.get("alumno_nombre", ""))
            ).lower()

            if texto not in contenido:
                continue

            esta_activo = estatus == "activo"

            boton_estado = ft.Button(
                content="Dar de baja" if esta_activo else "Reactivar",
                icon=ft.Icons.BLOCK if esta_activo else ft.Icons.CHECK_CIRCLE,
                on_click=lambda e, a=alumno: confirmar_estado_alumno(a),
                style=ft.ButtonStyle(
                    bgcolor="#FCE8E6" if esta_activo else "#E2F3E8",
                    color="#B3261E" if esta_activo else "#287A45"
                )
            )

            boton_editar = ft.IconButton(
                icon=ft.Icons.EDIT,
                tooltip="Editar alumno",
                icon_color="#2877C7",
                on_click=lambda e, a=alumno: abrir_edicion_alumno(a)
            )

            filas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(alumno.get("alumno_matricula") or ""))),
                        ft.DataCell(ft.Text(str(alumno.get("alumno_nombre") or ""))),
                        ft.DataCell(ft.Text(str(alumno.get("alumno_grado") or ""))),
                        ft.DataCell(ft.Text(str(alumno.get("alumno_grupo") or ""))),
                        ft.DataCell(ft.Text(str(alumno.get("alumno_especialidad") or ""))),
                        ft.DataCell(
                            ft.Text(
                                estatus.capitalize(),
                                color="#287A45" if esta_activo else "#B3261E"
                            )
                        ),
                        ft.DataCell(
                            ft.Row([boton_editar, boton_estado], spacing=2)
                        )
                    ]
                )
            )

        tabla_alumnos.controls = [
            ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Matrícula")),
                    ft.DataColumn(ft.Text("Alumno")),
                    ft.DataColumn(ft.Text("Grado")),
                    ft.DataColumn(ft.Text("Grupo")),
                    ft.DataColumn(ft.Text("Especialidad")),
                    ft.DataColumn(ft.Text("Estatus")),
                    ft.DataColumn(ft.Text("Acciones"))
                ],
                rows=filas,
                heading_row_color="#EAF0F7",
                data_row_min_height=55
            )
        ]

        if not filas:
            tabla_alumnos.controls = [
                ft.Text("No se encontraron alumnos.", color="#65758A")
            ]

   

    def mostrar_tutores(e=None):
        texto = (buscar_tutores.value or "").strip().lower()
        filas = []

        for tutor in tutores:
            activo = tutor.get("tutor_activo", True)

            contenido = (
                str(tutor.get("tutor_nombre", "")) + " " +
                str(tutor.get("tutor_telefono", ""))
            ).lower()

            if texto not in contenido:
                continue

            if filtro_tutores == "activos" and not activo:
                continue

            if filtro_tutores == "inactivos" and activo:
                continue

            tutor_activo = bool(activo)

            boton_estado = ft.Button(
                content="Dar de baja" if tutor_activo else "Reactivar",
                icon=ft.Icons.BLOCK if tutor_activo else ft.Icons.CHECK_CIRCLE,
                on_click=lambda e, t=tutor: confirmar_estado_tutor(t),
                style=ft.ButtonStyle(
                    bgcolor="#FCE8E6" if tutor_activo else "#E2F3E8",
                    color="#B3261E" if tutor_activo else "#287A45"
                )
            )

            boton_editar = ft.IconButton(
                icon=ft.Icons.EDIT,
                tooltip="Editar tutor",
                icon_color="#2877C7",
                on_click=lambda e, t=tutor: abrir_edicion_tutor(t)
            )

            telegram = (
                "Vinculado"
                if tutor.get("tutor_telegram_vinculado")
                else "Pendiente"
            )

            filas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(tutor.get("tutor_nombre") or ""))),
                        ft.DataCell(ft.Text(str(tutor.get("tutor_telefono") or ""))),
                        ft.DataCell(ft.Text(str(tutor.get("tutor_correo") or ""))),
                        ft.DataCell(ft.Text(str(tutor.get("tutor_ine") or ""))),
                        ft.DataCell(ft.Text(telegram)),
                        ft.DataCell(
                            ft.Text(
                                "Activo" if tutor_activo else "Inactivo",
                                color="#287A45" if tutor_activo else "#B3261E"
                            )
                        ),
                        ft.DataCell(
                            ft.Row([boton_editar, boton_estado], spacing=2)
                        )
                    ]
                )
            )

        tabla_tutores.controls = [
            ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Nombre")),
                    ft.DataColumn(ft.Text("Teléfono")),
                    ft.DataColumn(ft.Text("Correo")),
                    ft.DataColumn(ft.Text("INE")),
                    ft.DataColumn(ft.Text("Telegram")),
                    ft.DataColumn(ft.Text("Estado")),
                    ft.DataColumn(ft.Text("Acciones"))
                ],
                rows=filas,
                heading_row_color="#EAF0F7",
                data_row_min_height=55
            )
        ]

        if not filas:
            tabla_tutores.controls = [
                ft.Text("No se encontraron tutores.", color="#65758A")
            ]

  

    def abrir_edicion_alumno(alumno):
        matricula = ft.TextField(
            label="Matrícula",
            value=str(alumno.get("alumno_matricula") or "")
        )
        nombre_alumno = ft.TextField(
            label="Nombre completo",
            value=str(alumno.get("alumno_nombre") or "")
        )
        curp = ft.TextField(
            label="CURP",
            value=str(alumno.get("alumno_curp") or "")
        )
        grado = ft.TextField(
            label="Grado",
            value=str(alumno.get("alumno_grado") or "")
        )
        grupo = ft.TextField(
            label="Grupo",
            value=str(alumno.get("alumno_grupo") or "")
        )
        especialidad = ft.TextField(
            label="Especialidad",
            value=str(alumno.get("alumno_especialidad") or "")
        )
        error = ft.Text("", color="red")

        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar alumno"),
            content=ft.Container(
                width=420,
                content=ft.Column(
                    [
                        matricula,
                        nombre_alumno,
                        curp,
                        grado,
                        grupo,
                        especialidad,
                        error
                    ],
                    tight=True,
                    scroll=ft.ScrollMode.AUTO
                )
            ),
            actions_alignment=ft.MainAxisAlignment.END
        )

     
        def guardar(e):
            # Limpiar y normalizar los datos
            matricula_val = (matricula.value or "").strip()
            nombre_val = " ".join((nombre_alumno.value or "").split())
            curp_val = (curp.value or "").strip().upper()
            grado_val = (grado.value or "").strip()
            grupo_val = (grupo.value or "").strip().upper()
            especialidad_val = (especialidad.value or "").strip()

            # Validar matrícula
            if not validar_matricula(matricula_val):
                error.value = "La matrícula es obligatoria."
                page.update()
                return

            # Validar nombre
            if not validar_nombre(nombre_val):
                error.value = "Ingresa un nombre válido para el alumno."
                page.update()
                return

            # Validar CURP
            if not validar_curp(curp_val):
                error.value = "La CURP debe tener exactamente 18 caracteres alfanuméricos."
                page.update()
                return

            # Validar grado
            if not grado_val.isdigit() or not 1 <= int(grado_val) <= 25:
                error.value = "El grado debe ser un número entre 1 y 25."
                page.update()
                return

            # Validar grupo
            if not re.fullmatch(r"[A-Z0-9]{1,10}", grupo_val):
                error.value = "Ingresa un grupo válido de máximo 10 caracteres."
                page.update()
                return

            # Validar especialidad
            if len(especialidad_val) > 100:
                error.value = "La especialidad no puede superar 100 caracteres."
                page.update()
                return

            try:
                enviar_api(
                    f"alumnos/{alumno['alumno_id']}",
                    datos={
                        "alumno_matricula": matricula_val,
                        "alumno_nombre": nombre_val,
                        "alumno_curp": curp_val,
                        "alumno_grado": int(grado_val),
                        "alumno_grupo": grupo_val,
                        "alumno_especialidad": especialidad_val or None
                    }
                )

                cerrar_dialogo(dialogo)
                cargar_datos()
                mostrar_mensaje("Alumno actualizado correctamente.")

            except Exception as ex:
                error.value = str(ex)
                page.update()


        dialogo.actions = [
            ft.TextButton("Cancelar", on_click=lambda e: cerrar_dialogo(dialogo)),
            ft.Button("Guardar cambios", on_click=guardar)
        ]

        abrir_dialogo(dialogo)


 

    def abrir_edicion_tutor(tutor):
        nombre_tutor = ft.TextField(
            label="Nombre completo",
            value=str(tutor.get("tutor_nombre") or "")
        )
        ine = ft.TextField(
            label="INE",
            value=str(tutor.get("tutor_ine") or "")
        )
        telefono = ft.TextField(
            label="Teléfono",
            value=str(tutor.get("tutor_telefono") or "")
        )
        correo = ft.TextField(
            label="Correo electrónico",
            value=str(tutor.get("tutor_correo") or "")
        )
        error = ft.Text("", color="red")

        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar tutor"),
            content=ft.Container(
                width=420,
                content=ft.Column(
                    [nombre_tutor, ine, telefono, correo, error],
                    tight=True
                )
            ),
            actions_alignment=ft.MainAxisAlignment.END
        )

     
        def guardar(e):
            nombre_val = " ".join((nombre_tutor.value or "").split())
            ine_val = (ine.value or "").strip().upper()
            telefono_val = (telefono.value or "").strip()
            correo_val = (correo.value or "").strip()

            # Validar nombre
            if not validar_nombre(nombre_val):
                error.value = "Ingresa un nombre válido para el tutor."
                page.update()
                return

            # Validar INE
            if not validar_ine(ine_val):
                error.value = "La clave de elector debe tener 18 caracteres alfanuméricos."
                page.update()
                return

            # Validar teléfono
            if not validar_telefono(telefono_val):
                error.value = "El teléfono debe contener exactamente 10 dígitos."
                page.update()
                return

            # Validar correo
            if not validar_correo(correo_val):
                error.value = "Ingresa un correo electrónico válido."
                page.update()
                return

            try:
                enviar_api(
                    f"tutores/{tutor['tutor_id']}",
                    datos={
                        "tutor_nombre": nombre_val,
                        "tutor_ine": ine_val,
                        "tutor_telefono": telefono_val,
                        "tutor_correo": correo_val or None
                    }
                )

                cerrar_dialogo(dialogo)
                cargar_datos()
                mostrar_mensaje("Tutor actualizado correctamente.")

            except Exception as ex:
                error.value = str(ex)
                page.update()


        dialogo.actions = [
            ft.TextButton("Cancelar", on_click=lambda e: cerrar_dialogo(dialogo)),
            ft.Button("Guardar cambios", on_click=guardar)
        ]

        abrir_dialogo(dialogo)


 

    def confirmar_estado_alumno(alumno):
        esta_activo = str(alumno.get("alumno_estatus", "")).lower() == "activo"
        error = ft.Text("", color="red")

        if esta_activo:
            motivo = ft.TextField(
                label="Motivo de la baja",
                multiline=True,
                min_lines=2,
                max_lines=4
            )

            contenido = ft.Column(
                [
                    ft.Text(
                        f"¿Deseas dar de baja a {alumno.get('alumno_nombre')}?"
                    ),
                    motivo,
                    error
                ],
                tight=True
            )
        else:
            motivo = None
            contenido = ft.Column(
                [
                    ft.Text(
                        f"¿Deseas reactivar a {alumno.get('alumno_nombre')}?"
                    ),
                    error
                ],
                tight=True
            )

        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar operación"),
            content=ft.Container(width=420, content=contenido),
            actions_alignment=ft.MainAxisAlignment.END
        )

        def confirmar(e):
            try:
                if esta_activo:
                    if not motivo.value.strip():
                        error.value = "Debes indicar el motivo de la baja."
                        page.update()
                        return

                    enviar_api(
                        f"alumnos/{alumno['alumno_id']}/baja",
                        datos={"motivo": motivo.value.strip()}
                    )
                else:
                    enviar_api(
                        f"alumnos/{alumno['alumno_id']}/alta"
                    )

                cerrar_dialogo(dialogo)
                cargar_datos()
                mostrar_mensaje("Estado del alumno actualizado.")

            except Exception as ex:
                error.value = str(ex)
                page.update()

        dialogo.actions = [
            ft.TextButton("Cancelar", on_click=lambda e: cerrar_dialogo(dialogo)),
            ft.Button("Confirmar", on_click=confirmar)
        ]

        abrir_dialogo(dialogo)



    def confirmar_estado_tutor(tutor):
        esta_activo = bool(tutor.get("tutor_activo", True))
        error = ft.Text("", color="red")

        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar operación"),
            content=ft.Container(
                width=420,
                content=ft.Column(
                    [
                        ft.Text(
                            f"¿Deseas {'dar de baja' if esta_activo else 'reactivar'} "
                            f"a {tutor.get('tutor_nombre')}?"
                        ),
                        error
                    ],
                    tight=True
                )
            ),
            actions_alignment=ft.MainAxisAlignment.END
        )

        def confirmar(e):
            try:
                accion = "baja" if esta_activo else "alta"

                enviar_api(
                    f"tutores/{tutor['tutor_id']}/{accion}"
                )

                cerrar_dialogo(dialogo)
                cargar_datos()
                mostrar_mensaje("Estado del tutor actualizado.")

            except Exception as ex:
                error.value = str(ex)
                page.update()

        dialogo.actions = [
            ft.TextButton("Cancelar", on_click=lambda e: cerrar_dialogo(dialogo)),
            ft.Button("Confirmar", on_click=confirmar)
        ]

        abrir_dialogo(dialogo)

   

    def mostrar_usuarios(e=None):
        texto = (buscar_usuarios.value or "").strip().lower()
        filas = []

        for usuario in usuarios:
            contenido = (
                str(usuario.get("alumno_matricula", "")) + " " +
                str(usuario.get("alumno_nombre", "")) + " " +
                str(usuario.get("usuario_login", ""))
            ).lower()

            if texto not in contenido:
                continue

            activo = bool(usuario.get("usuario_activo"))
            debe_cambiar = bool(usuario.get("debe_cambiar_password"))

            estado = "Activa" if activo else "Inactiva"
            cambio = "Cambio pendiente" if debe_cambiar else "Contraseña actualizada"

            

            filas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(usuario.get("alumno_matricula") or ""))),
                        ft.DataCell(ft.Text(str(usuario.get("alumno_nombre") or ""))),
                        ft.DataCell(ft.Text(str(usuario.get("usuario_login") or ""))),
                        ft.DataCell(ft.Text(estado, color="#287A45" if activo else "#B3261E")),
                        ft.DataCell(ft.Text(cambio, color="#B56A20" if debe_cambiar else "#287A45")),
                        
                    ]
                )
            )

        tabla_usuarios.controls = [
            ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Matrícula")),
                    ft.DataColumn(ft.Text("Alumno")),
                    ft.DataColumn(ft.Text("Usuario")),
                    ft.DataColumn(ft.Text("Cuenta")),
                    ft.DataColumn(ft.Text("Contraseña")),
                    ft.DataColumn(ft.Text("Acciones"))
                ],
                rows=filas,
                heading_row_color="#EAF0F7",
                data_row_min_height=60
            )
        ]

        if not filas:
            tabla_usuarios.controls = [
                ft.Text("No se encontraron cuentas de acceso.", color="#65758A")
            ]

        page.update()

    def cargar_usuarios(e=None):
        try:
            respuesta = consultar_api("usuarios-alumnos")
            if not respuesta.get("exito"):
                raise Exception(respuesta.get("mensaje", "No se pudieron consultar las cuentas."))

            usuarios.clear()
            usuarios.extend(respuesta.get("usuarios", []))
            mostrar_usuarios()

        except Exception as ex:
            print("ERROR AL CARGAR USUARIOS:", repr(ex))
            tabla_usuarios.controls = [
                ft.Text(f"No se pudieron cargar las cuentas: {ex}", color="red")
            ]
            page.update()

  
        
        



        

    def cerrar_sesion(e):
        page.session.store.remove("token")
        page.clean()

        from screens.login import login_view
        page.add(login_view(page))
        page.update()

    buscar_alumnos.on_change = lambda e: (mostrar_alumnos(), page.update())
    buscar_tutores.on_change = lambda e: (mostrar_tutores(), page.update())
    buscar_usuarios.on_change = lambda e: mostrar_usuarios()

    cargar_datos()
    cargar_usuarios()

   


    return ft.Row(
        expand=True,
        spacing=0,
        controls=[

            # MENÚ LATERAL
            ft.Container(
                width=230,
                bgcolor="#082D59",
                padding=20,
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.SCHOOL, size=45, color="white"),
                        ft.Text(
                            "Sistema Escolar",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                            color="white"
                        ),
                        ft.Text("Administración", color="#B8CBE0"),
                        ft.Divider(color="#47617F"),
                        ft.Text("MENÚ PRINCIPAL", color="#B8CBE0", size=11),

                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.HOME, color="white"),
                            title=ft.Text("Inicio", color="white")
                        ),
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.SCHOOL, color="white"),
                            title=ft.Text("Alumnos y tutores", color="white")
                        ),
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.CREDIT_CARD, color="white"),
                            title=ft.Text("Asistencia NFC", color="white")
                        ),

                        ft.Container(expand=True),

                        ft.Text(
                            f"Administrador: {nombre}",
                            color="white",
                            size=12
                        ),

                        ft.Button(
                            content="Cerrar sesión",
                            icon=ft.Icons.LOGOUT,
                            on_click=cerrar_sesion,
                            width=190
                        )
                    ],
                    spacing=15
                )
            ),

            # CONTENIDO PRINCIPAL
            ft.Container(
                expand=True,
                bgcolor="#F3F6FA",
                padding=25,
                content=ft.Column(
                    [
                        ft.Text(
                            "Panel de administración",
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color="#082D59"
                        ),

                        ft.Text(
                            "Resumen general del sistema escolar",
                            color="#65758A"
                        ),

                        ft.Row(
                            alignment=ft.MainAxisAlignment.END,
                            controls=[
                                ft.Button(
                                    "Actualizar datos",
                                    icon=ft.Icons.REFRESH,
                                    on_click=cargar_datos
                                )
                            ]
                        ),

                        mensaje_estado,

                        ft.Text(
                            "Estadísticas generales",
                            size=21,
                            weight=ft.FontWeight.BOLD,
                            color="#082D59"
                        ),

                        ft.Row(
                            wrap=True,
                            spacing=15,
                            controls=[
                                crear_tarjeta(
                                    "Total de alumnos",
                                    total_alumnos,
                                    "Alumnos registrados",
                                    ft.Icons.SCHOOL,
                                    "#2877C7"
                                ),
                                crear_tarjeta(
                                    "Total de tutores",
                                    total_tutores,
                                    "Tutores registrados",
                                    ft.Icons.PEOPLE,
                                    "#287A45"
                                ),
                                crear_tarjeta(
                                    "Alumnos activos",
                                    alumnos_activos,
                                    "Con estatus activo",
                                    ft.Icons.PERSON,
                                    "#B56A20"
                                )
                            ]
                        ),

                        ft.Divider(),

                        ft.Text(
                            "Alumnos registrados",
                            size=21,
                            weight=ft.FontWeight.BOLD,
                            color="#082D59"
                        ),

                        ft.Row(
                            [
                                buscar_alumnos,
                                crear_boton_filtro("Todos", "alumnos", "todos"),
                                crear_boton_filtro("Activos", "alumnos", "activos"),
                                crear_boton_filtro("Bajas", "alumnos", "bajas")
                            ],
                            wrap=True,
                            spacing=8
                        ),

                        ft.Row(
                            scroll=ft.ScrollMode.AUTO,
                            controls=[tabla_alumnos]
                        ),

                        ft.Divider(),

                        ft.Text(
                            "Tutores registrados",
                            size=21,
                            weight=ft.FontWeight.BOLD,
                            color="#082D59"
                        ),

                        ft.Row(
                            [
                                buscar_tutores,
                                crear_boton_filtro("Todos", "tutores", "todos"),
                                crear_boton_filtro("Activos", "tutores", "activos"),
                                crear_boton_filtro("Inactivos", "tutores", "inactivos")
                            ],
                            wrap=True,
                            spacing=8
                        ),

                        ft.Row(
                            scroll=ft.ScrollMode.AUTO,
                            controls=[tabla_tutores]
                        ),

                        ft.Divider(),

                        

                        
                        
                        ft.Row(
                            scroll=ft.ScrollMode.AUTO,
                            controls=[tabla_usuarios]
                        )
                    ],
                    spacing=18,
                    scroll=ft.ScrollMode.AUTO
                )
            )
        ]
    )