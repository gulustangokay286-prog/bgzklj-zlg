// scheduler/native_bridge.py — C++ tabu aramasının şeritleri.
// Masaüstünde her şerit ayrı bir süreçti; burada ayrı bir işçi (Worker).
import type { Problem } from './problem.ts';

export interface TabuRec {
  hours: number;
  steps: number;
  restarts: number;
  soft_cost: number;
  positions: number[];
  cancelled?: boolean;
}

/** Tek şerit: problemi verilen süre ve tohumla çalıştırır, satırları iletir.
 *  shouldStop doğru dönünce şerit sonlandırılır (süreç terminate eşdeğeri). */
export interface LaneRunner {
  run(input: string, seconds: number, seed: number, onLine: (line: string) => void,
    shouldStop: () => boolean): Promise<void>;
  lanes(): number;
}

let runner: LaneRunner | null = null;
export function setLaneRunner(r: LaneRunner) { runner = r; }
export function getLaneRunner(): LaneRunner {
  if (!runner) throw new Error('Tabu şerit çalıştırıcısı kurulmadı');
  return runner;
}

const empty = (n: number): TabuRec => ({ hours: 0, steps: 0, restarts: 0, soft_cost: 0, positions: new Array(n).fill(-1) });

export async function search(problem: Problem, seconds: number, seed: number, upperBound: number,
  o: { progress?: (r: TabuRec) => void; cancelled?: () => boolean; input?: string } = {}): Promise<TabuRec> {
  const n = problem.world.cards.length;
  let best: TabuRec | null = null;
  let stopped = false;
  const input = o.input ?? problem.write(Math.max(0, seconds), (seed & 0xffffffff) >>> 0, upperBound);
  const readLine = (line: string) => {
    const v = line.trim().split(/\s+/);
    if (!v.length || (v[0] !== 'P' && v[0] !== 'F')) return;
    if (v.length !== n + 5) throw new Error('C++ motorundan eksik sonuç geldi');
    best = { hours: +v[1], steps: +v[2], restarts: +v[3], soft_cost: +v[4], positions: v.slice(5).map(Number) };
    o.progress?.(best);
  };
  await getLaneRunner().run(input, Math.max(0, seconds), seed & 0x7fffffff, readLine, () => {
    if (!stopped && o.cancelled?.()) stopped = true;
    return stopped;
  });
  const out: TabuRec = best ?? empty(n);
  out.cancelled = stopped;
  return out;
}

/** Aynı problemi FARKLI TOHUMLARLA aynı anda arar; ilk tam sonucu alır. */
export async function searchPortfolio(problem: Problem, seconds: number, seeds: number[], upperBound: number,
  o: { progress?: (r: TabuRec) => void; cancelled?: () => boolean } = {}): Promise<TabuRec> {
  let found = false;
  let best: TabuRec | null = null;
  const stopRequested = () => found || !!o.cancelled?.();
  // Bütün şeritler TEK bir problem metnini paylaşır; tohum ayrı verilir.
  const shared = problem.write(Math.max(0, seconds), 1, upperBound);
  const workers = Math.max(1, Math.min(seeds.length, getLaneRunner().lanes()));
  const queue = [...seeds];
  const lane = async () => {
    for (;;) {
      const seed = queue.shift();
      if (seed === undefined) return;
      const rec = await search(problem, seconds, seed, upperBound, { progress: o.progress, cancelled: stopRequested, input: shared });
      if (best === null || rec.hours > best.hours || (rec.hours === best.hours && rec.soft_cost < best.soft_cost)) best = rec;
      if (rec.hours >= upperBound) found = true;
    }
  };
  await Promise.all(Array.from({ length: workers }, lane));
  const rec: TabuRec = best ?? empty(problem.world.cards.length);
  rec.cancelled = !!o.cancelled?.();
  return rec;
}
