# Ficha de procedencia — Planes semafóricos de las intersecciones con SAST y datos del tablero

> **Actualización del 2026-11-20.** Esta ficha se emitió el 2026-10-09 (commit `55497a9`) y se
> actualiza por dos cambios ya publicados:
> - la **reasignación de grupos de Los Manguitos** (decisión 36, commit `0271333`): G1 controla el
>   acceso sur, G2 el norte y la Flecha (G5) está en la Carrera 19, con giro a la derecha al sur;
> - la **reubicación de las cabezas semafóricas** del diagrama del tablero (commit `5e87dd2`): ninguna
>   tapa a otra ni queda sobre la calzada. Es un cambio solo de dibujo y no toca datos.
>
> Tiempos, matriz, horario, validaciones, diferencias con el correo y figuras de la matriz tienen el
> mismo SHA-256 que el 2026-10-09, así que las conclusiones 1 a 5 no cambian. Lo que cambió está
> marcado con «(2026-11-20)».

- **Resultado:** programación semafórica de las 5 intersecciones semaforizadas con cámaras SAST en
  operación (La Viña, Mercado Público, Los Manguitos, Colegio Loperena y Universidad Área Andina):
  - por plan: ciclo, tiempos TIRA/TIV/TFV/TFA de cada grupo, matriz de grupos amigos y horario semanal
    (lunes a domingo y festivos);
  - cifras derivadas por plan: rojo máximo vehicular, rojo máximo peatonal, verde promedio de los
    flujos vehiculares, segundos de todo rojo, ciclos por hora y etapas;
  - asignación grupo → acceso validada por Santiago y geometría ilustrativa de cada cruce (OSM con
    correcciones de campo);
  - datos publicados del tablero «Semáforos SAST · Valledupar» (`tablero/data/`).

  5 intersecciones, 29 grupos (16 vehiculares, 12 peatonales, 1 flecha), 20 planes, 116 filas
  grupo × plan. Los resultados y su SHA-256 están en la tabla «Resultados».
- **Fuente de datos:**
  - **Reportes del controlador SISTRA Wiseverse V3.0**, uno por intersección. Cuatro son PDF creados el
    26/08/2026 y remitidos por la STTV en el correo del 29/09/2026. El de Universidad Área Andina lo
    descargó Santiago Torreglosa (STTV) del controlador el 08/10/2026 y no venía en el correo
    (decisión 33). Son la fuente de los tiempos (decisión 27).
  - **Correo de la STTV del 29/09/2026** con la tabla de planeamientos. Solo sirve de contraste: su
    tabla está transcrita a mano en `config/semaforos_correo.yaml`.
  - **Red vial OSM** del repo `red-vial-valledupar`, corte 2026-08-05.
  - **Capa de equipos SAST** de este repo (etapa 1; decisión 19).
  - **Asignación grupo → acceso, correcciones de campo y decisiones de Santiago:** en
    `config/semaforos.yaml` (decisiones 28 a 33 y 36).
  - **(2026-11-20) Asignación de Los Manguitos:** la observó Santiago Torreglosa en campo y en el
    controlador, y la confirmó el ingeniero que cargó la programación (decisión 36). No hay documento
    escrito de esa confirmación.
- **Periodo cubierto:** la programación vigente al corte de cada reporte: 26/08/2026 para cuatro
  cruces y 08/10/2026 para Universidad Área Andina. El horario es semanal y se repite. No está
  documentado desde cuándo rige cada programación ni si los controladores la siguen corriendo hoy.
- **CRS:**
  - **Insumos geográficos:** la red vial OSM (capas `vias` e `intersecciones`) y la capa de equipos
    están en EPSG:4326.
  - **Cálculo de la geometría:** todo en EPSG:9377 (CTM12): distancias, radios, líneas de pare y
    trayectorias. Nada se mide en grados.
  - **Salida:** en metros relativos al centro de cada cruce (x al este, y al norte de la cuadrícula
    CTM12). El centro va en EPSG:4326 (`centro.crs`).
  - **Tiempos y cifras:** no aplica.
