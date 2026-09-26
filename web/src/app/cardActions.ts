// timetable_grid.DraggableLessonCard._show_card_context_menu ve
// _compute_free_slot_capacity: yerleşmemiş kart üzerinden dağılım değiştirme,
// renk ve atama silme.
import { dims } from './model.ts';
import { formatTrName, matchesClass, syncKeys } from './datastore.ts';
import { normKey } from '../engine/norm.ts';
import { mutate, status, tell } from './store.ts';
import type { Unplaced } from './model.ts';

function rowMatches(a: any, s: string, c: string, t: string, rawTeacher: string): boolean {
  const as = formatTrName(a.subject || a.ders || ''), ac = formatTrName(a.class || a.sinif || '');
  const atRaw = a.teacher || a.ogretmen || '', at = formatTrName(atRaw);
  return as === s && (!c || ac === c) && (!t || at === t || normKey(atRaw) === normKey(rawTeacher));
}

/** _compute_free_slot_capacity — haftada bu ders için gerçekten boş kalan saat. */
export function freeCapacity(d: any, card: Unplaced): number | null {
  const { D, P } = dims(d);
  const total = D * P;
  const targets = card.classes.length ? card.classes : card.className ? [card.className] : [];
  if (!targets.length && !card.teacher) return null;
  const sfmt = formatTrName(card.subject);
  const unusable = (match: (p: any) => boolean, timeoff: any): number => {
    const u = new Set<string>();
    (Array.isArray(timeoff) ? timeoff : []).forEach((row: any, di: number) => (Array.isArray(row) ? row : []).forEach((v: any, pi: number) => { if (v === 0) u.add(`${di},${pi}`); }));
    for (const p of d.grid_placements ?? []) {
      if (!match(p) || formatTrName(p.subject_name || p.subject || '') === sfmt) continue;
      const day = Number(p.day ?? p.col ?? 0), per = Number(p.period ?? p.row ?? 0), dur = Number(p.duration ?? 1) || 1;
      for (let o = 0; o < dur; o++) u.add(`${day},${per + o}`);
    }
    return u.size;
  };
  const caps: number[] = [];
  for (const cn of targets) {
    const ent = (d.siniflar ?? []).find((c: any) => matchesClass(c.ad ?? '', cn) || matchesClass(cn, c.ad ?? ''));
    caps.push(total - unusable((p) => { const pc = String(p.class_name || p.class || '').trim(); return matchesClass(pc, cn) || matchesClass(cn, pc); }, ent?.timeoff));
  }
  if (card.teacher) {
    const tf = formatTrName(card.teacher);
    const ent = (d.ogretmenler ?? []).find((t: any) => formatTrName(t.ad ?? '') === tf);
    caps.push(total - unusable((p) => formatTrName(p.teacher_name || p.teacher || '') === tf, ent?.timeoff));
  }
  return caps.length ? Math.min(...caps) : null;
}

/** Kartın atamasını yeni dağılıma çevirir: tek satırda tutulur (type/distribution/duration). */
export async function changeDistribution(d: any, card: Unplaced, parts: number[]) {
  if (!parts.length || parts.some((x) => !(x > 0))) return;
  const cap = freeCapacity(d, card);
  const sum = parts.reduce((a, b) => a + b, 0);
  if (cap !== null && sum > cap) {
    await tell('Yeterli Boş Saat Yok', `'${card.subject}' dersi için seçilen ${parts.join('+')} dağılımı toplam ${sum} saat gerektiriyor.\n\nAncak ${card.className}${card.teacher ? ' / ' + card.teacher : ''} için çizelgede sadece ${cap} saat boş yer var.\n\nLütfen daha küçük bir dağılım seçin ya da önce çizelgede yer açın.`);
    return;
  }
  const s = formatTrName(card.subject), c = formatTrName(card.className), t = formatTrName(card.teacher);
  mutate(`${card.subject}: ${parts.join('+')}`, (x) => {
    const rows: any[] = x.atamalar ?? [];
    let idx = rows.map((a, i) => (rowMatches(a, s, c, t, card.teacher) ? i : -1)).filter((i) => i >= 0);
    if (!idx.length) idx = rows.map((a, i) => (formatTrName(a.subject || a.ders || '') === s ? i : -1)).filter((i) => i >= 0);
    if (!idx.length) return;
    const set = new Set(idx);
    const nr = { ...rows[idx[0]], type: parts.join('+'), distribution: [...parts], duration: sum, id: crypto.randomUUID() };
    syncKeys(nr);
    x.atamalar = [...rows.slice(0, idx[0]), nr, ...rows.filter((_, i) => i >= idx[0] && !set.has(i))];
    const sc = s, cc = c;
    x.loose_unplaced_cards = (x.loose_unplaced_cards ?? []).filter((lc: any) => !(formatTrName(lc.subject_name || '') === sc && (!cc || formatTrName(lc.class_name || '') === cc)));
    if (x.manual_unplaced_cards) x.manual_unplaced_cards = x.manual_unplaced_cards.filter((mc: any) => !(formatTrName(mc.subject_name || '') === sc && (!cc || formatTrName(mc.class_name || '') === cc)));
  });
  status(`'${card.subject}' dersi ${parts.join('+')} yapısına dönüştürüldü (${sum} saat).`);
}

/** İkiye Böl (2 → 1+1) / 2 Kartı Birleştir (1+1 → 2): mevcut dağılım üzerinden. */
export function currentParts(d: any, card: Unplaced): number[] | null {
  const s = formatTrName(card.subject), c = formatTrName(card.className), t = formatTrName(card.teacher);
  const a = (d.atamalar ?? []).find((x: any) => rowMatches(x, s, c, t, card.teacher));
  if (!a) return null;
  if (Array.isArray(a.distribution) && a.distribution.length) return a.distribution.map(Number);
  const tt = String(a.type ?? '').replace(/ /g, '');
  const p = tt.split('+').filter((x) => /^\d+$/.test(x)).map(Number);
  return p.length ? p : null;
}

export function splitParts(parts: number[] | null): number[] {
  if (parts && parts.includes(2)) { const i = parts.indexOf(2); return [...parts.slice(0, i), 1, 1, ...parts.slice(i + 1)]; }
  return [1, 1];
}
export function mergeParts(parts: number[] | null): number[] {
  if (parts && parts.filter((x) => x === 1).length >= 2) {
    const out: number[] = [];
    let ones = 0;
    for (const x of parts) { if (x === 1 && ones < 2) { ones++; if (ones === 2) out.push(2); } else out.push(x); }
    return out;
  }
  return [2];
}

export function deleteCardAssignment(card: Unplaced) {
  const s = formatTrName(card.subject), c = formatTrName(card.className), t = formatTrName(card.teacher);
  mutate(`${card.subject} ataması silindi`, (x) => { x.atamalar = (x.atamalar ?? []).filter((a: any) => !rowMatches(a, s, c, t, card.teacher)); });
}
