// scheduler/finish.py — bitirme geçişi: açıkta kalan son kartlar için
// tahliye zinciriyle derin arama. Başarısız dal birebir geri alınır.
import type { World } from './model.ts';
import { key } from './py.ts';
import * as R from './rules.ts';
import type { Rule } from './rules.ts';
import { validate } from './verify.ts';
import type { Pieces } from './verify.ts';

export class Finisher {
  w: World;
  P: number;
  pos: number[];
  rules: Rule[];
  forced: Set<string> | null;
  pieces: Pieces;
  subjectOnce: boolean;
  teacherOnce: boolean;
  subjectAdj: boolean;
  hardAdj = new Set<number>();
  clsCell = new Map<string, number>();
  tchCell = new Map<string, number>();
  famDay = new Map<string, Set<number>>();
  tchDay = new Map<string, Set<number>>();

  constructor(world: World, rules: Rule[], positions: number[], forced: Set<string> | null = null, pieces: Pieces | null = null) {
    this.w = world;
    this.P = world.P;
    this.pos = [...positions];
    this.rules = rules;
    this.forced = forced;
    this.pieces = new Map(pieces ?? []);
    this.subjectOnce = rules.some((r) => r.kind === R.X_SUBJECT_ONCE_DAY && r.isHard());
    this.teacherOnce = rules.some((r) => r.kind === R.X_TEACHER_ONCE_DAY && r.isHard());
    this.subjectAdj = rules.some((r) => r.kind === R.X_SUBJECT_NOT_ADJACENT && r.isHard());
    for (const r of rules) {
      if (r.kind === R.X_HARD_NOT_ADJACENT && r.isHard()) for (const s of r.subjects) this.hardAdj.add(world.subjectFamily[s]);
    }
    this.pos.forEach((idx, i) => { if (idx >= 0) this.occupy(i, idx, true); });
    for (const [i, cells] of this.pieces) {
      const c = world.cards[i];
      for (const cell of cells) {
        for (const ci of c.classes) {
          this.clsCell.set(key(ci, cell), -1 - i);
          this.day(this.famDay, ci, Math.floor(cell / this.P)).add(c.family);
          if (c.teacher >= 0) this.day(this.tchDay, ci, Math.floor(cell / this.P)).add(c.teacher);
        }
        if (c.teacher >= 0) this.tchCell.set(key(c.teacher, cell), -1 - i);
      }
    }
  }

  private day(m: Map<string, Set<number>>, ci: number, d: number): Set<number> {
    const k = key(ci, d);
    let s = m.get(k);
    if (!s) { s = new Set(); m.set(k, s); }
    return s;
  }

  private occupy(i: number, idx: number, on: boolean) {
    const c = this.w.cards[i];
    const d = Math.floor(idx / this.P);
    for (let off = 0; off < c.duration; off++) {
      const cell = idx + off;
      for (const ci of c.classes) {
        if (on) this.clsCell.set(key(ci, cell), i); else this.clsCell.delete(key(ci, cell));
      }
      if (c.teacher >= 0) {
        if (on) this.tchCell.set(key(c.teacher, cell), i); else this.tchCell.delete(key(c.teacher, cell));
      }
    }
    for (const ci of c.classes) {
      if (on) {
        this.day(this.famDay, ci, d).add(c.family);
        if (c.teacher >= 0) this.day(this.tchDay, ci, d).add(c.teacher);
      } else {
        const owners: number[] = [];
        for (const [k, j] of this.clsCell) {
          const [cj, cell] = k.split('\u0001').map(Number);
          if (cj === ci && Math.floor(cell / this.P) === d) owners.push(j < 0 ? -1 - j : j);
        }
        this.famDay.set(key(ci, d), new Set(owners.map((j) => this.w.cards[j].family)));
        this.tchDay.set(key(ci, d), new Set(owners.map((j) => this.w.cards[j].teacher).filter((t) => t >= 0)));
      }
    }
  }

