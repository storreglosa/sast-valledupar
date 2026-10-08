"""Páginas del reporte: resumen del equipo (p. 1) y una página por plan (diagrama de barras).

Tiempos de cada grupo, en segundos desde el inicio del ciclo (columna derecha del diagrama):
  TIRA  inicio del rojo-amarillo (solo vehiculares; en campo se ve rojo, decisión 29)
  TIV   inicio del verde
  TFV   fin del verde (inicio del amarillo, o del rojo intermitente peatonal)
  TFA   fin del amarillo (inicio del rojo)
Los valores dan la vuelta al ciclo (TIV 60, TFV 11 = verde de 60 a 11 pasando por 0).

Duración del ciclo: el diagrama mide siempre 600 pt de ancho desde x = 120, así que la
distancia entre las marcas «0» y «10» del eje superior da la escala: C = 6000 / (x10 − x0).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sast.semaforos.pdf import Palabra, misma_linea, palabras

ANCHO_DIAGRAMA_PT = 600.0
COLUMNAS = ("TIRA", "TIV", "TFV", "TFA")


@dataclass
class Grupo:
    id: str            # «G1»
    nombre: str        # «Flujo 2», «Peatonal 22», «Flecha»
    tipo: str          # vehicular | flecha | peatonal


@dataclass
class Plan:
    id: str                                   # «P2»
    ciclo: int
    tiempos: dict[str, dict[str, int | None]]  # G1 -> {tira, tiv, tfv, tfa}
    pagina: int
    ciclo_crudo: float = 0.0


def tipo_grupo(nombre: str) -> str:
    n = nombre.lower()
    if n.startswith("flujo"):
        return "vehicular"
    if n.startswith("flecha"):
        return "flecha"
    if n.startswith("peat"):
        return "peatonal"
    raise ValueError(f"Tipo de grupo desconocido: «{nombre}»")


def _tras(ps: list[Palabra], etiqueta: str) -> str:
    """Texto que sigue a «ETIQUETA:» en la misma palabra o línea («CÓDIGO:4254»)."""
    for p in ps:
        if p.texto.startswith(etiqueta + ":"):
            linea = misma_linea(ps, p.y0)
            resto = " ".join(q.texto for q in linea if q.x0 >= p.x0)
            return resto[len(etiqueta) + 1:].strip()
    raise ValueError(f"No se encontró «{etiqueta}:»")


def _numero_tras(ps: list[Palabra], etiqueta: str) -> int:
    return int(re.search(r"\d+", _tras(ps, etiqueta)).group())


def leer_resumen(pdf: Path, pagina: int = 1) -> dict:
    ps = palabras(pdf, pagina)
    # La tabla «INFORMACIÓN DE CRUCES»: la fila de valores va debajo de la fila de títulos.
    titulo = next(p for p in ps if p.texto == "CODIGO")
    valores = [p for p in ps if abs(p.x0 - titulo.x0) < 1 and p.y0 > titulo.y0 + 2]
    return {
        "equipo": _tras(ps, "CÓDIGO"),
        "direccion": _tras(ps, "DIRECCIÓN"),
        "cruce": min(valores, key=lambda p: p.y0).texto,
        "n_grupos": _numero_tras(ps, "GRUPOS"),
        "n_planes": _numero_tras(ps, "PLANES"),
        "n_horarios": _numero_tras(ps, "HORARIOS"),
    }


def es_pagina_plan(ps: list[Palabra]) -> bool:
    return any(p.texto == "PLANEAMIENTO" for p in ps) and any(p.texto == "TIRA" for p in ps)


def _pie(ps: list[Palabra], primera: str) -> str:
    """Línea del pie que empieza con `primera` («CRUCE 917, UBICADO EN cra 9 con calle 17»)."""
    p = max((q for q in ps if q.texto == primera), key=lambda q: q.y0)
    return " ".join(q.texto for q in misma_linea(ps, p.y0))


def leer_plan(pdf: Path, pagina: int) -> tuple[Plan, list[Grupo], str]:
    ps = palabras(pdf, pagina)
    pie = _pie(ps, "PLANEAMIENTO")
    m = re.match(r"PLANEAMIENTO N\. (\d+) DE LA", pie)
    if not m:
        raise ValueError(f"{pdf.name} p. {pagina}: pie de plan inesperado «{pie}»")
    plan_id = f"P{m.group(1)}"
    cruce = _pie(ps, "CRUCE")

    # Escala del eje superior (primera fila de marcas: la de menor y)
    y_eje = min(p.y0 for p in ps if p.texto == "0" and abs(p.x0 - 120) < 1)
    eje = {p.texto: p.x0 for p in misma_linea(ps, y_eje, 0.5)}
    if "0" not in eje or "10" not in eje:
        raise ValueError(f"{pdf.name} p. {pagina}: no se encontró la escala del eje")
    crudo = ANCHO_DIAGRAMA_PT * 10 / (eje["10"] - eje["0"])
    ciclo = round(crudo)

    # Grupos: «GR n» y debajo el nombre
    grupos, filas = [], []
    for p in ps:
        if p.texto == "GR" and p.x0 < 100:
            n = next(q for q in misma_linea(ps, p.y0) if q.x0 > p.x0).texto
            nombre = " ".join(q.texto for q in misma_linea(ps, p.y0 + 10) if q.x0 < 110)
            grupos.append(Grupo(f"G{n}", nombre, tipo_grupo(nombre)))
            filas.append((p.y0, f"G{n}"))

    # Tabla de la derecha: cada número va a la columna cuyo título queda más cerca en x
    titulos = {p.texto: p for p in ps if p.texto in COLUMNAS}
    if set(titulos) != set(COLUMNAS):
        raise ValueError(f"{pdf.name} p. {pagina}: faltan títulos de la tabla de tiempos")
    x_min = titulos["TIRA"].x0 - 25
    y_tit = titulos["TIRA"].y0
    tiempos = {g: {c.lower(): None for c in COLUMNAS} for _, g in filas}
    for p in ps:
        if p.x0 < x_min or p.y0 <= y_tit + 5 or not p.texto.isdigit():
            continue
        y_fila, g = min(filas, key=lambda f: abs(f[0] - p.y0))
        if abs(y_fila - p.y0) > 14:
            raise ValueError(f"{pdf.name} p. {pagina}: número «{p.texto}» sin fila de grupo")
        col = min(COLUMNAS, key=lambda c: abs(titulos[c].xc - p.xc))
        if tiempos[g][col.lower()] is not None:
            raise ValueError(f"{pdf.name} p. {pagina}: {g} trae dos valores en {col}")
        tiempos[g][col.lower()] = int(p.texto)
    orden = sorted(tiempos, key=lambda g: int(g[1:]))
    plan = Plan(plan_id, ciclo, {g: tiempos[g] for g in orden}, pagina, crudo)
    return plan, sorted(grupos, key=lambda g: int(g.id[1:])), cruce
