# BACKLOG — sast-valledupar

Lista viva de pendientes. Lo hecho se tacha con la fecha.

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
