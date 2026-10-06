"""Informe HTML autocontenido de la línea base (SVG a mano + mapa Leaflet desde CDN).

Colores (paleta de referencia validada, slots en orden fijo): agente = azul (slot 1),
fotodetección previa = naranja (slot 2), SAST = aqua (slot 3). Fallecidos = rojo (slot 8),
lesionados = amarillo (slot 4) solo en las barras de víctimas, que van en su propio gráfico.
"""

from __future__ import annotations

import html
import json

import pandas as pd

MEDIOS = {"agente": ("Agentes de tránsito", "--s1"), "fotodeteccion_previa": ("Fotodetección previa (no SAST)", "--s2"),
          "sast": ("Cámaras SAST", "--s3")}
VICTIMAS = {"Fallecidos": "--s8", "Lesionados": "--s4"}
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def esc(t) -> str:
    return html.escape(str(t))


def fmt(n) -> str:
    return f"{int(round(n)):,}".replace(",", ".")


def mes_corto(m: str) -> str:
    p = pd.Period(m, "M")
    return f"{MESES_CORTOS[p.month - 1]} {p.year}"


def svg_apiladas(meses: list[str], series: dict[str, list[float]], colores: dict[str, str],
                 nombres: dict[str, str], aria: str, marcas_x: dict[str, str] | None = None,
                 W: int = 760, H: int = 190) -> str:
    """Barras apiladas mensuales con hueco de 2 px entre segmentos y tooltip nativo."""
    izq, der, arr, aba = 36, 8, 10, 26
    n = len(meses)
    tot = [sum(s[i] for s in series.values()) for i in range(n)]
    mx = max(tot + [1])
    paso = max(1, mx / 4)
    paso = [p for p in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000) if p >= paso][0]
    tope = paso * (int(mx // paso) + (1 if mx % paso else 0))
    ancho = (W - izq - der) / n
    bw = max(2.0, ancho - 2)
    y = lambda v: arr + (H - arr - aba) * (1 - v / tope)  # noqa: E731
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(aria)}" class="graf">']
    for k in range(0, int(tope) + 1, int(paso)):
        out.append(f'<line x1="{izq}" x2="{W - der}" y1="{y(k):.1f}" y2="{y(k):.1f}" class="grid"/>'
                   f'<text x="{izq - 6}" y="{y(k) + 4:.1f}" class="eje" text-anchor="end">{fmt(k)}</text>')
    for m_, etiqueta in (marcas_x or {}).items():
        if m_ in meses:
            x = izq + meses.index(m_) * ancho
            fin = x > W * 0.75
            out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{arr}" y2="{H - aba}" class="marca"/>'
                       f'<text x="{x + (-3 if fin else 3):.1f}" y="{arr + 9}" class="eje" '
                       f'text-anchor="{"end" if fin else "start"}">{esc(etiqueta)}</text>')
    for i, m in enumerate(meses):
        x = izq + i * ancho + 1
        base = 0.0
        partes = []
        for k, vals in series.items():
            v = vals[i]
            if v <= 0:
                continue
            y0, y1 = y(base), y(base + v)
            h = max(y0 - y1 - (2 if base > 0 else 0), 0.8)
            partes.append(f'<rect x="{x:.1f}" y="{y1:.1f}" width="{bw:.1f}" height="{h:.1f}" '
                          f'style="fill:var({colores[k]})"/>')
            base += v
        detalle = "; ".join(f"{nombres[k]}: {fmt(series[k][i])}" for k in series if series[k][i])
        out.append(f'<g class="col"><title>{esc(mes_corto(m))} — total {fmt(tot[i])}'
                   f'{". " + esc(detalle) if detalle else ""}</title>'
                   f'<rect x="{x - 1:.1f}" y="{arr}" width="{ancho:.1f}" height="{H - arr - aba}" class="hit"/>'
                   + "".join(partes) + "</g>")
        if m.endswith("-01"):
            out.append(f'<text x="{x:.1f}" y="{H - 8}" class="eje">{m[:4]}</text>')
    out.append(f'<line x1="{izq}" x2="{W - der}" y1="{y(0):.1f}" y2="{y(0):.1f}" class="base"/></svg>')
    return "".join(out)


def leyenda(claves: list[str], colores: dict[str, str], nombres: dict[str, str]) -> str:
    return '<div class="leyenda">' + "".join(
        f'<span><i style="background:var({colores[k]})"></i>{esc(nombres[k])}</span>' for k in claves) + "</div>"


def tabla(cab: list[str], filas: list[list], clase: str = "") -> str:
    th = "".join(f"<th>{esc(c)}</th>" for c in cab)
    tr = "".join("<tr>" + "".join(f"<td>{c if isinstance(c, str) and c.startswith('<') else esc(c)}</td>"
                                  for c in f) + "</tr>" for f in filas)
    return f'<div class="tabla-env"><table class="{clase}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def tarjeta(cifra: str, rotulo: str, detalle: str = "") -> str:
    return (f'<div class="tarjeta"><div class="cifra">{cifra}</div><div class="rot">{esc(rotulo)}</div>'
            f'<div class="det">{esc(detalle)}</div></div>')


