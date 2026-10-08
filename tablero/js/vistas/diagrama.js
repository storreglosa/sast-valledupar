// Diagrama del cruce en la pantalla principal: geometría OSM en metros (orientada con el acceso
// «norte» de la codificación hacia arriba, como la figura del manual SDM), cajón amarillo, cebras,
// líneas de pare, cabezas semafóricas con contador y la microsimulación ilustrativa en canvas.
import { h, s } from '../util/dom.js';
import { cabeza } from './cabezas.js';
import { estado, luz, restanteVisible } from '../nucleo/tiempos.js';
import { crearSim, trazo, puntoEn } from '../simulacion/trafico.js';
import { bogota } from '../nucleo/horario.js';

const R_VISTA = 31;   // media altura visible (m)

export function diagrama(it, geo, { alAnunciar } = {}) {
  const n = (geo.norte * Math.PI) / 180;
  const cosn = Math.cos(-n), sinn = Math.sin(-n);
  // metros (x este, y norte de la cuadrícula) -> plano de la codificación (x der, y abajo)
  const rot = (x, y) => [x * cosn + y * sinn, x * sinn - y * cosn];

  const raiz = h('div', { class: 'diagrama', role: 'img', 'aria-label': `Diagrama del cruce ${it.nombre}` });
  const base = s('svg', { class: 'base', viewBox: `${-R_VISTA} ${-R_VISTA} ${2 * R_VISTA} ${2 * R_VISTA}`, preserveAspectRatio: 'xMidYMid slice' });
  const lienzo = h('canvas');
  const sobre = h('div', { class: 'sobre' });
  raiz.append(base, lienzo, sobre);

  // ---------------------------------------------------------------- base en SVG (metros)
  const mundo = s('g', { transform: `rotate(${-geo.norte}) scale(1 -1)` });
  const defs = s('defs', {},
    s('pattern', { id: `caj-${it.id}`, width: 2.2, height: 2.2, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' },
      s('path', { d: 'M0 1.1H2.2M1.1 0V2.2', stroke: 'var(--cajon)', 'stroke-width': 0.16, opacity: 0.75 })));
  base.append(defs, mundo);
  const pts = (p) => p.map(([x, y]) => `${x},${y}`).join(' ');
  const gCordon = s('g'), gAsfalto = s('g'), gMarcas = s('g'), gCajon = s('g'), gCebras = s('g'), gPare = s('g');
  mundo.append(gCordon, gAsfalto, gMarcas, gCajon, gCebras, gPare);
  const trazos = [];
  for (const v of geo.vias) {
    const w = v.ctx ? Math.max(4.5, v.ancho * 0.8) : v.ancho;
    gCordon.append(s('polyline', { points: pts(v.p), fill: 'none', stroke: v.ctx ? '#1b2126' : '#2b353e', 'stroke-width': w + 0.7, 'stroke-linejoin': 'round' }));
    const asf = s('polyline', { points: pts(v.p), fill: 'none', stroke: v.ctx ? '#12161a' : '#1a2025', 'stroke-width': w, 'stroke-linejoin': 'round' });
    gAsfalto.append(asf);
    trazos.push({ el: asf, largo: trazo(v.p).largo });
    if (v.ctx) continue;
    if (!v.unico) gMarcas.append(s('polyline', { points: pts(v.p), fill: 'none', stroke: 'var(--cajon)', 'stroke-width': 0.16, 'stroke-dasharray': '3 3', opacity: 0.7 }));
    else if (v.ancho >= 6) gMarcas.append(s('polyline', { points: pts(v.p), fill: 'none', stroke: '#dfe5e9', 'stroke-width': 0.13, 'stroke-dasharray': '3 4', opacity: 0.55 }));
    if (v.unico) {
      const tr = trazo(v.p);
      for (let d = 0; d < tr.largo; d += 2) {
        const q = puntoEn(tr, d);
        const r = Math.hypot(q.x, q.y);
        if (r > 20 && r < 44 && Math.round(d) % 22 === 0) {
          const a = (q.ang * 180) / Math.PI;
          gMarcas.append(s('path', { d: 'M-1.6 -0.35H0.4V-0.8L1.6 0L0.4 0.8V0.35H-1.6Z', fill: '#dfe5e9', opacity: 0.55,
            transform: `translate(${q.x} ${q.y}) rotate(${a})` }));
        }
      }
    }
  }
  // limpiar marcas dentro del cruce
  const radioCaja = Math.min(...geo.brazos.filter((b) => b.r_caja).map((b) => b.r_caja), 12);
  const mascara = s('mask', { id: `msk-${it.id}`, maskUnits: 'userSpaceOnUse', x: -200, y: -200, width: 400, height: 400 },
    s('rect', { x: -200, y: -200, width: 400, height: 400, fill: '#fff' }),
    geo.cajon ? s('polygon', { points: pts(geo.cajon), fill: '#000' }) : s('circle', { r: radioCaja - 1, fill: '#000' }));
  defs.append(mascara);
  gMarcas.setAttribute('mask', `url(#msk-${it.id})`);
  if (geo.cajon) {
    gCajon.append(s('polygon', { points: pts(geo.cajon), fill: `url(#caj-${it.id})`, stroke: 'var(--cajon)', 'stroke-width': 0.3, opacity: 0.85 }));
  }
  const cebras = [];
  for (const z of geo.cebras) {
    const [a, b] = z.eje;
    const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const u = [(z.poligono[3][0] - z.poligono[0][0]) / 4, (z.poligono[3][1] - z.poligono[0][1]) / 4];
    const g = s('g', { class: 'cebra', opacity: z.grupo ? 0.9 : 0.55 });
    for (let f = 0.35; f < L; f += 1.0) {
      const p = [a[0] + ((b[0] - a[0]) * f) / L, a[1] + ((b[1] - a[1]) * f) / L];
      g.append(s('line', { x1: p[0] - u[0] * 2, y1: p[1] - u[1] * 2, x2: p[0] + u[0] * 2, y2: p[1] + u[1] * 2, stroke: '#e6ebee', 'stroke-width': 0.5 }));
    }
    gCebras.append(g);
    cebras.push(g);
  }
  for (const [gid, l] of Object.entries(geo.pare)) {
    gPare.append(s('line', { x1: l[0][0], y1: l[0][1], x2: l[1][0], y2: l[1][1], stroke: '#f1f4f6', 'stroke-width': 0.45, 'data-g': gid }));
  }
  // rosa con el norte real
  const rosa = s('svg', { class: 'diag-norte', viewBox: '-24 -24 48 48', 'aria-label': 'Norte' },
    s('g', { transform: `rotate(${-geo.norte})` },
      s('circle', { r: 20, fill: 'rgba(5,7,10,.6)', stroke: '#2b343c' }),
      s('path', { d: 'M0 -16L5 3H-5Z', fill: 'var(--tinta)' }), s('path', { d: 'M0 16L5 3H-5Z', fill: '#3b4650' }),
      s('text', { y: -6, 'text-anchor': 'middle', transform: 'translate(0 -6)', class: 'r-g', fill: '#000' }, '')),
    s('text', { x: 0, y: 4, 'text-anchor': 'middle', class: 'r-g', style: 'fill: var(--tinta)' }, 'N'));
  raiz.append(rosa);

  // ---------------------------------------------------------------- cabezas (HTML, tamaño fijo en pantalla)
  const cabezas = [];
  for (const g of it.grupos) {
    let ancla = null;
    const tr = geo.trayectorias[g.id];
    if (geo.pare[g.id] && tr) {
      // sobre el andén derecho, 2 m aguas arriba de la línea de pare
      const t = trazo(tr.puntos);
      const q = puntoEn(t, Math.max(0, tr.s_pare - 2.5));
      const [p0, p1] = geo.pare[g.id];
      const ancho = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]);
      const lado = ancho / 2 + 2.6;
      ancla = [q.x + Math.sin(q.ang) * lado, q.y - Math.cos(q.ang) * lado];
    } else {
      const z = geo.cebras.find((c) => c.grupo === g.id);
      if (z) {
        const [a, b] = z.eje;
        const dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1;
        const u = [(z.poligono[3][0] - z.poligono[0][0]) / 4, (z.poligono[3][1] - z.poligono[0][1]) / 4];
        ancla = [b[0] + (dx / L) * 1.8 + u[0] * 3.2, b[1] + (dy / L) * 1.8 + u[1] * 3.2];
      }
    }
    if (!ancla) continue;
    const c = cabeza(g);
    const tag = h('div', { class: 'cab-tag' }, g.tipo === 'peatonal' ? (g.mov?.codigo || g.id) : g.id);
    const el = h('div', { class: `cab ${g.tipo === 'peatonal' ? 'peat-cab' : ''}`, 'data-g': g.id }, c.el, tag);
    sobre.append(el);
    cabezas.push({ g, c, el, ancla });
  }

  let nota = null;
  if (!Object.keys(geo.trayectorias).length) {
    nota = h('div', { class: 'diag-nota' }, 'Asignación de grupos a accesos pendiente de validación: los vehículos y las cabezas sobre el cruce aparecen cuando se valide (decisión 28).');
    raiz.append(nota);
  }

  // ---------------------------------------------------------------- proyección y canvas
  let W = 0, H = 0, k = 1, dpr = 1;
  const ctx = lienzo.getContext('2d');
  function medir() {
    const r = raiz.getBoundingClientRect();
    W = r.width; H = r.height;
    if (!W || !H) return;
    k = Math.min(W, H) / (2 * R_VISTA);
    // el SVG usa todo el rectángulo: misma escala que el canvas y las cabezas
    base.setAttribute('viewBox', `${-W / 2 / k} ${-H / 2 / k} ${W / k} ${H / k}`);
    dpr = Math.min(2, window.devicePixelRatio || 1);
    lienzo.width = Math.round(W * dpr); lienzo.height = Math.round(H * dpr);
    const pos = cabezas.map((cb) => aPantalla(cb.ancla[0], cb.ancla[1]));
    // que no se monten: empuje simple entre pares cercanos
    for (let it2 = 0; it2 < 6; it2++) {
      for (let i = 0; i < pos.length; i++) for (let j = i + 1; j < pos.length; j++) {
        const dx = pos[j][0] - pos[i][0], dy = pos[j][1] - pos[i][1], d = Math.hypot(dx, dy) || 0.1;
        const min = 50;
        if (d < min) { const e = (min - d) / 2; pos[i][0] -= (dx / d) * e; pos[i][1] -= (dy / d) * e; pos[j][0] += (dx / d) * e; pos[j][1] += (dy / d) * e; }
      }
    }
    cabezas.forEach((cb, i) => {
      cb.el.style.left = `${Math.max(24, Math.min(W - 24, pos[i][0]))}px`;
      cb.el.style.top = `${Math.max(34, Math.min(H - 34, pos[i][1]))}px`;
    });
  }
  const aPantalla = (x, y) => { const [a, b] = rot(x, y); return [W / 2 + a * k, H / 2 + b * k]; };
  const ro = new ResizeObserver(medir);
  ro.observe(raiz);

  // ---------------------------------------------------------------- simulación
  let sim = null, simPlan = null;
  function dibujarAgentes(T, plan, noche) {
    if (simPlan !== plan.id) { sim = crearSim(it, geo, plan); simPlan = plan.id; }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    if (!sim.listo) return;
    const { vehiculos, peatones } = sim.enT(T);
    ctx.setTransform(dpr * k, 0, 0, dpr * k, dpr * W / 2, dpr * H / 2);
    ctx.rotate(-n);
    ctx.scale(1, -1);
    if (noche) {
      ctx.globalCompositeOperation = 'lighter';
      for (const v of vehiculos) {
        ctx.save(); ctx.translate(v.x, v.y); ctx.rotate(v.ang);
        const g = ctx.createRadialGradient(v.largo / 2, 0, 0.2, v.largo / 2 + 5, 0, 7);
        g.addColorStop(0, 'rgba(255,240,200,.30)'); g.addColorStop(1, 'rgba(255,240,200,0)');
        ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(v.largo / 2, 0); ctx.arc(v.largo / 2, 0, 12, -0.32, 0.32); ctx.closePath(); ctx.fill();
        ctx.restore();
      }
      ctx.globalCompositeOperation = 'source-over';
    }
    for (const v of vehiculos) {
      ctx.save(); ctx.translate(v.x, v.y); ctx.rotate(v.ang);
      const L = v.largo, A = v.ancho;
      ctx.fillStyle = 'rgba(0,0,0,.45)'; redondo(ctx, -L / 2 + 0.25, -A / 2 - 0.2, L, A, 0.5); ctx.fill();
      if (v.tipo === 'moto') {
        ctx.fillStyle = '#20262b'; redondo(ctx, -L / 2, -0.28, L, 0.56, 0.28); ctx.fill();
        ctx.fillStyle = v.color; ctx.beginPath(); ctx.arc(-0.1, 0, 0.36, 0, Math.PI * 2); ctx.fill();
      } else {
        ctx.fillStyle = v.color; redondo(ctx, -L / 2, -A / 2, L, A, v.tipo === 'buseta' ? 0.35 : 0.55); ctx.fill();
        ctx.fillStyle = 'rgba(10,14,18,.55)';
        if (v.tipo === 'buseta') { redondo(ctx, -L / 2 + 0.6, -A / 2 + 0.25, L - 1.6, A - 0.5, 0.2); ctx.fill(); }
        else { redondo(ctx, -L * 0.18, -A / 2 + 0.22, L * 0.42, A - 0.44, 0.3); ctx.fill(); }
        if (v.tipo === 'taxi') { ctx.fillStyle = '#111'; ctx.fillRect(-0.2, -0.18, 0.4, 0.36); }
      }
      // luces: freno atrás (encendidas si frena o está detenido), delanteras de noche
      ctx.fillStyle = v.frena ? '#ff3b30' : 'rgba(150,30,30,.6)';
      if (v.frena) { ctx.shadowColor = '#ff3b30'; ctx.shadowBlur = 8; }
      if (v.tipo === 'moto') ctx.fillRect(-L / 2 - 0.05, -0.12, 0.14, 0.24);
      else { ctx.fillRect(-L / 2 - 0.02, -A / 2 + 0.12, 0.16, 0.34); ctx.fillRect(-L / 2 - 0.02, A / 2 - 0.46, 0.16, 0.34); }
      ctx.shadowBlur = 0;
      if (noche) { ctx.fillStyle = '#fff6d0'; if (v.tipo === 'moto') ctx.fillRect(L / 2 - 0.1, -0.1, 0.14, 0.2); else { ctx.fillRect(L / 2 - 0.12, -A / 2 + 0.15, 0.14, 0.3); ctx.fillRect(L / 2 - 0.12, A / 2 - 0.45, 0.14, 0.3); } }
      ctx.restore();
    }
    for (const p of peatones) {
      const bob = p.camina ? Math.sin(p.fase * Math.PI) * 0.06 : 0;
      ctx.fillStyle = 'rgba(0,0,0,.4)'; ctx.beginPath(); ctx.arc(p.x + 0.12, p.y - 0.12, 0.34, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = p.ropa; ctx.beginPath(); ctx.arc(p.x, p.y + bob, 0.32, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#3a2a22'; ctx.beginPath(); ctx.arc(p.x, p.y + bob, 0.15, 0, Math.PI * 2); ctx.fill();
    }
  }

  // ---------------------------------------------------------------- por cuadro
  const previos = {};
  function actualizar(T, t, plan, ms) {
    const c = plan.ciclo;
    for (const cb of cabezas) {
      const ti = plan.tiempos[cb.g.id];
      const e = luz(estado(ti, cb.g.tipo, t, c));
      cb.c.actualizar(e, restanteVisible(ti, cb.g.tipo, t, c));
      if (previos[cb.g.id] && previos[cb.g.id] !== e && e === 'verde' && alAnunciar) alAnunciar(cb.g, e);
      previos[cb.g.id] = e;
    }
    const b = bogota(ms);
    dibujarAgentes(T, plan, b.hora >= 18 || b.hora < 6);
  }

  /** Animación de entrada: el cruce «se dibuja». */
  function encender() {
    const g = window.gsap;
    if (!g || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    for (const t of trazos) { t.el.style.strokeDasharray = t.largo; t.el.style.strokeDashoffset = t.largo; }
    const tl = g.timeline({ defaults: { ease: 'expo.out' } });
    tl.to(trazos.map((t) => t.el), { strokeDashoffset: 0, duration: 0.9, stagger: 0.04 })
      .from([gMarcas, gCajon, gPare], { opacity: 0, duration: 0.5 }, '-=0.45');
    if (cebras.length) tl.from(cebras, { opacity: 0, duration: 0.35, stagger: 0.05 }, '-=0.35');
    if (cabezas.length) tl.from(cabezas.map((c) => c.el), { opacity: 0, scale: 0.6, duration: 0.45, stagger: 0.05 }, '-=0.2');
    tl.from(lienzo, { opacity: 0, duration: 0.6 }, '-=0.3');
    tl.eventCallback('onComplete', () => { for (const t of trazos) { t.el.style.strokeDasharray = ''; t.el.style.strokeDashoffset = ''; } });
    // salvaguarda para equipos lentos: el contenido nunca se queda oculto a medio animar
    setTimeout(() => { if (tl.progress() < 1) tl.progress(1); }, 3500);
  }

  return { el: raiz, actualizar, medir, encender, destruir: () => ro.disconnect() };
}

function redondo(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}
