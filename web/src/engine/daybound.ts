// scheduler/daybound.py — gün-seviyesi gevşetme: bu kurallarla EN FAZLA kaç
// saat yerleşebilir? Esas modelin her kısıtı burada ya aynen var ya da
// gevşetilmiş; bulunan sayı geçerli bir ÜST SINIRDIR.
import { Expr, Model, NOT, defaultWorkers, getBackend } from './cp.ts';
import type { Ref } from './cp.ts';
import type { Card, World } from './model.ts';
import { totalHours } from './model.ts';
import { key } from './py.ts';
import { forcedKey } from './problem.ts';
import * as R from './rules.ts';
import type { Rule } from './rules.ts';

const DAY_RULE_KINDS = new Set([R.X_SUBJECT_ONCE_DAY, R.X_TEACHER_ONCE_DAY, R.X_PAIR_NOT_SAME_DAY,
  R.X_SUBJECT_MAX_HOURS, R.X_PRACTICAL_MAX_HOURS, R.X_CLASS_MAX_HOURS, R.X_TEACHER_MAX_HOURS]);

function openHours(mask: Uint8Array, d: number, P: number): number {
  let n = 0;
  for (let p = 0; p < P; p++) if (!mask[d * P + p]) n++;
  return n;
}

interface SolveOpts { skip?: Set<string>; openTeachers?: Set<number>; allowSplit?: boolean; seed?: number }

