"""Usuarios del panel, con dos roles:

- **admin**: acceso a Configuración (impresoras, clientes/tokens,
  usuarios) además de las pantallas de comandas.
- **estandar**: solo entra a ver las pantallas de comandas y
  aceptarlas/completarlas — sin acceso a Configuración. Opcionalmente
  queda ASIGNADO a una sola impresora (ej. "Pamela" -> "Brasa"): entra
  directo a esa pantalla y no puede ver ni operar las demás. Sin
  asignación, ve el listado completo de pantallas (comportamiento previo).

Alta manual (la crea un admin desde Configuración → Usuarios), salvo el
primero, que se crea en /setup en el primer arranque (siempre como admin).
Mismo esquema de hash que horno-ruta80/app/auth.py (PBKDF2 vía hashlib,
sin dependencias nuevas).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import uuid

from . import config

_PATH = os.path.join(config.DATA_DIR, "users.json")
_lock = threading.RLock()
_users: list[dict] = []

ROLES = {"admin", "estandar"}


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


def _persist() -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    tmp = _PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_users, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _PATH)


def load() -> None:
    global _users
    try:
        with open(_PATH, encoding="utf-8") as f:
            _users = json.load(f)
    except (OSError, json.JSONDecodeError):
        _users = []


def exists_any() -> bool:
    with _lock:
        return bool(_users)


def _public(u: dict) -> dict:
    return {"id": u["id"], "username": u["username"], "rol": u["rol"],
            "nombre": u.get("nombre", ""), "impresora": u.get("impresora") or None}


def list_users() -> list[dict]:
    with _lock:
        return [_public(u) for u in _users]


def create(username: str, password: str, rol: str = "estandar", nombre: str = "",
          impresora: str | None = None) -> dict:
    username = (username or "").strip().lower()
    if not username:
        raise ValueError("El usuario es obligatorio.")
    if len(password or "") < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres.")
    if rol not in ROLES:
        raise ValueError("Rol inválido.")
    # Solo tiene sentido restringir a una impresora a un usuario estándar —
    # un admin siempre ve/opera todas.
    impresora = (impresora or "").strip() or None
    if rol == "admin":
        impresora = None
    with _lock:
        if any(u["username"] == username for u in _users):
            raise ValueError("Ese usuario ya existe.")
        user = {
            "id": uuid.uuid4().hex[:8],
            "username": username,
            "password_hash": _hash(password),
            "rol": rol,
            "nombre": nombre or username,
            "impresora": impresora,
        }
        _users.append(user)
        _persist()
        return _public(user)


def delete(user_id: str) -> None:
    with _lock:
        target = next((u for u in _users if u["id"] == user_id), None)
        if not target:
            return
        admins_restantes = [u for u in _users if u["rol"] == "admin" and u["id"] != user_id]
        if target["rol"] == "admin" and not admins_restantes:
            raise ValueError("No puedes eliminar al único administrador.")
        _users[:] = [u for u in _users if u["id"] != user_id]
        _persist()


def authenticate(username: str, password: str) -> dict | None:
    username = (username or "").strip().lower()
    with _lock:
        for u in _users:
            if u["username"] == username and _verify_hash(password, u["password_hash"]):
                return _public(u)
    return None


load()
