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

Abre `http://<IP-de-esta-PC>:8120` — la primera vez te lleva a `/setup`
para crear tu propio usuario administrador (igual que horno-ruta80 /
Ruta80G: se pide una sola vez, nadie te da una contraseña generada al
azar).

- **Tablero** (`/`) — da de alta impresoras virtuales (o se crean solas la
  primera vez que llega un trabajo con ese nombre) y muestra el último
  ticket de cada una en miniatura, con un botón para mandarle un ticket de
  prueba sin depender de ningún sistema externo.
- **Pantalla dedicada** (`/pantalla/<nombre>`) — vista grande tipo KDS
  (como las pantallas de cocina de KFC), pensada para abrir en su propia
  ventana del navegador y dejarla fija en el monitor; se actualiza sola
  con cada ticket nuevo.

En el sistema que quieras probar, apunta su `print_agent_url` a
`http://<IP-de-esta-PC>:8120` y usa como "nombre de impresora" el mismo
nombre que le des acá (ej. "Barra", "Caja", "Brasa").

## Seguridad

Dos capas de autenticación:

1. **Tablero, pantallas y API de administración** (`/`, `/pantalla/*`,
   `/api/*`): HTTP Basic contra el usuario/contraseña que creas en
   `/setup` en el primer arranque (guardado con hash PBKDF2 en
   `./data/admin.json`, mismo esquema que horno-ruta80/Ruta80G). Mientras
   no exista ese usuario, todo redirige a `/setup`.
2. **`POST /print`** (lo que usan los sistemas que imprimen): token por
   cliente. Se gestiona desde el tablero, sección "Clientes / tokens" (un
   nombre + token por cada sistema, header `Authorization: Bearer
   <token>`). Si no configuras ningún cliente, el endpoint queda abierto en
   la red local.

## Notas

- Los tickets recibidos se guardan en memoria (se pierden al reiniciar el
  contenedor) — es una herramienta de vista previa, no un archivo de
  auditoría. Los NOMBRES de impresoras creadas sí se persisten en
  `./data/printers.json`.
- Solo entiende trabajos por `blocks` (el formato que ya usan todos los
  sistemas de este proyecto). Un trabajo `raw.escpos_base64` (nadie lo usa
  hoy) se muestra como aviso, no se decodifica.
