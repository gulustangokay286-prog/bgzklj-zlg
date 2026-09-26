// scheduler/problem.py — kuralları C++ tabu aramasının problem metnine derler.
// Üretilen metin Python'unkiyle BİREBİR aynı olmalıdır (tools/golden ile
// denetlenir): aynı metin + aynı tohum = aynı arama.
import type { Card, World } from './model.ts';
import { noonOf } from './build.ts';
import { key } from './py.ts';
import * as R from './rules.ts';
import type { Rule } from './rules.ts';

const PAIR_KINDS = new Set([R.X_SUBJECT_ONCE_DAY, R.X_TEACHER_ONCE_DAY, R.X_PAIR_NOT_SAME_DAY,
  R.X_HARD_NOT_ADJACENT, R.X_MIN_DAYS_BETWEEN, R.X_SUBJECT_NOT_ADJACENT]);
const FACTOR_KINDS = new Set([R.X_SUBJECT_MAX_HOURS, R.X_PRACTICAL_MAX_HOURS, R.X_SUBJECT_MAX_SESSIONS,
  R.X_CLASS_MAX_HOURS, R.X_TEACHER_MAX_HOURS, R.X_TEACHER_MAX_DAYS, R.X_SAME_DAY_ADJACENT,
  R.X_NO_CLASS_GAP, R.X_NO_TEACHER_GAP, R.X_TEACHER_MAX_RUN, R.X_EVEN_SPREAD,
  R.Y_SUBJECT_MAX_PARALLEL, R.Y_TEACHER_MAX_PARALLEL]);
const CORE_KINDS = new Set([R.Y_CLASS_CLASH, R.Y_TEACHER_CLASH, R.Y_CLOSED_CELL, R.Y_CROSS_INSTITUTION]);

/** ('s'|'t', sınıf, kaynak) anahtarı */
export function forcedKey(which: 's' | 't', ci: number, res: number): string {
  return key(which, ci, res);
}

/** Kart sayısı ulaşılabilir gün sayısını aşan gruplar (aritmetik taban). */
export function impossibleGroups(w: World): Set<string> {
  const subj = new Map<string, Card[]>(), tch = new Map<string, Card[]>();
  const push = (m: Map<string, Card[]>, k: string, c: Card) => {
    const l = m.get(k);
    if (l) l.push(c); else m.set(k, [c]);
  };
  for (const c of w.cards) {
    for (const ci of c.classes) {
      if (c.family >= 0) push(subj, key(ci, c.family), c);
      if (c.teacher >= 0) push(tch, key(ci, c.teacher), c);
    }
  }
  const impossible = (items: Card[]) => {
    if (items.length < 2) return false;
    const days = new Set<number>();
    for (const c of items) for (const idx of c.slots) days.add(Math.floor(idx / w.P));
    return items.length > days.size;
  };
  const out = new Set<string>();
  for (const [k, items] of subj) if (impossible(items)) out.add('s\u0001' + k);
  for (const [k, items] of tch) if (impossible(items)) out.add('t\u0001' + k);
  return out;
}

interface Factor { kind: number; limit: number; hard: boolean; weight: number; cards: number[]; label: string }

export class Problem {
  world: World;
  rules: Rule[];
  completionFirst: boolean;
  forcedGroups: Set<string>;
  edges: [number, number, number[], number[]][] = [];
  factors: Factor[] = [];
  softUnary: number[][] = [];
  domains: number[][];
  errors: string[] = [];
  private bodyCache: string | null = null;

  constructor(world: World, rules: Rule[], completionFirst = true) {
    this.world = world;
    this.rules = rules;
    this.completionFirst = completionFirst;
    this.forcedGroups = completionFirst ? impossibleGroups(world) : new Set();
    this.domains = world.cards.map((c) => [...c.slots]);
    for (const r of rules) {
      if (!(PAIR_KINDS.has(r.kind) || FACTOR_KINDS.has(r.kind) || CORE_KINDS.has(r.kind)
        || R.WINDOW_RULES.has(r.kind) || R.DEFINITION_RULES.has(r.kind))) {
        this.errors.push(`Desteklenmeyen kural: ${r.label}`);
      }
    }
    this.compileUnary();
    this.compilePairs();
    this.compileFactors();
  }

