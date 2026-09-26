// scheduler/model.py — Kart ve Dünya.
//
// Python hücre maskelerini sınırsız tamsayı olarak tutuyor (Birey'de 5x11 =
// 55 bit; JS sayısına sığmaz). Burada her birim için hücre başına bir bayt:
// closed[ci][hücre] = 1. Kartın aday yeri başlangıç hücresidir; kapladığı
// hücreler aynı günde ardışık olduğu için ayak izi (idx, süre) ile tam bellidir.

export interface Card {
  cid: number;
  classes: number[];
  subject: number;
  teacher: number;
  duration: number;
  origin: number;
  group: number;
  lockedAt: number | null;
  family: number;
  slots: number[];
  subjectName: string;
  teacherName: string;
  classNames: string[];
}

export interface World {
  D: number;
  P: number;
  classes: string[];
  teachers: string[];
  subjects: string[];
  cards: Card[];
  classClosed: Uint8Array[];
  teacherClosed: Uint8Array[];
  classAvoid: Uint8Array[];
  teacherAvoid: Uint8Array[];
  classCapacity: number[];
  classDemand: number[];
  families: string[];
  subjectFamily: number[];
  /** kilitlerde dünyada karşılığı olmayan kayıtlar (engine._kilitleri_isle) */
  kilitDisi?: any[];
}

export function totalHours(w: World): number {
  let s = 0;
  for (const c of w.cards) s += c.duration * c.classes.length;
  return s;
}

export function familyName(w: World, f: number): string {
  return f >= 0 && f < w.families.length ? w.families[f] : '?';
}

/** Kart ayak izi gün sınırını aşmıyor mu (Python footprint != 0)? */
export function fits(w: World, p: number, dur: number): boolean {
  return p + dur <= w.P;
}

/** Ayak izi bir maskeyle kesişiyor mu? */
export function hitsMask(mask: Uint8Array, idx: number, dur: number): boolean {
  for (let k = 0; k < dur; k++) if (mask[idx + k]) return true;
  return false;
}

/** İki yerleşimin ayak izi kesişiyor mu (Python af & bf)? */
export function overlaps(P: number, a: number, adur: number, b: number, bdur: number): boolean {
  if (Math.floor(a / P) !== Math.floor(b / P)) return false;
  return a < b + bdur && b < a + adur;
}

export function cardLabel(c: Card): string {
  return `<Kart ${c.classNames.join('+')} ${c.subjectName} ${c.teacherName} ${c.duration}s>`;
}

export function copyCard(c: Card, over: Partial<Card> = {}): Card {
  return { ...c, classes: [...c.classes], slots: [...c.slots], classNames: [...c.classNames], ...over };
}
