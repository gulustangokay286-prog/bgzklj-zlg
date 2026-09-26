// scheduler/cpsat.py — CP-SAT arka ucu: ekrandaki HER kural modellenir.
//   x[i][s]  kart i, s numaralı aday yerine konuldu mu (bütün blok)
//   u[i][k][c] kart i'nin k. 1 saatlik parçası c hücresine konuldu mu (bölme)
import { windowBreaks, windowOk } from './build.ts';
import { Expr, Model, NOT, defaultWorkers, getBackend } from './cp.ts';
import type { CpParams, Ref } from './cp.ts';
import type { Card, World } from './model.ts';
import { totalHours } from './model.ts';
import { impossibleGroups, forcedKey } from './problem.ts';
import { key } from './py.ts';
import * as R from './rules.ts';
import type { Rule } from './rules.ts';
import type { Pieces } from './verify.ts';

export const SAAT = 100_000;
const SOFT_WEIGHT: Record<number, number> = { [R.HIGH]: 1_000, [R.NORMAL]: 100, [R.LOW]: 10 };
const SPLIT_PEN = 1;
const GAP_PEN = 60;
const AVOID_PEN = 1;
const FORCED_NONADJ_PEN = 2_000;
const FORCED_CAP_PEN = 2_000;
const sw = (r: Rule) => SOFT_WEIGHT[r.hardness] ?? 100;

interface Occ { i: number; d: number; p: number; dur: number; v: Ref; card: Card; piece: boolean; k: number }

class CpModelBuild {
  w: World;
  P: number;
  D: number;
  rules: Rule[];
  forced: Set<string>;
  m = new Model();
  pen: [Ref, number][] = [];
  xs: [number, Ref][][] = [];
  su = new Map<number, [number, Ref][][]>();
  splits: [number, Ref, number][] = [];
  occ: Occ[] = [];
  clsCell = new Map<string, Ref[]>();
  tchCell = new Map<string, Ref[]>();

  constructor(world: World, ruleList: Rule[], allowSplit: boolean, forced: Set<string>) {
    this.w = world;
    this.P = world.P;
    this.D = world.D;
    this.rules = ruleList.filter((r) => !R.DEFINITION_RULES.has(r.kind));
    this.forced = forced;
    this.buildVars(allowSplit);
    this.physical();
    this.sameLessonContiguous();
    this.compact();
    this.compileRules();
  }

  private sameLessonContiguous() {
    const m = this.m;
    const groups = new Map<string, Occ[]>();
    for (const o of this.occ) {
      const k = key(o.card.classes.join(','), o.card.subject);
      const l = groups.get(k);
      if (l) l.push(o); else groups.set(k, [o]);
    }
    for (const occs of groups.values()) {
      if (new Set(occs.map((o) => o.i)).size < 2 && !occs.some((o) => o.piece)) continue;
      const cover = new Map<string, Ref[]>();
      for (const o of occs) for (let off = 0; off < o.dur; off++) {
        const k = key(o.d, o.p + off);
        const l = cover.get(k);
        if (l) l.push(o.v); else cover.set(k, [o.v]);
      }
      const byDay = new Map<number, Occ[]>();
      for (const o of occs) {
        const l = byDay.get(o.d);
        if (l) l.push(o); else byDay.set(o.d, [o]);
      }
      for (const [d, lst] of byDay) {
        for (let x = 0; x < lst.length; x++) {
          const a = lst[x];
          for (let y = 0; y < x; y++) {
            const b = lst[y];
            if (exclusive(a, b)) continue;
            const [lo, hi] = a.p <= b.p ? [a, b] : [b, a];
            const gap0 = lo.p + lo.dur, gap1 = hi.p;
            if (gap1 <= gap0) continue;
            for (let q = gap0; q < gap1; q++) {
              const cov = (cover.get(key(d, q)) ?? []).filter((v) => v !== a.v && v !== b.v);
              if (!cov.length) {
                m.boolOr([NOT(a.v), NOT(b.v)]);
                break;
              }
              m.le(Expr.of([a.v, b.v]).addAll(cov, -1), 1);
            }
          }
        }
      }
    }
  }

  private buildVars(allowSplit: boolean) {
    const { w, m, P, D } = this;
    const hardWindows = this.rules.filter((r) => R.WINDOW_RULES.has(r.kind) && r.isHard());
    w.cards.forEach((c, i) => {
      const row: [number, Ref][] = [];
      for (const idx of c.slots) {
        const v = m.bool();
        row.push([idx, v]);
        this.occ.push({ i, d: Math.floor(idx / P), p: idx % P, dur: c.duration, v, card: c, piece: false, k: -1 });
      }
      let su: [number, Ref][][] = [];
      if (allowSplit && c.duration >= 2 && c.lockedAt === null) {
        for (let k = 0; k < c.duration; k++) {
          const us: [number, Ref][] = [];
          for (let d = 0; d < D; d++) for (let p = 0; p < P; p++) {
            const idx = d * P + p;
            if (c.classes.some((ci) => w.classClosed[ci][idx])) continue;
            if (c.teacher >= 0 && w.teacherClosed[c.teacher][idx]) continue;
            if (!windowOk(w, hardWindows, c, p, 1)) continue;
            const v = m.bool();
            us.push([idx, v]);
            this.occ.push({ i, d, p, dur: 1, v, card: c, piece: true, k });
          }
          su.push(us);
        }
      }
      this.xs.push(row);
      if (su.length && su.every((us) => us.length)) this.su.set(i, su);
      else su = [];
      if (row.length || su.length) {
        if (c.lockedAt !== null) {
          for (const [idx, v] of row) m.eq(Expr.of([v]), idx === c.lockedAt ? 1 : 0);
        } else if (su.length) {
          const bol = m.bool();
          m.le(Expr.of(row.map(([, v]) => v)).add(bol), 1);
          for (const us of su) m.eq(Expr.of(us.map(([, v]) => v)).add(bol, -1), 0);
          const yer = su.map((us) => { const e = new Expr(); for (const [idx, v] of us) e.add(v, idx); return e; });
          for (let k = 0; k + 1 < yer.length; k++) {
            m.le(new Expr().plus(yer[k]).plus(yer[k + 1], -1), -1, [bol]);
          }
          for (let k = 0; k + 1 < su.length; k++) {
            for (const [ia, va] of su[k]) {
              const da = Math.floor(ia / P);
              for (const [ib, vb] of su[k + 1]) {
                if (Math.floor(ib / P) === da && ib !== ia + 1) m.boolOr([NOT(va), NOT(vb)]);
              }
            }
          }
          this.splits.push([i, bol, c.duration - 1]);
        } else {
          m.atMostOne(row.map(([, v]) => v));
        }
      }
    });
  }

