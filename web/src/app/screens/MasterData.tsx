// dialogs/master_data_dialog.py (MasterDataDialog) ve edit_forms.py'deki
// Ders / Sınıf / Derslik / Öğretmen formları.
import { useMemo, useState } from 'react';
import { getMatrix, hours as hoursOf, typeStr } from '../../engine/data.ts';
import {
  autoShortCode, deleteAll, deleteEntity, formatTrName, linkClassTeacher, linkTeacherClass, matchesClass, renameEntity,
} from '../datastore.ts';
import type { Kind } from '../datastore.ts';
import { classColor, dims } from '../model.ts';
import { ask, closeScreen, mutate, openScreen, redo, setState, tell, undo, useApp } from '../store.ts';
import { Btn, ColorField, CustomFields, Field, Icon, MiniGrid, MultiSelect, Window } from '../ui.tsx';
import { openTimeoffFor } from './Timeoff.tsx';

const KINDS: Kind[] = ['dersler', 'siniflar', 'derslikler', 'ogretmenler'];
const TITLES = ['Dersler', 'Sınıflar', 'Derslikler', 'Öğretmenler'];
const TABLE_TITLES = ['Tanımlı Dersler', 'Tanımlı Sınıflar', 'Tanımlı Derslikler', 'Tanımlı Öğretmenler ve Dersleri'];
const ICONS = ['book', 'users', 'door', 'teacher'];
const HEADERS = [
  ['Ders Adı', 'Kısa Kodu', 'Toplam', 'Zaman Tablosu', 'Dağılım', 'Max. Günlük'],
  ['Sınıf Adı', 'Kısa Kodu', 'Toplam', 'Zaman Tablosu', 'Ders Bitim Saati', 'Sınıf Öğretmeni', 'Öğrenci'],
  ['Derslik Adı', 'Kısa Kodu', 'Toplam', 'Zaman Tablosu', 'Kapasite', 'Bina'],
  ['Öğretmen Adı', 'Kısa Kodu', 'Toplam', 'Zaman Tablosu & Çizelge', 'Sınıf Öğretmeni', 'Branşı', 'Atanan Dersler ve Sınıflar'],
];
const WORDS = ['ders', 'sınıf', 'derslik', 'öğretmen'];
const PLURAL = ['derslerin', 'sınıfların', 'dersliklerin', 'öğretmenlerin'];
const collator = new Intl.Collator('tr', { numeric: true, sensitivity: 'base' });

const durNum = (a: any) => { const n = parseInt(String(a?.duration ?? a?.hours ?? 1), 10); return Number.isFinite(n) ? n : 1; };

interface Row { ent: any; index: number; cells: string[]; matrix: number[][] }

function buildRows(d: any, tab: number): Row[] {
  const { P } = dims(d);
  const atamalar: any[] = d.atamalar ?? [];
  const list: any[] = d[KINDS[tab]] ?? [];
  const bySubject = new Map<string, number>(), byClass = new Map<string, number>(), byTeacher = new Map<string, number>();
  const tAssign = new Map<string, any[]>();
  for (const a of atamalar) {
    if (!a || typeof a !== 'object') continue;
    const dur = durNum(a);
    const t = formatTrName(a.teacher ?? ''), s = formatTrName(a.subject ?? ''), c = String(a.class ?? '').trim();
    if (t) { byTeacher.set(t, (byTeacher.get(t) ?? 0) + dur); (tAssign.get(t) ?? tAssign.set(t, []).get(t)!).push(a); }
    if (s) bySubject.set(s, (bySubject.get(s) ?? 0) + dur);
    if (c) byClass.set(c, (byClass.get(c) ?? 0) + dur);
  }
  const classTeacher = new Map<string, string>();
  for (const s of d.siniflar ?? []) { const so = String(s?.sinif_ogretmeni ?? '').trim(); if (so) classTeacher.set(formatTrName(so), s.ad ?? ''); }
  return list.map((ent, index) => {
    const ad = String(ent?.ad ?? '');
    const matrix = getMatrix(ent, ad.trim(), d);
    let cells: string[];
    if (tab === 0) cells = [ad, ent.kisa ?? '', String(bySubject.get(formatTrName(ad)) ?? 0), '', 'İdeal', String(ent.max_gunluk ?? P)];
    else if (tab === 1) cells = [ad, ent.kisa ?? '', String(byClass.get(ad.trim()) ?? 0), '', String(ent.ders_bitimi ?? '15:30'), ent.sinif_ogretmeni ?? '', String(ent.kapasite ?? '30')];
    else if (tab === 2) cells = [ad, ent.kisa ?? '', '0', '', String(ent.kapasite ?? ''), 'Merkez'];
    else {
      const f = formatTrName(ad);
      const summ = (tAssign.get(f) ?? []).map((a) => (a.subject && a.class ? `${a.subject} (${a.class})` : a.subject)).filter(Boolean);
      cells = [ad, ent.kisa ?? '', String(byTeacher.get(f) ?? byTeacher.get(ad) ?? 0), '', classTeacher.get(f) ?? '', ent.brans ?? '', summ.length ? summ.join(', ') : 'Atama Yok'];
    }
    return { ent, index, cells, matrix };
  });
}

