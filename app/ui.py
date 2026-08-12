"""Interfaz web, autocontenida (mismo patrón que print-agent/app/ui.py):
un tablero general y una pantalla dedicada por impresora, sin dependencias
externas de frontend."""
from __future__ import annotations

import json

_TICKET_CSS = """
  :root{--bg:#f4f5f7;--card:#fff;--ink:#1b1f27;--muted:#6b7280;--line:#d8dce3;--accent:#2563eb;--err:#dc2626}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,Segoe UI,Roboto,sans-serif}
  header{background:var(--card);border-bottom:1px solid var(--line);padding:14px 20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
  header h1{font-size:1.1rem;margin:0}
  header .sub{color:var(--muted);font-size:.85rem}
  header a{color:var(--accent);text-decoration:none;font-size:.85rem}
  .wrap{padding:20px;max-width:1200px;margin:0 auto}
  .addbar{display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap}
  .addbar input{padding:8px 10px;border:1px solid var(--line);border-radius:8px;font-size:.9rem;min-width:220px}
  .addbar button, .btn{padding:8px 14px;border:1px solid var(--line);background:var(--card);border-radius:8px;cursor:pointer;font-size:.85rem}
  .btn.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
  .btn.danger{color:var(--err);border-color:#f3c2c2}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
  .pcard{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;display:flex;flex-direction:column;gap:8px}
  .pcard .phead{display:flex;justify-content:space-between;align-items:center}
  .pcard .pname{font-weight:600}
  .pcard .pactions{display:flex;gap:6px;flex-wrap:wrap}
  .pcard .pactions .btn{padding:5px 9px;font-size:.78rem}
  .empty{color:var(--muted);font-size:.85rem;padding:30px;text-align:center}
  .ticket{background:#fffef8;border:1px dashed #c9c2a8;border-radius:6px;padding:12px 14px;font-family:'Courier New',monospace;font-size:.82rem;line-height:1.35;color:#222}
  .ticket .tk-left{text-align:left}.ticket .tk-center{text-align:center}.ticket .tk-right{text-align:right}
  .ticket .tk-bold{font-weight:700}.ticket .tk-underline{text-decoration:underline}
  .ticket .tk-size-double,.ticket .tk-size-double_h{font-size:1.5em;line-height:1.3}
  .ticket .tk-size-double_w{letter-spacing:.12em}
  .ticket .tk-row{display:flex;justify-content:space-between;gap:10px}
  .ticket .tk-line{border-top:1px dashed #999;margin:4px 0}
  .ticket .tk-feed{width:100%}
  .ticket .tk-qr,.ticket .tk-barcode{text-align:center;border:1px dashed #999;border-radius:4px;padding:8px;margin:6px 0;color:#555;font-size:.78rem;word-break:break-all}
  .ticket .tk-cut{text-align:center;color:#999;margin:6px 0}
  .ticket .tk-drawer{text-align:center;color:#a15c00;margin:4px 0}
  .ticket .tk-empty{color:#999;text-align:center}
  .meta{color:var(--muted);font-size:.75rem;display:flex;justify-content:space-between}
  .badge{background:#eef2ff;color:var(--accent);border-radius:999px;padding:1px 8px;font-size:.72rem}
  .card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-top:22px}
  .card h2{margin:0 0 4px;font-size:1rem}
  .card .hint{color:var(--muted);font-size:.8rem;margin:0 0 12px}
  table.tbl{width:100%;border-collapse:collapse;font-size:.85rem}
  table.tbl th,table.tbl td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}
  .cform{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
  .cform input{padding:8px 10px;border:1px solid var(--line);border-radius:8px;font-size:.9rem}
"""

_RENDER_JS = r"""
function esc(s){ return String(s??'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function renderBlocks(blocks){
  let html = '';
  for(const b of (blocks||[])){
    const t = (b.type||'text').toLowerCase();
    if(t==='text'){
      const cls = ['tk-'+(b.align||'left'), 'tk-size-'+(b.size||'normal'), b.bold?'tk-bold':'', b.underline?'tk-underline':''].filter(Boolean).join(' ');
      html += `<div class="${cls}">${esc(b.text).replace(/\n/g,'<br>')}</div>`;
    } else if(t==='row'){
      html += `<div class="tk-row ${b.bold?'tk-bold':''}"><span>${esc(b.left)}</span><span>${esc(b.right)}</span></div>`;
    } else if(t==='line'||t==='divider'){
      html += `<div class="tk-line"></div>`;
    } else if(t==='feed'){
      html += `<div class="tk-feed" style="height:${(b.lines||1)*1.1}em"></div>`;
    } else if(t==='qr'){
      html += `<div class="tk-qr">▦ QR<br>${esc(b.data)}</div>`;
    } else if(t==='barcode'){
      html += `<div class="tk-barcode">▮▮▮ ${esc(b.symbology||'')}<br>${esc(b.data)}</div>`;
    } else if(t==='cut'){
      html += `<div class="tk-cut">✂ - - - - - - - - - - - - - - - ✂</div>`;
    } else if(t==='drawer'){
      html += `<div class="tk-drawer">💰 abre cajón</div>`;
    }
  }
  return html || '<div class="tk-empty">(ticket vacío)</div>';
}
"""

