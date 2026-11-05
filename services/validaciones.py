
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

    matricula = datos.get("matricula", "").strip()
    alumno = " ".join(datos.get("alumno", "").split())
    tutor = " ".join(datos.get("tutor", "").split())
    ine = datos.get("ine", "").strip().upper()
    telefono = datos.get("telefono", "").strip()
    correo = datos.get("correo", "").strip()

    # Matrícula
    if not matricula:
        errores["matricula"] = (
            "Ingresa la matrícula del alumno. "
            "Debe ser la matrícula asignada por la institución."
        )

    # Nombre del alumno
    if not alumno:
        errores["alumno"] = "Ingresa el nombre completo del alumno."
    elif not validar_nombre(alumno):
        errores["alumno"] = (
            "Escribe solamente letras, espacios, acentos, "
            "guiones o apóstrofes. Ejemplo: José Luis Pérez."
        )

    # Nombre del tutor
    if not tutor:
        errores["tutor"] = "Ingresa el nombre completo del tutor."
    elif not validar_nombre(tutor):
        errores["tutor"] = (
            "Escribe solamente letras, espacios, acentos, "
            "guiones o apóstrofes. Ejemplo: María López García."
        )

    # INE
    if not ine:
        errores["ine"] = "Ingresa la clave de elector de la INE."
    elif not validar_ine(ine):
        errores["ine"] = (
            "La clave de elector debe tener exactamente "
            "18 caracteres, utilizando únicamente letras y números."
        )

    # Teléfono
    if not telefono:
        errores["telefono"] = "Ingresa el número telefónico del tutor."
    elif not validar_telefono(telefono):
        errores["telefono"] = (
            "Escribe exactamente 10 números, sin espacios, "
            "guiones ni letras. Ejemplo: 2461234567."
        )

    # Correo electrónico (opcional)
    if not validar_correo(correo):
        errores["correo"] = (
            "Ingresa un correo válido. Ejemplo: usuario@gmail.com."
        )

    datos_limpios = {
        "matricula": matricula,
        "alumno": alumno,
        "tutor": tutor,
        "ine": ine,
        "telefono": telefono,
        "correo": correo
    }

    return errores, datos_limpios