  private physical() {
    const { w, m, P } = this;
    for (const o of this.occ) {
      const c = o.card;
      let avoid = 0;
      for (let off = 0; off < o.dur; off++) {
        const cell = o.d * P + o.p + off;
        for (const ci of c.classes) {
          const k = key(ci, cell);
          const l = this.clsCell.get(k);
          if (l) l.push(o.v); else this.clsCell.set(k, [o.v]);
          if (w.classAvoid[ci][cell]) avoid++;
        }
        if (c.teacher >= 0) {
          const k = key(c.teacher, cell);
          const l = this.tchCell.get(k);
          if (l) l.push(o.v); else this.tchCell.set(k, [o.v]);
          if (w.teacherAvoid[c.teacher][cell]) avoid++;
        }
      }
      if (avoid) this.pen.push([o.v, AVOID_PEN * avoid]);
    }
    for (const vs of this.clsCell.values()) if (vs.length > 1) m.atMostOne(vs);
    for (const vs of this.tchCell.values()) if (vs.length > 1) m.atMostOne(vs);
  }

  private compact() {
    const { w, m, P, D } = this;
    for (let ci = 0; ci < w.classes.length; ci++) {
      for (let d = 0; d < D; d++) {
        const dolu: Ref[] = [];
        for (let p = 0; p < P; p++) {
          const cell = d * P + p;
          if (w.classClosed[ci][cell]) continue;
          const vs = this.clsCell.get(key(ci, cell)) ?? [];
          if (!vs.length) continue;
          const u = m.bool();
          m.maxEquality(u, vs);
          dolu.push(u);
        }
        for (let k = 0; k + 1 < dolu.length; k++) {
          const a = dolu[k], b = dolu[k + 1];
          const g = m.bool();
          m.le(Expr.of([b]).add(a, -1).add(g, -1), 0);
          this.pen.push([g, GAP_PEN]);
        }
      }
    }
  }

  /** sum(terms) <= limit — sert kısıt ya da ceza. terms: ifade, n: terim sayısı */
  private cap(e: Expr, n: number, limit: number, rule: Rule) {
    if (!n) return;
    if (rule.isHard()) this.m.le(e, limit);
    else {
      const viol = this.m.int(0, Math.max(1, n * 4));
      this.m.le(new Expr().plus(e).add(viol, -1), limit);
      this.pen.push([viol, sw(rule)]);
    }
  }

  private notBoth(a: Ref, b: Ref, rule: Rule) {
    if (rule.isHard()) this.m.atMostOne([a, b]);
    else {
      const y = this.m.bool();
      this.m.le(Expr.of([a, b]).add(y, -1), 1);
      this.pen.push([y, sw(rule)]);
    }
  }

  private groupBy<T>(rule: Rule, keyfn: (o: Occ, ci: number) => T | null, name: (k: T) => string):
    Map<string, { k: T; occs: Occ[] }> {
    const groups = new Map<string, { k: T; occs: Occ[] }>();
    for (const o of this.occ) {
      if (!rule.appliesCard(o.card)) continue;
      for (const ci of o.card.classes) {
        if (!rule.appliesClass(ci)) continue;
        const k = keyfn(o, ci);
        if (k === null) continue;
        const s = name(k);
        let g = groups.get(s);
        if (!g) { g = { k, occs: [] }; groups.set(s, g); }
        g.occs.push(o);
      }
    }
    return groups;
  }

  private dayPresence(occs: Occ[]): Map<number, Ref> {
    const byDay = new Map<number, Ref[]>();
    for (const o of occs) {
      const l = byDay.get(o.d);
      if (l) l.push(o.v); else byDay.set(o.d, [o.v]);
    }
    const has = new Map<number, Ref>();
    for (const [d, vs] of byDay) {
      const h = this.m.bool();
      for (const v of vs) this.m.implication(v, h);
      this.m.le(Expr.of([h]).addAll(vs, -1), 0);
      has.set(d, h);
    }
    return has;
  }

  private cellsOf(occs: Occ[]): Map<string, { d: number; p: number; vs: Ref[] }> {
    const cells = new Map<string, { d: number; p: number; vs: Ref[] }>();
    for (const o of occs) for (let off = 0; off < o.dur; off++) {
      const k = key(o.d, o.p + off);
      let c = cells.get(k);
      if (!c) { c = { d: o.d, p: o.p + off, vs: [] }; cells.set(k, c); }
      c.vs.push(o.v);
    }
    return cells;
  }

