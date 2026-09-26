// Tanımlama pencereleri: Seçmeli Dersler (electives_dialog.py), Kısıtlamalar
// (constraints_dialog.py) ve Sınıf Grupları (groups_dialog.py).
import { useState } from 'react';
import { CLOSED, OPEN, getMatrix } from '../../engine/data.ts';
import { candidateStore } from '../feasibility.ts';
import { setMatrix, syncAll } from '../datastore.ts';
import { dims } from '../model.ts';
import { runPreflight } from '../preflight.ts';
import { ask, closeScreen, mutate, tell, useApp } from '../store.ts';
import { Btn, Window } from '../ui.tsx';

// ════════════════════════════════════════════════════════════════════════════
// Seminerler / Seçmeli Dersler
// ════════════════════════════════════════════════════════════════════════════
export function ElectivesScreen() {
  const data = useApp((s) => s.data);
  const list: any[] = data.secmeli_dersler ?? [];
  const [sel, setSel] = useState<number | null>(null);
  const [edit, setEdit] = useState<{ index: number | null } | null>(null);
  const [pickCls, setPickCls] = useState(false);
  const [clsSel, setClsSel] = useState<string | null>(null);
  const cur = sel !== null ? list[sel] : null;

  const del = async () => {
    if (sel === null) return;
    if (!(await ask({ title: 'Sil', body: 'Bu semineri silmek istediğinize emin misiniz?', ok: 'Sil', cancel: 'Vazgeç', tone: 'danger' }))) return;
    mutate('Seminer silindi', (d) => { d.secmeli_dersler.splice(sel, 1); });
    setSel(null);
  };
  return (
    <Window title="Seminerler" onClose={closeScreen} width={900} footer={<><span className="sp" /><Btn kind="primary" onClick={closeScreen}>Kapat</Btn></>}>
      <div className="split">
        <div className="pane">
          <div className="card-title">Seminerler / Seçmeli Dersler</div>
          <div className="dtable-wrap" style={{ maxHeight: '50vh' }}>
            <table className="dtable">
              <thead><tr><th>Seminer</th><th>Saat</th><th>Öğretmen</th></tr></thead>
              <tbody>
                {list.map((x, i) => (
                  <tr key={i} className={sel === i ? 'sel' : ''} onClick={() => { setSel(i); setClsSel(null); }} onDoubleClick={() => setEdit({ index: i })}>
                    <td>{x.ad ?? ''}</td><td>{String(x.saat ?? 2)}</td><td>{x.ogretmen ?? 'Atanmadı'}</td>
                  </tr>
                ))}
                {!list.length && <tr><td colSpan={3} className="muted center">Henüz seminer / seçmeli ders yok.</td></tr>}
              </tbody>
            </table>
          </div>
          <div className="toolbar" style={{ marginTop: 8 }}>
            <Btn kind="primary" onClick={() => setEdit({ index: null })}>Ekle</Btn>
            <Btn disabled={sel === null} onClick={() => sel !== null && setEdit({ index: sel })}>Düzenle</Btn>
            <Btn disabled={sel === null} onClick={() => void del()}>Sil</Btn>
          </div>
        </div>
        <div className="pane">
          <div className="card-title">Seçili Seminere Atanan Sınıflar</div>
          <div className="dtable-wrap" style={{ maxHeight: '50vh' }}>
            <table className="dtable">
              <thead><tr><th>Sınıf / Grup</th></tr></thead>
              <tbody>
                {(cur?.siniflar ?? []).map((c: string) => <tr key={c} className={clsSel === c ? 'sel' : ''} onClick={() => setClsSel(c)}><td>{c}</td></tr>)}
                {cur && !(cur.siniflar ?? []).length && <tr><td className="muted center">Sınıf eklenmedi.</td></tr>}
                {!cur && <tr><td className="muted center">Soldan bir seminer seçin.</td></tr>}
              </tbody>
            </table>
          </div>
          <div className="toolbar" style={{ marginTop: 8 }}>
            <Btn disabled={!cur} onClick={() => setPickCls(true)}>Sınıf Ekle</Btn>
            <Btn disabled={!cur || !clsSel} onClick={() => {
              if (sel === null || !clsSel) return;
              mutate('Seminerden sınıf çıkarıldı', (d) => { const s = d.secmeli_dersler[sel]; s.siniflar = (s.siniflar ?? []).filter((x: string) => x !== clsSel); });
              setClsSel(null);
            }}>Sınıfı Çıkar</Btn>
          </div>
        </div>
      </div>
      {edit && <SeminarForm data={data} seminar={edit.index !== null ? list[edit.index] : null} onClose={() => setEdit(null)}
        onSave={async (nd) => {
          if (!nd.ad) { await tell('Hata', 'Seminer adı boş olamaz!'); return; }
          mutate(edit.index === null ? 'Seminer eklendi' : 'Seminer güncellendi', (d) => {
            d.secmeli_dersler ??= [];
            if (edit.index === null) d.secmeli_dersler.push(nd); else d.secmeli_dersler[edit.index] = nd;
          });
          setEdit(null);
        }} />}
      {pickCls && cur && <ClassCheckList data={data} onClose={() => setPickCls(false)} onOk={(cls) => {
        if (sel === null) return;
        mutate('Seminere sınıf eklendi', (d) => {
          const s = d.secmeli_dersler[sel];
          const ex: string[] = s.siniflar ?? [];
          for (const c of cls) if (!ex.includes(c)) ex.push(c);
          s.siniflar = ex;
        });
        setPickCls(false);
      }} />}
    </Window>
  );
}

