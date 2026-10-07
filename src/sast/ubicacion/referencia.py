# Vendorizado de ~/Claude_code/Analisis_siniestralidad/src/ubicacion/referencia.py (commit d057993, 2026-10-06; = db52cbd tras la reescritura del historial de ese repo el 2026-10-07).
# Solo se cambian las importaciones; la lógica es la del original.
"""Capas de referencia del POT de Valledupar para el diagnóstico de ubicación.

Origen: GDB `GDB_POT_ME_Valledupar_2023.gdb` de la Oficina de Planeación (Ac. 011/2015 y
Ac. 014/2023), repartida por categoría en `~/Claude_code/POT_Valledupar` y publicada en el
portal en «00. Información territorial» (2026-10-02/03). Santiago copia los zip a
`data/raw/pot/`; aquí se leen sin descomprimir (`/vsizip/`).

El SHA-256 de cada zip se congela en `docs/pot_procedencia.csv` la primera vez y se
verifica en cada corrida: si cambia, se detiene. Todo se pasa de EPSG:3116 a EPSG:9377.
"""

from __future__ import annotations

import csv
import hashlib
import warnings
from datetime import date
from pathlib import Path

import geopandas as gpd
import pyogrio
from shapely import force_2d

from sast.rutas import CRS_METRICO

# nombre -> (zip de la categoría, capa)
CAPAS = {
    "municipio": ("Limites_Administrativos", "Valledupar_IGAC2021"),
    "comunas": ("Limites_Administrativos", "Comunas_2023"),
    "corregimientos": ("Limites_Administrativos", "Corregimientos"),
    "perimetro_urbano": ("Clasificacion_Suelo", "PerimetroUrbano_2023"),
    "centros_poblados": ("Clasificacion_Suelo", "PerimetroCorregimientos_2023"),
    "nomenclatura": ("Movilidad_Vial", "IGAC_2021_Nomenclatura_Vial_Urbana"),
}
ZIPS = sorted({z for z, _ in CAPAS.values()})


def _zip(directorio: Path, categoria: str) -> Path:
    return directorio / f"POT_Valledupar_{categoria}.gdb.zip"


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def verificar_pot(directorio: Path, registro: Path) -> dict[str, str]:
    """SHA-256 de los zip. Si `registro` no existe, lo crea (congela); si existe, exige que
    coincida. -> {categoría: sha256}."""
    faltan = [str(_zip(directorio, z)) for z in ZIPS if not _zip(directorio, z).exists()]
    if faltan:
        raise FileNotFoundError(
            "Faltan capas del POT (las copia Santiago):\n  mkdir -p data/raw/pot && cp "
            "~/Claude_code/POT_Valledupar/data/processed/publicacion/POT_Valledupar_"
            "{Limites_Administrativos,Clasificacion_Suelo,Movilidad_Vial}.gdb.zip data/raw/pot/"
            "\nNo encontrados: " + ", ".join(faltan))
    shas = {z: _sha256(_zip(directorio, z)) for z in ZIPS}
    if registro.exists():
        with open(registro, encoding="utf-8-sig") as f:
            congelado = {r["archivo"]: r["sha256"] for r in csv.DictReader(f)}
        for z, sha in shas.items():
            nombre = _zip(directorio, z).name
            if congelado.get(nombre) != sha:
                raise ValueError(f"{nombre}: el SHA-256 no coincide con {registro} "
                                 f"({sha[:12]}… frente a {str(congelado.get(nombre))[:12]}…). "
                                 "Si la capa cambió a propósito, borra el registro y documenta.")
    else:
        with open(registro, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["archivo", "sha256", "origen", "congelado"])
            for z, sha in shas.items():
                w.writerow([_zip(directorio, z).name, sha,
                            "~/Claude_code/POT_Valledupar/data/processed/publicacion/",
                            date.today().isoformat()])
        print(f"  SHA-256 del POT congelado en {registro}")
    return shas


def cargar_pot(directorio: Path) -> dict[str, gpd.GeoDataFrame]:
    """Las capas de `CAPAS` en EPSG:9377 y en 2D. Los avisos de GDAL (dimensión M que no
    se soporta y se descarta) se reportan, no se silencian."""
    capas = {}
    for nombre, (categoria, capa) in CAPAS.items():
        ruta = f"/vsizip/{_zip(directorio, categoria)}/POT_Valledupar_{categoria}.gdb"
        with warnings.catch_warnings(record=True) as avisos:
            warnings.simplefilter("always")
            g = pyogrio.read_dataframe(ruta, layer=capa)
        for a in {str(a.message) for a in avisos}:
            print(f"  aviso GDAL en {capa}: {a}")
        g = g.set_geometry(gpd.GeoSeries(force_2d(g.geometry.array), crs=g.crs,
                                         index=g.index)).to_crs(CRS_METRICO)
        capas[nombre] = g
    return capas
