from contextlib import asynccontextmanager
from typing import Optional
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel

load_dotenv()

# ---------------------------------------------------------------------------
# Connection pool
# ---------------------------------------------------------------------------

CONNINFO = (
    f"host={os.getenv('DB_HOST')} "
    f"port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.getenv('DB_NAME')} "
    f"user={os.getenv('DB_USER')} "
    f"password={os.getenv('DB_PASSWORD')}"
)

pool: AsyncConnectionPool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = AsyncConnectionPool(conninfo=CONNINFO, min_size=1, max_size=5)
    yield
    await pool.close()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Galerías Rubí API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to your domain in production
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# DB dependency
# ---------------------------------------------------------------------------

async def get_db():
    async with pool.connection() as conn:
        yield conn


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class Categoria(BaseModel):
    id: int
    nombre: str
    descuento_pct: float


class Producto(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    precio: float
    descuento_pct: Optional[float]   # effective: product-level overrides category-level
    fotos: list[str]
    color: Optional[str]
    material: Optional[str]
    categoria_id: Optional[int]
    categoria: Optional[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/categorias", response_model=list[Categoria])
async def listar_categorias(conn=Depends(get_db)):
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT id, nombre, descuento_pct FROM categorias ORDER BY nombre"
        )
        rows = await cur.fetchall()
    return [
        {"id": r[0], "nombre": r[1], "descuento_pct": float(r[2] or 0)}
        for r in rows
    ]


@app.get("/productos", response_model=list[Producto])
async def listar_productos(
    categoria_id: Optional[int] = Query(None, description="Filtrar por ID de categoría"),
    conn=Depends(get_db),
):
    """
    Returns all visible products. Pass ?categoria_id=<n> to filter by category.
    The effective discount is the product-level value when set, otherwise the
    category-level value (mirrors the COALESCE logic in the DB design).
    """
    sql = """
        SELECT
            p.id,
            p.nombre,
            p.descripcion,
            p.precio_base,
            COALESCE(p.descuento_pct, c.descuento_pct) AS descuento_efectivo,
            p.fotos,
            p.color,
            p.material,
            p.categoria_id,
            c.nombre AS categoria
        FROM productos p
        LEFT JOIN categorias c ON c.id = p.categoria_id
        WHERE p.visible_en_sitio = true
    """
    params: list = []
    if categoria_id is not None:
        sql += " AND p.categoria_id = %s"
        params.append(categoria_id)
    sql += " ORDER BY p.nombre"

    async with conn.cursor() as cur:
        await cur.execute(sql, params)
        rows = await cur.fetchall()

    return [_row_to_producto(r) for r in rows]


@app.get("/productos/{producto_id}", response_model=Producto)
async def obtener_producto(producto_id: int, conn=Depends(get_db)):
    sql = """
        SELECT
            p.id,
            p.nombre,
            p.descripcion,
            p.precio_base,
            COALESCE(p.descuento_pct, c.descuento_pct) AS descuento_efectivo,
            p.fotos,
            p.color,
            p.material,
            p.categoria_id,
            c.nombre AS categoria
        FROM productos p
        LEFT JOIN categorias c ON c.id = p.categoria_id
        WHERE p.id = %s
    """
    async with conn.cursor() as cur:
        await cur.execute(sql, (producto_id,))
        row = await cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    return _row_to_producto(row)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_producto(r) -> dict:
    return {
        "id": r[0],
        "nombre": r[1],
        "descripcion": r[2],
        "precio": float(r[3] or 0),
        "descuento_pct": float(r[4]) if r[4] is not None else None,
        "fotos": r[5] or [],
        "color": r[6],
        "material": r[7],
        "categoria_id": r[8],
        "categoria": r[9],
    }
