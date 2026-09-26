// dialogs/timeoff_dialog.py — Zaman Tablosu (Kısıtlamalar).
// İki durum: müsait ✓ / kısıtlı ✕. Öğretmenlerde ayrıca kişisel katman
// (izin/rapor) ve yarım gün. Kaydetmeden önce ön kontrol çalışır.
import { useMemo, useState } from 'react';
import { CLOSED, OPEN, getMatrix, getPersonal } from '../../engine/data.ts';
import { candidateStore } from '../feasibility.ts';
import { formatTrName, setMatrix, setPersonal } from '../datastore.ts';
import { dayOf, dims, durOf, periodOf } from '../model.ts';
import { runPreflight } from '../preflight.ts';
import { closeScreen, mutate, openScreen, tell, useApp } from '../store.ts';
import { Btn, Window } from '../ui.tsx';

type Kind = 'siniflar' | 'ogretmenler' | 'derslikler';
const TYPE_NAME: Record<Kind, string> = { siniflar: 'Sınıf', ogretmenler: 'Öğretmen', derslikler: 'Derslik' };

export function findEntity(d: any, kind: Kind, name: string, index?: number): number {
  const list: any[] = d?.[kind] ?? [];
  if (index !== undefined && list[index] && String(list[index].ad ?? '').trim() === name.trim()) return index;
  return list.findIndex((e) => String(e?.ad ?? e?.name ?? '').trim() === name.trim());
}

