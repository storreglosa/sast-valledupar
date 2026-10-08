"""Guardia de publicación del tablero (corre en GitHub Actions antes de desplegar Pages).

Solo usa la biblioteca estándar. Falla (código 1) si:
- en `tablero/` hay archivos de tipos no previstos;
- los JSON de `tablero/data/` no traen el esquema esperado o llevan claves fuera de la lista blanca;
- alguna asignación grupo -> acceso está en «borrador» (decisión 28: solo se publica validada);
- algún texto parece placa, cédula o correo (decisión 26 y regla de datos sensibles).
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
                       "duracion", "verdes", "horario", "asignacion", "estado", "validado_por", "fecha"},
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
# claves que son identificadores dinámicos (ids de cruce, grupos, equipos, códigos, días)
DINAMICAS = re.compile(r"^(G\d+|P\d+|EQUIPO\d{3}|[A-Z]\d{2}|[a-z-]+|sin_semaforo_\w+)$")
PLACA = re.compile(r"\b[A-Z]{3}\s?-?\d{3}\b|\b[A-Z]{3}\d{2}[A-Z]\b")
CEDULA = re.compile(r"\b\d{1,3}(\.\d{3}){2,3}\b|\b\d{8,10}\b")
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


def textos(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from textos(v)
    elif isinstance(o, list):
        for v in o:
            yield from textos(v)
    elif isinstance(o, str):
        yield o


def main() -> int:
    errores = []
    for p in TABLERO.rglob("*"):
        if p.is_file() and p.suffix.lower() not in TIPOS:
            errores.append(f"tipo no previsto: {p.relative_to(RAIZ)}")
    for nombre, esquema in ESQUEMAS.items():
        ruta = TABLERO / "data" / nombre
        if not ruta.exists():
            errores.append(f"falta {ruta.relative_to(RAIZ)}")
            continue
        d = json.loads(ruta.read_text(encoding="utf-8"))
        if d.get("esquema") != esquema:
            errores.append(f"{nombre}: esquema {d.get('esquema')!r}, se esperaba {esquema!r}")
        fuera = {k for k, _ in claves(d) if k not in CLAVES[nombre] and not DINAMICAS.match(k)}
        if fuera:
            errores.append(f"{nombre}: claves fuera de la lista blanca: {sorted(fuera)}")
        for t in textos(d):
            for patron, que in ((PLACA, "placa"), (CEDULA, "cédula"), (CORREO, "correo")):
                for m in patron.finditer(t):
                    if not PERMITIDOS.match(m.group(0)):
                        errores.append(f"{nombre}: posible {que} «{m.group(0)}» en «{t[:60]}»")
        if nombre == "semaforos.json":
            for it in d["intersecciones"]:
                if it["asignacion"]["estado"] == "borrador":
                    errores.append(f"{it['id']}: asignación en borrador (corre 10_tablero.py sin --borrador)")
    for e in errores:
        print(f"ERROR {e}")
    print("tablero publicable" if not errores else f"{len(errores)} problemas: no se publica")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
