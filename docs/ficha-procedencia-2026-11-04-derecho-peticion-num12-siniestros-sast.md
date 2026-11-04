# Ficha de procedencia — Siniestros con víctimas, fallecidos y lesionados por punto SAST, antes y después del inicio de operación (derecho de petición, numeral 12)

- **Resultado:** tabla de respuesta al numeral 12 de un derecho de petición («Informar el número de
  siniestros viales, lesionados y fallecidos registrados en los puntos donde operan los sistemas SAST
  antes y después de su instalación»):
  - **Tabla 1, equipos en operación** (9 equipos en 5 puntos): código único ANSV, ubicación y sentido,
    fecha de inicio de cada equipo y fecha de inicio considerada para el punto (la más temprana).
  - **Tabla 2:** periodos de análisis por punto y su duración en días (antes: 1.826; después: 34 a 141).
  - **Tabla 3, por punto** (5 puntos, sin doble conteo): siniestros con víctimas, fallecidos y
    lesionados en dos periodos, y el mismo resultado en prosa por punto.
  - **Tabla A1 (anexo), por equipo** (9 equipos): las mismas cifras. Las zonas de 021/022 y 041/042
    se solapan, así que la suma del anexo no coincide con la Tabla 3.
  - La redacción del Word se reescribió el 2026-11-04 (commit `1ce4620`) para dar el contexto de los
    equipos y el método; las cifras no cambiaron.

  | Punto (equipos) | Inicio | Antes: siniestros / fallecidos / lesionados | Después: siniestros / fallecidos / lesionados |
  |---|---|---|---|
  | Los Manguitos (021, 022) | 02/09/2026 | 2 / 1 / 1 | 0 / 0 / 0 |
  | Mercado Público (031, 032) | 27/08/2026 | 9 / 4 / 7 | 0 / 0 / 0 |
  | Colegio Loperena (041, 042) | 17/06/2026 | 1 / 0 / 1 | 1 / 0 / 1 |
  | La Viña (051, 052) | 27/08/2026 | 1 / 0 / 3 | 0 / 0 / 0 |
  | Universidad Área Andina (071) | 02/10/2026 | 1 / 0 / 1 | 0 / 0 / 0 |
  | **Total** | | **14 / 5 / 13** | **1 / 0 / 1** |

- **Fuente de datos:**
  - **Siniestros:** capa «Siniestralidad Valledupar» del portal ArcGIS de la ANSV
    (`srvansvargweb.ansv.gov.co/portalansv`, item `7ec1893e94144a33807dc967455955b2`, capa 0).
    - Snapshot de solo lectura descargado el 04/11/2026 a las 09:51 con `scripts/00_snapshot_portal.py`.
    - Trae 3.964 registros.
    - La capa consolida varias fuentes: Reporte Policía, Reporte IPAT, Reporte IPAT DITTRA, Geoportal
      ANSV, Mesa calidad ANSV, Deceso clínico y Reporte Siniestro STTV, además de 11 registros
      recientes sin `fuente`.
    - En el Word, la fuente se describe con la redacción que aprobó Santiago (decisión 35).
  - **Equipos, puntos y zonas de influencia:** Excel de equipos SAST y `Zona de influencia.shp`
    (etapa 1, decisión 19). Las fechas de inicio de operación salen de la plataforma de fotodetección
    de la ANSV (captura del 06/10/2026, `config/equipos.yaml`).
- **Periodo cubierto:**
  - **Antes:** los 5 años previos a la fecha de inicio de cada punto. El periodo más temprano es
    17/06/2021 – 16/06/2026 (Loperena) y el más tardío 02/10/2021 – 01/10/2026 (Área Andina).
  - **Después:** desde la fecha de inicio hasta el 04/11/2026, fecha de la descarga. El último
    siniestro con fecha válida en la capa es del 01/11/2026.
- **CRS:**
  - **Capas fuente:** EPSG:4326. El portal guarda en Web Mercator y la descarga se pide con
    `out_sr=4326`.
  - **Zona + 15 m:** el buffer se calculó en EPSG:9377 (etapa 1, capa `zonas_buffer`).
  - **Prueba de inclusión** (punto en polígono): EPSG:4326. No mide distancias.
  - **Resultado:** tabular, sin geometría.
