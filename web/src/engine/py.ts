// Python semantiği yardımcıları. Motor Python'dan satır satır taşındı; bir
// değerin "boş" sayılması, sayıya çevrilmesi ya da metne dönmesi iki dilde
// farklı davranırsa aynı veri iki motorda farklı çizelge üretir. Bu küçük
// yardımcılar o farkı tek yerde kapatır.

/** Python bool(v). */
export function truthy(v: unknown): boolean {
  if (v === null || v === undefined || v === false || v === 0 || v === '') return false;
  if (Array.isArray(v)) return v.length > 0;
  if (typeof v === 'object') return Object.keys(v as object).length > 0;
  return true;
}

/** Python str(v or "") — yanlış değerler boş metin. */
export function str(v: unknown): string {
  if (!truthy(v)) return '';
  return String(v);
}

/** Python int(v); dönüşemezse null (ValueError/TypeError yerine). */
export function toInt(v: unknown): number | null {
  if (typeof v === 'boolean') return v ? 1 : 0;
  if (typeof v === 'number') return Number.isFinite(v) ? Math.trunc(v) : null;
  if (typeof v === 'string') {
    const t = v.trim();
    return /^[+-]?\d+$/.test(t) ? parseInt(t, 10) : null;
  }
  return null;
}

/** " ".join(str(v or "").split()) */
export function text(v: unknown): string {
  return str(v).split(/\s+/).filter(Boolean).join(' ');
}

/** Python str.isdigit() (ASCII yeterli: veride başka rakam yok). */
export function isDigit(s: string): boolean {
  return /^\d+$/.test(s);
}

export function popcount(cells: Uint8Array): number {
  let n = 0;
  for (let i = 0; i < cells.length; i++) n += cells[i];
  return n;
}

/** (a, b) -> "a,b" anahtarı; Python tuple anahtarlarının karşılığı. */
export function key(...parts: (string | number)[]): string {
  return parts.join('\u0001');
}

export class DefaultMap<K, V> extends Map<K, V> {
  private readonly make: () => V;
  constructor(make: () => V) {
    super();
    this.make = make;
  }
  need(k: K): V {
    let v = this.get(k);
    if (v === undefined) {
      v = this.make();
      this.set(k, v);
    }
    return v;
  }
}

export function sum(xs: Iterable<number>): number {
  let s = 0;
  for (const x of xs) s += x;
  return s;
}

export function range(n: number): number[] {
  return Array.from({ length: Math.max(0, n) }, (_, i) => i);
}

/** Python divmod (negatif olmayan sayılar için). */
export function divmod(a: number, b: number): [number, number] {
  return [Math.floor(a / b), a % b];
}

export function sortedNums(xs: Iterable<number>): number[] {
  return [...xs].sort((a, b) => a - b);
}
