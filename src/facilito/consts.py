"""
Constants
"""

from enum import Enum

COOKIES_FILE = ".cookies.txt"
BASE_URL = "https://codigofacilito.com"
LOGIN_URL = "https://codigofacilito.com/users/sign_in"
POST_LOGIN_URL = "https://codigofacilito.com/usuarios/mis_cursos"
SAMPLE_VIDEO_URL = "https://codigofacilito.com/videos/icon"
SAMPLE_ARTICLE_URL = "https://codigofacilito.com/articulos/programacion-concurrente"
SAMPLE_COURSE_URL = "https://codigofacilito.com/cursos/flutter-profesional"
ARTICLE_URL_REGEX = r"https://codigofacilito\.com/articulos/.+"
VIDEO_URL_REGEX = r"https://codigofacilito\.com/videos/.+"
COURSE_URL_REGEX = r"https://codigofacilito\.com/cursos/.+"
BOOTCAMP_URL_REGEX = r"https://codigofacilito\.com/programas/.+"
FFMPEG_URL = "https://ffmpeg.org/download.html"
CONFIG_FILE = ".conf.json"
DOWNLOADS_DIR = "downloads"
SYMBOLS_NAME = r"[<>.:;'\"/\\|?!¡¿º%&~ª*+=@#$%&[\]\{\}\(\)]"
NEWLINE_NAME = r"[\n]"
CLASS_NAME = r"(?m)^(\d+)-\s*(.*)"
BOOTCAMP_NAME = r"(?i)\bBootcamp\b(?:\s*de\s*)?(.*)"
MODULE_NUMBER = r"(?i)\b(Módulo|Modulo)\b(?:\s*)"
VIDEO_NUMBER = r"(?i)\bClase\b(?:\s*)"

## For messages of error
CLIENT_ERROR = "FacilitoApi must be used as a context manager"

## For messages of download
LOGIN_OK = (
    "[bold reverse blink green]   SUCCESSFUL LOGIN !!!   [/bold reverse blink green]"
)
PROCESSING = "[yellow]⠹[/yellow] Processing ..."
DOWNLOADING = "[yellow]⠹[/yellow] Downloading"
VIDEO_DL_DONE = "[green]✓[/green] Done!"
VIDEO_DL_ERROR_1 = "An [red]error[/red] occurred while downloading :("
VIDEO_DL_ERROR_2 = "=>[reverse white]Retrying [/reverse white]..."
VIDEO_DL_ERROR_MAX = "[red]✗[/red] Unable to download the video"


class FileType(Enum):
    """
    File type
    """

    PDF = "pdf"
    HTML = "html"
