// scheduler/engine.py — kilitli yerleşimler (_dunya_kur, _kilitleri_isle,
// kilit_catismalari). Kilitli ders modelin İÇİNDE, yerinde sabit bir karttır;
// veriyle çelişen kilit sessizce kabul edilmez.
import { applySubjectGroups, attachSlots, buildWorld, windowBreaks } from './build.ts';
import type { Store } from './data.ts';
import type { Card, World } from './model.ts';
import { normClass, normKey } from './norm.ts';
import { impossibleGroups } from './problem.ts';
import { toInt, truthy } from './py.ts';
import * as R from './rules.ts';
import { compileRules } from './rules.ts';
import type { Rule, RuleReport } from './rules.ts';
import { validate } from './verify.ts';

export interface Kilit { kart: number; ids: number[]; pls: any[]; d: number; p: number }
export interface Catisma extends Kilit { neden: string; mesaj: string }

export class LockedConflict extends Error {
  catismalar: Catisma[];
  constructor(catismalar: Catisma[]) {
    const satirlar = catismalar.map((k) => k.mesaj);
    const fazla = satirlar.length - 15;
    super('Kilitli dersler verilerle çelişiyor. Motor kapalı saati ya da kuralı kendiliğinden açmaz, '
      + 'bu kilitleri de sessizce kabul etmez:\n' + satirlar.slice(0, 15).map((s) => '• ' + s).join('\n')
      + (fazla > 0 ? `\n… ve ${fazla} kilit daha.` : ''));
    this.catismalar = catismalar;
  }
}

const EVET = new Set<unknown>([true, 'True', 'true', 1, '1']);

export function kilitliMi(pl: any): boolean {
  return EVET.has(pl.locked) || EVET.has(pl.pinned) || EVET.has(pl.is_locked);
}

const intOr = (v: unknown, dflt: number) => toInt(v) ?? dflt;

function dayOf(pl: any): number { return intOr('day' in pl ? pl.day : ('col' in pl ? pl.col : 0), 0); }
function periodOf(pl: any): number { return intOr('period' in pl ? pl.period : ('row' in pl ? pl.row : 0), 0); }
function durOf(pl: any): number { return Math.max(1, intOr(truthy(pl.duration) ? pl.duration : 1, 1)); }
const clsOf = (pl: any) => (truthy(pl.class_name) ? pl.class_name : pl.class);
const subOf = (pl: any) => (truthy(pl.subject_name) ? pl.subject_name : pl.subject);
const tchOf = (pl: any) => (truthy(pl.teacher_name) ? pl.teacher_name : pl.teacher);

/** Kilitli kaydı çizelgeye döndürülecek biçime getirir (değer değiştirmeden). */
export function kilitliKopya(pl: any): any {
  const d = dayOf(pl), p = periodOf(pl);
  const cn = clsOf(pl), sn = subOf(pl), tn = tchOf(pl);
  return { ...pl, class_name: cn, class: cn, subject_name: sn, subject: sn, teacher_name: tn, teacher: tn,
    day: d, day_idx: d, col: d, period: p, row: p, duration: intOr(truthy(pl.duration) ? pl.duration : 1, 1),
    locked: true, is_manual: true, is_filler: false };
}

export function gunAdlari(data: Store | null, D: number): string[] {
  const gunler = data?.settings?.days;
  if (Array.isArray(gunler) && gunler.length >= D) return gunler.slice(0, D).map(String);
  return Array.from({ length: D }, (_, d) => `${d + 1}. gün`);
}

/** Dünya + kurallar + kilitli kartlar + aday yerler. */
export function dunyaKur(data: Store, D: number | null, P: number | null, crossBusy: Map<string, [number, number][]> | null,
  onlyClasses: string[] | null, raw: any[], atla: Set<number> = new Set()): [World, Rule[], RuleReport, Kilit[]] {
  const w = buildWorld(data, { D, P, crossBusy, onlyClasses });
  const [rules, report] = compileRules(raw, w);
  if (report.errors.length) return [w, rules, report, []];
  applySubjectGroups(w, rules);
  if (onlyClasses && onlyClasses.length) {
    const active = new Set<string>();
    for (const c of w.cards) for (const cn of c.classNames) active.add(normClass(cn));
    const teachers = new Map(w.teachers.map((n, i) => [normKey(n), i] as const));
    for (const pl of (data.grid_placements ?? [])) {
      if (active.has(normClass(clsOf(pl)))) continue;
      const ti = teachers.get(normKey(tchOf(pl)));
      if (ti === undefined) continue;
      const d = dayOf(pl), p = periodOf(pl);
      const dur = intOr(truthy(pl.duration) ? pl.duration : 1, 1);
      for (let off = 0; off < dur; off++) {
        if (d >= 0 && d < w.D && p + off >= 0 && p + off < w.P) w.teacherClosed[ti][d * w.P + p + off] = 1;
      }
    }
  }
  const kilitler = kilitleriIsle(data, w, onlyClasses, atla);
  attachSlots(w, rules);
  return [w, rules, report, kilitler];
}

