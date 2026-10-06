"""Equipos SAST: lectura del Excel de equipos, la configuración y las zonas de influencia."""

from __future__ import annotations

import re

import geopandas as gpd
import pandas as pd
import yaml

from sast.rutas import BUFFER_M, CONFIG, CRS_GEO, CRS_METRICO, RAW, ultimo

_CODIGO = re.compile(r"\b([A-Z]\d{2})\b")


def codigos(texto) -> list[str]:
    """«C02, C03, … D05 y C32.» -> ['C02', 'C03', …] en el orden del texto, sin repetir."""
    vistos = []
    for c in _CODIGO.findall(str(texto or "").upper()):
        if c not in vistos:
            vistos.append(c)
    return vistos


def leer_config() -> dict:
    with open(CONFIG / "equipos.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def leer_excel() -> pd.DataFrame:
    """Hoja «Equipos SAST»: una fila por equipo. Las celdas combinadas (solicitud, referencia,
    estado) solo vienen en la primera fila de cada solicitud: se propagan hacia abajo."""
    ruta = ultimo(RAW / "equipos", "*_sttv_equipos-sast.xlsx")
    df = pd.read_excel(ruta, sheet_name="Equipos SAST")
    df[["ID SOLICITUD", "REFERENCIA", "Estado"]] = df[["ID SOLICITUD", "REFERENCIA", "Estado"]].ffill()
    out = pd.DataFrame({
        "equipo": df["NOMBRE"].str.strip(),
        "solicitud": df["ID SOLICITUD"].astype(int),
        "punto": df["REFERENCIA"].str.strip(),
        "direccion": df["DIRECCIÓN"].str.strip(),
        "sentido": df["SENTIDO DE DETECCIÓN"],
        "lon": df["LONGITUD"], "lat": df["LATITUD"],
        "infracciones_texto": df["INFRACCIONES"],
        "estado_solicitud": df["Estado"],
    })
    out["codigos"] = out["infracciones_texto"].map(codigos)
    out.attrs["fuente"] = ruta.name
    return out


def normalizar_direccion_sast(texto) -> str:
    """Llave para casar la dirección de un comparendo SAST con la `direccion_ansv` del equipo:
    «CALLE 21 - CARRERA 15 (OESTE - ESTE)» = «CALLE 21 - CARRERA 15 (SENTIDO OESTE - ESTE)»."""
    t = str(texto or "").upper().replace("SENTIDO", "")
    return re.sub(r"[^A-Z0-9]", "", t)


def equipos_operativos() -> pd.DataFrame:
    """Equipos de las solicitudes operativas: Excel (nombre, coordenadas, códigos) + config
    (fecha de inicio, código único, solicitud y dirección en la plataforma ANSV)."""
    cfg = leer_config()
    df = leer_excel()
    df = df[df["solicitud"].isin(cfg["solicitudes_operativas"])].copy()
    extra = cfg.get("equipos", {})
    faltan = sorted(set(df["equipo"]) - set(extra))
    sobran = sorted(set(extra) - set(df["equipo"]))
    if faltan or sobran:
        raise ValueError(f"config/equipos.yaml no cuadra con el Excel: faltan {faltan}, sobran {sobran}")
    sin_fecha = [e for e in df["equipo"] if not extra[e].get("fecha_inicio")]
    if sin_fecha:
        raise ValueError(f"Equipos sin fecha_inicio en config/equipos.yaml: {sin_fecha}")
    df["fecha_inicio"] = [pd.Timestamp(extra[e]["fecha_inicio"]) for e in df["equipo"]]
    for campo in ("codigo_unico", "solicitud_ansv", "direccion_ansv"):
        df[campo] = [extra[e].get(campo) for e in df["equipo"]]
    df["llave_sast"] = df["direccion_ansv"].map(normalizar_direccion_sast)
    if df["llave_sast"].duplicated().any():
        raise ValueError("Dos equipos con la misma dirección ANSV")
    return df.reset_index(drop=True)


def leer_zonas() -> gpd.GeoDataFrame:
    """Zonas de influencia (un polígono por equipo, campo `Equipo`) en EPSG:4326."""
    ruta = RAW / "equipos" / "Zona de influencia.shp"
    if not ruta.exists():
        raise FileNotFoundError(f"Falta {ruta}. Ver docs/ingesta.md.")
    z = gpd.read_file(ruta)
    if z.crs is None or z.crs.to_epsg() != CRS_GEO:
        raise ValueError(f"Zona de influencia: CRS {z.crs}, se esperaba EPSG:{CRS_GEO}")
    z = z.rename(columns={"Equipo": "equipo"})[["equipo", "geometry"]]
    z["equipo"] = z["equipo"].str.strip()
    return z


def zonas_operativas(equipos: pd.DataFrame) -> gpd.GeoDataFrame:
    """Zona de cada equipo operativo, en EPSG:9377, con la geometría estricta y con buffer."""
    z = leer_zonas()
    vacias = z[z.geometry.isna() | z.geometry.is_empty]["equipo"].tolist()
    z = z[~z["equipo"].isin(vacias)]
    dup = z["equipo"][z["equipo"].duplicated()].tolist()
    if dup:
        raise ValueError(f"Zonas repetidas para {dup}")
    sin_zona = sorted(set(equipos["equipo"]) - set(z["equipo"]))
    if sin_zona:
        raise ValueError(f"Equipos operativos sin zona de influencia: {sin_zona}")
    z = z[z["equipo"].isin(equipos["equipo"])].to_crs(CRS_METRICO)
    invalidas = z[~z.is_valid]["equipo"].tolist()
    if invalidas:
        raise ValueError(f"Zonas con geometría inválida: {invalidas}")
    z = z.merge(equipos[["equipo", "solicitud", "punto"]], on="equipo")
    z["geom_buffer"] = z.buffer(BUFFER_M)
    z.attrs["vacias_excluidas"] = vacias
    return z.reset_index(drop=True)
