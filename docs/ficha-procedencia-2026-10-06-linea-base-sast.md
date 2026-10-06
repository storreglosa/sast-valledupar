# Ficha de procedencia — Línea base de indicadores de seguridad vial, equipos SAST en operación

- **Resultado:** indicadores de línea base por equipo SAST (021, 022, 031, 032, 041, 042, 051, 052, 071)
  y por mes, dentro de la zona de influencia de cada equipo:
  - fallecidos y lesionados (personas);
  - comparendos por código de infracción aprobado para el equipo, desglosados en agentes y
    fotodetección previa no SAST.

  Entregables (versionados en git):

  | Archivo | SHA-256 |
  |---|---|
  | `outputs/2026-10-04_sttv_linea-base-sast.xlsx` (formato ANSV, una hoja por equipo + anexos) | `089f772f4ed58afdbfc8e3239587b3113029d93140cc72fd23df7fc8b68d35cd` |
  | `outputs/2026-10-04_sttv_linea-base-sast.html` (informe) | `8b36b5d45bdc7e5ba4dcecc7e2f00c5067bd6ce87aa64f8d281cdb28f6d4c301` |
  | `outputs/capas/equipos_sast.geojson` (equipos: coordenadas del Excel + datos de la plataforma ANSV) | `fb7b199701f4ec158fa79c659f44b5c0e8b6e3af9ab5196ca215773cdc760dbe` |
  | `outputs/tables/indicadores_largo.csv` (equipo/punto × mes × indicador × medio × criterio) | `ecec00ff071ac74956e3470b56c76549ef954f57b3abfbcf09455447b43bee9f` |
  | `outputs/tables/sensibilidad_ubicacion.csv` | `3c969d2c429299d970440d29b7befec03a9bf5c0477eab19910a9bd3d40cc2cf` |
  | `outputs/tables/siniestros_en_zona_revision.csv` | `a3fe65f891f8d0ec8239632aaab0a90b9eeef8855cfbd69a71ece353e9d0af2a` |
  | `outputs/tables/revision_geocodificacion_en_zona.csv` | `ddf35760aedce90fae83ffb1eafc5c4d99eb690b851c7cc03cb178fbc2b97a96` |
  | `outputs/tables/revision_geocodificacion_muestra_fuera.csv` | `02f8f535ae22d6fd6755b4b770bb10d3636fd794590dff73a6179b24fc88034c` |

  Totales por punto en la línea base, criterio oficial, sin doble conteo entre zonas solapadas. El
  punto usa la ventana del equipo que inició primero:

  | Solicitud (punto) | Ventana | C02 | C03 | C24 | C32 | C35 | D02 | D04 | D05 | Fallecidos | Lesionados |
  |---|---|---|---|---|---|---|---|---|---|---|---|
  | 2 Los Manguitos | sep-2023 a ago-2026 | 12 | 1 | 2 | 3 | 8 | 7 | 21 | 23 | 0 | 0 |
  | 3 Mercado Público | ago-2023 a jul-2026 | 473 | 0 | 19 | 3 | 29 | 38 | 4 | 4 | 3 | 5 |
  | 4 Colegio Loperena | jun-2023 a may-2026 | 1.540 | 7 | 62 | 18 | 84 | 93 | 93 | 18 | 0 | 0 |
  | 5 La Viña | ago-2023 a jul-2026 | 3.008 | 2 | 12 | 13 | 191 | 166 | 11 | 6 | 0 | 3 |
  | 7 U. Área Andina | oct-2023 a sep-2026 | 3 | 0 | 11 | 3 | 5 | 4 | 0 | 1 | 0 | 1 |

  C29 da 0 en los puntos donde está aprobado (2). La D03 del punto 7 está en su hoja de equipo.

- **Fuente de datos:**

  | Insumo | Origen | Corte |
  |---|---|---|
  | Comparendos | Sistema de comparendos de la STTV, reporte «Comparendos Pendientes Notificacion»: 4 archivos HTML-.xls en un zip entregado por la STTV. Según Santiago incluye todos los comparendos impuestos, también los pagados. | 2026-10-04 |
  | Siniestros y víctimas | Portal ArcGIS Enterprise de la ANSV, item `7ec1893e94144a33807dc967455955b2` «Siniestralidad Valledupar» (`…/Siniestralidad_Valledupar/FeatureServer/0` y `/2`). Snapshot de solo lectura: 3.953 siniestros, 6.152 víctimas. | 2026-10-06 12:04 |
  | Equipos | «Equipos SAST Actualizado.xlsx», STTV: coordenadas, nombres y códigos aprobados | archivo del 2026-10-06 |
  | Datos de la plataforma | Plataforma ANSV fotodeteccion-app.ansv.gov.co, listado de puntos «Operando» (captura enviada por Santiago): fecha de inicio de operación, código único, solicitud y dirección (`config/equipos.yaml`) | 2026-10-06 |
  | Zonas de influencia | `Zona de influencia.shp`, SIG de equipos SAST de la STTV | archivo del 2026-10-06 |
  | Referencia vial para geocodificar | Nomenclatura vial urbana IGAC 2021 (GDB del POT de Valledupar) y red vial OSM del repo red-vial-valledupar | OSM 2026-08-05 |

  SHA-256 de cada insumo: `docs/manifiesto_raw.csv` y `docs/pot_procedencia.csv`.