function SeminarForm({ data, seminar, onSave, onClose }: { data: any; seminar: any | null; onSave: (d: any) => void; onClose: () => void }) {
  const sd = seminar ?? {};
  const teachers = ['Atanmadı', ...(data.ogretmenler ?? []).map((t: any) => t.ad).filter(Boolean)];
  const [ad, setAd] = useState<string>(sd.ad ?? '');
  const [og, setOg] = useState<string>(teachers.includes(sd.ogretmen) ? sd.ogretmen : 'Atanmadı');
  const [saat, setSaat] = useState<number>(sd.saat ?? 2);
  return (
    <Window title="Seminer / Seçmeli Ders" onClose={onClose} width={460}
      footer={<><span className="sp" /><Btn onClick={onClose}>İptal</Btn><Btn kind="primary" onClick={() => onSave({ ad: ad.trim(), ogretmen: og, saat, siniflar: sd.siniflar ?? [] })}>Tamam</Btn></>}>
      <label className="field"><span className="field-label">Seminer / Seçmeli Adı</span><input autoFocus value={ad} onChange={(e) => setAd(e.target.value)} /></label>
      <label className="field"><span className="field-label">Öğretmen</span>
        <select value={og} onChange={(e) => setOg(e.target.value)}>{teachers.map((t: string) => <option key={t} value={t}>{t}</option>)}</select></label>
      <label className="field"><span className="field-label">Haftalık Ders Saati</span>
        <input type="number" min={1} max={10} value={saat} onChange={(e) => setSaat(Math.max(1, Math.min(10, Number(e.target.value) || 1)))} style={{ width: 90 }} /></label>
    </Window>
  );
}

