// constraint_sync.py (grid_dimensions, get_matrix, get_personal) ve
// lesson_hours.py karşılıkları: .roz verisini motorun okuduğu biçimde okur.
import { isDigit, text, toInt, truthy } from './py.ts';

export type Store = Record<string, any>;

export const OPEN = 2, AVOID = 1, CLOSED = 0;
const PERSONAL_KEY = 'personal_off';
const PERSONAL_STORE = 'kisitlamalar_kisisel';

function get(o: any, k: string): any {
  return o && typeof o === 'object' ? o[k] : undefined;
}

/** (gün sayısı, saat sayısı) */
export function gridDimensions(data: Store): [number, number] {
  const settings = get(data, 'settings') || {};
  let dayCount: number;
  const days = get(settings, 'days');
  if (truthy(days)) {
    dayCount = Array.isArray(days) ? days.length : String(days).length;
  } else {
    let dc: any = 'days_count' in settings ? settings.days_count : settings.day_count;
    if (!truthy(dc)) dc = data && 'gun_sayisi' in data ? data.gun_sayisi : 5;
    dayCount = toInt(dc) ?? 5;
  }
  if (dayCount <= 0) dayCount = 5;
  let periods: any = get(settings, 'periods');
  if (!truthy(periods)) periods = data && 'ders_saati' in data ? data.ders_saati : 8;
  let p = toInt(periods) ?? 8;
  if (p <= 0) p = 8;
  return [dayCount, p];
}

export function coerceState(value: unknown): number {
  if (typeof value === 'boolean') return value ? OPEN : CLOSED;
  const ival = toInt(value);
  if (ival === null) return OPEN;
  // "? tercih edilmez" (AVOID) kaldırıldı: AÇIK okunur.
  if (ival === AVOID) return OPEN;
  if (ival === OPEN || ival === CLOSED) return ival;
  return ival > 0 ? OPEN : CLOSED;
}

export function getPersonal(entity: any, name: string, data: Store): boolean[][] {
  const [D, P] = gridDimensions(data);
  const grid = Array.from({ length: D }, () => new Array<boolean>(P).fill(false));
  const raw = truthy(get(entity, PERSONAL_KEY)) ? entity[PERSONAL_KEY] : [];
  for (let d = 0; d < D; d++) {
    if (d < raw.length && Array.isArray(raw[d])) {
      for (let p = 0; p < P; p++) if (p < raw[d].length && truthy(raw[d][p])) grid[d][p] = true;
    }
  }
  const store = truthy(get(data, PERSONAL_STORE)) ? data[PERSONAL_STORE] : {};
  const entry = get(store, name);
  if (entry && typeof entry === 'object' && !Array.isArray(entry)) {
    for (const [k, val] of Object.entries(entry)) {
      const parts = String(k).split(',');
      if (parts.length !== 2) continue;
      const d = toInt(parts[0]), p = toInt(parts[1]);
      if (d === null || p === null) continue;
      if (d >= 0 && d < D && p >= 0 && p < P && truthy(val)) grid[d][p] = true;
    }
  }
  return grid;
}

/** Birimin 3 durumlu müsaitlik matrisi [gün][saat]. */
export function getMatrix(entity: any, name: string, data: Store): number[][] {
  const [D, P] = gridDimensions(data);
  const matrix = Array.from({ length: D }, () => new Array<number>(P).fill(OPEN));
  const toff = get(entity, 'timeoff');
  if (Array.isArray(toff) && toff.length > 0) {
    for (let d = 0; d < D; d++) {
      if (d < toff.length && Array.isArray(toff[d])) {
        const row = toff[d];
        const allClosed = row.length > 0 && row.every((x: unknown) => coerceState(x) === CLOSED);
        for (let p = 0; p < P; p++) {
          matrix[d][p] = p < row.length ? coerceState(row[p]) : (allClosed ? CLOSED : OPEN);
        }
      } else {
        matrix[d] = new Array<number>(P).fill(OPEN);
      }
    }
  } else {
    const kis = truthy(get(data, 'kisitlamalar')) ? data.kisitlamalar : {};
    const entry = get(kis, name);
    if (entry && typeof entry === 'object' && !Array.isArray(entry)) {
      for (const [k, raw] of Object.entries(entry)) {
        const parts = String(k).split(',');
        if (parts.length !== 2) continue;
        const d = toInt(parts[0]), p = toInt(parts[1]);
        if (d === null || p === null) continue;
        if (d >= 0 && d < D && p >= 0 && p < P) matrix[d][p] = coerceState(raw);
      }
    }
  }
  const personal = getPersonal(entity, name, data);
  for (let d = 0; d < D; d++) for (let p = 0; p < P; p++) if (personal[d][p]) matrix[d][p] = CLOSED;
  return matrix;
}

