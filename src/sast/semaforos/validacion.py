"""Chequeos de los planes leídos. Se reportan todos; ninguno corrige el dato.

Niveles: ERROR (el dato no se puede usar así; detiene 09 salvo decisión registrada en
config/semaforos.yaml), AVISO (raro pero usable; se informa) e INFO (constancia).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from sast.semaforos.tiempos import NO_ROJO, dur, estado

# Duraciones observadas en los cinco reportes. Un desvío se reporta, no se corrige.
PREPARACION_S, AMARILLO_S, DESPEJE_S = 2, 3, 1


@dataclass
class Hallazgo:
    nivel: str
    interseccion: str
    plan: str
    codigo: str
    texto: str


def validar(inter: dict) -> list[Hallazgo]:
    """`inter`: dict armado por 09 con resumen, grupos, planes, matriz y horario de un reporte."""
    iid = inter["id"]
    out: list[Hallazgo] = []

    def h(nivel, plan, codigo, texto):
        out.append(Hallazgo(nivel, iid, plan, codigo, texto))

    r, esperado = inter["resumen"], inter["controlador"]
    if (r["equipo"], r["cruce"]) != (esperado["equipo"], esperado["cruce"]):
        h("ERROR", "", "controlador", f"El reporte es del equipo {r['equipo']}/cruce {r['cruce']}; "
          f"config espera {esperado['equipo']}/{esperado['cruce']}")
    grupos = inter["grupos"]
    ids = [g["id"] for g in grupos]
    tipo = {g["id"]: g["tipo"] for g in grupos}
    if r["n_grupos"] != len(grupos):
        h("ERROR", "", "n_grupos", f"Resumen dice {r['n_grupos']} grupos; se leyeron {len(grupos)}")
    if r["n_planes"] != len(inter["planes"]):
        h("ERROR", "", "n_planes", f"Resumen dice {r['n_planes']} planes; se leyeron {len(inter['planes'])}")
    if r["n_horarios"] != len(inter["leyenda"]):
        h("AVISO", "", "n_horarios", f"Resumen dice {r['n_horarios']} horarios; la leyenda trae {len(inter['leyenda'])}")
    for cruce in sorted({p["cruce_pie"] for p in inter["planes"]}):
        if not cruce.startswith(f"CRUCE {r['cruce']},"):
            h("ERROR", "", "cruce_pie", f"Pie de plan «{cruce}» no corresponde al cruce {r['cruce']}")
    if len({p["cruce_pie"] for p in inter["planes"]}) > 1:
        h("AVISO", "", "cruce_pie", "Los planes traen pies de cruce distintos")
    h("INFO", "", "ubicacion", f"Reporte: «{r['direccion']}»; planes: «{inter['planes'][0]['cruce_pie']}»")

    # ---- matriz de grupos amigos
    m = inter["matriz"]
    if m["grupos"] != ids:
        h("ERROR", "", "matriz_grupos", f"Matriz con grupos {m['grupos']}; planes con {ids}")
    for i, j, v in m["ambiguas"]:
        h("ERROR", "", "matriz_ambigua", f"Celda {i}×{j} ambigua (fracción verde {v})")
    amigos = m["amigos"]
    for i in ids:
        if (i, i) not in amigos:
            h("ERROR", "", "matriz_diagonal", f"{i} no figura amigo de sí mismo")
    for i, j in combinations(ids, 2):
        if ((i, j) in amigos) != ((j, i) in amigos):
            h("ERROR", "", "matriz_asimetrica", f"{i}×{j} y {j}×{i} no coinciden")

    # ---- planes
    for p in inter["planes"]:
        pid, c = p["id"], p["ciclo"]
        if abs(p["ciclo_crudo"] - c) > 0.05:
            h("ERROR", pid, "ciclo", f"Escala del eje da {p['ciclo_crudo']:.3f} s, no un entero")
        if list(p["tiempos"]) != ids:
            h("ERROR", pid, "grupos", f"Grupos del plan {list(p['tiempos'])} ≠ {ids}")
            continue
        fin_ciclo = []
        for g, t in p["tiempos"].items():
            for k in ("tiv", "tfv", "tfa"):
                if t[k] is None:
                    h("ERROR", pid, "valor_faltante", f"{g}: falta {k.upper()}")
            if None in (t["tiv"], t["tfv"], t["tfa"]):
                continue
            for k, v in t.items():
                if v is not None and not 0 <= v <= c:
                    h("ERROR", pid, "fuera_de_ciclo", f"{g}: {k.upper()} = {v} fuera de 0–{c}")
            if t["tfa"] == c:
                fin_ciclo.append(g)
            if t["tira"] is None and tipo[g] != "peatonal":
                h("AVISO", pid, "tira_vacia", f"{g} ({tipo[g]}): TIRA en blanco en la tabla del PDF; revisar si el "
                  "diagrama de barras de esa página dibuja preparación antes del verde y decidir cuál vale "
                  "(config: decisiones; en campo se ve rojo igual, decisión 29)")
            prep = dur(t["tira"], t["tiv"], c) if t["tira"] is not None else 0
            verde, cola = dur(t["tiv"], t["tfv"], c), dur(t["tfv"], t["tfa"], c)
            if verde == 0:
                h("ERROR", pid, "verde_nulo", f"{g}: verde de 0 s")
            if prep + verde + cola >= c:
                h("ERROR", pid, "orden", f"{g}: TIRA→TIV→TFV→TFA ocupa todo el ciclo o más")
            if t["tira"] is not None and prep != PREPARACION_S:
                h("AVISO", pid, "preparacion", f"{g}: preparación de {prep:g} s (lo usual: {PREPARACION_S})")
            esperado_cola = DESPEJE_S if tipo[g] == "peatonal" else AMARILLO_S
            if cola != esperado_cola:
                h("AVISO", pid, "amarillo" if tipo[g] != "peatonal" else "despeje",
                  f"{g}: {'despeje' if tipo[g] == 'peatonal' else 'amarillo'} de {cola:g} s "
                  f"(lo usual: {esperado_cola})")
        if fin_ciclo:
            h("INFO", pid, "tfa_fin_ciclo", f"TFA = {c} (fin del ciclo) en {', '.join(fin_ciclo)}: equivale a 0")

        # conflictos: nadie fuera de la matriz con paso habilitado a la vez
        est = {g: [estado(t, tipo[g], k + 0.5, c) for k in range(c)] for g, t in p["tiempos"].items()}
        for i, j in combinations(ids, 2):
            juntos = [k for k in range(c) if est[i][k] in NO_ROJO and est[j][k] in NO_ROJO]
            verdes = [k for k in range(c) if est[i][k] == "verde" and est[j][k] == "verde"]
            if (i, j) not in amigos and juntos:
                h("ERROR", pid, "conflicto", f"{i} y {j} no son amigos y tienen paso a la vez en "
                  f"{len(juntos)} s (desde t = {juntos[0]})")
            if verdes and (i, j) not in amigos:
                h("ERROR", pid, "verde_no_amigo", f"{i} y {j} en verde a la vez sin ser amigos")
        # despeje mínimo entre grupos en conflicto: fin de i (TFA) -> inicio del verde de j
        despejes = []
        for i in ids:
            for j in ids:
                if i != j and (i, j) not in amigos:
                    ti, tj = p["tiempos"][i], p["tiempos"][j]
                    if None not in (ti["tfa"], tj["tiv"]):
                        despejes.append((dur(ti["tfa"], tj["tiv"], c), i, j))
        if despejes:
            s, i, j = min(despejes)
            h("INFO", pid, "todo_rojo_min", f"Despeje mínimo entre grupos en conflicto: {s:g} s ({i} → {j})")
            for s0, i0, j0 in sorted(despejes):
                if s0 == 0:
                    h("AVISO", pid, "despeje_cero", f"{i0} termina su amarillo o despeje y {j0} entra en verde "
                      "en el mismo segundo: 0 s de despeje entre grupos en conflicto")

    # ---- horario
    planes = {p["id"] for p in inter["planes"]}
    usados = {b[2] for fila in inter["horario"].values() for b in fila}
    for nivel, texto in inter["hallazgos_horario"]:
        h(nivel, "", "horario", texto)
    for pid in sorted(usados - planes):
        h("ERROR", pid, "horario_sin_plan", f"El horario usa {pid}, que no tiene página de plan")
    for pid in sorted(planes - usados):
        h("INFO", pid, "plan_sin_horario", f"{pid} está programado en el controlador pero no tiene horario: no corre")
    for dia, fila in inter["horario"].items():
        if not fila or fila[0][0] != 0 or fila[-1][1] != 1440:
            h("ERROR", "", "horario_cobertura", f"{dia}: no cubre de 00:00 a 24:00")
    if any(t["fin"] == 1440 for t in inter["leyenda_dict"]):
        h("INFO", "", "fin_dia", "La leyenda termina tramos a las 23:59: se toma como 24:00")
    return out
