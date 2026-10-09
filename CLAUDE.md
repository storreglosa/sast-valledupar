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
- `src/sast/semaforos/` — lectura de los reportes SISTRA, modelo de tiempos, validaciones, geometría OSM.
- `tests/` — pruebas (`unittest`; `tests/fixtures/` = estados de referencia que comparten Python y JS).
- `tablero/` — sitio estático publicado en GitHub Pages (`docs/tablero.md`). Lo único que se publica.

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
python scripts/07_revision_geocodificacion.py  # listas para revisar la geocodificación a mano
python scripts/08_reporte_ejecutivo.py # informe ejecutivo (gerencia) + Excel para copiar a la plataforma ANSV (+15 m)
python scripts/09_semaforos.py         # planes semafóricos (PDF SISTRA), validaciones, borrador de accesos y página de validación
python scripts/10_tablero.py           # datos públicos del tablero (tablero/data/); --borrador = ensayo local
python scripts/verificar_tablero.py    # guardia de publicación (la corre también GitHub Actions)
python -m unittest discover -s tests   # pruebas (las de PDF se saltan si falta data/raw/semaforos/)
node --test tests/js/*.test.mjs        # pruebas del tablero (modelo = Python, festivos, simulación)
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

Decisiones del 2026-10-06 (tarde), Santiago:
19. **Equipos = Excel de equipos.** Coordenadas, nombres y códigos aprobados salen siempre del Excel,
    nunca de geocodificar la dirección del equipo. Capa versionada: `outputs/capas/equipos_sast.geojson`.
    La fecha de inicio, el código único, la solicitud y la dirección vienen de la plataforma ANSV
    (`config/equipos.yaml`).
20. **Ventana de línea base por equipo:** los 36 meses previos al mes de inicio de operación de cada
    equipo. Es la regla del formulario ANSV, donde un inicio el 02/09/2026 da un Año 1 de sep-2023 a
    ago-2024. El total por punto usa la ventana del equipo que inició primero.
21. **Comparendos SAST:** se asignan a su equipo por la dirección ANSV (sin «SENTIDO») y se ubican
    en la coordenada del equipo. No se cuentan por zona. Ninguno es anterior al inicio de su equipo.
22. **Correcciones manuales de siniestros** en `docs/correcciones_siniestros.csv` (no se toca el
    portal). La primera es el gemelo de Mercado Público del 01/06/2025: un solo hecho con muertos,
    con 1 fallecido (el motociclista) y 1 herido.
23. **EQUIPO071 sin comparendos SAST:** inició el 02/10/2026 y el export corta el 04/10/2026; según
    Santiago, en esa zona no se hacía ese tipo de control.
24. ~~**El repo se mantiene privado.**~~ Reemplazada por la 26. Estuvo sin remoto hasta el 2026-10-07:
    `origin` = `github.com/storreglosa/sast-valledupar`.
25. **Cifra oficial reportada a la ANSV = zona + 15 m para todo** (Santiago, 2026-10-06; reemplaza la
    decisión 15 solo para el reporte). El informe técnico (`06_reportes.py`) se deja como está, con
    el criterio mixto y las sensibilidades. El informe ejecutivo para gerencia y el Excel para
    copiar en la plataforma (`08_reporte_ejecutivo.py`) usan +15 m.

Decisiones del 2026-10-08, Santiago (tablero de semáforos SAST, `tablero/`):
26. **El repo pasa a público** para publicar el tablero en GitHub Pages (reemplaza la 24). El
    historial se deja como está: auditado el 2026-10-08 (16 commits), sin placas, cédulas, nombres
    ni secretos. Dejan de versionarse los 4 CSV de revisión con registros puntuales (`.gitignore`);
    siguen en commits anteriores. Los HTML de línea base (entregables) siguen versionados.
27. **Tiempos semafóricos = reportes de los controladores SISTRA** (`data/raw/semaforos/`), no la
    tabla del correo del 29/09/2026. Diferencias: La Viña P1 85 s (correo 60), Mercado P2 110 s
    (correo 100), Mercado P1 sin horario en el controlador (correo: dom/fest 05:30–17:00).
28. **Grupo semafórico → acceso:** no viene en los PDF. Se propone con OSM + matriz de grupos
    amigos y lo valida Santiago; sin validación el tablero no anima vehículos en ese cruce.
29. **Así se ve en campo:** TIRA→TIV (2 s) es solo rojo; el último segundo peatonal (TFV→TFA) es
    rojo intermitente; las cinco intersecciones tienen contador regresivo.
30. **Nombres de los grupos SISTRA = codificación de trayectorias SDM Bogotá** (Manual de Planeación y
    Diseño para la Administración del Tránsito y el Transporte, 2005, Tomo III, num. 5.2.1; figura
    aportada por Santiago). Accesos: 1 Norte, 2 Sur, 3 Oeste, 4 Este (de dónde viene el vehículo).
    «Flujo k» = directo desde el acceso k; 5–8 = giro a la izquierda desde el acceso k−4; 9(k) = giro a
    la derecha. «Peatonal 2k» = cruce sobre la mitad de entrada del acceso k; «Peatonal 3k» = cruce sobre
    la mitad por donde sale el directo k (31 brazo sur, 32 norte, 33 este, 34 oeste). Verificado contra
    las matrices de grupos amigos y los sentidos de las cámaras SAST. Lo que falta validar en campo es
    qué brazo físico es cada acceso y el movimiento de la «Flecha» de Los Manguitos.
31. **Asignación validada (Santiago, 2026-10-08):** La Viña, Mercado, Loperena y Área Andina «todo
    bien» sobre la página de validación. Eso incluye el centro de Mercado, el brazo este de Área Andina
    sin grupo y la orientación de Área Andina con una sola cámara. **Los Manguitos** se rehízo con su mapa
    anotado: el acceso 4 es la Calle 21, de un solo sentido hacia el cruce (OSM la tiene de doble
    sentido); los pares del Flujo 1 y de la Flecha quedan a ~58 m (antes del empalme de la Calle 21), el
    del Flujo 4 en la Calle 21 a ~77 m y el del Flujo 3 a ~13 m. La Flecha (giro a la derecha desde el
    norte) es correcta. Estas correcciones de campo van en `config/semaforos.yaml` (`geometria`).
32. **Ajustes de Santiago al tablero (2026-10-08, tarde):** Los Manguitos con los movimientos de sus
    esquemas sobre Google Maps (G1: sur y «U» a la Carrera 19; G2: norte e izquierda a la Carrera 19;
    G3: sur e izquierda al norte; G4: derecha al norte y cruce a la calzada que baja; G5: solo la «U»;
    nadie sale por la Carrera 19 al sureste); un grupo puede tener varias salidas (`sale_por` lista).
    Área Andina: la Calle 6 al este es de un solo sentido de salida. El diagrama va con el norte del
    mapa arriba, con nombres de vías y cabezas paralelas a su vía, fuera de la calzada. El reloj y la
    explicación muestran el rojo máximo y el verde promedio (flujos vehiculares) del plan.
    **Los Manguitos validado** por Santiago el mismo día sobre el ensayo: los cinco cruces quedan
    con la asignación validada.
