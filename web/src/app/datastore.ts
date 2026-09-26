// .roz verisi üzerindeki kalıcı değişiklikler. Masaüstündeki kurallar:
//   edit_forms.format_tr_name / _auto_short_code, version_store.sanitize_atamalar,
//   lesson_hours.sync_keys, master_data_dialog (_act_update/_act_delete/
//   _sync_class_teacher_two_way), constraint_sync.set_matrix/set_personal.
// Masaüstü aynı dosyayı açtığında aynı şeyi görsün diye alan adları birebir.
import { CLOSED, OPEN, classNameOf, classesOf, coerceState, getMatrix, gridDimensions, hours as hoursOf, partsOf, subjectOf, teacherOf, typeStr } from '../engine/data.ts';
import { matchesClass, normTeacher } from '../engine/norm.ts';

const TR_UP: Record<string, string> = { 'i': 'İ', 'ı': 'I', 'ç': 'Ç', 'ğ': 'Ğ', 'ö': 'Ö', 'ş': 'Ş', 'ü': 'Ü' };
const TR_LO: Record<string, string> = { 'İ': 'i', 'I': 'ı', 'Ç': 'ç', 'Ğ': 'ğ', 'Ö': 'ö', 'Ş': 'ş', 'Ü': 'ü' };

/** edit_forms.format_tr_name — 'hüseyin arman' -> 'Hüseyin Arman' */
export function formatTrName(s: unknown): string {
  if (!s) return String(s ?? '');
  return String(s).trim().split(/\s+/).filter(Boolean).map((w) => {
    const first = TR_UP[w[0]] ?? w[0].toUpperCase();
    const rest = [...w.slice(1)].map((c) => TR_LO[c] ?? c.toLowerCase()).join('');
    return first + rest;
  }).join(' ');
}

/** edit_forms.normalize_tr — arama için. */
export function normalizeTr(s: unknown): string {
  const m: Record<string, string> = { 'İ': 'i', 'I': 'i', 'ı': 'i', 'i': 'i', 'Ç': 'c', 'ç': 'c', 'Ğ': 'g', 'ğ': 'g', 'Ö': 'o', 'ö': 'o', 'Ş': 's', 'ş': 's', 'Ü': 'u', 'ü': 'u' };
  return [...String(s ?? '')].map((c) => m[c] ?? c.toLowerCase()).join('');
}

