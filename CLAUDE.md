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
Acordadas con Santiago el 2026-10-06:
1. **Período:** el HTML muestra la serie mensual de ene-2023 a sep-2026. El Excel
   ANSV cubre los 36 meses de sep-2023 a ago-2026 (Año 1, 2 y 3; inicio de
   operación el 2-sep-2026). Los comparendos generados por las cámaras SAST se
   excluyen de la línea base y se informan aparte.
2. **Fotodetección previa no SAST** (2024–2026, casi todo C02): entra en la línea
   base, pero siempre desglosada por medio (agente / fotodetección previa).
3. **Criterio espacial:** zona de influencia con buffer de 15 m (calculado en
   EPSG:9377). La cifra con el polígono estricto se informa como sensibilidad.
4. **Coordenada contra dirección:** manda la dirección geocodificada. Si
   discrepan en más de 100 m, el registro se marca. La coordenada GPS se usa solo
   cuando la dirección no se puede ubicar y la coordenada cae en el perímetro urbano.
5. **Solapes:** un evento que cae en zonas de dos equipos cuenta para cada uno,
   porque la ANSV pide el dato por equipo. El total por punto se calcula sin doble
   conteo.
6. **Fallecidos y lesionados** se cuentan como personas (`cantidad_muertos`,
   `cantidad_heridos`), no como siniestros.