- **Transformaciones:**
  - **Lectura de los PDF** (poppler `pdftotext` 26.01.0):
    - **Ciclo:** por la escala del eje, C = 6000 / Δx(0→10), porque el gráfico mide 600 pt. En las 20
      páginas de plan, todas las marcas del eje dan un mismo ciclo entero.
    - **Tabla TIRA/TIV/TFV/TFA:** por coordenadas (`-bbox`).
    - **Matriz de grupos amigos:** rasterizada y muestreada (umbrales 0,30 / 0,08). Todas las celdas
      dan fracción 0 o 1.
    - **Horario:** por las etiquetas de la grilla, ajustadas a las horas exactas de la leyenda.
  - **Modelo de estados** (`tiempos.py`, replicado en `tablero/js/nucleo/tiempos.js` y probado contra
    el mismo fixture):
    - TIRA→TIV se ve en rojo (decisión 29);
    - el último segundo peatonal es rojo intermitente;
    - rojo = ciclo − (TFA − TIV), de modo que la preparación cuenta como rojo.
  - **Validaciones:** 54 hallazgos, 0 ERROR, 13 AVISO y 41 INFO (`semaforos_validacion.csv`). Los
    AVISO son:
    - 9 pares con 0 s de despeje;
    - la matriz permisiva de Mercado;
    - 2 de orientación (Los Manguitos y Área Andina);
    - el brazo de entrada sin acceso de Los Manguitos.
  - **Diferencias con el correo:** 5 filas (`semaforos_diferencias_correo.csv`); manda el controlador.
  - **Decisión 33:** la TIRA en blanco de La Viña P5 G1 se deja en blanco; manda la tabla del
    controlador. El diagrama de barras de esa página dibuja 0–2 s.
  - **Geometría y asignación:**
    - el borrador grupo → acceso sale de la codificación SDM (decisión 30), la red OSM y los sentidos
      de las cámaras SAST;
    - Santiago validó los 5 cruces (decisiones 31 y 32) sobre la página de validación, que no es una
      verificación de campo (ver «Límites»);
    - correcciones de campo en Los Manguitos: la Calle 21 es el acceso 4 y solo entra; pares a 58,0,
      12,8 y 76,9 m; movimientos múltiples por grupo; trayectorias por la red;
    - corrección de campo en Área Andina: la Calle 6 al oriente solo sale;
    - **(2026-11-20) Los Manguitos es una excepción a la codificación SDM** (decisión 36): el Flujo 1
      (G1) controla el acceso sur (Diagonal 21 que sube) y el Flujo 2 (G2) el norte (Diagonal 21 que
      baja); la Flecha (G5) pasa del acceso norte a la Carrera 19 y habilita el giro a la derecha al
      sur. G3 y G4 no cambian, y cada acceso conserva sus movimientos (decisión 32). Con la nueva
      asignación, la validación no encuentra pares amigos cuyas trayectorias se crucen (G5 es amiga
      de G1 y de G3). El cambio solo afecta a Los Manguitos: asignación de G1, G2 y G5, sus
      trayectorias y líneas de pare, y la huella de la configuración.
  - **Tablero:**
    - publica solo asignaciones validadas;
    - la guardia de publicación (`scripts/verificar_tablero.py`) bloquea borradores, claves fuera de
      lista y patrones de placa, cédula o correo;
    - las cifras clave las calcula `claves()` en `tablero/js/nucleo/explicacion.js`: el verde promedio
      se redondea al segundo y los ,5 suben;
    - **(2026-11-20) cabezas del diagrama** (`tablero/js/util/solapes.js`): cada cabeza es un
      rectángulo girado que, si su sitio ideal está ocupado, busca la posición libre más cercana por su
      andén (hacia afuera, aguas arriba, hacia el cruce y, si no cabe, el andén opuesto de su misma vía)
      sin tocar calzadas, otras cabezas ni el borde. Si no hay lugar libre, lo avisa en la consola.
      Verificación ad hoc, no reproducible desde el repo (el script de medición no se guardó): en
      Chromium sin interfaz, en los 5 cruces a 1280, 1366, 1600 y 1920 px de ancho, con muestreo que no
      usa ese código y con controles positivos, dio 0 cabezas sobre la calzada, 0 montadas y 0 fuera
      del recuadro. Lo reproducible son las 8 pruebas de `tests/js/solapes.test.mjs`.
