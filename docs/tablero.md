# Tablero «Semáforos SAST · Valledupar»

Sitio estático en `tablero/` (sin compilación), publicado en GitHub Pages por
`.github/workflows/pages.yml`, que despliega **solo** esa carpeta.

## Qué muestra
- Mapa con los 5 cruces semaforizados con SAST (relojes del ciclo en vivo) y las 15 cámaras SAST
  autorizadas (9 operando). Ficha de cada cámara con su línea base oficial (+15 m, decisión 25).
- Por cruce: diagrama desde OSM con cabezas y contador, reloj del ciclo, línea de tiempo,
  explicación en lenguaje claro, horario semanal y tabla de tiempos del controlador.
- Modo presentación (botón «Presentar»; espacio pausa, ← → saltan, Esc sale).
- Rutas enlazables: `#/cruce/la-vina?plan=P2&t=98&vel=5&pausa=1`, `#/sast/EQUIPO051`, `#/presentacion`.
  `?ahora=2026-10-12T15:00:00-05:00` fija la hora (demostraciones y pruebas).

## Límites (se rotulan en el tablero)
- **Fase ilustrativa:** el plan es el que rige a esa hora (hora de Bogotá, festivos de Colombia),
  pero el segundo del ciclo se ancla al inicio del bloque horario; no está sincronizado con el
  controlador.
- **Vehículos y peatones ilustrativos:** no son aforos. Solo aparecen en los cruces cuya
  asignación grupo → acceso validó Santiago (decisión 28).

## Regenerar
```bash
source .venv/bin/activate
python scripts/09_semaforos.py          # lee los PDF, valida, borrador de accesos y página de validación
python scripts/10_tablero.py            # datos públicos en tablero/data/ (solo asignaciones validadas)
python scripts/verificar_tablero.py     # guardia: sin borradores ni datos personales
node --test tests/js/*.test.mjs         # modelo idéntico a Python, festivos, simulación
python -m http.server 8765 -d tablero   # ver en http://127.0.0.1:8765
```
`python scripts/10_tablero.py --borrador` arma un ensayo local con el borrador sin validar
(marcado «Borrador sin validar»); la guardia impide publicarlo.

## Validar la asignación de un cruce (decisión 28)
1. Revisar `outputs/semaforos_validacion-accesos.html`.
2. En `config/semaforos.yaml`, dentro del cruce:
   `asignacion: {validado_por: Santiago Torreglosa, fecha: AAAA-MM-DD, desde_borrador: true}`
   y, si algún grupo cambia, `cambios: {G5: {movimiento: "…", acceso: norte, sale_por: oeste}}`.
3. Correr `10_tablero.py` y la guardia; commit y push.

## Publicar
El repo es público (decisión 26). En GitHub: Settings → Pages → Source: **GitHub Actions**.
Cada push a `master` que toque `tablero/` vuelve a desplegar.
