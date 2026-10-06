"""Etapa 8 — Informe ejecutivo para gerencia y Excel para copiar a la plataforma ANSV.

Cifra oficial: zona de influencia + 15 m para siniestros y comparendos (decisión 25). Comparendos
de agentes y fotodetección previa con código aprobado para el equipo; los de las cámaras SAST no
entran. Ventana de 36 meses previa al inicio de cada equipo; el punto usa la del equipo que inició
primero. Lee lo que dejó la etapa 5; no recalcula la ubicación.

Salidas:
  outputs/AAAA-MM-DD_sttv_linea-base-sast_ejecutivo.html
  outputs/AAAA-MM-DD_sttv_linea-base-sast_plataforma-ansv.xlsx
(fecha = corte de los comparendos)
"""

import json
import subprocess
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd

import _entorno  # noqa: F401
from sast.ejecutivo import INFRACCIONES, barras, excel_ansv, fmt, mes_largo, pagina, rango
from sast.equipos import equipos_operativos
from sast.rutas import OUTPUTS, PROCESSED, RAIZ, anio_base, ventana_base

CRITERIO = "buffer15"
MEDIOS = ["agente", "fotodeteccion_previa"]
VICTIMAS = ["Fallecidos", "Lesionados"]
VALIDADO = "Santiago Torreglosa"
LEAFLET_CSS = Path.home() / "Claude_code/Analisis_siniestralidad/assets/leaflet-1.9.4/leaflet.css"


def version() -> str:
    r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True, text=True)
    return r.stdout.strip() or "sin commit"


