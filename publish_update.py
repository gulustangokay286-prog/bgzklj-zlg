"""
publish_update.py — "evden guncelleme yolla" komutu.

Derlenmis build'i alir, parcalara boler, yalnizca sunucuda olmayan
parcalari yukler, manifesti Ed25519 ile imzalar, surumu kaydeder ve
dagitimi %100'e cikarir. Bundan sonra acik olan her Chenkron kurulumu
guncellemeyi kendiliginden indirir ve kullanip kullanmayacagini sorar.

    # 1) build
    python tools/build_scheduler.py
    pyinstaller Chenkron.spec --noconfirm

    # 2) yayinla
    python publish_update.py --notes "Kilitli sutun sifirlama duzeltildi"

    # sunucuda ne var, kim hangi surumde?
    python publish_update.py --status

NEDEN BU DOSYA VAR
------------------
Eskiden yayin push_ota.py ile yapiliyordu ve o betik Bogazici_Backend'de
var olmayan /api/updates ucuna POST atiyordu: her yayin 404 aliyor, hicbir
istemciye hicbir sey ulasmiyordu. Calisan kontrol duzlemi bastan beri
ReleaseSystem (https://updates.chenki.net:8443) idi; bu betik oraya
konusur.

%100 DAGITIM VARSAYILAN
-----------------------
Kontrol duzlemi bir surum yayinlandiginda once %1 "kanarya" dagitimiyla
baslar (rollout_steps = 1,5,10,25,50,100). Bes on kurulumluk bir filoda
%1 pratikte "kimseye gitmesin" demektir — yayinlayip sonra kimsede
gorunmemesinin sebeplerinden biri de budur. Bu yuzden varsayilan davranis
dagitimi kademe kademe %100'e cikarmaktir. Yavas dagitim isteniyorsa
--canary ile kademede birakilir.

GUVENLIK
--------
Manifest Ed25519 ozel anahtariyla imzalanir; istemcinin dogrulayacagi acik
anahtar exe'nin icine gomulüdür. Imza tutmuyorsa istemci paketi kurmaz.
Ozel anahtar bu makineden disari cikmaz.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RELEASE_SYSTEM = HERE.parent / "ReleaseSystem"
BACKEND = RELEASE_SYSTEM / "backend"

DEFAULT_API = os.environ.get("CHENKRON_RELEASE_API_URL", "https://updates.chenki.net:8443")
DEFAULT_PRODUCT = os.environ.get("CHENKRON_PRODUCT", "chenkron")
DEFAULT_CHANNEL = os.environ.get("CHENKRON_CHANNEL", "stable")
DEFAULT_PLATFORM = os.environ.get("CHENKRON_PLATFORM", "windows-x64")
DEFAULT_BUILD_DIR = HERE / "dist" / "Chenkron"

# Dagitimin %100 sayildigi esik; kontrol duzleminin son kademesi.
FULL_ROLLOUT = 100


def _fail(message: str) -> int:
    print(f"HATA: {message}", file=sys.stderr)
    return 1


def _read_env_value(key: str) -> str | None:
    """backend/.env icinden tek bir deger. Ozel anahtar ve yonetici
    anahtari depoda duruyor; ortam degiskeni verilmisse o oncelikli."""
    env_path = BACKEND / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name.strip() == key:
            return value.strip() or None
    return None


def admin_key(cli_value: str | None) -> str | None:
    return (
        cli_value
        or os.environ.get("CHENKRON_ADMIN_KEY")
        or os.environ.get("ADMIN_API_KEY")
        or _read_env_value("ADMIN_API_KEY")
    )


def signing_key_file(cli_value: str | None) -> Path | None:
    if cli_value:
        return Path(cli_value)
    env_file = os.environ.get("CHENKRON_SIGNING_KEY_FILE")
    if env_file:
        return Path(env_file)
    default = BACKEND / "signing_key.pem"
    return default if default.exists() else None


def app_version() -> str:
    from version import APP_VERSION

    return APP_VERSION


def app_build() -> int:
    from version import APP_BUILD

    return int(APP_BUILD)


def _import_backend():
    """Yayin hatti backend paketinin icinde (chunking, imzalama, MinIO).
    Ayarlar .env'den, CALISMA DIZININE gore okunuyor (pydantic-settings
    env_file='.env'), o yuzden once oraya geciliyor."""
    if not BACKEND.is_dir():
        raise RuntimeError(f"ReleaseSystem/backend bulunamadi: {BACKEND}")
    os.chdir(BACKEND)
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))


def _http():
    import httpx

    return httpx


# -- Sunucu durumu --------------------------------------------------------
def show_status(api: str, key: str | None, product: str, channel: str, platform: str) -> int:
    httpx = _http()
    print(f"Sunucu : {api}")
    try:
        health = httpx.get(f"{api}/health", timeout=15)
        print(f"Saglik : {health.status_code} {health.text.strip()[:40]}")
    except Exception as exc:
        return _fail(f"sunucuya ulasilamadi: {exc}")

    print(f"Yerel surum: {app_version()} (build {app_build()})")

    if not key:
        print("\n(Yonetici anahtari yok — surum listesi gosterilemiyor.)")
        return 0

    try:
        resp = httpx.get(f"{api}/v1/admin/releases", headers={"X-Admin-Key": key}, timeout=30)
        resp.raise_for_status()
        releases = resp.json()
    except Exception as exc:
        return _fail(f"surum listesi alinamadi: {exc}")

    print(f"\nSon surumler ({product}/{channel}/{platform} dahil tumu):")
    if not releases:
        print("  (hic surum yayinlanmamis)")
    for r in releases[:10]:
        print(
            f"  {r['version']:<10} {r['status']:<10} dagitim=%{r['rollout_percentage']:<4} "
            f"{r['platform']}  {str(r['created_at'])[:19]}"
        )

    try:
        devices = httpx.get(f"{api}/v1/admin/devices", headers={"X-Admin-Key": key}, timeout=30).json()
    except Exception:
        devices = []
    if devices:
        print(f"\nKayitli cihazlar ({len(devices)}):")
        for d in devices[:15]:
            seen = str(d.get("last_seen") or "")[:19]
            print(f"  {d.get('current_version', '?'):<10} {d.get('platform', ''):<14} son goruldu {seen}")
    else:
        print("\nKayitli cihaz yok. (Yeni istemci ilk denetiminde kendini kaydeder.)")
    return 0


# -- Dagitimi %100'e cikar -----------------------------------------------
def ramp_to_full(api: str, key: str, release_id: str) -> int:
    """Kanarya kademelerini tek tek gecerek %100'e cikarir.

    Her kademe ayri bir cagri: kontrol duzleminin kendi kademe listesini
    burada kopyalamak yerine, o ne diyorsa ona uyuluyor — kademeler
    sunucuda degisirse bu betigin degismesi gerekmiyor.
    """
    httpx = _http()
    for _ in range(12):  # kademe sayisindan fazlasi; sonsuz donguye karsi
        resp = httpx.post(
            f"{api}/v1/admin/releases/{release_id}/advance",
            headers={"X-Admin-Key": key},
            timeout=30,
        )
        if resp.status_code >= 400:
            print(f"  uyari: dagitim ilerletilemedi ({resp.status_code}): {resp.text[:200]}")
            return -1
        body = resp.json()
        pct = body.get("rollout_percentage", 0)
        print(f"  dagitim %{pct} ({body.get('status')})")
        if pct >= FULL_ROLLOUT:
            return pct
    return -1


# -- Yayin ----------------------------------------------------------------
def publish(args: argparse.Namespace) -> int:
    build_dir = Path(args.build_dir).resolve()
    if not build_dir.is_dir():
        return _fail(
            f"build klasoru yok: {build_dir}\n"
            "       Once derleyin:  pyinstaller Chenkron.spec --noconfirm"
        )
    exe = build_dir / "Chenkron.exe"
    if not exe.exists():
        return _fail(f"{build_dir} icinde Chenkron.exe yok — burasi bir Chenkron build'i degil.")

    key = admin_key(args.admin_key)
    if not key:
        return _fail(
            "yonetici anahtari bulunamadi. CHENKRON_ADMIN_KEY ortam degiskenini "
            "verin ya da ReleaseSystem/backend/.env icindeki ADMIN_API_KEY'i kullanin."
        )

    signer_file = signing_key_file(args.private_key_file)
    if signer_file is None or not signer_file.exists():
        return _fail(
            "imzalama anahtari bulunamadi (ReleaseSystem/backend/signing_key.pem). "
            "Imzasiz manifest istemcide REDDEDILIR, o yuzden yayin durduruldu."
        )

    version = args.version or app_version()
    if not args.force_version and version != app_version():
        return _fail(
            f"--version {version} ile version.py ({app_version()}) uyusmuyor.\n"
            "       Yayinlanan surum numarasi ile paketin ICINDEKI surum farkliysa "
            "istemci guncellemeden sonra kendini hala eski surum sanir ve her acilista "
            "ayni guncellemeyi indirir. version.py'yi duzeltin ya da --force-version verin."
        )

    api = args.api.rstrip("/")
    httpx = _http()

    # Ayni surum ikinci kez kaydedilemez (sunucu 409 doner); once soyleyip
    # 300 MB'lik bir chunk'lamadan sonra ogrenmekten kurtaralim.
    try:
        existing = httpx.get(
            f"{api}/v1/releases/{version}", params={"product": args.product}, timeout=20
        )
        if existing.status_code == 200:
            return _fail(
                f"{args.product} {version} zaten yayinlanmis. version.py'de surumu "
                "yukseltip yeniden derleyin."
            )
    except Exception as exc:
        return _fail(f"sunucuya ulasilamadi: {exc}")

    _import_backend()

    from app.config import get_settings
    from app.security.signing import Signer
    from app.services.manifest_service import build_manifest
    from app.storage.minio_client import chunk_object_key, get_minio_client, put_chunk, put_manifest

    settings = get_settings()
    signer = Signer.from_pem(signer_file.read_text(encoding="ascii"))

    print(f"[1/5] parcalaniyor: {build_dir}")
    result = build_manifest(
        build_dir=build_dir,
        product=args.product,
        version=version,
        channel=args.channel,
        platform=args.platform,
        minimum_version=args.minimum_version,
        signer=signer,
        min_chunk=settings.cdc_min_chunk_size,
        avg_chunk=settings.cdc_avg_chunk_size,
        max_chunk=settings.cdc_max_chunk_size,
        release_notes=args.notes,
    )
    total = sum(f["size"] for f in result.manifest["files"])
    print(
        f"      {len(result.manifest['files'])} dosya, "
        f"{len(result.chunks_by_hash)} benzersiz parca, {total / 1e6:.1f} MB"
    )

    if args.dry_run:
        print("[deneme] yukleme ve kayit yapilmadi.")
        print(json.dumps({k: v for k, v in result.manifest.items() if k != "files"}, indent=2))
        return 0

    print(f"[2/5] parcalar yukleniyor (bucket={settings.minio_bucket})")
    client = get_minio_client()
    existing_keys = set()
    try:
        for obj in client.list_objects(settings.minio_bucket, prefix=f"{args.product}/chunks/", recursive=True):
            existing_keys.add(obj.object_name)
    except Exception as exc:
        print(f"      not: mevcut parca listesi alinamadi ({exc}); hepsi yuklenecek")

    to_upload = [
        (h, c)
        for h, c in result.chunks_by_hash.items()
        if chunk_object_key(args.product, h) not in existing_keys
    ]
    skipped = len(result.chunks_by_hash) - len(to_upload)

    from concurrent.futures import ThreadPoolExecutor, as_completed

    uploaded = 0
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(put_chunk, args.product, h, c.data) for h, c in to_upload]
        for future in as_completed(futures):
            future.result()  # yukleme hatasini burada yukselt, sessizce yutma
            uploaded += 1
            if uploaded % 50 == 0 or uploaded == len(to_upload):
                print(f"      ...{uploaded}/{len(to_upload)}")
    new_bytes = sum(c.size for _, c in to_upload)
    print(
        f"      {uploaded} yeni parca yuklendi ({new_bytes / 1e6:.1f} MB), "
        f"{skipped} parca zaten sunucuda (yeniden yuklenmedi)"
    )

    print("[3/5] manifest yukleniyor")
    put_manifest(args.product, args.channel, version, json.dumps(result.manifest).encode("utf-8"))

    print(f"[4/5] surum kaydediliyor: {api}")
    payload = {
        "product": args.product,
        "channel": args.channel,
        "platform": args.platform,
        "version": version,
        "build_number": args.build_number if args.build_number is not None else app_build(),
        "minimum_version": args.minimum_version,
        "notes": args.notes,
        "manifest": result.manifest,
    }
    resp = httpx.post(
        f"{api}/v1/admin/releases", json=payload, headers={"X-Admin-Key": key}, timeout=180
    )
    if resp.status_code >= 400:
        return _fail(f"kayit basarisiz ({resp.status_code}): {resp.text[:400]}")
    release_id = resp.json()["release_id"]
    print(f"      kaydedildi: {release_id}")

    print("[5/5] yayinlaniyor")
    resp = httpx.post(
        f"{api}/v1/admin/releases/{release_id}/publish", headers={"X-Admin-Key": key}, timeout=60
    )
    if resp.status_code >= 400:
        return _fail(f"yayin basarisiz ({resp.status_code}): {resp.text[:400]}")
    body = resp.json()
    print(f"      dagitim %{body['rollout_percentage']} ({body['status']})")

    if args.canary:
        print(
            "\nKanarya kademesinde birakildi. Ilerletmek icin:\n"
            f"  python publish_update.py --advance {release_id}"
        )
        return 0

    print("      dagitim %100'e cikariliyor...")
    pct = ramp_to_full(api, key, release_id)
    if pct < FULL_ROLLOUT:
        print(
            "\nUYARI: dagitim %100'e cikarilamadi. Surum yayinda ama yalnizca "
            "kullanicilarin bir kismina gorunuyor."
        )
        return 1

    print(
        f"\nTAMAM. {args.product} {version} yayinda, dagitim %100.\n"
        "Acik olan kurulumlar en gec 10 dakika icinde, kapali olanlar acilis "
        "ekraninda guncellemeyi kendiliginden indirecek."
    )
    return 0


def advance_only(args: argparse.Namespace) -> int:
    key = admin_key(args.admin_key)
    if not key:
        return _fail("yonetici anahtari bulunamadi.")
    pct = ramp_to_full(args.api.rstrip("/"), key, args.advance)
    return 0 if pct >= FULL_ROLLOUT else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Chenkron guncellemesini yayinlar (parcali, imzali, %100 dagitim)."
    )
    parser.add_argument("--build-dir", default=str(DEFAULT_BUILD_DIR),
                        help=f"PyInstaller cikti klasoru (varsayilan: {DEFAULT_BUILD_DIR})")
    parser.add_argument("--version", default=None,
                        help="Yayinlanacak surum (varsayilan: version.py'deki APP_VERSION)")
    parser.add_argument("--build-number", type=int, default=None,
                        help="Tam sayi build numarasi (varsayilan: version.py'deki APP_BUILD)")
    parser.add_argument("--notes", default=None, help="Kullaniciya gosterilecek degisiklik notu")
    parser.add_argument("--minimum-version", default=None,
                        help="Bu surume dogrudan gecebilecek en eski surum")
    parser.add_argument("--product", default=DEFAULT_PRODUCT)
    parser.add_argument("--channel", default=DEFAULT_CHANNEL)
    parser.add_argument("--platform", default=DEFAULT_PLATFORM)
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--admin-key", default=None)
    parser.add_argument("--private-key-file", default=None)
    parser.add_argument("--canary", action="store_true",
                        help="Dagitimi %%100'e cikarma, ilk kademede birak")
    parser.add_argument("--force-version", action="store_true",
                        help="version.py ile uyusmasa da yayinla")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parcala ve imzala, ama yukleme/kayit yapma")
    parser.add_argument("--status", action="store_true",
                        help="Sunucudaki surumleri ve cihazlari listele, cik")
    parser.add_argument("--advance", default=None, metavar="RELEASE_ID",
                        help="Var olan bir surumun dagitimini %%100'e cikar, cik")
    args = parser.parse_args()

    if args.status:
        return show_status(
            args.api.rstrip("/"), admin_key(args.admin_key),
            args.product, args.channel, args.platform,
        )
    if args.advance:
        return advance_only(args)
    return publish(args)


if __name__ == "__main__":
    sys.exit(main())
