// Microsimulación ILUSTRATIVA (no son aforos): vehículos y peatones deterministas por semilla.
// La posición de cada agente es una función del tiempo T (s), sin integrar, así que adelantar,
// retroceder o cambiar la velocidad no la descuadra. Respeta la regla de oro: nadie pasa la línea
// de pare fuera de la ventana de verde de su grupo (más 1 s de amarillo).
import { dur } from '../nucleo/tiempos.js';

// ---------------------------------------------------------------- utilidades
export function mulberry32(a) {
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
export function semilla(...partes) {
  let h = 2166136261;
  for (const c of partes.join('|')) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

export function trazo(puntos) {
  const L = [0];
  for (let i = 1; i < puntos.length; i++) {
    L.push(L[i - 1] + Math.hypot(puntos[i][0] - puntos[i - 1][0], puntos[i][1] - puntos[i - 1][1]));
  }
  return { p: puntos, L, largo: L[L.length - 1] };
}
/** Punto a distancia s del inicio, desplazado `lat` m a la derecha del sentido de avance. */
export function puntoEn(tr, s, lat = 0) {
  const { p, L } = tr;
  s = Math.max(0, Math.min(s, tr.largo));
  let i = 1;
  while (i < L.length - 1 && L[i] < s) i++;
  const f = (s - L[i - 1]) / (L[i] - L[i - 1] || 1);
  const dx = p[i][0] - p[i - 1][0], dy = p[i][1] - p[i - 1][1], n = Math.hypot(dx, dy) || 1;
  const x = p[i - 1][0] + f * dx, y = p[i - 1][1] + f * dy;
  return { x: x + (dy / n) * lat, y: y - (dx / n) * lat, ang: Math.atan2(dy, dx) };
}

const TIPOS = [
  { tipo: 'moto', p: 0.45, largo: 2.0, ancho: 0.8, h: 0.9, v0: 9.0 },
  { tipo: 'carro', p: 0.36, largo: 4.3, ancho: 1.8, h: 2.0, v0: 8.0 },
  { tipo: 'taxi', p: 0.15, largo: 4.2, ancho: 1.75, h: 2.0, v0: 8.0 },
  { tipo: 'buseta', p: 0.04, largo: 8.5, ancho: 2.4, h: 3.2, v0: 7.0 },
];
const COLORES_CARRO = ['#e9edf0', '#a3acb3', '#4a535b', '#8f2f2f', '#2f5ea8', '#d7d2c4', '#2a2f34'];
const ACEL = 2.2, FRENO = 2.6, ARRANQUE = 1.2, USO_AMARILLO = 1.0;

/** Ventana de paso (s del ciclo) de un grupo: verde + 1 s de amarillo, sin el arranque. */
function ventana(ti, c) {
  const a = ti.tiv + ARRANQUE;
  const b = ti.tiv + dur(ti.tiv, ti.tfv, c) + USO_AMARILLO;
  return [a, b];
}
function abrir(tau, [a, b], c) {
  // primer instante ≥ tau dentro de una ventana [kC + a, kC + b]
  let k = Math.floor((tau - a) / c) - 1;
  for (let i = 0; i < 4; i++, k++) {
    const ga = k * c + a, gb = k * c + b;
    if (gb > tau) return { t: Math.max(tau, ga), fin: gb };
  }
  return { t: tau, fin: tau + 1 };
}

// ---------------------------------------------------------------- vehículos
function corrienteVehicular({ clave, gid, tr, sPare, lat, ti, c, verde, motos, carriles }) {
  // llegadas por ciclo: caben en el verde (la cola se vacía) y en lo visible del tramo de entrada
  const capacidad = Math.max(1, Math.floor((verde - ARRANQUE) / (motos ? 0.9 : 2.0)) - 1);
  const visibles = Math.max(1, Math.floor((sPare - 6) / (motos ? 3.0 : 6.4)));
  const base = Math.min(capacidad, visibles, motos ? 6 : 4) * (motos ? 1 : carriles > 1 ? 0.8 : 1);
  const win = ventana(ti, c);
  const cache = new Map();

  function llegadas(k) {
    if (cache.has(k)) return cache.get(k);
    const r = mulberry32(semilla(clave, k));
    const n = Math.max(0, Math.round(base * (0.55 + 0.6 * r())));
    const out = [];
    for (let j = 0; j < n; j++) {
      const u = r();
      let t = TIPOS[1];
      if (motos) t = TIPOS[0];
      else { const x = r(); t = x < 0.68 ? TIPOS[1] : x < 0.95 ? TIPOS[2] : TIPOS[3]; }
      out.push({ ...t, a: k * c + ((j + u) / Math.max(n, 1)) * c, color: t.tipo === 'taxi' ? '#f2c014' :
        t.tipo === 'buseta' ? '#e6e1d3' : t.tipo === 'moto' ? COLORES_CARRO[Math.floor(r() * 3) + 2] :
        COLORES_CARRO[Math.floor(r() * COLORES_CARRO.length)], id: `${clave}:${k}:${j}` });
    }
    out.sort((x, y) => x.a - y.a);
    cache.set(k, out);
    if (cache.size > 12) cache.delete(cache.keys().next().value);
    return out;
  }

  return function enT(T) {
    const k = Math.floor(T / c);
    const lista = [];
    for (let i = k - 3; i <= k; i++) lista.push(...llegadas(i));
    // salidas en orden: el que va adelante sale primero; respeta la ventana de su grupo
    let dPrev = -Infinity, hPrev = 0;
    const plan = lista.map((v) => {
      const tau = v.a + sPare / v.v0;
      let o = abrir(tau, win, c);
      let d = Math.max(o.t, dPrev + hPrev);
      if (d > o.fin) { o = abrir(o.fin + 0.01, win, c); d = Math.max(o.t, dPrev + hPrev); }
      dPrev = d; hPrev = v.h;
      return { ...v, tau, d, para: d > tau + 0.4 };
    });
    // posición de cola: largo de los que siguen esperando cuando este llega
    const out = [];
    let sAnterior = Infinity, largoAnt = 0;
    for (let j = 0; j < plan.length; j++) {
      const v = plan[j];
      if (T < v.a) continue;
      let s;
      if (!v.para) s = v.v0 * (T - v.a);
      else {
        let cola = 0;
        for (let i = 0; i < j; i++) if (plan[i].para && plan[i].d > v.tau) cola += plan[i].largo + (motos ? 0.9 : 1.8);
        const sQ = Math.max(4, sPare - cola - v.largo / 2);
        const db = (v.v0 * v.v0) / (2 * FRENO);
        const sB = Math.max(0, sQ - db);
        const tB = v.a + sB / v.v0, tStop = tB + v.v0 / FRENO;
        const m = Math.max(tStop, v.d - Math.sqrt((2 * Math.max(0, sPare - sQ)) / ACEL));
        if (T < tB) s = v.v0 * (T - v.a);
        else if (T < tStop) { const x = T - tB; s = sB + v.v0 * x - 0.5 * FRENO * x * x; }
        else if (T < m) s = sQ;
        else { const x = T - m, tv = v.v0 / ACEL; s = x < tv ? sQ + 0.5 * ACEL * x * x : sQ + 0.5 * ACEL * tv * tv + v.v0 * (x - tv); }
      }
      // nadie se monta sobre el de adelante
      if (sAnterior < Infinity) s = Math.min(s, sAnterior - (largoAnt / 2 + v.largo / 2 + (motos ? 0.8 : 1.6)));
      if (s > tr.largo + 3) { sAnterior = s; largoAnt = v.largo; continue; }
      if (s < 0) continue;
      sAnterior = s; largoAnt = v.largo;
      const p = puntoEn(tr, s, lat);
      const quieto = v.para && T >= v.a + (s / v.v0) && T < v.d;
      out.push({ ...p, s, sPare, id: v.id, tipo: v.tipo, largo: v.largo, ancho: v.ancho, color: v.color,
        frena: quieto || (v.para && T < v.d), grupo: gid });
    }
    return out;
  };
}

// ---------------------------------------------------------------- peatones
function corrientePeatonal({ clave, eje, ti, c }) {
  const [a, b] = eje;
  const largo = Math.hypot(b[0] - a[0], b[1] - a[1]);
  const u = [(b[0] - a[0]) / largo, (b[1] - a[1]) / largo];
  const nrm = [u[1], -u[0]];
  const verde = dur(ti.tiv, ti.tfv, c);
  const cache = new Map();
  function llegadas(k) {
    if (cache.has(k)) return cache.get(k);
    const r = mulberry32(semilla(clave, k));
    const n = 2 + Math.floor(r() * 4);
    const out = [];
    for (let j = 0; j < n; j++) {
      const lado = r() < 0.5 ? 0 : 1, llega = k * c + r() * c, v = 1.05 + r() * 0.45, off = (r() - 0.5) * 2.6;
      // empieza a cruzar en verde (si llega con al menos 4 s de verde por delante) o espera al próximo
      const tc = ((llega % c) + c) % c;
      const enVerde = dur(ti.tiv, tc, c) < verde - 4;
      const ini = enVerde ? llega : llega + dur(tc, ti.tiv, c) + 0.3 + r() * 1.4;
      out.push({ id: `${clave}:${k}:${j}`, lado, llega, ini, v, off, ropa: ['#d9dee2', '#5f8fd6', '#d25b5b', '#e2b84c', '#7bbf8a'][Math.floor(r() * 5)] });
    }
    cache.set(k, out);
    if (cache.size > 10) cache.delete(cache.keys().next().value);
    return out;
  }
  return function enT(T) {
    const k = Math.floor(T / c);
    const out = [];
    for (let i = k - 2; i <= k; i++) {
      for (const p of llegadas(i)) {
        if (T < p.llega) continue;
        const desde = p.lado ? b : a, hacia = p.lado ? a : b;
        const sgn = p.lado ? -1 : 1;
        let f, camina = false;
        if (T < p.ini) f = -0.06;                   // esperando en el andén
        else { f = ((T - p.ini) * p.v) / largo; camina = true; }
        if (f > 1.08) continue;
        const x = desde[0] + (hacia[0] - desde[0]) * f + nrm[0] * p.off * 0.5 * sgn;
        const y = desde[1] + (hacia[1] - desde[1]) * f + nrm[1] * p.off * 0.5 * sgn;
        out.push({ id: p.id, x: x - u[0] * (f < 0 ? 0.9 : 0) * sgn, y: y - u[1] * (f < 0 ? 0.9 : 0) * sgn, camina, ropa: p.ropa,
          fase: (T - p.ini) * 3.2 });
      }
    }
    return out;
  };
}

/**
 * Simulación de un cruce para un plan. `geo`: geometria.json del cruce (trayectorias, cebras).
 * Devuelve {listo, enT(T) -> {vehiculos, peatones}}; sin trayectorias (asignación pendiente) no hay agentes.
 */
export function crearSim(it, geo, plan) {
  const c = plan.ciclo;
  const grupos = Object.fromEntries(it.grupos.map((g) => [g.id, g]));
  const corrientes = [];
  for (const [gid, t] of Object.entries(geo.trayectorias || {})) {
    const ti = plan.tiempos[gid];
    if (!ti) continue;
    const tr = trazo(t.puntos);
    const verde = dur(ti.tiv, ti.tfv, c);
    const via = (geo.vias || []).reduce((m, v) => Math.max(m, v.ancho), 6);
    const carriles = verde > 0 && via >= 6 ? 2 : 1;
    const comun = { gid, tr, sPare: t.s_pare, ti, c, verde, carriles };
    if (carriles > 1) {
      corrientes.push(corrienteVehicular({ ...comun, clave: `${it.id}${gid}${plan.id}L`, lat: -1.6, motos: false }));
      corrientes.push(corrienteVehicular({ ...comun, clave: `${it.id}${gid}${plan.id}R`, lat: 1.6, motos: false }));
      corrientes.push(corrienteVehicular({ ...comun, clave: `${it.id}${gid}${plan.id}M`, lat: 0, motos: true }));
    } else {
      corrientes.push(corrienteVehicular({ ...comun, clave: `${it.id}${gid}${plan.id}C`, lat: -0.4, motos: false }));
      corrientes.push(corrienteVehicular({ ...comun, clave: `${it.id}${gid}${plan.id}M`, lat: 1.1, motos: true }));
    }
  }
  const peatonales = [];
  for (const z of geo.cebras || []) {
    if (!z.grupo || !plan.tiempos[z.grupo] || grupos[z.grupo]?.tipo !== 'peatonal') continue;
    peatonales.push(corrientePeatonal({ clave: `${it.id}${z.grupo}${plan.id}`, eje: z.eje, ti: plan.tiempos[z.grupo], c }));
  }
  return {
    listo: corrientes.length > 0,
    enT(T) {
      return { vehiculos: corrientes.flatMap((f) => f(T)), peatones: peatonales.flatMap((f) => f(T)) };
    },
  };
}
