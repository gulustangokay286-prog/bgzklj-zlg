// auto_scheduler.check_feasibility + constraint_sync.candidate_store +
// dialogs/preflight_dialog._fmt_report karşılıkları: "bu ayarla çizelge dolar mı?"
// Kurumlar bağımsız çalışır (masaüstündeki INSTITUTIONS_INDEPENDENT): yalnızca bu
// dosyanın zaman tabloları okunur.
import { CLOSED, gridDimensions, getMatrix, hours as hoursOf } from '../engine/data.ts';
import { matchesClass, normTeacher } from '../engine/norm.ts';
import { dims } from './model.ts';
import { formatTrName, setMatrix, setPersonal } from './datastore.ts';

export interface Feasibility {
  ok: boolean;
  classes: number;
  open_hours_per_class: number;
  total_cells: number;
  total_demand: number;
  max_fillable: number;
  teachers_with_lessons: number;
  idle_teachers: string[];
  understaffed_slots: { day: number; period: number; needed: number; available: number; shortfall: number }[];
  overloaded_teachers: { teacher: string; assigned: number; available: number; shortfall: number }[];
}

/** auto_scheduler.parse_distribution_parts */
export function parseDistributionParts(typeStr: unknown, total = 0): number[] {
  const t = String(typeStr ?? '').trim();
  const parts: number[] = [];
  if (t.includes('+')) {
    for (const p of t.split('+').map((x) => x.trim()).filter((x) => /^\d+$/.test(x))) if (Number(p) > 0) parts.push(Number(p));
  } else if (/^\d+$/.test(t) && Number(t) > 0) {
    let rem = Number(t);
    while (rem > 0) { const b = Math.min(2, rem); parts.push(b); rem -= b; }
  }
  if (!parts.length && total > 0) {
    let rem = total;
    while (rem > 0) { const b = Math.min(2, rem); parts.push(b); rem -= b; }
  }
  return parts.length ? parts : (total > 0 ? [total] : [2]);
}

function closedSlots(entity: any, name: string, d: any): Set<string> {
  const m = getMatrix(entity, name, d);
  const out = new Set<string>();
  for (let day = 0; day < m.length; day++) for (let p = 0; p < m[day].length; p++) if (m[day][p] === CLOSED) out.add(`${day},${p}`);
  return out;
}

export function checkFeasibility(d: any): Feasibility {
  const [D, P] = gridDimensions(d);
  const blockedByClass = new Map<string, Set<string>>();
  for (const c of d.siniflar ?? []) {
    if (!c || typeof c !== 'object') continue;
    const n = String(c.ad || c.name || '').trim();
    if (n) blockedByClass.set(n, closedSlots(c, n, d));
  }
  const teacherOff = new Map<string, Set<string>>();
  for (const t of d.ogretmenler ?? []) {
    if (!t || typeof t !== 'object') continue;
    const n = String(t.ad || t.name || '').trim();
    if (!n) continue;
    const key = normTeacher(n);
    const s = teacherOff.get(key) ?? new Set<string>();
    for (const x of closedSlots(t, n, d)) s.add(x);
    teacherOff.set(key, s);
  }
  const classes = (d.siniflar ?? []).filter((c: any) => c && typeof c === 'object').map((c: any) => String(c.ad || c.name || '').trim()).filter(Boolean) as string[];
  const openByClass = new Map<string, Set<string>>();
  for (const cn of classes) {
    const shut = blockedByClass.get(cn) ?? new Set();
    const open = new Set<string>();
    for (let day = 0; day < D; day++) for (let p = 0; p < P; p++) if (!shut.has(`${day},${p}`)) open.add(`${day},${p}`);
    openByClass.set(cn, open);
  }
  let totalCells = 0;
  for (const v of openByClass.values()) totalCells += v.size;

  const load = new Map<string, number>();
  const display = new Map<string, string>();
  for (const a of d.atamalar ?? []) {
    if (!a || typeof a !== 'object') continue;
    const name = formatTrName(a.teacher || a.ogretmen || a.teacher_name || '');
    const tk = normTeacher(name);
    if (!tk) continue;
    if (!display.has(tk)) display.set(tk, name);
    const rawType = String(a.type || a.dagilim || '').trim();
    const hrs = parseDistributionParts(rawType, hoursOf(a) || 2).reduce((x, y) => x + y, 0);
    const rawC = String(a.class || a.sinif || a.class_name || '').trim();
    for (const cn of classes) if (matchesClass(rawC, cn)) load.set(tk, (load.get(tk) ?? 0) + hrs);
  }
  let totalDemand = 0;
  for (const v of load.values()) totalDemand += v;

  const understaffed: Feasibility['understaffed_slots'] = [];
  let coverGap = 0;
  for (let day = 0; day < D; day++) {
    for (let p = 0; p < P; p++) {
      const slot = `${day},${p}`;
      let need = 0;
      for (const cn of classes) if (openByClass.get(cn)!.has(slot)) need++;
      if (!need) continue;
      let free = 0;
      for (const tk of load.keys()) if (!(teacherOff.get(tk)?.has(slot))) free++;
      if (free < need) {
        coverGap += need - free;
        understaffed.push({ day, period: p, needed: need, available: free, shortfall: need - free });
      }
    }
  }
  understaffed.sort((a, b) => b.shortfall - a.shortfall);

  const union = new Set<string>();
  for (const v of openByClass.values()) for (const s of v) union.add(s);
  const overloaded: Feasibility['overloaded_teachers'] = [];
  let loadGap = 0;
  for (const [tk, assigned] of load) {
    let cap = 0;
    for (const s of union) if (!(teacherOff.get(tk)?.has(s))) cap++;
    if (assigned > cap) {
      loadGap += assigned - cap;
      overloaded.push({ teacher: display.get(tk) ?? tk, assigned, available: cap, shortfall: assigned - cap });
    }
  }
  overloaded.sort((a, b) => b.shortfall - a.shortfall);

  const maxFillable = Math.min(totalCells, totalDemand, totalDemand - loadGap, totalCells - coverGap);
  const idle: string[] = [];
  for (const t of d.ogretmenler ?? []) {
    if (!t || typeof t !== 'object') continue;
    const n = String(t.ad || t.name || '').trim();
    if (n && !load.has(normTeacher(n))) idle.push(n);
  }
  return {
    ok: maxFillable >= Math.min(totalCells, totalDemand),
    classes: classes.length,
    open_hours_per_class: classes.length ? openByClass.get(classes[0])!.size : 0,
    total_cells: totalCells,
    total_demand: totalDemand,
    max_fillable: maxFillable,
    teachers_with_lessons: load.size,
    idle_teachers: idle,
    understaffed_slots: understaffed,
    overloaded_teachers: overloaded,
  };
}

