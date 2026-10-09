// Cifras clave del plan que muestra el tablero (rojo máximo vehicular y peatonal, verde promedio),
// contra los valores que el revisor-datos calculó por su cuenta desde los PDF (2026-10-09).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { claves } from '../../tablero/js/nucleo/explicacion.js';

const proc = JSON.parse(readFileSync(new URL('../../data/processed/semaforos.json', import.meta.url)));
const cruce = (id) => proc.intersecciones.find((x) => x.id === id);
const plan = (it, pid) => it.planes.find((p) => p.id === pid);
const nombre = (it, gid) => it.grupos.find((g) => g.id === gid).nombre;

test('La Viña P2: rojo vehicular 57 s (Flujo 4), peatonal 60 s, verde promedio 42,5 → 43 s', () => {
  const it = cruce('la-vina'), k = claves(plan(it, 'P2'), it.grupos);
  assert.equal(k.rojoMax, 57);
  assert.equal(nombre(it, k.rojoMaxId), 'Flujo 4');
  assert.equal(k.rojoPeatMax, 60);
  assert.equal(k.verdeProm, 43);
});

test('Los Manguitos P2: rojo vehicular 93 s (Flujo 1), sin peatonales, verde promedio 20,25 → 20 s', () => {
  const it = cruce('manguitos'), k = claves(plan(it, 'P2'), it.grupos);
  assert.equal(k.rojoMax, 93);
  assert.equal(nombre(it, k.rojoMaxId), 'Flujo 1');
  assert.equal(k.rojoPeatMax, null);
  assert.equal(k.verdeProm, 20);
});

test('el rojo peatonal más largo supera al vehicular donde hay peatonales', () => {
  for (const [id, pid, veh, peat] of [['area-andina', 'P2', 77, 98], ['loperena', 'P5', 77, 91]]) {
    const it = cruce(id), k = claves(plan(it, pid), it.grupos);
    assert.equal(k.rojoMax, veh, `${id} ${pid} vehicular`);
    assert.equal(k.rojoPeatMax, peat, `${id} ${pid} peatonal`);
  }
});
