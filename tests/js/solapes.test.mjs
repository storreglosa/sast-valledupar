// Ubicación de las cabezas semafóricas del diagrama (tablero/js/util/solapes.js): sin taparse entre
// sí, sin pisar la calzada y dentro del recuadro.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { seSolapan, calzada, ubicar } from '../../tablero/js/util/solapes.js';

// cabeza en columna, 20 × 70 px. El cruce queda arriba (y menor): aguas arriba es hacia abajo,
// d = [0, 1]. La calzada que controla queda a su izquierda: afuera es a la derecha, n = [1, 0].
const col = (x, y, extra = {}) => ({ x, y, w: 20, h: 70, giro: 0, d: [0, 1], n: [1, 0], ...extra });
// calzada vertical de 60 px de ancho con eje en x = 300 (bordes en 270 y 330); coordenadas de
// pantalla, siempre positivas
const via = calzada([[300, 0], [300, 1000]], 60);
const libre = (r, otros, vias) => !vias.some((v) => seSolapan(v, r)) && !otros.some((o) => o !== r && seSolapan(o, r));

test('rectángulos separados, tocándose y girados', () => {
  assert.equal(seSolapan(col(0, 0), col(30, 0)), false);
  assert.equal(seSolapan(col(0, 0), col(10, 0)), true);
  assert.equal(seSolapan(col(0, 0), col(23, 0), 5), true);
  // a 25 px dos columnas no se tocan; girada 90° una (barra de 70 px), sí
  assert.equal(seSolapan(col(0, 0), col(25, 0, { giro: 90 })), true);
});

test('calzada: un rectángulo por tramo, con el ancho dado y alargado en las uniones', () => {
  const [a, b] = calzada([[0, 0], [100, 0], [100, 50]], 10);
  assert.deepEqual([a.x, a.y, a.w, a.h, a.giro], [50, 0, 110, 10, 0]);
  assert.deepEqual([b.x, b.y, b.w, b.h, b.giro], [100, 25, 60, 10, 90]);
});

test('una cabeza que pisa la calzada sale hacia su andén (asimétrico), no hacia el otro lado', () => {
  // centro en x = 320: la mitad izquierda (310..330) pisa la calzada; afuera es +x
  const [r] = ubicar([col(320, 200)], via);
  assert.ok(r.libre);
  assert.ok(r.x - 10 >= 330, `el borde izquierdo debería quedar fuera de la calzada y quedó en ${r.x - 10}`);
  assert.ok(r.x < 350, 'debería correrse solo lo justo');
  assert.equal(r.y, 200);                          // correrse hacia afuera cuesta menos que bajar
});

test('control con la dirección invertida a propósito: la misma cabeza cruzaría la vía', () => {
  // con n = [−1, 0] la cabeza tiene que atravesar toda la calzada para salir por el otro andén
  const [r] = ubicar([col(320, 200, { n: [-1, 0] })], via);
  assert.ok(r.libre);
  assert.ok(r.x + 10 <= 270, `con n invertido debería salir por el otro lado y quedó en ${r.x}`);
});

test('dos cabezas en el mismo sitio: se queda la primera y la segunda se corre por su lado', () => {
  const [a, b] = ubicar([col(100, 200), col(100, 200)], []);
  assert.deepEqual([a.x, a.y], [100, 200]);
  assert.ok(b.x > 100 || b.y > 200, 'la segunda solo puede correrse hacia afuera o aguas arriba');
  assert.ok(b.x >= 100 && b.y >= 200);
  assert.equal(seSolapan(a, b, 5), false);
});

test('respeta el recuadro: no se corre por fuera del borde aunque ahí no haya nada', () => {
  // pegada al borde derecho: correrse hacia afuera (+x) la sacaría; debe bajar por su vía
  const [a, b] = ubicar([col(180, 50), col(180, 50)], [], { W: 200, H: 400 });
  assert.equal(b.x, 180);
  assert.ok(b.y > 50 && b.y + 35 <= 396);
  assert.equal(seSolapan(a, b), false);
});

test('el resultado no pisa calzadas ni otras cabezas en un caso con varias', () => {
  const vias = [...via, ...calzada([[0, 300], [1000, 300]], 50)];
  const rs = ubicar([col(320, 340), col(325, 345), col(280, 360, { n: [-1, 0], d: [0, 1] }),
    { x: 360, y: 310, w: 70, h: 20, giro: 0, d: [1, 0], n: [0, -1] }], vias);
  assert.ok(rs.every((r) => r.libre));
  rs.forEach((r) => assert.ok(libre(r, rs, vias)));
});

test('si no hay lugar libre, lo marca en vez de esconderlo', () => {
  const ancha = calzada([[300, 0], [300, 1000]], 2000);   // todo es calzada
  const [r] = ubicar([col(300, 300)], ancha, { maxS: 30, maxL: 30 });
  assert.equal(r.libre, false);
});