- **Script/notebook:** `scripts/09_semaforos.py` (`src/sast/semaforos/`), `scripts/10_tablero.py`
  (`src/sast/tablero.py`), `scripts/verificar_tablero.py`, `tablero/js/nucleo/{tiempos,explicacion}.js`
  y, desde el 2026-11-20, `tablero/js/util/solapes.js` y `tablero/js/vistas/diagrama.js`.
  - **Commit `5e87dd2`** (`5e87dd21139037ba0c1c010c18362b6c03370c4f`, 2026-11-20). Las salidas de la
    tabla «Resultados» se regeneraron con el código de `0271333` (el de `5e87dd2` solo cambia el dibujo) y
    la guardia pasa. Pruebas: 31 `unittest` y 17 `node --test`. Publicado en GitHub Pages con la
    ejecución `44740705965` de GitHub Actions (correcta, 2026-11-20).
  - Emisión anterior: commit `55497a9` (2026-10-09).
- **Generado:** 2026-10-09; actualizado el 2026-11-20 | **Validado por:** pendiente — persona distinta del autor (decisión 24 del observatorio)

## Insumos
| Insumo | Ruta | Productor | Commit | Etiqueta | SHA-256 |
|---|---|---|---|---|---|
| Reporte SISTRA La Viña (controlador 4254, cruce 917) | `data/raw/semaforos/2026-08-26_sistra_planes-la-vina.pdf` | Controlador SISTRA Wiseverse V3.0; remitido por la STTV (correo del 29/09/2026) | — | — | `39a56fc0837c03763c80ef0f9176f793474a88602bf0b3c9b0658eb88a2b80cb` |
| Reporte SISTRA Mercado Público (4162/2112) | `data/raw/semaforos/2026-08-26_sistra_planes-mercado.pdf` | Ídem | — | — | `f07c5450fbc6bde8aebbcad890ffb72773dcc09869272140d6d7d87e1c22e6f0` |
| Reporte SISTRA Los Manguitos (4190/1921) | `data/raw/semaforos/2026-08-26_sistra_planes-manguitos.pdf` | Ídem | — | — | `2fdf9280ff5d4aa83365244857acad68c11a56696c44310755b524f4b62cb0ab` |
| Reporte SISTRA Colegio Loperena (4159/1612) | `data/raw/semaforos/2026-08-26_sistra_planes-loperena.pdf` | Ídem | — | — | `180d37fb27b9915e4b563a4f75d715848ad2b01acd44416dd5348de5266fa690` |
| Reporte SISTRA Universidad Área Andina (4255/2306) | `data/raw/semaforos/2026-10-08_sistra_planes-area-andina.pdf` | Controlador SISTRA; descargado por Santiago Torreglosa (STTV) el 08/10/2026 | — | — | `a4004e7c6890f19c0b8b08429840eadb25668a97d4723e644f6ed197d052c463` |
| Correo de remisión de los planeamientos | `data/raw/semaforos/2026-09-29_sttv_correo-planeamientos.pdf` | STTV | — | — | `82774689a73ee3d3714420c899176f7cf6af3baf0a101dbc0c72c8000a395d16` |
| Red vial OSM de Valledupar (`vias` 14.108, `intersecciones` 8.856) | `data/raw/red_vial/2026-08-05_osm_red-vial-valledupar.gpkg` | repo `red-vial-valledupar` | no determinable: el archivo no está versionado en ese repo; su HEAD al copiarlo era `7e32c04` | — | `18a24dc4fc08ac7665c861656b591a07783f4684265668fc27bf4c78bdac175a` |
| Capa de equipos SAST (15) | `outputs/capas/equipos_sast.geojson` | este repo, etapa 1 | `c21b0b2` | — | `fb7b199701f4ec158fa79c659f44b5c0e8b6e3af9ab5196ca215773cdc760dbe` |
| Transcripción de la tabla del correo | `config/semaforos_correo.yaml` | este repo (transcripción manual) | `e90a838` | — | `4349316497a0142d36767964f81d42289b1a60e27b4fc01928ac0cddb659ba5d` |
| Asignaciones validadas, correcciones de campo y decisiones (2026-11-20: decisión 36) | `config/semaforos.yaml` | Santiago Torreglosa (STTV), en este repo | `0271333` | — | `828eda6bc08e8c757887696baed723e524e6719a302793b2a6d6e64f7011ba91` |
| Manifiesto de `data/raw/` (2026-11-20: incluye el corte del portal del numeral 12; las filas de estos insumos no cambian) | `docs/manifiesto_raw.csv` | este repo (`00_manifiesto.py`) | `24def9e` | — | `85263a546aa00fcca1c398e1ef50c0514b1816477c23d5bdd92951a7d68e945c` |

