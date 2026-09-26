// placement_engine.py — "bu ders buraya konabilir mi?" sorusunun TEK cevabı.
// Sürükleme sırasında her hedef hücrenin yeşil / mavi / kırmızı / gri yanması.
// Renk bir sonuçtur: önce yerleşim SEMANTİK olarak sınıflandırılır.
import { CLOSED, AVOID, getMatrix, gridDimensions } from '../engine/data.ts';
import { normClass, normKey } from '../engine/norm.ts';
import { truthy } from '../engine/py.ts';
import {
  X_PAIR_NOT_SAME_DAY, X_SUBJECT_NOT_ADJACENT, X_SUBJECT_ONCE_DAY,
  familyLookup, sameSubject, subjectCount, subjectRuleScopes,
} from '../engine/rules.ts';
import type { RuleScope } from '../engine/rules.ts';

export const VALID = 'VALID', QUESTIONABLE = 'QUESTIONABLE', CONFLICT = 'CONFLICT', FORBIDDEN = 'FORBIDDEN',
  CURRENT = 'CURRENT', OUT_OF_RANGE = 'OUT_OF_RANGE', INVALID_GEOMETRY = 'INVALID_GEOMETRY', ANALYSIS_ERROR = 'ANALYSIS_ERROR';
export const SEV_NONE = 0, SEV_INFO = 1, SEV_PREFERENCE = 2, SEV_SOFT = 3, SEV_HARD = 4;
export type Visual = 'GREEN' | 'BLUE' | 'RED' | 'GREY' | 'SELECTED' | 'NONE';
const VISUAL: Record<string, Visual> = {
  VALID: 'GREEN', QUESTIONABLE: 'BLUE', CONFLICT: 'RED', FORBIDDEN: 'GREY', CURRENT: 'SELECTED',
  OUT_OF_RANGE: 'NONE', INVALID_GEOMETRY: 'GREY', ANALYSIS_ERROR: 'GREY',
};

export const TEACHER_COLLISION = 'TEACHER_COLLISION', CLASS_COLLISION = 'CLASS_COLLISION', GROUP_COLLISION = 'GROUP_COLLISION',
  ROOM_COLLISION = 'ROOM_COLLISION', TEACHER_UNAVAILABLE = 'TEACHER_UNAVAILABLE', CLASS_UNAVAILABLE = 'CLASS_UNAVAILABLE',
  ROOM_UNAVAILABLE = 'ROOM_UNAVAILABLE', SUBJECT_UNAVAILABLE = 'SUBJECT_UNAVAILABLE', TEACHER_AVOID = 'TEACHER_AVOID',
  CLASS_AVOID = 'CLASS_AVOID', LOCKED_TARGET = 'LOCKED_TARGET', LOCKED_SOURCE = 'LOCKED_SOURCE',
  SAME_SUBJECT_SAME_DAY = 'SAME_SUBJECT_SAME_DAY', SUBJECT_WINDOW = 'SUBJECT_WINDOW', CONSECUTIVE_RULE = 'CONSECUTIVE_RULE',
  PAIR_NOT_SAME_DAY = 'PAIR_NOT_SAME_DAY', GEOMETRY = 'GEOMETRY', DATA_ERROR = 'DATA_ERROR';

const norm = (v: unknown) => String(v ?? '').split(/\s+/).filter(Boolean).join(' ').trim();
const UP_TR: Record<string, string> = { 'i': 'İ', 'ı': 'I', 'ç': 'Ç', 'ğ': 'Ğ', 'ö': 'Ö', 'ş': 'Ş', 'ü': 'Ü' };
export const upper = (v: unknown) => norm(v).replace(/[iıçğöşü]/g, (c) => UP_TR[c]).toUpperCase();

/** Sınıf eşleşme anahtarı — matches_class + parantez kırpma. */
export function classKey(v: unknown): string {
  const t = String(v ?? '').trim().toUpperCase().replace(/ /g, '').replace(/-/g, '/').replace(/\\/g, '/');
  const base = t.split('(')[0].trim();
  return base || t;
}

