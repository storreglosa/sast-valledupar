"""Horario semanal del controlador (última página) y festivos de Colombia.

La página trae dos cosas:
- una grilla de 8 filas (Lunes … Domingo, Festivo) × 24 h, con un rótulo «Pn» donde empieza
  cada bloque: de ahí salen los DÍAS en que corre cada plan;
- una leyenda con HORA INICIO / HORA FIN exactas de cada tramo: de ahí salen las HORAS. Los días
  activos de la leyenda solo se distinguen por el color de la letra, que no se puede leer como
  texto; por eso los días se toman de la grilla.
Cada rótulo de la grilla se ajusta al inicio de la leyenda del mismo plan (±20 min). «23:59» es
fin de día (1440 min).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from sast.semaforos.pdf import Palabra, misma_linea, palabras

DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo", "festivo")
_ROTULO_DIA = {"Lunes": "lunes", "Martes": "martes", "Miercoles": "miercoles", "Jueves": "jueves",
               "Viernes": "viernes", "Sabado": "sabado", "Domingo": "domingo", "Festivo": "festivo"}
TOLERANCIA_MIN = 20
X_LEYENDA = 690.0


@dataclass(frozen=True)
class Tramo:
    plan: str
    inicio: int   # minutos desde 00:00
    fin: int


def _min(hh: str, mm: str) -> int:
    m = int(hh) * 60 + int(mm)
    return 1440 if m == 23 * 60 + 59 else m


def leer_leyenda(ps: list[Palabra]) -> list[Tramo]:
    der = sorted((p for p in ps if p.x0 >= X_LEYENDA), key=lambda p: (round(p.y0, 1), p.x0))
    tramos, plan = [], None
    for y in sorted({round(p.y0, 1) for p in der}):
        linea = [p.texto for p in der if round(p.y0, 1) == y]
        t = " ".join(linea)
        if m := re.fullmatch(r"PLAN (\d+)", t):
            plan = f"P{m.group(1)}"
        elif m := re.fullmatch(r"HORA INICIO (\d\d) : (\d\d) HORA FIN (\d\d) : (\d\d)", t):
            if plan is None:
                raise ValueError("Tramo de horario antes de cualquier PLAN en la leyenda")
            tramos.append(Tramo(plan, _min(*m.group(1, 2)), _min(*m.group(3, 4))))
    return tramos


def leer_horario(pdf: Path, pagina: int) -> dict:
    """{dia: [[inicio, fin, plan], …]}, la leyenda y los hallazgos de la lectura."""
    ps = palabras(pdf, pagina)
    hallazgos = []
    leyenda = leer_leyenda(ps)
    horas = {p.texto: p for p in ps if re.fullmatch(r"\d\d:00", p.texto)}
    if "00:00" not in horas or "22:00" not in horas:
        raise ValueError(f"{pdf.name}: no se encontró el eje de horas del horario")
    x0 = horas["00:00"].xc
    pt_min = (horas["22:00"].xc - x0) / (22 * 60)
    filas = {_ROTULO_DIA[p.texto]: p for p in ps if p.texto in _ROTULO_DIA and p.x0 < 120}
    if set(filas) != set(DIAS):
        raise ValueError(f"{pdf.name}: faltan filas del horario: {sorted(set(DIAS) - set(filas))}")

    horario = {}
    for dia, rot in filas.items():
        etiquetas = sorted((p for p in ps if re.fullmatch(r"P\d+", p.texto) and abs(p.yc - rot.yc) < 4
                            and p.x0 < X_LEYENDA), key=lambda p: p.x0)
        bloques = []
        for e in etiquetas:
            leido = (e.x0 - 2 - x0) / pt_min   # el rótulo va 2 pt a la derecha del inicio del bloque
            cand = [t for t in leyenda if t.plan == e.texto]
            if not cand:
                hallazgos.append(("ERROR", f"{dia}: {e.texto} en la grilla no está en la leyenda"))
                continue
            t = min(cand, key=lambda t: abs(t.inicio - leido))
            if abs(t.inicio - leido) > TOLERANCIA_MIN:
                hallazgos.append(("ERROR", f"{dia}: {e.texto} empieza en la grilla a las "
                                  f"{_hhmm(round(leido))}, sin tramo de la leyenda cercano"))
                continue
            bloques.append([t.inicio, None, e.texto])
        for i, b in enumerate(bloques):
            b[1] = bloques[i + 1][0] if i + 1 < len(bloques) else 1440
        if not bloques or bloques[0][0] != 0:
            hallazgos.append(("ERROR", f"{dia}: el horario no empieza a las 00:00"))
        for ini, fin, plan in bloques:
            if not any(t.plan == plan and t.inicio == ini and t.fin == fin for t in leyenda):
                hallazgos.append(("AVISO", f"{dia}: bloque {plan} {_hhmm(ini)}–{_hhmm(fin)} no coincide "
                                  "con un tramo completo de la leyenda"))
        horario[dia] = bloques

    usados = {(plan, ini) for bl in horario.values() for ini, _, plan in bl}
    for t in leyenda:
        if (t.plan, t.inicio) not in usados:
            hallazgos.append(("AVISO", f"Tramo {t.plan} {_hhmm(t.inicio)}–{_hhmm(t.fin)} de la leyenda "
                              "no aparece en la grilla"))
    return {"horario": {d: horario[d] for d in DIAS}, "leyenda": leyenda, "hallazgos": hallazgos}


def _hhmm(m: int) -> str:
    return "24:00" if m >= 1440 else f"{m // 60:02d}:{m % 60:02d}"


# ---------------------------------------------------------------- festivos (Ley 51 de 1983)
def pascua(anio: int) -> date:
    """Domingo de Pascua (algoritmo anónimo gregoriano)."""
    a, b, c = anio % 19, anio // 100, anio % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(anio, mes, dia)


def _lunes_siguiente(d: date) -> date:
    return d + timedelta(days=(7 - d.weekday()) % 7)


def festivos(anio: int) -> dict[date, str]:
    fijos = {(1, 1): "Año Nuevo", (5, 1): "Día del Trabajo", (7, 20): "Día de la Independencia",
             (8, 7): "Batalla de Boyacá", (12, 8): "Inmaculada Concepción", (12, 25): "Navidad"}
    trasladables = {(1, 6): "Reyes Magos", (3, 19): "San José", (6, 29): "San Pedro y San Pablo",
                    (8, 15): "Asunción de la Virgen", (10, 12): "Día de la Raza",
                    (11, 1): "Todos los Santos", (11, 11): "Independencia de Cartagena"}
    out = {date(anio, m, d): n for (m, d), n in fijos.items()}
    out.update({_lunes_siguiente(date(anio, m, d)): n for (m, d), n in trasladables.items()})
    p = pascua(anio)
    out[p - timedelta(days=3)] = "Jueves Santo"
    out[p - timedelta(days=2)] = "Viernes Santo"
    out[p + timedelta(days=43)] = "Ascensión del Señor"
    out[p + timedelta(days=64)] = "Corpus Christi"
    out[p + timedelta(days=71)] = "Sagrado Corazón"
    return dict(sorted(out.items()))


def dia_horario(d: date) -> str:
    """Fila del horario que rige ese día: «festivo» si lo es, si no el día de la semana."""
    if d in festivos(d.year):
        return "festivo"
    return DIAS[d.weekday()]


def plan_vigente(horario: dict, momento: datetime) -> tuple[str, int, int]:
    """(plan, inicio, fin) en minutos del bloque que rige en `momento` (hora local de Bogotá)."""
    fila = horario[dia_horario(momento.date())]
    m = momento.hour * 60 + momento.minute + momento.second / 60
    for ini, fin, plan in fila:
        if ini <= m < fin:
            return plan, ini, fin
    raise ValueError(f"Sin plan a las {momento:%H:%M} del {momento:%d/%m/%Y}")
