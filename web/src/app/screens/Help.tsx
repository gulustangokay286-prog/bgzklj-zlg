// dialogs/faq_dialog.py (Sıkça Sorulan Sorular) ve main_window._act_tip_of_day.
import { useState } from 'react';
import { closeScreen } from '../store.ts';
import { Btn, Window } from '../ui.tsx';

const CATS = ['Tümü', 'Otomatik Planlama', 'Ders & Sınıf', 'Kısıtlamalar & Ayarlar', 'Yazdırma & Kayıt'];
const FAQ: { cat: string; q: string; a: string }[] = [
  { cat: 'Otomatik Planlama', q: 'Elle yerleştirdiğim dersler otomatik planlama sırasında silinir mi?', a: 'Kilitlediğiniz dersler yerinde kalır; motor onların üzerine ders yazmaz ve yerlerini değiştirmez. Kilitsiz dersler yeniden yerleştirilir. Bir dersi korumak için çizelgede sağ tıklayıp kilitleyin.' },
  { cat: 'Otomatik Planlama', q: 'Otomatik planlama nasıl %100 doluluk sağlar?', a: 'Motor önce kısa bir hızlı aramayla başlar, sonra matematiksel bir çözücüyle (CP-SAT) mümkün olan en dolu çizelgeyi arar. Kapalı saatleri ve kuralları asla kendiliğinden açmaz; tam doluluk mümkün değilse kaç saatin neden yerleşemeyeceğini sayılarla söyler.' },
  { cat: 'Otomatik Planlama', q: 'Motor nerede çalışıyor, verim bir yere gidiyor mu?', a: 'Planlama motoru bu bilgisayarda, tarayıcının içinde çalışır. Veriniz hiçbir sunucuya gönderilmez; tarayıcıda saklanır.' },
  { cat: 'Ders & Sınıf', q: 'Ders kısaltmaları ve otomatik kod üretimi nasıl çalışır?', a: 'Ders adını girdiğinizde sistem otomatik olarak standart Türkçe kısaltma üretir (Örn: Biyoloji -> BİYO, Matematik 1 -> MATE 1, Rehberlik -> REHBERLİK). Numaralar harflerden her zaman bir boşlukla ayrı tutulur.' },
  { cat: 'Kısıtlamalar & Ayarlar', q: 'İki zor dersin aynı gün peş peşe gelmesi nasıl engellenir?', a: "Planlama İlişkileri ekranından 'İki zor ders art arda gelmesin' kuralını ekleyin. Motor bu kurala göre zor dersler arasına başka dersler yerleştirir." },
  { cat: 'Kısıtlamalar & Ayarlar', q: 'Günlük ders saatini 8 saatin üzerine nasıl çıkarabilirim?', a: "Ana Menü -> Temel Bilgiler ekranından 'Günlük Ders Saati' kutusundan istediğiniz saat sayısını (1-16) seçebilirsiniz. Çizelge ve yazdırma çıktıları buna göre ölçeklenir." },
  { cat: 'Ders & Sınıf', q: 'Bir öğretmene birden fazla ders ve farklı sınıflar nasıl atanır?', a: "Öğretmenler ekranında öğretmeni seçip 'Ders Atama'ya basın. Bir ders seçtiğinizde aşağıda otomatik yeni ders satırı açılır. Her dersin yanındaki 'Sınıf(lar) Ata...' düğmesiyle o ders için hangi sınıflara gireceğini bağımsız seçebilirsiniz." },
  { cat: 'Ders & Sınıf', q: 'Birleşik sınıflar (ortak ders) nedir ve nasıl tanımlanır?', a: "Bir öğretmenin aynı saatte birden fazla sınıfa ortak derse girmesidir (Örn: 9A + 9B Beden Eğitimi). Ders satırındaki 'Birleşik Sınıf...' düğmesiyle en az 2 sınıf seçin." },
  { cat: 'Ders & Sınıf', q: 'Ders rengini nasıl değiştirebilirim?', a: 'Dersler ekranında dersi açıp Renk Kodu bölümünden yeni rengi seçin. Değişiklik o dersin bütün kartlarına uygulanır.' },
  { cat: 'Yazdırma & Kayıt', q: 'Baskı ve PDF çıktıları nasıl alınır?', a: "Yazdır veya Önizleme düğmesiyle rapor türünü seçin (çarşaf, 6'lı çizelge, tekil çizelge, atama listesi, ders yükü). PDF için yazdırma penceresinde hedef olarak 'PDF olarak kaydet'i seçin." },
  { cat: 'Yazdırma & Kayıt', q: 'Çalışmam nereye kaydediliyor?', a: 'Her değişiklik bu tarayıcıya otomatik kaydedilir. Kaydet düğmesi kurumun sürüm listesine yeni bir sürüm ekler. Diğer > Aktar ile Excel/CSV, Anasayfa\'dan .roz dosyası olarak indirip masaüstü uygulamasında açabilirsiniz.' },
];

