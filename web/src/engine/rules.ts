// scheduler/rules.py — Planlama İlişkileri ekranı ile motor arasındaki sözleşme.
import type { Card, World } from './model.ts';
import { normClass, normKey } from './norm.ts';
import { toInt, truthy } from './py.ts';

export const X = 'X', Y = 'Y';
export const HARD = 3, HIGH = 2, NORMAL = 1, LOW = 0;
export const PENALTY: Record<number, number> = { [HIGH]: 10_000, [NORMAL]: 1_000, [LOW]: 100 };

const ONEM_MAP: [string, number][] = [
  ['sikikesinlikleuygulanmali', HARD],
  ['siki', HARD],
  ['yuksek', HIGH],
  ['normal', NORMAL],
  ['dusukmumkunse', LOW],
  ['dusuk', LOW],
];

export const X_SUBJECT_ONCE_DAY = 'X_SUBJECT_ONCE_DAY';
export const X_TEACHER_ONCE_DAY = 'X_TEACHER_ONCE_DAY';
export const X_SUBJECT_MAX_HOURS = 'X_SUBJECT_MAX_HOURS';
export const X_SUBJECT_MAX_SESSIONS = 'X_SUBJECT_MAX_SESSIONS';
export const X_PRACTICAL_MAX_HOURS = 'X_PRACTICAL_MAX_HOURS';
export const X_PAIR_NOT_SAME_DAY = 'X_PAIR_NOT_SAME_DAY';
export const X_CLASS_MAX_HOURS = 'X_CLASS_MAX_HOURS';
export const X_TEACHER_MAX_HOURS = 'X_TEACHER_MAX_HOURS';
export const X_TEACHER_MAX_DAYS = 'X_TEACHER_MAX_DAYS';
export const X_MIN_DAYS_BETWEEN = 'X_MIN_DAYS_BETWEEN';
export const X_SUBJECT_NOT_ADJACENT = 'X_SUBJECT_NOT_ADJACENT';
export const X_EVEN_SPREAD = 'X_EVEN_SPREAD';
export const X_SAME_DAY_ADJACENT = 'X_SAME_DAY_ADJACENT';
export const X_HARD_NOT_ADJACENT = 'X_HARD_NOT_ADJACENT';
export const X_NO_CLASS_GAP = 'X_NO_CLASS_GAP';
export const X_NO_TEACHER_GAP = 'X_NO_TEACHER_GAP';
export const X_TEACHER_MAX_RUN = 'X_TEACHER_MAX_RUN';
export const X_TIME_WINDOW = 'X_TIME_WINDOW';
export const X_MORNING_ONLY = 'X_MORNING_ONLY';
export const X_AFTERNOON_ONLY = 'X_AFTERNOON_ONLY';
export const X_NOT_LAST_PERIOD = 'X_NOT_LAST_PERIOD';
export const X_NOT_FIRST_PERIOD = 'X_NOT_FIRST_PERIOD';
export const X_SUBJECT_GROUP = 'X_SUBJECT_GROUP';
export const Y_TEACHER_CLASH = 'Y_TEACHER_CLASH';
export const Y_CLASS_CLASH = 'Y_CLASS_CLASH';
export const Y_CLOSED_CELL = 'Y_CLOSED_CELL';
export const Y_CROSS_INSTITUTION = 'Y_CROSS_INSTITUTION';
export const Y_SUBJECT_MAX_PARALLEL = 'Y_SUBJECT_MAX_PARALLEL';
export const Y_TEACHER_MAX_PARALLEL = 'Y_TEACHER_MAX_PARALLEL';

export const WINDOW_RULES = new Set([X_TIME_WINDOW, X_MORNING_ONLY, X_AFTERNOON_ONLY, X_NOT_LAST_PERIOD, X_NOT_FIRST_PERIOD]);
export const DEFINITION_RULES = new Set([X_SUBJECT_GROUP]);
export const SELECTION_GROUP_KINDS = new Set([X_SUBJECT_ONCE_DAY, X_SUBJECT_NOT_ADJACENT]);
const GROUPED_KINDS = new Set([X_PAIR_NOT_SAME_DAY, X_SUBJECT_ONCE_DAY, X_SUBJECT_NOT_ADJACENT, X_SUBJECT_GROUP]);

