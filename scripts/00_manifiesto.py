"""Congela el SHA-256 de los insumos de `data/raw/` en `docs/manifiesto_raw.csv`.

La primera vez que aparece un archivo se registra; después se exige que no cambie. Si un
insumo cambia a propósito (nuevo corte), se agrega con otro nombre (la fecha va en el nombre)
y el anterior se conserva.
"""

import csv
import hashlib
from datetime import date

import _entorno  # noqa: F401
from sast.rutas import DOCS, RAW

REGISTRO = DOCS / "manifiesto_raw.csv"


def sha256(ruta) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def main() -> None:
    archivos = sorted(p for p in RAW.rglob("*") if p.is_file() and p.name != ".gitkeep")
    if not archivos:
        raise SystemExit("data/raw/ está vacío. Ver docs/ingesta.md.")
    congelado = {}
    if REGISTRO.exists():
        with open(REGISTRO, encoding="utf-8-sig") as f:
            congelado = {r["archivo"]: r for r in csv.DictReader(f)}
    filas, cambiados, nuevos = [], [], []
    for p in archivos:
        rel = p.relative_to(RAW).as_posix()
        h = sha256(p)
        previo = congelado.get(rel)
        if previo is None:
            nuevos.append(rel)
            filas.append({"archivo": rel, "sha256": h, "bytes": p.stat().st_size,
                          "congelado": date.today().isoformat()})
        else:
            if previo["sha256"] != h:
                cambiados.append(rel)
            filas.append(previo)
    faltan = sorted(set(congelado) - {f["archivo"] for f in filas})
    if cambiados:
        raise SystemExit("Cambió el contenido de: " + ", ".join(cambiados)
                         + ". Un insumo nuevo va con otro nombre (fecha de corte).")
    for rel in faltan:
        print(f"  AVISO: {rel} está en el manifiesto pero no en data/raw/")
        filas.append(congelado[rel])
    with open(REGISTRO, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["archivo", "sha256", "bytes", "congelado"])
        w.writeheader()
        w.writerows(sorted(filas, key=lambda r: r["archivo"]))
    print(f"{len(archivos)} archivos verificados; {len(nuevos)} nuevos registrados.")
    for rel in nuevos:
        print(f"  + {rel}")


if __name__ == "__main__":
    main()