// ── lesson_hours.py ─────────────────────────────────────────────────────────
const HOUR_KEYS = ['duration', 'saat', 'ders_sayisi', 'toplam_saat', 'hours'];
const TYPE_KEYS = ['type', 'dagilim'];
const DIST_KEY = 'distribution';
const TEACHER_KEYS = ['teacher', 'ogretmen', 'teacher_name'];
const CLASS_KEYS = ['class', 'sinif', 'class_name'];
const SUBJECT_KEYS = ['subject', 'ders', 'subject_name'];

function first(a: any, keys: string[]): string {
  for (const k of keys) {
    const v = text(get(a, k));
    if (v) return v;
  }
  return '';
}

export function parseType(value: unknown): number | null {
  if (Array.isArray(value)) {
    const parts: number[] = [];
    for (const p of value) {
      const n = toInt(p);
      if (n !== null && n > 0) parts.push(n);
    }
    return parts.length ? parts.reduce((a, b) => a + b, 0) : null;
  }
  const t = text(value).replace(/ /g, '');
  if (!t) return null;
  if (t.includes('+')) {
    const parts = t.split('+').filter(isDigit).map((p) => parseInt(p, 10));
    return parts.length ? parts.reduce((a, b) => a + b, 0) : null;
  }
  return isDigit(t) ? parseInt(t, 10) : null;
}

function isObj(a: unknown): a is Record<string, any> {
  return !!a && typeof a === 'object' && !Array.isArray(a);
}

export function partsOf(a: any): number[] {
  if (isObj(a)) {
    for (const k of TYPE_KEYS) {
      const t = text(a[k]).replace(/ /g, '');
      if (t && truthy(parseType(t))) {
        if (t.includes('+')) return t.split('+').filter(isDigit).map((p) => parseInt(p, 10));
        return [parseInt(t, 10)];
      }
    }
    const dist = a[DIST_KEY];
    if (Array.isArray(dist) && truthy(parseType(dist))) {
      return dist.filter((p: unknown) => isDigit(String(p).trim()) && parseInt(String(p), 10) > 0)
        .map((p: unknown) => parseInt(String(p), 10));
    }
  }
  const total = hours(a);
  const parts: number[] = [];
  let rem = total;
  while (rem > 0) {
    parts.push(Math.min(2, rem));
    rem -= Math.min(2, rem);
  }
  return parts;
}

export function typeStr(a: any): string {
  for (const k of TYPE_KEYS) {
    if (parseType(get(a, k)) !== null) return text(a[k]).replace(/ /g, '');
  }
  const parts = partsOf(a);
  return parts.length ? parts.join('+') : '';
}

export function hours(a: any): number {
  if (!isObj(a)) return 0;
  for (const k of TYPE_KEYS) {
    const parsed = parseType(a[k]);
    if (parsed) return parsed;
  }
  const dist = parseType(a[DIST_KEY]);
  if (dist) return dist;
  for (const k of HOUR_KEYS) {
    const raw = a[k];
    if (raw === null || raw === undefined) continue;
    const f = Number(String(raw).trim());
    if (String(raw).trim() === '' || !Number.isFinite(f)) continue;
    const value = Math.trunc(f);
    if (value > 0) return value;
  }
  return 0;
}

export const teacherOf = (a: any) => (isObj(a) ? first(a, TEACHER_KEYS) : '');
export const subjectOf = (a: any) => (isObj(a) ? first(a, SUBJECT_KEYS) : '');
export const classNameOf = (a: any) => (isObj(a) ? first(a, CLASS_KEYS) : '');

export function classesOf(a: any): string[] {
  if (!isObj(a)) return [];
  const combined = a.combined_classes;
  if (Array.isArray(combined) && combined.length) {
    const names = combined.map((c: unknown) => text(c)).filter(Boolean);
    if (names.length) return names;
  }
  let raw = classNameOf(a);
  if (!raw) return [];
  for (const sep of [',', '&']) raw = raw.split(sep).join('+');
  const parts = raw.split('+').map((p) => p.trim()).filter(Boolean);
  return parts.length ? parts : [classNameOf(a)];
}
