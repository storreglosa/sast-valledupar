"""Etapa 5 — Indicadores por equipo y mes en la zona de influencia.

Criterios espaciales (decisión 3): `buffer15` (oficial: polígono + 15 m) y `estricto`.
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
        jc = en_zonas(gc, zz, unidad).merge(
            c[["id_evento", "fecha", "codigo", "medio", "ubicacion", "discordante", "sast_antes_inicio",
               "direccion", "lon_u", "lat_u"]], on="id_evento")
        js = en_zonas(gs, zz, unidad).merge(
            s[["id_evento", "fecha", "cantidad_muertos", "cantidad_heridos", "gravedad", "fuente",
               "direccion", "lon", "lat"]], on="id_evento")
        for j in (jc, js):
            j["mes"] = j["fecha"].dt.to_period("M")
        jc = jc[(jc["mes"] >= SERIE_INICIO) & (jc["mes"] <= SERIE_FIN)]
        js = js[(js["mes"] >= SERIE_INICIO) & (js["mes"] <= SERIE_FIN)]
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
    largo["anio_base"] = largo["mes"].map(anio_base)
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
    for crit in CRITERIOS:
        t = base[base["criterio"] == crit].pivot_table(index="unidad", columns="indicador",
                                                       values="valor", aggfunc="sum", fill_value=0)
        print(f"\nLínea base sep-2023–ago-2026, criterio {crit} (aprobados, sin SAST):")
        print(t.to_string())
    sast = largo[(largo["medio"] == "sast") & (largo["nivel"] == "equipo") & (largo["criterio"] == "buffer15")]
    print("\nComparendos SAST por equipo de zona (aparte):")
    print(sast.pivot_table(index="unidad", columns="indicador", values="valor", aggfunc="sum", fill_value=0).to_string())

    largo.to_parquet(PROCESSED / "indicadores_largo.parquet", index=False)
    ev.to_parquet(PROCESSED / "eventos_en_zona.parquet", index=False)
    largo.to_csv(OUTPUTS / "tables" / "indicadores_largo.csv", index=False, encoding="utf-8-sig")
    print("\n-> data/processed/indicadores_largo.parquet")


if __name__ == "__main__":
    main()
