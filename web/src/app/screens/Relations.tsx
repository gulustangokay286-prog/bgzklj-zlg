// dialogs/relations_dialog.py — Planlama İlişkileri (planlama_iliskileri).
// Kural adları, gruplama ve "tek ders" okuması motorun kendi fonksiyonlarıyla
// (engine/rules.ts) yapılır; ekranın gösterdiği, motorun uyguladığıdır.
import { useState } from 'react';
import {
  SELECTION_GROUP_KINDS, X_PAIR_NOT_SAME_DAY, X_SUBJECT_GROUP, X_SUBJECT_NOT_ADJACENT, X_SUBJECT_ONCE_DAY,
  familyLookup, matchRuleName, ruleGroups, sameSubject, selectionIsGroup, subjectCount,
} from '../../engine/rules.ts';
import { normKey } from '../../engine/norm.ts';
import { ask, closeScreen, mutate, tell, useApp } from '../store.ts';
import { Btn, Icon, Window } from '../ui.tsx';

const GROUPED_KINDS = new Set([X_PAIR_NOT_SAME_DAY, X_SUBJECT_ONCE_DAY, X_SUBJECT_NOT_ADJACENT, X_SUBJECT_GROUP]);
const RULES = [
  'Seçilen dersler aynı ders sayılsın',
  'Günde maksimum ders sayısı',
  'Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun',
  'Aynı ders aynı gün tekrar etmesin',
  'Aynı ders art arda gelmesin',
  'Aynı öğretmen aynı gün tekrar etmesin',
  'Dersler haftanın günlerine eşit dağıtılsın',
  'Seçilen dersler aynı gün peş peşe gelsin',
  'İki ders aynı güne gelmesin',
  'Öğretmenin dersleri öğleden önce toplansın',
  'Öğretmenin dersleri öğleden sonra toplansın',
  'Son ders saatine zor ders konulmasın',
  'X dersi belirli saatlerde kalmalı',
  'İki zor ders art arda gelmesin',
];
const IMP = ['Sıkı (Kesinlikle uygulanmalı)', 'Yüksek', 'Normal', 'Düşük (Mümkünse)'];
const GROUP_RULE = 'Seçilen dersler aynı ders sayılsın';
const PAIR_RULE = 'İki ders aynı güne gelmesin';
const kindOf = (rule: string) => matchRuleName(normKey(rule));
const isGroupRel = (item: any) => (item.kind || kindOf(item.kural || '')) === X_SUBJECT_GROUP;

