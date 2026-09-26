// Kontrol ve analiz pencereleri:
//   Ön Kontrol (test_timetable_dialog + preflight), Son Kontrol (verify_timetable_dialog
//   + motorun kilit denetimi), İstatistik (statistics_dialog), Danışman (advisor_dialog).
import { useEffect, useMemo, useState } from 'react';
import { analyse, audit, engineViolations, openSlotsPerClass, perClass, perTeacher, placedPerClass, teacherCapacity } from '../analysis.ts';
import type { Violation } from '../analysis.ts';
import { checkFeasibility, formatReport } from '../feasibility.ts';
import { dunyaKur, kilitCatismalari } from '../../engine/locks.ts';
import { hazirla } from '../../engine/prep.ts';
import { closeScreen, setState, useApp } from '../store.ts';
import { Btn, Window } from '../ui.tsx';

// ════════════════════════════════════════════════════════════════════════════
// Planlama Öncesi Kontrol
// ════════════════════════════════════════════════════════════════════════════
export function PrecheckScreen() {
  const data = useApp((s) => s.data);
  const entities = useMemo(() => {
    const e = [...(data.siniflar ?? []).filter((c: any) => c.ad).map((c: any) => `Sınıf: ${c.ad}`), ...(data.ogretmenler ?? []).filter((t: any) => t.ad).map((t: any) => `Öğretmen: ${t.ad}`)];
    return e.length ? e : ['Veri bulunamadı'];
  }, [data]);
  const [step, setStep] = useState(0);
  const result = useMemo(() => {
    const rep = checkFeasibility(data);
    let locks: string[] = [];
    try {
      const pr = hazirla(data, null);
      const [w, rules, report, kilitler] = dunyaKur(pr.data, pr.D, pr.P, pr.engel, pr.selected, pr.data.planlama_iliskileri ?? []);
      if (report.errors.length) locks = report.errors.map((x) => `Planlama ilişkisi okunamadı: ${x}`);
      else locks = kilitCatismalari(w, rules, kilitler, pr.data, true).map((c) => c.mesaj);
    } catch (e: any) { locks = [String(e?.message ?? e)]; }
    return { rep, lines: rep.ok ? [] : formatReport(rep, data), locks };
  }, [data]);
  useEffect(() => {
    if (step >= entities.length) return;
    const t = setTimeout(() => setStep((s) => Math.min(entities.length, s + Math.max(1, Math.ceil(entities.length / 40)))), 25);
    return () => clearTimeout(t);
  }, [step, entities.length]);
  const done = step >= entities.length;
  const ok = result.rep.ok && !result.locks.length;
  return (
    <Window title={done ? 'Planlama Öncesi Kontrol' : 'Test ediliyor...'} onClose={closeScreen} width={640}
      footer={<><span className="sp" />{done && ok && <Btn onClick={() => { closeScreen(); setState({ plannerOpen: true }); }}>Otomatik Planla</Btn>}<Btn kind="primary" disabled={!done} onClick={closeScreen}>Kapat</Btn></>}>
      <b>{done ? (ok ? 'Test başarıyla tamamlandı!' : 'Test tamamlandı — dikkat edilmesi gerekenler var') : 'Temel veriler test ediliyor...'}</b>
      <div className="bar"><div style={{ width: `${Math.round((100 * Math.min(step, entities.length)) / entities.length)}%` }} /></div>
      <div className="log">
        <div>Test başlatıldı...</div>
        {entities.slice(0, step).map((e) => <div key={e}>Test ediliyor -&gt; {e}</div>)}
        {done && ok && <div className="ok">Hiçbir temel sorun bulunamadı. Program otomatik planlamaya hazır.</div>}
      </div>
      {done && !result.rep.ok && (
        <div className="rep">{result.lines.map((l, i) => <div key={i} className={l.kind}>{l.text}</div>)}</div>
      )}
      {done && result.locks.length > 0 && (
        <div className="card warnbox">
          <b>Kilitli dersler verilerle çelişiyor ({result.locks.length})</b>
          <ul className="list">{result.locks.slice(0, 12).map((m) => <li key={m}>{m}</li>)}</ul>
          <div className="muted small">Otomatik planlayıcı bu kilitleri kendiliğinden açmaz; başlatınca "Bu kilitleri çöz ve planla" seçeneğini sunar.</div>
        </div>
      )}
    </Window>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Planlama Sonrası Kontrol (Doğrulama Sonuçları)
// ════════════════════════════════════════════════════════════════════════════
export function VerifyScreen() {
  const data = useApp((s) => s.data);
  const { items, error } = useMemo(() => {
    const out: Violation[] = [];
    if (!(data.grid_placements ?? []).length) out.push({ severity: 'Yüksek', desc: 'Ders programı boş! Hiçbir ders yerleştirilmemiş.', affected: 'Tüm Sınıflar' });
    for (const e of data.secmeli_dersler ?? []) if (e.ogretmen === 'Atanmadı') out.push({ severity: 'Normal', desc: 'Seçmeli derse öğretmen atanmamış.', affected: e.ad ?? 'Bilinmeyen' });
    for (const e of data.secmeli_dersler ?? []) if (!(e.siniflar ?? []).length) out.push({ severity: 'Düşük', desc: 'Seçmeli ders hiçbir sınıfa atanmamış.', affected: e.ad ?? 'Bilinmeyen' });
    const v = engineViolations(data);
    return { items: [...out, ...v.items], error: v.error };
  }, [data]);
  return (
    <Window title="Doğrulama Sonuçları" onClose={closeScreen} width={820} footer={<><span className="sp" /><Btn kind="primary" onClick={closeScreen}>Kapat</Btn></>}>
      <b>{items.length ? `Doğrulama tamamlandı. ${items.length} adet kısıtlama ihlali bulundu!` : 'Doğrulama başarılı! Hiçbir kısıtlama ihlali bulunamadı.'}</b>
      <div className="muted small" style={{ margin: '4px 0 10px' }}>Çizelgedeki her ders, otomatik planlayıcının kullandığı kurallarla (kapalı saatler, çakışmalar, planlama ilişkileri) denetlenir.</div>
      {error && <div className="card warnbox">Denetim tamamlanamadı: {error}</div>}
      <div className="dtable-wrap" style={{ maxHeight: '55vh' }}>
        <table className="dtable">
          <thead><tr><th style={{ width: 80 }}>Önem</th><th>Kısıtlama / İhlal Nedeni</th><th>Etkilenen Nesneler</th></tr></thead>
          <tbody>
            {items.map((x, i) => (
              <tr key={i}><td className={x.severity === 'Yüksek' ? 'txt-bad' : x.severity === 'Normal' ? 'txt-warn' : ''}>{x.severity}</td><td>{x.desc}</td><td>{x.affected}</td></tr>
            ))}
            {!items.length && <tr><td colSpan={3} className="muted center">İhlal yok.</td></tr>}
          </tbody>
        </table>
      </div>
    </Window>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// İstatistikler ve Analiz
// ════════════════════════════════════════════════════════════════════════════
export function StatisticsScreen() {
  const data = useApp((s) => s.data);
  const s = useMemo(() => {
    const pc = perClass(data), pt = perTeacher(data), au = audit(data);
    const cap = teacherCapacity(data), open = openSlotsPerClass(data), placed = placedPerClass(data);
    const known = (data.ogretmenler ?? []).map((t: any) => String(t.ad || t.name || '').trim()).filter(Boolean) as string[];
    const names = [...new Set([...known, ...pt.keys()])].sort((a, b) => ((pt.get(b) ?? 0) - (pt.get(a) ?? 0)) || (a < b ? -1 : a > b ? 1 : 0));
    let classNames = (data.siniflar ?? []).map((c: any) => String(c.ad || c.name || '').trim()).filter(Boolean) as string[];
    if (!classNames.length) classNames = [...pc.keys()].sort();
    const parts: string[] = [];
    if (au.stale.length) parts.push(`${au.stale.length} atamada saat alanları birbirini tutmuyor (ör. ${au.stale[0][0]} — ${au.stale[0][1]}).`);
    if (au.unknownTeachers.length) parts.push(`${au.unknownTeachers.length} atamanın öğretmeni öğretmen listesinde yok: ${au.unknownTeachers.slice(0, 3).map((x) => x[2]).join(', ')}`);
    if (au.unknownClasses.length) parts.push(`${au.unknownClasses.length} atamanın sınıfı sınıf listesinde yok: ${au.unknownClasses.slice(0, 3).map((x) => x[0]).join(', ')}`);
    if (au.combinedExtra) parts.push(`${au.combinedExtra} saat birleşik (eş zamanlı) ders olduğu için sınıf tarafı toplamı daha yüksek görünür.`);
    return { pc, pt, au, cap, open, placed, names, classNames, warn: parts.join('  ') };
  }, [data]);
  return (
    <Window title="İstatistikler ve Analiz" onClose={closeScreen} width={900} footer={<><span className="sp" /><Btn kind="primary" onClick={closeScreen}>Kapat</Btn></>}>
      <div className="card">
        <div className="card-title">Genel Okul Özeti</div>
        <div>Toplam Sınıf Sayısı: {(data.siniflar ?? []).length}</div>
        <div>Toplam Öğretmen Sayısı: {(data.ogretmenler ?? []).length}</div>
        <div>Atanan Toplam Ders Saati: {s.au.lessonTotal} Saat</div>
        <div>Sınıf tarafı toplamı: {s.au.classTotal} Saat  |  Öğretmen tarafı toplamı: {s.au.teacherTotal} Saat</div>
        {s.warn ? <div className="txt-warn" style={{ marginTop: 6 }}>{s.warn}</div> : <div className="txt-ok" style={{ marginTop: 6 }}>Sınıf ekranı ile öğretmen ekranı birebir tutuyor ✔</div>}
      </div>
      <div className="split">
        <div className="card">
          <div className="card-title">Öğretmen Ders Yükü Dağılımı</div>
          <div className="dtable-wrap" style={{ maxHeight: '40vh' }}>
            <table className="dtable">
              <thead><tr><th>Öğretmen</th><th>Haftalık Toplam Saat</th><th>En Fazla Mümkün</th></tr></thead>
              <tbody>{s.names.map((n) => {
                const h = s.pt.get(n) ?? 0, c = s.cap.get(n);
                const over = c !== undefined && h > c;
                return <tr key={n} className={over ? 'bad-row' : ''}><td>{n}</td><td className="center">{h} Saat</td><td className="center">{c === undefined ? '—' : over ? `${c} Saat  (+${h - c} fazla)` : `${c} Saat`}</td></tr>;
              })}</tbody>
            </table>
          </div>
        </div>
        <div className="card">
          <div className="card-title">Sınıf Ders Yükü Dağılımı</div>
          <div className="dtable-wrap" style={{ maxHeight: '40vh' }}>
            <table className="dtable">
              <thead><tr><th>Sınıf</th><th>Atanan Saat</th><th>Açık Saat</th><th>Yerleşen</th></tr></thead>
              <tbody>{s.classNames.map((c) => {
                const need = s.pc.get(c) ?? 0, have = s.open.get(c), got = s.placed.get(c) ?? 0;
                return <tr key={c}><td>{c}</td><td className={`center ${have !== undefined && need > have ? 'bad-cell' : ''}`}>{need}</td><td className="center">{have === undefined ? '—' : have}</td><td className="center">{got}</td></tr>;
              })}</tbody>
            </table>
          </div>
        </div>
      </div>
    </Window>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Danışman — Çizelge Analizi
// ════════════════════════════════════════════════════════════════════════════
const TAG = { error: 'Sorun', warning: 'Uyarı', info: 'Bilgi' } as const;

export function AdvisorScreen() {
  const data = useApp((s) => s.data);
  const [n, setN] = useState(0);
  const findings = useMemo(() => {
    try { return analyse(data); } catch (e: any) { return [['error', 'Analiz yapılamadı', String(e?.message ?? e), '']] as ReturnType<typeof analyse>; }
  }, [data, n]);
  const errors = findings.filter((f) => f[0] === 'error').length, warnings = findings.filter((f) => f[0] === 'warning').length;
  return (
    <Window title="Danışman — Çizelge Analizi" onClose={closeScreen} width={820}
      footer={<><Btn onClick={() => setN((x) => x + 1)}>Yeniden Analiz Et</Btn><span className="sp" /><Btn kind="primary" onClick={closeScreen}>Kapat</Btn></>}>
      <b className="adv-head">{errors ? `${errors} sorun, ${warnings} uyarı bulundu` : warnings ? `${warnings} uyarı bulundu — engelleyici sorun yok` : 'Çizelge temiz görünüyor'}</b>
      <div className="adv-list">
        {findings.map(([sev, title, detail, action], i) => (
          <div key={i} className={`adv adv-${sev}`}>
            <div className="adv-top"><span className="chip">{TAG[sev]}</span><b>{title}</b></div>
            {detail && <div className="adv-detail">{detail}</div>}
            {action && <div className="adv-act">→ {action}</div>}
          </div>
        ))}
      </div>
    </Window>
  );
}
