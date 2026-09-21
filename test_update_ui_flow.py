"""
test_update_ui_flow.py — guncelleme akisinin ARAYUZ tarafi.

test_ota_update.py agi ve chunk'lari dogruluyor; burasi onun uzerindeki Qt
katmanini dogruluyor: is parcacigindan gelen sinyaller ana is parcacigina
dogru tasiniyor mu, ortadaki pencere dogru sirayla dogru durumlari
gosteriyor mu, "Daha Sonra" gercekten erteliyor mu, ve en onemlisi —
kaydedilmemis calisma varken yeniden baslatma gercekten iptal ediliyor mu.

Ag KULLANMAZ: OtaClient sahtesiyle degistirilir, cunku burada denenen sey
sunucu degil kablolama. 300 MB indirip arayuz testi yapmanin da anlami yok.

    python test_update_ui_flow.py
"""
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

import bk_update  # noqa: E402
import ota_update  # noqa: E402

_app = QApplication.instance() or QApplication([])


def _pump(ms: int = 400) -> None:
    """Olay dongusunu kisa sure dondur: arka plan is parcaciginin
    sinyalleri ancak boyle ana is parcacigina teslim edilir."""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


class FakeOtaClient:
    """Gercek OtaClient'in bu akista kullanilan yuzeyi kadari."""

    behaviour = "update"      # "update" | "none" | "error"
    version = "9.9.9"
    total = 40 * 1024 * 1024
    prepared = False

    def __init__(self, current_version=None):
        self.current_version = current_version
        type(self).prepared = False

    def ensure_registered(self):
        pass

    def heartbeat(self):
        pass

    def check(self):
        if type(self).behaviour == "error":
            raise RuntimeError("sunucu yok")
        if type(self).behaviour == "none":
            return None
        return ota_update.UpdateInfo(
            release_id="rel_test", version=type(self).version,
            notes="Test notu", total_size_bytes=type(self).total,
        )

    def staged_dir(self, version):
        return None

    def prepare(self, info, on_progress=None, on_stage=None):
        for done in (0.25, 0.60, 1.0):
            if on_progress:
                on_progress(int(type(self).total * done), type(self).total)
        if on_stage:
            on_stage()
        type(self).prepared = True
        return "staged-path"


