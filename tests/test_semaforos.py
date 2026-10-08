"""Pruebas del modelo de tiempos, el horario, los festivos y las validaciones de semáforos.

    python -m unittest discover -s tests -v

Las pruebas que leen los PDF usan data/raw/semaforos/ (o SAST_RAW) y se saltan con aviso si
no están los insumos.
"""

import sys
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sast.rutas import RAW  # noqa: E402
from sast.semaforos import accesos, horario, tiempos  # noqa: E402
from sast.semaforos.validacion import validar  # noqa: E402

VEH, PEA = "vehicular", "peatonal"


class Tiempos(unittest.TestCase):
    def test_vuelta_de_ciclo_loperena_p2_g3(self):
        g3 = {"tira": 98, "tiv": 0, "tfv": 27, "tfa": 30}
        self.assertEqual(tiempos.estado(g3, VEH, 98.0, 100), "preparacion")
        self.assertEqual(tiempos.estado(g3, VEH, 99.9, 100), "preparacion")
        self.assertEqual(tiempos.estado(g3, VEH, 0, 100), "verde")
        self.assertEqual(tiempos.estado(g3, VEH, 26.9, 100), "verde")
        self.assertEqual(tiempos.estado(g3, VEH, 27, 100), "amarillo")
        self.assertEqual(tiempos.estado(g3, VEH, 30, 100), "rojo")
        self.assertEqual(tiempos.estado(g3, VEH, -1, 100), "preparacion")   # t negativo = 99
        self.assertEqual(tiempos.estado(g3, VEH, 200.5, 100), "verde")      # t ≥ C

    def test_la_vina_p2_g2_cruza_el_cero(self):
        g2 = {"tira": 78, "tiv": 80, "tfv": 20, "tfa": 23}
        esperado = {79: "preparacion", 80: "verde", 99.9: "verde", 0: "verde", 19.9: "verde",
                    20: "amarillo", 22.9: "amarillo", 23: "rojo", 77.9: "rojo"}
        for t, e in esperado.items():
            self.assertEqual(tiempos.estado(g2, VEH, t, 100), e, f"t = {t}")

    def test_peatonal_despeje_es_rojo_intermitente(self):
        g = {"tira": None, "tiv": 27, "tfv": 71, "tfa": 72}
        self.assertEqual(tiempos.estado(g, PEA, 71.5, 100), "despeje")
        self.assertEqual(tiempos.estado(g, PEA, 26.5, 100), "rojo")

    def test_tfa_igual_al_ciclo(self):
        g = {"tira": 64, "tiv": 66, "tfv": 87, "tfa": 90}   # Área Andina P1 G1
        self.assertEqual(tiempos.estado(g, VEH, 89.5, 90), "amarillo")
        self.assertEqual(tiempos.estado(g, VEH, 0.5, 90), "rojo")

    def test_restante(self):
        g = {"tira": 78, "tiv": 80, "tfv": 20, "tfa": 23}
        self.assertEqual(tiempos.restante(g, 10, 100), 10)
        self.assertEqual(tiempos.restante(g, 23, 100), 55)
        self.assertEqual(tiempos.restante(g, 95, 100), 25)

    def test_kpis_y_etapas(self):
        plan = {"ciclo": 100, "tiempos": {"G1": {"tira": 25, "tiv": 27, "tfv": 72, "tfa": 75},
                                          "G2": {"tira": 78, "tiv": 80, "tfv": 20, "tfa": 23}}}
        grupos = [{"id": "G1", "tipo": VEH}, {"id": "G2", "tipo": VEH}]
        k = tiempos.kpis(plan, grupos)
        self.assertEqual(k["verde_s"], {"G1": 45, "G2": 40})
        self.assertEqual(k["ciclos_hora"], 36.0)
        self.assertEqual(k["todo_rojo_s"], 4 + 5)     # 23–27 y 75–80 (la preparación es rojo)
        et = tiempos.etapas(plan, grupos)
        self.assertEqual(sum(e["duracion"] for e in et), 100)
        self.assertIn({"inicio": 80, "fin": 20, "duracion": 40, "verdes": ["G2"]}, et)