/** Döner [durum, üst sınır, bulunan] — Python _solve(want_solution=False). */
async function solve(w: World, rules: Rule[], forced: Set<string>, seconds: number, o: SolveOpts = {}):
  Promise<[string, number | null, number | null]> {
  const { D, P } = w;
  const skip = o.skip ?? new Set<string>();
  const openTeachers = o.openTeachers ?? new Set<number>();
  const allowSplit = o.allowSplit ?? true;
  const tClosed = (ti: number) => (openTeachers.has(ti) ? new Uint8Array(D * P) : w.teacherClosed[ti]);
  const m = new Model();
  const h = new Map<string, Ref>();       // (kart, gün) -> o gün o karttan kaç saat
  const whole = new Map<string, Ref>();
  const piece = new Map<string, Ref>();
  for (const c of w.cards) {
    let days: number[];
    if (c.lockedAt !== null) days = [Math.floor(c.lockedAt / P)];
    else {
      days = [];
      for (let d = 0; d < D; d++) {
        let ok = false;
        for (const ci of c.classes) {
          for (let p = 0; p < P && !ok; p++) {
            if (!w.classClosed[ci][d * P + p] && (c.teacher < 0 || !tClosed(c.teacher)[d * P + p])) ok = true;
          }
          if (ok) break;
        }
        if (ok) days.push(d);
      }
    }
    if (!days.length) continue;
    if (c.lockedAt !== null) {
      const d = days[0];
      h.set(key(c.cid, d), m.int(c.duration, c.duration));
      const wv = m.bool();
      whole.set(key(c.cid, d), wv);
      m.eq(Expr.of([wv]), 1);
      continue;
    }
    const ws: Ref[] = [];
    for (const d of days) {
      const wv = m.bool();
      whole.set(key(c.cid, d), wv);
      ws.push(wv);
    }
    m.le(Expr.of(ws), 1);
    const canSplit = allowSplit && c.duration >= 2;
    for (const d of days) {
      const hv = m.int(0, c.duration);
      h.set(key(c.cid, d), hv);
      if (canSplit) {
        const pv = m.int(0, c.duration);
        piece.set(key(c.cid, d), pv);
        m.le(Expr.of([pv]).addAll(ws, c.duration), c.duration);
        m.eq(Expr.of([hv]).add(whole.get(key(c.cid, d))!, -c.duration).add(pv, -1), 0);
      } else {
        m.eq(Expr.of([hv]).add(whole.get(key(c.cid, d))!, -c.duration), 0);
      }
    }
    if (canSplit) m.le(Expr.of(days.map((d) => piece.get(key(c.cid, d))!)), c.duration);
    m.le(Expr.of(days.map((d) => h.get(key(c.cid, d))!)), c.duration);
  }
  const used = (e: Expr): Ref => {
    const a = m.bool();
    m.ge(e, 1, [a]);
    m.eq(e, 0, [NOT(a)]);
    return a;
  };
  const hv = (c: Card, d: number) => h.get(key(c.cid, d));
  rules.forEach((r, ri) => {
    if (!r.isHard() || !DAY_RULE_KINDS.has(r.kind)) return;
    if (skip.has(key(ri, 'all'))) return;
    if (r.kind === R.X_SUBJECT_ONCE_DAY || r.kind === R.X_TEACHER_ONCE_DAY) {
      const which = r.kind === R.X_SUBJECT_ONCE_DAY ? 's' : 't';
      const groups = new Map<string, { ci: number; res: number; cards: Card[] }>();
      for (const c of w.cards) {
        if (!r.appliesCard(c)) continue;
        const res = which === 's' ? c.family : c.teacher;
        if (res < 0) continue;
        for (const ci of c.classes) {
          if (r.appliesClass(ci) && !skip.has(key(ri, ci))) {
            const k = key(ci, res);
            let g = groups.get(k);
            if (!g) { g = { ci, res, cards: [] }; groups.set(k, g); }
            g.cards.push(c);
          }
        }
      }
      for (const { ci, res, cards } of groups.values()) {
        if (forced.has(forcedKey(which, ci, res))) continue;
        const byOrigin = new Map<number, Card[]>();
        for (const c of cards) {
          if (!byOrigin.has(c.origin)) byOrigin.set(c.origin, []);
          byOrigin.get(c.origin)!.push(c);
        }
        if (byOrigin.size < 2) continue;
        for (let d = 0; d < D; d++) {
          const flags: Ref[] = [];
          for (const cs of byOrigin.values()) {
            const vs = cs.map((c) => hv(c, d)).filter((v): v is Ref => v !== undefined);
            if (vs.length) flags.push(used(Expr.of(vs)));
          }
          if (flags.length > 1) m.le(Expr.of(flags), 1);
        }
      }
    } else if (r.kind === R.X_SUBJECT_MAX_HOURS || r.kind === R.X_PRACTICAL_MAX_HOURS) {
      const lim = Math.max(1, r.param || 0);
      const groups = new Map<string, Card[]>();
      for (const c of w.cards) {
        if (!r.appliesCard(c) || c.family < 0) continue;
        for (const ci of c.classes) {
          if (r.appliesClass(ci) && !skip.has(key(ri, ci))) {
            const k = key(ci, c.family);
            if (!groups.has(k)) groups.set(k, []);
            groups.get(k)!.push(c);
          }
        }
      }
      for (const cards of groups.values()) {
        for (let d = 0; d < D; d++) {
          const vs = cards.map((c) => hv(c, d)).filter((v): v is Ref => v !== undefined);
          if (vs.length) m.le(Expr.of(vs), lim);
        }
      }
    } else if (r.kind === R.X_CLASS_MAX_HOURS) {
      const lim = Math.max(1, r.param || 0);
      for (let ci = 0; ci < w.classes.length; ci++) {
        if (!r.appliesClass(ci) || skip.has(key(ri, ci))) continue;
        for (let d = 0; d < D; d++) {
          const vs = w.cards.filter((c) => c.classes.includes(ci) && r.appliesCard(c)).map((c) => hv(c, d)).filter((v): v is Ref => v !== undefined);
          if (vs.length) m.le(Expr.of(vs), lim);
        }
      }
    } else if (r.kind === R.X_TEACHER_MAX_HOURS) {
      const lim = Math.max(1, r.param || 0);
      for (let ti = 0; ti < w.teachers.length; ti++) {
        if (!r.appliesTeacher(ti)) continue;
        for (let d = 0; d < D; d++) {
          const vs = w.cards.filter((c) => c.teacher === ti && r.appliesCard(c)).map((c) => hv(c, d)).filter((v): v is Ref => v !== undefined);
          if (vs.length) m.le(Expr.of(vs), lim);
        }
      }
    } else if (r.kind === R.X_PAIR_NOT_SAME_DAY) {
      for (let ci = 0; ci < w.classes.length; ci++) {
        if (!r.appliesClass(ci) || skip.has(key(ri, ci))) continue;
        for (let d = 0; d < D; d++) {
          const bySubj = new Map<number, Ref[]>();
          for (const c of w.cards) {
            const v = hv(c, d);
            if (c.classes.includes(ci) && r.appliesCard(c) && v !== undefined) {
              if (!bySubj.has(c.subject)) bySubj.set(c.subject, []);
              bySubj.get(c.subject)!.push(v);
            }
          }
          if (bySubj.size < 2) continue;
          const has: Ref[] = [];
          for (const vs of bySubj.values()) has.push(used(Expr.of(vs)));
          m.le(Expr.of(has), 1);
        }
      }
    }
  });
  for (let ti = 0; ti < w.teachers.length; ti++) {
    const mask = tClosed(ti);
    for (let d = 0; d < D; d++) {
      const vs = w.cards.filter((c) => c.teacher === ti).map((c) => hv(c, d)).filter((v): v is Ref => v !== undefined);
      if (vs.length) m.le(Expr.of(vs), openHours(mask, d, P));
    }
  }
  for (let ci = 0; ci < w.classes.length; ci++) {
    for (let d = 0; d < D; d++) {
      const vs = w.cards.filter((c) => c.classes.includes(ci)).map((c) => hv(c, d)).filter((v): v is Ref => v !== undefined);
      if (vs.length) m.le(Expr.of(vs), openHours(w.classClosed[ci], d, P));
    }
  }
  const saat = new Expr();
  for (const [k, v] of h) {
    const cid = Number(k.split('\u0001')[0]);
    saat.add(v, w.cards[cid].classes.length);
  }
  m.maximize(saat);
  const res = await getBackend().solve(m, {
    maxTimeInSeconds: Math.max(0.2, seconds), numWorkers: defaultWorkers,
    ...(o.seed ? { randomSeed: o.seed & 0x7fffffff } : {}),
  });
  if (res.status === 'OPTIMAL' || res.status === 'FEASIBLE') {
    return [res.status, Math.trunc(res.bound), Math.trunc(saat.value(res.values!))];
  }
  if (res.status === 'INFEASIBLE') return [res.status, 0, 0];
  return [res.status, null, null];
}

