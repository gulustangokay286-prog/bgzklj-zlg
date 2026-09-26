// CP-SAT modeli kurucu (CpModelProto) ve çözücü arka ucu.
//
// Python tarafı ortools.sat.python.cp_model kullanıyor; burada modeli doğrudan
// protokol biçiminde kuruyoruz ve or-tools-wasm ile çözüyoruz. Literal
// gösterimi CP-SAT'inkiyle aynı: v >= 0 değişken, -v-1 onun değili.
//
// Paketin çözüm geri çağrıları CANLI değil (arama bitince toplu gelir) ve
// arama sürerken iptal işlemez. Bu yüzden:
//   * Python'daki "tam çizelge bulununca dur" (StopSearch) yerine, hedefin
//     sert kısıt olduğu çağrılarda stop_after_first_solution kullanılır —
//     anlamı birebir aynıdır; diğerlerinde arama süre sonuna ya da kanıta
//     kadar sürer (sonuç aynı ya da daha iyi, süre biraz daha uzun).
//   * Kullanıcı iptali çözücüyü taşıyan işçinin kapatılmasıdır.

import { Writer, encodeCons, encodeHint, encodeObjective, encodeVars } from './pb.ts';

export type Ref = number;
export const NOT = (r: Ref): Ref => -r - 1;
const BIG = Number.MAX_SAFE_INTEGER;

/** Doğrusal ifade biriktirici: sum(katsayı * değişken) + sabit. */
export class Expr {
  terms = new Map<number, number>();
  k = 0;

  add(ref: Ref, coef = 1): this {
    if (!coef) return this;
    if (ref >= 0) this.terms.set(ref, (this.terms.get(ref) ?? 0) + coef);
    else {
      const v = -ref - 1;
      this.terms.set(v, (this.terms.get(v) ?? 0) - coef);
      this.k += coef;
    }
    return this;
  }

  addAll(refs: Iterable<Ref>, coef = 1): this {
    for (const r of refs) this.add(r, coef);
    return this;
  }

  plus(e: Expr, coef = 1): this {
    for (const [v, c] of e.terms) this.terms.set(v, (this.terms.get(v) ?? 0) + coef * c);
    this.k += coef * e.k;
    return this;
  }

  constant(c: number): this {
    this.k += c;
    return this;
  }

  static of(refs: Iterable<Ref> = [], coef = 1): Expr {
    return new Expr().addAll(refs, coef);
  }

  value(values: ArrayLike<number>): number {
    let s = this.k;
    for (const [v, c] of this.terms) s += c * values[v];
    return s;
  }
}

function linearParts(e: Expr): { vars: number[]; coeffs: number[] } {
  const vars: number[] = [], coeffs: number[] = [];
  for (const [v, c] of e.terms) if (c) { vars.push(v); coeffs.push(c); }
  return { vars, coeffs };
}

export interface Objective { vars: number[]; coeffs: number[]; offset: number; scalingFactor: number }

export class Model {
  domains: number[][] = [];
  cons: any[] = [];
  objective: Objective | null = null;
  hintVars: number[] = [];
  hintVals: number[] = [];

  bool(): Ref {
    this.domains.push([0, 1]);
    return this.domains.length - 1;
  }

  int(lb: number, ub: number): Ref {
    this.domains.push([lb, ub]);
    return this.domains.length - 1;
  }

  /** lb <= e <= ub (enf literalleri doğruysa). */
  linear(e: Expr, lb: number, ub: number, enf?: Ref[]): void {
    const { vars, coeffs } = linearParts(e);
    const lo = lb <= -BIG ? -BIG : lb - e.k, hi = ub >= BIG ? BIG : ub - e.k;
    if (!vars.length) {
      if (lo <= 0 && 0 <= hi) return;            // Python: Add(True)
      this.cons.push(enf && enf.length ? { boolOr: { literals: [] }, enforcementLiteral: enf } : { boolOr: { literals: [] } });
      return;
    }
    const c: any = { linear: { vars, coeffs, domain: [lo, hi] } };
    if (enf && enf.length) c.enforcementLiteral = enf;
    this.cons.push(c);
  }

  le(e: Expr, ub: number, enf?: Ref[]) { this.linear(e, -BIG, ub, enf); }
  ge(e: Expr, lb: number, enf?: Ref[]) { this.linear(e, lb, BIG, enf); }
  eq(e: Expr, v: number, enf?: Ref[]) { this.linear(e, v, v, enf); }

  boolOr(lits: Ref[], enf?: Ref[]) {
    const c: any = { boolOr: { literals: lits } };
    if (enf && enf.length) c.enforcementLiteral = enf;
    this.cons.push(c);
  }

