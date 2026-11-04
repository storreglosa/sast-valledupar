"""Etapa 11 — Derecho de petición, numeral 12: siniestros, lesionados y fallecidos en los puntos
SAST antes y después del inicio de operación.

Pregunta: «Informar el número de siniestros viales, lesionados y fallecidos registrados en los
puntos donde operan los sistemas SAST antes y después de su instalación».

Criterios acordados con Santiago (2026-11-04):
- Unidad: los 5 puntos (solicitudes), sin doble conteo; desglose por equipo en el anexo.
  La fecha de inicio del punto es la del equipo que inició primero.
- Criterio espacial: zona de influencia + 15 m (capa `zonas_buffer`, calculada en EPSG:9377),
  el mismo de la cifra oficial reportada a la ANSV (decisión 25).
- Antes: los 5 años previos a la fecha de inicio [inicio − 5 años, inicio).
- Después: desde la fecha de inicio hasta la fecha de descarga del corte del portal (inclusive).
  Los registros con fecha posterior a la descarga se excluyen y se reportan.
- Siniestros = siniestros con víctimas (gravedad «Con Heridos» o «Con Muertos»; Santiago, 2026-11-04:
  la respuesta muestra siniestros con lesionados y fallecidos, no los «Solo Daños», cuyo registro
  en el portal prácticamente desaparece desde 2022). Fallecidos y lesionados = personas
  (`cantidad_muertos`, `cantidad_heridos`; decisión 6), con las correcciones manuales de
  `docs/correcciones_siniestros.csv` (decisión 22).
- La respuesta se limita a las cifras y su fuente (Santiago): no interpreta el efecto.

Como control se recalcula con el corte anterior del portal y se reportan las diferencias.

Uso:  python scripts/11_derecho_peticion.py [--corte AAAA-MM-DD]   (por defecto, el último)
Salida: outputs/<corte>_sttv_derecho-peticion-num12_siniestros-sast.{docx,xlsx}
        outputs/tables/derecho_peticion_siniestros_en_zona.csv (registro a registro; no versionado)
"""

import argparse
import hashlib
import json
from datetime import date, datetime

import geopandas as gpd
import pandas as pd
import yaml
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

import _entorno  # noqa: F401
from sast.rutas import CONFIG, CRS_GEO, DOCS, OUTPUTS, PROCESSED, RAW

ANIOS_ANTES = 5
PREGUNTA = ("12. Informar el número de siniestros viales, lesionados y fallecidos registrados en los "
            "puntos donde operan los sistemas SAST antes y después de su instalación")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_larga(f) -> str:
    f = pd.Timestamp(f)
    return f"{f.day} de {MESES[f.month - 1]} de {f.year}"


