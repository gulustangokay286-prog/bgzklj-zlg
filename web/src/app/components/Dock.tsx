// Yerleştirilemeyen dersler paneli (UnplacedLessonsDock). Seçili satırın ya da
// bütün okulun açıkta kalan blokları; ızgaraya sürüklenir. Izgaradan buraya
// bırakılan ders çizelgeden kaldırılır (silinmez).
import { useMemo, useState } from 'react';
import type { MouseEvent } from 'react';
import { changeDistribution, currentParts, deleteCardAssignment, mergeParts, splitParts } from '../cardActions.ts';
import type { Unplaced } from '../model.ts';
import { ask, promptText } from '../store.ts';
import { SubjectColorDialog } from './SubjectColor.tsx';
import { removeBlock } from '../actions.ts';
import { unplacedCards } from '../model.ts';
import { classKey, teacherKey } from '../placement.ts';
import { getState, setState, useApp } from '../store.ts';

function tint(hex: string) {
  const n = parseInt(hex.slice(1), 16);
  const mix = (c: number) => Math.round(c + (255 - c) * 0.72);
  return `rgb(${mix((n >> 16) & 255)}, ${mix((n >> 8) & 255)}, ${mix(n & 255)})`;
}

export function Dock() {
  const data = useApp((s) => s.data);
  const view = useApp((s) => s.view);
  const row = useApp((s) => s.selectedRow);
  const [scope, setScope] = useState<'row' | 'all'>('row');
  const [over, setOver] = useState(false);
  const [menu, setMenu] = useState<{ x: number; y: number; card: Unplaced } | null>(null);
  const [colorOf, setColorOf] = useState<string | null>(null);
  const onMenu = (e: MouseEvent, card: Unplaced) => { e.preventDefault(); setMenu({ x: e.clientX, y: Math.min(e.clientY, window.innerHeight - 380), card }); };
  const dist = (parts: number[]) => { if (menu) void changeDistribution(data, menu.card, parts); setMenu(null); };
  const all = useMemo(() => unplacedCards(data), [data]);
  const cards = scope === 'all' || !row ? all : all.filter((c) =>
    view === 'classes' ? c.classes.some((x) => classKey(x) === classKey(row)) : teacherKey(c.teacher) === teacherKey(row));
  const total = cards.reduce((s, c) => s + c.duration * Math.max(1, c.classes.length), 0);

  return (
    <div className={`dock${over ? ' drop' : ''}`}
      onDragOver={(e) => { const d = getState().drag; if (d && !d.fromDock) { e.preventDefault(); setOver(true); } }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        const d = getState().drag;
        setState({ drag: null });
        if (d && !d.fromDock && d.entries) void removeBlock(d.entries);
      }}>
      <h4>
        Yerleştirilemeyenler · {total} saat
        <span className="seg">
          <button className={scope === 'row' ? 'on' : ''} onClick={() => setScope('row')}>{row ? row : 'Seçili satır'}</button>
          <button className={scope === 'all' ? 'on' : ''} onClick={() => setScope('all')}>Tümü ({all.length})</button>
        </span>
      </h4>
      {cards.length === 0 ? (
        <div className="empty">{scope === 'row' && !row ? 'Bir satır seçin ya da "Tümü"ne geçin.' : 'Açıkta ders yok.'}</div>
      ) : (
        <div className="cards">
          {cards.map((c) => (
            <div key={c.id} className="card" draggable style={{ background: tint(c.color) }}
              title={`${c.subject} — ${c.teacher} — ${c.className} (${c.duration} saat)`}
              onDragStart={(e) => {
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', c.subject);
                setState({ drag: { lesson: { subject_name: c.subject, subject: c.subject, teacher_name: c.teacher, teacher: c.teacher,
                  class_name: c.classes.length > 1 ? c.classes.join(' + ') : c.classes[0], combined_classes: c.classes.length > 1 ? c.classes : [],
                  is_combined: c.classes.length > 1 }, duration: c.duration, origin: null, blockId: '', fromDock: true, looseId: c.loose } });
              }}
              onDragEnd={() => setState({ drag: null })} onContextMenu={(e) => onMenu(e, c)}>
              <b>{c.subject} · {c.duration}s</b>
              <small>{view === 'classes' ? c.teacher : c.className}{scope === 'all' ? ` · ${view === 'classes' ? c.className : c.teacher}` : ''}</small>
            </div>
          ))}
        </div>
      )}
      {menu && (
        <div className="ctx-back" onClick={() => setMenu(null)} onContextMenu={(e) => { e.preventDefault(); setMenu(null); }}>
          <div className="ctx" style={{ left: menu.x, top: menu.y }} onClick={(e) => e.stopPropagation()}>
            <button onClick={() => { setColorOf(menu.card.subject); setMenu(null); }}>{menu.card.subject} Rengini Ayarla...</button>
            <hr />
            {menu.card.duration === 2 && <button onClick={() => dist(splitParts(currentParts(data, menu.card)))}>İkiye Böl (1+1 Saat Yap)</button>}
            {menu.card.duration === 1 && <button onClick={() => dist(mergeParts(currentParts(data, menu.card)))}>2 Kartı Birleştir (2 Saatlik Blok Yap)</button>}
            <hr />
            <button onClick={() => dist([2, 2])}>2+2 Saat (2 İkili Blok)</button>
            <button onClick={() => dist([2, 1])}>2+1 Saat (1 İkili + 1 Tekli)</button>
            <button onClick={() => dist([2, 2, 1])}>2+2+1 Saat (5 Saat)</button>
            <button onClick={() => dist([3, 2])}>3+2 Saat (5 Saat)</button>
            <button onClick={() => dist([1, 1, 1])}>1+1+1 Saat (3 Tekli)</button>
            <button onClick={async () => {
              const card = menu.card; setMenu(null);
              const v = await promptText('Özel Dağılım', 'Saat Dağılımı (Örn: 2+2 veya 1+1+1):', String(card.duration));
              if (v?.trim()) {
                const parts = v.replace(/,/g, '+').split('+').map((x) => x.trim()).filter(Boolean).map(Number);
                if (parts.every((x) => Number.isInteger(x) && x > 0)) void changeDistribution(data, card, parts);
              }
            }}>Özel Dağılım Yapısı Gir...</button>
            <hr />
            <button className="danger-txt" onClick={async () => {
              const card = menu.card; setMenu(null);
              if (await ask({ title: 'Atamayı Sil', body: `${card.subject} (${card.className}${card.teacher ? ' · ' + card.teacher : ''}) ataması silinsin mi?`, ok: 'Sil', cancel: 'Vazgeç', tone: 'danger' })) deleteCardAssignment(card);
            }}>Atamayı Sil (Kaldır)</button>
          </div>
        </div>
      )}
      {colorOf && <SubjectColorDialog subject={colorOf} onClose={() => setColorOf(null)} />}
    </div>
  );
}
