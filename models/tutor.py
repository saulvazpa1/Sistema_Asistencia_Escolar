class Tutor:

    def __init__(
        self,
        tutor_nombre,
        tutor_telefono=None,
        tutor_correo=None,
        tutor_ine=None
    ):
        self.__tutor_nombre = tutor_nombre
        self.__tutor_telefono = tutor_telefono
        self.__tutor_correo = tutor_correo
        self.__tutor_ine = tutor_ine

    def get_tutor_nombre(self):
        return self.__tutor_nombre

    def get_tutor_telefono(self):
        return self.__tutor_telefono

    def get_tutor_correo(self):
        return self.__tutor_correo

    def get_tutor_ine(self):
        return self.__tutor_ine