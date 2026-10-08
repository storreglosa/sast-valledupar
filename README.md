# sast-valledupar

Gestión y seguimiento de los indicadores de seguridad vial de los equipos SAST
(sistemas automáticos de detección de infracciones) en operación en Valledupar,
para el reporte de la Secretaría de Tránsito y Transporte de Valledupar (STTV) a la ANSV.

**Primera tarea:** línea base por equipo — fallecidos, lesionados y comparendos por
código de infracción dentro de la zona de influencia de cada equipo
(serie ene-2023 a sep-2026; formato ANSV sep-2023 a ago-2026).

## Equipos en operación (oct-2026)
| Solicitud | Punto | Equipos |
|---|---|---|
| 2 | Los Manguitos | 021, 022 |
| 3 | Mercado Público | 031, 032 |
| 4 | Colegio Loperena | 041, 042 |
| 5 | La Viña | 051, 052 |
| 7 | Universidad Área Andina | 071 |

## Tablero de semáforos SAST
Sitio estático en `tablero/` (GitHub Pages): sala de control con el mapa de los 5 cruces
semaforizados con SAST y las 15 cámaras autorizadas, la simulación del ciclo de cada semáforo
(planes reales de los controladores SISTRA, plan vigente por hora de Bogotá y festivos) y la línea
base oficial de cada equipo. Ver `docs/tablero.md`.

## Datos
`data/raw/` no se versiona: los comparendos contienen datos personales.
Ver `docs/` para la procedencia de cada insumo.
