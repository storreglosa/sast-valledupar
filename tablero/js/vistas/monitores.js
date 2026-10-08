// Monitores de análisis (columna derecha). Modo mapa: red semafórica y ficha SAST. Modo cruce:
// reloj del ciclo, cabezas con contador y explicación (con semana y tabla de tiempos).
import { h, mostrarTip, ocultarTip } from '../util/dom.js';
import { estado, luz, restanteVisible, kpis } from '../nucleo/tiempos.js';
import { resumen, rotulo, brazosPartidos, claves, GLOSARIO } from '../nucleo/explicacion.js';
import { anillo } from './anillo.js';
import { cabeza, PALABRA } from './cabezas.js';
import { semana, colorCiclo } from './programacion.js';
import { vivo, inter } from '../estado.js';

export function monitor(titulo, { tally = '' } = {}) {
  const pantalla = h('div', { class: 'pantalla' });
  const txt = h('span', { class: 'rotulo-txt' }, titulo);
  const el = h('section', { class: 'monitor', 'aria-label': titulo }, pantalla, h('div', { class: 'rotulo' }, txt, h('span', { class: `tally ${tally}`, 'aria-hidden': 'true' })));
  return { el, pantalla, titulo: (t) => { txt.textContent = t; } };
}

const MENORES = new Set(['con', 'de', 'del', 'la', 'el', 'y', 'bis']);
/** «CARRERA 12 - CALLE 16 (SUR - NORTE)» -> «Carrera 12 - Calle 16 (sur - norte)». */
export const tipoTitulo = (t) => {
  let dentro = false;
  return String(t).toLowerCase().split(/(\s+|\(|\))/).map((w) => {
    if (w === '(') dentro = true;
    if (w === ')') dentro = false;
    return !dentro && w.length > 1 && !MENORES.has(w) ? w[0].toUpperCase() + w.slice(1) : w;
  }).join('');
};

// ---------------------------------------------------------------- modo mapa
export function red(sem, alElegir) {
  const m = monitor('Red semafórica · fase ilustrativa', { tally: 'vivo' });
  const cuerpo = h('div', { class: 'mon-cuerpo' });
  const lista = h('ul', { class: 'red' });
  cuerpo.append(h('h3', {}, 'Cinco cruces con cámaras SAST'), lista);
  m.pantalla.append(cuerpo);
  const filas = sem.intersecciones.map((it) => {
    const leds = it.grupos.filter((g) => g.tipo !== 'peatonal').map(() => h('span', { class: 'led' }));
    const p = h('div', { class: 'p num' });
    const btn = h('button', { type: 'button', title: it.direccion, onclick: () => alElegir(it.id) },
      h('span', { class: 'leds' }, leds), h('div', {}, h('div', { class: 'n' }, it.nombre)), p);
    lista.append(h('li', {}, btn));
    return { it, leds, p, prev: [] };
  });
  function actualizar(ms) {
    for (const f of filas) {
      const v = vivo(f.it, ms);
      const veh = f.it.grupos.filter((g) => g.tipo !== 'peatonal');
      veh.forEach((g, i) => {
        const e = luz(estado(v.plan.tiempos[g.id], g.tipo, v.t, v.plan.ciclo));
        if (f.prev[i] !== e) { f.prev[i] = e; f.leds[i].className = `led ${e}`; }
      });
      const faltan = v.vigente.fin - v.vigente.b.minutos;
      const txt = `${v.plan.id} · ${v.plan.ciclo} s|${faltan >= 60 ? `${Math.floor(faltan / 60)} h ${Math.floor(faltan % 60)} min` : `${Math.ceil(faltan)} min`}`;
      if (f.p.dataset.t !== txt) {
        f.p.dataset.t = txt;
        const [a, b] = txt.split('|');
        f.p.replaceChildren(a);
        f.p.title = `El plan cambia en ${b}`;
      }
    }
  }
  return { ...m, actualizar };
}