## Resultados
| Resultado | Descripción | SHA-256 |
|---|---|---|
| `data/processed/semaforos.json` | Todo lo leído y derivado por cruce: planes, matriz, horario, geometría, borrador validado, huella de la config, correcciones de campo y fuente con SHA-256 (2026-11-20: cambia Los Manguitos) | `8b7ef3499631b69fc5873a9b84e23f8f7edee5d2878a696f16b89ae9d9fd1ce4` |
| `outputs/tables/semaforos_planes.csv` | TIRA/TIV/TFV/TFA por cruce × plan × grupo (116 filas) | `2bd2cb777e03d92d3a52d6b2d8ec93b5274b0a08be05a8000d75054138089f09` |
| `outputs/tables/semaforos_horario.csv` | Horario semanal (día × tramo × plan) | `0c894bc82c07f14c363c36a61278206eb3689e70ddaddf4f933b3afa0ee9e989` |
| `outputs/tables/semaforos_matriz.csv` | Matriz de grupos amigos muestreada | `c94bea419dd0beec1a2fd29e84835298e363f5b5acaa462bd75a7ecd1e4f90e2` |
| `outputs/tables/semaforos_validacion.csv` | Hallazgos de validación (0 ERROR, 13 AVISO, 41 INFO) | `a67a697aec41ef527d67738ded15b3b0053763298cd3bb77fcc8b3cc3ce696a7` |
| `outputs/tables/semaforos_diferencias_correo.csv` | Diferencias controlador vs. correo (5 filas) | `cd152cb17001f5a761c398fe7d116b8bfaa208d47368435a9974c71a252ba607` |
| `outputs/tables/semaforos_accesos_borrador.csv` | Asignación grupo → acceso, validada en los 5 cruces (2026-11-20: G1, G2 y G5 de Los Manguitos) | `ca00177ad3dd77fbd8e2502c29f53c0f348563f24a6acf44db435da19258e4f1` |
| `outputs/figures/semaforos_matriz_la-vina.png` | Muestreo de la matriz (control visual) | `75d30700ba3b1ab1bc6122d78e9ee940fde9f1592e70d0b97ec556ca64bd63a3` |
| `outputs/figures/semaforos_matriz_mercado.png` | Ídem | `bfaa0fd57248db48c9a43261ff6b5cad8ef9af7686d375d4231d5e6a67a736e6` |
| `outputs/figures/semaforos_matriz_manguitos.png` | Ídem | `8bc1cbc06887bcfd58394f014886216d510f55bf0cf7f239071a9bcf8de7589a` |
| `outputs/figures/semaforos_matriz_loperena.png` | Ídem | `dc4e914bda3b12d6bd607489c002bfa078a42079f18503ff56814b2a2eb60cd5` |
| `outputs/figures/semaforos_matriz_area-andina.png` | Ídem | `0e1acab6855339b5ae8c49a918ac8cb42c2b15dbb224dbc2b2ab7db555ce69d9` |
| `outputs/semaforos_validacion-accesos.html` | Página de validación (uso interno; 2026-11-20: regenerada) | `1936a7576694ca5e2f56dcaae4f8eac9f4fab42e2ffd0de4ad02fa6322241804` |
| `tablero/data/semaforos.json` | Planes, horario, cifras y asignación publicados en el tablero (2026-11-20: movimientos de G1, G2 y G5 de Los Manguitos y fecha de su asignación) | `cfe9dd8440eee4604f9bbb99cee8f04cad79a84506f8da35bfa50c1d178641b3` |
| `tablero/data/geometria.json` | Geometría ilustrativa publicada (2026-11-20: trayectorias y líneas de pare de Los Manguitos) | `74ca827d4da8d519f835a8220aa537af6beab68f15ba46e6645a259455930117` |
| `tablero/data/sast.json` | Equipos SAST y línea base publicada. Sus cifras son las de la ficha `docs/ficha-procedencia-2026-10-06-linea-base-sast.md`; la etapa 10 solo las copia y las coteja | `0277a55270e1ec9be8c49a0ece82a215f01cb47ef075994c63c78a76f5d4bf7c` |
| `tests/fixtures/estados_referencia.json` | Estados de referencia segundo a segundo (Python = JS) y festivos 2024–2035 | `589f01e716c2f50f66b82de450ac2cbf8e52a44a600b61011d4105c2ea303a6b` |

