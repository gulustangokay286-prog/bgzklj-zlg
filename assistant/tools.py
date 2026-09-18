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


def _obj(props, required=()):
    return {"type": "OBJECT", "properties": props, "required": list(required)}

def _s(desc=""):
    return {"type": "STRING", "description": desc}

def _b(desc=""):
    return {"type": "BOOLEAN", "description": desc}

def _i(desc=""):
    return {"type": "INTEGER", "description": desc}

def _arr(desc=""):
    return {"type": "ARRAY", "items": {"type": "STRING"}, "description": desc}

TOOLS += [
    # ── okuma ──
    {"name": "list_classes", "description": "Sınıfları listeler.", "parameters": _obj({})},
    {"name": "list_subjects", "description": "Dersleri listeler.", "parameters": _obj({})},
    {"name": "list_assignments",
     "description": "Ders atamalarını (sınıf, ders, öğretmen, saat, dağılım) listeler; sınıf ya da öğretmenle süzülebilir.",
     "parameters": _obj({"class_name": _s("isteğe bağlı"), "teacher": _s("isteğe bağlı")})},
    {"name": "teacher_schedule",
     "description": "Bir öğretmenin bu kurumdaki haftalık ders programı (gün gün hangi saatte hangi sınıf).",
     "parameters": _obj({"teacher": _s()}, ["teacher"])},
    {"name": "class_schedule",
     "description": "Bir sınıfın haftalık programı (gün gün ders ve öğretmen).",
     "parameters": _obj({"class_name": _s()}, ["class_name"])},
    {"name": "free_slots",
     "description": "Öğretmenin hem açık hem BOŞ saatleri (ders konabilecek yerler).",
     "parameters": _obj({"teacher": _s()}, ["teacher"])},
    {"name": "unplaced_lessons",
     "description": "Çizelgeye yerleşmemiş (açıkta kalan) dersler ve son planlama raporunun sebepleri.",
     "parameters": _obj({})},
    {"name": "list_rules", "description": "Planlama İlişkileri kurallarını numaralarıyla listeler.", "parameters": _obj({})},
    {"name": "precheck", "description": "Ön Kontrol: bu veri ve tablolarla çizelge dolar mı? Kapasite ve yük sorunlarını söyler.", "parameters": _obj({})},
    {"name": "verify_schedule", "description": "Son Kontrol: yerleşmiş çizelgede çakışma, kapalı saat ve kural ihlallerini bulur.", "parameters": _obj({})},
    # ── kurumlar arası (okuma) ──
    {"name": "list_institutions", "description": "Bu bilgisayardaki bütün kurumları (Birey, Boğaziçi...) ve aktif sürümlerini listeler.", "parameters": _obj({})},
    {"name": "institution_teacher_availability",
     "description": "BAŞKA bir kurumda bir öğretmenin hangi gün hangi saatlerinin kapalı olduğunu ve o kurumda hangi saatlerde dersi olduğunu söyler (o kurumun EN SON çizelgesinden; yalnızca okur).",
     "parameters": _obj({"institution": _s("kurum adı ya da kısaltması, örn. Birey"), "teacher": _s()}, ["institution", "teacher"])},
    {"name": "institution_info",
     "description": "BAŞKA bir kurumun EN SON çizelgesinden özet: kaç öğretmen, kaç sınıf, kaç ders, "
                    "kaç saat atanmış ve kaç saat yerleşmiş, hangi sürüm. Şu an açık olmayan bir kurum "
                    "hakkında SAYI sorulduğunda (ör. 'Birey'de kaç öğretmen var') BU aracı kullan; "
                    "list_teachers yalnızca açık olan kurumu bilir.",
     "parameters": _obj({"institution": _s()}, ["institution"])},
    {"name": "institution_teachers",
     "description": "BAŞKA bir kurumun en son çizelgesindeki öğretmenler: ad, branş, atanmış ders saati.",
     "parameters": _obj({"institution": _s()}, ["institution"])},
    {"name": "institution_classes",
     "description": "BAŞKA bir kurumun en son çizelgesindeki sınıflar.",
     "parameters": _obj({"institution": _s()}, ["institution"])},
    {"name": "institution_teacher_schedule",
     "description": "Bir öğretmenin BAŞKA kurumdaki haftalık ders programı: gün gün hangi saatte hangi ders ve sınıf.",
     "parameters": _obj({"institution": _s(), "teacher": _s()}, ["institution", "teacher"])},
    # ── yazma ──
    {"name": "clear_schedule",
     "description": "Çizelgeyi sıfırlar: bütün yerleşmiş dersleri kaldırır. Kullanıcı istediyse doğrudan "
                    "yap, ayrıca onay sorma — işlem Ctrl+Z ile geri alınabilir.",
     "parameters": _obj({})},
    {"name": "set_class_day", "description": "Bir sınıfın bir gününü tamamen açar/kapatır (sınıf Zaman Tablosu). " + DAY_HINT,
     "parameters": _obj({"class_name": _s(), "day": _s(), "open": _b()}, ["class_name", "day", "open"])},
    {"name": "set_class_period", "description": "Bir sınıfın belirli gün ve saatini açar/kapatır. period 1'den başlar.",
     "parameters": _obj({"class_name": _s(), "day": _s(), "period": _i(), "open": _b()}, ["class_name", "day", "period", "open"])},
    {"name": "add_rule",
     "description": "Planlama İlişkileri'ne kural ekler. kind: ayni_ders_ayni_gun, iki_ders_ayni_gune_gelmesin (en az 2 ders), "
                    "ayni_ders_sayilsin (en az 2 ders), ayni_ders_art_arda_gelmesin, iki_zor_ders_art_arda, gunde_maksimum_ders (param), "
                    "ayni_ogretmen_ayni_gun, ogretmen_haftada_en_fazla_n_gun (param), sinif_gunde_en_fazla_n_saat (param), "
                    "ogretmen_gunde_en_fazla_n_saat (param), sinifta_bos_saat_kalmasin, ogretmende_bos_saat_kalmasin, "
                    "ders_ogleden_once, ders_ogleden_sonra, son_derse_zor_ders_konulmasin, ilk_derse_konulmasin. "
                    "subjects/classes/teachers boşsa kural hepsine uygulanır. importance: sıkı | yüksek | normal.",
     "parameters": _obj({"kind": _s(), "subjects": _arr("ders adları"), "classes": _arr("sınıf adları"),
                         "teachers": _arr("öğretmen adları"), "importance": _s(), "param": _i("sayısal parametre")}, ["kind"])},
    {"name": "remove_rule", "description": "Kuralı numarasıyla siler (list_rules).", "parameters": _obj({"index": _i()}, ["index"])},
    {"name": "set_rule_active", "description": "Kuralı numarasıyla açar/kapatır.", "parameters": _obj({"index": _i(), "active": _b()}, ["index", "active"])},
    {"name": "add_assignment",
     "description": "Bir sınıfa ders ve öğretmen atar. distribution: blok dağılımı, örn. '2+2+1' (haftada 5 saat).",
     "parameters": _obj({"class_name": _s(), "subject": _s(), "teacher": _s(), "distribution": _s()},
                        ["class_name", "subject", "teacher", "distribution"])},
    {"name": "remove_assignment", "description": "Bir sınıftaki bir dersin atamasını kaldırır.",
     "parameters": _obj({"class_name": _s(), "subject": _s()}, ["class_name", "subject"])},
    {"name": "add_subject", "description": "Yeni ders tanımlar.", "parameters": _obj({"name": _s(), "short": _s("kısa kod")}, ["name"])},
    {"name": "add_teacher", "description": "Yeni öğretmen ekler.", "parameters": _obj({"name": _s(), "branch": _s("branş")}, ["name"])},
    {"name": "move_lesson",
     "description": "Bir sınıfın yerleşmiş bir dersini (ilk bloğunu) verilen gün/saate taşır; çakışma varsa taşımaz ve sebebini söyler.",
     "parameters": _obj({"class_name": _s(), "subject": _s(), "day": _s(), "period": _i("1'den başlar"), "teacher": _s("isteğe bağlı")},
                        ["class_name", "subject", "day", "period"])},
    {"name": "lock_lesson", "description": "Bir sınıfın bir dersinin bütün bloklarını kilitler/serbest bırakır (kilitli ders planlamada oynamaz).",
     "parameters": _obj({"class_name": _s(), "subject": _s(), "locked": _b()}, ["class_name", "subject", "locked"])},
    {"name": "remove_lesson_from_grid", "description": "Bir sınıfın bir dersini çizelgeden alır (açıkta kalan derslere düşer).",
     "parameters": _obj({"class_name": _s(), "subject": _s()}, ["class_name", "subject"])},
    {"name": "go_home", "description": "Anasayfaya (kurum ve sürüm listesi) döner.", "parameters": _obj({})},
    {"name": "print_preview", "description": "Yazdırma önizlemesini açar.", "parameters": _obj({})},
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

Kullanıcı bir EYLEM istiyorsa (aç, kapat, başlat, sıfırla, kaydet, geri al, taşı, ekle, sil, göster) konuşma, uygun aracı çağır.
Birden fazla iş verirse sırayla hepsini yap. Araç sonucunu tek cümleyle özetle; listeleri kısa ve okunur ver.
Öğretmen/sınıf/ders adı belirsizse ya da araç "bulunamadı" derse önce list_* araçlarıyla bak, yine de emin değilsen sor.
Bir gün için "aç" = o günün bütün saatlerini açık yap; "kapat" = kapalı yap.
ŞU AN AÇIK OLMAYAN bir kurum sorulduğunda (ör. "Birey'de kaç öğretmen var?", "Birey'de Ahmet hocanın
hangi saatleri kapalı?") mutlaka institution_* araçlarını kullan: institution_info (sayılar/özet),
institution_teachers, institution_classes, institution_teacher_schedule, institution_teacher_availability.
list_teachers / list_classes / schedule_summary YALNIZCA şu an açık olan kurumu bilir; başka kurum için
onları kullanma. institution_* araçları o kurumun EN SON çizelgesini okur ve hangi sürüm olduğunu söyler;
cevabında sürümü de belirt.
Silme/sıfırlama gibi geri dönüşü zor işleri kullanıcı açıkça istediyse yap; uygulama kendi onay kutusunu gösterir.
Sorunun cevabı veride ise (program, boş saat, açıkta kalan ders, kural listesi) tahmin etme, aracı çağırıp gerçek veriyi söyle.
Uydurma: bilmediğin bir ekranı ya da düğmeyi varmış gibi anlatma.

{KNOWLEDGE}
"""
