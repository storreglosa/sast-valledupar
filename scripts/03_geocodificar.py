"""Etapa 3 — Ubicación de cada comparendo (decisión 4: manda la dirección).

Por cada dirección distinta se busca un punto en los ejes (src/sast/geocodificacion.py).
Luego, por registro:
  direccion          la dirección da un punto (cruce o domiciliaria). Si además hay GPS y
                     está a más de DISCORDANCIA_M, se marca `discordante`.
  direccion_gps      la dirección da varios cruces posibles y el GPS elige el más cercano.
  equipo             comparendo de una cámara SAST: coordenada de su equipo en el Excel de equipos.
  gps                la dirección no da punto; el GPS es utilizable y cae en el perímetro
                     urbano (+ margen de la cabecera).
  no_ubicable        ninguno de los anteriores.

Salida: data/processed/comparendos_ubicados.parquet (EPSG:4326 en lon_u/lat_u y 9377 en x/y),
data/processed/cache/direcciones.parquet, outputs/tables/geocodificacion_resumen.csv.
"""

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import Point

import _entorno  # noqa: F401
from sast.equipos import leer_excel
from sast.geocodificacion import Geocodificador
from sast.rutas import CRS_GEO, CRS_METRICO, DISCORDANCIA_M, DOCS, OUTPUTS, PROCESSED, RAW
from sast.ubicacion.geocodificar import MARGEN_CABECERA_M, acuerdo_referencias, preparar_ejes
from sast.ubicacion.referencia import cargar_pot, verificar_pot


def referencias():
    dir_pot = RAW / "pot"
    verificar_pot(dir_pot, DOCS / "pot_procedencia.csv")
    pot = cargar_pot(dir_pot)
    gpkg = sorted((RAW / "red_vial").glob("*_osm_red-vial-valledupar.gpkg"))
    if not gpkg:
        raise SystemExit("Falta la red OSM en data/raw/red_vial/ (docs/ingesta.md).")
    osm = gpd.read_file(gpkg[-1], layer="vias")
    perimetro = pot["perimetro_urbano"].union_all()
    zona = perimetro.buffer(MARGEN_CABECERA_M)
    ejes = preparar_ejes({"IGAC": (pot["nomenclatura"], "TEXTO"), "OSM": (osm, "nombre")}, zona)
    ac = acuerdo_referencias(pot["nomenclatura"], "TEXTO", osm, "nombre", zona)
    print(f"Referencias: {len(ejes.por_clave)} vías con nombre (IGAC+OSM, {gpkg[-1].name}); "
          f"solo IGAC {ac['solo_igac']}, solo OSM {ac['solo_osm']}, comunes {ac['comunes']}; "
          f"longitud coincidente {ac['fraccion_longitud_coincide']:.0%}")
    return ejes, zona


