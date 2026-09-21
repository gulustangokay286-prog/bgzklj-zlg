"""
ota_update.py — uzaktan (OTA) guncelleme motoru: kurulu, "duz" build icin.

NEDEN BU DOSYA VAR
------------------
Guncelleme yollamak uzun suredir hic calismiyordu ve sebebi tek bir hata
degildi; birbirinden habersiz iki yarim sistem vardi:

  1. updater.py + push_ota.py, Bogazici_Backend uzerinde `/api/updates`
     diye bir uca konusuyordu. O uc o sunucuda HIC yok (bugun de yok:
     GET/POST -> 404). Yani "evden guncelleme yolla" komutu 404 aliyor,
     istemci de her denetimde "zaten guncelsiniz" dalina dusuyordu.

  2. bk_update.py + ReleaseSystem/client (chunk'li gercek motor) ise
     uygulamanin <ROOT>/Versions/<surum>/ + <ROOT>/State/ duzeniyle,
     Launcher.exe altindan kurulmus olmasini sart kosuyordu. Chenkron.iss
     ise her seyi duz bicimde {app} icine kuruyor. Dolayisiyla
     bk_update.install_root() her kurulu makinede None donuyor, splash'teki
     denetim de, oturum ici denetleyici de, ana ekrandaki "Guncelleme
     mevcut" etiketi de sessizce hicbir sey yapmiyordu.

Bu modul ikisini tek bir calisan yola indiriyor: ReleaseSystem'in gercek
chunk'li cekme hattini (imzali manifest -> icerik-adresli chunk'lar ->
dogrulama -> kurgulama) kullanir, AMA Launcher/Versions duzenini sart
kosmaz. Kurulum {app} icinde duz kalir, kisayollar degismez, arka planda
ayri bir updater sureci calismaz.

NASIL CALISIR
-------------
  denetle   -> GET /v1/releases/latest (surum, kanal, platform, cihaz)
  indir     -> imzali manifest + YALNIZCA eksik chunk'lar (Ed25519 + SHA-256)
  kurgula   -> yeni surum OTA_ROOT/Versions/<surum>/ altinda birlestirilir
  uygula    -> bu surec kapaninca kurulum klasorunu robocopy ile degistirip
               uygulamayi yeniden acan kucuk bir .cmd betigi

Durum/onbellek dosyalari kurulum klasorunde degil, her zaman yazilabilir
olan %LOCALAPPDATA%\\Chenkron\\OTA altinda durur. Program Files'a kurulmus
bir uygulamanin kendi klasorune yazamamasi yuzunden guncellemenin
baslayamamasi bu sayede mumkun degil; yalnizca son takas adimi gerekirse
yukseltme ister.

Chunk onbellegi kalicidir: 300 MB'lik bir uygulamada 6 MB degistiyse
indirilen de ~6 MB olur (icerik-tanimli chunk'lama). Asil kazanc budur.

Qt'ye hic bagimli degildir; arayuz katmani update_overlay.py ve
bk_update.py icindedir.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from version import APP_VERSION

logger = logging.getLogger("ota")

# Takas betiginin uygulamayi yeniden acmadan once bu surecin olmesini
# beklerken attigi tur; robocopy kilitli bir .exe'nin uzerine yazamaz.
# ping -n N, N-1 saniye bekler.
_WAIT_TICK_SECONDS = 3

# Bekleme suresiz olamaz: kapanmayi reddeden (donmus) bir surecte betik
# sonsuza kadar donerdi. ~100 x 2 sn = ~3,5 dakika sonra vazgecer ve
# HICBIR SEY kopyalamaz; guncelleme bir sonraki aciliista yeniden denenir.
_WAIT_MAX_TRIES = 100


# -- ReleaseSystem istemci paketini bulunur kil ---------------------------
def _release_system_root() -> Path | None:
    """Yalnizca kaynaktan calisirken (python main.py) anlamli. Donmus
    derlemede `client` paketi Chenkron.spec'in pathex'i sayesinde exe'nin
    kendi arsivine gomuludur, dosya sisteminde aranacak bir yol yoktur."""
    if getattr(sys, "frozen", False):
        return None
    candidate = Path(__file__).resolve().parent.parent / "ReleaseSystem"
    return candidate if candidate.is_dir() else None


_rs_root = _release_system_root()
if _rs_root is not None and str(_rs_root) not in sys.path:
    sys.path.insert(0, str(_rs_root))

try:
    from client.config import ClientConfig, ca_bundle_path
    from client.networking.http_client import HttpClient
    from client.security import device_identity
    from client.state.paths import Layout
    from client.updater import chunk_store, downloader, installer, manifest
    from client.updater.downloader import DownloadProgress

    ENGINE_AVAILABLE = True
except Exception:  # pragma: no cover - yalnizca eksik/bozuk kurulumda
    ENGINE_AVAILABLE = False
    DownloadProgress = None  # type: ignore[assignment]


class OtaError(Exception):
    pass


# -- Yollar ---------------------------------------------------------------
def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def install_dir() -> Path | None:
    """Chenkron.exe'nin bulundugu klasor - takasin hedefi. Kaynaktan
    calisirken None: bir Python agacinin uzerine robocopy cekmek yapilacak
    en son sey olurdu."""
    if not is_frozen():
        return None
    return Path(sys.executable).resolve().parent


def ota_root() -> Path:
    """Durum + chunk onbellegi + kurgulanan surumler. Kurulum klasorunden
    KASITLI olarak ayri: orasi Program Files olabilir ve yonetici hakki
    olmadan yazilamaz; guncellemenin indirilmesi buna takilmamali."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "Chenkron" / "OTA"


