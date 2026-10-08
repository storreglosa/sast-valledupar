// Reloj del ciclo: un anillo por grupo (exterior = G1), 0 s a las 12 y sentido horario.
// Verde, amarillo y el rojo atenuado se leen también por forma: el amarillo va rayado, el despeje
// peatonal punteado y la etiqueta de cada anillo nombra el grupo. Una aguja barre el ciclo y las
// «cuentas» LED que viajan sobre ella muestran la luz actual de cada grupo.
import { s, arco, mostrarTip, ocultarTip } from '../util/dom.js';
import { display } from '../util/siete.js';
import { estado, luz, tramos, restanteVisible } from '../nucleo/tiempos.js';

const COLOR = { verde: 'var(--verde)', amarillo: 'var(--ambar)', despeje: 'var(--rojo)', preparacion: 'var(--rojo)', rojo: 'var(--rojo)' };
let uid = 0;

export function anillo(it, { tam = 'completo', fases = null } = {}) {
  const id = `an${uid++}`;
  const completo = tam === 'completo';
  const grupos = it.grupos;
  const n = grupos.length;
  const R0 = completo ? 132 : 140;
  const w = completo ? Math.min(13, 92 / n) : Math.min(17, 104 / n);
  const gap = completo ? 3.5 : 2.5;
  const radio = (i) => R0 - i * (w + gap);
  const vb = completo ? 178 : 152;

  const defs = s('defs', {},
    s('pattern', { id: `${id}-raya`, width: 4, height: 4, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' },
      s('rect', { width: 4, height: 4, fill: 'var(--ambar)' }), s('rect', { width: 1.4, height: 4, fill: 'rgba(0,0,0,.45)' })));
  // Tres capas: arcos (quietos, se pintan una vez), aguja y cuentas (giran con CSS en el
  // compositor, sin repintar) y centro (cambia una vez por segundo).
  const capaArcos = s('g');
  const capaMarcas = s('g', { class: 'marcas' });
  const aguja = s('g', {},
    s('line', { x1: 0, y1: completo ? -(radio(n - 1) - w) : 0, x2: 0, y2: -(R0 + (completo ? 12 : 6)), stroke: '#fff', 'stroke-width': completo ? 2.4 : 4, 'stroke-linecap': 'round', opacity: 0.95 }),
    ...(completo ? [] : [s('circle', { r: 7, fill: '#fff' })]));
  const halos = grupos.map((_, i) => s('circle', { cx: 0, cy: -radio(i), r: w * 1.15, fill: 'var(--rojo)', opacity: 0.28 }));
  const cuentas = grupos.map((_, i) => s('circle', { cx: 0, cy: -radio(i), r: w * 0.62, fill: 'var(--rojo)' }));
  const centro = s('g');
  const vista = { viewBox: `${-vb} ${-vb} ${2 * vb} ${2 * vb}` };
  const svgArcos = s('svg', vista, defs, capaMarcas, capaArcos);
  // en el reloj grande la aguja es un solo trazo (las cabezas ya muestran cada luz); en los mini, cuentas LED
  const svgMovil = s('svg', { ...vista, class: 'movil', 'aria-hidden': 'true' }, ...(completo ? [] : [...halos, ...cuentas]), aguja);
  const svgCentro = s('svg', { ...vista, 'aria-hidden': 'true' }, centro);
  const svg = document.createElement('div');
  svg.className = `anillo ${tam}`;
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', `Reloj del ciclo de ${it.nombre}`);
  svg.append(svgArcos, svgMovil, svgCentro);

  let disp = null, txtSub = null;
  if (completo) {
    disp = display('000', { alto: 40 });
    const fo = s('g', { transform: 'translate(-26 -36)' });
    disp.el.setAttribute('width', 52); disp.el.setAttribute('height', 40);
    fo.append(disp.el);
    txtSub = s('text', { y: 22, 'text-anchor': 'middle', class: 'r-sub' }, 's del ciclo');
    centro.append(s('circle', { r: radio(n - 1) - w / 2 - 6, fill: 'rgba(5,7,10,.65)' }), fo, txtSub);
  }

  let planId = null, estados = [];
  function dibujar(plan) {
    planId = plan.id;
    const c = plan.ciclo;
    capaArcos.replaceChildren();
    capaMarcas.replaceChildren();
    grupos.forEach((g, i) => {
      const r = radio(i);
      capaArcos.append(s('circle', { r, fill: 'none', stroke: '#141c22', 'stroke-width': w }));
      for (const [a, b, e] of tramos(plan.tiempos[g.id], g.tipo, c)) {
        const a0 = (a / c) * 360, a1 = (b / c) * 360 - (completo ? 0.6 : 0);
        const attrs = { d: arco(0, 0, r, a0, Math.max(a0 + 0.1, a1)), fill: 'none', 'stroke-width': w, class: `arc ${e}` };
        if (e === 'verde') attrs.stroke = 'var(--verde)';
        else if (e === 'amarillo') attrs.stroke = `url(#${id}-raya)`;
        else if (e === 'despeje') Object.assign(attrs, { stroke: 'var(--rojo)', 'stroke-dasharray': '1.6 2.2' });
        else Object.assign(attrs, { stroke: 'var(--rojo)', 'stroke-opacity': completo ? 0.26 : 0.32 });
        const p = s('path', attrs);
        if (completo) {
          p.addEventListener('pointermove', (ev) => mostrarTip(ev, `<b>${g.id} · ${g.nombre}</b><br>${nombreEstado(e)} de ${a} a ${b} s <span class="t2">(${b - a} s)</span>`));
          p.addEventListener('pointerleave', ocultarTip);
        }
        capaArcos.append(p);
      }
      if (completo) {
        capaMarcas.append(s('text', { x: -6, y: -r + 3.5, 'text-anchor': 'end', class: 'r-g' }, g.id));
      }
    });
    if (completo) {
      for (let k = 0; k < c; k += 10) {
        const a = ((k / c) * 360 - 90) * Math.PI / 180;
        const r1 = R0 + w / 2 + 3, r2 = r1 + (k % 30 === 0 ? 7 : 4);
        capaMarcas.append(s('line', { x1: r1 * Math.cos(a), y1: r1 * Math.sin(a), x2: r2 * Math.cos(a), y2: r2 * Math.sin(a), stroke: '#3a4752', 'stroke-width': 1.2 }));
        if (k % 20 === 0 && k > 0) capaMarcas.append(s('text', { x: (r2 + 9) * Math.cos(a), y: (r2 + 9) * Math.sin(a) + 3.5, 'text-anchor': 'middle', class: 'r-num' }, k));
      }
      (fases ? fases(plan) : []).forEach((f) => {
        if (f.tipo === 'cambio') return;
        const a = ((f.inicio / c) * 360 - 90) * Math.PI / 180;
        const r1 = R0 + w / 2 + 2, r2 = R0 + w / 2 + 16;
        capaMarcas.append(s('line', { x1: r1 * Math.cos(a), y1: r1 * Math.sin(a), x2: r2 * Math.cos(a), y2: r2 * Math.sin(a), stroke: 'var(--tinta-2)', 'stroke-width': 1.6 }));
      });
      if (window.gsap && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        const tw = window.gsap.fromTo(capaArcos, { opacity: 0, scale: 0.94, transformOrigin: '0 0' }, { opacity: 1, scale: 1, duration: 0.5, ease: 'expo.out' });
        setTimeout(() => tw.progress(1), 1500);
      }
    }
    estados = [];
  }

  function actualizar(t, plan, focoId = null) {
    if (plan.id !== planId) dibujar(plan);
    const c = plan.ciclo;
    svgMovil.style.transform = `rotate(${((t / c) * 360).toFixed(2)}deg)`;
    grupos.forEach((g, i) => {
      const e = luz(estado(plan.tiempos[g.id], g.tipo, t, c));
      if (estados[i] !== e) {
        estados[i] = e;
        cuentas[i].setAttribute('fill', COLOR[e]); halos[i].setAttribute('fill', COLOR[e]);
        cuentas[i].classList.toggle('parpadea', e === 'despeje');
        halos[i].setAttribute('opacity', e === 'rojo' ? 0.18 : 0.34);
      }
    });
    if (disp) {
      const g = grupos.find((x) => x.id === focoId);
      if (g) {
        const e = luz(estado(plan.tiempos[g.id], g.tipo, t, c));
        disp.poner(String(Math.ceil(restanteVisible(plan.tiempos[g.id], g.tipo, t, c) - 1e-9)).padStart(3, ' '), COLOR[e]);
        txtSub.textContent = `${g.id}: ${nombreEstado(e).toLowerCase()} por`;
      } else {
        disp.poner(String(Math.floor(t)).padStart(3, ' '), '#e8eef2');
        txtSub.textContent = 's del ciclo';
      }
    }
  }
  return { el: svg, actualizar };
}

export const nombreEstado = (e) => ({ verde: 'Verde', amarillo: 'Amarillo', despeje: 'Despeje (rojo intermitente)',
  preparacion: 'Rojo (preparación)', rojo: 'Rojo' }[e]);
