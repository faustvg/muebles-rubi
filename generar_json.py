"""
generar_json.py
----------------
Lee la tabla PRODUCTOS de la base de datos PostgreSQL y escribe un
archivo productos.json que el sitio público (GitHub Pages) puede leer.

Este es el "puente" entre la base de datos privada y el sitio estático.
Credenciales se leen de un archivo .env (que NO se sube a GitHub).
"""

import os
import json
import psycopg
from dotenv import load_dotenv

# 1. Cargar las credenciales desde el archivo .env
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# 2. Conectarse a la base de datos y leer los productos visibles
def obtener_productos():
    # La cadena de conexión usa las variables del .env
    with psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, nombre, descripcion, precio_base,
                       fotos, color, material
                FROM productos
                WHERE visible_en_sitio = true
                ORDER BY nombre;
                """
            )
            filas = cur.fetchall()

    # 3. Convertir cada fila en un diccionario (clave: valor)
    productos = []
    for fila in filas:
        productos.append({
            "id": fila[0],
            "nombre": fila[1],
            "descripcion": fila[2],
            "precio": float(fila[3]) if fila[3] is not None else 0,
            "fotos": fila[4] if fila[4] is not None else [],
            "color": fila[5],
            "material": fila[6],
        })

    return productos


# 4. Escribir la lista de productos a productos.json
def main():
    productos = obtener_productos()

    with open("productos.json", "w", encoding="utf-8") as f:
        json.dump(productos, f, ensure_ascii=False, indent=2)

    print(f"Listo: {len(productos)} productos escritos en productos.json")


if __name__ == "__main__":
    main()