def _layout() -> "Layout":
    layout = Layout(ota_root())
    layout.ensure_all()
    return layout


def updates_supported() -> bool:
    """Motor yuklenebiliyor mu? Degilse arayuz guncelleme denetimini hic
    gostermez - kullaniciya her acilista basarisiz olan bir denetim
    gostermektense hic gostermemek dogru."""
    return ENGINE_AVAILABLE


# -- Sunucu ---------------------------------------------------------------
def config() -> "ClientConfig":
    return ClientConfig()


def _http(cfg: "ClientConfig", timeout: float = 30.0) -> "HttpClient":
    # ca_bundle_path() yoksa normal sistem guveni kullanilir; updates.chenki.net
    # artik gercek bir Let's Encrypt sertifikasi sunuyor, sabitlemeye gerek yok.
    return HttpClient(cfg.api_base_url, timeout=timeout, verify_tls=ca_bundle_path() or True)


@dataclass
class UpdateInfo:
    """Sunucunun "senin icin su surum var" cevabi."""

    release_id: str
    version: str
    notes: str
    total_size_bytes: int


class OtaClient:
    """Tek bir denetim-indir-kurgula-uygula turu.

    Tek seferlik degil: ayni nesne uzerinden tekrar tekrar check() cagirmak
    guvenlidir. Indirme, chunk onbellegi sayesinde kendiliginden devam
    eder - yarida kesilen bir indirme bir sonraki turda yalnizca eksik
    kalan chunk'lari ister, bastan baslamaz.
    """

    def __init__(self, current_version: str | None = None):
        if not ENGINE_AVAILABLE:
            raise OtaError("guncelleme motoru bu derlemede yok")
        self.cfg = config()
        self.layout = _layout()
        self.http = _http(self.cfg)
        self.identity = device_identity.load_or_create(self.layout.state_dir)
        self.current_version = current_version or APP_VERSION
        self._session_id: str | None = None

    # --- Cihaz kimligi ---------------------------------------------------
    def ensure_registered(self) -> None:
        """Kayit, guncellemenin calismasi icin sart DEGIL; sunucudaki cihaz
        listesinin ("kim hangi surumde") gercek olmasini saglar. Bu yuzden
        basarisizligi yutuluyor, akisi durdurmuyor."""
        if self.identity.device_id and self.identity.device_token:
            return
        try:
            resp = self.http.post_json(
                "/v1/devices/register",
                {
                    "device_uuid": self.identity.device_uuid,
                    "product": self.cfg.product,
                    "platform": self.cfg.platform,
                    "channel": self.cfg.channel,
                    "version": self.current_version,
                    "public_key": self.identity.public_key_pem(),
                },
            )
        except Exception:
            logger.debug("cihaz kaydi basarisiz (sonra denenecek)", exc_info=True)
            return
        self.identity.device_id = resp.get("device_id")
        self.identity.device_token = resp.get("device_token")
        device_identity.save(self.layout.state_dir, self.identity)

    def heartbeat(self) -> None:
        if not (self.identity.device_id and self.identity.device_token):
            return
        self.http.fire_and_forget(
            "/v1/devices/heartbeat",
            {
                "device_id": self.identity.device_id,
                "device_token": self.identity.device_token,
                "version": self.current_version,
                "status": "running",
            },
        )

    # --- Denetim ---------------------------------------------------------
    def check(self) -> UpdateInfo | None:
        """Bu cihaz icin uygun, DAHA YENI bir surum var mi? Yoksa None.

        Surum karsilastirmasini ve asamali dagitim kovasini sunucu yapar
        (find_eligible_release); istemci "daha yeni mi" kararini kendi
        vermez, boylece dagitimi yuzde yuze cikarmadan yarim surum
        dagitilmasi mumkun olmaz."""
        summary = self.http.get_json(
            "/v1/releases/latest",
            params={
                "product": self.cfg.product,
                "channel": self.cfg.channel,
                "platform": self.cfg.platform,
                "current_version": self.current_version,
                "device_id": self.identity.device_uuid,
            },
        )
        if not summary or not summary.get("version"):
            return None
        return UpdateInfo(
            release_id=summary.get("release_id", ""),
            version=summary["version"],
            notes=summary.get("notes") or "",
            total_size_bytes=int(summary.get("total_size_bytes") or 0),
        )

    # --- Indirme + kurgulama ---------------------------------------------
    def prepare(self, info: UpdateInfo, on_progress=None, on_stage=None) -> Path:
        """Manifesti dogrular, eksik chunk'lari indirir, yeni surumu
        Versions/<surum>/ altinda birlestirir ve dosya dosya saglamasini
        kontrol eder. Donen klasor kurulmaya hazirdir; kurulum klasorune
        bu asamada HIC dokunulmaz - kullanici calismaya devam ediyor
        olabilir.

        on_progress(downloaded_bytes, total_bytes) GUI is parcacigindan
        degil, indirme is parcaciklarindan cagrilir; cagiran tarafin bunu
        sinyalle tasimasi gerekir. on_stage() indirme bitip dogrulama +
        birlestirme asamasi basladiginda bir kez cagrilir; 300 MB'lik bir
        paketin birlestirilmesi saniyeler suruyor ve bu sirada ilerleme
        cubugunun donmus gorunmemesi icin arayuzun haberi olmasi gerekiyor.
        """
        self._start_session(info)
        self._gc_stale_versions(keep=info.version)

        man = manifest.fetch_and_verify(
            self.http, self.layout, self.cfg.product, self.cfg.channel, info.version
        )
        chunk_sizes = {c["hash"]: c["size"] for f in man["files"] for c in f["chunks"]}

        def _cb(p: "DownloadProgress") -> None:
            if on_progress:
                on_progress(p.downloaded_bytes, p.total_bytes)

        self._event("download_started", {"version": info.version})
        downloader.download_chunks(
            self.http, self.layout, self.cfg.product, chunk_sizes, self.cfg, _cb
        )

        missing = [h for h in chunk_sizes if not chunk_store.has_chunk(self.layout, h)]
        if missing:
            raise OtaError(f"indirme sonrasi {len(missing)} parca hala eksik")
        self._event("download_completed", {"version": info.version})

        if on_stage:
            on_stage()
        staged = installer.stage_release(self.layout, man, info.version)
        final = self.layout.version_dir(info.version)
        if final.exists():
            shutil.rmtree(final, ignore_errors=True)
        os.replace(staged, final)

        # Yalnizca bu surumun parcalarini tut: bir sonraki surum bunlarin
        # buyuk kismini yeniden kullanacak, gerisi olu yer kapliyor.
        try:
            chunk_store.evict_unreferenced(self.layout, set(chunk_sizes))
        except Exception:
            logger.debug("chunk temizligi atlandi", exc_info=True)

        self._event("staged", {"version": info.version})
        return final

    def staged_dir(self, version: str) -> Path | None:
        """Onceki bir turda zaten kurgulanmis surum varsa yolu - yeniden
        indirmeye gerek yok demektir."""
        path = self.layout.version_dir(version)
        return path if path.is_dir() else None

    def _gc_stale_versions(self, keep: str) -> None:
        if not self.layout.versions_dir.exists():
            return
        for d in self.layout.versions_dir.iterdir():
            if d.name in (keep, f"{keep}.tmp"):
                continue
            shutil.rmtree(d, ignore_errors=True)

    # --- Telemetri -------------------------------------------------------
    def _start_session(self, info: UpdateInfo) -> None:
        if not (self.identity.device_id and self.identity.device_token) or not info.release_id:
            return
        try:
            sess = self.http.post_json(
                "/v1/update/session",
                {
                    "device_id": self.identity.device_id,
                    "device_token": self.identity.device_token,
                    "from_version": self.current_version,
                    "to_release_id": info.release_id,
                },
            )
            self._session_id = sess.get("session_id")
        except Exception:
            logger.debug("sunucu tarafi oturum acilamadi (yerelde devam)", exc_info=True)

    def _event(self, event_type: str, payload: dict) -> None:
        if not self._session_id:
            return
        self.http.fire_and_forget(
            "/v1/update/events",
            {
                "session_id": self._session_id,
                "device_token": self.identity.device_token,
                "event_type": event_type,
                "payload": payload,
            },
        )

    def report_applied(self, version: str) -> None:
        self._event("activating", {"version": version})