interface Grup { hucre: Map<number, Set<number>>; kayit: [number, any, number][]; sn: string; tn: string; d: number; ad: [string, string] | null }

/** Kilitli yerleşimleri dünyaya SABİT KART olarak ekler (Python ile aynı sıra). */
export function kilitleriIsle(data: Store, w: World, onlyClasses: string[] | null, atla: Set<number>): Kilit[] {
  const grid: any[] = truthy(data.grid_placements) ? data.grid_placements : [];
  const sec = onlyClasses && onlyClasses.length ? new Set(onlyClasses.map(normClass)) : null;
  const clsIx = new Map(w.classes.map((n, i) => [normClass(n), i] as const));
  const tchIx = new Map(w.teachers.map((n, i) => [normKey(n), i] as const));
  const subIx = new Map(w.subjects.map((n, i) => [normKey(n), i] as const));
  const gruplar = new Map<string, Grup>();
  const disi: any[] = [];
  grid.forEach((pl, n) => {
    if (!pl || typeof pl !== 'object' || Array.isArray(pl) || atla.has(n) || !kilitliMi(pl)) return;
    const cn = normClass(clsOf(pl));
    if (sec !== null && !sec.has(cn)) return;
    let ci = clsIx.get(cn);
    const d = toInt('day' in pl ? pl.day : ('col' in pl ? pl.col : 0));
    const p = toInt('period' in pl ? pl.period : ('row' in pl ? pl.row : 0));
    const dur0 = toInt(truthy(pl.duration) ? pl.duration : 1);
    if (d === null || p === null || dur0 === null) ci = undefined;
    if (ci === undefined) { disi.push(pl); return; }
    const dur = Math.max(1, dur0!);
    const sn = normKey(subOf(pl)), tn = normKey(tchOf(pl));
    const comb = truthy(pl.is_combined) || truthy(pl.combined_classes);
    const bid = truthy(pl.block_id) ? String(pl.block_id) : '';
    const k = comb ? JSON.stringify([sn, tn, d, bid || ['@', p], null]) : JSON.stringify([sn, tn, d, bid || ['#', n], ci]);
    let g = gruplar.get(k);
    if (!g) { g = { hucre: new Map(), kayit: [], sn, tn, d: d!, ad: null }; gruplar.set(k, g); }
    if (g.ad === null) g.ad = [String(subOf(pl) ?? ''), String(tchOf(pl) ?? '')];
    for (let off = 0; off < dur; off++) {
      if (!g.hucre.has(p! + off)) g.hucre.set(p! + off, new Set());
      g.hucre.get(p! + off)!.add(ci);
    }
    g.kayit.push([n, pl, p!]);
  });

  const talep = [...w.cards];
  const tuketilen = new Set<number>();
  const yeni: { kart: Card; ids: number[]; pls: any[]; d: number; p: number }[] = [];
  const sameSet = (a: Set<number>, b: Set<number>) => a.size === b.size && [...a].every((x) => b.has(x));
  for (const g of gruplar.values()) {
    const saatler = [...g.hucre.keys()].sort((a, b) => a - b);
    const kosular: number[][] = [];
    for (const q of saatler) {
      const last = kosular[kosular.length - 1];
      if (last && q === last[last.length - 1] + 1 && sameSet(g.hucre.get(q)!, g.hucre.get(last[0])!)) last.push(q);
      else kosular.push([q]);
    }
    for (const kosu of kosular) {
      const siniflar = [...g.hucre.get(kosu[0])!].sort((a, b) => a - b);
      const sinifSet = new Set(siniflar);
      const L = kosu.length;
      let koken: number | null = null;
      let gerek = L;
      while (gerek > 0) {
        const aday = talep.filter((c) => !tuketilen.has(c.cid) && normKey(c.subjectName) === g.sn
          && normKey(c.teacherName) === g.tn && c.classes.some((x) => sinifSet.has(x)));
        if (!aday.length) break;
        const rank = (c: Card) => [sameSet(new Set(c.classes), sinifSet) ? 0 : 1, c.duration !== gerek ? 1 : 0];
        aday.sort((a, b) => { const ra = rank(a), rb = rank(b); return (ra[0] - rb[0]) || (ra[1] - rb[1]); });
        const c = aday[0];
        if (koken === null) koken = c.origin;
        if (c.duration <= gerek) { gerek -= c.duration; tuketilen.add(c.cid); }
        else { c.duration -= gerek; gerek = 0; }
      }
      const sIx = subIx.get(g.sn) ?? -1, tIx = tchIx.get(g.tn) ?? -1;
      if (koken === null) koken = -2 - yeni.length;
      const kart: Card = {
        cid: -1, classes: siniflar, subject: sIx, teacher: tIx, duration: L, origin: koken, group: koken,
        lockedAt: g.d * w.P + kosu[0],
        family: sIx >= 0 && sIx < w.subjectFamily.length ? w.subjectFamily[sIx] : -1, slots: [],
        subjectName: sIx >= 0 ? w.subjects[sIx] : g.ad![0], teacherName: tIx >= 0 ? w.teachers[tIx] : g.ad![1],
        classNames: siniflar.map((ci) => w.classes[ci]),
      };
      const kayit = g.kayit.filter(([, , p0]) => kosu[0] <= p0 && p0 <= kosu[kosu.length - 1]);
      yeni.push({ kart, ids: kayit.map(([n]) => n), pls: kayit.map(([, pl]) => pl), d: g.d, p: kosu[0] });
    }
  }
  w.cards = [...w.cards.filter((c) => !tuketilen.has(c.cid)), ...yeni.map((k) => k.kart)];
  w.cards.forEach((c, i) => { c.cid = i; });
  w.kilitDisi = disi;
  return yeni.map((k) => ({ kart: k.kart.cid, ids: k.ids, pls: k.pls, d: k.d, p: k.p }));
}

