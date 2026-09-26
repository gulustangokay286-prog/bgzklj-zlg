// Tek tabu şeridi: C++ aramasını (wasm) eşzamanlı çalıştırır, her iyileşme
// satırını anında iletir. İptal, bu işçinin sonlandırılmasıdır.
import { runTabu } from '../engine/wasi.ts';

self.onmessage = (e: MessageEvent) => {
  const { wasm, input, seconds, seed } = e.data as { wasm: WebAssembly.Module; input: string; seconds: number; seed: number };
  try {
    runTabu(wasm, new TextEncoder().encode(input), seconds, seed, (line) => self.postMessage({ line }));
    self.postMessage({ done: true });
  } catch (err) {
    self.postMessage({ error: String(err) });
  }
};
