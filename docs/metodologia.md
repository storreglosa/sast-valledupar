# Metodología — línea base de indicadores SAST

Fuente de verdad de las decisiones: `CLAUDE.md` («Decisiones tomadas», 1–18). Este documento
explica el flujo y las limitaciones. Las reglas al detalle están en los docstrings de
`src/sast/comparendos.py`, `src/sast/geocodificacion.py` y `scripts/05_indicadores.py`.

## Indicadores
Se calculan **por equipo SAST en operación** (021, 022, 031, 032, 041, 042, 051, 052, 071) y por mes:
- **Fallecidos y lesionados:** personas (`cantidad_muertos`, `cantidad_heridos`) de los siniestros
  del portal ANSV «Siniestralidad Valledupar» (snapshot de solo lectura, `scripts/00_snapshot_portal.py`).
- **Comparendos por código:** solo los códigos aprobados del equipo (Excel «Equipos SAST»). Se
  desglosan por medio: agente o fotodetección previa (no SAST). Los generados por las cámaras SAST se
  excluyen de la línea base.

**Periodo:** el Excel ANSV cubre, para cada equipo, los 36 meses previos al mes de su inicio de
operación (Año 1, 2 y 3; fechas de la plataforma ANSV en `config/equipos.yaml`). El HTML muestra la
serie de ene-2023 a sep-2026.

**Equipos:** coordenadas, nombres y códigos del Excel «Equipos SAST» (nunca de geocodificar su
dirección). Capa versionada en `outputs/capas/equipos_sast.geojson`. Los comparendos de las cámaras
SAST se asignan a su equipo por la dirección de la plataforma ANSV.

**Correcciones manuales de siniestros:** `docs/correcciones_siniestros.csv`, aplicadas por
`scripts/04_siniestros.py` sin tocar el portal.

## Ubicación de los comparendos
El export no trae coordenadas para la fotodetección. Además, el GPS de las comparenderas discrepa
más de 100 m de la dirección en la mitad de los casos (la mediana pasa de 47 m en 2023 a más de
100 m después). Por eso **manda la dirección**:
1. La dirección se lee con `leer` (vendorizado de Analisis_siniestralidad). Antes se normalizan
   las placas sin «#».
2. Se ubica en el cruce teórico o a `placa` metros del cruce, sobre los ejes IGAC 2021 + OSM.
3. Hay reglas para los aliases y huecos de la referencia (decisiones 7–10).
4. El GPS solo se usa si la dirección no da un punto y el GPS cae en la cabecera.

## Asignación a zonas (criterio oficial mixto)
- **Comparendos ubicados por dirección:** su punto queda sobre el eje de la vía, así que cuentan si
  caen dentro del polígono estricto.
- **Siniestros y comparendos ubicados por GPS:** pueden caer fuera de la calzada, así que cuentan si
  caen a ≤ 15 m del polígono.
- Todas las distancias se calculan en EPSG:9377.
- Como sensibilidad se informan además el criterio todo estricto, el todo +15 m y la comparación
  GPS–dirección (`outputs/tables/sensibilidad_ubicacion.csv`).

## Limitaciones (deben acompañar cualquier uso de las cifras)
1. **Es un piso, no un conteo exhaustivo.** Una parte de los comparendos no se puede ubicar (ver
   «Calidad de los datos» en el HTML).
2. **La incertidumbre de ubicación es mayor que el ancho de las zonas** (16–55 m). Las cifras por
   equipo son un orden de magnitud. Las de equipos con zonas que se solapan (021/022, 041/042)
   deben leerse por punto.
3. **Lesionados:** el registro del portal no es homogéneo. Hay 7–9 lesionados por mes en el
   municipio en 2023–2025 frente a unos 29 en 2026. Afecta los Años 1 y 2 y la primera parte del
   Año 3. Se reporta con salvedad.
4. **Fallecidos:** la mezcla de fuentes del portal cambia entre años. Los siniestros en zona
   (`outputs/tables/siniestros_en_zona_revision.csv`) requieren revisión manual, incluidos los
   posibles gemelos «Deceso clínico».
5. **Ventanas distintas por equipo:** cada equipo tiene su propia ventana de 36 meses, según su fecha
   de inicio en la plataforma ANSV. Los totales por punto usan la ventana del equipo que inició
   primero. Las cifras de equipos de un mismo punto (p. ej. 041 y 042) no cubren los mismos meses.
6. **Placas sin «#»** («CARRERA 16 20-27»): se interpretan como domiciliarias. La regla solo pudo
   contrastarse con GPS en 182 registros (la fotodetección previa no trae coordenada). La mediana
   coincide, pero el 27 % discrepa más de 500 m, sobre todo en «CALLE 16B 7A-45 … CALLE DE LOS
   TURCOS» y «CARRERA 27 44-100». Probablemente el problema está en la referencia vial.
7. **La fotodetección previa no SAST sigue operando** cerca de las zonas después del inicio SAST.
   Es un factor de confusión en cualquier comparación antes/después.