  private compileUnary() {
    const w = this.world;
    const noon = noonOf(w.P);
    for (const c of w.cards) {
      const costs: number[] = [];
      for (const idx of c.slots) {
        const p = idx % w.P;
        let cost = 0;
        for (const ci of c.classes) for (let k = 0; k < c.duration; k++) cost += w.classAvoid[ci][idx + k];
        if (c.teacher >= 0) for (let k = 0; k < c.duration; k++) cost += w.teacherAvoid[c.teacher][idx + k];
        for (const r of this.rules) {
          if (r.isHard() || !R.WINDOW_RULES.has(r.kind) || !r.appliesCard(c)) continue;
          const bad = (r.kind === R.X_MORNING_ONLY && p + c.duration > noon)
            || (r.kind === R.X_AFTERNOON_ONLY && p < noon)
            || (r.kind === R.X_NOT_LAST_PERIOD && p + c.duration > w.P - 1)
            || (r.kind === R.X_NOT_FIRST_PERIOD && p === 0)
            || (r.kind === R.X_TIME_WINDOW && (p < r.param || p + c.duration - 1 > r.param2));
          cost += (bad ? 1 : 0) * r.penalty();
        }
        costs.push(cost);
      }
      this.softUnary.push(costs);
    }
  }

  private compilePairs() {
    const w = this.world, P = w.P;
    const pairRules = this.rules.filter((r) => PAIR_KINDS.has(r.kind));
    for (let i = 0; i < w.cards.length; i++) {
      const a = w.cards[i];
      for (let j = 0; j < i; j++) {
        const b = w.cards[j];
        const shared = a.classes.filter((ci) => b.classes.includes(ci));
        const teacher = a.teacher >= 0 && a.teacher === b.teacher;
        if (!shared.length && !teacher) continue;
        const ayniDers = shared.length > 0 && a.subject === b.subject;
        const relevant = pairRules.filter((r) => r.appliesCard(a) && r.appliesCard(b)
          && shared.some((ci) => r.appliesClass(ci)));
        const sameFamily = a.family >= 0 && a.family === b.family;
        const checks: [number, Rule][] = [];
        for (const r of relevant) {
          if (r.kind === R.X_SUBJECT_ONCE_DAY && sameFamily) checks.push([0, r]);
          else if (r.kind === R.X_TEACHER_ONCE_DAY && teacher) checks.push([0, r]);
          else if (r.kind === R.X_PAIR_NOT_SAME_DAY && a.subject !== b.subject) checks.push([0, r]);
          else if (r.kind === R.X_HARD_NOT_ADJACENT && !sameFamily) checks.push([1, r]);
          else if (r.kind === R.X_SUBJECT_NOT_ADJACENT && sameFamily) checks.push([1, r]);
          else if (r.kind === R.X_MIN_DAYS_BETWEEN && sameFamily) checks.push([2, r]);
        }
        const forcedSubject = sameFamily && shared.some((ci) => this.forcedGroups.has(forcedKey('s', ci, a.family)));
        const forcedTeacher = a.teacher >= 0 && a.teacher === b.teacher
          && shared.some((ci) => this.forcedGroups.has(forcedKey('t', ci, a.teacher)));
        const hard: number[] = [], soft: number[] = [];
        let anyH = false, anyS = false;
        for (const ax of a.slots) {
          const ad = Math.floor(ax / P), ap = ax % P;
          for (const bx of b.slots) {
            const bd = Math.floor(bx / P), bp = bx % P;
            let h = (ad === bd && ax < bx + b.duration && bx < ax + a.duration) ? 1 : 0;
            let s = 0;
            const bitisik = ap + a.duration === bp || bp + b.duration === ap;
            if (ayniDers && ad === bd && !bitisik) h = 1;
            for (const [kind, r] of checks) {
              const ayniGunTekrar = ad === bd && !(bitisik && a.origin === b.origin
                && (r.kind === R.X_SUBJECT_ONCE_DAY || r.kind === R.X_TEACHER_ONCE_DAY));
              const hit = (kind === 0 && ayniGunTekrar) || (kind === 1 && ad === bd && bitisik)
                || (kind === 2 && Math.abs(ad - bd) < Math.max(1, r.param));
              const bendable = (r.kind === R.X_SUBJECT_ONCE_DAY || r.kind === R.X_MIN_DAYS_BETWEEN) ? forcedSubject
                : r.kind === R.X_TEACHER_ONCE_DAY ? forcedTeacher : false;
              if (hit) {
                if (!r.isHard()) s += r.penalty();
                else if (bendable) {
                  const adjacent = ap + a.duration === bp || bp + b.duration === ap;
                  if (!adjacent) h = 1;
                } else h = 1;
              }
            }
            hard.push(h);
            soft.push(s);
            if (h) anyH = true;
            if (s) anyS = true;
          }
        }
        if (anyH || anyS) this.edges.push([i, j, hard, soft]);
      }
    }
  }

