// scheduler/diagnostics.py — yeniden üretilebilir tanıklarla gerekli koşullar.
import type { Card, World } from './model.ts';
import { familyName, totalHours } from './model.ts';
import { key } from './py.ts';
import * as R from './rules.ts';
import type { Rule } from './rules.ts';

export interface Issue {
  kind: string;
  message: string;
  cards: number[];
  min_unplaced_hours?: number;
  suggested_unplaced?: number[];
  [k: string]: unknown;
}

export function diagnose(world: World, rules: Rule[]): [Issue[], number] {
  const issues: Issue[] = [];
  const deficits: [number, Set<number>][] = [];
  const seen = new Set<string>();
  const P = world.P;
  for (const r of rules) {
    if (!r.isHard() || (r.kind !== R.X_SUBJECT_ONCE_DAY && r.kind !== R.X_TEACHER_ONCE_DAY)) continue;
    const groups = new Map<string, { ci: number; resource: number; cards: Card[] }>();
    for (const c of world.cards) {
      if (!r.appliesCard(c)) continue;
      const resource = r.kind === R.X_SUBJECT_ONCE_DAY ? c.family : c.teacher;
      if (resource < 0) continue;
      for (const ci of c.classes) {
        if (!r.appliesClass(ci)) continue;
        const k = key(ci, resource);
        let g = groups.get(k);
        if (!g) { g = { ci, resource, cards: [] }; groups.set(k, g); }
        g.cards.push(c);
      }
    }
    for (const { ci, resource, cards } of groups.values()) {
      const owner = new Map<number, number>();
      const allowed = new Map<number, number[]>();
      for (const c of cards) allowed.set(c.cid, [...new Set(c.slots.map((s) => Math.floor(s / P)))].sort((a, b) => a - b));
      const augment = (cid: number, visited: Set<number>): boolean => {
        for (const day of allowed.get(cid)!) {
          if (visited.has(day)) continue;
          visited.add(day);
          if (!owner.has(day) || augment(owner.get(day)!, visited)) {
            owner.set(day, cid);
            return true;
          }
        }
        return false;
      };
      const matched: Card[] = [];
      for (const c of [...cards].sort((a, b) => b.duration * b.classes.length - a.duration * a.classes.length)) {
        if (augment(c.cid, new Set())) matched.push(c);
      }
      const hrs = (xs: Card[]) => xs.reduce((s, c) => s + c.duration * c.classes.length, 0);
      const missing = hrs(cards) - hrs(matched);
      const ids = new Set(cards.map((c) => c.cid));
      const idsKey = [...ids].sort((a, b) => a - b).join(',');
      if (missing <= 0 || seen.has(idsKey)) continue;
      seen.add(idsKey);
      const days = [...new Set([...allowed.values()].flat())].sort((a, b) => a - b);
      const name = r.kind === R.X_SUBJECT_ONCE_DAY ? familyName(world, resource) : world.teachers[resource];
      const message = `${world.classes[ci]} · ${name}: ${cards.length} ayrı kart (${cards.map((c) => c.duration).join('+')}) için `
        + `${days.length} uygun gün var. ‘${r.label}’ kuralıyla en az ${missing} sınıf-saati yerleşemez.`;
      const owned = new Set(owner.values());
      issues.push({ kind: 'day_capacity', rule: r.label, message, class: world.classes[ci], resource: name,
        cards: [...ids].sort((a, b) => a - b), available_days: days, min_unplaced_hours: missing,
        suggested_unplaced: [...ids].filter((x) => !owned.has(x)).sort((a, b) => a - b) });
      deficits.push([missing, ids]);
    }
  }
  world.classDemand.forEach((demand, ci) => {
    const capacity = world.classCapacity[ci];
    if (demand > capacity) {
      const ids = new Set(world.cards.filter((c) => c.classes.includes(ci)).map((c) => c.cid));
      const missing = demand - capacity;
      issues.push({ kind: 'class_capacity', message: `${world.classes[ci]}: ${demand} saat ders, ${capacity} açık saat.`,
        min_unplaced_hours: missing, cards: [...ids].sort((a, b) => a - b) });
      deficits.push([missing, ids]);
    }
  });
  world.teachers.forEach((name, ti) => {
    const cards = world.cards.filter((c) => c.teacher === ti);
    const needed = cards.reduce((s, c) => s + c.duration, 0);
    const available = new Set<number>();
    for (const c of cards) for (const idx of c.slots) for (let k = 0; k < c.duration; k++) available.add(idx + k);
    const capacity = available.size;
    if (needed > capacity) {
      const ids = new Set(cards.map((c) => c.cid));
      const missing = needed - capacity;
      issues.push({ kind: 'teacher_capacity', message: `${name}: ${needed} saat ders, sınıflarıyla ortak ${capacity} uygun saat.`,
        teacher: name, assigned: needed, available: capacity, min_unplaced_hours: missing, cards: [...ids].sort((a, b) => a - b) });
      deficits.push([missing, ids]);
    }
  });
  for (const c of world.cards) {
    if (!c.slots.length) {
      const missing = c.duration * c.classes.length;
      issues.push({ kind: 'no_slot', message: `${c.classNames.join(' + ')} · ${c.subjectName}: ${c.duration} saatlik kart için uygun başlangıç yok.`,
        min_unplaced_hours: missing, cards: [c.cid] });
      deficits.push([missing, new Set([c.cid])]);
    }
  }
  const used = new Set<number>();
  let missingBound = 0;
  for (const [missing, ids] of [...deficits].sort((a, b) => (b[0] - a[0]) || (a[1].size - b[1].size))) {
    if (![...ids].some((x) => used.has(x))) {
      for (const x of ids) used.add(x);
      missingBound += missing;
    }
  }
  return [issues, Math.max(0, totalHours(world) - missingBound)];
}