  private byTeacher(r: Rule): Map<number, Occ[]> {
    const groups = new Map<number, Occ[]>();
    for (const o of this.occ) {
      if (o.card.teacher >= 0 && r.appliesCard(o.card)) {
        const l = groups.get(o.card.teacher);
        if (l) l.push(o); else groups.set(o.card.teacher, [o]);
      }
    }
    return groups;
  }

  private compileRules() {
    const tuple = (k: number[]) => k.join(',');
    for (const r of this.rules) {
      const k = r.kind;
      if (k === R.Y_CLASS_CLASH || k === R.Y_TEACHER_CLASH || k === R.Y_CLOSED_CELL || k === R.Y_CROSS_INSTITUTION) continue;
      if (R.WINDOW_RULES.has(k)) this.window(r);
      else if (k === R.X_SUBJECT_ONCE_DAY) this.onceDay(r, 's');
      else if (k === R.X_TEACHER_ONCE_DAY) this.onceDay(r, 't');
      else if (k === R.X_SUBJECT_MAX_HOURS || k === R.X_PRACTICAL_MAX_HOURS) {
        for (const { occs } of this.groupBy(r, (o, ci) => [ci, o.d, o.card.family], tuple).values()) {
          const e = new Expr(); for (const o of occs) e.add(o.v, o.dur);
          this.cap(e, occs.length, Math.max(1, r.param), r);
        }
      } else if (k === R.X_SUBJECT_MAX_SESSIONS) {
        for (const { occs } of this.groupBy(r, (o, ci) => [ci, o.d, o.card.family], tuple).values()) {
          this.cap(Expr.of(occs.map((o) => o.v)), occs.length, Math.max(1, r.param), r);
        }
      } else if (k === R.X_CLASS_MAX_HOURS) {
        for (const { occs } of this.groupBy(r, (o, ci) => [ci, o.d], tuple).values()) {
          const e = new Expr(); for (const o of occs) e.add(o.v, o.dur);
          this.cap(e, occs.length, Math.max(1, r.param), r);
        }
      } else if (k === R.X_TEACHER_MAX_HOURS) {
        const groups = new Map<string, Occ[]>();
        for (const o of this.occ) {
          if (o.card.teacher >= 0 && r.appliesCard(o.card)) {
            const gk = key(o.card.teacher, o.d);
            const l = groups.get(gk);
            if (l) l.push(o); else groups.set(gk, [o]);
          }
        }
        for (const occs of groups.values()) {
          const e = new Expr(); for (const o of occs) e.add(o.v, o.dur);
          this.cap(e, occs.length, Math.max(1, r.param), r);
        }
      } else if (k === R.X_TEACHER_MAX_DAYS) {
        for (const occs of this.byTeacher(r).values()) {
          const has = [...this.dayPresence(occs).values()];
          this.cap(Expr.of(has), has.length, Math.max(1, r.param), r);
        }
      } else if (k === R.X_PAIR_NOT_SAME_DAY) this.pairNotSameDay(r);
      else if (k === R.X_HARD_NOT_ADJACENT) this.adjacent(r, false);
      else if (k === R.X_SUBJECT_NOT_ADJACENT) this.adjacent(r, true);
      else if (k === R.X_MIN_DAYS_BETWEEN) this.minDays(r);
      else if (k === R.X_EVEN_SPREAD) this.evenSpread(r);
      else if (k === R.X_SAME_DAY_ADJACENT || k === R.X_NO_CLASS_GAP) {
        for (const { occs } of this.groupBy(r, (_o, ci) => [ci], tuple).values()) this.contiguous(occs, r);
      } else if (k === R.X_NO_TEACHER_GAP) {
        for (const occs of this.byTeacher(r).values()) this.contiguous(occs, r);
      } else if (k === R.X_TEACHER_MAX_RUN) {
        for (const occs of this.byTeacher(r).values()) this.maxRun(occs, Math.max(1, r.param), r);
      } else if (k === R.Y_SUBJECT_MAX_PARALLEL || k === R.Y_TEACHER_MAX_PARALLEL) {
        const groups = new Map<string, [Ref, number][]>();
        for (const o of this.occ) {
          const c = o.card;
          if (!r.appliesCard(c)) continue;
          const gk0 = k === R.Y_SUBJECT_MAX_PARALLEL ? c.family : c.teacher;
          if (gk0 < 0) continue;
          for (let off = 0; off < o.dur; off++) {
            const gk = key(gk0, o.d, o.p + off);
            const l = groups.get(gk);
            if (l) l.push([o.v, c.classes.length]); else groups.set(gk, [[o.v, c.classes.length]]);
          }
        }
        for (const terms of groups.values()) {
          const e = new Expr(); for (const [v, c] of terms) e.add(v, c);
          this.cap(e, terms.length, Math.max(1, r.param), r);
        }
      }
    }
  }

  private window(r: Rule) {
    if (r.isHard()) return;
    const wgt = sw(r);
    for (const o of this.occ) {
      if (r.appliesCard(o.card) && windowBreaks(r, o.p, o.dur, this.P)) this.pen.push([o.v, wgt]);
    }
  }

