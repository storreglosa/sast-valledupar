# Ficha de procedencia — Línea base de indicadores de seguridad vial, equipos SAST en operación

- **Resultado:** indicadores de línea base por equipo SAST (021, 022, 031, 032, 041, 042, 051, 052, 071)
  y por mes, dentro de la zona de influencia de cada equipo:
  - fallecidos y lesionados (personas);
  - comparendos por código de infracción aprobado para el equipo, desglosados en agentes y
    fotodetección previa no SAST.

  Entregables (no versionados; regenerables con el pipeline):

  | Archivo | SHA-256 |
  |---|---|
  | `outputs/2026-10-04_sttv_linea-base-sast.xlsx` (formato ANSV, una hoja por equipo + anexos) | `3a2a76aa60955523dc2e2d00bc7764bcfb213e0abd173f84f9715d24b4e7c7a8` |
  | `outputs/2026-10-04_sttv_linea-base-sast.html` (informe) | `e5eabd1fa00d9858e149828c5fc61f363a91c75bc0fd1552a40b8c8665edbed4` |
  | `outputs/tables/indicadores_largo.csv` (equipo/punto × mes × indicador × medio × criterio) | `3ef7baffcdd024d70c6eb47d78896e3ec400fec50f2ff4713e38d11f5491b4c9` |
  | `outputs/tables/sensibilidad_ubicacion.csv` | `725d81c3b280df55670a46e44f28222c539b6ab6dca641a1829e0abfd59a3e8f` |
  | `outputs/tables/siniestros_en_zona_revision.csv` | `9078a66936fd3317b18a511163659041812fd5fee9c68386f015ec326213c4a0` |

  Totales por punto en la línea base, criterio oficial, sin doble conteo entre zonas solapadas:

  | Solicitud (punto) | C02 | C03 | C24 | C32 | C35 | D02 | D04 | D05 | Fallecidos | Lesionados |
  |---|---|---|---|---|---|---|---|---|---|---|
  | 2 Los Manguitos | 12 | 1 | 2 | 3 | 8 | 7 | 21 | 23 | 0 | 0 |
  | 3 Mercado Público | 478 | 0 | 18 | 3 | 24 | 33 | 4 | 4 | 3 | 6 |
  | 4 Colegio Loperena | 1.422 | 0 | 49 | 13 | 84 | 92 | 84 | 14 | 0 | 1 |
  | 5 La Viña | 3.028 | 2 | 12 | 13 | 192 | 167 | 11 | 6 | 0 | 3 |
  | 7 U. Área Andina | 4 | 0 | 11 | 3 | 8 | 8 | 0 | 1 | 0 | 1 |

  C29 da 0 en los puntos donde está aprobado (2). La D03 del punto 7 está en su hoja de equipo.

- **Fuente de datos:**

  | Insumo | Origen | Corte |
  |---|---|---|
  | Comparendos | Sistema de comparendos de la STTV, reporte «Comparendos Pendientes Notificacion»: 4 archivos HTML-.xls en un zip entregado por la STTV. Según Santiago incluye todos los comparendos impuestos, también los pagados. | 2026-10-04 |
  | Siniestros y víctimas | Portal ArcGIS Enterprise de la ANSV, item `7ec1893e94144a33807dc967455955b2` «Siniestralidad Valledupar» (`…/Siniestralidad_Valledupar/FeatureServer/0` y `/2`). Snapshot de solo lectura: 3.953 siniestros, 6.152 víctimas. | 2026-10-06 12:04 |
  | Equipos y códigos aprobados | «Equipos SAST Actualizado.xlsx», STTV (carpeta 06. Equipos SATS) | archivo del 2026-10-06 |
  | Zonas de influencia | `Zona de influencia.shp`, SIG de equipos SAST de la STTV | archivo del 2026-10-06 |
  | Referencia vial para geocodificar | Nomenclatura vial urbana IGAC 2021 (GDB del POT de Valledupar) y red vial OSM del repo red-vial-valledupar | OSM 2026-08-05 |

  SHA-256 de cada insumo: `docs/manifiesto_raw.csv` y `docs/pot_procedencia.csv`.

- **Periodo cubierto:**
  - Línea base en formato ANSV: sep-2023 a ago-2026, 36 meses (Año 1, 2 y 3).
  - Serie del informe HTML: ene-2023 a sep-2026.
  - El inicio de operación (2-sep-2026) se tomó del formulario ANSV de un equipo y **no está
    confirmado por equipo**.