export function ficha(sast, alVerSemaforo) {
  const m = monitor('Ficha del punto SAST');
  const cuerpo = h('div', { class: 'mon-cuerpo' });
  m.pantalla.append(cuerpo);
  const feats = sast.equipos.features;
  function mostrar(equipo) {
    cuerpo.replaceChildren();
    const f = feats.find((x) => x.properties.equipo === equipo);
    if (!f) {
      const op = feats.filter((x) => x.properties.estado === 'Operando').length;
      cuerpo.append(h('h3', {}, `${feats.length} puntos SAST autorizados`),
        h('p', { class: 'sub' }, `${op} en operación y ${feats.length - op} autorizados que aún no operan. Toque una cámara en el mapa para ver su ficha y su línea base.`),
        h('dl', { class: 'glosario' },
          h('dt', {}, 'Línea base'), h('dd', {}, 'Fallecidos, lesionados y comparendos en la zona de influencia de cada equipo durante los 36 meses previos a su inicio de operación.'),
          h('dt', {}, 'Criterio'), h('dd', {}, sast.criterio),
          h('dt', {}, 'Cortes'), h('dd', {}, `Siniestros ${sast.cortes.siniestros} · comparendos ${sast.cortes.comparendos}`)));
      m.titulo('Ficha del punto SAST');
      return;
    }
    const p = f.properties;
    m.titulo(`Ficha · ${p.equipo}`);
    const op = p.estado === 'Operando';
    cuerpo.append(h('div', { class: 'ficha-cab' },
      h('div', {}, h('h3', {}, `Equipo ${p.numero} · ${p.punto}`), h('p', { class: 'sub ficha-dir' }, tipoTitulo(p.direccion_ansv || p.direccion))),
      h('span', { class: `estado ${op ? 'op' : 'no'}` }, op ? 'Operando' : 'Autorizado, no opera')));
    const dl = h('dl', { class: 'dl' });
    const fila = (a, b) => b && dl.append(h('dt', {}, a), h('dd', {}, b));
    fila('Inicio de operación', p.fecha_inicio ? p.fecha_inicio.split('-').reverse().join('/') : null);
    fila('Código único ANSV', p.codigo_unico);
    fila('Solicitud', p.solicitud_ansv || `Solicitud ${p.solicitud}`);
    cuerpo.append(dl);
    cuerpo.append(h('div', { class: 'sub', style: { margin: '0 0 4px' } }, 'Infracciones aprobadas'));
    const cods = h('div', { class: 'codigos' });
    for (const c of p.codigos) {
      const desc = sast.infracciones[c] || 'Descripción pendiente';
      const chip = h('span', { class: 'cod', tabindex: 0, 'aria-label': `${c}: ${desc}` }, c);
      chip.addEventListener('pointermove', (ev) => mostrarTip(ev, `<b>${c}</b> · ${desc}`));
      chip.addEventListener('pointerleave', ocultarTip);
      cods.append(chip);
    }
    cuerpo.append(cods);
    const lb = sast.linea_base[p.equipo];
    if (lb) {
      cuerpo.append(h('div', { class: 'sub', style: { margin: '6px 0 0' } }, `Línea base oficial (+15 m): ${lb.ventana}`),
        h('div', { class: 'cifras' },
          h('div', { class: 'cifra' }, h('div', { class: 'v num' }, lb.fallecidos), h('div', { class: 'e' }, 'fallecidos')),
          h('div', { class: 'cifra' }, h('div', { class: 'v num' }, lb.lesionados), h('div', { class: 'e' }, 'lesionados')),
          h('div', { class: 'cifra' }, h('div', { class: 'v num' }, lb.total_comparendos.toLocaleString('es-CO')), h('div', { class: 'e' }, 'comparendos'))));
      const max = Math.max(1, ...lb.comparendos.map((c) => c.total));
      const barras = h('div', { class: 'barras', role: 'table', 'aria-label': 'Comparendos por código' });
      const visibles = lb.comparendos.slice(0, 4), resto = lb.comparendos.slice(4);
      for (const c of visibles) {
        const b = h('div', { class: 'barra', role: 'row' }, h('span', { class: 'c', role: 'cell' }, c.codigo),
          h('span', { class: 't', role: 'cell' }, h('i', { style: { width: `${(100 * c.total) / max}%` } })),
          h('span', { class: 'n', role: 'cell' }, c.total.toLocaleString('es-CO')));
        b.addEventListener('pointermove', (ev) => mostrarTip(ev, `<b>${c.codigo}</b> · ${sast.infracciones[c.codigo] || ''}<br>Agentes ${c.agente.toLocaleString('es-CO')} · fotodetección previa ${c.foto_previa.toLocaleString('es-CO')}`));
        b.addEventListener('pointerleave', ocultarTip);
        barras.append(b);
      }
      if (resto.length) barras.append(h('p', { class: 'resto' }, `Otros: ${resto.map((c) => `${c.codigo} ${c.total.toLocaleString('es-CO')}`).join(' · ')}`));
      cuerpo.append(barras, h('details', { class: 'salvedades' }, h('summary', {}, 'Cómo leer estas cifras'),
        h('ul', {}, sast.salvedades.map((x) => h('li', {}, x)))));
    } else {
      cuerpo.append(h('p', { class: 'vacio' }, 'Sin línea base: el equipo aún no ha iniciado operación.'));
    }
    if (p.semaforo) {
      cuerpo.append(h('p', { style: { marginTop: '10px' } }, h('button', { type: 'button', class: 'enlace-btn', onclick: () => alVerSemaforo(p.semaforo) }, `Ver el semáforo de ${inter(p.semaforo).nombre}`)));
    }
  }
  return { ...m, mostrar };
}

