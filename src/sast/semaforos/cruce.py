"""Geometría exportable y borrador de asignación grupo -> acceso de un cruce (decisiones 28 y 30).

El borrador NO es un hecho: lo valida Santiago (config/semaforos.yaml: asignacion). Confianza:
  alta    directo cuyo acceso vigila una cámara SAST con el mismo sentido
  media   directo o cruce peatonal ubicado por la codificación y la geometría OSM, sin cámara
  baja    «Flecha»: el giro se deduce de la matriz y de con quién arranca; por confirmar
"""

from __future__ import annotations

from itertools import combinations

import geopandas as gpd
from shapely.geometry import MultiLineString, Point

from sast.rutas import CRS_GEO
from sast.semaforos import geometria as G
from sast.semaforos.accesos import candidatos_flecha, conflicto, movimiento
from sast.semaforos.tiempos import NO_ROJO, estado

TEXTO_GIRO = {"directo": "directo", "izquierda": "giro a la izquierda", "derecha": "giro a la derecha"}


def _xy(pts, c: Point) -> list[list[float]]:
    return [[round(float(x) - c.x, 1), round(float(y) - c.y, 1)] for x, y in pts]


def _texto_mov(m: dict) -> str:
    return f"{TEXTO_GIRO[m['giro']]} desde el {m['acceso']} (sale al {m['sale_por']})"


