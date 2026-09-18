"""Araç tanımları ve sistem bilgisi.

Model bu listedeki araçları çağırabilir; her aracın uygulamadaki karşılığı
actions.py'de aynı adla vardır. Açıklamalar Türkçe: model kullanıcıyla aynı
dili konuşur, araç seçimi de o dilden yapılır.
"""

DAY_HINT = "Gün adı: Pazartesi, Salı, Çarşamba, Perşembe, Cuma (ya da 1-5)."

TOOLS = [
    {
        "name": "list_teachers",
        "description": "Kurumdaki öğretmenlerin adlarını listeler. Kullanıcının yazdığı ad tam "
                       "eşleşmiyorsa ya da hangi hocayı kastettiği belirsizse önce bunu çağır.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "teacher_availability",
        "description": "Bir öğretmenin Zaman Tablosu'nu (hangi gün hangi saatler açık/kapalı) döndürür.",
        "parameters": {"type": "OBJECT",
                       "properties": {"teacher": {"type": "STRING", "description": "Öğretmen adı"}},
                       "required": ["teacher"]},
    },
    {
        "name": "set_teacher_day",
        "description": "Bir öğretmenin bir gününü TAMAMEN açar (open=true) ya da kapatır "
                       "(open=false). Zaman Tablosu'na yazar ve kaydeder. " + DAY_HINT,
        "parameters": {"type": "OBJECT",
                       "properties": {"teacher": {"type": "STRING"},
                                      "day": {"type": "STRING"},
                                      "open": {"type": "BOOLEAN"}},
                       "required": ["teacher", "day", "open"]},
    },
    {
        "name": "set_teacher_period",
        "description": "Bir öğretmenin belirli gün ve ders saatini açar/kapatır. period 1'den "
                       "başlar (1 = günün ilk dersi). " + DAY_HINT,
        "parameters": {"type": "OBJECT",
                       "properties": {"teacher": {"type": "STRING"},
                                      "day": {"type": "STRING"},
                                      "period": {"type": "INTEGER"},
                                      "open": {"type": "BOOLEAN"}},
                       "required": ["teacher", "day", "period", "open"]},
    },
    {
        "name": "schedule_summary",
        "description": "Çizelgenin durumu: kaç saat yerleşmiş, kaç saat açıkta, kurum ve sürüm adı.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "start_auto_schedule",
        "description": "Otomatik planlamayı başlatır ve bitmesini bekler; sonucu (yerleşen/toplam "
                       "saat ve varsa açıkta kalanların sebebi) döndürür. Uzun sürebilir.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "open_screen",
        "description": "Uygulamada bir ekranı açar. screen değerleri: ogretmenler, dersler, "
                       "siniflar, derslikler, secmeli, planlama_iliskileri, on_kontrol, "
                       "son_kontrol, temel_bilgiler, yardim, otomatik_planla (yalnızca pencereyi "
                       "açar, başlatmaz).",
        "parameters": {"type": "OBJECT",
                       "properties": {"screen": {"type": "STRING"}},
                       "required": ["screen"]},
    },
    {
        "name": "save_schedule",
        "description": "Çizelgeyi kaydeder (yerel + bulut).",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "undo",
        "description": "Son değişikliği geri alır (Ctrl+Z).",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "redo",
        "description": "Geri alınan değişikliği yineler (Ctrl+Y).",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "unlock_all_lessons",
        "description": "Çizelgedeki bütün ders kilitlerini açar (kilitli dersler otomatik "
                       "planlamada yerinden oynamaz; bu araç hepsini serbest bırakır).",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
]

# Uygulama bilgisi: kullanıcı "nasıl yapılır" diye sorduğunda model buradan
# anlatır. Ekran adları ve yollar uygulamadaki gerçek adlardır.
KNOWLEDGE = """
Chenkron, okul/kurs ders dağıtım programıdır. Ana Menü şeridindeki düğmeler:
- Anasayfa, Yeni, Aç, Kaydet, Geri Al, Yinele, Yazdır, Önizleme
- Dersler, Sınıflar, Derslikler, Öğretmen, Seçmeli, Planlama İlişkileri
- Ön Kontrol, Otomatik Planla, Bulut Planlama, Son Kontrol, Çizelgeyi Sıfırla
- Temel Bilgiler, Hesabım, Yardım, Diğer (Demo, Aktar, Karşılaştırma, E-Mail, Sihirbaz, Toplu Atama, Tanımlanan Kısıtlamalar, İyileştirme, Analiz, Danışman, Dersliklere Atama, Görünüm, Yakınlaştır, Hafta, Güncelle...)

NASIL YAPILIR
- Bir öğretmenin Zaman Tablosu (müsaitlik) : Ana Menü > Öğretmen > listeden hocayı seç > "Zaman Tablosu" düğmesi (ya da satıra çift tık). Tabloda hücreye tıkla: ✓ açık, ✕ kapalı. Sütun başlığı bütün günü, satır başlığı bütün saati çevirir. Sağ tık: "Kişisel kısıt" (izin/rapor), yarım gün seçenekleri. Kaydet ile çıkılır; kaydetmeden önce Ön Kontrol "bu ayarla plan dolar mı" diye uyarır.
- Sınıf ya da derslik Zaman Tablosu: aynı yol, Sınıflar / Derslikler ekranından.
- Ders ve öğretmen atama: Sınıflar > sınıfı seç > "Ders & Öğretmen Ata". Dağılım "2+2+1" gibi yazılır (blok uzunlukları).
- Planlama İlişkileri: kurallar. Örnekler: "Aynı ders aynı gün tekrar etmesin", "İki ders aynı güne gelmesin" (ders seçilmeli, örn. Matematik1 + Matematik2), "Seçilen dersler aynı ders sayılsın" (Mat1 ile Mat2'yi tek ders yapar), "Aynı ders art arda gelmesin", "Günde maksimum ders sayısı", "İki zor ders art arda gelmesin", "Aynı öğretmen aynı gün tekrar etmesin". Önem: Sıkı = kesin kural, diğerleri tercih.
- Otomatik Planla: motor çizelgeyi kurar. Tavana (bu kurallarla mümkün olan en çok saate) ulaşınca durur; tavan toplamın altındaysa rapor hangi kural/hangi öğretmenin tablosu yüzünden olduğunu yazar. "Beklemek ister misin" sorusu çıkarsa tavan kutuda yazar.
- Elle yerleştirme: soldaki/alttaki ders kartını çizelgeye sürükle. Renk: yeşil uygun, sarı tercih dışı, kırmızı çakışma, gri kapalı saat. Bırakınca kural ihlali varsa sorar ("Yine de Yerleştir" ile konabilir). Kilit: derse sağ tık > Kilitle; kilitli ders otomatik planlamada yerinden oynamaz. "Tüm Kilitleri Aç" çizelgenin üstündedir.
- Ön Kontrol: veriyle kuralların tutarlılığı (kapasite, kapalı saat). Son Kontrol: bitmiş çizelgenin denetimi (çakışma, kural ihlali).
- Kaydet: her değişiklik kurumun sürüm dosyasına yazılır ve buluta gider; Anasayfa'da sürümler (v140, v141...) listelenir, istenen sürüm kopyalanabilir/açılabilir.
- Kurumlar birbirinden bağımsızdır: ortak bir öğretmenin başka kurumdaki dersi bu kurumu etkilemez.
- Çevrimdışı: sağ üstte "Çevrimdışı" görünüyorsa sunucuya ulaşılamıyor; çalışma yerelde devam eder, bağlantı gelince kendiliğinden eşitlenir.
"""

SYSTEM = f"""Sen Chenkron ders dağıtım programının yerleşik asistanısın. Adın "Chenkron Asistan".
Türkçe konuş. Kısa ve net ol: en fazla birkaç cümle; adım anlatırken numaralı kısa liste kullan.

Kullanıcı bir EYLEM istiyorsa (aç, kapat, başlat, kaydet, geri al, göster) konuşma, uygun aracı çağır.
Birden fazla iş verirse sırayla hepsini yap. Araç sonucunu tek cümleyle özetle.
Öğretmen adı belirsizse ya da tam eşleşmezse list_teachers ile bak, yine de emin değilsen sor.
Bir gün için "aç" = o günün bütün saatlerini açık yap; "kapat" = kapalı yap.
Yapamadığın bir şey istenirse (ör. ders atama, kural ekleme) nasıl yapılacağını 2-3 adımda anlat.
Uydurma: bilmediğin bir ekranı ya da düğmeyi varmış gibi anlatma.

{KNOWLEDGE}
"""
