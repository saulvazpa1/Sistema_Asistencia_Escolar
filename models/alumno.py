
class Alumno:

    def __init__(
        self,
        alumno_matricula,
        alumno_nombre,
        alumno_curp=None,
        alumno_carrera_id=None,
        alumno_grado=None,
        alumno_grupo=None,
        alumno_especialidad=None
    ):
        self.alumno_matricula = alumno_matricula
        self.alumno_nombre = alumno_nombre
        self.alumno_curp = alumno_curp
        self.alumno_carrera_id = alumno_carrera_id
        self.alumno_grado = alumno_grado
        self.alumno_grupo = alumno_grupo
        self.alumno_especialidad = alumno_especialidad