def main() -> None:
    c = pd.read_parquet(PROCESSED / "comparendos.parquet")
    ejes, zona_urbana = referencias()
    eq = leer_excel()
    pe = gpd.GeoSeries(gpd.points_from_xy(eq["lon"], eq["lat"]), crs=CRS_GEO).to_crs(CRS_METRICO)
    geo = Geocodificador(ejes, dict(zip(eq["direccion"], pe)))
    print(f"Direcciones oficiales de equipos SAST como puntos conocidos: {len(eq)}")

    dirs = c["direccion"].fillna("").unique()
    print(f"{len(c):,} comparendos, {len(dirs):,} direcciones distintas")
    filas = []
    for t in dirs:
        r = geo.ubicar(t)
        filas.append({"direccion": t, "metodo_dir": r.metodo, "tipo_direccion": r.tipo_direccion,
                      "vias": r.vias, "alias": r.alias, "detalle": r.detalle, "n_candidatos": len(r.candidatos),
                      "candidatos": [(p.x, p.y) for p in r.candidatos]})
    cache = pd.DataFrame(filas)
    (PROCESSED / "cache").mkdir(exist_ok=True)
    cache.drop(columns="candidatos").to_parquet(PROCESSED / "cache" / "direcciones.parquet", index=False)
    print("\nDirecciones distintas por resultado:")
    print(cache["metodo_dir"].value_counts().to_string())

    c = c.merge(cache, on="direccion", how="left", validate="many_to_one")
    gps_ok = c["coord_estado"].eq("ok")
    gps = gpd.GeoSeries(gpd.points_from_xy(c["lon"].where(gps_ok), c["lat"].where(gps_ok)),
                        crs=CRS_GEO).to_crs(CRS_METRICO)
    gx, gy = gps.x.to_numpy(), gps.y.to_numpy()

    x = np.full(len(c), np.nan)
    y = np.full(len(c), np.nan)
    ubic = np.array(["no_ubicable"] * len(c), dtype=object)
    dist_gps = np.full(len(c), np.nan)
    # comparendos SAST: en la coordenada de su equipo (Excel de equipos), sin geocodificar
    pe_equipo = dict(zip(eq["equipo"], pe))
    for i, (met, cand, eqs) in enumerate(zip(c["metodo_dir"], c["candidatos"], c["equipo_sast"])):
        tiene_gps = gps_ok.iat[i]
        if isinstance(eqs, str):
            x[i], y[i] = pe_equipo[eqs].x, pe_equipo[eqs].y
            ubic[i] = "equipo"
            continue
        if met in ("cruce", "cruce_hueco", "punto_equipo", "cruce_aproximado", "domiciliaria", "domiciliaria_cuadra"):
            x[i], y[i] = cand[0]
            ubic[i] = "direccion"
        elif met == "ambigua" and tiene_gps:
            p = Point(gx[i], gy[i])
            x[i], y[i] = min(cand, key=lambda q: p.distance(Point(q)))
            ubic[i] = "direccion_gps"
        if tiene_gps:
            if ubic[i] != "no_ubicable":
                dist_gps[i] = np.hypot(gx[i] - x[i], gy[i] - y[i])
            elif zona_urbana.contains(Point(gx[i], gy[i])):
                x[i], y[i] = gx[i], gy[i]
                ubic[i] = "gps"
    c["ubicacion"] = ubic
    c["x"], c["y"] = x, y
    c["dist_gps_direccion_m"] = dist_gps
    c["discordante"] = c["dist_gps_direccion_m"] > DISCORDANCIA_M
    pts = gpd.GeoSeries(gpd.points_from_xy(c["x"], c["y"]), crs=CRS_METRICO).to_crs(CRS_GEO)
    ok = c["x"].notna().to_numpy()
    c["lon_u"] = np.where(ok, pts.x.to_numpy(), np.nan)
    c["lat_u"] = np.where(ok, pts.y.to_numpy(), np.nan)
    c = c.drop(columns="candidatos")

    print("\nComparendos por ubicación y medio:")
    print(pd.crosstab(c["ubicacion"], c["medio"], margins=True).to_string())
    con = c[c["dist_gps_direccion_m"].notna()]
    print(f"\nConcordancia GPS ↔ dirección ({len(con):,} con ambos): mediana "
          f"{con['dist_gps_direccion_m'].median():.0f} m; ≤ 50 m {con['dist_gps_direccion_m'].le(50).mean():.0%}; "
          f"> {DISCORDANCIA_M:.0f} m {con['discordante'].mean():.0%}")
    assert c["ubicacion"].value_counts().sum() == len(c)

    c.to_parquet(PROCESSED / "comparendos_ubicados.parquet", index=False)
    res = pd.crosstab([c["medio"], c["ubicacion"]], c["fecha"].dt.year).reset_index()
    res.to_csv(OUTPUTS / "tables" / "geocodificacion_resumen.csv", index=False, encoding="utf-8-sig")
    print("\n-> data/processed/comparendos_ubicados.parquet")


if __name__ == "__main__":
    main()