  private onceDay(r: Rule, which: 's' | 't') {
    const groups = this.groupBy(r, (o, ci) => {
      const res = which === 's' ? o.card.family : o.card.teacher;
      return res >= 0 ? [ci, o.d, res] : null;
    }, (k) => k.join(','));
    const cardsOf = new Map<string, Set<number>>(), daysOf = new Map<string, Set<number>>();
    for (const { k: [ci, d, res], occs } of groups.values()) {
      const gk = key(ci, res);
      if (!cardsOf.has(gk)) { cardsOf.set(gk, new Set()); daysOf.set(gk, new Set()); }
      for (const o of occs) cardsOf.get(gk)!.add(o.i);
      daysOf.get(gk)!.add(d);
    }
    for (const { k: [ci, , res], occs } of groups.values()) {
      const isForced = this.forced.has(forcedKey(which, ci, res)) && r.isHard();
      if (!isForced) {
        for (let x = 0; x < occs.length; x++) {
          const a = occs[x];
          for (let y = 0; y < x; y++) {
            const b = occs[y];
            if (exclusive(a, b)) continue;
            if (a.card.origin === b.card.origin && (a.p + a.dur === b.p || b.p + b.dur === a.p)) continue;
            this.notBoth(a.v, b.v, r);
          }
        }
        continue;
      }
      const gk = key(ci, res);
      const nCards = cardsOf.get(gk)!.size;
      const nDays = Math.max(1, daysOf.get(gk)!.size);
      const capv = Math.max(1, Math.ceil(nCards / nDays));
      const viol = this.m.int(0, occs.length);
      this.m.le(Expr.of(occs.map((o) => o.v)).add(viol, -1), capv);
      this.pen.push([viol, FORCED_CAP_PEN]);
      for (let ai = 0; ai < occs.length; ai++) {
        const a = occs[ai];
        for (let bi = 0; bi < ai; bi++) {
          const b = occs[bi];
          if (exclusive(a, b)) continue;
          const adjacent = a.p + a.dur === b.p || b.p + b.dur === a.p;
          const overlap = !(a.p + a.dur <= b.p || b.p + b.dur <= a.p);
          if (adjacent || overlap) continue;
          const y = this.m.bool();
          this.m.le(Expr.of([a.v, b.v]).add(y, -1), 1);
          this.pen.push([y, FORCED_NONADJ_PEN]);
        }
      }
    }
  }

  private pairNotSameDay(r: Rule) {
    for (const { occs } of this.groupBy(r, (o, ci) => [ci, o.d], (k) => k.join(',')).values()) {
      const bySubj = new Map<number, Ref[]>();
      for (const o of occs) {
        const l = bySubj.get(o.card.subject);
        if (l) l.push(o.v); else bySubj.set(o.card.subject, [o.v]);
      }
      if (bySubj.size < 2) continue;
      const has: Ref[] = [];
      for (const vs of bySubj.values()) {
        const h = this.m.bool();
        for (const v of vs) this.m.implication(v, h);
        this.m.le(Expr.of([h]).addAll(vs, -1), 0);
        has.push(h);
      }
      this.cap(Expr.of(has), has.length, 1, r);
    }
  }

  private adjacent(r: Rule, sameFamily: boolean) {
    for (const { occs } of this.groupBy(r, (o, ci) => [ci, o.d], (k) => k.join(',')).values()) {
      const ends = new Map<number, Occ[]>(), starts = new Map<number, Occ[]>();
      for (const o of occs) {
        if (!starts.has(o.p)) starts.set(o.p, []);
        starts.get(o.p)!.push(o);
        const e = o.p + o.dur - 1;
        if (!ends.has(e)) ends.set(e, []);
        ends.get(e)!.push(o);
      }
      for (const [p, evs] of ends) {
        const svs = starts.get(p + 1);
        if (!svs) continue;
        for (const a of evs) for (const b of svs) {
          if (a.i === b.i) continue;
          const fa = a.card.family, fb = b.card.family;
          if (sameFamily && fa !== fb) continue;
          if (!sameFamily && fa === fb) continue;
          this.notBoth(a.v, b.v, r);
        }
      }
    }
  }

  private minDays(r: Rule) {
    const N = Math.max(1, r.param);
    const groups = this.groupBy(r, (o, ci) => (o.card.family >= 0 ? [ci, o.card.family] : null), (k) => k.join(','));
    for (const { occs } of groups.values()) {
      const byDay = new Map<number, Ref[]>();
      for (const o of occs) {
        const l = byDay.get(o.d);
        if (l) l.push(o.v); else byDay.set(o.d, [o.v]);
      }
      const has = this.dayPresence(occs);
      const days = [...byDay.keys()].sort((a, b) => a - b);
      days.forEach((d1, ai) => {
        this.cap(Expr.of(byDay.get(d1)!), byDay.get(d1)!.length, 1, r);
        for (const d2 of days.slice(ai + 1)) if (d2 - d1 < N) this.notBoth(has.get(d1)!, has.get(d2)!, r);
      });
    }
  }

  private evenSpread(r: Rule) {
    const groups = this.groupBy(r, (o, ci) => (o.card.family >= 0 ? [ci, o.card.family] : null), (k) => k.join(','));
    for (const { occs } of groups.values()) {
      const byDay = new Map<number, Ref[]>();
      for (const o of occs) {
        const l = byDay.get(o.d);
        if (l) l.push(o.v); else byDay.set(o.d, [o.v]);
      }
      if (byDay.size < 2) continue;
      const n = occs.length;
      const mx = this.m.int(0, n), mn = this.m.int(0, n);
      for (let d = 0; d < this.D; d++) {
        const cnt = Expr.of(byDay.get(d) ?? []);
        this.m.ge(Expr.of([mx]).plus(cnt, -1), 0);
        this.m.le(Expr.of([mn]).plus(cnt, -1), 0);
      }
      if (r.isHard()) this.m.le(Expr.of([mx]).add(mn, -1), 1);
      else {
        const viol = this.m.int(0, n);
        this.m.le(Expr.of([mx]).add(mn, -1).add(viol, -1), 1);
        this.pen.push([viol, sw(r)]);
      }
    }
  }

