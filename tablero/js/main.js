// Arranque del muro: carga los datos, valida su esquema, monta el muro y el bucle único.
import { $, h } from './util/dom.js';
import { E, cambiar, leerRuta, arrancarBucle, escribiendoRuta } from './estado.js';
import { crearMuro } from './vistas/muro.js';
import { presentacion } from './vistas/presentacion.js';

const ESQUEMAS = { semaforos: 'tablero-semaforos/1', geometria: 'tablero-geometria/1', sast: 'tablero-sast/1' };

async function cargar(nombre) {
  const r = await fetch(`data/${nombre}.json`, { cache: 'no-cache' });
  if (!r.ok) throw new Error(`No se pudo leer data/${nombre}.json (${r.status})`);
  const d = await r.json();
  if (d.esquema !== ESQUEMAS[nombre]) throw new Error(`data/${nombre}.json trae el esquema «${d.esquema}», se esperaba «${ESQUEMAS[nombre]}»`);
  return d;
}

async function iniciar() {
  const aviso = $('#aviso-carga');
  // ?ahora=2026-10-12T15:00:00-05:00 fija la hora (pruebas y demostraciones)
  const q = new URLSearchParams(location.search);
  if (q.get('ahora') && !Number.isNaN(Date.parse(q.get('ahora')))) E.offsetMs = Date.parse(q.get('ahora')) - Date.now();
  let sem, geo, sast;
  try {
    [sem, geo, sast] = await Promise.all(['semaforos', 'geometria', 'sast'].map(cargar));
  } catch (e) {
    aviso.classList.add('error');
    aviso.textContent = `No se pudo encender el muro: ${e.message}.`;
    console.error(e);
    return;
  }
  E.datos = { sem, geo, sast };
  await new Promise((ok) => (window.gsap ? ok() : window.addEventListener('load', ok, { once: true })));
  const muro = crearMuro(E.datos);
  const pres = presentacion(muro);
  arrancarBucle();
  window.__tablero.muro = muro;
  const r = leerRuta();
  cambiar({ fuente: r.fuente, equipo: r.equipo, modo: r.modo, ...(r.exp ? { exp: r.exp } : {}) });
  aviso.remove();
  if (r.presentar) pres.iniciar();

  window.addEventListener('hashchange', () => {
    if (escribiendoRuta()) return;
    const x = leerRuta();
    if (x.presentar) { pres.iniciar(); return; }
    cambiar({ fuente: x.fuente, equipo: x.equipo, modo: x.modo, ...(x.exp ? { exp: x.exp } : {}) }, { ruta: false });
  });
  $('#btn-presentar').addEventListener('click', () => (pres.activa() ? pres.terminar() : pres.iniciar()));

  const dlg = $('#acerca');
  $('#btn-acerca').addEventListener('click', () => {
    const cuerpo = $('#acerca-cuerpo');
    cuerpo.replaceChildren(
      h('p', {}, h('b', {}, 'Tiempos semafóricos. '), `${sem.fuente}. Cada plan trae los tiempos de inicio y fin del verde y del amarillo de cada grupo; el horario semanal sale de la grilla del controlador.`),
      h('p', {}, h('b', {}, 'Grupos y accesos. '), 'Los nombres de los grupos («Flujo 2», «Peatonal 22») siguen la codificación de trayectorias del Manual de Planeación y Diseño para la Administración del Tránsito y el Transporte (SDM Bogotá, 2005, Tomo III, num. 5.2.1).'),
      h('p', {}, h('b', {}, 'En vivo. '), sem.nota_fase),
      h('p', {}, h('b', {}, 'Simulación. '), sem.nota_vehiculos, ' Las cabezas muestran lo que se ve en campo: la preparación de 2 s antes del verde es rojo y el último segundo peatonal es rojo intermitente.'),
      h('p', {}, h('b', {}, 'Equipos SAST y línea base. '), `${sast.criterio} Cortes: siniestros ${sast.cortes.siniestros}, comparendos ${sast.cortes.comparendos}.`),
      h('p', {}, h('b', {}, 'Mapa. '), 'Mapa base OpenFreeMap con datos de OpenStreetMap. ', geo.atribucion, '.'),
      h('p', {}, 'Secretaría de Tránsito y Transporte de Valledupar. Datos al corte del ', sem.generado, '.'));
    dlg.showModal();
  });

  // atajos: espacio pausa la simulación del cruce en pantalla
  window.addEventListener('keydown', (ev) => {
    if (pres.activa() || ev.target.closest('input, textarea, [role="slider"]')) return;
    if (ev.key === ' ' && E.fuente !== 'mapa') {
      ev.preventDefault();
      document.querySelector('.controles .ico-btn[aria-label="Pausar"], .controles .ico-btn[aria-label="Reproducir"]')?.click();
    }
  });
}

iniciar();
