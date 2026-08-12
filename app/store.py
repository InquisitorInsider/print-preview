"""Estado en memoria de las impresoras virtuales + su historial de tickets.

Los `blocks` de cada ticket llegan ya en la misma estructura que usa
print-agent (ver su `app/printer.py`) — no hace falta decodificar nada, se
guardan tal cual y se renderizan en el navegador (ver `ui.py`).

Persistencia liviana: solo los NOMBRES de las impresoras creadas sobreviven
un reinicio (`DATA_DIR/printers.json`). El historial de tickets es efímero
a propósito — esto es una herramienta de vista previa, no un archivo de
auditoría.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
_CONFIG_PATH = os.path.join(DATA_DIR, "printers.json")
_MAX_HISTORY = 15

ESTADOS = ("pendiente", "aceptado", "completado")

_lock = threading.Lock()
_printers: set[str] = set()
_history: dict[str, list[dict]] = {}


def _save_config() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = _CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sorted(_printers), f, ensure_ascii=False, indent=2)
    os.replace(tmp, _CONFIG_PATH)


def load_config() -> list[str]:
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        return [str(x) for x in raw]
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return []


def ensure_printer(name: str) -> None:
    """Da de alta la impresora si no existía — alta manual desde el tablero,
    o automática al recibir el primer trabajo con ese nombre (el sistema
    que imprime no tiene por qué pre-registrar nada acá)."""
    name = (name or "").strip()
    if not name:
        return
    with _lock:
        if name not in _printers:
            _printers.add(name)
            _history.setdefault(name, [])
            _save_config()


def remove_printer(name: str) -> None:
    with _lock:
        _printers.discard(name)
        _history.pop(name, None)
        _save_config()


def list_printers() -> list[str]:
    with _lock:
        return sorted(_printers)


def record_ticket(name: str, blocks: list, copies: int, source: str) -> None:
    ensure_printer(name)
    with _lock:
        hist = _history.setdefault(name, [])
        hist.insert(0, {
            "id": uuid.uuid4().hex[:10],
            "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "blocks": blocks,
            "copies": copies,
            "source": source,
            "estado": "pendiente",
        })
        del hist[_MAX_HISTORY:]


def set_estado(name: str, ticket_id: str, estado: str) -> bool:
    if estado not in ESTADOS:
        raise ValueError("Estado inválido.")
    with _lock:
        for t in _history.get(name, []):
            if t["id"] == ticket_id:
                t["estado"] = estado
                return True
    return False


def clear_history(name: str) -> None:
    with _lock:
        _history[name] = []


def get_history(name: str) -> list[dict]:
    with _lock:
        return list(_history.get(name, []))


def snapshot() -> dict:
    with _lock:
        return {
            "printers": [
                {"name": name, "history": list(_history.get(name, []))}
                for name in sorted(_printers)
            ]
        }
