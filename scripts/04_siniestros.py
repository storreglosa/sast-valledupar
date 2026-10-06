"""Etapa 4 — Siniestros del portal: fallecidos y lesionados como personas (decisión 6).

Usa el último corte de data/raw/portal/ (scripts/00_snapshot_portal.py). Contrasta
`cantidad_muertos`/`cantidad_heridos` con la tabla de víctimas y reporta la cobertura mensual,
porque el registro del portal cambia de intensidad entre años.

Salida: data/processed/siniestros.parquet, outputs/tables/siniestros_{cobertura,contraste}.csv.
"""

import geopandas as gpd
import pandas as pd

import _entorno  # noqa: F401
from sast.rutas import CRS_GEO, CRS_METRICO, OUTPUTS, PROCESSED, RAW, SERIE_FIN, SERIE_INICIO, ultimo

TABLAS = OUTPUTS / "tables"


def main() -> None:
    ruta = ultimo(RAW / "portal", "*_portal_siniestros.parquet")
    corte = ruta.name[:10]
    s = pd.read_parquet(ruta)
    v = pd.read_parquet(RAW / "portal" / f"{corte}_portal_victimas.parquet")
    print(f"Corte {corte}: {len(s):,} siniestros, {len(v):,} víctimas")

    s["fecha"] = pd.to_datetime(s["fechahecho"]).dt.normalize()
    s["mes"] = s["fecha"].dt.to_period("M")
    futuras = s["fecha"].gt(pd.Timestamp(corte))
    if futuras.any():
        print(f"  AVISO: {futuras.sum()} siniestros con fecha posterior al corte: {s.loc[futuras, 'codrot'].tolist()}")
    for c in ("cantidad_muertos", "cantidad_heridos"):
        nul = s[c].isna().sum()
        if nul:
            print(f"  AVISO: {nul} siniestros sin {c} (se cuentan como 0 y se reportan)")
        s[c] = s[c].fillna(0).astype(int)

    # contraste con la tabla de víctimas
    vv = v.groupby("codrot")["gravedad"].value_counts().unstack(fill_value=0)
    s = s.merge(vv.reindex(columns=["Muerto", "Herido"], fill_value=0)
                .rename(columns={"Muerto": "v_muertos", "Herido": "v_heridos"}),
                left_on="codrot", right_index=True, how="left")
    s[["v_muertos", "v_heridos"]] = s[["v_muertos", "v_heridos"]].fillna(0).astype(int)
    s["difiere_victimas"] = (s["cantidad_muertos"].ne(s["v_muertos"]) | s["cantidad_heridos"].ne(s["v_heridos"]))

    # coordenadas
    caja = s["lat"].between(9.6, 10.95) & s["lon"].between(-74.2, -72.9)
    s["coord_ok"] = s["lat"].notna() & caja
    if (~s["coord_ok"]).any():
        print(f"  AVISO: {(~s['coord_ok']).sum()} siniestros sin coordenada utilizable (no se pueden asignar a zona)")
    pts = gpd.GeoSeries(gpd.points_from_xy(s["lon"].where(s["coord_ok"]), s["lat"].where(s["coord_ok"])),
                        crs=CRS_GEO).to_crs(CRS_METRICO)
    s["x"], s["y"] = pts.x, pts.y

    serie = s[(s["mes"] >= SERIE_INICIO) & (s["mes"] <= SERIE_FIN)]
    cob = serie.groupby("mes").agg(siniestros=("codrot", "size"),
                                   con_victimas=("gravedad", lambda g: g.ne("Solo Daños").sum()),
                                   fallecidos=("cantidad_muertos", "sum"),
                                   lesionados=("cantidad_heridos", "sum"))
    cob = cob.reindex(pd.period_range(SERIE_INICIO, SERIE_FIN, freq="M"), fill_value=0)
    vacios = cob.index[cob["siniestros"].eq(0)].astype(str).tolist()
    if vacios:
        print(f"  AVISO: meses sin ningún siniestro en el portal: {vacios}")
    por_anio = cob.groupby(cob.index.year).sum()
    por_anio["meses"] = cob.groupby(cob.index.year).size()
    por_anio["lesionados_por_mes"] = (por_anio["lesionados"] / por_anio["meses"]).round(1)
    por_anio["fallecidos_por_mes"] = (por_anio["fallecidos"] / por_anio["meses"]).round(1)
    print("\nCobertura del portal (Valledupar, todas las zonas) por año:")
    print(por_anio.to_string())
    ratio = por_anio["lesionados_por_mes"].max() / max(por_anio["lesionados_por_mes"].min(), 0.1)
    if ratio > 2:
        print(f"  AVISO: los lesionados por mes cambian {ratio:.1f}× entre años: el registro de "
              "lesionados no es homogéneo en el periodo (ver informe).")
    print(f"\nFuente por año:\n{pd.crosstab(serie['fuente'], serie['fecha'].dt.year).to_string()}")

    dif = serie[serie["difiere_victimas"]]
    print(f"\nSiniestros 2023–2026 cuyo conteo difiere de la tabla de víctimas: {len(dif)} "
          f"(muertos {dif['cantidad_muertos'].sum()} vs {dif['v_muertos'].sum()}; "
          f"heridos {dif['cantidad_heridos'].sum()} vs {dif['v_heridos'].sum()})")

    cols = ["codrot", "fecha", "mes", "gravedad", "cantidad_muertos", "cantidad_heridos",
            "v_muertos", "v_heridos", "difiere_victimas", "direccion", "fuente", "lon", "lat",
            "x", "y", "coord_ok"]
    s[cols].assign(mes=s["mes"].astype(str), corte=corte).to_parquet(PROCESSED / "siniestros.parquet", index=False)
    cob.assign(mes=cob.index.astype(str)).to_csv(TABLAS / "siniestros_cobertura.csv", index=False, encoding="utf-8-sig")
    dif[["codrot", "fecha", "cantidad_muertos", "v_muertos", "cantidad_heridos", "v_heridos", "fuente"]] \
        .to_csv(TABLAS / "siniestros_contraste_victimas.csv", index=False, encoding="utf-8-sig")
    print("\n-> data/processed/siniestros.parquet")


if __name__ == "__main__":
    main()
