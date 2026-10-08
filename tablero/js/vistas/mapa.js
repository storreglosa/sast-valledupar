// Mapa de la red (pantalla grande del muro): semáforos como mini-relojes vivos y cámaras SAST.
import * as maplibregl from '../../vendor/maplibre-gl-6.11.1/maplibre-gl.mjs';
import { h } from '../util/dom.js';
import { anillo } from './anillo.js';
import { vivo } from '../estado.js';

const ESTILO = 'https://tiles.openfreemap.org/styles/dark';

const CAMARA = (op) => `<svg viewBox="0 0 30 30" aria-hidden="true">
  ${op ? '<path class="cam-cono" d="M15 15 L29 7 A16 16 0 0 1 29 23 Z" fill="var(--sast)" opacity=".22"/>' : '<circle cx="15" cy="15" r="13" fill="none" stroke="#7d8b95" stroke-dasharray="2.5 2.5"/>'}
  <rect class="cam-cuerpo" x="7" y="10.5" width="13" height="9" rx="2" fill="${op ? 'var(--sast)' : '#0a0f13'}" stroke="${op ? '#ffd2b0' : '#a9b6bf'}" stroke-width="1"/>
  <path d="M20 13l4-2v8l-4-2z" fill="${op ? 'var(--sast)' : '#0a0f13'}" stroke="${op ? '#ffd2b0' : '#a9b6bf'}" stroke-width="1"/>
  <circle cx="11.5" cy="15" r="2" fill="${op ? '#3a1f0c' : '#a9b6bf'}"/>
  ${op ? '' : '<path d="M6 24L24 6" stroke="#a9b6bf" stroke-width="1.3"/>'}
</svg>`;
export const ICONO_CAMARA = CAMARA;

