// Pruebas del núcleo del tablero contra la referencia de Python.
//   node --test tests/js/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { cadena, estado, restante, restanteVisible, etapas, kpis } from '../../tablero/js/nucleo/tiempos.js';
import { festivos, planVigente, segundoEnVivo, bogota } from '../../tablero/js/nucleo/horario.js';

const ref = JSON.parse(readFileSync(new URL('../fixtures/estados_referencia.json', import.meta.url)));
const datos = JSON.parse(readFileSync(new URL('../../tablero/data/semaforos.json', import.meta.url)));

test('estados por segundo idénticos a Python en todos los planes', () => {
  for (const it of datos.intersecciones) {
    const tipo = Object.fromEntries(it.grupos.map((g) => [g.id, g.tipo]));
    for (const p of it.planes) {
      for (const [g, ti] of Object.entries(p.tiempos)) {
        assert.equal(cadena(ti, tipo[g], p.ciclo), ref.intersecciones[it.id][p.id].estados[g], `${it.id} ${p.id} ${g}`);
      }
    }
  }
});

test('etapas y KPI idénticos a los que calculó Python', () => {
  for (const it of datos.intersecciones) {
    for (const p of it.planes) {
      assert.deepEqual(etapas(p, it.grupos), p.etapas, `${it.id} ${p.id}`);
      assert.deepEqual(kpis(p, it.grupos), p.kpis, `${it.id} ${p.id}`);
    }
  }
});

test('vuelta de ciclo: Loperena P2 G3 (TIRA 98, TIV 0)', () => {
  const g3 = { tira: 98, tiv: 0, tfv: 27, tfa: 30 };
  assert.equal(estado(g3, 'vehicular', 98, 100), 'preparacion');
  assert.equal(estado(g3, 'vehicular', 99.9, 100), 'preparacion');
  assert.equal(estado(g3, 'vehicular', 0, 100), 'verde');
  assert.equal(estado(g3, 'vehicular', -1, 100), 'preparacion');
  assert.equal(restante({ tira: 78, tiv: 80, tfv: 20, tfa: 23 }, 95, 100), 25);
  // lo visible: de rojo (con preparación incluida) pasa a verde en TIV
  assert.equal(restanteVisible(g3, 'vehicular', 50, 100), 50);
});

test('festivos 2024–2035 idénticos a Python', () => {
  for (const [anio, f] of Object.entries(ref.festivos)) assert.deepEqual(festivos(+anio), f, anio);
});

test('plan vigente con hora de Bogotá, bordes y festivo', () => {
  const lv = datos.intersecciones.find((i) => i.id === 'la-vina');
  const ms = (iso) => Date.parse(iso);
  assert.equal(planVigente(lv.horario, ms('2026-10-06T05:29:59-05:00')).plan, 'P3');
  assert.equal(planVigente(lv.horario, ms('2026-10-06T05:30:00-05:00')).plan, 'P2');
  assert.equal(planVigente(lv.horario, ms('2026-10-11T10:00:00-05:00')).plan, 'P1');   // domingo
  const f = planVigente(lv.horario, ms('2026-10-12T15:00:00-05:00'));                // Día de la Raza
  assert.equal(f.fila, 'festivo'); assert.equal(f.festivo, 'Día de la Raza'); assert.equal(f.plan, 'P1');
  assert.equal(bogota(ms('2026-10-08T03:00:00Z')).hora, 22);
  const s = segundoEnVivo(lv.horario, lv.planes, ms('2026-10-06T05:31:45-05:00'));
  assert.equal(s.plan, 'P2'); assert.equal(Math.round(s.t), 5);   // 105 s después de las 05:30, ciclo 100
});
