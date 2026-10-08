"""Matriz de grupos amigos (p. 2): un círculo verde en la celda (i, j) = los grupos i y j pueden
estar en verde a la vez. Los círculos son gráficos, no texto: se rasteriza la página y se mide
la fracción de píxeles verdes en el centro de cada celda.

El centro de cada celda sale de los rótulos «Gn» (columna: x del rótulo + 15 pt; fila: y del
rótulo + 18 pt; celdas de 50 pt, círculos de ~20 pt de radio). Se muestrea un cuadro de 16 pt.
Una celda con fracción intermedia es ambigua y se reporta como error, nunca se adivina.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from sast.semaforos.pdf import imagen, palabras

DPI = 144
DX, DY, MEDIO = 15.0, 18.0, 8.0
UMBRAL_SI, UMBRAL_NO = 0.30, 0.08


def _verde(rgb) -> bool:
    r, g, b = rgb
    return g > 120 and r < 100 and b < 100


def leer_matriz(pdf: Path, pagina: int = 2, figura: Path | None = None) -> dict:
    ps = palabras(pdf, pagina)
    rotulos = [p for p in ps if p.texto.startswith("G") and p.texto[1:].isdigit()]
    y_cols = min(p.y0 for p in rotulos)
    cols = sorted((p for p in rotulos if abs(p.y0 - y_cols) < 1), key=lambda p: p.x0)
    x_filas = min(p.x0 for p in rotulos)
    filas = sorted((p for p in rotulos if abs(p.x0 - x_filas) < 1), key=lambda p: p.y0)
    if [p.texto for p in cols] != [p.texto for p in filas]:
        raise ValueError(f"{pdf.name}: rótulos de filas y columnas no coinciden")
    ids = [p.texto for p in cols]

    im = imagen(pdf, pagina, DPI)
    k = DPI / 72
    fraccion, ambiguas = {}, []
    for f in filas:
        for c in cols:
            xc, yc = c.x0 + DX, f.y0 + DY
            caja = [(x, y) for x in range(int((xc - MEDIO) * k), int((xc + MEDIO) * k))
                    for y in range(int((yc - MEDIO) * k), int((yc + MEDIO) * k))]
            v = sum(_verde(im.getpixel(px)) for px in caja) / len(caja)
            fraccion[(f.texto, c.texto)] = v
            if UMBRAL_NO < v < UMBRAL_SI:
                ambiguas.append((f.texto, c.texto, round(v, 2)))

    if figura is not None:
        _figura(im, filas, cols, fraccion, k, figura)
    amigos = {(i, j) for (i, j), v in fraccion.items() if v >= UMBRAL_SI}
    return {"grupos": ids, "amigos": amigos, "fraccion": fraccion, "ambiguas": ambiguas}


def _figura(im: Image.Image, filas, cols, fraccion, k, destino: Path) -> None:
    """Copia recortada de la matriz con los puntos muestreados: verde = amigo, rojo = no."""
    im = im.copy()
    d = ImageDraw.Draw(im)
    for f in filas:
        for c in cols:
            xc, yc = (c.x0 + DX) * k, (f.y0 + DY) * k
            color = (0, 160, 0) if fraccion[(f.texto, c.texto)] >= UMBRAL_SI else (220, 0, 0)
            r = MEDIO * k
            d.rectangle([xc - r, yc - r, xc + r, yc + r], outline=color, width=3)
    x1 = (cols[-1].x0 + 60) * k
    y1 = (filas[-1].y0 + 60) * k
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.crop((int(80 * k), int(80 * k), int(x1), int(y1))).save(destino)
