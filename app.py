from flask import Flask, request, render_template
from models.alumno import Alumno
from models.tutor import Tutor
from services.registro_service import RegistroService
import traceback

app = Flask(__name__)

registro_service = RegistroService()


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/registrar", methods=["POST"])
def registrar():

    try:
        # 1. Obtener datos del formulario
        matricula = request.form.get("matricula")
        nombre_alumno = request.form.get("alumno")

        nombre_tutor = request.form.get("tutor")
        telefono = request.form.get("telefono")
        ine = request.form.get("ine")

        # 2. Crear objetos
        alumno = Alumno(
            alumno_matricula=matricula,
            alumno_nombre=nombre_alumno
        )

        tutor = Tutor(
            tutor_nombre=nombre_tutor,
            tutor_telefono=telefono,
            tutor_ine=ine
        )

        # 3. Registrar alumno y tutor
        alumno_id = registro_service.registrar_alumno(alumno)
        tutor_id = registro_service.registrar_tutor(tutor)

        # 4. Relacionar alumno y tutor
        registro_service.relacionar_alumno_tutor(
            alumno_id,
            tutor_id,
            relacion="Tutor",
            es_tutor_principal=True
        )

        # 5. Generar enlace de Telegram
        enlace = registro_service.generar_enlace_telegram(tutor_id)

        if not enlace:
            return "Se registraron los datos, pero no se pudo generar el enlace."

        return f"""
            <h2>¡Registro exitoso!</h2>
            <p>Alumno: {nombre_alumno}</p>
            <p>Tutor: {nombre_tutor}</p>
            <a href="{enlace}" target="_blank">
                Vincular Telegram
            </a>
        """

    except Exception as error:
        print("ERROR AL REGISTRAR:")
        traceback.print_exc()
        return f"Error al registrar: {error}"


if __name__ == "__main__":
    app.run(debug=True)