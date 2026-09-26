// CP-SAT çözücü işçisi. Arama sürerken bu işçi meşguldür; kullanıcı iptali
// motor işçisinin bunu sonlandırmasıyla olur (paket arama sırasında iptali
// işlemiyor).
import CpSat from 'or-tools-wasm/cp-sat';

self.onmessage = async (e: MessageEvent) => {
  const { id, bytes, params } = e.data as { id: number; bytes: Uint8Array; params: Record<string, unknown> };
  try {
    const r = await CpSat.solve(bytes, params as any);
    self.postMessage({ id, response: r.response });
  } catch (err) {
    self.postMessage({ id, error: String(err) });
  }
};
self.postMessage({ ready: true });
