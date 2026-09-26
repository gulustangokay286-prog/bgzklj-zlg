// scheduler/build.py — data_store -> World.
import { getMatrix, gridDimensions, hours, subjectOf, teacherOf, typeStr } from './data.ts';
import type { Store } from './data.ts';
import type { Card, World } from './model.ts';
import { normClass, normKey } from './norm.ts';
import { isDigit, truthy } from './py.ts';
import * as R from './rules.ts';
import type { Rule } from './rules.ts';


/** timeoff matrisi -> (kapalı, kaçın) hücre bayrakları. 0=KAPALI 1=KAÇIN 2=AÇIK */
function states(matrix: unknown, D: number, P: number): [Uint8Array, Uint8Array] {
  const closed = new Uint8Array(D * P), avoid = new Uint8Array(D * P);
  if (!Array.isArray(matrix)) return [closed, avoid];
  for (let d = 0; d < Math.min(D, matrix.length); d++) {
    const row = matrix[d];
    if (!Array.isArray(row)) continue;
    for (let p = 0; p < Math.min(P, row.length); p++) {
      const v = typeof row[p] === 'number' ? Math.trunc(row[p]) : 2;
      if (v === 0) closed[d * P + p] = 1;
      else if (v === 1) avoid[d * P + p] = 1;
    }
  }
  return [closed, avoid];
}

/** Dağılım metnini kart uzunluklarına çevirir. */
export function parseDistribution(typeStr_: unknown, total: number): number[] {
  const t = String(typeStr_ ?? '').trim();
  const parts: number[] = [];
  if (t.includes('+')) {
    for (let piece of t.split('+')) {
      piece = piece.trim();
      if (isDigit(piece) && parseInt(piece, 10) > 0) parts.push(parseInt(piece, 10));
    }
  } else if (isDigit(t) && parseInt(t, 10) > 0) {
    let rem = parseInt(t, 10);
    while (rem > 0) {
      const b = Math.min(2, rem);
      parts.push(b);
      rem -= b;
    }
  }
  if (!parts.length && total > 0) {
    let rem = total;
    while (rem > 0) {
      const b = Math.min(2, rem);
      parts.push(b);
      rem -= b;
    }
  }
  return parts.length ? parts : (total ? [total] : []);
}

function splitClasses(raw: string): string[] {
  for (const sep of ['&', ',', '/']) raw = raw.split(sep).join('+');
  return raw.split('+').map((p) => p.trim()).filter(Boolean);
}

function nameOf(e: any): string {
  return String((truthy(e?.ad) ? e.ad : truthy(e?.name) ? e.name : '') ?? '').trim();
}

