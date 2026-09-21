"""
updater.py — KULLANIMDAN KALDIRILDI. Yerine: ota_update.py + bk_update.py

Bu modul VDS'te `GET /api/updates` ucunu yokluyordu. O uc Bogazici_Backend'de
HIC yok: istek her seferinde 404 donuyor, `get_latest_release()` None
donduruyor ve denetim sessizce "up-to-date" dalina dusuyordu. Yani menudeki
"Yeni Versiyon Kontrolu" hangi surum yayinlanirsa yayinlansin her zaman
"en guncel surumu kullaniyorsunuz" diyordu.

Yerine gecen calisan yol:

  ota_update.py   ReleaseSystem kontrol duzlemine (updates.chenki.net:8443)
                  konusan parcali cekme motoru: imzali manifest, yalnizca
                  degisen chunk'lar, dogrulama, kurgulama, takas.
  bk_update.py    Qt katmani: splash'te engelleyici denetim, program
                  acikken periyodik denetim, ortadaki guncelleme penceresi.

Tek fark davranista degil, iscilikte: eski yol her guncellemede paketin
TAMAMINI (~300 MB) indirirdi; yeni yol yalnizca gercekten degisen baytlari
indirir.

Bu dosya, ayni olu uca geri donulmesin diye duruyor. Iceri aktarmaya
calisan kod aninda ve acik bir hata alir, sessizce eski davranisa
donmez.
"""

_MESSAGE = (
    "updater.py kullanimdan kaldirildi: /api/updates ucu sunucuda yok "
    "(her cagri 404). Guncelleme icin ota_update.py / bk_update.py kullanin."
)


class UpdaterRemovedError(RuntimeError):
    pass


def __getattr__(name: str):
    """Eski adlarin (UpdateChecker, install_staged_update, is_frozen,
    current_version_string) hepsi buraya dusuyor. Sessiz bir None yerine
    hata: bu modulu yeniden baglayan biri, calismadigini kullanicilar
    aylarca guncelleme alamadiktan sonra degil, ilk calistirmada gormeli."""
    raise UpdaterRemovedError(f"{_MESSAGE} (istenen ad: {name})")
