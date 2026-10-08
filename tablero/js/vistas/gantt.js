// Línea de tiempo del ciclo (versión moderna del diagrama de barras del controlador): una fila por
// grupo, fila de «todo rojo», marcas cada 10 s y un cursor que avanza y se puede arrastrar.
import { h, s, mostrarTip, ocultarTip } from '../util/dom.js';
import { tramos, estado, NO_ROJO } from '../nucleo/tiempos.js';
import { nombreEstado } from './anillo.js';

export function gantt(it, { alArrastrar } = {}) {
  const raiz = h('div', { class: 'franja-cuerpo' });
  const svg = s('svg', { preserveAspectRatio: 'none', role: 'img', 'aria-label': `Línea de tiempo del ciclo de ${it.nombre}` });
  const cursor = h('div', { class: 'cursor' }, h('span', { class: 'cursor-burbuja num' }, '0 s'));
  const zona = h('div', { class: 'arrastrable', style: { position: 'absolute', inset: '0' }, 'aria-label': 'Arrastre para mover el segundo del ciclo', role: 'slider', tabindex: 0, 'aria-valuemin': 0 });
  raiz.append(svg, zona, cursor);
  let planId = null, plan = null, geom = null;

  function dibujar(p) {
    plan = p; planId = p.id;
    const c = p.ciclo;
    const W = raiz.clientWidth - 24, H = raiz.clientHeight - 16;
    if (W <= 0 || H <= 0) return;
    const izq = Math.min(170, Math.max(96, W * 0.16));
    const filas = it.grupos.length + 1;
    const alto = Math.min(22, (H - 18) / filas - 3);
    geom = { izq, ancho: W - izq - 8, x0: 12 + izq };
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.replaceChildren();
    const xs = (t) => izq + (t / c) * geom.ancho;
    for (let k = 0; k <= c; k += 5) {
      const x = xs(k);
      svg.append(s('line', { x1: x, x2: x, y1: 14, y2: H, stroke: k % 10 ? '#141b21' : '#1f2a33', 'stroke-width': 1 }));
      if (k % 10 === 0) svg.append(s('text', { x, y: 10, 'text-anchor': 'middle', class: 'r-num', style: 'font-size:10px' }, k));
    }
    it.grupos.forEach((g, i) => {
      const y = 18 + i * (alto + 3);
      svg.append(s('text', { x: 0, y: y + alto * 0.72, class: 'r-g', style: 'font-size:11px' }, `${g.id} ${g.nombre}`));
      for (const [a, b, e] of tramos(p.tiempos[g.id], g.tipo, c)) {
        const rojo = e === 'rojo' || e === 'preparacion';
        const r = s('rect', { x: xs(a), y: y + (rojo ? alto * 0.38 : 0), width: Math.max(0.5, xs(b) - xs(a) - (rojo ? 0 : 1)),
          height: rojo ? alto * 0.24 : alto, rx: rojo ? 0 : 2,
          fill: e === 'verde' ? 'var(--verde)' : e === 'amarillo' ? 'var(--ambar)' : 'var(--rojo)',
          opacity: rojo ? 0.55 : 1 });
        if (e === 'despeje') { r.setAttribute('fill', 'var(--rojo)'); r.setAttribute('class', 'parpadea'); }
        r.addEventListener('pointermove', (ev) => mostrarTip(ev, `<b>${g.id} · ${g.nombre}</b><br>${nombreEstado(e)}: ${a}–${b} s <span class="t2">(${b - a} s)</span>`));
        r.addEventListener('pointerleave', ocultarTip);
        svg.append(r);
      }
    });
    // todo rojo
    const y = 18 + it.grupos.length * (alto + 3);
    svg.append(s('text', { x: 0, y: y + alto * 0.72, class: 'r-g', style: 'font-size:11px; fill: var(--tinta-3)' }, 'Todo rojo'));
    const tipo = Object.fromEntries(it.grupos.map((g) => [g.id, g.tipo]));
    let ini = null;
    for (let k = 0; k <= c; k++) {
      const todo = k < c && Object.entries(p.tiempos).every(([gid, ti]) => !NO_ROJO.has(estado(ti, tipo[gid], k + 0.5, c)));
      if (todo && ini === null) ini = k;
      if (!todo && ini !== null) {
        svg.append(s('rect', { x: xs(ini), y: y + alto * 0.2, width: xs(k) - xs(ini) - 1, height: alto * 0.6, fill: '#c9d3da', opacity: 0.85, rx: 1 }));
        ini = null;
      }
    }
    zona.setAttribute('aria-valuemax', c);
  }

  // arrastrar el cursor = explorar ese segundo (pausado)
  let arrastrando = false;
  const tDesde = (ev) => {
    const r = raiz.getBoundingClientRect();
    const x = ev.clientX - r.left - geom.x0;
    return Math.max(0, Math.min(plan.ciclo - 0.01, (x / geom.ancho) * plan.ciclo));
  };
  zona.addEventListener('pointerdown', (ev) => { if (!geom) return; arrastrando = true; zona.setPointerCapture(ev.pointerId); alArrastrar?.(tDesde(ev), true); });
  zona.addEventListener('pointermove', (ev) => { if (arrastrando) alArrastrar?.(tDesde(ev), true); });
  zona.addEventListener('pointerup', () => { arrastrando = false; });
  zona.addEventListener('keydown', (ev) => {
    if (!plan) return;
    const actual = +zona.getAttribute('aria-valuenow') || 0;
    if (ev.key === 'ArrowRight') { alArrastrar?.((actual + 1) % plan.ciclo, true); ev.preventDefault(); }
    if (ev.key === 'ArrowLeft') { alArrastrar?.((actual - 1 + plan.ciclo) % plan.ciclo, true); ev.preventDefault(); }
  });
  new ResizeObserver(() => plan && dibujar(plan)).observe(raiz);

  let tPrevio = -1;
  function actualizar(t, p) {
    if (p.id !== planId || !geom) dibujar(p);
    if (!geom) return;
    const x = geom.x0 + (t / p.ciclo) * geom.ancho;
    cursor.style.transform = `translateX(${x}px)`;
    const ts = Math.floor(t);
    if (ts !== tPrevio) { tPrevio = ts; cursor.firstChild.textContent = `${ts} s`; zona.setAttribute('aria-valuenow', ts); }
  }
  return { el: raiz, actualizar, redibujar: () => plan && dibujar(plan) };
}