const TK: Record<string, string> = { 'İ': 'i', 'I': 'ı', 'ı': 'i', 'Ş': 's', 'ş': 's', 'Ğ': 'g', 'ğ': 'g', 'Ü': 'u', 'ü': 'u', 'Ö': 'o', 'ö': 'o', 'Ç': 'c', 'ç': 'c' };
/** Öğretmen eşleşme anahtarı — normalize_clean. */
export function teacherKey(v: unknown): string {
  return String(v ?? '').replace(/[İIıŞşĞğÜüÖöÇç]/g, (c) => TK[c]).toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');
}

function splitMulti(v: unknown): string[] {
  let t = norm(v);
  if (!t) return [];
  for (const sep of [',', '&', '/']) t = t.split(sep).join('+');
  return t.split('+').map((p) => p.trim()).filter(Boolean);
}

export function lessonTeachers(l: any): string[] {
  const names = splitMulti(l.teacher_name || l.teacher || l.ogretmen || '');
  const extra = l.teachers || l.ogretmenler;
  if (Array.isArray(extra)) {
    for (const t of extra) {
      const n = norm(t && typeof t === 'object' ? (t.ad || t.name) : t);
      if (n && !names.includes(n)) names.push(n);
    }
  }
  return names;
}

export function lessonClasses(l: any): string[] {
  const comb = l.combined_classes;
  if (Array.isArray(comb) && comb.length) {
    const names = comb.map(norm).filter(Boolean);
    if (names.length) return names;
  }
  return splitMulti(l.class_name || l.class || l.sinif || '');
}

function lessonGroups(l: any): string[] {
  const raw = l.groups || l.gruplar || l.grup || l.group;
  if (Array.isArray(raw)) return raw.map(norm).filter(Boolean);
  return splitMulti(raw);
}

function groupsIntersect(a: string[], b: string[]): boolean {
  if (!a.length || !b.length) return true;
  const sa = new Set(a.map(upper));
  return b.map(upper).some((x) => sa.has(x));
}

export interface Conflict { type: string; kind: string; name: string; periods: number[]; severity: number; message: string; rule: string }
const conflict = (type: string, kind: string, name: string, periods: number[], severity: number, message: string, rule = ''): Conflict =>
  ({ type, kind, name, periods, severity, message, rule });

export class Candidate {
  lesson: any; day: number; start: number; duration: number; periods: number[];
  subject: string; teachers: string[]; classes: string[]; room: string; groups: string[];
  blockId: string; sourceDay: number | null; sourcePeriod: number | null;
  constructor(lesson: any, day: number, start: number, duration?: number) {
    this.lesson = lesson || {};
    this.day = day;
    this.start = start;
    this.duration = Math.max(1, duration ?? (Number(this.lesson.duration) || 1));
    this.periods = Array.from({ length: this.duration }, (_, k) => start + k);
    this.subject = norm(this.lesson.subject_name || this.lesson.subject);
    this.teachers = lessonTeachers(this.lesson);
    this.classes = lessonClasses(this.lesson);
    this.room = norm(this.lesson.room_name || this.lesson.room || this.lesson.derslik);
    this.groups = lessonGroups(this.lesson);
    this.blockId = norm(this.lesson.block_id);
    const src = this.lesson.source || {};
    this.sourceDay = src.day ?? this.lesson.origin_day ?? null;
    this.sourcePeriod = src.period ?? this.lesson.origin_period ?? null;
  }
}

export interface Result { status: string; severity: number; score: number; conflicts: Conflict[]; explanation: string; candidate: Candidate | null }
export const visualOf = (r: Result): Visual => VISUAL[r.status] ?? 'NONE';
export const hardViolations = (r: Result) => r.conflicts.filter((c) => c.severity >= SEV_HARD);
export const ruleViolations = (r: Result) => r.conflicts.filter((c) =>
  [SAME_SUBJECT_SAME_DAY, CONSECUTIVE_RULE, PAIR_NOT_SAME_DAY].includes(c.type) && c.severity >= SEV_SOFT && c.rule);
export const outsideClassHours = (r: Result) => r.conflicts.some((c) =>
  c.type === CLASS_UNAVAILABLE && c.severity >= SEV_HARD && r.candidate !== null && c.periods.includes(r.candidate.start));

interface Entry { subject: string; classes: string[]; teachers: string[]; groups: string[]; room: string; locked: boolean; blockId: string; day: number; period: number; duration: number; raw: any }

