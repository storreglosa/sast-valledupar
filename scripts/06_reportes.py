"""Etapa 6 — Entregables: Excel ANSV y informe HTML de la línea base.

Salida: outputs/AAAA-MM-DD_sttv_linea-base-sast.xlsx y outputs/AAAA-MM-DD_sttv_linea-base-sast.html
(fecha = corte de los comparendos, el más reciente de los insumos). Nada con datos personales:
el mapa lleva fecha, código y medio de cada comparendo, nunca número, placa ni persona.
"""

import json

import geopandas as gpd
import pandas as pd

import _entorno  # noqa: F401
from sast.equipos import equipos_operativos
from sast.excel_ansv import libro
from sast.informe import (MEDIOS, VICTIMAS, esc, fmt, leyenda, mes_corto, pagina, svg_apiladas,
                          tabla, tarjeta)
from sast.rutas import (BASE_FIN, BASE_INICIO, BUFFER_M, DISCORDANCIA_M, OUTPUTS, PROCESSED,
                        meses_base, meses_serie)

BASE = ["agente", "fotodeteccion_previa"]
SALVEDAD_LESIONADOS = ("SALVEDAD: el portal registra muchos menos lesionados por mes en 2023–2025 que en 2026 "
                       "(cambio de captura, hoja «Cobertura portal»); la serie no es homogénea y el valor puede "
                       "estar subestimado.")
SALVEDAD_FALLECIDOS = ("SALVEDAD: la mezcla de fuentes del portal cambia entre años (Deceso clínico desde 2024, "
                       "Geoportal y Policía hasta 2024, Mesa calidad solo 2025); puede haber subregistro o doble conteo.")
INDICES_VICTIMAS = ["Fallecidos", "Lesionados"]


def cargar():
    eq = equipos_operativos()
    largo = pd.read_parquet(PROCESSED / "indicadores_largo.parquet")
    ev = pd.read_parquet(PROCESSED / "eventos_en_zona.parquet")
    comp = pd.read_parquet(PROCESSED / "comparendos_ubicados.parquet",
                           columns=["fecha", "codigo", "medio", "ubicacion", "metodo_dir", "discordante",
                                    "dist_gps_direccion_m", "coord_estado", "dup_conflicto"])
    sin = pd.read_parquet(PROCESSED / "siniestros.parquet")
    cob = pd.read_csv(OUTPUTS / "tables" / "siniestros_cobertura.csv")
    diag = pd.read_csv(OUTPUTS / "tables" / "comparendos_diagnostico.csv").set_index("indicador")["valor"]
    return eq, largo, ev, comp, sin, cob, diag


def matriz(largo, unidad, indicadores, medios, criterio="oficial", nivel="equipo", meses=None):
    meses = [str(m) for m in (meses if meses is not None else meses_base())]
    d = largo[(largo["nivel"] == nivel) & (largo["unidad"] == str(unidad)) & (largo["criterio"] == criterio)
              & largo["medio"].isin(medios + ["portal"])]
    t = d.pivot_table(index="indicador", columns="mes", values="valor", aggfunc="sum", fill_value=0)
    return t.reindex(index=indicadores, columns=meses, fill_value=0)


def total_base(largo, unidad, ind, medios, criterio="oficial", nivel="equipo"):
    d = largo[(largo["nivel"] == nivel) & (largo["unidad"] == str(unidad)) & (largo["criterio"] == criterio)
              & (largo["indicador"] == ind) & largo["medio"].isin(medios + ["portal"])
              & largo["anio_base"].notna()]
    return int(d["valor"].sum())