/** constraint_sync.candidate_store — kaydedilmemiş bir zaman tablosunun uygulanmış kopyası. */
export function candidateStore(d: any, kind: 'siniflar' | 'ogretmenler' | 'derslikler', entityIndex: number, matrix: number[][], personal: boolean[][] | null): any {
  const probe: any = {
    settings: d.settings ?? {},
    atamalar: d.atamalar ?? [],
    siniflar: structuredClone(d.siniflar ?? []),
    ogretmenler: structuredClone(d.ogretmenler ?? []),
    derslikler: structuredClone(d.derslikler ?? []),
    kisitlamalar: structuredClone(d.kisitlamalar ?? {}),
    kisitlamalar_kisisel: structuredClone(d.kisitlamalar_kisisel ?? {}),
    gun_sayisi: d.gun_sayisi,
    ders_saati: d.ders_saati,
  };
  const target = probe[kind][entityIndex];
  if (!target) return probe;
  if (personal) setPersonal(probe, target, personal);
  setMatrix(probe, kind, target, matrix);
  if (personal) setPersonal(probe, target, personal);
  return probe;
}

export type ReportLine = { kind: 'baslik' | 'satir' | 'ara' | 'madde' | 'ipucu'; text: string };

/** dialogs/preflight_dialog._fmt_report */
export function formatReport(r: Feasibility, d: any): ReportLine[] {
  const days = dims(d).days;
  const out: ReportLine[] = [];
  const gap = Math.max(0, Math.min(r.total_cells, r.total_demand) - r.max_fillable);
  out.push({ kind: 'baslik', text: `${gap} ders saati bu ayarlarla HİÇBİR ŞEKİLDE yerleşemez` });
  out.push({ kind: 'satir', text: `${r.classes} sınıf × ${r.open_hours_per_class} açık saat = ${r.total_cells} hücre` });
  out.push({ kind: 'satir', text: `Atanan ders: ${r.total_demand} saat  •  En fazla dolabilecek: ${r.max_fillable} saat` });
  if (r.overloaded_teachers.length) {
    out.push({ kind: 'ara', text: 'Müsait olduğundan fazla ders atanmış öğretmenler' });
    for (const o of r.overloaded_teachers.slice(0, 8)) out.push({ kind: 'madde', text: `${o.teacher}: ${o.assigned} saat atanmış, ${o.available} saat müsait → ${o.shortfall} saat sığmıyor` });
    if (r.overloaded_teachers.length > 8) out.push({ kind: 'madde', text: `... ve ${r.overloaded_teachers.length - 8} öğretmen daha` });
  }
  if (r.understaffed_slots.length) {
    out.push({ kind: 'ara', text: 'O saatte derse girecek öğretmen yetmiyor' });
    for (const u of r.understaffed_slots.slice(0, 6)) {
      const dn = u.day < days.length ? days[u.day] : `${u.day + 1}. gün`;
      out.push({ kind: 'madde', text: `${dn} ${u.period + 1}. saat: ${u.available} müsait / ${u.needed} gerekli → ${u.shortfall} sınıf boş kalır` });
    }
    if (r.understaffed_slots.length > 6) out.push({ kind: 'madde', text: `... ve ${r.understaffed_slots.length - 6} saat daha` });
  }
  if (r.idle_teachers.length) {
    out.push({ kind: 'ara', text: 'Hiç dersi olmayan öğretmenler' });
    out.push({ kind: 'madde', text: r.idle_teachers.slice(0, 8).join(', ') + (r.idle_teachers.length > 8 ? ' ...' : '') });
    out.push({ kind: 'ipucu', text: 'Yükün bir kısmını onlara aktarmak boşlukları kapatır.' });
  }
  return out;
}
