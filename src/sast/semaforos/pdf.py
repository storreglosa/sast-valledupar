"""Lectura de los PDF del controlador con poppler (`pdftotext`, `pdftoppm`, `pdfinfo`).

Los reportes son vectoriales: el texto trae su posición exacta en puntos (1/72 in) y los
gráficos (barras, círculos de la matriz) solo se pueden leer rasterizando la página.
"""

from __future__ import annotations

import html
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

_PALABRA = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>')


@dataclass(frozen=True)
class Palabra:
    x0: float
    y0: float
    x1: float
    y1: float
    texto: str

    @property
    def xc(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def yc(self) -> float:
        return (self.y0 + self.y1) / 2


def _correr(args: list[str]) -> str:
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{args[0]} falló ({r.returncode}): {r.stderr.strip()}")
    return r.stdout


def version_poppler() -> str:
    r = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True)
    return (r.stderr or r.stdout).splitlines()[0].strip()


def n_paginas(pdf: Path) -> int:
    m = re.search(r"^Pages:\s+(\d+)", _correr(["pdfinfo", str(pdf)]), re.M)
    if not m:
        raise RuntimeError(f"pdfinfo no reporta páginas para {pdf.name}")
    return int(m.group(1))


def palabras(pdf: Path, pagina: int) -> list[Palabra]:
    """Palabras de una página con su caja. Verifica que no se pierda ninguna al leer."""
    xml = _correr(["pdftotext", "-bbox", "-f", str(pagina), "-l", str(pagina), str(pdf), "-"])
    out = [Palabra(float(a), float(b), float(c), float(d), html.unescape(t))
           for a, b, c, d, t in _PALABRA.findall(xml)]
    esperadas = xml.count("<word ")
    if len(out) != esperadas:
        raise RuntimeError(f"{pdf.name} p. {pagina}: se leyeron {len(out)} de {esperadas} palabras")
    return out


def texto(pdf: Path, pagina: int) -> str:
    return " ".join(p.texto for p in palabras(pdf, pagina))


def imagen(pdf: Path, pagina: int, dpi: int = 144) -> Image.Image:
    """Página rasterizada en RGB. `pdftoppm` no escribe PNG a stdout: usa una carpeta temporal."""
    with tempfile.TemporaryDirectory() as td:
        _correr(["pdftoppm", "-png", "-r", str(dpi), "-f", str(pagina), "-l", str(pagina),
                 "-singlefile", str(pdf), f"{td}/p"])
        im = Image.open(f"{td}/p.png").convert("RGB")
        im.load()
    return im


def misma_linea(ps: list[Palabra], y0: float, tol: float = 1.0) -> list[Palabra]:
    return sorted((p for p in ps if abs(p.y0 - y0) <= tol), key=lambda p: p.x0)
