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
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import store, ui

app = FastAPI(title="print-screen", version="1.0.0", docs_url="/docs")


class PrintJob(BaseModel):
    printer: str | None = None
    copies: int | None = 1
    blocks: list[Any] | None = None
    raw: dict[str, Any] | None = None
    source: str | None = None
    model_config = {"extra": "ignore"}


# ---------- Mismo contrato público que print-agent ----------
@app.post("/print", status_code=202)
def print_endpoint(job: PrintJob) -> dict:
    if not job.blocks and not job.raw:
        raise HTTPException(status_code=400, detail="Falta 'blocks' o 'raw'")
    printer_name = (job.printer or "").strip() or "(por defecto)"
    source = (job.source or "").strip() or "anónimo"
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


# ---------- Interfaz ----------
@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return ui.DASHBOARD


@app.get("/pantalla/{name}", response_class=HTMLResponse)
def pantalla(name: str) -> str:
    store.ensure_printer(name)
    return ui.pantalla_page(name)


@app.get("/api/state")
def api_state() -> dict:
    return store.snapshot()


@app.get("/api/state/{name}")
def api_state_one(name: str) -> dict:
    return {"name": name, "history": store.get_history(name)}


@app.post("/api/printers")
def api_add_printer(payload: dict) -> dict:
    name = str((payload or {}).get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Falta el nombre")
    store.ensure_printer(name)
    return {"printers": store.list_printers()}


@app.delete("/api/printers/{name}")
def api_delete_printer(name: str) -> dict:
    store.remove_printer(name)
    return {"printers": store.list_printers()}


@app.post("/api/printers/{name}/clear")
def api_clear_history(name: str) -> dict:
    store.clear_history(name)
    return {"ok": True}


@app.on_event("startup")
def _startup() -> None:
    for name in store.load_config():
        store.ensure_printer(name)