const SHORT: Record<string, string> = {
  'BEDEN': 'BEDEN', 'BEDEN EĞİTİMİ': 'BEDEN', 'BEDEN EĞİTİMİ VE SPOR': 'BEDEN', 'BED': 'BEDEN', 'TARİH': 'TARİH', 'TAR': 'TARİH',
  'İNKILAP': 'İNKILAP TARİHİ', 'İNKILAP TARİHİ': 'İNKILAP TARİHİ', 'T.C. İNKILAP TARİHİ': 'İNKILAP TARİHİ', 'REHBERLİK': 'REHBERLİK',
  'REHBERLİK VE YÖNLENDİRME': 'REHBERLİK', 'REH': 'REHBERLİK', 'TÜRKÇE': 'TÜRKÇE', 'TÜRK': 'TÜRKÇE', 'MÜZİK': 'MÜZİK', 'MÜZ': 'MÜZİK',
  'FELSEFE': 'FELSEFE', 'FEL': 'FELSEFE', 'DİN': 'DİN', 'DİN KÜLTÜRÜ': 'DİN', 'DİN KÜLTÜRÜ VE AHLAK BİLGİSİ': 'DİN', 'EDİN KÜLTÜRÜ': 'DİN',
  'GÖRSEL SANATLAR': 'GÖRSEL', 'GÖRSEL': 'GÖRSEL', 'GÖRS': 'GÖRSEL', 'RESİM': 'GÖRSEL', 'BİYOLOJİ': 'BİYO', 'BİYO': 'BİYO', 'FİZİK': 'FİZİK',
  'FİZ': 'FİZİK', 'KİMYA': 'KİMYA', 'KİM': 'KİMYA', 'COĞRAFYA': 'COĞRAF', 'COĞ': 'COĞRAF', 'GEOMETRİ': 'GEOM', 'GEOMETRI': 'GEOM',
  'GEO': 'GEOM', 'EDEBİYAT': 'EDEB', 'EDB': 'EDEB', 'TÜRK DİLİ VE EDEBİYATI': 'TDE', 'TDE': 'TDE', 'MATEMATİK': 'MATE', 'MATEMATIK': 'MATE',
  'MAT': 'MATE', 'MATE': 'MATE', 'İNGİLİZCE': 'İNG', 'İNG': 'İNG', 'ALMANCA': 'ALM', 'ALM': 'ALM', 'FRANSIZCA': 'FRA', 'FRA': 'FRA',
  'PARAGRAF': 'PARAG', 'PARAG': 'PARAG', 'PAR': 'PARAG', 'PROBLEM': 'PROB', 'PROB': 'PROB', 'BİLİŞİM': 'BİLİŞ', 'KODLAMA': 'KODLAM',
  'YAZILIM': 'YAZILIM', 'ROBOTİK': 'ROBOTİK', 'SAĞLIK': 'SAĞLIK BİLGİSİ', 'SAĞLIK BİLGİSİ': 'SAĞLIK BİLGİSİ', 'TRAFİK': 'TRAFİK',
  'ASTRONOMİ': 'ASTRONOMİ', 'MANTIK': 'MANTIK', 'SOSYOLOJİ': 'SOSYOLOJİ', 'PSİKOLOJİ': 'PSİKOLOJİ',
};
/** edit_forms._auto_short_code */
export function autoShortCode(text: string): string {
  if (!text) return '';
  const clean = text.trim();
  const nums = (clean.match(/\d+/g) ?? []).join('');
  const letters = clean.replace(/\d+/g, '').trim();
  const up = letters.replace(/i/g, 'İ').replace(/ı/g, 'I').toUpperCase();
  const base = SHORT[up] ?? (up.length > 4 ? up.slice(0, 4) : up);
  return (nums ? `${base} ${nums}` : base).trim();
}

// ── atamalar ───────────────────────────────────────────────────────────────
const HOUR_KEYS = ['duration', 'saat', 'ders_sayisi', 'toplam_saat', 'hours'];
const TYPE_KEYS = ['type', 'dagilim'];

/** lesson_hours.sync_keys — eş anlamlı alanları tek değere eşitler. */
export function syncKeys(a: any): any {
  const hrs = hoursOf(a), dist = typeStr(a);
  const t = teacherOf(a), s = subjectOf(a), c = classNameOf(a);
  for (const k of HOUR_KEYS) if (k in a || k === 'duration') a[k] = hrs;
  for (const k of TYPE_KEYS) if (k in a || k === 'type') a[k] = dist;
  if ('distribution' in a) a.distribution = partsOf(a);
  if (t) for (const k of ['teacher', 'ogretmen', 'teacher_name']) if (k in a || k === 'teacher') a[k] = t;
  if (s) for (const k of ['subject', 'ders', 'subject_name']) if (k in a || k === 'subject') a[k] = s;
  if (c) for (const k of ['class', 'sinif', 'class_name']) if (k in a || k === 'class') a[k] = c;
  return a;
}

/** version_store.sanitize_atamalar — tekilleştirir ve alanları eşitler. */
export function sanitizeAtamalar(list: any[]): any[] {
  const seen = new Map<string, any>();
  for (const a of list ?? []) {
    if (!a || typeof a !== 'object' || Array.isArray(a)) continue;
    const subj = String(a.subject || a.ders || a.subject_name || '').trim();
    if (!subj) continue;
    const tParts: string[] = [];
    for (const p of String(a.teacher || a.ogretmen || a.teacher_name || '').split(',').map((x) => x.trim()).filter(Boolean)) {
      if (!tParts.includes(p)) tParts.push(p);
    }
    const teacher = tParts.join(', ');
    const cls = String(a.class || a.sinif || a.class_name || '').trim();
    let rawType = String(a.type ?? '').trim();
    if (rawType === '0' || rawType === 'None' || rawType === 'undefined' || rawType === 'null') rawType = '';
    const parts = rawType.split('+').map((p) => p.trim()).filter((p) => /^\d+$/.test(p)).map(Number);
    let dur: number;
    if (parts.length) dur = parts.reduce((x, y) => x + y, 0);
    else if (/^\d+$/.test(rawType)) dur = Number(rawType);
    else {
      const dv = a.duration ?? a.saat;
      dur = dv !== null && dv !== undefined && /^\d+$/.test(String(dv)) ? Number(dv) : 0;
      if (dur > 0 && !rawType) rawType = String(dur);
    }
    const clean = { ...a, subject: subj, teacher, class: cls, duration: dur, type: rawType };
    syncKeys(clean);
    seen.set(`${subj.toUpperCase()}|${teacher.toUpperCase()}|${cls.toUpperCase()}`, clean);
  }
  return [...seen.values()];
}

