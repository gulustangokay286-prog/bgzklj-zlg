// Motor işçisi: planlamanın tamamı burada, arayüzü dondurmadan koşar.
//   gelen : {type:'run', data, unlock} | {type:'answer', devam} | {type:'cancel'}
//   giden : {type:'progress'|'ask'|'conflict'|'done'|'error'|'status', ...}
import { setBackend, setDefaultWorkers, toResult } from '../engine/cp.ts';
import type { CpParams, CpResult, Model } from '../engine/cp.ts';
import { LockedConflict, runPlanner } from '../engine/engine.ts';
import { setLaneRunner } from '../engine/tabu.ts';

const post = (m: unknown) => (self as unknown as Worker).postMessage(m);
const cores = Math.max(2, navigator.hardwareConcurrency || 4);
let cancelled = false;
let answer: ((v: boolean) => void) | null = null;

// ── CP-SAT: ayrı işçide; iptal = işçiyi kapat ──
let cpWorker: Worker | null = null;
let cpReady: Promise<void> | null = null;
let seq = 0;
function cpw(): [Worker, Promise<void>] {
  if (!cpWorker) {
    cpWorker = new Worker(new URL('./cpsat.worker.ts', import.meta.url), { type: 'module' });
    const w = cpWorker;
    cpReady = new Promise((res) => {
      const h = (e: MessageEvent) => { if (e.data?.ready) { w.removeEventListener('message', h); res(); } };
      w.addEventListener('message', h);
    });
  }
  return [cpWorker, cpReady!];
}

setDefaultWorkers(Math.min(8, cores));
setBackend({
  async solve(model: Model, params: CpParams, isCancelled?: () => boolean): Promise<CpResult> {
    if (isCancelled?.()) return { status: 'CANCELLED', values: null, objective: 0, bound: 0 };
    const [w, ready] = cpw();
    await ready;
    const id = ++seq;
    const bytes = model.encode();
    return new Promise((resolve) => {
      let done = false;
      const finish = (r: CpResult) => {
        if (done) return;
        done = true;
        clearInterval(timer);
        w.removeEventListener('message', onMsg);
        resolve(r);
      };
      const onMsg = (e: MessageEvent) => {
        if (e.data?.id !== id) return;
        if (e.data.error) finish({ status: 'MODEL_INVALID', values: null, objective: 0, bound: 0 });
        else finish(toResult(e.data.response));
      };
      w.addEventListener('message', onMsg);
      const timer = setInterval(() => {
        if (isCancelled?.()) {
          w.terminate();
          cpWorker = null;
          finish({ status: 'CANCELLED', values: null, objective: 0, bound: 0 });
        }
      }, 200);
      w.postMessage({ id, bytes, params }, [bytes.buffer]);
    });
  },
});

// ── Tabu şeritleri: her şerit ayrı işçi ──
let wasmModule: Promise<WebAssembly.Module> | null = null;
const wasm = () => (wasmModule ??= WebAssembly.compileStreaming(fetch(new URL('/search.wasm', self.location.origin))));
setLaneRunner({
  lanes: () => cores,
  async run(input, seconds, seed, onLine, shouldStop) {
    const mod = await wasm();
    return new Promise<void>((resolve, reject) => {
      const w = new Worker(new URL('./tabu.worker.ts', import.meta.url), { type: 'module' });
      let done = false;
      const finish = () => { if (!done) { done = true; clearInterval(timer); w.terminate(); resolve(); } };
      const timer = setInterval(() => { if (shouldStop()) finish(); }, 20);
      w.onmessage = (e) => {
        if (e.data.line) { try { onLine(e.data.line); } catch (err) { done = true; clearInterval(timer); w.terminate(); reject(err); } }
        if (e.data.error) { done = true; clearInterval(timer); w.terminate(); reject(new Error(e.data.error)); }
        if (e.data.done) finish();
      };
      w.onerror = (e) => { done = true; clearInterval(timer); reject(new Error(e.message)); };
      w.postMessage({ wasm: mod, input, seconds, seed });
    });
  },
});

self.onmessage = async (e: MessageEvent) => {
  const m = e.data;
  if (m.type === 'cancel') { cancelled = true; answer?.(false); return; }
  if (m.type === 'answer') { answer?.(!!m.devam); answer = null; return; }
  if (m.type !== 'run') return;
  cancelled = false;
  const t0 = performance.now();
  post({ type: 'status', text: `Motor hazır · ${cores} çekirdek · ${crossOriginIsolated ? 'çok iş parçacıklı' : 'tek iş parçacıklı (başlıklar eksik)'}` });
  try {
    const out = await runPlanner(m.data, {
      lanes: cores,
      unlockConflictingLocks: !!m.unlock,
      cancelled: () => cancelled,
      progress: (placed, total, attempt) => post({ type: 'progress', placed, total, attempt, t: (performance.now() - t0) / 1000 }),
      askContinue: (info) => new Promise<boolean>((res) => { answer = res; post({ type: 'ask', info }); }),
    });
    post({ type: 'done', result: out, t: (performance.now() - t0) / 1000 });
  } catch (err: any) {
    if (err instanceof LockedConflict) post({ type: 'conflict', items: err.catismalar.map((k) => k.mesaj) });
    else post({ type: 'error', message: String(err?.message ?? err) });
  }
};