export function RelationsScreen() {
  const data = useApp((s) => s.data);
  const rels: any[] = data.planlama_iliskileri ?? [];
  const [sel, setSel] = useState<number | null>(null);
  const [edit, setEdit] = useState<{ index: number | null } | null>(null);
  const nSubj = subjectCount(data);
  const active = rels.filter((r) => r.aktif ?? true).length;

  const setActive = (i: number, on: boolean) => mutate(on ? 'Kural açıldı' : 'Kural kapatıldı', (d) => { d.planlama_iliskileri[i].aktif = on; });
  const toggleAll = () => {
    const all = rels.every((r) => r.aktif ?? true);
    mutate(all ? 'Tüm kurallar kapatıldı' : 'Tüm kurallar açıldı', (d) => { for (const r of d.planlama_iliskileri ?? []) r.aktif = !all; });
  };
  const del = async () => {
    if (sel === null || !rels[sel]) return;
    if (!(await ask({ title: 'Kuralı Sil', body: 'Bu kuralı silmek istediğinize emin misiniz?', ok: 'Sil', cancel: 'Vazgeç', tone: 'danger' }))) return;
    mutate('Kural silindi', (d) => { d.planlama_iliskileri.splice(sel, 1); });
    setSel(null);
  };

  return (
    <Window title="Planlama İlişkileri — Ders Kısıtlamaları ve Kurallar" onClose={closeScreen} width={1100}
      footer={<>
        <Btn kind="primary" onClick={() => setEdit({ index: null })}><Icon name="plus" size={15} /> Kural Ekle</Btn>
        <Btn disabled={sel === null} onClick={() => sel !== null && setEdit({ index: sel })}><Icon name="edit" size={15} /> Düzenle</Btn>
        <Btn disabled={sel === null} onClick={() => void del()}><Icon name="trash" size={15} /> Sil</Btn>
        <Btn onClick={toggleAll} disabled={!rels.length}>Tümünü Aktifleştir / Kapat</Btn>
        <span className="muted">Toplam {rels.length} kural ({active} aktif)</span>
        <span className="sp" />
        <Btn kind="primary" onClick={closeScreen}>Kapat ve Kaydet</Btn>
      </>}>
      <div className="card head-card">
        <Icon name="list" size={26} />
        <div>
          <b>Planlama İlişkileri ve Gelişmiş Bağıntılar</b>
          <div className="muted small">Otomatik ve manuel planlama sırasında uygulanacak pedagojik kısıtlamaları ve kuralları buradan yönetebilirsiniz. Aktif kurallar optimizasyon algoritmasında öncelikli olarak uygulanır.</div>
        </div>
      </div>
      <div className="dtable-wrap" style={{ maxHeight: '58vh' }}>
        <table className="dtable">
          <thead><tr><th style={{ width: 56 }}>Aktif</th><th>Kural</th><th>Dersler</th><th>Sınıflar</th><th>Öğretmenler</th><th>Önem</th></tr></thead>
          <tbody>
            {rels.map((item, i) => {
              const on = item.aktif ?? true;
              let kural = String(item.kural ?? '');
              if (item.parametre) kural += ` (maks: ${item.parametre} saat)`;
              if (item.period_start && item.period_end) kural += ` (${item.period_start}.–${item.period_end}. saat)`;
              const grp = isGroupRel(item);
              const subj: string[] = item.dersler ?? [];
              let tek = false, grps: string[][] = subj.length ? [subj] : [];
              try { tek = selectionIsGroup(item, nSubj); grps = ruleGroups(item); } catch { /* ekran için */ }
              const unusable = (item.kural === PAIR_RULE || grp) && subj.length < 2;
              const subjText = unusable ? 'Ders seçilmedi — kural uygulanmaz'
                : grps.length > 1 ? grps.map((g) => g.join(' + ')).join('  |  ') + (tek ? '  (her grup tek ders)' : '')
                  : grp || tek ? subj.join(' + ') + (tek ? '  (tek ders)' : '')
                    : subj.length ? subj.join(', ') : 'Tüm dersler';
              const onem = String(item.onem ?? 'Sıkı');
              const short = grp ? 'Tanım' : onem.includes('(') ? onem.split('(')[0].trim() : onem;
              const cls: string[] = item.siniflar ?? [], tea: string[] = item.ogretmenler ?? [];
              return (
                <tr key={i} className={sel === i ? 'sel' : ''} onClick={() => setSel(i)} onDoubleClick={() => setEdit({ index: i })}>
                  <td className="center" onClick={(e) => e.stopPropagation()}><input type="checkbox" checked={on} onChange={(e) => setActive(i, e.target.checked)} /></td>
                  <td className={on ? '' : 'muted'}>{kural}</td>
                  <td className={unusable ? 'txt-bad' : subj.length ? '' : 'muted'} title={unusable ? 'Çift tıklayıp dersleri seçin.' : ''}>{subjText}</td>
                  <td className={cls.length ? '' : 'muted'}>{grp ? '—' : cls.length ? cls.join(', ') : 'Tüm sınıflar'}</td>
                  <td className={tea.length ? '' : 'muted'}>{grp ? '—' : tea.length ? tea.join(', ') : 'Tüm öğretmenler'}</td>
                  <td><span className={`imp imp-${short === 'Tanım' ? 'def' : short.includes('Sıkı') ? 'hard' : short.includes('Yüksek') ? 'high' : short.includes('Normal') ? 'norm' : 'low'}`}>{short}</span></td>
                </tr>
              );
            })}
            {!rels.length && <tr><td colSpan={6} className="muted center">Henüz kural yok. "Kural Ekle" ile başlayın.</td></tr>}
          </tbody>
        </table>
      </div>
      {edit && (
        <RelationEditor data={data} relation={edit.index !== null ? rels[edit.index] : null} onClose={() => setEdit(null)}
          onSave={(nd) => {
            mutate(edit.index === null ? 'Kural eklendi' : 'Kural güncellendi', (d) => {
              d.planlama_iliskileri ??= [];
              if (edit.index === null) d.planlama_iliskileri.push(nd); else d.planlama_iliskileri[edit.index] = nd;
            });
            setEdit(null);
          }} />
      )}
    </Window>
  );
}

