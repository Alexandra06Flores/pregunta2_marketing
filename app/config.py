"""Lectura de configuracion desde variables de entorno."""
import os


def media_dir():
    return os.getenv("MEDIA_DIR", "/data/media")
