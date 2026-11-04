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
import re
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


def victimas_txt(f: int, l: int) -> str:
    fa, le = n_txt(f, "fallecido", "fallecidos"), n_txt(l, "lesionado", "lesionados")
    if f and l:
        return f"con {fa} y {le}"
    if f:
        return f"con {fa} y sin lesionados"
    return f"sin fallecidos y con {le}" if l else "sin fallecidos ni lesionados"


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


def _tabla_word(doc, t: pd.DataFrame, etiqueta: str, filas_etiqueta: list[str], total: bool,
                rotulo_inicio: str = "Inicio de operación") -> None:
    cab1 = [etiqueta, rotulo_inicio, "Antes (5 años previos)", "", "",
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


def _num(n: int) -> str:
    """Número en letras y cifras para los conteos pequeños del texto («nueve (9)»)."""
    letras = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez"]
    return f"{letras[n]} ({n})" if 0 <= n <= 10 else str(n)


def _titulo(doc, texto: str) -> None:
    _parrafo(doc, texto, negrita=True, tam=11, alinear=WD_ALIGN_PARAGRAPH.LEFT)


def _rotulo(doc, texto: str) -> None:
    _parrafo(doc, texto, negrita=True, tam=10, alinear=WD_ALIGN_PARAGRAPH.LEFT)


def _tabla_simple(doc, cabecera: list[str], filas: list[list], anchos: list) -> object:
    w = doc.add_table(rows=1, cols=len(cabecera))
    w.style = "Table Grid"
    w.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, c in enumerate(cabecera):
        _celda(w.rows[0].cells[i], c, negrita=True)
        _sombrear(w.rows[0].cells[i], "D9E2F3")
    for f in filas:
        cells = w.add_row().cells
        for i, v in enumerate(f):
            _celda(cells[i], v, centrado=i > 0)
    for fila in w.rows:
        for c, a in zip(fila.cells, anchos):
            c.width = a
    return w


def _fusionar_verticales(w, columnas: list[int], grupos: list[int]) -> None:
    """Fusiona en vertical las celdas de `columnas` para cada grupo de filas (tamaños en `grupos`)."""
    fila = 1
    for n in grupos:
        if n > 1:
            for c in columnas:
                texto = w.cell(fila, c).text
                w.cell(fila, c).merge(w.cell(fila + n - 1, c))
                _celda(w.cell(fila, c), texto, centrado=c > 0)
        fila += n


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

    n_p, n_e = len(puntos), len(equipos)
    ini_min, ini_max = equipos["inicio"].min(), equipos["inicio"].max()
    tot_a = tp[["antes_siniestros", "antes_fallecidos", "antes_lesionados"]].sum().astype(int)
    tot_d = tp[["despues_siniestros", "despues_fallecidos", "despues_lesionados"]].sum().astype(int)
    sv = ("siniestro vial con víctimas", "siniestros viales con víctimas")

    _parrafo(doc, "INSUMO TÉCNICO PARA LA RESPUESTA AL DERECHO DE PETICIÓN — NUMERAL 12",
             negrita=True, tam=12, alinear=WD_ALIGN_PARAGRAPH.CENTER)
    _parrafo(doc, "Secretaría de Tránsito y Transporte de Valledupar", tam=10,
             alinear=WD_ALIGN_PARAGRAPH.CENTER)
    _parrafo(doc, f"Fecha de corte de la información: {fecha_larga(descarga)}", tam=10,
             alinear=WD_ALIGN_PARAGRAPH.CENTER)

    # 1. Pregunta
    _titulo(doc, "1. Solicitud")
    _parrafo(doc, f"«{PREGUNTA}».", cursiva=True)

    # 2. Contexto
    _titulo(doc, "2. Equipos SAST en operación en Valledupar")
    _parrafo(doc, (
        f"A la fecha de corte, el municipio de Valledupar cuenta con {_num(n_e)} equipos de sistemas "
        "automáticos, semiautomáticos y otros medios tecnológicos (SAST) para la detección de infracciones "
        f"de tránsito, todos en operación, instalados en {_num(n_p)} puntos de la red vial urbana. Cada punto "
        "corresponde a una solicitud autorizada por la Agencia Nacional de Seguridad Vial (ANSV) y agrupa uno "
        "o dos equipos, que controlan sentidos de circulación distintos en una misma intersección o en "
        "intersecciones contiguas."))
    _parrafo(doc, (
        "Los equipos no iniciaron operación en la misma fecha. La entrada en operación fue escalonada entre "
        f"el {fecha_larga(ini_min)} y el {fecha_larga(ini_max)}, según las fechas de inicio de operación "
        "registradas para cada equipo en la plataforma de fotodetección de la ANSV. La Tabla 1 relaciona "
        "cada equipo con su punto, su código único en la plataforma, la ubicación y el sentido que controla, "
        "y su fecha de inicio de operación."))
    _rotulo(doc, "Tabla 1. Equipos SAST en operación, fecha de inicio por equipo y fecha de inicio "
                 "considerada para el punto")
    filas, grupos = [], []
    for p in puntos.itertuples():
        eqs = equipos[equipos["punto"] == p.punto]
        grupos.append(len(eqs))
        for e in eqs.itertuples():
            filas.append([p.punto.title(), e.equipo, e.codigo_unico, e.direccion_ansv.title(),
                          fecha_corta(e.inicio), fecha_corta(p.inicio)])
    w = _tabla_simple(doc, ["Punto", "Equipo", "Código único ANSV", "Ubicación y sentido controlado",
                            "Inicio de operación del equipo", "Inicio de operación considerado para el punto"],
                      filas, [Cm(4.0), Cm(2.6), Cm(3.4), Cm(8.0), Cm(2.9), Cm(3.2)])
    _fusionar_verticales(w, [0, 5], grupos)
    distintos = [p for p in puntos.itertuples()
                 if equipos.loc[equipos["punto"] == p.punto, "inicio"].nunique() > 1]
    texto = ("Para responder por punto se adopta una única fecha de inicio de operación en cada uno: la del "
             "equipo que entró primero en operación, de modo que el periodo posterior incluya todo el tiempo "
             "en que el punto ha contado con control SAST.")
    for p in distintos:
        eqs = equipos[equipos["punto"] == p.punto].sort_values("inicio")
        detalle = " y ".join(f"el {e.equipo} el {fecha_corta(e.inicio)}" for e in eqs.itertuples())
        texto += (f" En {p.punto.title()} las fechas difieren ({detalle}); se toma el "
                  f"{fecha_corta(p.inicio)}.")
    iguales = [p.punto.title() for p in puntos.itertuples() if p not in distintos
               and (equipos["punto"] == p.punto).sum() > 1]
    if iguales:
        texto += (f" En {', '.join(iguales[:-1])} y {iguales[-1]} los dos equipos iniciaron el mismo día."
                  if len(iguales) > 1 else f" En {iguales[0]} los dos equipos iniciaron el mismo día.")
    _parrafo(doc, texto)

    # 3. Método
    _titulo(doc, "3. Fuente y método")
    _parrafo(doc, (
        "Fuente. Las cifras corresponden a los casos de siniestralidad vial registrados en la zona de "
        "influencia de cada equipo, según el registro de siniestros viales conocidos por la Secretaría de "
        "Tránsito y Transporte de Valledupar (capa «Siniestralidad Valledupar», que consolida informes de la "
        "Policía de Tránsito, reportes de la Secretaría y casos de deceso posterior), con corte al "
        f"{fecha_larga(descarga)}."))
    _parrafo(doc, (
        "Delimitación espacial. Se entiende por «punto donde opera el SAST» la zona de influencia definida "
        "por la Secretaría para cada equipo, ampliada en 15 metros. La ampliación se calculó en metros, en el "
        "sistema de referencia MAGNA-SIRGAS Origen Nacional (EPSG:9377), y es la misma delimitación "
        "utilizada en el reporte de la línea base de los equipos a la ANSV. La zona de un punto es la unión de "
        "las zonas de sus equipos. Un siniestro se asigna a un punto cuando su ubicación georreferenciada en "
        "el registro cae dentro de esa zona."))
    _parrafo(doc, (
        "Variables. Se cuentan: (i) los siniestros viales con víctimas, es decir, los registrados con "
        "gravedad «con heridos» o «con muertos»; (ii) los fallecidos, y (iii) los lesionados. Fallecidos y "
        "lesionados corresponden al número de personas registradas en cada siniestro, no al número de "
        "siniestros. En los puntos con dos equipos cada siniestro se cuenta una sola vez, aunque su "
        "ubicación quede dentro de la zona de ambos equipos."))
    _parrafo(doc, (
        "Periodos. El periodo anterior a la instalación comprende los cinco (5) años previos a la fecha de "
        "inicio de operación considerada para cada punto. El periodo posterior va desde esa fecha hasta la "
        "fecha de corte, inclusive. Como la entrada en operación fue escalonada, la duración del periodo "
        "posterior varía entre puntos (Tabla 2)."))
    _rotulo(doc, "Tabla 2. Periodos de análisis por punto")
    filas = []
    for p in tp.itertuples():
        d_a = (p.inicio - p.antes_desde).days
        d_d = (p.despues_hasta - p.inicio).days + 1
        filas.append([p.punto.title(), fecha_corta(p.inicio),
                      f"{fecha_corta(p.antes_desde)} a {fecha_corta(p.antes_hasta)}", f"{d_a:,}".replace(",", "."),
                      f"{fecha_corta(p.inicio)} a {fecha_corta(p.despues_hasta)}", str(d_d)])
    _tabla_simple(doc, ["Punto", "Inicio de operación considerado", "Periodo anterior", "Días",
                        "Periodo posterior", "Días"],
                  filas, [Cm(5.0), Cm(3.2), Cm(5.2), Cm(1.8), Cm(5.2), Cm(1.8)])

    # 4. Resultados
    _titulo(doc, "4. Resultados")
    _rotulo(doc, "Tabla 3. Siniestros viales con víctimas, fallecidos y lesionados por punto SAST, antes y "
                 "después del inicio de operación")
    etq_p = [f"{r.punto.title()} (equipo{'s' if ',' in r.equipos else ''} {r.equipos.replace(', ', ' y ')})"
             for r in puntos.itertuples()]
    _tabla_word(doc, tp, "Punto SAST", etq_p, total=True, rotulo_inicio="Inicio de operación considerado")
    _parrafo(doc, (
        f"En los cinco años previos a la entrada en operación, en las zonas de influencia de los {_num(n_p)} "
        f"puntos se registraron {n_txt(tot_a.iloc[0], *sv)}, con {n_txt(tot_a.iloc[1], 'fallecido', 'fallecidos')} "
        f"y {n_txt(tot_a.iloc[2], 'lesionado', 'lesionados')}. Desde la entrada en operación y hasta el "
        f"{fecha_larga(descarga)} se registró {n_txt(tot_d.iloc[0], *sv)}, "
        f"{victimas_txt(tot_d.iloc[1], tot_d.iloc[2])}. "
        "Por punto:"))
    for p, r in zip(puntos.itertuples(), tp.itertuples()):
        a = (f"{n_txt(r.antes_siniestros, *sv)}, {victimas_txt(r.antes_fallecidos, r.antes_lesionados)}"
             if r.antes_siniestros else "ningún siniestro vial con víctimas")
        d = (f"{n_txt(r.despues_siniestros, *sv)}, {victimas_txt(r.despues_fallecidos, r.despues_lesionados)}"
             if r.despues_siniestros else "ningún siniestro vial con víctimas")
        par = doc.add_paragraph(style="List Bullet")
        run = par.add_run(f"{p.punto.title()}: ")
        run.bold = True
        par.add_run(f"antes de la instalación ({fecha_corta(r.antes_desde)} a {fecha_corta(r.antes_hasta)}), {a}; "
                    f"después ({fecha_corta(r.inicio)} a {fecha_corta(r.despues_hasta)}), {d}.")
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Anexo
    doc.add_page_break()
    _titulo(doc, "Anexo. Desglose por equipo SAST")
    _parrafo(doc, (
        "En este anexo cada equipo se presenta con su propia fecha de inicio de operación y su propia zona de "
        "influencia. Las zonas de los equipos de un mismo punto se superponen, de modo que un siniestro puede "
        "aparecer en los dos equipos; por esa razón la suma de esta tabla no coincide con los totales por "
        "punto de la Tabla 3, que cuentan cada siniestro una sola vez."), tam=10)
    _rotulo(doc, "Tabla A1. Siniestros viales con víctimas, fallecidos y lesionados por equipo SAST")
    etq_e = [f"{r.equipo} — {r.direccion_ansv.title()} ({r.punto.title()})" for r in equipos.itertuples()]
    _tabla_word(doc, te, "Equipo SAST", etq_e, total=False, rotulo_inicio="Inicio de operación del equipo")
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
               .assign(inicio=lambda d: d["equipo"].map(lambda e: pd.Timestamp(cfg[e]["fecha_inicio"])),
                       codigo_unico=lambda d: d["equipo"].map(lambda e: cfg[e]["codigo_unico"]),
                       direccion_ansv=lambda d: d["equipo"].map(
                           lambda e: re.sub(r"\((?!SENTIDO)", "(SENTIDO ", cfg[e]["direccion_ansv"])))
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
