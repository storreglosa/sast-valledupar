"""Grupo semafórico -> movimiento, según la codificación de trayectorias de la SDM Bogotá
(Manual de Planeación y Diseño para la Administración del Tránsito y el Transporte, 2005, Tomo III,
num. 5.2.1), que es la que usan los nombres de grupo de los controladores SISTRA (decisión 30).

Accesos (de dónde VIENE el vehículo): 1 norte, 2 sur, 3 oeste, 4 este.
  Flujo k (1–4)     directo desde el acceso k
  Flujo k (5–8)     giro a la izquierda desde el acceso k − 4
  Flujo 9k          giro a la derecha desde el acceso k
  Peatonal 2k       cruce sobre la mitad de ENTRADA del acceso k
  Peatonal 3k       cruce sobre la mitad por donde SALE el directo k (31 sur, 32 norte, 33 este, 34 oeste)
  Flecha            sin número: el giro se deduce de la matriz de grupos amigos y queda por confirmar
"""

from __future__ import annotations

import re

ACCESO = {1: "norte", 2: "sur", 3: "oeste", 4: "este"}
OPUESTO = {"norte": "sur", "sur": "norte", "este": "oeste", "oeste": "este"}
# hacia dónde va cada directo / a qué brazo sale
SALIDA_DIRECTO = {"norte": "sur", "sur": "norte", "oeste": "este", "este": "oeste"}
# giro a la izquierda / derecha de quien viene desde cada acceso (sale por ese brazo)
IZQUIERDA = {"norte": "este", "sur": "oeste", "oeste": "norte", "este": "sur"}
DERECHA = {"norte": "oeste", "sur": "este", "oeste": "sur", "este": "norte"}
CARDINALES = ("norte", "este", "sur", "oeste")   # sentido horario


def movimiento(nombre: str) -> dict:
    """«Flujo 2» -> {tipo, codigo, acceso, giro, sale_por}; «Peatonal 31» -> {tipo, codigo, brazo, mitad}."""
    m = re.fullmatch(r"(Flujo|Peatonal|Flecha)\s*(\d*)", nombre.strip())
    if not m:
        raise ValueError(f"Nombre de grupo fuera de la codificación: «{nombre}»")
    clase, num = m.group(1), m.group(2)
    if clase == "Flecha":
        return {"tipo": "flecha", "codigo": None, "acceso": None, "giro": None, "sale_por": None}
    n = int(num)
    if clase == "Flujo":
        if 1 <= n <= 4:
            a = ACCESO[n]
            return {"tipo": "vehicular", "codigo": str(n), "acceso": a, "giro": "directo",
                    "sale_por": SALIDA_DIRECTO[a]}
        if 5 <= n <= 8:
            a = ACCESO[n - 4]
            return {"tipo": "vehicular", "codigo": str(n), "acceso": a, "giro": "izquierda",
                    "sale_por": IZQUIERDA[a]}
        if 91 <= n <= 94:
            a = ACCESO[n - 90]
            return {"tipo": "vehicular", "codigo": f"9({n - 90})", "acceso": a, "giro": "derecha",
                    "sale_por": DERECHA[a]}
    if clase == "Peatonal":
        if 21 <= n <= 24:
            return {"tipo": "peatonal", "codigo": str(n), "brazo": ACCESO[n - 20], "mitad": "entrada"}
        if 31 <= n <= 34:
            return {"tipo": "peatonal", "codigo": str(n), "brazo": SALIDA_DIRECTO[ACCESO[n - 30]],
                    "mitad": "salida"}
    raise ValueError(f"Código fuera de la codificación SDM: «{nombre}»")


def candidatos_flecha(flecha: str, grupos: list[dict], amigos: set) -> list[dict]:
    """Giros compatibles con todo lo que corre junto a la flecha (sus amigos vehiculares).

    Un giro es candidato si no cruza a ningún amigo vehicular: no sale por el brazo de entrada
    de un amigo ni corta su trayectoria. Se usa una prueba simple de conflicto entre pares de
    movimientos de una intersección de 4 brazos.
    """
    movs = {g["id"]: movimiento(g["nombre"]) for g in grupos}
    amigos_veh = [movs[j] for (i, j) in amigos if i == flecha and j != flecha and movs[j]["tipo"] == "vehicular"]
    out = []
    for a in CARDINALES:
        for giro, destino in (("izquierda", IZQUIERDA[a]), ("derecha", DERECHA[a])):
            cand = {"acceso": a, "giro": giro, "sale_por": destino}
            if all(not conflicto(cand, m) for m in amigos_veh):
                out.append(cand)
    return out


def conflicto(a: dict, b: dict) -> bool:
    """¿Se cruzan las trayectorias a y b (acceso -> sale_por) dentro del cruce? Convergencias en la
    misma salida cuentan como conflicto; mismo acceso no."""
    if a["acceso"] == b["acceso"]:
        return False
    if a["sale_por"] == b["sale_por"]:
        return True
    orden = {c: i for i, c in enumerate(CARDINALES)}

    def arco(m):
        # cuerda entre el punto de entrada y el de salida en el borde del cruce. Tránsito por la
        # derecha: quien entra por el brazo norte (rumbo 0°) va por su lado oeste (340°) y quien
        # sale por él va por el lado este (20°).
        e = orden[m["acceso"]] * 90 - 20
        s = orden[m["sale_por"]] * 90 + 20
        return e % 360, s % 360

    def separa(p, q, x):
        # ¿x queda en el arco que va de p a q en sentido horario?
        return (x - p) % 360 < (q - p) % 360

    ea, sa = arco(a)
    eb, sb = arco(b)
    return separa(ea, sa, eb) != separa(ea, sa, sb)
