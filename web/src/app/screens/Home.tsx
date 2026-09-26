// home_dashboard.py (Anasayfa: kurumlar ve sürümler) + startup_wizard.py
// (Yeni Kurum Sihirbazı). Veriler tarayıcıda (IndexedDB) tutulur.
import { useEffect, useRef, useState } from 'react';
import { autoShortCode, formatTrName } from '../datastore.ts';
import { ask, closeScreen, getState, load, openScreen, promptText, tell, useApp } from '../store.ts';
import {
  INST_COLORS, addVersion, createInstitution, deleteInstitution, deleteVersion, listInstitutions, listVersions, loadVersionData,
  openVersion, patchVersion, updateInstitution, versionLabel,
} from '../versions.ts';
import type { Institution, VersionInfo } from '../versions.ts';
import { Btn, Icon, Window } from '../ui.tsx';

const SAMPLES: string[] = import.meta.env.DEV ? ['birey_v161', 'bogazici_v227', 'bogazici_v229'] : [];

async function readRoz(f: File): Promise<any> {
  const data = JSON.parse(await f.text());
  if (!data || typeof data !== 'object' || !Array.isArray(data.atamalar)) throw new Error('Bu dosya bir Chenkron (.roz) çizelgesi değil.');
  return data;
}

function downloadJson(name: string, data: any) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
  a.download = name.endsWith('.roz') ? name : `${name}.roz`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

