"""Clientes/tokens autorizados a mandar trabajos a POST /print — mismo
patrón que print-agent/app/settings.py (la parte de clientes). Si no hay
ningún cliente configurado, /print queda abierto en la red local
(conveniencia para pruebas rápidas); en cuanto agregas uno, exige un
Authorization: Bearer <token> válido.
"""
from __future__ import annotations

import json
import os
import threading

from . import config

_PATH = os.path.join(config.DATA_DIR, "clients.json")
_lock = threading.RLock()
_clients: list[dict] = []


def _persist() -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    tmp = _PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_clients, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _PATH)


def load() -> None:
    global _clients
    try:
        with open(_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        _clients = [
            {"name": str(c.get("name", "")).strip(), "token": str(c.get("token", "")).strip()}
            for c in raw if c.get("name")
        ]
    except (OSError, json.JSONDecodeError, TypeError):
        _clients = []


def public() -> list[dict]:
    """Lista para la UI, ocultando el token real."""
    with _lock:
        return [{"name": c["name"], "token": "***" if c.get("token") else ""} for c in _clients]


def has_clients() -> bool:
    with _lock:
        return any(c.get("token") for c in _clients)


def resolve(token: str | None) -> str | None:
    """Devuelve el nombre del cliente cuyo token coincide, o None."""
    token = (token or "").strip()
    if not token:
        return None
    with _lock:
        for c in _clients:
            if c.get("token") and c["token"] == token:
                return c["name"]
    return None


def save(name: str, token: str) -> None:
    name = (name or "").strip()
    token = (token or "").strip()
    if not name:
        raise ValueError("el cliente necesita un nombre")
    with _lock:
        for i, c in enumerate(_clients):
            if c["name"] == name:
                if not token:  # token vacío al editar => conservar el guardado
                    token = c.get("token", "")
                _clients[i] = {"name": name, "token": token}
                break
        else:
            _clients.append({"name": name, "token": token})
        _persist()


def delete(name: str) -> None:
    with _lock:
        _clients[:] = [c for c in _clients if c["name"] != name]
        _persist()


load()
