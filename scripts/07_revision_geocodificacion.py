"""Etapa 7 — Listas para revisar a mano la geocodificación (no cambia ninguna cifra).

1. outputs/tables/revision_geocodificacion_en_zona.csv: TODAS las direcciones distintas de los
   comparendos (agentes y fotodetección previa, ene-2023–sep-2026) que quedaron dentro de alguna
   zona con el criterio oficial. Una fila por dirección: cuántos comparendos, en qué equipos,
   cómo se ubicó y dónde quedó el punto. Es la lista que decide las cifras.
2. outputs/tables/revision_geocodificacion_muestra_fuera.csv: muestra aleatoria (semilla fija) de
   100 comparendos ubicados FUERA de toda zona, para estimar si alguno debió caer dentro.

Columnas vacías `revision_ok` y `revision_nota` para que Santiago anote. Sin números de
comparendo ni datos personales: solo dirección, código, fecha, medio y coordenadas del punto.
"""

import pandas as pd

import _entorno  # noqa: F401
from sast.rutas import OUTPUTS, PROCESSED, SERIE_FIN, SERIE_INICIO

SEMILLA = 20261006
N_MUESTRA = 100
TABLAS = OUTPUTS / "tables"


def main() -> None:
    c = pd.read_parquet(PROCESSED / "comparendos_ubicados.parquet")
    c = c[c["medio"].isin(["agente", "fotodeteccion_previa"])]
    c = c[(c["fecha"].dt.to_period("M") >= SERIE_INICIO) & (c["fecha"].dt.to_period("M") <= SERIE_FIN)]
    c["id_evento"] = "C" + c["nro"] + "_" + c["codigo"]
    ev = pd.read_parquet(PROCESSED / "eventos_en_zona.parquet")
    ev = ev[(ev["tipo"] == "comparendo") & (ev["nivel"] == "equipo") & (ev["criterio"] == "oficial")]
    equipos = ev.groupby("id_evento")["unidad"].agg(lambda u: ", ".join(sorted(set(u))))
    c["equipos"] = c["id_evento"].map(equipos)

    dentro = c[c["equipos"].notna()]
    por_dir = (dentro.groupby(["direccion", "equipos"], dropna=False)
               .agg(comparendos=("id_evento", "size"),
                    codigos=("codigo", lambda x: ", ".join(f"{k}:{v}" for k, v in x.value_counts().items())),
                    medios=("medio", lambda x: ", ".join(f"{k}:{v}" for k, v in x.value_counts().items())),
                    ubicacion=("ubicacion", lambda x: ", ".join(sorted(set(x)))),
                    metodo_dir=("metodo_dir", "first"), vias=("vias", "first"), alias=("alias", "first"),
                    detalle=("detalle", "first"), lon=("lon_u", "median"), lat=("lat_u", "median"),
                    mediana_dist_gps_m=("dist_gps_direccion_m", "median"),
                    desde=("fecha", "min"), hasta=("fecha", "max"))
               .reset_index().sort_values("comparendos", ascending=False))
    por_dir["mediana_dist_gps_m"] = por_dir["mediana_dist_gps_m"].round(0)
    por_dir[["lon", "lat"]] = por_dir[["lon", "lat"]].round(6)
    por_dir["revision_ok"] = ""
    por_dir["revision_nota"] = ""
    por_dir.to_csv(TABLAS / "revision_geocodificacion_en_zona.csv", index=False, encoding="utf-8-sig")

    fuera = c[c["equipos"].isna() & c["x"].notna()]
    muestra = fuera.sample(n=min(N_MUESTRA, len(fuera)), random_state=SEMILLA)
    muestra = muestra[["fecha", "codigo", "medio", "direccion", "ubicacion", "metodo_dir", "vias", "detalle",
                       "lon_u", "lat_u", "dist_gps_direccion_m"]].sort_values("fecha")
    muestra[["lon_u", "lat_u"]] = muestra[["lon_u", "lat_u"]].round(6)
    muestra["dist_gps_direccion_m"] = muestra["dist_gps_direccion_m"].round(0)
    muestra["revision_ok"] = ""
    muestra["revision_nota"] = ""
    muestra.to_csv(TABLAS / "revision_geocodificacion_muestra_fuera.csv", index=False, encoding="utf-8-sig")

    print(f"En zona: {len(dentro):,} comparendos en {len(por_dir):,} combinaciones dirección–equipos "
          f"-> outputs/tables/revision_geocodificacion_en_zona.csv")
    print(f"  las 20 direcciones más frecuentes suman {por_dir['comparendos'].head(20).sum():,} "
          f"({por_dir['comparendos'].head(20).sum() / len(dentro):.0%} de lo que está en zona)")
    print(f"Fuera de zona: muestra de {len(muestra)} de {len(fuera):,} ubicados (semilla {SEMILLA}) "
          "-> outputs/tables/revision_geocodificacion_muestra_fuera.csv")


if __name__ == "__main__":
    main()
