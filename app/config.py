"""Configuración base (variables de entorno). Mismo patrón que
print-agent/app/config.py."""
import os


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


DATA_DIR = _get("DATA_DIR", "/app/data")

# --- Protección del tablero/pantallas/API de administración ---
# Si ADMIN_PASSWORD queda vacío, esas rutas quedan abiertas en la red local
# (igual que print-agent) — definirlo es justamente lo que activa la
# protección.
ADMIN_USER = _get("ADMIN_USER", "admin")
ADMIN_PASSWORD = _get("ADMIN_PASSWORD")