// ---------------------------------------------------------------- modo cruce
export function reloj(it, fases) {
  const m = monitor('Reloj del ciclo');
  m.el.title = 'Pase el cursor por una cabeza semafórica para ver su cuenta regresiva en el centro del reloj.';
  const a = anillo(it, { tam: 'completo', fases });
  const plan = h('div', { class: 'rl-plan' });
  // cifras clave del plan, siempre a la vista: el rojo más largo y el verde promedio
  const cifras = h('div', { class: 'rl-kpi' });
  const foco = h('div', { class: 'rl-foco' });
  m.pantalla.classList.add('pant-reloj');
  // en pantallas bajas se ocultan primero verde/amarillo/rojo («basico»): se leen solos
  const ley = h('ul', { class: 'rl-ley' },
    h('li', { class: 'basico' }, h('i', { class: 'sw verde' }), 'verde'), h('li', { class: 'basico' }, h('i', { class: 'sw amarillo' }), 'amarillo'),
    h('li', { class: 'basico' }, h('i', { class: 'sw rojo' }), 'rojo'), ...(it.grupos.some((g) => g.tipo === 'peatonal') ? [h('li', {}, h('i', { class: 'sw despeje' }), 'despeje peatonal')] : []),
    h('li', {}, h('i', { class: 'sw aguja' }), 'aguja = ahora'));
  m.pantalla.append(h('div', { class: 'reloj' }, h('div', { class: 'rl-anillo' }, a.el),
    h('div', { class: 'rl-info' }, plan, cifras, foco, ley)));
  let enfoque = null, previo = '';
  return {
    ...m,
    enfocar: (g) => { enfoque = g; },
    actualizar(t, p) {
      a.actualizar(t, p, enfoque);
      const clave = `${p.id}|${Math.floor(t)}|${enfoque}`;
      if (clave === previo) return;
      previo = clave;
      plan.replaceChildren(h('b', {}, p.id), ` · ciclo ${p.ciclo} s`);
      if (cifras.dataset.plan !== p.id) {
        cifras.dataset.plan = p.id;
        const k = claves(p, it.grupos);
        const nom = it.grupos.find((g) => g.id === k.rojoMaxId)?.nombre || k.rojoMaxId;
        cifras.replaceChildren(
          h('span', { title: `La espera más larga en rojo: ${nom}` }, h('b', {}, `${k.rojoMax} s`), ' rojo máx.'),
          ...(k.verdeProm != null ? [h('span', { title: 'Promedio del verde de los flujos vehiculares (sin flechas ni peatonales)' }, h('b', {}, `${k.verdeProm} s`), ' verde prom.')] : []));
      }
      foco.textContent = enfoque ? `Centro: cuenta regresiva de ${enfoque}` : '';
    },
  };
}

