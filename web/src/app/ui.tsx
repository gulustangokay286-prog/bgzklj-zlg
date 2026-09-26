// Ortak arayüz parçaları: pencere, düğme, alanlar, renk seçici, simgeler.
import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';

export function Window({ title, subtitle, onClose, width = 900, children, footer, className = '' }: {
  title: string; subtitle?: string; onClose: () => void; width?: number; children: ReactNode; footer?: ReactNode; className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') { e.stopPropagation(); onClose(); } };
    const el = ref.current;
    el?.addEventListener('keydown', onKey);
    el?.focus();
    return () => el?.removeEventListener('keydown', onKey);
  }, [onClose]);
  return (
    <div className="overlay win-overlay">
      <div className={`win ${className}`} style={{ width: `min(${width}px, calc(100vw - 24px))` }} ref={ref} tabIndex={-1} role="dialog" aria-modal="true" aria-label={title}>
        <div className="win-head">
          <div>
            <div className="win-title">{title}</div>
            {subtitle && <div className="win-sub">{subtitle}</div>}
          </div>
          <button className="win-x" onClick={onClose} aria-label="Kapat">×</button>
        </div>
        <div className="win-body">{children}</div>
        {footer && <div className="win-foot">{footer}</div>}
      </div>
    </div>
  );
}

export function Btn({ kind = 'default', children, ...rest }: { kind?: 'default' | 'primary' | 'danger' | 'ghost' } & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={`btn btn-${kind}`} {...rest}>{children}</button>;
}