function sameBlock(p: any, c: Candidate): boolean {
  const bid = norm(p.block_id);
  if (c.blockId && bid) return bid === c.blockId;
  if (c.sourceDay === null || c.sourcePeriod === null) return false;
  const pd = Number(p.day ?? p.col ?? 0), pp = Number(p.period ?? p.row ?? 0), pdur = Math.max(1, Number(p.duration) || 1);
  if (pd !== Number(c.sourceDay) || !(pp <= Number(c.sourcePeriod) && Number(c.sourcePeriod) < pp + pdur)) return false;
  const ps = norm(p.subject_name || p.subject);
  if (c.subject && ps && ps !== c.subject) return false;
  const pc = new Set(lessonClasses(p).map(classKey));
  const cc = c.classes.map(classKey);
  if (pc.size && cc.length && !cc.some((x) => pc.has(x))) return false;
  return true;
}

export class Snapshot {
  data: any; D: number; P: number; days: string[];
  classClosed = new Map<string, Set<string>>(); classAvoid = new Map<string, Set<string>>();
  teacherClosed = new Map<string, Set<string>>(); teacherAvoid = new Map<string, Set<string>>();
  roomClosed = new Map<string, Set<string>>(); roomAvoid = new Map<string, Set<string>>();
  subjectClosed = new Map<string, Set<string>>(); subjectAvoid = new Map<string, Set<string>>();
  byClass = new Map<string, Entry[]>(); byTeacher = new Map<string, Entry[]>(); byRoom = new Map<string, Entry[]>();
  placements: Entry[] = [];
  prefWindows = new Map<string, string>(); prefMaxDaily = 4;
  family: Map<string, string>; ruleOnceDay: RuleScope[]; ruleNotAdjacent: RuleScope[]; rulePair: RuleScope[];

  constructor(data: any, excludeBlockId = '') {
    this.data = data || {};
    [this.D, this.P] = gridDimensions(this.data);
    this.days = (this.data.settings?.days ?? []).slice(0, this.D);
    this.states(this.data.siniflar, classKey, this.classClosed, this.classAvoid);
    this.states(this.data.ogretmenler, teacherKey, this.teacherClosed, this.teacherAvoid);
    this.states(this.data.derslikler, upper, this.roomClosed, this.roomAvoid);
    this.states(this.data.dersler, upper, this.subjectClosed, this.subjectAvoid);
    const ex = norm(excludeBlockId);
    for (const p of this.data.grid_placements ?? []) {
      if (!p || typeof p !== 'object') continue;
      const bid = norm(p.block_id);
      if (ex && bid === ex) continue;
      const day = Number(p.day ?? p.col ?? 0), period = Number(p.period ?? p.row ?? 0), dur = Math.max(1, Number(p.duration) || 1);
      if (!Number.isFinite(day) || !Number.isFinite(period)) continue;
      const e: Entry = { subject: norm(p.subject_name || p.subject), classes: lessonClasses(p), teachers: lessonTeachers(p),
        groups: lessonGroups(p), room: norm(p.room_name || p.room || p.derslik), locked: !!(p.locked || p.is_locked),
        blockId: bid, day, period, duration: dur, raw: p };
      this.placements.push(e);
      for (let off = 0; off < dur; off++) {
        const slot = `${day},${period + off}`;
        for (const cn of e.classes) this.push(this.byClass, `${classKey(cn)}|${slot}`, e);
        for (const tn of e.teachers) this.push(this.byTeacher, `${teacherKey(tn)}|${slot}`, e);
        if (e.room) this.push(this.byRoom, `${upper(e.room)}|${slot}`, e);
      }
    }
    const c = this.data.constraints || {};
    for (const [k, v] of Object.entries(c.subject_windows || {})) this.prefWindows.set(upper(k), String(v));
    this.prefMaxDaily = Number(c.max_daily_same_subject || 4) || 4;
    const rels = this.data.planlama_iliskileri ?? [];
    this.family = familyLookup(rels, subjectCount(this.data));
    const scopes = subjectRuleScopes(rels);
    this.ruleOnceDay = scopes.get(X_SUBJECT_ONCE_DAY) ?? [];
    this.ruleNotAdjacent = scopes.get(X_SUBJECT_NOT_ADJACENT) ?? [];
    this.rulePair = (scopes.get(X_PAIR_NOT_SAME_DAY) ?? []).filter((sc) => sc.subjects.length >= 2);
  }