def armar(cfg: dict, inter: dict, vias: gpd.GeoDataFrame, nodos: gpd.GeoDataFrame,
          camaras: list[dict]) -> dict:
    """`inter`: lo leído del PDF (grupos, matriz, planes). `camaras`: equipos SAST del punto en
    EPSG:9377 con `direccion_ansv`. Devuelve geometría (metros locales), borrador y hallazgos."""
    c = G.centro(cfg["centro"]["nodos_osm"], nodos)
    arms = G.brazos(c, vias, cfg["centro"].get("radio_conexion", G.R_CONEXION))
    evidencia = G.cardinales(arms, c, camaras, cfg["centro"]["ejes"])
    for a in arms:
        a["r_caja"] = G.radio_caja(a, arms, c) if a["cardinal"] else None
    por_card = {a["cardinal"]: a for a in arms if a["cardinal"]}
    hallazgos = [("AVISO", "orientacion", e[7:]) for e in evidencia if e.startswith("AVISO")]

    # cámaras que anclan cada acceso (mismo sentido)
    anclado = {}
    for cam in camaras:
        m = G._SENTIDO.search(cam["direccion_ansv"] or "")
        if m:
            anclado[m.group(1).lower()] = cam["equipo"]

    grupos = inter["grupos"]
    amigos = inter["matriz"]["amigos"]
    movs, asign = {}, {}
    for g in grupos:
        m = movimiento(g["nombre"])
        if m["tipo"] == "flecha":
            cands = candidatos_flecha(g["id"], grupos, amigos)
            # arranca con el amigo vehicular de igual TIV en la mayoría de planes
            votos = {}
            for p in inter["planes"]:
                tiv = p["tiempos"][g["id"]]["tiv"]
                for h in grupos:
                    mh = movimiento(h["nombre"])
                    if h["id"] != g["id"] and mh["tipo"] == "vehicular" and p["tiempos"][h["id"]]["tiv"] == tiv:
                        votos[mh["acceso"]] = votos.get(mh["acceso"], 0) + 1
            cands.sort(key=lambda k: -votos.get(k["acceso"], 0))
            if cands:
                m = {**m, **cands[0], "tipo": "vehicular", "codigo": None}
                alternativas = "; ".join(_texto_mov(k) for k in cands[1:]) or "ninguna"
                asign[g["id"]] = {"confianza": "baja", "evidencia":
                                  f"Compatible solo con giros que no cruzan a sus amigos; arranca con el "
                                  f"acceso {cands[0]['acceso']} en {votos.get(cands[0]['acceso'], 0)} de "
                                  f"{len(inter['planes'])} planes. Alternativas: {alternativas}. POR CONFIRMAR."}
            else:
                hallazgos.append(("AVISO", "flecha", f"{g['id']}: ningún giro es compatible con sus amigos"))
                asign[g["id"]] = {"confianza": "baja", "evidencia": "Sin giro compatible"}
        elif m["tipo"] == "vehicular":
            ok = m["acceso"] in por_card and m["sale_por"] in por_card
            conf = "alta" if anclado.get(m["acceso"]) and ok else ("media" if ok else "baja")
            ev = f"Nombre «{g['nombre']}» = movimiento {m['codigo']} (codificación SDM)"
            if anclado.get(m["acceso"]):
                ev += f"; la cámara {anclado[m['acceso']]} vigila el tránsito que entra desde el {m['acceso']}"
            if not ok:
                ev += "; FALTA el brazo de entrada o de salida en la red OSM"
            asign[g["id"]] = {"confianza": conf, "evidencia": ev}
        else:
            ok = m["brazo"] in por_card
            asign[g["id"]] = {"confianza": "media" if ok else "baja",
                              "evidencia": f"Nombre «{g['nombre']}» = cruce {m['codigo']} (codificación SDM): "
                                           f"mitad de {m['mitad']} del brazo {m['brazo']}"
                                           + ("" if ok else "; FALTA ese brazo en la red OSM")}
        movs[g["id"]] = m

    # ---- chequeo de seguridad: la matriz permite juntos pares que se cruzan
    planes = inter["planes"]

    def chocan(i, j):
        a, b = movs[i], movs[j]
        if a["tipo"] == "vehicular" and b["tipo"] == "vehicular":
            return conflicto(a, b)
        if a["tipo"] == "peatonal" and b["tipo"] == "peatonal":
            return False
        p, v = (a, b) if a["tipo"] == "peatonal" else (b, a)
        return (v["acceso"] == p["brazo"]) if p["mitad"] == "entrada" else (v["sale_por"] == p["brazo"])

    tipo = {g["id"]: g["tipo"] for g in grupos}
    for i, j in combinations([g["id"] for g in grupos], 2):
        if (i, j) in amigos and chocan(i, j):
            juntos = []
            for p in planes:
                c_ = p["ciclo"]
                n = sum(estado(p["tiempos"][i], tipo[i], k + 0.5, c_) in NO_ROJO and
                        estado(p["tiempos"][j], tipo[j], k + 0.5, c_) in NO_ROJO for k in range(c_))
                if n:
                    juntos.append(f"{p['id']} {n} s")
            hallazgos.append(("AVISO" if juntos else "INFO", "matriz_permisiva",
                              f"La matriz deja a {i} ({movs[i].get('codigo') or 'flecha'}) y {j} "
                              f"({movs[j].get('codigo') or 'flecha'}) en verde a la vez aunque sus trayectorias "
                              f"se cruzan; " + (f"corren juntos en {', '.join(juntos)}" if juntos
                                                else "en los planes nunca coinciden")))

    # ---- geometría exportable
    tray, pare, cebras = {}, {}, {}
    for gid, m in movs.items():
        if m["tipo"] == "vehicular" and m.get("acceso") in por_card and m.get("sale_por") in por_card:
            t = G.trayectoria(por_card[m["acceso"]], por_card[m["sale_por"]], c)
            if t is None:
                hallazgos.append(("AVISO", "trayectoria", f"{gid}: no se pudo trazar {_texto_mov(m)}"))
                continue
            tray[gid] = {"puntos": _xy(t["linea"].coords, c), "s_pare": round(t["s_pare"], 1),
                         "largo": round(t["largo"], 1)}
            lp = G.linea_pare(por_card[m["acceso"]], c)
            if lp is not None:
                pare[gid] = _xy(lp, c)
        elif m["tipo"] == "peatonal" and m["brazo"] in por_card:
            z = G.cebra(por_card[m["brazo"]], m["mitad"], c)
            if z is None:
                hallazgos.append(("AVISO", "cebra", f"{gid}: el brazo {m['brazo']} no tiene mitad de {m['mitad']}"))
                continue
            cebras[gid] = {"eje": _xy(z["eje"], c), "poligono": _xy(z["poligono"], c)}
    # señalización del inventario de Santiago: cebras sin grupo peatonal y cajón amarillo
    senal = cfg.get("senalizacion") or {}
    for card in senal.get("cebras_sin_semaforo", []):
        if card not in por_card:
            hallazgos.append(("AVISO", "cebra", f"Cebra sin semáforo en el brazo {card}, que no existe en OSM"))
            continue
        z = G.cebra(por_card[card], "toda", c)
        if z is not None:
            cebras[f"sin_semaforo_{card}"] = {"eje": _xy(z["eje"], c), "poligono": _xy(z["poligono"], c)}
    caja = G.cajon(arms, c) if senal.get("cajon_amarillo") else None
    controlados = {m["acceso"] for m in movs.values() if m["tipo"] == "vehicular" and m.get("acceso")}
    for card, a in por_card.items():
        if any(p["entrante"] for p in a["partes"]) and card not in controlados:
            hallazgos.append(("AVISO", "acceso_sin_grupo", f"El brazo {card} ({a['nomencla'] or 'sin nombre'}) "
                              "recibe tránsito en OSM pero ningún grupo vehicular lo controla"))

    # vías para dibujar: las que forman el cruce y las del contexto cercano
    circulo = c.buffer(G.R_DIBUJO)
    dibujo = []
    for r in G._unir_tramos(vias[vias.intersects(c.buffer(G.R_DIBUJO + 60))]).itertuples():
        geom = r.geometry.intersection(circulo)
        if geom.is_empty:
            continue
        carr, sup = G._carriles(r)
        for ln in (geom.geoms if isinstance(geom, MultiLineString) else [geom]):
            if ln.length < 3:
                continue
            dibujo.append({"nomencla": r.nomencla if isinstance(r.nomencla, str) else None,
                           "tipo_via": r.tipo_via, "unico": r.sentido == "Unidireccional",
                           "carriles": carr, "ancho": round(carr * G.ANCHO_CARRIL, 1), "supuesto": sup,
                           "contexto": ln.distance(c) > cfg["centro"].get("radio_conexion", G.R_CONEXION),
                           "puntos": _xy(ln.coords, c)})
    sem = nodos[(nodos["semaforo"] == "Sí") & (nodos.distance(c) < G.R_DIBUJO)]
    origen = gpd.GeoSeries([c], crs=nodos.crs).to_crs(CRS_GEO).iloc[0]
    norte = next(float(e.split(" a ")[1].split("°")[0]) for e in evidencia if e.startswith("Norte de la"))
    geo = {
        "origen": {"lon": round(origen.x, 7), "lat": round(origen.y, 7)},
        "norte_codificacion": round(norte, 1),
        "vias": dibujo,
        "brazos": [{"id": a["id"], "cardinal": a["cardinal"], "rumbo": round(a["rumbo"], 1),
                    "nomencla": a["nomencla"], "r_caja": a["r_caja"],
                    "entrante": any(p["entrante"] for p in a["partes"]),
                    "saliente": any(p["saliente"] for p in a["partes"]),
                    "ancho_supuesto": any(p["supuesto"] for p in a["partes"])} for a in arms],
        "trayectorias": tray, "lineas_pare": pare, "cebras": cebras,
        "cajon_amarillo": _xy(caja.exterior.coords, c) if caja is not None else None,
        "camaras": [{"equipo": k["equipo"], "x": round(k["x"] - c.x, 1), "y": round(k["y"] - c.y, 1)}
                    for k in camaras],
        "semaforos_osm": [[round(p.x - c.x, 1), round(p.y - c.y, 1)] for p in sem.geometry],
        "evidencia": evidencia,
    }
    borrador = {}
    for g in grupos:
        m = movs[g["id"]]
        if m["tipo"] == "peatonal":
            texto, brazo = f"cruce {m['codigo']}: mitad de {m['mitad']} del brazo {m['brazo']}", m["brazo"]
        elif m.get("acceso"):
            texto, brazo = _texto_mov(m), m["acceso"]
        else:
            texto, brazo = "sin movimiento compatible", None
        a = por_card.get(brazo)
        borrador[g["id"]] = {"nombre": g["nombre"], "tipo": g["tipo"], "codigo": m.get("codigo"),
                             "movimiento": texto, "acceso": m.get("acceso"), "sale_por": m.get("sale_por"),
                             "brazo": brazo, "mitad": m.get("mitad"),
                             "via": (a["nomencla"] or "sin nombre") if a else None,
                             **asign[g["id"]]}
    return {"geometria": geo, "borrador": borrador, "hallazgos": hallazgos}
