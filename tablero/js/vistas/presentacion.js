// Modo presentación: un recorrido automático por los cinco cruces para mostrarlo en reunión.
// Una sola línea de tiempo GSAP: vuelo del mapa, cambio de pantalla, un ciclo completo acelerado
// con subtítulos que siguen a la aguja, y el contraste con el plan de la noche.
// Espacio pausa, ← → saltan de cruce, Esc sale.
import { $ } from '../util/dom.js';
import { E, cambiar, tiempo, cadaCuadro } from '../estado.js';
import { resumen } from '../nucleo/explicacion.js';
import { planVigente } from '../nucleo/horario.js';

const CICLO_EN_PANTALLA = 24; // s reales para recorrer un ciclo completo

export function presentacion(muro) {
  const sub = $('#subtitulos');
  let tl = null, cruceActual = null, fasesActuales = null, textoPrevio = '';
  const decir = (html) => {
    if (html === textoPrevio) return;
    textoPrevio = html;
    sub.innerHTML = html;
    sub.classList.remove('entra'); void sub.offsetWidth; sub.classList.add('entra');
  };

  cadaCuadro(() => {
    if (!E.presentando || !cruceActual || E.fuente !== cruceActual.id || !fasesActuales) return;
    const v = tiempo(cruceActual);
    const f = fasesActuales.find((x) => (x.inicio < x.fin ? v.t >= x.inicio && v.t < x.fin : v.t >= x.inicio || v.t < x.fin));
    if (f) decir(`<b>${f.titulo}.</b> ${f.texto}`);
  });

  function iniciar() {
    if (!window.gsap) return;
    const sem = E.datos.sem;
    document.body.classList.add('presentando');
    cambiar({ presentando: true, fuente: 'mapa', equipo: null });
    sub.hidden = false;
    document.documentElement.requestFullscreen?.().catch(() => {});
    const mapa = muro.mapa();
    tl = window.gsap.timeline({ onComplete: terminar });
    tl.addLabel('inicio')
      .call(() => { cruceActual = null; mapa?.vistaGeneral(1600); decir('<b>Cinco cruces semaforizados con cámaras SAST.</b> Cada reloj del mapa es el ciclo de un semáforo, girando en vivo con el plan que rige a esta hora.'); })
      .to({}, { duration: 7 });
    for (const it of sem.intersecciones) {
      const vig = planVigente(it.horario, Date.now() + E.offsetMs);
      const plan = it.planes.find((p) => p.id === vig.plan);
      const r = resumen(it, plan, vig);
      const primera = r.fases.find((f) => f.tipo === 'vehicular') || r.fases[0];
      tl.addLabel(it.id)
        .call(() => {
          cruceActual = null; fasesActuales = null;
          cambiar({ fuente: 'mapa' });
          mapa?.volarA(it, { duracion: 2400 });
          decir(`<b>${it.nombre}.</b> ${it.direccion} · controlador ${it.controlador.equipo}.`);
        })
        .to({}, { duration: 3 })
        .call(() => {
          decir(`<b>${it.nombre}.</b> ${r.intro} ${r.ciclo}`);
          cambiar({ fuente: it.id, modo: 'explorar', exp: { plan: plan.id, t0: primera.inicio, real0: performance.now(), vel: plan.ciclo / CICLO_EN_PANTALLA, pausado: false } });
        })
        .to({}, { duration: 4 })
        .call(() => { cruceActual = it; fasesActuales = r.fases; })
        .to({}, { duration: CICLO_EN_PANTALLA - 4 })
        .call(() => { cruceActual = null; decir(r.noche ? `<b>De noche.</b> ${r.noche}` : r.espera); })
        .to({}, { duration: 5 });
    }
    tl.addLabel('fin')
      .call(() => { cruceActual = null; cambiar({ fuente: 'mapa', modo: 'vivo' }); mapa?.vistaGeneral(1600);
        decir(`<b>Fase ilustrativa.</b> El plan es el real de cada hora; el segundo del ciclo no está sincronizado con el controlador. Fuente: reportes SISTRA del 29/09/2026.`); })
      .to({}, { duration: 8 });
    window.addEventListener('keydown', teclas);
    $('#btn-presentar').setAttribute('aria-pressed', 'true');
  }

  function teclas(ev) {
    if (!tl) return;
    if (ev.key === ' ') {
      ev.preventDefault();
      const pausar = !tl.paused();
      tl.paused(pausar);
      const it = E.datos.sem.intersecciones.find((i) => i.id === E.fuente);
      if (E.modo === 'explorar' && it) cambiar({ exp: { ...E.exp, t0: tiempo(it).T, real0: performance.now(), pausado: pausar } });
    } else if (ev.key === 'ArrowRight') { ev.preventDefault(); saltar(1); }
    else if (ev.key === 'ArrowLeft') { ev.preventDefault(); saltar(-1); }
    else if (ev.key === 'Escape') terminar();
  }
  function saltar(dir) {
    const etiquetas = Object.entries(tl.labels).sort((a, b) => a[1] - b[1]);
    const t = tl.time();
    let i = etiquetas.findIndex(([, v]) => v > t + 0.01) - 1;
    if (i < 0) i = etiquetas.length - 1;
    const j = Math.max(0, Math.min(etiquetas.length - 1, i + dir));
    tl.play(etiquetas[j][1]);
  }
  function terminar() {
    if (!tl) return;
    tl.kill(); tl = null;
    cruceActual = null; fasesActuales = null; textoPrevio = '';
    sub.hidden = true;
    document.body.classList.remove('presentando');
    window.removeEventListener('keydown', teclas);
    if (document.fullscreenElement) document.exitFullscreen?.();
    $('#btn-presentar').setAttribute('aria-pressed', 'false');
    cambiar({ presentando: false, modo: 'vivo' });
  }
  return { iniciar, terminar, activa: () => !!tl };
}

