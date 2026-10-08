"""Página interna para que Santiago valide el borrador grupo -> acceso (decisión 28).

Una sección por cruce: mapa sobre imagen satelital (Esri World Imagery) con la geometría OSM,
las trayectorias propuestas, cebras, líneas de pare y cámaras; la tabla de asignación con su
confianza y evidencia; el diagrama de cada plan; la matriz muestreada y preguntas puntuales.
No se publica (va en outputs/, no en tablero/).
"""

from __future__ import annotations

import base64
import html
import json
import math
from pathlib import Path

import pandas as pd
from pyproj import Transformer

from sast.rutas import CRS_GEO, CRS_METRICO
from sast.semaforos.tiempos import estado

COLORES = ["#2b7bff", "#ff7a1a", "#18b26b", "#e0245e", "#8b5cf6", "#00a3a3", "#b8860b"]
ESTADO_COLOR = {"verde": "#1fae5b", "amarillo": "#f2b705", "despeje": "#e8635a", "preparacion": "#c0392b",
                "rojo": "#c0392b"}
PREGUNTAS = {
    "la-vina": ["¿El semáforo es un solo cruce (Cra 9 × Cl 17)? El controlador dice «Cra 9 con Calle 16B» y OSM "
                "también marca semáforo en Cl 17 × Kr 8 y Cl 16B × Kr 9."],
    "mercado": ["¿El cruce es la Calle 21 con la vía que OSM llama Carrera 16 al sur y deja sin nombre al norte "
                "(la «Transversal 12» del equipo 032)? El controlador dice «Calle21 X Carrera12» y «Calle 20 x Cra 12»."],
    "manguitos": ["¿La «Flecha» es el giro a la derecha desde el norte (Diagonal 21 hacia el sur que gira a la "
                  "Carrera 19 hacia el noroccidente)? Arranca siempre con el Flujo 1.",
                  "¿El acceso este es la Carrera 19 local que llega desde el suroriente, y no la Calle 21?"],
    "loperena": ["¿La vía de entrada desde el oeste (OSM: «DG 21») es la que el Excel llama Diagonal 16 y la "
                 "ANSV Calle 16?"],
    "area-andina": ["La Calle 6 al este de la Carrera 23 es de doble sentido en OSM, pero ningún grupo controla "
                    "a quien entra desde el este. ¿Ese brazo es solo de salida o el giro está prohibido?"],
}


