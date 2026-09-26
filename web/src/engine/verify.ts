// scheduler/verify.py — bağımsız son denetim, sıfırdan.
import type { Card, World } from './model.ts';
import { copyCard, familyName } from './model.ts';
import { impossibleGroups, forcedKey } from './problem.ts';
import { key } from './py.ts';
import * as R from './rules.ts';
import type { Rule } from './rules.ts';

export type Pieces = Map<number, number[]>;

/** Döner: [hatalar, tercih ihlalleri, esneyen (aritmetik taban)] */
export function validate(world: World, rules: Rule[], positions: number[], bendRules = false,
  forcedIn: Set<string> | null = null, piecesIn: Pieces | null = null): [string[], string[], string[]] {
  const errors: string[] = [], soft: string[] = [], bent: string[] = [];
  if (positions.length !== world.cards.length) return [['Motorun döndürdüğü kart sayısı atamalarla eşleşmiyor'], [], []];
  let forced = forcedIn;
  if (bendRules && forced === null) forced = impossibleGroups(world);
  forced = forced ?? new Set();
  const pieces = piecesIn ?? new Map();
  const P = world.P;
  const classCells = new Map<string, number>(), teacherCells = new Map<string, number>();
  const rows: [Card, number, number][] = [];
  const placed: [Card, number][] = [];
  world.cards.forEach((c, i) => {
    const idx = positions[i];
    const pc = pieces.get(i);
    if (idx < 0 && pc && pc.length) {
      if (c.lockedAt !== null) errors.push(`Kilitli kart bölünmüş: ${c.classNames.join(' + ')} · ${c.subjectName}`);
      if (pc.length !== c.duration) errors.push(`Bölünmüş kartın parça sayısı süresiyle eşleşmiyor: ${c.classNames.join(' + ')} · ${c.subjectName}`);
      for (const pidx of pc) placed.push([copyCard(c, { duration: 1, slots: [] }), pidx]);
      const days = new Map<number, number[]>();
      for (const pidx of pc) {
        const d = Math.floor(pidx / P);
        if (!days.has(d)) days.set(d, []);
        days.get(d)!.push(pidx);
      }
      for (const [d, lst0] of days) {
        const lst = [...lst0].sort((a, b) => a - b);
        if (lst.some((v, k) => k > 0 && v - lst[k - 1] !== 1)) {
          errors.push(`Bölünmüş kartın parçaları aynı günde yan yana değil: ${c.classNames.join(' + ')} · ${c.subjectName}, gün ${d + 1}`);
        }
      }
      return;
    }
    placed.push([c, idx]);
  });
  // Aynı sınıfta aynı dersin aynı güne düşen saatleri tek kesintisiz blok.
  const ayni = new Map<string, { cls: number[]; subj: number; d: number; cells: Set<number> }>();
  for (const [c, idx] of placed) {
    if (idx < 0) continue;
    const d = Math.floor(idx / P);
    const k = key(c.classes.join(','), c.subject, d);
    let e = ayni.get(k);
    if (!e) { e = { cls: c.classes, subj: c.subject, d, cells: new Set() }; ayni.set(k, e); }
    for (let off = 0; off < c.duration; off++) e.cells.add(idx + off);
  }
  for (const e of ayni.values()) {
    const lst = [...e.cells].sort((a, b) => a - b);
    if (lst.some((v, k) => k > 0 && v - lst[k - 1] !== 1)) {
      const subj = e.subj >= 0 ? world.subjects[e.subj] : world.subjects[world.subjects.length + e.subj];
      errors.push(`Aynı ders aynı günde araya ders girerek bölünmüş: ${e.cls.map((ci) => world.classes[ci]).join(' + ')} · ${subj}, gün ${e.d + 1}`);
    }
  }
  for (const [c, idx] of placed) {
    const label = `${c.classNames.join(' + ')} · ${c.subjectName}`;
    if (idx < 0) {
      if (c.lockedAt !== null) errors.push(`Kilitli kart yerleşmedi: ${label}`);
      continue;
    }
    const d = Math.floor(idx / P), p = idx % P;
    if (!(d >= 0 && d < world.D) || p + c.duration > P) {
      errors.push(`Gün/saat sınırı aşıldı: ${label}`);
      continue;
    }
    if (c.lockedAt !== null && idx !== c.lockedAt) errors.push(`Kilit değişti: ${label}`);
    for (let off = 0; off < c.duration; off++) {
      const cell = idx + off;
      for (const ci of c.classes) {
        const k = key(ci, cell);
        if (classCells.has(k)) errors.push(`Sınıf çakışması: ${world.classes[ci]}, gün ${d + 1}, saat ${p + off + 1}`);
        classCells.set(k, c.cid);
        if (world.classClosed[ci][cell]) errors.push(`Kapalı sınıf saati: ${label}`);
      }
      if (c.teacher >= 0) {
        const k = key(c.teacher, cell);
        if (teacherCells.has(k)) errors.push(`Öğretmen çakışması: ${c.teacherName}, gün ${d + 1}, saat ${p + off + 1}`);
        teacherCells.set(k, c.cid);
        if (world.teacherClosed[c.teacher][cell]) errors.push(`Kapalı öğretmen saati: ${c.teacherName}`);
      }
    }
    rows.push([c, d, p]);
  }
  for (const r of rules) {
    if (R.DEFINITION_RULES.has(r.kind)) continue;
    const selected = rows.filter((x) => r.appliesCard(x[0]));
    const hit = (detail: string, bendable = false) => {
      const msg = `${r.label}: ${detail}`;
      if (!r.isHard()) soft.push(msg);
      else if (bendRules && bendable) bent.push(msg);
      else errors.push(msg);
    };
    const byClass = new Map<number, [Card, number, number][]>(), byTeacher = new Map<number, [Card, number, number][]>();
    for (const row of selected) {
      const c = row[0];
      for (const ci of c.classes) if (r.appliesClass(ci)) {
        if (!byClass.has(ci)) byClass.set(ci, []);
        byClass.get(ci)!.push(row);
      }
      if (c.teacher >= 0) {
        if (!byTeacher.has(c.teacher)) byTeacher.set(c.teacher, []);
        byTeacher.get(c.teacher)!.push(row);
      }
    }
    if (R.WINDOW_RULES.has(r.kind)) {
      const noon = world.P >= 6 ? 4 : Math.floor((world.P + 1) / 2);
      for (const [c, d, p] of selected) {
        if ((r.kind === R.X_MORNING_ONLY && p + c.duration > noon)
          || (r.kind === R.X_AFTERNOON_ONLY && p < noon)
          || (r.kind === R.X_NOT_FIRST_PERIOD && p === 0)
          || (r.kind === R.X_NOT_LAST_PERIOD && p + c.duration > world.P - 1)
          || (r.kind === R.X_TIME_WINDOW && (p < r.param || p + c.duration - 1 > r.param2))) {
          hit(`${c.subjectName}, gün ${d + 1}, saat ${p + 1}`);
        }
      }
    } else if ([R.X_SUBJECT_ONCE_DAY, R.X_TEACHER_ONCE_DAY, R.X_PAIR_NOT_SAME_DAY,
      R.X_HARD_NOT_ADJACENT, R.X_SUBJECT_NOT_ADJACENT, R.X_MIN_DAYS_BETWEEN].includes(r.kind)) {
      for (const [ci, lst] of byClass) {
        for (let i = 0; i < lst.length; i++) {
          const [a, ad, ap] = lst[i];
          for (let j = 0; j < i; j++) {
            const [b, bd, bp] = lst[j];
            const sameDay = ad === bd;
            const sameFamily = a.family >= 0 && a.family === b.family;
            const adjacent = ap + a.duration === bp || bp + b.duration === ap;
            const blok = adjacent && a.origin === b.origin;
            const bad = (r.kind === R.X_SUBJECT_ONCE_DAY && sameDay && sameFamily && !blok)
              || (r.kind === R.X_TEACHER_ONCE_DAY && sameDay && a.teacher >= 0 && a.teacher === b.teacher && !blok)
              || (r.kind === R.X_PAIR_NOT_SAME_DAY && sameDay && a.subject !== b.subject)
              || (r.kind === R.X_HARD_NOT_ADJACENT && sameDay && !sameFamily && adjacent)
              || (r.kind === R.X_SUBJECT_NOT_ADJACENT && sameDay && sameFamily && adjacent && a.cid !== b.cid)
              || (r.kind === R.X_MIN_DAYS_BETWEEN && sameFamily && Math.abs(ad - bd) < Math.max(1, r.param));
            if (bad) {
              let bendable = false;
              if ((r.kind === R.X_SUBJECT_ONCE_DAY || r.kind === R.X_MIN_DAYS_BETWEEN) && sameFamily) bendable = forced.has(forcedKey('s', ci, a.family));
              else if (r.kind === R.X_TEACHER_ONCE_DAY) bendable = forced.has(forcedKey('t', ci, a.teacher));
              hit(`${world.classes[ci]}, gün ${ad + 1}: ${a.subjectName} / ${b.subjectName}`, bendable);
            }
          }
        }
      }
    } else if ([R.X_SUBJECT_MAX_HOURS, R.X_PRACTICAL_MAX_HOURS, R.X_SUBJECT_MAX_SESSIONS, R.X_EVEN_SPREAD].includes(r.kind)) {
      for (const [ci, lst] of byClass) {
        const counts = new Map<number, number[]>();
        for (const [c, d] of lst) {
          if (!counts.has(c.family)) counts.set(c.family, new Array(world.D).fill(0));
          counts.get(c.family)![d] += (r.kind === R.X_SUBJECT_MAX_SESSIONS || r.kind === R.X_EVEN_SPREAD) ? 1 : c.duration;
        }
        for (const [fam, values] of counts) {
          if (r.kind === R.X_EVEN_SPREAD) {
            if (Math.max(...values) - Math.min(...values) > 1) hit(`${world.classes[ci]}, ${familyName(world, fam)}: [${values.join(', ')}]`);
          } else if (values.some((v) => v > r.param)) hit(`${world.classes[ci]}, ${familyName(world, fam)}: [${values.join(', ')}]`);
        }
      }
    } else if ([R.X_CLASS_MAX_HOURS, R.X_TEACHER_MAX_HOURS, R.X_TEACHER_MAX_DAYS].includes(r.kind)) {
      const groups = r.kind === R.X_CLASS_MAX_HOURS ? byClass : byTeacher;
      for (const lst of groups.values()) {
        const counts = new Array(world.D).fill(0);
        for (const [c, d] of lst) counts[d] += c.duration;
        if (r.kind === R.X_TEACHER_MAX_DAYS) {
          if (counts.filter((v) => v > 0).length > r.param) hit(`Öğretmenin gün sayısı ${r.param} sınırını aşıyor`);
        } else if (counts.some((v) => v > r.param)) hit(`Günlük saat sınırı ${r.param} aşıldı: [${counts.join(', ')}]`);
      }
    } else if ([R.X_SAME_DAY_ADJACENT, R.X_NO_CLASS_GAP, R.X_NO_TEACHER_GAP, R.X_TEACHER_MAX_RUN].includes(r.kind)) {
      const groups = (r.kind === R.X_NO_TEACHER_GAP || r.kind === R.X_TEACHER_MAX_RUN) ? byTeacher : byClass;
      for (const lst of groups.values()) {
        const days = new Map<number, Set<number>>();
        for (const [c, d, p] of lst) {
          if (!days.has(d)) days.set(d, new Set());
          for (let q = p; q < p + c.duration; q++) days.get(d)!.add(q);
        }
        for (const [d, periods] of days) {
          if (!periods.size) continue;
          if (r.kind === R.X_TEACHER_MAX_RUN) {
            let run = 0;
            for (let p = 0; p < world.P; p++) {
              run = periods.has(p) ? run + 1 : 0;
              if (run > r.param) { hit(`Gün ${d + 1}: ardışık saat sınırı aşıldı`); break; }
            }
          } else if (periods.size !== Math.max(...periods) - Math.min(...periods) + 1) hit(`Gün ${d + 1}: dersler arasında boşluk var`);
        }
      }
    } else if (r.kind === R.Y_SUBJECT_MAX_PARALLEL || r.kind === R.Y_TEACHER_MAX_PARALLEL) {
      const counts = new Map<string, number>();
      for (const [c, d, p] of selected) {
        const k0 = r.kind === R.Y_SUBJECT_MAX_PARALLEL ? c.family : c.teacher;
        for (let off = 0; off < c.duration; off++) {
          const k = key(k0, d, p + off);
          counts.set(k, (counts.get(k) ?? 0) + c.classes.length);
        }
      }
      if ([...counts.values()].some((v) => v > r.param)) hit('Eşzamanlı sınıf sınırı aşıldı');
    }
  }
  return [errors, soft, bent];
}
