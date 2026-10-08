"""Pruebas de las correcciones de campo a la geometría OSM (config: geometria), sobre una red
sintética en metros: no necesitan data/raw/.

    python -m unittest discover -s tests -v

Red de prueba: una avenida norte–sur de un solo sentido hacia el sur que pasa por el centro, una
calle este–oeste de doble sentido y una calle que llega del noreste y se une a la avenida 50 m al
norte del centro (como la Calle 21 de Los Manguitos).
"""

import sys
import unittest
from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString, Point

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sast.semaforos import geometria as G  # noqa: E402

C = Point(0, 0)


def red(sentido_ne="Bidireccional"):
    filas = [
        # avenida: digitalizada de norte a sur (un solo sentido hacia el sur)
        {"nomencla": "AV 1", "sentido": "Unidireccional", "geometry": LineString([(0, 120), (0, 50), (0, 0), (0, -120)])},
        {"nomencla": "CL 2", "sentido": "Bidireccional", "geometry": LineString([(-120, 0), (0, 0), (120, 0)])},
        # calle del noreste, digitalizada alejándose de la avenida (al revés de como entra en campo)
        {"nomencla": "CL 3", "sentido": sentido_ne, "geometry": LineString([(0, 50), (60, 110)])},
    ]
    v = gpd.GeoDataFrame(filas, crs=9377)
    v["tipo_via"], v["carriles"], v["nombre"], v["osm_id"], v["sent_f"] = "secondary", float("nan"), None, 1, "OSM"
    return v


class Sentidos(unittest.TestCase):
    def test_entra_reorienta_hacia_el_cruce(self):
        v = G.aplicar_sentidos(red(), C, {"CL 3": "entra"}, 200)
        ne = v[v["nomencla"] == "CL 3"].iloc[0]
        self.assertEqual(ne["sentido"], "Unidireccional")
        self.assertEqual(ne["sent_f"], "corrección de campo")
        self.assertLess(Point(ne.geometry.coords[-1]).distance(C), Point(ne.geometry.coords[0]).distance(C))

    def test_no_toca_otras_vias(self):
        v = G.aplicar_sentidos(red(), C, {"CL 3": "entra"}, 200)
        self.assertEqual(v[v["nomencla"] == "CL 2"].iloc[0]["sentido"], "Bidireccional")

    def test_via_inexistente_falla(self):
        with self.assertRaises(ValueError):
            G.aplicar_sentidos(red(), C, {"CL 99": "entra"}, 200)


class Ruteo(unittest.TestCase):
    def setUp(self):
        self.v = G.aplicar_sentidos(red(), C, {"CL 3": "entra"}, 200)
        self.arms = G.brazos(C, self.v, r_conexion=55, r_dibujo=110)
        self.g = G.grafo_vial(self.v, C, 110)

    def brazo(self, nom, rumbo):
        return min((a for a in self.arms if a["nomencla"] == nom), key=lambda a: G.dif_angular(a["rumbo"], rumbo))

    def test_la_calle_del_noreste_es_brazo_solo_de_entrada(self):
        ne = self.brazo("CL 3", 45)
        self.assertTrue(any(p["entrante"] for p in ne["partes"]))
        self.assertFalse(any(p["saliente"] for p in ne["partes"]))

    def test_trayectoria_sigue_la_red_y_pare_a_distancia(self):
        ne, oeste = self.brazo("CL 3", 45), self.brazo("CL 2", 270)
        for a in self.arms:
            a["r_caja"] = 7.0
        t = G.trayectoria_red(ne, oeste, C, self.g, pare_m=70)
        self.assertIsNotNone(t)
        # pasa por el empalme con la avenida (0, 50) y por el centro, no en línea recta
        self.assertLess(t["linea"].distance(Point(0, 50)), 2.0)
        self.assertLess(t["linea"].distance(C), 4.0)
        q = t["linea"].interpolate(t["s_pare"])
        self.assertAlmostEqual(q.distance(C), 70, delta=0.5)

    def test_respeta_el_sentido_unico(self):
        # la avenida solo baja: hay arco de (0, 50) a (0, 0) y no al revés; la calle de doble sentido, ambos
        self.assertTrue(self.g.has_edge((0.0, 50.0), (0.0, 0.0)))
        self.assertFalse(self.g.has_edge((0.0, 0.0), (0.0, 50.0)))
        self.assertTrue(self.g.has_edge((0.0, 0.0), (-110.0, 0.0)) and self.g.has_edge((-110.0, 0.0), (0.0, 0.0)))


class Pare(unittest.TestCase):
    def test_s_a_distancia(self):
        ln = LineString([(0, 100), (0, 0)])
        self.assertAlmostEqual(G.s_a_distancia(ln, C, 58), 42, delta=0.3)

    def test_linea_en_es_perpendicular_y_del_ancho_pedido(self):
        a, b = G.linea_en(LineString([(0, 100), (0, 0)]), 42, 6.6)
        self.assertAlmostEqual(abs(a[0] - b[0]), 6.6, delta=0.01)
        self.assertAlmostEqual(a[1], b[1], delta=0.01)


if __name__ == "__main__":
    unittest.main()
