// Estado del tablero, reloj único y rutas enlazables (#/cruce/la-vina?plan=P2&t=98&vel=5&pausa=1).
import { segundoEnVivo, planVigente } from './nucleo/horario.js';
import { mod } from './nucleo/tiempos.js';

const subs = new Set();
export const E = {
  datos: null,
  fuente: 'mapa',          // 'mapa' o id de intersección en la pantalla principal
  equipo: null,            // equipo SAST seleccionado
  modo: 'vivo',            // 'vivo' | 'explorar'
  exp: { plan: null, t0: 0, real0: 0, vel: 1, pausado: false },
  presentando: false,
  offsetMs: 0,             // para pruebas: ?ahora=2026-10-12T15:00:00-05:00
};

export const suscribir = (fn) => { subs.add(fn); return () => subs.delete(fn); };
export function cambiar(parcial, { ruta = true } = {}) {
  Object.assign(E, parcial);
  if (ruta) escribirRuta();
  for (const fn of subs) fn(E);
}

export const ahora = () => Date.now() + E.offsetMs;
export const inter = (id) => E.datos.sem.intersecciones.find((i) => i.id === id);
export const planDe = (it, id) => it.planes.find((p) => p.id === id);

/** Tiempo en vivo de un cruce (lo que usan miniaturas, marcadores y la red). */
export function vivo(it, ms = ahora()) {
  const v = segundoEnVivo(it.horario, it.planes, ms);
  const T = (v.b.minutos - v.inicio) * 60;
  return { plan: planDe(it, v.plan), t: mod(T, v.ciclo), T, vigente: v, vivo: true };
}

/** Tiempo del cruce en la pantalla principal: en vivo o explorando un plan. */
export function tiempo(it, ms = ahora()) {
  if (E.modo === 'vivo' || E.fuente !== it.id) return vivo(it, ms);
  const x = E.exp;
  const T = x.t0 + (x.pausado ? 0 : ((performance.now() - x.real0) / 1000) * x.vel);
  const plan = planDe(it, x.plan);
  return { plan, t: mod(T, plan.ciclo), T, vigente: planVigente(it.horario, ms), vivo: false };
}

export function explorar(it, cambios) {
  const actual = tiempo(it);
  const x = { ...E.exp };
  if (E.modo === 'vivo') Object.assign(x, { plan: actual.plan.id, t0: actual.T, real0: performance.now(), vel: 1, pausado: false });
  else Object.assign(x, { t0: actual.T, real0: performance.now() });
  Object.assign(x, cambios);
  cambiar({ modo: 'explorar', exp: x });
}

export function volverEnVivo() { cambiar({ modo: 'vivo' }); }

// ---------------------------------------------------------------- bucle único
const alCuadro = new Set();
export const cadaCuadro = (fn) => { alCuadro.add(fn); return () => alCuadro.delete(fn); };
let activo = true;
const medida = { ms: 0, n: 0 };
function tic() {
  if (!activo) return;
  const t0 = performance.now();
  const ms = ahora();
  for (const fn of alCuadro) {
    try { fn(ms); } catch (e) { console.error(e); }
  }
  const d = performance.now() - t0;
  medida.ms = medida.n ? medida.ms * 0.9 + d * 0.1 : d;
  medida.n++;
}
export function arrancarBucle() {
  if (window.gsap) { window.gsap.ticker.lagSmoothing(0); window.gsap.ticker.add(tic); }
  else { const loop = () => { tic(); requestAnimationFrame(loop); }; requestAnimationFrame(loop); }
  document.addEventListener('visibilitychange', () => { activo = !document.hidden; });
  window.__tablero = { get activo() { return activo; }, E, medida };
}

// ---------------------------------------------------------------- rutas
export function leerRuta() {
  const [ruta, q = ''] = location.hash.replace(/^#/, '').split('?');
  const p = new URLSearchParams(q);
  const partes = ruta.split('/').filter(Boolean);
  const out = { fuente: 'mapa', equipo: null, modo: 'vivo', presentar: false };
  if (partes[0] === 'cruce' && inter(partes[1])) {
    out.fuente = partes[1];
    if (p.get('plan') && planDe(inter(partes[1]), p.get('plan'))) {
      out.modo = 'explorar';
      out.exp = { plan: p.get('plan'), t0: +p.get('t') || 0, real0: performance.now(), vel: +p.get('vel') || 1,
        pausado: p.get('pausa') === '1' };
    }
  } else if (partes[0] === 'sast') out.equipo = partes[1] || null;
  else if (partes[0] === 'presentacion') out.presentar = true;
  return out;
}

let escribiendo = false;
function escribirRuta() {
  let h = '#/';
  if (E.fuente !== 'mapa') {
    h = `#/cruce/${E.fuente}`;
    if (E.modo === 'explorar') {
      const it = inter(E.fuente);
      const t = Math.floor(tiempo(it).t);
      h += `?plan=${E.exp.plan}&t=${t}&vel=${E.exp.vel}${E.exp.pausado ? '&pausa=1' : ''}`;
    }
  } else if (E.equipo) h = `#/sast/${E.equipo}`;
  if (location.hash !== h) { escribiendo = true; history.replaceState(null, '', h); escribiendo = false; }
}
export const escribiendoRuta = () => escribiendo;