export class Rule {
  kind: string;
  axis: string;
  hardness: number;
  param = 0;
  param2 = 0;
  subjects: Set<number>;
  teachers: Set<number>;
  klasses: Set<number>;
  label: string;

  constructor(o: {
    kind: string; axis: string; hardness?: number; param?: number;
    subjects?: Set<number>; teachers?: Set<number>; klasses?: Set<number>; label?: string;
  }) {
    this.kind = o.kind;
    this.axis = o.axis;
    this.hardness = o.hardness ?? HARD;
    this.param = o.param ?? 0;
    this.subjects = o.subjects ?? new Set();
    this.teachers = o.teachers ?? new Set();
    this.klasses = o.klasses ?? new Set();
    this.label = o.label ?? '';
  }

  isHard(): boolean {
    return this.hardness >= HARD;
  }

  penalty(): number {
    return PENALTY[this.hardness] ?? 0;
  }

  appliesClass(c: number): boolean {
    return this.klasses.size === 0 || this.klasses.has(c);
  }

  appliesSubject(s: number): boolean {
    return this.subjects.size === 0 || this.subjects.has(s);
  }

  appliesTeacher(t: number): boolean {
    return this.teachers.size === 0 || this.teachers.has(t);
  }

  appliesCard(card: Card): boolean {
    if (this.klasses.size && !card.classes.some((c) => this.klasses.has(c))) return false;
    if (this.subjects.size && !this.subjects.has(card.subject)) return false;
    if (this.teachers.size && !this.teachers.has(card.teacher)) return false;
    return true;
  }
}

const UI_MAP: [string, string][] = [
  ['gundemaksimumderssayisi', X_SUBJECT_MAX_HOURS],
  ['bedenegitimiuygulamalidersleragundeenfazla2saatolsun', X_PRACTICAL_MAX_HOURS],
  ['uygulamalidersler', X_PRACTICAL_MAX_HOURS],
  ['aynidersayniguntekraretmesin', X_SUBJECT_ONCE_DAY],
  ['derslerhaftaningunlerineesitdagitilsin', X_EVEN_SPREAD],
  ['secilendersleraynigunpespesegelsin', X_SAME_DAY_ADJACENT],
  ['ikidersaynigunegelmesin', X_PAIR_NOT_SAME_DAY],
  ['ogretmenindersleriogledenoncetoplansin', X_MORNING_ONLY],
  ['ogretmenindersleriogledensonratoplansin', X_AFTERNOON_ONLY],
  ['sonderssaatinezorderskonulmasin', X_NOT_LAST_PERIOD],
  ['xdersibelirlisaatlerdekalmali', X_TIME_WINDOW],
  ['ikizordersartardagelmesin', X_HARD_NOT_ADJACENT],
  ['aynidersartardagelmesin', X_SUBJECT_NOT_ADJACENT],
  ['aynidersartardatekraretmesin', X_SUBJECT_NOT_ADJACENT],
  ['secilenderslerayniderssayilsin', X_SUBJECT_GROUP],
  ['ayniderssayilsin', X_SUBJECT_GROUP],
  ['dersgrubu', X_SUBJECT_GROUP],
  ['ayniogretmenayniguntekraretmesin', X_TEACHER_ONCE_DAY],
  ['ayniogretmenaynigunegelmesin', X_TEACHER_ONCE_DAY],
  ['dersgundeenfazlanseans', X_SUBJECT_MAX_SESSIONS],
  ['sinifgundeenfazlansaat', X_CLASS_MAX_HOURS],
  ['ogretmengundeenfazlansaat', X_TEACHER_MAX_HOURS],
  ['ogretmenhaftadaenfazlangun', X_TEACHER_MAX_DAYS],
  ['ayniderskartlariarasindaenaznguolsun', X_MIN_DAYS_BETWEEN],
  ['ayniderskartlariarasindaenazngun', X_MIN_DAYS_BETWEEN],
  ['siniftabossaatkalmasin', X_NO_CLASS_GAP],
  ['ogretmendebossaatkalmasin', X_NO_TEACHER_GAP],
  ['ogretmenartardaenfazlansaat', X_TEACHER_MAX_RUN],
  ['aynisaatteendersfazlansinifalabilir', Y_SUBJECT_MAX_PARALLEL],
  ['aynisaatteenfazlansinif', Y_SUBJECT_MAX_PARALLEL],
  ['ilkderssaatinekonulmasin', X_NOT_FIRST_PERIOD],
  ['pespesegelsin', X_SAME_DAY_ADJACENT],
  ['esitdagitilsin', X_EVEN_SPREAD],
  ['ogledenoncetoplansin', X_MORNING_ONLY],
  ['ogledensonratoplansin', X_AFTERNOON_ONLY],
  ['belirlisaatlerdekalmali', X_TIME_WINDOW],
  ['zorderartarda', X_HARD_NOT_ADJACENT],
  ['zordersartarda', X_HARD_NOT_ADJACENT],
];