/** "2+2" -> 4; "3" -> 3; boş/0 -> 0 */
export function typeHours(type: string): number {
  const t = String(type ?? '').replace(/\s/g, '');
  const parts = t.split('+').filter((p) => /^\d+$/.test(p)).map(Number);
  if (t.includes('+')) return parts.reduce((a, b) => a + b, 0);
  return /^\d+$/.test(t) ? Number(t) : 0;
}

/** Kullanıcının yazdığı dağılımı kanonik biçime getirir: "2 + 2" -> "2+2". */
export function canonicalType(type: string): string {
  const parts = String(type ?? '').split('+').map((p) => p.trim()).filter((p) => /^\d+$/.test(p) && Number(p) > 0);
  if (parts.length > 1) return parts.join('+');
  return parts.length ? parts[0] : '';
}

export const assignmentHours = hoursOf;
export const assignmentClasses = classesOf;

export function newAssignment(o: { teacher: string; subject: string; classes: string[]; type: string; color?: string }): any {
  const comb = o.classes.length > 1;
  const cls = comb ? o.classes.join(' + ') : (o.classes[0] ?? '');
  const type = canonicalType(o.type) || '2';
  const dur = typeHours(type);
  return {
    ogretmen: o.teacher, teacher: o.teacher, ders: o.subject, subject: o.subject, sinif: cls, class: cls,
    ders_sayisi: dur, duration: dur, dagilim: type, type, renk: o.color ?? '', color: o.color ?? '',
    is_combined: comb, combined_classes: comb ? [...o.classes] : [],
  };
}

// ── ilişkiler (sınıf öğretmeni) ────────────────────────────────────────────
/** master_data_dialog._sync_class_teacher_two_way */
export function syncClassTeacher(d: any) {
  const siniflar: any[] = d.siniflar ?? [], ogretmenler: any[] = d.ogretmenler ?? [];
  const teacherToClass = new Map<string, string>();
  for (const s of siniflar) {
    const so = String(s.sinif_ogretmeni ?? '').trim();
    if (so) teacherToClass.set(formatTrName(so), s.ad ?? '');
  }
  const classToTeacher = new Map<string, string>();
  for (const t of ogretmenler) {
    const soc = String(t.sinif_ogretmeni ?? '').trim();
    if (soc) classToTeacher.set(soc, t.ad ?? '');
  }
  for (const [cName, tName] of classToTeacher) {
    const s = siniflar.find((x) => String(x.ad ?? '').trim() === cName);
    if (s) { s.sinif_ogretmeni = tName; teacherToClass.set(formatTrName(tName), cName); }
  }
  for (const t of ogretmenler) t.sinif_ogretmeni = teacherToClass.get(formatTrName(t.ad ?? '')) ?? '';
}

// ── yeniden adlandırma / silme zincirleri ──────────────────────────────────
export type Kind = 'dersler' | 'siniflar' | 'derslikler' | 'ogretmenler';

const sameTeacher = (a: unknown, b: unknown) => !!a && !!b && normTeacher(a) === normTeacher(b);

