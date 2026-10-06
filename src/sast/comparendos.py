"""Comparendos 2023–2026: lectura del export «Comparendos Pendientes Notificacion».

Los «.xls» del zip son HTML (latin-1) con una tabla de 21 columnas. Se leen sin
descomprimir y **los datos personales (cédula, tipo de documento, nombre, apellido, placa) se
descartan en la lectura**: nunca llegan a un DataFrame ni a `data/processed/`.

Reglas [Nuestra] (docs/metodologia.md):
- Fila malformada (número de celdas distinto del encabezado): se aparta y se cuenta.
- Duplicados por (número de comparendo, código): ver `depurar_duplicados`.
- Coordenada (1, 1) o (0, 0): marcador de «sin coordenada», no un punto.
- Medio:
    sast                 Foto Detección = S y dirección con el patrón de los equipos SAST
                         («CALLE 21 - CARRERA 15 (OESTE - ESTE)»: vía - vía (sentido)).
    fotodeteccion_previa Foto Detección = S sin ese patrón.
    agente               Foto Detección = N.
"""

from __future__ import annotations

import html
import re
import zipfile

import numpy as np
import pandas as pd

from sast.rutas import RAW, ultimo

ENCABEZADO = ["Nro Comparendo", "Fecha Comparendo", "Secretaría", "Tipo Documento",
              "Cédula Infractor", "Nombre", "Apellido", "Placa", "Infracciones Comparendo",
              "Valor", "Polca", "Nro Resolución", "Estado Resolución", "Foto Detección",
              "Fecha Notificacion", "Fuente Comparendo", "Latitud", "Longitud",
              "Dirección Infracción", "Inmovilización (S/N)", "Descripción Tipo vehículo"]
PERSONALES = {"Tipo Documento", "Cédula Infractor", "Nombre", "Apellido", "Placa"}
RENOMBRE = {"Nro Comparendo": "nro", "Fecha Comparendo": "fecha", "Secretaría": "secretaria",
            "Infracciones Comparendo": "codigo", "Valor": "valor", "Polca": "polca",
            "Nro Resolución": "nro_resolucion", "Estado Resolución": "estado_resolucion",
            "Foto Detección": "foto", "Fecha Notificacion": "fecha_notificacion",
            "Fuente Comparendo": "fuente", "Latitud": "lat", "Longitud": "lon",
            "Dirección Infracción": "direccion", "Inmovilización (S/N)": "inmovilizacion",
            "Descripción Tipo vehículo": "tipo_vehiculo"}

_TR = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
_TD = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
# «CALLE 21 - CARRERA 15 (OESTE - ESTE)», «DIAGONAL 21 - CARRERA 18E (NORTE-SUR)»
PATRON_SAST = re.compile(
    r"^\s*(CALLE|CARRERA|DIAGONAL|TRANSVERSAL)\s+\w+(\s+\w+)?\s+-\s+"
    r"(CALLE|CARRERA|DIAGONAL|TRANSVERSAL)\s+\w+(\s+\w+)?\s*"
    r"\(\s*(NORTE|SUR|ESTE|OESTE)\s*-\s*(NORTE|SUR|ESTE|OESTE)\s*\)\s*$")


def _celda(c: str) -> str:
    return " ".join(html.unescape(_TAG.sub(" ", c)).split())


def _leer_html(texto: str, nombre: str) -> tuple[pd.DataFrame, list[dict]]:
    filas, malformadas, encabezado = [], [], None
    idx_publicas = None
    for m in _TR.finditer(texto):
        celdas = [_celda(c) for c in _TD.findall(m.group(1))]
        if encabezado is None:
            if celdas and celdas[0] == "Nro Comparendo":
                if celdas != ENCABEZADO:
                    raise ValueError(f"{nombre}: el encabezado cambió: {celdas}")
                encabezado = celdas
                idx_publicas = [i for i, c in enumerate(celdas) if c not in PERSONALES]
            continue
        if len(celdas) != len(encabezado):
            # sin datos personales: solo cuántas celdas y el número de comparendo si lo hay
            malformadas.append({"archivo": nombre, "n_celdas": len(celdas),
                                "primera_celda": celdas[0][:25] if celdas and celdas[0].startswith("'") else ""})
            continue
        filas.append([celdas[i] for i in idx_publicas])
    if encabezado is None:
        raise ValueError(f"{nombre}: no se encontró el encabezado de la tabla")
    df = pd.DataFrame(filas, columns=[encabezado[i] for i in idx_publicas])
    df.insert(0, "archivo", nombre)
    return df, malformadas


