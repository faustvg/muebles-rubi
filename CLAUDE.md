# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

**Muebles Rubí** is a static landing page for a Mexican furniture craftsman, served via GitHub Pages. A PostgreSQL database (local dev on Windows, production on a Hetzner VPS running Ubuntu 24.04) stores the product catalog and order records. A Python script bridges the private DB to the public static site.

## Commands

### Python environment

```bash
# Activate virtual environment (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Generate the public product catalog from the database
python generar_json.py
```

### Database (psql)

```bash
# Load the schema (run once to initialize)
psql -U <user> -d <dbname> -f schema.sql

# Or from inside psql
\i 'D:/Faus_/galerias_rubi/schema.sql'
```

### Environment variables

Create a `.env` file (never commit it) with:

```
DB_HOST=
DB_PORT=
DB_NAME=
DB_USER=
DB_PASSWORD=
```

## Architecture

### Data flow

```
PostgreSQL DB  →  generar_json.py  →  productos.json  →  index.html (GitHub Pages)
```

`generar_json.py` is the publish step: run it after updating products in the DB to regenerate `productos.json`, then commit and push so the static site picks up the changes.

### Database schema (`schema.sql`)

Five tables in dependency order:

| Table | Purpose |
|---|---|
| `categorias` | Product categories; `descuento_pct` applies to all products in the category |
| `proveedores` | Supplier names, linked per product |
| `productos` | Master catalog. `fotos TEXT[]` stores URL/path array (first = main image). `visible_en_sitio` gates what goes into `productos.json`. Product-level `descuento_pct` overrides category-level; `NULL` means inherit. |
| `notas` | Order header (quote/order/delivered). Client data is **denormalized** here (`nombre_cliente`, `telefono`) — no separate clients table. `folio` is a text primary key (paper receipt number, e.g. `'0986'`). `resta` is a generated column (`total - anticipo`). |
| `partidas` | Order line items (many-to-many bridge between `notas` and `productos`). `importe` is generated (`cantidad * precio_unitario`). `producto_id` is nullable to allow one-off items not in the catalog. Cascades delete from `notas`. |

> **Note:** `relational_diagramm.md` shows an older draft with a separate `CLIENTES` table. The authoritative schema is `schema.sql`.

### Frontend (`index.html`)

Single self-contained file — all CSS and JS are inline, no build step, no framework.

- **Catalog data** is currently hardcoded in the `products` JS array at the bottom of the file. The intent is for the site to eventually fetch `productos.json` from the DB bridge instead.
- **WhatsApp number** placeholder is `527XXXXXXXXX` — appears in three places: `WA_NUMBER` constant, the contact section link, and the footer/bubble links. Replace all three with the real number (country code + number, no `+` or spaces).
- **Sections:** `#inicio` (hero) → `#destacados` → `#nosotros` → `#coleccion` (filterable grid) → `#amedida` (process steps) → `#testimonios` → `#contacto` (form + info).
- Form submission (`handleFormSubmit`) and card clicks (`openWhatsApp`) both open a pre-filled WhatsApp URL — there is no backend form handler.
