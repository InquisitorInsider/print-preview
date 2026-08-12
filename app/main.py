"""print-screen: "impresora virtual" para pruebas — se instala en la PC que
tiene pantalla (a diferencia de print-agent, que corre headless en la
Raspberry Pi y sí habla con hardware real por SMB/RAW/LPR).

Expone EL MISMO contrato público que print-agent (POST /print, GET
/printers, GET /health) para que cualquier sistema (Ruta80G, horno-ruta80,
caja-ruta80, etc.) pueda apuntar su `print_agent_url` acá en vez de al
agente real, sin cambiar una sola línea de código de negocio — pasar de
"impresora física" a "impresora virtual" es solo cambiar esa URL.

En vez de imprimir, cada trabajo se guarda y se muestra en el tablero (/)
o en la pantalla dedicada de esa impresora (/pantalla/<nombre>), tipo KDS.

Dos capas de autenticación, igual que print-agent:
1) Admin (tablero, pantallas, API de administración): HTTP Basic con
   ADMIN_USER/ADMIN_PASSWORD. Si ADMIN_PASSWORD está vacía, no hay
   protección.
2) Clientes de impresión (POST /print): Bearer token. Si no hay clientes
   configurados, el endpoint queda abierto en la red local.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from . import clients, config, store, ui

app = FastAPI(title="print-screen", version="1.1.0", docs_url="/docs")
_basic = HTTPBasic(auto_error=False)


def require_admin(creds: HTTPBasicCredentials | None = Depends(_basic)) -> None:
    if not config.ADMIN_PASSWORD:
        return
    ok = (
        creds is not None
        and secrets.compare_digest(creds.username, config.ADMIN_USER)
        and secrets.compare_digest(creds.password, config.ADMIN_PASSWORD)
    )
    if not ok:
        raise HTTPException(status_code=401, detail="No autorizado",
                            headers={"WWW-Authenticate": "Basic"})


class PrintJob(BaseModel):
    printer: str | None = None
    copies: int | None = 1
    blocks: list[Any] | None = None
    raw: dict[str, Any] | None = None
    source: str | None = None
    model_config = {"extra": "ignore"}


def _resolve_source(authorization: str | None, explicit: str | None) -> str:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if clients.has_clients():
        name = clients.resolve(token)
        if not name:
            raise HTTPException(status_code=401, detail="Token inválido o ausente")
        return name
    return (explicit or "").strip() or "anónimo"


# ---------- Mismo contrato público que print-agent ----------
@app.post("/print", status_code=202)
def print_endpoint(job: PrintJob, authorization: str | None = Header(default=None)) -> dict:
    if not job.blocks and not job.raw:
        raise HTTPException(status_code=400, detail="Falta 'blocks' o 'raw'")
    source = _resolve_source(authorization, job.source)
    printer_name = (job.printer or "").strip() or "(por defecto)"
    if job.blocks:
        blocks = job.blocks
    elif job.raw and "text" in job.raw:
        blocks = [{"type": "text", "text": job.raw["text"]}]
    else:
        # raw.escpos_base64: nadie en este proyecto lo usa hoy (todos mandan
        # `blocks`) — se avisa en vez de intentar decodificar ESC/POS.
        blocks = [{"type": "text", "text": "[contenido binario ESC/POS crudo — sin vista previa]"}]
    store.record_ticket(printer_name, blocks, job.copies or 1, source)
    job_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    return {"accepted": True, "job_id": job_id, "printer": printer_name, "source": source}


@app.get("/printers")
def list_printer_names() -> dict:
    names = store.list_printers()
    return {"default": names[0] if names else "", "printers": names}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "printers": store.list_printers()}


# ---------- Interfaz (protegida) ----------
@app.get("/", response_class=HTMLResponse)
def dashboard(_: None = Depends(require_admin)) -> str:
    return ui.DASHBOARD


@app.get("/pantalla/{name}", response_class=HTMLResponse)
def pantalla(name: str, _: None = Depends(require_admin)) -> str:
    store.ensure_printer(name)
    return ui.pantalla_page(name)


@app.get("/api/state")
def api_state(_: None = Depends(require_admin)) -> dict:
    return store.snapshot()


@app.get("/api/state/{name}")
def api_state_one(name: str, _: None = Depends(require_admin)) -> dict:
    return {"name": name, "history": store.get_history(name)}


@app.post("/api/printers")
def api_add_printer(payload: dict, _: None = Depends(require_admin)) -> dict:
    name = str((payload or {}).get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Falta el nombre")
    store.ensure_printer(name)
    return {"printers": store.list_printers()}


@app.delete("/api/printers/{name}")
def api_delete_printer(name: str, _: None = Depends(require_admin)) -> dict:
    store.remove_printer(name)
    return {"printers": store.list_printers()}


@app.post("/api/printers/{name}/clear")
def api_clear_history(name: str, _: None = Depends(require_admin)) -> dict:
    store.clear_history(name)
    return {"ok": True}


@app.post("/api/test")
def api_test(payload: dict, _: None = Depends(require_admin)) -> dict:
    name = str((payload or {}).get("printer", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Falta el nombre de la impresora")
    store.record_ticket(name, _sample_blocks(name), 1, "prueba")
    return {"ok": True}


def _sample_blocks(printer_name: str) -> list:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return [
        {"type": "text", "text": "TICKET DE PRUEBA", "align": "center", "bold": True, "size": "double"},
        {"type": "text", "text": "print-screen", "align": "center"},
        {"type": "line", "char": "="},
        {"type": "text", "text": f"Impresora: {printer_name}"},
        {"type": "text", "text": f"Fecha:     {now}"},
        {"type": "line"},
        {"type": "row", "left": "2 x Articulo de ejemplo", "right": "20.00", "bold": True},
        {"type": "row", "left": "1 x Otro articulo", "right": "5.50"},
        {"type": "line"},
        {"type": "row", "left": "TOTAL", "right": "25.50", "bold": True},
        {"type": "text", "text": "Acentos: ñ á é í ó ú ¿? ¡!"},
        {"type": "qr", "data": "https://print-screen.local/prueba", "size": 6},
        {"type": "feed", "lines": 1},
        {"type": "text", "text": "Configuracion correcta :)", "align": "center"},
        {"type": "cut"},
    ]


# ---------- Clientes / tokens (protegido) ----------
@app.get("/api/clients")
def api_list_clients(_: None = Depends(require_admin)) -> dict:
    return {"clients": clients.public()}


@app.post("/api/clients")
def api_save_client(payload: dict, _: None = Depends(require_admin)) -> dict:
    try:
        clients.save(str((payload or {}).get("name", "")), str((payload or {}).get("token", "")))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"clients": clients.public()}


@app.delete("/api/clients/{name}")
def api_delete_client(name: str, _: None = Depends(require_admin)) -> dict:
    clients.delete(name)
    return {"clients": clients.public()}


@app.on_event("startup")
def _startup() -> None:
    for name in store.load_config():
        store.ensure_printer(name)