## Revisión independiente
- **Auditado por:** subagente `revisor-datos`, 2026-10-09, con contexto fresco, sobre el commit
  `b215913`. Retomó una primera vuelta hecha sobre `fd57f8a`.
- **Veredicto:** APTO CON RESERVAS. El revisor lo llamó «apto con correcciones», tanto para evidencia
  como para publicar.
- **Qué verificó:**
  - los 7 insumos contra el manifiesto;
  - la lectura de los PDF, con un lector propio que no usa código del repo: las 116 filas grupo × plan
    coinciden con el CSV y el JSON, y los ciclos son coherentes en las 20 páginas;
  - a ojo, 2 páginas de plan, 3 horarios y 2 matrices;
  - los festivos de 2026;
  - las cifras del tablero, recalculadas de forma independiente en los 20 planes;
  - que ningún par en conflicto tiene paso simultáneo;
  - que la geometría se calcula en EPSG:9377, que los centros caen en el casco urbano y que las
    correcciones de campo aparecen en la salida;
  - que La Viña, Mercado y Loperena no cambiaron con el código nuevo;
  - la reproducibilidad en un clon (09 y 10 dejan `git status` limpio);
  - que no hay datos personales en `tablero/` ni en las salidas versionadas.
- **Reservas corregidas en el código** (commit `55497a9`, después de la auditoría; **no reauditado**):
  - el rótulo pasó a «rojo máx. vehicular», se agregó el máximo peatonal y hay una prueba de las
    cifras contra el cálculo del revisor;
  - la guardia de publicación quedó endurecida, con 5 pruebas con datos inyectados;
  - la 10 se niega a publicar si la 09 dejó errores sin decisión;
  - la huella cubre asignación, geometría, centro y señalización;
  - la red vial se verifica contra el manifiesto y queda en la fuente;
  - la decisión 33 quedó acotada a La Viña P5 G1;
  - la Flecha de Los Manguitos ya no dice «por confirmar» (se refiere a la Flecha de entonces, desde el
    norte; desde el 2026-11-20 está en la Carrera 19, decisión 36);
  - hay un AVISO nuevo para brazos de entrada sin acceso;
  - `generado` es la fecha de corte de los insumos;
  - el BACKLOG está al día.