class Festivos(unittest.TestCase):
    # Calendario oficial (Ley 51 de 1983)
    OFICIAL = {
        2026: ["01-01", "01-12", "03-23", "04-02", "04-03", "05-01", "05-18", "06-08", "06-15", "06-29",
               "07-20", "08-07", "08-17", "10-12", "11-02", "11-16", "12-08", "12-25"],
        2027: ["01-01", "01-11", "03-22", "03-25", "03-26", "05-01", "05-10", "05-31", "06-07", "07-05",
               "07-20", "08-07", "08-16", "10-18", "11-01", "11-15", "12-08", "12-25"],
    }

    def test_calendario(self):
        for anio, fechas in self.OFICIAL.items():
            calc = [d.strftime("%m-%d") for d in horario.festivos(anio)]
            self.assertEqual(calc, fechas, anio)

    def test_pascua(self):
        self.assertEqual(horario.pascua(2026), date(2026, 4, 5))
        self.assertEqual(horario.pascua(2027), date(2027, 3, 28))


class PlanVigente(unittest.TestCase):
    LA_VINA = {d: [[0, 330, "P3"], [330, 690, "P2"], [690, 810, "P5"], [810, 1020, "P2"],
                   [1020, 1200, "P5"], [1200, 1440, "P3"]] for d in horario.DIAS[:6]}
    LA_VINA |= {d: [[0, 330, "P3"], [330, 1200, "P1"], [1200, 1440, "P3"]] for d in ("domingo", "festivo")}

    def test_bordes_y_festivo(self):
        pv = lambda *a: horario.plan_vigente(self.LA_VINA, datetime(*a))[0]
        self.assertEqual(pv(2026, 10, 6, 5, 29, 59), "P3")
        self.assertEqual(pv(2026, 10, 6, 5, 30), "P2")
        self.assertEqual(pv(2026, 10, 6, 23, 59, 59), "P3")
        self.assertEqual(pv(2026, 10, 11, 10, 0), "P1")    # domingo
        self.assertEqual(pv(2026, 10, 12, 10, 0), "P1")    # lunes festivo (Día de la Raza)
        self.assertEqual(pv(2026, 10, 13, 10, 0), "P2")


def _inter(tiempos_plan: dict, amigos: set, tipos: dict) -> dict:
    ids = list(tiempos_plan)
    todos = {(i, i) for i in ids} | amigos | {(j, i) for i, j in amigos}
    fila = [[0, 1440, "P1"]]
    return {"id": "prueba", "controlador": {"equipo": "1", "cruce": "1"},
            "resumen": {"equipo": "1", "cruce": "1", "direccion": "x", "n_grupos": len(ids),
                        "n_planes": 1, "n_horarios": 1},
            "grupos": [{"id": g, "nombre": g, "tipo": tipos[g]} for g in ids],
            "matriz": {"grupos": ids, "amigos": todos, "ambiguas": []},
            "planes": [{"id": "P1", "ciclo": 60, "ciclo_crudo": 60.0, "cruce_pie": "CRUCE 1, UBICADO EN x",
                        "tiempos": tiempos_plan}],
            "horario": {d: fila for d in horario.DIAS}, "leyenda": [object()],
            "leyenda_dict": [{"plan": "P1", "inicio": 0, "fin": 1440}], "hallazgos_horario": []}


class Conflictos(unittest.TestCase):
    def test_detecta_conflicto_sintetico(self):
        t = {"G1": {"tira": 0, "tiv": 2, "tfv": 30, "tfa": 33},
             "G2": {"tira": 25, "tiv": 27, "tfv": 55, "tfa": 58}}     # G2 entra antes de que G1 termine
        hs = validar(_inter(t, set(), {"G1": VEH, "G2": VEH}))
        self.assertTrue(any(h.codigo == "conflicto" and h.nivel == "ERROR" for h in hs))

    def test_plan_limpio_sin_errores(self):
        t = {"G1": {"tira": 0, "tiv": 2, "tfv": 25, "tfa": 28},
             "G2": {"tira": 30, "tiv": 32, "tfv": 55, "tfa": 58}}
        hs = validar(_inter(t, set(), {"G1": VEH, "G2": VEH}))
        self.assertEqual([h for h in hs if h.nivel == "ERROR"], [])

    def test_verde_simultaneo_sin_ser_amigos(self):
        t = {"G1": {"tira": 0, "tiv": 2, "tfv": 25, "tfa": 28},
             "G2": {"tira": None, "tiv": 5, "tfv": 20, "tfa": 21}}
        hs = validar(_inter(t, set(), {"G1": VEH, "G2": PEA}))
        self.assertTrue(any(h.codigo == "verde_no_amigo" for h in hs))
        hs = validar(_inter(t, {("G1", "G2")}, {"G1": VEH, "G2": PEA}))
        self.assertFalse(any(h.nivel == "ERROR" for h in hs))