function countLabel(d: any, tab: number): string {
  const n = (d[KINDS[tab]] ?? []).filter((x: any) => x && typeof x === 'object' && String(x.ad ?? '').trim()).length;
  const field = ['subject', 'class', null, 'teacher'][tab];
  if (!field) return `${n} ${WORDS[tab]}`;
  let h = 0;
  for (const a of d.atamalar ?? []) if (a && typeof a === 'object' && String(a[field] ?? '').trim()) h += parseInt(String(a.duration || a.hours || 1), 10) || 1;
  return `${n} ${WORDS[tab]}  ·  ${h} saat`;
}

export function MasterDataScreen({ tab: startTab }: { tab: number }) {
  const data = useApp((s) => s.data);
  const canUndo = useApp((s) => s.undo.length > 0);
  const canRedo = useApp((s) => s.redo.length > 0);
  const [tab, setTab] = useState(startTab);
  const [sel, setSel] = useState<number | null>(null);
  const [q, setQ] = useState('');
  const [max, setMax] = useState(false);
  const [form, setForm] = useState<{ tab: number; index: number | null } | null>(null);
  const [dragFrom, setDragFrom] = useState<number | null>(null);
  const { D, P } = dims(data);
  const rows = useMemo(() => buildRows(data, tab), [data, tab]);
  const shown = q.trim() ? rows.filter((r) => r.cells.some((c) => c.toLocaleLowerCase('tr').includes(q.trim().toLocaleLowerCase('tr')))) : rows;
  const kind = KINDS[tab];
  const selRow = sel !== null ? rows[sel] ?? null : null;
  const selName = selRow ? String(selRow.ent.ad ?? '').trim() : null;

  const selectTab = (i: number) => { setTab(i); setSel(null); setQ(''); };
  const move = (from: number, to: number) => {
    const n = (data[kind] ?? []).length;
    if (from < 0 || from >= n || to < 0 || to >= n || from === to) return;
    mutate(`${TITLES[tab]}: sıra`, (d) => { const l = d[kind]; const [x] = l.splice(from, 1); l.splice(to, 0, x); });
    setSel(to);
  };
  const sortAZ = () => mutate(`${TITLES[tab]}: A-Z`, (d) => { d[kind].sort((a: any, b: any) => collator.compare(String(a?.ad ?? ''), String(b?.ad ?? ''))); });

  const actDelete = async () => {
    if (!selRow) return;
    const name = String(selRow.ent.ad ?? '').trim();
    if (!(await ask({ title: 'Silme Onayı', body: `'${name}' kaydını ve bağlı tüm atama/program verilerini silmek istediğinize emin misiniz?`, ok: 'Sil', cancel: 'Vazgeç', tone: 'danger' }))) return;
    mutate(`${name} silindi`, (d) => deleteEntity(d, kind, name));
    setSel(null);
  };
  const actDeleteAll = async () => {
    if (!(await ask({ title: 'Tümünü Sil Onayı', body: `Tanımlı tüm ${PLURAL[tab]} listesini silmek istediğinize emin misiniz?`, ok: 'Tümünü Sil', cancel: 'Vazgeç', tone: 'danger' }))) return;
    mutate(`Tüm ${TITLES[tab].toLocaleLowerCase('tr')} silindi`, (d) => deleteAll(d, kind));
    setSel(null);
  };
  const actResetClasses = async () => {
    if (!(await ask({ title: 'Tüm Sınıf Atamalarını Sıfırla', body: 'TÜM sınıflara ait ders ve öğretmen görevlendirmeleri tamamen silinecektir.\n\nEmin misiniz?', ok: 'Sıfırla', cancel: 'Vazgeç', tone: 'danger' }))) return;
    mutate('Tüm sınıf atamaları sıfırlandı', (d) => { d.atamalar = []; d.grid_placements = []; d.yerlesim = {}; });
    await tell('Başarılı', 'Tüm sınıf atamaları başarıyla sıfırlandı.');
  };
  const actAssign = async () => {
    if (tab === 1) {
      let c = selName;
      if (!c) {
        const classes = (data.siniflar ?? []).map((x: any) => x.ad).filter(Boolean);
        if (!classes.length) return;
        await tell('Sınıfın Dersleri', 'Derslerini düzenleyeceğiniz sınıfı listeden seçin.');
        return;
      }
      openScreen({ kind: 'assignClass', className: c });
      return;
    }
    openScreen({ kind: 'assignTeacher', teacher: tab === 3 ? selName ?? undefined : undefined });
  };
  const actTimeoff = () => void openTimeoffFor(kind, selName, selRow?.index);
  const actConstraints = () => openScreen({ kind: 'constraints', target: tab === 3 ? 'ogretmen' : 'sinif', name: (tab === 3 || tab === 1) ? selName ?? undefined : undefined });

  return (
    <Window title={TITLES[tab]} onClose={closeScreen} width={1080} className={`md-win${max ? ' max' : ''}`}
      footer={<>
        <Btn onClick={() => openScreen({ kind: 'faq' })}>Yardım</Btn>
        <Btn disabled={!canUndo} onClick={undo}>Geri Al</Btn>
        <Btn disabled={!canRedo} onClick={redo}>Yinele</Btn>
        <Btn kind="primary" onClick={closeScreen}>Kaydet</Btn>
        <Btn kind="danger" onClick={() => void actResetClasses()}>Tüm Sınıf Atamalarını Sıfırla</Btn>
        <Btn onClick={() => openScreen({ kind: 'info' })}>Bilgi Al</Btn>
        <span className="sp" />
        <Btn onClick={() => setMax(!max)}><Icon name="zoom" size={15} /> {max ? 'Normal Boyut (Küçült)' : 'Tam Ekran (Büyüt)'}</Btn>
        <Btn onClick={closeScreen}>Kapat</Btn>
      </>}>
      <div className="md">
        <nav className="md-tabs" aria-label="Tanımlar">
          {TITLES.map((t, i) => (
            <button key={t} className={i === tab ? 'on' : ''} onClick={() => selectTab(i)} title={t}>
              <Icon name={ICONS[i]} size={22} /><span>{t}</span>
            </button>
          ))}
        </nav>
        <div className="md-main">
          <div className="md-top">
            <b>{TABLE_TITLES[tab]}</b>
            <span className="sp" />
            <span className="muted" title="Tanımlı kayıt sayısı ve atanmış toplam haftalık ders saati.">ⓘ {countLabel(data, tab)}</span>
            <Btn onClick={sortAZ}>A-Z Sırala</Btn>
            <input className="search" placeholder="Gerçek Zamanlı Ara..." value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <div className="dtable-wrap">
            <table className="dtable">
              <thead><tr>{HEADERS[tab].map((h) => <th key={h}>{h}</th>)}</tr></thead>
              <tbody>
                {shown.map((r) => (
                  <tr key={r.index} className={sel === r.index ? 'sel' : ''} onClick={() => setSel(r.index)}
                    draggable={!q.trim()} onDragStart={() => setDragFrom(r.index)} onDragOver={(e) => e.preventDefault()}
                    onDrop={() => { if (dragFrom !== null) move(dragFrom, r.index); setDragFrom(null); }}>
                    {r.cells.map((c, ci) => (
                      <td key={ci} className={ci === 3 ? 'mini-cell' : ci === r.cells.length - 1 && tab === 3 ? 'wrap' : ''}
                        onDoubleClick={() => { setSel(r.index); if (ci === 3) void openTimeoffFor(kind, String(r.ent.ad ?? '').trim(), r.index); else setForm({ tab, index: r.index }); }}>
                        {ci === 3 ? <MiniGrid matrix={r.matrix} D={D} P={P} /> : c}
                      </td>
                    ))}
                  </tr>
                ))}
                {!shown.length && <tr><td colSpan={HEADERS[tab].length} className="muted center">{q ? 'Sonuç yok.' : 'Kayıt yok. "Yeni" ile ekleyin.'}</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
        <div className="md-actions">
          <Btn kind="primary" onClick={() => setForm({ tab, index: null })}><Icon name="plus" size={15} /> Yeni</Btn>
          <Btn disabled={!selRow} onClick={() => selRow && setForm({ tab, index: selRow.index })}><Icon name="edit" size={15} /> Güncelle</Btn>
          <Btn disabled={!selRow} onClick={() => void actDelete()}><Icon name="minus" size={15} /> Sil</Btn>
          <Btn disabled={!selRow || sel === 0} onClick={() => sel !== null && move(sel, sel - 1)}><Icon name="up" size={15} /> Yukarı Taşı</Btn>
          <Btn disabled={!selRow || sel === rows.length - 1} onClick={() => sel !== null && move(sel, sel + 1)}><Icon name="down" size={15} /> Aşağı Taşı</Btn>
          <div className="gap" />
          <Btn onClick={() => void actAssign()}><Icon name="file" size={15} /> Ders Atama</Btn>
          <Btn onClick={actTimeoff}><Icon name="clock" size={15} /> Zaman Tablosu</Btn>
          <Btn onClick={actConstraints}><Icon name="hash" size={15} /> Kısıtlamalar</Btn>
          <Btn onClick={() => openScreen({ kind: 'groups' })}><Icon name="branch" size={15} /> Gruplar</Btn>
          <span className="sp" />
          <Btn onClick={() => void actDeleteAll()}><Icon name="minus" size={15} /> Tümünü Sil</Btn>
          <Btn kind="primary" onClick={() => setState({ plannerOpen: true })}><Icon name="plus" size={15} /> Otomatik Oluştur</Btn>
        </div>
      </div>
      {form && <EntityForm tab={form.tab} index={form.index} onClose={() => setForm(null)} onSaved={(i) => setSel(i)} />}
    </Window>
  );
}

// ── formlar ────────────────────────────────────────────────────────────────
function teacherShort(text: string): string {
  const parts = text.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0][0].toUpperCase()}. ${parts.slice(1).join(' ').toUpperCase()}`;
  if (parts.length === 1) return `${parts[0][0].toUpperCase()}. ${parts[0].toUpperCase()}`;
  return text.trim().toUpperCase();
}

function EntityForm({ tab, index, onClose, onSaved }: { tab: number; index: number | null; onClose: () => void; onSaved: (i: number) => void }) {
  const data = useApp((s) => s.data);
  const kind = KINDS[tab];
  const existing = index !== null ? data[kind]?.[index] ?? {} : {};
  const isNew = index === null;
  const defaultColor = ['#C4C4F0', '', '#F39C12', '#27AE60'][tab] || classColor(existing.ad ?? '', data);
  const [f, setF] = useState<any>(() => ({
    ad: existing.ad ?? '', kisa: existing.kisa ?? '', renk: existing.renk || (tab === 1 ? existing.color : '') || defaultColor,
    ozel_alanlar: existing.ozel_alanlar ?? {}, sinif_ogretmeni: existing.sinif_ogretmeni ?? '', foto: existing.foto ?? true,
    brans: existing.brans ?? '', es_zamanli: !!existing.es_zamanli, kapasite: existing.kapasite ?? (tab === 1 ? '30' : ''), tur: existing.tur || 'Normal',
  }));
  const [custom, setCustom] = useState(false);
  const set = (patch: any) => setF((x: any) => ({ ...x, ...patch }));

  // Sınıf öğretmeni seçimi: kayıtta yoksa karşı taraftan bul (edit_forms).
  const initialSo = useMemo(() => {
    const ad = String(existing.ad ?? '').trim();
    if (tab === 1) {
      let so = String(existing.sinif_ogretmeni ?? '').trim();
      if (!so && ad) for (const t of data.ogretmenler ?? []) if (String(t.sinif_ogretmeni ?? '').trim().toUpperCase() === ad.toUpperCase()) { so = String(t.ad ?? '').trim(); break; }
      return so;
    }
    if (tab === 3) {
      let so = String(existing.sinif_ogretmeni ?? '').trim();
      if (!so && ad) for (const s of data.siniflar ?? []) if (formatTrName(String(s.sinif_ogretmeni ?? '').trim()) === formatTrName(ad)) { so = String(s.ad ?? '').trim(); break; }
      return so;
    }
    return '';
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const [so, setSo] = useState(initialSo);

  const onName = (v: string) => {
    const patch: any = { ad: v };
    if (v) patch.kisa = tab === 0 ? autoShortCode(v) : tab === 1 ? v.trim().replace(/ /g, '').toUpperCase() : tab === 2 ? v.trim().toUpperCase() : teacherShort(v);
    set(patch);
  };

  const getData = () => {
    if (tab === 0) return { ad: formatTrName(f.ad.trim()), kisa: f.kisa.trim(), renk: f.renk, ozel_alanlar: f.ozel_alanlar };
    if (tab === 1) return {
      ad: f.ad, kisa: f.kisa, renk: f.renk, foto: f.foto, sinif_ogretmeni: so, sinif_tipi: existing.sinif_tipi ?? 'Hepsi',
      kapasite: String(existing.kapasite ?? '30'), ders_bitimi: String(existing.ders_bitimi ?? '15:30'), ozel_alanlar: f.ozel_alanlar,
    };
    if (tab === 2) return { ad: f.ad.trim(), kisa: f.kisa.trim(), renk: f.renk, kapasite: String(f.kapasite).trim(), tur: String(f.tur).trim(), ozel_alanlar: f.ozel_alanlar };
    return { ad: formatTrName(f.ad.trim()), kisa: f.kisa.trim(), renk: f.renk, sinif_ogretmeni: so.trim(), brans: f.brans.trim(), es_zamanli: f.es_zamanli, ozel_alanlar: f.ozel_alanlar };
  };

  const save = async () => {
    const nd = getData();
    const newName = String(nd.ad ?? '').trim();
    if (!newName) { await tell('Eksik bilgi', `${TITLES[tab].slice(0, -3) || 'Kayıt'} adı boş olamaz.`); return; }
    const clash = (data[kind] ?? []).some((x: any, i: number) => i !== index && String(x?.ad ?? '').trim().toLocaleUpperCase('tr') === newName.toLocaleUpperCase('tr'));
    if (clash && !(await ask({ title: 'Aynı ad', body: `'${newName}' adında bir kayıt zaten var. Yine de kaydedilsin mi?`, ok: 'Kaydet', cancel: 'Vazgeç', tone: 'warn' }))) return;
    let savedIndex = index ?? (data[kind] ?? []).length;
    mutate(isNew ? `${newName} eklendi` : `${newName} güncellendi`, (d) => {
      d[kind] ??= [];
      if (isNew) {
        d[kind].push(nd);
        savedIndex = d[kind].length - 1;
      } else {
        const old = d[kind][index!];
        const oldName = String(old?.ad ?? '');
        if (oldName && newName && oldName !== newName) renameEntity(d, kind, oldName, newName);
        // Formun görmediği alanlar (zaman tablosu vb.) korunur.
        d[kind][index!] = { ...old, ...nd };
      }
      const self = d[kind][savedIndex];
      if (tab === 0 && nd.renk) applySubjectColor(d, newName, nd.renk);
      if (tab === 1) linkClassTeacher(d, newName, nd.sinif_ogretmeni ?? '', self);
      if (tab === 3) linkTeacherClass(d, newName, nd.sinif_ogretmeni ?? '', self);
    });
    onSaved(savedIndex);
    onClose();
    // Yeni öğretmen: masaüstündeki gibi ardından ders atama penceresi açılır.
    if (isNew && tab === 3) openScreen({ kind: 'assignTeacher', teacher: newName });
  };

  const liveName = (f.ad || existing.ad || '').trim();
  const titles = ['Ders', 'Sınıf', 'Derslik', 'Öğretmen Düzenle'];
  return (
    <Window title={titles[tab]} subtitle={tab === 1 ? 'Sınıf temel bilgileri, rehber öğretmen ve haftalık planlama detayları.' : undefined} onClose={onClose} width={600}
      footer={<><span className="sp" /><Btn onClick={onClose}>İptal</Btn><Btn kind="primary" onClick={() => void save()}>{tab === 0 ? 'Kaydet' : 'Tamam'}</Btn></>}>
      <div className="form">
        <div className="card">
          <Field label={['Dersin Adı', 'Sınıf Adı', 'Derslik Adı', 'Öğretmen Adı'][tab]}>
            <input autoFocus value={f.ad} placeholder={['', 'Örn: 9A', '', 'Öğretmen Adı Soyadı'][tab]} onChange={(e) => onName(e.target.value)} />
          </Field>
          <Field label="Kısa Kodu"><input value={f.kisa} onChange={(e) => set({ kisa: e.target.value })} /></Field>
          <div className="row-end"><Btn type="button" onClick={() => setCustom(true)}>Özel Alanlar...</Btn></div>
          {tab === 1 && (
            <>
              <Field label="Sınıf Öğretmeni">
                <select value={so} onChange={(e) => setSo(e.target.value)}>
                  <option value="" />
                  {[...(data.ogretmenler ?? []).map((t: any) => t.ad).filter(Boolean)].sort(collator.compare).map((t: string) => <option key={t} value={t}>{t}</option>)}
                </select>
              </Field>
              <label className="check"><input type="checkbox" checked={!!f.foto} onChange={(e) => set({ foto: e.target.checked })} /> Fotoğrafları yazdırın</label>
            </>
          )}
          {tab === 3 && (
            <>
              <Field label="Sınıf Öğretmeni (Rehberlik)">
                <select value={so} onChange={(e) => setSo(e.target.value)}>
                  <option value="" />
                  {[...(data.siniflar ?? []).map((c: any) => c.ad).filter(Boolean)].sort(collator.compare).map((c: string) => <option key={c} value={c}>{c}</option>)}
                </select>
              </Field>
              <BranchField value={f.brans} onChange={(v) => set({ brans: v })} data={data} />
              <label className="check"><input type="checkbox" checked={f.es_zamanli} onChange={(e) => set({ es_zamanli: e.target.checked })} /> Aynı saatte çoklu/paralel ders girebilir (Çoklu Ders İzni)</label>
            </>
          )}
          {tab === 2 && (
            <div className="grid2">
              <Field label="Derslik Kapasitesi"><input value={f.kapasite} placeholder="örn. 30" onChange={(e) => set({ kapasite: e.target.value })} /></Field>
              <Field label="Türü">
                <input list="room-types" value={f.tur} onChange={(e) => set({ tur: e.target.value })} />
                <datalist id="room-types">{['Normal', 'Laboratuvar', 'Spor Salonu', 'Atölye', 'Bilgisayar', 'Müzik', 'Resim', 'Konferans'].map((t) => <option key={t} value={t} />)}</datalist>
              </Field>
            </div>
          )}
        </div>
        <div className="card">
          <Field label={tab === 0 ? 'Renk Kodu / Küçük Resim Seç' : 'Renk Kodu'}><ColorField value={f.renk} onChange={(c) => set({ renk: c })} /></Field>
        </div>
        {tab !== 2 && (
          <div className="card">
            <div className="card-title">{['Atandığı Sınıflar ve Öğretmenler (Gerçek Zamanlı):', 'Atandığı Dersler ve Öğretmenler (Gerçek Zamanlı):', '', 'Atandığı Sınıflar ve Dersler (Gerçek Zamanlı):'][tab]}</div>
            <AssignmentList tab={tab} name={liveName} data={data} />
            <div className="btnrow">
              {tab === 0 && <>
                <Btn onClick={() => openScreen({ kind: 'master', tab: 2 })}>Derslikler</Btn>
                <Btn kind="primary" disabled={!liveName} onClick={() => openScreen({ kind: 'assignSubject', subject: formatTrName(liveName) })}>Dersin Öğretmenlerini ve Sınıflarını Ata</Btn>
              </>}
              {tab === 1 && <>
                <Btn kind="primary" disabled={!liveName} onClick={() => openScreen({ kind: 'assignClass', className: liveName })}>Ders ve Öğretmen Ata</Btn>
                <Btn disabled={!liveName} onClick={() => openScreen({ kind: 'print', preset: { entity: 'class', name: liveName } })}>Çizelge Göster / Yazdır</Btn>
              </>}
              {tab === 3 && <>
                <Btn kind="primary" disabled={isNew || !liveName} title={isNew ? 'Önce Tamam ile kaydedin' : ''} onClick={() => openScreen({ kind: 'assignTeacher', teacher: formatTrName(liveName) })}>Ders Ata</Btn>
                <Btn disabled={!liveName} onClick={() => openScreen({ kind: 'print', preset: { entity: 'teacher', name: formatTrName(liveName) } })}>Çizelge / Yazdır</Btn>
                <Btn disabled={isNew || !liveName} onClick={() => openScreen({ kind: 'constraints', target: 'ogretmen', name: String(existing.ad ?? liveName) })}>Zaman / Kısıtlama</Btn>
                <Btn onClick={() => setState({ plannerOpen: true })}>Otomatik Oluştur</Btn>
              </>}
            </div>
          </div>
        )}
      </div>
      {custom && (
        <Window title={`Özel Alanlar — ${liveName || TITLES[tab]}`} onClose={() => setCustom(false)} width={480}
          footer={<><span className="sp" /><Btn kind="primary" onClick={() => setCustom(false)}>Tamam</Btn></>}>
          <CustomFields value={f.ozel_alanlar} onChange={(v) => set({ ozel_alanlar: v })} />
        </Window>
      )}
    </Window>
  );
}

function BranchField({ value, onChange, data }: { value: string; onChange: (v: string) => void; data: any }) {
  const [open, setOpen] = useState(false);
  const current = value.split(',').map((b) => b.trim()).filter(Boolean);
  const all = [...new Set([...(data.dersler ?? []).map((d: any) => String(d.ad ?? '').trim()).filter(Boolean), ...current])].sort(collator.compare) as string[];
  const [pick, setPick] = useState<string[]>(current);
  return (
    <Field label="Öğretmen Branş(lar)ı">
      <div className="inline">
        <input readOnly value={value} placeholder="Branş atanmadı..." />
        <Btn type="button" onClick={() => { setPick(current); setOpen(true); }}>Branş(lar) Ata...</Btn>
      </div>
      {open && (
        <Window title="Branş Seçimi" onClose={() => setOpen(false)} width={420}
          footer={<><span className="sp" /><Btn onClick={() => setOpen(false)}>İptal</Btn><Btn kind="primary" onClick={() => { onChange(pick.join(', ')); setOpen(false); }}>Tamam</Btn></>}>
          <MultiSelect options={all} value={pick} onChange={setPick} height={320} />
        </Window>
      )}
    </Field>
  );
}

function AssignmentList({ tab, name, data }: { tab: number; name: string; data: any }) {
  if (!name) return <div className="alist muted">{tab === 0 ? 'Ders adı girildiğinde atamalar burada listelenir.' : 'Ad girildiğinde atamalar burada listelenir.'}</div>;
  const items: string[] = [];
  for (const a of data.atamalar ?? []) {
    if (!a || typeof a !== 'object') continue;
    const dur = hoursOf(a), tip = typeStr(a);
    if (tab === 0 && formatTrName(a.ders || a.subject || '') === formatTrName(name)) {
      items.push(`${a.ogretmen || a.teacher || 'Atanmadı'}  →  ${a.sinif || a.class || ''} (${dur} Saat, Tip: ${tip || '-'})`);
    } else if (tab === 1) {
      const c = String(a.class || a.sinif || '').trim();
      const combs = (Array.isArray(a.combined_classes) ? a.combined_classes : []).filter((x: any) => typeof x === 'string').map((x: string) => formatTrName(x).toLowerCase());
      const my = formatTrName(name).toLowerCase();
      if (formatTrName(c).toLowerCase() === my || combs.includes(my) || matchesClass(c, name)) {
        const comb = Array.isArray(a.combined_classes) && a.combined_classes.length > 1 ? ` [Ortak: ${a.combined_classes.join(', ')}]` : '';
        items.push(`${a.subject || a.ders || ''}  →  ${a.teacher || a.ogretmen || 'Öğretmen Atanmadı'}  (${dur} Saat: ${tip || dur})${comb}`);
      }
    } else if (tab === 3 && formatTrName(a.ogretmen || a.teacher || '') === formatTrName(name)) {
      items.push(`${a.ders || a.subject || ''}  →  ${a.sinif || a.class || ''}  (${dur} Saat: ${tip || dur})`);
    }
  }
  if (!items.length) {
    return <div className="alist muted">{['Henüz hiçbir sınıfa / öğretmene atanmadı.', 'Henüz bu sınıfa atanmış ders veya öğretmen bulunmuyor.', '', 'Henüz atanmış ders veya sınıf bulunmuyor.'][tab]}</div>;
  }
  return <ul className="alist">{items.map((t, i) => <li key={i}>{t}</li>)}</ul>;
}

// color_picker_dialog.update_subject_color_globally
function subjectMatch(a: unknown, b: unknown): boolean {
  if (!a || !b) return false;
  const x = String(a).trim(), y = String(b).trim();
  if (x.toUpperCase() === y.toUpperCase()) return true;
  return formatTrName(x) === formatTrName(y);
}
export function applySubjectColor(d: any, subject: string, color: string) {
  const hex = String(color).toUpperCase().trim();
  if (!subject || !hex) return;
  let found = false;
  for (const x of d.dersler ?? []) if (subjectMatch(x.ad, subject) || subjectMatch(x.kisa, subject)) { x.renk = hex; x.color = hex; found = true; }
  if (!found) (d.dersler ??= []).push({ ad: subject.trim(), kisa: subject.trim().slice(0, 3).toUpperCase(), renk: hex, color: hex });
  for (const a of d.atamalar ?? []) if (subjectMatch(a.subject, subject) || subjectMatch(a.ders, subject)) { a.color = hex; a.renk = hex; }
  for (const p of d.grid_placements ?? []) if (subjectMatch(p.subject_name || p.subject, subject)) p.color = hex;
  if (d.yerlesim && typeof d.yerlesim === 'object') for (const v of Object.values(d.yerlesim) as any[]) if (v && typeof v === 'object' && subjectMatch(v.subject_name || v.subject, subject)) v.color = hex;
  for (const c of d.manual_unplaced_cards ?? []) if (subjectMatch(c.subject_name, subject)) c.color = hex;
  for (const c of d.loose_unplaced_cards ?? []) if (subjectMatch(c.subject_name, subject)) c.color = hex;
}