/** Kanıtlanmış üst sınır (saat) ya da null. */
export async function dayBound(w: World, rules: Rule[], forced: Set<string>, seconds = 2.0): Promise<number | null> {
  if (!w.cards.length) return 0;
  const [, bound] = await solve(w, rules, forced, seconds);
  return bound;
}

function dayName(d: number): string {
  // Python: world.day_names hiç atanmadığı için sabit liste kullanılıyor.
  const names = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar'];
  return d < 7 ? names[d] : `${d + 1}. gün`;
}

export async function explainDayBound(w: World, rules: Rule[], forced: Set<string>, bound: number | null,
  seconds = 5.0): Promise<any[]> {
  const total = totalHours(w);
  if (bound === null || bound >= total) return [];
  const deadline = performance.now() / 1000 + seconds;
  const per = 0.6;
  const out: any[] = [];
  const probe = async (o: SolveOpts): Promise<number | null> => {
    if (performance.now() / 1000 > deadline) return null;
    const r = await solve(w, rules, forced, per, o);
    return r[2];
  };
  const openTotal = (ti: number) => {
    let s = 0;
    for (let d = 0; d < w.D; d++) s += openHours(w.teacherClosed[ti], d, w.P);
    return s;
  };
  const candidates = rules.map((r, ri) => [w.cards.filter((c) => r.appliesCard(c)).length, ri, r] as const)
    .filter(([, , r]) => r.isHard() && DAY_RULE_KINDS.has(r.kind))
    .sort((a, b) => a[0] - b[0]);
  for (const [, ri, r] of candidates) {
    const without = await probe({ skip: new Set([key(ri, 'all')]) });
    if (without === null || without <= bound) continue;
    const kazanc = without - bound;
    const involvedSet = new Set<number>();
    for (const c of w.cards) if (r.appliesCard(c)) for (const ci of c.classes) if (r.appliesClass(ci)) involvedSet.add(ci);
    const involved = [...involvedSet].sort((a, b) => a - b);
    let classes: number[] = [];
    for (const ci of involved) {
      const b2 = await probe({ skip: new Set([key(ri, ci)]) });
      if (b2 !== null && b2 > bound) classes.push(ci);
    }
    if (!classes.length) classes = involved;
    const tset = new Set<number>();
    for (const c of w.cards) if (r.appliesCard(c) && c.teacher >= 0 && c.classes.some((ci) => classes.includes(ci))) tset.add(c.teacher);
    const teachers = [...tset].sort((a, b) => a - b).sort((a, b) => openTotal(a) - openTotal(b));
    const bottleneck: number[] = [];
    for (const ti of teachers) {
      if (bottleneck.length >= 3) break;
      const b3 = await probe({ openTeachers: new Set([ti]) });
      if (b3 !== null && b3 > bound) bottleneck.push(ti);
    }
    let label = r.label || r.kind;
    if (r.kind === R.X_PAIR_NOT_SAME_DAY && r.subjects.size) {
      label += ' (' + [...r.subjects].sort((a, b) => a - b).filter((s) => s >= 0 && s < w.subjects.length).map((s) => w.subjects[s]).join(' + ') + ')';
    }
    const clsTxt = classes.map((ci) => w.classes[ci]).join(', ');
    let msg = `'${label}' kuralı ${clsTxt} için ${kazanc} saati dışarıda bırakıyor: kural bu sınıf(lar)da kalkınca ${without}/${total} saat mümkün.`;
    if (bottleneck.length) {
      const parts = bottleneck.map((ti) => {
        const days: string[] = [];
        for (let d = 0; d < w.D; d++) {
          const oh = openHours(w.teacherClosed[ti], d, w.P);
          if (oh > 0) days.push(`${dayName(d)} ${oh}`);
        }
        const load = w.cards.filter((c) => c.teacher === ti).reduce((s, c) => s + c.duration, 0);
        return `${w.teachers[ti]} haftada ${openTotal(ti)} saat açık (${days.join(', ')}), ${load} saat yükü var`;
      });
      msg += ' Darboğaz: ' + parts.join('; ') + '.';
    }
    out.push({ message: msg, rule: label, classes: classes.map((ci) => w.classes[ci]),
      teachers: bottleneck.map((ti) => w.teachers[ti]), hours: kazanc, cards: [] });
    if (performance.now() / 1000 > deadline) break;
  }
  return out;
}
