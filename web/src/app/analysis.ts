// lesson_hours.py (rows/per_class/per_teacher/audit) ve advisor.py karşılıkları:
// İstatistik, Danışman ve Son Kontrol ekranlarının okuduğu hesaplar.
import { classNameOf, classesOf, hours as hoursOf, subjectOf, teacherOf, typeStr } from '../engine/data.ts';
import { dunyaKur, kilitCatismalari } from '../engine/locks.ts';
import { hazirla } from '../engine/prep.ts';

const norm = (v: unknown) => String(v ?? '').split(/\s+/).filter(Boolean).join(' ').trim();
const int = (v: unknown, def = 0) => { const n = Number(String(v ?? '').trim()); return Number.isFinite(n) && String(v ?? '').trim() !== '' ? Math.trunc(n) : def; };
const HOUR_KEYS = ['duration', 'saat', 'ders_sayisi', 'toplam_saat', 'hours'];

export interface LessonRow { teacher: string; subject: string; cls: string; classes: string[]; hours: number; type: string; isCombined: boolean; raw: any }

export function lessonRows(d: any): LessonRow[] {
  const out: LessonRow[] = [];
  for (const a of d?.atamalar ?? []) {
    if (!a || typeof a !== 'object' || Array.isArray(a)) continue;
    const h = hoursOf(a);
    if (h <= 0) continue;
    const cl = classesOf(a);
    out.push({ teacher: teacherOf(a), subject: subjectOf(a), cls: classNameOf(a), classes: cl, hours: h, type: typeStr(a), isCombined: !!a.is_combined || cl.length > 1, raw: a });
  }
  return out;
}

export function perClass(d: any): Map<string, number> {
  const m = new Map<string, number>();
  for (const r of lessonRows(d)) for (const c of r.classes) m.set(c, (m.get(c) ?? 0) + r.hours);
  return m;
}

export function perTeacher(d: any): Map<string, number> {
  const m = new Map<string, number>();
  for (const r of lessonRows(d)) if (r.teacher) m.set(r.teacher, (m.get(r.teacher) ?? 0) + r.hours);
  return m;
}

export function audit(d: any) {
  const knownT = new Set((d.ogretmenler ?? []).filter((t: any) => t && typeof t === 'object').map((t: any) => String(t.ad || t.name || '').trim()).filter(Boolean));
  const knownC = new Set((d.siniflar ?? []).filter((c: any) => c && typeof c === 'object').map((c: any) => String(c.ad || c.name || '').trim()).filter(Boolean));
  const rws = lessonRows(d);
  const classTotal = rws.reduce((s, r) => s + r.hours * r.classes.length, 0);
  const teacherTotal = rws.filter((r) => r.teacher).reduce((s, r) => s + r.hours, 0);
  const lessonTotal = rws.reduce((s, r) => s + r.hours, 0);
  const unknownTeachers: [string, string, string, number][] = [], unknownClasses: [string, string, string, number][] = [];
  const stale: [string, string, string, Record<string, unknown>][] = [];
  for (const r of rws) {
    if (r.teacher && knownT.size && !knownT.has(r.teacher)) unknownTeachers.push([r.cls, r.subject, r.teacher, r.hours]);
    for (const c of r.classes) if (knownC.size && !knownC.has(c)) unknownClasses.push([c, r.subject, r.teacher, r.hours]);
    const seen = new Set<number>();
    for (const k of HOUR_KEYS) if (k in r.raw) { const n = Number(String(r.raw[k]).trim()); if (Number.isFinite(n) && String(r.raw[k]).trim() !== '') seen.add(Math.trunc(n)); }
    if (seen.size > 1) stale.push([r.cls, r.subject, r.teacher, Object.fromEntries(HOUR_KEYS.filter((k) => k in r.raw).map((k) => [k, r.raw[k]]))]);
  }
  return {
    classTotal, teacherTotal, lessonTotal, combinedExtra: classTotal - lessonTotal, unknownTeachers, unknownClasses, stale,
    consistent: !unknownTeachers.length && !unknownClasses.length && !stale.length && teacherTotal === lessonTotal,
  };
}

