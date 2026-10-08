"""Geometría de cada cruce a partir de la red vial OSM (data/raw/red_vial/), en metros locales.

Todo se calcula en EPSG:9377 (CTM12) y se exporta en metros relativos al centro del cruce:
x hacia el este, y hacia el norte de la cuadrícula CTM12. Nada se mide en grados.

- brazos: tramos de vía que salen del cruce, agrupados por rumbo y nombre; cada parte sabe si
  el tránsito entra o sale (en OSM una vía de un solo sentido está digitalizada en ese sentido).
- cardinales: qué brazo es el acceso «norte», «sur», «este», «oeste» de la codificación (decisión
  30). Se ancla en las cámaras SAST, cuya dirección ANSV dice el sentido que vigilan (p. ej. «SUR -
  NORTE» = vigila a quien entra por el brazo sur); los demás brazos siguen el orden horario.
- trayectorias, líneas de pare y cebras para dibujar el cruce y mover los vehículos ilustrativos.

Anchos: OSM casi nunca trae carriles; se suponen 3,3 m por carril y se marca `supuesto`.
"""

from __future__ import annotations

import math
import re

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import linemerge, substring, unary_union

from sast.semaforos.accesos import CARDINALES

R_DIBUJO = 75.0      # radio exportado para dibujar
R_BRAZO = 28.0       # radio donde se lee el rumbo de cada brazo
R_CONEXION = 18.0    # una parte cuenta si pasa a menos de esto del centro
ANCHO_CARRIL = 3.3
CEBRA = 4.0          # ancho de la franja peatonal
TOL_RUMBO = 30.0

_CARRILES_DEFECTO = {  # (tipo_via, un solo sentido) -> carriles
    ("trunk", True): 2, ("primary", True): 2, ("secondary", True): 2, ("tertiary", True): 2,
    ("trunk", False): 4, ("primary", False): 4, ("secondary", False): 2, ("tertiary", False): 2,
}


def rumbo(dx: float, dy: float) -> float:
    """Rumbo en grados desde el norte de la cuadrícula, sentido horario."""
    return math.degrees(math.atan2(dx, dy)) % 360


