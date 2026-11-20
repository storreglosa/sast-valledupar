// Ubicación de las cabezas semafóricas del diagrama (Santiago, 2026-11-20): ninguna tapa a otra ni
// queda sobre la calzada, y todas caben en el recuadro.
//
// Todo va en píxeles de pantalla y como rectángulos girados:
//   { x, y, w, h, giro }      centro, ancho y alto sin girar, giro en grados (como el CSS `rotate`).
// Una cabeza trae además su posición ideal (x, y) y dos direcciones unitarias propias:
//   d   aguas arriba de su vía (vehicular) o a lo largo del andén hacia afuera del cruce (peatonal)
//   n   hacia afuera de la calzada que controla (el andén derecho; en la peatonal, más allá de la cebra);
//       −n es el andén opuesto, que se usa solo si el propio no tiene sitio
// Solo se corre a lo largo de esas dos direcciones y nunca queda sobre una calzada. Las
// calzadas son rectángulos (un tramo de vía con su ancho dibujado), obstáculos fijos.

const rad = (g) => (g * Math.PI) / 180;

function ejes(r) {
  const c = Math.cos(rad(r.giro)), s = Math.sin(rad(r.giro));
  return [[c, s], [-s, c]];
}

function proyeccion(r, a) {
  const [u, v] = ejes(r);
  const c = r.x * a[0] + r.y * a[1];
  const m = (r.w / 2) * Math.abs(u[0] * a[0] + u[1] * a[1]) + (r.h / 2) * Math.abs(v[0] * a[0] + v[1] * a[1]);
  return [c - m, c + m];
}

/** true si los rectángulos quedan a menos de `holgura` px (teorema del eje separador). */
export function seSolapan(a, b, holgura = 0) {
  for (const e of [...ejes(a), ...ejes(b)]) {
    const [a0, a1] = proyeccion(a, e), [b0, b1] = proyeccion(b, e);
    if (b0 >= a1 + holgura || a0 >= b1 + holgura) return false;
  }
  return true;
}

/** Rectángulos de calzada de una polilínea en pantalla: un rectángulo por tramo, alargado medio
 *  ancho en cada punta para tapar las uniones entre tramos. */
export function calzada(puntos, anchoPx) {
  const out = [];
  for (let i = 1; i < puntos.length; i++) {
    const [x0, y0] = puntos[i - 1], [x1, y1] = puntos[i];
    const L = Math.hypot(x1 - x0, y1 - y0);
    if (L < 0.5) continue;
    out.push({ x: (x0 + x1) / 2, y: (y0 + y1) / 2, w: L + anchoPx, h: anchoPx, giro: (Math.atan2(y1 - y0, x1 - x0) * 180) / Math.PI });
  }
  return out;
}

/** Ubica las cabezas en orden (la primera elige primero). Para cada una prueba posiciones corridas
 *  `s` px por d (negativo = hacia el cruce, por el mismo andén) y `l` px por n (negativo = andén opuesto), y
 *  toma la de menor costo que no toque calzadas, cabezas ya ubicadas ni el borde. Costo: s + l, y
 *  1,5 × |s| hacia el cruce y 3 × |l| + 60 al andén opuesto. Si no hay ninguna libre,
 *  toma la que no tape cabezas y quede más cerca, y la marca (`libre: false`): un solape sin resolver se
 *  avisa, no se esconde. */
export function ubicar(cabezas, calzadas, { W = Infinity, H = Infinity, margen = 4, holgura = 6,
  holguraVia = 2, pasoPx = 3, maxS = 160, maxL = 90 } = {}) {
  const puestas = [];
  const cabe = (r) => {
    const [x0, x1] = proyeccion(r, [1, 0]), [y0, y1] = proyeccion(r, [0, 1]);
    return x0 >= margen && y0 >= margen && x1 <= W - margen && y1 <= H - margen;
  };
  const cands = [];
  // desde 0 hacia los dos lados, para que la posición ideal (s = 0, l = 0) esté entre las candidatas.
  // l < 0 = el andén opuesto de su misma vía (o el otro extremo de la cebra): en campo también hay
  // cabezas a ese lado, pero se usa solo si el suyo no tiene sitio (costo 3 × |l| + 60)
  for (let a = 0; a <= maxS; a += pasoPx) for (const s of a ? [a, -a] : [0]) {
    for (let b = 0; b <= maxL; b += pasoPx) for (const l of b ? [b, -b] : [0]) {
      cands.push([s, l, (s < 0 ? -1.5 * s : s) + (l < 0 ? 60 - 3 * l : l)]);
    }
  }
  cands.sort((a, b) => a[2] - b[2] || a[1] - b[1] || b[0] - a[0]);
  for (const c of cabezas) {
    let elegida = null, respaldo = null, peor = Infinity;
    for (const [s, l, costo] of cands) {
      const r = { x: c.x + c.d[0] * s + c.n[0] * l, y: c.y + c.d[1] * s + c.n[1] * l, w: c.w, h: c.h, giro: c.giro };
      if (!cabe(r)) continue;
      const nCab = puestas.filter((p) => seSolapan(p, r, holgura)).length;
      const nVia = nCab ? 0 : calzadas.filter((v) => seSolapan(v, r, holguraVia)).length;
      if (!nCab && !nVia) { elegida = r; break; }
      // sin lugar libre: primero no tapar otra cabeza; después, quedarse cerca de su acceso (no saltar
      // a otra vía), y entre posiciones parecidas, la que menos tramos de calzada pise
      const choque = nCab * 1e6 + costo + nVia * 15;
      if (choque < peor) { peor = choque; respaldo = r; }
    }
    const r = elegida || respaldo || { x: c.x, y: c.y, w: c.w, h: c.h, giro: c.giro };
    puestas.push({ ...r, libre: !!elegida });
  }
  return puestas;
}