- **CRS:**
  - Fuentes: zonas y puntos de equipos en EPSG:4326. El portal guarda en Web Mercator (102100) y
    se consultó con `out_sr=4326`. La nomenclatura del POT viene en EPSG:3116 y se transformó a
    EPSG:9377. La red OSM está en EPSG:4326.
  - Todas las operaciones métricas (buffers, cruces, distancias, áreas) se hicieron en
    **EPSG:9377 (MAGNA-SIRGAS / Origen-Nacional, CTM12)**.
  - Resultados geográficos (mapa, `equipos_sast.gpkg`) en EPSG:4326.

- **Transformaciones:**
  - **Comparendos:**
    - Se leyeron 146.626 filas, que cuadran con la suma de los pies «Total:» de los 4 archivos.
    - Cédula, nombre, apellido, tipo de documento y placa se descartaron en la lectura.
    - 4 placas escritas en el campo de dirección se enmascararon.
    - Se apartaron 242 duplicados por (número, código) y quedaron 146.384. En 110 pares la fecha,
      la dirección o el medio no coincidían; se conservó la fila con coordenada útil.
    - 102 comparendos tienen dos códigos y se cuentan ambos.
  - **Medio:**
    - Agente: 88.336.
    - Fotodetección previa no SAST: 52.339.
    - Cámaras SAST: 5.709. Se excluyen de la línea base; 1.410 son anteriores al 2-sep-2026 y se
      tratan como pruebas.
  - **Código «F»:** 240 registros fuera de toda lista aprobada.
  - **Revocados, anulados y absueltos:** se cuentan, porque el indicador mide comparendos impuestos.
  - **Ubicación:**
    - Manda la dirección, geocodificada por cruce o placa sobre los ejes IGAC + OSM, con las reglas
      7–10 y 13 de `CLAUDE.md`. El GPS solo se usa si la dirección no da un punto.
    - Resultado: 95.073 por dirección, 991 por dirección con desempate por GPS, 37.473 por GPS y
      12.847 no ubicables.
    - En la línea base: agentes 7.808 y fotodetección previa 2.806 no ubicables.
    - GPS frente a dirección: mediana 102 m; el 51 % discrepa más de 100 m.
  - **Siniestros:**
    - 111 sin `cantidad_muertos` y 3 sin `cantidad_heridos` se cuentan como 0.
    - 3 no tienen coordenada utilizable.
    - 12 siniestros difieren de la tabla de víctimas; se usa `cantidad_*`.
  - **Asignación a zonas (criterio oficial mixto, decisión 15):**
    - Comparendos ubicados por dirección: polígono estricto.
    - Siniestros y comparendos ubicados por GPS: polígono + 15 m.
    - Como sensibilidad se publican todo estricto y todo +15 m.
    - Un evento en zonas solapadas cuenta para cada equipo; los totales por punto no tienen doble
      conteo.
  - **Siniestros en zona:** 11 en la serie (10 en la línea base), 4 con posible gemelo.
  - **Controles:**
    - Las celdas del Excel coinciden con la tabla larga.
    - Las 8 direcciones de los comparendos SAST caen en la zona de su equipo. Es un control débil,
      porque varias zonas se solapan y la del 032 es circular.
    - Auditoría del revisor-datos (2026-10-06) y re-verificación: «apto con salvedades».

- **Salvedades para el uso como evidencia** (detalle en `docs/metodologia.md`):
  1. La línea base es un piso. La incertidumbre de ubicación es mayor que el ancho de las zonas, así
     que las cifras por equipo son un orden de magnitud.
  2. El registro de lesionados del portal no es homogéneo: 7–9 por mes en el municipio en 2023–2025
     frente a unos 29 en 2026. Las fuentes de fallecidos también cambian entre años.
  3. Los fallecidos y lesionados del punto 3 no deben citarse hasta revisar a mano
     `siniestros_en_zona_revision.csv`.
  4. La fecha de inicio y el id ANSV de cada equipo están pendientes. El 071 no registra
     comparendos SAST.

- **Script/notebook:**
  - Comandos: `scripts/00_snapshot_portal.py`, `00_manifiesto.py`, `01_equipos.py`,
    `02_comparendos.py`, `03_geocodificar.py`, `04_siniestros.py`, `05_indicadores.py`,
    `06_reportes.py`.
  - Funciones en `src/sast/`; reglas en `CLAUDE.md` (decisiones 1–18) y `docs/metodologia.md`.
  - Commit `0f04824330d56bc4f82fc5100fb2822716631acb` (0f04824). El repo es
    `~/Claude_code/sast-valledupar` y no tiene remoto.

- **Generado:** 2026-10-06 | **Validado por:** pendiente — lo confirma Santiago Torreglosa