const AXIS = new Map<string, string>(UI_MAP.map(([, k]) => [k, k.startsWith('Y_') ? Y : X]));

const PRACTICAL_KEYWORDS = ['beden', 'muzik', 'gorsel', 'resim', 'sanat', 'spor', 'uygulama', 'atolye', 'teknoloji', 'tasarim'];
const HARD_KEYWORDS = ['mat', 'fizik', 'kimya', 'biyo', 'geometri', 'fen', 'geo'];

export function isPractical(name: string): boolean {
  const n = normKey(name);
  return PRACTICAL_KEYWORDS.some((k) => n.includes(k));
}

export function isHardSubject(name: string): boolean {
  const n = normKey(name);
  return HARD_KEYWORDS.some((k) => n.includes(k));
}

function stripGroupNo(label: unknown): string {
  return String(label ?? '').replace(/\s*\(\d+\/\d+\)\s*$/, '');
}

export function matchRuleName(key: string): string | null {
  if (!key) return null;
  for (const [pat, k] of UI_MAP) if (pat === key) return k;
  let best: string | null = null, bestLen = 0;
  for (const [pat, k] of UI_MAP) {
    if ((key.includes(pat) || pat.includes(key)) && pat.length > bestLen) {
      best = k;
      bestLen = pat.length;
    }
  }
  return best;
}

function hardnessFrom(onem: unknown): number {
  const k = normKey(onem);
  for (const [key, val] of ONEM_MAP) if (k.startsWith(key) || k.includes(key)) return val;
  return HARD;
}

export function ruleGroups(raw: any): string[][] {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return [];
  const groups = raw.gruplar;
  let out: string[][] = [];
  if (Array.isArray(groups)) {
    for (const g of groups) {
      if (Array.isArray(g)) {
        const names = g.filter((x: unknown) => truthy(x) && String(x).trim()).map((x: unknown) => String(x));
        if (names.length) out.push(names);
      }
    }
  }
  if (!out.length) {
    const names = (truthy(raw.dersler) ? raw.dersler : []).filter((x: unknown) => truthy(x) && String(x).trim()).map((x: unknown) => String(x));
    out = names.length ? [names] : [];
  }
  return out;
}

function kindOf(raw: any, strip: boolean): string | null {
  if (truthy(raw.kind)) return raw.kind;
  const label = truthy(raw.kural) ? raw.kural : '';
  return matchRuleName(normKey(strip ? stripGroupNo(label) : label));
}

