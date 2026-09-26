// main_window._build_ribbon — tek şerit (Ana Menü) + "Diğer" sayfası.
import { useState } from 'react';
import { hourTotals } from '../model.ts';
import { ask, getState, mutate, openScreen, redo, setState, status, tell, undo, useApp } from '../store.ts';
import { saveVersion } from '../versions.ts';
import { Icon } from '../ui.tsx';

function RB({ icon, label, onClick, disabled, title }: { icon: string; label: string; onClick: () => void; disabled?: boolean; title?: string }) {
  return (
    <button className="rb" onClick={onClick} disabled={disabled} title={title ?? label.replace('\n', ' ')}>
      <Icon name={icon} size={22} />
      <span>{label.split('\n').map((l, i) => <span key={i}>{l}</span>)}</span>
    </button>
  );
}
const Sep = () => <span className="rsep" />;

const ZOOMS = [0.85, 1, 1.25, 1.5];

export function Ribbon({ onOpen, onClose }: { onOpen: () => void; onClose: () => void }) {
  const data = useApp((s) => s.data);
  const name = useApp((s) => s.name);
  const view = useApp((s) => s.view);
  const canUndo = useApp((s) => s.undo.length > 0);
  const canRedo = useApp((s) => s.redo.length > 0);
  const lastUndo = useApp((s) => s.undo[s.undo.length - 1]?.label);
  const savedAt = useApp((s) => s.savedAt);
  const [page, setPage] = useState<0 | 1>(0);
  const has = !!data;
  const { assigned, placed } = data ? hourTotals(data) : { assigned: 0, placed: 0 };
  const hasEntities = !!data && ['dersler', 'ogretmenler', 'derslikler', 'siniflar', 'atamalar'].some((k) => (data[k] ?? []).length > 0);
  const need = (fn: () => void) => () => { if (!getState().data) void tell('Açık çizelge yok', 'Önce bir çizelge açın ya da yeni bir kurum oluşturun.'); else fn(); };

  const actNew = () => {
    if (hasEntities) {
      void tell('Yeni Sihirbaz Devre Dışı', 'Bu kurumda halihazırda mevcut dersler, öğretmenler veya sınıflar bulunmaktadır.\nSıfırdan sihirbaz çalıştırmak yerine üst menüdeki Dersler, Sınıflar ve Öğretmenler sekmelerini kullanabilirsiniz.');
      return;
    }
    openScreen({ kind: 'newSchedule', inst: getState().inst?.slug });
  };
  const actImprove = () => {
    const n = (getState().data?.grid_placements ?? []).length;
    if (!n) { void tell('İyileştirme', "Çizelge boş. Önce 'Otomatik Planlamayı Başlat' ile bir çizelge oluşturun."); return; }
    setState({ plannerOpen: true });
  };
  const actViewMode = () => {
    const order: ('classes' | 'teachers')[] = ['classes', 'teachers'];
    const nxt = order[(order.indexOf(getState().view as any) + 1) % order.length];
    setState({ view: nxt, selectedRow: null });
    status(`Görünüm: ${nxt === 'classes' ? 'Sınıflar' : 'Öğretmenler'}`);
  };
  const actZoom = () => {
    const cur = getState().zoom;
    const i = ZOOMS.indexOf(cur);
    const nxt = ZOOMS[(i + 1) % ZOOMS.length] ?? 1;
    setState({ zoom: nxt });
    status(`Yakınlaştırma: %${Math.round(nxt * 100)}`);
  };
  // main_window._act_week — A/B hafta düzeni (yalnızca ayar; motor okumaz).
  const actWeek = async () => {
    const st = getState().data?.settings ?? {};
    if (!st.uses_ab_weeks) {
      if (!(await ask({ title: 'A/B Hafta Düzeni', body: 'Bu kurum için A/B haftası tanımlı değil.\n\nÇift haftalık (A/B) düzeni açılsın mı?\nAçıldığında dersleri A haftası, B haftası veya her hafta olarak işaretleyebilirsiniz.', ok: 'Aç', cancel: 'Vazgeç' }))) return;
      mutate('A/B hafta düzeni', (d) => { d.settings ??= {}; d.settings.uses_ab_weeks = true; d.settings.current_week = 'A'; });
      status('A/B hafta düzeni açıldı. Şu an: A haftası');
      return;
    }
    const nxt = (st.current_week ?? 'A') === 'A' ? 'B' : 'A';
    mutate(`${nxt} haftası`, (d) => { d.settings.current_week = nxt; });
    status(`${nxt} haftası gösteriliyor`);
  };
  const actSupport = () => void tell('Teknik Destek', 'Chenkron Ders Planlama — Web\n\nDestek: destek@chenki.net\n\nBir sorun bildirirken yaptığınız son işlemi belirtmeniz çözümü hızlandırır.');

  return (
    <header className="ribbon">
      <div className="titlebar">
        <span className="brand">Chenkron</span>
        <span className="inst" title={name}>{name || 'Çizelge açık değil'}</span>
        <span className="sp" />
        {has && (
          <span className="seg" role="tablist" aria-label="Görünüm">
            <button className={view === 'classes' ? 'on' : ''} onClick={() => setState({ view: 'classes', selectedRow: null })}>Sınıflar</button>
            <button className={view === 'teachers' ? 'on' : ''} onClick={() => setState({ view: 'teachers', selectedRow: null })}>Öğretmenler</button>
          </span>
        )}
        {has && <span className="stat" title="Yerleşen / atanan ders saati"><b>{placed}</b>/{assigned} saat</span>}
        {savedAt && <span className="saved" title="Her değişiklik bu tarayıcıya otomatik kaydedilir.">Kaydedildi</span>}
      </div>
      <div className="rpages">
        <div className="rtrack" style={{ transform: `translateX(${page === 0 ? '0' : '-50%'})` }}>
          <div className="rpage" aria-hidden={page !== 0}>
            <RB icon="home" label="Anasayfa" onClick={() => openScreen({ kind: 'home' })} />
            <RB icon="file" label="Yeni" onClick={actNew} title={hasEntities ? 'Kurumda mevcut veriler/dersler bulunduğu için yeni sihirbaz devre dışıdır.' : 'Yeni Kurum Sihirbazı'} />
            <RB icon="open" label="Aç" onClick={onOpen} />
            <RB icon="save" label="Kaydet" onClick={need(() => void saveVersion())} disabled={!has} />
            <RB icon="undo" label={'Geri Al\nCtrl+Z'} onClick={undo} disabled={!canUndo} title={lastUndo ? `Geri al: ${lastUndo}` : 'Geri Al'} />
            <RB icon="redo" label={'Yinele\nCtrl+Y'} onClick={redo} disabled={!canRedo} />
            <RB icon="print" label="Yazdır" onClick={need(() => openScreen({ kind: 'print', preset: { direct: true } }))} disabled={!has} />
            <RB icon="eye" label="Önizleme" onClick={need(() => openScreen({ kind: 'print' }))} disabled={!has} />
            <Sep />
            <RB icon="book" label="Dersler" onClick={need(() => openScreen({ kind: 'master', tab: 0 }))} disabled={!has} />
            <RB icon="users" label="Sınıflar" onClick={need(() => openScreen({ kind: 'master', tab: 1 }))} disabled={!has} />
            <RB icon="door" label="Derslikler" onClick={need(() => openScreen({ kind: 'master', tab: 2 }))} disabled={!has} />
            <RB icon="teacher" label="Öğretmen" onClick={need(() => openScreen({ kind: 'master', tab: 3 }))} disabled={!has} />
            <RB icon="choice" label="Seçmeli" onClick={need(() => openScreen({ kind: 'electives' }))} disabled={!has} />
            <RB icon="link" label={'Planlama\nİlişkileri'} onClick={need(() => openScreen({ kind: 'relations' }))} disabled={!has} />
            <Sep />
            <RB icon="check" label={'Ön\nKontrol'} onClick={need(() => openScreen({ kind: 'precheck' }))} disabled={!has} />
            <RB icon="magic" label={'Otomatik\nPlanla'} onClick={need(() => setState({ plannerOpen: true }))} disabled={!has} />
            <RB icon="cloud" label={'Bulut\nPlanlama'} onClick={() => void tell('Bulut Tabanlı Planlama', 'Planlama motoru zaten bu tarayıcıda, sizin bilgisayarınızda çalışıyor; veriniz hiçbir sunucuya gönderilmez.')} />
            <RB icon="check" label={'Son\nKontrol'} onClick={need(() => openScreen({ kind: 'verify' }))} disabled={!has} />
            <RB icon="trash" label={'Çizelgeyi\nSıfırla'} onClick={need(() => setState({ resetOpen: true }))} disabled={!has} />
            <Sep />
            <RB icon="school" label={'Temel\nBilgiler'} onClick={need(() => openScreen({ kind: 'school' }))} disabled={!has} />
            <RB icon="cloud" label="Hesabım" onClick={() => window.open('https://chenki.net/', '_blank', 'noopener')} />
            <RB icon="help" label="Yardım" onClick={() => openScreen({ kind: 'faq' })} />
            <RB icon="grid" label="Diğer" onClick={() => setPage(1)} />
          </div>
          <div className="rpage" aria-hidden={page !== 1}>
            <RB icon="undo" label="Geri" onClick={() => setPage(0)} />
            <RB icon="x" label="Kapat" onClick={need(onClose)} disabled={!has} />
            <RB icon="school" label={'Demo\nDosyaları'} onClick={() => openScreen({ kind: 'home' })} />
            <RB icon="export" label="Aktar" onClick={need(() => openScreen({ kind: 'export' }))} disabled={!has} />
            <RB icon="compare" label="Karşılaştırma" onClick={need(() => openScreen({ kind: 'compare' }))} disabled={!has} />
            <RB icon="mail" label={'E-Mail\nGönder'} onClick={need(() => openScreen({ kind: 'export', mail: true }))} disabled={!has} />
            <Sep />
            <RB icon="magic" label="Sihirbaz" onClick={actNew} />
            <RB icon="list" label={'Toplu Atama\nListesi'} onClick={need(() => openScreen({ kind: 'assignmentList' }))} disabled={!has} />
            <RB icon="hash" label={'Tanımlanan\nKısıtlamalar'} onClick={need(() => openScreen({ kind: 'constraints', target: 'ogretmen' }))} disabled={!has} />
            <RB icon="settings" label="Değiştir" onClick={need(() => openScreen({ kind: 'school' }))} disabled={!has} />
            <Sep />
            <RB icon="magic" label={'İyileştirme\nUygula'} onClick={need(actImprove)} disabled={!has} />
            <RB icon="chart" label={'Analiz /\nİstatistik'} onClick={need(() => openScreen({ kind: 'statistics' }))} disabled={!has} />
            <RB icon="bulb" label="Danışman" onClick={need(() => openScreen({ kind: 'advisor' }))} disabled={!has} />
            <RB icon="rooms" label={'Dersliklere\nAtama'} onClick={need(() => openScreen({ kind: 'rooms' }))} disabled={!has} />
            <Sep />
            <RB icon="grid" label="Görünüm" onClick={need(actViewMode)} disabled={!has} />
            <RB icon="zoom" label="Yakınlaştır" onClick={need(actZoom)} disabled={!has} />
            <RB icon="week" label="Hafta" onClick={need(() => void actWeek())} disabled={!has} />
            <Sep />
            <RB icon="help" label={'Tanıtım ve\nÖğrenme'} onClick={() => openScreen({ kind: 'faq' })} />
            <RB icon="bulb" label={'Günlük\nİpucu'} onClick={() => openScreen({ kind: 'tips' })} />
            <RB icon="help" label={'Teknik\nDestek'} onClick={actSupport} />
            <RB icon="cloud" label={'Online\nYardım'} onClick={() => window.open('https://chenki.net/', '_blank', 'noopener')} />
          </div>
        </div>
      </div>
    </header>
  );
}