# -- Uygulama (takas) -----------------------------------------------------
def _dir_is_writable(path: Path) -> bool:
    probe = path / f".ota_probe_{os.getpid()}"
    try:
        probe.write_bytes(b"")
        probe.unlink()
        return True
    except OSError:
        return False


def _write_swap_script(staged: Path, target: Path, exe: Path) -> Path:
    """Calisan bir .exe Windows'ta kendi dosyasini kilitler; takasi bu
    surecin olmesini bekleyen kucuk bir betige devretmek zorundayiz.

    robocopy KASITLI olarak /MIR veya /PURGE olmadan cagriliyor: kurulum
    klasorunde Inno Setup'in kendi kaldirma dosyalari (unins000.exe/.dat)
    duruyor ve aynalama onlari silerdi - program bir daha kaldirilamazdi.
    Artakalan eski dosyalar zararsiz, kaldiriciyi silmek degil.

    Dosya OEM kod sayfasiyla yaziliyor, UTF-8 ile degil: cmd.exe bir .cmd
    dosyasini konsolun OEM kod sayfasina gore okur (Turkiye'de cp857).
    Yollar %LOCALAPPDATA% uzerinden geciyor, yani kullanici adi iceriyor;
    "Gokay" degil de "Gökay" olan bir makinede UTF-8 yazilmis bir betik
    robocopy'ye bozuk bir yol verir ve guncelleme sessizce basarisiz
    olurdu.
    """
    script = ota_root() / "apply_update.cmd"
    script.parent.mkdir(parents=True, exist_ok=True)
    pid = os.getpid()
    body = (
        "@echo off\r\n"
        "setlocal\r\n"
        "rem Chenkron OTA - bu betik ota_update.py tarafindan uretildi.\r\n"
        "rem\r\n"
        "rem tasklist/find/ping/robocopy TAM YOLLA cagriliyor, ciplak adla\r\n"
        "rem degil. Kullanicinin PATH'inde System32'den once gelen bir\r\n"
        "rem dizin varsa (Git for Windows'un usr\\bin'i en yaygin ornegi,\r\n"
        "rem orada Unix'in 'find' komutu duruyor) ciplak 'find' bambaska\r\n"
        "rem bir program calistirir, kosul yanlis sonuclanir ve betik\r\n"
        "rem uygulama HALA ACIKKEN kopyalamaya baslar. Bu tam olarak\r\n"
        "rem calisan .exe'nin uzerine yazmaya calismak demektir.\r\n"
        'set "SYS=%SystemRoot%\\System32"\r\n'
        "set /a TRIES=0\r\n"
        "rem Uygulamanin kendi .exe'si uzerindeki kilidi birakmasini bekle.\r\n"
        ":waitloop\r\n"
        "set /a TRIES+=1\r\n"
        f"if %TRIES% GTR {_WAIT_MAX_TRIES} goto giveup\r\n"
        f'"%SYS%\\tasklist.exe" /FI "PID eq {pid}" /NH 2>nul | "%SYS%\\find.exe" "{pid}" >nul\r\n'
        "if not errorlevel 1 (\r\n"
        f'    "%SYS%\\ping.exe" -n {_WAIT_TICK_SECONDS} 127.0.0.1 >nul\r\n'
        "    goto waitloop\r\n"
        ")\r\n"
        f'"%SYS%\\robocopy.exe" "{staged}" "{target}" /E /IS /IT /R:3 /W:2 /NFL /NDL /NJH /NJS >nul\r\n'
        f'start "" "{exe}"\r\n'
        "goto end\r\n"
        ":giveup\r\n"
        "rem Program bu kadar surede kapanmadi. Yarim bir kopyalama yapmaktansa\r\n"
        "rem hic yapmamak dogru: paket diskte duruyor, guncelleme bir sonraki\r\n"
        "rem aciliista yeniden denenecek ve tek bir bayt bile yeniden inmeyecek.\r\n"
        ":end\r\n"
        "endlocal\r\n"
    )
    for encoding in ("oem", "mbcs", "utf-8"):
        try:
            script.write_text(body, encoding=encoding)
            return script
        except (LookupError, UnicodeEncodeError):
            continue  # "oem" yalnizca Windows'ta var; yoksa sirayla in
    script.write_text(body, encoding="utf-8", errors="replace")
    return script