  atMostOne(lits: Ref[]) {
    this.cons.push({ atMostOne: { literals: lits } });
  }

  implication(a: Ref, b: Ref) {
    this.cons.push({ boolOr: { literals: [b] }, enforcementLiteral: [a] });
  }

  /** target == max(refs) */
  maxEquality(target: Ref, refs: Ref[]) {
    const exprOf = (r: Ref) => (r >= 0 ? { vars: [r], coeffs: [1], offset: 0 } : { vars: [-r - 1], coeffs: [-1], offset: 1 });
    this.cons.push({ linMax: { target: exprOf(target), exprs: refs.map(exprOf) } });
  }

  maximize(e: Expr) {
    const { vars, coeffs } = linearParts(e);
    this.objective = { vars, coeffs: coeffs.map((c) => -c), offset: -e.k, scalingFactor: -1 };
  }

  minimize(e: Expr) {
    const { vars, coeffs } = linearParts(e);
    this.objective = { vars, coeffs, offset: e.k, scalingFactor: 1 };
  }

  hint(ref: Ref, value: number) {
    if (ref >= 0) { this.hintVars.push(ref); this.hintVals.push(value); }
    else { this.hintVars.push(-ref - 1); this.hintVals.push(1 - value); }
  }

  /** Taban kodlaması: çatallanan modeller bunun arkasına yalnızca eklerini yazar. */
  private base: { bytes: Uint8Array; nVars: number; nCons: number } | null = null;
  private sealed: Uint8Array | null = null;

  /** Taban modelin ucuz kopyası (Python model_cache: Proto().copy_from). */
  fork(): Model {
    if (!this.sealed) {
      const w = new Writer();
      if (this.base) w.bytes(this.base.bytes);
      encodeVars(w, this.domains, this.base?.nVars ?? 0);
      encodeCons(w, this.cons, this.base?.nCons ?? 0);
      this.sealed = w.result();
    }
    const m = new Model();
    m.domains = this.domains.slice();
    m.cons = this.cons.slice();
    m.objective = this.objective;
    m.hintVars = this.hintVars.slice();
    m.hintVals = this.hintVals.slice();
    m.base = { bytes: this.sealed, nVars: this.domains.length, nCons: this.cons.length };
    return m;
  }

  /** CpModelProto baytları (CpSat.solve'a doğrudan verilir). */
  encode(): Uint8Array {
    const w = new Writer();
    if (this.base) w.bytes(this.base.bytes);
    encodeVars(w, this.domains, this.base?.nVars ?? 0);
    encodeCons(w, this.cons, this.base?.nCons ?? 0);
    if (this.objective) encodeObjective(w, this.objective);
    encodeHint(w, this.hintVars, this.hintVals);
    return w.result();
  }

  proto(): any {
    const p: any = { variables: this.domains.map((d) => ({ domain: d })), constraints: this.cons };
    if (this.objective) p.objective = this.objective;
    if (this.hintVars.length) p.solutionHint = { vars: this.hintVars, values: this.hintVals };
    return p;
  }
}

export interface CpParams {
  maxTimeInSeconds: number;
  numWorkers: number;
  randomSeed?: number;
  stopAfterFirstSolution?: boolean;
  logSearchProgress?: boolean;
}

export interface CpResult {
  status: string;          // OPTIMAL | FEASIBLE | INFEASIBLE | MODEL_INVALID | UNKNOWN | CANCELLED
  values: number[] | null;
  objective: number;
  bound: number;
}

export interface CpBackend {
  solve(model: Model, params: CpParams, cancelled?: () => boolean): Promise<CpResult>;
}

export function toResult(response: any): CpResult {
  if (!response) return { status: 'UNKNOWN', values: null, objective: 0, bound: 0 };
  const status = typeof response.status === 'string' ? response.status
    : ['UNKNOWN', 'MODEL_INVALID', 'FEASIBLE', 'INFEASIBLE', 'OPTIMAL'][response.status ?? 0];
  const sol = response.solution && response.solution.length ? response.solution.map(Number) : null;
  return { status, values: sol, objective: Number(response.objectiveValue ?? 0), bound: Number(response.bestObjectiveBound ?? 0) };
}

let backend: CpBackend | null = null;

export function setBackend(b: CpBackend) {
  backend = b;
}

export function getBackend(): CpBackend {
  if (!backend) throw new Error('CP-SAT arka ucu kurulmadı');
  return backend;
}

/** Varsayılan iş parçacığı sayısı (Python: workers=8). */
export let defaultWorkers = 8;
export function setDefaultWorkers(n: number) {
  defaultWorkers = Math.max(1, n);
}