class Codificacion(unittest.TestCase):
    """Codificación de trayectorias SDM Bogotá (decisión 30)."""

    def test_flujos_y_peatonales(self):
        m = accesos.movimiento
        self.assertEqual((m("Flujo 1")["acceso"], m("Flujo 1")["sale_por"]), ("norte", "sur"))
        self.assertEqual((m("Flujo 4")["acceso"], m("Flujo 4")["sale_por"]), ("este", "oeste"))
        self.assertEqual((m("Flujo 5")["acceso"], m("Flujo 5")["giro"], m("Flujo 5")["sale_por"]),
                         ("norte", "izquierda", "este"))
        self.assertEqual((m("Peatonal 22")["brazo"], m("Peatonal 22")["mitad"]), ("sur", "entrada"))
        self.assertEqual((m("Peatonal 31")["brazo"], m("Peatonal 31")["mitad"]), ("sur", "salida"))
        self.assertEqual(m("Peatonal 34")["brazo"], "oeste")
        with self.assertRaises(ValueError):
            m("Grupo raro")

    def test_conflictos_basicos(self):
        d = lambda a, s: {"acceso": a, "sale_por": s}
        self.assertTrue(accesos.conflicto(d("norte", "sur"), d("oeste", "este")))     # directos cruzados
        self.assertFalse(accesos.conflicto(d("norte", "sur"), d("sur", "norte")))     # opuestos
        self.assertTrue(accesos.conflicto(d("norte", "este"), d("oeste", "este")))    # misma salida
        self.assertFalse(accesos.conflicto(d("norte", "oeste"), d("oeste", "este")))  # derecha vs directo

    def test_flecha_manguitos(self):
        g = [{"id": f"G{i}", "nombre": n} for i, n in
             enumerate(["Flujo 1", "Flujo 2", "Flujo 3", "Flujo 4", "Flecha"], 1)]
        amigos = {("G5", "G1"), ("G5", "G3"), ("G1", "G5"), ("G3", "G5")}
        cands = accesos.candidatos_flecha("G5", g, amigos)
        self.assertIn({"acceso": "norte", "giro": "derecha", "sale_por": "oeste"}, cands)


CARPETA = RAW / "semaforos"


@unittest.skipUnless(CARPETA.exists() and any(CARPETA.glob("*_sistra_planes-*.pdf")),
                     f"SIN PDF en {CARPETA}: no se probó la lectura real (docs/ingesta.md)")
class LecturaPdf(unittest.TestCase):
    CICLOS = {"la-vina": {"P1": 85, "P2": 100, "P3": 30, "P5": 100},
              "mercado": {"P1": 85, "P2": 110, "P3": 55, "P5": 100},
              "manguitos": {"P1": 75, "P2": 110, "P3": 65, "P5": 110},
              "loperena": {"P1": 85, "P2": 100, "P4": 50, "P5": 100},
              "area-andina": {"P1": 90, "P2": 105, "P4": 75, "P5": 105}}

    def test_ciclos(self):
        from sast.semaforos import pdf, planes
        for nombre, esperados in self.CICLOS.items():
            ruta = CARPETA / f"2026-09-29_sistra_planes-{nombre}.pdf"
            leidos = {}
            for pag in range(3, pdf.n_paginas(ruta)):
                p, _, _ = planes.leer_plan(ruta, pag)
                leidos[p.id] = p.ciclo
            self.assertEqual(leidos, esperados, nombre)

    def test_tabla_la_vina_p2(self):
        """Transcrita a mano de la p. 3 del reporte de La Viña."""
        from sast.semaforos import planes
        p, g, cruce = planes.leer_plan(CARPETA / "2026-09-29_sistra_planes-la-vina.pdf", 3)
        self.assertEqual(p.id, "P2")
        self.assertEqual(p.tiempos, {"G1": {"tira": 25, "tiv": 27, "tfv": 72, "tfa": 75},
                                     "G2": {"tira": 78, "tiv": 80, "tfv": 20, "tfa": 23},
                                     "G3": {"tira": None, "tiv": 80, "tfv": 19, "tfa": 20},
                                     "G4": {"tira": None, "tiv": 27, "tfv": 71, "tfa": 72}})
        self.assertEqual([x.nombre for x in g], ["Flujo 2", "Flujo 4", "Peatonal 22", "Peatonal 24"])
        self.assertTrue(cruce.startswith("CRUCE 917"))

    def test_matriz_loperena_fase_peatonal_exclusiva(self):
        from sast.semaforos import matriz
        m = matriz.leer_matriz(CARPETA / "2026-09-29_sistra_planes-loperena.pdf")
        self.assertEqual(m["ambiguas"], [])
        for v in ("G1", "G2", "G3"):
            for p in ("G4", "G5", "G6", "G7"):
                self.assertNotIn((v, p), m["amigos"])


if __name__ == "__main__":
    unittest.main()