// ── advisor.py ─────────────────────────────────────────────────────────────
function advDims(d: any): { days: string[]; periods: number } {
  const st = d.settings ?? {};
  let days: string[] = st.days;
  if (!Array.isArray(days) || !days.length) {
    const count = int(st.day_count ?? d.gun_sayisi ?? 5, 5);
    days = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar'].slice(0, count);
  }
  return { days: [...days], periods: int(st.periods ?? d.ders_saati ?? 8, 8) || 8 };
}

function openCells(grid: any, days: number, periods: number): Set<string> | null {
  if (!Array.isArray(grid) || !grid.length) return null;
  const out = new Set<string>();
  for (let dd = 0; dd < Math.min(days, grid.length); dd++) {
    const row = Array.isArray(grid[dd]) ? grid[dd] : [];
    for (let p = 0; p < Math.min(periods, row.length); p++) if (row[p] === 2) out.add(`${dd},${p}`);
  }
  return out;
}

export function openSlotsPerClass(d: any): Map<string, number> {
  const { days, periods } = advDims(d);
  const out = new Map<string, number>();
  for (const c of d.siniflar ?? []) {
    if (!c || typeof c !== 'object') continue;
    const name = norm(c.ad || c.name);
    if (!name) continue;
    const cells = openCells(c.timeoff, days.length, periods);
    out.set(name, cells ? cells.size : days.length * periods);
  }
  return out;
}

export function teacherCapacity(d: any): Map<string, number> {
  const { days, periods } = advDims(d);
  const all = () => { const s = new Set<string>(); for (let x = 0; x < days.length; x++) for (let p = 0; p < periods; p++) s.add(`${x},${p}`); return s; };
  const classOpen = new Map<string, Set<string>>();
  for (const c of d.siniflar ?? []) {
    if (!c || typeof c !== 'object') continue;
    classOpen.set(norm(c.ad || c.name), openCells(c.timeoff, days.length, periods) ?? all());
  }
  const tClasses = new Map<string, Set<string>>();
  for (const a of d.atamalar ?? []) {
    if (!a || typeof a !== 'object') continue;
    const t = norm(a.teacher || a.ogretmen), c = norm(a.class || a.sinif);
    if (t && c) (tClasses.get(t) ?? tClasses.set(t, new Set()).get(t)!).add(c);
  }
  const ownOff = new Map<string, any>();
  for (const t of d.ogretmenler ?? []) if (t && typeof t === 'object') ownOff.set(norm(t.ad || t.name), t.timeoff);
  const out = new Map<string, number>();
  for (const [teacher, classes] of tClasses) {
    let reach = new Set<string>();
    for (const cls of classes) for (const s of classOpen.get(cls) ?? []) reach.add(s);
    const personal = openCells(ownOff.get(teacher), days.length, periods);
    if (personal) reach = new Set([...reach].filter((s) => personal.has(s)));
    out.set(teacher, reach.size);
  }
  return out;
}

export function placedPerClass(d: any): Map<string, number> {
  const out = new Map<string, number>();
  for (const p of d.grid_placements ?? []) {
    if (!p || typeof p !== 'object') continue;
    const c = norm(p.class_name || p.class);
    if (c) out.set(c, (out.get(c) ?? 0) + Math.max(1, int(p.duration ?? 1, 1)));
  }
  return out;
}

