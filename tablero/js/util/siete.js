// Display LED de 7 segmentos en SVG (como los contadores regresivos de los semáforos de campo).
import { s } from './dom.js';

// segmentos de un dígito de 10 × 18 (a arriba, b arriba-der, c abajo-der, d abajo, e abajo-izq, f arriba-izq, g centro)
const SEG = {
  a: '1.6,0.6 8.4,0.6 7.2,1.9 2.8,1.9',
  b: '8.9,1.1 8.9,8.4 7.8,9.0 7.6,2.4',
  c: '8.9,9.6 8.9,16.9 7.6,15.6 7.8,10.2',
  d: '2.8,16.1 7.2,16.1 8.4,17.4 1.6,17.4',
  e: '1.1,9.6 2.2,10.2 2.4,15.6 1.1,16.9',
  f: '1.1,1.1 2.4,2.4 2.2,8.0 1.1,8.4',
  g: '2.2,8.4 7.8,8.4 8.6,9.0 7.8,9.6 2.2,9.6 1.4,9.0',
};
const DIGITO = { 0: 'abcdef', 1: 'bc', 2: 'abdeg', 3: 'abcdg', 4: 'bcfg', 5: 'acdfg', 6: 'acdefg', 7: 'abc',
  8: 'abcdefg', 9: 'abcdfg', '-': 'g', ' ': '' };

/**
 * Crea un display de `n` posiciones. El patrón puede llevar ':' (dos puntos fijos).
 * Devuelve {el, poner(texto, color)}; solo toca el DOM cuando cambia algo.
 */
export function display(patron, { alto = 18 } = {}) {
  const pos = [];
  let x = 0;
  const g = s('g');
  for (const ch of patron) {
    if (ch === ':') {
      const dp = s('g', { class: 'dp' }, s('rect', { x: x + 0.6, y: 5, width: 1.8, height: 1.8, rx: 0.4 }),
        s('rect', { x: x + 0.6, y: 11.2, width: 1.8, height: 1.8, rx: 0.4 }));
      g.append(dp); pos.push({ tipo: ':', el: dp }); x += 3.2;
    } else {
      const d = s('g', { transform: `translate(${x} 0) skewX(-6)` });
      const segs = {};
      for (const [k, pts] of Object.entries(SEG)) { segs[k] = s('polygon', { points: pts }); d.append(segs[k]); }
      g.append(d); pos.push({ tipo: 'd', segs }); x += 11.2;
    }
  }
  const ancho = x - 1.2;
  const el = s('svg', { viewBox: `-0.5 0 ${ancho + 1} 18`, height: alto, class: 'siete', 'aria-hidden': 'true' }, g);
  let previo = '', colorPrevio = '';
  function poner(texto, color = 'var(--rojo)', apagado = null) {
    texto = String(texto);
    if (texto === previo && color === colorPrevio) return;
    previo = texto; colorPrevio = color;
    const off = apagado || `color-mix(in srgb, ${color} 9%, #0a0d10)`;
    const chars = [...texto].filter((c) => c !== ':');
    let i = 0;
    for (const p of pos) {
      if (p.tipo === ':') { p.el.setAttribute('fill', color); continue; }
      const c = chars[i++] ?? ' ';
      const on = DIGITO[c] ?? '';
      for (const [k, seg] of Object.entries(p.segs)) seg.setAttribute('fill', on.includes(k) ? color : off);
    }
    el.style.filter = `drop-shadow(0 0 3px color-mix(in srgb, ${color} 55%, transparent))`;
  }
  return { el, poner };
}
