// Web motorunu Node'da uçtan uca çalıştırır (tarayıcıdaki ile aynı kod).
//   node tools/run-node.ts VERI.roz all|locked|asis|unlock [soru_sayisi]
import { readFileSync } from 'node:fs';
import { availableParallelism } from 'node:os';
import { runPlanner } from '../src/engine/engine.ts';
import { setupNode, stats } from './node-env.ts';

const [, , roz, mode, askN] = process.argv;
const src = JSON.parse(readFileSync(roz, 'utf8'));
const d = structuredClone(src);
const gp = (d.grid_placements ?? []).filter((p: any) => p && typeof p === 'object');
if (mode === 'all') { d.grid_placements = []; d.auto_schedule_results = []; }
else if (mode === 'locked' || mode === 'unlock') d.grid_placements = gp.filter((p: any) => p.locked || p.is_locked);
d.yerlesim = {}; d.loose_unplaced_cards = []; d.manual_unplaced_cards = [];

setupNode();
const t0 = performance.now();
let last = -1, asked = 0;
try {
  const out = await runPlanner(d, {
    lanes: availableParallelism(),
    unlockConflictingLocks: mode === 'unlock',
    progress: (placed, total) => {
      if (placed !== last) { last = placed; console.log(`  [${((performance.now() - t0) / 1000).toFixed(1)}s] ${placed}/${total}`); }
    },
    askContinue: async (info) => {
      asked++;
      console.log(`  [${((performance.now() - t0) / 1000).toFixed(1)}s] SORU #${asked}: ${info.saat}/${info.toplam} ust=${info.ust}`);
      return asked <= Number(askN ?? 0);
    },
  });
  console.log(`SONUÇ ${out.placed_hours}/${out.total_assigned_hours} durum=${out.status} tam=${out.complete} `
    + `süre=${((performance.now() - t0) / 1000).toFixed(1)}s cp çağrı=${stats.cpCalls} kurma=${(stats.cpBuildMs / 1000).toFixed(1)}s çözme=${(stats.cpSolveMs / 1000).toFixed(1)}s`);
  for (const w of out.warnings) if (!w.startsWith('Yerleşmedi')) console.log('  W:', w);
  for (const u of out.unplaced_cards) console.log('  U:', JSON.stringify(u));
} catch (e: any) {
  console.log('HATA:', e.message);
}
process.exit(0);