- **Reservas que quedan como límite:** son las limitaciones 6 a 11 de la auditoría, que se detallan
  abajo.
- **(2026-11-20) Cambios de esta actualización:**
  - **Auditado por:** subagente `revisor-datos`, 2026-11-20, con contexto fresco, sobre `5e87dd2` y la
    ficha sin commitear.
  - **Veredicto:** APTO CON RESERVAS. No encontró errores en cifras, huellas ni commits.
  - **Qué verificó:**
    - corrió 09 y 10: `git status` queda limpio salvo la ficha; 31 `unittest`, 17 `node --test` y la
      guardia, en verde;
    - los 28 SHA-256 de la ficha; frente a la emisión del 2026-10-09 cambian justo los 8 marcados;
    - con un diff estructural, que el cambio de datos se limita a Los Manguitos (G1, G2 y G5) y que
      planes, horario, matriz, validación, diferencias, figuras, fixture y `sast.json` quedan byte a
      byte iguales;
    - contraprueba: con la config de `55497a9` regenera exactamente el tablero anterior; el único
      cambio de datos viene de la config;
    - que la asignación corresponde a la decisión 36;
    - con razonamiento geométrico propio, que los pares amigos G1–G5 y G3–G5 no entran en conflicto:
      sobre las trayectorias publicadas, G1 y G5 no se cortan y quedan a 8,0 m como mínimo. Control
      positivo: con G5 desde el este hacia el norte, la etapa 09 levanta 2 AVISO. Con G1 en el sur, la
      Flecha antigua (norte → oeste) chocaría; mover la Flecha era necesario para que la asignación
      fuera coherente;
    - que `5e87dd2` solo cambia la posición en pantalla de las cabezas y que la ejecución de
      Actions `44740705965` publicó `5e87dd2`;
    - que no hay datos personales en `tablero/`.
  - **Reservas que quedan como límite** (no se corrigieron en el código; ver «Límites»):
    - el tablero no dice que Los Manguitos es una excepción a la SDM;
    - nada en las pruebas impide deshacer la decisión 36;
    - la validación sobre la página no se sostuvo en el único cruce cotejado en campo;
    - la medición de las cabezas no es reproducible;
    - la fecha de la asignación y la evidencia por grupo perdieron detalle.

## Conclusiones que se pueden citar (con estos límites)
Todas son **programación declarada en los reportes del controlador** al corte de cada PDF, no
mediciones de campo.

1. **Ciclos por plan (s):**

   | Cruce | Planes |
   |---|---|
   | La Viña | P1 85, P2 100, P3 30, P5 100 |
   | Mercado Público | P1 85 (sin horario), P2 110, P3 55, P5 100 |
   | Los Manguitos | P1 75, P2 110, P3 65, P5 110 |
   | Colegio Loperena | P1 85 (sin horario), P2 100, P4 50, P5 100 |
   | Universidad Área Andina | P1 90, P2 105, P4 75, P5 105 |

2. **Diferencias con el correo del 29/09/2026** (manda el controlador, decisión 27):
   - La Viña P1 tiene ciclo de 85 s; el correo dice 60.
   - Mercado P2 tiene 110 s; el correo dice 100.
   - Mercado P1 no tiene horario en el controlador; el correo lo pone domingos y festivos de 05:30 a
     17:00.
   - Universidad Área Andina no estaba en el correo.
