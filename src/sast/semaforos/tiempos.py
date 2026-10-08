"""Modelo de estados del ciclo semafórico. `tablero/js/nucleo/tiempos.js` lo replica y una
prueba compara los dos contra `tests/fixtures/estados_referencia.json`.

Estados (decisión 29, así se ve en campo):
  preparacion  TIRA–TIV, solo vehiculares: el controlador lo grafica rojo-amarillo; en campo es rojo
  verde        TIV–TFV
  amarillo     TFV–TFA, vehiculares
  despeje      TFV–TFA, peatonales: rojo intermitente
  rojo         el resto del ciclo
Todos los tiempos son segundos enteros, así que evaluar en k + 0,5 (k = 0 … C−1) es exacto.
"""

from __future__ import annotations

CODIGO = {"preparacion": "p", "verde": "V", "amarillo": "A", "despeje": "D", "rojo": "r"}
NO_ROJO = {"verde", "amarillo", "despeje"}   # indicaciones que habilitan o despejan el paso


def dur(a: float, b: float, c: int) -> float:
    """Segundos de a hasta b avanzando en el ciclo (0 si a == b)."""
    return ((b - a) % c + c) % c


def dentro(t: float, a: float, b: float, c: int) -> bool:
    return dur(a, t, c) < dur(a, b, c)


def estado(tiempos: dict, tipo: str, t: float, c: int) -> str:
    t = ((t % c) + c) % c
    if tiempos.get("tira") is not None and dentro(t, tiempos["tira"], tiempos["tiv"], c):
        return "preparacion"
    if dentro(t, tiempos["tiv"], tiempos["tfv"], c):
        return "verde"
    if dentro(t, tiempos["tfv"], tiempos["tfa"], c):
        return "despeje" if tipo == "peatonal" else "amarillo"
    return "rojo"


def restante(tiempos: dict, t: float, c: int) -> float:
    """Segundos hasta el próximo cambio de indicación de ese grupo."""
    bordes = [v for k, v in tiempos.items() if v is not None]
    return min(dur(t, b, c) or c for b in bordes)


def cadena(tiempos: dict, tipo: str, c: int) -> str:
    """Un carácter por segundo del ciclo (evaluado en k + 0,5)."""
    return "".join(CODIGO[estado(tiempos, tipo, k + 0.5, c)] for k in range(c))


def etapas(plan: dict, grupos: list[dict]) -> list[dict]:
    """Intervalos del ciclo con el mismo conjunto de grupos en verde (cíclicos, fusionados)."""
    c = plan["ciclo"]
    tipo = {g["id"]: g["tipo"] for g in grupos}
    verdes = [tuple(sorted((g for g, ti in plan["tiempos"].items()
                            if estado(ti, tipo[g], k + 0.5, c) == "verde"), key=lambda g: int(g[1:])))
              for k in range(c)]
    # arranca en un cambio para no partir una etapa en el borde 0/C
    inicio = next((k for k in range(c) if verdes[k] != verdes[k - 1]), 0)
    out = []
    for i in range(c):
        k = (inicio + i) % c
        if out and out[-1]["verdes"] == list(verdes[k]):
            out[-1]["fin"] = (k + 1) % c or c
            out[-1]["duracion"] += 1
        else:
            out.append({"inicio": k, "fin": (k + 1) % c or c, "duracion": 1, "verdes": list(verdes[k])})
    return out


def kpis(plan: dict, grupos: list[dict]) -> dict:
    c = plan["ciclo"]
    tipo = {g["id"]: g["tipo"] for g in grupos}
    verde = {g: int(dur(ti["tiv"], ti["tfv"], c)) for g, ti in plan["tiempos"].items()}
    rojo_veh = {g: int(c - dur(ti["tiv"], ti["tfa"], c)) for g, ti in plan["tiempos"].items()
                if tipo[g] != "peatonal"}
    todo_rojo = sum(all(estado(ti, tipo[g], k + 0.5, c) not in NO_ROJO
                        for g, ti in plan["tiempos"].items()) for k in range(c))
    return {"ciclo": c, "ciclos_hora": round(3600 / c, 1), "verde_s": verde,
            "verde_pct": {g: round(100 * v / c, 1) for g, v in verde.items()},
            "rojo_s": rojo_veh, "todo_rojo_s": todo_rojo}
