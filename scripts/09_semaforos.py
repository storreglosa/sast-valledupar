"""Etapa 9 — Planeamientos semafóricos de las intersecciones con SAST (decisiones 27–29).

Lee los reportes del controlador SISTRA (data/raw/semaforos/, docs/ingesta.md): resumen, matriz
de grupos amigos, tiempos de cada plan y horario semanal. Valida (conflictos entre grupos, todo
rojo, duraciones, cobertura del horario) y lista las diferencias con la tabla del correo del
29/09/2026. Es evidencia: no inventa ni corrige; lo raro se reporta.

Con la red vial OSM (data/raw/red_vial/) arma la geometría de cada cruce y un BORRADOR de qué
acceso controla cada grupo, según la codificación de trayectorias SDM (decisión 30). El borrador
lo valida Santiago en outputs/semaforos_validacion-accesos.html (decisión 28).

Salidas:
  data/processed/semaforos.json                    lo que lee 10_tablero.py
  outputs/tables/semaforos_{planes,horario,matriz,validacion,diferencias_correo,accesos_borrador}.csv
  outputs/semaforos_validacion-accesos.html        página para validar el borrador
  outputs/figures/semaforos_matriz_<id>.png        puntos muestreados de la matriz (auditoría)
  tests/fixtures/estados_referencia.json           estados por segundo (prueba Python ↔ JS)
"""

import csv
import hashlib
import json
import os
import sys
from datetime import date

import geopandas as gpd
import pandas as pd
import yaml

import _entorno  # noqa: F401
from sast.rutas import CONFIG, CRS_METRICO, DOCS, OUTPUTS, PROCESSED, RAIZ, RAW, ultimo
from sast.semaforos import correo, cruce, horario, matriz, pdf, planes, tiempos, validacion_html
from sast.semaforos.validacion import Hallazgo, validar

TABLAS = OUTPUTS / "tables"
FIGURAS = OUTPUTS / "figures"


def sha256(ruta) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def verificar_manifiesto(archivos) -> None:
    """Los insumos deben estar congelados en docs/manifiesto_raw.csv (00_manifiesto.py)."""
    if "SAST_RAW" in os.environ:
        print(f"  AVISO: SAST_RAW={RAW} (ensayo): no se verifica el manifiesto de data/raw/")
        return
    with open(DOCS / "manifiesto_raw.csv", encoding="utf-8-sig") as f:
        congelado = {r["archivo"]: r["sha256"] for r in csv.DictReader(f)}
    for ruta in archivos:
        rel = ruta.relative_to(RAW).as_posix()
        if rel not in congelado:
            raise SystemExit(f"{rel} no está en docs/manifiesto_raw.csv: corre scripts/00_manifiesto.py")
        if congelado[rel] != sha256(ruta):
            raise SystemExit(f"{rel} cambió desde que se congeló en el manifiesto")


def leer_interseccion(cfg: dict) -> dict:
    ruta = RAW / "semaforos" / cfg["archivo"]
    if not ruta.exists():
        raise SystemExit(f"Falta {ruta}. Ver docs/ingesta.md.")
    n = pdf.n_paginas(ruta)
    resumen = planes.leer_resumen(ruta)
    m = matriz.leer_matriz(ruta, 2, FIGURAS / f"semaforos_matriz_{cfg['id']}.png")
    lista, grupos = [], None
    for pag in range(3, n):
        if not planes.es_pagina_plan(pdf.palabras(ruta, pag)):
            raise SystemExit(f"{ruta.name} p. {pag}: se esperaba una página de plan")
        p, g, cruce = planes.leer_plan(ruta, pag)
        if grupos is None:
            grupos = g
        elif [(x.id, x.nombre) for x in g] != [(x.id, x.nombre) for x in grupos]:
            raise SystemExit(f"{ruta.name} p. {pag}: los grupos cambian entre planes")
        lista.append({"id": p.id, "ciclo": p.ciclo, "ciclo_crudo": p.ciclo_crudo, "pagina": pag,
                      "cruce_pie": cruce, "tiempos": p.tiempos})
    h = horario.leer_horario(ruta, n)
    return {**cfg, "ruta": ruta, "paginas": n, "resumen": resumen,
            "grupos": [{"id": g.id, "nombre": g.nombre, "tipo": g.tipo} for g in grupos],
            "matriz": m, "planes": sorted(lista, key=lambda p: int(p["id"][1:])),
            "horario": h["horario"], "leyenda": h["leyenda"],
            "leyenda_dict": [{"plan": t.plan, "inicio": t.inicio, "fin": t.fin} for t in h["leyenda"]],
            "hallazgos_horario": h["hallazgos"]}


