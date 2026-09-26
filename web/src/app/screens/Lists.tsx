// Toplu Atama Listesi (assignment_list_dialog.py), Karşılaştırma (compare_dialog.py)
// ve Dersliklere Atama (room_assign_dialog.py).
import { useMemo, useRef, useState } from 'react';
import { classNameOf, hours as hoursOf, subjectOf, teacherOf } from '../../engine/data.ts';
import { ask, closeScreen, getState, mutate, openScreen, tell, useApp } from '../store.ts';
import { listVersions, loadVersionData, versionLabel } from '../versions.ts';
import type { VersionInfo } from '../versions.ts';
import { Btn, Window } from '../ui.tsx';

const norm = (v: unknown) => String(v ?? '').split(/\s+/).filter(Boolean).join(' ').trim();
const intOrNull = (v: unknown) => { const t = String(v ?? '').trim(); if (!t) return null; const n = Number(t); return Number.isFinite(n) ? Math.trunc(n) : null; };
const int0 = (v: unknown) => { const n = Number(v); return Number.isFinite(n) ? Math.trunc(n) : 0; };
function clsSortKey(c: string): [number, string] { const m = /^(\d+)(.*)$/.exec(c.trim()); return m ? [Number(m[1]), m[2]] : [999, c]; }

// ════════════════════════════════════════════════════════════════════════════
// Sınıf Dersleri & Atama Listesi
// ════════════════════════════════════════════════════════════════════════════
export function AssignmentListScreen() {
  const data = useApp((s) => s.data);
  const [q, setQ] = useState('');
  const rows = useMemo(() => {
    const flat: { cls: string; subject: string; teacher: string; dur: number }[] = [];
    for (const a of data.atamalar ?? []) {
      if (!a || typeof a !== 'object') continue;
      const raw = String(a.class ?? '').trim(), s = String(a.subject ?? '').trim(), t = String(a.teacher ?? '').trim(), dur = Number(a.duration ?? 0) || 0;
      if (raw.includes(',') || raw.includes('&')) for (const p of raw.replace(/&/g, ',').split(',').map((x) => x.trim()).filter(Boolean)) flat.push({ cls: p, subject: `${s} (Ortak)`, teacher: t, dur });
      else flat.push({ cls: raw, subject: s, teacher: t, dur });
    }
    return flat.sort((x, y) => { const a = clsSortKey(x.cls), b = clsSortKey(y.cls); return a[0] - b[0] || (a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0); });
  }, [data]);
  const ql = q.trim().toLocaleLowerCase('tr');
  const shown = ql ? rows.filter((r) => [r.cls, r.subject, r.teacher, String(r.dur)].some((x) => x.toLocaleLowerCase('tr').includes(ql))) : rows;
  return (
    <Window title="Sınıf Dersleri & Atama Listesi" onClose={closeScreen} width={860} footer={<><span className="muted">{shown.length} satır · {shown.reduce((s, r) => s + r.dur, 0)} saat</span><span className="sp" /><Btn kind="primary" onClick={closeScreen}>Kapat</Btn></>}>
      <div className="toolbar">
        <b>Sınıf Dersleri &amp; Atama Listesi</b><span className="sp" />
        <input placeholder="Sınıf, Ders veya Öğretmen Ara..." value={q} onChange={(e) => setQ(e.target.value)} style={{ width: 260 }} />
        <Btn onClick={() => openScreen({ kind: 'print', preset: { entity: 'class_list' } })}>Yazdır / PDF Önizle</Btn>
      </div>
      <div className="dtable-wrap" style={{ maxHeight: '60vh' }}>
        <table className="dtable">
          <thead><tr><th>Sınıf</th><th>Ders</th><th>Öğretmen</th><th>Haftalık Saat</th></tr></thead>
          <tbody>{shown.map((r, i) => <tr key={i}><td>{r.cls}</td><td>{r.subject}</td><td>{r.teacher}</td><td className="center">{r.dur}</td></tr>)}</tbody>
        </table>
      </div>
    </Window>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Ders Programı Karşılaştırma (Diff)
// ════════════════════════════════════════════════════════════════════════════
const sig = (a: any) => `${norm(classNameOf(a))}_${norm(teacherOf(a))}_${norm(subjectOf(a))}_${hoursOf(a)}`;

export function CompareScreen() {
  const data = useApp((s) => s.data);
  const inst = useApp((s) => s.inst);
  const [old, setOld] = useState<{ label: string; data: any } | null>(null);
  const [versions, setVersions] = useState<VersionInfo[] | null>(null);
  const file = useRef<HTMLInputElement>(null);
  const diff = useMemo(() => {
    if (!old) return null;
    const oa: any[] = old.data.atamalar ?? [], na: any[] = data.atamalar ?? [];
    const os = new Set(oa.map(sig)), ns = new Set(na.map(sig));
    const added = na.filter((a) => !os.has(sig(a))), removed = oa.filter((a) => !ns.has(sig(a)));
    const cellKey = (p: any) => `${norm(p.class_name || p.class)}|${int0(p.day ?? p.col)}|${int0(p.period ?? p.row)}|${norm(p.subject_name || p.subject)}|${norm(p.teacher_name || p.teacher)}`;
    const oc = new Set((old.data.grid_placements ?? []).map(cellKey)), nc = new Set((data.grid_placements ?? []).map(cellKey));
    const moved = [...nc].filter((k) => !oc.has(k)).length + [...oc].filter((k) => !nc.has(k)).length;
    return { added, removed, moved, oldPlaced: (old.data.grid_placements ?? []).length, newPlaced: (data.grid_placements ?? []).length };
  }, [old, data]);
  const openFile = async (f: File) => {
    try {
      const d = JSON.parse(await f.text());
      if (!d || !Array.isArray(d.atamalar)) throw new Error('Bu dosya bir Chenkron (.roz) çizelgesi değil.');
      setOld({ label: f.name, data: d });
    } catch (e: any) { await tell('Hata', `Dosya okunurken hata oluştu:\n${String(e?.message ?? e)}`); }
  };
  return (
    <Window title="Ders Programı Karşılaştırma (Diff)" onClose={closeScreen} width={860} footer={<><span className="sp" /><Btn kind="primary" onClick={closeScreen}>Kapat</Btn></>}>
      <div className="toolbar">
        <span>{old ? `Seçilen: ${old.label}` : 'Lütfen karşılaştırmak istediğiniz eski dosyayı ya da kayıtlı bir sürümü seçin.'}</span>
        <span className="sp" />
        <Btn onClick={() => file.current?.click()}>Eski Dosyayı Seç</Btn>
        {inst && <Btn onClick={async () => setVersions(await listVersions(inst.slug))}>Kayıtlı Sürümden…</Btn>}
      </div>
      <input ref={file} type="file" accept=".roz,.json" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) void openFile(f); e.target.value = ''; }} />
      {versions && inst && (
        <div className="card">
          <div className="card-title">{inst.name} — kayıtlı sürümler</div>
          <div className="pick-list" style={{ maxHeight: '24vh' }}>
            {[...versions].reverse().map((v) => (
              <div key={v.id} className="multi-item" onClick={async () => { const d = await loadVersionData(inst.slug, v.id); if (d) { setOld({ label: `${versionLabel(v)} (${new Date(v.created).toLocaleString('tr-TR')})`, data: d }); setVersions(null); } }}>
                <b>{versionLabel(v)}</b><span className="muted small">{new Date(v.created).toLocaleString('tr-TR')} · {v.summary.placed}/{v.summary.assigned} saat</span>
              </div>
            ))}
            {!versions.length && <div className="muted small">Bu kurumda kayıtlı sürüm yok.</div>}
          </div>
        </div>
      )}
      {diff && (
        <>
          <div className="muted small" style={{ marginBottom: 8 }}>Yerleşim: eski {diff.oldPlaced} kayıt, şimdi {diff.newPlaced} kayıt · {diff.moved} hücre farklı.</div>
          {!diff.added.length && !diff.removed.length ? <div className="card">Mevcut program ile seçilen eski programın atamaları tamamen aynı. Hiçbir fark bulunamadı.</div> : (
            <div className="dtable-wrap" style={{ maxHeight: '52vh' }}>
              <table className="dtable">
                <thead><tr><th>Sınıf</th><th>Öğretmen</th><th>Ders</th><th>Saat</th><th>Değişim Durumu</th></tr></thead>
                <tbody>
                  {diff.added.map((a, i) => <tr key={`a${i}`} className="diff-add"><td>{classNameOf(a)}</td><td>{teacherOf(a)}</td><td>{subjectOf(a)}</td><td>{hoursOf(a)}</td><td>YENİ EKLENDİ</td></tr>)}
                  {diff.removed.map((a, i) => <tr key={`r${i}`} className="diff-del"><td>{classNameOf(a)}</td><td>{teacherOf(a)}</td><td>{subjectOf(a)}</td><td>{hoursOf(a)}</td><td>SİLİNMİŞ</td></tr>)}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </Window>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Dersliklere Atama
// ════════════════════════════════════════════════════════════════════════════
type Key = [string, string, string];
const keyOf = (e: any): Key => [norm(e.class || e.sinif || e.class_name), norm(e.subject || e.ders || e.subject_name), norm(e.teacher || e.ogretmen || e.teacher_name)];
const ks = (k: Key) => k.join('\u0001');
const roomOf = (p: any) => norm(p.room_name || p.room || p.derslik);

/** room_assign_dialog.auto_assign_rooms — elle seçilmiş derslikler korunur. */
function autoAssignRooms(d: any): { assigned: number; skipped: number; reasons: string[] } {
  const rooms = (d.derslikler ?? []).filter((r: any) => r && typeof r === 'object');
  if (!rooms.length) return { assigned: 0, skipped: 0, reasons: ['Tanımlı derslik yok.'] };
  const sizes = new Map<string, number | null>();
  for (const c of d.siniflar ?? []) if (c && typeof c === 'object') sizes.set(norm(c.ad || c.name), intOrNull(c.kapasite || c.mevcut));
  const taken = new Set<string>();
  for (const p of d.grid_placements ?? []) {
    if (!p || typeof p !== 'object') continue;
    const r = roomOf(p);
    if (!r) continue;
    const day = int0(p.day ?? p.col), st = int0(p.period ?? p.row);
    for (let o = 0; o < Math.max(1, int0(p.duration) || 1); o++) taken.add(`${r}|${day}|${st + o}`);
  }
  let assigned = 0, skipped = 0;
  const reasons: string[] = [];
  const byKey = new Map<string, string>();
  const pls = (d.grid_placements ?? []).filter((p: any) => p && typeof p === 'object').sort((a: any, b: any) => int0(a.day) - int0(b.day) || int0(a.period) - int0(b.period));
  for (const p of pls) {
    if (roomOf(p)) continue;
    const day = int0(p.day ?? p.col), st = int0(p.period ?? p.row), span = Math.max(1, int0(p.duration) || 1);
    const cls = norm(p.class_name || p.class);
    const need = sizes.get(cls) ?? null;
    let chosen: string | null = null;
    for (const room of rooms) {
      const name = norm(room.ad || room.name);
      if (!name) continue;
      const cap = intOrNull(room.kapasite);
      if (need !== null && cap !== null && cap < need) continue;
      if (Array.from({ length: span }, (_, o) => `${name}|${day}|${st + o}`).some((k) => taken.has(k))) continue;
      chosen = name;
      break;
    }
    if (!chosen) { skipped++; reasons.push(`${cls} — ${norm(p.subject_name || p.subject)} (${day + 1}. gün ${st + 1}. saat): uygun boş derslik yok`); continue; }
    p.room_name = chosen; p.room = chosen;
    for (let o = 0; o < span; o++) taken.add(`${chosen}|${day}|${st + o}`);
    assigned++;
    byKey.set(ks(keyOf(p)), chosen);
  }
  for (const a of d.atamalar ?? []) if (a && typeof a === 'object' && !norm(a.room || a.derslik)) { const r = byKey.get(ks(keyOf(a))); if (r) a.room = r; }
  return { assigned, skipped, reasons };
}

export function RoomsScreen() {
  const [work, setWork] = useState<any>(() => structuredClone(getState().data));
  const [sel, setSel] = useState<string[]>(() => (work.atamalar ?? []).filter((a: any) => a && typeof a === 'object').map((a: any) => norm(a.room || a.derslik)));
  const rooms = (work.derslikler ?? []).filter((r: any) => r && typeof r === 'object' && norm(r.ad || r.name)).map((r: any) => ({ name: norm(r.ad || r.name), cap: intOrNull(r.kapasite), kind: norm(r.tur) }));
  const entries: any[] = (work.atamalar ?? []).filter((a: any) => a && typeof a === 'object');
  const sizes = new Map<string, number | null>();
  for (const c of work.siniflar ?? []) if (c && typeof c === 'object') sizes.set(norm(c.ad || c.name), intOrNull(c.kapasite || c.mevcut));
  const caps = new Map<string, number | null>(rooms.map((r: any) => [r.name, r.cap] as [string, number | null]));
  const slotsOf = useMemo(() => {
    const m = new Map<string, Set<string>>();
    for (const p of work.grid_placements ?? []) {
      if (!p || typeof p !== 'object') continue;
      const k = ks(keyOf(p));
      const set = m.get(k) ?? m.set(k, new Set()).get(k)!;
      const day = int0(p.day ?? p.col), st = int0(p.period ?? p.row);
      for (let o = 0; o < Math.max(1, int0(p.duration) || 1); o++) set.add(`${day}|${st + o}`);
    }
    return m;
  }, [work]);
  const status = (i: number): [string, string] => {
    const room = sel[i];
    if (!room) return ['Derslik atanmadı', 'muted'];
    const k = keyOf(entries[i]);
    const size = sizes.get(k[0]) ?? null, cap = caps.get(room) ?? null;
    if (size !== null && cap !== null && cap < size) return [`Kapasite yetersiz (${cap} < ${size})`, 'txt-bad'];
    const mine = slotsOf.get(ks(k));
    if (mine?.size) {
      for (let j = 0; j < entries.length; j++) {
        if (j === i || sel[j] !== room) continue;
        const ok = keyOf(entries[j]);
        const other = slotsOf.get(ks(ok));
        if (other && [...mine].some((s) => other.has(s))) return [`Çakışma: ${ok[0]} ${ok[1]}`, 'txt-bad'];
      }
    }
    return ['Uygun', 'txt-ok'];
  };
  const stats = entries.map((_, i) => status(i));
  const bad = stats.filter(([t]) => t.startsWith('Çakışma') || t.startsWith('Kapasite')).length;
  const hoursOfKey = (k: Key) => (work.grid_placements ?? []).filter((p: any) => p && ks(keyOf(p)) === ks(k)).reduce((s: number, p: any) => s + Math.max(1, int0(p.duration) || 1), 0);

  const auto = async () => {
    if (!(work.derslikler ?? []).length) { await tell('Derslik Yok', 'Önce en az bir derslik tanımlamalısınız.'); return; }
    const next = structuredClone(work);
    for (let i = 0; i < entries.length; i++) { const a = (next.atamalar ?? []).filter((x: any) => x && typeof x === 'object')[i]; if (sel[i]) a.room = sel[i]; }
    const r = autoAssignRooms(next);
    setWork(next);
    setSel((next.atamalar ?? []).filter((a: any) => a && typeof a === 'object').map((a: any) => norm(a.room || a.derslik)));
    let msg = `${r.assigned} ders için derslik atandı.`;
    if (r.skipped) msg += `\n${r.skipped} ders yerleştirilemedi:\n\n` + r.reasons.slice(0, 12).join('\n') + (r.reasons.length > 12 ? `\n… ve ${r.reasons.length - 12} tane daha` : '');
    await tell('Otomatik Derslik Atama', msg);
  };
  const save = async () => {
    if (bad && !(await ask({ title: 'Sorunlu Atamalar', body: `${bad} derste çakışma veya kapasite sorunu var.\n\nYine de kaydedilsin mi? Sorunlar listede kırmızı kalır, sonradan düzeltebilirsiniz.`, ok: 'Kaydet', cancel: 'Vazgeç', tone: 'warn' }))) return;
    const byKey = new Map<string, string>();
    const selCopy = [...sel];
    mutate('Derslik atamaları', (d) => {
      const list = (d.atamalar ?? []).filter((a: any) => a && typeof a === 'object');
      list.forEach((a: any, i: number) => {
        const room = selCopy[i] ?? '';
        byKey.set(ks(keyOf(a)), room);
        if (room) a.room = room; else { delete a.room; delete a.derslik; }
      });
      for (const p of d.grid_placements ?? []) {
        if (!p || typeof p !== 'object') continue;
        const room = byKey.get(ks(keyOf(p)));
        if (room) { p.room_name = room; p.room = room; }
        else if (room === '') { delete p.room_name; delete p.room; delete p.derslik; }
      }
    });
    closeScreen();
  };
  return (
    <Window title="Dersliklere Atama" onClose={closeScreen} width={1000}
      footer={<>
        <Btn onClick={() => void auto()}>Otomatik Ata</Btn>
        <Btn onClick={async () => { if (await ask({ title: 'Tümünü Temizle', body: 'Bütün derslik atamaları kaldırılsın mı? Ders programı değişmez.', ok: 'Temizle', cancel: 'Vazgeç' })) setSel(sel.map(() => '')); }}>Tümünü Temizle</Btn>
        <span className="muted">{entries.length} ders · {sel.filter(Boolean).length} derslik atandı{bad ? ` · ${bad} sorunlu` : ''}{!rooms.length ? ' · Tanımlı derslik yok — önce Tanımlama İşlemleri → Derslikler.' : ''}</span>
        <span className="sp" />
        <Btn onClick={closeScreen}>Vazgeç</Btn>
        <Btn kind="primary" onClick={() => void save()}>Kaydet</Btn>
      </>}>
      <b>Her ders için derslik seçin</b>
      <div className="dtable-wrap" style={{ maxHeight: '60vh', marginTop: 8 }}>
        <table className="dtable">
          <thead><tr><th>Sınıf</th><th>Ders</th><th>Öğretmen</th><th>Saat</th><th>Derslik</th><th>Durum</th></tr></thead>
          <tbody>{entries.map((a, i) => {
            const k = keyOf(a);
            const [st, cls] = stats[i];
            return (
              <tr key={i}>
                <td>{k[0]}</td><td>{k[1]}</td><td>{k[2]}</td><td className="center">{hoursOfKey(k) || intOrNull(a.duration) || 0}</td>
                <td><select value={sel[i] ?? ''} onChange={(e) => setSel((s) => s.map((x, j) => (j === i ? e.target.value : x)))}>
                  <option value="">— derslik yok —</option>
                  {rooms.map((r: any) => <option key={r.name} value={r.name}>{r.name}{r.cap || r.kind ? `  (${[r.cap ? `${r.cap} kişi` : '', r.kind].filter(Boolean).join(', ')})` : ''}</option>)}
                </select></td>
                <td className={cls}>{st}</td>
              </tr>
            );
          })}</tbody>
        </table>
      </div>
    </Window>
  );
}
