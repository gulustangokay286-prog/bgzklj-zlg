// Uygulama durumu: açık çizelge (.roz verisi), görünüm, seçim, geri al/yinele,
// sorular ve otomatik kayıt. Tek dış kaynak, React'e useSyncExternalStore ile.
import { useSyncExternalStore } from 'react';
import * as db from './db.ts';
import type { View } from './model.ts';

export interface Dialog {
  title: string;
  body: string;               // düz metin; satırlar \n ile
  ok: string;
  cancel?: string;
  tone?: 'normal' | 'warn' | 'danger';
  /** Ön kontrol raporu gibi biçimli satırlar (isteğe bağlı). */
  lines?: { kind: string; text: string }[];
  note?: string;
  foot?: string;
  /** Metin girişi (promptText). */
  input?: { value: string; placeholder?: string };
  resolve: (v: boolean) => void;
}

export interface DragInfo { lesson: any; duration: number; origin: { day: number; period: number } | null; blockId: string; fromDock: boolean; entries?: any[]; looseId?: string }

export interface State {
  data: any | null;
  name: string;
  view: View;
  selectedRow: string | null;
  status: string;
  dirty: boolean;
  savedAt: number | null;
  undo: { label: string; snap: string }[];
  redo: { label: string; snap: string }[];
  dialog: Dialog | null;
  drag: DragInfo | null;
  plannerOpen: boolean;
  resetOpen: boolean;
  /** Açık pencereler, alttan üste (masaüstündeki iç içe diyaloglar gibi). */
  screens: Screen[];
  zoom: number;
  /** Açık çizelgenin kurumu ve sürümü (Anasayfa / Kaydet). */
  inst: { slug: string; name: string; color: string } | null;
  versionId: string | null;
}

/** Açık pencere (masaüstündeki diyalogların karşılığı). */
export type Screen = ScreenKind & { key?: number };
type ScreenKind =
  | { kind: 'master'; tab: number }
  | { kind: 'relations' } | { kind: 'electives' } | { kind: 'school'; tab?: string } | { kind: 'assignTeacher'; teacher?: string }
  | { kind: 'assignClass'; className: string } | { kind: 'assignSubject'; subject: string; className?: string }
  | { kind: 'timeoff'; entityKind: 'siniflar' | 'ogretmenler' | 'derslikler'; name: string; index?: number } | { kind: 'constraints'; target: 'ogretmen' | 'sinif'; name?: string }
  | { kind: 'groups' } | { kind: 'precheck' } | { kind: 'verify' } | { kind: 'statistics' } | { kind: 'advisor' }
  | { kind: 'constraintsOverview' } | { kind: 'print'; preset?: any } | { kind: 'export'; mail?: boolean } | { kind: 'compare' }
  | { kind: 'rooms' } | { kind: 'assignmentList' } | { kind: 'info' } | { kind: 'faq' } | { kind: 'tips' }
  | { kind: 'newSchedule'; inst?: string } | { kind: 'wizard' } | { kind: 'versions' } | { kind: 'home' } | { kind: 'settings' } | { kind: 'improve' };

let state: State = {
  data: null, name: '', view: 'classes', selectedRow: null, status: '', dirty: false, savedAt: null,
  undo: [], redo: [], dialog: null, drag: null, plannerOpen: false, resetOpen: false, screens: [], zoom: 1, inst: null, versionId: null,
};
const listeners = new Set<() => void>();

export function getState() { return state; }

export function setState(patch: Partial<State>) {
  state = { ...state, ...patch };
  for (const l of listeners) l();
}

export function useApp<T>(sel: (s: State) => T): T {
  return useSyncExternalStore((cb) => { listeners.add(cb); return () => { listeners.delete(cb); }; }, () => sel(state));
}

// ── veri ───────────────────────────────────────────────────────────────────
// Geri al/yinele TÜM veriyi kapsar: tanım ekranlarındaki değişiklikler de geri alınır.
const snapOf = (d: any) => JSON.stringify(d);