  private contiguous(occs: Occ[], r: Rule) {
    const byDay = new Map<number, Map<number, Ref[]>>();
    for (const { d, p, vs } of this.cellsOf(occs).values()) {
      if (!byDay.has(d)) byDay.set(d, new Map());
      byDay.get(d)!.set(p, vs);
    }
    for (const row of byDay.values()) {
      const ps = [...row.keys()].sort((a, b) => a - b);
      for (let ai = 0; ai < ps.length; ai++) {
        const p1 = ps[ai];
        for (let ci = ai + 2; ci < ps.length; ci++) {
          const p3 = ps[ci];
          for (let p2 = p1 + 1; p2 < p3; p2++) {
            const e = Expr.of(row.get(p1)!).addAll(row.get(p3)!).addAll(row.get(p2) ?? [], -1);
            if (r.isHard()) this.m.le(e, 1);
            else {
              const y = this.m.bool();
              this.m.le(e.add(y, -1), 1);
              this.pen.push([y, sw(r)]);
            }
          }
        }
      }
    }
  }

  private maxRun(occs: Occ[], N: number, r: Rule) {
    const byDay = new Map<number, Map<number, Ref[]>>();
    for (const { d, p, vs } of this.cellsOf(occs).values()) {
      if (!byDay.has(d)) byDay.set(d, new Map());
      byDay.get(d)!.set(p, vs);
    }
    for (const row of byDay.values()) {
      for (let q = 0; q < this.P - N; q++) {
        const terms: Ref[][] = [];
        for (let p = q; p < q + N + 1; p++) if (row.has(p)) terms.push(row.get(p)!);
        if (terms.length > N) this.cap(Expr.of(terms.flat()), terms.length, N, r);
      }
    }
  }
}

function exclusive(a: Occ, b: Occ): boolean {
  if (a.i !== b.i) return false;
  return !(a.piece && b.piece && a.k !== b.k);
}

export interface CpCache { key?: string; M?: CpModelBuild }

export interface SolveCpOpts {
  seconds?: number; seed?: number; workers?: number; warmStart?: number[] | null; allowSplit?: boolean;
  piecesOut?: [number, number[]][]; hedefSaat?: number | null; referans?: Map<number, number> | null;
  takasOut?: { oynayan?: number }; forced?: Set<string> | null; cancelled?: () => boolean;
  stopWhenFull?: boolean; boundOut?: { saat?: number | null }; stopAtHours?: number | null;
  warmPieces?: Pieces | null; minHours?: number | null; pureObjective?: boolean;
  fixed?: Map<number, number | number[]> | null; modelCache?: CpCache | null;
}

let worldIds = new WeakMap<object, number>();
let nextWorldId = 1;
const idOf = (o: object) => {
  let id = worldIds.get(o);
  if (!id) { id = nextWorldId++; worldIds.set(o, id); }
  return id;
};