export function FaqScreen() {
  const [cat, setCat] = useState('Tümü');
  const [q, setQ] = useState('');
  const [open, setOpen] = useState<number | null>(null);
  const ql = q.trim().toLocaleLowerCase('tr');
  const items = FAQ.map((x, i) => ({ ...x, i })).filter((x) => (cat === 'Tümü' || x.cat === cat) && (!ql || x.q.toLocaleLowerCase('tr').includes(ql) || x.a.toLocaleLowerCase('tr').includes(ql)));
  return (
    <Window title="Sıkça Sorulan Sorular" onClose={closeScreen} width={720}
      footer={<><Btn onClick={() => window.open('https://chenki.net/', '_blank', 'noopener')}>Destek Portalı</Btn><span className="sp" /><Btn kind="primary" onClick={closeScreen}>Kapat</Btn></>}>
      <input placeholder="Soru ara..." value={q} onChange={(e) => setQ(e.target.value)} style={{ width: '100%', marginBottom: 8 }} />
      <div className="chips">{CATS.map((c) => <button key={c} className={cat === c ? 'on' : ''} onClick={() => setCat(c)}>{c}</button>)}</div>
      <div className="faq">
        {items.map((x) => (
          <div key={x.i} className={`faq-item${open === x.i ? ' open' : ''}`}>
            <button onClick={() => setOpen(open === x.i ? null : x.i)}><span className="muted small">{x.cat}</span><b>{x.q}</b><span className="chev">{open === x.i ? '−' : '+'}</span></button>
            {open === x.i && <p>{x.a}</p>}
          </div>
        ))}
        {!items.length && <p className="muted">Sonuç yok.</p>}
      </div>
    </Window>
  );
}

const TIPS = [
  'Bir dersi gridde başka bir dersin üzerine sürüklerseniz ikisi yer değiştirir; hiçbir ders silinmez.',
  'Zaman Tablosu ekranından bir sınıfın saatlerini kapatırsanız, otomatik planlayıcı oraya asla ders koymaz.',
  "Otomatik planlayıcı çalışmadan önce 'Planlama Öncesi Kontrol' size çizelgenin dolup dolamayacağını söyler.",
  'Yerleştirilemeyen dersler alttaki listeye düşer; oradan sürükleyerek elle yerleştirebilirsiniz.',
  'Bir öğretmene, sınıfların açık olduğu saat sayısından fazla ders atarsanız fazlası hiçbir şekilde yerleşemez.',
  'Aktar düğmesiyle çizelgeyi Excel veya CSV olarak dışa aktarabilirsiniz.',
  'Ctrl+Z ile son işlemi geri alabilirsiniz.',
];

export function TipsScreen() {
  const [i, setI] = useState(() => Math.floor(Math.random() * TIPS.length));
  return (
    <Window title="Günün İpucu" onClose={closeScreen} width={460}
      footer={<><Btn onClick={() => setI((i + 1) % TIPS.length)}>Başka bir ipucu</Btn><span className="sp" /><Btn kind="primary" onClick={closeScreen}>Tamam</Btn></>}>
      <p className="tip">{TIPS[i]}</p>
    </Window>
  );
}
