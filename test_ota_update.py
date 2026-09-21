"""Uzaktan guncelleme (OTA) yolunun testleri.

Bu testler ag kullanir ve CANLI kontrol duzlemine (updates.chenki.net)
konusur; kasitli olarak oyle. Bu sistemin bugune kadar calismamasinin
sebebi "kod dogru ama sunucuda o uc yok" turunden bir kopukluktu
(/api/updates hic var olmadi) ve sahte bir sunucuya karsi yazilan test
bunu asla yakalayamazdi. Sunucuya ulasilamazsa testler ATLANIR.

Hicbir test yayin yapmaz, hicbir test kurulum klasorune dokunmaz.

    python test_ota_update.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import ota_update

# Sunucuda su an yayinli olan urun/surum; testlerin "bilinen iyi verisi".
KNOWN_PRODUCT = "bkplanner"
KNOWN_VERSION = "3.1.0"
KNOWN_CHANNEL = "stable"

# KNOWN_VERSION'in minimum_version'i 3.0.0. Sunucu, bu esigin ALTINDAKI bir
# surumden dogrudan yukseltmeyi reddeder (meets_minimum). Yukseltme
# testlerinin esigin ustunden baslamasi bu yuzden sart: 0.0.1 ile sorulunca
# cevap bos gelir ve bu bir hata degil, kurala uygun davranistir.
UPGRADABLE_FROM = "3.0.5"


def _server_reachable() -> bool:
    try:
        import requests

        cfg = ota_update.config()
        return requests.get(f"{cfg.api_base_url}/health", timeout=8).status_code == 200
    except Exception:
        return False


SERVER_UP = _server_reachable()
needs_server = unittest.skipUnless(SERVER_UP, "guncelleme sunucusuna ulasilamadi")


def _client_for(product: str, current_version: str):
    """ClientConfig donmus bir dataclass ve alan varsayilanlari MODUL
    YUKLENIRKEN okunuyor; os.environ'i sonradan degistirmek hicbir sey
    yapmaz. Bu yuzden urun adini testte replace() ile degistiriyoruz."""
    import dataclasses

    client = ota_update.OtaClient(current_version)
    client.cfg = dataclasses.replace(client.cfg, product=product)
    return client


_MANIFEST_CACHE = {}


def _manifest():
    """Manifest bir kez indirilir, testler arasinda paylasilir.

    1205 dosyalik bir manifest birkac megabayt; her testte yeniden
    indirmek butun takimi gereksiz yere dakikalarca uzatiyordu."""
    from client.networking.http_client import HttpClient

    if "http" not in _MANIFEST_CACHE:
        cfg = ota_update.config()
        http = HttpClient(cfg.api_base_url, verify_tls=True)
        man = http.get_json(
            f"/v1/releases/{KNOWN_VERSION}/manifest",
            params={"product": KNOWN_PRODUCT, "channel": KNOWN_CHANNEL},
        )
        _MANIFEST_CACHE["http"] = http
        _MANIFEST_CACHE["man"] = man
    import copy

    return _MANIFEST_CACHE["http"], copy.deepcopy(_MANIFEST_CACHE["man"])


def _smallest_real_file(manifest: dict) -> dict:
    """En kucuk ama BOS OLMAYAN dosya. Bos dosyanin hic parcasi yoktur;
    onu secmek parca testlerini sessizce anlamsizlastirirdi."""
    with_chunks = [f for f in manifest["files"] if f["chunks"]]
    return min(with_chunks, key=lambda f: f["size"])


class Configuration(unittest.TestCase):
    def test_engine_available(self):
        """Chunk motoru import edilebilmeli; edilemezse guncelleme tamamen
        devre disi kalir ve bunu sessizce yasamak istemiyoruz."""
        self.assertTrue(ota_update.updates_supported(), "ReleaseSystem/client import edilemedi")

    def test_ota_root_is_separate_and_writable(self):
        """Durum dizini kurulum klasorunden AYRI ve yazilabilir olmali.

        Eski tasarim durumu kurulumun yaninda tutuyordu; Program Files'a
        kurulmus bir uygulamada orasi yazilamaz ve guncelleme daha ilk
        adimda olurdu."""
        root = ota_update.ota_root()
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".test_probe"
        probe.write_text("ok", encoding="utf-8")
        self.assertEqual(probe.read_text(encoding="utf-8"), "ok")
        probe.unlink()

        install = ota_update.install_dir()
        if install is not None:
            self.assertNotEqual(root, install)
            self.assertNotIn(install, root.parents)

    def test_api_url_is_real_and_tls(self):
        """Varsayilan sunucu adresi gercek ve TLS'li olmali: bu deger
        yanlis oldugu icin de bir donem hicbir denetim sonuc vermiyordu."""
        cfg = ota_update.config()
        self.assertTrue(cfg.api_base_url.startswith("https://"))
        self.assertEqual(cfg.platform, "windows-x64")


class ServerConversation(unittest.TestCase):
    @needs_server
    def test_no_update_when_current_is_newer(self):
        """Gercek kurulumun durumu: 5.x calisiyor, sunucuda daha yenisi yok."""
        self.assertIsNone(_client_for(KNOWN_PRODUCT, "99.0.0").check())

    @needs_server
    def test_finds_newer_release(self):
        """Eski bir surumdeymis gibi sorulunca sunucu gercekten bir surum
        onermeli. "Yayinladim ama kimseye gitmiyor" sikayetinin tam
        kalbindeki cagri bu."""
        info = _client_for(KNOWN_PRODUCT, UPGRADABLE_FROM).check()
        self.assertIsNotNone(info, "sunucu yayinli surumu onermedi")
        self.assertEqual(info.version, KNOWN_VERSION)
        self.assertGreater(info.total_size_bytes, 0)
        self.assertTrue(info.release_id)

    @needs_server
    def test_unknown_product_yields_nothing(self):
        """Urun adi sunucudakiyle tutmazsa denetim sessizce bos doner —
        istemcinin varsayilani ile sunucudaki urun adinin ayni olmasi bu
        yuzden kritik; publish_update.py ikisini de ayni yerden aliyor."""
        self.assertIsNone(_client_for("boyle-bir-urun-yok", UPGRADABLE_FROM).check())

    @needs_server
    def test_minimum_version_blocks_upgrade(self):
        """SESSIZ TUZAK, kayit altina aliniyor: surumun minimum_version'i
        kullanicinin surumunden yuksekse guncelleme HIC onerilmez ve
        istemci tarafinda hicbir hata gorunmez — "yayinladim, kimseye
        gitmedi" tablosunun bir baska sebebi budur.

        publish_update.py bu yuzden --minimum-version'i varsayilan olarak
        BOS birakir; elle verilecekse ne yaptigini bilerek verilmeli."""
        self.assertIsNone(_client_for(KNOWN_PRODUCT, "0.0.1").check())
        self.assertIsNotNone(_client_for(KNOWN_PRODUCT, UPGRADABLE_FROM).check())


class ManifestTrust(unittest.TestCase):
    @needs_server
    def test_signature_verifies(self):
        """Manifest, exe'ye gomulu ACIK anahtarla dogrulanmali. Bu koparsa
        istemci hicbir guncellemeyi kurmaz."""
        from client.security.signature import verify_manifest

        _, man = _manifest()
        self.assertIsNotNone(man)
        verify_manifest(man)  # imza tutmazsa SignatureError
        self.assertTrue(man["files"])

    @needs_server
    def test_tampered_manifest_rejected(self):
        """Imza dogrulamasinin gercekten bir sey yaptiginin kaniti: tek bir
        alani degistirilen manifest reddedilmeli."""
        from client.security.signature import SignatureError, verify_manifest

        _, man = _manifest()
        man["files"][0]["sha256"] = "0" * 64
        with self.assertRaises(SignatureError):
            verify_manifest(man)


class ChunkPipeline(unittest.TestCase):
    @needs_server
    def test_download_and_assemble_file(self):
        """Bir dosyayi parcalarindan indirip birlestirir ve butun dosyanin
        sha256'sini dogrular — kurgulama adiminin kucuk olcekli provasi."""
        from client.state.paths import Layout
        from client.updater import chunk_store, installer
        from client.updater.verifier import verify_assembled_file

        http, man = _manifest()
        entry = _smallest_real_file(man)

        tmp = Path(tempfile.mkdtemp(prefix="ota_test_"))
        try:
            layout = Layout(tmp)
            layout.ensure_all()
            for chunk in entry["chunks"]:
                dest = layout.chunk_partial_path(chunk["hash"])
                http.download_to_file(
                    f"{http.base_url}/v1/chunks/{chunk['hash']}?product={KNOWN_PRODUCT}", dest
                )
                chunk_store.commit_partial(layout, chunk["hash"], dest)
                self.assertTrue(chunk_store.has_chunk(layout, chunk["hash"]))

            out = tmp / "assembled.bin"
            installer.assemble_file(layout, out, entry["chunks"])
            verify_assembled_file(out, entry["sha256"])  # tutmazsa VerificationError
            self.assertEqual(out.stat().st_size, entry["size"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @needs_server
    def test_cached_chunk_not_refetched(self):
        """Icerik-tanimli chunk'lamanin butun amaci: onbellekteki parca
        ikinci kez istenmez. Bozulursa her guncelleme yine 300 MB olur."""
        from client.state.paths import Layout
        from client.updater import chunk_store

        http, man = _manifest()
        entry = _smallest_real_file(man)
        chunk_hash = entry["chunks"][0]["hash"]

        tmp = Path(tempfile.mkdtemp(prefix="ota_cache_"))
        try:
            layout = Layout(tmp)
            layout.ensure_all()
            self.assertFalse(chunk_store.has_chunk(layout, chunk_hash))

            dest = layout.chunk_partial_path(chunk_hash)
            http.download_to_file(
                f"{http.base_url}/v1/chunks/{chunk_hash}?product={KNOWN_PRODUCT}", dest
            )
            chunk_store.commit_partial(layout, chunk_hash, dest)

            sizes = {c["hash"]: c["size"] for c in entry["chunks"]}
            missing = [h for h in sizes if not chunk_store.has_chunk(layout, h)]
            self.assertNotIn(chunk_hash, missing)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_corrupt_chunk_rejected(self):
        """Bozuk indirilen parca onbellege KONMAMALI; yoksa bozuk bayt
        kalici olur ve her kurgulama bastan basarisiz olur."""
        from client.state.paths import Layout
        from client.updater import chunk_store
        from client.updater.verifier import VerificationError

        tmp = Path(tempfile.mkdtemp(prefix="ota_corrupt_"))
        try:
            layout = Layout(tmp)
            layout.ensure_all()
            fake_hash = "a" * 64
            part = layout.chunk_partial_path(fake_hash)
            part.parent.mkdir(parents=True, exist_ok=True)
            part.write_bytes(b"bu baytlarin hash'i tutmuyor")

            with self.assertRaises(VerificationError):
                chunk_store.commit_partial(layout, fake_hash, part)
            self.assertFalse(chunk_store.has_chunk(layout, fake_hash))
            self.assertFalse(part.exists(), "bozuk .part dosyasi silinmeliydi")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class SwapStep(unittest.TestCase):
    def test_script_never_mirrors(self):
        """robocopy asla /MIR veya /PURGE ile cagrilmamali: kurulum
        klasorunde Inno Setup'in kaldirma dosyalari duruyor ve aynalama
        onlari silerdi — program bir daha kaldirilamazdi."""
        staged = Path(tempfile.mkdtemp(prefix="ota_staged_"))
        target = Path(tempfile.mkdtemp(prefix="ota_target_"))
        try:
            script = ota_update._write_swap_script(staged, target, target / "Chenkron.exe")
            body = script.read_text(encoding="utf-8")
            self.assertIn("robocopy", body)
            self.assertNotIn("/MIR", body)
            self.assertNotIn("/PURGE", body)
            self.assertIn(str(staged), body)
            self.assertIn(str(target), body)
            self.assertIn("goto waitloop", body, "surec olmeden kopyalamaya baslamamali")
        finally:
            shutil.rmtree(staged, ignore_errors=True)
            shutil.rmtree(target, ignore_errors=True)

    def test_script_uses_absolute_tool_paths(self):
        """GERCEK BIR HATANIN TESTI. Betik once `tasklist | find` yaziyordu.
        Kullanicinin PATH'inde System32'den once gelen bir dizin varsa
        (Git for Windows'un usr\\bin'i icinde Unix'in `find`'i var) ciplak
        `find` bambaska bir program calistiriyor, kosul yanlis sonuclaniyor
        ve betik uygulama HALA ACIKKEN kopyalamaya basliyordu — yani
        calisan .exe'nin uzerine yazmaya calisiyordu.

        Cozum: butun araclar %SystemRoot%\\System32 altindan tam yolla."""
        staged = Path(tempfile.mkdtemp(prefix="ota_staged_"))
        target = Path(tempfile.mkdtemp(prefix="ota_target_"))
        try:
            body = ota_update._write_swap_script(
                staged, target, target / "Chenkron.exe"
            ).read_text(encoding="oem" if sys.platform == "win32" else "utf-8")
            for tool in ("tasklist.exe", "find.exe", "ping.exe", "robocopy.exe"):
                self.assertIn(f'"%SYS%\\{tool}"', body, f"{tool} tam yolla cagrilmiyor")
            self.assertIn('set "SYS=%SystemRoot%\\System32"', body)
            self.assertIn("goto giveup", body, "bekleme dongusunun ust siniri yok")
        finally:
            shutil.rmtree(staged, ignore_errors=True)
            shutil.rmtree(target, ignore_errors=True)

    @unittest.skipUnless(sys.platform == "win32", "gercek surec bekleme testi")
    def test_script_waits_for_process_to_exit(self):
        """Betigi GERCEKTEN calistirir: surec yasarken hicbir seye
        dokunmamali, surec olunce kopyalamali. Bu yolun sessizce bozulmasi
        "guncelleme geldi ama program acilmiyor" demek olurdu."""
        staged = Path(tempfile.mkdtemp(prefix="ota_wait_s_"))
        target = Path(tempfile.mkdtemp(prefix="ota_wait_t_"))
        victim = None
        runner = None
        try:
            (staged / "Chenkron.exe").write_text("YENI", encoding="utf-8")
            (target / "Chenkron.exe").write_text("ESKI", encoding="utf-8")

            victim = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(25)"])
            real_getpid = os.getpid
            os.getpid = lambda: victim.pid
            try:
                script = ota_update._write_swap_script(staged, target, Path(sys.executable))
            finally:
                os.getpid = real_getpid

            runner = subprocess.Popen(["cmd", "/c", str(script)])
            time.sleep(4)
            self.assertEqual(
                (target / "Chenkron.exe").read_text(encoding="utf-8"), "ESKI",
                "surec hala calisirken kopyalamis — bekleme dongusu kopuk",
            )

            victim.terminate()
            victim.wait()
            deadline = time.time() + 30
            while time.time() < deadline:
                if (target / "Chenkron.exe").read_text(encoding="utf-8") == "YENI":
                    break
                time.sleep(0.5)
            self.assertEqual(
                (target / "Chenkron.exe").read_text(encoding="utf-8"), "YENI",
                "surec kapandi ama takas yapilmadi",
            )
        finally:
            for proc in (victim, runner):
                if proc is not None and proc.poll() is None:
                    proc.kill()
            shutil.rmtree(staged, ignore_errors=True)
            shutil.rmtree(target, ignore_errors=True)

    @unittest.skipUnless(sys.platform == "win32", "robocopy yalnizca Windows'ta")
    def test_swap_replaces_files_and_keeps_uninstaller(self):
        """Takasin kendisi: betikteki robocopy satiri gercekten eski
        dosyalarin uzerine yaziyor, kaynakta olmayan dosyalara (kaldirici)
        dokunmuyor mu?"""
        staged = Path(tempfile.mkdtemp(prefix="ota_staged_"))
        target = Path(tempfile.mkdtemp(prefix="ota_target_"))
        try:
            (staged / "Chenkron.exe").write_text("YENI", encoding="utf-8")
            (staged / "_internal").mkdir()
            (staged / "_internal" / "lib.dll").write_text("YENI-DLL", encoding="utf-8")

            (target / "Chenkron.exe").write_text("ESKI", encoding="utf-8")
            (target / "unins000.exe").write_text("KALDIRICI", encoding="utf-8")

            subprocess.run(
                ["robocopy", str(staged), str(target), "/E", "/IS", "/IT",
                 "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS"],
                capture_output=True,
            )

            self.assertEqual((target / "Chenkron.exe").read_text(encoding="utf-8"), "YENI")
            self.assertEqual(
                (target / "_internal" / "lib.dll").read_text(encoding="utf-8"), "YENI-DLL"
            )
            self.assertTrue(
                (target / "unins000.exe").exists(), "kaldirici silinmis — aynalama sizmis"
            )
        finally:
            shutil.rmtree(staged, ignore_errors=True)
            shutil.rmtree(target, ignore_errors=True)

    def test_no_swap_from_source_checkout(self):
        """Kaynaktan calisirken takas ASLA yapilmamali: canli bir
        yorumlayicinin altindaki .py agacinin uzerine kopyalamak yapilacak
        en kotu seydir."""
        if ota_update.is_frozen():
            self.skipTest("yalnizca kaynaktan calisirken anlamli")
        staged = Path(tempfile.mkdtemp(prefix="ota_staged_"))
        try:
            self.assertIsNone(ota_update.install_dir())
            self.assertFalse(ota_update.apply_staged(staged))
        finally:
            shutil.rmtree(staged, ignore_errors=True)


class DeadPathsStayDead(unittest.TestCase):
    def test_old_updater_api_raises(self):
        """updater.py'nin eski API'si sessizce geri gelmemeli: o modul
        VDS'te olmayan /api/updates ucunu yokluyor ve her denetimi
        "guncelsiniz" yapiyordu."""
        import updater

        with self.assertRaises(updater.UpdaterRemovedError):
            updater.UpdateChecker  # noqa: B018

    def test_nothing_builds_an_api_updates_url(self):
        """Hicbir yerde olu uca giden bir URL KURULMAMALI.

        Metnin kendisini degil, URL kurulumunu ariyoruz: aciklama
        satirlarinda "/api/updates" gecmesi iyi bir sey (neden olmadigini
        anlatiyor), oraya istek atan kod ise olmamali."""
        import re

        pattern = re.compile(r"""[}'"]\s*/api/updates""")
        offenders = [
            p.name
            for p in Path(__file__).parent.glob("*.py")
            if p.name != Path(__file__).name  # kendi desenimiz sayilmasin
            and pattern.search(p.read_text(encoding="utf-8", errors="replace"))
        ]
        self.assertEqual(offenders, [], f"olu uca giden cagri kalmis: {offenders}")


if __name__ == "__main__":
    if not SERVER_UP:
        print("NOT: guncelleme sunucusuna ulasilamadi — ag testleri atlanacak.\n")
    unittest.main(verbosity=2)
