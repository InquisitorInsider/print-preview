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

- **Pantallas** (`/`) — lista de impresoras virtuales; cada una abre su
  propia pantalla dedicada (`/pantalla/<nombre>`), tipo KDS (como las
  pantallas de cocina de KFC): se abre en su propia ventana del navegador,
  se actualiza sola con cada ticket nuevo, y cada comanda se puede
  **Aceptar** y luego **Completar**.
- **Configuración** (`/configuracion`, solo admin) — todo lo que toca
  impresoras vive acá, en pestañas: alta/baja de impresoras virtuales +
  ticket de prueba, Clientes/tokens, y Usuarios.

En el sistema que quieras probar, apunta su `print_agent_url` a
`http://<IP-de-esta-PC>:8120` y usa como "nombre de impresora" el mismo
nombre que le des en Configuración → Impresoras (ej. "Barra", "Caja",
"Brasa").

## Seguridad

Tres capas:

1. **Usuarios, con dos roles** (HTTP Basic): el primero se crea en
   `/setup` en el primer arranque, siempre como **admin**. Desde
   Configuración → Usuarios el admin da de alta más usuarios:
   - **admin**: Configuración completa + pantallas de comandas.
   - **estándar**: solo entra a las pantallas de comandas, a
     verlas y aceptarlas/completarlas — sin acceso a Configuración.
   Contraseñas con hash PBKDF2 en `./data/users.json` (mismo esquema que
   horno-ruta80/Ruta80G). No se puede eliminar al único administrador que
   quede.
2. **`/configuracion` y su API** (`/api/printers`, `/api/clients`,
   `/api/users`): solo usuarios con rol admin (403 para estándar).
3. **`POST /print`** (lo que usan los sistemas que imprimen): token por
   cliente, gestionado desde Configuración → Clientes y tokens (un
   nombre + token por cada sistema, header `Authorization: Bearer
   <token>`). Si no configuras ningún cliente, el endpoint queda abierto en
   la red local.

## Notas

- Los tickets recibidos se guardan en memoria (se pierden al reiniciar el
  contenedor) — es una herramienta de vista previa, no un archivo de
  auditoría. Los NOMBRES de impresoras/usuarios/clientes sí se persisten en
  `./data/*.json`.
- Solo entiende trabajos por `blocks` (el formato que ya usan todos los
  sistemas de este proyecto). Un trabajo `raw.escpos_base64` (nadie lo usa
  hoy) se muestra como aviso, no se decodifica.
