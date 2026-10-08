// Explicación en lenguaje claro de un plan: fases, cambios, fase peatonal y comparación con la
// noche. Solo afirma lo que sale de los tiempos del controlador (nada de aforos ni causas supuestas).
import { estado, NO_ROJO, kpis } from './tiempos.js';
import { hhmm, NOMBRE_DIA } from './horario.js';

const VIA = { KR: 'Carrera', CL: 'Calle', DG: 'Diagonal', TV: 'Transversal', AV: 'Avenida' };
export const nombreVia = (n) => {
  if (!n) return null;
  const m = /^([A-Z]{2})\s+(.*)$/.exec(n);
  return m && VIA[m[1]] ? `${VIA[m[1]]} ${m[2]}` : n;
};
export const plural = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`;
const lista = (xs) => (xs.length <= 1 ? xs.join('') : `${xs.slice(0, -1).join(', ')} y ${xs[xs.length - 1]}`);

/** Brazos con cebras en las dos mitades (entrada y salida): ahí hay que decir cuál. */
export function brazosPartidos(it) {
  const mitades = {};
  for (const g of it.grupos) {
    if (g.tipo === 'peatonal' && g.mov) (mitades[g.mov.brazo] ||= new Set()).add(g.mov.mitad);
  }
  return new Set(Object.keys(mitades).filter((b) => mitades[b].size > 1));
}

/** «Flujo 2 (Carrera 9, desde el sur)» o solo «Flujo 2» si la asignación no está publicada. */
export function rotulo(g, partidos = new Set()) {
  const m = g.mov;
  if (!m) return g.tipo === 'peatonal' ? `el grupo ${g.nombre}` : g.nombre;
  if (g.tipo === 'peatonal') {
    const lado = partidos.has(m.brazo) ? `, carriles de ${m.mitad}` : '';
    return `la cebra ${m.codigo} (${nombreVia(m.via) || 'vía'}, brazo ${m.brazo}${lado})`;
  }
  if (g.tipo === 'flecha') return `la flecha de giro a la ${m.movimiento.includes('izquierda') ? 'izquierda' : 'derecha'} desde el ${m.acceso} (por confirmar)`;
  return `${g.nombre} (${nombreVia(m.via) || 'vía sin nombre'}, desde el ${m.acceso})`;
}

/** Segmentos del ciclo para narrar: fase vehicular, fase peatonal o cambio. */
export function fases(it, plan) {
  const c = plan.ciclo;
  const g = Object.fromEntries(it.grupos.map((x) => [x.id, x]));
  const part = brazosPartidos(it);
  const seg = [];
  for (let k = 0; k < c; k++) {
    const est = Object.fromEntries(Object.entries(plan.tiempos).map(([id, ti]) => [id, estado(ti, g[id].tipo, k + 0.5, c)]));
    const veh = Object.keys(est).filter((id) => g[id].tipo !== 'peatonal' && est[id] === 'verde');
    const pea = Object.keys(est).filter((id) => g[id].tipo === 'peatonal' && est[id] === 'verde');
    const clave = veh.length ? `V:${veh}` : pea.length ? `P:${pea}` : 'C';
    const ult = seg[seg.length - 1];
    if (ult && ult.clave === clave) { ult.fin = k + 1; ult.seg.push(est); }
    else seg.push({ clave, inicio: k, fin: k + 1, seg: [est] });
  }
  // unir el último con el primero si son la misma fase (el ciclo es circular)
  if (seg.length > 1 && seg[0].clave === seg[seg.length - 1].clave) {
    const u = seg.pop();
    seg[0] = { ...seg[0], inicio: u.inicio, seg: [...u.seg, ...seg[0].seg] };
  }
  // fases peatonales seguidas (cambia qué cebras siguen en verde) se narran como una sola
  let unio = true;
  while (unio && seg.length > 1) {
    unio = false;
    for (let i = 0; i < seg.length; i++) {
      const j = (i + 1) % seg.length;
      if (seg[i].clave.startsWith('P:') && seg[j].clave.startsWith('P:')) {
        const peds = [...new Set([...seg[i].clave.slice(2).split(','), ...seg[j].clave.slice(2).split(',')])];
        seg[i] = { clave: `P:${peds}`, inicio: seg[i].inicio, fin: seg[j].fin, seg: [...seg[i].seg, ...seg[j].seg] };
        seg.splice(j, 1);
        unio = true;
        break;
      }
    }
  }
  seg.sort((a, b) => a.inicio - b.inicio);
  return seg.map((s) => {
    const d = s.seg.length;
    const ids = Object.keys(plan.tiempos);
    const cuenta = (pred) => s.seg.filter(pred).length;
    if (s.clave === 'C') {
      const amarillo = cuenta((e) => ids.some((id) => e[id] === 'amarillo'));
      const todoRojo = cuenta((e) => ids.every((id) => !NO_ROJO.has(e[id])));
      const quien = ids.filter((id) => s.seg.some((e) => e[id] === 'amarillo')).map((id) => g[id].nombre);
      const partes = [];
      if (amarillo) partes.push(`${amarillo} s de amarillo${quien.length ? ` para ${lista(quien)}` : ''}`);
      if (todoRojo) partes.push(`${todoRojo} s de todo rojo para despejar el cruce`);
      return { tipo: 'cambio', inicio: s.inicio, fin: s.fin, duracion: d,
        titulo: 'Cambio', texto: partes.length ? `${lista(partes)}.` : 'Transición.' };
    }
    const verdes = s.clave.slice(2).split(',');
    if (s.clave.startsWith('P:')) {
      const seg_ = verdes.map((id) => cuenta((e) => e[id] === 'verde'));
      const iguales = seg_.every((x) => x === seg_[0]);
      return { tipo: 'peatonal', inicio: s.inicio, fin: s.fin, duracion: d, grupos: verdes,
        titulo: 'Fase peatonal',
        texto: `Todos los vehículos esperan en rojo y cruzan los peatones de ${lista(verdes.map((id) => rotulo(g[id], part)))}`
          + (iguales ? ` durante ${seg_[0]} s.` : `: ${lista(verdes.map((id, i) => `${g[id].nombre} ${seg_[i]} s`))}.`) };
    }
    const peatones = ids.filter((id) => g[id].tipo === 'peatonal' && s.seg.some((e) => e[id] === 'verde'));
    let texto = `Verde para ${lista(verdes.map((id) => rotulo(g[id], part)))} durante ${d} s.`;
    if (peatones.length) texto += ` A la vez cruzan los peatones de ${lista(peatones.map((id) => rotulo(g[id], part)))}.`;
    return { tipo: 'vehicular', inicio: s.inicio, fin: s.fin, duracion: d, grupos: verdes, titulo: 'Fase', texto };
  }).map((f, i, arr) => ({ ...f, titulo: f.tipo === 'vehicular'
    ? `Fase ${arr.slice(0, i + 1).filter((x) => x.tipo === 'vehicular').length}` : f.titulo }));
}

/** Resumen para el monitor de explicación y el modo presentación. */
export function resumen(it, plan, vigente) {
  const k = kpis(plan, it.grupos);
  const g = Object.fromEntries(it.grupos.map((x) => [x.id, x]));
  const rojoMax = Math.max(...Object.values(k.rojo_s));
  const cuando = vigente
    ? `${NOMBRE_DIA[vigente.b.diaSemana]} ${hhmm(vigente.b.minutos)}${vigente.festivo ? ` (festivo: ${vigente.festivo})` : ''}`
    : null;
  const intro = vigente && vigente.plan === plan.id
    ? `Ahora (${cuando}) rige el plan ${plan.id}.`
    : `Plan ${plan.id}${plan.con_horario ? '' : ', programado en el controlador pero sin horario: hoy no corre'}.`;
  const ciclo = `El ciclo dura ${plan.ciclo} s: el semáforo repite la misma secuencia ${String(k.ciclos_hora).replace('.', ',')} veces por hora.`;
  const espera = `Quien llega justo cuando se pone en rojo espera hasta ${rojoMax} s.`;

  // comparación con el plan más corto que sí corre (de noche)
  const corren = it.planes.filter((p) => p.con_horario);
  const corto = corren.reduce((a, b) => (b.ciclo < a.ciclo ? b : a));
  let noche = null;
  if (corto.id !== plan.id) {
    const kc = kpis(corto, it.grupos);
    const bloques = Object.entries(it.horario).flatMap(([d, f]) => f.filter((b) => b[2] === corto.id).map((b) => b));
    const horas = [...new Set(bloques.map(([a, b]) => `${hhmm(a)}–${hhmm(b)}`))].join(' y ');
    noche = `En ${horas} rige ${corto.id}, con un ciclo de ${corto.ciclo} s: la espera máxima en rojo baja de ${rojoMax} s a ${Math.max(...Object.values(kc.rojo_s))} s.`;
  }
  const verdes = Object.entries(k.verde_s).filter(([id]) => g[id].tipo !== 'peatonal')
    .map(([id, s]) => ({ id, s, pct: k.verde_pct[id] }));
  return { intro, ciclo, espera, noche, verdes, kpis: k, fases: fases(it, plan) };
}

export const GLOSARIO = [
  ['Ciclo', 'Una vuelta completa de la secuencia de luces. Al terminar, todo se repite igual.'],
  ['Plan', 'Una programación del ciclo (duración y reparto del verde). El controlador cambia de plan según la hora y el día.'],
  ['Grupo semafórico', 'Los semáforos que encienden juntos: un flujo vehicular, una flecha o un cruce peatonal. Sus nombres siguen la codificación de trayectorias de la SDM Bogotá.'],
  ['Fase', 'El tramo del ciclo en que un mismo conjunto de grupos tiene verde.'],
  ['Todo rojo', 'Segundos en que todos están en rojo para que el cruce quede libre antes del siguiente verde.'],
  ['Despeje peatonal', 'El último segundo del verde peatonal: la figura roja parpadea y nadie debe empezar a cruzar.'],
  ['Preparación', 'Dos segundos antes del verde que el controlador marca aparte; en la calle se ven en rojo.'],
];
