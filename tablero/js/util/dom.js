// Ayudas mínimas de DOM y SVG.
const NS = 'http://www.w3.org/2000/svg';

export function h(tag, attrs = {}, ...hijos) {
  const el = document.createElement(tag);
  aplicar(el, attrs);
  for (const c of hijos.flat()) if (c != null && c !== false) el.append(c instanceof Node ? c : String(c));
  return el;
}

export function s(tag, attrs = {}, ...hijos) {
  const el = document.createElementNS(NS, tag);
  aplicar(el, attrs);
  for (const c of hijos.flat()) if (c != null && c !== false) el.append(c instanceof Node ? c : String(c));
  return el;
}

function aplicar(el, attrs) {
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === 'class') el.setAttribute('class', v);
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
    else if (k === 'html') el.innerHTML = v;
    else el.setAttribute(k, v === true ? '' : v);
  }
}

export const $ = (sel, raiz = document) => raiz.querySelector(sel);
export const vaciar = (el) => { while (el.firstChild) el.firstChild.remove(); return el; };

/** Arco de anillo (grados desde las 12, sentido horario) como path SVG. */
export function arco(cx, cy, r, a0, a1) {
  const rad = (a) => ((a - 90) * Math.PI) / 180;
  const p = (a) => [cx + r * Math.cos(rad(a)), cy + r * Math.sin(rad(a))];
  const [x0, y0] = p(a0), [x1, y1] = p(a1);
  const grande = a1 - a0 > 180 ? 1 : 0;
  return `M${x0.toFixed(2)} ${y0.toFixed(2)}A${r} ${r} 0 ${grande} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
}

/** Tooltip compartido. */
const tip = () => document.getElementById('tooltip');
export function mostrarTip(e, html) {
  const t = tip();
  t.innerHTML = html;
  t.hidden = false;
  const x = Math.min(e.clientX + 14, window.innerWidth - t.offsetWidth - 8);
  const y = Math.min(e.clientY + 14, window.innerHeight - t.offsetHeight - 8);
  t.style.left = `${x}px`; t.style.top = `${y}px`;
}
export const ocultarTip = () => { tip().hidden = true; };

export const reducido = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