3. **Rojo máximo vehicular, rojo máximo peatonal y verde promedio de los flujos vehiculares (s) en los
   planes con horario:**

   | Cruce | Plan | Rojo máx. vehicular | Rojo máx. peatonal | Verde prom. vehicular |
   |---|---|---|---|---|
   | La Viña | P1 | 46 | 49 | 37 |
   | La Viña | P2 | 57 | 60 | 43 |
   | La Viña | P3 | 17 | 21 | 10 |
   | La Viña | P5 | 55 | 59 | 44 |
   | Mercado | P2 | 89 | 93 | 23 |
   | Mercado | P3 | 44 | 48 | 9 |
   | Mercado | P5 | 78 | 79 | 20 |
   | Los Manguitos | P1 | 62 | — | 12 |
   | Los Manguitos | P2 | 93 | — | 20 |
   | Los Manguitos | P3 | 54 | — | 10 |
   | Los Manguitos | P5 | 92 | — | 20 |
   | Loperena | P2 | 75 | 90 | 25 |
   | Loperena | P4 | 38 | 45 | 10 |
   | Loperena | P5 | 77 | 91 | 25 |
   | Área Andina | P1 | 67 | 82 | 22 |
   | Área Andina | P2 | 77 | 98 | 27 |
   | Área Andina | P4 | 59 | 69 | 18 |
   | Área Andina | P5 | 80 | 97 | 27 |

   En los 14 planes con horario de los cruces con grupos peatonales, el rojo peatonal más largo supera
   siempre al vehicular (en Mercado P1, sin horario, ambos son de 68 s).
4. Ningún par de grupos en conflicto tiene paso simultáneo en ningún plan.
5. Hay 9 pares de grupos en conflicto con 0 s entre el fin de uno y el verde del otro:
   - Loperena P5: G3→G4 y G3→G6;
   - Área Andina P1, P2 y P4: G1→G5 y G1→G6;
   - Área Andina P5: G1→G5.

   En G1→G6, la cebra 31 es la salida del propio Flujo 1.

## Límites que viajan con cualquier cifra
- **Programado, no medido.** Las cifras son la programación declarada en el reporte del controlador. No
  hay verificación de campo de que los controladores la ejecuten hoy, ni de desde cuándo rige: la
  fecha del PDF es de creación o descarga, no de entrada en vigencia.
- **Festivos.** No se verificó si SISTRA aplica los festivos de Colombia. El tablero aplica el calendario
  oficial (Ley 51 de 1983).
- **Las validaciones son de consistencia interna** (limitación 6). La preparación de 2 s, el amarillo
  de 3 s y el despeje peatonal de 1 s son lo observado en los propios datos, no una norma; que no
  haya AVISO no significa que se cumpla un manual. El despeje peatonal es de 1 s en todos los planes,
  y hay verdes peatonales de 4 a 6 s. Los 9 pares con 0 s de despeje y la matriz permisiva de Mercado
  (G2 con G6, que nunca coinciden en los planes) están sin revisar en campo; el tablero no los muestra.
- **Definiciones de las cifras.**
  - Rojo = ciclo − (TFA − TIV): la preparación TIRA→TIV cuenta como rojo (decisión 29).
  - El «rojo máx. vehicular» incluye la flecha.
  - El verde promedio es solo de los flujos vehiculares (sin flecha ni peatonales), redondeado al
    segundo, y los ,5 suben: La Viña P1 36,5 → 37, La Viña P2 42,5 → 43, Mercado P2 22,5 → 23. Con el
    redondeo bancario de Python darían 36, 42 y 22.
- **El correo tiene contradicciones** (limitación 9):
  - en Mercado, el P1 de domingos y festivos (05:30–17:00) se solapa con el P2 y el P5;
  - Loperena P1 (sin horario) no está en el correo y no se reporta como diferencia.
- **Metadatos raros en la página 1 de los PDF** (limitación 10):
  - los cinco dicen «COD MUNICIPIO: 8001», que es el código DANE de Barranquilla; Valledupar es 20001;
  - el de Loperena dice «DIRECCIÓN: 4159»;
  - Mercado tiene dos ubicaciones: «Calle 20 x Cra 12» en el pie y «Calle21 X Carrera12» en la portada.

  Los códigos de equipo y cruce sí coinciden con lo esperado. Lo más probable es que sean valores por
  defecto de SISTRA.
