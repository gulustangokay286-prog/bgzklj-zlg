// Node ortamı: CP-SAT doğrudan (or-tools-wasm), tabu şeritleri worker_threads.
import { readFileSync } from 'node:fs';
import { availableParallelism } from 'node:os';
import { Worker } from 'node:worker_threads';
import CpSat from 'or-tools-wasm/cp-sat';
import { setBackend, setDefaultWorkers, toResult } from '../src/engine/cp.ts';
import type { CpParams, Model } from '../src/engine/cp.ts';
import { setLaneRunner } from '../src/engine/tabu.ts';

export const stats = { cpCalls: 0, cpBuildMs: 0, cpSolveMs: 0 };

export function setupNode(opts: { cpWorkers?: number } = {}) {
  setDefaultWorkers(opts.cpWorkers ?? 8);
  setBackend({
    async solve(model: Model, params: CpParams) {
      stats.cpCalls++;
      let t = performance.now();
      const bytes = model.encode();
      stats.cpBuildMs += performance.now() - t;
      t = performance.now();
      const r = await CpSat.solve(bytes, params as any);
      const dt = performance.now() - t;
      stats.cpSolveMs += dt;
      const res = toResult(r.response);
      if (process.env.DEBUG_CP) console.log(`    cp#${stats.cpCalls} vars=${model.domains.length} cons=${model.cons.length} t=${params.maxTimeInSeconds.toFixed(1)}s first=${!!params.stopAfterFirstSolution} -> ${res.status} obj=${res.objective} bound=${res.bound} ${(dt / 1000).toFixed(1)}s`);
      return res;
    },
  });
  const wasm = new WebAssembly.Module(readFileSync(new URL('../public/search.wasm', import.meta.url)));
  const lanes = availableParallelism();
  setLaneRunner({
    lanes: () => lanes,
    run(input, seconds, seed, onLine, shouldStop) {
      return new Promise((resolve, reject) => {
        const w = new Worker(new URL('./lane-node.ts', import.meta.url), { workerData: { wasm, input, seconds, seed } });
        let done = false;
        const finish = () => { if (!done) { done = true; clearInterval(timer); resolve(); } };
        const timer = setInterval(() => { if (shouldStop()) { w.terminate(); finish(); } }, 20);
        w.on('message', (m: any) => {
          if (m.line) { try { onLine(m.line); } catch (e) { reject(e); } }
          if (m.done) finish();
        });
        w.on('error', (e) => { clearInterval(timer); reject(e); });
        w.on('exit', finish);
      });
    },
  });
}
