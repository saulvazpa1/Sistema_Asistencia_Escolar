
import re


def validar_matricula(matricula):
    return bool(matricula and matricula.strip())


def validar_nombre(nombre):
    if not nombre:
        return False

    patron = r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:[ '-][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*$"
    return bool(re.fullmatch(patron, nombre))


def validar_telefono(telefono):
    return bool(re.fullmatch(r"[0-9]{10}", telefono or ""))


def validar_ine(ine):
    return bool(re.fullmatch(r"[A-Za-z0-9]{18}", ine or ""))


def validar_correo(correo):
    if not correo:
        return True

    patron = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.fullmatch(patron, correo))


def validar_registro(datos):
    errores = {}

    # Obtener y limpiar datos
    matricula = datos.get("matricula", "").strip()
    alumno = " ".join(datos.get("alumno", "").split())
    curp = datos.get("curp", "").strip().upper()
   
    grado = datos.get("grado", "").strip()
    grupo = datos.get("grupo", "").strip().upper()
    tiene_especialidad = datos.get("tiene_especialidad", "").strip()
    especialidad = datos.get("especialidad", "").strip()
    tutor = " ".join(datos.get("tutor", "").split())
    ine = datos.get("ine", "").strip().upper()
    telefono = datos.get("telefono", "").strip()
    correo = datos.get("correo", "").strip()

    # Matrícula
    if not matricula:
        errores["matricula"] = "Ingresa la matrícula del alumno."

    # Alumno
    if not alumno:
        errores["alumno"] = "Ingresa el nombre completo del alumno."
    elif not validar_nombre(alumno):
        errores["alumno"] = "Ingresa un nombre válido."

    # CURP
    if not re.fullmatch(r"[A-Z0-9]{18}", curp):
        errores["curp"] = "La CURP debe contener exactamente 18 caracteres."

    # Carrera manual
   
    # Grado
    if not grado.isdigit() or not 1 <= int(grado) <= 25:
        errores["grado"] = "El grado debe ser un número entre 1 y 25."

    # Grupo manual
    if not re.fullmatch(r"[A-Z0-9]{1,10}", grupo):
        errores["grupo"] = "Ingresa un grupo válido (máximo 10 caracteres)."

    # Especialidad
    if tiene_especialidad == "si":
        if not especialidad or len(especialidad) > 100:
            errores["especialidad"] = "Ingresa la especialidad."
    elif tiene_especialidad != "no":
        errores["tiene_especialidad"] = "Selecciona una opción."

    if tiene_especialidad == "no":
        especialidad = ""

    # Tutor
    if not tutor:
        errores["tutor"] = "Ingresa el nombre completo del tutor."
    elif not validar_nombre(tutor):
        errores["tutor"] = "Ingresa un nombre válido para el tutor."

    # INE
    if not ine:
        errores["ine"] = "Ingresa la clave de elector."
    elif not validar_ine(ine):
        errores["ine"] = "La clave de elector debe tener 18 caracteres."

    # Teléfono
    if not telefono:
        errores["telefono"] = "Ingresa el teléfono del tutor."
    elif not validar_telefono(telefono):
        errores["telefono"] = "El teléfono debe tener exactamente 10 dígitos."

    # Correo opcional
    if not validar_correo(correo):
        errores["correo"] = "Ingresa un correo válido."

    # Datos limpios
    datos_limpios = {
        "matricula": matricula,
        "alumno": alumno,
        "curp": curp,
   
        "grado": int(grado) if grado.isdigit() else None,
        "grupo": grupo,
        "tiene_especialidad": tiene_especialidad,
        "especialidad": especialidad,
        "tutor": tutor,
        "ine": ine,
        "telefono": telefono,
        "correo": correo
    }

    return errores, datos_limpios