// dialogs/export_dialog.py (Aktar — Excel / CSV) ve main_window._act_email.
import { useMemo, useState } from 'react';
import { EXPORT_KINDS, buildSheet, downloadBlob, exportFile } from '../exporters.ts';
import { closeScreen, tell, useApp } from '../store.ts';
import { Btn, Window } from '../ui.tsx';

function baseName(d: any): string {
  const b = d.settings?.school_name;
  return b ? [...String(b)].filter((c) => /[\p{L}\p{N} _-]/u.test(c)).join('').trim().replace(/ /g, '_') || 'ders_programi' : 'ders_programi';
}

export function ExportScreen({ mail }: { mail?: boolean }) {
  const data = useApp((s) => s.data);
  const counts = useMemo(() => Object.fromEntries(EXPORT_KINDS.map(([k]) => { try { return [k, buildSheet(data, k)[2].length]; } catch { return [k, 0]; } })), [data]);
  const [on, setOn] = useState<Record<string, boolean>>(() => Object.fromEntries(EXPORT_KINDS.map(([k]) => [k, mail ? ['timetable_classes', 'timetable_teachers', 'lessons'].includes(k) && counts[k] > 0 : counts[k] > 0 && k.startsWith('timetable_classes')])));
  const [xlsx, setXlsx] = useState(true);

  const run = async () => {
    const kinds = EXPORT_KINDS.map(([k]) => k).filter((k) => on[k] && counts[k] > 0);
    if (!kinds.length) { await tell('Seçim Yok', 'En az bir bölüm seçmelisiniz.'); return; }
    const { blob, ext } = exportFile(data, kinds, xlsx);
    const name = baseName(data) + ext;
    downloadBlob(blob, name);
    if (mail) {
      const inst = data.settings?.school_name || data.okul_adi || 'Kurum';
      const subject = encodeURIComponent(`${inst} — Ders Programı`);
      const body = encodeURIComponent(`Ders programı ektedir.\n\nDosya: ${name}\n\n(E-posta programınız eki otomatik almadıysa indirilen dosyayı ekleyin.)`);
      window.location.href = `mailto:?subject=${subject}&body=${body}`;
      await tell('E-Mail Gönder', `Çizelge dışa aktarıldı: ${name} (${Math.round(blob.size / 1024)} KB) indirildi.\n\nE-posta programınız açıldı; dosyayı ek olarak eklemeniz yeterli.`);
    } else {
      const note = !xlsx && kinds.length > 1 ? '\n\nNot: CSV tek tablo tuttuğu için yalnızca ilk bölüm yazıldı.' : '';
      await tell('Dışa Aktarıldı', `${name} (${Math.max(1, Math.round(blob.size / 1024))} KB) indirildi.${note}`);
    }
    closeScreen();
  };

  return (
    <Window title={mail ? 'E-Mail Gönder' : 'Aktar — Excel / CSV'} onClose={closeScreen} width={560}
      footer={<><span className="sp" /><Btn onClick={closeScreen}>Vazgeç</Btn><Btn kind="primary" onClick={() => void run()}>{mail ? 'Aktar ve E-posta Aç' : 'Kaydet...'}</Btn></>}>
      <b>Dışa aktarılacak bölümleri seçin</b>
      <div className="card" style={{ marginTop: 8 }}>
        {EXPORT_KINDS.map(([k, label]) => (
          <label key={k} className={`check${counts[k] ? '' : ' muted'}`}>
            <input type="checkbox" disabled={!counts[k]} checked={!!on[k] && counts[k] > 0} onChange={(e) => setOn((o) => ({ ...o, [k]: e.target.checked }))} />
            {label}   ({counts[k]} satır)
          </label>
        ))}
      </div>
      <b>Biçim</b>
      <div className="card" style={{ marginTop: 8 }}>
        <label className="check"><input type="radio" checked={xlsx} onChange={() => setXlsx(true)} /> Excel (.xlsx) — tüm bölümler ayrı sayfalarda</label>
        <label className="check"><input type="radio" checked={!xlsx} onChange={() => setXlsx(false)} /> CSV (.csv) — tek bölüm, Excel ile uyumlu</label>
        <div className="muted small"><i>CSV tek bir tablo tutabildiği için, seçtiğiniz ilk bölüm yazılır.</i></div>
      </div>
    </Window>
  );
}