export function buildWorld(data: Store, opts: {
  D?: number | null; P?: number | null; crossBusy?: Map<string, [number, number][]> | null; onlyClasses?: string[] | null;
} = {}): World {
  const [defD, defP] = gridDimensions(data);
  const D = opts.D ?? defD, P = opts.P ?? defP;
  if (D <= 0 || P <= 0) throw new Error('Gün ve saat sayısı pozitif olmalı');

  const classNames: string[] = [], teacherNames: string[] = [], subjectNames: string[] = [];
  const classIx = new Map<string, number>(), teacherIx = new Map<string, number>(), subjectIx = new Map<string, number>();
  const list = (k: string): any[] => (truthy(data[k]) ? data[k] : []);

  for (const c of list('siniflar')) {
    const n = nameOf(c);
    if (n && !classIx.has(normClass(n))) { classIx.set(normClass(n), classNames.length); classNames.push(n); }
  }
  for (const t of list('ogretmenler')) {
    const n = nameOf(t);
    if (n && !teacherIx.has(normKey(n))) { teacherIx.set(normKey(n), teacherNames.length); teacherNames.push(n); }
  }
  for (const s of list('dersler')) {
    const n = nameOf(s);
    if (n && !subjectIx.has(normKey(n))) { subjectIx.set(normKey(n), subjectNames.length); subjectNames.push(n); }
  }
  for (const a of list('atamalar')) {
    const s = subjectOf(a);
    if (s && !subjectIx.has(normKey(s))) { subjectIx.set(normKey(s), subjectNames.length); subjectNames.push(s); }
    const t = teacherOf(a);
    if (t && t !== '—' && t !== 'Atanmadı' && !teacherIx.has(normKey(t))) { teacherIx.set(normKey(t), teacherNames.length); teacherNames.push(t); }
  }

  const nC = classNames.length, nT = teacherNames.length, N = D * P;
  const classClosed = Array.from({ length: nC }, () => new Uint8Array(N));
  const classAvoid = Array.from({ length: nC }, () => new Uint8Array(N));
  const teacherClosed = Array.from({ length: nT }, () => new Uint8Array(N));
  const teacherAvoid = Array.from({ length: nT }, () => new Uint8Array(N));
  const orInto = (dst: Uint8Array, src: Uint8Array) => { for (let i = 0; i < N; i++) if (src[i]) dst[i] = 1; };

  for (const c of list('siniflar')) {
    const n = nameOf(c);
    const i = classIx.get(normClass(n));
    if (i === undefined) continue;
    const [cl, av] = states(getMatrix(c, n, data), D, P);
    orInto(classClosed[i], cl);
    orInto(classAvoid[i], av);
  }
  for (const t of list('ogretmenler')) {
    const n = nameOf(t);
    const i = teacherIx.get(normKey(n));
    if (i === undefined) continue;
    const [cl, av] = states(getMatrix(t, n, data), D, P);
    orInto(teacherClosed[i], cl);
    orInto(teacherAvoid[i], av);
  }
  for (const [name, slots] of opts.crossBusy ?? []) {
    const i = teacherIx.get(normKey(name));
    if (i === undefined) continue;
    for (const [d, p] of slots) if (d >= 0 && d < D && p >= 0 && p < P) teacherClosed[i][d * P + p] = 1;
  }

  const want = opts.onlyClasses && opts.onlyClasses.length ? new Set(opts.onlyClasses.map(normClass)) : null;
  const cards: Card[] = [];
  list('atamalar').forEach((a, ai) => {
    const rawC = String((truthy(a?.class) ? a.class : truthy(a?.sinif) ? a.sinif : truthy(a?.class_name) ? a.class_name : '') ?? '').trim();
    if (!rawC) return;
    const partsC = classIx.has(normClass(rawC)) ? [rawC] : splitClasses(rawC);
    for (const e of (truthy(a.combined_classes) ? a.combined_classes : [])) {
      if (truthy(e) && !partsC.includes(String(e).trim())) partsC.push(String(e).trim());
    }
    const idxs: number[] = [];
    for (const pc of partsC) {
      const i = classIx.get(normClass(pc));
      if (i !== undefined && !idxs.includes(i)) idxs.push(i);
    }
    if (!idxs.length) throw new Error(`Atamadaki sınıf bulunamadı: ${rawC}`);
    if (want && !idxs.some((i) => want.has(normClass(classNames[i])))) return;
    const sName = subjectOf(a), tName = teacherOf(a);
    const sIdx = subjectIx.get(normKey(sName)) ?? -1;
    const tIdx = teacherIx.get(normKey(tName)) ?? -1;
    const total = hours(a);
    for (const dur of parseDistribution(typeStr(a), total)) {
      cards.push({
        cid: cards.length, classes: [...idxs], subject: sIdx, teacher: tIdx, duration: dur,
        origin: ai, group: ai, lockedAt: null, family: sIdx >= 0 ? sIdx : -1, slots: [],
        subjectName: sName, teacherName: tName, classNames: idxs.map((i) => classNames[i]),
      });
    }
  });

  const world: World = {
    D, P, classes: classNames, teachers: teacherNames, subjects: subjectNames, cards,
    classClosed, teacherClosed, classAvoid, teacherAvoid,
    classCapacity: classClosed.map((m) => N - m.reduce((s, v) => s + v, 0)),
    classDemand: new Array(nC).fill(0),
    families: [...subjectNames], subjectFamily: subjectNames.map((_, i) => i),
  };
  for (const c of cards) for (const ci of c.classes) world.classDemand[ci] += c.duration;
  return world;
}

