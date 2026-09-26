// Ekranın okuduğu türetilmiş veri: satırlar, hücreler, yerleştirilemeyenler,
// renkler, kısaltmalar. Tek kaynak .roz verisidir (data_store); burada hiçbir
// şey değiştirilmez.
import { classesOf, gridDimensions, hours, subjectOf, teacherOf, typeStr } from '../engine/data.ts';
import { parseDistribution } from '../engine/build.ts';
import { normKey } from '../engine/norm.ts';
import { classKey, lessonClasses, lessonTeachers, teacherKey } from './placement.ts';

export type View = 'classes' | 'teachers';

export function dims(data: any): { D: number; P: number; days: string[] } {
  const [D, P] = gridDimensions(data);
  const days: string[] = Array.isArray(data?.settings?.days) && data.settings.days.length >= D
    ? data.settings.days.slice(0, D).map(String)
    : ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar'].slice(0, D);
  while (days.length < D) days.push(`${days.length + 1}. gün`);
  return { D, P, days };
}

/** main_window.cls_sort_key: "9A" < "10A" (sayı önce). */
function clsSortKey(c: string): [number, string] {
  const m = /^(\d+)(.*)$/.exec(String(c).trim());
  return m ? [parseInt(m[1], 10), m[2]] : [999, String(c)];
}

export function classRows(data: any): string[] {
  const names = (data?.siniflar ?? []).map((c: any) => String(c?.ad || c?.name || '').trim()).filter(Boolean);
  return [...new Set<string>(names)].sort((a, b) => {
    const ka = clsSortKey(a), kb = clsSortKey(b);
    return ka[0] - kb[0] || (ka[1] < kb[1] ? -1 : ka[1] > kb[1] ? 1 : 0);
  });
}

export function teacherRows(data: any): string[] {
  const names = (data?.ogretmenler ?? []).map((t: any) => String(t?.ad || t?.name || '').trim()).filter(Boolean);
  return [...new Set<string>(names)].sort((a, b) => a.localeCompare(b, 'tr'));
}

// ── renk ────────────────────────────────────────────────────────────────────
const BAD = new Set(['#FFFFFF', '#000000', '#C0C0C0', '#B4B4B8', '#D0D0D0', '']);
const okColor = (c: unknown) => typeof c === 'string' && /^#[0-9a-fA-F]{6}$/.test(c) && !BAD.has(c.toUpperCase());
const PALETTE = ['#2563EB', '#16A34A', '#DC2626', '#9333EA', '#EA580C', '#0891B2', '#DB2777', '#65A30D',
  '#7C3AED', '#0D9488', '#CA8A04', '#4F46E5', '#BE123C', '#15803D', '#1D4ED8', '#C2410C'];
function hashColor(key: string): string {
  let h = 0;
  for (const ch of key) h = (h * 131 + ch.codePointAt(0)!) >>> 0;
  return PALETTE[h % PALETTE.length];
}

export function subjectColor(name: string, data: any): string {
  const k = normKey(name);
  if (!k) return '#2563EB';
  for (const d of data?.dersler ?? []) {
    if ((normKey(d?.ad) === k || normKey(d?.kisa) === k) && okColor(d?.color || d?.renk)) return String(d.color || d.renk).toUpperCase();
  }
  for (const a of data?.atamalar ?? []) {
    if ((normKey(a?.subject) === k || normKey(a?.ders) === k) && okColor(a?.color || a?.renk)) return String(a.color || a.renk).toUpperCase();
  }
  return hashColor(k);
}

export function classColor(name: string, data: any): string {
  const k = normKey(name);
  for (const c of data?.siniflar ?? []) if (normKey(c?.ad || c?.name) === k && okColor(c?.renk || c?.color)) return String(c.renk || c.color).toUpperCase();
  return hashColor('c' + k);
}