export function selectionIsGroup(raw: any, nSubjects: number | null = null): boolean {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return false;
  const kind = kindOf(raw, true);
  if (!kind || !SELECTION_GROUP_KINDS.has(kind)) return false;
  if (ruleGroups(raw).length > 1) return true;
  const keys = new Set<string>();
  for (const x of truthy(raw.dersler) ? raw.dersler : []) {
    const k = normKey(x);
    if (k) keys.add(k);
  }
  if (keys.size < 2) return false;
  const flag = raw.tek_ders;
  if (flag !== null && flag !== undefined) return truthy(flag);
  if (nSubjects === null) return keys.size <= 8;
  return keys.size * 2 < nSubjects;
}

export function expandGroups(rawRelations: any[]): any[] {
  const out: any[] = [];
  for (const raw of rawRelations || []) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
      out.push(raw);
      continue;
    }
    const kind = kindOf(raw, false);
    const groups = ruleGroups(raw);
    if (!kind || !GROUPED_KINDS.has(kind) || groups.length < 2) {
      out.push(raw);
      continue;
    }
    groups.forEach((g, i) => {
      const piece: any = { ...raw };
      delete piece.gruplar;
      piece.dersler = [...g];
      piece.kural = `${truthy(raw.kural) ? raw.kural : kind} (${i + 1}/${groups.length})`;
      piece._grup_no = i + 1;
      out.push(piece);
    });
  }
  return out;
}

export class RuleReport {
  warnings: string[] = [];
  compiled: [string, Rule][] = [];
  skipped: [string, string][] = [];
  errors: string[] = [];
  warn(msg: string) { this.warnings.push(msg); }
  skip(label: string, why: string) {
    this.skipped.push([label, why]);
    this.warnings.push(`UYGULANMADI — ${label}: ${why}`);
  }
  ok(label: string, rule: Rule) { this.compiled.push([label, rule]); }
}

type Lookup = { norm: (x: unknown) => string; map: Map<string, number> };

function resolve(names: unknown, lookup: Lookup, kind: string, label: string, report: RuleReport): Set<number> {
  const out = new Set<number>();
  for (const raw of (truthy(names) ? (names as unknown[]) : [])) {
    const k = lookup.norm(raw);
    let idx = lookup.map.get(k);
    if (idx === undefined) {
      const cands: number[] = [];
      for (const [mk, i] of lookup.map) if (k && (mk.includes(k) || k.includes(mk))) cands.push(i);
      if (cands.length === 1) idx = cands[0];
    }
    if (idx === undefined) {
      const msg = `${label}: '${raw}' adında ${kind} bulunamadı. Kuralın kapsamı çözülemedi.`;
      report.warn(msg);
      report.errors.push(msg);
    } else {
      out.add(idx);
    }
  }
  return out;
}

