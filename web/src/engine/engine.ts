// scheduler/engine.py (optimal kip) ve scheduler/worker.py (run_worker).
// Uygulamanın kullandığı yol budur: tabu ısıtma -> CP-SAT turları -> takas ->
// bitirme geçişi -> bağımsız denetim.
import { dayBound, explainDayBound } from './daybound.ts';
import type { Issue } from './diagnostics.ts';
import { diagnose } from './diagnostics.ts';
import { solveOptimal } from './cpsat.ts';
import type { AskInfo } from './cpsat.ts';
import { Finisher } from './finish.ts';
import type { Catisma, Kilit } from './locks.ts';
import { LockedConflict, dunyaKur, kilitCatismalari, kilitliKopya } from './locks.ts';
import type { World } from './model.ts';
import { totalHours } from './model.ts';
import { normClass, normKey } from './norm.ts';
import { hazirla } from './prep.ts';
import { Problem, impossibleGroups } from './problem.ts';
import { toInt, truthy } from './py.ts';
import type { Rule } from './rules.ts';
import { searchPortfolio } from './tabu.ts';
import type { TabuRec } from './tabu.ts';
import type { Pieces } from './verify.ts';
import { validate } from './verify.ts';

export { LockedConflict };
export const ISITMA_SANIYE = 15.0;
const now = () => performance.now() / 1000;

export class Result {
  placements: any[] = [];
  unplaced: any[] = [];
  warnings: string[] = [];
  diagnostics: Issue[] = [];
  elapsed = 0;
  placedHours = 0;
  totalHours = 0;
  status = 'not_started';
  upperBound = 0;
  positions: number[] = [];
  splitPieces: Pieces = new Map();
  forcedMinimums: string[] = [];
  world!: World;
  rules!: Rule[];
  kilitler = new Map<number, Kilit>();
  kilitDisi: any[] = [];
  catismalar: Catisma[] = [];

  get valid() { return true; }
  get complete() { return this.placedHours === this.totalHours && !this.unplaced.length; }
}

/** Kartın KAYITLI çizelgedeki yeri (takas aşamasının referansı). */
function kayitliYerTablosu(data: any, w: World): Map<string, number[]> {
  const t = new Map<string, number[]>();
  for (const pl of data.grid_placements ?? []) {
    const d = toInt('day' in pl ? pl.day : ('col' in pl ? pl.col : 0));
    const p = toInt('period' in pl ? pl.period : ('row' in pl ? pl.row : 0));
    if (d === null || p === null) continue;
    const k = [normClass(truthy(pl.class_name) ? pl.class_name : pl.class), normKey(truthy(pl.subject_name) ? pl.subject_name : pl.subject),
      normKey(truthy(pl.teacher_name) ? pl.teacher_name : pl.teacher), toInt(truthy(pl.duration) ? pl.duration : 1) ?? 1].join('|');
    if (!t.has(k)) t.set(k, []);
    t.get(k)!.push(d * w.P + p);
  }
  return t;
}