def n_txt(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def fecha_corta(f) -> str:
    return pd.Timestamp(f).strftime("%d/%m/%Y")


def cargar_siniestros(corte: str) -> tuple[gpd.GeoDataFrame, dict]:
    """Siniestros del corte con correcciones manuales y coordenada utilizable, en EPSG:4326."""
    s = pd.read_parquet(RAW / "portal" / f"{corte}_portal_siniestros.parquet")
    proc = json.loads((RAW / "portal" / f"{corte}_portal_procedencia.json").read_text(encoding="utf-8"))
    s["fecha"] = pd.to_datetime(s["fechahecho"]).dt.normalize()
    corr = pd.read_csv(DOCS / "correcciones_siniestros.csv", encoding="utf-8")
    faltan = sorted(set(corr["codrot"]) - set(s["codrot"]))
    if faltan:
        raise SystemExit(f"Correcciones para codrot que no están en el corte {corte}: {faltan}")
    for r in corr.itertuples():
        m = s["codrot"] == r.codrot
        if r.accion == "excluir":
            s = s[~m]
        elif r.accion == "ajustar":
            s.loc[m, ["gravedad", "cantidad_muertos", "cantidad_heridos"]] = [
                r.gravedad, int(r.cantidad_muertos), int(r.cantidad_heridos)]
        else:
            raise SystemExit(f"Acción desconocida en correcciones: {r.accion}")
    s = s.reset_index(drop=True)
    for c in ("cantidad_muertos", "cantidad_heridos"):
        nul = s[c].isna()
        if nul.any():
            print(f"  [{corte}] AVISO: {nul.sum()} siniestros sin {c} (cuentan como 0)")
        s[c] = s[c].fillna(0).astype(int)
    caja = s["lat"].between(9.6, 10.95) & s["lon"].between(-74.2, -72.9)
    sin = ~(s["lat"].notna() & caja)
    if sin.any():
        print(f"  [{corte}] AVISO: {sin.sum()} siniestros sin coordenada utilizable, no se pueden "
              f"asignar a zona: {s.loc[sin, 'codrot'].tolist()}")
    s = s[~sin]
    g = gpd.GeoDataFrame(s, geometry=gpd.points_from_xy(s["lon"], s["lat"]), crs=CRS_GEO)
    return g, proc


def en_zonas(g: gpd.GeoDataFrame, zonas: gpd.GeoDataFrame) -> pd.DataFrame:
    """Un registro por (siniestro, equipo) cuyo punto cae dentro de la zona + 15 m."""
    j = gpd.sjoin(g, zonas[["equipo", "solicitud", "punto", "geometry"]], predicate="within")
    return pd.DataFrame(j.drop(columns=["geometry", "index_right"]))


def con_victimas(j: pd.DataFrame, corte: str) -> pd.DataFrame:
    """Deja los siniestros con víctimas y reporta los «Solo Daños» apartados y las incoherencias."""
    victimas = j["gravedad"].isin(["Con Heridos", "Con Muertos"])
    otras = sorted(set(j["gravedad"].dropna()) - {"Con Heridos", "Con Muertos", "Solo Daños"})
    if otras or j["gravedad"].isna().any():
        raise SystemExit(f"[{corte}] gravedad no prevista en zona: {otras} / nulos {j['gravedad'].isna().sum()}")
    personas = j["cantidad_muertos"] + j["cantidad_heridos"]
    raros = j[(victimas & personas.eq(0)) | (~victimas & personas.gt(0))]
    if len(raros):
        print(f"  [{corte}] AVISO: gravedad incoherente con las personas en zona: "
              f"{raros[['equipo', 'codrot', 'gravedad', 'cantidad_muertos', 'cantidad_heridos']].values.tolist()}")
    apart = j.loc[~victimas].drop_duplicates("codrot")
    recientes = apart[apart["fecha"] >= pd.Timestamp("2021-06-01")]
    print(f"  [{corte}] «Solo Daños» en zona apartados: {len(apart)} (todos los años); desde jun-2021: "
          f"{recientes[['codrot', 'fecha']].astype(str).values.tolist()}")
    return j[victimas]


def periodo(fecha: pd.Series, inicio: pd.Timestamp, descarga: pd.Timestamp) -> pd.Series:
    antes = (fecha >= inicio - pd.DateOffset(years=ANIOS_ANTES)) & (fecha < inicio)
    despues = (fecha >= inicio) & (fecha <= descarga)
    return pd.Series(pd.NA, index=fecha.index, dtype="object").mask(antes, "antes").mask(despues, "despues")


def tabla(j: pd.DataFrame, unidades: pd.DataFrame, clave: str, descarga: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Conteo antes/después por unidad (equipo o punto). En punto, cada siniestro una sola vez."""
    filas, detalle = [], []
    for u in unidades.itertuples():
        sel = j[j[clave] == getattr(u, clave)].drop_duplicates("codrot").copy()
        sel["periodo"] = periodo(sel["fecha"], u.inicio, descarga)
        sel = sel[sel["periodo"].notna()]
        detalle.append(sel.assign(unidad=getattr(u, clave)))
        fila = {clave: getattr(u, clave), "inicio": u.inicio,
                "antes_desde": u.inicio - pd.DateOffset(years=ANIOS_ANTES),
                "antes_hasta": u.inicio - pd.Timedelta(days=1), "despues_hasta": descarga}
        for p in ("antes", "despues"):
            x = sel[sel["periodo"] == p]
            fila |= {f"{p}_siniestros": len(x), f"{p}_fallecidos": int(x["cantidad_muertos"].sum()),
                     f"{p}_lesionados": int(x["cantidad_heridos"].sum())}
        filas.append(fila)
    return pd.DataFrame(filas), pd.concat(detalle, ignore_index=True)


# --- Word ---------------------------------------------------------------------------------

def _sombrear(celda, color: str) -> None:
    tcPr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def _celda(celda, texto, negrita=False, centrado=True, tam=9) -> None:
    celda.text = ""
    p = celda.paragraphs[0]
    r = p.add_run(str(texto))
    r.bold = negrita
    r.font.size = Pt(tam)
    if centrado:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _tabla_word(doc, t: pd.DataFrame, etiqueta: str, filas_etiqueta: list[str], total: bool) -> None:
    cab1 = [etiqueta, "Inicio de operación", "Antes (5 años previos)", "", "",
            "Después (desde el inicio)", "", ""]
    cab2 = ["", "", "Siniestros con víctimas", "Fallecidos", "Lesionados",
            "Siniestros con víctimas", "Fallecidos", "Lesionados"]
    w = doc.add_table(rows=2, cols=8)
    w.style = "Table Grid"
    w.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (a, b) in enumerate(zip(cab1, cab2)):
        _celda(w.rows[0].cells[i], a, negrita=True)
        _celda(w.rows[1].cells[i], b, negrita=True)
    w.cell(0, 2).merge(w.cell(0, 4))
    w.cell(0, 5).merge(w.cell(0, 7))
    for c in (0, 1):
        w.cell(0, c).merge(w.cell(1, c))
    _celda(w.cell(0, 0), cab1[0], negrita=True)
    _celda(w.cell(0, 1), cab1[1], negrita=True)
    _celda(w.cell(0, 2), cab1[2], negrita=True)
    _celda(w.cell(0, 5), cab1[5], negrita=True)
    for fila in w.rows[:2]:
        for c in fila.cells:
            _sombrear(c, "D9E2F3")
    cols = ["antes_siniestros", "antes_fallecidos", "antes_lesionados",
            "despues_siniestros", "despues_fallecidos", "despues_lesionados"]
    for etq, r in zip(filas_etiqueta, t.itertuples()):
        cells = w.add_row().cells
        _celda(cells[0], etq, centrado=False)
        _celda(cells[1], fecha_corta(r.inicio))
        for i, c in enumerate(cols):
            _celda(cells[2 + i], getattr(r, c))
    if total:
        cells = w.add_row().cells
        _celda(cells[0], "Total", negrita=True, centrado=False)
        _celda(cells[1], "")
        for i, c in enumerate(cols):
            _celda(cells[2 + i], int(t[c].sum()), negrita=True)
            _sombrear(cells[2 + i], "F2F2F2")
        _sombrear(cells[0], "F2F2F2")
        _sombrear(cells[1], "F2F2F2")
    anchos = [Cm(6.2), Cm(2.2)] + [Cm(1.9)] * 6
    for fila in w.rows:
        for c, a in zip(fila.cells, anchos):
            c.width = a


def _parrafo(doc, texto, negrita=False, cursiva=False, tam=11, alinear=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p = doc.add_paragraph()
    r = p.add_run(texto)
    r.bold, r.italic, r.font.size = negrita, cursiva, Pt(tam)
    p.alignment = alinear
    return p


def escribir_word(ruta, tp, te, puntos, equipos, descarga) -> None:
    doc = Document()
    cp = doc.core_properties
    cp.author = cp.last_modified_by = "Secretaría de Tránsito y Transporte de Valledupar"
    cp.title = "Insumo técnico — derecho de petición, numeral 12"
    cp.created = cp.modified = datetime.now()
    cp.revision = 1
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = sec.page_height, sec.page_width
    for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, m, Cm(2))
    doc.styles["Normal"].font.name = "Arial"
    doc.styles["Normal"].font.size = Pt(11)

    _parrafo(doc, "INSUMO TÉCNICO PARA RESPUESTA A DERECHO DE PETICIÓN — NUMERAL 12",
             negrita=True, tam=12, alinear=WD_ALIGN_PARAGRAPH.CENTER)
    _parrafo(doc, "Secretaría de Tránsito y Transporte de Valledupar", tam=10,
             alinear=WD_ALIGN_PARAGRAPH.CENTER)
    _parrafo(doc, f"Pregunta: «{PREGUNTA}».", cursiva=True)

    _parrafo(doc, "Respuesta", negrita=True)
    n_puntos, n_equipos = len(puntos), len(equipos)
    _parrafo(doc, (
        f"En el municipio de Valledupar operan {n_equipos} equipos de sistemas automáticos, "
        f"semiautomáticos y otros medios tecnológicos (SAST), ubicados en {n_puntos} puntos. A continuación "
        "se informa el número de siniestros viales con víctimas, fallecidos y lesionados registrados en la zona de "
        "influencia de cada punto en dos periodos: antes de la instalación, durante los cinco (5) años "
        "previos a la fecha de inicio de operación, y después de la instalación, desde la fecha de inicio "
        f"de operación hasta el {fecha_larga(descarga)}."))
    _parrafo(doc, (
        "Las cifras corresponden a los casos de siniestralidad vial registrados en la zona de influencia "
        "de cada equipo, según el registro de siniestros viales conocidos por la Secretaría de Tránsito y "
        "Transporte de Valledupar (capa «Siniestralidad Valledupar», que consolida informes de la Policía "
        "de Tránsito, reportes de la Secretaría y casos de deceso posterior), con corte al "
        f"{fecha_larga(descarga)}."))

    _parrafo(doc, "Tabla 1. Siniestros viales con víctimas, fallecidos y lesionados por punto SAST, antes y después "
                  "del inicio de operación", negrita=True, tam=10, alinear=WD_ALIGN_PARAGRAPH.LEFT)
    etq_p = [f"{r.punto.title()} — {r.direcciones.title()} (equipos {r.equipos})" for r in puntos.itertuples()]
    _tabla_word(doc, tp, "Punto SAST", etq_p, total=True)
    _parrafo(doc, (
        "Se cuentan los siniestros con víctimas (con lesionados o fallecidos). Fallecidos y lesionados se "
        "cuentan como personas. En los puntos con dos equipos, la fecha de inicio "
        "es la del equipo que inició primero y cada siniestro se cuenta una sola vez."), tam=9)
    tot_a = tp[["antes_siniestros", "antes_fallecidos", "antes_lesionados"]].sum()
    tot_d = tp[["despues_siniestros", "despues_fallecidos", "despues_lesionados"]].sum()
    _parrafo(doc, (
        "En total, en los cinco años previos a la instalación se registraron "
        f"{n_txt(tot_a.iloc[0], 'siniestro vial con víctimas', 'siniestros viales con víctimas')}, con "
        f"{n_txt(tot_a.iloc[1], 'fallecido', 'fallecidos')} y {n_txt(tot_a.iloc[2], 'lesionado', 'lesionados')}, "
        f"en las zonas de influencia de los {n_puntos} puntos. Desde el inicio de operación y hasta el "
        f"{fecha_larga(descarga)} se registró un total de "
        f"{n_txt(tot_d.iloc[0], 'siniestro vial con víctimas', 'siniestros viales con víctimas')}, con "
        f"{n_txt(tot_d.iloc[1], 'fallecido', 'fallecidos')} y {n_txt(tot_d.iloc[2], 'lesionado', 'lesionados')}."))

    _parrafo(doc, "Tabla 2. Periodos considerados por punto", negrita=True, tam=10,
             alinear=WD_ALIGN_PARAGRAPH.LEFT)
    w = doc.add_table(rows=1, cols=3)
    w.style = "Table Grid"
    w.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, c in enumerate(["Punto SAST", "Antes de la instalación", "Después de la instalación"]):
        _celda(w.rows[0].cells[i], c, negrita=True)
        _sombrear(w.rows[0].cells[i], "D9E2F3")
    for p, r in zip(puntos.itertuples(), tp.itertuples()):
        cells = w.add_row().cells
        _celda(cells[0], p.punto.title(), centrado=False)
        _celda(cells[1], f"{fecha_corta(r.antes_desde)} a {fecha_corta(r.antes_hasta)}")
        _celda(cells[2], f"{fecha_corta(r.inicio)} a {fecha_corta(r.despues_hasta)}")

    doc.add_page_break()
    _parrafo(doc, "Anexo. Desglose por equipo SAST", negrita=True)
    _parrafo(doc, (
        "Cada equipo se presenta con su propia fecha de inicio de operación. En los puntos con dos equipos "
        "las zonas de influencia se superponen, por lo que un mismo siniestro puede aparecer en ambos "
        "equipos; por esa razón la suma de esta tabla no coincide con el total de la Tabla 1."), tam=10)
    etq_e = [f"{r.equipo} — {r.direccion.title()} ({r.punto.title()})" for r in equipos.itertuples()]
    _tabla_word(doc, te, "Equipo SAST", etq_e, total=False)

    _parrafo(doc, "Nota sobre la fuente", negrita=True, tam=10, alinear=WD_ALIGN_PARAGRAPH.LEFT)
    _parrafo(doc, (
        "Zona de influencia: polígono definido para cada equipo SAST, ampliado 15 metros (la misma "
        "delimitación usada en el reporte de la línea base a la Agencia Nacional de Seguridad Vial). "
        "Se cuenta un siniestro cuando su ubicación registrada cae dentro de la zona. Fechas de inicio "
        "de operación: plataforma de fotodetección de la ANSV. Registro de siniestros consultado el "
        f"{fecha_larga(descarga)}."), tam=9)
    doc.save(ruta)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corte", help="fecha AAAA-MM-DD del corte en data/raw/portal/ (por defecto, el último)")
    args = ap.parse_args()
    cortes = sorted(p.name[:10] for p in (RAW / "portal").glob("*_portal_siniestros.parquet"))
    corte = args.corte or cortes[-1]
    anterior = max((c for c in cortes if c < corte), default=None)

    cfg = yaml.safe_load((CONFIG / "equipos.yaml").read_text(encoding="utf-8"))["equipos"]
    zonas = gpd.read_file(PROCESSED / "equipos_sast.gpkg", layer="zonas_buffer").to_crs(CRS_GEO)
    eq = gpd.read_file(PROCESSED / "equipos_sast.gpkg", layer="equipos")
    if set(zonas["equipo"]) != set(cfg):
        raise SystemExit(f"Equipos de zonas {sorted(zonas['equipo'])} ≠ config {sorted(cfg)}")
    equipos = (pd.DataFrame(eq.drop(columns="geometry"))[["equipo", "solicitud", "punto", "direccion"]]
               .assign(inicio=lambda d: d["equipo"].map(lambda e: pd.Timestamp(cfg[e]["fecha_inicio"])))
               .sort_values(["solicitud", "equipo"]).reset_index(drop=True))
    puntos = (equipos.groupby(["solicitud", "punto"], as_index=False)
              .agg(inicio=("inicio", "min"), equipos=("equipo", lambda s: ", ".join(e[-3:] for e in s)),
                   direcciones=("direccion", lambda s: " / ".join(dict.fromkeys(s))))
              .sort_values("solicitud").reset_index(drop=True))

    g, proc = cargar_siniestros(corte)
    descarga = pd.Timestamp(proc["descargado"]).normalize()
    futuras = g[g["fecha"] > descarga]
    if len(futuras):
        print(f"AVISO: {len(futuras)} siniestros con fecha posterior a la descarga ({descarga:%d/%m/%Y}); "
              f"se excluyen: {futuras[['codrot', 'fecha']].astype(str).values.tolist()}")
    j = con_victimas(en_zonas(g, zonas), corte)
    j_fut = j[j["fecha"] > descarga]
    if len(j_fut):
        print(f"  ... de ellos en zona SAST: {j_fut[['equipo', 'codrot', 'fecha']].astype(str).values.tolist()}")
    ultima = g.loc[g["fecha"] <= descarga, "fecha"].max()
    print(f"Corte {corte}: descarga {descarga:%d/%m/%Y}; último siniestro con fecha válida {ultima:%d/%m/%Y}")

    tp, det_p = tabla(j, puntos, "punto", descarga)
    te, det_e = tabla(j, equipos, "equipo", descarga)
    print("\nPor punto:\n" + tp.drop(columns=["antes_desde", "antes_hasta", "despues_hasta"]).to_string(index=False))
    print("\nPor equipo:\n" + te.drop(columns=["antes_desde", "antes_hasta", "despues_hasta"]).to_string(index=False))

    # control: lo mismo con el corte anterior
    if anterior:
        ga, proc_a = cargar_siniestros(anterior)
        desc_a = pd.Timestamp(proc_a["descargado"]).normalize()
        ta, det_a = tabla(con_victimas(en_zonas(ga, zonas), anterior), puntos, "punto", desc_a)
        a = ta.set_index("punto").filter(like="antes_").drop(columns=["antes_desde", "antes_hasta"])
        b = tp.set_index("punto")[a.columns]
        dif = (b - a)[(b - a).ne(0).any(axis=1)]
        print(f"\nControl contra el corte {anterior} (periodo «antes»): "
              + ("sin diferencias." if dif.empty else f"diferencias (nuevo − anterior):\n{dif.to_string()}"))
        cods_n = set(det_p.loc[det_p["periodo"] == "antes", "codrot"])
        cods_a = set(det_a.loc[det_a["periodo"] == "antes", "codrot"])
        if cods_n ^ cods_a:
            print(f"  entran: {sorted(cods_n - cods_a)}  salen: {sorted(cods_a - cods_n)}")

    # salidas
    base = f"{corte}_sttv_derecho-peticion-num12_siniestros-sast"
    escribir_word(OUTPUTS / f"{base}.docx", tp, te, puntos, equipos, descarga)
    sha = hashlib.sha256((RAW / "portal" / f"{corte}_portal_siniestros.parquet").read_bytes()).hexdigest()
    with pd.ExcelWriter(OUTPUTS / f"{base}.xlsx") as xw:
        for nombre, t in (("por_punto", tp), ("por_equipo", te)):
            t2 = t.copy()
            for c in ("inicio", "antes_desde", "antes_hasta", "despues_hasta"):
                t2[c] = t2[c].dt.date
            t2.to_excel(xw, sheet_name=nombre, index=False)
        pd.DataFrame({"campo": ["pregunta", "portal", "item", "capa", "corte_portal", "descarga",
                                "sha256_snapshot", "ultimo_siniestro_con_fecha_valida", "siniestros",
                                "criterio_espacial", "antes", "despues", "correcciones",
                                "excluidos", "script", "generado"],
                      "valor": [PREGUNTA, proc["portal"], proc["item"], proc["capas"]["siniestros"], corte,
                                proc["descargado"], sha, ultima.date().isoformat(),
                                "con víctimas (Con Heridos / Con Muertos); fallecidos y lesionados = personas",
                                "zona de influencia + 15 m (EPSG:9377)",
                                f"{ANIOS_ANTES} años previos a la fecha de inicio",
                                "desde la fecha de inicio hasta la descarga (inclusive)",
                                "docs/correcciones_siniestros.csv",
                                f"fecha posterior a la descarga: {futuras['codrot'].tolist()}; "
                                f"sin coordenada utilizable: ver salida del script",
                                "scripts/11_derecho_peticion.py", date.today().isoformat()]}
                     ).to_excel(xw, sheet_name="procedencia", index=False)
    cols = ["unidad", "periodo", "codrot", "fecha", "gravedad", "cantidad_muertos", "cantidad_heridos",
            "direccion", "fuente", "lon", "lat"]
    pd.concat([det_p.assign(nivel="punto"), det_e.assign(nivel="equipo")])[["nivel"] + cols] \
        .sort_values(["nivel", "unidad", "fecha"]) \
        .to_csv(OUTPUTS / "tables" / "derecho_peticion_siniestros_en_zona.csv", index=False, encoding="utf-8-sig")
    print(f"\n-> outputs/{base}.docx / .xlsx")


if __name__ == "__main__":
    main()