export function TimeoffScreen({ entityKind, name, index }: { entityKind: Kind; name: string; index?: number }) {
  const data = useApp((s) => s.data);
  const idx = findEntity(data, entityKind, name, index);
  const entity = idx >= 0 ? data[entityKind][idx] : null;
  const { D, P, days } = dims(data);
  const isTeacher = entityKind === 'ogretmenler';
  const [matrix, setM] = useState<number[][]>(() => (entity ? getMatrix(entity, name, data) : []));
  const [personal, setPers] = useState<boolean[][]>(() => (entity ? getPersonal(entity, name, data) : []));
  const [menu, setMenu] = useState<{ x: number; y: number; d: number; p: number } | null>(null);
  const [help, setHelp] = useState(false);

  // Öğretmenin çizelgede dolu olduğu saatler (timeoff_dialog._load_busy_slots).
  const busy = useMemo(() => {
    const out = new Map<string, string>();
    if (!isTeacher) return out;
    const want = formatTrName(name);
    for (const p of data?.grid_placements ?? []) {
      if (!p || typeof p !== 'object') continue;
      if (formatTrName(p.teacher_name || p.teacher || '') !== want) continue;
      const cls = String(p.class_name || p.class || '').trim(), subj = String(p.subject_name || p.subject || '').trim();
      const label = [cls, subj].filter(Boolean).join(' · ') || 'Ders';
      for (let o = 0; o < durOf(p); o++) { const k = `${dayOf(p)},${periodOf(p) + o}`; if (!out.has(k)) out.set(k, label); }
    }
    return out;
  }, [data, isTeacher, name]);

  if (!entity) {
    return <Window title="Zaman Tablosu" onClose={closeScreen} width={420}><p>Kayıt bulunamadı: {name}</p></Window>;
  }

  const update = (fn: (m: number[][], pe: boolean[][]) => void) => {
    const m = matrix.map((r) => [...r]), pe = personal.map((r) => [...r]);
    fn(m, pe);
    setM(m); setPers(pe);
  };
  const clickCell = (d: number, p: number) => update((m, pe) => {
    const nw = m[d][p] === OPEN ? CLOSED : OPEN;
    if (nw === OPEN) pe[d][p] = false;
    m[d][p] = nw;
  });
  const toggleDay = (d: number) => update((m, pe) => {
    const anyOpen = m[d].some((x) => x > 0);
    for (let p = 0; p < P; p++) { if (!anyOpen) pe[d][p] = false; m[d][p] = anyOpen ? CLOSED : OPEN; }
  });
  const togglePeriod = (p: number) => update((m, pe) => {
    const anyOpen = m.some((r) => r[p] > 0);
    for (let d = 0; d < D; d++) { if (!anyOpen) pe[d][p] = false; m[d][p] = anyOpen ? CLOSED : OPEN; }
  });
  const allOpen = () => update((m, pe) => { for (let d = 0; d < D; d++) for (let p = 0; p < P; p++) { pe[d][p] = false; m[d][p] = OPEN; } });
  const allClose = () => update((m) => { for (let d = 0; d < D; d++) for (let p = 0; p < P; p++) m[d][p] = CLOSED; });
  const setPersonalCell = (d: number, p: number, on: boolean) => update((m, pe) => { pe[d][p] = on; if (on) m[d][p] = CLOSED; });
  const halfDay = (d: number, first: boolean) => update((m, pe) => {
    const half = Math.floor(P / 2) || 1;
    for (let p = first ? 0 : half; p < (first ? half : P); p++) { pe[d][p] = false; m[d][p] = CLOSED; }
  });
  const openDay = (d: number) => update((m, pe) => { for (let p = 0; p < P; p++) { pe[d][p] = false; m[d][p] = OPEN; } });

  let open = 0, closed = 0, pers = 0;
  for (let d = 0; d < D; d++) for (let p = 0; p < P; p++) {
    if (matrix[d]?.[p] === OPEN) open++; else if (matrix[d]?.[p] === CLOSED) closed++;
    if (personal[d]?.[p]) pers++;
  }

  const save = async () => {
    const probe = candidateStore(data, entityKind, idx, matrix, personal);
    if (!(await runPreflight(probe, 'save'))) return;
    mutate(`${name} zaman tablosu`, (d) => {
      const ent = d[entityKind][idx];
      setMatrix(d, entityKind, ent, matrix);
      setPersonal(d, ent, personal);
    });
    closeScreen();
  };

  return (
    <Window title={name} subtitle={`zaman tablosu · ${TYPE_NAME[entityKind]}`} onClose={closeScreen} width={820}
      footer={<>
        <button className="linkbtn ok" onClick={allOpen}>Tümünü müsait yap</button>
        <button className="linkbtn bad" onClick={allClose}>Tümünü kısıtla</button>
        <span className="legend"><i className="dot ok" /> Müsait: {open}</span>
        <span className="legend"><i className="dot bad" /> Kısıtlı: {closed}{pers ? ` (${pers} kişisel)` : ''}</span>
        {busy.size > 0 && <span className="legend muted">● Çizelgede dolu: {busy.size}</span>}
        <span className="sp" />
        <Btn kind="ghost" onClick={() => setHelp(true)} title="Bu tablo nasıl kullanılır?">?</Btn>
        <Btn onClick={closeScreen}>İptal</Btn>
        <Btn kind="primary" onClick={() => void save()}>Kaydet</Btn>
      </>}>
      <div className="toff-wrap" onContextMenu={(e) => e.preventDefault()}>
        <table className="toff">
          <thead>
            <tr><th />{days.map((dn, d) => <th key={d} className="click" onClick={() => toggleDay(d)} title="Günün tamamını çevir">{dn}</th>)}</tr>
          </thead>
          <tbody>
            {Array.from({ length: P }, (_, p) => (
              <tr key={p}>
                <th className="click" onClick={() => togglePeriod(p)} title="Bu saati bütün günlerde çevir">{p + 1}. Ders</th>
                {Array.from({ length: D }, (_, d) => {
                  const st = matrix[d]?.[p];
                  const isP = !!personal[d]?.[p];
                  const b = busy.get(`${d},${p}`);
                  const cls = isP ? 'pers' : st === OPEN ? (b ? 'busy' : 'open') : 'shut';
                  const tip = isP ? 'Kişisel kısıt: öğretmen bu saatte müsait değil.\nKaldırmak için sağ tıklayın.'
                    : st === OPEN && b ? `Çizelgede bu saatte ders var: ${b}` : isTeacher ? 'Kişisel kısıt ya da yarım gün için sağ tıklayın.' : '';
                  return (
                    <td key={d} className={`tc ${cls}`} title={tip} onClick={() => clickCell(d, p)}
                      onContextMenu={(e) => { if (!isTeacher) return; e.preventDefault(); setMenu({ x: e.clientX, y: e.clientY, d, p }); }}>
                      {isP ? '✕ Kişisel' : st === OPEN ? '✓' : '✕'}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {menu && (
        <div className="ctx-back" onClick={() => setMenu(null)} onContextMenu={(e) => { e.preventDefault(); setMenu(null); }}>
          <div className="ctx" style={{ left: menu.x, top: menu.y }} onClick={(e) => e.stopPropagation()}>
            {personal[menu.d]?.[menu.p]
              ? <button onClick={() => { setPersonalCell(menu.d, menu.p, false); setMenu(null); }}>Kişisel kısıtı kaldır</button>
              : <button onClick={() => { setPersonalCell(menu.d, menu.p, true); setMenu(null); }}>Kişisel kısıt (izin/rapor) olarak kapat</button>}
            <hr />
            <button onClick={() => { halfDay(menu.d, true); setMenu(null); }}>Bu gün: sabah gelmiyor (yarım gün)</button>
            <button onClick={() => { halfDay(menu.d, false); setMenu(null); }}>Bu gün: öğleden sonra gelmiyor (yarım gün)</button>
            <button onClick={() => { openDay(menu.d); setMenu(null); }}>Bu günü tamamen aç</button>
          </div>
        </div>
      )}
      {help && (
        <Window title="Zaman tablosu nasıl kullanılır?" onClose={() => setHelp(false)} width={440}
          footer={<><span className="sp" /><Btn kind="primary" onClick={() => setHelp(false)}>Anladım</Btn></>}>
          <dl className="helpdl">
            <dt>Hücreye tıklayın</dt><dd>Saati müsait ✓ ile kısıtlı ✕ arasında çevirir.</dd>
            <dt>Gün veya saat başlığına tıklayın</dt><dd>O günün ya da o saatin tamamını birden çevirir.</dd>
            <dt>Gri hücreler</dt><dd>Çizelgede o saate bir ders yerleşmiş demektir; hangisi olduğunu görmek için üzerine gelin.</dd>
            {isTeacher && <><dt>Sağ tıklayın</dt><dd>Kişisel kısıt koyabilir ya da yarım gün kapatabilirsiniz.</dd></>}
          </dl>
        </Window>
      )}
    </Window>
  );
}

/** Masaüstündeki "Lütfen listeden bir kayıt seçin." uyarısı dahil, zaman tablosunu açar. */
export async function openTimeoffFor(kind: 'dersler' | Kind, name: string | null, index?: number) {
  if (kind === 'dersler') { await tell('Hata', 'Dersler için zaman tablosu ayarlanamaz.'); return; }
  if (!name) { await tell('Hata', 'Lütfen listeden bir kayıt seçin.'); return; }
  openScreen({ kind: 'timeoff', entityKind: kind, name, index });
}
