"""Geocodificación de direcciones de comparendos sobre los ejes viales de Valledupar.

Lectura de la dirección: `sast.ubicacion.direccion.leer` (vendorizado). Ejes: unión de la
nomenclatura vial IGAC 2021 (POT) y la red OSM, recortada a la cabecera
(`sast.ubicacion.geocodificar.preparar_ejes`). Todo en EPSG:9377.

Reglas [Nuestra] (docs/metodologia.md):
- **Cruce** («CL 16B CR 13», «DIAGONAL 21 - CARRERA 19»): el cruce teórico de las dos vías.
- **Domiciliaria** («CALLE 16 # 12-20»): sobre la vía principal (Calle 16), a `placa` metros
  del cruce con la Carrera 12 en dirección al cruce con la Carrera 13 (el siguiente número),
  en línea recta y sin pasar de ese cruce. Si el siguiente cruce no existe en la referencia,
  queda en el cruce con la Carrera 12 (precisión de una cuadra).
- Si las vías se cruzan en más de un lugar a ≤ `CERCANOS_M` entre sí (dobles calzadas,
  cruces escalonados), se toma el centro de los candidatos: `cruce_aproximado` (el error es
  a lo sumo la mitad de la separación). Si están más lejos, la dirección sola no decide:
  `ambigua`, con los candidatos; con coordenada GPS se toma el candidato más cercano.
- Vía sola, vías paralelas, kilometraje, referencias o texto no interpretable: la dirección
  no da un punto (`sin_punto`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from shapely import Point

from sast.ubicacion.direccion import _MARCA_PLACA, Via, leer, limpiar
from sast.ubicacion.geocodificar import Ejes, cruces_teoricos

# placa tras el número de la vía generadora: «# 12-20», «# 7A 41», «12 B BIS - 20»
_PLACA_TRAS_MARCA = re.compile(r"#\s*\d{1,3}\s*(?:[A-Z]\b)?\s*(?:BIS\b)?\s*(?:[A-Z]\b)?\s*-?\s*(\d{1,3})\b")
_PLACA_GUION = re.compile(r"\b\d{1,3}\s*(?:[A-Z]\b)?\s*(?:BIS\b)?\s*(?:[A-Z]\b)?\s*-\s*(\d{1,3})\b")
SIGUIENTE_MAX_M = 250.0     # el siguiente cruce debe estar a menos de esto (una cuadra larga)
CERCANOS_M = 150.0          # candidatos de un mismo cruce a menos de esto: se promedian


@dataclass
class Resultado:
    metodo: str     # cruce | cruce_aproximado | domiciliaria | domiciliaria_cuadra | ambigua | sin_punto
    tipo_direccion: str
    candidatos: list = field(default_factory=list)   # puntos EPSG:9377
    detalle: str = ""
    vias: str = ""


def placa(texto: str) -> int | None:
    t = _MARCA_PLACA.sub(" # ", limpiar(texto))
    m = _PLACA_TRAS_MARCA.search(t) or _PLACA_GUION.search(t)
    return int(m.group(1)) if m else None


class Geocodificador:
    def __init__(self, ejes: Ejes):
        self.ejes = ejes
        self._cruces: dict = {}

    def cruces(self, a: Via, b: Via) -> tuple[list[Point], str]:
        k = (a.clave, b.clave)
        if k not in self._cruces:
            if a not in self.ejes or b not in self.ejes:
                faltan = [str(v) for v in (a, b) if v not in self.ejes]
                self._cruces[k] = ([], "vía no está en la referencia: " + ", ".join(faltan))
            else:
                self._cruces[k] = cruces_teoricos(self.ejes.get(a), self.ejes.get(b))
        return self._cruces[k]

    def ubicar(self, texto: str) -> Resultado:
        d = leer(texto)
        vias = " × ".join(str(v) for v in d.vias)
        if d.tipo not in ("cruce", "cruce_inferido"):
            return Resultado("sin_punto", d.tipo, detalle=f"dirección de tipo {d.tipo}", vias=vias)
        v1, v2 = d.via_1, d.via_2
        pts, det = self.cruces(v1, v2)
        if not pts:
            return Resultado("sin_punto", d.tipo, detalle=det, vias=vias)
        if len(pts) > 1:
            sep = max(p.distance(q) for p in pts for q in pts)
            if sep > CERCANOS_M:
                return Resultado("ambigua", d.tipo, pts, f"{len(pts)} cruces posibles a {sep:.0f} m", vias)
            centro = Point(sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts))
            return Resultado("cruce_aproximado", d.tipo, [centro],
                             f"{len(pts)} cruces a {sep:.0f} m: se toma el centro", vias)
        c0 = pts[0]
        n = placa(texto) if d.domiciliaria else None
        if n is None:
            return Resultado("cruce", d.tipo, [c0], det, vias)
        sig = Via(v2.tipo, v2.num + 1)
        pts1, _ = self.cruces(v1, sig)
        pts1 = [p for p in pts1 if p.distance(c0) <= SIGUIENTE_MAX_M]
        if not pts1:
            return Resultado("domiciliaria_cuadra", d.tipo, [c0],
                             f"placa {n}; sin cruce con {sig} a ≤ {SIGUIENTE_MAX_M:.0f} m", vias)
        c1 = min(pts1, key=c0.distance)
        dist = c0.distance(c1)
        f = min(n, dist) / dist if dist > 0 else 0.0
        p = Point(c0.x + f * (c1.x - c0.x), c0.y + f * (c1.y - c0.y))
        return Resultado("domiciliaria", d.tipo, [p], f"placa {n} m hacia {sig} (cuadra de {dist:.0f} m)", vias)
