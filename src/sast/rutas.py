"""Rutas del repo, sistemas de referencia y periodos de la línea base."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "data" / "raw"
PROCESSED = RAIZ / "data" / "processed"
OUTPUTS = RAIZ / "outputs"
DOCS = RAIZ / "docs"
CONFIG = RAIZ / "config"

CRS_GEO = 4326        # almacenamiento (Survey123, portal)
CRS_METRICO = 9377    # MAGNA-SIRGAS / Origen-Nacional (CTM12): toda medida en metros

# Serie mensual del informe HTML (decisión 1, 2026-10-06)
SERIE_INICIO = pd.Period("2023-01", "M")
SERIE_FIN = pd.Period("2026-09", "M")
# Línea base del formato ANSV: 36 meses previos al inicio de operación (Año 1, 2 y 3)
BASE_INICIO = pd.Period("2023-09", "M")
BASE_FIN = pd.Period("2026-08", "M")

BUFFER_M = 15.0              # tolerancia de la zona de influencia (decisión 3)
DISCORDANCIA_M = 100.0       # coordenada GPS frente a dirección (decisión 4)


def meses_serie() -> pd.PeriodIndex:
    return pd.period_range(SERIE_INICIO, SERIE_FIN, freq="M")


def meses_base() -> pd.PeriodIndex:
    return pd.period_range(BASE_INICIO, BASE_FIN, freq="M")


def anio_base(mes: pd.Period) -> int | None:
    """Año 1, 2 o 3 de la línea base ANSV (sep–ago); None si el mes queda fuera."""
    if mes < BASE_INICIO or mes > BASE_FIN:
        return None
    return (mes - BASE_INICIO).n // 12 + 1


def ultimo(directorio: Path, patron: str) -> Path:
    """Archivo más reciente (por nombre con fecha AAAA-MM-DD al inicio) que cumple el patrón."""
    candidatos = sorted(directorio.glob(patron))
    if not candidatos:
        raise FileNotFoundError(f"No hay {patron} en {directorio}. Ver docs/ingesta.md.")
    return candidatos[-1]
