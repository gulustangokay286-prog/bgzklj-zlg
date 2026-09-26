// Uygulama iskeleti: üst çubuk, ana çizelge, yerleştirilemeyenler, durum satırı.
import { useEffect, useRef } from 'react';
import { Dock } from './components/Dock.tsx';
import { DialogHost, PlannerSheet, ResetSheet } from './components/Dialogs.tsx';
import { Grid } from './components/Grid.tsx';
import { Ribbon } from './components/Ribbon.tsx';
import { ScreenHost } from './screens/index.tsx';
import { HomeBody } from './screens/Home.tsx';
import { ask, closeFile, getState, load, redo, restore, tell, undo, useApp } from './store.ts';
import { saveVersion } from './versions.ts';

const SAMPLES: string[] = import.meta.env.DEV ? ['birey_v161', 'bogazici_v227', 'bogazici_v229'] : [];

async function openFile(f: File) {
  try {
    const data = JSON.parse(await f.text());
    if (!data || typeof data !== 'object' || !Array.isArray(data.atamalar)) throw new Error('Bu dosya bir Chenkron (.roz) çizelgesi değil.');
    load(data, f.name.replace(/\.(roz|json)$/i, ''));
  } catch (e: any) {
    await tell('Dosya açılamadı', String(e?.message ?? e));
  }
}

async function openSample(name: string) {
  const r = await fetch(`/samples/${name}.roz`);
  load(await r.json(), name);
}

async function closeCurrent() {
  if (getState().dirty && !(await ask({ title: 'Dosyayı kapat', body: 'Son değişiklikler bir sürüm olarak kaydedilmedi. Kapatmadan önce kaydedilsin mi?', ok: 'Kaydet ve kapat', cancel: 'Kaydetmeden kapat' }))) {
    closeFile();
    return;
  }
  if (getState().dirty) await saveVersion();
  closeFile();
}

export function App() {
  const data = useApp((s) => s.data);
  const st = useApp((s) => s.status);
  const file = useRef<HTMLInputElement>(null);
  const open = () => file.current?.click();

  useEffect(() => {
    const q = new URLSearchParams(location.search).get('ornek');
    if (q && SAMPLES.includes(q)) void openSample(q);
    else void restore();
    const key = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      if (e.key === 'z' && !e.shiftKey) { e.preventDefault(); undo(); }
      else if (e.key === 'y' || (e.key === 'z' && e.shiftKey)) { e.preventDefault(); redo(); }
      else if (e.key === 's') { e.preventDefault(); if (getState().data) void saveVersion(); }
    };
    window.addEventListener('keydown', key);
    return () => window.removeEventListener('keydown', key);
  }, []);

  return (
    <div className="app">
      <Ribbon onOpen={open} onClose={() => void closeCurrent()} />
      {data ? <Grid /> : <div className="home-page"><HomeBody onOpenFile={open} /></div>}
      {data ? <Dock /> : <div />}
      <div className="statusbar"><span className="hint">{st}</span></div>
      <input id="roz-file" ref={file} type="file" accept=".roz,.json" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) void openFile(f); e.target.value = ''; }} />
      <ScreenHost />
      <ResetSheet />
      <PlannerSheet />
      <DialogHost />
    </div>
  );
}

