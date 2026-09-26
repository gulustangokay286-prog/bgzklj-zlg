// dialogs/school_info.py (Temel Bilgiler) + days_dialog.py (Çalışma Günleri)
// + bell_times_dialog.py (Zil ve Teneffüs Saatleri).
import { useState } from 'react';
import { closeScreen, mutate, tell, useApp } from '../store.ts';
import { Btn, Window } from '../ui.tsx';

const DAYS_ALL = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar'];
const YEARS = ['2025-2026', '2026-2027', '2024-2025', '2027-2028'];
const MEVZUAT = ['MEB Standart Haftalık Çizelgesi', 'Özel Öğretim Kurumları Yönetmeliği', 'YÖK / Üniversite Standart'];
const WEEKEND = ['Cumartesi - Pazar', 'Yalnız Pazar', 'Hafta Sonu Tatili Yok', 'Pazar - Pazartesi', 'Cuma - Cumartesi'];
const COUNTRIES = ['Türkiye (TR)', 'Kuzey Kıbrıs Türk Cumhuriyeti (KKTC)', 'Almanya (DE)', 'İngiltere (UK)', 'Azerbaycan (AZ)'];
const LANGS = ['Türkçe (Varsayılan)', 'English', 'Deutsch'];
const TZS = ['GMT+3 (İstanbul, Ankara)', 'GMT+2 (Berlin, Paris)', 'GMT+0 (Londra)', 'GMT+4 (Bakü)'];