def leer_zip() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """-> (comparendos sin datos personales, filas malformadas, nombre del zip)."""
    ruta = ultimo(RAW / "comparendos", "*_sttv_comparendos-*.zip")
    partes, malas = [], []
    with zipfile.ZipFile(ruta) as z:
        for nombre in sorted(z.namelist()):
            texto = z.read(nombre).decode("latin-1")
            df, m = _leer_html(texto, nombre)
            partes.append(df)
            malas.extend(m)
    df = pd.concat(partes, ignore_index=True).rename(columns=RENOMBRE)
    return df, pd.DataFrame(malas), ruta.name


def tipificar(df: pd.DataFrame) -> pd.DataFrame:
    """Tipos y banderas; los valores originales que se interpretan se conservan."""
    d = df.copy()
    d["nro"] = d["nro"].str.lstrip("'")
    d["fecha"] = pd.to_datetime(d["fecha"], format="%d/%m/%Y", errors="coerce")
    d["fecha_notificacion"] = pd.to_datetime(d["fecha_notificacion"].replace("", None),
                                             format="%d/%m/%Y", errors="coerce")
    d["bandera_notificacion_1900"] = d["fecha_notificacion"].dt.year.eq(1900)
    for c in ("lat", "lon"):
        d[c] = pd.to_numeric(d[c].str.replace(",", ".", regex=False), errors="coerce")
    d["valor"] = pd.to_numeric(d["valor"], errors="coerce")
    d["codigo"] = d["codigo"].str.strip().str.upper()
    d["direccion"] = d["direccion"].str.strip()
    # coordenada utilizable: dentro de una caja holgada del municipio de Valledupar
    caja = d["lat"].between(9.6, 10.95) & d["lon"].between(-74.2, -72.9)
    d["coord_estado"] = np.select(
        [d["lat"].isna() | d["lon"].isna(), d["lat"].eq(0) | d["lon"].eq(0),
         d["lat"].eq(1) & d["lon"].eq(1), ~caja],
        ["sin_coordenada", "cero", "marcador_1_1", "fuera_de_valledupar"], "ok")
    d["patron_sast"] = d["direccion"].str.upper().str.match(PATRON_SAST)
    d["medio"] = np.select(
        [d["foto"].eq("S") & d["patron_sast"], d["foto"].eq("S"), d["foto"].eq("N")],
        ["sast", "fotodeteccion_previa", "agente"], "sin_dato")
    return d


def depurar_duplicados(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Una fila por (número de comparendo, código); -> (depurado, apartados).

    Un mismo número con dos códigos distintos es un comparendo con dos infracciones: se
    conservan ambas. Un mismo número y código repetido es el mismo comparendo exportado dos
    veces (típicamente una fila «Comparenderas electrónicas SIMIT» con coordenada y otra «No
    reportada» con la resolución). Se conserva la que trae coordenada utilizable (lo que este
    análisis necesita), luego la de resolución más completa. Las parejas que difieren en fecha,
    dirección o medio quedan marcadas en `dup_conflicto` para el informe.
    """
    puntaje = (d["coord_estado"].eq("ok").astype(int) * 8
               + d["nro_resolucion"].fillna("").ne("").astype(int) * 4
               + d["estado_resolucion"].fillna("").ne("").astype(int) * 2
               + d["fecha_notificacion"].notna().astype(int))
    llave = ["nro", "codigo"]
    g = d.groupby(llave)
    conflicto = (g["fecha"].transform("nunique").gt(1) | g["direccion"].transform("nunique").gt(1)
                 | g["medio"].transform("nunique").gt(1))
    orden = (d.assign(_p=puntaje, dup_conflicto=conflicto & d.duplicated(llave, keep=False))
             .sort_values(llave + ["_p", "fecha"], ascending=[True, True, False, True]))
    dup = orden.duplicated(llave, keep="first")
    return orden[~dup].drop(columns="_p"), orden[dup].drop(columns="_p")
