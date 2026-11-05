
from flask import Flask, request, render_template
import psycopg

from models.alumno import Alumno
from models.tutor import Tutor
from services.registro_service import RegistroService
from services.validaciones import validar_registro


app = Flask(__name__)

registro_service = RegistroService()



def normalizar_errores(errores):
    """
    Garantiza que los errores siempre sean un diccionario,
    para evitar problemas al utilizar errores.get() en Jinja2.
    """

    if isinstance(errores, dict):
        return errores

    if isinstance(errores, list):
        return {
            "general": " ".join(str(error) for error in errores)
        }

    return {}



@app.route("/")
def inicio():

    return render_template(
        "index.html",
        errores={},
        valores={},
        enlace=None,
        exito=None
    )




@app.route("/registrar", methods=["POST"])
def registrar():

    datos = request.form.to_dict()

    # Validar los datos recibidos del formulario
    errores, datos = validar_registro(datos)

    errores = normalizar_errores(errores)

    # Si existen errores, regresar al formulario
    if errores:

        return render_template(
            "index.html",
            errores=errores,
            valores=datos,
            enlace=None,
            exito=None
        )

    try:

        

        alumno = Alumno(
            alumno_matricula=datos["matricula"],
            alumno_nombre=datos["alumno"]
        )

   
        tutor = Tutor(
            tutor_nombre=datos["tutor"],
            tutor_telefono=datos["telefono"],
            tutor_correo=datos["correo"] or None,
            tutor_ine=datos["ine"]
        )


       
        alumno_id = registro_service.registrar_alumno(alumno)

      

        tutor_id = registro_service.registrar_tutor(tutor)

       
        registro_service.relacionar_alumno_tutor(
            alumno_id=alumno_id,
            tutor_id=tutor_id,
            relacion="Tutor",
            es_tutor_principal=True
        )

      
        enlace = registro_service.generar_enlace_telegram(tutor_id)

     
        return render_template(
            "index.html",
            errores={},
            valores={},
            enlace=enlace,
            exito="¡Alumno y tutor registrados correctamente!"
        )

  

    except psycopg.errors.UniqueViolation as error:

        print("ERROR DE REGISTRO DUPLICADO:", repr(error))

        nombre_restriccion = error.diag.constraint_name

        errores = {}

        if nombre_restriccion == "uq_alumnos_matricula":

            errores["matricula"] = (
                "Esta matrícula ya se encuentra registrada. "
                "Ingresa una matrícula diferente."
            )

        elif nombre_restriccion == "uq_tutores_ine":

            errores["ine"] = (
                "Esta clave de elector ya se encuentra registrada."
            )

        else:

            errores["general"] = (
                "Uno de los datos únicos ya se encuentra registrado. "
                "Verifica la información."
            )

        return render_template(
            "index.html",
            errores=errores,
            valores=datos,
            enlace=None,
            exito=None
        )

   

    except Exception as error:

        print("ERROR REAL AL REGISTRAR:", repr(error))

        return render_template(
            "index.html",
            errores={
                "general": (
                    "No fue posible guardar el registro. "
                    "Revisa la consola para conocer el problema."
                )
            },
            valores=datos,
            enlace=None,
            exito=None
        )




if __name__ == "__main__":

    app.run(
        debug=True,
        use_reloader=False
    )