export function SchoolScreen() {
  const data = useApp((s) => s.data);
  const st = data.settings ?? {};
  const [tab, setTab] = useState(0);
  const [name, setName] = useState<string>(data.okul_adi || st.school_name || data.school_name || '');
  const [year, setYear] = useState<string>(YEARS.includes(st.academic_year) ? st.academic_year : '2025-2026');
  const [periods, setPeriods] = useState<number>(() => { const v = Number(data.ders_saati || st.periods_per_day || st.periods || 8); return v >= 1 && v <= 16 ? v : 8; });
  const [dayCount, setDayCount] = useState<number>(() => { const v = Number(data.gun_sayisi || st.days_count || (Array.isArray(st.days) ? st.days.length : 5)); return v >= 1 && v <= 7 ? v : 5; });
  const [weekend, setWeekend] = useState<string>(WEEKEND.includes(st.weekend_option) ? st.weekend_option : 'Cumartesi - Pazar');
  const [mevzuat, setMevzuat] = useState<string>(MEVZUAT.includes(st.mevzuat_tipi) ? st.mevzuat_tipi : MEVZUAT[0]);
  const [teblig, setTeblig] = useState<string>(st.teblig_bilgisi ?? '');
  const [yAd, setYAd] = useState<string>(st.yetkili_ad ?? '');
  const [yUnvan, setYUnvan] = useState<string>(st.yetkili_unvan ?? '');
  const [kurum, setKurum] = useState<'okul' | 'fakulte'>(st.kurum_tipi === 'fakulte' ? 'fakulte' : 'okul');
  const [multi, setMulti] = useState<boolean>(!!st.multi_term);
  const [model, setModel] = useState<string>(['ab_haftalik', 'donemlik'].includes(st.program_modeli) ? st.program_modeli : 'standart');
  const [country, setCountry] = useState<string>(st.country ?? COUNTRIES[0]);
  const [lang, setLang] = useState<string>(st.language ?? LANGS[0]);
  const [tz, setTz] = useState<string>(st.timezone ?? TZS[0]);
  const [sub, setSub] = useState<'bells' | 'days' | null>(null);

  const changeDays = (n: number) => {
    setDayCount(n);
    if (n >= 7) setWeekend('Hafta Sonu Tatili Yok'); else if (n === 6) setWeekend('Yalnız Pazar'); else if (n === 5) setWeekend('Cumartesi - Pazar');
  };
  const changeWeekend = (w: string) => {
    setWeekend(w);
    if (w === 'Hafta Sonu Tatili Yok') setDayCount(7); else if (w === 'Yalnız Pazar') setDayCount(6); else setDayCount(5);
  };

  const save = async () => {
    if (!name.trim()) { await tell('Uyarı', 'Lütfen okul veya kurum adını boş bırakmayınız.'); return; }
    mutate('Temel bilgiler', (d) => {
      d.okul_adi = name.trim();
      d.ders_saati = periods;
      d.gun_sayisi = dayCount;
      const s = (d.settings ??= {});
      Object.assign(s, {
        school_name: name.trim(), academic_year: year, periods, periods_per_day: periods, days_count: dayCount, day_count: dayCount,
        weekend_option: weekend, mevzuat_tipi: mevzuat, teblig_bilgisi: teblig.trim(), yetkili_ad: yAd.trim(), yetkili_unvan: yUnvan.trim(),
        kurum_tipi: kurum, multi_term: multi, program_modeli: model, country, language: lang, timezone: tz,
      });
      const active = s.active_days_list;
      if (Array.isArray(active) && active.length === 7 && active.filter((x: any) => x.active ?? true).length === dayCount) {
        s.days = active.filter((x: any) => x.active ?? true).map((x: any) => x.name);
      } else {
        s.days = DAYS_ALL.slice(0, dayCount);
        s.active_days_list = DAYS_ALL.map((n, i) => ({ day_index: i, name: n, active: i < dayCount }));
      }
    });
    closeScreen();
  };

  return (
    <Window title="Temel Okul Bilgileri ve Genel Ayarlar" subtitle="Ders çizelgesi zaman yapısı, kurum kimliği ve planlama parametreleri." onClose={closeScreen} width={820}
      footer={<><span className="lic">Lisans Türü: Sınırsız</span><span className="sp" /><Btn onClick={closeScreen}>Vazgeç</Btn><Btn kind="primary" onClick={() => void save()}>Kaydet ve Uygula</Btn></>}>
      <div className="tabs">
        {['Genel Bilgiler ve Zaman', 'Ülke ve Yerelleştirme', 'Program ve Dönem Türü'].map((t, i) => <button key={t} className={tab === i ? 'on' : ''} onClick={() => setTab(i)}>{t}</button>)}
      </div>
      {tab === 0 && (
        <>
          <div className="card grid2">
            <label className="field" style={{ gridColumn: '1 / -1' }}><span className="field-label">Okul / Kurum Adı</span><input value={name} placeholder="Örn: Çeken Akademi / Anadolu Lisesi" onChange={(e) => setName(e.target.value)} /></label>
            <label className="field"><span className="field-label">Akademik Eğitim Yılı</span><select value={year} onChange={(e) => setYear(e.target.value)}>{YEARS.map((y) => <option key={y}>{y}</option>)}</select></label>
            <label className="field"><span className="field-label">Mevzuat / Tebliğ</span><select value={mevzuat} onChange={(e) => setMevzuat(e.target.value)}>{MEVZUAT.map((y) => <option key={y}>{y}</option>)}</select></label>
            <label className="field"><span className="field-label">Tebliğ bilgisi</span><input value={teblig} placeholder="Örn: 2025/14 Tebliğler Dergisi" onChange={(e) => setTeblig(e.target.value)} /></label>
            <label className="field"><span className="field-label">Kurum Yetkilisi</span><input value={yAd} placeholder="Örn: Ad Soyad" onChange={(e) => setYAd(e.target.value)} /></label>
            <label className="field"><span className="field-label">Unvan</span><input value={yUnvan} placeholder="Örn: Okul Müdürü" onChange={(e) => setYUnvan(e.target.value)} /></label>
          </div>
          <div className="card grid2">
            <label className="field"><span className="field-label">Günlük Ders Saati</span>
              <div className="inline"><select value={periods} onChange={(e) => setPeriods(Number(e.target.value))}>{Array.from({ length: 16 }, (_, i) => <option key={i} value={i + 1}>{i + 1}</option>)}</select>
                <Btn type="button" onClick={() => setSub('bells')}>Zil ve Teneffüs Saatleri...</Btn></div></label>
            <label className="field"><span className="field-label">Haftalık Çalışma Gün Sayısı</span>
              <div className="inline"><select value={dayCount} onChange={(e) => changeDays(Number(e.target.value))}>{Array.from({ length: 7 }, (_, i) => <option key={i} value={i + 1}>{i + 1}</option>)}</select>
                <Btn type="button" onClick={() => setSub('days')}>Günler ve Tatil Seçimi...</Btn></div></label>
            <label className="field"><span className="field-label">Hafta Sonu Tatili</span><select value={weekend} onChange={(e) => changeWeekend(e.target.value)}>{WEEKEND.map((w) => <option key={w}>{w}</option>)}</select></label>
          </div>
          <div className="card">
            <label className="check"><input type="radio" checked={kurum === 'okul'} onChange={() => setKurum('okul')} /> Okul / Kolej / Kurs / Özel Öğretim</label>
            <label className="check"><input type="radio" checked={kurum === 'fakulte'} onChange={() => setKurum('fakulte')} /> Fakülte / Yüksek Okul / Üniversite</label>
            <label className="check"><input type="checkbox" checked={multi} onChange={(e) => setMulti(e.target.checked)} /> Çok Dönemli veya Çok Haftalı Program (Güz / Bahar)</label>
          </div>
          <p className="muted small">Gün ya da ders saati sayısını değiştirmek çizelgenin boyutunu değiştirir; yeni boyuta sığmayan yerleşimler motor tarafından yok sayılır.</p>
        </>
      )}
      {tab === 1 && (
        <div className="card grid2">
          <label className="field"><span className="field-label">Ülke Seçimi</span><select value={country} onChange={(e) => setCountry(e.target.value)}>{COUNTRIES.map((x) => <option key={x}>{x}</option>)}</select></label>
          <label className="field"><span className="field-label">Arayüz Dili</span><select value={lang} onChange={(e) => setLang(e.target.value)}>{LANGS.map((x) => <option key={x}>{x}</option>)}</select></label>
          <label className="field"><span className="field-label">Saat Dilimi / Zaman</span><select value={tz} onChange={(e) => setTz(e.target.value)}>{TZS.map((x) => <option key={x}>{x}</option>)}</select></label>
        </div>
      )}
      {tab === 2 && (
        <div className="card">
          <b>Çizelge Programlama Modeli</b>
          <div className="muted small" style={{ marginBottom: 8 }}>Kurumunuz için geçerli olan haftalık ders dağılım sistemini belirleyin.</div>
          <label className="check"><input type="radio" checked={model === 'standart'} onChange={() => setModel('standart')} /> Standart Tek Haftalık Çizelge (Haftalık Ders Dağılımı - Önerilen)</label>
          <label className="check"><input type="radio" checked={model === 'ab_haftalik'} onChange={() => setModel('ab_haftalik')} /> 2 Haftalık Dönüşümlü Çizelge (A Haftası / B Haftası Çift Sistem)</label>
          <label className="check"><input type="radio" checked={model === 'donemlik'} onChange={() => setModel('donemlik')} /> Dönemlik Modüler Çizelge (Güz Dönemi / Bahar Dönemi Ayrımı)</label>
        </div>
      )}
      {sub === 'days' && <DaysWindow dayCount={dayCount} onClose={() => setSub(null)} onSaved={(n) => { setDayCount(n); changeDays(n); setSub(null); }} />}
      {sub === 'bells' && <BellsWindow periods={periods} onClose={() => setSub(null)} />}
    </Window>
  );
}

