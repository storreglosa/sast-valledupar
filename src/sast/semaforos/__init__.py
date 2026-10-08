"""Planeamientos semafóricos de las intersecciones con SAST (decisiones 27–29).

Fuente: reportes PDF del controlador SISTRA «Wiseverse V. 3.0» en `data/raw/semaforos/`. Cada
reporte trae un resumen (p. 1), la matriz de grupos amigos (p. 2), una página por plan con los
tiempos TIRA/TIV/TFV/TFA de cada grupo y el horario semanal (última página).

- `pdf`: texto con posición (`pdftotext -bbox`) e imagen de una página (`pdftoppm`).
- `planes`, `matriz`, `horario`: lectura de cada tipo de página.
- `tiempos`: modelo de estados del ciclo (lo replica `tablero/js/nucleo/tiempos.js`).
- `validacion`: chequeos que se reportan, nunca se corrigen.
- `correo`: comparación con la tabla del correo del 29/09/2026.
"""