/** version_store.rename_teacher_in_data_store + master_data_dialog._act_update */
export function renameEntity(d: any, kind: Kind, oldName: string, newName: string) {
  if (!oldName || !newName || oldName === newName) return;
  if (kind === 'ogretmenler') {
    for (const a of d.atamalar ?? []) {
      const parts = String(a.teacher || a.ogretmen || a.teacher_name || '').split(',').map((p) => p.trim()).filter(Boolean)
        .map((p) => (sameTeacher(p, oldName) || p === oldName ? newName : p));
      if (parts.length) {
        a.teacher = parts.join(', ');
        if ('ogretmen' in a) a.ogretmen = a.teacher;
        if ('teacher_name' in a) a.teacher_name = a.teacher;
      }
    }
    for (const list of [d.grid_placements ?? [], d.auto_schedule_results ?? []]) {
      for (const p of list) {
        const t = p.teacher_name || p.teacher || '';
        if (sameTeacher(t, oldName) || String(t).trim() === oldName) { p.teacher_name = newName; p.teacher = newName; }
      }
    }
    for (const s of d.siniflar ?? []) if (sameTeacher(s.sinif_ogretmeni, oldName)) s.sinif_ogretmeni = newName;
    for (const key of ['kisitlamalar', 'kisitlamalar_kisisel']) {
      const m = d[key];
      if (m && typeof m === 'object' && oldName in m) { m[newName] = m[oldName]; delete m[oldName]; }
    }
    for (const r of d.planlama_iliskileri ?? []) {
      if (Array.isArray(r.ogretmenler)) r.ogretmenler = r.ogretmenler.map((x: string) => (sameTeacher(x, oldName) ? newName : x));
    }
    return;
  }
  if (kind === 'dersler') {
    for (const a of d.atamalar ?? []) {
      if (a.subject === oldName) a.subject = newName;
      if (a.ders === oldName) a.ders = newName;
    }
    for (const list of [d.grid_placements ?? [], d.auto_schedule_results ?? []]) {
      for (const p of list) if (p.subject_name === oldName || p.subject === oldName) { p.subject_name = newName; p.subject = newName; }
    }
    for (const r of d.planlama_iliskileri ?? []) {
      if (Array.isArray(r.dersler)) r.dersler = r.dersler.map((x: string) => (x === oldName ? newName : x));
      if (Array.isArray(r.gruplar)) r.gruplar = r.gruplar.map((g: any) => (Array.isArray(g) ? g.map((x: string) => (x === oldName ? newName : x)) : g));
    }
    return;
  }
  if (kind === 'siniflar') {
    for (const a of d.atamalar ?? []) {
      if (a.class === oldName) a.class = newName;
      if (a.sinif === oldName) a.sinif = newName;
      if (Array.isArray(a.combined_classes)) {
        a.combined_classes = a.combined_classes.map((c: string) => (c === oldName ? newName : c));
        if (a.is_combined && a.combined_classes.length > 1) { a.class = a.combined_classes.join(' + '); if ('sinif' in a) a.sinif = a.class; }
      }
    }
    for (const list of [d.grid_placements ?? [], d.auto_schedule_results ?? []]) {
      for (const p of list) {
        if (p.class_name === oldName || p.class === oldName) { p.class_name = newName; p.class = newName; }
        if (Array.isArray(p.combined_classes)) p.combined_classes = p.combined_classes.map((c: string) => (c === oldName ? newName : c));
      }
    }
    for (const t of d.ogretmenler ?? []) if (String(t.sinif_ogretmeni ?? '').trim() === oldName) t.sinif_ogretmeni = newName;
    for (const key of ['kisitlamalar']) {
      const m = d[key];
      if (m && typeof m === 'object' && oldName in m) { m[newName] = m[oldName]; delete m[oldName]; }
    }
    for (const r of d.planlama_iliskileri ?? []) {
      if (Array.isArray(r.siniflar)) r.siniflar = r.siniflar.map((x: string) => (x === oldName ? newName : x));
    }
  }
}