export function cabezasMon(it, alEnfocar) {
  const m = monitor('Cabezas semafóricas · contador');
  const cuerpo = h('div', { class: 'mon-cuerpo' });
  const grilla = h('div', { class: 'cabezas' });
  const part = brazosPartidos(it);
  cuerpo.append(grilla);
  m.pantalla.append(cuerpo);
  const items = it.grupos.map((g) => {
    const c = cabeza(g);
    const palabra = h('div', { class: 'palabra' });
    const desc = g.mov ? rotulo(g, part).replace(/^la /, '') : (g.tipo === 'peatonal' ? 'peatonal' : g.tipo);
    const el = h('div', { class: 'cabeza', tabindex: 0, title: `${g.id} · ${g.nombre} — ${desc}`, 'aria-label': `${g.id} ${g.nombre}, ${desc}` },
      h('div', { class: 'g' }, g.id, h('span', { class: 'gn' }, ` ${g.nombre.replace('Peatonal ', 'P').replace('Flujo ', 'F')}`)), c.el, palabra);
    el.addEventListener('pointerenter', () => alEnfocar(g.id));
    el.addEventListener('focus', () => alEnfocar(g.id));
    el.addEventListener('pointerleave', () => alEnfocar(null));
    el.addEventListener('blur', () => alEnfocar(null));
    grilla.append(el);
    return { g, c, palabra, prev: null };
  });
  function actualizar(t, plan) {
    for (const x of items) {
      const ti = plan.tiempos[x.g.id];
      const e = luz(estado(ti, x.g.tipo, t, plan.ciclo));
      x.c.actualizar(e, restanteVisible(ti, x.g.tipo, t, plan.ciclo));
      if (x.prev !== e) { x.prev = e; x.palabra.className = `palabra ${e}`; x.palabra.textContent = x.g.tipo === 'peatonal' && e === 'verde' ? 'CRUCE' : PALABRA[e]; }
    }
  }
  return { ...m, actualizar };
}

