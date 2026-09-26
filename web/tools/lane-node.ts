// Node'da tek tabu şeridi (worker_threads).
import { parentPort, workerData } from 'node:worker_threads';
import { runTabu } from '../src/engine/wasi.ts';

const { wasm, input, seconds, seed } = workerData as { wasm: WebAssembly.Module; input: string; seconds: number; seed: number };
runTabu(wasm, new TextEncoder().encode(input), seconds, seed, (line) => parentPort!.postMessage({ line }));
parentPort!.postMessage({ done: true });