function bitir(res: Result, w: World, rules: Rule[], data: any, completionFirst: boolean, start: number): Result {
  for (const i of res.kilitler.keys()) {
    if (res.positions[i] < 0 && w.cards[i].lockedAt !== null) res.positions[i] = w.cards[i].lockedAt!;
  }
  const forced = completionFirst ? impossibleGroups(w) : new Set<string>();
  const [errors, soft, bent] = validate(w, rules, res.positions, completionFirst, forced, res.splitPieces);
  if (errors.length) throw new Error('Çizelge son denetimden geçmedi; sonuç uygulanmadı:\n' + errors.slice(0, 12).join('\n'));
  res.warnings.push(...soft);
  res.forcedMinimums = bent;
  for (const b of bent) res.warnings.push('ARİTMETİK TABAN — ' + b + ' (bu ders için mümkün olan en az tekrar)');
  const atamalar = data.atamalar ?? [];
  const colorOf = (c: any) => {
    const original = atamalar[c.origin] ?? {};
    return original.color || original.renk;
  };
  w.cards.forEach((c, i) => {
    const idx = res.positions[i];
    const kilit = res.kilitler.get(i);
    if (kilit) {
      res.placedHours += c.duration * c.classes.length;
      for (const pl of kilit.pls) res.placements.push(kilitliKopya(pl));
      return;
    }
    const parcalar = res.splitPieces.get(i);
    if (idx < 0 && parcalar) {
      parcalar.forEach((pidx, k) => {
        const d = Math.floor(pidx / w.P), p = pidx % w.P;
        res.placedHours += c.classes.length;
        for (const cn of c.classNames) {
          res.placements.push({ class_name: cn, class: cn, subject_name: c.subjectName, subject: c.subjectName,
            teacher_name: c.teacherName, teacher: c.teacherName, day: d, day_idx: d, col: d, period: p, row: p,
            duration: 1, is_combined: c.classes.length > 1, combined_classes: c.classes.length > 1 ? [...c.classNames] : [],
            block_id: `c${c.cid}b${k}`, card_id: c.cid, assignment_index: c.origin, locked: false, is_manual: false,
            is_filler: false, is_split: true, color: colorOf(c) });
        }
      });
      return;
    }
    if (idx < 0) {
      for (const cn of c.classNames) {
        res.unplaced.push({ card_id: c.cid, class: cn, subject: c.subjectName, teacher: c.teacherName,
          duration: c.duration, hours: c.duration, block_id: `c${c.cid}` });
      }
      return;
    }
    const d = Math.floor(idx / w.P), p = idx % w.P;
    res.placedHours += c.duration * c.classes.length;
    for (const cn of c.classNames) {
      res.placements.push({ class_name: cn, class: cn, subject_name: c.subjectName, subject: c.subjectName,
        teacher_name: c.teacherName, teacher: c.teacherName, day: d, day_idx: d, col: d, period: p, row: p,
        duration: c.duration, is_combined: c.classes.length > 1, combined_classes: c.classes.length > 1 ? [...c.classNames] : [],
        block_id: `c${c.cid}`, card_id: c.cid, assignment_index: c.origin, locked: false, is_manual: false,
        is_filler: false, color: colorOf(c) });
    }
  });
  for (const pl of res.kilitDisi) res.placements.push(kilitliKopya(pl));
  if (res.status !== 'cancelled') res.status = res.placedHours === res.totalHours ? 'complete' : 'timeout';
  if (res.complete) {
    res.status = 'complete';
    const eski = new Set(res.diagnostics.map((x) => x.message));
    res.diagnostics = [];
    res.warnings = res.warnings.filter((x) => !eski.has(x));
  } else if (res.diagnostics.length && res.status !== 'cancelled') res.status = 'infeasible';
  res.elapsed = now() - start;
  return res;
}

export interface SolveOptions {
  D?: number | null; P?: number | null; crossBusy?: Map<string, [number, number][]> | null;
  onlyClasses?: string[] | null; seed?: number | null; relations?: any[] | null;
  progress?: (placed: number, total: number, attempt: number) => void; cancelled?: () => boolean;
  completionFirst?: boolean; allowSplit?: boolean; azamiSaniye?: number;
  askContinue?: ((info: AskInfo) => Promise<boolean>) | null; unlockConflictingLocks?: boolean;
  lanes?: number; log?: (msg: string) => void;
}

