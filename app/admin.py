"""Credenciales del panel de administración: se crean interactivamente en
el primer arranque (mismo patrón de "primer arranque crea el admin" que
horno-ruta80/Ruta80G) — el usuario elige su propia contraseña en vez de
recibir una generada al azar. Hash PBKDF2 vía hashlib (stdlib, sin
dependencias nuevas), mismo esquema que horno-ruta80/app/auth.py.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading

from . import config

_PATH = os.path.join(config.DATA_DIR, "admin.json")
_lock = threading.RLock()


def _hash(pw: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000)
    return "pbkdf2_sha256$200000$%s$%s" % (
        base64.b64encode(salt).decode(), base64.b64encode(dk).decode())


def _verify_hash(pw: str, stored: str) -> bool:
    try:
        _algo, iters, salt_b64, hash_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, int(iters))
        return hmac.compare_digest(dk, expected)
    except Exception:  # noqa: BLE001
        return False


def exists() -> bool:
    return os.path.exists(_PATH)


def create(username: str, password: str) -> None:
    username = (username or "").strip()
    if not username:
        raise ValueError("El usuario es obligatorio.")
    if len(password or "") < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres.")
    with _lock:
        if exists():
            raise ValueError("Ya existe un usuario administrador.")
        os.makedirs(config.DATA_DIR, exist_ok=True)
        tmp = _PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"username": username, "password_hash": _hash(password)}, f)
        os.replace(tmp, _PATH)


def verify(username: str, password: str) -> bool:
    if not exists():
        return False
    try:
        with open(_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    return (
        secrets.compare_digest((username or "").strip(), data.get("username", ""))
        and _verify_hash(password, data.get("password_hash", ""))
    )