function allSubjects(d: any): string[] {
  const s = new Set<string>();
  for (const x of d.dersler ?? []) if (x.ad) s.add(x.ad);
  for (const a of d.atamalar ?? []) if (a.subject) s.add(a.subject);
  return [...s].sort();
}

function RelationEditor({ data, relation, onSave, onClose }: { data: any; relation: any | null; onSave: (r: any) => void; onClose: () => void }) {
  const rd = relation ?? {};
  const [rule, setRule] = useState<string>(() => (RULES.includes(rd.kural) ? rd.kural : RULES[0]));
  const [subjects, setSubjects] = useState<string[]>(() => {
    const g = safeGroups(rd);
    return g.length > 1 ? [...new Set(g.flat())].sort() : [...(rd.dersler ?? [])];
  });
  const [groups, setGroups] = useState<string[][]>(() => { const g = safeGroups(rd); return g.length > 1 ? g.map((x) => [...x]) : []; });
  const [teachers, setTeachers] = useState<string[]>(() => [...(rd.ogretmenler ?? [])]);
  const [classes, setClasses] = useState<string[]>(() => [...(rd.siniflar ?? [])]);
  const [useSubj, setUseSubj] = useState(() => (rd.dersler ?? []).length > 0);
  const [useTeach, setUseTeach] = useState(() => (rd.ogretmenler ?? []).length > 0);
  const [useCls, setUseCls] = useState(() => (rd.siniflar ?? []).length > 0);
  const [param, setParam] = useState<number>(rd.parametre || 2);
  const [pStart, setPStart] = useState<number>(rd.period_start || 1);
  const [pEnd, setPEnd] = useState<number>(rd.period_end || 4);
  const [imp, setImp] = useState<string>(IMP.includes(rd.onem) ? rd.onem : IMP[0]);
  const [tek, setTek] = useState<boolean>(() => {
    if (rd.tek_ders !== undefined && rd.tek_ders !== null) return !!rd.tek_ders;
    if ((rd.dersler ?? []).length >= 2) { try { return selectionIsGroup(rd, subjectCount(data)); } catch { return true; } }
    return true;
  });
  const [picker, setPicker] = useState<'subj' | 'teach' | 'cls' | null>(null);

  const kind = kindOf(rule);
  const grouped = !!kind && GROUPED_KINDS.has(kind);
  const selGroupKind = !!kind && SELECTION_GROUP_KINDS.has(kind);
  const isGroup = rule === GROUP_RULE;
  const showMax = rule === 'Günde maksimum ders sayısı' || rule === 'Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun';
  const showPeriod = rule === 'X dersi belirli saatlerde kalmalı';
  const needsPick = rule === PAIR_RULE || rule === GROUP_RULE;
  const nSel = useSubj ? subjects.length : 0;

  const changeRule = (r: string) => {
    setRule(r);
    if (r === 'Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun') {
      setParam(2);
      if (!subjects.length) {
        const prac = (n: string) => { const u = String(n).replace(/i/g, 'İ').replace(/ı/g, 'I').toUpperCase(); return ['BEDEN', 'MÜZ', 'MUZ', 'GÖR', 'GOR', 'RES', 'SANAT', 'SPOR', 'UYGULAMA', 'ATÖLYE', 'ATOLYE'].some((k) => u.includes(k)); };
        const list: string[] = [];
        for (const d of data.dersler ?? []) if (prac(d.ad ?? '')) list.push(d.ad);
        for (const a of data.atamalar ?? []) if (prac(a.subject ?? '') && !list.includes(a.subject)) list.push(a.subject);
        if (list.length) { setSubjects(list); setUseSubj(true); }
      }
    } else if (r === 'Günde maksimum ders sayısı' && param > 4) setParam(2);
    if ((r === PAIR_RULE || r === GROUP_RULE) && !subjects.length) setPicker('subj');
  };

  // _auto_select_scope_for_subjects: ders seçilince öğretmen/sınıf süzgeci o derslere göre kurulur.
  const autoScope = (subs: string[]) => {
    if (isGroup || !subs.length) return;
    let fam = new Map<string, string>();
    try { fam = familyLookup(data.planlama_iliskileri ?? [], subjectCount(data)); } catch { /* yoksay */ }
    const t = new Set<string>(), c = new Set<string>();
    for (const a of data.atamalar ?? []) {
      const s = a.subject || a.ders || '';
      if (!subs.some((x) => sameSubject(s, x, fam))) continue;
      const tn = a.teacher || a.ogretmen || '';
      if (tn && tn !== '—' && tn !== 'Atanmadı') t.add(tn);
      const cn = a.class || a.sinif || '';
      if (cn) c.add(cn);
      for (const x of a.combined_classes ?? []) if (x) c.add(x);
    }
    setTeachers([...t].sort()); setClasses([...c].sort());
    setUseTeach(t.size > 0); setUseCls(c.size > 0);
  };

  const trySave = async () => {
    if (isGroup && nSel < 2) { await tell('Ders Grubu', 'Bu kural için en az iki ders seçmelisiniz.\n\nÖrnek: Mat1 + Mat2, Edebiyat + Türkçe, Biyoloji 9 + Biyoloji 11.'); setPicker('subj'); return; }
    if (rule === PAIR_RULE && nSel < 2) { await tell('Ders Seçimi', '“İki ders aynı güne gelmesin” için hangi derslerin aynı güne gelmeyeceğini seçmelisiniz (en az iki ders).\n\nDers seçilmeden bu kural kaydedilemez; motor onu uygulayamaz.'); setPicker('subj'); return; }
    const many = rule === PAIR_RULE || (selGroupKind && tek);
    if (many && groups.length && groups.some((g) => g.length < 2)) { await tell('Grup', 'Her grupta en az iki ders olmalı.'); setPicker('subj'); return; }
    if (many && !groups.length && nSel >= 3) {
      const regroup = await ask({
        title: 'Gruplama gerekli',
        body: `${nSel} ders seçtiniz ama grup oluşturmadınız.\n\nBu kuralda seçilen derslerin hepsi tek bir küme sayılır: ${subjects.slice(0, 6).join(', ')}${subjects.length > 6 ? '…' : ''} birlikte aynı ders kabul edilir.\n\nMat1 + Mat2 bir ders, Türkçe + Edebiyat ayrı bir ders olsun istiyorsanız ders seçme penceresinde grup oluşturmalısınız. Gruplamazsanız hepsi birden tek ders sayılır ve çizelge büyük ihtimalle oturmaz.`,
        ok: 'Grupları düzenle', cancel: 'Tek küme olarak kaydet', tone: 'warn',
      });
      if (regroup) { setPicker('subj'); return; }
    }
    let n = nSel;
    if (groups.length) n = Math.max(...groups.map((g) => g.length));
    if (many && n >= 2) {
      const total = Math.max(1, allSubjects(data).length);
      if (n >= total || n > 6 || n * 2 >= total) {
        const body = rule === PAIR_RULE
          ? `${n} ders seçtiniz (kurumda ${total} ders var). Bu kural seçilen derslerden aynı sınıfta günde EN FAZLA BİRİNE izin verir: ${n} dersin ${n - 1}'i her gün dışarıda kalır.\n\nBu kadar çok dersle çizelge büyük ihtimalle oturmaz; kural yalnızca birbirine denk gelmemesi gereken birkaç ders için düşünülmüştür.`
          : `${n} ders tek ders sayılacak (kurumda ${total} ders var): hepsi birlikte aynı sınıfta günde en fazla bir kez gelebilir.\n\nBu kadar çok dersle çizelge büyük ihtimalle oturmaz. Her dersin kendi içinde tekrar etmemesini istiyorsanız kutuyu kaldırın ya da hiç ders seçmeyin (tüm dersler).`;
        if (!(await ask({ title: 'Çok fazla ders seçildi', body: body + '\n\nYine de kaydedilsin mi?', ok: 'Kaydet', cancel: 'Vazgeç', tone: 'warn' }))) return;
      }
    }
    onSave({
      kind,
      aktif: rd.aktif ?? true,
      kural: rule,
      dersler: useSubj ? subjects : [],
      ogretmenler: isGroup ? [] : useTeach ? teachers : [],
      siniflar: isGroup ? [] : useCls ? classes : [],
      parametre: showMax ? param : null,
      period_start: showPeriod ? pStart : null,
      period_end: showPeriod ? pEnd : null,
      onem: isGroup ? IMP[0] : imp,
      tek_ders: selGroupKind && useSubj && subjects.length >= 2 ? tek : null,
      gruplar: useSubj && groups.length > 1 ? groups.map((g) => [...g]) : null,
    });
  };

  const subjSummary = groups.length > 1 ? `Seçili (${groups.length} grup): ${groups.map((g) => g.join(' + ')).join(' | ')}`
    : subjects.length ? `Seçili (${subjects.length} ders): ${subjects.slice(0, 3).join(', ')}${subjects.length > 3 ? '...' : ''}` : '';
  const pickRow = (label: string, on: boolean, setOn: (v: boolean) => void, sum: string, allLabel: string, kindKey: 'subj' | 'teach' | 'cls') => (
    <div className="rel-row">
      <span className="rel-lbl">{label}</span>
      <select value={on ? '1' : '0'} onChange={(e) => { const v = e.target.value === '1'; setOn(v); if (v && !sum) setPicker(kindKey); }}>
        <option value="0">{allLabel}</option>
        <option value="1">{sum || `Seçili ${label.toLocaleLowerCase('tr').replace(':', '')}...`}</option>
      </select>
      <Btn onClick={() => setPicker(kindKey)}>Seç</Btn>
    </div>
  );

  return (
    <Window title="Planlama Kuralı Düzenle" onClose={onClose} width={680}
      footer={<><span className="sp" /><Btn onClick={onClose}>İptal</Btn><Btn kind="primary" onClick={() => void trySave()}>Kaydet</Btn></>}>
      <div className="card">
        <div className="card-title">Kural Seçimi</div>
        <select value={rule} onChange={(e) => changeRule(e.target.value)} style={{ width: '100%' }}>
          {RULES.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>
      <div className="card">
        <div className="card-title">Uygulanacak Filtreler</div>
        {pickRow('Dersler:', useSubj, setUseSubj, subjSummary, needsPick ? 'Ders seçin…' : 'Tüm dersler', 'subj')}
        {selGroupKind && nSel >= 2 && (
          <label className="check" style={{ paddingLeft: 84 }}><input type="checkbox" checked={tek} onChange={(e) => setTek(e.target.checked)} />
            Seçilen dersler tek ders sayılsın (örn. Mat1 + Mat2 + Geometri birlikte günde en fazla bir kez)</label>
        )}
        {!isGroup && pickRow('Öğretmenler:', useTeach, setUseTeach, teachers.length ? `Seçili (${teachers.length} öğretmen): ${teachers.slice(0, 3).join(', ')}${teachers.length > 3 ? '...' : ''}` : '', 'Tüm öğretmenler', 'teach')}
        {!isGroup && pickRow('Sınıflar:', useCls, setUseCls, classes.length ? `Seçili (${classes.length} sınıf): ${classes.slice(0, 3).join(', ')}${classes.length > 3 ? '...' : ''}` : '', 'Tüm sınıflar', 'cls')}
        {isGroup && <div className="hint-box">Bu satır bir kısıt değil, bir tanımdır: seçtiğiniz dersler motor için TEK ders olur (örn. Mat1 + Mat2, Edebiyat + Türkçe, Biyoloji 9 + Biyoloji 11). “Aynı ders aynı gün tekrar etmesin”, “Aynı ders art arda gelmesin”, “Günde maksimum ders sayısı” gibi bütün kurallar bu dersleri birlikte sayar. En az iki ders seçin.</div>}
      </div>
      {(showMax || showPeriod) && (
        <div className="card">
          <div className="card-title">Parametre Ayarları</div>
          {showMax && <label className="inline-field">Maksimum günlük ders saati: <input type="number" min={1} max={15} value={param} onChange={(e) => setParam(Math.max(1, Math.min(15, Number(e.target.value) || 1)))} style={{ width: 80 }} /></label>}
          {showPeriod && <label className="inline-field">Saat aralığı (örn: 1-4): <input type="number" min={1} max={12} value={pStart} onChange={(e) => setPStart(Number(e.target.value) || 1)} style={{ width: 70 }} /> – <input type="number" min={1} max={12} value={pEnd} onChange={(e) => setPEnd(Number(e.target.value) || 1)} style={{ width: 70 }} /></label>}
        </div>
      )}
      {!isGroup && (
        <div className="card">
          <div className="card-title">Önem Derecesi</div>
          <select value={imp} onChange={(e) => setImp(e.target.value)} style={{ width: '100%' }}>{IMP.map((x) => <option key={x}>{x}</option>)}</select>
        </div>
      )}
      {picker === 'subj' && (
        <PickList title={'Dersleri Seç' + (grouped ? ' — birden çok küme için GRUP oluşturun' : '')} items={allSubjects(data)} selected={subjects}
          groups={grouped ? groups : null} onClose={() => setPicker(null)}
          onOk={(selected, gs) => {
            setSubjects(selected); setGroups(gs.length > 1 ? gs : []); setUseSubj(selected.length > 0); autoScope(selected); setPicker(null);
          }} />
      )}
      {picker === 'teach' && (
        <PickList title="Öğretmenleri Seç" items={[...new Set([...(data.ogretmenler ?? []).map((t: any) => t.ad).filter(Boolean), ...(data.atamalar ?? []).map((a: any) => a.teacher).filter((t: any) => t && t !== '—' && t !== 'Atanmadı')])].sort() as string[]}
          selected={teachers} groups={null} onClose={() => setPicker(null)} onOk={(s) => { setTeachers(s); setUseTeach(s.length > 0); setPicker(null); }} />
      )}
      {picker === 'cls' && (
        <PickList title="Sınıfları Seç" items={[...new Set([...(data.siniflar ?? []).map((c: any) => c.ad).filter(Boolean), ...(data.atamalar ?? []).map((a: any) => a.class).filter(Boolean)])].sort() as string[]}
          selected={classes} groups={null} onClose={() => setPicker(null)} onOk={(s) => { setClasses(s); setUseCls(s.length > 0); setPicker(null); }} />
      )}
    </Window>
  );
}

function safeGroups(rd: any): string[][] {
  try { return ruleGroups(rd); } catch { return (rd.dersler ?? []).length ? [rd.dersler] : []; }
}

/** MultiSelectDialog — groups verilirse grup kipi (Mat1 + Mat2 | Türkçe + Edebiyat). */
function PickList({ title, items, selected, groups: initGroups, onOk, onClose }: {
  title: string; items: string[]; selected: string[]; groups: string[][] | null; onOk: (sel: string[], groups: string[][]) => void; onClose: () => void;
}) {
  const mode = initGroups !== null;
  const [groups, setGroups] = useState<string[][]>(() => (initGroups ?? []).filter((g) => g.length).map((g) => [...g]));
  const grouped = new Set(groups.flat());
  const [sel, setSel] = useState<Set<string>>(() => new Set(selected.filter((x) => !mode || !(initGroups ?? []).flat().includes(x))));
  const [q, setQ] = useState('');
  const [gSel, setGSel] = useState<number | null>(null);
  const groupOf = (n: string) => groups.findIndex((g) => g.includes(n)) + 1;
  const vis = items.filter((i) => !q.trim() || i.toLowerCase().includes(q.trim().toLowerCase()));
  const loose = [...sel].filter((n) => !grouped.has(n)).sort();
  const make = async () => {
    const names = vis.filter((n) => sel.has(n) && !groupOf(n));
    if (names.length < 2) { await tell('Grup', 'Grup yapmak için en az iki ders işaretleyin.\n\nÖrnek: önce Mat1 ile Mat2\'yi işaretleyip “Seçilenleri Grup Yap”, sonra Türkçe ile Edebiyat\'ı işaretleyip yine “Seçilenleri Grup Yap”.'); return; }
    setGroups((g) => [...g, [...names].sort()]);
    setSel((s) => { const n = new Set(s); for (const x of names) n.delete(x); return n; });
  };
  const finish = () => {
    if (!mode) { onOk([...sel].sort(), []); return; }
    const out = groups.map((g) => [...g]);
    if (loose.length >= 2 || !out.length) { if (loose.length) out.push(loose); }
    onOk([...new Set(out.flat())].sort(), out);
  };
  return (
    <Window title={title} onClose={onClose} width={560}
      footer={<><span className="sp" /><Btn onClick={onClose}>İptal</Btn><Btn kind="primary" onClick={finish}>Uygula</Btn></>}>
      <input placeholder="Listede filtrele..." value={q} onChange={(e) => setQ(e.target.value)} style={{ width: '100%', marginBottom: 6 }} />
      <div className="toolbar">
        <Btn onClick={() => setSel((s) => { const n = new Set(s); for (const x of vis) if (!mode || !groupOf(x)) n.add(x); return n; })}>Tümünü Seç</Btn>
        <Btn onClick={() => setSel((s) => { const n = new Set(s); for (const x of vis) n.delete(x); return n; })}>Temizle</Btn>
      </div>
      <div className="pick-list" style={{ maxHeight: mode ? '30vh' : '50vh' }}>
        {vis.map((n) => {
          const k = mode ? groupOf(n) : 0;
          return (
            <label key={n} className={`multi-item${k ? ' grouped' : ''}`}>
              <input type="checkbox" disabled={!!k} checked={!!k || sel.has(n)} onChange={(e) => setSel((s) => { const x = new Set(s); if (e.target.checked) x.add(n); else x.delete(n); return x; })} />
              <span>{n}{k ? `   — Grup ${k}` : ''}</span>
            </label>
          );
        })}
      </div>
      {mode && (
        <div style={{ marginTop: 10 }}>
          <div className="muted small">Gruplar — her grup ayrı ayrı uygulanır (Mat1 + Mat2 | Türkçe + Edebiyat)</div>
          <div className="pick-list" style={{ maxHeight: '18vh', marginTop: 4 }}>
            {groups.map((g, i) => <div key={i} className={`multi-item${gSel === i ? ' on' : ''}`} onClick={() => setGSel(i)}>Grup {i + 1}:  {g.join(' + ')}</div>)}
            {!groups.length && <div className="muted small">Grup yapmazsanız seçilen bütün dersler tek grup sayılır.</div>}
          </div>
          <div className="toolbar" style={{ marginTop: 6 }}>
            <Btn onClick={() => void make()}>Seçilenleri Grup Yap</Btn>
            <Btn disabled={gSel === null} onClick={() => { if (gSel !== null) { setGroups((g) => g.filter((_, i) => i !== gSel)); setGSel(null); } }}>Grubu Kaldır</Btn>
          </div>
          {groups.length > 0 && loose.length > 0 && <div className="muted small">Gruba alınmamış {loose.length} seçili ders {loose.length >= 2 ? 'kendi başına bir grup olur.' : 'tek başına anlamsızdır, yok sayılır.'}</div>}
        </div>
      )}
    </Window>
  );
}
