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
```bash
source .venv/bin/activate
python scripts/00_snapshot_portal.py   # siniestros del portal ANSV (solo lectura) -> data/raw/portal/
python scripts/00_manifiesto.py        # congela/verifica SHA-256 de data/raw/ (docs/manifiesto_raw.csv)
python scripts/01_equipos.py           # equipos operativos + zonas (data/processed/equipos_sast.gpkg)
python scripts/02_comparendos.py       # lectura sin datos personales, duplicados, medio
python scripts/03_geocodificar.py      # ubicación de comparendos (~1,5 min)
python scripts/04_siniestros.py        # fallecidos/lesionados, cobertura del portal
python scripts/05_indicadores.py       # tabla larga equipo × mes × indicador × medio
python scripts/06_reportes.py          # Excel ANSV + HTML en outputs/
```
Los insumos de `data/raw/` los copia Santiago (`docs/ingesta.md`). `SAST_RAW=<carpeta>` corre el
pipeline contra otra carpeta de insumos (ensayos), sin tocar `data/raw/`.

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

Reglas de geocodificación (2026-10-06, `src/sast/geocodificacion.py`), cada una motivada por un caso
real de los datos:
7. **Diagonal ausente de la referencia → calle homónima** («DIAGONAL 16» → CL 16): el IGAC rotula
   «CALLE 16 B (DIAG. 16B)» y el equipo 041 es «DIAGONAL 16 - CARRERA 12» en el Excel y «CALLE 16 -
   CARRERA 12» en sus comparendos.
8. **Cruce con hueco ≤ 100 m** (`cruce_hueco`): vías que en IGAC+OSM no se tocan por poco (CR 16 ×
   CL 20 a 49 m, 1.530 comparendos). El original solo llegaba a 30 m.
9. **Dirección oficial de un equipo → su coordenada** si la referencia no da el cruce a ≤ 150 m
   (`punto_equipo`). Solo aplica a «TRANSVERSAL 12 - CALLE 20B» (032), cuyo cruce teórico queda a 265 m.
10. **Placa sobre diagonal o transversal** («DIAGONAL 21 # 18B-6»): se infiere la vía generadora
    (DG → CR, luego TV; TV → CL, luego DG).
11. **Control de las direcciones SAST:** las 8 direcciones de los comparendos SAST caen en la zona de
    su propio equipo (verificado el 2026-10-06). Es un control débil, no una prueba independiente
    (revisor-datos): en 041/042 y 021/022 las zonas se solapan y la dirección cae en ambas; en 032 es
    circular (`punto_equipo` usa la coordenada del propio equipo); el 071 no tiene registros SAST.
12. **Duplicados:** por (número, código). Mismo número con dos códigos = dos infracciones. Del par
    repetido se conserva la fila con coordenada útil y luego la de resolución más completa.
    La coordenada (1, 1) es un marcador de «sin coordenada».
13. **Placa sin «#»** («CARRERA 16 20-27»): se inserta el «#» antes de leer (`marcar_placa`). Sin
    esto, el 76–92 % de la fotodetección previa de 2024 quedaba sin ubicar (revisor-datos).
14. **Placas en el campo dirección** se enmascaran como `<PLACA>` al leer; las filas leídas se
    concilian contra el pie «Total:» de cada archivo del export.

Decisiones tras la auditoría del revisor-datos (Santiago, 2026-10-06):
15. **Criterio espacial oficial mixto** (reemplaza la decisión 3): comparendos ubicados por dirección
    (punto sobre el eje) → polígono estricto; siniestros y comparendos ubicados por GPS → +15 m.
    Motivo: con +15 m para todo, el 041 absorbía entero el cruce vecino Cra 13 × Cl 16 (C02 533 → 1.304).
    Todo estricto y todo +15 m se informan como sensibilidad.
16. **Lesionados se reportan con salvedad** en cada celda de Observaciones y en la metodología
    (registro del portal no homogéneo entre 2023–2025 y 2026). Fallecidos también llevan salvedad
    por el cambio de fuentes.
17. **Universo del export:** según Santiago, incluye todos los comparendos impuestos, también los
    pagados, pese al título «Pendientes Notificación».
18. **Revocados, anulados y absueltos cuentan:** el indicador mide comparendos impuestos.