export function Field({ label, children, hint, wide }: { label: string; children: ReactNode; hint?: string; wide?: boolean }) {
  return (
    <label className={`field${wide ? ' wide' : ''}`}>
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

export function Section({ title, children, actions }: { title: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <section className="section">
      <div className="section-head"><span>{title}</span>{actions}</div>
      <div className="section-body">{children}</div>
    </section>
  );
}

export const PALETTE = ['#E53935', '#D81B60', '#8E24AA', '#5E35B1', '#3949AB', '#1E88E5', '#039BE5', '#00ACC1', '#00897B',
  '#43A047', '#7CB342', '#C0CA33', '#FDD835', '#FFB300', '#FB8C00', '#F4511E', '#6D4C41', '#757575', '#546E7A',
  '#C4C4F0', '#A30F37', '#27AE60', '#F39C12', '#2563EB'];

export function ColorField({ value, onChange }: { value: string; onChange: (c: string) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="colorfield">
      <button type="button" className="swatch big" style={{ background: value }} onClick={() => setOpen(!open)} aria-label="Renk seç" />
      <code>{String(value).toUpperCase()}</code>
      <Btn type="button" onClick={() => setOpen(!open)}>Değiştir…</Btn>
      {open && (
        <div className="palette">
          {PALETTE.map((c) => <button type="button" key={c} className={`swatch${c.toUpperCase() === String(value).toUpperCase() ? ' on' : ''}`} style={{ background: c }} onClick={() => { onChange(c); setOpen(false); }} aria-label={c} />)}
          <label className="swatch custom" title="Özel renk"><input type="color" value={/^#[0-9a-f]{6}$/i.test(value) ? value : '#2563eb'} onChange={(e) => onChange(e.target.value.toUpperCase())} />+</label>
        </div>
      )}
    </div>
  );
}

/** Özel alanlar (CustomFieldsDialog) — anahtar/değer listesi. */
export function CustomFields({ value, onChange }: { value: Record<string, string>; onChange: (v: Record<string, string>) => void }) {
  const entries = Object.entries(value ?? {});
  const [k, setK] = useState('');
  const [v, setV] = useState('');
  return (
    <div className="kv">
      {entries.length === 0 && <div className="muted small">Özel alan yok.</div>}
      {entries.map(([key, val]) => (
        <div className="kv-row" key={key}>
          <span className="kv-k">{key}</span>
          <input value={val} onChange={(e) => onChange({ ...value, [key]: e.target.value })} />
          <button type="button" className="icon-btn" onClick={() => { const n = { ...value }; delete n[key]; onChange(n); }} aria-label="Sil">×</button>
        </div>
      ))}
      <div className="kv-row">
        <input placeholder="Alan adı" value={k} onChange={(e) => setK(e.target.value)} />
        <input placeholder="Değer" value={v} onChange={(e) => setV(e.target.value)} />
        <Btn type="button" disabled={!k.trim()} onClick={() => { onChange({ ...value, [k.trim()]: v }); setK(''); setV(''); }}>Ekle</Btn>
      </div>
    </div>
  );
}

/** Çoklu seçim (arama + onay kutuları). */
export function MultiSelect({ options, value, onChange, placeholder = 'Ara…', height = 180 }: {
  options: string[]; value: string[]; onChange: (v: string[]) => void; placeholder?: string; height?: number;
}) {
  const [q, setQ] = useState('');
  const shown = options.filter((o) => !q || o.toLocaleLowerCase('tr').includes(q.toLocaleLowerCase('tr')));
  return (
    <div className="multi">
      <input className="multi-q" placeholder={placeholder} value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="multi-list" style={{ maxHeight: height }}>
        {shown.map((o) => (
          <label key={o} className="multi-item">
            <input type="checkbox" checked={value.includes(o)} onChange={(e) => onChange(e.target.checked ? [...value, o] : value.filter((x) => x !== o))} />
            <span>{o}</span>
          </label>
        ))}
        {!shown.length && <div className="muted small">Sonuç yok.</div>}
      </div>
    </div>
  );
}

/** Zaman tablosu küçük önizlemesi (MiniTimeoffGridWidget). */
export function MiniGrid({ matrix, D, P }: { matrix: number[][]; D: number; P: number }) {
  const cell = Math.max(3, Math.min(6, Math.floor(60 / Math.max(D, P))));
  return (
    <span className="mini" style={{ gridTemplateColumns: `repeat(${D}, ${cell}px)`, gridAutoRows: `${cell}px` }} aria-hidden>
      {Array.from({ length: P }, (_, p) => Array.from({ length: D }, (_, d) => (
        <i key={`${d}-${p}`} className={matrix?.[d]?.[p] === 0 ? 'x' : 'o'} />
      )))}
    </span>
  );
}

const ICONS: Record<string, string> = {
  home: 'M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
  file: 'M6 3h8l4 4v14H6zM14 3v4h4',
  open: 'M3 7h6l2 2h10v10H3z',
  save: 'M5 3h11l3 3v15H5zM8 3v5h7V3M8 21v-7h8v7',
  undo: 'M9 7L4 12l5 5M4 12h11a5 5 0 0 1 0 10h-3',
  redo: 'M15 7l5 5-5 5M20 12H9a5 5 0 0 0 0 10h3',
  print: 'M7 9V3h10v6M6 18H4v-7h16v7h-2M7 14h10v7H7z',
  eye: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zm10-3a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
  book: 'M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM6 17h13',
  users: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8',
  door: 'M5 21V3h11v18M3 21h18M13 12h.01',
  teacher: 'M22 10L12 5 2 10l10 5 10-5zM6 12v5c3 2 9 2 12 0v-5',
  choice: 'M4 6h16M4 12h10M4 18h7M18 15l2 2 3-4',
  link: 'M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1',
  check: 'M9 12l2 2 4-4M12 22a10 10 0 1 1 0-20 10 10 0 0 1 0 20z',
  magic: 'M15 4V2M15 16v-2M8 9h2M20 9h2M17.8 11.8L19 13M15 9h.01M17.8 6.2L19 5M3 21l9-9M12.2 6.2L11 5',
  cloud: 'M18 10h-1.3A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z',
  trash: 'M3 6h18M8 6V4h8v2M6 6l1 15h10l1-15',
  school: 'M3 21h18M5 21V10l7-5 7 5v11M9 21v-6h6v6',
  help: 'M12 22a10 10 0 1 1 0-20 10 10 0 0 1 0 20zM9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01',
  clock: 'M12 22a10 10 0 1 1 0-20 10 10 0 0 1 0 20zM12 6v6l4 2',
  hash: 'M4 9h16M4 15h16M10 3L8 21M16 3l-2 18',
  branch: 'M6 3v12M18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18 9a9 9 0 0 1-9 9',
  chart: 'M3 3v18h18M7 14l4-4 3 3 5-6',
  export: 'M12 3v12M8 7l4-4 4 4M5 21h14',
  compare: 'M8 3v18M16 3v18M3 8h5M16 16h5',
  mail: 'M3 5h18v14H3zM3 5l9 7 9-7',
  settings: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-2.9 1.2V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-2.9-1.2l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0-1.2-2.9H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.2-2.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 2.9-1.2V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 2.9 1.2l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0 1.2 2.9H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z',
  zoom: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3M11 8v6M8 11h6',
  week: 'M3 5h18v16H3zM3 10h18M8 3v4M16 3v4',
  grid: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
  plus: 'M12 5v14M5 12h14',
  edit: 'M4 20h4L20 8l-4-4L4 16zM14 6l4 4',
  minus: 'M5 12h14',
  up: 'M12 19V5M5 12l7-7 7 7',
  down: 'M12 5v14M19 12l-7 7-7-7',
  bulb: 'M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z',
  rooms: 'M3 21V8l9-5 9 5v13M9 21v-8h6v8',
  list: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
  versions: 'M12 8v4l3 3M3 12a9 9 0 1 0 3-6.7M3 3v5h5',
  x: 'M18 6L6 18M6 6l12 12',
};

export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d={ICONS[name] ?? ICONS.grid} />
    </svg>
  );
}
