"""
build_installer.py — özel kurulum yöneticisini tek dosyalık exe olarak üretir
ve masaüstüne bırakır.

    python tools\\build_scheduler.py          # C++ motor
    pyinstaller Chenkron.spec --noconfirm     # program -> dist\\Chenkron
    python build_installer.py                 # kurulum dosyası -> Masaüstü

Ne yapar:
  1. dist\\Chenkron'un gerçekten bu kaynaktan derlendiğini kabaca doğrular,
  2. onu tek bir payload.zip'e sıkıştırır,
  3. ChenkronKurulum.spec ile tek dosyalık installer'ı derler,
  4. sonucu masaüstüne ChenkronKurulum-<sürüm>.exe olarak kopyalar.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST_APP = HERE / "dist" / "Chenkron"
BUILD_PAYLOAD = HERE / "build_payload"
PAYLOAD_ZIP = BUILD_PAYLOAD / "payload.zip"
OUT_DIR = HERE / "Output"


def _version() -> str:
    """Kurulum dosyasının adındaki sürüm.

    Installer penceresinde yazan sürüm custom_installer.APP_VERSION'dan
    geliyor; dosya adı da onunla aynı olsun ki kullanıcı ikisini
    karşılaştırınca şaşırmasın. version.py ile uyuşmuyorsa gürültülü
    biçimde söylüyoruz: otomatik güncelleme "hangi sürümdeyim" sorusunu
    version.py'den cevaplıyor, bu ikisi ayrıştığında yayınlanan sürüm ile
    programın kendini sandığı sürüm farklı olur.
    """
    sys.path.insert(0, str(HERE))
    from custom_installer import APP_VERSION as INSTALLER_VERSION
    from version import APP_VERSION as APP

    if INSTALLER_VERSION != APP:
        print()
        print(f"UYARI: installer penceresi v{INSTALLER_VERSION} diyor, "
              f"version.py ise {APP}.")
        print("       Otomatik güncelleme version.py'yi esas alır. Yayın")
        print("       yapmadan önce ikisini eşitleyin, yoksa program")
        print("       güncellendikten sonra kendini hâlâ eski sürüm sanar.")
        print()
    return INSTALLER_VERSION


def _desktop() -> Path:
    """OneDrive devredeyse masaüstü ~\\Desktop değil ~\\OneDrive\\Desktop
    olur; yanlışına yazarsak dosya "masaüstünde" görünmez."""
    candidates = [
        Path(os.environ.get("OneDrive", "")) / "Desktop",
        Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop",
        Path.home() / "Desktop",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return Path.home()


def check_payload() -> int:
    if not DIST_APP.is_dir():
        print(f"HATA: {DIST_APP} yok.")
        print("      Önce programı derleyin:  pyinstaller Chenkron.spec --noconfirm")
        return 1
    exe = DIST_APP / "Chenkron.exe"
    if not exe.exists():
        print(f"HATA: {exe} yok — burası bir Chenkron derlemesi değil.")
        return 1

    # Derleme kaynaktan eski mi? Bu sessiz bir hata kaynağı: kaynakta
    # düzelttiğiniz şey paketin içinde olmayınca "düzeltmedin ki" denir.
    exe_time = exe.stat().st_mtime
    # custom_installer.py kurulum yöneticisinin kendi kaynağı, programın
    # içine girmiyor; onu "derleme bayatlamış" saymak her seferinde yanlış
    # alarm verir ve uyarı ciddiye alınmaz hale gelir.
    skip = {"custom_installer.py", "publish_update.py"}
    newer = [
        p.name
        for p in HERE.glob("*.py")
        if p.name not in skip
        and not p.name.startswith(("test_", "scratch_", "build_"))
        and p.stat().st_mtime > exe_time
    ]
    if newer:
        print("UYARI: şu dosyalar derlemeden SONRA değişmiş:")
        for n in sorted(newer)[:10]:
            print(f"       {n}")
        print("       Yeniden derleyin:  pyinstaller Chenkron.spec --noconfirm")
        print()
    return 0


def make_zip() -> None:
    BUILD_PAYLOAD.mkdir(parents=True, exist_ok=True)
    if PAYLOAD_ZIP.exists():
        PAYLOAD_ZIP.unlink()

    files = [p for p in DIST_APP.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    print(f"[1/3] {len(files)} dosya sıkıştırılıyor ({total / 1e6:.0f} MB)...")

    started = time.time()
    done = 0
    # ZIP_DEFLATED, seviye 6: seviye 9 bu boyutta dakikalarca sürüp
    # kazandırdığı birkaç megabayt için kurulum dosyasını bekletiyor.
    with zipfile.ZipFile(PAYLOAD_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in files:
            z.write(p, p.relative_to(DIST_APP).as_posix())
            done += p.stat().st_size
            pct = int(100 * done / max(1, total))
            print(f"\r      %{pct}", end="", flush=True)
    size = PAYLOAD_ZIP.stat().st_size
    print(
        f"\r      {size / 1e6:.0f} MB oldu "
        f"(%{100 - int(100 * size / max(1, total))} küçüldü, {time.time() - started:.0f} sn)"
    )


def build_exe() -> int:
    print("[2/3] installer derleniyor...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "ChenkronKurulum.spec",
         "--noconfirm", "--distpath", str(OUT_DIR), "--workpath", str(HERE / "build")],
        cwd=str(HERE),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("HATA: PyInstaller başarısız.")
        print(result.stdout[-3000:])
        print(result.stderr[-3000:])
        return 1
    return 0


def deliver() -> int:
    built = OUT_DIR / "ChenkronKurulum.exe"
    if not built.exists():
        print(f"HATA: beklenen çıktı yok: {built}")
        return 1
    target = _desktop() / f"ChenkronKurulum-{_version()}.exe"
    shutil.copy2(built, target)
    print(f"[3/3] masaüstüne bırakıldı:")
    print(f"      {target}")
    print(f"      {target.stat().st_size / 1e6:.0f} MB")
    return 0


def main() -> int:
    if check_payload() != 0:
        return 1
    make_zip()
    if build_exe() != 0:
        return 1
    return deliver()


if __name__ == "__main__":
    raise SystemExit(main())