SETUP_PAGE = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Configurar administrador — print-screen</title>
<style>
{_TICKET_CSS}
  .setup{{max-width:380px;margin:60px auto;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:24px}}
  .setup h1{{font-size:1.1rem;margin:0 0 6px}}
  .setup p{{color:var(--muted);font-size:.85rem;margin:0 0 18px}}
  .setup label{{display:block;font-size:.82rem;margin:10px 0 4px}}
  .setup input{{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:8px;font-size:.9rem}}
  .setup button{{width:100%;margin-top:18px;padding:10px;border:none;border-radius:8px;background:var(--accent);color:#fff;font-size:.9rem;cursor:pointer}}
  .setup .err{{color:var(--err);font-size:.82rem;margin-top:10px;display:none}}
</style>
</head><body>
<div class="setup">
  <h1>🖨️ print-screen — primer arranque</h1>
  <p>Crea el usuario administrador del tablero. Se pide una sola vez.</p>
  <label>Usuario</label><input id="su" value="admin">
  <label>Contraseña</label><input id="sp" type="password">
  <label>Confirmar contraseña</label><input id="sp2" type="password">
  <div class="err" id="serr"></div>
  <button onclick="doSetup()">Crear administrador</button>
</div>
<script>
async function doSetup(){{
  const u = document.getElementById('su').value.trim();
  const p = document.getElementById('sp').value;
  const p2 = document.getElementById('sp2').value;
  const err = document.getElementById('serr');
  err.style.display = 'none';
  if(p !== p2){{ err.textContent = 'Las contraseñas no coinciden.'; err.style.display = 'block'; return; }}
  const r = await fetch('/api/setup', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{username:u, password:p}})}});
  if(!r.ok){{ const e = await r.json().catch(()=>({{}})); err.textContent = e.detail || 'Error'; err.style.display = 'block'; return; }}
  location.href = '/';
}}
document.getElementById('sp2').addEventListener('keydown', e=>{{ if(e.key==='Enter') doSetup(); }});
</script>
</body></html>"""

DASHBOARD = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>print-screen</title>
<style>{_TICKET_CSS}</style>
</head><body>
<header>
  <h1>🖨️ print-screen</h1>
  <span class="sub">Impresoras virtuales — vista previa de tickets, sin gastar papel</span>
</header>
<div class="wrap">
  <div class="addbar">
    <input id="newName" placeholder="Nombre de la impresora (ej. Barra, Caja, Brasa)">
    <button class="btn primary" onclick="addPrinter()">+ Agregar impresora virtual</button>
  </div>
  <div id="grid" class="grid"><div class="empty">Cargando…</div></div>

  <div class="card">
    <h2>Clientes / tokens</h2>
    <p class="hint">Cada sistema que manda tickets acá (Ruta80G, horno-ruta80, etc.) puede usar su propio token (header <code>Authorization: Bearer &lt;token&gt;</code>). Si no defines ninguno, <code>POST /print</code> queda abierto en la red local.</p>
    <table class="tbl" id="clientsTbl"><tr><th>Cliente</th><th>Token</th><th></th></tr></table>
    <div class="cform">
      <input id="clName" placeholder="Nombre del sistema (ej. ruta80g)">
      <input id="clToken" placeholder="token">
      <button class="btn" onclick="genToken()">Generar token</button>
      <button class="btn primary" onclick="saveClient()">Guardar cliente</button>
    </div>
  </div>
</div>
<script>
{_RENDER_JS}

async function api(path, opts){{
  const r = await fetch(path, opts);
  if(!r.ok) throw new Error(await r.text());
  return r.json();
}}

function fmtAt(h){{ return h && h[0] ? h[0].at : 'sin tickets todavía'; }}

function renderGrid(state){{
  const grid = document.getElementById('grid');
  if(!state.printers.length){{
    grid.innerHTML = '<div class="empty">Sin impresoras virtuales todavía. Agrega una arriba, o simplemente manda un trabajo de impresión con ese nombre — se crea sola.</div>';
    return;
  }}
  grid.innerHTML = state.printers.map(p => {{
    const last = p.history[0];
    return `<div class="pcard">
      <div class="phead">
        <span class="pname">${{esc(p.name)}}</span>
        <div class="pactions">
          <a class="btn" href="/pantalla/${{encodeURIComponent(p.name)}}" target="_blank">Abrir pantalla ↗</a>
          <button class="btn" onclick="testPrint('${{esc(p.name)}}')">Ticket de prueba</button>
          <button class="btn" onclick="clearPrinter('${{esc(p.name)}}')">Limpiar</button>
          <button class="btn danger" onclick="delPrinter('${{esc(p.name)}}')">Eliminar</button>
        </div>
      </div>
      <div class="meta"><span>${{fmtAt(p.history)}}</span>${{p.history.length? `<span class="badge">${{p.history.length}} ticket(s)</span>`:''}}</div>
      ${{last ? `<div class="ticket">${{renderBlocks(last.blocks)}}</div>` : '<div class="empty">Sin tickets todavía</div>'}}
    </div>`;
  }}).join('');
}}

async function refresh(){{
  try{{ renderGrid(await api('/api/state')); }}catch(e){{ /* red caída, se reintenta solo */ }}
}}

async function addPrinter(){{
  const name = document.getElementById('newName').value.trim();
  if(!name) return;
  await api('/api/printers', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{name}})}});
  document.getElementById('newName').value = '';
  refresh();
}}
async function delPrinter(name){{
  if(!confirm('¿Eliminar la impresora virtual "'+name+'"? Se borra su historial de tickets.')) return;
  await api('/api/printers/'+encodeURIComponent(name), {{method:'DELETE'}});
  refresh();
}}
async function clearPrinter(name){{
  await api('/api/printers/'+encodeURIComponent(name)+'/clear', {{method:'POST'}});
  refresh();
}}
async function testPrint(name){{
  await api('/api/test', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{printer:name}})}});
  refresh();
}}

// ---- clientes / tokens ----
function genToken(){{
  const a = new Uint8Array(24); crypto.getRandomValues(a);
  document.getElementById('clToken').value = [...a].map(b=>b.toString(16).padStart(2,'0')).join('');
}}
async function loadClients(){{
  const {{clients}} = await api('/api/clients');
  const tbl = document.getElementById('clientsTbl');
  let t = '<tr><th>Cliente</th><th>Token</th><th></th></tr>';
  for(const c of clients){{
    t += `<tr><td>${{esc(c.name)}}</td><td class="meta">${{c.token?'•••••• (guardado)':'(sin token)'}}</td>
      <td><button class="btn danger" onclick="delClient('${{esc(c.name)}}')">Eliminar</button></td></tr>`;
  }}
  if(!clients.length) t += '<tr><td colspan="3" class="meta">Sin clientes: /print queda abierto en la red local.</td></tr>';
  tbl.innerHTML = t;
}}
async function saveClient(){{
  const name = document.getElementById('clName').value.trim();
  const token = document.getElementById('clToken').value.trim();
  if(!name) return;
  await api('/api/clients', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{name, token}})}});
  document.getElementById('clName').value = ''; document.getElementById('clToken').value = '';
  loadClients();
}}
async function delClient(name){{
  if(!confirm('¿Eliminar el cliente "'+name+'"?')) return;
  await api('/api/clients/'+encodeURIComponent(name), {{method:'DELETE'}});
  loadClients();
}}

document.getElementById('newName').addEventListener('keydown', e=>{{ if(e.key==='Enter') addPrinter(); }});
refresh();
loadClients();
setInterval(refresh, 2000);
</script>
</body></html>"""


