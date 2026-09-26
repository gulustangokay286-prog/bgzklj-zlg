import { defineConfig } from 'vite';
import type { Plugin } from 'vite';
import react from '@vitejs/plugin-react';

// CP-SAT çok iş parçacıklı çalışmak için SharedArrayBuffer ister; tarayıcı
// bunu yalnızca "cross-origin isolated" sayfaya verir. Aynı başlıklar
// yayında da verilmelidir (public/_headers ve vercel.json).
const isolation = {
  'Cross-Origin-Opener-Policy': 'same-origin',
  'Cross-Origin-Embedder-Policy': 'require-corp',
};

// or-tools-wasm yükleyicisi bütün çözücülerin (routing, mathopt, mp_solver...)
// wasm dosyalarına new URL(...) ile başvuruyor; Vite hepsini pakete koyuyor
// (~150 MB). Motor yalnızca CP-SAT kullanır: yükleyici CP-SAT'a indirgenir.
function trimOrTools(): Plugin {
  const CP_SAT_ONLY = `const runtimeAssets = {
  cp_sat_runtime: {
    jspi: {
      jsUrl: new URL("../wasm/cp_sat_runtime.js", import.meta.url).href,
      wasmUrl: new URL("../wasm/cp_sat_runtime.wasm", import.meta.url).href
    },
    asyncify: {
      jsUrl: new URL("../wasm/cp_sat_runtime_asyncify.js", import.meta.url).href,
      wasmUrl: new URL("../wasm/cp_sat_runtime_asyncify.wasm", import.meta.url).href
    }
  }
};
`;
  return {
    name: 'trim-or-tools',
    enforce: 'pre',
    transform(code, id) {
      if (!/or-tools-wasm[\\/]build[\\/]javascript[\\/]browser[\\/]runtime_loader\.js$/.test(id)) return null;
      const start = code.indexOf('const runtimeAssets = {');
      const end = code.indexOf('async function loadFactory');
      if (start < 0 || end < 0) this.error('or-tools-wasm runtime_loader.js beklenen biçimde değil; sürüm değişmiş olabilir.');
      return { code: code.slice(0, start) + CP_SAT_ONLY + code.slice(end), map: null };
    },
  };
}

export default defineConfig({
  plugins: [react(), trimOrTools()],
  server: { headers: isolation, port: 5199, strictPort: true },
  preview: { headers: isolation, port: 5199, strictPort: true },
  worker: { format: 'es', plugins: () => [trimOrTools()] },
  optimizeDeps: {
    // Paket wasm dosyalarını import.meta.url'e göre buluyor; ön paketleme
    // (esbuild) bu yolları bozuyor.
    exclude: ['or-tools-wasm'],
    include: ['or-tools-wasm > protobufjs'],
  },
  build: { target: 'es2022', chunkSizeWarningLimit: 2000 },
});