def main() -> None:
    eq, largo, ev, comp, sin, cob, diag = cargar()
    corte_comp = comp["fecha"].max().date().isoformat()
    corte_portal = str(sin["corte"].iat[0])
    nombre = f"{corte_comp}_sttv_linea-base-sast"
    base_txt = f"{mes_corto(str(BASE_INICIO))} a {mes_corto(str(BASE_FIN))}"

    # cobertura del portal por año (para el aviso de lesionados)
    cob["anio"] = cob["mes"].str[:4]
    cob_anio = cob.groupby("anio").agg(meses=("mes", "size"), siniestros=("siniestros", "sum"),
                                       fallecidos=("fallecidos", "sum"), lesionados=("lesionados", "sum"))
    cob_anio["lesionados_mes"] = cob_anio["lesionados"] / cob_anio["meses"]
    cob_anio["fallecidos_mes"] = cob_anio["fallecidos"] / cob_anio["meses"]
    salto = cob_anio["lesionados_mes"].max() / max(cob_anio["lesionados_mes"].min(), 0.1)

    # ---------------- Excel ANSV ----------------
    hojas, resumen = [], []
    for r in eq.itertuples():
        inds = INDICES_VICTIMAS + list(r.codigos)
        val = matriz(largo, r.equipo, inds, BASE)
        val.columns = [pd.Period(m, "M") for m in val.columns]
        obs = {}
        for ind in inds:
            if ind in INDICES_VICTIMAS:
                est = total_base(largo, r.equipo, ind, [], "estricto")
                obs[ind] = (f"Portal ANSV (personas), corte {corte_portal}. Sensibilidad: polígono estricto {est}. "
                            + (SALVEDAD_LESIONADOS if ind == "Lesionados" else SALVEDAD_FALLECIDOS))
            else:
                ag = total_base(largo, r.equipo, ind, ["agente"])
                fp = total_base(largo, r.equipo, ind, ["fotodeteccion_previa"])
                est = total_base(largo, r.equipo, ind, BASE, "estricto")
                b15 = total_base(largo, r.equipo, ind, BASE, "buffer15")
                obs[ind] = (f"Agentes: {ag}; fotodetección previa: {fp}. Sensibilidad: todo estricto {est}; "
                            f"todo +{BUFFER_M:.0f} m {b15}.")
            resumen.append({"equipo": r.equipo, "solicitud": r.solicitud, "punto": r.punto, "indicador": ind,
                            "linea_base": int(val.loc[ind].sum()),
                            "agentes": None if ind in INDICES_VICTIMAS else total_base(largo, r.equipo, ind, ["agente"]),
                            "fotodeteccion_previa": None if ind in INDICES_VICTIMAS else total_base(largo, r.equipo, ind, ["fotodeteccion_previa"]),
                            "estricto": total_base(largo, r.equipo, ind, [] if ind in INDICES_VICTIMAS else BASE, "estricto"),
                            "buffer15": total_base(largo, r.equipo, ind, [] if ind in INDICES_VICTIMAS else BASE, "buffer15")})
        info = {"fecha_confirmada": bool(r.fecha_inicio_confirmada), "id_ansv": r.id_ansv, "equipo": r.equipo, "punto": r.punto.title(), "solicitud": r.solicitud, "direccion": r.direccion,
                "fecha_inicio": r.fecha_inicio.strftime("%d/%m/%Y"), "buffer": BUFFER_M, "corte_portal": corte_portal}
        hojas.append((info, val, obs))
    resumen = pd.DataFrame(resumen)

    serie = largo[(largo["nivel"] == "equipo") & (largo["criterio"] == "oficial")].copy()
    serie_t = (serie.pivot_table(index=["unidad", "indicador", "medio", "aprobado"], columns="mes",
                                 values="valor", aggfunc="sum", fill_value=0)
               .reindex(columns=[str(m) for m in meses_serie()], fill_value=0).reset_index()
               .rename(columns={"unidad": "equipo"}))
    punto = largo[(largo["nivel"] == "solicitud") & (largo["criterio"] == "oficial") & largo["anio_base"].notna()
                  & largo["aprobado"] & largo["medio"].isin(BASE + ["portal"])]
    punto_t = punto.pivot_table(index="unidad", columns="indicador", values="valor", aggfunc="sum", fill_value=0)
    punto_t = punto_t.reset_index().rename(columns={"unidad": "solicitud"})
    sast = largo[(largo["medio"] == "sast") & (largo["nivel"] == "equipo") & (largo["criterio"] == "oficial")]
    sast_t = (sast.pivot_table(index=["unidad", "indicador"], columns="mes", values="valor", aggfunc="sum", fill_value=0)
              .reset_index().rename(columns={"unidad": "equipo_zona"}))
    no_ub = (comp.assign(anio=comp["fecha"].dt.year).groupby(["medio", "ubicacion", "anio"]).size()
             .unstack(fill_value=0).reset_index())
    metodologia = [
        "LÍNEA BASE DE INDICADORES DE SEGURIDAD VIAL — EQUIPOS SAST EN OPERACIÓN — STTV Valledupar",
        f"Periodo de línea base (formato ANSV): {base_txt}, 36 meses (Año 1, 2 y 3) previos al inicio de operación.",
        "Zona: polígono de la capa «Zona de influencia» del SIG de equipos SAST. Criterio oficial mixto: los comparendos "
        "ubicados por dirección (punto sobre el eje de la vía) cuentan si caen dentro del polígono; los siniestros y los "
        f"comparendos ubicados por GPS (pueden caer fuera de la calzada), si caen a ≤ {BUFFER_M:.0f} m del polígono. "
        "Distancias en EPSG:9377 (CTM12). Las cifras con todo estricto y todo +15 m están en Observaciones y en «Resumen».",
        "Fallecidos y lesionados: personas (cantidad_muertos, cantidad_heridos) de los siniestros georreferenciados "
        f"del portal ANSV «Siniestralidad Valledupar», corte {corte_portal}.",
        f"Comparendos: export del sistema de comparendos 01/01/2023–{pd.Timestamp(corte_comp):%d/%m/%Y}. Se cuentan los "
        "impuestos por agentes y por la fotodetección previa (no SAST), por código; los generados por las cámaras SAST "
        "se excluyen de la línea base (hoja «SAST inicio»).",
        "Ubicación de comparendos: manda la dirección del comparendo, geocodificada sobre los ejes viales IGAC 2021 + OSM "
        f"(cruce o placa domiciliaria). La coordenada GPS de la comparendera solo se usa si la dirección no da un punto y "
        f"la coordenada cae en la cabecera; discrepancias GPS–dirección > {DISCORDANCIA_M:.0f} m quedan marcadas.",
        "Un evento en zonas de dos equipos cuenta para cada equipo; la hoja «Por punto» cuenta sin doble conteo.",
        "Cada hoja de equipo lista solo los códigos de infracción aprobados para ese equipo (Excel «Equipos SAST»).",
    ]
    if salto > 2:
        metodologia.append(
            "ADVERTENCIA: el portal registra en 2026 muchos más lesionados por mes que en 2023–2025 "
            f"({cob_anio['lesionados_mes'].min():.1f} a {cob_anio['lesionados_mes'].max():.1f} por mes en todo el municipio). "
            "La diferencia corresponde a un cambio en la captura, no necesariamente en la siniestralidad: la línea base de "
            "lesionados puede estar subestimada en los Años 1 y 2.")
    sens = pd.read_csv(OUTPUTS / "tables" / "sensibilidad_ubicacion.csv")
    sin_rev = pd.read_csv(OUTPUTS / "tables" / "siniestros_en_zona_revision.csv")
    anexos = {"Resumen": resumen, "Sensibilidad ubicación": sens, "Siniestros en zona": sin_rev, "Por punto": punto_t, "Serie 2023-2026": serie_t,
              "SAST inicio": sast_t, "Ubicación comparendos": no_ub,
              "Cobertura portal": cob.drop(columns="anio")}
    wb = libro(hojas, anexos, metodologia)
    ruta_xlsx = OUTPUTS / f"{nombre}.xlsx"
    wb.save(ruta_xlsx)

    # ---------------- HTML ----------------
    meses = [str(m) for m in meses_serie()]
    marcas = {str(BASE_INICIO): "inicio línea base", "2026-09": "inicio SAST"}
    partes = [f"<h1>Línea base de indicadores — equipos SAST en operación</h1>"
              f'<p class="sub">Secretaría de Tránsito y Transporte de Valledupar · reporte a la ANSV · '
              f"comparendos al {pd.Timestamp(corte_comp):%d/%m/%Y}, portal de siniestros al {corte_portal}</p>"]
    b = resumen
    tot_comp = b[~b["indicador"].isin(INDICES_VICTIMAS)]
    partes.append('<div class="tarjetas">'
                  + tarjeta(str(len(eq)), "equipos en operación", f"{eq['solicitud'].nunique()} puntos")
                  + tarjeta(fmt(punto_t.get('Fallecidos', pd.Series([0])).sum()), "fallecidos", f"{base_txt}, sin doble conteo")
                  + tarjeta(fmt(punto_t.get('Lesionados', pd.Series([0])).sum()), "lesionados", f"{base_txt}, sin doble conteo")
                  + tarjeta(fmt(punto_t[[c for c in punto_t.columns if c not in ('solicitud', 'Fallecidos', 'Lesionados')]].to_numpy().sum()),
                            "comparendos con código aprobado", f"{base_txt}, sin doble conteo")
                  + "</div>")
    partes.append('<p class="nota">Cifras de los 5 puntos sin doble conteo. Las tablas por equipo cuentan para cada '
                  'equipo lo que cae donde se solapan las zonas de un mismo punto.</p>')
    if salto > 2:
        partes.append(f'<div class="aviso"><b>Lesionados: registro no homogéneo.</b> En todo el municipio el portal registra '
                      f'{cob_anio.loc["2026", "lesionados_mes"]:.1f} lesionados por mes en 2026, frente a '
                      + ", ".join(f'{cob_anio.loc[a, "lesionados_mes"]:.1f} en {a}' for a in ("2023", "2024", "2025"))
                      + '. '
                      'Es un cambio en la captura (más fuentes desde 2026), no necesariamente en la siniestralidad: la línea '
                      'base de lesionados de los Años 1 y 2 puede estar subestimada.</div>')

    # tabla resumen por equipo
    partes.append(f"<h2>Línea base por equipo ({base_txt})</h2>"
                  f'<p class="sub">Criterio oficial mixto: comparendos ubicados por dirección dentro del polígono; siniestros y '
                  f"comparendos ubicados por GPS a ≤ {BUFFER_M:.0f} m. Agentes y fotodetección previa; sin cámaras SAST. "
                  f"Entre paréntesis, sensibilidad: todo estricto / todo +{BUFFER_M:.0f} m.</p>")
    for r in eq.itertuples():
        sub = b[b["equipo"] == r.equipo]
        filas = []
        for x in sub.itertuples():
            filas.append([x.indicador, f"{fmt(x.linea_base)} ({fmt(x.estricto)} / {fmt(x.buffer15)})",
                          "" if x.agentes is None or pd.isna(x.agentes) else fmt(x.agentes),
                          "" if x.fotodeteccion_previa is None or pd.isna(x.fotodeteccion_previa) else fmt(x.fotodeteccion_previa)])
        partes.append(f"<h3>{esc(r.equipo)} · {esc(r.punto.title())} · {esc(r.direccion)}</h3>"
                      + tabla(["Indicador", "Línea base (estricto / +15 m)", "Agentes", "Fotodetección previa"], filas))

    # series por punto
    partes.append("<h2>Evolución mensual por punto (ene-2023 a sep-2026)</h2>"
                  '<p class="sub">Unión de las zonas del punto (sin doble conteo), códigos aprobados del punto. '
                  "Los comparendos de las cámaras SAST no se grafican aquí (sección siguiente). "
                  "Pase el cursor sobre una barra para ver el detalle.</p>"
                  + leyenda(BASE, {k: v[1] for k, v in MEDIOS.items()}, {k: v[0] for k, v in MEDIOS.items()}))
    for sol, g in eq.groupby("solicitud"):
        d = largo[(largo["nivel"] == "solicitud") & (largo["unidad"] == str(sol)) & (largo["criterio"] == "oficial")
                  & largo["aprobado"]]
        series = {k: [int(d[(d.mes == m) & (d.medio == k)].valor.sum()) for m in meses] for k in BASE}
        vict = {k: [int(d[(d.mes == m) & (d.indicador == k)].valor.sum()) for m in meses] for k in VICTIMAS}
        nom = g["punto"].iat[0].title()
        partes.append(f"<h3>{esc(nom)} (solicitud {sol}: {', '.join(g['equipo'])})</h3>"
                      + svg_apiladas(meses, series, {k: v[1] for k, v in MEDIOS.items()},
                                     {k: v[0] for k, v in MEDIOS.items()}, f"Comparendos por mes en {nom}", marcas)
                      + leyenda(list(VICTIMAS), VICTIMAS, {k: k for k in VICTIMAS})
                      + svg_apiladas(meses, vict, VICTIMAS, {k: k for k in VICTIMAS},
                                     f"Fallecidos y lesionados por mes en {nom}", marcas, H=130))
    partes.append("<h3>Totales por punto, sin doble conteo</h3>")
    cols_p = [c for c in punto_t.columns if c != "solicitud"]
    partes.append(tabla(["Solicitud"] + cols_p, [[str(r[0])] + [fmt(v) for v in r[1:]]
                                                for r in punto_t[["solicitud"] + cols_p].itertuples(index=False)]))

    # SAST
    s_eq = sast.groupby(["unidad", "indicador"])["valor"].sum().unstack(fill_value=0)
    partes.append("<h2>Comparendos de las cámaras SAST (fuera de la línea base)</h2>"
                  '<p class="sub">Registros con fotodetección y dirección del equipo, por zona en la que caen. '
                  "Sirven para verificar el geocodificador: cada equipo debe recibir los de su propia dirección.</p>"
                  + tabla(["Zona"] + list(s_eq.columns), [[i] + [fmt(v) for v in row] for i, row in s_eq.iterrows()]))
    primeros = ev[(ev["tipo"] == "comparendo") & (ev["medio"] == "sast") & (ev["nivel"] == "equipo")
                  & (ev["criterio"] == "oficial")].groupby("unidad")["fecha"].min()
    if len(primeros):
        partes.append('<p class="nota">Primer registro SAST por zona: '
                      + "; ".join(f"{k} {v:%d/%m/%Y}" for k, v in primeros.items())
                      + f". Los anteriores al {eq['fecha_inicio'].min():%d/%m/%Y} se tratan como pruebas o arranque anticipado.</p>")

    # mapa
    z = gpd.read_file(PROCESSED / "equipos_sast.gpkg", layer="zonas")
    zb = gpd.read_file(PROCESSED / "equipos_sast.gpkg", layer="zonas_buffer")
    evc = ev[(ev["tipo"] == "comparendo") & (ev["nivel"] == "equipo") & (ev["criterio"] == "oficial")] \
        .drop_duplicates("id_evento")
    evs = ev[(ev["tipo"] == "siniestro") & (ev["nivel"] == "equipo") & (ev["criterio"] == "oficial")] \
        .drop_duplicates("id_evento")
    evs = evs[(evs["cantidad_muertos"] + evs["cantidad_heridos"]) > 0]
    datos = {"zonas": json.loads(z[["equipo", "geometry"]].to_json()),
             "zonas_buffer": json.loads(zb[["equipo", "geometry"]].to_json()),
             "nombres": {k: v[0] for k, v in MEDIOS.items()},
             "comparendos": [[round(r.lon_u, 6), round(r.lat_u, 6), r.medio, f"{r.fecha:%d/%m/%Y}", r.codigo]
                             for r in evc.itertuples()],
             "siniestros": [[round(r.lon, 6), round(r.lat, 6), f"{r.fecha:%d/%m/%Y}", r.gravedad,
                             int(r.cantidad_muertos), int(r.cantidad_heridos)] for r in evs.itertuples()]}
    partes.append("<h2>Mapa</h2><p class=\"sub\">Zonas de influencia (línea continua) y tolerancia de "
                  f"{BUFFER_M:.0f} m (línea punteada). Comparendos y siniestros con víctimas de ene-2023 a sep-2026 "
                  "dentro de alguna zona. Varios comparendos en un mismo cruce quedan superpuestos.</p><div id=\"mapa\"></div>")

    # calidad
    ub = comp["ubicacion"].value_counts()
    md = comp["metodo_dir"].value_counts()
    con = comp[comp["dist_gps_direccion_m"].notna()]
    partes.append("<h2>Calidad de los datos</h2><h3>Comparendos</h3>" + tabla(["Concepto", "Valor"], [
        ["Filas leídas (= suma de los pies «Total:» de los 4 archivos)", fmt(diag["filas_leidas"])],
        ["Otras filas malformadas apartadas", fmt(diag["filas_malformadas"])],
        ["Duplicados (mismo número y código) apartados", fmt(diag["duplicados_apartados"])],
        ["Conservados con conflicto de fecha/dirección/medio", fmt(diag["dup_conflicto"])],
        ["Comparendos depurados", fmt(diag["depurados"])],
        *[[f"Ubicados por: {k}", fmt(v)] for k, v in ub.items()],
        *[[f"Dirección → {k}", fmt(v)] for k, v in md.items()],
        ["Con GPS y dirección: mediana de la distancia", f"{con['dist_gps_direccion_m'].median():.0f} m"],
        [f"Con GPS y dirección: discrepancia > {DISCORDANCIA_M:.0f} m", f"{con['discordante'].mean():.1%}"],
    ]))
    partes.append("<h3>Sensibilidad de la ubicación</h3><p class=\"sub\">Comparendos de la línea base que tienen a la vez "
                  "GPS utilizable y dirección ubicada (códigos aprobados): cuántos caen en la zona de cada equipo según la "
                  "dirección y según el GPS, con polígono estricto y con +15 m. Si las columnas difieren mucho, la cifra del "
                  "equipo debe leerse como orden de magnitud: la incertidumbre de ubicación (mediana GPS–dirección "
                  f"{con['dist_gps_direccion_m'].median():.0f} m) es mayor que el ancho de las zonas (16–55 m).</p>"
                  + tabla(list(sens.columns), [[r[0]] + [fmt(v) for v in r[1:]] for r in sens.itertuples(index=False)]))
    partes.append(f"<h3>Siniestros en zona</h3><p class=\"sub\">{len(sin_rev)} siniestros caen en alguna zona entre ene-2023 y "
                  f"sep-2026 ({int(sin_rev['base'].sum())} en la línea base). Se ubican solo por la coordenada del portal; "
                  "la columna «posible gemelo» marca otro registro a ±1 día y < 150 m (p. ej. un «Deceso clínico» que repite el "
                  "hecho). Requieren revisión manual antes de reportarse.</p>"
                  + tabla(["Fecha", "Equipos", "Gravedad", "Fallec.", "Lesion.", "Fuente", "Dirección", "Posible gemelo"],
                          [[str(r.fecha)[:10], r.equipos, r.gravedad, int(r.cantidad_muertos), int(r.cantidad_heridos),
                            r.fuente, "" if pd.isna(r.direccion) else r.direccion,
                            "" if pd.isna(r.posible_gemelo) else r.posible_gemelo] for r in sin_rev.itertuples()]))
    ub_m = pd.crosstab(comp["medio"], comp["ubicacion"])
    partes.append("<p class=\"sub\">Ubicación por medio. Lo no ubicable no puede asignarse a ninguna zona: la línea base "
                  "es un piso, no un conteo exhaustivo.</p>"
                  + tabla(["Medio"] + list(ub_m.columns), [[i] + [fmt(v) for v in row] for i, row in ub_m.iterrows()]))
    partes.append("<h3>Siniestros del portal (todo el municipio)</h3>"
                  + tabla(["Año", "Meses", "Siniestros", "Fallecidos", "Lesionados", "Lesionados/mes"],
                          [[a, int(r.meses), fmt(r.siniestros), fmt(r.fallecidos), fmt(r.lesionados), f"{r.lesionados_mes:.1f}"]
                           for a, r in cob_anio.iterrows()]))
    partes.append("<h2>Metodología</h2><ul>" + "".join(f"<li>{esc(t)}</li>" for t in metodologia[1:]) + "</ul>"
                  f'<p class="nota">Archivos: {esc(ruta_xlsx.name)}; código en el repositorio sast-valledupar '
                  "(scripts 00–06).</p>")
    ruta_html = OUTPUTS / f"{nombre}.html"
    ruta_html.write_text(pagina("Línea base SAST Valledupar", "".join(partes), datos), encoding="utf-8")
    print(f"-> {ruta_xlsx.relative_to(OUTPUTS.parent)}\n-> {ruta_html.relative_to(OUTPUTS.parent)}")

    # control: Excel = tabla larga
    for info, val, _ in hojas:
        for ind in val.index:
            assert int(val.loc[ind].sum()) == int(resumen[(resumen.equipo == info["equipo"]) & (resumen.indicador == ind)]
                                                  .linea_base.iat[0])
    print("Control: totales del Excel = tabla larga ✓")


if __name__ == "__main__":
    main()