/** Çizelgeyi kurar (optimal kip). */
export async function solve(data: any, o: SolveOptions = {}): Promise<Result> {
  const start = now();
  const res = new Result();
  const completionFirst = o.completionFirst ?? true;
  const cancelled = () => !!o.cancelled?.();
  const raw = o.relations ?? data.planlama_iliskileri ?? [];
  let [w, rules, report, kilitler] = dunyaKur(data, o.D ?? null, o.P ?? null, o.crossBusy ?? null, o.onlyClasses ?? null, raw);
  if (report.errors.length) throw new Error('Planlama ilişkileri uygulanamadı:\n' + report.errors.join('\n'));
  const catisma = kilitCatismalari(w, rules, kilitler, data, completionFirst);
  let kilitNotu: string[] = [];
  if (catisma.length) {
    if (!o.unlockConflictingLocks) throw new LockedConflict(catisma);
    const atla = new Set(catisma.flatMap((k) => k.ids));
    [w, rules, report, kilitler] = dunyaKur(data, o.D ?? null, o.P ?? null, o.crossBusy ?? null, o.onlyClasses ?? null, raw, atla);
    kilitNotu = catisma.map((k) => 'KİLİT ÇÖZÜLDÜ — ' + k.mesaj);
    res.catismalar = catisma;
  }
  res.kilitler = new Map(kilitler.map((k) => [k.kart, k]));
  res.kilitDisi = [...(w.kilitDisi ?? [])];
  res.world = w;
  res.rules = rules;
  res.warnings = [...report.warnings, ...kilitNotu];
  res.totalHours = totalHours(w);
  res.positions = w.cards.map((c) => (c.lockedAt !== null ? c.lockedAt : -1));
  [res.diagnostics, res.upperBound] = diagnose(w, rules);
  const forced = completionFirst ? impossibleGroups(w) : new Set<string>();
  let gunUst: number | null = null;
  if (w.cards.length) {
    try { gunUst = await dayBound(w, rules, forced, 2.0); }
    catch (e) { res.warnings.push(`Gün-seviyesi sınır hesaplanamadı: ${e}`); }
  }
  if (gunUst !== null) {
    if (gunUst < Math.min(totalHours(w), res.upperBound)) {
      try { res.diagnostics.push(...await explainDayBound(w, rules, forced, gunUst, 5.0)); }
      catch (e) { res.warnings.push(`Gün-seviyesi tanı çalışmadı: ${e}`); }
    }
    if (gunUst < res.upperBound) res.upperBound = gunUst;
  }
  res.warnings.push(...res.diagnostics.map((x) => x.message));
  if (!w.cards.length) return bitir(res, w, rules, data, completionFirst, start);

  // Takas aşamasının referansı: mevcut çizelge.
  const mevcut = new Map<number, number>();
  w.cards.forEach((c, i) => { if (c.lockedAt !== null) mevcut.set(i, c.lockedAt); });
  const tablo = kayitliYerTablosu(data, w);
  w.cards.forEach((c, i) => {
    if (mevcut.has(i)) return;
    for (const cn of c.classNames) {
      const yerler = tablo.get([normClass(cn), normKey(c.subjectName), normKey(c.teacherName), c.duration].join('|'));
      if (yerler && yerler.length) { mevcut.set(i, yerler.shift()!); return; }
    }
  });

  // ── ISITMA: önce C++ tabu portföyü ──
  let isitma: [number[], number, boolean] | null = null;
  if (!cancelled()) {
    try {
      const prI = new Problem(w, rules, completionFirst);
      if (!prI.errors.length) {
        const tabuIlerle = (r: TabuRec) => o.progress?.(r.hours, res.totalHours, r.restarts + 1);
        const baseI = o.seed ?? 20260912;
        const lanesI = Math.max(2, o.lanes ?? 4);
        let enIyiI: TabuRec | null = null;
        const sonI = now() + ISITMA_SANIYE;
        let kusak = 0;
        while (now() < sonI && !cancelled()) {
          kusak++;
          const kalanI = sonI - now();
          if (kalanI < 1.5) break;
          const seeds = Array.from({ length: lanesI }, (_, k) => baseI * kusak + (k + 1) * 15485863 + kusak * 2654435761);
          const alt = await searchPortfolio(prI, Math.min(6.0, kalanI), seeds, totalHours(w), { progress: tabuIlerle, cancelled });
          if (enIyiI === null || alt.hours > enIyiI.hours) enIyiI = alt;
          if (enIyiI.hours >= totalHours(w)) break;
        }
        if (enIyiI !== null && enIyiI.hours > 0) {
          const [errsI] = validate(w, rules, enIyiI.positions, false, impossibleGroups(w));
          isitma = [[...enIyiI.positions], enIyiI.hours, !errsI.length];
          res.warnings.push(`Isıtma (tabu, ${kusak} kuşak): ${enIyiI.hours}/${res.totalHours} saat`
            + (errsI.length ? ' (sert kural ihlali var, yalnızca ipucu)' : '') + '.');
        }
      }
    } catch (e) {
      res.warnings.push(`Isıtma çalışmadı: ${e}`);
    }
  }
  const [pos, parcalar, placed0, durum, tur] = await solveOptimal(w, rules, {
    referans: mevcut, allowSplit: o.allowSplit ?? true, azamiSaniye: o.azamiSaniye ?? 3600,
    progress: (rec) => o.progress?.(rec.saat, res.totalHours, rec.tur), cancelled, askContinue: o.askContinue ?? null,
    bilinenUst: gunUst, isitma,
  });
  let placed = placed0;
  res.positions = pos;
  res.splitPieces = parcalar;
  res.status = durum === 'OPTIMAL' ? 'optimal' : durum.toLowerCase();
  if ((durum === 'STALLED' || durum === 'FEASIBLE') && pos.some((i) => i < 0) && !cancelled()) {
    try {
      const fin = new Finisher(w, rules, pos, forced, parcalar);
      const [yeni, kazanc] = fin.run();
      if (kazanc > 0) {
        const [hata] = validate(w, rules, yeni, completionFirst, forced, parcalar);
        if (!hata.length) {
          res.positions = yeni;
          placed += kazanc;
          res.warnings.push(`Bitirme geçişi ${kazanc} saat daha yerleştirdi.`);
        }
      }
    } catch (e) {
      res.warnings.push(`Bitirme geçişi çalışmadı: ${e}`);
    }
  }
  // Açıkta kalan her kart için SAAT düzeyinde sebep.
  const P = w.P;
  w.cards.forEach((c, i) => {
    if (res.positions[i] >= 0 || res.splitPieces.has(i) || c.teacher < 0) return;
    const ti = c.teacher;
    const tOpen: number[] = [];
    for (let cell = 0; cell < w.D * P; cell++) if (!w.teacherClosed[ti][cell]) tOpen.push(cell);
    const ortak = tOpen.filter((cell) => !c.classes.some((ci) => w.classClosed[ci][cell]));
    const yuk = w.cards.filter((x) => x.teacher === ti).reduce((s, x) => s + x.duration, 0);
    const gunler = [...new Set(ortak.map((cell) => Math.floor(cell / P)))].sort((a, b) => a - b);
    res.diagnostics.push({ kind: 'hour_level', cards: [i],
      message: `Yerleşmedi — ${c.classNames.join(' + ')} · ${c.subjectName} (${c.duration} saat, ${c.teacherName}): `
        + `öğretmenin haftalık açık saati ${tOpen.length}, yükü ${yuk} saat; bu sınıfla ORTAK açık saat ${ortak.length} `
        + `(gün: ${gunler.map((d) => String(d + 1)).join(', ') || '-'}). Ortak saatler öğretmenin diğer derslerine gidince `
        + 'bu karta yer kalmıyor; öğretmenin ya da sınıfın tablosunda saat açmak gerekir.' });
  });
  let aciklama: string;
  if (durum === 'STALLED') aciklama = 'iki tur üst üste ilerleme olmadı, daha fazla beklenmedi';
  else if (durum === 'OPTIMAL' && placed < totalHours(w)) {
    aciklama = gunUst !== null && placed >= gunUst ? 'bu kurallarla daha fazlası mümkün değil (gün-seviyesi kanıt)'
      : 'bu kurallar ve zaman tablolarıyla daha fazlası mümkün değil (CP-SAT kanıtı)';
  } else aciklama = `CP-SAT ${durum}`;
  res.warnings.push(`Optimal kip: ${tur} tur, ${placed}/${res.totalHours} saat, ${aciklama}.`
    + (parcalar.size ? ` ${parcalar.size} blok parçalara bölündü.` : ''));
  if (durum === 'CANCELLED') res.status = 'cancelled';
  return bitir(res, w, rules, data, completionFirst, start);
}

