# Vendorizado de ~/Claude_code/Analisis_siniestralidad/src/ubicacion/geocodificar.py (commit d057993, 2026-10-06).
# Solo se cambian las importaciones; la lógica es la del original.
"""Punto teórico de una dirección sobre los ejes viales, y distancia al punto registrado.

Referencias: nomenclatura vial urbana del IGAC (2021, POT), con los nombres oficiales, y
red OSM del repo (corte 2026-08-03). Ninguna basta sola: el IGAC no trae ejes de vías
principales del centro (p. ej. la Carrera 12 o la Carrera 19 sin letra) y OSM no tiene
nombre en el 29 % de su longitud urbana. Los ejes de cada vía son la unión de ambas,
recortada a la cabecera (perímetro urbano 2023 más `MARGEN_CABECERA_M`): los centros
poblados repiten nombres («CALLE 13» de un corregimiento a 27 km). Todo en EPSG:9377.

Reglas [Nuestra]:
- Una vía se busca por su llave exacta (tipo, número, letra, BIS). No se relaja la letra:
  la Calle 13 y la Calle 13A son vías distintas, a una cuadra.
- El cruce teórico es la intersección de los ejes de las dos vías. Si no se tocan, el punto
  medio de la menor distancia, solo si es ≤ `HUECO_MAX_M`. Los puntos de intersección a
  menos de `AGRUPAR_M` entre sí (dobles calzadas, glorietas) son un solo cruce.
- Si dos vías se cruzan en varios lugares (vías curvas), se toma el más cercano al punto
  registrado y se reporta cuántos había: la dirección no basta para decidir.
- Si las dos vías no se cruzan en la referencia, no hay punto teórico: con referencias
  incompletas no se puede saber si falla la dirección o la referencia. Se guardan la
  distancia a cada vía (`dist_via_1_m`, `dist_via_2_m`) y la clasificación decide
  (`src/ubicacion/controles.py`).
"""

from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import numpy as np
from shapely import Point, get_parts, unary_union
from shapely.ops import nearest_points

from sast.rutas import CRS_METRICO
from sast.ubicacion.direccion import COMPLEMENTO, Direccion, Via, leer_nombre_via

HUECO_MAX_M = 30.0
MARGEN_CABECERA_M = 1000.0
AGRUPAR_M = 60.0


@dataclass
class Ejes:
    """Ejes viales agrupados por llave de vía: {clave: geometría unida} y, por llave, de qué
    referencias salió."""
    fuente: str
    por_clave: dict
    origen: dict

    def __contains__(self, via: Via) -> bool:
        return via.clave in self.por_clave

    def get(self, via: Via):
        return self.por_clave.get(via.clave)


def _tramos_por_clave(gdf: gpd.GeoDataFrame, columna: str, zona=None) -> dict:
    g = gdf[gdf[columna].notna()].to_crs(CRS_METRICO)
    if zona is not None:
        g = g[g.intersects(zona)]
    grupos: dict = {}
    for nombre, geom in zip(g[columna], g.geometry):
        for parte in str(nombre).split(";"):        # OSM: «A;B» cuenta para las dos
            via = leer_nombre_via(parte)
            if via is not None:
                grupos.setdefault(via.clave, []).append(geom)
    return grupos


def preparar_ejes(referencias: dict, zona=None) -> Ejes:
    """referencias = {'IGAC': (gdf, columna), 'OSM': (gdf, columna)}. Lo que no es una vía
    numerada («ZONA RURAL», «AVENIDA SIMON BOLIVAR») queda fuera."""
    grupos, origen = {}, {}
    for fuente, (gdf, columna) in referencias.items():
        for clave, geoms in _tramos_por_clave(gdf, columna, zona).items():
            grupos.setdefault(clave, []).extend(geoms)
            origen.setdefault(clave, set()).add(fuente)
    return Ejes("+".join(referencias), {k: unary_union(v) for k, v in grupos.items()},
                {k: "+".join(sorted(v)) for k, v in origen.items()})


def acuerdo_referencias(igac: gpd.GeoDataFrame, col_igac: str, osm: gpd.GeoDataFrame,
                        col_osm: str, zona=None, tolerancia_m: float = 30.0) -> dict:
    """Control de la referencia: en las vías que tienen las dos, qué fracción de la longitud
    del IGAC queda a ≤ `tolerancia_m` del eje OSM del mismo nombre. Una fracción baja indica
    nombres que no coinciden entre fuentes."""
    a, b = _tramos_por_clave(igac, col_igac, zona), _tramos_por_clave(osm, col_osm, zona)
    comunes = set(a) & set(b)
    total = cerca = 0.0
    discrepantes = []
    for k in comunes:
        ga, gb = unary_union(a[k]), unary_union(b[k]).buffer(tolerancia_m)
        la, lc = ga.length, ga.intersection(gb).length
        total, cerca = total + la, cerca + lc
        if la > 0 and lc / la < 0.5:
            discrepantes.append(str(Via(*k)))
    return {"solo_igac": len(set(a) - set(b)), "solo_osm": len(set(b) - set(a)),
            "comunes": len(comunes), "fraccion_longitud_coincide": cerca / total if total else float("nan"),
            "vias_discrepantes": sorted(discrepantes)}


