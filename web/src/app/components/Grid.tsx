// Ana çizelge: aSc tarzı büyük tablo. Satırlar sınıflar ya da öğretmenler,
// sütunlar gün × saat. Sürüklerken hedef satır(lar)ın her hücresi yerleştirme
// motorunun kararıyla boyanır: yeşil konabilir, mavi tercih edilmez, kırmızı
// çakışma, gri kapalı.
import { useEffect, useMemo, useRef, useState } from 'react';
import type { DragEvent, MouseEvent } from 'react';
import { getMatrix, CLOSED } from '../../engine/data.ts';
import { dropLesson, lockRow, removeBlock, toggleLock } from '../actions.ts';
import { abbr, buildCells, classColor, classRows, dims, subjectColor, teacherRows, unplacedCards } from '../model.ts';
import type { Cell } from '../model.ts';
import { Candidate, Snapshot, analyze, classKey, lessonClasses, lessonTeachers, teacherKey, visualOf } from '../placement.ts';
import type { Result } from '../placement.ts';
import { getState, openScreen, setState, status, useApp } from '../store.ts';
import { SubjectColorDialog } from './SubjectColor.tsx';
import type { DragInfo } from '../store.ts';

function tint(hex: string, amount = 0.72): string {
  const n = parseInt(hex.slice(1), 16);
  const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
  const mix = (c: number) => Math.round(c + (255 - c) * amount);
  return `rgb(${mix(r)}, ${mix(g)}, ${mix(b)})`;
}

interface Ctx { x: number; y: number; items: [string, () => void][] }

