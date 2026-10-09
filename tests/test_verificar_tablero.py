"""Pruebas de la guardia de publicación (scripts/verificar_tablero.py) con datos personales inyectados
en una copia del tablero. Son los casos con los que el revisor-datos mostró que la guardia anterior
dejaba pasar todo (2026-10-09).

    python -m unittest discover -s tests -v
"""

import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("verificar_tablero", RAIZ / "scripts" / "verificar_tablero.py")
guardia = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guardia)


class Guardia(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.tablero = self.tmp / "tablero"
        shutil.copytree(RAIZ / "tablero", self.tablero, ignore=shutil.ignore_patterns("vendor"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def correr(self):
        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = guardia.main(self.tablero)
        return codigo, salida.getvalue()

    def editar_sast(self, f):
        ruta = self.tablero / "data" / "sast.json"
        d = json.loads(ruta.read_text(encoding="utf-8"))
        f(d)
        ruta.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")

    def test_el_tablero_actual_es_publicable(self):
        codigo, salida = self.correr()
        self.assertEqual(codigo, 0, salida)

    def test_cedula_como_numero(self):
        self.editar_sast(lambda d: d["equipos"]["features"][0]["properties"].update(total=1065123456))
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1)
        self.assertIn("cédula", salida)

    def test_clave_nueva_en_minusculas_no_pasa(self):
        self.editar_sast(lambda d: d.update(victima="Juan Pérez Gómez"))
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1)
        self.assertIn("victima", salida)

    def test_placa_en_minusculas_en_datos(self):
        self.editar_sast(lambda d: d["salvedades"].append("vehículo abc123 involucrado"))
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1)
        self.assertIn("placa", salida)

    def test_datos_personales_en_la_pagina(self):
        html = self.tablero / "index.html"
        html.write_text(html.read_text(encoding="utf-8")
                        + "<!-- contacto: alguien@correo.com, CC 1.065.123.456, placa ABC123 -->", encoding="utf-8")
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1)
        for que in ("correo", "cédula", "placa"):
            self.assertIn(que, salida)


if __name__ == "__main__":
    unittest.main()
