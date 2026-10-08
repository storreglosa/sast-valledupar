"""Etapa 10 — Datos públicos del tablero de semáforos SAST (tablero/data/*.json).

Lee lo que dejó la etapa 9 (data/processed/semaforos.json), la capa de equipos SAST
(outputs/capas/equipos_sast.geojson), la línea base oficial (hoja «Resumen» del Excel para la
plataforma ANSV, cruzada con outputs/tables/indicadores_largo.csv) y config/semaforos.yaml.
La asignación grupo -> acceso solo se publica validada (decisión 28).

    python scripts/10_tablero.py             # lo que se publica
    python scripts/10_tablero.py --borrador  # ensayo local con el borrador sin validar (no publicable)
"""

import argparse
import json

import geopandas as gpd
import pandas as pd
import yaml

import _entorno  # noqa: F401
from sast import tablero
from sast.rutas import CONFIG, OUTPUTS, PROCESSED, RAIZ, ultimo

DESTINO = RAIZ / "tablero" / "data"


def escribir(nombre: str, datos: dict) -> None:
    ruta = DESTINO / nombre
    ruta.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  {ruta.relative_to(RAIZ)}  {ruta.stat().st_size / 1024:.0f} KB")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--borrador", action="store_true", help="incluye el borrador de accesos sin validar")
    args = ap.parse_args()

    with open(CONFIG / "semaforos.yaml", encoding="utf-8") as f:
        conf = yaml.safe_load(f)
    with open(PROCESSED / "semaforos.json", encoding="utf-8") as f:
        proc = json.load(f)
    sem, geo = tablero.semaforos(proc, conf, args.borrador)
    semaforo_de = {e: it["id"] for it in proc["intersecciones"] for e in it["equipos"]}
    eq = gpd.read_file(OUTPUTS / "capas" / "equipos_sast.geojson")
    largo = pd.read_csv(OUTPUTS / "tables" / "indicadores_largo.csv", encoding="utf-8-sig")
    geocod = pd.read_csv(OUTPUTS / "tables" / "geocodificacion_resumen.csv", encoding="utf-8-sig")
    excel = ultimo(OUTPUTS, "*_sttv_linea-base-sast_plataforma-ansv.xlsx")
    sast = tablero.sast(eq, excel, largo, geocod, semaforo_de)

    DESTINO.mkdir(parents=True, exist_ok=True)
    print(f"Datos del tablero ({'BORRADOR, no publicable' if args.borrador else 'publicable'}):")
    escribir("semaforos.json", sem)
    escribir("geometria.json", geo)
    escribir("sast.json", sast)
    for it in sem["intersecciones"]:
        print(f"  {it['nombre']:<24} asignación {it['asignacion']['estado']}")
    print(f"  {len(sast['equipos']['features'])} equipos SAST, línea base de {len(sast['linea_base'])} "
          f"(cuadra con la tabla larga); cortes {sast['cortes']}")


if __name__ == "__main__":
    main()