function ClassCheckList({ data, onOk, onClose }: { data: any; onOk: (cls: string[]) => void; onClose: () => void }) {
  const classes: string[] = (data.siniflar ?? []).map((s: any) => s.ad).filter(Boolean);
  const [on, setOn] = useState<Set<string>>(new Set());
  return (
    <Window title="Sınıf Seçimi" onClose={onClose} width={380}
      footer={<><span className="sp" /><Btn onClick={onClose}>İptal</Btn><Btn kind="primary" onClick={() => onOk(classes.filter((c) => on.has(c)))}>Tamam</Btn></>}>
      <div className="pick-list">
        {classes.map((c) => (
          <label key={c} className="multi-item"><input type="checkbox" checked={on.has(c)} onChange={(e) => setOn((s) => { const n = new Set(s); if (e.target.checked) n.add(c); else n.delete(c); return n; })} /><span>{c}</span></label>
        ))}
      </div>
    </Window>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Gelişmiş Planlama ve Zaman Kısıtlamaları (ConstraintsDialog)
// ════════════════════════════════════════════════════════════════════════════
const WIN_OPTS = ['Fark Etmez (Esnek)', 'Sabah Saatleri (1-4. Saatler)', 'Öğleden Sonra Saatleri'];

export function ConstraintsScreen({ target, name }: { target: 'ogretmen' | 'sinif'; name?: string }) {
  const data = useApp((s) => s.data);
  const key = target === 'ogretmen' ? 'ogretmenler' : 'siniflar';
  const items: string[] = (data[key] ?? []).map((x: any) => x.ad).filter(Boolean).sort();
  const { D, P, days } = dims(data);
  const [tab, setTab] = useState(0);
  const [cur, setCur] = useState<string>(() => (name && items.includes(name) ? name : items[0] ?? ''));
  const [matrices, setMatrices] = useState<Record<string, number[][]>>({});
  const c0 = data.constraints ?? {};
  const [noHard, setNoHard] = useState<boolean>(c0.no_consecutive_hard ?? true);
  const [gaps, setGaps] = useState<boolean>(c0.limit_teacher_gaps ?? true);
  const [maxDaily, setMaxDaily] = useState<boolean>((c0.max_daily_same_subject ?? 2) === 2);
  const subjects: string[] = (data.dersler ?? []).map((d: any) => d.ad).filter(Boolean).sort();
  const [windows, setWindows] = useState<Record<string, number>>(() => {
    const out: Record<string, number> = {};
    for (const s of subjects) { const v = (c0.subject_windows ?? {})[s]; out[s] = v === 'morning' ? 1 : v === 'afternoon' ? 2 : 0; }
    return out;
  });

  const entityIndex = (n: string) => (data[key] ?? []).findIndex((x: any) => x.ad === n);
  const matrixOf = (n: string): number[][] => {
    if (matrices[n]) return matrices[n];
    const i = entityIndex(n);
    return getMatrix(i >= 0 ? data[key][i] : {}, n, data);
  };
  const setCell = (d: number, p: number, st: number) => {
    if (!cur) return;
    const m = matrixOf(cur).map((r) => [...r]);
    m[d][p] = st;
    setMatrices((all) => ({ ...all, [cur]: m }));
  };
  const setAll = (fn: (m: number[][]) => void) => {
    if (!cur) return;
    const m = matrixOf(cur).map((r) => [...r]);
    fn(m);
    setMatrices((all) => ({ ...all, [cur]: m }));
  };

  const save = async () => {
    // Ön kontrol: düzenlenen bütün birimler uygulanmış hâlde.
    let probe: any = null;
    for (const [n, m] of Object.entries(matrices)) {
      const i = entityIndex(n);
      if (i < 0) continue;
      probe = candidateStore(probe ?? data, key, i, m, null);
    }
    if (probe && !(await runPreflight(probe, 'save'))) return;
    mutate('Kısıtlamalar kaydedildi', (d) => {
      const c = (d.constraints ??= {});
      c.no_consecutive_hard = noHard;
      c.limit_teacher_gaps = gaps;
      c.max_daily_same_subject = maxDaily ? 2 : 4;
      const sw: Record<string, string> = {};
      for (const [s, v] of Object.entries(windows)) if (v === 1) sw[s] = 'morning'; else if (v === 2) sw[s] = 'afternoon';
      c.subject_windows = sw;
      for (const [n, m] of Object.entries(matrices)) {
        const ent = (d[key] ?? []).find((x: any) => x.ad === n);
        if (ent) setMatrix(d, key, ent, m);
      }
      syncAll(d);
    });
    closeScreen();
  };

  const m = cur ? matrixOf(cur) : [];
  return (
    <Window title="Gelişmiş Planlama ve Zaman Kısıtlamaları" onClose={closeScreen} width={960}
      footer={<><span className="sp" /><Btn onClick={closeScreen}>İptal</Btn><Btn kind="primary" onClick={() => void save()}>Kaydet ve Uygula</Btn></>}>
      <div className="tabs">
        <button className={tab === 0 ? 'on' : ''} onClick={() => setTab(0)}>Zaman Müsaitlik Matrisi</button>
        <button className={tab === 1 ? 'on' : ''} onClick={() => setTab(1)}>Gelişmiş Pedagojik Ayarlar</button>
      </div>
      {tab === 0 && (
        <>
          <div className="toolbar">
            <span>{target === 'ogretmen' ? 'Öğretmen' : 'Sınıf'}:</span>
            <select value={cur} onChange={(e) => setCur(e.target.value)} style={{ minWidth: 240 }}>{items.map((n) => <option key={n} value={n}>{n}{matrices[n] ? ' •' : ''}</option>)}</select>
            <span className="sp" />
            <Btn onClick={() => setAll((mm) => { for (let d = 0; d < D; d++) for (let p = 0; p < P; p++) mm[d][p] = OPEN; })}>Tümünü Uygun Yap (✓)</Btn>
          </div>
          <div className="muted small" style={{ marginBottom: 8 }}>Hücreye tıklayarak müsait ✓ / kapalı ✗ arasında çevirin. Bu ekran Zaman Tablosu ekranıyla aynı veriyi kullanır; birinde yaptığınız değişiklik diğerine de yansır.</div>
          {cur ? (
            <table className="toff">
              <thead><tr><th />{days.map((dn) => <th key={dn}>{dn}</th>)}</tr></thead>
              <tbody>
                {Array.from({ length: P }, (_, p) => (
                  <tr key={p}>
                    <th>{p + 1}. Ders</th>
                    {Array.from({ length: D }, (_, d) => {
                      const st = m[d]?.[p];
                      return <td key={d} className={`tc ${st === CLOSED ? 'shut' : 'open'}`} onClick={() => setCell(d, p, st === CLOSED ? OPEN : CLOSED)}>{st === CLOSED ? '✗ KAPALI' : '✓ Müsait'}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p className="muted">Kayıt yok.</p>}
          <div className="toolbar" style={{ marginTop: 8 }}>
            <span className="muted small">Hızlı Gün Kapat:</span>
            {days.map((dn, d) => <Btn key={dn} onClick={() => setAll((mm) => { for (let p = 0; p < P; p++) mm[d][p] = CLOSED; })}>{dn} Kapat</Btn>)}
          </div>
        </>
      )}
      {tab === 1 && (
        <>
          <div className="card">
            <div className="card-title">Pedagojik Dağılım ve Sağlık Kuralları</div>
            <label className="check"><input type="checkbox" checked={noHard} onChange={(e) => setNoHard(e.target.checked)} /> İki zor ders (Matematik, Fizik, Kimya, Biyoloji, Geometri vb.) aynı gün art arda gelmesin</label>
            <label className="check"><input type="checkbox" checked={gaps} onChange={(e) => setGaps(e.target.checked)} /> Öğretmenlerin haftalık programında boş saatler (pencere) minimize edilsin</label>
            <label className="check"><input type="checkbox" checked={maxDaily} onChange={(e) => setMaxDaily(e.target.checked)} /> Bir günde aynı dersten en fazla 2 saat blok ders yerleştirilsin</label>
          </div>
          <div className="card">
            <div className="card-title">Ders Bazlı Saat Tercihi (X Dersi Sabah / Öğle Saatlerine Yerleşsin)</div>
            <div className="dtable-wrap" style={{ maxHeight: '36vh' }}>
              <table className="dtable">
                <thead><tr><th>Ders Adı</th><th>Öncelikli Yerleşim Zamanı</th></tr></thead>
                <tbody>{subjects.map((s) => (
                  <tr key={s}><td>{s}</td><td><select value={windows[s] ?? 0} onChange={(e) => setWindows((w) => ({ ...w, [s]: Number(e.target.value) }))}>{WIN_OPTS.map((o, i) => <option key={o} value={i}>{o}</option>)}</select></td></tr>
                ))}</tbody>
              </table>
            </div>
          </div>
          <div className="muted small">Not: Otomatik planlayıcı bu sekmedeki tercihleri değil, Planlama İlişkileri'ndeki kuralları uygular. Motorun uymasını istediğiniz kuralları oradan ekleyin.</div>
        </>
      )}
    </Window>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Sınıf Ders Grupları ve Şube Bölünmeleri (GroupsDialog)
// ════════════════════════════════════════════════════════════════════════════
export function GroupsScreen() {
  const data = useApp((s) => s.data);
  const classes: string[] = (data.siniflar ?? []).map((s: any) => s.ad ?? '');
  const [cls, setCls] = useState<string>(classes[0] ?? '');
  const [groups, setGroups] = useState<any[]>(() => structuredClone(data.gruplar ?? []));
  const [sel, setSel] = useState<number | null>(null);
  const [name, setName] = useState('');
  const shown = groups.map((g, i) => ({ g, i })).filter((x) => x.g.sinif === cls);
  return (
    <Window title="Sınıf Ders Grupları ve Şube Bölünmeleri" onClose={closeScreen} width={720}
      footer={<><span className="sp" /><Btn onClick={closeScreen}>İptal</Btn><Btn kind="primary" onClick={() => { mutate('Sınıf grupları', (d) => { d.gruplar = groups; }); closeScreen(); }}>Kaydet ve Kapat</Btn></>}>
      <div className="toolbar">
        <span>Sınıf Seçin:</span>
        <select value={cls} onChange={(e) => { setCls(e.target.value); setSel(null); }}>{classes.map((c) => <option key={c} value={c}>{c}</option>)}</select>
      </div>
      <div className="dtable-wrap" style={{ maxHeight: '44vh' }}>
        <table className="dtable">
          <thead><tr><th>Grup Adı</th><th>Kısa Adı</th><th>Öğrenci / Ders Detayı</th></tr></thead>
          <tbody>
            {shown.map(({ g, i }) => <tr key={i} className={sel === i ? 'sel' : ''} onClick={() => setSel(i)}><td>{g.ad}</td><td>{g.kisa}</td><td>{g.detay}</td></tr>)}
            {!shown.length && <tr><td colSpan={3} className="muted center">Bu sınıf için grup yok.</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="toolbar" style={{ marginTop: 8 }}>
        <input placeholder="Grup Adı (Örn: Seçmeli İngilizce)" value={name} onChange={(e) => setName(e.target.value)} style={{ flex: 1 }} />
        <Btn kind="primary" disabled={!name.trim() || !cls} onClick={() => { setGroups((g) => [...g, { sinif: cls, ad: name.trim(), kisa: name.trim().slice(0, 4).toUpperCase(), detay: 'Tüm Sınıf / Şube' }]); setName(''); }}>Yeni Grup Ekle</Btn>
        <Btn disabled={sel === null} onClick={() => { if (sel !== null) { setGroups((g) => g.filter((_, i) => i !== sel)); setSel(null); } }}>Grubu Sil</Btn>
      </div>
    </Window>
  );
}
