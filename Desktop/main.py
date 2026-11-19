
import sys
from pathlib import Path

import flet as ft

# Obtener la carpeta principal del proyecto
RUTA_PROYECTO = Path(__file__).resolve().parent.parent

# Agregar la carpeta principal a las rutas de Python
if str(RUTA_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RUTA_PROYECTO))

from screens.login import login_view


def main(page: ft.Page):
    page.title = "Sistema de Asistencia Escolar"
    page.window.width = 1100
    page.window.height = 750
    page.window.min_width = 800
    page.window.min_height = 600
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F3F6FA"

    page.add(login_view(page))


ft.run(main)