  private push(m: Map<string, Entry[]>, k: string, e: Entry) {
    const l = m.get(k);
    if (l) l.push(e); else m.set(k, [e]);
  }

  private states(list: any[], kf: (s: string) => string, closed: Map<string, Set<string>>, avoid: Map<string, Set<string>>) {
    for (const ent of list ?? []) {
      if (!ent || typeof ent !== 'object') continue;
      const name = norm(ent.ad || ent.name);
      if (!name) continue;
      const m = getMatrix(ent, name, this.data);
      const cs = new Set<string>(), as = new Set<string>();
      for (let d = 0; d < Math.min(this.D, m.length); d++) {
        for (let p = 0; p < Math.min(this.P, m[d].length); p++) {
          if (m[d][p] === CLOSED) cs.add(`${d},${p}`);
          else if (m[d][p] === AVOID) as.add(`${d},${p}`);
        }
      }
      closed.set(kf(name), cs);
      avoid.set(kf(name), as);
    }
  }

  sameSubject(a: string, b: string) { return sameSubject(a, b, this.family); }

  ruleScopeMatches(sc: RuleScope, teachers: string[], className: string) {
    if (sc.teachers.size && !teachers.some((t) => sc.teachers.has(normKey(t)))) return false;
    if (sc.classes.size && !sc.classes.has(normClass(className))) return false;
    return true;
  }

  ruleApplies(scopes: RuleScope[], subject: string, teachers: string[], className: string): string {
    for (const sc of scopes) {
      if (sc.subjects.length && !sc.subjects.some((x) => this.sameSubject(subject, x))) continue;
      if (!this.ruleScopeMatches(sc, teachers, className)) continue;
      return sc.label;
    }
    return '';
  }

  classLessonsOnDay(className: string, day: number): Entry[] {
    const k = classKey(className);
    return this.placements.filter((e) => e.day === day && e.classes.some((c) => classKey(c) === k));
  }

  slotLabel(day: number, period: number) {
    return `${day < this.days.length ? this.days[day] : `${day + 1}. gün`} ${period + 1}. saat`;
  }
}

function finish(status: string, conflicts: Conflict[], candidate: Candidate | null): Result {
  const severity = Math.max(SEV_NONE, ...conflicts.map((c) => c.severity));
  let score = 0;
  for (const c of conflicts) score -= ({ [SEV_HARD]: 1000, [SEV_SOFT]: 25, [SEV_PREFERENCE]: 8 } as Record<number, number>)[c.severity] ?? 0;
  const hard = conflicts.filter((c) => c.severity >= SEV_HARD);
  const soft = conflicts.filter((c) => c.severity > SEV_NONE && c.severity < SEV_HARD);
  let explanation = '';
  if (hard.length) explanation = hard[0].message + (hard.length > 1 ? `  (+${hard.length - 1} sorun daha)` : '');
  else if (soft.length) explanation = soft[0].message;
  else if (status === CURRENT) explanation = 'Dersin şu anki yeri.';
  else if (status === VALID) explanation = 'Buraya konabilir.';
  return { status, severity, score, conflicts, explanation, candidate };
}

