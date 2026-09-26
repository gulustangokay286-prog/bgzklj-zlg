// dialogs/print_preview.py raporları — QPainter yerine A4 HTML sayfaları.
// Sayfa ölçüsü masaüstünün sanal tuvaliyle aynı oranda: yatay 1123×794, dikey 794×1123.
import type { ReactNode } from 'react';
import { hours as hoursOf, typeStr } from '../../engine/data.ts';
import { matchesClass } from '../../engine/norm.ts';
import { matchesTeacherLoose } from '../datastore.ts';

export const REPORT_MODES = [
  'Toplu Çarşaf Liste : Sınıflar',
  'Toplu Çarşaf Liste : Öğretmenler',
  'Tablo Olarak : Dersler',
  "[BİREBİR] Tüm Sınıflar (Yatay Sayfada 6'lı Çizelge)",
  "[BİREBİR] Tüm Öğretmenler (Yatay Sayfada 6'lı Çizelge)",
  'Sınıf Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)',
  'Öğretmen Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)',
  'Sınıf Dersleri & Atama Listesi (Liste Formatı)',
  'Tüm Öğretmenlerin Ders Yükü Listesi',
] as const;
export type ReportMode = typeof REPORT_MODES[number];
export const ALL_CLASSES = 'Tüm Sınıflar (Çoklu Sayfa)';
export const ALL_TEACHERS = 'Tüm Öğretmenler (Çoklu Sayfa)';

const ALL_DAYS = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar'];
const SHORT_DAYS = ['Pa', 'Sa', 'Ça', 'Pe', 'Cu', 'Cts', 'Paz'];
const TR_UP: Record<string, string> = { i: 'İ', ı: 'I', ç: 'Ç', ğ: 'Ğ', ö: 'Ö', ş: 'Ş', ü: 'Ü' };
const trUpper = (s: string) => [...String(s)].map((c) => TR_UP[c] ?? c).join('').toUpperCase();
/** print_preview.format_tr_name */
const upperTr = (v: unknown) => String(v ?? '').trim().replace(/i/g, 'İ').replace(/ı/g, 'I').toUpperCase();
const today = (sep = '.') => { const d = new Date(); return [d.getDate(), d.getMonth() + 1, d.getFullYear()].map((x, i) => (i < 2 ? String(x).padStart(2, '0') : String(x))).join(sep); };

export function schoolName(d: any, fallback = 'Özel Öğretim Kurumu') { return d.okul_adi || d.settings?.school_name || fallback; }
export function natKey(s: string): [number, string] { const m = /^(\d+)(.*)$/.exec(String(s).trim()); return m ? [Number(m[1]), m[2]] : [999, String(s)]; }
export const natCmp = (a: string, b: string) => { const x = natKey(a), y = natKey(b); return x[0] - y[0] || (x[1] < y[1] ? -1 : x[1] > y[1] ? 1 : 0); };

function daysOf(d: any): string[] {
  const st = d.settings ?? {};
  const cnt = Number(st.day_count || st.days_count || d.gun_sayisi || 5) || 5;
  return (Array.isArray(st.days) && st.days.length ? st.days : Array.isArray(st.days_list) && st.days_list.length ? st.days_list : ALL_DAYS.slice(0, cnt)).map(String);
}
const periodsOf = (d: any) => Number(d.settings?.periods || 8) || 8;
const shortDays = (d: any) => daysOf(d).map((x) => (ALL_DAYS.includes(x) ? SHORT_DAYS[ALL_DAYS.indexOf(x)] : x.slice(0, 3)));

/** print_preview.get_bell_times */
export function bellTimes(d: any, periods: number, sep = '-'): string[] {
  const st = d.settings ?? {};
  const sched = st.bell_schedule || d.bell_schedule || d.bell_times || st.bell_times || st.zil_saatleri || d.zil_saatleri;
  const out: (string | null)[] = new Array(periods).fill(null);
  if (Array.isArray(sched)) {
    for (let p = 0; p < Math.min(periods, sched.length); p++) {
      const it = sched[p];
      if (it && typeof it === 'object') {
        const s = String(it.start || it.baslangic || '').trim(), e = String(it.end || it.bitis || '').trim();
        if (s && e) out[p] = `${s}${sep}${e}`;
      } else if (typeof it === 'string' && it.includes('-')) out[p] = it.replace(' - ', sep).replace(/ /g, '');
    }
  }
  if (out.some((x) => x === null)) {
    const bells = d.zil_programi || st.zil_saatleri;
    if (bells && typeof bells === 'object' && !Array.isArray(bells)) {
      for (let p = 0; p < periods; p++) {
        if (out[p] !== null) continue;
        const e = bells[String(p)] ?? bells[p] ?? bells[String(p + 1)] ?? bells[p + 1];
        if (e && typeof e === 'object') {
          const s = String(e.start || e.baslangic || '').trim(), en = String(e.end || e.bitis || '').trim();
          if (s && en) out[p] = `${s}${sep}${en}`;
        }
      }
    }
  }
  let ch = 8, cm = 30;
  const first = out.find((x) => x);
  if (first) { const sp = first.split(sep)[0].trim(); if (sp.includes(':')) { const [h, m] = sp.split(':').map(Number); if (Number.isFinite(h) && Number.isFinite(m)) { ch = h; cm = m; } } }
  const res: string[] = [];
  const hm = (t: number) => `${String(Math.floor(t / 60) % 24).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`;
  for (let p = 0; p < periods; p++) {
    const v = out[p];
    if (v) {
      res.push(v);
      const ep = v.split(sep)[1]?.trim();
      if (ep && ep.includes(':')) { const [eh, em] = ep.split(':').map(Number); const t = eh * 60 + em + 10; ch = Math.floor(t / 60) % 24; cm = t % 60; }
    } else {
      const st2 = ch * 60 + cm, en = st2 + 40;
      res.push(`${hm(st2)}${sep}${hm(en)}`);
      const nx = en + 10; ch = Math.floor(nx / 60) % 24; cm = nx % 60;
    }
  }
  return res;
}