const when = (t: number) => new Date(t).toLocaleString('tr-TR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });

/** Anasayfa içeriği: hem veri yokken ana ekran, hem de şeritteki "Anasayfa" penceresi. */
export function HomeBody({ onOpenFile }: { onOpenFile: () => void }) {
  const cur = useApp((s) => s.inst);
  const [insts, setInsts] = useState<Institution[]>([]);
  const [sel, setSel] = useState<string | null>(cur?.slug ?? null);
  const [versions, setVersions] = useState<VersionInfo[]>([]);
  const [tick, setTick] = useState(0);
  const importRef = useRef<HTMLInputElement>(null);
  const refresh = () => setTick((x) => x + 1);

  useEffect(() => {
    void (async () => {
      const list = await listInstitutions();
      setInsts(list);
      const s = sel && list.some((x) => x.slug === sel) ? sel : list[0]?.slug ?? null;
      setSel(s);
      setVersions(s ? await listVersions(s) : []);
    })();
  }, [tick, sel]);

  const inst = insts.find((x) => x.slug === sel) ?? null;

  const newInst = async () => {
    const name = await promptText('Yeni Eğitim Kurumu Ekle', 'Bağımsız ders çizelgeleri ve sürüm alanı tanımlayın.', '', 'Örn: Boğaziçi Eğitim Kurumları, Birey Kurs...');
    if (!name?.trim()) return;
    const c = await createInstitution(name.trim(), INST_COLORS[insts.length % INST_COLORS.length]);
    setSel(c.slug);
    refresh();
  };
  const importRoz = async (f: File) => {
    try {
      const data = await readRoz(f);
      let target = inst;
      if (!target) target = await createInstitution(f.name.replace(/\.(roz|json)$/i, ''), INST_COLORS[insts.length % INST_COLORS.length]);
      await addVersion(target.slug, data, 'import', `İçe aktarıldı: ${f.name}`);
      setSel(target.slug);
      refresh();
    } catch (e: any) { await tell('Dosya açılamadı', String(e?.message ?? e)); }
  };
  const openSample = async (name: string) => {
    const r = await fetch(`/samples/${name}.roz`);
    load(await r.json(), name);
  };

  return (
    <div className="home">
      <aside className="home-left">
        <div className="home-lh"><b>Kurumlar</b><Btn onClick={() => void newInst()}><Icon name="plus" size={14} /> Yeni Kurum</Btn></div>
        <div className="inst-list">
          {insts.map((x) => (
            <button key={x.slug} className={`inst-card${x.slug === sel ? ' on' : ''}`} onClick={() => setSel(x.slug)} onDoubleClick={() => setSel(x.slug)}>
              <span className="inst-dot" style={{ background: x.color }}>{x.name.slice(0, 1).toLocaleUpperCase('tr')}</span>
              <span className="inst-meta"><b>{x.name}</b><small>{x.slug === cur?.slug ? 'Açık · ' : ''}{when(x.updated)}</small></span>
            </button>
          ))}
          {!insts.length && <div className="muted small" style={{ padding: 10 }}>Henüz kurum yok. "Yeni Kurum" ile başlayın ya da bir .roz dosyası açın.</div>}
        </div>
        <div className="home-actions">
          <Btn onClick={onOpenFile}><Icon name="open" size={14} /> .roz dosyası aç</Btn>
          {SAMPLES.map((s) => <Btn key={s} onClick={() => void openSample(s)}>{s}</Btn>)}
        </div>
      </aside>
      <main className="home-main">
        {inst ? (
          <>
            <div className="home-mh">
              <span className="inst-dot big" style={{ background: inst.color }}>{inst.name.slice(0, 1).toLocaleUpperCase('tr')}</span>
              <div className="grow"><div className="home-title">{inst.name}</div><div className="muted small">{versions.length} sürüm · son güncelleme {when(inst.updated)}</div></div>
              <Btn kind="primary" onClick={() => openScreen({ kind: 'newSchedule', inst: inst.slug })}><Icon name="plus" size={14} /> Yeni Çizelge</Btn>
              <Btn onClick={() => importRef.current?.click()}><Icon name="open" size={14} /> İçe Aktar (.roz)</Btn>
              <details className="more"><summary className="btn">•••</summary>
                <div className="ctx static">
                  <button onClick={async () => { const n = await promptText('Kurumu Yeniden Adlandır', 'Kurum adı:', inst.name); if (n?.trim()) { await updateInstitution(inst.slug, { name: n.trim() }); refresh(); } }}>Yeniden Adlandır</button>
                  <div className="palette mini">{INST_COLORS.map((c) => <button key={c} className={`swatch${c === inst.color ? ' on' : ''}`} style={{ background: c }} onClick={async () => { await updateInstitution(inst.slug, { color: c }); refresh(); }} />)}</div>
                  <button className="danger-txt" onClick={async () => {
                    if (!(await ask({ title: 'Kurumu sil', body: `'${inst.name}' kurumu ve bütün sürümleri bu tarayıcıdan silinecek. Bu işlem geri alınamaz.`, ok: 'Sil', cancel: 'Vazgeç', tone: 'danger' }))) return;
                    await deleteInstitution(inst.slug); setSel(null); refresh();
                  }}>Kurumu Sil</button>
                </div>
              </details>
            </div>
            <div className="ver-list">
              {[...versions].reverse().map((v) => {
                const active = inst.active === v.id;
                return (
                  <div key={v.id} className={`ver${active ? ' active' : ''}`} onDoubleClick={() => void openVersion(inst, v)}>
                    <div className="ver-main">
                      <b>{versionLabel(v)}</b>{active && <span className="pill live">Yayında</span>}
                      <div className="muted small">{when(v.created)} · {v.summary.classes} sınıf · {v.summary.teachers} öğretmen · {v.summary.placed}/{v.summary.assigned} saat{v.source === 'import' ? ' · içe aktarıldı' : v.source === 'new' ? ' · yeni' : ''}</div>
                      {v.note && <div className="small">{v.note}</div>}
                    </div>
                    <div className="ver-acts">
                      <Btn kind="primary" onClick={() => void openVersion(inst, v)}>Aç</Btn>
                      <Btn onClick={async () => { const n = await promptText('Sürüm Adı', 'Bu sürüm için bir ad yazın (boş bırakırsanız numarası görünür):', v.name ?? ''); if (n !== null) { await patchVersion(inst.slug, v.id, { name: n.trim() || undefined }); refresh(); } }}>Ad</Btn>
                      <Btn onClick={async () => { const n = await promptText('Sürüm Notu', 'Not:', v.note ?? ''); if (n !== null) { await patchVersion(inst.slug, v.id, { note: n.trim() || undefined }); refresh(); } }}>Not</Btn>
                      <Btn onClick={async () => { const d = await loadVersionData(inst.slug, v.id); if (d) downloadJson(`${inst.name}_${versionLabel(v)}`.replace(/\s+/g, '_'), d); }}>İndir</Btn>
                      <Btn kind="danger" onClick={async () => {
                        if (!(await ask({ title: 'Sürümü sil', body: `${versionLabel(v)} silinsin mi? Bu işlem geri alınamaz.`, ok: 'Sil', cancel: 'Vazgeç', tone: 'danger' }))) return;
                        await deleteVersion(inst.slug, v.id); refresh();
                      }}>Sil</Btn>
                    </div>
                  </div>
                );
              })}
              {!versions.length && <div className="empty-state"><p>Bu kurumda henüz kayıtlı sürüm yok.</p><p className="muted small">"Yeni Çizelge" ile sihirbazı başlatın ya da bir .roz dosyasını içe aktarın.</p></div>}
            </div>
          </>
        ) : (
          <div className="empty-state">
            <h2>Chenkron — Web</h2>
            <p className="muted">Bir kurum oluşturun ya da bir .roz çizelge dosyası açın. Veriniz bu tarayıcıda kalır; planlama motoru da burada çalışır.</p>
            <div className="toolbar" style={{ justifyContent: 'center' }}>
              <Btn kind="primary" onClick={() => void newInst()}>Yeni Kurum</Btn>
              <Btn onClick={onOpenFile}>.roz dosyası aç</Btn>
            </div>
          </div>
        )}
      </main>
      <input ref={importRef} type="file" accept=".roz,.json" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) void importRoz(f); e.target.value = ''; }} />
    </div>
  );
}