export function explicacionMon(it, { alElegirPlan }) {
  const m = monitor('Explicación del plan');
  m.pantalla.classList.add('pant-expl');
  const cuerpo = h('div', { class: 'mon-cuerpo col' });
  m.pantalla.append(cuerpo);
  const tabs = ['Explicación', 'Semana', 'Tiempos'];
  let pest = 'Explicación', planId = null, fasesEl = [], semanaVista = null, vivoPrevio = null;
  const anuncio = h('div', { class: 'solo-lector', 'aria-live': 'polite' });
  const barra = h('div', { class: 'pestanas', role: 'tablist' }, tabs.map((t) => h('button', { type: 'button', class: 'pestana', role: 'tab', 'aria-selected': String(t === pest), onclick: () => { pest = t; planId = null; } }, t)));
  const contenido = h('div', { class: 'contenido' });
  let lista = null;
  cuerpo.append(barra, contenido, anuncio);

  function render(plan, v) {
    for (const b of barra.children) b.setAttribute('aria-selected', String(b.textContent === pest));
    contenido.replaceChildren();
    lista = null;
    fasesEl = [];
    semanaVista = null;
    if (pest === 'Explicación') {
      const r = resumen(it, plan, v.vigente);
      const k = r.kpis;
      contenido.append(h('div', { class: 'kpis' },
        h('div', { class: 'kpi' }, h('div', { class: 'v num' }, `${plan.ciclo} s`), h('div', { class: 'e' }, 'dura el ciclo')),
        h('div', { class: 'kpi' }, h('div', { class: 'v num' }, `${r.rojoMax} s`), h('div', { class: 'e' }, 'rojo máximo')),
        h('div', { class: 'kpi' }, h('div', { class: 'v num' }, r.verdeProm != null ? `${r.verdeProm} s` : '–'), h('div', { class: 'e' }, 'verde promedio')),
        h('div', { class: 'kpi' }, h('div', { class: 'v num' }, `${k.todo_rojo_s} s`), h('div', { class: 'e' }, 'todo rojo por ciclo'))));
      // los mismos cuatro indicadores en una línea: reemplaza a la fila en pantallas bajas (CSS)
      contenido.append(h('p', { class: 'kpis-linea' }, h('b', { class: 'num' }, `${plan.ciclo} s`), ' de ciclo · ',
        h('b', { class: 'num' }, `${r.rojoMax} s`), ' rojo máximo · ', ...(r.verdeProm != null ? [h('b', { class: 'num' }, `${r.verdeProm} s`), ' verde promedio · '] : []),
        h('b', { class: 'num' }, `${k.todo_rojo_s} s`), ' de todo rojo'));
      const ex = h('div', { class: 'expl' }, h('p', { class: 'lead', title: `${r.ciclo} ${r.espera}` }, r.intro, h('span', { class: 'lead-ciclo' }, ` ${r.ciclo}`)));
      const ol = h('ol', { class: 'fases' });
      lista = h('div', { class: 'fases-scroll' }, ol);
      for (const f of r.fases) {
        // texto largo y corto: en pantallas bajas el CSS deja el corto para que la fase en curso quepa entera
        const li = h('li', { class: `fase ${f.tipo}` }, h('span', { class: 'rango num' }, `${f.inicio}–${f.fin} s`),
          h('span', {}, h('b', {}, `${f.titulo}. `), h('span', { class: 'largo' }, f.texto), h('span', { class: 'corto', title: f.texto }, f.corto)));
        ol.append(li);
        fasesEl.push({ f, li });
      }
      if (r.noche) lista.append(h('p', { class: 'nota-noche' }, r.noche));
      contenido.append(ex, lista);
    } else if (pest === 'Semana') {
      contenido.append(h('p', { class: 'sub' }, 'Qué plan corre cada día y hora. Más claro = ciclo más largo. Clic en un bloque para explorarlo.'));
      const caja = h('div', { style: { position: 'relative', height: '250px' } });
      semanaVista = semana(it, Date.now(), (pid) => alElegirPlan(pid));
      caja.append(semanaVista.el);
      contenido.append(caja);
      const ley = h('div', { class: 'sub', style: { display: 'flex', gap: '10px', flexWrap: 'wrap', marginTop: '8px' } },
        [...new Set(it.planes.map((p) => p.ciclo))].sort((a, b) => a - b).map((c) =>
          h('span', { style: { display: 'inline-flex', alignItems: 'center', gap: '5px' } }, h('i', { style: { width: '10px', height: '10px', borderRadius: '2px', background: colorCiclo(c), display: 'inline-block' } }), `${c} s`)));
      contenido.append(ley);
    } else {
      const t = h('table', { class: 'tabla-t' }, h('caption', { class: 'sub', style: { textAlign: 'left' } }, `Tiempos del plan ${plan.id} (s desde el inicio del ciclo), tal como los trae el reporte del controlador ${it.controlador.equipo}.`),
        h('thead', {}, h('tr', {}, ['Grupo', 'TIRA', 'TIV', 'TFV', 'TFA', 'Verde'].map((x) => h('th', { scope: 'col' }, x)))),
        h('tbody', {}, it.grupos.map((g) => {
          const ti = plan.tiempos[g.id];
          return h('tr', {}, h('th', { scope: 'row', style: { textAlign: 'left' } }, `${g.id} ${g.nombre}`),
            [ti.tira ?? '–', ti.tiv, ti.tfv, ti.tfa, `${kpis(plan, it.grupos).verde_s[g.id]} s`].map((x) => h('td', {}, x)));
        })));
      const gl = h('dl', { class: 'glosario', style: { marginTop: '12px' } }, GLOSARIO.flatMap(([a, b]) => [h('dt', {}, a), h('dd', {}, b)]),
        h('dt', {}, 'TIRA · TIV · TFV · TFA'), h('dd', {}, 'Inicio de la preparación, inicio del verde, fin del verde y fin del amarillo (o del despeje peatonal).'));
      contenido.append(t, gl);
    }
  }

  let faseActiva = null;
  function actualizar(t, plan, v, ms) {
    const clave = `${plan.id}|${pest}|${v.vivo}`;
    if (clave !== planId) { planId = clave; render(plan, v); faseActiva = null; }
    if (vivoPrevio !== v.vivo) vivoPrevio = v.vivo;
    for (const { f, li } of fasesEl) {
      const dentro = f.inicio < f.fin ? t >= f.inicio && t < f.fin : t >= f.inicio || t < f.fin;
      if (dentro && faseActiva !== f) {
        faseActiva = f;
        for (const x of fasesEl) x.li.classList.toggle('activa', x.f === f);
        anuncio.textContent = `${f.titulo}: ${f.texto}`;
        // el monitor sigue a la aguja: la fase activa queda a la vista sin desplazar la página
        // instantáneo: la fase en curso queda arriba en el mismo cuadro (un scroll suave se queda atrás)
        if (lista) lista.scrollTop = Math.max(0, li.offsetTop - 2);
        if (window.gsap && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) window.gsap.fromTo(li, { x: -6 }, { x: 0, duration: 0.35, ease: 'expo.out' });
      }
    }
    if (semanaVista) {
      const b = v.vigente.b;
      semanaVista.ahora(b.minutos);
    }
  }
  return { ...m, actualizar, faseActual: () => faseActiva };
}