export function analyze(s: Snapshot, lesson: any, c: Candidate | null): Result {
  if (!c) return { status: OUT_OF_RANGE, severity: SEV_NONE, score: -1e9, conflicts: [], explanation: 'Izgara dışı.', candidate: null };
  const conflicts: Conflict[] = [];
  try {
    if (lesson && (lesson.locked || lesson.is_locked)) {
      conflicts.push(conflict(LOCKED_SOURCE, 'ders', c.subject, c.periods, SEV_HARD, 'Bu ders kilitli; taşınamaz.'));
      return finish(FORBIDDEN, conflicts, c);
    }
    if (c.day < 0 || c.day >= s.D || c.start < 0 || c.start >= s.P) return finish(OUT_OF_RANGE, conflicts, c);
    if (c.start + c.duration > s.P) {
      conflicts.push(conflict(GEOMETRY, 'gün', s.slotLabel(c.day, c.start), c.periods, SEV_HARD,
        `${c.duration} saatlik ders buraya sığmıyor: gün ${s.P}. saatte bitiyor.`));
      return finish(INVALID_GEOMETRY, conflicts, c);
    }
    if (!c.classes.length) {
      conflicts.push(conflict(DATA_ERROR, 'ders', c.subject, c.periods, SEV_HARD, 'Dersin sınıfı belli değil.'));
      return finish(ANALYSIS_ERROR, conflicts, c);
    }
    // KAPALI (gri) — sınıf/öğretmen/derslik/ders o saatte YOK
    let blocked = false;
    const checks: [string[], Map<string, Set<string>>, Map<string, Set<string>>, string, string, string, (x: string) => string][] = [
      [c.classes, s.classClosed, s.classAvoid, 'sınıf', CLASS_UNAVAILABLE, CLASS_AVOID, classKey],
      [c.teachers, s.teacherClosed, s.teacherAvoid, 'öğretmen', TEACHER_UNAVAILABLE, TEACHER_AVOID, teacherKey],
      [c.room ? [c.room] : [], s.roomClosed, s.roomAvoid, 'derslik', ROOM_UNAVAILABLE, ROOM_UNAVAILABLE, upper],
      [c.subject ? [c.subject] : [], s.subjectClosed, s.subjectAvoid, 'ders', SUBJECT_UNAVAILABLE, SUBJECT_UNAVAILABLE, upper],
    ];
    for (const [names, closedMap, avoidMap, kind, hardType, softType, kf] of checks) {
      for (const name of names) {
        const closed = closedMap.get(kf(name)) ?? new Set(), avoid = avoidMap.get(kf(name)) ?? new Set();
        const hits = c.periods.filter((p) => closed.has(`${c.day},${p}`));
        if (hits.length) {
          blocked = true;
          const msg = c.duration > 1 && hits[0] !== c.start
            ? `${c.duration} saatlik ders ${c.start + 1}. saatten başlayınca ${hits[0] + 1}. saate taşıyor; ${name} o saatte kapalı.`
            : `${name}: ${s.slotLabel(c.day, hits[0])} kapalı işaretli.`;
          conflicts.push(conflict(hardType, kind, name, hits, SEV_HARD, msg));
        }
        const soft = c.periods.filter((p) => avoid.has(`${c.day},${p}`));
        if (soft.length) conflicts.push(conflict(softType, kind, name, soft, SEV_SOFT, `${name} bu saatte 'tercih edilmez' işaretli.`));
      }
    }
    // MEŞGUL (kırmızı)
    let occupied = false;
    for (const cn of c.classes) {
      for (const p of c.periods) {
        for (const o of s.byClass.get(`${classKey(cn)}|${c.day},${p}`) ?? []) {
          if (sameBlock(o.raw, c)) continue;
          if (!groupsIntersect(c.groups, o.groups)) {
            conflicts.push(conflict(GROUP_COLLISION, 'grup', cn, [p], SEV_INFO, `${cn} aynı saatte ${o.subject} dersini görüyor ama farklı grup — çakışma sayılmadı.`));
            continue;
          }
          occupied = true;
          conflicts.push(conflict(CLASS_COLLISION, 'sınıf', cn, [p], SEV_HARD, `${cn} sınıfında ${s.slotLabel(c.day, p)}: ${o.subject} (${o.teachers.join(', ')}) var.`));
          if (o.locked) conflicts.push(conflict(LOCKED_TARGET, 'ders', o.subject, [p], SEV_HARD, `${o.subject} dersi kilitli, yerinden oynatılamaz.`));
        }
      }
    }
    const candClassKeys = new Set(c.classes.map(classKey));
    for (const tn of c.teachers) {
      for (const p of c.periods) {
        for (const o of s.byTeacher.get(`${teacherKey(tn)}|${c.day},${p}`) ?? []) {
          if (sameBlock(o.raw, c)) continue;
          if (o.classes.some((x) => candClassKeys.has(classKey(x)))) continue;
          occupied = true;
          conflicts.push(conflict(TEACHER_COLLISION, 'öğretmen', tn, [p], SEV_HARD, `${tn} bu saatte ${o.classes.join(', ')} sınıfında ${o.subject} dersinde.`));
        }
      }
    }
    if (c.room) {
      for (const p of c.periods) {
        for (const o of s.byRoom.get(`${upper(c.room)}|${c.day},${p}`) ?? []) {
          if (sameBlock(o.raw, c)) continue;
          occupied = true;
          conflicts.push(conflict(ROOM_COLLISION, 'derslik', c.room, [p], SEV_HARD, `${c.room} dersliği bu saatte ${o.classes.join(', ')} ${o.subject} ile dolu.`));
        }
      }
    }
    // İLİŞKİLER
    const teachers = lessonTeachers(c.lesson);
    for (const cn of c.classes) {
      const sameDay = s.classLessonsOnDay(cn, c.day).filter((e) => s.sameSubject(e.subject, c.subject) && !sameBlock(e.raw, c));
      if (sameDay.length) {
        const label = s.ruleApplies(s.ruleOnceDay, c.subject, teachers, cn);
        conflicts.push(conflict(SAME_SUBJECT_SAME_DAY, 'ders', c.subject, c.periods, label ? SEV_SOFT : SEV_PREFERENCE,
          label ? `${label}: ${cn} sınıfı ${c.subject} dersini bugün zaten görüyor (${sameDay[0].subject}).`
            : `${cn} sınıfı ${c.subject} dersini bugün zaten görüyor.`, label));
      }
      if (sameDay.length + 1 > s.prefMaxDaily) {
        conflicts.push(conflict(SAME_SUBJECT_SAME_DAY, 'ders', c.subject, c.periods, SEV_SOFT, `${c.subject} bir günde en fazla ${s.prefMaxDaily} saat olmalı.`));
      }
      const label = s.ruleApplies(s.ruleNotAdjacent, c.subject, teachers, cn);
      if (label) {
        for (const p of [c.start - 1, c.start + c.duration]) {
          const hit = (s.byClass.get(`${classKey(cn)}|${c.day},${p}`) ?? []).find((e) => !sameBlock(e.raw, c) && s.sameSubject(e.subject, c.subject));
          if (hit) conflicts.push(conflict(CONSECUTIVE_RULE, 'ders', c.subject, c.periods, SEV_SOFT, `${label}: ${c.subject} ile ${hit.subject} art arda geliyor.`, label));
        }
      }
      for (const sc of s.rulePair) {
        if (!s.ruleScopeMatches(sc, teachers, cn)) continue;
        const subs = new Set(sc.subjects.map(upper));
        if (!subs.has(upper(c.subject))) continue;
        const others = s.classLessonsOnDay(cn, c.day).filter((e) => subs.has(upper(e.subject)) && upper(e.subject) !== upper(c.subject) && !sameBlock(e.raw, c));
        if (others.length) {
          conflicts.push(conflict(PAIR_NOT_SAME_DAY, 'ders', c.subject, c.periods, SEV_SOFT,
            `${sc.label}: ${cn} sınıfında ${c.subject} ile ${others[0].subject} aynı güne gelemez (${s.slotLabel(c.day, others[0].period)} ${others[0].subject} var).`, sc.label));
          break;
        }
      }
    }
    const window = s.prefWindows.get(upper(c.subject));
    if (window) {
      const half = Math.floor(s.P / 2) || 1;
      if ((window === 'morning' && c.start >= half) || (window === 'afternoon' && c.start < half)) {
        conflicts.push(conflict(SUBJECT_WINDOW, 'ders', c.subject, c.periods, SEV_PREFERENCE,
          `${c.subject} için tercih edilen zaman dilimi: ${window === 'morning' ? 'sabah' : 'öğleden sonra'}.`));
      }
    }
    let status: string;
    if (conflicts.some((x) => x.type === LOCKED_SOURCE) || blocked) status = FORBIDDEN;
    else if (occupied) status = CONFLICT;
    else if (c.sourceDay === c.day && c.sourcePeriod === c.start) status = CURRENT;
    else if (conflicts.some((x) => x.severity >= SEV_PREFERENCE)) status = QUESTIONABLE;
    else status = VALID;
    return finish(status, conflicts, c);
  } catch (e) {
    conflicts.push(conflict(DATA_ERROR, '', '', [], SEV_HARD, `Analiz hatası: ${e}`));
    return finish(ANALYSIS_ERROR, conflicts, c);
  }
}

export const isPlaceable = (r: Result) => [VALID, QUESTIONABLE, CONFLICT, CURRENT].includes(r.status);
export { truthy };