  private rulesOk(i: number, idx: number): boolean {
    const c = this.w.cards[i];
    const d = Math.floor(idx / this.P), p = idx % this.P;
    for (const ci of c.classes) {
      if (this.subjectOnce && this.day(this.famDay, ci, d).has(c.family)) return false;
      if (this.teacherOnce && c.teacher >= 0 && this.day(this.tchDay, ci, d).has(c.teacher)) return false;
      if (this.hardAdj.has(c.family) || this.subjectAdj) {
        for (const nb of [p - 1, p + c.duration]) {
          if (nb < 0 || nb >= this.P) continue;
          const j = this.clsCell.get(key(ci, d * this.P + nb));
          if (j === undefined) continue;
          const o = this.w.cards[j < 0 ? -1 - j : j];
          if (this.hardAdj.has(c.family) && this.hardAdj.has(o.family) && o.family !== c.family) return false;
          if (this.subjectAdj && o.family === c.family) return false;
        }
      }
    }
    return true;
  }

  private blockers(i: number, idx: number): Set<number> {
    const c = this.w.cards[i];
    const out = new Set<number>();
    for (let off = 0; off < c.duration; off++) {
      const cell = idx + off;
      for (const ci of c.classes) {
        const j = this.clsCell.get(key(ci, cell));
        if (j !== undefined) out.add(j);
      }
      if (c.teacher >= 0) {
        const j = this.tchCell.get(key(c.teacher, cell));
        if (j !== undefined) out.add(j);
      }
    }
    return out;
  }

  private free(i: number, idx: number): boolean {
    return this.blockers(i, idx).size === 0;
  }

  private place(i: number, depth: number, maxDepth: number, banned: Set<number>): boolean {
    const c = this.w.cards[i];
    for (const idx of c.slots) {
      if (this.free(i, idx) && this.rulesOk(i, idx)) {
        this.pos[i] = idx;
        this.occupy(i, idx, true);
        return true;
      }
    }
    if (depth >= maxDepth) return false;
    for (const idx of c.slots) {
      if (!this.rulesOk(i, idx)) continue;
      const blk = [...this.blockers(i, idx)].sort((a, b) => a - b);
      if (!blk.length || blk.length > 2 || blk.some((j) => banned.has(j)) || blk.some((j) => j < 0)
        || blk.some((j) => this.w.cards[j].lockedAt !== null)) continue;   // kilitli ders asla tahliye edilmez
      const snap = [...this.pos];
      const moved: number[] = [];
      for (const j of blk) {
        this.occupy(j, this.pos[j], false);
        this.pos[j] = -1;
        moved.push(j);
      }
      if (this.free(i, idx) && this.rulesOk(i, idx)) {
        this.pos[i] = idx;
        this.occupy(i, idx, true);
        let ok = true;
        const nb = new Set([...banned, ...blk, i]);
        for (const j of moved) {
          if (!this.place(j, depth + 1, maxDepth, nb)) { ok = false; break; }
        }
        if (ok) return true;
      }
      this.restore(snap);
    }
    return false;
  }

  private restore(snap: number[]) {
    this.pos.forEach((idx, i) => {
      if (idx >= 0 && snap[i] !== idx) { this.occupy(i, idx, false); this.pos[i] = -1; }
    });
    snap.forEach((idx, i) => {
      if (idx >= 0 && this.pos[i] < 0 && this.free(i, idx)) { this.pos[i] = idx; this.occupy(i, idx, true); }
    });
  }

  run(maxDepth = 4): [number[], number] {
    const eksik = this.pos.map((idx, i) => [idx, i] as const)
      .filter(([idx, i]) => idx < 0 && this.w.cards[i].slots.length && !this.pieces.has(i)).map(([, i]) => i);
    let kazanc = 0;
    for (const i of [...eksik].sort((a, b) => this.w.cards[a].slots.length - this.w.cards[b].slots.length)) {
      if (this.pos[i] >= 0) continue;
      const snap = [...this.pos];
      if (this.place(i, 0, maxDepth, new Set())) {
        const [errs] = validate(this.w, this.rules, this.pos, true, this.forced, this.pieces);
        if (errs.length) { this.restore(snap); continue; }
        kazanc += this.w.cards[i].duration * this.w.cards[i].classes.length;
      }
    }
    return [this.pos, kazanc];
  }
}
