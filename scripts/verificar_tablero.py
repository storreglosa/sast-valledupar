"""Guardia de publicación del tablero (corre en GitHub Actions antes de desplegar Pages).

Solo usa la biblioteca estándar. Falla (código 1) si:
- en `tablero/` hay archivos de tipos no previstos;
- los JSON de `tablero/data/` no traen el esquema esperado o llevan claves fuera de la lista blanca;
- alguna asignación grupo -> acceso está en «borrador» (decisión 28: solo se publica validada);
- algún texto o número parece placa, cédula o correo (decisión 26 y regla de datos sensibles): en
  los JSON de datos se revisan todas las cadenas y los enteros; en el resto de archivos de texto de
  `tablero/` (HTML, JS, CSS, MD, SVG), salvo las librerías de `vendor/`, correos, cédulas con puntos
  y placas en mayúsculas.
"""

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TABLERO = RAIZ / "tablero"
TIPOS = {".html", ".css", ".js", ".mjs", ".json", ".svg", ".txt", ".md"}
ESQUEMAS = {"semaforos.json": "tablero-semaforos/1", "geometria.json": "tablero-geometria/1", "sast.json": "tablero-sast/1"}
CLAVES = {
    "semaforos.json": {"esquema", "generado", "zona_horaria", "nota_fase", "nota_vehiculos", "fuente", "intersecciones",
                       "id", "nombre", "direccion", "controlador", "equipo", "cruce", "cruce_pie", "equipos", "centro", "lon", "lat",
                       "grupos", "tipo", "mov", "codigo", "movimiento", "acceso", "sale_por", "brazo", "mitad", "via",
                       "amigos", "planes", "ciclo", "con_horario", "tiempos", "tira", "tiv", "tfv", "tfa", "kpis",
                       "ciclos_hora", "verde_s", "verde_pct", "rojo_s", "todo_rojo_s", "etapas", "inicio", "fin",
                       "duracion", "verdes", "horario", "asignacion", "estado", "validado_por", "fecha", "crs", "confirmada"},
    "geometria.json": {"esquema", "unidad", "crs_origen", "atribucion", "intersecciones", "norte", "vias", "p", "ancho",
                       "unico", "ctx", "n", "brazos", "id", "cardinal", "rumbo", "nomencla", "r_caja", "cajon", "cebras",
                       "grupo", "codigo", "poligono", "eje", "pare", "trayectorias", "puntos", "s_pare", "largo",
                       "camaras", "equipo", "x", "y", "vista", "r", "otras"},
    "sast.json": {"esquema", "criterio", "cortes", "siniestros", "comparendos", "version", "salvedades", "infracciones",
                  "equipos", "type", "features", "geometry", "coordinates", "properties", "equipo", "numero",
                  "solicitud", "punto", "direccion", "direccion_ansv", "estado", "fecha_inicio", "codigo_unico",
                  "solicitud_ansv", "codigos", "semaforo", "linea_base", "ventana", "inicio", "fallecidos",
                  "lesionados", "codigo", "total", "agente", "foto_previa", "total_comparendos"},
}
# claves que son identificadores dinámicos (grupos, planes, equipos, códigos de infracción); los
# ids de cruce se toman de semaforos.json y los días son fijos: ninguna otra clave pasa
DINAMICAS = re.compile(r"^(G\d+|P\d+|EQUIPO\d{3}|[A-Z]\d{2}|sin_semaforo_\w+)$")
DIAS = {"lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo", "festivo"}
PLACA = re.compile(r"\b[A-Za-z]{3}\s?-?\d{3}\b|\b[A-Za-z]{3}\d{2}[A-Za-z]\b")
CEDULA = re.compile(r"\b\d{1,3}(\.\d{3}){2,3}\b|\b\d{6,10}\b")
# en código y páginas: placas en mayúsculas (no colores #ffb000) y cédulas con puntos
PLACA_TEXTO = re.compile(r"(?<![#\w])[A-Z]{3}\s?-?\d{3}\b|(?<![#\w])[A-Z]{3}\d{2}[A-Z]\b")
CEDULA_TEXTO = re.compile(r"\b\d{1,3}(\.\d{3}){2,3}\b")
TEXTO = {".html", ".css", ".js", ".mjs", ".md", ".svg", ".txt"}
CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PERMITIDOS = re.compile(r"^(CU\d{12}|SOL\d{10})$")   # códigos de la plataforma ANSV


def claves(o, ruta=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k, ruta
            yield from claves(v, f"{ruta}.{k}")
    elif isinstance(o, list):
        for v in o:
            yield from claves(v, ruta)


def numeros(o, ruta=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from numeros(v, f"{ruta}.{k}")
    elif isinstance(o, list):
        for v in o:
            yield from numeros(v, ruta)
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield ruta, o


def textos(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from textos(v)
    elif isinstance(o, list):
        for v in o:
            yield from textos(v)
    elif isinstance(o, str):
        yield o


def main(tablero: Path = TABLERO) -> int:
    errores = []
    for p in tablero.rglob("*"):
        if p.is_file() and p.suffix.lower() not in TIPOS:
            errores.append(f"tipo no previsto: {p.relative_to(tablero)}")
    try:
        ids = {it["id"] for it in json.loads((tablero / "data" / "semaforos.json").read_text(encoding="utf-8"))["intersecciones"]}
    except (OSError, KeyError, ValueError):
        ids = set()
    for nombre, esquema in ESQUEMAS.items():
        ruta = tablero / "data" / nombre
        if not ruta.exists():
            errores.append(f"falta data/{nombre}")
            continue
        d = json.loads(ruta.read_text(encoding="utf-8"))
        if d.get("esquema") != esquema:
            errores.append(f"{nombre}: esquema {d.get('esquema')!r}, se esperaba {esquema!r}")
        fuera = {k for k, _ in claves(d)
                 if k not in CLAVES[nombre] and k not in DIAS and k not in ids and not DINAMICAS.match(k)}
        if fuera:
            errores.append(f"{nombre}: claves fuera de la lista blanca: {sorted(fuera)}")
        for t in textos(d):
            for patron, que in ((PLACA, "placa"), (CEDULA, "cédula"), (CORREO, "correo")):
                for m in patron.finditer(t):
                    if not PERMITIDOS.match(m.group(0)):
                        errores.append(f"{nombre}: posible {que} «{m.group(0)}» en «{t[:60]}»")
        for r, n in numeros(d):     # una cédula también puede venir como número
            if float(n).is_integer() and abs(n) >= 100_000:
                errores.append(f"{nombre}: número de {len(str(int(abs(n))))} cifras en {r} (¿cédula?)")
        if nombre == "semaforos.json":
            for it in d["intersecciones"]:
                if it["asignacion"]["estado"] == "borrador":
                    errores.append(f"{it['id']}: asignación en borrador (corre 10_tablero.py sin --borrador)")
    for p in tablero.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in TEXTO or "vendor" in p.relative_to(tablero).parts:
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        for patron, que in ((PLACA_TEXTO, "placa"), (CEDULA_TEXTO, "cédula"), (CORREO, "correo")):
            for m in patron.finditer(t):
                errores.append(f"{p.relative_to(tablero)}: posible {que} «{m.group(0)}»")
    for e in errores:
        print(f"ERROR {e}")
    print("tablero publicable" if not errores else f"{len(errores)} problemas: no se publica")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
