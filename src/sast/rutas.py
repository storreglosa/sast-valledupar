"""Rutas del repo, sistemas de referencia y periodos de la línea base."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
# SAST_RAW permite ensayar el pipeline contra otra carpeta de insumos sin tocar data/raw/
RAW = Path(os.environ.get("SAST_RAW", RAIZ / "data" / "raw"))
PROCESSED = RAIZ / "data" / "processed"
OUTPUTS = RAIZ / "outputs"
DOCS = RAIZ / "docs"
CONFIG = RAIZ / "config"

CRS_GEO = 4326        # almacenamiento (Survey123, portal)
CRS_METRICO = 9377    # MAGNA-SIRGAS / Origen-Nacional (CTM12): toda medida en metros

# Serie mensual del informe HTML (decisión 1, 2026-10-06)
SERIE_INICIO = pd.Period("2023-01", "M")
SERIE_FIN = pd.Period("2026-09", "M")
# Línea base del formato ANSV: los 36 meses previos al mes de inicio de operación DE CADA EQUIPO
# (Año 1, 2 y 3). En el formulario ANSV de un equipo con inicio el 02/09/2026 el Año 1 es
# sep-2023–ago-2024. Ver `ventana_base`.
MESES_BASE = 36

BUFFER_M = 15.0              # tolerancia de la zona de influencia (decisión 3)
DISCORDANCIA_M = 100.0       # coordenada GPS frente a dirección (decisión 4)


def meses_serie() -> pd.PeriodIndex:
    return pd.period_range(SERIE_INICIO, SERIE_FIN, freq="M")


def ventana_base(fecha_inicio) -> pd.PeriodIndex:
    """Los 36 meses previos al mes de inicio de operación."""
    fin = pd.Timestamp(fecha_inicio).to_period("M") - 1
    return pd.period_range(fin - (MESES_BASE - 1), fin, freq="M")


def anio_base(mes: pd.Period, fecha_inicio) -> int | None:
    """Año 1, 2 o 3 de la línea base del equipo; None si el mes queda fuera de su ventana."""
    v = ventana_base(fecha_inicio)
    if mes < v[0] or mes > v[-1]:
        return None
    return (mes - v[0]).n // 12 + 1


def ultimo(directorio: Path, patron: str) -> Path:
    """Archivo más reciente (por nombre con fecha AAAA-MM-DD al inicio) que cumple el patrón."""
    candidatos = sorted(directorio.glob(patron))
    if not candidatos:
        raise FileNotFoundError(f"No hay {patron} en {directorio}. Ver docs/ingesta.md.")
    return candidatos[-1]
