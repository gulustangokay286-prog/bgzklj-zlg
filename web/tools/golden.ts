// TypeScript motorunun ara çıktılarını golden.py ile aynı biçimde döker ve
// Python dökümüyle karşılaştırır.
//   node tools/golden.ts VERI.roz all|locked|asis|unlock KLASOR
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { diagnose } from '../src/engine/diagnostics.ts';
import { dunyaKur, kilitCatismalari } from '../src/engine/locks.ts';
import type { Kilit } from '../src/engine/locks.ts';
import { totalHours } from '../src/engine/model.ts';
import { hazirla } from '../src/engine/prep.ts';
import { Problem, impossibleGroups } from '../src/engine/problem.ts';
import { validate } from '../src/engine/verify.ts';

const [, , roz, mode, outDir] = process.argv;
const src = JSON.parse(readFileSync(roz, 'utf8'));

function prep(s: any, m: string) {
  const d = structuredClone(s);
  const gp = (d.grid_placements ?? []).filter((p: any) => p && typeof p === 'object');
  if (m === 'all') { d.grid_placements = []; d.auto_schedule_results = []; }
  else if (m === 'locked' || m === 'unlock') d.grid_placements = gp.filter((p: any) => p.locked || p.is_locked);
  d.yerlesim = {}; d.loose_unplaced_cards = []; d.manual_unplaced_cards = [];
  return d;
}

const cells = (m: Uint8Array) => [...m.keys()].filter((i) => m[i]);
const t0 = performance.now();
const pr = hazirla(prep(src, mode));
const raw = pr.data.planlama_iliskileri ?? [];
let [w, rules, report, kilitler] = dunyaKur(pr.data, pr.D, pr.P, pr.engel, pr.selected, raw);
const catisma = kilitCatismalari(w, rules, kilitler, pr.data, true);
if (catisma.length && mode === 'unlock') {
  const atla = new Set(catisma.flatMap((k) => k.ids));
  [w, rules, report, kilitler] = dunyaKur(pr.data, pr.D, pr.P, pr.engel, pr.selected, raw, atla);
}
const forced = impossibleGroups(w);
const [issues, ub] = diagnose(w, rules);
const pb = new Problem(w, rules, true);
const body = pb.body();
const g = JSON.parse(readFileSync(join(outDir, 'golden_py.json'), 'utf8'));
const [errs, soft, bent] = validate(w, rules, g.validate.positions, true, forced);
const ms = performance.now() - t0;

const dump = {
  D: pr.D, P: pr.P, selected: pr.selected,
  engel: Object.fromEntries([...pr.engel.entries()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([k, v]) => [k, [...v].sort((a, b) => a[0] - b[0] || a[1] - b[1])])),
  world: {
    classes: w.classes, teachers: w.teachers, subjects: w.subjects, families: w.families,
    subject_family: w.subjectFamily,
    class_closed: w.classClosed.map(cells), teacher_closed: w.teacherClosed.map(cells),
    class_avoid: w.classAvoid.map(cells), teacher_avoid: w.teacherAvoid.map(cells),
    class_capacity: w.classCapacity, class_demand: w.classDemand,
    cards: w.cards.map((c) => ({ cid: c.cid, classes: c.classes, subject: c.subject, teacher: c.teacher,
      duration: c.duration, origin: c.origin, group: c.group, locked_at: c.lockedAt, family: c.family,
      slots: c.slots, subject_name: c.subjectName, teacher_name: c.teacherName, class_names: c.classNames })),
    total_hours: totalHours(w),
  },
  rules: rules.map((r) => ({ kind: r.kind, axis: r.axis, hardness: r.hardness, param: r.param, param2: r.param2,
    subjects: [...r.subjects].sort((a, b) => a - b), teachers: [...r.teachers].sort((a, b) => a - b),
    klasses: [...r.klasses].sort((a, b) => a - b), label: r.label })),
  report: { warnings: report.warnings, errors: report.errors, skipped: report.skipped },
  kilitler: kilitler.map((k: Kilit) => ({ kart: k.kart, ids: k.ids, d: k.d, p: k.p })),
  catisma: catisma.map((k) => k.mesaj),
  forced: [...forced].map((s) => s.split('\u0001').join('|')).sort(),
  diagnostics: issues.map((x) => x.message), upper_bound: ub,
  problem_sha256: createHash('sha256').update(body).digest('hex'),
  problem_len: body.length,
  validate: { positions: g.validate.positions, errors: errs, soft, bent },
};
writeFileSync(join(outDir, 'golden_ts.json'), JSON.stringify(dump, null, 1));
writeFileSync(join(outDir, 'problem_ts.txt'), pb.header(2.0, 1, totalHours(w)) + body);

// Karşılaştırma
let fails = 0;
const skip = new Set(['day_bound', 'tabu_first_line']);
for (const k of Object.keys(g)) {
  if (skip.has(k)) continue;
  const a = JSON.stringify(g[k]), b = JSON.stringify((dump as any)[k]);
  if (a !== b) {
    fails++;
    console.log(`FARK ${k}`);
    if (k === 'world') {
      for (const wk of Object.keys(g.world)) {
        if (JSON.stringify(g.world[wk]) !== JSON.stringify((dump.world as any)[wk])) {
          console.log(`   world.${wk}`);
          if (wk === 'cards') {
            const pc = g.world.cards, tc = dump.world.cards;
            console.log(`   kart sayısı py ${pc.length} ts ${tc.length}`);
            for (let i = 0; i < Math.min(pc.length, tc.length); i++) {
              if (JSON.stringify(pc[i]) !== JSON.stringify(tc[i])) { console.log('   py', JSON.stringify(pc[i]).slice(0, 400)); console.log('   ts', JSON.stringify(tc[i]).slice(0, 400)); break; }
            }
          }
        }
      }
    } else {
      console.log('   py', a.slice(0, 600));
      console.log('   ts', b.slice(0, 600));
    }
  }
}
console.log(`${fails === 0 ? 'AYNI' : 'FARKLI'} — kart ${w.cards.length} saat ${totalHours(w)} kenar ${pb.edges.length} faktör ${pb.factors.length} (${ms.toFixed(0)} ms)`);
process.exit(fails ? 1 : 0);
