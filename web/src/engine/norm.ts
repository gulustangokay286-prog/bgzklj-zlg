// scheduler/model.py (norm_key, norm_class), version_store.normalize_teacher_name
// ve auto_scheduler.normalize_class_name / matches_class karşılıkları.
import { str } from './py.ts';

const TR_FOLD: Record<string, string> = {
  'ı': 'i', 'İ': 'i', 'I': 'i', 'i': 'i',
  'ş': 's', 'Ş': 's', 'ğ': 'g', 'Ğ': 'g',
  'ü': 'u', 'Ü': 'u', 'ö': 'o', 'Ö': 'o',
  'ç': 'c', 'Ç': 'c', 'â': 'a', 'Â': 'a',
  'î': 'i', 'Î': 'i', 'û': 'u', 'Û': 'u',
};
const TR_FOLD_RE = /[ıİIişŞğĞüÜöÖçÇâÂîÎûÛ]/g;

const cache = new Map<string, string>();

/** Karşılaştırma anahtarı: Türkçe katlanmış, aksansız, boşluksuz, küçük harf. */
export function normKey(s: unknown): string {
  const raw = str(s);
  const hit = cache.get(raw);
  if (hit !== undefined) return hit;
  let t = raw.replace(TR_FOLD_RE, (ch) => TR_FOLD[ch]).toLowerCase();
  t = t.normalize('NFKD').replace(/\p{Mn}/gu, '');
  t = t.replace(/[^\p{L}\p{N}]/gu, '');
  cache.set(raw, t);
  return t;
}

export const normClass = normKey;

/** version_store.normalize_teacher_name */
export function normTeacher(name: unknown): string {
  if (!name) return '';
  let s = String(name).trim().toUpperCase();
  s = s.replace(/İ/g, 'I').replace(/ı/g, 'I')
    .replace(/Ş/g, 'S').replace(/ş/g, 'S')
    .replace(/Ğ/g, 'G').replace(/ğ/g, 'G')
    .replace(/Ü/g, 'U').replace(/ü/g, 'U')
    .replace(/Ö/g, 'O').replace(/ö/g, 'O')
    .replace(/Ç/g, 'C').replace(/ç/g, 'C');
  return s.replace(/\s+/g, ' ').trim();
}

/** auto_scheduler.normalize_class_name */
export function normalizeClassName(name: unknown): string {
  if (!name) return '';
  return String(name).trim().toUpperCase().replace(/ /g, '').replace(/-/g, '/').replace(/\\/g, '/');
}

/** auto_scheduler.matches_class */
export function matchesClass(asgn: unknown, target: unknown): boolean {
  if (!asgn || !target) return false;
  const a = String(asgn), t = String(target);
  const normTarget = normalizeClassName(t);
  const normAsgn = normalizeClassName(a);
  if (normAsgn === normTarget) return true;
  const cleanTarget = normTarget.split('(')[0].trim();
  const cleanAsgn = normAsgn.split('(')[0].trim();
  if (cleanTarget && cleanAsgn && cleanTarget === cleanAsgn) return true;
  for (const part of a.replace(/&/g, ',').replace(/\+/g, ',').split(',')) {
    const pNorm = normalizeClassName(part);
    if (pNorm === normTarget) return true;
    const pClean = pNorm.split('(')[0].trim();
    if (cleanTarget && pClean && pClean === cleanTarget) return true;
  }
  return false;
}