- **La geometría es ilustrativa** (limitación 11):
  - viene de OSM con corte 2026-08-05, más las correcciones de campo de Santiago;
  - los anchos de vía son supuestos cuando OSM no trae carriles;
  - en Los Manguitos, según OSM se puede entrar por la Carrera 19 desde el suroriente (B3) y ningún
    grupo lo controla; está por confirmar en campo;
  - **(2026-11-20)** la asignación de Los Manguitos no sigue la codificación SDM que se usa en los
    otros cuatro cruces (decisión 36). Quien lea «Flujo 1» en ese cruce debe entender el acceso sur,
    no el norte. **El tablero no lo advierte:** sus textos generales (`tablero/js/main.js:55` y el
    glosario en `tablero/js/nucleo/explicacion.js:174`) dicen que todos los nombres siguen la SDM.
    Lo correcto en el tablero es el rótulo de cada grupo, que sale de los datos («Flujo 1 (Diagonal
    21, desde el sur)»);
  - **(2026-11-20) Las asignaciones «validadas» no son verdad de campo.** Las del 2026-10-08 se
    validaron sobre la página de validación. En el único cruce que después se cotejó en campo y en
    el controlador, Los Manguitos, esa validación no se sostuvo en 3 de 5 grupos (G1, G2 y G5). Los
    otros cuatro cruces descansan en el mismo tipo de validación más la codificación SDM, y no se
    han cotejado contra el controlador;
  - **(2026-11-20) Los tiempos y la matriz no distinguen la asignación nueva de la vieja.** La
    Flecha arranca con G1 en los 4 planes y termina con G3 en 3 de 4 (en P1, 1 s después), y eso es
    compatible con ambas. La decisión 36 se apoya solo en la observación de campo de Santiago y en la
    confirmación verbal del ingeniero;
  - **(2026-11-20) Nada impide deshacer la decisión 36.** Con la config anterior repuesta pasan todas
    las pruebas y la guardia. La única protección es el comentario en `config/semaforos.yaml` y la
    decisión 36 en `CLAUDE.md`. Además, `tests/test_semaforos.py:164-170` comprueba la propuesta
    automática de la Flecha desde el norte, que es correcta para el borrador pero es la posición que
    se descartó;
  - **(2026-11-20) Detalle perdido en la asignación de Los Manguitos.** `asignacion.fecha` pasó a
    2026-11-20 para todo el cruce, aunque G3 y G4 siguen como se validaron el 2026-10-08. La evidencia
    de G5 en el borrador dice «Corregido por Santiago Torreglosa», sin fecha. La historia completa
    está en git (`0271333`);
  - **(2026-11-20)** la posición de cada cabeza en el diagrama es un recurso de lectura, no la
    ubicación real del poste: se corre por su andén, o al andén opuesto en pantallas pequeñas, para no
    tapar la calzada ni otra cabeza. Los nombres de las vías no se tratan como obstáculo;
  - el tablero rotula «Carrera 16» y «Carrera 15» (nombres de OSM) dos brazos de Mercado que otras
    fuentes llaman Cra 12 o Tv 12;
  - la corrección de la Calle 6 en Área Andina (`09d69b0`) es posterior a su validación (`9589d34`) y
    movió alrededor de 1 m cebras, una línea de pare y el cajón amarillo.
- **El tablero es ilustrativo.** La fase en vivo se ancla al inicio del bloque horario y no está
  sincronizada con el controlador. Los vehículos y peatones son una microsimulación determinista,
  no aforos.
- **Lo que no se verificó:**
  - las correcciones de `55497a9` no se reauditaron;
  - (2026-11-20) la confirmación del ingeniero de la programación de Los Manguitos no está documentada
    por escrito: consta como observación de Santiago (decisión 36);
  - (2026-11-20) la reubicación de las cabezas se midió en Chromium sin interfaz, no en otros
    navegadores;
  - la verdad de campo de las asignaciones;
  - la procedencia de la red vial: no está versionada en su repo y su commit no se puede determinar;
  - el sitio publicado a ojo: el 2026-11-20 se verificó solo que la publicación en GitHub Pages terminó
    bien;
  - el resto de las páginas de los PDF a ojo.