def dif_angular(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def centro(nodos_osm: list[int], intersecciones: gpd.GeoDataFrame) -> Point:
    sel = intersecciones[intersecciones["nodo_id"].astype("int64").isin(nodos_osm)]
    if len(sel) != len(nodos_osm):
        faltan = set(nodos_osm) - set(sel["nodo_id"].astype("int64"))
        raise ValueError(f"Nodos OSM que no están en la red vial: {sorted(faltan)}")
    return Point(sel.geometry.x.mean(), sel.geometry.y.mean())


def _carriles(r) -> tuple[int, bool]:
    unico = r.sentido == "Unidireccional"
    if r.carriles == r.carriles and r.carriles:  # no NaN
        return int(r.carriles), False
    return _CARRILES_DEFECTO.get((r.tipo_via, unico), 1 if unico else 2), True


def _partes(linea: LineString, c: Point):
    """Parte una línea en el punto más cercano al centro: devuelve los pedazos orientados desde
    el centro hacia afuera, con el sentido de digitalización de cada uno."""
    s0 = linea.project(c)
    out = []
    if s0 > 1:
        out.append((substring(linea, s0, 0), False))     # recorrida al revés de la digitalización
    if linea.length - s0 > 1:
        out.append((substring(linea, s0, linea.length), True))
    return out


def _unir_tramos(vias: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Une tramos contiguos de una misma vía (mismo nombre, sentido y tipo). OSM parte una calle
    en cada nodo, y un tramo corto pegado al cruce no alcanzaría el radio donde se lee el brazo.
    En un solo sentido se respeta la dirección de digitalización."""
    filas = []
    for _, g in vias.groupby([vias["nomencla"].fillna("?"), "sentido", "tipo_via"], dropna=False):
        unida = linemerge(list(g.geometry), directed=(g["sentido"].iat[0] == "Unidireccional"))
        lineas = list(unida.geoms) if hasattr(unida, "geoms") else [unida]
        base = g.iloc[0]
        for ln in lineas:
            fila = base.copy()
            fila["geometry"] = ln
            filas.append(fila)
    return gpd.GeoDataFrame(filas, crs=vias.crs)


def brazos(c: Point, vias: gpd.GeoDataFrame, r_conexion: float = R_CONEXION) -> list[dict]:
    circulo = c.buffer(R_DIBUJO)
    cerca = _unir_tramos(vias[vias.intersects(c.buffer(R_DIBUJO + 60))])
    cerca = cerca[cerca.intersects(circulo)]
    partes = []
    for r in cerca.itertuples():
        geom = r.geometry.intersection(circulo)
        lineas = list(geom.geoms) if isinstance(geom, MultiLineString) else [geom]
        carriles, supuesto = _carriles(r)
        for ln in lineas:
            if ln.is_empty or ln.distance(c) > r_conexion:
                continue
            for pedazo, a_favor in _partes(ln, c):
                fin = pedazo.interpolate(1.0, normalized=True)
                ini = pedazo.interpolate(0.0)
                if fin.distance(c) < R_BRAZO:      # no llega al radio de lectura: es parte del cruce
                    continue
                if fin.distance(c) - ini.distance(c) < 12:   # no se aleja del cruce: es un conector
                    continue
                p = pedazo.intersection(c.buffer(R_BRAZO).exterior)
                p = p if isinstance(p, Point) else (list(p.geoms)[0] if hasattr(p, "geoms") and len(p.geoms) else fin)
                unico = r.sentido == "Unidireccional"
                partes.append({
                    "linea": pedazo, "rumbo": rumbo(p.x - c.x, p.y - c.y),
                    "via": r.nombre if isinstance(r.nombre, str) else None,
                    "nomencla": r.nomencla if isinstance(r.nomencla, str) else None,
                    "tipo_via": r.tipo_via, "unico": unico,
                    # a favor de la digitalización y hacia afuera = sale; en contra = entra
                    "entrante": (not unico) or (not a_favor), "saliente": (not unico) or a_favor,
                    "carriles": carriles, "ancho": round(carriles * ANCHO_CARRIL, 1),
                    "supuesto": supuesto, "osm_id": int(r.osm_id) if r.osm_id == r.osm_id else None,
                })
    grupos: list[dict] = []
    for p in sorted(partes, key=lambda p: p["rumbo"]):
        for g in grupos:
            mismo = (p["nomencla"] is None or g["nomencla"] is None or p["nomencla"] == g["nomencla"])
            if mismo and dif_angular(p["rumbo"], g["rumbo"]) <= TOL_RUMBO:
                g["partes"].append(p)
                g["nomencla"] = g["nomencla"] or p["nomencla"]
                g["via"] = g["via"] or p["via"]
                g["rumbo"] = _media_angular([q["rumbo"] for q in g["partes"]])
                break
        else:
            grupos.append({"rumbo": p["rumbo"], "nomencla": p["nomencla"], "via": p["via"], "partes": [p]})
    for i, g in enumerate(sorted(grupos, key=lambda g: g["rumbo"])):
        g["id"] = f"B{i + 1}"
    return sorted(grupos, key=lambda g: g["rumbo"])


def _media_angular(angulos: list[float]) -> float:
    x = sum(math.sin(math.radians(a)) for a in angulos)
    y = sum(math.cos(math.radians(a)) for a in angulos)
    return math.degrees(math.atan2(x, y)) % 360


_SENTIDO = re.compile(r"\((?:SENTIDO\s+)?(NORTE|SUR|ESTE|OESTE)\s*-\s*(NORTE|SUR|ESTE|OESTE)\)")


def cardinales(arms: list[dict], c: Point, camaras: list[dict], ejes: dict) -> list[str]:
    """Asigna «norte/este/sur/oeste» a cada brazo (decisión 30) y devuelve la evidencia.

    1. Las cámaras SAST orientan: su dirección ANSV dice de dónde viene el tránsito que vigilan
       («SUR - NORTE» = entra por el brazo sur); con eso se estima hacia dónde queda el «norte».
    2. `ejes` (config) dice qué vías forman el eje norte–sur y el este–oeste: un brazo de una vía
       del eje N–S es norte o sur según el rumbo; uno del eje E–O es este u oeste según el lado.
    3. Un brazo de otra vía queda sin acceso (se dibuja, pero ningún grupo lo controla).
    """
    def nombre(a):
        return a["nomencla"] or "sin nombre"

    evidencia, estimados = [], []
    for cam in camaras:
        m = _SENTIDO.search(cam["direccion_ansv"] or "")
        if not m:
            continue
        origen = m.group(1).lower()
        rb = rumbo(cam["x"] - c.x, cam["y"] - c.y)
        cand = [a for a in arms if any(p["entrante"] for p in a["partes"])]
        a = min(cand, key=lambda a: dif_angular(a["rumbo"], rb))
        estimados.append((a["rumbo"] - 90 * CARDINALES.index(origen)) % 360)
        evidencia.append(f"{cam['equipo']} vigila «{m.group(1)} - {m.group(2)}»; queda a "
                         f"{dif_angular(a['rumbo'], rb):.0f}° del brazo {a['id']} ({nombre(a)})")
    if not estimados:
        raise ValueError("Sin cámaras con sentido para orientar el cruce")
    norte = _media_angular(estimados)
    disp = max(dif_angular(e, norte) for e in estimados)
    evidencia.append(f"Norte de la codificación a {norte:.0f}° del norte de la cuadrícula CTM12"
                     + (f" (AVISO: las cámaras discrepan {disp:.0f}°)" if disp > 25 else ""))
    ns, eo = set(ejes["norte_sur"]), set(ejes["este_oeste"])
    for a in arms:
        rel = (a["rumbo"] - norte) % 360
        if nombre(a) in ns:
            a["cardinal"] = "norte" if dif_angular(rel, 0) < dif_angular(rel, 180) else "sur"
            ideal = 0 if a["cardinal"] == "norte" else 180
        elif nombre(a) in eo:
            a["cardinal"] = "este" if rel < 180 else "oeste"
            ideal = 90 if a["cardinal"] == "este" else 270
        else:
            a["cardinal"], ideal = None, rel
        a["desvio"] = round(dif_angular(rel, ideal), 1)
    for card in CARDINALES:
        mismos = [a for a in arms if a["cardinal"] == card]
        for a in sorted(mismos, key=lambda a: a["desvio"])[1:]:
            evidencia.append(f"AVISO: {a['id']} ({nombre(a)}) también cae en «{card}»; queda sin acceso")
            a["cardinal"] = None
        if not mismos:
            evidencia.append(f"Sin brazo para el acceso {card}")
    for a in arms:
        evidencia.append(f"{a['id']} {nombre(a)} rumbo {a['rumbo']:.0f}° -> "
                         f"{a['cardinal'] or 'sin acceso'}" + (f" (desvío {a['desvio']:.0f}°)" if a["cardinal"] else ""))
    return evidencia


# ------------------------------------------------------------------ dibujo y trayectorias
def _poligono_via(p: dict):
    return p["linea"].buffer(p["ancho"] / 2, cap_style="flat")


def radio_caja(arm: dict, arms: list[dict], c: Point) -> float:
    """Distancia al centro donde el brazo sale de las calzadas de los demás accesos (borde del
    cruce). Solo cuentan brazos con acceso y los primeros 30 m."""
    otras = unary_union([_poligono_via(p) for a in arms if a is not arm and a.get("cardinal")
                         for p in a["partes"]])
    r = 6.0
    for p in arm["partes"]:
        ln = p["linea"]
        for s in np.arange(0, min(ln.length, 30), 0.5):
            q = ln.interpolate(s)
            if otras.contains(q):
                r = max(r, q.distance(c))
    return round(r + 1.0, 1)


def _desplazar(ln: LineString, d: float) -> LineString:
    """Paralela a `d` m a la DERECHA del sentido de la línea."""
    if abs(d) < 0.05:
        return ln
    off = ln.offset_curve(-d)
    return off if isinstance(off, LineString) and not off.is_empty else ln


def _corte_desde_centro(ln: LineString, c: Point, r: float) -> float:
    """Distancia a lo largo de `ln` (orientada desde el centro) donde queda a `r` m del centro."""
    for s in np.arange(0, ln.length, 0.25):
        if ln.interpolate(s).distance(c) >= r:
            return float(s)
    return ln.length


def _bezier(p0, p1, p2, n=14):
    t = np.linspace(0, 1, n)[:, None]
    return ((1 - t) ** 2) * p0 + 2 * (1 - t) * t * p1 + (t ** 2) * p2


def _tangente(ln: LineString, al_inicio: bool):
    a = np.array(ln.coords[0] if al_inicio else ln.coords[-1])
    b = np.array(ln.interpolate(min(3, ln.length), normalized=False).coords[0] if al_inicio
                 else ln.interpolate(max(ln.length - 3, 0)).coords[0])
    v = (b - a) if al_inicio else (a - b)
    n = np.linalg.norm(v)
    return v / n if n else v


def carril_entrada(arm: dict) -> tuple[LineString, float] | None:
    """Línea por la que se ENTRA al cruce (orientada hacia el centro) y su ancho."""
    ps = [p for p in arm["partes"] if p["entrante"]]
    if not ps:
        return None
    p = max(ps, key=lambda p: p["carriles"])
    ln = LineString(list(p["linea"].coords)[::-1])
    if not p["unico"]:                       # doble sentido: carril derecho
        ln = _desplazar(ln, p["ancho"] / 4)
    return ln, p["ancho"] / (1 if p["unico"] else 2)


def carril_salida(arm: dict) -> tuple[LineString, float] | None:
    ps = [p for p in arm["partes"] if p["saliente"]]
    if not ps:
        return None
    p = max(ps, key=lambda p: p["carriles"])
    ln = p["linea"]
    if not p["unico"]:
        ln = _desplazar(ln, p["ancho"] / 4)
    return ln, p["ancho"] / (1 if p["unico"] else 2)


def trayectoria(arm_in: dict, arm_out: dict, c: Point) -> dict | None:
    ent, sal = carril_entrada(arm_in), carril_salida(arm_out)
    if ent is None or sal is None:
        return None
    lin, lout = ent[0], sal[0]
    rin, rout = arm_in["r_caja"], arm_out["r_caja"]
    # tramo de entrada: desde afuera hasta el borde del cruce
    s_in = lin.length - _corte_desde_centro(LineString(list(lin.coords)[::-1]), c, rin)
    a = substring(lin, 0, s_in)
    s_out = _corte_desde_centro(lout, c, rout)
    b = substring(lout, s_out, lout.length)
    if a.length < 5 or b.length < 5:
        return None
    p0, p2 = np.array(a.coords[-1]), np.array(b.coords[0])
    t0, t2 = _tangente(a, False), _tangente(b, True)
    # control: cruce de las tangentes, o punto medio si son casi paralelas
    m = np.array([t0, -t2]).T
    if abs(np.linalg.det(m)) > 0.15:
        k = np.linalg.solve(m, p2 - p0)
        p1 = p0 + t0 * k[0]
        if np.linalg.norm(p1 - (p0 + p2) / 2) > 60:
            p1 = (p0 + p2) / 2
    else:
        p1 = (p0 + p2) / 2
    curva = _bezier(p0, p1, p2)
    puntos = list(a.coords) + [tuple(x) for x in curva[1:-1]] + list(b.coords)
    ln = LineString(puntos)
    s_pare = max(a.length - CEBRA - 1.0, 0)
    return {"linea": ln, "s_pare": s_pare, "largo": ln.length}


def cebra(arm: dict, mitad: str, c: Point) -> dict | None:
    """Franja peatonal sobre la mitad de «entrada» o de «salida» del brazo, o sobre «toda» la vía,
    justo fuera del cruce."""
    sel = [p for p in arm["partes"] if mitad == "toda" or (p["entrante"] if mitad == "entrada" else p["saliente"])]
    if not sel:
        return None
    r = arm["r_caja"] + CEBRA / 2
    ang = math.radians(arm["rumbo"])
    u = np.array([math.sin(ang), math.cos(ang)])          # a lo largo del brazo (hacia afuera)
    n = np.array([u[1], -u[0]])                           # perpendicular (a la derecha mirando afuera)
    extremos = []
    for p in sel:
        ln = p["linea"]
        q = ln.interpolate(_corte_desde_centro(ln, c, r))
        q = np.array(q.coords[0])
        if p["unico"] or mitad == "toda":
            mitades = (-p["ancho"] / 2, p["ancho"] / 2)
        else:
            # doble sentido: quien entra va a la izquierda mirando hacia afuera
            mitades = (-p["ancho"] / 2, 0.0) if mitad == "entrada" else (0.0, p["ancho"] / 2)
        for d in mitades:
            extremos.append(q + n * d)
    proy = [float(np.dot(e - np.array(c.coords[0]), n)) for e in extremos]
    i, j = int(np.argmin(proy)), int(np.argmax(proy))
    a, b = extremos[i], extremos[j]
    return {"eje": [a, b], "poligono": [a - u * CEBRA / 2, b - u * CEBRA / 2, b + u * CEBRA / 2, a + u * CEBRA / 2]}


def linea_pare(arm: dict, c: Point) -> list | None:
    ent = carril_entrada(arm)
    if ent is None:
        return None
    ln, ancho = ent
    s = ln.length - _corte_desde_centro(LineString(list(ln.coords)[::-1]), c, arm["r_caja"] + CEBRA + 1.0)
    q = np.array(ln.interpolate(s).coords[0])
    t = _tangente(substring(ln, 0, s), False)
    n = np.array([t[1], -t[0]])
    return [q - n * ancho / 2, q + n * ancho / 2]


def cajon(arms: list[dict], c: Point):
    """Área del cruce (para el cajón amarillo de no bloqueo): envolvente de los cruces entre
    calzadas del eje norte–sur y del eje este–oeste."""
    ns = [_poligono_via(p) for a in arms if a.get("cardinal") in ("norte", "sur") for p in a["partes"]]
    eo = [_poligono_via(p) for a in arms if a.get("cardinal") in ("este", "oeste") for p in a["partes"]]
    if not ns or not eo:
        return None
    zona = unary_union(ns).intersection(unary_union(eo)).intersection(c.buffer(25))
    return None if zona.is_empty else zona.convex_hull
