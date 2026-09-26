// dialogs/report_selection_dialog.py (rapor seçimi) + dialogs/print_preview.py
// (Baskı Ön İzleme ve PDF Raporu). Yazdır / PDF Kaydet tarayıcının yazdırma
// penceresini açar (PDF olarak kaydet oradan seçilir).
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { renderToStaticMarkup } from 'react-dom/server';
import { PRINT_CSS, PRINT_ROOT_CSS } from '../print/css.ts';
import { ALL_CLASSES, ALL_TEACHERS, REPORT_MODES, isPortrait, isTeacherMode, natCmp, renderReport } from '../print/reports.tsx';
import type { ReportMode } from '../print/reports.tsx';
import { closeScreen, getState, useApp } from '../store.ts';
import { Btn, Window } from '../ui.tsx';

export interface PrintPreset { mode?: ReportMode; target?: string; entity?: 'class' | 'teacher' | 'class_list'; name?: string; direct?: boolean }

function ensureStyles() {
  if (document.getElementById('pp-style')) return;
  const s = document.createElement('style');
  s.id = 'pp-style';
  s.textContent = PRINT_CSS + PRINT_ROOT_CSS;
  document.head.appendChild(s);
}

function setPageSize(portrait: boolean) {
  let s = document.getElementById('pp-page-size') as HTMLStyleElement | null;
  if (!s) { s = document.createElement('style'); s.id = 'pp-page-size'; document.head.appendChild(s); }
  s.textContent = `@page { size: A4 ${portrait ? 'portrait' : 'landscape'}; margin: 0; }`;
}

function presetToSelection(p: PrintPreset | undefined): { mode: ReportMode; target: string } | null {
  if (!p) return null;
  if (p.mode) return { mode: p.mode, target: p.target ?? '' };
  if (p.entity === 'class') return { mode: 'Sınıf Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)', target: p.name ?? '' };
  if (p.entity === 'teacher') return { mode: 'Öğretmen Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)', target: p.name ?? '' };
  if (p.entity === 'class_list') return { mode: 'Sınıf Dersleri & Atama Listesi (Liste Formatı)', target: p.name ?? ALL_CLASSES };
  return null;
}

export function PrintScreen({ preset }: { preset?: PrintPreset }) {
  const direct = !!preset?.direct;
  const [sel, setSel] = useState<{ mode: ReportMode; target: string } | null>(() => presetToSelection(preset));
  if (!sel) return <ReportSelection direct={direct} onCancel={closeScreen} onOk={(s) => setSel(s)} />;
  return <Preview initial={sel} direct={direct} />;
}

// ════════════════════════════════════════════════════════════════════════════
// Yazdırma & Baskı Önizleme — rapor seçimi
// ════════════════════════════════════════════════════════════════════════════
type Opt = 'cls_carsaf' | 'cls_6' | 'cls_single' | 't_carsaf' | 't_6' | 't_asgn' | 't_load' | 't_single';