/** print_preview.get_subject_badge */
export function subjectBadge(name: string, d: any): string {
  if (!name) return '';
  const s = String(name).trim();
  for (const x of d.dersler ?? []) {
    if (String(x.ad ?? '').trim().toLowerCase() === s.toLowerCase()) {
      const k = String(x.kisa ?? '').trim().toUpperCase();
      if (k && k.length <= 5 && k.toLowerCase() !== String(x.ad ?? '').trim().toLowerCase()) return k;
    }
  }
  const m = /^(.*?)\s*(\d+)$/.exec(s);
  const base = m ? m[1].trim() : s, num = m ? ` ${m[2]}` : '';
  const up = trUpper(base);
  const STD: [string, string][] = [
    ['MATEMATİK', 'MAT'], ['MATEMATIK', 'MAT'], ['MATE', 'MAT'], ['MAT', 'MAT'], ['GEOMETRİ', 'GEOMETRİ'], ['GEOMETRI', 'GEOMETRİ'], ['GEOM', 'GEOMETRİ'], ['GEO', 'GEOMETRİ'],
    ['COĞRAFYA', 'COĞRAFYA'], ['COGRAFYA', 'COĞRAFYA'], ['COĞRAF', 'COĞRAFYA'], ['COĞ', 'COĞRAFYA'], ['COG', 'COĞRAFYA'],
    ['BEDEN EĞİTİMİ VE SPOR', 'BEDEN'], ['BEDEN EĞİTİMİ', 'BEDEN'], ['BEDEN', 'BEDEN'], ['BED', 'BEDEN'], ['FİZİK', 'FİZİK'], ['FIZIK', 'FİZİK'], ['FİZ', 'FİZİK'], ['FIZ', 'FİZİK'],
    ['KİMYA', 'KİMYA'], ['KIMYA', 'KİMYA'], ['KİM', 'KİMYA'], ['KIM', 'KİMYA'], ['BİYOLOJİ', 'BİYO'], ['BIYOLOJI', 'BİYO'], ['BİYO', 'BİYO'], ['BIYO', 'BİYO'], ['BİY', 'BİYO'], ['BIY', 'BİYO'],
    ['TÜRK DİLİ VE EDEBİYATI', 'EDEBİYAT'], ['EDEBİYAT', 'EDEBİYAT'], ['EDEBIYAT', 'EDEBİYAT'], ['TÜRKÇE', 'TÜRKÇE'], ['TURKCE', 'TÜRKÇE'], ['TRK', 'TÜRKÇE'],
    ['TARİH', 'TARİH'], ['TARIH', 'TARİH'], ['TAR', 'TARİH'], ['DİN KÜLTÜRÜ VE AHLAK BİLGİSİ', 'DİN'], ['DİN KÜLTÜRÜ', 'DİN'], ['DİN', 'DİN'], ['DIN', 'DİN'],
    ['FELSEFE', 'FELSEFE'], ['FELS', 'FELSEFE'], ['FEL', 'FELSEFE'], ['İNGİLİZCE', 'İNGİLİZCE'], ['INGILIZCE', 'İNGİLİZCE'], ['İNG', 'İNGİLİZCE'], ['ING', 'İNGİLİZCE'],
    ['ALMANCA', 'ALMANCA'], ['ALM', 'ALMANCA'], ['GÖRSEL SANATLAR', 'GÖRSEL'], ['GÖRSEL', 'GÖRSEL'], ['RESİM', 'GÖRSEL'], ['GÖR', 'GÖRSEL'], ['GOR', 'GÖRSEL'],
    ['MÜZİK', 'MÜZİK'], ['MUZIK', 'MÜZİK'], ['MÜZ', 'MÜZİK'], ['MUZ', 'MÜZİK'], ['REHBERLİK', 'REHBERLİK'], ['REHBERLIK', 'REHBERLİK'], ['REH', 'REHBERLİK'],
    ['PARAGRAF', 'PARAGRAF'], ['PRG', 'PARAGRAF'], ['PAR', 'PARAGRAF'],
  ];
  for (const [k, v] of STD) if (up === k || up.startsWith(k)) return `${v}${num}`.trim();
  const alpha = [...up].filter((c) => /[\p{L}\p{N}]/u.test(c)).join('');
  return `${alpha.slice(0, 5)}${num}`.trim();
}

