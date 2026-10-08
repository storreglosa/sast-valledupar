// Hora de Bogotá, festivos de Colombia (Ley 51 de 1983) y plan vigente. Réplica de
// src/sast/semaforos/horario.py; tests/js/horario.test.mjs compara contra la referencia de Python.

export const DIAS = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo', 'festivo'];
export const NOMBRE_DIA = { lunes: 'Lunes', martes: 'Martes', miercoles: 'Miércoles', jueves: 'Jueves',
  viernes: 'Viernes', sabado: 'Sábado', domingo: 'Domingo', festivo: 'Festivo' };

const ymd = (y, m, d) => `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
const desdeUTC = (dt) => ymd(dt.getUTCFullYear(), dt.getUTCMonth() + 1, dt.getUTCDate());
const masDias = (y, m, d, n) => { const t = new Date(Date.UTC(y, m - 1, d + n)); return t; };

/** Domingo de Pascua (algoritmo anónimo gregoriano). Devuelve [anio, mes, dia]. */
export function pascua(anio) {
  const a = anio % 19, b = Math.floor(anio / 100), c = anio % 100;
  const d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25), g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30, i = Math.floor(c / 4), k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451);
  const mes = Math.floor((h + l - 7 * m + 114) / 31), dia = ((h + l - 7 * m + 114) % 31) + 1;
  return [anio, mes, dia];
}

const lunesSiguiente = (y, m, d) => {
  const t = new Date(Date.UTC(y, m - 1, d));
  const dw = (t.getUTCDay() + 6) % 7; // 0 = lunes
  return masDias(y, m, d, (7 - dw) % 7);
};

const cache = new Map();
/** {'AAAA-MM-DD': nombre} con los festivos del año. */
export function festivos(anio) {
  if (cache.has(anio)) return cache.get(anio);
  const out = {};
  const fijos = [[1, 1, 'Año Nuevo'], [5, 1, 'Día del Trabajo'], [7, 20, 'Día de la Independencia'],
    [8, 7, 'Batalla de Boyacá'], [12, 8, 'Inmaculada Concepción'], [12, 25, 'Navidad']];
  const trasl = [[1, 6, 'Reyes Magos'], [3, 19, 'San José'], [6, 29, 'San Pedro y San Pablo'],
    [8, 15, 'Asunción de la Virgen'], [10, 12, 'Día de la Raza'], [11, 1, 'Todos los Santos'],
    [11, 11, 'Independencia de Cartagena']];
  for (const [m, d, n] of fijos) out[ymd(anio, m, d)] = n;
  for (const [m, d, n] of trasl) out[desdeUTC(lunesSiguiente(anio, m, d))] = n;
  const [, pm, pd] = pascua(anio);
  for (const [n, nom] of [[-3, 'Jueves Santo'], [-2, 'Viernes Santo'], [43, 'Ascensión del Señor'],
    [64, 'Corpus Christi'], [71, 'Sagrado Corazón']]) out[desdeUTC(masDias(anio, pm, pd, n))] = nom;
  const ordenado = Object.fromEntries(Object.entries(out).sort(([a], [b]) => (a < b ? -1 : 1)));
  cache.set(anio, ordenado);
  return ordenado;
}

const FMT = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Bogota', year: 'numeric', month: '2-digit',
  day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' });

/** Fecha y hora de Bogotá de un instante (ms epoch). Bogotá no tiene horario de verano (UTC−5). */
export function bogota(ms) {
  const p = Object.fromEntries(FMT.formatToParts(new Date(ms)).map((x) => [x.type, x.value]));
  const fecha = `${p.year}-${p.month}-${p.day}`;
  const dw = (new Date(Date.UTC(+p.year, +p.month - 1, +p.day)).getUTCDay() + 6) % 7;
  const seg = (ms / 1000) % 1;
  return { fecha, anio: +p.year, hora: +p.hour, minuto: +p.minute, segundo: +p.second + seg,
    minutos: +p.hour * 60 + +p.minute + (+p.second + seg) / 60, diaSemana: DIAS[dw] };
}

export function diaHorario(b) {
  const f = festivos(b.anio)[b.fecha];
  return f ? { fila: 'festivo', festivo: f } : { fila: b.diaSemana, festivo: null };
}

/** Bloque del horario que rige en el instante `ms`: {plan, inicio, fin, fila, festivo}. */
export function planVigente(horario, ms) {
  const b = bogota(ms);
  const { fila, festivo } = diaHorario(b);
  for (const [ini, fin, plan] of horario[fila]) {
    if (b.minutos >= ini && b.minutos < fin) return { plan, inicio: ini, fin, fila, festivo, b };
  }
  throw new Error(`Sin plan a las ${b.hora}:${b.minuto} (${fila})`);
}

/**
 * Segundo del ciclo en vivo: anclado al inicio del bloque horario (fase ilustrativa; el desfase
 * real del controlador no se conoce). Así todos los que miran ven lo mismo y el cambio de plan es limpio.
 */
export function segundoEnVivo(horario, planes, ms) {
  const v = planVigente(horario, ms);
  const c = planes.find((p) => p.id === v.plan).ciclo;
  const desde = (v.b.minutos - v.inicio) * 60;
  return { ...v, ciclo: c, t: ((desde % c) + c) % c };
}

export const hhmm = (min) => {
  if (min >= 1440) return '24:00';
  const h = Math.floor(min / 60), m = Math.round(min % 60);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
};