def main() -> None:
    with open(CONFIG / "semaforos.yaml", encoding="utf-8") as f:
        conf = yaml.safe_load(f)
    archivos = [RAW / "semaforos" / c["archivo"] for c in conf["intersecciones"]]
    ruta_correo = RAW / "semaforos" / "2026-09-29_sttv_correo-planeamientos.pdf"
    verificar_manifiesto(archivos + [ruta_correo])
    if sha256(ruta_correo) != correo.leer()["sha256_pdf"]:
        raise SystemExit("El PDF del correo no es el transcrito en config/semaforos_correo.yaml")
    print(f"poppler: {pdf.version_poppler()}")

    inters = [leer_interseccion(c) for c in conf["intersecciones"]]
    hallazgos = [x for it in inters for x in validar(it)]

    # ---------------- geometría OSM y borrador de accesos (decisiones 28 y 30)
    red = ultimo(RAW / "red_vial", "*_osm_red-vial-valledupar.gpkg")
    vias = gpd.read_file(red, layer="vias").to_crs(CRS_METRICO)
    nodos = gpd.read_file(red, layer="intersecciones").to_crs(CRS_METRICO)
    eq = gpd.read_file(OUTPUTS / "capas" / "equipos_sast.geojson").to_crs(CRS_METRICO)
    print(f"red vial: {red.name}")
    for it in inters:
        cams = [{"equipo": r.equipo, "direccion_ansv": r.direccion_ansv, "x": r.geometry.x, "y": r.geometry.y}
                for r in eq[eq["equipo"].isin(it["equipos"])].itertuples()]
        it.update(cruce.armar(it, it, vias, nodos, cams))
        hallazgos += [Hallazgo(n, it["id"], "", cod, txt) for n, cod, txt in it["hallazgos"]]
    aceptadas = {(d["interseccion"], d["codigo"]) for d in conf.get("decisiones") or []}

    # ---------------- reporte en consola
    for it in inters:
        r = it["resumen"]
        print(f"\n{it['nombre']} — equipo {r['equipo']}, cruce {r['cruce']}, {len(it['grupos'])} grupos: "
              + ", ".join(f"{g['id']} {g['nombre']}" for g in it["grupos"]))
        for p in it["planes"]:
            corre = any(b[2] == p["id"] for f in it["horario"].values() for b in f)
            print(f"  {p['id']}: ciclo {p['ciclo']} s{'' if corre else '  (sin horario: no corre)'}")
    print("\nHallazgos:")
    for x in hallazgos:
        if x.nivel != "INFO":
            marca = "  (aceptado)" if (x.interseccion, x.codigo) in aceptadas else ""
            print(f"  {x.nivel:5} {x.interseccion:11} {x.plan:3} {x.codigo}: {x.texto}{marca}")
    print(f"  ({sum(x.nivel == 'INFO' for x in hallazgos)} de nivel INFO en semaforos_validacion.csv)")

    # ---------------- tablas
    filas_planes, filas_horario, filas_matriz = [], [], []
    for it in inters:
        tipo = {g["id"]: g for g in it["grupos"]}
        for p in it["planes"]:
            k = tiempos.kpis(p, it["grupos"])
            for g, t in p["tiempos"].items():
                filas_planes.append({"interseccion": it["id"], "plan": p["id"], "ciclo": p["ciclo"],
                                     "pagina": p["pagina"], "grupo": g, "nombre": tipo[g]["nombre"],
                                     "tipo": tipo[g]["tipo"], **t, "verde_s": k["verde_s"][g]})
        for d, fila in it["horario"].items():
            for a, b, pl in fila:
                filas_horario.append({"interseccion": it["id"], "dia": d, "inicio": horario._hhmm(a),
                                      "fin": horario._hhmm(b), "plan": pl})
        for (i, j), v in it["matriz"]["fraccion"].items():
            filas_matriz.append({"interseccion": it["id"], "grupo_i": i, "grupo_j": j,
                                 "amigos": v >= matriz.UMBRAL_SI, "fraccion_verde": round(v, 3)})
    TABLAS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(filas_planes).to_csv(TABLAS / "semaforos_planes.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(filas_horario).to_csv(TABLAS / "semaforos_horario.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(filas_matriz).to_csv(TABLAS / "semaforos_matriz.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([x.__dict__ for x in hallazgos]).to_csv(TABLAS / "semaforos_validacion.csv", index=False,
                                                         encoding="utf-8-sig")
    filas_borr = [{"interseccion": it["id"], "grupo": g, **{k: v for k, v in b.items()},
                   "validado": "", "observacion": ""} for it in inters for g, b in it["borrador"].items()]
    pd.DataFrame(filas_borr).to_csv(TABLAS / "semaforos_accesos_borrador.csv", index=False, encoding="utf-8-sig")
    dif = pd.DataFrame(correo.diferencias(inters))
    dif.to_csv(TABLAS / "semaforos_diferencias_correo.csv", index=False, encoding="utf-8-sig")
    print("\nDiferencias con el correo del 29/09/2026 (manda el controlador):")
    print(dif.drop(columns="decision").to_string(index=False))

    # ---------------- JSON procesado y estados de referencia
    salida = {
        "esquema": "semaforos-procesado/1",
        "generado": date.today().isoformat(),
        "poppler": pdf.version_poppler(),
        "fuente": [{"archivo": a.relative_to(RAW).as_posix(), "sha256": sha256(a)} for a in archivos],
        "intersecciones": [],
    }
    referencia = {}
    for it in inters:
        ids = [g["id"] for g in it["grupos"]]
        amigos = sorted([i, j] for i, j in it["matriz"]["amigos"] if ids.index(i) < ids.index(j))
        tipo = {g["id"]: g["tipo"] for g in it["grupos"]}
        planes_json = []
        for p in it["planes"]:
            planes_json.append({
                "id": p["id"], "ciclo": p["ciclo"], "pagina": p["pagina"],
                "con_horario": any(b[2] == p["id"] for f in it["horario"].values() for b in f),
                "tiempos": p["tiempos"], "kpis": tiempos.kpis(p, it["grupos"]),
                "etapas": tiempos.etapas(p, it["grupos"])})
            referencia.setdefault(it["id"], {})[p["id"]] = {
                "ciclo": p["ciclo"],
                "estados": {g: tiempos.cadena(t, tipo[g], p["ciclo"]) for g, t in p["tiempos"].items()}}
        salida["intersecciones"].append({
            "id": it["id"], "nombre": it["nombre"], "archivo": it["archivo"], "solicitud": it["solicitud"],
            "equipos": it["equipos"], "controlador": it["resumen"],
            "cruce_pie": it["planes"][0]["cruce_pie"], "grupos": it["grupos"], "amigos": amigos,
            "planes": planes_json, "horario": it["horario"], "leyenda": it["leyenda_dict"],
            "geometria": it["geometria"], "borrador": it["borrador"]})
    PROCESSED.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED / "semaforos.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)
    fx = RAIZ / "tests" / "fixtures"
    fx.mkdir(parents=True, exist_ok=True)
    with open(fx / "estados_referencia.json", "w", encoding="utf-8") as f:
        json.dump({"leyenda": tiempos.CODIGO, "intersecciones": referencia}, f, ensure_ascii=False, indent=1)
    por_inter = {}
    for x in hallazgos:
        por_inter.setdefault(x.interseccion, []).append((x.nivel, f"{x.plan + ': ' if x.plan else ''}{x.texto}"))
    validacion_html.escribir(salida, dif, por_inter, OUTPUTS / "semaforos_validacion-accesos.html", FIGURAS)
    print(f"\nEscrito data/processed/semaforos.json ({len(inters)} intersecciones) y tablas en outputs/tables/")

    errores = [x for x in hallazgos if x.nivel == "ERROR" and (x.interseccion, x.codigo) not in aceptadas]
    if errores:
        sys.exit(f"{len(errores)} hallazgos de nivel ERROR sin decisión en config/semaforos.yaml")


if __name__ == "__main__":
    main()
