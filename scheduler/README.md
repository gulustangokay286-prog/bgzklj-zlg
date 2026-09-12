# C++ otomatik planlama motoru

`AutoSchedulerWorker` artık `scheduler.solve()` üzerinden C++ aramasını çalıştırır.
Python, uygulamanın kayıtlarını ve aktif planlama ilişkilerini derler; C++ gün ve
saat kararlarını aynı aramada değiştirir. Sonuç ayrı bir Python denetiminden geçer.

- Dersler atama dağılımındaki kartlar olarak kalır. Saat veya öğretmen üretilmez.
- Aynı ders/öğretmen aynı gün tekrar etmesin kuralları, seçilmiş kapsamda günde
  bir kart anlamındadır. İki saatlik kart bir karttır; iki ayrı kart bitişik diye
  birleştirilmez. Kapatılmış ilişkiler motor tarafından yeniden açılmaz.
- Eski kayıtlarda ders seçimi boş olan “İki ders aynı güne gelmesin”, mevcut
  uygulamanın elle yerleştirme davranışıyla aynı şekilde, aynı sınıfta aynı
  öğretmenin günlük tekrarını engeller. Yeni ekranda bunun açık adı da bulunur.
- Öğretmen/sınıf çakışması, kapalı hücre ve kilitler sert kısıtlardır.
- Sıkı ilişkiler ihlal edilmez. Diğer önem seviyeleri tercih olarak puanlanır;
  karşılanamayan tercihler rapora yazılır. Tercih optimumu garanti edilmez.
- Süre dolması, tek başına çözümsüzlük kanıtı değildir. Gün/saat kapasitesi
  denetimleri ayrı tanıklarla raporlanır. Raporun üst sınırı yalnızca okunan
  veri ve derlenen kural anlamları için geçerlidir; başka bir programın modeliyle
  eşdeğerlik kanıtı değildir.
- C++ aramasının geçici çakışmalı durumları kullanıcı çizelgesine yazılmaz.
  Yalnızca denetlenmiş yerleşimler ve eksik kartların tamamı geri döner.

## Derleme ve doğrulama

```sh
python3 tools/build_scheduler.py
python3 -m unittest -v test_native_scheduler
QT_QPA_PLATFORM=offscreen python3 test_auto_scheduler_constraints.py
python3 tools/schedule.py INPUT.roz --seconds 25 --seed 17 --output OUTPUT.roz
```

C++17 için clang++ veya g++ gerekir. Geliştirmede kaynak özetiyle derleme önbelleği
kullanılır. PyInstaller paketi için önce derleyin; `Chenkron.spec` çalıştırılabilir
motoru pakete alır. Son kullanıcı bilgisayarında derleyici gerekmez.

Komut satırı aracı kaynak dosyanın üzerine yazmaz. Çıktı raporunda kaynak SHA-256,
aktif kuralların tanıları, eksik kartlar, süre ve kullanılan tohum bulunur.
Tamamlanmış sonuç için çıkış kodu 0, eksik sonuç için 2 döner.

## v188 doğrulaması

v188'in yerel `.roz` kaydı ve aktif ilişkileri üzerinde 281/285 saatlik, sıfır
sert kural ihlalli bir sonuç bulunmuştur. Kaynak atamalar/müsaitlikler değiştirilmedi.
Bu henüz istenen 285/285 sonucu değildir. Kullanıcının aSc'de tamamladığı program
elde olmadığı için aSc ile veri, dağılım ve kural kapsamı eşdeğerliği doğrulanmadı.
`artifacts/scheduler/v188-native-audited.roz` yalnızca yerel inceleme çıktısıdır.
