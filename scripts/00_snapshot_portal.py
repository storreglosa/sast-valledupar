"""Snapshot de solo lectura de Siniestros y Victimas del portal ANSV.

Item «Siniestralidad Valledupar» (7ec1893e94144a33807dc967455955b2): capa 0 = Siniestros,
tabla 1 = Victimas. No escribe nada en el portal.

- Paginación por lotes de OBJECTID (250), no por resultOffset: en este servidor la
  paginación por offset repite y omite registros. Se aborta si el total no cuadra.
- Geometría con out_sr=4326 (el servicio guarda en Web Mercator).
- Fechas: misma regla que ArcgisManage/core/extract.py (UTC a Bogotá salvo medianoche UTC
  exacta, que es solo fecha).
- Datos personales fuera: de Victimas solo se guardan el codrot, la gravedad y la condición.

Salida: data/raw/portal/AAAA-MM-DD_portal_{siniestros,victimas}.parquet + procedencia JSON.
"""

import json
import os
from datetime import date, datetime

import pandas as pd
from arcgis.gis import GIS
from dotenv import load_dotenv

import _entorno  # noqa: F401
from sast.rutas import RAIZ, RAW

ITEM = "7ec1893e94144a33807dc967455955b2"
LOTE = 250
CAMPOS_SINIESTROS = ["codrot", "ipat", "fechahecho", "horahecho", "gravedad",
                     "cantidad_muertos", "cantidad_heridos", "direccion", "claseacc",
                     "area", "fuente"]
CAMPOS_VICTIMAS = ["codrot", "gravedad", "condicion"]


def _fechas_ms_a_local(serie: pd.Series) -> pd.Series:
    utc = pd.to_datetime(serie, unit="ms", utc=True, errors="coerce")
    solo_fecha = (utc.dt.time == pd.Timestamp("00:00:00").time()) | utc.isna()
    local = utc.dt.tz_convert("America/Bogota").dt.tz_localize(None)
    return local.where(~solo_fecha, utc.dt.tz_localize(None))


def descargar(capa, campos: list[str], geometria: bool) -> tuple[pd.DataFrame, int]:
    props = capa.properties
    oid = props.objectIdField
    existentes = {f.name for f in props.fields}
    faltan = [c for c in campos if c not in existentes]
    if faltan:
        raise SystemExit(f"{props.name}: el esquema ya no trae {faltan}. Revisar antes de seguir.")
    ids = capa.query(where="1=1", return_ids_only=True)
    ids = sorted(set((ids.get("objectIds") if isinstance(ids, dict) else ids) or []))
    filas = []
    for i in range(0, len(ids), LOTE):
        fs = capa.query(object_ids=",".join(map(str, ids[i:i + LOTE])),
                        out_fields=",".join([oid] + campos),
                        return_geometry=geometria, out_sr=4326)
        for f in fs.features:
            a = dict(f.attributes)
            if geometria:
                g = f.geometry or {}
                a["lon"], a["lat"] = g.get("x"), g.get("y")
            filas.append(a)
    df = pd.DataFrame(filas)
    if len(df) != len(ids) or df[oid].nunique() != len(ids):
        raise SystemExit(f"{props.name}: se esperaban {len(ids)} registros y llegaron "
                         f"{len(df)} ({df[oid].nunique()} únicos). Se aborta.")
    for f in props.fields:
        if f.type == "esriFieldTypeDate" and f.name in df.columns:
            df[f.name] = _fechas_ms_a_local(df[f.name])
    return df, len(ids)


def main() -> None:
    load_dotenv(RAIZ / ".env")
    if not os.getenv("PORTAL_URL"):
        raise SystemExit("Falta .env con PORTAL_URL/PORTAL_USERNAME/PORTAL_PASSWORD (docs/ingesta.md).")
    gis = GIS(os.environ["PORTAL_URL"], os.environ["PORTAL_USERNAME"],
              os.environ["PORTAL_PASSWORD"], verify_cert=True)
    item = gis.content.get(ITEM)
    siniestros, n_s = descargar(item.layers[0], CAMPOS_SINIESTROS, geometria=True)
    victimas, n_v = descargar(item.tables[1], CAMPOS_VICTIMAS, geometria=False)

    corte = date.today().isoformat()
    destino = RAW / "portal"
    destino.mkdir(parents=True, exist_ok=True)
    for nombre, df in (("siniestros", siniestros), ("victimas", victimas)):
        ruta = destino / f"{corte}_portal_{nombre}.parquet"
        if ruta.exists():
            raise SystemExit(f"{ruta.name} ya existe: un corte no se reescribe.")
        df.to_parquet(ruta, index=False)
    procedencia = {
        "portal": os.environ["PORTAL_URL"], "item": ITEM, "titulo": item.title,
        "capas": {"siniestros": item.layers[0].url, "victimas": item.tables[1].url},
        "registros": {"siniestros": n_s, "victimas": n_v},
        "descargado": datetime.now().isoformat(timespec="seconds"),
        "campos": {"siniestros": CAMPOS_SINIESTROS, "victimas": CAMPOS_VICTIMAS},
    }
    (destino / f"{corte}_portal_procedencia.json").write_text(
        json.dumps(procedencia, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Corte {corte}: {n_s} siniestros, {n_v} víctimas.")


if __name__ == "__main__":
    main()