- **Transformaciones:**
  1. **Correcciones manuales** de `docs/correcciones_siniestros.csv` (decisión 22): se excluye
     1 gemelo y se ajusta 1 registro (Mercado Público, 01/06/2025).
  2. **Nulos:** 120 registros sin `cantidad_muertos` cuentan como 0. Todos son «Con Heridos». Otros 3
     sin `cantidad_heridos` también cuentan como 0.
  3. **Sin coordenada utilizable:** se excluyen 3 registros porque no se pueden asignar a una zona:
     - `20750_1589726`, de un municipio rural vecino;
     - `{B0460577…}`;
     - `{40DD54CF…}`, del 15/08/2026, «Carrera 9 con calle 19», con coordenada (0, 0). Según el
       revisor-datos, su dirección geocodificada queda 64 m fuera de la zona 051 + 15 m, así que no
       cambia las cifras.
  4. **Fecha posterior a la descarga:** se excluyen 2 registros (`{FF294F50…}` con fecha 30/11/2026 y
     `{7320715D…}` con fecha 02/12/2026). Ninguno cae en una zona SAST.
  5. **Asignación a zona:** se usa la zona + 15 m (decisión 25). Cada siniestro se cuenta una vez por
     punto y una vez por equipo.
  6. **Solo siniestros con víctimas** (decisión 34): en zona se apartan 61 registros «Solo Daños». De
     ellos, 2 caían en las ventanas de «antes»: `20001_6084845` (Los Manguitos) y `20001_6026241`
     (Área Andina).
  7. **Personas:** fallecidos y lesionados se cuentan como personas (`cantidad_muertos`,
     `cantidad_heridos`; decisión 6).
  8. **Control contra el corte anterior (2026-10-06):** el periodo «antes» da lo mismo. Entre los dos
     cortes el portal reubicó 162 registros, cambió `20001_WHATSAPP_0027` de «Con Muertos» a «Con
     Heridos» y agregó 11 registros. El revisor-datos verificó que nada de eso entra ni sale de las
     zonas, y que el caso de «después» ya estaba en el corte del 06/10.
- **Script/notebook:** `scripts/11_derecho_peticion.py`
  - **Commit `1ce4620`** (etapa creada en `24def9e`)
- **Generado:** 2026-11-04 | **Validado por:** pendiente — persona distinta del autor (decisión 24)

## Insumos
| Insumo | Ruta | Productor | Commit | Etiqueta | SHA-256 |
|---|---|---|---|---|---|
| Siniestros portal ANSV, corte 2026-11-04 | `data/raw/portal/2026-11-04_portal_siniestros.parquet` | ANSV (portal); snapshot de `sast-valledupar` | `24def9e` | — | `a53e5a4c3e26f301d06d3659f06d7ad4330dee0ad16d7020605ba9aaa33ef7f4` |
| Procedencia del snapshot | `data/raw/portal/2026-11-04_portal_procedencia.json` | `sast-valledupar` (`00_snapshot_portal.py`) | `24def9e` | — | `0a9c06eee6da80ac8089a53364e55f96233722e10f70ef2b01f67fd862e4532a` |
| Siniestros portal ANSV, corte 2026-10-06 (control) | `data/raw/portal/2026-10-06_portal_siniestros.parquet` | ANSV (portal); snapshot de `sast-valledupar` | `24def9e` | — | `2187122a561a02912d824dbee807004737eb4cc941c1c257360cde5289b31c8d` |
| Equipos y zonas (+15 m) | `data/processed/equipos_sast.gpkg` | `sast-valledupar` (`01_equipos.py`) | `c21b0b2` | — | `64830981026a545dca5b6f35a27f02d5ea31e909640caa3fabf1c4a8188bfa64` |
| Fechas de inicio de operación | `config/equipos.yaml` | plataforma ANSV (captura de Santiago, 06/10/2026) | `c21b0b2` | — | `e3807148d04464251f5e785312d796a2ab01a22e76927b26c4a85bec709f9ae2` |
| Correcciones manuales de siniestros | `docs/correcciones_siniestros.csv` | Santiago Torreglosa (STTV) | `c21b0b2` | — | `e406635b847054229fcf9e95ba116581e9e48e988033d1cdbbd6aab88074e672` |

`data/raw/` y `data/processed/*.gpkg` no se versionan. Sus huellas están en `docs/manifiesto_raw.csv`
(para raw) y en esta tabla.

## Resultados
| Resultado | Descripción | SHA-256 |
|---|---|---|
| `outputs/2026-11-04_sttv_derecho-peticion-num12_siniestros-sast.docx` | Insumo técnico en Word para jurídica: contexto de los equipos, fuente y método, Tablas 1–3 y anexo por equipo | `80d246edca9b76a9fb960387aa832c0c9d6828116b1990a144f06e7e4d4875e5` |
| `outputs/2026-11-04_sttv_derecho-peticion-num12_siniestros-sast.xlsx` | Mismas tablas (por punto, por equipo) y hoja de procedencia | `88e8042c1eb4310e30dd22d3c6b445fd54c1dd80269cfc1e826917e2a5fbed89` |
| `outputs/tables/derecho_peticion_siniestros_en_zona.csv` | Detalle registro a registro (codrot, fecha, gravedad, dirección, coordenada). No se versiona (decisión 26) | `e124f3ba8996c6bb3ac8e1b632f0d171102cb588bdbb1f1021e79b66a127c000` |