/** World + kurallar -> [positions, placed_hours, status]. */
export async function solveCpsat(w: World, ruleList: Rule[], o: SolveCpOpts = {}): Promise<[number[], number, string]> {
  const allowSplit = o.allowSplit ?? true;
  const forced = o.forced ?? impossibleGroups(w);
  const cacheKey = `${idOf(w)}|${idOf(ruleList)}|${allowSplit}|${[...forced].sort().join(';')}`;
  let M: CpModelBuild;
  if (o.modelCache && o.modelCache.key === cacheKey && o.modelCache.M) M = o.modelCache.M;
  else {
    M = new CpModelBuild(w, ruleList, allowSplit, forced);
    if (o.modelCache) { o.modelCache.key = cacheKey; o.modelCache.M = M; }
  }
  const { xs, su, splits } = M;
  const model = M.m.fork();

  const yerlesen = new Expr();
  let saatTerms = 0;
  w.cards.forEach((c, i) => {
    const agirlik = SAAT * c.duration * c.classes.length;
    for (const [, v] of xs[i]) { yerlesen.add(v, agirlik); saatTerms++; }
  });
  for (const [i, usList] of su) {
    const agirlik = SAAT * w.cards[i].classes.length;
    for (const us of usList) for (const [, v] of us) { yerlesen.add(v, agirlik); saatTerms++; }
  }
  if (o.minHours !== undefined && o.minHours !== null && saatTerms) model.ge(new Expr().plus(yerlesen), o.minHours * SAAT);
  const hedefSaat = o.hedefSaat ?? null;
  let oynadiRefs: [number, Ref][] = [];
  if (hedefSaat === null) {
    const obj = new Expr().plus(yerlesen);
    if (!o.pureObjective) {
      for (const [, bol, kesim] of splits) obj.add(bol, -SPLIT_PEN * kesim);
      for (const [v, c] of M.pen) obj.add(v, -c);
    }
    model.maximize(obj);
  } else {
    model.eq(new Expr().plus(yerlesen), hedefSaat * SAAT);
    const sapma = new Expr();
    for (const [, bol, kesim] of splits) sapma.add(bol, 1000 * kesim);
    for (const [v, c] of M.pen) sapma.add(v, c);
    const ref = o.referans ?? new Map<number, number>();
    for (let i = 0; i < xs.length; i++) {
      const eski = ref.get(i);
      if (eski === null || eski === undefined || eski < 0) continue;
      const ayni = xs[i].find(([idx]) => idx === eski);
      if (!ayni) continue;
      const oynadi = model.bool();
      model.eq(Expr.of([ayni[1]]), 1, [NOT(oynadi)]);
      model.eq(Expr.of([ayni[1]]), 0, [oynadi]);
      sapma.add(oynadi);
      oynadiRefs.push([i, oynadi]);
    }
    model.minimize(sapma);
  }
  for (const [i, yer] of o.fixed ?? new Map()) {
    if (i >= xs.length) continue;
    if (Array.isArray(yer)) {
      const usList = su.get(i) ?? [];
      if (usList.length === yer.length) {
        usList.forEach((us, k) => { for (const [sidx, v] of us) model.eq(Expr.of([v]), sidx === yer[k] ? 1 : 0); });
        for (const [, v] of xs[i]) model.eq(Expr.of([v]), 0);
      }
    } else if (yer !== null && yer !== undefined && yer >= 0) {
      for (const [sidx, v] of xs[i]) model.eq(Expr.of([v]), sidx === yer ? 1 : 0);
      for (const us of su.get(i) ?? []) for (const [, v] of us) model.eq(Expr.of([v]), 0);
    }
  }
  if (o.warmStart) {
    const wp = o.warmPieces ?? new Map();
    for (let i = 0; i < o.warmStart.length; i++) {
      if (i >= xs.length) break;
      const idx = o.warmStart[i];
      if (idx !== null && idx !== undefined && idx >= 0) {
        for (const [sidx, v] of xs[i]) model.hint(v, sidx === idx ? 1 : 0);
        for (const us of su.get(i) ?? []) for (const [, v] of us) model.hint(v, 0);
      } else if (wp.has(i) && su.has(i) && wp.get(i)!.length === su.get(i)!.length) {
        for (const [, v] of xs[i]) model.hint(v, 0);
        su.get(i)!.forEach((us, k) => { for (const [sidx, v] of us) model.hint(v, sidx === wp.get(i)![k] ? 1 : 0); });
      }
    }
  }
  const params: CpParams = { maxTimeInSeconds: o.seconds ?? 60, numWorkers: o.workers ?? defaultWorkers };
  if (o.seed) params.randomSeed = o.seed & 0x7fffffff;
  // Python _Full geri çağrısı: yerleşen >= hedef olunca dur. Hedef zaten sert
  // kısıt (min_hours) ise ilk çözüm hedeftedir: stop_after_first_solution aynı şey.
  if (o.stopWhenFull && hedefSaat === null && saatTerms) {
    const hedef = SAAT * (o.stopAtHours !== undefined && o.stopAtHours !== null ? Math.min(totalHours(w), o.stopAtHours) : totalHours(w));
    if (o.minHours !== undefined && o.minHours !== null && o.minHours * SAAT >= hedef) params.stopAfterFirstSolution = true;
  }
  const res = await getBackend().solve(model, params, o.cancelled);
  if (o.boundOut) o.boundOut.saat = (hedefSaat === null && o.pureObjective) ? Math.floor(res.bound / SAAT) : null;
  const positions = new Array<number>(w.cards.length).fill(-1);
  const parcalar = new Map<number, number[]>();
  if ((res.status === 'OPTIMAL' || res.status === 'FEASIBLE') && res.values) {
    const val = res.values;
    xs.forEach((row, i) => {
      for (const [idx, v] of row) if (val[v]) { positions[i] = idx; break; }
    });
    for (const [i, usList] of su) {
      if (positions[i] >= 0) continue;
      const yerler: number[] = [];
      for (const us of usList) {
        for (const [idx, v] of us) if (val[v]) { yerler.push(idx); break; }
      }
      if (yerler.length === usList.length && yerler.length) parcalar.set(i, yerler.sort((a, b) => a - b));
    }
  }
  if (o.piecesOut) o.piecesOut.push(...[...parcalar.entries()].sort((a, b) => a[0] - b[0]));
  let placed = 0;
  positions.forEach((idx, i) => { if (idx >= 0) placed += w.cards[i].duration * w.cards[i].classes.length; });
  for (const [i, v] of parcalar) placed += v.length * w.cards[i].classes.length;
  if (o.takasOut && o.referans && o.referans.size) {
    let oynayan = 0;
    for (const [i, eski] of o.referans) {
      if (eski === null || eski === undefined || eski < 0) continue;
      if (positions[i] !== eski) oynayan++;
    }
    o.takasOut.oynayan = oynayan;
  }
  void oynadiRefs;
  return [positions, placed, res.status === 'CANCELLED' ? 'UNKNOWN' : res.status];
}

