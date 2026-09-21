"""
push_ota.py — KULLANIMDAN KALDIRILDI. Yerine: publish_update.py

Bu betik Bogazici_Backend uzerinde `POST /api/updates` diye bir uca
yayin yapiyordu. O uc o sunucuda HIC var olmadi (bugun de yok; istek 404
donuyor). Yani "evden guncelleme yolla" komutu yillardir hicbir sey
yapmiyor, sessizce basarisiz oluyordu — kullanicilara guncellemenin hic
ulasmamasinin birinci sebebi buydu.

Gercek yayin hatti calisan ReleaseSystem kontrol duzlemine gider
(https://updates.chenki.net:8443): parcali (CDC) yukleme, Ed25519 imzali
manifest, asamali dagitim. Tek komut:

    python publish_update.py --notes "ne degisti"

Bu dosya, ayni 404'e geri donulmesin diye duruyor; calistirmaya calisan
ne yapmasi gerektigini ogreniyor.
"""
import sys

MESSAGE = """
push_ota.py artik kullanilmiyor.

Bu betik Bogazici_Backend'de var olmayan /api/updates ucuna yayin
yapiyordu; her cagrisi 404 aliyordu ve hicbir istemciye guncelleme
ulasmiyordu.

Bunun yerine:

    python publish_update.py --notes "ne degisti"

Yayin oncesi durumu gormek icin:

    python publish_update.py --status
"""


def main() -> int:
    print(MESSAGE.strip())
    return 2


if __name__ == "__main__":
    sys.exit(main())
