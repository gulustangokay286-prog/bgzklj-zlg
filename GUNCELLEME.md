# Uzaktan Güncelleme (OTA)

Evden bir güncelleme yayınlandığında, kullanıcıdaki Chenkron kurulumunun
kendiliğinden yeni sürüme geçmesini sağlayan sistem. Artık kimseye kurulum
dosyası göndermek gerekmiyor.

## Yayınlamak

Windows makinede, depo klasöründe tek komut:

```bat
yayinla.bat "Çevrimdışına düşme düzeltildi"
```

Betik `git pull` → motor → PyInstaller → yayın adımlarını sırayla koşar;
adımlardan biri düşerse orada durur. Elle yapmak isterseniz aynı sıra:

```bat
python tools\build_scheduler.py
pyinstaller Chenkron.spec --noconfirm
python publish_update.py --notes "Kilitli sütun sıfırlama düzeltildi"
```

Yayın **yalnızca Windows makineden** yapılabilir: yönetici anahtarı ve
Ed25519 imza anahtarı `..\ReleaseSystem\backend\` altında, paket de
`windows-x64`. Mac'te `publish_update.py` "ReleaseSystem/backend
bulunamadı" der.

`publish_update.py` sırasıyla şunları yapar:

1. `dist\Chenkron` klasörünü içerik-tanımlı parçalara böler (CDC),
2. sunucuda **olmayan** parçaları yükler (değişmeyen ~%95 tekrar yüklenmez),
3. manifesti Ed25519 ile imzalar,
4. sürümü kaydeder ve dağıtımı **%100'e** çıkarır.

Sürüm numarası `version.py`'den gelir. `--version` ile başka bir numara
verilirse ve `version.py` ile uyuşmuyorsa komut **durur**: paketin içindeki
sürüm ile yayınlanan numara farklı olursa istemci güncellemeden sonra
kendini hâlâ eski sürüm sanır ve aynı güncellemeyi her açılışta yeniden
indirir.

### Her yayından önce `version.py`

```python
APP_VERSION = "5.3.8"
APP_BUILD = 538
```

Sunucu "daha yeni mi" kararını bu numaraya göre verir. Yükseltmeden
yayınlarsanız hiçbir istemci güncellemeyi almaz.

### Durum görmek

```bat
python publish_update.py --status
```

Sunucudaki sürümleri, dağıtım yüzdelerini ve hangi cihazın hangi sürümde
olduğunu listeler.

### Yavaş dağıtım

```bat
python publish_update.py --notes "..." --canary          # %1'de bırak
python publish_update.py --advance rel_01m16f55aa94n...  # %100'e çıkar
```

## Kullanıcı tarafında ne oluyor

**Program kapalıyken açılırsa:** açılış (splash) ekranında güncelleme
denetlenir, varsa orada indirilir ve **program yeni sürümle açılır**.
Kullanıcı hiçbir şeye tıklamaz.

**Program açıkken:** 10 dakikada bir denetlenir. Yeni sürüm bulunduğunda
ekranın ortasında — anasayfadaki senkronizasyon penceresinin aynısı —
güncelleme penceresi kendiliğinden açılır ve indirme kendi başlar. İndirme
bitince tek bir soru sorulur: **Şimdi Yeniden Başlat** / **Daha Sonra**.
Çalışma ortasında program kendiliğinden kapanmaz.

Açık bir çizelgede kaydedilmemiş değişiklik varsa yeniden başlatmadan önce
kaydetme penceresi çıkar; kullanıcı iptal ederse güncelleme de iptal edilir.

## Nerede ne duruyor

| Yer | İçerik |
|---|---|
| `%LOCALAPPDATA%\Chenkron\OTA\State` | cihaz kimliği, bekleyen sürüm notları |
| `%LOCALAPPDATA%\Chenkron\OTA\Cache\chunks` | parça önbelleği (bir sonraki güncellemeyi küçültür) |
| `%LOCALAPPDATA%\Chenkron\OTA\Versions\<sürüm>` | kurulmayı bekleyen yeni sürüm |
| `%LOCALAPPDATA%\Chenkron\OTA\apply_update.cmd` | takas betiği |

Kurulum klasörü (`{app}`) **bilerek** kullanılmıyor: orası Program Files
olabilir ve yönetici hakkı olmadan yazılamaz. İndirme hiçbir zaman buna
takılmaz; yalnızca son takas adımı gerekirse bir kez UAC sorar.

## Sunucu

- Kontrol düzlemi: `https://updates.chenki.net:8443` (ReleaseSystem)
- Ürün: `chenkron` · Kanal: `stable` · Platform: `windows-x64`
- Parçalar MinIO'da; API parça baytlarını taşımaz, kısa ömürlü imzalı
  bağlantıya yönlendirir.
- Yönetici anahtarı `ReleaseSystem/backend/.env`, imzalama anahtarı
  `ReleaseSystem/backend/signing_key.pem`. **İkisi de sunucuya gitmez.**

## Sessiz tuzaklar

Bunların hepsi istemci tarafında **hiçbir hata göstermeden** "güncelleme
yok" sonucunu verir. Yayınladıktan sonra `--status` ile bakın.

1. **`version.py` yükseltilmemiş.** Sunucu daha yeni bir sürüm görmez.
2. **`--minimum-version` sürümünüzün üstünde.** O eşiğin altındaki
   kurulumlara güncelleme hiç önerilmez. Varsayılan boş; sebepsiz vermeyin.
3. **Dağıtım %100 değil.** `--canary` ile bıraktıysanız çoğu kurulum
   güncellemeyi görmez.
4. **Ürün adı uyuşmuyor.** İstemci `chenkron` soruyor; başka bir `--product`
   ile yayınlarsanız kimse bulamaz. (Sunucudaki eski `bkplanner` 3.x
   sürümleri bu yüzden artık kimseye gitmiyor.)

## Testler

```bat
python test_ota_update.py      # ağ + parça + imza + takas betiği
python test_update_ui_flow.py  # ortadaki pencere ve karar akışı
```

`test_ota_update.py` canlı sunucuya bağlanır (yayın yapmaz). Sunucuya
ulaşılamazsa ağ testleri atlanır.

## Bu işin geçmişi

Güncelleme uzun süre hiç çalışmadı ve tek bir hata yüzünden değil:

- `updater.py` + `push_ota.py`, Bogazici_Backend'de **hiç var olmamış**
  `/api/updates` ucuna konuşuyordu. Yayın komutu 404 alıyor, istemci her
  denetimde "zaten güncelsiniz" diyordu.
- `bk_update.py` + ReleaseSystem ise uygulamanın `<KÖK>/Versions/<sürüm>/`
  düzeniyle, `Launcher.exe` altından kurulmuş olmasını şart koşuyordu.
  `Chenkron.iss` ise her şeyi düz biçimde `{app}` içine kuruyor; yani
  `install_root()` kurulu **her** makinede `None` dönüyor ve splash'teki
  denetim de, oturum içi denetleyici de, anasayfadaki "Güncelleme mevcut"
  etiketi de sessizce hiçbir şey yapmıyordu.

Şimdi tek bir yol var: `ota_update.py` (motor) + `bk_update.py` (Qt katmanı)
+ `update_overlay.py` (pencere) + `publish_update.py` (yayın). Ölü iki dosya
(`updater.py`, `push_ota.py`) silinmedi ama içleri boşaltıldı — içe
aktarılırlarsa sessizce eski davranışa dönmek yerine hata veriyorlar.
