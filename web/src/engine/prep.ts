// scheduler/worker.py (hazirla) ve auto_scheduler._build_teacher_timeoff_map.
// Kurumlar bağımsızdır: başka kurumun hiçbir verisi okunmaz.
import { CLOSED, classesOf, getMatrix, gridDimensions } from './data.ts';
import type { Store } from './data.ts';
import { matchesClass, normClass, normTeacher } from './norm.ts';
import { toInt, truthy } from './py.ts';

export interface Prepared {
  data: Store;
  D: number;
  P: number;
  selected: string[];
  engel: Map<string, [number, number][]>;
  others: any[];
}

function teacherTimeoffMap(data: Store): Map<string, Set<string>> {
  const blocked = new Map<string, Set<string>>();
  for (const t of (truthy(data.ogretmenler) ? data.ogretmenler : [])) {
    if (!t || typeof t !== 'object' || Array.isArray(t)) continue;
    const tAd = String((truthy(t.ad) ? t.ad : truthy(t.name) ? t.name : '') ?? '').trim();
    if (!tAd) continue;
    const k = normTeacher(tAd);
    const m = getMatrix(t, tAd, data);
    for (let d = 0; d < m.length; d++) for (let p = 0; p < m[d].length; p++) {
      if (m[d][p] === CLOSED) {
        if (!blocked.has(k)) blocked.set(k, new Set());
        blocked.get(k)!.add(`${d},${p}`);
      }
    }
  }
  return blocked;
}

export function hazirla(dataIn: Store, targetClass: string | null = null): Prepared {
  const data: Store = structuredClone(dataIn);
  const [D, P] = gridDimensions(data);
  const names: string[] = (data.siniflar ?? []).map((c: any) => (truthy(c?.ad) ? c.ad : c?.name));
  const selected = !targetClass ? [...names] : names.filter((n) => matchesClass(n, targetClass));
  if (!selected.length) throw new Error('Planlanacak sınıf bulunamadı');
  if (!truthy(data.atamalar)) throw new Error('Herhangi bir ders ataması bulunamadı.');
  for (let iter = 0; iter < names.length; iter++) {
    let changed = false;
    for (const a of data.atamalar ?? []) {
      const members = classesOf(a);
      if (selected.some((n) => members.some((m) => matchesClass(n, m)))) {
        for (const n of names) {
          if (!selected.includes(n) && members.some((m) => matchesClass(n, m))) { selected.push(n); changed = true; }
        }
      }
    }
    if (!changed) break;
  }
  const closed = teacherTimeoffMap(data);
  const cross = new Map<string, Set<string>>();
  const others: any[] = [];
  const selectedKeys = new Set(selected.map(normClass));
  for (const pl of data.grid_placements ?? []) {
    if (selectedKeys.has(normClass(truthy(pl.class_name) ? pl.class_name : pl.class))) continue;
    others.push(pl);
    const k = normTeacher(truthy(pl.teacher_name) ? pl.teacher_name : pl.teacher);
    const d = toInt('day' in pl ? pl.day : ('col' in pl ? pl.col : 0)) ?? 0;
    const p = toInt('period' in pl ? pl.period : ('row' in pl ? pl.row : 0)) ?? 0;
    const dur = toInt(truthy(pl.duration) ? pl.duration : 1) ?? 1;
    for (let off = 0; off < dur; off++) {
      if (!cross.has(k)) cross.set(k, new Set());
      cross.get(k)!.add(`${d},${p + off}`);
    }
  }
  const engel = new Map<string, [number, number][]>();
  for (const t of data.ogretmenler ?? []) {
    const name = truthy(t?.ad) ? t.ad : t?.name;
    const k = normTeacher(name);
    const ek = new Set([...(closed.get(k) ?? []), ...(cross.get(k) ?? [])]);
    if (ek.size) {
      const cells: [number, number][] = [];
      for (const s of ek) {
        const [d, p] = s.split(',').map(Number);
        if (d >= 0 && d < D && p >= 0 && p < P) cells.push([d, p]);
      }
      engel.set(name, cells);
    }
  }
  return { data, D, P, selected, engel, others };
}