export function compileRules(rawRelations: any[], world: World, defaults = true): [Rule[], RuleReport] {
  const rep = new RuleReport();
  const rules: Rule[] = [];
  const mapOf = (names: string[], norm: (x: unknown) => string) => {
    const m = new Map<string, number>();
    names.forEach((n, i) => m.set(norm(n), i));
    return m;
  };
  const sub: Lookup = { norm: normKey, map: mapOf(world.subjects, normKey) };
  const tch: Lookup = { norm: normKey, map: mapOf(world.teachers, normKey) };
  const cls: Lookup = { norm: normClass, map: mapOf(world.classes, normClass) };

  for (const raw of expandGroups(rawRelations)) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) continue;
    const label = String(truthy(raw.kural) ? raw.kural : '?');
    if ('aktif' in raw && !truthy(raw.aktif)) continue;

    const k = normKey(stripGroupNo(label));
    let kind: string | null = truthy(raw.kind) ? raw.kind : matchRuleName(k);
    if (kind && !AXIS.has(kind)) kind = null;
    if (!kind) {
      rep.skip(label, 'bu kural adı motorda tanımlı değil');
      rep.errors.push(rep.warnings[rep.warnings.length - 1]);
      continue;
    }
    let subs = resolve(raw.dersler, sub, 'ders', label, rep);
    const tchs = resolve(raw.ogretmenler, tch, 'öğretmen', label, rep);
    const klss = resolve(raw.siniflar, cls, 'sınıf', label, rep);
    const hardness = hardnessFrom(raw.onem);
    const param = toInt(truthy(raw.parametre) ? raw.parametre : 0);
    if (param === null) {
      rep.errors.push(`${label}: geçersiz parametre`);
      continue;
    }
    const pStart = raw.period_start, pEnd = raw.period_end;
    const r = new Rule({ kind, axis: AXIS.get(kind) ?? X, hardness, param, subjects: subs, teachers: tchs, klasses: klss, label });

    if (kind === X_SUBJECT_GROUP) {
      if (subs.size < 2) {
        rep.skip(label, 'en az iki ders seçilmeli; tek dersle grup kurulamaz');
        continue;
      }
      r.hardness = HARD;
      r.teachers = new Set();
      r.klasses = new Set();
      rules.push(r);
      rep.ok(label, r);
      continue;
    }
    if (kind === X_PAIR_NOT_SAME_DAY && subs.size < 2) {
      rep.skip(label, 'en az iki ders seçilmeli; ders seçimi boş olduğu için kural hiçbir şeyi kısıtlamıyor');
      continue;
    }
    if (kind === X_PAIR_NOT_SAME_DAY && r.teachers.size) {
      r.teachers = new Set();
      rep.warn(`${label}: öğretmen filtresi yoksayıldı; kural seçili derslerin bütün kartlarına uygulanır.`);
    }
    if (kind === X_TIME_WINDOW) {
      if (!truthy(pStart) || !truthy(pEnd)) {
        rep.errors.push(`${label}: saat aralığı girilmemiş`);
        continue;
      }
      r.param = (toInt(pStart) ?? 0) - 1;
      r.param2 = (toInt(pEnd) ?? 0) - 1;
      if (r.param > r.param2) {
        rep.errors.push(`${label}: geçersiz aralık (${pStart}-${pEnd})`);
        continue;
      }
    }
    if ([X_SUBJECT_MAX_HOURS, X_PRACTICAL_MAX_HOURS, X_CLASS_MAX_HOURS, X_TEACHER_MAX_HOURS,
      X_TEACHER_MAX_RUN, X_SUBJECT_MAX_SESSIONS].includes(kind)) {
      if (r.param <= 0) {
        r.param = 2;
        rep.warn(`${label}: parametre girilmemiş, 2 kabul edildi.`);
      }
    }
    if (kind === X_PRACTICAL_MAX_HOURS && !subs.size) {
      subs = new Set(world.subjects.map((n, i) => [n, i] as const).filter(([n]) => isPractical(n)).map(([, i]) => i));
      r.subjects = subs;
      if (!subs.size) {
        rep.skip(label, 'uygulamalı ders bulunamadı');
        continue;
      }
    }
    if (kind === X_HARD_NOT_ADJACENT && !subs.size) {
      subs = new Set(world.subjects.map((n, i) => [n, i] as const).filter(([n]) => isHardSubject(n)).map(([, i]) => i));
      r.subjects = subs;
      if (!subs.size) {
        rep.skip(label, 'zor ders bulunamadı');
        continue;
      }
    }
    if (kind === X_NOT_LAST_PERIOD && !subs.size) {
      subs = new Set(world.subjects.map((n, i) => [n, i] as const).filter(([n]) => isHardSubject(n)).map(([, i]) => i));
      r.subjects = subs;
    }
    rules.push(r);
    rep.ok(label, r);
    if (SELECTION_GROUP_KINDS.has(kind) && selectionIsGroup(raw, world.subjects.length)) {
      const g = new Rule({ kind: X_SUBJECT_GROUP, axis: X, hardness: HARD, subjects: subs,
        label: `[${label}] seçilen dersler tek ders sayıldı` });
      rules.push(g);
      rep.ok(g.label, g);
    }
  }
  if (defaults) {
    for (const k of [Y_TEACHER_CLASH, Y_CLASS_CLASH, Y_CLOSED_CELL, Y_CROSS_INSTITUTION]) {
      rules.push(new Rule({ kind: k, axis: Y, hardness: HARD, label: `[çekirdek] ${k}` }));
    }
  }
  return [rules, rep];
}

