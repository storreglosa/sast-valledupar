# BACKLOG — sast-valledupar

Lista viva de pendientes. Lo hecho se tacha con la fecha.

## Tablero de semáforos SAST (`tablero/`, decisiones 26–30)
- [x] ~~Copiar los PDF a `data/raw/semaforos/`, manifiesto y 09/10 sin `SAST_RAW`~~ (2026-10-08).
- [x] ~~Procedencia del reporte de Universidad Área Andina~~: lo descargó Santiago del controlador el
      08/10/2026 (decisión 33). Falta: desde cuándo rige esa programación en el controlador.
- [x] ~~La Viña P5, G1, TIRA en blanco~~: manda la tabla (decisión 33, `config/semaforos.yaml: decisiones`).
- [x] ~~Validar el borrador grupo → acceso~~: los cinco cruces validados (decisiones 31 y 32).
- [ ] Los Manguitos: confirmar en campo si se puede entrar por la Carrera 19 desde el suroriente
      (B3); hoy ningún grupo lo controla (AVISO `brazo_sin_acceso`).
- [ ] Mercado: el tablero rotula «Carrera 16» y «Carrera 15» (nombres OSM) los brazos sur y
      noroccidental; las otras fuentes hablan de Cra 12 / Tv 12. Confirmar y, si hace falta,
      corregir con `nombres_via`.
- [ ] Revisar en campo los 9 pares con 0 s de despeje (Loperena P5; Área Andina P1, P2, P4, P5) y la
      matriz permisiva de Mercado (G2 con G6).
- [ ] Ficha de procedencia de las etapas 9 y 10 (revisor-datos del 2026-10-09: apto con correcciones).
- [ ] Descripción de los códigos C31, D07 y D10 (solo equipos 061/062, que no operan).
- [x] ~~Publicación: repo público, Pages con «GitHub Actions»~~ (2026-10-09).

## Datos y validación
- [ ] Revisar a mano `outputs/tables/revision_geocodificacion_en_zona.csv`, que tiene todas las
      direcciones que deciden las cifras. Las 20 más frecuentes suman cerca de la mitad de lo que
      está en zona: empezar por esas.
- [ ] Revisar `outputs/tables/revision_geocodificacion_muestra_fuera.csv` (100 comparendos fuera de
      zona, semilla 20261006) para estimar cuántos debieron caer dentro.
- [ ] Aclarar el radicado del EQUIPO071: la plataforma ANSV dice SOL0000010785 y el Excel de equipos
      SOL0000011264 (coordenadas iguales).
- [ ] Recalcular cuando llegue un nuevo export de comparendos o un nuevo corte del portal. Los
      insumos nuevos van con otro nombre en `data/raw/` (`docs/ingesta.md`).

## Geocodificación (limitaciones abiertas, `docs/metodologia.md`)
- [ ] «DIAGONAL 16-18» / «DIAGONAL 16-14» (unos 190 comparendos cerca de Loperena): un solo número
      tras el guion. No se sabe si es placa o cruce, así que hoy quedan sin interpretar.
- [ ] `domiciliaria_cuadra`: si no existe el cruce siguiente en la referencia, la placa queda en el
      cruce donde empieza la cuadra. Eso sesga hacia los cruces.
- [ ] Direcciones con discrepancias grandes frente al GPS: «CALLE 16B 7A-45 … CALLE DE LOS TURCOS» y
      «CARRERA 27 44-100». Probablemente es un problema de la referencia vial IGAC/OSM.
- [ ] Deduplicación: en 67 de los 110 pares en conflicto, la regla (priorizar la fila con
      coordenada) cambia el medio de fotodetección a agente y corre la fecha. Revisar si conviene
      otra prioridad.

## Seguimiento (siguiente fase)
- [ ] Indicadores mensuales posteriores al inicio de operación de cada equipo (Año 1 de operación)
      en el mismo formato.
- [ ] La fotodetección previa no SAST sigue operando cerca de las zonas después del inicio SAST. Hay
      que separarla en cualquier comparación antes/después.

## Hecho
- ~~Repo, pipeline 00–07, Excel ANSV e informe HTML~~ (2026-10-06)
- ~~Auditoría del revisor-datos y re-verificación: «apto con salvedades»~~ (2026-10-06)
- ~~Fechas de inicio, código único y dirección ANSV por equipo (`config/equipos.yaml`)~~ (2026-10-06)
- ~~Corrección del gemelo «Deceso clínico» de Mercado Público (`docs/correcciones_siniestros.csv`)~~ (2026-10-06)
- ~~Listas de revisión de la geocodificación (etapa 07)~~ (2026-10-06)
