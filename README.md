# print-screen · Impresora virtual para pruebas

Se instala en la **PC que tiene pantalla** — a diferencia de `print-agent`
(que corre headless en la Raspberry Pi y sí manda bytes a impresoras reales
por SMB/RAW/LPR), este servicio no imprime nada: muestra en el navegador lo
que se habría impreso.

Expone **el mismo contrato HTTP que print-agent** (`POST /print`,
`GET /printers`, `GET /health`). Para probar un sistema (Ruta80G,
horno-ruta80, caja-ruta80, etc.), cambia su `print_agent_url` para que
apunte acá en vez de al agente real — no hace falta tocar ni una línea de
código de negocio. Para volver a imprimir de verdad, se vuelve a cambiar
esa URL al agente real.

## Uso

```bash
docker compose up -d --build
```

Abre `http://<IP-de-esta-PC>:8120`:

- **Tablero** (`/`) — da de alta impresoras virtuales (o se crean solas la
  primera vez que llega un trabajo con ese nombre) y muestra el último
  ticket de cada una en miniatura.
- **Pantalla dedicada** (`/pantalla/<nombre>`) — vista grande tipo KDS
  (como las pantallas de cocina de KFC), pensada para abrir en su propia
  ventana del navegador y dejarla fija en el monitor; se actualiza sola
  con cada ticket nuevo.

En el sistema que quieras probar, apunta su `print_agent_url` a
`http://<IP-de-esta-PC>:8120` y usa como "nombre de impresora" el mismo
nombre que le des acá (ej. "Barra", "Caja", "Brasa").

## Notas

- Los tickets recibidos se guardan en memoria (se pierden al reiniciar el
  contenedor) — es una herramienta de vista previa, no un archivo de
  auditoría. Los NOMBRES de impresoras creadas sí se persisten en
  `./data/printers.json`.
- Solo entiende trabajos por `blocks` (el formato que ya usan todos los
  sistemas de este proyecto). Un trabajo `raw.escpos_base64` (nadie lo usa
  hoy) se muestra como aviso, no se decodifica.