/** master_data_dialog._act_delete — kaydı ve bağlı bütün atama/programı siler. */
export function deleteEntity(d: any, kind: Kind, name: string) {
  const fmt = formatTrName(name);
  d[kind] = (d[kind] ?? []).filter((x: any) => formatTrName(x.ad ?? '') !== fmt && x.kisa !== name);
  const dropYerlesim = (pred: (info: any) => boolean) => {
    const y = d.yerlesim;
    if (y && typeof y === 'object' && !Array.isArray(y)) for (const k of Object.keys(y)) if (y[k] && typeof y[k] === 'object' && pred(y[k])) delete y[k];
  };
  if (kind === 'ogretmenler') {
    const isT = (v: unknown) => sameTeacher(v, name) || formatTrName(v) === fmt;
    d.atamalar = (d.atamalar ?? []).filter((a: any) => !isT(a.teacher ?? ''));
    d.grid_placements = (d.grid_placements ?? []).filter((p: any) => !isT(p.teacher_name || p.teacher || ''));
    dropYerlesim((i) => isT(i.teacher_name || i.teacher || ''));
    if ('auto_schedule_results' in d) d.auto_schedule_results = (d.auto_schedule_results ?? []).filter((p: any) => !isT(p.teacher_name || p.teacher || ''));
    for (const s of d.siniflar ?? []) if (isT(String(s.sinif_ogretmeni ?? ''))) s.sinif_ogretmeni = '';
    if (d.kisitlamalar) { delete d.kisitlamalar[name]; delete d.kisitlamalar[fmt]; }
  } else if (kind === 'dersler') {
    const isS = (v: unknown) => formatTrName(v) === fmt;
    d.atamalar = (d.atamalar ?? []).filter((a: any) => !isS(a.subject ?? ''));
    d.grid_placements = (d.grid_placements ?? []).filter((p: any) => !isS(p.subject_name || p.subject || ''));
    dropYerlesim((i) => isS(i.subject_name || i.subject || ''));
    if ('auto_schedule_results' in d) d.auto_schedule_results = (d.auto_schedule_results ?? []).filter((p: any) => !isS(p.subject_name || p.subject || ''));
  } else if (kind === 'siniflar') {
    const isC = (v: any) => matchesClass(v.class_name || v.class || '', name) || v.class === name
      || (Array.isArray(v.combined_classes) && v.combined_classes.includes(name));
    d.atamalar = (d.atamalar ?? []).filter((a: any) => !isC(a));
    d.grid_placements = (d.grid_placements ?? []).filter((p: any) => !isC(p));
    dropYerlesim(isC);
    if ('auto_schedule_results' in d) d.auto_schedule_results = (d.auto_schedule_results ?? []).filter((p: any) => !isC(p));
    for (const t of d.ogretmenler ?? []) if (String(t.sinif_ogretmeni ?? '').trim().toUpperCase() === name.toUpperCase()) t.sinif_ogretmeni = '';
  }
}

/** master_data_dialog._act_delete_all */
export function deleteAll(d: any, kind: Kind) {
  d[kind] = [];
  if (kind === 'derslikler') {
    for (const a of d.atamalar ?? []) a.room = '';
    for (const p of d.grid_placements ?? []) p.room_name = '';
    const y = d.yerlesim;
    if (y && typeof y === 'object') for (const v of Object.values(y)) if (v && typeof v === 'object') (v as any).room = '';
  } else {
    d.atamalar = [];
    d.grid_placements = [];
    d.yerlesim = {};
    if ('auto_schedule_results' in d) d.auto_schedule_results = [];
  }
}

/** Yeni ya da güncellenen sınıfın sınıf öğretmeni ilişkisini iki yönlü kurar. */
export function linkClassTeacher(d: any, className: string, teacher: string, self: any) {
  const c = className.trim();
  if (teacher.trim()) {
    for (const s of d.siniflar ?? []) if (s !== self && formatTrName(s.sinif_ogretmeni ?? '') === formatTrName(teacher)) s.sinif_ogretmeni = '';
    for (const t of d.ogretmenler ?? []) {
      if (formatTrName(t.ad ?? '') === formatTrName(teacher)) t.sinif_ogretmeni = c;
      else if (String(t.sinif_ogretmeni ?? '').trim().toUpperCase() === c.toUpperCase()) t.sinif_ogretmeni = '';
    }
  } else {
    for (const t of d.ogretmenler ?? []) if (String(t.sinif_ogretmeni ?? '').trim().toUpperCase() === c.toUpperCase()) t.sinif_ogretmeni = '';
  }
}