/** scheduler/worker.run_worker — uygulamanın "finished_successfully" sözlüğü. */
export async function runPlanner(dataStore: any, o: SolveOptions & { targetClass?: string | null } = {}): Promise<any> {
  const pr = hazirla(dataStore, o.targetClass ?? null);
  const result = await solve(pr.data, { ...o, D: pr.D, P: pr.P, onlyClasses: pr.selected, crossBusy: pr.engel });
  const perKey = new Map<string, any>();
  for (const x of result.unplaced) {
    const k = [x.class, x.subject, x.teacher].join('|');
    const e = perKey.get(k) ?? { class: x.class, subject: x.subject, teacher: x.teacher, hours: 0 };
    e.hours += x.hours;
    perKey.set(k, e);
  }
  const schedule = [...pr.others, ...result.placements];
  const capacity = result.world.classCapacity.reduce((s, v, i) => s + (pr.selected.includes(result.world.classes[i]) ? v : 0), 0);
  return {
    schedule, placements: schedule, placed_hours: result.placedHours, placed_real_hours: result.placedHours,
    total_hours: capacity, total_assigned_hours: result.totalHours, status: result.status, complete: result.complete,
    engine: 'web-wasm', upper_bound: result.upperBound, diagnostics: result.diagnostics, warnings: result.warnings,
    unplaced_summary: [...perKey.values()], unplaced_cards: result.unplaced, elapsed_seconds: Math.round(result.elapsed * 1000) / 1000,
    classes: result.world.classes, D: result.world.D, P: result.world.P,
  };
}