def _img(ruta: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(ruta.read_bytes()).decode() if ruta.exists() else ""


def _gantt(plan: dict, grupos: list[dict]) -> str:
    c, w, h, izq = plan["ciclo"], 560, 18, 110
    filas = []
    for i, g in enumerate(grupos):
        t = plan["tiempos"][g["id"]]
        y = 18 + i * (h + 4)
        k = 0
        while k < c:
            e = estado(t, g["tipo"], k + 0.5, c)
            j = k
            while j < c and estado(t, g["tipo"], j + 0.5, c) == e:
                j += 1
            col = ESTADO_COLOR[e]
            alto = h if e != "rojo" else 6
            dy = 0 if e != "rojo" else (h - 6) / 2
            filas.append(f'<rect x="{izq + k * w / c:.1f}" y="{y + dy}" width="{(j - k) * w / c:.1f}" '
                         f'height="{alto}" fill="{col}"><title>{g["id"]} {e} {k}–{j} s</title></rect>')
            k = j
        filas.append(f'<text x="4" y="{y + 13}" font-size="11">{g["id"]} {html.escape(g["nombre"])}</text>')
    marcas = "".join(f'<line x1="{izq + s * w / c:.1f}" x2="{izq + s * w / c:.1f}" y1="12" y2="{18 + len(grupos) * (h + 4)}" '
                     f'stroke="#0002"/><text x="{izq + s * w / c:.1f}" y="10" font-size="9" text-anchor="middle">{s}</text>'
                     for s in range(0, c + 1, 10))
    alto = 24 + len(grupos) * (h + 4)
    return (f'<figure><figcaption>{plan["id"]} · ciclo {c} s{"" if plan["con_horario"] else " · sin horario (no corre)"}'
            f'</figcaption><svg viewBox="0 0 {izq + w + 10} {alto}" width="100%">{marcas}{"".join(filas)}</svg></figure>')


def escribir(datos: dict, diferencias: pd.DataFrame, hallazgos: dict, destino: Path, figuras: Path) -> None:
    """`hallazgos`: {interseccion: [(nivel, texto), …]}."""
    secciones, mapas = [], {}
    for it in datos["intersecciones"]:
        geo, o = it["geometria"], it["geometria"]["origen"]
        a_m = Transformer.from_crs(CRS_GEO, CRS_METRICO, always_xy=True)
        a_g = Transformer.from_crs(CRS_METRICO, CRS_GEO, always_xy=True)
        cx, cy = a_m.transform(o["lon"], o["lat"])

        def ll(p):
            lon, lat = a_g.transform(cx + p[0], cy + p[1])
            return [round(lat, 7), round(lon, 7)]

        color = {g["id"]: COLORES[i % len(COLORES)] for i, g in enumerate(it["grupos"])}
        mapas[it["id"]] = {
            "centro": [o["lat"], o["lon"]],
            "vias": [{"p": [ll(q) for q in v["puntos"]], "a": v["ancho"], "ctx": v["contexto"],
                      "n": v["nomencla"] or "sin nombre"} for v in geo["vias"]],
            "tray": [{"p": [ll(q) for q in t["puntos"]], "c": color[g], "g": g,
                      "pare": ll(_punto_en(t["puntos"], t["s_pare"]))} for g, t in geo["trayectorias"].items()],
            "cebras": [{"p": [ll(q) for q in z["poligono"]], "c": color.get(g, "#ffffff"), "g": g,
                        "cod": it["borrador"][g]["codigo"] if g in it["borrador"] else "sin semáforo"}
                       for g, z in geo["cebras"].items()],
            "cajon": [ll(q) for q in geo["cajon_amarillo"]] if geo["cajon_amarillo"] else None,
            "brazos": [{"p": ll([30 * _sin(b["rumbo"]), 30 * _cos(b["rumbo"])]), "t": f'{b["id"]} · {b["cardinal"] or "sin acceso"}'
                        f'<br>{b["nomencla"] or "sin nombre"}'} for b in geo["brazos"]],
            "camaras": [{"p": ll([k["x"], k["y"]]), "t": k["equipo"]} for k in geo["camaras"]],
            "sem": [ll(p) for p in geo["semaforos_osm"]],
        }
        filas = "".join(
            f'<tr><td><span class="pt" style="background:{color[g]}"></span>{g}</td><td>{html.escape(b["nombre"])}</td>'
            f'<td>{b["codigo"] or "—"}</td><td>{html.escape(b["movimiento"])}</td><td>{html.escape(b["via"] or "—")}</td>'
            f'<td><span class="conf {b["confianza"]}">{b["confianza"]}</span></td><td class="ev">{html.escape(b["evidencia"])}</td>'
            f'<td><input type="checkbox" aria-label="Validado {g}"></td></tr>' for g, b in it["borrador"].items())
        avisos = [h for h in hallazgos.get(it["id"], []) if h[0] != "INFO"]
        preg = "".join(f"<li>{html.escape(p)}</li>" for p in PREGUNTAS.get(it["id"], []))
        evid = "".join(f"<li>{html.escape(e)}</li>" for e in geo["evidencia"])
        av = "".join(f"<li><b>{n}</b> {html.escape(t)}</li>" for n, t in avisos) or "<li>Sin avisos</li>"
        gantts = "".join(_gantt(p, it["grupos"]) for p in it["planes"])
        secciones.append(f"""
<section id="{it['id']}">
  <h2>{html.escape(it['nombre'])} <small>controlador {it['controlador']['equipo']} · cruce {it['controlador']['cruce']} ·
  «{html.escape(it['cruce_pie'])}» · cámaras {', '.join(it['equipos'])}</small></h2>
  <div class="dos">
    <div id="mapa-{it['id']}" class="mapa"></div>
    <div>
      <h3>Preguntas para validar</h3><ol class="preg">{preg}<li>¿Los sentidos de circulación y el centro del cruce están bien?</li>
      <li>¿Cada grupo controla el acceso o el cruce peatonal propuesto?</li></ol>
      <h3>Avisos</h3><ul class="av">{av}</ul>
      <details><summary>Cómo se orientó el cruce</summary><ul>{evid}</ul></details>
      <details><summary>Matriz de grupos amigos (puntos muestreados)</summary>
        <img src="{_img(figuras / f"semaforos_matriz_{it['id']}.png")}" alt="Matriz de grupos amigos de {html.escape(it['nombre'])}" width="420"></details>
    </div>
  </div>
  <table><thead><tr><th>Grupo</th><th>Nombre</th><th>Código</th><th>Movimiento propuesto</th><th>Vía (OSM)</th>
  <th>Confianza</th><th>Evidencia</th><th>OK</th></tr></thead><tbody>{filas}</tbody></table>
  <div class="gantts">{gantts}</div>
</section>""")
    dif = diferencias.drop(columns="decision").to_html(index=False, border=0, classes="dif")
    pagina = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Validación de accesos semafóricos</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<style>
body{{font:14px/1.45 system-ui,sans-serif;margin:0;background:#f4f5f2;color:#1c2227}}
header,section{{max-width:1240px;margin:0 auto;padding:16px 20px}} section{{background:#fff;margin:18px auto;border-radius:10px;box-shadow:0 1px 3px #0002}}
h1{{font-size:22px;margin:8px 0}} h2 small{{font-weight:400;color:#5a646c;font-size:13px;display:block}}
.dos{{display:grid;grid-template-columns:3fr 2fr;gap:18px}} .mapa{{height:520px;border-radius:8px}}
table{{border-collapse:collapse;width:100%;margin-top:14px;font-size:13px}} th,td{{border-bottom:1px solid #e3e6e1;padding:6px;text-align:left;vertical-align:top}}
.pt{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}} .ev{{color:#48525a;max-width:420px}}
.conf{{padding:1px 8px;border-radius:9px;font-size:12px;color:#fff}} .alta{{background:#1f8a4c}} .media{{background:#c98a00}} .baja{{background:#b8332a}}
.gantts{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}} figure{{margin:0}} figcaption{{font-weight:600;font-size:12px}}
.preg li{{margin-bottom:6px}} .av li{{margin-bottom:4px}} .dif td,.dif th{{padding:4px 8px}}
.leaflet-tooltip.rot{{background:#000a;color:#fff;border:0;font-size:11px}} .cod{{font-weight:700;color:#fff;text-shadow:0 0 3px #000}}
@media (max-width:900px){{.dos,.gantts{{grid-template-columns:1fr}}}}
</style></head><body>
<header><h1>Validación del borrador grupo → acceso (decisión 28)</h1>
<p>Borrador generado por <code>scripts/09_semaforos.py</code> el {datos['generado']} a partir de los nombres de los grupos
(codificación de trayectorias SDM Bogotá, decisión 30), la red vial OSM y el sentido que vigila cada cámara SAST.
<b>No es un hecho hasta que lo valides</b>: lo validado se copia a <code>config/semaforos.yaml</code> (<code>asignacion</code>)
y solo entonces el tablero mueve vehículos en ese cruce. En el mapa: líneas de color = trayectoria de cada grupo,
punto negro = línea de pare, franjas = cebras con su código (blancas = sin semáforo peatonal), recuadro amarillo = cajón de no bloqueo, cuadros naranja = cámaras SAST, puntos verdes = semáforo en OSM.</p>
<h3>Diferencias con el correo del 29/09/2026 (manda el controlador, decisión 27)</h3>{dif}
<p>Ir a: {' · '.join(f'<a href="#{i["id"]}">{html.escape(i["nombre"])}</a>' for i in datos["intersecciones"])}</p></header>
{''.join(secciones)}
<script>
const M={json.dumps(mapas, ensure_ascii=False)};
for (const [id,d] of Object.entries(M)) {{
  const m=L.map('mapa-'+id,{{maxZoom:21}}).setView(d.centro,19);
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
    {{maxZoom:21,maxNativeZoom:19,attribution:'Imagen: Esri World Imagery · Vías: © OpenStreetMap'}}).addTo(m);
  for (const v of d.vias) L.polyline(v.p,{{color:v.ctx?'#ddd':'#fff',opacity:v.ctx?.35:.55,weight:2}}).bindTooltip(v.n).addTo(m);
  if (d.cajon) L.polygon(d.cajon,{{color:'#ffd400',weight:2,fillOpacity:.15,dashArray:'4 3'}}).bindTooltip('cajón amarillo').addTo(m);
  for (const z of d.cebras) L.polygon(z.p,{{color:z.c,weight:2,fillOpacity:.35}}).bindTooltip(`<span class="cod">${{z.g}} · ${{z.cod}}</span>`,{{permanent:true,direction:'center',className:'rot'}}).addTo(m);
  for (const t of d.tray) {{
    L.polyline(t.p,{{color:t.c,weight:4,opacity:.95}}).bindTooltip(t.g).addTo(m);
    const f=t.p[t.p.length-1]; L.circleMarker(f,{{radius:5,color:t.c,fillOpacity:1}}).addTo(m);
    L.circleMarker(t.pare,{{radius:4,color:'#000',fillColor:'#000',fillOpacity:1}}).bindTooltip('pare '+t.g).addTo(m);
  }}
  for (const b of d.brazos) L.marker(b.p,{{opacity:0}}).bindTooltip(b.t,{{permanent:true,direction:'center',className:'rot'}}).addTo(m);
  for (const k of d.camaras) L.circleMarker(k.p,{{radius:7,color:'#000',fillColor:'#ff8c1a',fillOpacity:1,weight:1}}).bindTooltip(k.t).addTo(m);
  for (const s of d.sem) L.circleMarker(s,{{radius:5,color:'#0b0',fillColor:'#3f3',fillOpacity:1}}).bindTooltip('semáforo en OSM').addTo(m);
  L.circleMarker(d.centro,{{radius:3,color:'#f0f'}}).bindTooltip('centro').addTo(m);
}}
</script></body></html>"""
    destino.write_text(pagina, encoding="utf-8")


def _punto_en(puntos: list, s: float) -> list:
    acum = 0.0
    for (x0, y0), (x1, y1) in zip(puntos, puntos[1:]):
        d = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        if acum + d >= s and d > 0:
            f = (s - acum) / d
            return [x0 + f * (x1 - x0), y0 + f * (y1 - y0)]
        acum += d
    return puntos[-1]


def _sin(g):
    return math.sin(math.radians(g))


def _cos(g):
    return math.cos(math.radians(g))
