// edit_forms.py atama pencereleri:
//   LessonAssignmentDialog            → AssignTeacherScreen  (öğretmene ders ve sınıf)
//   ClassComprehensiveAssignmentDialog→ AssignClassScreen    (sınıfın dersleri ve öğretmenleri)
//   SubjectTeacherAssignmentDialog    → AssignSubjectScreen  (dersin öğretmenleri ve saatleri)
// ve alt pencereleri (SubjectClassMultiSelect, CombinedClasses, MultiClassAssign).
import { useMemo, useState } from 'react';
import { hours as hoursOf, typeStr } from '../../engine/data.ts';
import {
  canonicalHours, formatTrName, matchesClass, matchesTeacherLoose, normalizeTr, pruneOrphanPlacements, sanitizeAtamalar, typeDuration,
} from '../datastore.ts';
import { dims, subjectColor } from '../model.ts';
import { ask, closeScreen, mutate, openScreen, tell, useApp } from '../store.ts';
import { Btn, Icon, Window } from '../ui.tsx';

const DIST = ['1', '2', '3', '4', '5', '6', '1+1', '2+1', '2+2', '3+1', '3+2', '4+2', '3+3', '2+2+1', '2+2+2', '3+2+1'];
const DIST_INLINE = ['', '1', '2', '3', '4', '5', '6', '7', '8', '1+1', '2+1', '2+2', '3+1', '3+2', '2+2+1', '2+2+2', '2+2+3', '2+2+2+1'];
const collator = new Intl.Collator('tr', { numeric: true, sensitivity: 'base' });
const splitClasses = (s: string) => s.replace(/&/g, '+').replace(/,/g, '+').split('+').map((p) => p.trim()).filter(Boolean);
let uid = 0;

