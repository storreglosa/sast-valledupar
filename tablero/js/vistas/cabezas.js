// Cabezas semafóricas: vehicular (tres lentes), peatonal (figura quieta / caminando) y flecha, con
// el contador regresivo que tienen las cinco intersecciones en campo (decisión 29).
import { h } from '../util/dom.js';
import { display } from '../util/siete.js';

const PICTO = {
  quieto: '<svg viewBox="0 0 12 12"><circle cx="6" cy="1.7" r="1.5"/><path d="M4 4h4v4.2H7.3V12H6.4V8.4h-.8V12h-.9V8.2H4z"/></svg>',
  camina: '<svg viewBox="0 0 12 12"><circle cx="6.6" cy="1.6" r="1.5"/><path d="M5.2 3.6l2.1.2 1.5 2.2 1.6.6-.3.8-2-.7-.7-1-.4 2 1.6 1.7.5 2.6-.9.2-.6-2.3-1.6-1.4-.8 1.8-1.9 2-.7-.6 1.7-1.9 1-3.4-.9.6-.5 1.7-.9-.2.7-2.2z"/></svg>',
  flecha: '<svg viewBox="0 0 12 12"><path d="M1.5 5.2h6V2.6L11 6l-3.5 3.4V6.8h-6z"/></svg>',
};
export const PALABRA = { verde: 'SIGA', amarillo: 'PREVENCIÓN', rojo: 'PARE', despeje: 'NO INICIE' };
const COLOR = { verde: 'var(--verde)', amarillo: 'var(--ambar)', rojo: 'var(--rojo)', despeje: 'var(--rojo)' };

export function cabeza(g) {
  const peat = g.tipo === 'peatonal';
  const lentes = peat
    ? { rojo: h('div', { class: 'lente r peat', html: PICTO.quieto }), verde: h('div', { class: 'lente v peat', html: PICTO.camina }) }
    : { rojo: h('div', { class: 'lente r' }), amarillo: h('div', { class: 'lente a' }),
      verde: h('div', { class: `lente v${g.tipo === 'flecha' ? ' peat' : ''}`, html: g.tipo === 'flecha' ? PICTO.flecha : '' }) };
  const caja = h('div', { class: 'cab-caja' }, ...Object.values(lentes));
  const cuenta = display('00', { alto: 15 });
  const el = h('div', { class: 'cab-cuerpo' }, caja, h('div', { class: 'cab-cuenta' }, cuenta.el));
  let previo = null;
  function actualizar(luz, segundos) {
    if (luz !== previo) {
      previo = luz;
      for (const l of Object.values(lentes)) l.classList.remove('on', 'parpadea');
      const k = luz === 'despeje' ? 'rojo' : luz;
      if (lentes[k]) {
        lentes[k].classList.add('on');
        if (luz === 'despeje') lentes[k].classList.add('parpadea');
      }
    }
    cuenta.poner(String(Math.max(0, Math.ceil(segundos - 1e-9))).padStart(2, ' ').slice(-2), COLOR[luz]);
  }
  return { el, actualizar, color: COLOR };
}