export function linkTeacherClass(d: any, teacherName: string, className: string, self: any) {
  const t = teacherName.trim();
  if (className.trim()) {
    for (const x of d.ogretmenler ?? []) if (x !== self && String(x.sinif_ogretmeni ?? '').trim().toUpperCase() === className.trim().toUpperCase()) x.sinif_ogretmeni = '';
    for (const s of d.siniflar ?? []) {
      if (String(s.ad ?? '').trim().toUpperCase() === className.trim().toUpperCase()) s.sinif_ogretmeni = t;
      else if (formatTrName(s.sinif_ogretmeni ?? '') === formatTrName(t)) s.sinif_ogretmeni = '';
    }
  } else {
    for (const s of d.siniflar ?? []) if (formatTrName(s.sinif_ogretmeni ?? '') === formatTrName(t)) s.sinif_ogretmeni = '';
  }
}

// ── zaman tablosu (constraint_sync.set_matrix / set_personal) ─────────────
export function setMatrix(d: any, kind: Kind, entity: any, matrix: number[][]) {
  const name = String(entity.ad || entity.name || '').trim();
  if (!name) return;
  const [D, P] = gridDimensions(d);
  const toff: number[][] = [];
  for (let day = 0; day < D; day++) {
    const src = matrix[day];
    const allClosed = Array.isArray(src) && src.length > 0 && src.every((x) => coerceState(x) === CLOSED);
    const row: number[] = [];
    for (let p = 0; p < P; p++) row.push(Array.isArray(src) && p < src.length ? coerceState(src[p]) : (allClosed ? CLOSED : OPEN));
    toff.push(row);
  }
  entity.timeoff = toff;
  const kis = (d.kisitlamalar ??= {});
  const cells: Record<string, number> = {};
  for (let day = 0; day < D; day++) for (let p = 0; p < P; p++) cells[`${day},${p}`] = toff[day][p];
  kis[name] = cells;
  // Aynı ada sahip diğer kayıtlar YALNIZCA aynı grupta eşitlenir.
  for (const other of d[kind] ?? []) {
    if (other === entity || !other || typeof other !== 'object') continue;
    const oAd = String(other.ad || other.name || '').trim();
    if (normTeacher(oAd) === normTeacher(name)) { other.timeoff = toff.map((r) => [...r]); kis[oAd] = cells; }
  }
}

/** constraint_sync.sync_all — bütün birimlerin iki gösterimini (timeoff + kisitlamalar) hizalar. */
export function syncAll(d: any) {
  for (const kind of ['ogretmenler', 'siniflar', 'derslikler'] as Kind[]) {
    for (const e of d[kind] ?? []) {
      if (!e || typeof e !== 'object') continue;
      const name = String(e.ad || e.name || '').trim();
      if (name) setMatrix(d, kind, e, getMatrix(e, name, d));
    }
  }
}

export function setPersonal(d: any, entity: any, grid: boolean[][]) {
  const name = String(entity.ad || entity.name || '').trim();
  if (!name) return;
  const [D, P] = gridDimensions(d);
  const rows: number[][] = [], cells: Record<string, number> = {};
  for (let day = 0; day < D; day++) {
    const row: number[] = [];
    for (let p = 0; p < P; p++) {
      const on = !!grid[day]?.[p];
      row.push(on ? 1 : 0);
      if (on) cells[`${day},${p}`] = 1;
    }
    rows.push(row);
  }
  entity.personal_off = rows;
  const store = (d.kisitlamalar_kisisel ??= {});
  if (Object.keys(cells).length) store[name] = cells; else delete store[name];
}

/** Atamalardan saat toplamları (master_data_dialog._populate_tab_rows). */
export function totalsByField(d: any, field: 'subject' | 'class' | 'teacher'): Map<string, number> {
  const out = new Map<string, number>();
  for (const a of d.atamalar ?? []) {
    const k = field === 'teacher' ? formatTrName(a.teacher ?? '') : field === 'subject' ? formatTrName(a.subject ?? '') : String(a.class ?? '').trim();
    if (!k) continue;
    out.set(k, (out.get(k) ?? 0) + (Number(a.duration) || 1));
  }
  return out;
}