let saveTimer: ReturnType<typeof setTimeout> | null = null;
function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(async () => {
    if (!state.data) return;
    await db.set('current', { name: state.name, data: state.data, at: Date.now(), inst: state.inst, versionId: state.versionId });
    setState({ savedAt: Date.now() });
  }, 400);
}

export function load(data: any, name: string, meta?: { inst?: State['inst']; versionId?: string | null }) {
  setState({
    data, name, undo: [], redo: [], dirty: false, selectedRow: null, screens: [], status: `${name} açıldı.`,
    inst: meta?.inst ?? null, versionId: meta?.versionId ?? null,
  });
  scheduleSave();
}

/** Dosyayı kapatır (main_window._act_close): geçmiş de kapanır. */
export function closeFile() {
  setState({ data: null, name: '', undo: [], redo: [], dirty: false, selectedRow: null, screens: [], inst: null, versionId: null, status: 'Dosya kapatıldı.' });
  void db.del('current');
}

export async function restore(): Promise<boolean> {
  const saved = await db.get<{ name: string; data: any; at: number; inst?: State['inst']; versionId?: string | null }>('current');
  if (!saved?.data) return false;
  setState({ data: saved.data, name: saved.name, savedAt: saved.at, inst: saved.inst ?? null, versionId: saved.versionId ?? null, status: `${saved.name} — son çalışma geri yüklendi.` });
  return true;
}

/** Veriyi değiştiren her işlem buradan geçer: geri alınabilir ve kaydedilir. */
export function mutate(label: string, fn: (data: any) => void) {
  if (!state.data) return;
  const before = snapOf(state.data);
  const next = structuredClone(state.data);
  fn(next);
  setState({ data: next, dirty: true, undo: [...state.undo.slice(-49), { label, snap: before }], redo: [] });
  scheduleSave();
}

function applySnap(snap: string) {
  return JSON.parse(snap);
}

export function undo() {
  const u = state.undo[state.undo.length - 1];
  if (!u || !state.data) return;
  const cur = snapOf(state.data);
  setState({ data: applySnap(u.snap), undo: state.undo.slice(0, -1), redo: [...state.redo, { label: u.label, snap: cur }], status: `Geri alındı: ${u.label}` });
  scheduleSave();
}

export function redo() {
  const r = state.redo[state.redo.length - 1];
  if (!r || !state.data) return;
  const cur = snapOf(state.data);
  setState({ data: applySnap(r.snap), redo: state.redo.slice(0, -1), undo: [...state.undo, { label: r.label, snap: cur }], status: `Yinelendi: ${r.label}` });
  scheduleSave();
}

export function status(msg: string) { setState({ status: msg }); }

let screenSeq = 0;
/** Yeni pencereyi en üste açar; alttakiler durumlarını korur. */
export function openScreen(screen: Screen) {
  const s = { ...screen, key: ++screenSeq } as Screen;
  setState({ screens: [...state.screens, s] });
}
/** En üstteki pencereyi kapatır. */
export function closeScreen() { setState({ screens: state.screens.slice(0, -1) }); }
export function closeAllScreens() { setState({ screens: [] }); }

/** Kullanıcıya evet/hayır sorusu (masaüstündeki QMessageBox karşılığı). */
export function ask(o: Omit<Dialog, 'resolve'>): Promise<boolean> {
  return new Promise((resolve) => setState({ dialog: { ...o, resolve: (v) => { setState({ dialog: null }); resolve(v); } } }));
}

/** Tek satırlık metin sorar (QInputDialog karşılığı); vazgeçilirse null. */
export async function promptText(title: string, body: string, value = '', placeholder = ''): Promise<string | null> {
  const input = { value, placeholder };
  const ok = await ask({ title, body, ok: 'Tamam', cancel: 'Vazgeç', input });
  return ok ? input.value : null;
}

export function tell(title: string, body: string) {
  return ask({ title, body, ok: 'Tamam' });
}

export function download(name: string, data: any) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name.endsWith('.roz') ? name : `${name}.roz`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  setState({ dirty: false, status: `${a.download} indirildi.` });
}