  private compileFactors() {
    const w = this.world;
    const KIND: Record<string, number> = {
      [R.X_SUBJECT_MAX_HOURS]: 0, [R.X_PRACTICAL_MAX_HOURS]: 0, [R.X_CLASS_MAX_HOURS]: 0,
      [R.X_TEACHER_MAX_HOURS]: 0, [R.X_SUBJECT_MAX_SESSIONS]: 1, [R.X_TEACHER_MAX_DAYS]: 2,
      [R.X_SAME_DAY_ADJACENT]: 3, [R.X_NO_CLASS_GAP]: 3, [R.X_NO_TEACHER_GAP]: 3,
      [R.X_TEACHER_MAX_RUN]: 4, [R.X_EVEN_SPREAD]: 5, [R.Y_SUBJECT_MAX_PARALLEL]: 6,
      [R.Y_TEACHER_MAX_PARALLEL]: 6,
    };
    const teacherKinds = new Set([R.X_TEACHER_MAX_HOURS, R.X_TEACHER_MAX_DAYS, R.X_NO_TEACHER_GAP, R.X_TEACHER_MAX_RUN]);
    const familyKeyed = new Set([R.X_SUBJECT_MAX_HOURS, R.X_PRACTICAL_MAX_HOURS, R.X_SUBJECT_MAX_SESSIONS, R.X_EVEN_SPREAD]);
    for (const r of this.rules) {
      if (!FACTOR_KINDS.has(r.kind)) continue;
      const groups = new Map<string, number[]>();
      const add = (k: string, cid: number) => {
        const l = groups.get(k);
        if (l) l.push(cid); else groups.set(k, [cid]);
      };
      for (const c of w.cards) {
        if (!r.appliesCard(c)) continue;
        if (teacherKinds.has(r.kind)) {
          if (c.teacher >= 0) add(String(c.teacher), c.cid);
        } else if (r.kind === R.Y_SUBJECT_MAX_PARALLEL || r.kind === R.Y_TEACHER_MAX_PARALLEL) {
          add(String(r.kind === R.Y_SUBJECT_MAX_PARALLEL ? c.family : c.teacher), c.cid);
        } else {
          for (const ci of c.classes) {
            if (!r.appliesClass(ci)) continue;
            add(familyKeyed.has(r.kind) ? key(ci, c.family) : String(ci), c.cid);
          }
        }
      }
      for (const cards of groups.values()) {
        this.factors.push({ kind: KIND[r.kind], limit: Math.max(1, r.param), hard: r.isHard(),
          weight: r.penalty(), cards, label: r.label });
      }
    }
  }

  /** Tohumdan bağımsız gövde — bir kez üretilir. */
  body(): string {
    if (this.bodyCache !== null) return this.bodyCache;
    const w = this.world;
    const out: string[] = [];
    w.cards.forEach((c, i) => {
      const domain = this.domains[i], soft = this.softUnary[i];
      out.push(`${c.duration} ${c.duration * c.classes.length} ${c.lockedAt !== null ? 1 : 0} ${domain.length || 1} `);
      out.push(domain.length ? domain.map((p, k) => `${p} ${soft[k]}`).join(' ') : '-1 0');
      out.push('\n');
    });
    for (const [i, j, hardIn, softIn] of this.edges) {
      let hard = hardIn, soft = softIn;
      const nh = Math.max(1, this.domains[i].length) * Math.max(1, this.domains[j].length);
      if (!hard.length) { hard = new Array(nh).fill(0); soft = new Array(nh).fill(0); }
      const parts: string[] = [];
      for (let k = 0; k < hard.length; k++) parts.push(`${hard[k]} ${soft[k]}`);
      out.push(`${i} ${j} ${parts.join(' ')}\n`);
    }
    for (const f of this.factors) {
      out.push(`${f.kind} ${f.limit} ${f.hard ? 1 : 0} ${f.weight} ${f.cards.length} ${f.cards.join(' ')}\n`);
    }
    this.bodyCache = out.join('');
    return this.bodyCache;
  }

  header(seconds: number, seed: number, upperBound: number): string {
    const w = this.world;
    return `2 ${w.cards.length} ${this.edges.length} ${this.factors.length} ${w.D} ${w.P} ${seconds} ${seed} ${upperBound}\n`;
  }

  write(seconds: number, seed: number, upperBound: number): string {
    return this.header(seconds, seed, upperBound) + this.body();
  }
}
