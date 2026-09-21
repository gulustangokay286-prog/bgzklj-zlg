"""
bk_update.py — guncelleme akisinin Qt katmani.

ota_update.py agi ve diski yapar, bu dosya onu arayuze baglar. Tek is
parcacigi kurali gecerli: her ag/disk isi bir QThread'de, her widget
dokunusu ana is parcaciginda (sinyaller araciligiyla).

BU DOSYA NEDEN DEGISTI
----------------------
Onceki hali ReleaseSystem'in Launcher/Versions kurulum duzenini sart
kosuyordu: install_root() o duzeni bulamazsa None donuyor ve buradaki HER
SEY sessizce devre disi kaliyordu. Chenkron.iss ise duz kurulum yapiyor,
yani install_root() kurulu her makinede None donuyordu — guncelleme
denetimi yillardir hic calismamisti. Artik ota_update.py duz kurulumu
destekledigi icin bu katman her zaman calisir; Launcher.exe'ye,
Versions/ duzenine ve arka planda duran ayri bir updater surecine gerek
yok.

IKI GIRIS NOKTASI
-----------------
  1. Acilista, splash ekraninda (run_blocking_check + apply_and_restart):
     bayat bir kurulum, anasayfa hic gorunmeden once kendini toparlar.
  2. Program acikken (InSessionUpdateChecker): periyodik denetim; yeni
     surum bulunursa ortada UpdateCenterOverlay acilir, indirme kendi
     basina baslar, bitince tek bir karar sorulur. Kullanici calisirken
     hicbir sey kendiliginden yeniden baslatilmaz.

Tercihin bedeli acikca soylenmeli: surekli acik bir WebSocket yerine
periyodik denetim var, yani program acikken yayinlanan bir surum saniyesi
saniyesine degil, en gec bir denetim araligi sonra fark edilir. Buna
karsilik arka planda hicbir surec durmuyor.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import QWidget

import ota_update
from ota_update import OtaError  # noqa: F401  (cagiranlar icin yeniden disa vurum)
from version import APP_VERSION

# Program acikken denetim araligi. 10 dakika: yeni surum yayinlandiktan
# sonra makul bir gecikme, ama bos yere sunucuya gidip gelmeyecek kadar da
# seyrek.
IN_SESSION_POLL_MS = 10 * 60 * 1000

# Ilk denetim acilistan hemen sonra degil: acilis zaten agir (oturum
# dogrulama, kurum listesi, bulut senkronu). Guncelleme denetimi o
# kalabaliga karismasin.
FIRST_CHECK_DELAY_MS = 45 * 1000

# Eski adin karsiligi; update_notifications.py gibi cagiranlar bunu
# kontrol ediyor.
_HAS_UPDATE_ENGINE = ota_update.ENGINE_AVAILABLE


def updates_supported() -> bool:
    return ota_update.updates_supported()


def install_root() -> Path | None:
    """Geriye donuk ad. Artik "kurulumun kokunu bul" degil, "guncelleme
    durumu nerede duruyor" sorusunun cevabi: %LOCALAPPDATA%\\Chenkron\\OTA.
    Motor yoksa None — cagiranlar bunu "burada guncelleme yapilamaz"
    olarak ele aliyor, oyle de kalsin."""
    if not ota_update.updates_supported():
        return None
    return ota_update.ota_root()


# -- Arka plan isi --------------------------------------------------------
class UpdateWorker(QObject):
    """Tek bir denetim-indir-kurgula turu, bir QThread icinde.

    found:     yeni surum var, indirme basliyor (surum, toplam bayt)
    progress:  indirilen / toplam bayt
    verifying: indirme bitti, imza + saglama dogrulamasi basladi
    staged:    paket kurulmaya hazir (surum, notlar)
    nothing:   guncel
    failed:    hata metni
    """

    found = Signal(str, int)
    progress = Signal(int, int)
    verifying = Signal(str)
    staged = Signal(str, str)
    nothing = Signal()
    failed = Signal(str)

    def __init__(self, current_version: str | None = None):
        super().__init__()
        self._current_version = current_version or APP_VERSION

    def run(self) -> None:
        try:
            client = ota_update.OtaClient(self._current_version)
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        try:
            client.ensure_registered()
            info = client.check()
        except Exception as exc:
            self.failed.emit(f"Sunucuya ulasilamadi: {exc}")
            return

        if info is None:
            try:
                client.heartbeat()
            except Exception:
                pass
            self.nothing.emit()
            return

        self.found.emit(info.version, info.total_size_bytes)

        try:
            # Onceki turda indirilip kurgulanmis olabilir: o zaman tek bir
            # bayt bile yeniden indirilmez.
            ready = client.staged_dir(info.version)
            if ready is None:
                client.prepare(
                    info,
                    on_progress=lambda d, t: self.progress.emit(d, t),
                    on_stage=lambda: self.verifying.emit(info.version),
                )
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        self.staged.emit(info.version, info.notes)


class _ThreadRunner(QObject):
    """QThread + UpdateWorker ikilisinin omrunu tek yerde tutar.

    Ayri bir sinif olmasinin sebebi somut: worker'i yerel degiskende
    tutmak Python'un onu toplamasina, thread'i yerel degiskende tutmak da
    "QThread: Destroyed while thread is still running" cokmesine yol
    aciyor. Ikisi de burada, cagirana referans olarak veriliyor."""

    def __init__(self, parent: QObject, current_version: str | None = None):
        super().__init__(parent)
        self.thread = QThread(parent)
        self.worker = UpdateWorker(current_version)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        """Thread'i durdurup Qt nesnelerini de sil. deleteLater olmadan
        her denetim (10 dakikada bir) ana pencereye bir QThread cocugu
        daha takiyor: uzun bir gun sonunda onlarca olu nesne birikiyor."""
        self.thread.quit()
        self.thread.wait(3000)
        self.worker.deleteLater()
        self.thread.deleteLater()
        self.deleteLater()


# -- Acilis (splash) yolu -------------------------------------------------
def run_blocking_check(root=None, on_progress=None, on_stage=None):
    """Splash ekrani icin: denetle, gerekiyorsa indir ve kurgula; CAGIRAN
    is parcacigini yerel bir olay dongusuyle bekletir, boylece splash'in
    var olan exec() akisini degistirmeye gerek kalmaz.

    Doner: (hazir_mi, surum). hazir_mi True ise paket kurulmayi bekliyor;
    kurulumu baslatmak cagirana ait (apply_and_restart).

    `root` yalnizca eski imzayi korumak icin duruyor ve kullanilmiyor.
    """
    if not ota_update.updates_supported():
        return False, ""

    from PySide6.QtCore import QEventLoop

    result = {"ready": False, "version": ""}
    loop = QEventLoop()
    runner = _ThreadRunner(None)

    def _done_ok(version: str, _notes: str) -> None:
        result["ready"] = True
        result["version"] = version
        loop.quit()

    def _done_none() -> None:
        loop.quit()

    def _done_fail(_msg: str) -> None:
        loop.quit()

    runner.worker.staged.connect(_done_ok)
    runner.worker.nothing.connect(_done_none)
    runner.worker.failed.connect(_done_fail)
    if on_progress:
        runner.worker.progress.connect(on_progress)
    if on_stage:
        runner.worker.verifying.connect(lambda _v: on_stage())

    runner.start()
    loop.exec()
    runner.stop()
    return result["ready"], result["version"]


def apply_and_restart(version: str) -> bool:
    """Kurgulanmis surumu kurar ve sureci SERT bicimde kapatir; takas
    betigi tam olarak bunu bekliyor. Basarisizsa False doner ve hicbir sey
    olmaz — cagiran eski surumle devam edebilir."""
    if not ota_update.updates_supported() or not version:
        return False
    staged = ota_update.ota_root() / "Versions" / version
    if not staged.is_dir():
        return False
    # Takastan once yazilir: sonrasi yok, bu surec birazdan oluyor.
    ota_update.write_pending_notes(version)
    if not ota_update.apply_staged(staged):
        return False
    ota_update.quit_now(0)
    return True  # pragma: no cover - quit_now doner donmez


# -- Oturum ici denetleyici ----------------------------------------------
class InSessionUpdateChecker(QObject):
    """Program acikken calisan denetleyici.

    Yeni surum bulundugu anda ekranin ortasinda UpdateCenterOverlay acilir
    ve indirme KENDILIGINDEN baslar; kullanicinin bir sey onaylamasi
    gerekmez. Onay yalnizca en sonda, yeniden baslatma icin sorulur —
    calisma ortasinda kendiliginden kapanan bir program olmasin diye.

    on_before_restart: yeniden baslatmadan hemen once cagrilir ve False
    donerse baslatma iptal edilir (ornegin kullanici kaydetme penceresini
    iptal ettiyse).
    """

    def __init__(self, parent: QWidget, on_before_restart=None):
        super().__init__(parent)
        self._parent = parent
        self._on_before_restart = on_before_restart
        self._overlay = None
        self._runner: _ThreadRunner | None = None
        self._busy = False
        self._manual = False
        self._downloading_version = ""  # su an iniyor
        self._pending_version = ""      # inmis, kurulmayi bekliyor
        self._declined_version = ""

        self._timer = QTimer(parent)
        self._timer.timeout.connect(self.check_silently)
        if ota_update.updates_supported():
            QTimer.singleShot(FIRST_CHECK_DELAY_MS, self.check_silently)
            self._timer.start(IN_SESSION_POLL_MS)

    # --- Kaplama ---------------------------------------------------------
    def _ensure_overlay(self):
        if self._overlay is None:
            from update_overlay import UpdateCenterOverlay

            self._overlay = UpdateCenterOverlay(self._parent)
            self._overlay.restart_requested.connect(self._do_restart)
            self._overlay.dismissed.connect(self._on_dismissed)
        return self._overlay

    # --- Denetim ---------------------------------------------------------
    def check_silently(self) -> None:
        self._check(manual=False)

    def check_now(self) -> None:
        """Menuden elle denetim: sonuc ne olursa olsun kullaniciya bir sey
        gosterilir, cunku denetimi kullanici istedi."""
        self._check(manual=True)

    def _check(self, manual: bool) -> None:
        if not ota_update.updates_supported():
            if manual:
                self._ensure_overlay().show_failed(
                    "Bu derlemede guncelleme motoru bulunmuyor."
                )
            return
        if self._busy:
            if manual and self._pending_version:
                self._ensure_overlay().show_ready(self._pending_version)
            return

        # Indirilmis ama kullanicinin "daha sonra" dedigi bir surum varsa
        # onu tekrar tekrar onune koymanin anlami yok; elle denetimde
        # yeniden gosterilir.
        if self._pending_version and not manual:
            return

        self._manual = manual
        self._busy = True
        if manual:
            self._ensure_overlay().show_checking()

        self._runner = _ThreadRunner(self._parent)
        w = self._runner.worker
        w.found.connect(self._on_found)
        w.progress.connect(self._on_progress)
        w.verifying.connect(self._on_verifying)
        w.staged.connect(self._on_staged)
        w.nothing.connect(self._on_nothing)
        w.failed.connect(self._on_failed)
        self._runner.start()

    # --- Sinyaller (ana is parcacigi) ------------------------------------
    def _on_found(self, version: str, total_bytes: int) -> None:
        # Sessiz denetimde bile kaplama BURADA acilir: indirilecek gercek
        # bir sey var demektir. Anasayfadaki senkron penceresinin davranisi
        # da aynidir (bkz. HomeDashboard._on_sync_started).
        self._downloading_version = version
        self._ensure_overlay().show_downloading(0, total_bytes, version)

    def _on_progress(self, downloaded: int, total: int) -> None:
        if self._overlay is not None:
            self._overlay.show_downloading(downloaded, total, self._downloading_version)

    def _on_verifying(self, version: str) -> None:
        self._ensure_overlay().show_staging(version)

    def _on_staged(self, version: str, notes: str) -> None:
        self._finish_thread()
        self._downloading_version = ""
        self._pending_version = version
        if version and version == self._declined_version and not self._manual:
            return  # kullanici bu surumu zaten erteledi
        self._ensure_overlay().show_ready(version, notes)

    def _on_nothing(self) -> None:
        self._finish_thread()
        if self._manual:
            self._ensure_overlay().show_up_to_date()

    def _on_failed(self, message: str) -> None:
        self._finish_thread()
        was_visible = self._overlay is not None and self._overlay.isVisible()
        self._downloading_version = ""
        # Sessiz denetimin basarisizligi sessiz kalir (cevrimdisi olmak
        # hata degil) — AMA kaplama zaten aciksa kullanici bir seyin
        # indigini gormus demektir; o pencereyi yarida birakip kaybolmak
        # olmaz, ne oldugu soylenir.
        if self._manual or was_visible:
            self._ensure_overlay().show_failed(message)

    def _finish_thread(self) -> None:
        self._busy = False
        if self._runner is not None:
            self._runner.stop()
            self._runner = None

    # --- Kullanici karari -------------------------------------------------
    def _on_dismissed(self) -> None:
        self._declined_version = self._pending_version

    def _do_restart(self) -> None:
        if self._on_before_restart is not None:
            try:
                if self._on_before_restart() is False:
                    if self._overlay is not None:
                        self._overlay.show_ready(self._pending_version)
                    return
            except Exception:
                pass  # kaydetme sorunu guncellemeyi engellemesin
        if not apply_and_restart(self._pending_version):
            if self._overlay is not None:
                self._overlay.show_failed(
                    "Guncelleme baslatilamadi. Programi kapatip tekrar deneyin."
                )


def start_in_session_checker(parent: QWidget, on_before_restart=None):
    """Denetleyiciyi ana pencereye baglar. Referansi pencerede tutulur:
    yerel bir degiskende birakilsa Python nesneyi toplar ve zamanlayici
    hicbir zaman atesle(n)mez."""
    checker = InSessionUpdateChecker(parent, on_before_restart=on_before_restart)
    parent._bk_update_checker = checker  # noqa: SLF001
    return checker