/** Yazılabilir açılır liste (QComboBox setEditable). */
function Combo({ value, onChange, options, placeholder, onCommit, disabled, width }: {
  value: string; onChange: (v: string) => void; options: string[]; placeholder?: string; onCommit?: (v: string) => void; disabled?: boolean; width?: number;
}) {
  const [id] = useState(() => `dl${++uid}`);
  return (
    <>
      <input className="combo" list={id} value={value} placeholder={placeholder} disabled={disabled} style={width ? { width } : undefined}
        onChange={(e) => {
          onChange(e.target.value);
          // Listeden seçim hemen işlenir; elle yazım odak çıkınca/Enter'da (QComboBox activated / editingFinished).
          const it = (e.nativeEvent as InputEvent).inputType;
          if (onCommit && (!it || it === 'insertReplacementText') && options.includes(e.target.value)) onCommit(e.target.value);
        }}
        onBlur={(e) => onCommit?.(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }} />
      <datalist id={id}>{options.map((o) => <option key={o} value={o} />)}</datalist>
    </>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Öğretmene Ders ve Sınıf Atama Paneli (LessonAssignmentDialog)
// ════════════════════════════════════════════════════════════════════════════
interface LRow { id: number; subject: string; tip: string; classes: string[]; configs: Record<string, { type: string; duration: number }>; isCombined: boolean; combined: string[] }
const emptyRow = (): LRow => ({ id: ++uid, subject: '', tip: '2', classes: [], configs: {}, isCombined: false, combined: [] });

function rowsForTeacher(d: any, teacher: string): LRow[] {
  const mine = (d.atamalar ?? []).filter((a: any) => formatTrName(a.ogretmen || a.teacher || '') === formatTrName(teacher));
  const normal = new Map<string, LRow>();
  const combined: LRow[] = [];
  for (const a of mine) {
    const s = String(a.ders || a.subject || '').trim();
    if (!s) continue;
    const c = String(a.sinif || a.class || '').trim();
    const dur = hoursOf(a) || 2;
    const typ = typeStr(a) || String(dur);
    const isComb = !!(a.is_combined || c.includes('+') || c.includes('&'));
    if (isComb) {
      const cc = Array.isArray(a.combined_classes) && a.combined_classes.length ? [...a.combined_classes] : splitClasses(c);
      combined.push({ id: ++uid, subject: s, tip: typ, classes: [c], configs: {}, isCombined: true, combined: cc });
    } else {
      const r = normal.get(s) ?? { id: ++uid, subject: s, tip: typ, classes: [], configs: {}, isCombined: false, combined: [] };
      if (c && !r.classes.includes(c)) r.classes.push(c);
      r.configs[c] = { type: typ, duration: dur };
      normal.set(s, r);
    }
  }
  const rows = [...normal.values(), ...combined];
  if (!rows.length || rows[rows.length - 1].subject.trim()) rows.push(emptyRow());
  return rows;
}

function rowBadge(r: LRow): string {
  const def = r.tip.trim() || '2';
  if (r.isCombined) {
    const cc = r.combined.length ? r.combined : r.classes;
    return `BİRLEŞİK / ORTAK DERS: ${cc.length ? cc.join(' + ') : '-'} (${def} Saat)`;
  }
  if (!r.classes.length) return 'Atanan Sınıflar: Henüz Seçilmedi';
  return 'Atanan Sınıflar: ' + r.classes.map((c) => {
    const t = r.configs[c]?.type ?? def;
    const dur = t.includes('+') ? typeDuration(t, 0) : /^\d+$/.test(t) ? Number(t) : (r.configs[c]?.duration ?? 2);
    const clean = /[,+&]/.test(c) ? c.replace(/,/g, '+').replace(/ /g, '') : c;
    return `${clean} (${dur}s: ${t})`;
  }).join(', ');
}

export function AssignTeacherScreen({ teacher: initial }: { teacher?: string }) {
  const data = useApp((s) => s.data);
  const teachers = useMemo(() => (data.ogretmenler ?? []).map((t: any) => String(t.ad ?? '')).filter(Boolean).sort(collator.compare) as string[], [data]);
  const subjects = useMemo(() => [...new Set((data.dersler ?? []).map((d: any) => String(d.ad ?? '').trim()).filter(Boolean))].sort() as string[], [data]);
  const classes = useMemo(() => (data.siniflar ?? []).map((c: any) => String(c.ad ?? '')).filter(Boolean).sort() as string[], [data]);
  const [teacher, setTeacher] = useState(() => (initial && teachers.includes(initial) ? initial : initial && teachers.find((t) => formatTrName(t) === formatTrName(initial)) || teachers[0] || ''));
  const [rows, setRows] = useState<LRow[]>(() => rowsForTeacher(data, teacher));
  const [pick, setPick] = useState<{ kind: 'classes' | 'combined'; id: number } | null>(null);

  const changeTeacher = (t: string) => { setTeacher(t); setRows(rowsForTeacher(data, t)); };
  const upd = (id: number, patch: Partial<LRow> | ((r: LRow) => LRow)) => setRows((rs) => {
    const out = rs.map((r) => (r.id === id ? (typeof patch === 'function' ? patch(r) : { ...r, ...patch }) : r));
    const last = out[out.length - 1];
    // Tanınan bir ders seçilince sona yeni boş satır (edit_forms._on_subject_changed).
    if (last && last.subject.trim() && subjects.includes(last.subject.trim())) out.push(emptyRow());
    return out;
  });
  const setTip = (r: LRow, tip: string) => upd(r.id, (x) => {
    const configs: LRow['configs'] = {};
    for (const [c, v] of Object.entries(x.configs)) {
      const t = tip.trim();
      configs[c] = { type: t, duration: t.includes('+') ? typeDuration(t, 0) : /^\d+$/.test(t) ? Number(t) : v.duration };
    }
    return { ...x, tip, configs };
  });
  const remove = (r: LRow) => setRows((rs) => (rs.length <= 1 ? [emptyRow()] : rs.filter((x) => x.id !== r.id)));

  const valid = rows.filter((r) => r.subject.trim());
  const summary: string[] = [];
  for (const r of valid) {
    if (r.isCombined) {
      const s = `BİRLEŞİK: ${(r.combined.length ? r.combined : r.classes).join(' + ')}`;
      if (!summary.includes(s)) summary.push(s);
    } else for (const c of r.classes) {
      const clean = /[,+&]/.test(c) ? c.replace(/,/g, '+').replace(/ /g, '') : c;
      if (clean && !summary.includes(clean)) summary.push(clean);
    }
  }
  const allCls = new Set<string>();
  let total = 0;
  for (const r of valid) {
    const def = r.tip.trim() || '2';
    if (r.isCombined) {
      for (const c of r.combined.length ? r.combined : r.classes) allCls.add(c);
      total += def.includes('+') ? typeDuration(def, 2) : /^\d+$/.test(def) ? Number(def) : 2;
    } else for (const c of r.classes) {
      allCls.add(c);
      const t = r.configs[c]?.type ?? def;
      total += t.includes('+') ? typeDuration(t, 2) : /^\d+$/.test(t) ? Number(t) : (r.configs[c]?.duration ?? 2);
    }
  }

  const save = async () => {
    const tName = formatTrName(teacher.trim());
    if (!tName) { await tell('Öğretmen Seçilmedi', 'Lütfen bir öğretmen seçiniz.'); return; }
    const out: any[] = [];
    for (const r of valid) {
      const subj = r.subject.trim();
      const def = r.tip.trim() || '2';
      const color = subjectColor(subj, data);
      if (r.isCombined) {
        const cc = r.combined.length ? r.combined : r.classes;
        if (cc.length < 2) { await tell('Eksik Sınıf', `'${subj}' birleşik dersi için en az 2 sınıf seçilmelidir!`); return; }
        const cs = cc.join(' + ');
        const tv = r.configs[cs]?.type ?? def;
        const dur = tv.includes('+') ? typeDuration(tv, 2) : /^\d+$/.test(tv) ? Number(tv) : 2;
        out.push({ ogretmen: tName, teacher: tName, ders: subj, subject: subj, sinif: cs, class: cs, ders_sayisi: dur, duration: dur, dagilim: tv, type: tv, renk: color, color, is_combined: true, combined_classes: [...cc] });
      } else {
        if (!r.classes.length) { await tell('Eksik Sınıf Seçimi', `Lütfen '${subj}' dersi için en az bir sınıf seçiniz!`); return; }
        for (const c of r.classes) {
          const tv = r.configs[c]?.type ?? def;
          const dur = tv.includes('+') ? typeDuration(tv, 2) : /^\d+$/.test(tv) ? Number(tv) : 2;
          out.push({ ogretmen: tName, teacher: tName, ders: subj, subject: subj, sinif: c, class: c, ders_sayisi: dur, duration: dur, dagilim: tv, type: tv, renk: color, color, is_combined: false, combined_classes: [] });
        }
      }
    }
    if (!out.length && !rows.some((r) => r.subject.trim())) {
      await tell('Ders Seçilmedi', 'Kaydedilecek geçerli bir ders veya sınıf seçimi bulunamadı.\nLütfen atanacak dersi seçtiğinizden emin olunuz.');
      return;
    }
    mutate(`${tName}: ders atamaları`, (d) => {
      d.atamalar = (d.atamalar ?? []).filter((a: any) => formatTrName(a.ogretmen || a.teacher || '') !== tName);
      d.atamalar.push(...out);
      pruneOrphanPlacements(d, (p) => formatTrName(p.teacher_name || p.teacher || '') === tName);
    });
    closeScreen();
  };

  const pr = pick ? rows.find((r) => r.id === pick.id) : null;
  return (
    <Window title="Öğretmene Ders ve Sınıf Atama Paneli" onClose={closeScreen} width={900}
      footer={<><Btn onClick={closeScreen}>İptal</Btn><span className="sp" /><Btn kind="primary" onClick={() => void save()}>Tamam ve Kaydet</Btn></>}>
      <div className="card">
        <div className="card-title">Atanacak Öğretmen</div>
        <select value={teacher} onChange={(e) => changeTeacher(e.target.value)} style={{ minWidth: 320 }}>
          {teachers.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      <div className="card">
        <div className="card-title">Atanacak Dersler <span className="muted">— Bireysel veya Birleşik Sınıf Eşleme</span></div>
        <div className="lrows">
          {rows.map((r) => (
            <div key={r.id} className="lrow">
              <div className="lrow-top">
                <Combo value={r.subject} options={subjects} placeholder="Ders Ara veya Seç..." onChange={(v) => upd(r.id, { subject: v })} />
                <Combo value={r.tip} options={DIST} width={90} onChange={(v) => setTip(r, v)} />
                <Btn onClick={() => setPick({ kind: 'classes', id: r.id })}>Sınıf(lar) Ata...</Btn>
                <Btn onClick={() => setPick({ kind: 'combined', id: r.id })}>Birleşik Sınıf...</Btn>
                <button className="icon-btn round" onClick={() => remove(r)} aria-label="Satırı sil">✕</button>
              </div>
              <div className={`badge-line${r.isCombined ? ' comb' : ''}`}>{rowBadge(r)}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="card">
        <div className="card-title">Tüm Atanan Sınıflar (Genel Özet)</div>
        <input readOnly value={summary.join(', ')} placeholder="Derslere atanan sınıflar burada otomatik listelenir (Örn: 9A, 10B, 11A + 10B)" style={{ width: '100%' }} />
      </div>
      <div className="ozet"><b>Öğretmen:</b> {teacher || '-'} | <b>Toplam Ders Sayısı:</b> {valid.length} | <b>Atanan Sınıf Sayısı:</b> {allCls.size} | <b>Toplam Haftalık Saat:</b> {total} Saat</div>
      {pick?.kind === 'classes' && pr && (
        <ClassPicker subject={pr.subject.trim() || 'Ders'} allClasses={classes} selected={pr.isCombined ? [] : pr.classes} defaultDist={pr.tip.trim() || '2'} configs={pr.configs}
          onClose={() => setPick(null)}
          onOk={(sel, cfg) => { upd(pr.id, { classes: sel, configs: cfg, isCombined: false, combined: [] }); setPick(null); }} />
      )}
      {pick?.kind === 'combined' && pr && (
        <CombinedPicker data={data} selected={pr.combined.length ? pr.combined : pr.classes} subject={pr.subject.trim()} type={pr.tip.trim() || '2'} teacher={teacher}
          onClose={() => setPick(null)}
          onOk={(res) => {
            if (res.classes.length) upd(pr.id, { isCombined: true, combined: res.classes, classes: [res.classes.join(' + ')], subject: res.subject || pr.subject, tip: res.type });
            else upd(pr.id, { isCombined: false, combined: [] });
            setPick(null);
          }} />
      )}
    </Window>
  );
}

/** SubjectClassMultiSelectDialog — ders için sınıflar ve sınıf başına saat. */
function ClassPicker({ subject, allClasses, selected, defaultDist, configs, onOk, onClose }: {
  subject: string; allClasses: string[]; selected: string[]; defaultDist: string; configs: Record<string, { type: string; duration: number }>;
  onOk: (sel: string[], cfg: Record<string, { type: string; duration: number }>) => void; onClose: () => void;
}) {
  const [q, setQ] = useState('');
  const [state, setStateL] = useState(() => Object.fromEntries(allClasses.map((c) => [c, { on: selected.includes(c), type: configs[c]?.type ?? defaultDist }])));
  const visible = allClasses.filter((c) => !q.trim() || c.toLowerCase().includes(q.trim().toLowerCase()));
  const toggleAll = () => {
    const all = visible.every((c) => state[c].on);
    setStateL((s) => ({ ...s, ...Object.fromEntries(visible.map((c) => [c, { ...s[c], on: !all }])) }));
  };
  const ok = () => {
    const sel: string[] = [], cfg: Record<string, { type: string; duration: number }> = {};
    for (const c of allClasses) {
      if (!state[c].on) continue;
      const t = state[c].type.trim() || '2';
      sel.push(c);
      cfg[c] = { type: t, duration: t.includes('+') ? typeDuration(t, 1) : /^\d+$/.test(t) ? Number(t) : 1 };
    }
    onOk(sel, cfg);
  };
  return (
    <Window title={`Sınıf(lar) Ata — ${subject}`} onClose={onClose} width={560}
      footer={<><Btn onClick={toggleAll}>Tümünü Seç / Kaldır</Btn><span className="sp" /><Btn onClick={onClose}>İptal</Btn><Btn kind="primary" onClick={ok}>Seçimi Onayla</Btn></>}>
      <div className="card">
        <b>{subject}</b> Dersi İçin Sınıfları ve Saat Formatını Seçin
        <div className="muted small">Her sınıf için bağımsız saat formatı (Örn: 11A = 3 saat 2+1, 9A = 4 saat 2+2) belirleyebilirsiniz.</div>
      </div>
      <input placeholder="Ders veya Sınıf Ara..." value={q} onChange={(e) => setQ(e.target.value)} style={{ width: '100%', marginBottom: 8 }} />
      <div className="pick-list">
        {visible.map((c) => (
          <div key={c} className="pick-row">
            <label className="check"><input type="checkbox" checked={state[c].on} onChange={(e) => setStateL((s) => ({ ...s, [c]: { ...s[c], on: e.target.checked } }))} /> {c}</label>
            <span className="sp" />
            <span className="muted small">Saat / Dağılım:</span>
            <Combo value={state[c].type} options={DIST} width={90} disabled={!state[c].on} onChange={(v) => setStateL((s) => ({ ...s, [c]: { ...s[c], type: v } }))} />
          </div>
        ))}
      </div>
    </Window>
  );
}

const GROUPS = ['Bütün Sınıf', 'Grup 1', 'Grup 2', 'Erkekler', 'Kızlar', 'Seçmeli Ders'];

/** CombinedClassesDialog — birleşik / ortak ders (en az 2 sınıf). */
export function CombinedPicker({ data, selected, subject, type, teacher, onOk, onClose }: {
  data: any; selected: string[]; subject: string; type: string; teacher: string;
  onOk: (r: { classes: string[]; subject: string; type: string; teacher: string }) => void; onClose: () => void;
}) {
  const subjects = [...new Set((data.dersler ?? []).map((d: any) => String(d.ad ?? '').trim()).filter(Boolean))].sort() as string[];
  const teachers = (data.ogretmenler ?? []).map((t: any) => String(t.ad ?? '')).filter(Boolean).sort() as string[];
  const classes = (data.siniflar ?? []).map((c: any) => String(c.ad ?? '')).filter(Boolean).sort() as string[];
  const [subj, setSubj] = useState(subject);
  const [tip, setTip] = useState(type || '2');
  const [tea, setTea] = useState(teacher);
  const [rows, setRows] = useState<{ c: string; g: string }[]>(() => {
    const raw: string[] = [];
    for (const item of selected) for (const p of splitClasses(String(item))) raw.push(p);
    const out = Array.from({ length: 8 }, () => ({ c: '', g: GROUPS[0] }));
    raw.slice(0, 8).forEach((item, i) => {
      const m = /^(.*?)\s*\((.*?)\)$/.exec(item.trim());
      const cn = m ? m[1].trim() : item.trim(), gn = m ? m[2].trim() : GROUPS[0];
      out[i] = { c: classes.find((x) => x === cn) ?? classes.find((x) => x.toUpperCase() === cn.toUpperCase()) ?? '', g: GROUPS.find((x) => x === gn) ?? GROUPS.find((x) => x.toUpperCase().includes(gn.toUpperCase())) ?? GROUPS[0] };
    });
    return out;
  });
  const sel = rows.filter((r) => r.c.trim()).map((r) => (r.g === 'Bütün Sınıf' ? r.c.trim() : `${r.c.trim()} (${r.g})`));
  const accept = async () => {
    if (!subj.trim()) { await tell('Ders Seçimi Gerekli', 'Lütfen birleşik ders için atanacak Dersi seçiniz veya yazınız!'); return; }
    if (sel.length === 1) { await tell('Yetersiz Sınıf Seçimi', "Birleşik sınıf oluşturabilmek için en az 2 sınıf seçiniz veya seçimi temizlemek için 'Birleşik Sınıfı Kaldır' butonuna basınız."); return; }
    onOk({ classes: sel, subject: subj.trim(), type: tip.trim() || '2', teacher: tea.trim() });
  };
  return (
    <Window title="Birleşik / Ortak Ders Oluştur" onClose={onClose} width={640}
      footer={<><Btn kind="danger" onClick={() => onOk({ classes: [], subject: subj.trim(), type: tip.trim() || '2', teacher: tea.trim() })}>Birleşik Sınıfı Kaldır</Btn><span className="sp" /><Btn onClick={onClose}>İptal</Btn><Btn kind="primary" onClick={() => void accept()}>Birleşik Dersi Onayla</Btn></>}>
      <div className="card">
        <b>Birleşik / Ortak Ders Tanımlama</b> — En az 2 sınıf gereklidir
        <div className="muted small">Farklı sınıflar veya gruplar aynı saatte, aynı öğretmenle ortak ders işleyecek şekilde eşleştirilir.</div>
      </div>
      <div className="card grid2">
        <label className="field"><span className="field-label">Ders Seçimi</span><Combo value={subj} options={subjects} onChange={setSubj} /></label>
        <label className="field"><span className="field-label">Haftalık Saat / Dağılım</span><Combo value={tip} options={DIST.slice(0, 15)} onChange={setTip} /></label>
        <label className="field" style={{ gridColumn: '1 / -1' }}><span className="field-label">Öğretmen</span><Combo value={tea} options={teachers} onChange={setTea} /></label>
      </div>
      <div className="card">
        <div className="grid2 head"><b>Birleştirilecek Sınıf</b><b>Grup / Alt Kısım</b></div>
        {rows.map((r, i) => (
          <div key={i} className="grid2" style={{ marginTop: 6 }}>
            <select value={r.c} onChange={(e) => setRows((rs) => rs.map((x, j) => (j === i ? { ...x, c: e.target.value } : x)))}>
              <option value="" />{classes.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <select value={r.g} onChange={(e) => setRows((rs) => rs.map((x, j) => (j === i ? { ...x, g: e.target.value } : x)))}>
              {GROUPS.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
        ))}
      </div>
    </Window>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Sınıfın Dersleri ve Öğretmenleri (ClassComprehensiveAssignmentDialog)
// ════════════════════════════════════════════════════════════════════════════
const touchesClass = (a: any, cls: string) => {
  const c = String(a.class ?? '');
  if (matchesClass(c, cls)) return true;
  if (a.is_combined && Array.isArray(a.combined_classes) && a.combined_classes.length) return a.combined_classes.some((x: string) => matchesClass(x, cls));
  if (/[+,&]/.test(c)) return splitClasses(c).some((p) => matchesClass(p, cls));
  return false;
};
const isCombA = (a: any) => !!a.is_combined || String(a.class ?? '').includes('+') || String(a.class ?? '').includes(',');

export function AssignClassScreen({ className }: { className: string }) {
  const data = useApp((s) => s.data);
  const [q, setQ] = useState('');
  const [edits, setEdits] = useState<Record<string, string>>({});
  const subjects = useMemo(() => (data.dersler ?? []).map((d: any) => String(d.ad ?? '')).filter(Boolean).sort() as string[], [data]);
  const bySubj = useMemo(() => {
    const m = new Map<string, any[]>();
    for (const a of data.atamalar ?? []) if (a && touchesClass(a, className) && a.subject) (m.get(a.subject) ?? m.set(a.subject, []).get(a.subject)!).push(a);
    return m;
  }, [data, className]);
  const { D, P } = dims(data);

  // _update_summary_label
  const seen = new Set<string>();
  let tot = 0;
  for (const a of data.atamalar ?? []) {
    if (!a || !touchesClass(a, className)) continue;
    const k = `${formatTrName(a.subject ?? '')}|${formatTrName(a.teacher ?? '')}|${formatTrName(a.class ?? '')}`;
    if (seen.has(k)) continue;
    seen.add(k);
    tot += parseInt(String(a.duration ?? 0), 10) || 0;
  }
  const maxH = P * D || 40;
  const pct = Math.min(100, Math.floor((tot / maxH) * 100));

  const commitSep = (subject: string, raw: string) => {
    const { type, dur } = canonicalHours(raw);
    const st = formatTrName(subject), cur = formatTrName(className);
    mutate(`${className} · ${subject}: ${type || 'saat silindi'}`, (d) => {
      let found = false;
      for (const a of d.atamalar ?? []) {
        if (formatTrName(a.subject ?? '') === st && !a.is_combined && !String(a.class ?? '').includes('+') && formatTrName(a.class ?? '') === cur) {
          a.type = type; a.duration = dur; found = true;
        }
      }
      if (!found && dur > 0) {
        const ex = (d.atamalar ?? []).find((a: any) => formatTrName(a.subject ?? '') === st && a.teacher);
        const teacher = ex ? String(ex.teacher).split(',')[0].trim() : '';
        if (teacher) d.atamalar.push({ teacher, subject, class: className, duration: dur, type, color: subjectColor(subject, d), is_combined: false, combined_classes: [] });
      }
      d.atamalar = sanitizeAtamalar(d.atamalar ?? []);
    });
  };
  const commitComb = (subject: string, raw: string) => {
    const { type, dur } = canonicalHours(raw);
    const st = formatTrName(subject);
    mutate(`${className} · ${subject} (birleşik): ${type || 'saat silindi'}`, (d) => {
      let found = false;
      for (const a of d.atamalar ?? []) {
        if (formatTrName(a.subject ?? '') !== st) continue;
        if ((a.is_combined && (a.combined_classes ?? []).some((c: string) => matchesClass(c, className))) || (!a.is_combined && String(a.class ?? '').includes('+') && matchesClass(a.class ?? '', className))) {
          a.type = type; a.duration = dur; a.is_combined = true; found = true;
        }
      }
      if (!found && dur > 0) {
        for (const a of d.atamalar ?? []) {
          if (formatTrName(a.subject ?? '') === st && isCombA(a)) {
            let list: string[] = [...(a.combined_classes ?? [])];
            if (!list.length && String(a.class ?? '').includes('+')) list = splitClasses(String(a.class));
            if (!list.some((c) => matchesClass(c, className))) list.push(className);
            a.combined_classes = list; a.class = list.join(' + '); a.type = type; a.duration = dur; a.is_combined = true;
            found = true;
            d.atamalar = d.atamalar.filter((x: any) => !(formatTrName(x.subject ?? '') === st && !x.is_combined && !String(x.class ?? '').includes('+') && matchesClass(x.class ?? '', className)));
            break;
          }
        }
      }
      if (!found && dur > 0) {
        const ex = (d.atamalar ?? []).find((a: any) => formatTrName(a.subject ?? '') === st && a.teacher);
        const teacher = ex ? String(ex.teacher).split(',')[0].trim() : '';
        if (teacher) d.atamalar.push({ teacher, subject, class: className, duration: dur, type, color: subjectColor(subject, d), is_combined: true, combined_classes: [className] });
      }
      d.atamalar = sanitizeAtamalar(d.atamalar ?? []);
    });
  };
  const removeSubject = (subject: string) => {
    const st = formatTrName(subject);
    mutate(`${className}: ${subject} kaldırıldı`, (d) => {
      const out: any[] = [];
      for (const a of d.atamalar ?? []) {
        if (formatTrName(a.subject ?? '') !== st) { out.push(a); continue; }
        const c = String(a.class ?? '');
        if (matchesClass(c, className)) continue;
        if (a.is_combined || /[+,&]/.test(c)) {
          let comb: string[] = [...(a.combined_classes ?? [])];
          if (!comb.length && /[+,&]/.test(c)) comb = splitClasses(c);
          comb = comb.filter((x) => !matchesClass(x, className));
          if (comb.length >= 2) { a.combined_classes = comb; a.class = comb.join(' + '); a.is_combined = true; out.push(a); }
          else if (comb.length === 1) { a.combined_classes = []; a.class = comb[0]; a.is_combined = false; out.push(a); }
        } else out.push(a);
      }
      d.atamalar = out;
      const hit = (p: any) => formatTrName(p.subject_name || p.subject || '') === st && matchesClass(p.class_name || p.class || '', className);
      if (Array.isArray(d.grid_placements)) d.grid_placements = d.grid_placements.filter((p: any) => !hit(p));
      if (d.yerlesim && typeof d.yerlesim === 'object') for (const k of Object.keys(d.yerlesim)) if (d.yerlesim[k] && hit(d.yerlesim[k])) delete d.yerlesim[k];
    });
  };
  const clearAll = async () => {
    if (!(await ask({ title: 'Hepsini Kaldır Onayı', body: `${className} sınıfına atanmış olan TÜM ders ve öğretmen görevlendirmelerini silmek istediğinize emin misiniz?`, ok: 'Hepsini Kaldır', cancel: 'Vazgeç', tone: 'danger' }))) return;
    mutate(`${className}: tüm atamalar kaldırıldı`, (d) => {
      d.atamalar = (d.atamalar ?? []).filter((a: any) => !matchesClass(a.class ?? '', className));
      if (Array.isArray(d.grid_placements)) d.grid_placements = d.grid_placements.filter((p: any) => !matchesClass(p.class_name || p.class || '', className));
      if (d.yerlesim && typeof d.yerlesim === 'object') for (const k of Object.keys(d.yerlesim)) { const i = d.yerlesim[k]; if (i && matchesClass(i.class_name || i.class || '', className)) delete d.yerlesim[k]; }
    });
    await tell('Başarılı', `${className} sınıfının tüm ders atamaları başarıyla temizlendi.`);
  };

  const qn = normalizeTr(q.trim());
  const sub = (t: string) => { const tt = String(t ?? '').trim(); if (!tt || tt === '0' || tt === '—' || tt === 'None') return ''; const n = typeDuration(tt, 0); return n > 0 ? `(${n} Saat)` : ''; };
  return (
    <Window title={`${className} Sınıfı — Ders ve Öğretmen Atama Paneli`} subtitle="Bu sınıfa ait tüm derslerin öğretmen görevlendirmelerini, haftalık ders saatlerini ve dağılım tiplerini yönetin." onClose={closeScreen} width={1000}
      footer={<>
        <span className={`sumlbl ${tot >= maxH ? 'ok' : tot >= Math.floor(maxH / 2) ? 'mid' : 'low'}`}>Toplam Atanan: {tot} / {maxH} Saat (%{pct} Haftalık Doluluk)</span>
        <span className="sp" />
        <Btn kind="danger" onClick={() => void clearAll()}><Icon name="trash" size={15} /> Hepsini Kaldır</Btn>
        <Btn kind="primary" onClick={closeScreen}><Icon name="save" size={15} /> Kapat ve Kaydet</Btn>
      </>}>
      <div className="toolbar">
        <input placeholder="Ders veya Öğretmen Ara..." value={q} onChange={(e) => setQ(e.target.value)} style={{ flex: 1 }} />
        <Btn onClick={() => openScreen({ kind: 'print', preset: { entity: 'class', name: className } })}><Icon name="print" size={15} /> Sınıf Çizelgesini Yazdır</Btn>
      </div>
      <div className="dtable-wrap" style={{ maxHeight: '58vh' }}>
        <table className="dtable">
          <thead><tr><th>Ders Adı</th><th>Atanan Öğretmen(ler)</th><th>{className} Saati</th><th>Birleşik Ders Saati</th><th>İşlemler</th></tr></thead>
          <tbody>
            {subjects.map((subj) => {
              const list = bySubj.get(subj) ?? [];
              const teachers = [...new Set(list.map((a) => a.teacher).filter(Boolean))] as string[];
              if (qn && !normalizeTr(subj).includes(qn) && !normalizeTr(teachers.join(', ')).includes(qn)) return null;
              const sep = list.filter((a) => !a.is_combined && !String(a.class ?? '').includes('+') && !String(a.class ?? '').includes(','));
              const comb = list.filter(isCombA);
              const combCls: string[] = [];
              for (const a of comb) for (const c of (a.combined_classes?.length ? a.combined_classes : splitClasses(String(a.class ?? '')))) if (String(c).trim() && !combCls.includes(String(c).trim())) combCls.push(String(c).trim());
              const inComb = comb.length > 0;
              const color = subjectColor(subj, data);
              const sepCur = (() => { const t = sep.length ? String(sep[0].type ?? '').trim() : ''; if (t && t !== '0' && t !== 'None') return t; return sep.length && Number(sep[0].duration) > 0 ? String(sep[0].duration) : ''; })();
              const combCur = (() => { const t = comb.length ? String(comb[0].type ?? '').trim() : ''; if (t && t !== '0' && t !== 'None') return t; return comb.length && Number(comb[0].duration) > 0 ? String(comb[0].duration) : ''; })();
              const sk = `s|${subj}`, ck = `c|${subj}`;
              return (
                <tr key={subj}>
                  <td><span style={{ color }}>●</span> {subj}</td>
                  <td>{teachers.length ? <>{teachers.join(', ')}{inComb && <span className="pill" style={{ borderColor: color, color }}>Birleşik: {combCls.join(' + ')}</span>}</> : <span className="muted">Atama Yok</span>}</td>
                  <td>
                    {inComb ? <div className="hcell"><input disabled value="— (Birleşik)" /><small className="muted">(Devre Dışı)</small></div>
                      : sep.length || teachers.length ? (
                        <div className="hcell">
                          <Combo value={edits[sk] ?? sepCur} options={DIST_INLINE} placeholder="Saat Girin" width={110}
                            onChange={(v) => setEdits((e) => ({ ...e, [sk]: v }))}
                            onCommit={(v) => { if (v !== sepCur) commitSep(subj, v); setEdits((e) => { const n = { ...e }; delete n[sk]; return n; }); }} />
                          <small className="muted">{sub(edits[sk] ?? sepCur)}</small>
                        </div>
                      ) : <span className="muted">—</span>}
                  </td>
                  <td>
                    {inComb ? (
                      <div className="hcell">
                        <Combo value={edits[ck] ?? combCur} options={DIST_INLINE} placeholder="Birleşik Saat" width={110}
                          onChange={(v) => setEdits((e) => ({ ...e, [ck]: v }))}
                          onCommit={(v) => { if (v !== combCur) commitComb(subj, v); setEdits((e) => { const n = { ...e }; delete n[ck]; return n; }); }} />
                        <small className="muted">{sub(edits[ck] ?? combCur)}</small>
                      </div>
                    ) : teachers.length ? <div className="hcell"><input disabled value={combCur || '—'} /><small className="muted">(Devre Dışı)</small></div> : <span className="muted">—</span>}
                  </td>
                  <td className="acts-cell">
                    {list.length ? <>
                      <Btn onClick={() => openScreen({ kind: 'assignSubject', subject: subj, className })}>Düzenle</Btn>
                      <Btn kind="danger" onClick={() => removeSubject(subj)}>Kaldır</Btn>
                    </> : <>
                      <Btn kind="primary" onClick={() => openScreen({ kind: 'assignSubject', subject: subj, className })}>+ Ata</Btn>
                      <Btn disabled>Kaldır</Btn>
                    </>}
                  </td>
                </tr>
              );
            })}
            {!subjects.length && <tr><td colSpan={5} className="muted center">Tanımlı ders yok. Önce Dersler ekranından ders ekleyin.</td></tr>}
          </tbody>
        </table>
      </div>
    </Window>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Dersin Öğretmenleri ve Saatleri (SubjectTeacherAssignmentDialog)
// ════════════════════════════════════════════════════════════════════════════
interface TCfg { checked: boolean; cur: string; comb: string; classes: string[]; combined: string[]; isCombined: boolean; sepHours: Record<string, string> }

function initConfigs(d: any, subject: string, current: string): Record<string, TCfg> {
  const st = formatTrName(subject);
  const existing = (d.atamalar ?? []).filter((a: any) => formatTrName(a.subject ?? '') === st);
  const out: Record<string, TCfg> = {};
  for (const t of (d.ogretmenler ?? []).map((x: any) => String(x.ad ?? '')).filter(Boolean) as string[]) {
    const mine = existing.filter((a: any) => matchesTeacherLoose(a.teacher ?? '', t));
    const classes: string[] = [], combined: string[] = [];
    let cur = '', comb = '';
    const sepHours: Record<string, string> = {};
    for (const a of mine) {
      let typ = String(a.type ?? '').trim();
      if (!typ || typ === '0' || typ === 'None') { const dur = parseInt(String(a.duration ?? 0), 10) || 0; typ = dur > 0 ? String(dur) : '2'; }
      const raw = String(a.class ?? '').trim();
      if (a.is_combined && Array.isArray(a.combined_classes) && a.combined_classes.length) {
        comb = typ;
        for (const c of a.combined_classes) { const cc = String(c).trim(); if (cc && !classes.includes(cc)) classes.push(cc); if (cc && !combined.includes(cc)) combined.push(cc); }
      } else if (raw.includes('+') || (raw.includes(',') && a.is_combined)) {
        comb = typ;
        for (const cc of splitClasses(raw)) { if (!classes.includes(cc)) classes.push(cc); if (!combined.includes(cc)) combined.push(cc); }
      } else if (raw) {
        if (!classes.includes(raw)) classes.push(raw);
        sepHours[formatTrName(raw)] = typ;
        if (current && (formatTrName(raw) === formatTrName(current) || matchesClass(raw, current))) cur = typ;
      }
    }
    const cc = formatTrName(current);
    const checked = current ? classes.some((c) => formatTrName(c) === cc || matchesClass(c, cc) || matchesClass(cc, c)) : mine.length > 0;
    // Normal saat kutusu seçili öğretmende boş kalmaz: 2 hazır yazılı gelir (edit_forms._create_hour_combo).
    out[t] = { checked, cur: checked ? (cur && cur !== '0' ? cur : '2') : cur, comb, classes, combined, isCombined: combined.length > 0 || !!comb || mine.some((a: any) => a.is_combined), sepHours };
  }
  return out;
}

function classDisplay(c: TCfg): [string, boolean] {
  const isComb = c.isCombined && c.combined.length > 1;
  if (!(c.checked && c.classes.length)) return ['—', false];
  if (isComb) {
    const sep = c.classes.filter((x) => !c.combined.includes(x));
    const cs = c.combined.join('+');
    return [sep.length ? `${sep.join(', ')}, ${cs} (Birleşik)` : `${cs} (Birleşik)`, true];
  }
  return [c.classes.join(', '), false];
}

export function AssignSubjectScreen({ subject, className }: { subject: string; className?: string }) {
  const data = useApp((s) => s.data);
  const current = className ?? '';
  const allClasses = useMemo(() => (data.siniflar ?? []).map((c: any) => String(c.ad ?? '')).filter(Boolean) as string[], [data]);
  const [cfgs, setCfgs] = useState<Record<string, TCfg>>(() => initConfigs(data, subject, current));
  const [q, setQ] = useState('');
  const [modal, setModal] = useState<string | null>(null);
  const names = Object.keys(cfgs).sort();
  const set = (t: string, patch: Partial<TCfg>) => setCfgs((c) => ({ ...c, [t]: { ...c[t], ...patch } }));

  const toggle = (t: string, on: boolean) => setCfgs((all) => {
    const c = { ...all[t], checked: on, cur: on ? (all[t].cur && all[t].cur !== '0' ? all[t].cur : '2') : all[t].cur };
    if (current) {
      if (on) { if (!c.classes.some((x) => formatTrName(x) === formatTrName(current) || matchesClass(x, current))) c.classes = [...c.classes, current]; }
      else {
        c.classes = c.classes.filter((x) => formatTrName(x) !== formatTrName(current) && !matchesClass(x, current));
        let comb = c.combined.filter((x) => formatTrName(x) !== formatTrName(current) && !matchesClass(x, current));
        if (comb.length <= 1) comb = [];
        c.combined = comb; c.isCombined = comb.length > 0;
      }
    } else if (on && !c.classes.length && allClasses.length) c.classes = [allClasses[0]];
    return { ...all, [t]: c };
  });

  const save = (source: Record<string, TCfg>) => {
    const st = formatTrName(subject);
    const cfgCopy: Record<string, TCfg> = structuredClone(source);
    mutate(`${subject}: öğretmen ve saatler`, (d) => {
      const atamalar: any[] = d.atamalar ?? [];
      const clean: any[] = atamalar.filter((a) => formatTrName(a.subject ?? '') !== st);
      const managed = Object.keys(cfgCopy).map((t) => formatTrName(t));
      for (const a of atamalar) {
        if (formatTrName(a.subject ?? '') === st && !managed.some((m) => matchesTeacherLoose(formatTrName(a.teacher ?? ''), m))) clean.push(a);
      }
      for (const [tName, cfg] of Object.entries(cfgCopy)) {
        let classes = cfg.classes.filter((c) => String(c).trim());
        if (!cfg.checked) {
          if (current) {
            const cc = formatTrName(current);
            classes = classes.filter((c) => formatTrName(c) !== cc && !matchesClass(c, cc));
            let comb = cfg.combined.filter((c) => formatTrName(c) !== cc && !matchesClass(c, cc));
            if (comb.length <= 1) comb = [];
            cfg.combined = comb; cfg.isCombined = comb.length > 0;
          } else { classes = []; cfg.combined = []; cfg.isCombined = false; }
        }
        if (!classes.length) continue;
        let comb = [...cfg.combined];
        let combType = cfg.comb.trim();
        if (!comb.length && combType) { comb = [...classes]; cfg.combined = comb; cfg.isCombined = true; }
        const isComb = cfg.isCombined || !!combType;
        const color = subjectColor(subject, d);
        if (isComb && comb.length) {
          if (!combType) combType = '2';
          const dur = typeDuration(combType, 2);
          clean.push({ teacher: tName.trim(), subject: subject.trim(), class: comb.join(' + '), duration: dur, type: combType, color, is_combined: true, combined_classes: [...comb] });
        }
        const separate = isComb ? classes.filter((c) => !comb.includes(c)) : classes;
        for (const c of separate) {
          let typ: string, dur: number;
          if (current && (formatTrName(c) === formatTrName(current) || matchesClass(c, current))) {
            const t = cfg.cur.trim();
            dur = typeDuration(t, 0); typ = dur > 0 ? t : '';
          } else {
            let old = cfg.sepHours[formatTrName(c)];
            if (!old) {
              const oa = atamalar.find((a) => formatTrName(a.subject ?? '') === st && matchesTeacherLoose(a.teacher ?? '', tName) && formatTrName(a.class ?? '') === formatTrName(c));
              old = oa && String(oa.type ?? '').trim() ? String(oa.type).trim() : oa && Number(oa.duration) > 0 ? String(oa.duration) : '';
            }
            dur = typeDuration(old, 0); typ = dur > 0 ? old : '';
          }
          clean.push({ teacher: tName.trim(), subject: subject.trim(), class: c.trim(), duration: dur, type: typ, color, is_combined: false, combined_classes: [] });
        }
      }
      d.atamalar = sanitizeAtamalar(clean);
      if (current) {
        const tc = formatTrName(current);
        pruneOrphanPlacements(d, (p) => formatTrName(p.subject_name || p.subject || '') === st && formatTrName(p.class_name || p.class || '') === tc);
      } else {
        pruneOrphanPlacements(d, (p) => formatTrName(p.subject_name || p.subject || '') === st);
      }
    });
    closeScreen();
  };
  const clearAll = () => {
    const next: Record<string, TCfg> = {};
    for (const [t, c0] of Object.entries(cfgs)) {
      const c = { ...c0, checked: false };
      if (current) {
        const cc = formatTrName(current);
        c.classes = c.classes.filter((x) => formatTrName(x) !== cc && !matchesClass(x, cc));
        let comb = c.combined.filter((x) => formatTrName(x) !== cc && !matchesClass(x, cc));
        if (comb.length <= 1) comb = [];
        c.combined = comb; c.isCombined = comb.length > 0;
      } else { c.classes = []; c.combined = []; c.isCombined = false; }
      next[t] = c;
    }
    save(next);
  };

  const qn = normalizeTr(q.trim());
  const mc = modal ? cfgs[modal] : null;
  return (
    <Window title={`${subject} Dersi — Öğretmen ve Saat Atama Paneli`}
      subtitle={`${current ? `Hedef Sınıf: ${current}` : 'Tüm Sınıflar'} | Seçilen öğretmene ders saati ve dağılım tipi otomatik eşleştirilir.`} onClose={closeScreen} width={1000}
      footer={<>
        <Btn kind="danger" onClick={clearAll}><Icon name="trash" size={15} /> Bu Dersi Kaldır</Btn>
        <span className="sp" />
        <Btn onClick={closeScreen}>İptal</Btn>
        <Btn kind="primary" onClick={() => save(cfgs)}><Icon name="save" size={15} /> Kaydet ve Eşleştir</Btn>
      </>}>
      <input placeholder="Arama Yap..." value={q} onChange={(e) => setQ(e.target.value)} style={{ width: '100%', marginBottom: 8 }} />
      <div className="dtable-wrap" style={{ maxHeight: '60vh' }}>
        <table className="dtable">
          <thead><tr><th>Atanacak Öğretmen</th><th>{current ? `${current} Saati` : 'Ders Saati'}</th><th>Birleşik Ders Saati</th><th>Atanan Sınıf(lar)</th><th>Ayrıcalıklı Sınıf Seçimi</th></tr></thead>
          <tbody>
            {names.filter((t) => !qn || normalizeTr(t).includes(qn)).map((t) => {
              const c = cfgs[t];
              const [txt, isComb] = classDisplay(c);
              return (
                <tr key={t} className={c.checked ? '' : 'dim'}>
                  <td><label className="check"><input type="checkbox" checked={c.checked} onChange={(e) => toggle(t, e.target.checked)} /> {t}</label></td>
                  <td>{c.checked ? <Combo value={c.cur} placeholder="Saat Yaz" options={DIST_INLINE.slice(0, 17)} width={100} onChange={(v) => set(t, { cur: v })} /> : <span className="muted">—</span>}</td>
                  <td>{c.checked ? <Combo value={c.comb} placeholder="Saat Yaz" options={DIST_INLINE.slice(0, 17)} width={100} onChange={(v) => set(t, { comb: v })} /> : <span className="muted">—</span>}</td>
                  <td className={c.checked ? (isComb ? 'txt-ok' : 'txt-acc') : 'muted'}>{txt}</td>
                  <td>{c.checked ? <Btn onClick={() => setModal(t)}><Icon name="settings" size={13} /> Daha Fazla Sınıf Ata</Btn> : <span className="muted">—</span>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {modal && mc && (
        <MultiClassAssign teacher={modal} subject={subject} allClasses={allClasses} selected={mc.classes} combined={mc.combined} isCombined={mc.isCombined}
          onClose={() => setModal(null)}
          onOk={(sel, comb) => { set(modal, { classes: sel, combined: comb, isCombined: comb.length > 1, checked: sel.length ? true : mc.checked, cur: mc.cur && mc.cur !== '0' ? mc.cur : '2' }); setModal(null); }} />
      )}
    </Window>
  );
}

/** MultiClassAssignDialog — öğretmene sınıflar + birleşik işaretleme. */
function MultiClassAssign({ teacher, subject, allClasses, selected, combined, isCombined, onOk, onClose }: {
  teacher: string; subject: string; allClasses: string[]; selected: string[]; combined: string[]; isCombined: boolean;
  onOk: (sel: string[], comb: string[]) => void; onClose: () => void;
}) {
  const initComb = isCombined && combined.length > 1;
  const same = (a: string, b: string) => matchesClass(a, b) || matchesClass(b, a) || a.trim() === b.trim();
  const [st, setSt] = useState(() => Object.fromEntries(allClasses.map((c) => {
    const on = selected.some((s) => same(c, s));
    return [c, { on, comb: on && initComb && combined.some((s) => same(c, s)) }];
  })));
  const [q, setQ] = useState('');
  const qn = normalizeTr(q.trim());
  const vis = allClasses.filter((c) => !qn || normalizeTr(c).includes(qn));
  const sel = allClasses.filter((c) => st[c].on);
  const combRaw = allClasses.filter((c) => st[c].on && st[c].comb);
  const comb = combRaw.length > 1 ? combRaw : [];
  const sep = sel.filter((c) => !comb.includes(c));
  return (
    <Window title={`Sınıf Seçimi ve Birleştirme — ${teacher}`} onClose={onClose} width={620}
      footer={<><span className="sp" /><Btn onClick={onClose}>İptal</Btn><Btn kind="primary" onClick={() => onOk(sel, comb)}>Uygula</Btn></>}>
      <div className="card">
        <b>{teacher}</b> — Atanacak Sınıflar ve Birleştirme
        <div className="muted small">Ders: <b>{subject}</b> | Bu öğretmene atanacak sınıfları seçin. Birlikte (ortak) işlenecek sınıflar için <b>Birleşik</b> kutucuğunu işaretleyin.</div>
      </div>
      <div className="toolbar">
        <input placeholder="Sınıf Ara..." value={q} onChange={(e) => setQ(e.target.value)} style={{ flex: 1 }} />
        <Btn onClick={() => setSt((s) => ({ ...s, ...Object.fromEntries(vis.map((c) => [c, { ...s[c], on: true }])) }))}>Tümünü Seç</Btn>
        <Btn onClick={() => setSt((s) => Object.fromEntries(Object.entries(s).map(([c, v]) => [c, { ...v, comb: v.on ? true : v.comb }])))}>Seçilileri Birleştir</Btn>
        <Btn onClick={() => setSt((s) => Object.fromEntries(Object.entries(s).map(([c, v]) => [c, { ...v, comb: false }])))}>Birleştirmeyi Sıfırla</Btn>
      </div>
      <div className="dtable-wrap" style={{ maxHeight: '46vh' }}>
        <table className="dtable">
          <thead><tr><th>1. Bu Sınıfa Ders Ata</th><th>2. Ortak / Birleşik İşlensin</th></tr></thead>
          <tbody>
            {vis.map((c) => (
              <tr key={c}>
                <td><label className="check"><input type="checkbox" checked={st[c].on} onChange={(e) => setSt((s) => ({ ...s, [c]: { on: e.target.checked, comb: e.target.checked ? s[c].comb : false } }))} /> {c}</label></td>
                <td><label className="check"><input type="checkbox" checked={st[c].comb} onChange={(e) => setSt((s) => ({ ...s, [c]: { on: e.target.checked ? true : s[c].on, comb: e.target.checked } }))} /> Birleşik (Ortak)</label></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="preview">
        {!sel.length ? 'Henüz hiçbir sınıf seçilmedi.'
          : comb.length > 1 ? <><b>Birleşik (Ortak) Sınıflar:</b> {comb.join('+')} ({sep.length ? 'Ortak İşlenir' : 'Tümü Ortak İşlenir'}){sep.length > 0 && <><br /><b>Ayrı Sınıflar:</b> {sep.join(', ')} (Bağımsız İşlenir)</>}</>
            : <><b>Ayrı Sınıflar:</b> {sel.join(', ')} (Her sınıf bağımsız olarak işlenecektir)</>}
      </div>
    </Window>
  );
}
