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
- Si las dos vías no se tocan en la referencia pero pasan a ≤ `HUECO_AMPLIO_M` (vías que se
  interrumpen o con trazado desfasado entre IGAC y OSM: «CR 16 × CL 20» a 49 m, «TV 12 × CL 20B»
  a 66 m), se toma el punto medio de la menor distancia: `cruce_hueco`. El original
  (`cruces_teoricos`) solo lo hace hasta 30 m.
- Diagonal que no está en la referencia: se busca la calle del mismo número y letra
  («DIAGONAL 16» -> «CALLE 16»), con `alias` marcado. Evidencia: el IGAC rotula «CALLE 16 B
  (DIAG. 16B)», «CALLE 16C (DIAG. 16C)», y el equipo 041 figura como «DIAGONAL 16 - CARRERA 12»
  en el Excel de equipos y como «CALLE 16 - CARRERA 12» en sus propios comparendos.
- Dirección de un equipo SAST (Excel de equipos): si la referencia no da ese cruce o lo da a
  más de `PUNTO_EQUIPO_M` de la coordenada levantada del equipo, manda la coordenada del
  equipo (`punto_equipo`). Caso que lo motiva: «TRANSVERSAL 12 - CALLE 20B» (equipo 032), cuyo
  cruce teórico en IGAC+OSM (punto medio de un hueco) queda a 265 m del equipo porque allí la referencia nombra las vías
  como Calle 21/22 y Carrera 15/16.