export function HomeScreen() {
  const openFile = () => document.getElementById('roz-file')?.click();
  return (
    <Window title="Anasayfa" subtitle="Kurumlar ve kayıtlı çizelge sürümleri" onClose={closeScreen} width={1100}>
      <HomeBody onOpenFile={openFile} />
    </Window>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Yeni Kurum / Yeni Çizelge Sihirbazı (startup_wizard.StartupWizard)
// ════════════════════════════════════════════════════════════════════════════
const STEPS = ['1. Genel Bilgiler', '2. Gün ve Saatler', '3. Dersler', '4. Sınıflar', '5. Derslikler', '6. Öğretmenler', '7. Tamamla'];
const DAYS_ALL = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar'];
const split = (t: string) => t.split(/[\n,;]+/).map((x) => x.trim()).filter(Boolean);

export function NewScheduleScreen({ inst: instSlug }: { inst?: string }) {
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [year, setYear] = useState('2025-2026');
  const [yetkili, setYetkili] = useState('');
  const [periods, setPeriods] = useState(8);
  const [days, setDays] = useState(5);
  const [weekend, setWeekend] = useState('Cumartesi - Pazar');
  const [lists, setLists] = useState(['', '', '', '']);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    void (async () => { if (instSlug) { const i = (await listInstitutions()).find((x) => x.slug === instSlug); if (i) setName(i.name); } })();
  }, [instSlug]);

  const finish = async () => {
    if (!name.trim()) { setStep(0); await tell('Eksik bilgi', 'Lütfen okul / kurum adını girin.'); return; }
    setBusy(true);
    const [ders, sinif, derslik, ogr] = lists.map(split);
    const dayNames = DAYS_ALL.slice(0, days);
    const data: any = {
      okul_adi: name.trim(), ogretim_yili: year, gun_sayisi: days, ders_saati: periods, kurum: { isim: name.trim() },
      settings: {
        school_name: name.trim(), academic_year: year, periods, periods_per_day: periods, days_count: days, day_count: days, days: dayNames,
        weekend_option: weekend, yetkili_ad: yetkili.trim(), active_days_list: DAYS_ALL.map((n, i) => ({ day_index: i, name: n, active: i < days })),
      },
      dersler: [...new Set(ders.map(formatTrName))].map((ad) => ({ ad, kisa: autoShortCode(ad), renk: '#C4C4F0', ozel_alanlar: {} })),
      siniflar: [...new Set(sinif)].map((ad) => ({ ad, kisa: ad.replace(/ /g, '').toUpperCase(), renk: '', foto: true, sinif_ogretmeni: '', sinif_tipi: 'Hepsi', kapasite: '30', ders_bitimi: '15:30', ozel_alanlar: {} })),
      derslikler: [...new Set(derslik)].map((ad) => ({ ad, kisa: ad.toUpperCase(), renk: '#F39C12', kapasite: '', tur: 'Normal', ozel_alanlar: {} })),
      ogretmenler: [...new Set(ogr.map(formatTrName))].map((ad) => {
        const p = ad.split(/\s+/);
        return { ad, kisa: p.length >= 2 ? `${p[0][0].toUpperCase()}. ${p.slice(1).join(' ').toUpperCase()}` : `${p[0][0].toUpperCase()}. ${p[0].toUpperCase()}`, renk: '#27AE60', sinif_ogretmeni: '', brans: '', ozel_alanlar: {} };
      }),
      atamalar: [], grid_placements: [], planlama_iliskileri: [], kisitlamalar: {},
    };
    let target = instSlug ? (await listInstitutions()).find((x) => x.slug === instSlug) ?? null : null;
    if (!target) target = await createInstitution(name.trim(), INST_COLORS[(await listInstitutions()).length % INST_COLORS.length]);
    const v = await addVersion(target.slug, data, 'new', 'Sihirbazla oluşturuldu');
    load(data, `${target.name} — ${versionLabel(v)}`, { inst: { slug: target.slug, name: target.name, color: target.color }, versionId: v.id });
    setBusy(false);
    // Tanımlar boş kaldıysa tanımlama ekranı açılır (sihirbazın 3-6. adımları gibi).
    if (!data.dersler.length || !data.siniflar.length || !data.ogretmenler.length) openScreen({ kind: 'master', tab: !data.dersler.length ? 0 : !data.siniflar.length ? 1 : 3 });
  };

  const entityStep = (i: number, title: string, hint: string) => (
    <>
      <h2>{title}</h2>
      <p className="muted">Her satıra bir kayıt yazın (virgülle de ayırabilirsiniz). Ayrıntıları sonra Tanımlama ekranından düzenleyebilirsiniz.</p>
      <textarea rows={10} placeholder={hint} value={lists[i]} onChange={(e) => setLists((l) => l.map((x, j) => (j === i ? e.target.value : x)))} style={{ width: '100%' }} />
      <div className="muted small">{split(lists[i]).length} kayıt</div>
    </>
  );

  return (
    <Window title="Yeni Program Yapılandır" onClose={closeScreen} width={820}
      footer={<><Btn disabled={step === 0} onClick={() => setStep(step - 1)}>Geri</Btn><span className="sp" /><Btn onClick={closeScreen}>İptal</Btn>
        <Btn kind="primary" disabled={busy} onClick={() => (step === STEPS.length - 1 ? void finish() : setStep(step + 1))}>{step === STEPS.length - 1 ? 'Bitir ve Oluştur' : 'İleri'}</Btn></>}>
      <div className="wiz">
        <nav className="wiz-steps">{STEPS.map((s, i) => <button key={s} className={i === step ? 'on' : ''} onClick={() => setStep(i)}>{s}</button>)}</nav>
        <div className="wiz-body">
          {step === 0 && <>
            <h2>Adım 1: Okul Bilgileri</h2>
            <label className="field"><span className="field-label">Okul / Kurum Adı</span><input autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="Örn: Atatürk Anadolu Lisesi" /></label>
            <label className="field"><span className="field-label">Öğretim Yılı</span><input value={year} onChange={(e) => setYear(e.target.value)} /></label>
            <label className="field"><span className="field-label">Kurum Yetkilisi Ad/Unvan</span><input value={yetkili} onChange={(e) => setYetkili(e.target.value)} /></label>
          </>}
          {step === 1 && <>
            <h2>Adım 2: Gün ve Saat Ayarları</h2>
            <label className="field"><span className="field-label">Günlük Ders Saati</span><input type="number" min={1} max={16} value={periods} onChange={(e) => setPeriods(Math.max(1, Math.min(16, Number(e.target.value) || 8)))} style={{ width: 100 }} /></label>
            <label className="field"><span className="field-label">Gün Sayısı</span><input type="number" min={1} max={7} value={days} onChange={(e) => { const n = Math.max(1, Math.min(7, Number(e.target.value) || 5)); setDays(n); setWeekend(n >= 7 ? 'Hafta Sonu Tatili Yok' : n === 6 ? 'Yalnız Pazar' : 'Cumartesi - Pazar'); }} style={{ width: 100 }} /></label>
            <label className="field"><span className="field-label">Hafta Sonu</span>
              <select value={weekend} onChange={(e) => { setWeekend(e.target.value); setDays(e.target.value === 'Hafta Sonu Tatili Yok' ? 7 : e.target.value === 'Yalnız Pazar' ? 6 : 5); }}>
                {['Cumartesi - Pazar', 'Yalnız Pazar', 'Hafta Sonu Tatili Yok'].map((w) => <option key={w}>{w}</option>)}
              </select></label>
            <p className="muted small">Günler: {DAYS_ALL.slice(0, days).join(', ')}</p>
          </>}
          {step === 2 && entityStep(0, '3. Dersleri Girin', 'Matematik\nTürkçe\nFizik')}
          {step === 3 && entityStep(1, '4. Sınıfları Girin', '9A\n10B\n11C')}
          {step === 4 && entityStep(2, '5. Derslikleri Girin', 'Lab 1\nSpor Salonu')}
          {step === 5 && entityStep(3, '6. Öğretmenleri Girin', 'Ahmet Yılmaz\nAyşe Demir')}
          {step === 6 && <>
            <h2>Adım 7: Sihirbazı Tamamla</h2>
            <p>{name || '—'} · {days} gün × {periods} saat</p>
            <p className="muted">{split(lists[0]).length} ders, {split(lists[1]).length} sınıf, {split(lists[2]).length} derslik, {split(lists[3]).length} öğretmen tanımlanacak.</p>
            <p className="muted small">{getState().data ? 'Açık çizelge kapanır; bu kurum için yeni bir sürüm oluşturulur. Eski sürümler Anasayfa\'da durur.' : 'Her şey hazır. Başlamak için \'Bitir ve Oluştur\'a tıklayın.'}</p>
          </>}
        </div>
      </div>
    </Window>
  );
}