class UpdateFlowTest(unittest.TestCase):
    def setUp(self):
        self.host = QWidget()
        self.host.resize(900, 600)
        # Kaplama kabugun COCUGU; ebeveyn gorunur degilse cocuk da
        # gorunmez. Gercek uygulamada kabuk her zaman aciktir.
        self.host.show()
        self._real_client = ota_update.OtaClient
        ota_update.OtaClient = FakeOtaClient
        FakeOtaClient.behaviour = "update"
        self.applied = []
        self._real_apply = bk_update.apply_and_restart
        bk_update.apply_and_restart = lambda v: (self.applied.append(v), True)[1]

    def tearDown(self):
        ota_update.OtaClient = self._real_client
        bk_update.apply_and_restart = self._real_apply
        self.host.deleteLater()

    def _checker(self, on_before_restart=None):
        checker = bk_update.InSessionUpdateChecker(self.host, on_before_restart=on_before_restart)
        checker._timer.stop()  # testte periyodik denetim istemiyoruz
        return checker

    # --- Ana akis --------------------------------------------------------
    def test_sheet_opens_by_itself_and_downloads(self):
        """Kullanicinin asil istedigi davranis: yeni surum varsa ekranin
        ortasinda pencere KENDILIGINDEN acilsin ve indirme kendi
        baslasin — kimse bir sey onaylamasin."""
        checker = self._checker()
        checker.check_silently()
        _pump()

        self.assertIsNotNone(checker._overlay, "pencere hic acilmadi")
        self.assertTrue(checker._overlay.isVisible(), "pencere kendiliginden acilmadi")
        self.assertTrue(FakeOtaClient.prepared, "indirme kendiliginden baslamadi")
        self.assertEqual(checker._pending_version, "9.9.9")
        self.assertIn("Hazır", checker._overlay.title_lbl.text())
        self.assertTrue(checker._overlay.actions.isVisible(), "karar dugmeleri gorunmuyor")

    def test_silent_check_stays_silent_when_up_to_date(self):
        """Guncelken arka plan denetimi HICBIR sey gostermemeli; 10
        dakikada bir "zaten guncelsiniz" penceresi acmak kullaniciyi
        bikmaktan baska ise yaramaz."""
        FakeOtaClient.behaviour = "none"
        checker = self._checker()
        checker.check_silently()
        _pump()
        self.assertTrue(checker._overlay is None or not checker._overlay.isVisible())

    def test_manual_check_always_answers(self):
        """Elle denetimde ise sonuc ne olursa olsun bir cevap gorunmeli —
        denetimi kullanici istedi."""
        FakeOtaClient.behaviour = "none"
        checker = self._checker()
        checker.check_now()
        _pump()
        self.assertIsNotNone(checker._overlay)
        self.assertTrue(checker._overlay.isVisible())
        self.assertIn("Güncel", checker._overlay.title_lbl.text())

    def test_silent_failure_is_silent(self):
        """Cevrimdisi olmak hata degil: arka plan denetimi sessizce
        vazgecer, kullaniciya kirmizi pencere gostermez."""
        FakeOtaClient.behaviour = "error"
        checker = self._checker()
        checker.check_silently()
        _pump()
        self.assertTrue(checker._overlay is None or not checker._overlay.isVisible())

    def test_manual_failure_is_reported(self):
        FakeOtaClient.behaviour = "error"
        checker = self._checker()
        checker.check_now()
        _pump()
        self.assertIn("Yapılamadı", checker._overlay.title_lbl.text())

    # --- Kullanici karari ------------------------------------------------
    def test_restart_applies_update(self):
        checker = self._checker()
        checker.check_silently()
        _pump()
        checker._overlay.btn_restart.click()
        _pump(120)
        self.assertEqual(self.applied, ["9.9.9"])

    def test_unsaved_work_cancels_restart(self):
        """EN KRITIK DAVRANIS: kullanici kaydetme penceresini iptal
        ederse guncelleme yuzunden program kapanmamali. Bir guncelleme
        hicbir kosulda calismayi silmemeli."""
        checker = self._checker(on_before_restart=lambda: False)
        checker.check_silently()
        _pump()
        checker._overlay.btn_restart.click()
        _pump(120)
        self.assertEqual(self.applied, [], "kaydetme iptal edilmisken yine de yeniden baslatildi")
        self.assertIn("Hazır", checker._overlay.title_lbl.text(),
                      "iptal sonrasi karar penceresi geri gelmeliydi")

    def test_later_defers_until_manual_check(self):
        """"Daha Sonra" denen surum arka plan denetimlerinde tekrar tekrar
        one surulmemeli; ama kullanici kendisi sorarsa gosterilmeli."""
        checker = self._checker()
        checker.check_silently()
        _pump()
        checker._overlay.btn_later.click()
        self.assertFalse(checker._overlay.isVisible())
        self.assertEqual(checker._declined_version, "9.9.9")

        checker.check_silently()
        _pump(150)
        self.assertFalse(checker._overlay.isVisible(), "ertelenen surum yine one suruldu")

        checker.check_now()
        _pump()
        self.assertTrue(checker._overlay.isVisible(), "elle denetimde gosterilmeliydi")

    # --- Kaplamanin kendisi ----------------------------------------------
    def test_overlay_follows_window_resize(self):
        """Kart her zaman ortada kalmali: pencere boyutlanirken kosede
        asili kalan bir kart, kullanicinin gozunde "bozuk" demektir."""
        checker = self._checker()
        checker.check_silently()
        _pump()
        overlay = checker._overlay

        self.host.resize(1400, 900)
        _pump(120)
        self.assertEqual(overlay.size(), self.host.size())
        expected_x = (overlay.width() - overlay.card.width()) // 2
        self.assertEqual(overlay.card.x(), expected_x)


if __name__ == "__main__":
    unittest.main(verbosity=2)