/** timetable_grid.get_subject_abbr — en fazla 6 karakter. */
const ABBR: [string, string][] = [
  ['TÜRK DİLİ VE EDEBİYATI', 'TDE'], ['TÜRKÇE', 'TÜR'], ['EDEBİYAT', 'EDEB'], ['GÖRSEL SANATLAR', 'GÖRSEL'],
  ['GÖRSEL', 'GÖRSEL'], ['İNGİLİZCE', 'İNG'], ['ALMANCA', 'ALM'], ['DİN KÜLTÜRÜ VE AHLAK BİLGİSİ', 'DİN'],
  ['DİN KÜLTÜRÜ', 'DİN'], ['FELSEFE', 'FELS'], ['REHBERLİK', 'REHBER'], ['BİYOLOJİ', 'BİYO'], ['KİMYA', 'KİMYA'],
  ['FİZİK', 'FİZİK'], ['TARİH', 'TARİH'], ['SEÇMELİ', 'SEÇ'],
];
const trUpper = (s: string) => s.replace(/i/g, 'İ').replace(/ı/g, 'I').toUpperCase();
export function abbr(subject: string, max = 6): string {
  if (!subject) return '';
  let s = trUpper(String(subject).trim());
  s = s.replace('BEDEN EĞİTİMİ VE SPOR', 'BEDEN').replace('BEDEN EĞİTİMİ', 'BEDEN')
    .replace('MATEMATİK', 'MAT').replace('GEOMETRİ', 'GEOM').replace('COĞRAFYA', 'COĞRAF');
  for (const [k, v] of ABBR) if (s === k || s.startsWith(k)) { s = s.replace(k, v); break; }
  const m = /^(.+?)\s*(\d+)$/.exec(s);
  const base = m ? m[1].trim() : s, num = m ? ` ${m[2]}` : '';
  if (base.length + num.length <= max) return base + num;
  const allowed = max - num.length;
  return allowed > 0 ? (base.slice(0, allowed) + num).trim().slice(0, max) : s.slice(0, max);
}

// ── hücreler ────────────────────────────────────────────────────────────────
export interface Cell {
  key: string;              // blok anahtarı
  day: number; start: number; span: number;
  subject: string; teacher: string; classes: string[];
  locked: boolean; split: boolean; conflict: boolean; manual: boolean;
  entries: any[];           // bu bloğa ait bütün grid_placements kayıtları
}

const intOf = (v: unknown, d = 0) => { const n = Number(v); return Number.isFinite(n) ? Math.trunc(n) : d; };
export const dayOf = (p: any) => intOf(p.day ?? p.col, 0);
export const periodOf = (p: any) => intOf(p.period ?? p.row, 0);
export const durOf = (p: any) => Math.max(1, intOf(p.duration, 1) || 1);

/** Satır -> hücre bloğu listesi. Çok saatlik dersler tek blok olarak döner. */
export function buildCells(data: any, view: View, rows: string[]): Map<string, Cell[]> {
  const { P } = dims(data);
  const rowKey = view === 'classes' ? classKey : teacherKey;
  const index = new Map(rows.map((r) => [rowKey(r), r] as const));
  // (satır, hücre) -> kayıtlar
  const slots = new Map<string, Map<number, any[]>>();
  for (const p of data?.grid_placements ?? []) {
    if (!p || typeof p !== 'object') continue;
    const owners = view === 'classes' ? lessonClasses(p) : lessonTeachers(p);
    const d = dayOf(p), s = periodOf(p), dur = durOf(p);
    for (const o of owners) {
      const row = index.get(rowKey(o));
      if (!row) continue;
      if (!slots.has(row)) slots.set(row, new Map());
      const m = slots.get(row)!;
      for (let k = 0; k < dur; k++) {
        const cell = d * P + s + k;
        if (!m.has(cell)) m.set(cell, []);
        m.get(cell)!.push(p);
      }
    }
  }
  const out = new Map<string, Cell[]>();
  for (const row of rows) {
    const m = slots.get(row);
    const cells: Cell[] = [];
    if (m) {
      const idxs = [...m.keys()].sort((a, b) => a - b);
      let cur: Cell | null = null;
      for (const idx of idxs) {
        const entries = m.get(idx)!;
        const p = entries[0];
        const bkey = String(p.block_id || `${dayOf(p)}|${periodOf(p)}|${normKey(p.subject_name || p.subject)}`);
        const d = Math.floor(idx / P), per = idx % P;
        const subject = String(p.subject_name || p.subject || '');
        const teacher = String(p.teacher_name || p.teacher || '');
        const classes = [...new Set(entries.flatMap((e) => lessonClasses(e)))];
        if (cur && cur.key === bkey && cur.day === d && cur.start + cur.span === per) {
          cur.span++;
          for (const e of entries) if (!cur.entries.includes(e)) cur.entries.push(e);
          continue;
        }
        const blocks = new Set(entries.map((e) => String(e.block_id || `${dayOf(e)}|${periodOf(e)}|${normKey(e.subject_name || e.subject)}|${teacherKey(e.teacher_name || e.teacher)}`)));
        cur = { key: bkey, day: d, start: per, span: 1, subject, teacher, classes,
          locked: entries.some((e) => e.locked || e.is_locked), split: entries.some((e) => e.is_split),
          conflict: entries.some((e) => e.has_conflict) || blocks.size > 1,
          manual: entries.some((e) => e.is_manual), entries: [...entries] };
        cells.push(cur);
      }
    }
    out.set(row, cells);
  }
  return out;
}

