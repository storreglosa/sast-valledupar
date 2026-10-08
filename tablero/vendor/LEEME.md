# Librerías incluidas (vendor)

Se sirven desde el mismo sitio para no depender de un CDN y porque MapLibre 6 carga su *worker*
como módulo, que el navegador no acepta desde otro dominio. Descargadas el 2026-10-08.

| Archivo | Origen | SHA-256 |
|---|---|---|
| maplibre-gl-6.11.1/maplibre-gl.mjs | https://cdn.jsdelivr.net/npm/maplibre-gl@6.11.1/dist/ (licencia BSD-3, LICENSE.txt) | ba262b95afed8ee89dbfdb8476f001c6ede2230660eb6edd6f453cb350c11f55 |
| maplibre-gl-6.11.1/maplibre-gl-shared.mjs | idem | 43110afea7c453d547855a562558f39e41d7abdc70e6853734bc8967974d716b |
| maplibre-gl-6.11.1/maplibre-gl-worker.mjs | idem | 9b59b123156783b3abc6d2d83f1ff02699a87ffd058557bbf22a62123de4dcac |
| maplibre-gl-6.11.1/maplibre-gl.css | idem | d8617d8421930e3fc6185365400e788c374c1a5d9fbe87999998c0bc14a202d3 |
| gsap-3.15.0/gsap.min.js | https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/ (licencia estándar de GSAP, uso sin costo) | 92bb9a96476f983d212a2bc4f54c889039c1696dd4461d40a736860938570fbb |

El mapa base (teselas y estilo `dark`) viene de OpenFreeMap (https://openfreemap.org), con datos
de OpenStreetMap; las fuentes, de Google Fonts.