def _agrupar(puntos: list[Point]) -> list[Point]:
    """Centroides de los grupos de puntos a menos de AGRUPAR_M (enlace simple)."""
    if not puntos:
        return []
    xy = np.array([(p.x, p.y) for p in puntos])
    grupo = list(range(len(xy)))

    def raiz(i):
        while grupo[i] != i:
            grupo[i] = grupo[grupo[i]]
            i = grupo[i]
        return i

    for i in range(len(xy)):
        for j in range(i + 1, len(xy)):
            if np.hypot(*(xy[i] - xy[j])) <= AGRUPAR_M:
                grupo[raiz(i)] = raiz(j)
    centros = {}
    for i in range(len(xy)):
        centros.setdefault(raiz(i), []).append(xy[i])
    return [Point(np.mean(v, axis=0)) for v in centros.values()]


def cruces_teoricos(a, b) -> tuple[list[Point], str]:
    """Puntos donde se cruzan las geometrías `a` y `b` -> (puntos, detalle)."""
    inter = a.intersection(b)
    puntos = []
    for p in get_parts(inter):
        if p.geom_type == "Point":
            puntos.append(p)
        elif not p.is_empty:                     # tramo compartido: su centro
            puntos.append(p.centroid)
    if puntos:
        return _agrupar(puntos), "intersección"
    pa, pb = nearest_points(a, b)
    hueco = pa.distance(pb)
    if hueco <= HUECO_MAX_M:
        return [Point((pa.x + pb.x) / 2, (pa.y + pb.y) / 2)], f"hueco de {hueco:.0f} m"
    return [], f"no se cruzan (más cerca: {hueco:.0f} m)"


def _cruce_mas_cercano(p: Point, ga, gb):
    puntos, detalle = cruces_teoricos(ga, gb)
    if not puntos:
        return None, 0, detalle
    return min(puntos, key=p.distance), len(puntos), detalle


def concordancia(d: Direccion, x: float, y: float, ejes: Ejes) -> dict:
    """Concordancia del punto registrado (x, y en EPSG:9377) con su dirección.

    metodo: «cruce» (las dos vías están en la referencia y se cruzan), «sin_cruce» (están
    pero no se cruzan), «una_via» (solo una vía interpretable o encontrada) o «ninguno»
    (con `motivo`). dist_m: al cruce teórico (cruce) o a la vía (una_via); NaN si no aplica.
    """
    r = {"metodo": "ninguno", "referencia": "", "dist_m": np.nan, "dist_via_1_m": np.nan,
         "dist_via_2_m": np.nan, "n_cruces": 0, "x_teo": np.nan, "y_teo": np.nan,
         "motivo": "", "dist_invertida_m": np.nan}
    if np.isnan(x) or np.isnan(y):
        r["motivo"] = "coordenada no válida"
        return r
    if d.tipo == "paralelas":
        r["motivo"] = "dos vías paralelas: no hay cruce"
        return r
    if not d.vias:
        r["motivo"] = f"dirección de tipo {d.tipo}"
        return r
    p = Point(x, y)
    presentes = [v for v in d.vias[:2] if v in ejes]
    faltan = [str(v) for v in d.vias[:2] if v not in ejes]
    if not presentes:
        r["motivo"] = "vía no está en la nomenclatura: " + ", ".join(faltan)
        return r
    r["referencia"] = " | ".join(ejes.origen[v.clave] for v in presentes)
    r["dist_via_1_m"] = p.distance(ejes.get(presentes[0]))
    if len(presentes) == 1:
        r.update(metodo="una_via", dist_m=r["dist_via_1_m"],
                 motivo="solo una vía" if d.tipo == "via_sola"
                 else "vía no está en la nomenclatura: " + ", ".join(faltan))
        return r
    ga, gb = ejes.get(d.via_1), ejes.get(d.via_2)
    r["dist_via_2_m"] = p.distance(gb)
    cerca, n, detalle = _cruce_mas_cercano(p, ga, gb)
    r["motivo"] = detalle
    if cerca is None:
        r["metodo"] = "sin_cruce"
    else:
        r.update(metodo="cruce", dist_m=p.distance(cerca), n_cruces=n,
                 x_teo=cerca.x, y_teo=cerca.y)
    # calle y carrera intercambiadas: CL a × CR b -> CL b × CR a
    v1, v2 = d.via_1, d.via_2
    if {v1.tipo, v2.tipo} == set(COMPLEMENTO):
        i1 = Via(v1.tipo, v2.num, v2.letra, v2.bis)
        i2 = Via(v2.tipo, v1.num, v1.letra, v1.bis)
        if i1 in ejes and i2 in ejes:
            c_i, _, _ = _cruce_mas_cercano(p, ejes.get(i1), ejes.get(i2))
            if c_i is not None:
                r["dist_invertida_m"] = p.distance(c_i)
    return r