function ReportSelection({ direct, onOk, onCancel }: { direct: boolean; onOk: (s: { mode: ReportMode; target: string }) => void; onCancel: () => void }) {
  const data = useApp((s) => s.data);
  const st = getState();
  const classes = useMemo(() => (data.siniflar ?? []).map((c: any) => String(c.ad ?? '')).filter(Boolean).sort(natCmp) as string[], [data]);
  const teachers = useMemo(() => (data.ogretmenler ?? []).map((t: any) => String(t.ad ?? '')).filter(Boolean).sort() as string[], [data]);
  const [opt, setOpt] = useState<Opt>(() => (st.selectedRow ? (st.view === 'teachers' ? 't_single' : 'cls_single') : st.view === 'teachers' ? 't_carsaf' : 'cls_carsaf'));
  const [cls, setCls] = useState<string>(() => (st.view === 'classes' && st.selectedRow && classes.includes(st.selectedRow) ? st.selectedRow : classes[0] ?? ''));
  const [tea, setTea] = useState<string>(() => (st.view === 'teachers' && st.selectedRow && teachers.includes(st.selectedRow) ? st.selectedRow : teachers[0] ?? ''));
  const [clsSub, setClsSub] = useState<'carsaf' | 'single' | 'asgn'>('single');
  const [tSub, setTSub] = useState<'asgn' | 'single'>('single');
  const confirm = () => {
    const map: Record<Opt, () => { mode: ReportMode; target: string }> = {
      cls_carsaf: () => ({ mode: 'Toplu Çarşaf Liste : Sınıflar', target: ALL_CLASSES }),
      cls_6: () => ({ mode: "[BİREBİR] Tüm Sınıflar (Yatay Sayfada 6'lı Çizelge)", target: ALL_CLASSES }),
      cls_single: () => ({ mode: clsSub === 'carsaf' ? 'Toplu Çarşaf Liste : Sınıflar' : clsSub === 'single' ? 'Sınıf Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)' : 'Sınıf Dersleri & Atama Listesi (Liste Formatı)', target: cls }),
      t_carsaf: () => ({ mode: 'Toplu Çarşaf Liste : Öğretmenler', target: ALL_TEACHERS }),
      t_6: () => ({ mode: "[BİREBİR] Tüm Öğretmenler (Yatay Sayfada 6'lı Çizelge)", target: ALL_TEACHERS }),
      t_asgn: () => ({ mode: 'Sınıf Dersleri & Atama Listesi (Liste Formatı)', target: ALL_TEACHERS }),
      t_load: () => ({ mode: 'Tüm Öğretmenlerin Ders Yükü Listesi', target: ALL_TEACHERS }),
      t_single: () => ({ mode: tSub === 'asgn' ? 'Sınıf Dersleri & Atama Listesi (Liste Formatı)' : 'Öğretmen Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)', target: tea }),
    };
    onOk(map[opt]());
  };
  const R = ({ v, children }: { v: Opt; children: React.ReactNode }) => (
    <label className="check"><input type="radio" checked={opt === v} onChange={() => setOpt(v)} /> {children}</label>
  );
  return (
    <Window title="Yazdırma & Baskı Önizleme" subtitle="Yazdırmak veya dışa aktarmak istediğiniz rapor formatını seçin" onClose={onCancel} width={640}
      footer={<><span className="sp" /><Btn onClick={onCancel}>İptal</Btn><Btn kind="primary" onClick={confirm}>{direct ? 'Yazdır' : 'Önizlemeyi Aç'}</Btn></>}>
      <div className="card">
        <div className="card-title small muted">SINIF RAPORLARI &amp; ÇİZELGELERİ</div>
        <R v="cls_carsaf">Tüm Sınıflar (Büyük Çarşaf Tablo — Okul Geneli Yatay)</R>
        <R v="cls_6">Tüm Sınıflar (Yatay Sayfada 6'lı Blok Çizelge)</R>
        <div className="inline-field"><R v="cls_single">Tek Bir Sınıf Seç:</R>
          <select disabled={opt !== 'cls_single'} value={cls} onChange={(e) => setCls(e.target.value)}>{classes.map((c) => <option key={c}>{c}</option>)}</select></div>
        {opt === 'cls_single' && (
          <div className="subopts">
            <label className="check"><input type="radio" checked={clsSub === 'carsaf'} onChange={() => setClsSub('carsaf')} /> Çarşaf Çizelgesi</label>
            <label className="check"><input type="radio" checked={clsSub === 'single'} onChange={() => setClsSub('single')} /> Haftalık Tekil Çizelge</label>
            <label className="check"><input type="radio" checked={clsSub === 'asgn'} onChange={() => setClsSub('asgn')} /> Ders Dağılım &amp; Atama Listesi</label>
          </div>
        )}
      </div>
      <div className="card">
        <div className="card-title small muted">ÖĞRETMEN RAPORLARI &amp; ÇİZELGELERİ</div>
        <R v="t_carsaf">Tüm Öğretmenler (Büyük Çarşaf Tablo — Okul Geneli)</R>
        <R v="t_6">Tüm Öğretmenler (Yatay Sayfada 6'lı Blok Çizelge)</R>
        <R v="t_asgn">Toplu Ders &amp; Branş Atama Listesi (Tüm Okul)</R>
        <R v="t_load">Öğretmenlerin Haftalık Ders Yükü Tablosu</R>
        <div className="inline-field"><R v="t_single">Tek Bir Öğretmen Seç:</R>
          <select disabled={opt !== 't_single'} value={tea} onChange={(e) => setTea(e.target.value)}>{teachers.map((t) => <option key={t}>{t}</option>)}</select></div>
        {opt === 't_single' && (
          <div className="subopts">
            <label className="check"><input type="radio" checked={tSub === 'asgn'} onChange={() => setTSub('asgn')} /> Girdiği Sınıflar &amp; Branş Listesi</label>
            <label className="check"><input type="radio" checked={tSub === 'single'} onChange={() => setTSub('single')} /> Haftalık Tekil Çizelge</label>
          </div>
        )}
      </div>
    </Window>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Baskı Ön İzleme ve PDF Raporu
// ════════════════════════════════════════════════════════════════════════════
function Preview({ initial, direct }: { initial: { mode: ReportMode; target: string }; direct: boolean }) {
  const data = useApp((s) => s.data);
  const [mode, setMode] = useState<ReportMode>(initial.mode);
  const [target, setTarget] = useState<string>(initial.target);
  const [full, setFull] = useState(false);
  const [printing, setPrinting] = useState(false);
  const pagesRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.5);
  useEffect(ensureStyles, []);

  const teacherMode = isTeacherMode(mode) || target === ALL_TEACHERS || (data.ogretmenler ?? []).some((t: any) => t.ad === target);
  const targets = useMemo(() => {
    if (teacherMode) return [ALL_TEACHERS, ...[...new Set((data.ogretmenler ?? []).map((t: any) => String(t.ad ?? '').trim()).filter(Boolean))].sort() as string[]];
    return [ALL_CLASSES, ...([...new Set((data.siniflar ?? []).map((c: any) => String(c.ad ?? '').trim()).filter(Boolean))] as string[]).sort(natCmp)];
  }, [data, teacherMode]);
  const tgt = targets.includes(target) ? target : targets[0];
  const portrait = isPortrait(mode);

  useLayoutEffect(() => {
    const el = pagesRef.current;
    if (!el) return;
    const fit = () => {
      const pageW = portrait ? 794 : 1123;
      setScale(Math.min(1.4, Math.max(0.2, (el.clientWidth - 40) / pageW)));
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return () => ro.disconnect();
  }, [portrait, full]);

  const doPrint = () => {
    setPageSize(portrait);
    setPrinting(true);
  };
  useEffect(() => {
    if (!printing) return;
    const t = setTimeout(() => {
      const after = () => { setPrinting(false); window.removeEventListener('afterprint', after); };
      window.addEventListener('afterprint', after);
      window.print();
      setTimeout(after, 1500);
    }, 60);
    return () => clearTimeout(t);
  }, [printing]);
  // "Yazdır" düğmesiyle gelindiyse doğrudan yazdırma penceresi açılır (direct_print).
  useEffect(() => { if (direct) doPrint(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const exportHtml = () => {
    const body = renderToStaticMarkup(<>{renderReport(mode, tgt, { data, print: true })}</>);
    const html = `<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>Ders Programı</title><style>body{margin:0;background:#e5e7eb}.pp-page{margin:12px auto;box-shadow:0 2px 10px rgba(0,0,0,.2)}@page{size:A4 ${portrait ? 'portrait' : 'landscape'};margin:0}@media print{body{background:#fff}.pp-page{margin:0;box-shadow:none;page-break-after:always}}${PRINT_CSS}</style></head><body>${body}</body></html>`;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
    a.download = 'Ders_Programi.html';
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  };

  return (
    <Window title="Baskı Ön İzleme ve PDF Raporu" onClose={closeScreen} width={1200} className={`pp-win${full ? ' max' : ''}`}>
      <div className="pp-bar">
        <span className="muted small">RAPOR TÜRÜ</span>
        <select value={mode} onChange={(e) => setMode(e.target.value as ReportMode)}>{REPORT_MODES.map((m) => <option key={m} value={m}>{m}</option>)}</select>
        <span className="muted small">SEÇİM</span>
        <select value={tgt} onChange={(e) => setTarget(e.target.value)}>{targets.map((t) => <option key={t} value={t}>{t}</option>)}</select>
        <span className="sp" />
        <Btn onClick={() => setFull(!full)}>{full ? 'Normal Boyut' : 'Tam Ekran'}</Btn>
        <Btn onClick={exportHtml}>HTML Çıktısı</Btn>
        <Btn onClick={doPrint} title="Yazdırma penceresinde hedef olarak 'PDF olarak kaydet' seçin">PDF Kaydet</Btn>
        <Btn kind="primary" onClick={doPrint}>Yazdır</Btn>
      </div>
      <div className="pp-pages" ref={pagesRef}>
        <div className="pp-scale" style={{ zoom: scale } as React.CSSProperties}>
          {renderReport(mode, tgt, { data, print: false })}
        </div>
      </div>
      {printing && createPortal(<div id="print-root">{renderReport(mode, tgt, { data, print: true })}</div>, document.body)}
    </Window>
  );
}
