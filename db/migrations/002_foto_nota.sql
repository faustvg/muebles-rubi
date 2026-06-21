-- ============================================================
--  Migración 002 — foto_nota
--  Agrega una columna a NOTAS para guardar la foto del recibo
--  de papel (la nota física), si el usuario la quiere subir.
--
--  foto_nota: ruta/URL a la imagen de la nota de papel. NULLABLE
--  (la mayoría de las notas, sobre todo las históricas, no la
--  tendrán). El archivo vive en disco; aquí solo se guarda la ruta.
--  Una nota tiene UNA foto de sí misma (a diferencia de productos,
--  que tienen un array de fotos), por eso es TEXT y no TEXT[].
--
--  Sienta las bases para la futura función de "subir foto de la
--  nota y leerla automáticamente".
-- ============================================================

ALTER TABLE notas
    ADD COLUMN foto_nota TEXT;