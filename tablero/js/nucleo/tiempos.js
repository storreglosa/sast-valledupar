// Modelo de estados del ciclo semafórico. Réplica exacta de src/sast/semaforos/tiempos.py;
// tests/js/tiempos.test.mjs compara las dos contra tests/fixtures/estados_referencia.json.
//
// Estados (decisión 29, así se ve en campo):
//   preparacion  TIRA–TIV, solo vehiculares: el controlador lo grafica rojo-amarillo; en campo es rojo
//   verde        TIV–TFV
//   amarillo     TFV–TFA, vehiculares
//   despeje      TFV–TFA, peatonales: rojo intermitente
//   rojo         el resto del ciclo

export const CODIGO = { preparacion: 'p', verde: 'V', amarillo: 'A', despeje: 'D', rojo: 'r' };
export const NO_ROJO = new Set(['verde', 'amarillo', 'despeje']);

/** Segundos de a hasta b avanzando en el ciclo (0 si a == b). */
export const dur = (a, b, c) => (((b - a) % c) + c) % c;
export const dentro = (t, a, b, c) => dur(a, t, c) < dur(a, b, c);
export const mod = (t, c) => ((t % c) + c) % c;

export function estado(ti, tipo, t, c) {
  t = mod(t, c);
  if (ti.tira != null && dentro(t, ti.tira, ti.tiv, c)) return 'preparacion';
  if (dentro(t, ti.tiv, ti.tfv, c)) return 'verde';
  if (dentro(t, ti.tfv, ti.tfa, c)) return tipo === 'peatonal' ? 'despeje' : 'amarillo';
  return 'rojo';
}

/** Lo que se ve en campo: la preparación es rojo (decisión 29). */
export const luz = (e) => (e === 'preparacion' ? 'rojo' : e);

/** Segundos hasta el próximo cambio de indicación de ese grupo. */
export function restante(ti, t, c) {
  let m = Infinity;
  for (const k of ['tira', 'tiv', 'tfv', 'tfa']) {
    if (ti[k] == null) continue;
    const d = dur(t, ti[k], c) || c;
    if (d < m) m = d;
  }
  return m;
}

/** Segundos hasta que cambie lo que VE el usuario (la preparación no cuenta como cambio). */
export function restanteVisible(ti, tipo, t, c) {
  const ahora = luz(estado(ti, tipo, t, c));
  let s = 0;
  for (let i = 0; i < 6; i++) {
    s += restante(ti, t + s, c);
    if (luz(estado(ti, tipo, t + s + 1e-9, c)) !== ahora) return Math.min(s, c);
  }
  return c;
}

/** Un carácter por segundo del ciclo (evaluado en k + 0,5). */
export function cadena(ti, tipo, c) {
  let s = '';
  for (let k = 0; k < c; k++) s += CODIGO[estado(ti, tipo, k + 0.5, c)];
  return s;
}

/** Tramos [inicio, fin, estado] de un grupo a lo largo del ciclo, sin partir en el borde 0/C. */
export function tramos(ti, tipo, c) {
  const est = Array.from({ length: c }, (_, k) => estado(ti, tipo, k + 0.5, c));
  const out = [];
  for (let k = 0; k < c; k++) {
    if (out.length && out[out.length - 1][2] === est[k]) out[out.length - 1][1] = k + 1;
    else out.push([k, k + 1, est[k]]);
  }
  return out;
}

/** Intervalos del ciclo con el mismo conjunto de grupos en verde (cíclicos, fusionados). */
export function etapas(plan, grupos) {
  const c = plan.ciclo;
  const tipo = Object.fromEntries(grupos.map((g) => [g.id, g.tipo]));
  const orden = (a, b) => +a.slice(1) - +b.slice(1);
  const verdes = Array.from({ length: c }, (_, k) =>
    Object.keys(plan.tiempos).filter((g) => estado(plan.tiempos[g], tipo[g], k + 0.5, c) === 'verde').sort(orden));
  const igual = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
  let inicio = 0;
  for (let k = 0; k < c; k++) if (!igual(verdes[k], verdes[(k - 1 + c) % c])) { inicio = k; break; }
  const out = [];
  for (let i = 0; i < c; i++) {
    const k = (inicio + i) % c;
    const ult = out[out.length - 1];
    if (ult && igual(ult.verdes, verdes[k])) { ult.fin = (k + 1) % c || c; ult.duracion += 1; }
    else out.push({ inicio: k, fin: (k + 1) % c || c, duracion: 1, verdes: verdes[k] });
  }
  return out;
}

export function kpis(plan, grupos) {
  const c = plan.ciclo;
  const tipo = Object.fromEntries(grupos.map((g) => [g.id, g.tipo]));
  const verde = {}, rojo = {}, pct = {};
  for (const [g, ti] of Object.entries(plan.tiempos)) {
    verde[g] = dur(ti.tiv, ti.tfv, c);
    pct[g] = Math.round((1000 * verde[g]) / c) / 10;
    if (tipo[g] !== 'peatonal') rojo[g] = c - dur(ti.tiv, ti.tfa, c);
  }
  let todoRojo = 0;
  for (let k = 0; k < c; k++) {
    if (Object.entries(plan.tiempos).every(([g, ti]) => !NO_ROJO.has(estado(ti, tipo[g], k + 0.5, c)))) todoRojo++;
  }
  return { ciclo: c, ciclos_hora: Math.round(36000 / c) / 10, verde_s: verde, verde_pct: pct, rojo_s: rojo, todo_rojo_s: todoRojo };
}