/** "Seçilen dersler aynı ders sayılsın" kurallarını dünyaya işler. */
export function applySubjectGroups(world: World, rules: Rule[]): World {
  const groups = rules.filter((r) => r.kind === R.X_SUBJECT_GROUP);
  const n = world.subjects.length;
  const parent = Array.from({ length: n }, (_, i) => i);
  const find = (x: number): number => {
    while (parent[x] !== x) {
      parent[x] = parent[parent[x]];
      x = parent[x];
    }
    return x;
  };
  for (const r of groups) {
    const members = [...r.subjects].sort((a, b) => a - b);
    for (const s of members.slice(1)) {
      const a = find(members[0]), b = find(s);
      if (a !== b) parent[Math.max(a, b)] = Math.min(a, b);
    }
  }
  const rootIx = new Map<number, number>(), famNames: string[] = [], membersOf = new Map<number, number[]>();
  const subjectFamily = new Array<number>(n).fill(0);
  for (let s = 0; s < n; s++) {
    const root = find(s);
    if (!rootIx.has(root)) {
      rootIx.set(root, famNames.length);
      famNames.push('');
      membersOf.set(root, []);
    }
    subjectFamily[s] = rootIx.get(root)!;
    membersOf.get(root)!.push(s);
  }
  for (const [root, fi] of rootIx) famNames[fi] = membersOf.get(root)!.map((s) => world.subjects[s]).join(' / ');
  world.families = famNames;
  world.subjectFamily = subjectFamily;
  for (const c of world.cards) c.family = c.subject >= 0 ? subjectFamily[c.subject] : -1;
  if (groups.length) {
    const byFamily = new Map<number, Set<number>>();
    for (let s = 0; s < n; s++) {
      if (!byFamily.has(subjectFamily[s])) byFamily.set(subjectFamily[s], new Set());
      byFamily.get(subjectFamily[s])!.add(s);
    }
    for (const r of rules) {
      if (r.kind === R.X_SUBJECT_GROUP || !r.subjects.size) continue;
      const wide = new Set<number>();
      for (const s of r.subjects) for (const x of byFamily.get(subjectFamily[s]) ?? new Set([s])) wide.add(x);
      r.subjects = wide;
    }
  }
  return world;
}

export function noonOf(P: number): number {
  return P >= 6 ? 4 : Math.floor((P + 1) / 2);
}

export function windowBreaks(rule: Rule, p: number, dur: number, P: number): boolean {
  const noon = noonOf(P);
  switch (rule.kind) {
    case R.X_MORNING_ONLY: return p + dur > noon;
    case R.X_AFTERNOON_ONLY: return p < noon;
    case R.X_NOT_LAST_PERIOD: return p + dur > P - 1;
    case R.X_NOT_FIRST_PERIOD: return p === 0;
    case R.X_TIME_WINDOW: return p < rule.param || (p + dur - 1) > rule.param2;
    default: return false;
  }
}

export function windowOk(world: World, windows: Rule[], card: Card, p: number, dur: number): boolean {
  for (const r of windows) if (r.appliesCard(card) && windowBreaks(r, p, dur, world.P)) return false;
  return true;
}

/** Her karta aday hücre listesini yazar. Kilit kapalı saati AÇMAZ. */
export function attachSlots(world: World, rules: Rule[]): World {
  const windows = rules.filter((r) => R.WINDOW_RULES.has(r.kind) && r.isHard());
  const { D, P } = world;
  for (const card of world.cards) {
    const block = new Uint8Array(D * P);
    for (const ci of card.classes) { const m = world.classClosed[ci]; for (let i = 0; i < block.length; i++) if (m[i]) block[i] = 1; }
    if (card.teacher >= 0) { const m = world.teacherClosed[card.teacher]; for (let i = 0; i < block.length; i++) if (m[i]) block[i] = 1; }
    const allowed: number[] = [];
    for (let d = 0; d < D; d++) {
      for (let p = 0; p < P - card.duration + 1; p++) {
        const idx = d * P + p;
        if (card.lockedAt !== null && idx !== card.lockedAt) continue;
        let hit = false;
        for (let k = 0; k < card.duration; k++) if (block[idx + k]) { hit = true; break; }
        if (hit) continue;
        if (windowOk(world, windows, card, p, card.duration)) allowed.push(idx);
      }
    }
    card.slots = allowed;
  }
  return world;
}
