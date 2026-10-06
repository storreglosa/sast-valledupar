"""Etapa 1 — Equipos operativos y zonas de influencia.

Salida: data/processed/equipos_sast.gpkg (capas `equipos`, `zonas`, `zonas_buffer`) en
EPSG:4326, y outputs/tables/equipos_operativos.csv. Reporta inconsistencias, no las corrige.
"""

import geopandas as gpd

import _entorno  # noqa: F401
from sast.equipos import equipos_operativos, leer_excel, leer_zonas, zonas_operativas
from sast.rutas import BUFFER_M, CRS_GEO, CRS_METRICO, OUTPUTS, PROCESSED


def main() -> None:
    todos = leer_excel()
    eq = equipos_operativos()
    print(f"Excel: {todos.attrs['fuente']} — {len(todos)} equipos; operativos: {len(eq)}")
    for _, r in eq.iterrows():
        print(f"  {r.equipo}  sol {r.solicitud}  {r.punto:<24} {r.direccion:<28} "
              f"{len(r.codigos)} códigos: {', '.join(r.codigos)}")
    sin_cod = eq[eq["codigos"].map(len).eq(0)]["equipo"].tolist()
    if sin_cod:
        raise SystemExit(f"Equipos sin códigos aprobados: {sin_cod}")
    if not eq["fecha_inicio_confirmada"].all():
        print(f"  AVISO: fecha de inicio por defecto ({eq['fecha_inicio'].min().date()}) en "
              f"{(~eq['fecha_inicio_confirmada']).sum()} equipos (config/equipos.yaml).")
    if eq["id_ansv"].isna().any():
        print(f"  AVISO: {eq['id_ansv'].isna().sum()} equipos sin id ANSV (config/equipos.yaml).")

    z_todas = leer_zonas()
    zonas = zonas_operativas(eq)
    print(f"Zonas: {len(z_todas)} en la capa; sin geometría (excluidas): {zonas.attrs['vacias_excluidas']}")

    # control: el punto del equipo debe caer en (o muy cerca de) su zona
    pts = gpd.GeoDataFrame(eq, geometry=gpd.points_from_xy(eq.lon, eq.lat), crs=CRS_GEO).to_crs(CRS_METRICO)
    dist = {r.equipo: zonas.set_index("equipo").geometry[r.equipo].distance(r.geometry)
            for r in pts.itertuples()}
    for e, d in dist.items():
        a = zonas.set_index("equipo").geometry[e].area
        print(f"  {e}: área {a:,.0f} m², punto del equipo a {d:,.1f} m de su zona")
    lejos = {e: d for e, d in dist.items() if d > BUFFER_M}
    if lejos:
        print(f"  AVISO: equipos cuyo punto queda a más de {BUFFER_M:.0f} m de su zona: {lejos}")
    # solapes entre zonas
    zi = zonas.set_index("equipo")
    for i, a in enumerate(zi.index):
        for b in zi.index[i + 1:]:
            inter = zi.geometry[a].intersection(zi.geometry[b]).area
            if inter > 0:
                print(f"  solape {a} ∩ {b}: {inter:,.0f} m²")

    destino = PROCESSED / "equipos_sast.gpkg"
    destino.unlink(missing_ok=True)
    pts["codigos"] = pts["codigos"].map(", ".join)
    pts["dist_zona_m"] = pts["equipo"].map(dist)
    pts.drop(columns=["infracciones_texto"]).to_crs(CRS_GEO).to_file(destino, layer="equipos")
    zonas.drop(columns="geom_buffer").to_crs(CRS_GEO).to_file(destino, layer="zonas")
    zonas.set_geometry("geom_buffer").drop(columns="geometry").rename_geometry("geometry") \
        .to_crs(CRS_GEO).to_file(destino, layer="zonas_buffer")
    tabla = pts.drop(columns="geometry")
    tabla.to_csv(OUTPUTS / "tables" / "equipos_operativos.csv", index=False, encoding="utf-8-sig")
    print(f"-> {destino.relative_to(destino.parents[2])}")


if __name__ == "__main__":
    main()