/** print_preview.format_teacher_display_name */
export function teacherDisplay(t: string, d: any): string {
  if (!t || ['—', 'Atanmadı', 'Atama Yok'].includes(t)) return '—';
  const c = String(t).trim();
  for (const x of d.ogretmenler ?? []) {
    const ad = String(x.ad ?? '').trim(), kisa = String(x.kisa ?? '').trim();
    if (ad.toLowerCase() === c.toLowerCase() || kisa.toLowerCase() === c.toLowerCase() || ad.toLowerCase().startsWith(c.toLowerCase())) {
      if (kisa && kisa.includes('.') && kisa.split('.')[0].length <= 3) return kisa.toUpperCase();
      const parts = ad.split(/\s+/).filter(Boolean);
      if (parts.length >= 2) return `${parts[0][0].toUpperCase()}. ${parts.slice(1).join(' ').toUpperCase()}`;
      if (parts.length === 1) return `${parts[0][0].toUpperCase()}. ${parts[0].toUpperCase()}`;
    }
  }
  if (c.includes('.') && c.split('.').length === 2) { const [p1, p2] = c.split('.'); if (p1.trim().length <= 3) return `${p1.trim().toUpperCase()}. ${p2.trim().toUpperCase()}`; }
  const parts = c.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0][0].toUpperCase()}. ${parts.slice(1).join(' ').toUpperCase()}`;
  if (parts.length === 1) return `${parts[0][0].toUpperCase()}. ${parts[0].toUpperCase()}`;
  return c.toUpperCase();
}

// ── yerleşim okuması (print_preview._get_pseudo_placements) ────────────────
const TR_CLEAN: Record<string, string> = { İ: 'i', I: 'ı', ı: 'i', Ş: 's', ş: 's', Ğ: 'g', ğ: 'g', Ü: 'u', ü: 'u', Ö: 'o', ö: 'o', Ç: 'c', ç: 'c' };
function normClean(s: unknown): string {
  if (!s) return '';
  const raw = String(s).trim().replace(/\s*\((?:ea|say|söz|soz|dil)\)\s*$/i, '');
  return [...raw].map((c) => TR_CLEAN[c] ?? c).join('').toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');
}
interface Slot { subject: string; teacher: string; cls: string; color: string; isCombined: boolean }
type Slots = Map<string, Slot>;

function slotsFor(d: any, target: string, teacherView: boolean): Slots {
  const res: Slots = new Map();
  const tn = normClean(target);
  const P = periodsOf(d);
  let grid: any[] = [...(d.grid_placements ?? [])];
  if (!grid.length && (d.auto_schedule_results ?? []).length) grid = [...d.auto_schedule_results];
  for (const it of grid) {
    if (!it || typeof it !== 'object') continue;
    let day: number, per: number;
    if (it.day !== undefined && it.day !== null && it.period !== undefined && it.period !== null) { day = Number(it.day); per = Number(it.period); }
    else { const col = Number(it.col ?? 0); day = P > 0 ? Math.floor(col / P) : 0; per = P > 0 ? col % P : 0; }
    const dur = Number(it.duration ?? 1) || 1;
    const t = it.teacher_name || it.teacher || '', c = it.class_name || it.class || '', s = it.subject_name || it.subject || '';
    let match = false;
    if (teacherView) match = !!t && (normClean(t) === tn || upperTr(t) === upperTr(target));
    else match = !!c && (normClean(c) === tn || matchesClass(c, target));
    if (!match) continue;
    const comb = !!(it.is_combined || (Array.isArray(it.combined_classes) && it.combined_classes.length > 1));
    for (let o = 0; o < dur; o++) {
      const k = `${day},${per + o}`;
      const old = res.get(k);
      if (teacherView && old) {
        if (comb && c && !old.cls.includes(c)) { old.cls = `${old.cls} + ${c}`; old.isCombined = true; }
        else if (!comb) res.set(k, { subject: s, teacher: t, cls: c, color: it.color || '', isCombined: false });
      } else res.set(k, { subject: s, teacher: t, cls: c, color: it.color || '', isCombined: comb });
    }
  }
  return res;
}

function isClosed(d: any, target: string, teacherView: boolean, day: number, p: number): boolean {
  const list = teacherView ? d.ogretmenler : d.siniflar;
  for (const e of list ?? []) {
    if (String(e.ad || e.name || '').trim() === target) {
      const t = e.timeoff;
      if (Array.isArray(t) && day < t.length && Array.isArray(t[day]) && p < t[day].length && t[day][p] === 0) return true;
      break;
    }
  }
  const k = d.kisitlamalar?.[target];
  if (k && typeof k === 'object' && `${day},${p}` in k) return k[`${day},${p}`] === 0 || k[`${day},${p}`] === false;
  return false;
}

export interface Ctx { data: any; print: boolean }

export function Page({ landscape, children, cls = '' }: { landscape: boolean; children: ReactNode; cls?: string }) {
  return <section className={`pp-page ${landscape ? 'land' : 'port'} ${cls}`}>{children}</section>;
}

// ── 6'lı / tekil çizelge (print_preview._draw_mini_grid) ────────────────────
function MiniGrid({ ctx, target, teacherView, single }: { ctx: Ctx; target: string; teacherView: boolean; single: boolean }) {
  const d = ctx.data;
  const days = shortDays(d), P = periodsOf(d), times = bellTimes(d, P, '-');
  const slots = slotsFor(d, target, teacherView);
  const year = d.settings?.academic_year || '2026 - 2027';
  return (
    <div className={`mg ${single ? 'single' : ''}`}>
      <div className="mg-head"><span>{today('/')}</span><b>{upperTr(target)}</b><span>Ders Planı : {year}</span></div>
      <table className="mg-grid">
        <thead><tr><th />{times.map((t, p) => <th key={p}><b>{p + 1}</b><small>{t}</small></th>)}</tr></thead>
        <tbody>{days.map((dn, di) => {
          const cells: ReactNode[] = [];
          let p = 0;
          while (p < P) {
            const l = slots.get(`${di},${p}`);
            if (l) {
              const other = teacherView ? l.cls : l.teacher;
              let span = 1;
              while (p + span < P) {
                const n = slots.get(`${di},${p + span}`);
                if (!n || n.subject !== l.subject || (teacherView ? n.cls : n.teacher) !== other) break;
                span++;
              }
              let disp = '';
              if (other) {
                if (!teacherView) disp = teacherDisplay(other, d);
                else if (/[,&+]/.test(other)) {
                  const parts = other.replace(/&/g, ',').replace(/\+/g, ',').split(',').map((c) => c.split('(')[0].trim()).filter(Boolean);
                  disp = parts.length <= 2 ? parts.join('+') : `${parts[0]}+${parts[1]}`;
                } else disp = other.trim();
              }
              const badge = subjectBadge(l.subject, d);
              const comb = l.isCombined || l.cls.includes('+') || l.cls.includes(',');
              cells.push(
                <td key={p} colSpan={span} className="mg-cell">
                  {comb && <i className="mg-link" title="Birleşik ders">⛓</i>}
                  <b className={span === 1 && badge.length >= 6 ? 'sm' : ''}>{badge}</b>
                  {disp && <span className={span === 1 && disp.length > 6 ? 'sm' : ''}>{disp}</span>}
                </td>,
              );
              p += span;
            } else {
              const closed = isClosed(d, target, teacherView, di, p);
              cells.push(<td key={p} className={closed ? `mg-closed${ctx.print ? '' : ' x'}` : ''} />);
              p++;
            }
          }
          return <tr key={di}><th>{dn}</th>{cells}</tr>;
        })}</tbody>
      </table>
    </div>
  );
}

function entityList(d: any, teacherView: boolean): string[] {
  if (teacherView) return (d.ogretmenler ?? []).map((t: any) => String(t.ad ?? '')).filter(Boolean).sort();
  return (d.siniflar ?? []).map((c: any) => String(c.ad ?? '')).filter(Boolean).sort(natCmp);
}

export function MultiGridReport({ ctx, target, teacherView }: { ctx: Ctx; target: string; teacherView: boolean }) {
  const items = target && !target.includes('Çoklu Sayfa') ? [target] : entityList(ctx.data, teacherView);
  if (items.length === 1) return <Page landscape><MiniGrid ctx={ctx} target={items[0]} teacherView={teacherView} single /></Page>;
  const pages: string[][] = [];
  for (let i = 0; i < items.length; i += 6) pages.push(items.slice(i, i + 6));
  return <>{pages.map((pg, i) => <Page key={i} landscape cls="six">{pg.map((n) => <MiniGrid key={n} ctx={ctx} target={n} teacherView={teacherView} single={false} />)}</Page>)}</>;
}

export function WeeklyReport({ ctx, target, teacherView }: { ctx: Ctx; target: string; teacherView: boolean }) {
  const items = target && !target.includes('Çoklu Sayfa') && !target.startsWith('Tüm ') ? [target] : entityList(ctx.data, teacherView);
  return <>{items.map((n) => <Page key={n} landscape><MiniGrid ctx={ctx} target={n} teacherView={teacherView} single /></Page>)}</>;
}

// ── Toplu Çarşaf Liste ─────────────────────────────────────────────────────
const ABBR_MAP: [string, string][] = [
  ['MATEMATİK', 'MAT'], ['MATEMATIK', 'MAT'], ['GEOMETRİ', 'GEO'], ['GEOMETRI', 'GEO'], ['COĞRAFYA', 'COĞ'], ['COGRAFYA', 'COĞ'],
  ['BEDEN EĞİTİMİ VE SPOR', 'BED'], ['BEDEN EGITIMI VE SPOR', 'BED'], ['BEDEN EĞİTİMİ', 'BED'], ['BEDEN EGITIMI', 'BED'], ['BEDEN', 'BED'],
  ['TÜRK DİLİ VE EDEBİYATI', 'TDE'], ['TURK DILI VE EDEBIYATI', 'TDE'], ['TÜRKÇE', 'TRK'], ['TURKCE', 'TRK'], ['EDEBİYAT', 'EDE'], ['EDEBIYAT', 'EDE'],
  ['GÖRSEL SANATLAR', 'GÖR'], ['GORSEL SANATLAR', 'GÖR'], ['GÖRSEL', 'GÖR'], ['GORSEL', 'GÖR'], ['RESİM', 'GÖR'], ['İNGİLİZCE', 'İNG'], ['INGILIZCE', 'İNG'], ['ALMANCA', 'ALM'],
  ['DİN KÜLTÜRÜ VE AHLAK BİLGİSİ', 'DİN'], ['DIN KULTURU VE AHLAK BILGISI', 'DİN'], ['DİN KÜLTÜRÜ', 'DİN'], ['DIN KULTURU', 'DİN'], ['FELSEFE', 'FEL'],
  ['REHBERLİK', 'REH'], ['REHBERLIK', 'REH'], ['BİYOLOJİ', 'BİY'], ['BIYOLOJI', 'BİY'], ['KİMYA', 'KİM'], ['KIMYA', 'KİM'], ['FİZİK', 'FİZ'], ['FIZIK', 'FİZ'],
  ['TARİH', 'TAR'], ['TARIH', 'TAR'], ['MÜZİK', 'MÜZ'], ['MUZIK', 'MÜZ'], ['BİLİŞİM', 'BİL'], ['KODLAMA', 'KOD'], ['SEÇMELİ', 'SEÇ'], ['SECMELI', 'SEÇ'], ['PARAGRAF', 'PRG'], ['PROBLEM', 'PRB'],
];
function squeeze(text: string, budget = 5): string {
  const t = String(text ?? '').trim().replace(/\s+/g, ' ');
  if (!t) return '';
  const m = /(\d+)\s*$/.exec(t);
  const num = m ? m[1] : '';
  const body = m ? t.slice(0, m.index).trim() : t;
  const room = Math.max(1, budget - num.length);
  if (body.length <= room) return `${body}${num}`;
  const words = body.split(' ').filter(Boolean);
  if (words.length > 1) { const ini = words.map((w) => w[0]).join('').slice(0, room); if (ini.length >= 2) return `${ini}${num}`; }
  let cand = (body[0] + [...body.slice(1)].filter((ch) => !'AEIİOÖUÜaeııoöuü'.includes(ch)).join('')).slice(0, room);
  if (cand.length < Math.min(3, room)) cand = body.slice(0, room);
  return `${cand}${num}`;
}
function smartAbbr(name: string, d: any): string {
  if (!name) return '';
  const s = String(name).trim();
  let user = '';
  for (const x of d.dersler ?? []) if (String(x.ad ?? '').trim().toLowerCase() === s.toLowerCase() && x.kisa) { user = String(x.kisa).trim(); break; }
  if (user && user.length <= 5) return user;
  const up = trUpper(s);
  for (const [k, v] of ABBR_MAP) if (up === k || up.startsWith(k)) { const m = /\s*(\d+)$/.exec(up); return `${v}${m ? m[1] : ''}`.slice(0, 5); }
  return squeeze(user || up);
}
function teacherShortTr(n: string): string {
  const c = String(n ?? '').trim();
  if (!c || ['boş', 'bos', '-', '—'].includes(c.toLowerCase())) return '';
  const parts = c.split(/\s+/);
  if (parts.length === 1) return upperTr(parts[0]);
  return `${parts.slice(0, -1).map(upperTr).join(' ')} ${trUpper(parts[parts.length - 1][0])}.`;
}

export function CarsafReport({ ctx, target, teacherView }: { ctx: Ctx; target: string; teacherView: boolean }) {
  const d = ctx.data;
  const days = daysOf(d), P = periodsOf(d);
  let items: any[] = teacherView ? [...(d.ogretmenler ?? [])].sort((a, b) => String(a.ad ?? '').localeCompare(String(b.ad ?? ''), 'tr'))
    : [...(d.siniflar ?? [])].sort((a, b) => natCmp(String(a.ad ?? ''), String(b.ad ?? '')));
  if (target && !target.includes('Tümü') && !target.includes('Tüm ')) items = items.filter((x) => x.ad === target);
  if (!items.length) items = [{ ad: 'Örnek 1' }];
  const per = 26, total = Math.max(1, Math.ceil(items.length / per));
  const title = teacherView ? 'Toplu Çarşaf Liste : Öğretmenler' : 'Toplu Çarşaf Liste : Sınıflar';
  const pages: ReactNode[] = [];
  for (let pi = 0; pi < total; pi++) {
    const pageItems = items.slice(pi * per, (pi + 1) * per);
    const used = new Map<string, Set<string>>();
    const rows = pageItems.map((item) => {
      const tname = String(item.ad || item.name || '').trim();
      const disp = teacherView && item.kisa ? item.kisa : !teacherView ? tname.replace(/\s*\([^)]*\)\s*$/, '').trim() : tname;
      const slots = slotsFor(d, tname, teacherView);
      const cells: ReactNode[] = [];
      for (let di = 0; di < days.length; di++) {
        let p = 0;
        while (p < P) {
          const l = slots.get(`${di},${p}`);
          if (!l || ['boş', 'bos', '-', '—', ''].includes(String(l.subject).trim().toLowerCase())) {
            const closed = isClosed(d, tname, teacherView, di, p);
            cells.push(<td key={`${di}-${p}`} className={`${p === 0 ? 'ds ' : ''}${closed ? `cs-closed${ctx.print ? '' : ' x'}` : ''}`} />);
            p++;
            continue;
          }
          let text: string;
          const rawC = String(l.cls || l.teacher || '');
          if (teacherView) {
            if (l.isCombined && /[,&+]/.test(rawC)) {
              const parts = rawC.replace(/&/g, ',').replace(/\+/g, ',').split(',').map((c) => c.split('(')[0].trim().replace(/ /g, '').toUpperCase()).filter(Boolean);
              text = parts.length === 1 ? parts[0] : `${parts[0]}+${parts[1]}`;
            } else text = rawC.split('(')[0].trim().replace(/ /g, '').toUpperCase();
            if (!text) text = smartAbbr(l.subject, d);
          } else {
            text = smartAbbr(l.subject, d);
            const set = used.get(text) ?? used.set(text, new Set()).get(text)!;
            const tv = String(l.teacher ?? '').trim();
            if (tv && !['boş', 'bos', '-', '—'].includes(tv.toLowerCase())) set.add(tv);
          }
          let span = 1;
          const s1 = smartAbbr(l.subject, d), c1 = String(l.cls || l.teacher || '').trim().toUpperCase();
          while (p + span < P) {
            const n = slots.get(`${di},${p + span}`);
            if (!n) break;
            if (teacherView ? (c1 && c1 === String(n.cls || n.teacher || '').trim().toUpperCase()) : (s1 && s1 === smartAbbr(n.subject, d))) span++;
            else break;
          }
          if (span >= 2 && teacherView && l.isCombined && /[,&]/.test(rawC)) {
            const parts = rawC.replace(/&/g, ',').replace(/\+/g, ',').split(',').map((c) => c.split('(')[0].trim().replace(/ /g, '').toUpperCase()).filter(Boolean);
            text = parts.length <= 3 ? parts.join('+') : `${parts[0]}+${parts[1]}+${parts.length - 2}`;
          }
          cells.push(<td key={`${di}-${p}`} colSpan={span} className={`${p === 0 ? 'ds ' : ''}cs-l`}>{text}</td>);
          p += span;
        }
      }
      return <tr key={tname}><th>{disp}</th>{cells}</tr>;
    });
    let legend: [string, string][] = [];
    if (!teacherView) {
      for (const item of pageItems) {
        const cn = String(item.ad || item.name || '').trim(), cnn = normClean(cn);
        for (const a of d.atamalar ?? []) {
          const ac = String(a.class || a.sinif || '').trim();
          if (normClean(ac) !== cnn && !matchesClass(ac, cn)) continue;
          const s = a.subject || a.ders || '', t = a.teacher || a.ogretmen || '';
          if (!s) continue;
          const ab = smartAbbr(s, d);
          const set = used.get(ab) ?? used.set(ab, new Set()).get(ab)!;
          if (t && String(t).trim() && !['boş', 'bos', '-', '—'].includes(String(t).trim().toLowerCase())) set.add(String(t).trim());
        }
      }
      if (!used.size) for (const x of d.dersler ?? []) { const n = String(x.ad ?? '').trim(); if (n) { const ab = smartAbbr(n, d); if (!used.has(ab)) used.set(ab, new Set()); } }
      legend = [...used.keys()].sort().map((ab) => {
        const shorts: string[] = [];
        for (const t of [...used.get(ab)!].sort()) { const st = teacherShortTr(t); if (st && !shorts.includes(st)) shorts.push(st); }
        return [ab, shorts.join(', ')];
      });
    }
    pages.push(
      <Page key={pi} landscape cls="carsaf">
        <div className="cs-head"><b>{schoolName(d, 'Okul Adı')} - {title}</b><span>Tarih: {today()}  |  Sayfa: {pi + 1}/{total}</span></div>
        <table className="cs-grid">
          <thead>
            <tr><th rowSpan={2}>{teacherView ? 'Öğretmen' : 'Sınıf'}</th>{days.map((dn) => <th key={dn} colSpan={P} className="ds">{dn}</th>)}</tr>
            <tr>{days.map((dn) => Array.from({ length: P }, (_, p) => <th key={`${dn}${p}`} className={p === 0 ? 'ds' : ''}>{p + 1}</th>))}</tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
        {!teacherView && legend.length > 0 && (
          <div className="cs-legend"><b>Dersler ve Öğretmenler:</b>
            <div className="cs-leg-grid">{legend.map(([ab, t]) => <div key={ab}><b>• {ab}{t ? ': ' : ''}</b>{t}</div>)}</div>
          </div>
        )}
        {!teacherView && <div className="pp-foot"><span>Ders Planı Oluşturuldu: {today()}</span><span>Chenkron Ders Planlama</span></div>}
      </Page>,
    );
  }
  return <>{pages}</>;
}

// ── Tablo Olarak : Dersler ─────────────────────────────────────────────────
export function LessonsTableReport({ ctx }: { ctx: Ctx }) {
  const d = ctx.data;
  let dersler: any[] = d.dersler ?? [];
  if (!dersler.length) dersler = [{ ad: 'MATEMATİK', kisa: 'MAT' }];
  const days = shortDays(d), P = periodsOf(d), times = bellTimes(d, P, ' - ');
  return <>{dersler.map((ders, i) => {
    const sname = String(ders.ad ?? '');
    const title = ders.kisa || subjectBadge(sname, d);
    const map = new Map<string, [string, string][]>();
    for (const it of d.grid_placements ?? []) {
      if (it.subject_name !== sname && it.subject !== sname) continue;
      const r = Number(it.period ?? it.row ?? 0), c = Number(it.day ?? it.col ?? 0), dur = Number(it.duration ?? 1) || 1;
      for (let o = 0; o < dur; o++) { const k = `${c},${r + o}`; (map.get(k) ?? map.set(k, []).get(k)!).push([it.class_name || it.class || '', it.teacher_name || it.teacher || '']); }
    }
    return (
      <Page key={i} landscape cls="lt">
        <div className="lt-title">{title}</div>
        <div className="lt-school">{schoolName(d, 'Okul Adı')}</div>
        <table className="lt-grid">
          <thead><tr><th />{times.map((t, p) => <th key={p}><b>{p + 1}</b><small>{t}</small></th>)}</tr></thead>
          <tbody>{days.map((dn, di) => (
            <tr key={di}><th>{dn}</th>{Array.from({ length: P }, (_, p) => {
              const pl = map.get(`${di},${p}`);
              if (!pl?.length) return <td key={p} />;
              const [cls, tch] = pl[0];
              const cs = /[,&+]/.test(cls) ? cls.replace(/&/g, ',').replace(/\+/g, ',').split(',').map((c) => c.split('(')[0].trim().replace(/ /g, '').toUpperCase()).filter(Boolean).join('+') : cls.split('(')[0].trim().replace(/ /g, '').toUpperCase();
              const parts = String(tch).split(/\s+/).filter(Boolean);
              const ts = parts.length >= 2 ? `${parts[0][0].toUpperCase()}. ${parts[1].toUpperCase()}` : String(tch).toUpperCase();
              return <td key={p}><b>{cs}</b>{tch && <span>{ts}</span>}</td>;
            })}</tr>
          ))}</tbody>
        </table>
        <div className="pp-foot"><span>Ders Planı Oluşturuldu:{today()}</span><span>Chenkron Ders Planlama</span></div>
      </Page>
    );
  })}</>;
}

// ── Sınıf Dersleri & Atama Listesi (dikey) ─────────────────────────────────
function chunkClasses(list: string[], maxLen = 36, maxCount = 4): string[][] {
  const out: string[][] = [];
  let cur: string[] = [], len = 0;
  for (const c0 of list) {
    const c = String(c0).trim();
    const add = c.length + (cur.length ? 2 : 0);
    if (cur.length && (len + add > maxLen || cur.length >= maxCount)) { out.push(cur); cur = [c]; len = c.length; }
    else { cur.push(c); len += add; }
  }
  if (cur.length) out.push(cur);
  return out;
}
function groupTeacherRows(list: any[]) {
  const g = new Map<string, { subject: string; classes: string[]; duration: number; types: string[]; color: string; comb: boolean }>();
  for (const a of list) {
    const s = String(a.ders || a.subject || '').trim();
    if (!s) continue;
    const x = g.get(s) ?? g.set(s, { subject: s, classes: [], duration: 0, types: [], color: a.renk || a.color || '', comb: false }).get(s)!;
    const cs = String(a.sinif || a.class || '').trim();
    if (a.is_combined || /[+,&]/.test(cs)) {
      x.comb = true;
      for (const cc of (a.combined_classes?.length ? a.combined_classes : cs.replace(/&/g, '+').replace(/,/g, '+').split('+').map((q: string) => q.trim()).filter(Boolean))) if (cc && !x.classes.includes(cc)) x.classes.push(cc);
    } else if (cs && !x.classes.includes(cs)) x.classes.push(cs);
    x.duration += hoursOf(a) || 1;
    const t = typeStr(a);
    if (t && !x.types.includes(t)) x.types.push(t);
  }
  const res: any[] = [];
  for (const x of g.values()) {
    const chunks = chunkClasses(x.classes);
    (chunks.length ? chunks : [[]]).forEach((c, i) => res.push(i === 0
      ? { subject: x.subject, class: c.length ? c.join(', ') : '—', duration: x.duration, type: x.types.length ? x.types.join(', ') : String(x.duration), color: x.color, is_combined: x.comb }
      : { subject: `${x.subject} (Devam)`, class: c.join(', '), duration: '—', type: '—', color: x.color, is_combined: x.comb }));
  }
  return res;
}

function lessonRowsFor(d: any, ent: string, teacherView: boolean): { rows: any[]; sub: string; brans: string; total: number } {
  const raw: any[] = d.atamalar ?? [];
  if (teacherView) {
    const mine = raw.filter((a) => (a.ogretmen || a.teacher) === ent || upperTr(a.ogretmen || a.teacher || '') === upperTr(ent));
    const t = (d.ogretmenler ?? []).find((x: any) => x.ad === ent || upperTr(x.ad ?? '') === upperTr(ent)) ?? {};
    const brans = t.brans || t.branch || 'Öğretmen';
    const rows = groupTeacherRows(mine);
    return { rows, sub: `${upperTr(brans)} ÖĞRETMENİ`, brans, total: rows.reduce((s, r) => s + (typeof r.duration === 'number' ? r.duration : 0), 0) };
  }
  const rows = raw.filter((a) => matchesClass(a.sinif || a.class || '', ent) || (a.is_combined && (a.combined_classes ?? []).some((cc: string) => matchesClass(cc, ent))));
  return { rows, sub: `${upperTr(ent)} SINIF PROGRAMI`, brans: 'Öğretmen', total: rows.reduce((s, a) => s + hoursOf(a), 0) };
}

export function ClassListReport({ ctx, target, teacherView }: { ctx: Ctx; target: string; teacherView: boolean }) {
  const d = ctx.data;
  const allT: string[] = (d.ogretmenler ?? []).map((t: any) => String(t.ad ?? '').trim()).filter(Boolean);
  const allC: string[] = (d.siniflar ?? []).map((c: any) => String(c.ad ?? '').trim()).filter(Boolean);
  const isT = allT.includes(target) || target === ALL_TEACHERS ? true : allC.includes(target) || target === ALL_CLASSES ? false : teacherView;
  const ents: string[] = target && ![ALL_CLASSES, ALL_TEACHERS, 'Tümü (Çoklu Sayfa)', 'Tüm Sınıflar', 'Tüm Öğretmenler', ''].includes(target) ? [target] : isT ? allT : allC;
  if (ents.length === 1) {
    const e = ents[0];
    let { rows, sub, brans } = lessonRowsFor(d, e, isT);
    if (!rows.length && (d.dersler ?? []).length) rows = (d.dersler ?? []).map((x: any) => ({ subject: x.ad || 'Ders', teacher: isT ? e : 'Atanmadı', class: isT ? '—' : e, duration: x.saat ?? 2, color: x.renk }));
    return (
      <Page landscape={false} cls="cl">
        <div className="cl-top"><b>{isT ? 'Öğretmenin Girdiği Sınıflar & Dersler' : 'Sınıfın Dersleri & Atamaları'}</b><span>{isT ? 'TÜM ÖĞRETMENLER' : 'TÜM SINIFLAR'}</span></div>
        <div className="cl-ent"><div className="cl-avatar" /><div><b>{upperTr(e)}</b><small>{isT ? (brans ? `${upperTr(brans)} ÖĞRETMENİ` : 'BRANŞ ÖĞRETMENİ') : sub}</small></div></div>
        <LessonTable d={d} rows={rows} isT={isT} brans={brans} single />
      </Page>
    );
  }
  // Çok sayfalı sürekli liste: tarayıcı sayfalara kendisi böler.
  return (
    <Page landscape={false} cls="cl flow">
      <div className="cl-banner"><b>{isT ? 'TOPLU ÖĞRETMEN DERS & BRANŞ ATAMA LİSTESİ' : 'TOPLU SINIF DERS & ÖĞRETMEN ATAMA LİSTESİ'}</b><span>{upperTr(schoolName(d))}</span></div>
      {ents.map((e) => {
        const { rows, sub, brans, total } = lessonRowsFor(d, e, isT);
        return (
          <div key={e} className="cl-block">
            <div className="cl-bh"><b>{upperTr(e)}</b><span>{sub}</span><span className="sp" /><span>Ders: {rows.length} | Toplam: {total} Saat</span></div>
            <LessonTable d={d} rows={rows} isT={isT} brans={brans} single={false} />
          </div>
        );
      })}
      <div className="pp-foot"><span>Chenkron Ders Planlama Sistemi 2026 - 2027</span><span /></div>
    </Page>
  );
}

function LessonTable({ d, rows, isT, brans, single }: { d: any; rows: any[]; isT: boolean; brans: string; single: boolean }) {
  const cols = single
    ? ['Ders', isT ? 'Sınıf' : 'Öğretmen', isT ? 'Branş / Not' : 'Sınıf', 'Toplam', 'Uzunluk', 'Derslikler', 'Hafta', 'Dönem']
    : ['Ders', isT ? 'Sınıf' : 'Öğretmen', isT ? 'Branş / Not' : 'Sınıf', 'Toplam Saat', 'Dağılım / Tip', 'Derslik', 'Dönem'];
  return (
    <table className="cl-table">
      <thead><tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
      <tbody>
        {!rows.length && <tr><td colSpan={cols.length} className="muted">— Atanmış ders bulunmuyor —</td></tr>}
        {rows.map((it, i) => {
          const subj = String(it.subject ?? ''), cls = String(it.class ?? '—'), tch = String(it.teacher ?? '—');
          const dur = String(it.duration ?? 1), typ = String(it.type ?? dur).trim();
          const comb = !!(it.is_combined || cls.includes('+') || (it.combined_classes?.length > 1));
          const color = it.color || '#E2E8F0';
          return (
            <tr key={i}>
              <td><span className="cl-badge" style={{ background: color }}>{subjectBadge(subj, d)}</span>{upperTr(subj)}</td>
              <td>{isT ? (comb && !cls.includes('Birleşik') ? `${upperTr(cls)} (Birleşik)` : upperTr(cls)) : single ? teacherDisplay(tch, d) : upperTr(tch)}</td>
              <td className="c">{isT ? brans || 'Öğretmen' : upperTr(cls)}</td>
              <td className="c">{dur}</td>
              <td className="c">{single ? (it.length ?? dur) : typ || dur}</td>
              <td className="c">Tümü</td>
              {single ? <><td className="c">—</td><td className="c">—</td></> : <td className="c">Her iki...</td>}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

// ── Tüm Öğretmenlerin Ders Yükü Listesi ────────────────────────────────────
export function TeacherLoadReport({ ctx }: { ctx: Ctx }) {
  const d = ctx.data;
  const teachers = [...(d.ogretmenler ?? [])].sort((a, b) => String(a.ad ?? '').localeCompare(String(b.ad ?? ''), 'tr'));
  const perPage = 36, total = Math.max(1, Math.ceil(teachers.length / perPage));
  return <>{Array.from({ length: total }, (_, pi) => (
    <Page key={pi} landscape cls="tl">
      <div className="tl-banner"><b>Tüm Öğretmenlerin Ders Yükü Raporu</b><span>Toplam {teachers.length} Öğretmen   |   Sayfa {pi + 1}/{total}</span></div>
      <table className="tl-table">
        <thead><tr><th>Öğretmen Adı</th><th>Kısa Kodu</th><th>Atanan Dersler</th><th>Toplam Saat</th></tr></thead>
        <tbody>{teachers.slice(pi * perPage, (pi + 1) * perPage).map((t) => {
          const mine = (d.atamalar ?? []).filter((a: any) => matchesTeacherLoose(a.ogretmen || a.teacher || '', t.ad ?? ''));
          const subs = [...new Set(mine.map((a: any) => a.ders || a.subject).filter(Boolean))].sort().join(', ') || '—';
          return <tr key={t.ad}><td>{t.ad}</td><td>{t.kisa ?? ''}</td><td className="el">{subs}</td><td className="c">{mine.reduce((s: number, a: any) => s + hoursOf(a), 0)} Saat</td></tr>;
        })}</tbody>
      </table>
    </Page>
  ))}</>;
}

export function renderReport(mode: ReportMode, target: string, ctx: Ctx): ReactNode {
  switch (mode) {
    case 'Toplu Çarşaf Liste : Sınıflar': return <CarsafReport ctx={ctx} target={target} teacherView={false} />;
    case 'Toplu Çarşaf Liste : Öğretmenler': return <CarsafReport ctx={ctx} target={target} teacherView />;
    case 'Tablo Olarak : Dersler': return <LessonsTableReport ctx={ctx} />;
    case "[BİREBİR] Tüm Sınıflar (Yatay Sayfada 6'lı Çizelge)": return <MultiGridReport ctx={ctx} target={target} teacherView={false} />;
    case "[BİREBİR] Tüm Öğretmenler (Yatay Sayfada 6'lı Çizelge)": return <MultiGridReport ctx={ctx} target={target} teacherView />;
    case 'Sınıf Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)': return <WeeklyReport ctx={ctx} target={target} teacherView={false} />;
    case 'Öğretmen Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)': return <WeeklyReport ctx={ctx} target={target} teacherView />;
    case 'Sınıf Dersleri & Atama Listesi (Liste Formatı)': return <ClassListReport ctx={ctx} target={target} teacherView={target === ALL_TEACHERS} />;
    case 'Tüm Öğretmenlerin Ders Yükü Listesi': return <TeacherLoadReport ctx={ctx} />;
  }
}

export const isPortrait = (mode: ReportMode) => mode.includes('Sınıf Dersleri');
export const isTeacherMode = (mode: ReportMode) => mode.includes('Öğretmen');