function slotYokNedeni(w: World, rules: Rule[], c: Card, k: Kilit): string {
  const { d, p } = k, P = w.P;
  if (!(d >= 0 && d < w.D) || p < 0 || p + c.duration > P) return 'çizelgenin gün/saat sınırı dışında';
  const idx = d * P + p;
  const parca: string[] = [];
  const hits = (m: Uint8Array) => { for (let o = 0; o < c.duration; o++) if (m[idx + o]) return true; return false; };
  for (const ci of c.classes) if (hits(w.classClosed[ci])) parca.push(`${w.classes[ci]} sınıfının zaman tablosunda KAPALI`);
  if (c.teacher >= 0 && hits(w.teacherClosed[c.teacher])) parca.push(`${w.teachers[c.teacher]} öğretmeninin zaman tablosunda KAPALI`);
  if (parca.length) return parca.join('; ');
  for (const r of rules) {
    if (R.WINDOW_RULES.has(r.kind) && r.isHard() && r.appliesCard(c) && windowBreaks(r, p, c.duration, P)) {
      return `sıkı kural «${r.label}» bu saate izin vermiyor`;
    }
  }
  return 'bu saat ders için izin verilen bir yer değil';
}

/** Veriyle ya da birbiriyle çelişen kilitli kartlar. */
export function kilitCatismalari(w: World, rules: Rule[], kilitler: Kilit[], data: Store | null, completionFirst = true): Catisma[] {
  if (!kilitler.length) return [];
  const forced = completionFirst ? impossibleGroups(w) : new Set<string>();
  const gunler = gunAdlari(data, w.D);
  const kabul: number[] = [];
  const out: Catisma[] = [];
  for (const k of kilitler) {
    const c = w.cards[k.kart];
    let neden: string;
    if (!c.slots.length) {
      neden = slotYokNedeni(w, rules, c, k);
    } else {
      const alt: World = { ...w, cards: [...kabul.map((j) => w.cards[j]), c] };
      const [errs] = validate(alt, rules, alt.cards.map((x) => x.lockedAt!), completionFirst, forced);
      if (errs.length) neden = [...new Set(errs)].join('; ');
      else { kabul.push(k.kart); continue; }
    }
    const gun = k.d >= 0 && k.d < gunler.length ? gunler[k.d] : `${k.d + 1}. gün`;
    const saat = c.duration === 1 ? `${k.p + 1}.` : `${k.p + 1}-${k.p + c.duration}.`;
    const mesaj = `${c.classNames.join(' + ')} · ${c.subjectName} (${c.teacherName}) — ${gun} ${saat} saat: ${neden}`;
    out.push({ ...k, neden, mesaj });
  }
  return out;
}