export function Grid() {
  const data = useApp((s) => s.data);
  const view = useApp((s) => s.view);
  const drag = useApp((s) => s.drag);
  const selectedRow = useApp((s) => s.selectedRow);
  const { D, P, days } = dims(data);
  const rows = useMemo(() => (view === 'classes' ? classRows(data) : teacherRows(data)), [data, view]);
  const cells = useMemo(() => buildCells(data, view, rows), [data, view, rows]);
  const [hover, setHover] = useState<string | null>(null);
  const [selKey, setSelKey] = useState<string | null>(null);
  const [ctx, setCtx] = useState<Ctx | null>(null);
  const [colorOf, setColorOf] = useState<string | null>(null);
  const zoom = useApp((s) => s.zoom);
  const [width, setWidth] = useState(1200);
  const wrap = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Satırın kapalı saatleri (sınıf ya da öğretmen zaman tablosu).
  const closed = useMemo(() => {
    const out = new Map<string, Set<number>>();
    const list = view === 'classes' ? data?.siniflar ?? [] : data?.ogretmenler ?? [];
    for (const ent of list) {
      const name = String(ent?.ad || ent?.name || '').trim();
      if (!name) continue;
      const m = getMatrix(ent, name, data);
      const s = new Set<number>();
      for (let d = 0; d < D; d++) for (let p = 0; p < P; p++) if (m[d]?.[p] === CLOSED) s.add(d * P + p);
      out.set(name, s);
    }
    return out;
  }, [data, view, D, P]);

  // Satır başına yerleştirilemeyen saat (rozet).
  const missing = useMemo(() => {
    const out = new Map<string, number>();
    for (const c of unplacedCards(data)) {
      const owners = view === 'classes' ? c.classes : [c.teacher];
      for (const o of owners) {
        const row = rows.find((r) => (view === 'classes' ? classKey(r) === classKey(o) : teacherKey(r) === teacherKey(o)));
        if (row) out.set(row, (out.get(row) ?? 0) + c.duration);
      }
    }
    return out;
  }, [data, view, rows]);

  // Sürükleme analizi: hedef satırların her başlangıç hücresi için motorun kararı.
  const analysis = useMemo(() => {
    if (!drag || !data) return null;
    const snap = new Snapshot(data, drag.blockId);
    const lesson = { ...drag.lesson, block_id: drag.blockId, duration: drag.duration, locked: false,
      source: drag.origin ? { day: drag.origin.day, period: drag.origin.period } : undefined };
    const targetRows = view === 'classes'
      ? rows.filter((r) => lessonClasses(drag.lesson).some((c) => classKey(c) === classKey(r)))
      : rows.filter((r) => lessonTeachers(drag.lesson).some((t) => teacherKey(t) === teacherKey(r)));
    const out = new Map<string, Result>();
    for (const r of targetRows) {
      for (let d = 0; d < D; d++) for (let p = 0; p < P; p++) {
        out.set(`${r}|${d}|${p}`, analyze(snap, lesson, new Candidate(lesson, d, p, drag.duration)));
      }
    }
    return out;
  }, [drag, data, view, rows, D, P]);

  if (!data) return null;
  const rowHead = 120;
  const col = Math.round(Math.max(26, Math.floor((width - rowHead - 2) / Math.max(1, D * P))) * zoom);

  const startDrag = (e: DragEvent, info: DragInfo) => {
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', info.lesson.subject_name || 'ders');
    setState({ drag: info });
  };

  const onBlockDragStart = (e: DragEvent, cell: Cell) => {
    if (cell.locked) {
      e.preventDefault();
      status('Kilitli ders taşınamaz — sağ tık > Kilidi aç.');
      return;
    }
    const e0 = cell.entries[0];
    startDrag(e, { lesson: { ...e0 }, duration: cell.span, origin: { day: cell.day, period: cell.start },
      blockId: String(e0.block_id || ''), fromDock: false, entries: cell.entries });
  };

  // Birden çok saati kaplayan hücrede farenin altındaki saat.
  const at = (e: DragEvent, p: number, span: number) => {
    if (span <= 1) return p;
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    return p + Math.max(0, Math.min(span - 1, Math.floor((e.clientX - rect.left) / col)));
  };

  const onDrop = async (e: DragEvent, row: string, d: number, p0: number, span = 1) => {
    e.preventDefault();
    const p = at(e, p0, span);
    const info = getState().drag;
    setState({ drag: null });
    setHover(null);
    if (!info) return;
    await dropLesson({ lesson: info.lesson, duration: info.duration, origin: info.origin, blockId: info.blockId,
      entries: info.entries, looseId: info.looseId }, row, d, p);
  };

  const onOver = (e: DragEvent, row: string, d: number, p0: number, span = 1) => {
    if (!getState().drag) return;
    e.preventDefault();
    const key = `${row}|${d}|${at(e, p0, span)}`;
    if (hover !== key) {
      setHover(key);
      const r = analysis?.get(key);
      if (r) status(r.explanation);
    }
  };

  // main_window._on_cell_edit: dersin öğretmen/saat paneli, bu sınıf seçili.
  const editBlock = (cell: Cell) => openScreen({ kind: 'assignSubject', subject: cell.subject, className: cell.classes[0] });

  const blockMenu = (e: MouseEvent, cell: Cell) => {
    e.preventDefault();
    setCtx({ x: e.clientX, y: e.clientY, items: [
      ['Düzenle', () => editBlock(cell)],
      [cell.locked ? 'Bu Dersin Kilidini Kaldır' : 'Dersi Kilitle (Sabitle)', () => toggleLock(cell.entries)],
      ['Renk Paleti Ayarla...', () => setColorOf(cell.subject)],
      ['Sil (Kaldır)', () => void removeBlock(cell.entries)],
    ] });
  };

  const rowMenu = (e: MouseEvent, row: string) => {
    e.preventDefault();
    const ent = view === 'classes' ? (data.siniflar ?? []).findIndex((c: any) => c.ad === row) : (data.ogretmenler ?? []).findIndex((t: any) => t.ad === row);
    setCtx({ x: e.clientX, y: e.clientY, items: [
      [view === 'classes' ? `${row} Sınıfının Dersleri (Atama Paneli)` : `${row} Öğretmenin Atamaları`,
        () => openScreen(view === 'classes' ? { kind: 'assignClass', className: row } : { kind: 'assignTeacher', teacher: row })],
      ['Zaman Tablosu', () => openScreen({ kind: 'timeoff', entityKind: view === 'classes' ? 'siniflar' : 'ogretmenler', name: row, index: ent >= 0 ? ent : undefined })],
      ['Çizelgeyi Yazdır', () => openScreen({ kind: 'print', preset: { entity: view === 'classes' ? 'class' : 'teacher', name: row } })],
      [`${row} — tümünü kilitle`, () => lockRow(row, view, true)],
      [`${row} — kilitleri aç`, () => lockRow(row, view, false)],
    ] });
  };

  const describe = (cell: Cell) => {
    const who = view === 'classes' ? cell.teacher : cell.classes.join(' + ');
    status(`${cell.subject} · ${who} · ${days[cell.day]} ${cell.start + 1}${cell.span > 1 ? `-${cell.start + cell.span}` : ''}. saat`
      + `${cell.locked ? ' · kilitli' : ''}${cell.split ? ' · bölünmüş' : ''}${cell.conflict ? ' · ÇAKIŞMA' : ''}`);
  };

  return (
    <div className="gridwrap" ref={wrap} onClick={() => setCtx(null)} style={{ ["--rowh" as any]: `${Math.round(40 * zoom)}px` }}>
      <table className="tt" style={{ width: rowHead + col * D * P }}>
        <colgroup>
          <col style={{ width: rowHead }} />
          {Array.from({ length: D * P }, (_, i) => <col key={i} style={{ width: col }} />)}
        </colgroup>
        <thead>
          <tr className="days">
            <th className="corner">{view === 'classes' ? 'Sınıf' : 'Öğretmen'}</th>
            {days.map((d, i) => <th key={i} colSpan={P}>{d}</th>)}
          </tr>
          <tr className="pers">
            <th className="corner" style={{ top: 24 }} />
            {Array.from({ length: D * P }, (_, i) => <th key={i} className={i % P === 0 ? 'dstart' : ''}>{(i % P) + 1}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const rc = cells.get(row) ?? [];
            const byStart = new Map(rc.map((c) => [c.day * P + c.start, c] as const));
            const cl = closed.get(row) ?? new Set<number>();
            const tds = [];
            for (let i = 0; i < D * P;) {
              const d = Math.floor(i / P), p = i % P;
              const key = `${row}|${d}|${p}`;
              const an = analysis?.get(key);
              const cellCls = [p === 0 ? 'dstart' : '', cl.has(i) ? 'closed' : '', an ? `an-${visualOf(an)}` : '', hover === key ? 'hover' : ''].join(' ');
              const block = byStart.get(i);
              if (block) {
                const span = Math.min(block.span, P - p);
                const color = view === 'classes' ? subjectColor(block.subject, data) : classColor(block.classes[0] ?? '', data);
                const sub = view === 'classes' ? block.teacher.split(' ').map((w) => w[0]).join('') : block.classes.join('+');
                tds.push(
                  <td key={i} colSpan={span} className={cellCls} onDragOver={(e) => onOver(e, row, d, p, span)} onDrop={(e) => onDrop(e, row, d, p, span)}>
                    <div className={`blk${block.locked ? ' locked' : ''}${block.split ? ' split' : ''}${block.conflict ? ' conflict' : ''}${selKey === `${row}|${block.key}|${i}` ? ' sel' : ''}`}
                      style={{ background: tint(color) }} draggable={!block.locked}
                      onDragStart={(e) => onBlockDragStart(e, block)} onDragEnd={() => { setState({ drag: null }); setHover(null); }}
                      onClick={() => { setSelKey(`${row}|${block.key}|${i}`); setState({ selectedRow: row }); describe(block); }}
                      onDoubleClick={() => editBlock(block)}
                      onContextMenu={(e) => blockMenu(e, block)} title={`${block.subject} — ${block.teacher} — ${block.classes.join(' + ')}`}>
                      <span className="s">{abbr(block.subject)}</span>
                      {col * span >= 38 && <span className="t">{sub}</span>}
                    </div>
                  </td>,
                );
                i += span;
              } else {
                tds.push(<td key={i} className={cellCls} onDragOver={(e) => onOver(e, row, d, p)} onDrop={(e) => onDrop(e, row, d, p)} />);
                i++;
              }
            }
            const miss = missing.get(row) ?? 0;
            return (
              <tr key={row}>
                <th className={selectedRow === row ? 'sel' : ''} onClick={() => setState({ selectedRow: row })} onContextMenu={(e) => rowMenu(e, row)} title={row}>
                  {miss > 0 && <span className="badge" title={`${miss} saat yerleşmedi`}>{miss}</span>}
                  {row}
                </th>
                {tds}
              </tr>
            );
          })}
        </tbody>
      </table>
      {colorOf && <SubjectColorDialog subject={colorOf} onClose={() => setColorOf(null)} />}
      {ctx && (
        <div className="ctx" style={{ left: ctx.x, top: ctx.y }} onClick={(e) => e.stopPropagation()}>
          {ctx.items.map(([label, fn]) => <button key={label} onClick={() => { setCtx(null); fn(); }}>{label}</button>)}
        </div>
      )}
    </div>
  );
}
