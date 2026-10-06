# CLAUDE.md — sast-valledupar

## Este proyecto
- **Objetivo:** calcular y sostener los indicadores de seguridad vial que la STTV
  reporta a la ANSV por cada equipo SAST en operación. Primera entrega: línea base
  (fallecidos, lesionados y comparendos por código en la zona de influencia).
- **Datos:**
  - `Equipos SAST Actualizado.xlsx` (hoja `Equipos SAST`): equipos, puntos y
    códigos de infracción aprobados por equipo.
  - `Zona de influencia.shp` (SIG Equipos SAST): un polígono por equipo, campo `Equipo`.
  - Siniestros: feature layer "Siniestralidad Valledupar" del portal ANSV
    (item `7ec1893e94144a33807dc967455955b2`), solo lectura.
  - Comparendos 2023–2026 (export HTML-.xls del sistema de comparendos):
    **contienen cédula, nombre y placa** → nunca salen de `data/raw/`.
- **Destino:** reporte a la plataforma ANSV (fotodeteccion-app.ansv.gov.co) y
  evidencia para estudios técnicos (Proyecto 2, con ficha de procedencia).
- **CRS:** EPSG:4326 para almacenar; EPSG:9377 para toda operación métrica
  (buffers, distancias).

## Estructura
- `config/` — equipos operativos, fechas de inicio, códigos aprobados.
- `data/raw/` — insumos sin modificar (no versionado). `data/processed/` — derivados sin datos personales.
- `src/sast/` — funciones (lectura, ubicación, indicadores, reportes).
- `scripts/NN_*.py` — pipeline numerado, se corre en orden.
- `outputs/` — HTML y Excel de entrega. `docs/` — metodología y fichas.

## Comandos frecuentes
(se completa al construir el pipeline)

## Decisiones tomadas
