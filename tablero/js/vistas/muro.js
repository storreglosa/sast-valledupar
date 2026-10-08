// El muro de video: columna de fuentes (mapa + 5 cruces), pantalla principal, monitores de
// análisis y franja inferior. Firma: al elegir una fuente, su monitor «vuela» a la pantalla
// principal (con un barrido de línea), y la pantalla y los monitores se reasignan a esa fuente.
import { h, s, $, reducido } from '../util/dom.js';
import { display } from '../util/siete.js';
import { estado, luz, dur } from '../nucleo/tiempos.js';
import { bogota, diaHorario, NOMBRE_DIA } from '../nucleo/horario.js';
import { E, cambiar, vivo, tiempo, inter, explorar, volverEnVivo, cadaCuadro, suscribir } from '../estado.js';
import { anillo } from './anillo.js';
import { crearMapa } from './mapa.js';
import { diagrama } from './diagrama.js';
import { gantt } from './gantt.js';
import { hoy, colorCiclo } from './programacion.js';
import { red, ficha, reloj, cabezasMon, explicacionMon } from './monitores.js';
import { fases as fasesDe } from '../nucleo/explicacion.js';

const ICO = {
  play: '<svg viewBox="0 0 16 16"><path d="M4 2.5v11l9-5.5z"/></svg>',
  pausa: '<svg viewBox="0 0 16 16"><path d="M3.5 2.5h3v11h-3zM9.5 2.5h3v11h-3z"/></svg>',
  atras: '<svg viewBox="0 0 16 16"><path d="M3 2.5h2v11H3zM14 2.5v11L6 8z"/></svg>',
  adelante: '<svg viewBox="0 0 16 16"><path d="M11 2.5h2v11h-2zM2 2.5v11L10 8z"/></svg>',
  mapa: '<svg viewBox="0 0 16 16"><path d="M1 3.5l4.5-2 5 2 4.5-2v11l-4.5 2-5-2L1 14.5zM5.5 3v9.5M10.5 4.5V14" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>',
};