/** DaysAndHolidaysDialog */
function DaysWindow({ dayCount, onClose, onSaved }: { dayCount: number; onClose: () => void; onSaved: (n: number) => void }) {
  const data = useApp((s) => s.data);
  const [on, setOn] = useState<boolean[]>(() => {
    const saved = data.settings?.active_days_list;
    if (Array.isArray(saved) && saved.length === 7) return DAYS_ALL.map((n) => { const x = saved.find((s: any) => s.name === n); return x ? (x.active ?? true) : false; });
    return DAYS_ALL.map((_, i) => i < (dayCount || 5));
  });
  const save = async () => {
    const n = on.filter(Boolean).length;
    if (!n) { await tell('Hata', 'Lütfen en az bir çalışma günü seçiniz!'); return; }
    mutate('Çalışma günleri', (d) => {
      const s = (d.settings ??= {});
      s.active_days_list = DAYS_ALL.map((name, i) => ({ day_index: i, name, active: on[i] }));
      s.days_count = n; s.day_count = n;
      s.days = DAYS_ALL.filter((_, i) => on[i]);
      d.gun_sayisi = n;
      if (n >= 7) s.weekend_option = 'Hafta Sonu Tatili Yok'; else if (n === 6) s.weekend_option = 'Yalnız Pazar'; else if (n === 5) s.weekend_option = 'Cumartesi - Pazar';
    });
    onSaved(n);
  };
  return (
    <Window title="Çalışma Günleri Ayarları" subtitle="Çizelgede ders planlaması yapılacak aktif günleri belirleyin." onClose={onClose} width={440}
      footer={<><span className="sp" /><Btn onClick={onClose}>İptal</Btn><Btn kind="primary" onClick={() => void save()}>Gün Ayarlarını Kaydet</Btn></>}>
      <div className="card" style={{ padding: 0 }}>
        {DAYS_ALL.map((n, i) => (
          <label key={n} className="day-row"><input type="checkbox" checked={on[i]} onChange={(e) => setOn((o) => o.map((x, j) => (j === i ? e.target.checked : x)))} />
            <span>{n}</span><span className="sp" /><span className={`tag ${i >= 5 ? 'we' : ''}`}>{i >= 5 ? 'Hafta Sonu' : 'Hafta İçi'}</span></label>
        ))}
      </div>
      <div className="toolbar">
        <span className="muted small">Hızlı Seçim:</span>
        {[5, 6, 7].map((c) => <Btn key={c} onClick={() => setOn(DAYS_ALL.map((_, i) => i < c))}>{c === 5 ? '5 Gün (Pzt - Cuma)' : c === 6 ? '6 Gün (+Cumartesi)' : '7 Gün (Tüm Hafta)'}</Btn>)}
      </div>
    </Window>
  );
}

