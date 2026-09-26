// Soru penceresi, sıfırlama ve oto planlayıcı.
import { useEffect, useRef, useState } from 'react';
import { applyPlan, resetSchedule } from '../actions.ts';
import { durOf } from '../model.ts';
import { getState, setState, undo, useApp } from '../store.ts';

export function DialogHost() {
  const dlg = useApp((s) => s.dialog);
  const okRef = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (!dlg?.input) okRef.current?.focus(); }, [dlg]);
  if (!dlg) return null;
  return (
    <div className="overlay dlg" onKeyDown={(e) => { if (e.key === 'Escape' && dlg.cancel) dlg.resolve(false); }}>
      <div className={`sheet ${dlg.tone === 'warn' ? 'warn' : dlg.tone === 'danger' ? 'danger' : ''}`} role="dialog" aria-modal="true" style={dlg.lines ? { width: 'min(680px, calc(100vw - 32px))' } : undefined}>
        <h3>{dlg.title}</h3>
        <p>{dlg.body}</p>
        {dlg.input && (
          <input className="dlg-input" autoFocus defaultValue={dlg.input.value} placeholder={dlg.input.placeholder}
            onChange={(e) => { dlg.input!.value = e.target.value; }} onKeyDown={(e) => { if (e.key === 'Enter') dlg.resolve(true); }} />
        )}
        {dlg.lines && (
          <div className="rep">
            {dlg.lines.map((l, i) => <div key={i} className={l.kind}>{l.text}</div>)}
            {dlg.note && <div className="note">{dlg.note}</div>}
          </div>
        )}
        {dlg.foot && <p className="muted small">{dlg.foot}</p>}
        <div className="acts">
          {dlg.cancel && <button className="tb" onClick={() => dlg.resolve(false)}>{dlg.cancel}</button>}
          <button className={`tb ${dlg.tone === 'danger' ? 'danger' : 'primary'}`} ref={okRef} onClick={() => dlg.resolve(true)}>{dlg.ok}</button>
        </div>
      </div>
    </div>
  );
}

export function ResetSheet() {
  const open = useApp((s) => s.resetOpen);
  const data = useApp((s) => s.data);
  const [keep, setKeep] = useState(true);
  if (!open || !data) return null;
  const all = (data.grid_placements ?? []).filter((p: any) => p);
  const locked = all.filter((p: any) => p.locked || p.is_locked);
  const blocks = new Set(locked.map((p: any) => String(p.block_id || Math.random())));
  const close = () => setState({ resetOpen: false });
  return (
    <div className="overlay">
      <div className="sheet">
        <h3>Çizelgeyi sıfırla</h3>
        <p className="muted">Çizelgede {all.reduce((n: number, p: any) => n + durOf(p), 0)} saat ders var{locked.length ? `; ${blocks.size} blok (${locked.reduce((n: number, p: any) => n + durOf(p), 0)} saat) kilitli` : ''}. Geri al ile dönebilirsiniz.</p>
        {locked.length > 0 && (
          <>
            <div className={`opt ${keep ? 'on' : ''}`} onClick={() => setKeep(true)}>
              <input type="radio" checked={keep} readOnly />
              <div><b>Kilitliler kalsın</b><br /><span className="muted">Yalnızca kilitsiz dersler kaldırılır.</span></div>
            </div>
            <div className={`opt ${!keep ? 'on' : ''}`} onClick={() => setKeep(false)}>
              <input type="radio" checked={!keep} readOnly />
              <div><b>Tümünü sıfırla</b><br /><span className="muted">Kilitli dersler dahil her şey kaldırılır.</span></div>
            </div>
          </>
        )}
        <div className="acts">
          <button className="tb" onClick={close}>Vazgeç</button>
          <button className="tb primary" onClick={() => { resetSchedule(locked.length > 0 && keep); close(); }}>Sıfırla</button>
        </div>
      </div>
    </div>
  );
}

interface Run {
  phase: 'idle' | 'running' | 'ask' | 'conflict' | 'done' | 'error';
  placed: number; total: number; t: number; text: string;
  ask?: any; conflicts?: string[]; result?: any; error?: string;
}