CSS = """
:root{color-scheme:light;--bg:#f7f7f5;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--ink3:#7a7974;
--line:#e2e1dc;--grid:#ecebe7;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s8:#e34948;--acento:#e07b4c}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#121211;--surface:#1a1a19;
--ink:#fff;--ink2:#c3c2b7;--ink3:#93928a;--line:#33332f;--grid:#2a2a27;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s8:#e66767}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#121211;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--ink3:#93928a;
--line:#33332f;--grid:#2a2a27;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s8:#e66767}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}h1{font-size:26px;margin:0 0 4px}h2{font-size:20px;margin:40px 0 8px;
border-bottom:1px solid var(--line);padding-bottom:6px}h3{font-size:16px;margin:24px 0 6px}.sub{color:var(--ink2);margin:0 0 16px}
.tarjetas{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:16px 0}
.tarjeta{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.cifra{font-size:26px;font-weight:650;font-variant-numeric:tabular-nums}.rot{font-weight:600;font-size:13px}.det{color:var(--ink3);font-size:12px}
.aviso{border-left:4px solid var(--acento);background:var(--surface);padding:10px 14px;margin:12px 0;border-radius:0 8px 8px 0}
.tabla-env{overflow-x:auto;margin:8px 0 16px}table{border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums;width:100%}
th,td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:right;white-space:nowrap}th{color:var(--ink2);font-weight:600;background:var(--surface)}
th:first-child,td:first-child{text-align:left}.graf{width:100%;height:auto;background:var(--surface);border:1px solid var(--line);border-radius:8px}
.graf .grid{stroke:var(--grid)}.graf .base{stroke:var(--ink3)}.graf .eje{fill:var(--ink3);font-size:10px}.graf .marca{stroke:var(--ink2);stroke-dasharray:3 3}
.graf .hit{fill:transparent}.graf .col:hover .hit{fill:var(--grid)}.leyenda{display:flex;flex-wrap:wrap;gap:14px;font-size:13px;color:var(--ink2);margin:6px 0}
.leyenda i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px;vertical-align:-1px}
#mapa{height:520px;border-radius:10px;border:1px solid var(--line)}details{margin:8px 0}summary{cursor:pointer;color:var(--ink2)}
.nota{color:var(--ink3);font-size:13px}code{font-size:12.5px}
"""


def pagina(titulo: str, cuerpo: str, datos_mapa: dict) -> str:
    datos = json.dumps(datos_mapa, ensure_ascii=False, separators=(",", ":"))
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(titulo)}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>{CSS}</style></head><body><main>{cuerpo}</main>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const D={datos};
(function(){{
 if(!window.L) {{document.getElementById('mapa').innerHTML='<p class="nota">El mapa necesita conexión a internet (Leaflet).</p>';return;}}
 const css=getComputedStyle(document.documentElement);const c=v=>css.getPropertyValue(v).trim();
 const m=L.map('mapa');// Fondo Esri: los servidores de OSM bloquean (403) las páginas abiertas como archivo local
 L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{{z}}/{{y}}/{{x}}',
   {{maxZoom:19,attribution:'Fondo © Esri, HERE, Garmin, OpenStreetMap contributors'}}).addTo(m);
 const zb=L.geoJSON(D.zonas_buffer,{{style:{{color:c('--ink2'),weight:1,dashArray:'3 3',fillOpacity:0.04}}}}).addTo(m);
 L.geoJSON(D.zonas,{{style:{{color:c('--acento'),weight:2,fillOpacity:0.12}},onEachFeature:(f,l)=>l.bindTooltip(f.properties.equipo)}}).addTo(m);
 const col={{agente:c('--s1'),fotodeteccion_previa:c('--s2'),sast:c('--s3')}};
 const capas={{}};
 for(const [k,nom] of Object.entries(D.nombres)){{capas[nom]=L.layerGroup();}}
 D.comparendos.forEach(p=>{{L.circleMarker([p[1],p[0]],{{radius:4,weight:1,color:c('--surface'),fillColor:col[p[2]],fillOpacity:.85}})
   .bindTooltip(p[3]+' · '+p[4]+' · '+D.nombres[p[2]]).addTo(capas[D.nombres[p[2]]]);}});
 const sin=L.layerGroup();D.siniestros.forEach(p=>{{L.circleMarker([p[1],p[0]],{{radius:6,weight:2,color:c('--s8'),fillColor:c('--s8'),fillOpacity:.35}})
   .bindTooltip(p[2]+' · '+p[3]+' · fallecidos '+p[4]+', lesionados '+p[5]).addTo(sin);}});
 capas['Siniestros con víctimas']=sin;
 Object.values(capas).forEach(l=>l.addTo(m));L.control.layers(null,capas,{{collapsed:false}}).addTo(m);
 m.fitBounds(zb.getBounds(),{{padding:[20,20]}});
}})();
</script></body></html>"""
