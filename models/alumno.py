
class Alumno:

    def __init__(
        self,
        alumno_matricula,
        alumno_nombre,
        alumno_carrera_id=None,
        alumno_grupo_id=None
    ):
        self.alumno_matricula = alumno_matricula
        self.alumno_nombre = alumno_nombre
        self.alumno_carrera_id = alumno_carrera_id
        self.alumno_grupo_id = alumno_grupo_id