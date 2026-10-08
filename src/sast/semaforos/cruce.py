"""Geometría exportable y borrador de asignación grupo -> acceso de un cruce (decisiones 28 y 30).

El borrador NO es un hecho: lo valida Santiago (config/semaforos.yaml: asignacion). Confianza:
  alta    directo cuyo acceso vigila una cámara SAST con el mismo sentido
  media   directo o cruce peatonal ubicado por la codificación y la geometría OSM, sin cámara
  baja    «Flecha»: el giro se deduce de la matriz y de con quién arranca; por confirmar
"""

from __future__ import annotations

import json
import math
from itertools import combinations

import geopandas as gpd
from shapely.geometry import MultiLineString, Point

from sast.rutas import CRS_GEO
from sast.semaforos import geometria as G
from sast.semaforos.accesos import candidatos_flecha, conflicto, movimiento
from sast.semaforos.tiempos import NO_ROJO, estado

VISTA_R = 31.0   # media altura del diagrama del tablero (tablero/js/vistas/diagrama.js: R_VISTA)
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
    # correcciones de campo de Santiago sobre OSM (config: geometria); sin ellas, todo sale de OSM
    aj = cfg.get("geometria") or {}
    r_dib = aj.get("radio_dibujo", G.R_DIBUJO)
    vias = G.aplicar_sentidos(vias, c, aj.get("sentidos") or {}, r_dib + 60)
    arms = G.brazos(c, vias, cfg["centro"].get("radio_conexion", G.R_CONEXION), r_dib)
    evidencia = G.cardinales(arms, c, camaras, cfg["centro"]["ejes"], aj.get("accesos"))
    norte = next(float(e.split(" a ")[1].split("°")[0]) for e in evidencia if e.startswith("Norte de la"))
    por_card = {a["cardinal"]: a for a in arms if a["cardinal"]}
    # salida distinta de la entrada (geometria.salidas): {«este»: «KR 19»} = quien sale al este lo hace
    # por la Carrera 19, aunque el acceso este sea otra vía
    por_sal = dict(por_card)
    for card, nom in (aj.get("salidas") or {}).items():
        ideal = 90 * G.CARDINALES.index(card)
        cands = [a for a in arms if (a["nomencla"] or "sin nombre") == nom and any(q["saliente"] for q in a["partes"])]
        if not cands:
            raise ValueError(f"{cfg['id']}: geometria.salidas: no hay un brazo de salida «{nom}» para {card}")
        por_sal[card] = min(cands, key=lambda a: G.dif_angular((a["rumbo"] - norte) % 360, ideal))
        evidencia.append(f"{por_sal[card]['id']} ({nom}) es la salida {card} por corrección de campo "
                         "(config: geometria.salidas)")
    usados = {id(a) for a in [*por_card.values(), *por_sal.values()]}
    for a in arms:
        a["r_caja"] = G.radio_caja(a, arms, c) if id(a) in usados else None
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
            ok = m["acceso"] in por_card and m["sale_por"] in por_sal
            conf = "alta" if anclado.get(m["acceso"]) and ok else ("media" if ok else "baja")
            ev = f"Nombre «{g['nombre']}» = movimiento {m['codigo']} (codificación SDM)"
            if anclado.get(m["acceso"]):
                ev += (f"; la cámara {anclado[m['acceso']]} vigila el tránsito que entra desde el {m['acceso']} "
                       "(la misma cámara orienta el cruce: no es evidencia independiente del acceso)")
            entra = [p for a in arms if a["cardinal"] == m["acceso"] for p in a["partes"] if p["entrante"]]
            if entra and all(p["unico"] for p in entra):
                ev += ("; ese brazo es de un solo sentido y entra al cruce (corrección de campo de Santiago; "
                       "OSM lo tiene de doble sentido)" if any(p.get("corregido") for p in entra)
                       else "; en OSM ese brazo es de un solo sentido y entra al cruce")
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

    # correcciones validadas por Santiago (config: asignacion.cambios) antes de trazar la geometría
    for gid, cambio in ((cfg.get("asignacion") or {}).get("cambios") or {}).items():
        if gid not in movs:
            hallazgos.append(("ERROR", "asignacion", f"La corrección validada nombra {gid}, que no existe"))
            continue
        movs[gid] = {**movs[gid], **{k: v for k, v in cambio.items() if k in ("acceso", "sale_por", "giro", "brazo", "mitad")}}
        if movs[gid].get("tipo") == "flecha":
            movs[gid]["tipo"] = "vehicular"
        quien = cfg["asignacion"].get("validado_por")
        asign[gid] = ({"confianza": "validada", "evidencia": f"Corregido por {quien}"} if quien else
                      {"confianza": "media", "evidencia": "Corrección de campo de Santiago; pendiente de su revisión"})

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
            hallazgos.append(("AVISO", "matriz_permisiva",
                              f"La matriz deja a {i} ({movs[i].get('codigo') or 'flecha'}) y {j} "
                              f"({movs[j].get('codigo') or 'flecha'}) en verde a la vez aunque sus trayectorias "
                              f"se cruzan; " + (f"corren juntos en {', '.join(juntos)}" if juntos
                                                else "en los planes nunca coinciden")))

    # ---- geometría exportable
    tray, pare, cebras = {}, {}, {}
    pare_m = aj.get("pare_m") or {}
    red = G.grafo_vial(vias, c, r_dib) if aj.get("por_la_red") else None
    for gid, m in movs.items():
        if m["tipo"] == "vehicular" and m.get("acceso") in por_card and m.get("sale_por") in por_sal:
            a_in, a_out = por_card[m["acceso"]], por_sal[m["sale_por"]]
            if red is not None:
                t = G.trayectoria_red(a_in, a_out, c, red, pare_m.get(m["acceso"]))
            else:
                t = G.trayectoria(a_in, a_out, c)
            if t is None:
                hallazgos.append(("AVISO", "trayectoria", f"{gid}: no se pudo trazar {_texto_mov(m)}"))
                continue
            if red is None and m["acceso"] in pare_m:
                t["s_pare"] = G.s_a_distancia(t["linea"], c, pare_m[m["acceso"]])
            tray[gid] = {"puntos": _xy(t["linea"].coords, c), "s_pare": round(t["s_pare"], 1),
                         "largo": round(t["largo"], 1)}
            if red is not None or m["acceso"] in pare_m:
                ent = G.carril_entrada(a_in)
                lp = G.linea_en(t["linea"], t["s_pare"], t.get("ancho_pare") or (ent[1] if ent else 3.3))
            else:
                lp = G.linea_pare(a_in, c)
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
    circulo = c.buffer(r_dib)
    dibujo = []
    for r in G._unir_tramos(vias[vias.intersects(c.buffer(r_dib + 60))]).itertuples():
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
    sem = nodos[(nodos["semaforo"] == "Sí") & (nodos.distance(c) < r_dib)]
    origen = gpd.GeoSeries([c], crs=nodos.crs).to_crs(CRS_GEO).iloc[0]
    # vista del diagrama: si alguna línea de pare o cebra queda lejos del centro (cruce largo), se
    # encuadra todo; si no, el diagrama queda como siempre (centro y 31 m de media altura)
    marcas = [q for l in pare.values() for q in l] + [q for z in cebras.values() for q in z["poligono"]]
    vista = None
    if marcas and max(math.hypot(x, y) for x, y in marcas) > VISTA_R - 5:
        # encuadre en el plano de la codificación (norte arriba, como el diagrama), con margen extra
        # arriba (título de la pantalla) y abajo (botones de planes); el centro vuelve a metros CTM12
        n = math.radians(norte)
        rot = [(x * math.cos(n) - y * math.sin(n), x * math.sin(n) + y * math.cos(n)) for x, y in marcas + [(0.0, 0.0)]]
        x0, x1 = min(u for u, _ in rot) - 12, max(u for u, _ in rot) + 12
        y0, y1 = min(v for _, v in rot) - 14, max(v for _, v in rot) + 20
        cu, cv = (x0 + x1) / 2, (y0 + y1) / 2
        vista = {"x": round(cu * math.cos(n) + cv * math.sin(n), 1), "y": round(-cu * math.sin(n) + cv * math.cos(n), 1),
                 "r": round(max(VISTA_R, (x1 - x0) / 2, (y1 - y0) / 2), 1)}
    geo = {
        "origen": {"lon": round(origen.x, 7), "lat": round(origen.y, 7)},
        "norte_codificacion": round(norte, 1),
        "vias": dibujo,
        "brazos": [{"id": a["id"], "cardinal": a["cardinal"], "rumbo": round(a["rumbo"], 1),
                    "nomencla": a["nomencla"], "r_caja": a["r_caja"],
                    "entrante": any(p["entrante"] for p in a["partes"]),
                    "saliente": any(p["saliente"] for p in a["partes"]),
                    "salida": next((k for k, v in por_sal.items() if v is a and por_card.get(k) is not a), None),
                    "ancho_supuesto": any(p["supuesto"] for p in a["partes"])} for a in arms],
        "trayectorias": tray, "lineas_pare": pare, "cebras": cebras,
        "cajon_amarillo": _xy(caja.exterior.coords, c) if caja is not None else None,
        "camaras": [{"equipo": k["equipo"], "x": round(k["x"] - c.x, 1), "y": round(k["y"] - c.y, 1)}
                    for k in camaras],
        "semaforos_osm": [[round(p.x - c.x, 1), round(p.y - c.y, 1)] for p in sem.geometry],
        "evidencia": evidencia,
        **({"vista": vista} if vista else {}),
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
        a = por_card.get(brazo) or por_sal.get(brazo)
        borrador[g["id"]] = {"nombre": g["nombre"], "tipo": g["tipo"], "codigo": m.get("codigo"),
                             "movimiento": texto, "acceso": m.get("acceso"), "sale_por": m.get("sale_por"),
                             "brazo": brazo, "mitad": m.get("mitad"),
                             "via": (a["nomencla"] or "sin nombre") if a else None,
                             **asign[g["id"]]}
    huella = json.dumps(cfg.get("asignacion") or {}, sort_keys=True, default=str, ensure_ascii=False)
    return {"geometria": geo, "borrador": borrador, "hallazgos": hallazgos, "asignacion_usada": huella}
