# Ficha de procedencia — Planes semafóricos de las intersecciones con SAST y datos del tablero

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
    `config/semaforos.yaml` (decisiones 28 a 33).
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
    - Santiago validó los 5 cruces (decisiones 31 y 32);
    - correcciones de campo en Los Manguitos: la Calle 21 es el acceso 4 y solo entra; pares a 58,0,
      12,8 y 76,9 m; movimientos múltiples por grupo; trayectorias por la red;
    - corrección de campo en Área Andina: la Calle 6 al oriente solo sale.
  - **Tablero:**
    - publica solo asignaciones validadas;
    - la guardia de publicación (`scripts/verificar_tablero.py`) bloquea borradores, claves fuera de
      lista y patrones de placa, cédula o correo;
    - las cifras clave las calcula `claves()` en `tablero/js/nucleo/explicacion.js`: el verde promedio
      se redondea al segundo y los ,5 suben.
- **Script/notebook:** `scripts/09_semaforos.py` (`src/sast/semaforos/`), `scripts/10_tablero.py`
  (`src/sast/tablero.py`), `scripts/verificar_tablero.py` y `tablero/js/nucleo/{tiempos,explicacion}.js`.
  - **Commit `55497a9`** (`55497a91abb1bf4ba55d907756b334de697564bc`, 2026-10-09). Las salidas de la tabla
    «Resultados» se regeneraron con ese código y la guardia pasa. Pruebas: 31 `unittest` y 9 `node --test`.
- **Generado:** 2026-10-09 | **Validado por:** pendiente — persona distinta del autor (decisión 24 del observatorio)

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
| Asignaciones validadas, correcciones de campo y decisiones | `config/semaforos.yaml` | Santiago Torreglosa (STTV), en este repo | `55497a9` | — | `c36529e7fe86e55ce72985523a93a4630f6bbbe81034a7ff8dff0cbe4fdae8b8` |
| Manifiesto de `data/raw/` | `docs/manifiesto_raw.csv` | este repo (`00_manifiesto.py`) | `6ac2168` | — | `81a896ec49ba356fb81332e69fcfb535f3fac26058a51af027d1a8688922e935` |

## Resultados
| Resultado | Descripción | SHA-256 |
|---|---|---|
| `data/processed/semaforos.json` | Todo lo leído y derivado por cruce: planes, matriz, horario, geometría, borrador validado, huella de la config, correcciones de campo y fuente con SHA-256 | `5c6e7c49fc27acddc9a0841fcc4e443b9f086d0b3087b0a70db1d32d8e51f176` |
| `outputs/tables/semaforos_planes.csv` | TIRA/TIV/TFV/TFA por cruce × plan × grupo (116 filas) | `2bd2cb777e03d92d3a52d6b2d8ec93b5274b0a08be05a8000d75054138089f09` |
| `outputs/tables/semaforos_horario.csv` | Horario semanal (día × tramo × plan) | `0c894bc82c07f14c363c36a61278206eb3689e70ddaddf4f933b3afa0ee9e989` |
| `outputs/tables/semaforos_matriz.csv` | Matriz de grupos amigos muestreada | `c94bea419dd0beec1a2fd29e84835298e363f5b5acaa462bd75a7ecd1e4f90e2` |
| `outputs/tables/semaforos_validacion.csv` | Hallazgos de validación (0 ERROR, 13 AVISO, 41 INFO) | `a67a697aec41ef527d67738ded15b3b0053763298cd3bb77fcc8b3cc3ce696a7` |
| `outputs/tables/semaforos_diferencias_correo.csv` | Diferencias controlador vs. correo (5 filas) | `cd152cb17001f5a761c398fe7d116b8bfaa208d47368435a9974c71a252ba607` |
| `outputs/tables/semaforos_accesos_borrador.csv` | Asignación grupo → acceso, validada en los 5 cruces | `47ba42f8fac6757a216d9893453a44fcbc33bdfa8efea8f61acd81683c6cc53d` |
| `outputs/figures/semaforos_matriz_la-vina.png` | Muestreo de la matriz (control visual) | `75d30700ba3b1ab1bc6122d78e9ee940fde9f1592e70d0b97ec556ca64bd63a3` |
| `outputs/figures/semaforos_matriz_mercado.png` | Ídem | `bfaa0fd57248db48c9a43261ff6b5cad8ef9af7686d375d4231d5e6a67a736e6` |
| `outputs/figures/semaforos_matriz_manguitos.png` | Ídem | `8bc1cbc06887bcfd58394f014886216d510f55bf0cf7f239071a9bcf8de7589a` |
| `outputs/figures/semaforos_matriz_loperena.png` | Ídem | `dc4e914bda3b12d6bd607489c002bfa078a42079f18503ff56814b2a2eb60cd5` |
| `outputs/figures/semaforos_matriz_area-andina.png` | Ídem | `0e1acab6855339b5ae8c49a918ac8cb42c2b15dbb224dbc2b2ab7db555ce69d9` |
| `outputs/semaforos_validacion-accesos.html` | Página de validación (uso interno) | `f0c3d059f1d0b0a4e94dbf36c3f3ec96eeebec0c90b1bb6955f1909b88ecaec7` |
| `tablero/data/semaforos.json` | Planes, horario, cifras y asignación publicados en el tablero | `3652fce9faaf2db6e1e747e145ec9677fc5aaaa2d1a8feb3856ee0a55d66f6ed` |
| `tablero/data/geometria.json` | Geometría ilustrativa publicada | `47af31255de9f68cc463864759f6c252a73005ef291eaf7ce1efa72b8e5e9fb6` |
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
  - la Flecha de Los Manguitos ya no dice «por confirmar»;
  - hay un AVISO nuevo para brazos de entrada sin acceso;
  - `generado` es la fecha de corte de los insumos;
  - el BACKLOG está al día.
- **Reservas que quedan como límite:** son las limitaciones 6 a 11 de la auditoría, que se detallan
  abajo.

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
  - el tablero rotula «Carrera 16» y «Carrera 15» (nombres de OSM) dos brazos de Mercado que otras
    fuentes llaman Cra 12 o Tv 12;
  - la corrección de la Calle 6 en Área Andina (`09d69b0`) es posterior a su validación (`9589d34`) y
    movió alrededor de 1 m cebras, una línea de pare y el cajón amarillo.
- **El tablero es ilustrativo.** La fase en vivo se ancla al inicio del bloque horario y no está
  sincronizada con el controlador. Los vehículos y peatones son una microsimulación determinista,
  no aforos.
- **Lo que no se verificó:**
  - las correcciones de `55497a9` no se reauditaron;
  - la verdad de campo de las asignaciones;
  - la procedencia de la red vial: no está versionada en su repo y su commit no se puede determinar;
  - el despliegue en GitHub Pages;
  - el resto de las páginas de los PDF a ojo.