export { matchesClass };

/** edit_forms._matches_teacher — aynı kişi mi (büyük/küçük harf, boşluk, ikinci ad). */
export function matchesTeacherLoose(t1: unknown, t2: unknown): boolean {
  if (!t1 || !t2) return false;
  const n1 = normTeacher(t1), n2 = normTeacher(t2);
  if (n1 === n2 || formatTrName(t1) === formatTrName(t2)) return true;
  const p1 = new Set(n1.split(' ').filter(Boolean)), p2 = new Set(n2.split(' ').filter(Boolean));
  if (!p1.size || !p2.size) return false;
  const sub = (a: Set<string>, b: Set<string>) => [...a].every((x) => b.has(x));
  return sub(p1, p2) || sub(p2, p1);
}

/** Atamalarda karşılığı kalmayan yerleşimleri siler (yalnızca scope'a uyanlara bakar).
 *  Birleşik dersin her sınıftaki yerleşimi, atamanın sınıflarından biriyle eşleşince yaşar. */
export function pruneOrphanPlacements(d: any, scope: (p: any) => boolean) {
  const bySubject = new Map<string, any[]>();
  for (const a of d.atamalar ?? []) {
    if (!a || typeof a !== 'object') continue;
    const s = formatTrName(subjectOf(a));
    (bySubject.get(s) ?? bySubject.set(s, []).get(s)!).push(a);
  }
  const alive = (p: any) => {
    const list = bySubject.get(formatTrName(p.subject_name || p.subject || ''));
    if (!list) return false;
    const t = String(p.teacher_name || p.teacher || '');
    const c = String(p.class_name || p.class || '').trim();
    return list.some((a) => {
      const at = teacherOf(a);
      const sameT = formatTrName(at) === formatTrName(t)
        || at.split(',').some((x: string) => formatTrName(x.trim()) === formatTrName(t));
      if (!sameT) return false;
      return classesOf(a).some((x) => formatTrName(x) === formatTrName(c) || matchesClass(x, c) || matchesClass(c, x))
        || formatTrName(classNameOf(a)) === formatTrName(c);
    });
  };
  const keep = (p: any) => !p || typeof p !== 'object' || !scope(p) || alive(p);
  if (Array.isArray(d.grid_placements)) d.grid_placements = d.grid_placements.filter(keep);
  if (Array.isArray(d.auto_schedule_results)) d.auto_schedule_results = d.auto_schedule_results.filter(keep);
  const y = d.yerlesim;
  if (y && typeof y === 'object' && !Array.isArray(y)) for (const k of Object.keys(y)) if (!keep(y[k])) delete y[k];
}

/** "2 + 1" → { type: "2+1", dur: 3 }; geçersiz/0 → { type: "", dur: 0 } (edit_forms satır içi saat). */
export function canonicalHours(raw: unknown): { type: string; dur: number } {
  const t = String(raw ?? '').trim();
  const parts = t.split('+').map((p) => p.trim()).filter((p) => /^\d+$/.test(p)).map(Number);
  const dur = parts.length ? parts.reduce((a, b) => a + b, 0) : (/^\d+$/.test(t) ? Number(t) : 0);
  if (dur <= 0) return { type: '', dur: 0 };
  return { type: parts.length > 1 ? parts.join('+') : String(dur), dur };
}

/** "2+1" → 3, "4" → 4, aksi hâlde fallback (edit_forms'daki tekrar eden hesap). */
export function typeDuration(t: unknown, fallback = 2): number {
  const s = String(t ?? '').trim();
  if (s.includes('+')) {
    const parts = s.split('+').map((p) => p.trim()).filter((p) => /^\d+$/.test(p)).map(Number);
    return parts.length ? parts.reduce((a, b) => a + b, 0) : fallback;
  }
  return /^\d+$/.test(s) ? Number(s) : fallback;
}