export function crearMuro(datos) {
  const { sem, geo, sast } = datos;
  const principal = $('#principal');
  const capaMapa = $('#capa-mapa'), capaCruce = $('#capa-cruce');
  const analisis = $('#analisis'), franja = $('#franja');
  const rotuloPrincipal = $('#rotulo-principal'), rotuloFranja = $('#rotulo-franja');

  // ---------------------------------------------------------------- reloj del operador
  const horaDisp = display('00:00:00', { alto: 30 });
  $('#hora-bogota').append(horaDisp.el);
  const horaDia = $('#hora-dia');
  let diaPrevio = '';
  cadaCuadro((ms) => {
    const b = bogota(ms);
    const p = (x) => String(Math.floor(x)).padStart(2, '0');
    horaDisp.poner(`${p(b.hora)}${p(b.minuto)}${p(b.segundo)}`, 'var(--ambar)');
    const d = diaHorario(b);
    const txt = d.festivo ? `${NOMBRE_DIA[b.diaSemana]}|Festivo: ${d.festivo}` : `${NOMBRE_DIA[b.diaSemana]}|${d.fila === 'domingo' ? 'Domingo' : d.fila === 'sabado' ? 'Sábado' : 'Día hábil'} · Bogotá`;
    if (txt !== diaPrevio) { diaPrevio = txt; const [a, c] = txt.split('|'); horaDia.replaceChildren(a, h('b', {}, c)); }
  });

  // ---------------------------------------------------------------- fuentes
  const fuentesEl = $('#fuentes');
  const fuentes = new Map();
  const xs = sem.intersecciones.map((i) => i.centro.lon), ys = sem.intersecciones.map((i) => i.centro.lat);
  const bx = [Math.min(...xs), Math.max(...xs)], by = [Math.min(...ys), Math.max(...ys)];
  const puntos = sem.intersecciones.map((it) => {
    const x = 12 + ((it.centro.lon - bx[0]) / (bx[1] - bx[0])) * 76, y = 10 + ((by[1] - it.centro.lat) / (by[1] - by[0])) * 40;
    return { it, x, y, c: s('circle', { cx: x, cy: y, r: 2.6, fill: 'var(--rojo)' }) };
  });
  const miniMapa = s('svg', { viewBox: '0 0 100 60', preserveAspectRatio: 'xMidYMid meet', 'aria-hidden': 'true' },
    s('rect', { width: 100, height: 60, fill: '#070b0e' }),
    ...[15, 30, 45].map((y) => s('line', { x1: 0, x2: 100, y1: y, y2: y, stroke: '#111a20', 'stroke-width': 0.4 })),
    ...[20, 40, 60, 80].map((x) => s('line', { x1: x, x2: x, y1: 0, y2: 60, stroke: '#111a20', 'stroke-width': 0.4 })),
    ...puntos.map((p) => s('circle', { cx: p.x, cy: p.y, r: 5, fill: 'none', stroke: '#2b3843', 'stroke-width': 0.6 })),
    ...puntos.map((p) => p.c));
  const fMapa = fuenteMonitor('mapa', 'Mapa de la red', h('div', { class: 'fuente-mapa-lienzo', style: { width: '100%', height: '100%' } }, miniMapa), 'fuente-mapa');
  fuentesEl.append(fMapa.el);
  fuentes.set('mapa', fMapa);
  for (const it of sem.intersecciones) {
    const a = anillo(it, { tam: 'mini' });
    const plan = h('div', { class: 'fuente-plan num' });
    const leds = it.grupos.filter((g) => g.tipo !== 'peatonal').map(() => h('span', { class: 'led' }));
    const cuenta = display('00', { alto: 22 });
    const cuerpo = [h('div', { class: 'fuente-anillo' }, a.el), h('div', { class: 'fuente-txt' }, h('div', { class: 'fuente-nombre' }, it.nombre), plan,
      h('div', { class: 'fuente-pie' }, h('div', { class: 'fuente-leds' }, leds), h('div', { class: 'fuente-cuenta', title: 'Segundos para el próximo cambio de fase' }, cuenta.el)))];
    const f = fuenteMonitor(it.id, `${it.nombre} · ${it.controlador.equipo}/${it.controlador.cruce}`, cuerpo);
    Object.assign(f, { it, a, plan, leds, cuenta, prev: [] });
    fuentesEl.append(f.el);
    fuentes.set(it.id, f);
  }
  function fuenteMonitor(id, rotulo, cuerpo, clase = '') {
    const pantalla = h('div', { class: 'pantalla' }, cuerpo);
    const tally = h('span', { class: 'tally', 'aria-hidden': 'true' });
    const el = h('button', { type: 'button', class: `monitor fuente ${clase}`, 'aria-pressed': 'false',
      'aria-label': id === 'mapa' ? 'Llevar el mapa de la red a la pantalla principal' : `Llevar ${rotulo} a la pantalla principal` },
    pantalla, h('div', { class: 'rotulo' }, h('span', { class: 'rotulo-txt' }, rotulo), tally));
    el.addEventListener('click', () => ir(id));
    return { el, pantalla, tally };
  }
  cadaCuadro((ms) => {
    for (const [id, f] of fuentes) {
      if (id === 'mapa') continue;
      const v = vivo(f.it, ms);
      f.a.actualizar(v.t, v.plan);
      const txt = `${v.plan.id}|${v.plan.ciclo}`;
      if (f.plan.dataset.t !== txt) { f.plan.dataset.t = txt; f.plan.replaceChildren(h('b', {}, v.plan.id), h('span', { class: 'ciclo-largo' }, ' · ciclo'), ` ${v.plan.ciclo} s`); }
      const veh = f.it.grupos.filter((g) => g.tipo !== 'peatonal');
      veh.forEach((g, i) => {
        const e = luz(estado(v.plan.tiempos[g.id], g.tipo, v.t, v.plan.ciclo));
        if (f.prev[i] !== e) { f.prev[i] = e; f.leds[i].className = `led ${e}`; }
      });
      // cuenta regresiva: segundos para el próximo cambio de fase (etapas del plan)
      const et = v.plan.etapas.find((x) => dur(x.inicio, v.t, v.plan.ciclo) < x.duracion) || v.plan.etapas[0];
      const vehVerde = et.verdes.some((gid) => f.it.grupos.find((g) => g.id === gid)?.tipo !== 'peatonal');
      f.cuenta.poner(String(Math.ceil(dur(v.t, et.fin, v.plan.ciclo) || v.plan.ciclo)).padStart(2, ' ').slice(-2),
        vehVerde ? 'var(--verde)' : 'var(--rojo)');
      const pt = puntos.find((p) => p.it === f.it);
      const e0 = f.prev.includes('verde') ? 'var(--verde)' : f.prev.includes('amarillo') ? 'var(--ambar)' : 'var(--rojo)';
      if (pt.c.getAttribute('fill') !== e0) pt.c.setAttribute('fill', e0);
    }
  });

  // ---------------------------------------------------------------- pantalla principal: mapa
  let mapa = null;
  if (!new URLSearchParams(location.search).has('sinmapa')) try {
    mapa = crearMapa($('#mapa'), datos, {
      alElegirCruce: (id) => ir(id),
      alElegirEquipo: (eq) => { cambiar({ equipo: eq }); },
    });
  } catch (e) {
    console.error(e);
    $('#mapa').append(h('div', { class: 'aviso-carga error' }, 'No se pudo cargar el mapa base. El resto del muro funciona sin él.'));
  }
  cadaCuadro((ms) => { if (E.fuente === 'mapa' && mapa) mapa.actualizar(ms); });

  // ---------------------------------------------------------------- monitores por modo
  let modoActual = null, vistas = {};
  function montarMapa() {
    analisis.replaceChildren();
    analisis.style.gridTemplateRows = 'minmax(0, .82fr) minmax(0, 1.45fr)';
    const r = red(sem, (id) => ir(id));
    const f = ficha(sast, (id) => ir(id));
    analisis.append(r.el, f.el);
    f.mostrar(E.equipo);
    franja.replaceChildren();
    const hv = hoy(sem, Date.now(), (id, pid) => { ir(id, { plan: pid }); });
    franja.append(hv.el);
    rotuloFranja.textContent = `Programación de hoy · ${hv.dia}`;
    franja.title = 'Azul más claro = ciclo más largo. Clic en un bloque para explorar ese plan.';
    vistas = { r, f, hv };
  }
  function montarCruce(it) {
    const g = geo.intersecciones[it.id];
    capaCruce.replaceChildren();
    const sellos = h('div', { class: 'sellos' });
    const subt = `${it.direccion} · cámaras SAST ${it.equipos.map((e) => e.slice(-3)).join(' y ')}`;
    const cab = h('div', { class: 'cruce-cab' },
      h('div', { class: 'cruce-titulo' }, h('h2', {}, it.nombre, h('span', { class: 'codigo' }, `controlador ${it.controlador.equipo} · cruce ${it.controlador.cruce}`)), h('p', {}, subt)),
      sellos);
    const d = diagrama(it, g);
    // sin asignación validada, la pantalla grande explica con el reloj del ciclo a escala de muro
    let gigante = null;
    if (!Object.keys(g.trayectorias).length) {
      d.el.classList.add('atenuado');
      const ag = anillo(it, { tam: 'completo', fases: (p) => fasesDe(it, p) });
      const cap = h('p', { class: 'gigante-fase', 'aria-live': 'polite' });
      d.el.append(h('div', { class: 'gigante' }, h('div', { class: 'gigante-anillo' }, ag.el), cap));
      let fPrev = null;
      gigante = (t, p) => {
        ag.actualizar(t, p);
        const fs = fasesDe(it, p);
        const f = fs.find((x) => dur(x.inicio, t, p.ciclo) < x.duracion) || fs[0];
        if (f !== fPrev && f) { fPrev = f; cap.replaceChildren(h('b', {}, `${f.titulo}. `), f.texto); }
      };
    }
    const controles = h('div', { class: 'controles', role: 'toolbar', 'aria-label': 'Controles de la simulación' });
    capaCruce.append(h('div', { class: 'cruce' }, cab, d.el, controles));

    // sellos: modo, fase ilustrativa, borrador, vehículos
    const sModo = h('span', { class: 'sello vivo' }, h('span', { class: 'led-punto' }), 'En vivo');
    const sFase = h('span', { class: 'sello', title: sem.nota_fase, tabindex: 0 }, 'Fase ilustrativa');
    sellos.append(sModo, sFase);
    if (it.asignacion.estado === 'borrador') sellos.append(h('span', { class: 'sello borrador', title: 'Asignación grupo → acceso sin validar (decisión 28)' }, 'Borrador sin validar'));
    if (Object.keys(g.trayectorias).length) sellos.append(h('span', { class: 'sello', title: sem.nota_vehiculos }, 'Vehículos ilustrativos'));

    // controles
    const chips = h('div', { class: 'chips', role: 'group', 'aria-label': 'Plan' });
    const chipEls = it.planes.map((p) => {
      const b = h('button', { type: 'button', class: `chip${p.con_horario ? '' : ' sin-horario'}`, 'aria-pressed': 'false',
        title: p.con_horario ? `Explorar el plan ${p.id}` : 'Programado en el controlador, sin horario: no corre' },
        h('span', { class: 'ciclo-sw', style: { background: colorCiclo(p.ciclo) } }), `${p.id} · ${p.ciclo} s`, h('span', { class: 'vig', 'aria-hidden': 'true' }));
      b.addEventListener('click', () => explorar(it, { plan: p.id, t0: 0, real0: performance.now(), pausado: false }));
      chips.append(b);
      return { p, b, vig: b.lastChild };
    });
    const bVivo = h('button', { type: 'button', class: 'chip', 'aria-pressed': 'true', onclick: () => volverEnVivo() }, h('span', { class: 'led-punto', style: { background: 'var(--verde)', boxShadow: '0 0 6px var(--verde)' } }), 'En vivo');
    const bPlay = h('button', { type: 'button', class: 'chip ico-btn', 'aria-label': 'Pausar', html: ICO.pausa });
    bPlay.addEventListener('click', () => {
      if (E.modo === 'vivo') explorar(it, { pausado: true });
      else explorar(it, { pausado: !E.exp.pausado });
    });
    const paso = (dt) => () => { const v = tiempo(it); explorar(it, { t0: v.T + dt, pausado: true }); };
    const bAtras = h('button', { type: 'button', class: 'chip ico-btn', 'aria-label': 'Un segundo atrás', html: ICO.atras, onclick: paso(-1) });
    const bAdel = h('button', { type: 'button', class: 'chip ico-btn', 'aria-label': 'Un segundo adelante', html: ICO.adelante, onclick: paso(1) });
    const vel = h('div', { class: 'vel', role: 'group', 'aria-label': 'Velocidad' });
    const velEls = [1, 2, 5, 10].map((x) => {
      const b = h('button', { type: 'button', class: 'chip', 'aria-pressed': 'false', onclick: () => explorar(it, { vel: x, pausado: false }) }, `×${x}`);
      vel.append(b); return { x, b };
    });
    const bMapa = h('button', { type: 'button', class: 'chip volver', onclick: () => ir('mapa') }, h('span', { html: ICO.mapa, style: { display: 'inline-flex', width: '14px' } }), 'Mapa');
    cab.querySelector('.cruce-titulo').prepend(bMapa);
    controles.append(chips, h('span', { class: 'sep' }), bVivo, bAtras, bPlay, bAdel, vel);

    // monitores de análisis
    analisis.replaceChildren();
    analisis.style.gridTemplateRows = 'minmax(0, 1fr) minmax(170px, .9fr) minmax(0, 1.3fr)';
    const rel = reloj(it, (p) => fasesDe(it, p));
    const cab2 = cabezasMon(it, (gid) => rel.enfocar(gid));
    const ex = explicacionMon(it, { alElegirPlan: (pid) => explorar(it, { plan: pid, t0: 0, real0: performance.now(), pausado: false }) });
    analisis.append(rel.el, cab2.el, ex.el);
    franja.replaceChildren();
    const gt = gantt(it, { alArrastrar: (t, pausar) => {
      const v = tiempo(it);
      const base = Math.floor(v.T / v.plan.ciclo) * v.plan.ciclo;
      explorar(it, { plan: v.plan.id, t0: base + t, pausado: pausar });
    } });
    franja.append(gt.el);
    rotuloFranja.textContent = `Línea de tiempo del ciclo · ${it.nombre}`;
    franja.title = 'Arrastre el cursor (o use ← →) para recorrer el ciclo.';

    let ctrlPrevio = '';
    function refrescarControles(v) {
      const clave = `${E.modo}|${v.plan.id}|${E.exp.pausado}|${E.exp.vel}|${v.vigente.plan}`;
      if (clave === ctrlPrevio) return;
      ctrlPrevio = clave;
      for (const c of chipEls) {
        c.b.setAttribute('aria-pressed', String(E.modo === 'explorar' && c.p.id === v.plan.id));
        c.b.classList.toggle('vigente', c.p.id === v.vigente.plan);
        c.b.title = c.p.id === v.vigente.plan ? `${c.p.id}: el plan que rige ahora` : c.p.con_horario ? `Explorar el plan ${c.p.id}` : 'Programado en el controlador, sin horario: no corre';
      }
      bVivo.setAttribute('aria-pressed', String(E.modo === 'vivo'));
      const pausado = E.modo === 'explorar' && E.exp.pausado;
      bPlay.innerHTML = pausado ? ICO.play : ICO.pausa;
      bPlay.setAttribute('aria-label', pausado ? 'Reproducir' : 'Pausar');
      for (const ve of velEls) ve.b.setAttribute('aria-pressed', String(E.modo === 'explorar' && E.exp.vel === ve.x));
      sModo.replaceChildren(h('span', { class: 'led-punto' }), E.modo === 'vivo' ? 'En vivo' : `Explorando ${v.plan.id}${pausado ? ' · pausa' : ` · ×${String(Math.round(E.exp.vel * 10) / 10).replace('.', ',')}`}`);
      sModo.classList.toggle('vivo', E.modo === 'vivo');
    }
    vistas = { it, d, rel, cab2, ex, gt, refrescarControles, gigante };
    requestAnimationFrame(() => { d.medir(); if (!reducido()) d.encender(); });
  }

  cadaCuadro((ms) => {
    if (modoActual === 'mapa') {
      vistas.r?.actualizar(ms);
      vistas.hv?.ahora(bogota(ms).minutos);
    } else if (vistas.it) {
      const v = tiempo(vistas.it, ms);
      vistas.d.actualizar(v.T, v.t, v.plan, ms);
      vistas.gigante?.(v.t, v.plan);
      vistas.rel.actualizar(v.t, v.plan);
      vistas.cab2.actualizar(v.t, v.plan);
      vistas.ex.actualizar(v.t, v.plan, v, ms);
      vistas.gt.actualizar(v.t, v.plan);
      vistas.refrescarControles(v);
    }
  });

  // ---------------------------------------------------------------- cambio de fuente (firma)
  function ir(id, { plan = null } = {}) {
    if (plan) cambiar({ fuente: id, modo: 'explorar', exp: { plan, t0: 0, real0: performance.now(), vel: 1, pausado: false } });
    else cambiar({ fuente: id, ...(id === 'mapa' ? {} : { modo: 'vivo' }) });
  }

  /** El monitor elegido vuela a la pantalla principal. No bloquea: el contenido nuevo se monta
   *  con un temporizador real, así un equipo lento nunca se queda esperando la animación. */
  function volar(desde, hacia) {
    if (reducido() || !window.gsap) return 0;
    const a = desde.getBoundingClientRect(), b = hacia.getBoundingClientRect();
    const fantasma = h('div', { class: 'vuelo' });
    const clon = desde.firstElementChild?.cloneNode(true);
    if (clon) { clon.style.width = '100%'; clon.style.height = '100%'; fantasma.append(clon); }
    Object.assign(fantasma.style, { left: `${a.left}px`, top: `${a.top}px`, width: `${a.width}px`, height: `${a.height}px` });
    document.body.append(fantasma);
    window.gsap.timeline({ onComplete: () => fantasma.remove() })
      .to(fantasma, { left: b.left, top: b.top, width: b.width, height: b.height, duration: 0.55, ease: 'expo.inOut' })
      .to(fantasma, { opacity: 0, duration: 0.3 });
    setTimeout(() => fantasma.remove(), 1600);
    return 380;
  }

  async function aplicar() {
    const destino = E.fuente;
    if (destino === modoActual || (destino !== 'mapa' && vistas.it?.id === destino && modoActual === 'cruce')) {
      if (modoActual === 'mapa') { vistas.f?.mostrar(E.equipo); mapa?.seleccionarEquipo(E.equipo); }
      return;
    }
    // bus de sala: la fuente elegida pasa por «preview» (verde) antes de salir «al aire» (rojo)
    for (const [id, f] of fuentes) {
      const on = id === destino;
      f.el.setAttribute('aria-pressed', String(on));
      f.tally.classList.remove('on', 'pvw');
      if (on && modoActual !== null && !reducido()) {
        f.tally.classList.add('pvw');
        setTimeout(() => { f.tally.classList.remove('pvw'); if (E.fuente === id) f.tally.classList.add('on'); }, 320);
      } else f.tally.classList.toggle('on', on);
    }
    const origen = fuentes.get(destino)?.pantalla;
    const primera = modoActual === null;
    const espera = !primera && origen ? volar(origen, principal) : 0;
    if (espera) await new Promise((ok) => setTimeout(ok, espera));
    if (E.fuente !== destino) return;   // otro clic llegó mientras volaba
    if (destino === 'mapa') {
      capaCruce.hidden = true; capaCruce.replaceChildren(); vistas.d?.destruir();
      capaMapa.hidden = false;
      modoActual = 'mapa';
      montarMapa();
      rotuloPrincipal.textContent = 'Pantalla principal · Mapa de la red';
      mapa?.resize();
      mapa?.seleccionarEquipo(E.equipo);
    } else {
      const it = inter(destino);
      capaMapa.hidden = true;
      capaCruce.hidden = false;
      modoActual = 'cruce';
      montarCruce(it);
      rotuloPrincipal.textContent = `Pantalla principal · ${it.nombre} · ${it.controlador.equipo}/${it.controlador.cruce}`;
    }
    principal.focus({ preventScroll: true });
  }
  suscribir(() => aplicar());
  return { aplicar, ir, mapa: () => mapa, vistas: () => vistas, fuentes };
}