def apply_staged(staged: Path) -> bool:
    """Kurgulanmis surumu kurulum klasorune tasiyacak betigi baslatir ve
    hemen doner. Cagiran taraf ARDINDAN sureci kapatmalidir - betik onu
    bekliyor.

    Kurulum klasoru yazilabilir degilse (Program Files'a yonetici olarak
    kurulmussa) betik yukseltilmis olarak baslatilir; kullanici UAC
    penceresini bir kez gorur.

    Kaynaktan calisirken False doner ve hicbir seye dokunmaz.
    """
    target = install_dir()
    if target is None:
        logger.info("kaynaktan calisiliyor - paket %s icinde, kurulum yapilmadi", staged)
        return False
    if not staged.is_dir():
        return False

    exe = Path(sys.executable).resolve()
    script = _write_swap_script(staged, target, exe)

    try:
        if _dir_is_writable(target):
            subprocess.Popen(
                ["cmd", "/c", str(script)],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                close_fds=True,
            )
        else:
            # Yukseltme gerekiyor. PowerShell'in Start-Process -Verb RunAs'i
            # UAC istemini cikarir; kullanici reddederse takas olmaz ve
            # uygulama eski surumle acilmaya devam eder (veri kaybi yok).
            ps = (
                "Start-Process -FilePath cmd -ArgumentList '/c',"
                f"'\"{script}\"' -Verb RunAs -WindowStyle Hidden"
            )
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                close_fds=True,
            )
    except Exception:
        logger.error("guncelleme betigi baslatilamadi", exc_info=True)
        return False
    return True