export function crearMapa(contenedor, datos, { alElegirCruce, alElegirEquipo }) {
  const { sem, sast } = datos;
  const urbanos = sast.equipos.features.filter((f) => f.properties.solicitud !== 1).map((f) => f.geometry.coordinates);
  const todos = sast.equipos.features.map((f) => f.geometry.coordinates);
  const caja = (pts) => pts.reduce((b, [x, y]) => [[Math.min(b[0][0], x), Math.min(b[0][1], y)], [Math.max(b[1][0], x), Math.max(b[1][1], y)]], [[180, 90], [-180, -90]]);

  const margen = () => (window.innerWidth < 760 ? { top: 70, bottom: 60, left: 70, right: 70 } : 90);
  const mapa = new maplibregl.Map({
    container: contenedor, style: ESTILO, bounds: caja(urbanos), fitBoundsOptions: { padding: margen() },
    attributionControl: { compact: true }, maxZoom: 19, minZoom: 10, pitchWithRotate: true, dragRotate: true,
  });
  mapa.addControl(new maplibregl.NavigationControl({ showCompass: true, visualizePitch: true }), 'top-right');

  // el estilo de OpenFreeMap pide imágenes que no trae su sprite: se resuelven con una transparente
  mapa.setMissingStyleImageResolver((id) => {
    if (!mapa.hasImage(id)) mapa.addImage(id, { width: 1, height: 1, data: new Uint8Array(4) });
  });
  mapa.on('style.load', () => {
    // un poco más oscuro y sobrio para que manden las luces
    for (const l of mapa.getStyle().layers) {
      try {
        if (l.type === 'background') mapa.setPaintProperty(l.id, 'background-color', '#070a0d');
        if (l.type === 'symbol' && /poi/.test(l.id)) mapa.setLayoutProperty(l.id, 'visibility', 'none');
      } catch { /* capa sin esa propiedad */ }
    }
  });

  // ---------------------------------------------------------------- cámaras SAST
  const camaras = [];
  for (const f of sast.equipos.features) {
    const p = f.properties;
    const op = p.estado === 'Operando';
    const el = h('button', { type: 'button', class: `mk-cam${op ? '' : ' inactiva'}`, html: CAMARA(op),
      'aria-label': `Equipo SAST ${p.numero}, ${p.punto}, ${op ? 'operando' : 'autorizado, no opera'}` });
    el.addEventListener('click', (ev) => { ev.stopPropagation(); alElegirEquipo(p.equipo); });
    camaras.push({ p, el, mk: new maplibregl.Marker({ element: el }).setLngLat(f.geometry.coordinates).addTo(mapa) });
  }

  // ---------------------------------------------------------------- semáforos (mini-relojes vivos)
  const semaforos = sem.intersecciones.map((it) => {
    const a = anillo(it, { tam: 'mini' });
    const nombre = h('span', { class: 'mk-nombre' }, it.nombre, h('b', {}, ''));
    const el = h('button', { type: 'button', class: 'mk-sem', 'aria-label': `Semáforo ${it.nombre}: llevar a la pantalla principal` }, a.el, nombre);
    el.addEventListener('click', (ev) => { ev.stopPropagation(); alElegirCruce(it.id); });
    const mk = new maplibregl.Marker({ element: el, anchor: 'center' }).setLngLat([it.centro.lon, it.centro.lat]).addTo(mapa);
    return { it, a, nombre, mk };
  });

  // ---------------------------------------------------------------- leyenda y acciones
  const leyenda = h('div', { class: 'leyenda', role: 'group', 'aria-label': 'Leyenda' },
    h('div', {}, h('span', { class: 'leyenda-ico', html: '<svg viewBox="0 0 22 22"><circle cx="11" cy="11" r="9" fill="none" stroke="#1fe08a" stroke-width="3"/><circle cx="11" cy="11" r="5" fill="none" stroke="#ff3b30" stroke-width="3" opacity=".7"/><path d="M11 11V1" stroke="#fff" stroke-width="1.6"/></svg>' }), 'Semáforo: reloj del ciclo (fase ilustrativa)'),
    h('div', {}, h('span', { class: 'leyenda-ico', html: CAMARA(true) }), 'Cámara SAST operando'),
    h('div', {}, h('span', { class: 'leyenda-ico', html: CAMARA(false) }), 'Cámara SAST autorizada, sin operar'));
  let vistaTodos = false;
  const btnTodos = h('button', { type: 'button', class: 'btn btn-mini', onclick: () => {
    vistaTodos = !vistaTodos;
    mapa.fitBounds(caja(vistaTodos ? todos : urbanos), { padding: margen(), duration: 1400 });
    btnTodos.textContent = vistaTodos ? 'Ver la ciudad' : 'Ver también El Zanjón';
  } }, 'Ver también El Zanjón');
  const sello = h('span', { class: 'sello sello-mapa', tabindex: 0, title: 'El plan es el que rige a esta hora; el segundo del ciclo no está sincronizado con el controlador.' }, 'Fase ilustrativa');
  contenedor.parentElement.append(leyenda, sello, h('div', { class: 'mapa-acciones' }, btnTodos));

  // etiquetas sin choque: si dos semáforos quedan cerca en pantalla, la del de arriba sube
  function acomodar() {
    const pos = semaforos.map((x) => ({ x, p: mapa.project([x.it.centro.lon, x.it.centro.lat]) }));
    for (const a of pos) a.x.mk.getElement().classList.remove('arriba');
    for (let i = 0; i < pos.length; i++) for (let j = i + 1; j < pos.length; j++) {
      const a = pos[i], b = pos[j];
      if (Math.abs(a.p.x - b.p.x) < 140 && Math.abs(a.p.y - b.p.y) < 60) (a.p.y <= b.p.y ? a : b).x.mk.getElement().classList.add('arriba');
    }
  }
  mapa.on('moveend', acomodar);
  mapa.on('load', acomodar);

  function actualizar(ms) {
    for (const s of semaforos) {
      const v = vivo(s.it, ms);
      s.a.actualizar(v.t, v.plan);
      const txt = `${v.plan.id} · ${v.plan.ciclo} s`;
      if (s.nombre.lastChild.textContent !== txt) s.nombre.lastChild.textContent = txt;
    }
  }
  function seleccionarEquipo(eq) { for (const c of camaras) c.el.classList.toggle('sel', c.p.equipo === eq); }
  function volarA(it, opts = {}) {
    mapa.flyTo({ center: [it.centro.lon, it.centro.lat], zoom: 17.2, pitch: 48, bearing: opts.bearing ?? 0, duration: opts.duracion ?? 2600, essential: true });
  }
  function vistaGeneral(duracion = 1800) { mapa.fitBounds(caja(urbanos), { padding: margen(), pitch: 0, bearing: 0, duration: duracion }); }
  return { mapa, actualizar, seleccionarEquipo, volarA, vistaGeneral, resize: () => mapa.resize() };
}