const toMin = (t: string) => { const m = /^(\d{1,2}):(\d{2})$/.exec(t); return m ? Number(m[1]) * 60 + Number(m[2]) : NaN; };
const toHHMM = (m: number) => { const x = ((m % 1440) + 1440) % 1440; return `${String(Math.floor(x / 60)).padStart(2, '0')}:${String(x % 60).padStart(2, '0')}`; };
interface Bell { start: string; end: string; brk: number }

/** BellAndBreakTimesDialog */
function BellsWindow({ periods, onClose }: { periods: number; onClose: () => void }) {
  const data = useApp((s) => s.data);
  const P = Math.max(1, Math.min(16, periods));
  const [start, setStart] = useState('08:30');
  const [lesson, setLesson] = useState(40);
  const [brk, setBrk] = useState(10);
  const [lunchAfter, setLunchAfter] = useState(P >= 4 ? 4 : 0);
  const [lunch, setLunch] = useState(45);
  const calc = (s = start, l = lesson, b = brk, la = lunchAfter, lm = lunch): Bell[] => {
    let cur = toMin(s);
    if (!Number.isFinite(cur)) cur = 510;
    const out: Bell[] = [];
    for (let i = 0; i < P; i++) {
      const end = cur + l;
      let bb: number;
      if (i === P - 1) bb = 0; else if (la > 0 && i + 1 === la) bb = lm; else bb = b;
      out.push({ start: toHHMM(cur), end: toHHMM(end), brk: bb });
      cur = end + bb;
    }
    return out;
  };
  const [rows, setRows] = useState<Bell[]>(() => {
    const st = data.settings ?? {};
    const saved = st.bell_schedule || data.bell_schedule || data.bell_times || st.bell_times || st.zil_saatleri || data.zil_saatleri;
    if (Array.isArray(saved) && saved.length >= P) return saved.slice(0, P).map((x: any) => ({ start: x?.start ?? '08:30', end: x?.end ?? '09:10', brk: Number(x?.break_duration ?? 10) }));
    return calc();
  });
  const recalc = (patch: Partial<{ s: string; l: number; b: number; la: number; lm: number }>) => {
    const s = patch.s ?? start, l = patch.l ?? lesson, b = patch.b ?? brk, la = patch.la ?? lunchAfter, lm = patch.lm ?? lunch;
    if (patch.s !== undefined) setStart(s);
    if (patch.l !== undefined) setLesson(l);
    if (patch.b !== undefined) setBrk(b);
    if (patch.la !== undefined) setLunchAfter(la);
    if (patch.lm !== undefined) setLunch(lm);
    setRows(calc(s, l, b, la, lm));
  };
  // _cascade_from: bir satır değişince sonraki satırlar, kendi sürelerini koruyarak kayar.
  const cascade = (rs: Bell[], from: number): Bell[] => {
    const out = rs.map((r) => ({ ...r }));
    for (let i = from; i + 1 < out.length; i++) {
      const e = toMin(out[i].end);
      if (!Number.isFinite(e)) break;
      const ns = e + out[i].brk;
      let nd = toMin(out[i + 1].end) - toMin(out[i + 1].start);
      if (!(nd > 0)) nd = 40;
      out[i + 1].start = toHHMM(ns);
      out[i + 1].end = toHHMM(ns + nd);
    }
    return out;
  };
  const setRow = (i: number, patch: Partial<Bell>) => setRows((rs) => {
    const next = rs.map((r, j) => (j === i ? { ...r, ...patch } : r));
    const d = toMin(next[i].end) - toMin(next[i].start);
    return d > 0 ? cascade(next, i) : next;
  });
  const save = async () => {
    const schedule: { period: number; start: string; end: string; duration: number; break_duration: number }[] = [];
    for (let i = 0; i < P; i++) {
      const dur = toMin(rows[i].end) - toMin(rows[i].start);
      if (!(dur > 0)) { await tell('Hata', `${i + 1}. Dersin bitiş saati başlangıç saatinden önce veya eşit olamaz!`); return; }
      schedule.push({ period: i + 1, start: rows[i].start, end: rows[i].end, duration: dur, break_duration: rows[i].brk });
    }
    mutate('Zil ve teneffüs saatleri', (d) => {
      const s = (d.settings ??= {});
      s.bell_schedule = schedule; s.bell_times = schedule; s.zil_saatleri = schedule;
      d.bell_schedule = schedule; d.bell_times = schedule; d.zil_saatleri = schedule;
      d.zil_programi = Object.fromEntries(schedule.map((x) => [String(x.period - 1), x]));
    });
    onClose();
  };
  return (
    <Window title="Zil ve Teneffüs Saatleri Ayarları" onClose={onClose} width={820}
      footer={<><Btn onClick={() => recalc({ s: '08:30', l: 40, b: 10, la: P >= 4 ? 4 : 0, lm: 45 })}>Standart MEB Şablonu</Btn>
        <Btn onClick={() => recalc({ s: '09:00', l: 45, b: 15, la: P >= 4 ? 4 : 0, lm: 40 })}>Kurs / Özel Öğretim Şablonu</Btn>
        <span className="sp" /><Btn onClick={onClose}>İptal</Btn><Btn kind="primary" onClick={() => void save()}>Zil ve Teneffüsleri Kaydet</Btn></>}>
      <div className="card">
        <div className="card-title">Hızlı Otomatik Doldurma ve Hesaplama</div>
        <div className="bell-wiz">
          <label>1. Ders Başlangıcı <input type="time" value={start} onChange={(e) => setStart(e.target.value)} /></label>
          <label>Ders Süresi (dk) <input type="number" min={20} max={90} value={lesson} onChange={(e) => recalc({ l: Math.max(20, Math.min(90, Number(e.target.value) || 40)) })} /></label>
          <label>Standart Teneffüs (dk) <input type="number" min={0} max={60} value={brk} onChange={(e) => recalc({ b: Math.max(0, Math.min(60, Number(e.target.value) || 0)) })} /></label>
          <label>Öğle Arası Saati <select value={lunchAfter} onChange={(e) => recalc({ la: Number(e.target.value) })}><option value={0}>Öğle Arası Yok</option>{Array.from({ length: Math.max(0, P - 1) }, (_, i) => <option key={i} value={i + 1}>{i + 1}. Ders Sonrası</option>)}</select></label>
          <label>Öğle Arası Süresi (dk) <input type="number" min={15} max={120} value={lunch} onChange={(e) => recalc({ lm: Math.max(15, Math.min(120, Number(e.target.value) || 45)) })} /></label>
          <Btn kind="primary" onClick={() => recalc({})}>Tüm Saatleri Otomatik Hesapla</Btn>
        </div>
      </div>
      <div className="dtable-wrap" style={{ maxHeight: '42vh' }}>
        <table className="dtable">
          <thead><tr><th>Ders No</th><th>Başlangıç Saati</th><th>Bitiş Saati</th><th>Ders Süresi</th><th>Sonraki Teneffüs (dk)</th></tr></thead>
          <tbody>
            {rows.map((r, i) => {
              const dur = toMin(r.end) - toMin(r.start);
              return (
                <tr key={i}>
                  <td>{i + 1}. Ders</td>
                  <td><input type="time" value={r.start} onChange={(e) => setRow(i, { start: e.target.value })} /></td>
                  <td><input type="time" value={r.end} onChange={(e) => setRow(i, { end: e.target.value })} /></td>
                  <td className={dur > 0 ? 'txt-acc' : 'txt-bad'}>{dur > 0 ? `${dur} dk` : 'Geçersiz'}</td>
                  <td><input type="number" min={0} max={120} value={r.brk} onChange={(e) => setRow(i, { brk: Math.max(0, Math.min(120, Number(e.target.value) || 0)) })} style={{ width: 80 }} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Window>
  );
}