def main() -> None:
    eq = equipos_operativos()
    largo = pd.read_parquet(PROCESSED / "indicadores_largo.parquet")
    ev = pd.read_parquet(PROCESSED / "eventos_en_zona.parquet")
    comp = pd.read_parquet(PROCESSED / "comparendos_ubicados.parquet", columns=["fecha", "medio", "ubicacion"])
    sin = pd.read_parquet(PROCESSED / "siniestros.parquet", columns=["corte"])
    corte_comp = comp["fecha"].max()
    corte_sin = pd.Timestamp(sin["corte"].iat[0])

    l = largo[(largo["criterio"] == CRITERIO) & largo["aprobado"] & largo["medio"].isin(MEDIOS + ["portal"])
              & largo["anio_base"].notna()]
    ventanas = {r.equipo: ventana_base(r.fecha_inicio) for r in eq.itertuples()}

    # ---------------- por equipo (Excel y tabla) ----------------
    equipos_xl, tabla, resumen = [], [], []
    for r in eq.itertuples():
        inds = VICTIMAS + sorted(r.codigos)
        d = l[(l["nivel"] == "equipo") & (l["unidad"] == r.equipo)]
        val = (d.pivot_table(index="indicador", columns="mes", values="valor", aggfunc="sum", fill_value=0)
               .reindex(index=inds, columns=[str(m) for m in ventanas[r.equipo]], fill_value=0))
        val.columns = list(ventanas[r.equipo])
        equipos_xl.append({"equipo": r.equipo, "punto": r.punto.title(), "solicitud_ansv": r.solicitud_ansv,
                           "codigo_unico": r.codigo_unico, "direccion_ansv": r.direccion_ansv,
                           "fecha_inicio": r.fecha_inicio.strftime("%d/%m/%Y"), "ventana": ventanas[r.equipo],
                           "valores": val})
        tot = val.sum(axis=1).astype(int).to_dict()
        tabla.append({"equipo": r.equipo, "punto": r.punto.title(), "ventana": rango(ventanas[r.equipo]), **tot})
        resumen.append({"Equipo": r.equipo, "Código único": r.codigo_unico, "Código solicitud": r.solicitud_ansv,
                        "Punto": r.punto.title(), "Dirección": r.direccion_ansv,
                        "Inicio de operación": r.fecha_inicio.strftime("%d/%m/%Y"),
                        "Línea base": f"{mes_largo(ventanas[r.equipo][0])} a {mes_largo(ventanas[r.equipo][-1])}",
                        **{k: tot.get(k) for k in VICTIMAS + sorted(set().union(*eq["codigos"]))}})
    resumen = pd.DataFrame(resumen)

    # ---------------- por punto (sin doble conteo) ----------------
    puntos = []
    for sol, g in eq.groupby("solicitud"):
        inicio = g["fecha_inicio"].min()
        v = ventana_base(inicio)
        d = l[(l["nivel"] == "solicitud") & (l["unidad"] == str(sol))]
        compd = d[~d["indicador"].isin(VICTIMAS)]
        serie = [int(compd[compd["mes"] == str(m)]["valor"].sum()) for m in v]
        top = compd.groupby("indicador")["valor"].sum().sort_values(ascending=False).head(3)
        zz = gpd.read_file(PROCESSED / "equipos_sast.gpkg", layer="zonas_buffer")
        b = zz[zz["equipo"].isin(g["equipo"])].total_bounds
        nombre = g["punto"].iat[0].title()
        puntos.append({
            "solicitud": int(sol), "nombre": nombre, "ventana": rango(v),
            "equipos": [{"corto": e.equipo.replace("EQUIPO", "Equipo "), "codigo_unico": e.codigo_unico,
                         "inicio": e.fecha_inicio.strftime("%d/%m/%Y")} for e in g.itertuples()],
            "comparendos": int(compd["valor"].sum()),
            "fallecidos": int(d[d["indicador"] == "Fallecidos"]["valor"].sum()),
            "lesionados": int(d[d["indicador"] == "Lesionados"]["valor"].sum()),
            "top": [(k, int(x)) for k, x in top.items() if x > 0],
            "grafico": barras(serie, list(v), f"Comparendos por mes en {nombre}"),
            "limites": [[b[1], b[0]], [b[3], b[2]]],
        })

    # ---------------- mapa: hechos de la línea base de cada equipo ----------------
    e = ev[(ev["criterio"] == CRITERIO) & (ev["nivel"] == "equipo")].copy()
    inicio_eq = dict(zip(eq["equipo"], eq["fecha_inicio"]))
    aprob = {r.equipo: set(r.codigos) for r in eq.itertuples()}
    e["en_base"] = [anio_base(pd.Period(m, "M"), inicio_eq[u]) is not None for m, u in zip(e["mes"], e["unidad"])]
    e = e[e["en_base"]]
    ec = e[(e["tipo"] == "comparendo") & e["medio"].isin(MEDIOS)]
    ec = ec[[c in aprob[u] for c, u in zip(ec["codigo"], ec["unidad"])]].drop_duplicates("id_evento")
    es = e[(e["tipo"] == "siniestro")].drop_duplicates("id_evento")
    es = es[(es["cantidad_muertos"] + es["cantidad_heridos"]) > 0]
    zb = gpd.read_file(PROCESSED / "equipos_sast.gpkg", layer="zonas_buffer")
    mapa = {
        "zonas": json.loads(zb[["equipo", "geometry"]].to_json()),
        "equipos": [[round(r.lon, 6), round(r.lat, 6), r.equipo[-3:], r.punto.title(), r.direccion_ansv,
                     r.codigo_unico, r.fecha_inicio.strftime("%d/%m/%Y")] for r in eq.itertuples()],
        "comparendos": [[round(r.lon_u, 6), round(r.lat_u, 6), f"{r.fecha:%d/%m/%Y}", r.codigo,
                         INFRACCIONES.get(r.codigo, "")] for r in ec.itertuples()],
        "siniestros": [[round(r.lon, 6), round(r.lat, 6), f"{r.fecha:%d/%m/%Y}", int(r.cantidad_muertos),
                        int(r.cantidad_heridos)] for r in es.itertuples()],
        "puntos": [{"nombre": p["nombre"], "limites": p["limites"]} for p in puntos],
    }

    # ---------------- control: puntos = mapa, equipo = tabla ----------------
    for p in puntos:
        sub = [x for x in tabla if x["punto"] == p["nombre"]]
        assert p["comparendos"] <= sum(sum(v for k, v in x.items() if k in INFRACCIONES) for x in sub), p["nombre"]
    n_mapa_comp = len(ec)
    print(f"Mapa: {n_mapa_comp:,} comparendos y {len(es)} siniestros con víctimas de la línea base")

    # ---------------- textos ----------------
    base = comp[comp["medio"].isin(MEDIOS)]
    pct = base["ubicacion"].eq("no_ubicable").mean()
    corte_c = f"{corte_comp:%d/%m/%Y}"
    corte_s = f"{corte_sin:%d/%m/%Y}"
    nombre = f"{corte_comp:%Y-%m-%d}_sttv_linea-base-sast"
    xlsx = OUTPUTS / f"{nombre}_plataforma-ansv.xlsx"
    htmlf = OUTPUTS / f"{nombre}_ejecutivo.html"
    cods = sorted(set().union(*eq["codigos"]))
    c = {
        "corte_comparendos": corte_c, "corte_siniestros": corte_s, "validado": VALIDADO,
        "n_equipos": len(eq), "n_puntos": eq["solicitud"].nunique(),
        "tot_comparendos": sum(p["comparendos"] for p in puntos),
        "tot_fallecidos": sum(p["fallecidos"] for p in puntos),
        "tot_lesionados": sum(p["lesionados"] for p in puntos),
        "n_comparendos_total": len(base), "pct_no_ubicable": f"El {pct:.0%}".replace(".", ","),
        "puntos": puntos, "tabla": tabla, "codigos_tabla": cods, "mapa": mapa,
        "generado": f"{date.today():%d/%m/%Y}", "version": version(),
        "fuentes": [
            ("Siniestros", f"Sistema de información de siniestralidad vial de Valledupar (portal de la ANSV), corte {corte_s}."),
            ("Comparendos", f"Sistema de comparendos de la Secretaría, 01/01/2023 a {corte_c}: {fmt(len(base))} comparendos de "
                            f"agentes y de la fotodetección anterior, más {fmt((comp['medio'] == 'sast').sum())} de los equipos SAST "
                            "(estos últimos fuera de la línea base)."),
            ("Equipos", "Inventario de equipos SAST de la Secretaría (ubicación y códigos de infracción autorizados) y "
                        "plataforma de fotodetección de la ANSV (código único, solicitud y fecha de inicio de operación)."),
            ("Zonas de influencia", "SIG de los estudios técnicos de los equipos SAST, con 15 metros de tolerancia."),
        ],
        "entregables": [
            ("Cifras para la plataforma ANSV", f"<code>{xlsx.name}</code>: una hoja por equipo, mes a mes, por Año 1, 2 y 3."),
            ("Soporte técnico", "Informe técnico con el detalle del método y la calidad de los datos, y ficha de procedencia "
                                "<code>docs/ficha-procedencia-2026-10-06-linea-base-sast.md</code>."),
            ("Repositorio de cálculo", f"<code>sast-valledupar</code>, versión <code>{version()}</code>. "
                                       "Todo el cálculo se puede regenerar desde los datos de origen."),
            ("Validación", f"{VALIDADO}, Secretaría de Tránsito y Transporte de Valledupar."),
        ],
    }
    htmlf.write_text(pagina(c, LEAFLET_CSS.read_text(encoding="utf-8")), encoding="utf-8")

    instrucciones = [
        f"Cifras de línea base de los {len(eq)} equipos SAST en operación, listas para copiar en la plataforma de "
        "fotodetección de la ANSV (sección Indicadores, pestaña Línea Base).",
        "Cada hoja corresponde a un equipo e identifica su código único, código de solicitud y fecha de inicio. Trae tres "
        "bloques (Año 1, Año 2 y Año 3) con los mismos meses y el mismo orden de filas del formulario: copie cada fila de "
        "doce meses en el indicador correspondiente.",
        "Periodo: los 36 meses anteriores al mes de inicio de operación de cada equipo.",
        "Zona: zona de influencia del estudio técnico de cada equipo, con 15 metros de tolerancia.",
        "Fallecidos y lesionados: personas en siniestros ocurridos en la zona (sistema de información de siniestralidad, "
        f"corte {corte_s}).",
        "Comparendos: impuestos en la zona por agentes de tránsito y por la fotodetección anterior a los equipos SAST, para "
        "las infracciones que controla cada equipo. Los comparendos generados por los propios equipos SAST no hacen parte "
        f"de la línea base. Corte {corte_c}.",
        "La hoja Resumen trae los totales de los 36 meses por equipo.",
        f"Validado por {VALIDADO}. Versión del cálculo: {version()}.",
    ]
    excel_ansv(equipos_xl, resumen, instrucciones).save(xlsx)

    # control: el Excel suma lo mismo que la tabla del informe
    for x, t in zip(equipos_xl, tabla):
        for ind in x["valores"].index:
            assert int(x["valores"].loc[ind].sum()) == t[ind], (x["equipo"], ind)
    print("Totales por punto (+15 m, sin doble conteo):")
    for p in puntos:
        print(f"  {p['nombre']:<26} comparendos {p['comparendos']:>5}  fallecidos {p['fallecidos']}  lesionados {p['lesionados']}")
    print(f"-> {htmlf.relative_to(RAIZ)}\n-> {xlsx.relative_to(RAIZ)}\nControl: Excel = tabla del informe ✓")


if __name__ == "__main__":
    main()