export function teacherClashes(d: any): [string, number, number, string[]][] {
  const slots = new Map<string, any[]>();
  for (const p of d.grid_placements ?? []) {
    if (!p || typeof p !== 'object') continue;
    const t = norm(p.teacher_name || p.teacher);
    if (!t) continue;
    const day = int(p.day ?? p.col ?? 0), start = int(p.period ?? p.row ?? 0);
    for (let o = 0; o < Math.max(1, int(p.duration ?? 1, 1)); o++) {
      const k = JSON.stringify([t, day, start + o]);
      (slots.get(k) ?? slots.set(k, []).get(k)!).push(p);
    }
  }
  const out: [string, number, number, string[]][] = [];
  for (const [k, items] of [...slots.entries()].sort((a, b) => (a[0] < b[0] ? -1 : 1))) {
    const [t, day, period] = JSON.parse(k);
    const classes = new Set(items.map((i) => norm(i.class_name || i.class)));
    const blocks = new Set(items.map((i, n) => i.block_id || `#${n}${JSON.stringify(i)}`));
    if (items.length > 1 && blocks.size > 1 && classes.size > 1) out.push([t, day, period, [...classes].sort()]);
  }
  return out;
}

export function unknownTeacherPlacements(d: any): [string, string, string][] {
  const allowed = new Set<string>();
  for (const a of d.atamalar ?? []) if (a && typeof a === 'object') allowed.add(JSON.stringify([norm(a.class || a.sinif), norm(a.subject || a.ders), norm(a.teacher || a.ogretmen)]));
  const bad: [string, string, string][] = [];
  for (const p of d.grid_placements ?? []) {
    if (!p || typeof p !== 'object') continue;
    const key: [string, string, string] = [norm(p.class_name || p.class), norm(p.subject_name || p.subject), norm(p.teacher_name || p.teacher)];
    if (key[2] && !allowed.has(JSON.stringify(key))) bad.push(key);
  }
  return bad;
}

export function gapsPerTeacher(d: any): Map<string, number> {
  const { days } = advDims(d);
  const busy = new Map<string, Map<number, Set<number>>>();
  for (const p of d.grid_placements ?? []) {
    if (!p || typeof p !== 'object') continue;
    const t = norm(p.teacher_name || p.teacher);
    if (!t) continue;
    const day = int(p.day ?? p.col ?? 0), start = int(p.period ?? p.row ?? 0);
    const byDay = busy.get(t) ?? busy.set(t, new Map()).get(t)!;
    const set = byDay.get(day) ?? byDay.set(day, new Set()).get(day)!;
    for (let o = 0; o < Math.max(1, int(p.duration ?? 1, 1)); o++) set.add(start + o);
  }
  const out = new Map<string, number>();
  for (const [t, byDay] of busy) {
    let total = 0;
    for (let day = 0; day < days.length; day++) {
      const hs = [...(byDay.get(day) ?? [])].sort((a, b) => a - b);
      if (hs.length > 1) total += (hs[hs.length - 1] - hs[0] + 1) - hs.length;
    }
    if (total) out.set(t, total);
  }
  return out;
}

export type Finding = [severity: 'error' | 'warning' | 'info', title: string, detail: string, action: string];