def write_pending_notes(version: str) -> None:
    """Yeni surumun degisiklik notlarini State/pending_notes.json'a yazar.

    Takastan HEMEN ONCE cagrilir: program bir daha acildiginda
    update_notifications.check_and_show_whats_new bu dosyayi okuyup silerek
    tek seferlik "yenilikler" bildirimini gosterir. Dosyanin VARLIGI
    "henuz gosterilmedi" bayragidir; ayrica tutulan bir durum yok.
    """
    if not ENGINE_AVAILABLE or not version:
        return
    try:
        layout = _layout()
        cfg = config()
        cached = manifest.load_cached(layout, cfg.product, cfg.channel, version)
        notes = (cached or {}).get("release_notes") or ""
        if not notes.strip():
            return
        from client.state.atomic_json import write_json

        write_json(layout.pending_notes_json_path, {"version": version, "notes": notes})
    except Exception:
        logger.debug("pending_notes yazilamadi", exc_info=True)


def quit_now(exit_code: int = 0) -> None:
    """Takas betigi bu surecin olmesini bekliyor; atexit kancalarinin ya da
    kapanmayi geciktiren bir arka plan is parcaciginin betigi suresiz
    bekletmesine izin verilemez, o yuzden sert cikis."""
    os._exit(exit_code)


def current_version_string() -> str:
    return APP_VERSION