def pantalla_page(name: str) -> str:
    safe_title = (name or "").replace("<", "").replace(">", "")
    name_json = json.dumps(name)
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title} — print-screen</title>
<style>
{_TICKET_CSS}
  body{{background:#e5e7eb}}
  header{{position:sticky;top:0;z-index:2}}
  .feed{{max-width:520px;margin:0 auto;padding:18px;display:flex;flex-direction:column;gap:16px}}
  .ticket{{font-size:1rem;box-shadow:0 2px 10px rgba(0,0,0,.08)}}
  .tkwrap .meta{{margin-bottom:4px}}
  .dot{{width:8px;height:8px;border-radius:50%;background:#22c55e;display:inline-block;margin-right:6px;animation:pulse 1.6s infinite}}
  @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
</style>
</head><body>
<header>
  <h1>🖨️ {safe_title}</h1>
  <span class="sub"><span class="dot"></span>en vivo</span>
  <a href="/">← tablero</a>
</header>
<div class="feed" id="feed"><div class="empty">Esperando el primer ticket…</div></div>
<script>
{_RENDER_JS}
function esc2(s){{ return esc(s); }}
const PRINTER = {name_json};

async function refresh(){{
  try{{
    const r = await fetch('/api/state/'+encodeURIComponent(PRINTER));
    const data = await r.json();
    const feed = document.getElementById('feed');
    if(!data.history.length){{ feed.innerHTML = '<div class="empty">Esperando el primer ticket…</div>'; return; }}
    feed.innerHTML = data.history.map(h => `
      <div class="tkwrap">
        <div class="meta"><span>${{esc2(h.at)}}</span><span>${{h.copies>1?('x'+h.copies+' · '):''}}${{esc2(h.source||'')}}</span></div>
        <div class="ticket">${{renderBlocks(h.blocks)}}</div>
      </div>`).join('');
  }}catch(e){{ /* red caída, se reintenta solo */ }}
}}
refresh();
setInterval(refresh, 1500);
</script>
</body></html>"""
