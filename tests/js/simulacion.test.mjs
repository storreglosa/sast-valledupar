// Invariantes de la simulación ilustrativa. Usa el borrador de accesos de data/processed/semaforos.json
// (etapa 09), así no depende de que la asignación ya esté validada y publicada.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { crearSim } from '../../tablero/js/simulacion/trafico.js';
import { estado, dur } from '../../tablero/js/nucleo/tiempos.js';

const proc = JSON.parse(readFileSync(new URL('../../data/processed/semaforos.json', import.meta.url)));

test('nadie cruza la línea de pare fuera del verde (+1 s de amarillo) y la simulación es determinista', (t) => {
  let revisados = 0;
  for (const it of proc.intersecciones) {
    const g = it.geometria;
    const geo = { trayectorias: g.trayectorias, vias: g.vias, cebras: Object.entries(g.cebras).map(([k, z]) => ({ grupo: k, ...z })) };
    for (const plan of it.planes) {
      const sim = crearSim(it, geo, plan);
      const c = plan.ciclo, prev = new Map();
      for (let T = 0; T < 4 * c; T += 0.1) {
        for (const v of sim.enT(T).vehiculos) {
          const s0 = prev.get(v.id);
          if (s0 != null && s0 < v.sPare && v.s >= v.sPare) {
            const ti = plan.tiempos[v.grupo];
            const tc = ((T % c) + c) % c;
            const e = estado(ti, 'vehicular', tc - 0.05, c);
            assert.ok(e === 'verde' || (e === 'amarillo' && dur(ti.tfv, tc, c) <= 1.2),
              `${it.id} ${plan.id} ${v.grupo} cruzó en ${e} (t=${tc.toFixed(1)})`);
            revisados++;
          }
          prev.set(v.id, v.s);
        }
      }
      assert.equal(JSON.stringify(sim.enT(123.4)), JSON.stringify(crearSim(it, geo, plan).enT(123.4)), `${it.id} ${plan.id} no es determinista`);
    }
  }
  t.diagnostic(`${revisados} cruces de línea de pare revisados`);
  assert.ok(revisados > 100);
});