// ── yerleştirilemeyenler ────────────────────────────────────────────────────
export interface Unplaced {
  id: string; subject: string; teacher: string; className: string; classes: string[];
  duration: number; color: string; loose?: string; assignment?: number;
}

/** Atamaların talebi eksi çizelgede duran saatler = yerleştirilemeyen bloklar. */
export function unplacedCards(data: any): Unplaced[] {
  const placed = new Map<string, number>();
  for (const p of data?.grid_placements ?? []) {
    if (!p || typeof p !== 'object' || p.is_filler) continue;
    const cls = lessonClasses(p);
    if (!cls.length) continue;
    // Birleşik ders her sınıf için ayrı kayıt; saat bir kez sayılır.
    const own = p.class_name || p.class;
    if (cls.length > 1 && own && classKey(own) !== classKey(cls[0])) continue;
    const k = `${classKey(cls[0])}|${normKey(p.subject_name || p.subject)}|${teacherKey(p.teacher_name || p.teacher)}`;
    placed.set(k, (placed.get(k) ?? 0) + durOf(p));
  }
  const looseByKey = new Map<string, number>();
  const out: Unplaced[] = [];
  for (const lc of data?.loose_unplaced_cards ?? []) {
    if (!lc || typeof lc !== 'object') continue;
    const cls = lessonClasses(lc);
    const k = `${classKey(cls[0] ?? '')}|${normKey(lc.subject_name || lc.subject)}|${teacherKey(lc.teacher_name || lc.teacher)}`;
    looseByKey.set(k, (looseByKey.get(k) ?? 0) + durOf(lc));
    out.push({ id: String(lc.id || `loose_${out.length}`), subject: String(lc.subject_name || lc.subject || ''),
      teacher: String(lc.teacher_name || lc.teacher || ''), className: cls.join(' + '), classes: cls, duration: durOf(lc),
      color: subjectColor(String(lc.subject_name || lc.subject || ''), data), loose: String(lc.id || '') });
  }
  (data?.atamalar ?? []).forEach((a: any, ai: number) => {
    const subject = subjectOf(a), teacher = teacherOf(a);
    const cls = classesOf(a);
    if (!cls.length || !subject) return;
    const k = `${classKey(cls[0])}|${normKey(subject)}|${teacherKey(teacher)}`;
    let pool = (placed.get(k) ?? 0) + (looseByKey.get(k) ?? 0);
    const parts = parseDistribution(typeStr(a), hours(a));
    parts.forEach((dur, pi) => {
      const used = Math.min(dur, pool);
      pool -= used;
      const need = dur - used;
      if (need > 0) {
        out.push({ id: `${ai}_${pi}`, subject, teacher, className: cls.join(' + '), classes: cls, duration: need,
          color: subjectColor(subject, data), assignment: ai });
      }
    });
    placed.set(k, Math.max(0, pool - (looseByKey.get(k) ?? 0)));
    looseByKey.delete(k);
  });
  return out;
}

/** Toplam atanan / yerleşen saat (sınıf-saati). */
export function hourTotals(data: any): { assigned: number; placed: number } {
  let assigned = 0;
  for (const a of data?.atamalar ?? []) assigned += hours(a) * Math.max(1, classesOf(a).length);
  let placed = 0;
  for (const p of data?.grid_placements ?? []) if (p && !p.is_filler) placed += durOf(p);
  return { assigned, placed };
}
