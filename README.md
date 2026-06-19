# Galerías Rubí — Sistema de catálogo y pedidos

Sitio web y API para **Muebles Rubí**, taller familiar de carpintería artesanal con más de 30 años de tradición en San Pedro Tultepec, Lerma, Estado de México. Fabrican muebles de pino macizo y chapa de parota por encargo y de catálogo.

---

## Contexto del negocio

El taller opera con dos sucursales sobre la Av. de los Muebles y atiende principalmente por WhatsApp. Los pedidos se registran en talonarios de papel (folios físicos). El proceso de venta es:

1. El cliente elige un modelo del catálogo o describe un diseño a medida.
2. El vendedor genera una **nota** (cotización/pedido) con folio físico y anticipo.
3. El taller fabrica en 7–15 días hábiles.
4. Se entrega y se cobra el saldo restante.

El sistema digitaliza ese flujo sin reemplazarlo: el folio de papel sigue siendo la referencia principal.

---

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | HTML + CSS + JS inline · sin framework · GitHub Pages |
| API | FastAPI · Python 3.12 · uvicorn |
| Base de datos | PostgreSQL (local Windows en desarrollo · VPS Hetzner Ubuntu 24.04 en producción) |
| Driver DB | psycopg 3 (psycopg3) + psycopg-pool |
| Puente estático | `generar_json.py` → `productos.json` |
| Secretos | `python-dotenv` · archivo `.env` (nunca en git) |

---

## Arquitectura

```
┌──────────────────────────────────────────────────────────┐
│                     GitHub Pages                         │
│                      index.html                          │
│          (HTML · CSS · JS todo en un solo archivo)       │
└────────────────────────┬─────────────────────────────────┘
                         │ GET /productos  (FastAPI)
                         │      ó
                         │ productos.json  (estático)
                         ▼
┌──────────────────────────────────────────────────────────┐
│               FastAPI  (main.py)                         │
│  /categorias · /productos · /productos/{id}              │
│  AsyncConnectionPool  min=1  max=5                       │
└────────────────────────┬─────────────────────────────────┘
                         │ psycopg3 async
                         ▼
┌──────────────────────────────────────────────────────────┐
│                   PostgreSQL                             │
│  categorias · proveedores · productos                    │
│  notas · partidas                                        │
└──────────────────────────────────────────────────────────┘
                         ▲
              generar_json.py  (script manual)
              Lee productos visibles y escribe
              productos.json para el sitio estático.
              Se ejecuta tras cada cambio en el catálogo.
```

### Dos modos de servir el catálogo

| Modo | Cómo funciona | Cuándo usarlo |
|---|---|---|
| **Estático** | `generar_json.py` genera `productos.json`, se sube a GitHub Pages | Deploy simple, sin servidor |
| **API** | `uvicorn main:app` sirve datos en tiempo real con filtros | Con VPS activo en producción |

---

## Instalación

```bash
# 1. Crear y activar entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / Mac

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Crear el archivo de credenciales
cp .env.example .env         # editar con los datos reales
```

### `.env`

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=galerias_rubi
DB_USER=
DB_PASSWORD=
```

### Cargar el esquema

```bash
psql -U <usuario> -d galerias_rubi -f schema.sql
```

### Ejecutar la API

```bash
uvicorn main:app --reload
# Documentación interactiva: http://localhost:8000/docs
```

### Generar el JSON estático

```bash
python generar_json.py
# Escribe productos.json con todos los productos visibles
```

---

## Endpoints de la API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/categorias` | Lista todas las categorías con su descuento |
| `GET` | `/productos` | Lista productos visibles (`?categoria_id=n` para filtrar) |
| `GET` | `/productos/{id}` | Detalle de un producto; 404 si no existe |

El campo `descuento_pct` en `/productos` refleja el descuento efectivo: el del producto si está definido, o el de su categoría si no (`COALESCE`).

---

## Esquema de base de datos

```
categorias ──< productos ──< partidas >── notas
proveedores──<
```

### Tablas

#### `categorias`
Salas, comedores, roperos, etc. El campo `descuento_pct` aplica a toda la categoría; cambiar un número aquí afecta a todos sus productos automáticamente.

#### `proveedores`
Nombre del proveedor externo de piezas ya fabricadas (salas de proveedor, sillones). Se almacena una vez y se enlaza desde `productos`.

#### `productos`
Catálogo base. Cada fila es un modelo; las piezas a medida se registran también aquí con `existencias = 0`. El campo `visible_en_sitio` controla qué sale en el sitio y en el JSON público.

#### `notas`
Encabezado de la transacción: cotización, pedido o entrega. Los datos del cliente se guardan aquí de forma aplanada (`nombre_cliente`, `telefono`) sin tabla separada de clientes.

#### `partidas`
Líneas de cada nota. Tabla puente entre `notas` y `productos`. Un registro = una pieza con su precio real cotizado. `ON DELETE CASCADE` desde `notas`: borrar la nota elimina sus partidas.

---

## Decisiones de diseño de la base de datos

### `folio` es `VARCHAR`, no `SERIAL`

Los vendedores usan talonarios de papel numerados. Los folios pueden empezar con ceros (`'0042'`, `'0986'`) y deben coincidir exactamente con el número impreso en el recibo físico. Un entero descartaría esos ceros y rompería la correspondencia con el papel.

### `resta` es una columna generada

```sql
resta NUMERIC(10,2) GENERATED ALWAYS AS (total - anticipo) STORED
```

Si fuera una columna normal, cualquier actualización de `total` o `anticipo` obligaría a recordar actualizar también `resta`. Una columna generada hace que sea imposible que se desincronice: la base de datos la recalcula sola y no se puede escribir directamente.

### `fotos` es `TEXT[]` (array de PostgreSQL)

Las alternativas eran una tabla separada `fotos(id, producto_id, url, orden)` o serializar las rutas en un campo de texto. El array de PostgreSQL es el punto medio: evita el JOIN extra para una relación simple y ordenada (la primera foto es siempre la imagen principal), sin sacrificar la posibilidad de indexar o filtrar por contenido si algún día hace falta.

### `producto_id` es nullable en `partidas`

Permite registrar una pieza completamente a medida que no existe en el catálogo, solo con descripción libre y precio. Sin esto, habría que crear un producto "fantasma" en el catálogo para cada encargo único.

### Sin tabla `CLIENTES`

Los clientes de este negocio rara vez repiten compra con el mismo folio de referencia. Mantener una tabla separada añadiría un JOIN en cada consulta de notas sin beneficio práctico real. Los datos de contacto (`nombre_cliente`, `telefono`) se guardan directamente en `notas`. La decisión es reversible si el negocio crece.

### `descuento_pct` en dos niveles

`productos.descuento_pct` sobreescribe a `categorias.descuento_pct`; si es `NULL`, hereda el de la categoría. El valor `0` significa explícitamente "sin descuento aunque la categoría tenga". Esto permite hacer promociones por categoría entera con un solo cambio.

---

## Estructura del proyecto

```
galerias_rubi/
├── index.html          # Sitio completo (CSS + JS inline, sin build)
├── main.py             # API FastAPI
├── generar_json.py     # Puente DB → JSON estático
├── schema.sql          # DDL completo de PostgreSQL
├── productos.json      # Generado; no editar a mano
├── requirements.txt
├── .env                # Credenciales (no en git)
├── assets/             # Logo
└── img/                # Fotos propias de productos
```