/** advisor.analyse */
export function analyse(d: any): Finding[] {
  const f: Finding[] = [];
  const { days } = advDims(d);
  const open = openSlotsPerClass(d), demandC = perClass(d), placed = placedPerClass(d), demandT = perTeacher(d), cap = teacherCapacity(d);
  if (!(d.atamalar ?? []).length) {
    return [['error', 'Hiç ders ataması yok', 'Toplu Atama Listesi boş; planlayacak bir şey yok.', "Tanımlama İşlemleri → Toplu Atama Listesi'nden dersleri girin."]];
  }
  const au = audit(d);
  if (au.stale.length) {
    const sample = au.stale.slice(0, 8).map(([c, s, t, v]) => `  • ${c} — ${s} (${t}): ${JSON.stringify(v)}`).join('\n');
    f.push(['error', `${au.stale.length} atamada saat alanları çelişiyor`, `Aynı ders için farklı saat değerleri kayıtlı; ekranlar farklı alanı okuduğunda farklı toplam çıkar:\n\n${sample}`,
      'Bu dersleri sınıf ekranından bir kez kaydedin; kayıt sırasında bütün alanlar tek değere eşitlenir.']);
  }
  if (au.unknownTeachers.length) {
    const sample = au.unknownTeachers.slice(0, 8).map(([c, s, t, h]) => `  • ${c} — ${s}: ${t} (${h} saat)`).join('\n');
    const lost = au.unknownTeachers.reduce((x, r) => x + r[3], 0);
    f.push(['error', `${au.unknownTeachers.length} atama, öğretmen listesinde olmayan bir isme yazılmış — ${lost} saat`,
      `Bu saatler sınıf ekranında görünür ama öğretmen ekranlarında hiçbir öğretmenin üzerinde çıkmaz; iki tarafın toplamı bu yüzden farklıdır:\n\n${sample}`,
      'Öğretmen adını Öğretmenler ekranındaki yazımıyla düzeltin veya öğretmeni tanımlayın.']);
  }
  if (au.unknownClasses.length) {
    const sample = au.unknownClasses.slice(0, 8).map(([c, s, t, h]) => `  • ${c} — ${s} (${t}): ${h} saat`).join('\n');
    f.push(['error', `${au.unknownClasses.length} atama, sınıf listesinde olmayan bir sınıfa yazılmış`, `Bu dersler hiçbir sınıfın çizelgesine düşmez:\n\n${sample}`, 'Sınıf adını Sınıflar ekranındaki yazımıyla düzeltin.']);
  }
  for (const [cls, need] of [...demandC.entries()].sort((a, b) => (a[0] < b[0] ? -1 : 1))) {
    const have = open.get(cls);
    if (have === undefined || need <= have) continue;
    f.push(['error', `${cls}: ${need} saat ders, ${have} açık saat`, `Sınıfa haftada ${need} saat ders atanmış ama Zaman Tablosu'nda yalnızca ${have} saat açık. ${need - have} saat hiçbir şekilde yerleşemez.`,
      `Ya ${cls} için kapalı saatleri açın ya da ${need - have} saat dersi azaltın.`]);
  }
  const over: [string, number, number][] = [];
  for (const [t, need] of [...demandT.entries()].sort((a, b) => (a[0] < b[0] ? -1 : 1))) {
    const have = cap.get(t);
    if (have !== undefined && need > have) over.push([t, need, have]);
  }
  if (over.length) {
    const excess = over.reduce((s, [, n, h]) => s + n - h, 0);
    const lines = [...over].sort((a, b) => (a[2] - a[1]) - (b[2] - b[1])).slice(0, 12).map(([t, n, h]) => `  • ${t}: ${n} saat atanmış, en fazla ${h} saat mümkün (+${n - h})`).join('\n');
    f.push(['error', `${over.length} öğretmen fizik olarak yetişemiyor — ${excess} saat boşta kalacak`,
      `Bir öğretmen aynı anda tek sınıfta olabilir. Sınıflarının açık olduğu saat sayısı bu öğretmenlerin ders yüküne yetmiyor:\n\n${lines}\n\nBu ${excess} saat, planlayıcı ne yaparsa yapsın yerleşemez; çizelgenin dolabileceği üst sınır bu kadar azalır.`,
      'Bu öğretmenlerin bazı derslerini başka bir öğretmene devredin veya sınıfların kapalı saatlerini açın.']);
  }
  for (const [cls, have] of [...open.entries()].sort((a, b) => (a[0] < b[0] ? -1 : 1))) {
    const got = placed.get(cls) ?? 0, need = demandC.get(cls) ?? 0;
    if (got < Math.min(have, need)) {
      f.push(['warning', `${cls}: ${got}/${Math.min(have, need)} saat yerleşti`, `${Math.min(have, need) - got} saat açıkta. Sınıfın ${have} açık saati, ${need} saat dersi var.`,
        'Yerleşmeyen dersler alttaki listede; oradan elle sürükleyebilir veya öğretmen devrederek çözebilirsiniz.']);
    }
  }
  const clashes = teacherClashes(d);
  if (clashes.length) {
    const sample = clashes.slice(0, 10).map(([t, dd, p, cs]) => `  • ${t} — ${dd < days.length ? days[dd] : dd + 1}. gün ${p + 1}. saat: ${cs.join(', ')}`).join('\n');
    f.push(['error', `${clashes.length} öğretmen çakışması`, `Aynı öğretmen aynı saatte birden fazla sınıfta görünüyor:\n\n${sample}`, 'Çakışan derslerden birini başka bir saate taşıyın.']);
  }
  const unknown = unknownTeacherPlacements(d);
  if (unknown.length) {
    const sample = unknown.slice(0, 10).map(([c, s, t]) => `  • ${c} — ${s}: ${t}`).join('\n');
    f.push(['error', `${unknown.length} derste atanmamış öğretmen`, `Gridde, atama listesinde olmayan öğretmen–ders eşleşmeleri var:\n\n${sample}`,
      'Planlama / Yerleştirme → Tabloyu Temizle sonrası yeniden plan oluşturun, veya bu dersleri sağ tıkla düzeltin.']);
  }
  const gaps = gapsPerTeacher(d);
  if (gaps.size) {
    const worst = [...gaps.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
    const total = [...gaps.values()].reduce((a, b) => a + b, 0);
    f.push(['warning', `Öğretmen boşlukları: toplam ${total} saat`, 'Gün içinde iki dersin arasında kalan boş saatler:\n\n' + worst.map(([t, n]) => `  • ${t}: ${n} boş saat`).join('\n'),
      'İyileştirme Uygula ile boşluklar azaltılmaya çalışılır.']);
  }
  const loose = d.loose_unplaced_cards ?? [];
  if (loose.length) {
    f.push(['info', `${loose.length} ders alt listede bekliyor`, 'Bu dersler yerleştirilemedi ve silinmedi; alttaki listede duruyorlar.',
      'Karta çift tıklayıp neden yerleşemediğini görebilir, sürükleyerek elle yerleştirebilirsiniz.']);
  }
  if (!f.length) {
    const totalOpen = [...open.values()].reduce((a, b) => a + b, 0), totalPlaced = [...placed.values()].reduce((a, b) => a + b, 0);
    f.push(['info', 'Sorun bulunamadı', `${totalPlaced}/${totalOpen} saat dolu, çakışma yok, atanmamış öğretmen yok.`, '']);
  }
  const order = { error: 0, warning: 1, info: 2 };
  return f.sort((a, b) => order[a[0]] - order[b[0]]);
}

// ── Son Kontrol: çizelgedeki her dersi motorun doğrulayıcısından geçirir ──
export interface Violation { severity: 'Yüksek' | 'Normal' | 'Düşük'; desc: string; affected: string }

/** Yerleşimleri kilitli say, motorun kilit çatışması denetimiyle sına (kapalı saat,
 *  öğretmen/sınıf çakışması, planlama ilişkileri). Motor kilitlere nasıl bakıyorsa öyle. */
export function engineViolations(d: any): { items: Violation[]; error?: string } {
  const items: Violation[] = [];
  if (!(d.grid_placements ?? []).length || !(d.atamalar ?? []).length) return { items };
  try {
    const copy = structuredClone(d);
    for (const p of copy.grid_placements ?? []) if (p && typeof p === 'object') p.locked = true;
    const pr = hazirla(copy, null);
    const [w, rules, report, kilitler] = dunyaKur(pr.data, pr.D, pr.P, pr.engel, pr.selected, pr.data.planlama_iliskileri ?? []);
    if (report.errors.length) return { items, error: 'Planlama ilişkileri okunamadı: ' + report.errors.join('; ') };
    for (const c of kilitCatismalari(w, rules, kilitler, pr.data, true)) {
      items.push({ severity: 'Yüksek', desc: c.neden, affected: c.mesaj.split(' — ')[0] + ' — ' + (c.mesaj.split(' — ')[1] ?? '').split(':')[0] });
    }
  } catch (e: any) {
    return { items, error: String(e?.message ?? e) };
  }
  return { items };
}