- **Periodo cubierto:**
  - Línea base en formato ANSV: para cada equipo, los 36 meses previos al mes de su inicio de
    operación. Esa es la regla del formulario ANSV.

    | Equipos | Inicio | Ventana |
    |---|---|---|
    | 021 y 022 | 02/09/2026 | sep-2023 a ago-2026 |
    | 031, 032, 051 y 052 | 27/08/2026 | ago-2023 a jul-2026 |
    | 041 | 18/08/2026 | ago-2023 a jul-2026 |
    | 042 | 17/06/2026 | jun-2023 a may-2026 |
    | 071 | 02/10/2026 | oct-2023 a sep-2026 |

  - Serie del informe HTML: ene-2023 a sep-2026.

- **CRS:**
  - Fuentes: equipos (Excel) y zonas en EPSG:4326. El portal guarda en Web Mercator (102100) y se
    consultó con `out_sr=4326`. La nomenclatura del POT viene en EPSG:3116 y se transformó a
    EPSG:9377. La red OSM está en EPSG:4326.
  - Todas las operaciones métricas (buffers, cruces, distancias, áreas) se hicieron en
    **EPSG:9377 (MAGNA-SIRGAS / Origen-Nacional, CTM12)**.
  - Resultados geográficos (capa de equipos, mapa) en EPSG:4326.

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
    - Cámaras SAST: 5.709. Se asignan a su equipo por la dirección de la plataforma ANSV, se ubican
      en la coordenada del equipo y se excluyen de la línea base. Ninguno es anterior al inicio de
      su equipo.
  - **Código «F»:** 240 registros fuera de toda lista aprobada.
  - **Revocados, anulados y absueltos:** se cuentan, porque el indicador mide comparendos impuestos.
  - **Ubicación:**
    - Manda la dirección, geocodificada por cruce o placa sobre los ejes IGAC + OSM (reglas 7–10 y
      13 de `CLAUDE.md`). El GPS solo se usa si la dirección no da un punto.
    - Resultado: 89.364 por dirección, 991 por dirección con desempate por GPS, 5.709 en la
      coordenada de su equipo (SAST), 37.473 por GPS y 12.847 no ubicables.
    - GPS frente a dirección: mediana 102 m; el 51 % discrepa más de 100 m.
  - **Siniestros:**
    - Una corrección manual, decidida por Santiago (`docs/correcciones_siniestros.csv`, SHA-256
      `e406635b847054229fcf9e95ba116581e9e48e988033d1cdbbd6aab88074e672`): el gemelo de Mercado
      Público del 01/06/2025 queda como un solo hecho «Con Muertos», con 1 fallecido (el
      motociclista) y 1 herido. Se excluye el registro de deceso clínico duplicado.
    - 111 sin `cantidad_muertos` y 3 sin `cantidad_heridos` se cuentan como 0.
    - 3 no tienen coordenada utilizable.
  - **Asignación a zonas (criterio oficial mixto, decisión 15):**
    - Comparendos ubicados por dirección: polígono estricto.
    - Siniestros y comparendos ubicados por GPS: polígono + 15 m.
    - Como sensibilidad se publican todo estricto y todo +15 m.
  - **Siniestros en zona:** 10 en la serie (8 en alguna ventana de línea base), revisados por Santiago.
  - **Controles:**
    - Las celdas del Excel coinciden con la tabla larga.
    - Las coordenadas x/y de cada siniestro coinciden con su lon/lat (control de ida y vuelta,
      agregado tras detectar y corregir un desalineamiento de índice el 2026-10-06).
    - Auditoría del revisor-datos (2026-10-06) y re-verificación: «apto con salvedades».

- **Salvedades para el uso como evidencia** (detalle en `docs/metodologia.md`):
  1. La línea base es un piso. La incertidumbre de ubicación es mayor que el ancho de las zonas, así
     que las cifras por equipo son un orden de magnitud.
  2. El registro de lesionados del portal no es homogéneo: 7–9 por mes en el municipio en 2023–2025
     frente a unos 29 en 2026. Las fuentes de fallecidos también cambian entre años.
  3. Los equipos de un mismo punto pueden tener ventanas distintas (041 y 042).
  4. La revisión a mano de la geocodificación (`revision_geocodificacion_*.csv`) sigue pendiente.
  5. El radicado del 071 difiere entre la plataforma (SOL0000010785) y el Excel (SOL0000011264).

- **Script/notebook:**
  - Comandos: `scripts/00_snapshot_portal.py`, `00_manifiesto.py`, `01_equipos.py`,
    `02_comparendos.py`, `03_geocodificar.py`, `04_siniestros.py`, `05_indicadores.py`,
    `06_reportes.py`, `07_revision_geocodificacion.py`.
  - Funciones en `src/sast/`; reglas en `CLAUDE.md` (decisiones 1–24) y `docs/metodologia.md`.
  - Commit `c21b0b242bb0fcdf73aaaaf71c8916df7bcf0e3d` (c21b0b2). El repo es
    `~/Claude_code/sast-valledupar`, privado y sin remoto.

- **Generado:** 2026-10-06 | **Validado por:** Santiago Torreglosa
