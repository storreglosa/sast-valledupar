"""Etapa 5 — Indicadores por equipo y mes en la zona de influencia.

Criterios espaciales: `oficial` (mixto, decisión 15: estricto para comparendos ubicados por
dirección, +15 m para siniestros y comparendos ubicados por GPS), `buffer15` y `estricto`
(sensibilidad).
Indicadores: Fallecidos y Lesionados (personas, portal) y cada código de infracción aprobado
para el equipo. Los comparendos se desglosan por medio (agente / fotodeteccion_previa); los
generados por las cámaras SAST van aparte (`sast`) y no entran a la línea base (decisión 1).
Un evento en zonas de dos equipos cuenta para cada uno (decisión 5); el total por punto
(solicitud) se calcula sobre la unión de sus zonas, sin doble conteo.

Salida: data/processed/indicadores_largo.parquet, data/processed/eventos_en_zona.parquet
(sin datos personales), outputs/tables/indicadores_largo.csv.
"""

import geopandas as gpd
import pandas as pd
from shapely import unary_union

import _entorno  # noqa: F401
from sast.equipos import equipos_operativos
from sast.rutas import BUFFER_M, CRS_METRICO, OUTPUTS, PROCESSED, SERIE_FIN, SERIE_INICIO, anio_base

CRITERIOS = {"buffer15": "geom_buffer", "estricto": "geometry"}


def zonas() -> gpd.GeoDataFrame:
    z = gpd.read_file(PROCESSED / "equipos_sast.gpkg", layer="zonas").to_crs(CRS_METRICO)
    z["geom_buffer"] = z.buffer(BUFFER_M)
    return z


def en_zonas(eventos: gpd.GeoDataFrame, z: gpd.GeoDataFrame, unidad: str) -> pd.DataFrame:
    """Pares (evento, unidad, criterio) con el evento dentro de la zona de la unidad."""
    partes = []
    for crit, col in CRITERIOS.items():
        zz = gpd.GeoDataFrame(z[[unidad]], geometry=z[col], crs=CRS_METRICO)
        j = gpd.sjoin(eventos[["id_evento", "geometry"]], zz, predicate="within")
        partes.append(j[["id_evento", unidad]].assign(criterio=crit))
    return pd.concat(partes, ignore_index=True)