function sample<T>(rng: () => number, pool: T[], k: number): T[] {
  const a = [...pool];
  for (let i = 0; i < k; i++) {
    const j = i + Math.floor(rng() * (a.length - i));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a.slice(0, k);
}

export function mulberry32(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const now = () => performance.now() / 1000;

/** Komşuluk aramasıyla eldeki çizelgeyi saat saat yükseltir. */
export async function lnsClimb(w: World, ruleList: Rule[], forced: Set<string>, posIn: number[], piecesIn: Pieces,
  hedef: number, o: { budget?: number; workers?: number; cancelled?: () => boolean; seed?: number;
    progress?: (saat: number) => void; modelCache?: CpCache | null }): Promise<[number[], Pieces, number, number]> {
  let pos = [...posIn];
  let pieces: Pieces = new Map(piecesIn);
  const rng = mulberry32(o.seed ?? 1);
  const t0 = now();
  const budget = o.budget ?? 45;
  let placed = 0;
  pos.forEach((x, i) => { if (x >= 0) placed += w.cards[i].duration * w.cards[i].classes.length; });
  for (const [i, v] of pieces) placed += v.length * w.cards[i].classes.length;
  const nCls = w.classes.length;
  const kinds = ['cevre', 'cevre+1', 'cevre2', 'cevre+2', 'rastgele3'];
  let tur = 0, k = 0;
  const allCls = Array.from({ length: nCls }, (_, i) => i);
  while (placed < hedef && now() - t0 < budget) {
    if (o.cancelled?.()) break;
    const U = pos.map((x, i) => [x, i] as const).filter(([x, i]) => x < 0 && !pieces.has(i) && w.cards[i].lockedAt === null).map(([, i]) => i);
    if (!U.length) break;
    const kind = kinds[k % kinds.length];
    k++;
    tur++;
    let obek = 3;
    let free: Set<number>;
    for (;;) {
      const off = (tur * obek) % U.length;
      const odak = [...U.slice(off), ...U.slice(0, off)].slice(0, obek);
      const tset = new Set(odak.map((i) => w.cards[i].teacher).filter((t) => t >= 0));
      let cset = new Set(odak.flatMap((i) => w.cards[i].classes));
      if (kind === 'cevre2') {
        for (const c of w.cards) if (c.teacher >= 0 && c.classes.some((ci) => cset.has(ci))) tset.add(c.teacher);
      } else if (kind === 'cevre+1') for (const x of sample(rng, allCls, Math.min(nCls, 1))) cset.add(x);
      else if (kind === 'cevre+2') for (const x of sample(rng, allCls, Math.min(nCls, 2))) cset.add(x);
      else if (kind === 'rastgele3') cset = new Set([...sample(rng, allCls, Math.min(nCls, 3)), ...cset]);
      free = new Set(odak);
      for (const c of w.cards) if (tset.has(c.teacher) || c.classes.some((ci) => cset.has(ci))) free.add(c.cid);
      if (free.size <= 80 || obek === 1) break;
      obek--;
    }
    const fixed = new Map<number, number | number[]>();
    pos.forEach((x, i) => {
      if (free.has(i) || w.cards[i].lockedAt !== null) return;
      if (x >= 0) fixed.set(i, x);
      else if (pieces.has(i)) fixed.set(i, [...pieces.get(i)!]);
    });
    const kalan = budget - (now() - t0);
    if (kalan < 2) break;
    const pcs: [number, number[]][] = [];
    const [pos2, placed2] = await solveCpsat(w, ruleList, {
      seconds: Math.min(7.0, kalan), workers: o.workers, allowSplit: true, piecesOut: pcs, forced,
      stopWhenFull: true, stopAtHours: hedef, minHours: placed + 1, fixed, warmStart: pos, warmPieces: pieces,
      seed: (o.seed ?? 1) + tur, cancelled: o.cancelled, modelCache: o.modelCache,
    });
    if (placed2 > placed) {
      pos = pos2;
      pieces = new Map(pcs);
      placed = placed2;
      k = 0;
      o.progress?.(placed);
    }
  }
  return [pos, pieces, placed, tur];
}

export interface OptimalProgress { asama: number; tur: number; saat: number; toplam: number; durum: string; ust?: number | null; gecen: number; oynayan?: number }
export interface AskInfo { saat: number; toplam: number; tur: number; gecen: number; durgun: number; ust: number | null }

/** OPTİMAL KİP — kanıt gelene kadar durmaz. Döner [pos, parçalar, saat, durum, tur] */
export async function solveOptimal(w: World, ruleList: Rule[], o: {
  referans?: Map<number, number> | null; allowSplit?: boolean; azamiSaniye?: number; workers?: number;
  progress?: (p: OptimalProgress) => void; cancelled?: () => boolean; askContinue?: ((i: AskInfo) => Promise<boolean>) | null;
  bilinenUst?: number | null; isitma?: [number[], number, boolean] | null;
}): Promise<[number[], Pieces, number, string, number]> {
  const allowSplit = o.allowSplit ?? true;
  const azami = o.azamiSaniye ?? 3600;
  const workers = o.workers ?? defaultWorkers;
  const forced = impossibleGroups(w);
  const baslangic = now();
  let enIyiPos = new Array<number>(w.cards.length).fill(-1);
  let enIyiParca: Pieces = new Map();
  let enIyiSaat = -1;
  let durum = 'NO_SOLUTION';
  let tur = 0;
  let ipucu: number[] | null = null;
  let ipucuParca: Pieces | null = null;
  let durgun = 0;
  let ustSinir: number | null = o.bilinenUst ?? null;
  if (o.isitma) {
    const [iPos, iSaat, iGecerli] = o.isitma;
    if (iPos && iPos.length === w.cards.length && iSaat > 0) {
      ipucu = [...iPos];
      ipucuParca = new Map();
      if (iGecerli) { enIyiPos = [...iPos]; enIyiParca = new Map(); enIyiSaat = iSaat; }
    }
  }
  const SORU_ARALIGI = 150.0;
  let sonSoru = now();
  const iptal = () => !!o.cancelled?.();
  const total = totalHours(w);
  let turSaniye = 20.0;
  const fizDenendi = new Set<number>();
  const onbellek: CpCache = {};
  while (!['OPTIMAL', 'STALLED', 'CANCELLED'].includes(durum)) {
    if (iptal()) { durum = 'CANCELLED'; break; }
    let kalan = azami - (now() - baslangic);
    if (kalan <= 1) break;
    let hedef = ustSinir === null ? total : Math.min(total, ustSinir);
    if (enIyiSaat >= hedef && enIyiSaat > 0) { durum = 'OPTIMAL'; break; }
    tur++;
    const pieces: [number, number[]][] = [];
    if (enIyiSaat > 0 && hedef - enIyiSaat > 0 && hedef - enIyiSaat <= 2 && !fizDenendi.has(hedef) && tur >= 1 && kalan > 5) {
      fizDenendi.add(hedef);
      const [pos, placed, st] = await solveCpsat(w, ruleList, {
        seconds: Math.min(60.0, kalan), workers, allowSplit, piecesOut: pieces, forced, cancelled: o.cancelled,
        stopWhenFull: true, stopAtHours: hedef, minHours: hedef, seed: tur * 7 + 3, modelCache: onbellek,
      });
      if (placed > enIyiSaat) {
        enIyiSaat = placed; enIyiPos = pos; enIyiParca = new Map(pieces);
        ipucu = pos; ipucuParca = new Map(pieces);
        durgun = 0;
      }
      if (st === 'INFEASIBLE') ustSinir = hedef - 1;
      o.progress?.({ asama: 1, tur, saat: enIyiSaat, toplam: total, durum: st, ust: ustSinir, gecen: now() - baslangic });
      continue;
    }
    const [pos, placed, st] = await solveCpsat(w, ruleList, {
      seconds: Math.min(turSaniye, kalan), workers, warmStart: ipucu, warmPieces: ipucuParca, allowSplit,
      piecesOut: pieces, forced, cancelled: o.cancelled, stopWhenFull: true, stopAtHours: ustSinir, seed: tur,
      modelCache: onbellek,
    });
    if (placed > enIyiSaat) {
      enIyiSaat = placed; enIyiPos = pos; enIyiParca = new Map(pieces);
      ipucu = pos; ipucuParca = new Map(pieces);
      durgun = 0;
    } else durgun++;
    durum = st;
    o.progress?.({ asama: 1, tur, saat: enIyiSaat, toplam: total, durum: st, ust: ustSinir, gecen: now() - baslangic });
    if (iptal()) { durum = 'CANCELLED'; break; }
    if (st === 'INFEASIBLE' || st === 'MODEL_INVALID') break;
    hedef = ustSinir === null ? total : Math.min(total, ustSinir);
    if (enIyiSaat >= hedef && enIyiSaat > 0) { durum = 'OPTIMAL'; break; }
    if (st === 'OPTIMAL') { ustSinir = enIyiSaat; durum = 'OPTIMAL'; break; }
    if (enIyiSaat > 0 && enIyiSaat < hedef) {
      kalan = azami - (now() - baslangic);
      const [posL, parcaL, placedL] = await lnsClimb(w, ruleList, forced, [...enIyiPos], new Map(enIyiParca), hedef, {
        budget: Math.min(75.0, Math.max(5.0, kalan)), workers, cancelled: o.cancelled, seed: tur,
        progress: (saat) => o.progress?.({ asama: 1, tur, saat, toplam: total, durum: 'LNS', ust: ustSinir, gecen: now() - baslangic }),
        modelCache: onbellek,
      });
      if (placedL > enIyiSaat) {
        enIyiSaat = placedL; enIyiPos = posL; enIyiParca = new Map(parcaL);
        ipucu = posL; ipucuParca = new Map(parcaL);
        durgun = 0;
        if (enIyiSaat >= hedef) { durum = 'OPTIMAL'; break; }
      }
    }
    const sureDoldu = now() - sonSoru >= SORU_ARALIGI;
    if (tur >= 2 && (durgun >= 1 || sureDoldu) && enIyiSaat > 0) {
      if (o.askContinue) {
        let devam = false;
        try {
          devam = await o.askContinue({ saat: enIyiSaat, toplam: total, tur, gecen: now() - baslangic, durgun, ust: ustSinir });
        } catch { devam = false; }
        sonSoru = now();
        if (!devam) { durum = 'STALLED'; break; }
        fizDenendi.clear();
      } else if (durgun >= 2) { durum = 'STALLED'; break; }
    }
    turSaniye = Math.min(turSaniye * 1.5, 40.0);
  }
  if (durum !== 'OPTIMAL' || enIyiSaat <= 0) return [enIyiPos, enIyiParca, Math.max(enIyiSaat, 0), durum, tur];

  // ── 2. AŞAMA: saati kilitle, takası en küçükle ──
  const ref = new Map(o.referans ?? []);
  let kalan = azami - (now() - baslangic);
  if (kalan <= 1) return [enIyiPos, enIyiParca, enIyiSaat, 'OPTIMAL', tur];
  const takasButcesi = Math.min(kalan * 0.25, 8.0);
  const takasBitis = now() + takasButcesi;
  let tur2 = 0;
  let takasSure = takasButcesi;
  for (;;) {
    tur2++;
    if (iptal()) break;
    kalan = Math.min(azami - (now() - baslangic), takasBitis - now());
    if (kalan <= 1) break;
    const pieces: [number, number[]][] = [];
    const takas: { oynayan?: number } = {};
    const [pos2, placed2, st2] = await solveCpsat(w, ruleList, {
      seconds: Math.min(takasSure, kalan), workers, warmStart: enIyiPos, warmPieces: enIyiParca, allowSplit,
      piecesOut: pieces, hedefSaat: enIyiSaat, referans: ref, takasOut: takas, forced, cancelled: o.cancelled,
      modelCache: onbellek,
    });
    if (placed2 === enIyiSaat && (st2 === 'OPTIMAL' || st2 === 'FEASIBLE') && pieces.length <= enIyiParca.size) {
      enIyiPos = pos2;
      enIyiParca = new Map(pieces);
    }
    o.progress?.({ asama: 2, tur: tur2, saat: enIyiSaat, toplam: total, durum: st2, oynayan: takas.oynayan, gecen: now() - baslangic });
    if (st2 === 'OPTIMAL' || st2 === 'INFEASIBLE' || st2 === 'MODEL_INVALID') break;
    takasSure = Math.min(takasSure * 2, takasButcesi);
  }
  return [enIyiPos, enIyiParca, enIyiSaat, 'OPTIMAL', tur + tur2];
}