- Placa sobre diagonal o transversal («DIAGONAL 21 # 18B-6»): el lector original solo infiere la
  vía generadora para calle y carrera. Aquí se prueba, en orden, el tipo que cruza (diagonal ->
  carrera, luego transversal; transversal -> calle, luego diagonal) y se toma el primero que
  existe y cruza en la referencia; queda marcado en `alias`.
- Placa sin «#» («CARRERA 16 20-27», «CALLE 16B 14-08»): el lector original solo reconoce la
  placa tras «#» o un conector. Si tras la primera vía viene «número[letra][BIS] - número», se
  inserta el «#» antes de leer (`marcar_placa`). «DIAGONAL 16-18» (un solo número tras el guion)
  no se interpreta: puede ser placa o cruce.
- Vía sola, vías paralelas, kilometraje, referencias o texto no interpretable: la dirección
  no da un punto (`sin_punto`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from shapely import Point
from shapely.ops import nearest_points

from sast.ubicacion.direccion import _MARCA_PLACA, _VIA, Via, leer, limpiar
from sast.ubicacion.geocodificar import Ejes, cruces_teoricos

# placa tras el número de la vía generadora: «# 12-20», «# 7A 41», «12 B BIS - 20»
_PLACA_TRAS_MARCA = re.compile(r"#\s*\d{1,3}\s*(?:[A-Z]\b)?\s*(?:BIS\b)?\s*(?:[A-Z]\b)?\s*-?\s*(\d{1,3})\b")
_GENERADORA = re.compile(r"#\s*(\d{1,3})(?!\d)\s*([A-WZ](?![A-Z]))?\s*(BIS\b)?")
CRUZA = {"DG": ("CR", "TV"), "TV": ("CL", "DG")}
_PLACA_SIN_MARCA = re.compile(r"^(\s+)(\d{1,3}\s*(?:[A-Z]\b)?\s*(?:BIS\b)?\s*(?:[A-Z]\b)?\s*-\s*\d{1,3})\b")
_PLACA_GUION = re.compile(r"\b\d{1,3}\s*(?:[A-Z]\b)?\s*(?:BIS\b)?\s*(?:[A-Z]\b)?\s*-\s*(\d{1,3})\b")
SIGUIENTE_MAX_M = 250.0     # el siguiente cruce debe estar a menos de esto (una cuadra larga)
CERCANOS_M = 150.0          # candidatos de un mismo cruce a menos de esto: se promedian
HUECO_AMPLIO_M = 100.0      # vías que no se tocan en la referencia pero pasan a menos de esto
PUNTO_EQUIPO_M = 150.0      # la cámara suele estar hasta una cuadra antes del cruce que nombra


@dataclass
class Resultado:
    metodo: str     # cruce | cruce_hueco | punto_equipo | cruce_aproximado | domiciliaria | domiciliaria_cuadra | ambigua | sin_punto
    tipo_direccion: str
    candidatos: list = field(default_factory=list)   # puntos EPSG:9377
    detalle: str = ""
    vias: str = ""
    alias: str = ""


def marcar_placa(texto: str) -> str:
    """«CARRERA 16 20-27» -> «CARRERA 16 # 20-27». Sin cambios si ya hay «#» o no calza."""
    t = limpiar(texto)
    if "#" in _MARCA_PLACA.sub(" # ", t):
        return t
    m = _VIA.search(t)
    if not m:
        return t
    resto = t[m.end():]
    r = _PLACA_SIN_MARCA.match(resto)
    if not r:
        return t
    return t[:m.end()] + " # " + resto[r.start(2):]


def placa(texto: str) -> int | None:
    t = _MARCA_PLACA.sub(" # ", limpiar(texto))
    m = _PLACA_TRAS_MARCA.search(t) or _PLACA_GUION.search(t)
    return int(m.group(1)) if m else None


class Geocodificador:
    def __init__(self, ejes: Ejes, equipos: dict[str, Point] | None = None):
        """equipos: {dirección oficial del equipo: punto EPSG:9377}."""
        self.ejes = ejes
        self._cruces: dict = {}
        self.puntos_equipo: dict = {}
        for texto, p in (equipos or {}).items():
            d = leer(texto)
            if d.tipo in ("cruce", "cruce_inferido"):
                a, _ = self.via_en_referencia(d.via_1)
                b, _ = self.via_en_referencia(d.via_2)
                self.puntos_equipo[(a.clave, b.clave)] = p
                self.puntos_equipo[(b.clave, a.clave)] = p

    def via_en_referencia(self, v: Via) -> tuple[Via, str]:
        """La vía tal cual o, si es una diagonal que no está, la calle homónima."""
        if v in self.ejes or v.tipo != "DG":
            return v, ""
        cl = Via("CL", v.num, v.letra, v.bis)
        return (cl, f"{v} -> {cl}") if cl in self.ejes else (v, "")

    def cruces(self, a: Via, b: Via) -> tuple[list[Point], str, str]:
        """-> (puntos, detalle, método: cruce | cruce_hueco | punto_equipo)."""
        k = (a.clave, b.clave)
        if k not in self._cruces:
            pts, det, met = [], "", "cruce"
            if a not in self.ejes or b not in self.ejes:
                det = "vía no está en la referencia: " + ", ".join(str(v) for v in (a, b) if v not in self.ejes)
            else:
                ga, gb = self.ejes.get(a), self.ejes.get(b)
                pts, det = cruces_teoricos(ga, gb)
                if not pts:
                    pa, pb = nearest_points(ga, gb)
                    d = pa.distance(pb)
                    if d <= HUECO_AMPLIO_M:
                        pts, det, met = [Point((pa.x + pb.x) / 2, (pa.y + pb.y) / 2)], f"hueco de {d:.0f} m", "cruce_hueco"
            pe = self.puntos_equipo.get(k)
            if pe is not None and (not pts or min(p.distance(pe) for p in pts) > PUNTO_EQUIPO_M):
                lejos = f"{min(p.distance(pe) for p in pts):.0f} m" if pts else det
                pts, det, met = [pe], f"coordenada del equipo SAST (referencia: {lejos})", "punto_equipo"
            self._cruces[k] = (pts, det, met)
        return self._cruces[k]

    def ubicar(self, texto: str) -> Resultado:
        texto = marcar_placa(texto)
        d = leer(texto)
        if d.tipo == "via_sola" and d.domiciliaria and d.via_1.tipo in CRUZA:
            m = _GENERADORA.search(_MARCA_PLACA.sub(" # ", d.texto))
            if m:
                for t in CRUZA[d.via_1.tipo]:
                    v2 = Via(t, int(m.group(1)), m.group(2) or "", bool(m.group(3)), inferida=True)
                    if v2 in self.ejes and self.cruces(d.via_1, v2)[0]:
                        d.vias.append(v2)
                        d.tipo = "cruce_inferido"
                        break
        vias = " × ".join(str(v) for v in d.vias)
        if d.tipo not in ("cruce", "cruce_inferido"):
            return Resultado("sin_punto", d.tipo, detalle=f"dirección de tipo {d.tipo}", vias=vias)
        (v1, al1), (v2, al2) = self.via_en_referencia(d.via_1), self.via_en_referencia(d.via_2)
        alias = "; ".join(a for a in (al1, al2) if a)
        if v1.clave == v2.clave or (v1.tipo == v2.tipo and alias):
            return Resultado("sin_punto", d.tipo, detalle="vías paralelas tras el alias", vias=vias, alias=alias)
        pts, det, met = self.cruces(v1, v2)
        if not pts:
            return Resultado("sin_punto", d.tipo, detalle=det, vias=vias, alias=alias)
        if len(pts) > 1:
            sep = max(p.distance(q) for p in pts for q in pts)
            if sep > CERCANOS_M:
                return Resultado("ambigua", d.tipo, pts, f"{len(pts)} cruces posibles a {sep:.0f} m", vias, alias)
            centro = Point(sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts))
            return Resultado("cruce_aproximado", d.tipo, [centro],
                             f"{len(pts)} cruces a {sep:.0f} m: se toma el centro", vias, alias)
        c0 = pts[0]
        n = placa(texto) if d.domiciliaria else None
        if n is None or met == "punto_equipo":
            return Resultado(met, d.tipo, [c0], det, vias, alias)
        sig = Via(v2.tipo, v2.num + 1)
        pts1, _, _ = self.cruces(v1, sig)
        pts1 = [p for p in pts1 if p.distance(c0) <= SIGUIENTE_MAX_M]
        if not pts1:
            return Resultado("domiciliaria_cuadra", d.tipo, [c0],
                             f"placa {n}; sin cruce con {sig} a ≤ {SIGUIENTE_MAX_M:.0f} m; {det}", vias, alias)
        c1 = min(pts1, key=c0.distance)
        dist = c0.distance(c1)
        f = min(n, dist) / dist if dist > 0 else 0.0
        p = Point(c0.x + f * (c1.x - c0.x), c0.y + f * (c1.y - c0.y))
        return Resultado("domiciliaria", d.tipo, [p],
                         f"placa {n} m hacia {sig} (cuadra de {dist:.0f} m); {det}", vias, alias)
