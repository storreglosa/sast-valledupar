// Programación por hora del día: «hoy» (5 cruces × 24 h, franja del mapa) y «semana» (un cruce,
// 8 filas × 24 h). El color dice cuánto dura el ciclo (escala azul validada: más claro = ciclo más
// largo) y cada bloque lleva su etiqueta «P2 · 100 s»: la identidad nunca va solo en el color.
import { h, s, mostrarTip, ocultarTip } from '../util/dom.js';
import { DIAS, NOMBRE_DIA, hhmm, bogota, diaHorario } from '../nucleo/horario.js';

export const colorCiclo = (c) => (c <= 55 ? 'var(--ciclo-1)' : c <= 80 ? 'var(--ciclo-2)' : c <= 95 ? 'var(--ciclo-3)' : 'var(--ciclo-4)');
const tintaSobre = (c) => (c > 80 ? '#06121f' : '#e8eef2');

/**
 * filas: [{clave, etiqueta, bloques: [[ini, fin, plan]], planes, activa}]
 * Devuelve {el, ahora(minutos, claveActiva)} para mover la línea «ahora».
 */
function tira(filas, { alElegir, titulo }) {
  const raiz = h('div', { class: 'franja-cuerpo' });
  const svg = s('svg', { preserveAspectRatio: 'none', role: 'img', 'aria-label': titulo });
  const linea = h('div', { class: 'cursor', style: { background: 'var(--tinta)' } }, h('span', { class: 'cursor-burbuja num' }, ''));
  raiz.append(svg, linea);
  let geom = null;
  function dibujar() {
    const W = raiz.clientWidth - 24, H = raiz.clientHeight - 16;
    if (W <= 0 || H <= 0) return;
    const izq = Math.min(150, Math.max(78, W * 0.13));
    const alto = Math.min(26, (H - 20) / filas.length - 3);
    geom = { izq, ancho: W - izq - 4, x0: 12 + izq, alto };
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.replaceChildren();
    const xs = (m) => izq + (m / 1440) * geom.ancho;
    for (let hh = 0; hh <= 24; hh += 2) {
      svg.append(s('line', { x1: xs(hh * 60), x2: xs(hh * 60), y1: 13, y2: H, stroke: '#1a232a' }));
      if (hh < 24) svg.append(s('text', { x: xs(hh * 60) + 2, y: 10, class: 'r-num', style: 'font-size:10px' }, `${String(hh).padStart(2, '0')}:00`));
    }
    filas.forEach((f, i) => {
      const y = 16 + i * (alto + 3);
      svg.append(s('text', { x: 0, y: y + alto * 0.68, class: 'r-g', style: `font-size:11.5px;${f.activa ? 'fill:var(--tinta)' : ''}` }, f.etiqueta));
      for (const [a, b, pid] of f.bloques) {
        const p = f.planes.find((x) => x.id === pid);
        const g = s('g', { style: 'cursor:pointer' });
        g.append(s('rect', { x: xs(a) + 0.5, y, width: Math.max(1, xs(b) - xs(a) - 1.5), height: alto, rx: 2, fill: colorCiclo(p.ciclo),
          opacity: f.activa === false ? 0.55 : 1 }));
        if (xs(b) - xs(a) > 52) g.append(s('text', { x: xs(a) + 5, y: y + alto * 0.68, style: `font:700 11px var(--f-rotulo);fill:${tintaSobre(p.ciclo)}` }, `${pid} · ${p.ciclo} s`));
        else if (xs(b) - xs(a) > 20) g.append(s('text', { x: xs(a) + 3, y: y + alto * 0.68, style: `font:700 10px var(--f-rotulo);fill:${tintaSobre(p.ciclo)}` }, pid));
        g.addEventListener('pointermove', (ev) => mostrarTip(ev, `<b>${f.etiqueta}</b> · ${hhmm(a)}–${hhmm(b)}<br>${pid}: ciclo de ${p.ciclo} s <span class="t2">(${(3600 / p.ciclo).toFixed(1).replace('.', ',')} ciclos por hora)</span>`));
        g.addEventListener('pointerleave', ocultarTip);
        g.addEventListener('click', () => alElegir?.(f.clave, pid));
        svg.append(g);
      }
    });
  }
  new ResizeObserver(dibujar).observe(raiz);
  let mPrevio = -1;
  function ahora(minutos) {
    if (!geom) dibujar();
    if (!geom) return;
    const x = geom.x0 + (minutos / 1440) * geom.ancho;
    linea.style.transform = `translateX(${x}px)`;
    const m = Math.floor(minutos);
    if (m !== mPrevio) { mPrevio = m; linea.firstChild.textContent = hhmm(minutos); }
  }
  return { el: raiz, ahora, redibujar: dibujar };
}

/** Franja del mapa: la programación de hoy de los cinco cruces. */
export function hoy(sem, ms, alElegir) {
  const b = bogota(ms);
  const d = diaHorario(b);
  const filas = sem.intersecciones.map((it) => ({ clave: it.id, etiqueta: it.nombre, bloques: it.horario[d.fila], planes: it.planes }));
  const t = tira(filas, { alElegir, titulo: 'Programación de hoy de los cinco cruces' });
  t.dia = d.festivo ? `Festivo · ${d.festivo}` : NOMBRE_DIA[d.fila];
  return t;
}

/** Semana de un cruce: 8 filas (lunes … domingo y festivo). */
export function semana(it, ms, alElegir) {
  const d = diaHorario(bogota(ms));
  const filas = DIAS.map((dia) => ({ clave: dia, etiqueta: NOMBRE_DIA[dia], bloques: it.horario[dia], planes: it.planes, activa: dia === d.fila }));
  const t = tira(filas, { alElegir: (_, pid) => alElegir?.(pid), titulo: `Programación semanal de ${it.nombre}` });
  return t;
}
