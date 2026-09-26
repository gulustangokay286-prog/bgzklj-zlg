// C++ tabu aramasını (scheduler/native/search.cpp, wasm32-wasi) çalıştıran en
// küçük WASI köprüsü. Masaüstündeki süreçle aynı sözleşme:
//   argv  : [ad, saniye, tohum]
//   stdin : problem metni
//   stdout: "P ..." / "F ..." satırları (her iyileşmede bir satır)
// Arama eşzamanlıdır; çağıran işçi bu süre boyunca meşguldür. Satırlar
// üretildikçe onLine ile dışarı verilir, iptal işçinin sonlandırılmasıdır.

const ESUCCESS = 0, EBADF = 8, ESPIPE = 70;

class Exit extends Error {
  code: number;
  constructor(code: number) {
    super(`exit ${code}`);
    this.code = code;
  }
}

export function runTabu(module: WebAssembly.Module, input: Uint8Array, seconds: number, seed: number,
  onLine: (line: string) => void): number {
  const args = ['search', String(seconds), String(seed)].map((a) => new TextEncoder().encode(a + '\0'));
  let memory: WebAssembly.Memory;
  let inPos = 0;
  let pending = '';
  const dec = new TextDecoder();
  const view = () => new DataView(memory.buffer);
  const bytes = () => new Uint8Array(memory.buffer);
  const now = () => (typeof performance !== 'undefined' ? performance.now() : Date.now());
  const origin = Date.now() - now();

  const imports = {
    wasi_snapshot_preview1: {
      args_sizes_get(argcPtr: number, bufSizePtr: number) {
        view().setUint32(argcPtr, args.length, true);
        view().setUint32(bufSizePtr, args.reduce((s, a) => s + a.length, 0), true);
        return ESUCCESS;
      },
      args_get(argvPtr: number, bufPtr: number) {
        let off = bufPtr;
        args.forEach((a, i) => {
          view().setUint32(argvPtr + i * 4, off, true);
          bytes().set(a, off);
          off += a.length;
        });
        return ESUCCESS;
      },
      environ_sizes_get(countPtr: number, sizePtr: number) {
        view().setUint32(countPtr, 0, true);
        view().setUint32(sizePtr, 0, true);
        return ESUCCESS;
      },
      environ_get() {
        return ESUCCESS;
      },
      clock_time_get(id: number, _precision: bigint, outPtr: number) {
        const ms = id === 0 ? origin + now() : now();
        view().setBigUint64(outPtr, BigInt(Math.round(ms * 1e6)), true);
        return ESUCCESS;
      },
      fd_fdstat_get(fd: number, statPtr: number) {
        if (fd > 2) return EBADF;
        const v = view();
        v.setUint8(statPtr, 2);            // karakter aygıtı
        v.setUint16(statPtr + 2, 0, true);
        v.setBigUint64(statPtr + 8, 0xffffffffffffffffn, true);
        v.setBigUint64(statPtr + 16, 0xffffffffffffffffn, true);
        return ESUCCESS;
      },
      fd_seek() {
        return ESPIPE;
      },
      fd_close() {
        return ESUCCESS;
      },
      fd_read(fd: number, iovs: number, iovsLen: number, nreadPtr: number) {
        if (fd !== 0) return EBADF;
        let total = 0;
        const v = view();
        for (let i = 0; i < iovsLen; i++) {
          const ptr = v.getUint32(iovs + i * 8, true), len = v.getUint32(iovs + i * 8 + 4, true);
          const n = Math.min(len, input.length - inPos);
          if (n <= 0) break;
          bytes().set(input.subarray(inPos, inPos + n), ptr);
          inPos += n;
          total += n;
          if (n < len) break;
        }
        v.setUint32(nreadPtr, total, true);
        return ESUCCESS;
      },
      fd_write(fd: number, iovs: number, iovsLen: number, nwrittenPtr: number) {
        let total = 0;
        const v = view();
        for (let i = 0; i < iovsLen; i++) {
          const ptr = v.getUint32(iovs + i * 8, true), len = v.getUint32(iovs + i * 8 + 4, true);
          if (fd === 1) pending += dec.decode(bytes().subarray(ptr, ptr + len));
          total += len;
        }
        if (fd === 1) {
          let nl: number;
          while ((nl = pending.indexOf('\n')) >= 0) {
            const line = pending.slice(0, nl);
            pending = pending.slice(nl + 1);
            if (line) onLine(line);
          }
        }
        v.setUint32(nwrittenPtr, total, true);
        return ESUCCESS;
      },
      proc_exit(code: number) {
        throw new Exit(code);
      },
    },
  };
  const instance = new WebAssembly.Instance(module, imports as unknown as WebAssembly.Imports);
  memory = instance.exports.memory as WebAssembly.Memory;
  try {
    (instance.exports._start as () => void)();
  } catch (e) {
    if (e instanceof Exit) return e.code;
    throw e;
  }
  if (pending) onLine(pending);
  return 0;
}