// ── Ders aileleri ve kural kapsamları (elle yerleştirme geri bildirimi) ──────
// scheduler/rules.py: subject_groups, family_lookup, same_subject,
// subject_rule_scopes, subject_count. Motorla aynı sözlük.

export function subjectGroups(rawRelations: any[], nSubjects: number | null = null): Set<string>[] {
  let groups: Set<string>[] = [];
  for (const raw of expandGroups(rawRelations)) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) continue;
    if ('aktif' in raw && !truthy(raw.aktif)) continue;
    const kind = kindOf(raw, true);
    if (kind !== X_SUBJECT_GROUP && !selectionIsGroup(raw, nSubjects)) continue;
    const keys = new Set<string>();
    for (const x of truthy(raw.dersler) ? raw.dersler : []) { const k = normKey(x); if (k) keys.add(k); }
    if (keys.size < 2) continue;
    const merged = new Set(keys);
    const rest: Set<string>[] = [];
    for (const g of groups) {
      if ([...g].some((k) => merged.has(k))) for (const k of g) merged.add(k);
      else rest.push(g);
    }
    rest.push(merged);
    groups = rest;
  }
  return groups;
}

export function familyLookup(rawRelations: any[], nSubjects: number | null = null): Map<string, string> {
  const out = new Map<string, string>();
  for (const g of subjectGroups(rawRelations, nSubjects)) {
    const head = [...g].sort()[0];
    for (const k of g) out.set(k, head);
  }
  return out;
}

export function sameSubject(a: unknown, b: unknown, lookup: Map<string, string> = new Map()): boolean {
  const ka = normKey(a), kb = normKey(b);
  if (!ka || !kb) return false;
  if (ka === kb) return true;
  return (lookup.get(ka) ?? ka) === (lookup.get(kb) ?? kb);
}

export interface RuleScope { label: string; subjects: string[]; teachers: Set<string>; classes: Set<string> }

export function subjectRuleScopes(rawRelations: any[], kinds: Set<string> | null = null): Map<string, RuleScope[]> {
  const out = new Map<string, RuleScope[]>();
  for (const raw of expandGroups(rawRelations)) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) continue;
    if ('aktif' in raw && !truthy(raw.aktif)) continue;
    const kind = kindOf(raw, true);
    if (!kind || DEFINITION_RULES.has(kind)) continue;
    if (kinds && !kinds.has(kind)) continue;
    if (hardnessFrom(raw.onem) < HARD) continue;
    if (!out.has(kind)) out.set(kind, []);
    out.get(kind)!.push({
      label: String(truthy(raw.kural) ? raw.kural : kind),
      subjects: (truthy(raw.dersler) ? raw.dersler : []).filter((x: unknown) => truthy(x)),
      teachers: new Set((truthy(raw.ogretmenler) ? raw.ogretmenler : []).filter((x: unknown) => truthy(x)).map((x: unknown) => normKey(x))),
      classes: new Set((truthy(raw.siniflar) ? raw.siniflar : []).filter((x: unknown) => truthy(x)).map((x: unknown) => normClass(x))),
    });
  }
  return out;
}

export function subjectCount(data: any): number {
  const keys = new Set<string>();
  for (const d of (data?.dersler ?? [])) { const k = normKey(d?.ad || d?.name || ''); if (k) keys.add(k); }
  for (const a of (data?.atamalar ?? [])) { const k = normKey(a?.subject || a?.ders || ''); if (k) keys.add(k); }
  return keys.size;
}
