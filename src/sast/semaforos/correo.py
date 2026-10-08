"""Diferencias entre la tabla del correo del 29/09/2026 (`config/semaforos_correo.yaml`) y lo
programado en los controladores. Decisión 27: manda el controlador."""

from __future__ import annotations

import yaml

from sast.rutas import CONFIG

DECISION = "Manda el controlador (decisión 27, Santiago, 2026-10-08)"
TIPOS_DIA = {"lun-sab": ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado"),
             "dom-fes": ("domingo", "festivo")}


def leer() -> dict:
    with open(CONFIG / "semaforos_correo.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _min(hhmm: str) -> int:
    h, m = map(int, hhmm.split(":"))
    return 1440 if (h, m) == (23, 59) else h * 60 + m


def _tramos(txt: list[str]) -> list[tuple[int, int]]:
    return [tuple(_min(x) for x in t.split("-")) for t in txt]


def _fmt(tr: list[tuple[int, int]]) -> str:
    f = lambda m: "23:59" if m == 1440 else f"{m // 60:02d}:{m % 60:02d}"
    return " y ".join(f"{f(a)}–{f(b)}" for a, b in tr) or "sin horario"


def minutos_correo(entrada: dict) -> dict[str, set[int]]:
    """{dia: minutos en que el correo dice que corre ese plan}."""
    out = {d: set() for d in TIPOS_DIA["lun-sab"] + TIPOS_DIA["dom-fes"]}
    for clave, txt in entrada.items():
        if clave == "ciclo":
            continue
        dias = out.keys() if clave == "todos" else TIPOS_DIA[clave]
        for a, b in _tramos(txt):
            for d in dias:
                out[d] |= set(range(a, b))
    return out


def minutos_controlador(horario: dict, plan: str) -> dict[str, set[int]]:
    return {d: {m for a, b, p in fila if p == plan for m in range(a, b)} for d, fila in horario.items()}


def _tramos_de(mins: set[int]) -> list[tuple[int, int]]:
    out = []
    for m in sorted(mins):
        if out and out[-1][1] == m:
            out[-1][1] = m + 1
        else:
            out.append([m, m + 1])
    return [tuple(t) for t in out]


def diferencias(intersecciones: list[dict]) -> list[dict]:
    correo = leer()["intersecciones"]
    filas = []
    for it in intersecciones:
        if it["correo"] is None:
            filas.append({"interseccion": it["nombre"], "plan": "", "campo": "interseccion",
                          "correo": "no incluida en el correo",
                          "controlador": f"{len(it['planes'])} planes", "decision": DECISION})
            continue
        tabla = correo[it["correo"]]
        planes = {p["id"]: p for p in it["planes"]}
        for pid in sorted(set(tabla) | set(planes)):
            ec, pc = tabla.get(pid), planes.get(pid)
            if ec is None:
                usado = any(b[2] == pid for f in it["horario"].values() for b in f)
                if usado:
                    filas.append({"interseccion": it["nombre"], "plan": pid, "campo": "plan",
                                  "correo": "no aparece", "controlador": f"corre, ciclo {pc['ciclo']} s",
                                  "decision": DECISION})
                continue
            if pc is None:
                filas.append({"interseccion": it["nombre"], "plan": pid, "campo": "plan",
                              "correo": f"ciclo {ec['ciclo']} s", "controlador": "no existe",
                              "decision": DECISION})
                continue
            if ec["ciclo"] != pc["ciclo"]:
                filas.append({"interseccion": it["nombre"], "plan": pid, "campo": "ciclo",
                              "correo": f"{ec['ciclo']} s", "controlador": f"{pc['ciclo']} s",
                              "decision": DECISION})
            mc, mk = minutos_correo(ec), minutos_controlador(it["horario"], pid)
            for grupo, dias in (("lun-sab", TIPOS_DIA["lun-sab"]), ("domingo", ("domingo",)),
                                ("festivo", ("festivo",))):
                a = {d: mc[d] for d in dias}
                b = {d: mk[d] for d in dias}
                if a != b:
                    filas.append({"interseccion": it["nombre"], "plan": pid, "campo": f"horario {grupo}",
                                  "correo": _fmt(_tramos_de(set().union(*a.values()))),
                                  "controlador": _fmt(_tramos_de(set().union(*b.values()))),
                                  "decision": DECISION})
    return filas