def main() -> None:
    eq = equipos_operativos()
    sol_de = dict(zip(eq["equipo"], eq["solicitud"]))
    # inicio de operación por unidad: el del equipo; para el punto, el más temprano de sus equipos
    # (así su ventana no incluye meses en que alguno ya operaba)
    inicio = {**dict(zip(eq["equipo"], eq["fecha_inicio"])),
              **{str(k): v for k, v in eq.groupby("solicitud")["fecha_inicio"].min().items()}}
    z = zonas()
    zp = (z.groupby("solicitud").agg(punto=("punto", "first"),
                                     geometry=("geometry", lambda g: unary_union(list(g))),
                                     geom_buffer=("geom_buffer", lambda g: unary_union(list(g))))
          .reset_index())

    # comparendos ubicados
    c = pd.read_parquet(PROCESSED / "comparendos_ubicados.parquet")
    c = c[c["x"].notna()].copy()
    c["id_evento"] = "C" + c["nro"] + "_" + c["codigo"]
    assert c["id_evento"].is_unique
    gc = gpd.GeoDataFrame(c, geometry=gpd.points_from_xy(c["x"], c["y"]), crs=CRS_METRICO)
    # siniestros con coordenada
    s = pd.read_parquet(PROCESSED / "siniestros.parquet")
    s = s[s["coord_ok"]].copy()
    s["id_evento"] = "S" + s["codrot"]
    assert s["id_evento"].is_unique
    gs = gpd.GeoDataFrame(s, geometry=gpd.points_from_xy(s["x"], s["y"]), crs=CRS_METRICO)

    filas = []
    eventos = []
    for unidad, zz in (("equipo", z), ("solicitud", zp)):
        cols_c = ["id_evento", "fecha", "codigo", "medio", "ubicacion", "discordante", "sast_antes_inicio",
                  "direccion", "lon_u", "lat_u"]
        jc = en_zonas(gc[gc["medio"] != "sast"], zz, unidad).merge(c[cols_c], on="id_evento")
        # comparendos SAST: cuentan para su propio equipo (dirección ANSV), no por la zona donde caen
        cs = c[c["medio"] == "sast"].copy()
        cs[unidad] = cs["equipo_sast"] if unidad == "equipo" else cs["equipo_sast"].map(sol_de)
        jc = pd.concat([jc] + [cs[cols_c + [unidad]].assign(criterio=k) for k in CRITERIOS], ignore_index=True)
        js = en_zonas(gs, zz, unidad).merge(
            s[["id_evento", "fecha", "cantidad_muertos", "cantidad_heridos", "gravedad", "fuente",
               "direccion", "lon", "lat"]], on="id_evento")
        for j in (jc, js):
            j["mes"] = j["fecha"].dt.to_period("M")
        jc = jc[(jc["mes"] >= SERIE_INICIO) & (jc["mes"] <= SERIE_FIN)]
        js = js[(js["mes"] >= SERIE_INICIO) & (js["mes"] <= SERIE_FIN)]
        # criterio oficial mixto (decisión 15): comparendos ubicados por dirección (sobre el eje
        # de la vía) -> polígono estricto; ubicados por GPS y siniestros (coordenada) -> +15 m
        por_dir = jc["ubicacion"].isin(["direccion", "direccion_gps", "equipo"])
        jc = pd.concat([jc, jc[(por_dir & (jc["criterio"] == "estricto"))
                               | (~por_dir & (jc["criterio"] == "buffer15"))].assign(criterio="oficial")],
                       ignore_index=True)
        js = pd.concat([js, js[js["criterio"] == "buffer15"].assign(criterio="oficial")], ignore_index=True)
        eventos.append(jc.assign(nivel=unidad, tipo="comparendo").rename(columns={unidad: "unidad"}))
        eventos.append(js.assign(nivel=unidad, tipo="siniestro").rename(columns={unidad: "unidad"}))

        a = (jc.groupby([unidad, "criterio", "mes", "codigo", "medio"]).size()
             .rename("valor").reset_index().rename(columns={"codigo": "indicador"}))
        for ind, col in (("Fallecidos", "cantidad_muertos"), ("Lesionados", "cantidad_heridos")):
            b = (js.groupby([unidad, "criterio", "mes"])[col].sum().rename("valor").reset_index()
                 .assign(indicador=ind, medio="portal"))
            a = pd.concat([a, b], ignore_index=True)
        filas.append(a.rename(columns={unidad: "unidad"}).assign(nivel=unidad))

    largo = pd.concat(filas, ignore_index=True)
    largo["unidad"] = largo["unidad"].astype(str)
    largo["anio_base"] = [anio_base(m, inicio[u]) for m, u in zip(largo["mes"], largo["unidad"])]
    # código aprobado para el equipo (o para algún equipo del punto)
    aprob_eq = {r.equipo: set(r.codigos) for r in eq.itertuples()}
    aprob_sol = eq.groupby("solicitud")["codigos"].agg(lambda x: set().union(*x)).to_dict()
    aprob = {**aprob_eq, **{str(k): v for k, v in aprob_sol.items()}}
    largo["aprobado"] = [ind in ("Fallecidos", "Lesionados") or ind in aprob[u]
                         for ind, u in zip(largo["indicador"], largo["unidad"])]
    largo["mes"] = largo["mes"].astype(str)

    ev = pd.concat(eventos, ignore_index=True)
    ev["mes"] = ev["mes"].astype(str)
    ev["unidad"] = ev["unidad"].astype(str)

    # resumen en pantalla: línea base oficial por equipo
    base = largo[(largo["nivel"] == "equipo") & largo["anio_base"].notna() & largo["aprobado"]
                 & (largo["medio"] != "sast")]
    for crit in ["oficial", *CRITERIOS]:
        t = base[base["criterio"] == crit].pivot_table(index="unidad", columns="indicador",
                                                       values="valor", aggfunc="sum", fill_value=0)
        print(f"\nLínea base (36 meses previos al inicio de cada equipo), criterio {crit} (aprobados, sin SAST):")
        print(t.to_string())
    sast = largo[(largo["medio"] == "sast") & (largo["nivel"] == "equipo") & (largo["criterio"] == "oficial")]
    print("\nComparendos SAST por equipo (aparte):")
    print(sast.pivot_table(index="unidad", columns="indicador", values="valor", aggfunc="sum", fill_value=0).to_string())

    # siniestros en zona para revisión manual (hallazgo de auditoría 2026-10-06), con posible gemelo:
    # otro siniestro del portal a ±1 día y < 150 m (típico de «Deceso clínico» que repite un hecho)
    sz = ev[(ev["tipo"] == "siniestro") & (ev["criterio"] == "oficial") & (ev["nivel"] == "equipo")]
    rev = (sz.groupby("id_evento").agg(equipos=("unidad", lambda u: ", ".join(sorted(u))))
           .join(s.set_index("id_evento")[["codrot", "fecha", "gravedad", "cantidad_muertos", "cantidad_heridos",
                                           "fuente", "direccion", "x", "y"]]).reset_index(drop=True))
    gemelos = []
    for r in rev.itertuples():
        cerca = s[(s["codrot"] != r.codrot) & ((s["fecha"] - r.fecha).abs() <= pd.Timedelta(days=1))
                  & (((s["x"] - r.x) ** 2 + (s["y"] - r.y) ** 2) ** 0.5 < 150)]
        gemelos.append("; ".join(f"{c.codrot} ({c.fuente}, {c.fecha:%d/%m/%Y}, m {c.cantidad_muertos} h {c.cantidad_heridos})"
                                 for c in cerca.itertuples()))
    rev["posible_gemelo"] = gemelos
    rev["base"] = [any(anio_base(f.to_period("M"), inicio[e]) for e in eqs.split(", "))
                   for f, eqs in zip(rev["fecha"], rev["equipos"])]
    rev.drop(columns=["x", "y"]).sort_values("fecha").to_csv(
        OUTPUTS / "tables" / "siniestros_en_zona_revision.csv", index=False, encoding="utf-8-sig")
    print(f"\nSiniestros en alguna zona (buffer 15 m), ene-2023–sep-2026: {len(rev)} "
          f"({rev['base'].sum()} en la línea base; {(rev['posible_gemelo'] != '').sum()} con posible gemelo) "
          "-> outputs/tables/siniestros_en_zona_revision.csv")

    # sensibilidad de la ubicación (hallazgo 4 de la auditoría): sobre los comparendos de la línea
    # base con GPS utilizable y dirección ubicada, ¿cuántos caen en cada zona por dirección y por GPS?
    cg = pd.read_parquet(PROCESSED / "comparendos_ubicados.parquet")
    cg = cg[cg["medio"].isin(["agente", "fotodeteccion_previa"]) & cg["coord_estado"].eq("ok")
            & cg["ubicacion"].isin(["direccion", "direccion_gps"])].copy()
    # ventana más amplia de los equipos (el filtro por equipo se hace tras la unión espacial)
    cg = cg[cg["fecha"].dt.to_period("M").map(lambda m: any(anio_base(m, f) for f in eq["fecha_inicio"]))]
    cg["id_evento"] = "C" + cg["nro"] + "_" + cg["codigo"]
    gps = gpd.GeoSeries(gpd.points_from_xy(cg["lon"], cg["lat"]), crs=4326).to_crs(CRS_METRICO)
    filas_s = []
    for fuente, geom in (("direccion", gpd.points_from_xy(cg["x"], cg["y"])), ("gps", gps.values)):
        g = gpd.GeoDataFrame(cg[["id_evento", "codigo"]], geometry=geom, crs=CRS_METRICO)
        j = en_zonas(g, z, "equipo").merge(cg[["id_evento", "codigo"]], on="id_evento")
        j = j.merge(cg[["id_evento", "fecha"]], on="id_evento")
        j = j[[c in aprob_eq[e] and anio_base(f.to_period("M"), inicio[e]) is not None
               for c, e, f in zip(j["codigo"], j["equipo"], j["fecha"])]]
        filas_s.append(j.groupby(["equipo", "criterio"]).size().rename(fuente))
    sens = pd.concat(filas_s, axis=1).fillna(0).astype(int).unstack("criterio")
    sens.columns = [f"{a}_{b}" for a, b in sens.columns]
    sens = sens.reindex(sorted(aprob_eq)).fillna(0).astype(int).reset_index()
    sens.to_csv(OUTPUTS / "tables" / "sensibilidad_ubicacion.csv", index=False, encoding="utf-8-sig")
    print(f"\nSensibilidad (línea base, {len(cg):,} comparendos con GPS y dirección ubicada; códigos aprobados):")
    print(sens.to_string(index=False))

    largo.to_parquet(PROCESSED / "indicadores_largo.parquet", index=False)
    ev.to_parquet(PROCESSED / "eventos_en_zona.parquet", index=False)
    largo.to_csv(OUTPUTS / "tables" / "indicadores_largo.csv", index=False, encoding="utf-8-sig")
    print("\n-> data/processed/indicadores_largo.parquet")


if __name__ == "__main__":
    main()