export function PlannerSheet() {
  const open = useApp((s) => s.plannerOpen);
  const [run, setRun] = useState<Run>({ phase: 'idle', placed: 0, total: 0, t: 0, text: '' });
  const worker = useRef<Worker | null>(null);

  useEffect(() => () => worker.current?.terminate(), []);
  if (!open) return null;

  const start = (unlock = false) => {
    const data = getState().data;
    if (!data) return;
    worker.current?.terminate();
    const w = new Worker(new URL('../../workers/engine.worker.ts', import.meta.url), { type: 'module' });
    worker.current = w;
    setRun({ phase: 'running', placed: 0, total: 0, t: 0, text: 'Başlatılıyor…' });
    w.onmessage = (e) => {
      const m = e.data;
      if (m.type === 'status') setRun((r) => ({ ...r, text: m.text }));
      else if (m.type === 'progress') setRun((r) => ({ ...r, phase: r.phase === 'ask' ? 'ask' : 'running', placed: Math.max(r.placed, m.placed), total: m.total, t: m.t }));
      else if (m.type === 'ask') setRun((r) => ({ ...r, phase: 'ask', ask: m.info }));
      else if (m.type === 'conflict') { setRun((r) => ({ ...r, phase: 'conflict', conflicts: m.items })); w.terminate(); }
      else if (m.type === 'error') { setRun((r) => ({ ...r, phase: 'error', error: m.message })); w.terminate(); }
      else if (m.type === 'done') {
        applyPlan(m.result);
        setRun((r) => ({ ...r, phase: 'done', result: m.result, placed: m.result.placed_hours, total: m.result.total_assigned_hours, t: m.t }));
        w.terminate();
      }
    };
    w.onerror = (e) => setRun((r) => ({ ...r, phase: 'error', error: e.message }));
    w.postMessage({ type: 'run', data, unlock });
  };
  const answer = (devam: boolean) => { worker.current?.postMessage({ type: 'answer', devam }); setRun((r) => ({ ...r, phase: 'running' })); };
  const stop = () => { worker.current?.postMessage({ type: 'cancel' }); setRun((r) => ({ ...r, text: 'Durduruluyor, en iyi çözüm alınıyor…' })); };
  const close = () => {
    if (run.phase === 'running' || run.phase === 'ask') worker.current?.terminate();
    setRun({ phase: 'idle', placed: 0, total: 0, t: 0, text: '' });
    setState({ plannerOpen: false });
  };
  const pct = run.total ? Math.round((100 * run.placed) / run.total) : 0;
  const res = run.result;

  return (
    <div className="overlay">
      <div className="sheet">
        <h3>Otomatik Planlama</h3>
        {run.phase === 'idle' && (
          <>
            <p className="muted">Motor bu bilgisayarda, tarayıcının içinde çalışır; veri hiçbir yere gönderilmez.
              Kilitli dersler yerinde kalır, diğer dersler kurallara ve zaman tablolarına göre yeniden yerleştirilir.</p>
            <div className="acts">
              <button className="tb" onClick={close}>Kapat</button>
              <button className="tb primary" onClick={() => start(false)}>Planlamayı başlat</button>
            </div>
          </>
        )}
        {(run.phase === 'running' || run.phase === 'ask') && (
          <>
            <div className="bar"><div style={{ width: `${pct}%` }} /></div>
            <p><b>{run.placed}/{run.total || '…'} saat</b> <span className="muted">· {run.t.toFixed(0)} sn · {run.text}</span></p>
            {run.phase === 'ask' && run.ask && (
              <div className="opt on">
                <div>
                  <b>{run.ask.saat}/{run.ask.toplam} saat yerleşti, {Math.round(run.ask.gecen)} sn geçti.</b><br />
                  <span className="muted">{run.ask.ust !== null && run.ask.ust < run.ask.toplam ? `Bu kurallarla en fazla ${run.ask.ust} saat mümkün. ` : ''}
                    Bir tur daha arayabilirim ya da bu hâliyle bitirebilirim.</span>
                  <div className="acts" style={{ justifyContent: 'flex-start' }}>
                    <button className="tb" onClick={() => answer(false)}>Bu hâliyle bitir</button>
                    <button className="tb primary" onClick={() => answer(true)}>Bir tur daha bekle</button>
                  </div>
                </div>
              </div>
            )}
            <div className="acts"><button className="tb" onClick={stop}>Durdur ve kaydet</button></div>
          </>
        )}
        {run.phase === 'conflict' && (
          <>
            <p><b>Kilitli dersler verilerle çelişiyor.</b></p>
            <ul className="list">{run.conflicts?.map((c) => <li key={c}>{c}</li>)}</ul>
            <p className="muted">Motor kapalı saati ya da kuralı kendiliğinden açmaz. Kilitleri çözersem bu dersleri kurallara uygun
              bir yere yerleştiririm; yer yoksa yerleştirilemeyenlere koyarım.</p>
            <div className="acts">
              <button className="tb" onClick={close}>Vazgeç</button>
              <button className="tb primary" onClick={() => start(true)}>Bu kilitleri çöz ve planla</button>
            </div>
          </>
        )}
        {run.phase === 'error' && (
          <>
            <p style={{ color: 'var(--bad)' }}>{run.error}</p>
            <div className="acts"><button className="tb primary" onClick={close}>Kapat</button></div>
          </>
        )}
        {run.phase === 'done' && res && (
          <>
            <p><b style={{ color: res.complete ? 'var(--ok)' : 'var(--bad)' }}>{res.placed_hours}/{res.total_assigned_hours} saat</b>
              <span className="muted"> · {run.t.toFixed(1)} sn · {res.complete ? 'tam çizelge, sert kural ihlali yok' : 'eksik — sebebi aşağıda'}</span></p>
            {res.unplaced_summary.length > 0 && (
              <ul className="list">{res.unplaced_summary.map((u: any) => <li key={`${u.class}|${u.subject}|${u.teacher}`}>Yerleşmedi: {u.class} · {u.subject} ({u.teacher}) — {u.hours} saat</li>)}</ul>
            )}
            <details><summary className="muted">Motor raporu ({res.warnings.length})</summary>
              <ul className="list">{res.warnings.map((x: string, i: number) => <li key={i}>{x}</li>)}</ul>
            </details>
            <div className="acts">
              <button className="tb" onClick={() => { undo(); close(); }}>Geri al</button>
              <button className="tb primary" onClick={close}>Tamam</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