El .docx y el .xlsx llevan marcas de tiempo, así que su SHA cambia en cada corrida aunque el contenido
sea el mismo. Las huellas de arriba son las de los archivos versionados en `1ce4620`.

## Revisión independiente
- **Auditado por:** revisor-datos, 2026-11-04, con contexto fresco. Auditó la versión que contaba
  todas las gravedades (16 siniestros antes). Después Santiago decidió contar solo siniestros con
  víctimas. Ese cambio es un filtro por `gravedad`, que el revisor no volvió a auditar; las cifras de
  fallecidos y lesionados no cambiaron.
- **Veredicto:** APTO CON RESERVAS.
- **Qué verificó:**
  - Recalculó las cifras con código propio (sjoin en EPSG:9377) y dan exactamente lo mismo.
  - `zonas_buffer` es igual a zona + 15 m.
  - Los cambios del portal entre cortes no afectan las zonas.
  - Las huellas coinciden con el manifiesto.
  - No hay pérdidas silenciosas.
  - No queda ningún dato personal versionado.
- **Reservas corregidas en el código:**
  - metadatos del Word (autor y fecha);
  - hoja de procedencia del Excel (SHA, item, correcciones, exclusiones);
  - la nota de «Solo Daños» dejó de ser necesaria al contar solo siniestros con víctimas.
- **Reservas que Santiago decidió dejar como están (decisión 35)** y que quedan declaradas como límite:
  1. **Caso único de «después»** (`{1881E171…}`, Loperena, 19/08/2026, «Diagonal 16 con 16 - 46»):
     - la coordenada está en Cl 16 × Dg 21;
     - leída como Cl 16 × Cr 16 o como placa Cl 16 # 16-46, la dirección queda a unos 246 m y fuera
       de la zona;
     - la coordenada entra a la zona solo por el buffer (11,6 m fuera del polígono estricto);
     - toda la columna «después» depende de este registro.
  2. **Posible gemelo del 30/07/2021 en Loperena:** `20001_5582625` (IPAT, peatón herido, en zona) y
     `20001_GEOPORTAL_10965` (Geoportal ANSV, peatón muerto, a 232 m y 17 m fuera de la zona 042 + 15
     m). No se corrige.
  3. **Descripción de la fuente en el Word:** no menciona que la capa está alojada en el portal de la
     ANSV ni sus registros de Geoportal y Mesa de calidad ANSV. 2 de los 4 fallecidos de Mercado
     Público son «Geoportal ANSV» sin dirección.
  4. **Rezago de carga:** octubre de 2026 tiene 14 registros, contra 27–31 por mes en el resto de
     2026, y el último dato es del 01/11/2026. El Word no lo advierte.

## Conclusiones que se pueden citar (con estos límites)
1. En las zonas de influencia (+15 m) de los 5 puntos SAST de Valledupar, la capa «Siniestralidad
   Valledupar» registra 14 siniestros con víctimas, con 5 fallecidos y 13 lesionados, en los 5 años
   previos al inicio de operación de cada punto.
2. Desde el inicio de operación y hasta el 04/11/2026, la misma capa registra en esas zonas 1 siniestro
   con víctimas (Colegio Loperena, 19/08/2026), con 0 fallecidos y 1 lesionado. Este caso está sujeto
   a la reserva 1.
3. Mercado Público concentra 9 de los 14 siniestros con víctimas de «antes» y 4 de los 5 fallecidos.

Ninguna de estas cifras sirve para afirmar un efecto de los SAST. Los periodos no son comparables:
5 años contra 1 a 4,5 meses, con un registro que cambia de fuentes y tiene rezago.

## Límites que viajan con cualquier cifra
- **Registro:** cuenta lo que tiene la capa del portal, no la siniestralidad real. La mezcla de fuentes
  cambia entre años, y los lesionados no tienen un registro homogéneo entre 2021–2025 y 2026
  (decisión 16).
- **Periodo «después»:** dura entre 1 y 4,5 meses según el punto, y las últimas semanas pueden estar
  incompletas por rezago de carga.
- **Ubicación:** las cifras dependen de la coordenada registrada y del buffer de 15 m. Varios casos
  entran solo por el buffer: el fallecido de Los Manguitos (7,5 m), el de Área Andina (12,3 m) y el
  caso de «después» (11,6 m). Otros quedan fuera por poco, entre ellos un fallecido a 28 m de la zona
  071 + 15 m (28/09/2025).
- **Instalación:** se toma la fecha de inicio de operación de la plataforma ANSV. No hay fecha de
  instalación física.
- **Siniestros con víctimas:** se excluyen los «Solo Daños». Fallecidos y lesionados son personas.
- **Puntos y equipos:** en un punto con dos equipos manda la fecha del equipo que inició primero. En el
  anexo por equipo hay doble conteo en las zonas que se solapan.
