"""Configuración base (variables de entorno)."""
import os


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


DATA_DIR = _get("DATA_DIR", "/app/data")
