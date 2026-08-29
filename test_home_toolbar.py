"""
test_home_toolbar.py — anasayfadaki Yenile ve Veri Aktar düğmeleri.

    python test_home_toolbar.py

  * Yenile düğmesi görünür, buluttan çeker ve panelleri yeniden kurar.
  * Veri Aktar düğmesi HER kullanıcıda görünür (yönetici olmayanda da) ve kurum
    seçili değilken bile makul bir hedef seçip açılır.
  * Uygulama açılışta, başka cihazdan gelen klasör/çizelge var mı diye buluttan
    çeker.
"""
import json
import os
import shutil
import sys
import tempfile
import types

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SANDBOX = os.path.join(tempfile.gettempdir(), "chenki_toolbar_test")
shutil.rmtree(SANDBOX, ignore_errors=True)
os.makedirs(SANDBOX, exist_ok=True)

import version_store  # noqa: E402

version_store._base_dir = lambda: os.path.join(SANDBOX, "institutions")

PULLS = []


class _NullCloud:
    def __getattr__(self, name):
        if name == "pull_all_from_rtdb":
            def _pull(*a, **k):
                PULLS.append(a)
                return True, "ok", 0
            return _pull
        if name in ("CloudSyncWorker", "RealtimeSyncClient"):
            class _W:
                def __init__(self, *a, **k):
                    pass

                def __getattr__(self, _n):
                    return lambda *a, **k: True
            return _W
        return lambda *a, **k: True


class _FakeApi:
    base_url = "http://localhost.invalid"
    token = None

    def is_admin(self):
        return False          # YÖNETİCİ DEĞİL: Veri Aktar yine de görünmeli

    def get_current_role(self):
        return "user"

    def get_latest_release(self):
        return None

    def __getattr__(self, _n):
        return lambda *a, **k: True


cloud_stub = types.ModuleType("cloud_sync")
for _n in ("pull_all_from_rtdb", "push_all_to_rtdb", "push_version_to_rtdb",
           "push_institution_to_rtdb", "CloudSyncWorker", "RealtimeSyncClient"):
    setattr(cloud_stub, _n, getattr(_NullCloud(), _n))
sys.modules["cloud_sync"] = cloud_stub

api_stub = types.ModuleType("api_client")
api_stub.api_client = _FakeApi()
api_stub.token_manager = api_stub.api_client
sys.modules["api_client"] = api_stub

db_stub = types.ModuleType("database")
db_stub.trigger_save_db = lambda *a, **k: True
db_stub.create_database_backup = lambda *a, **k: True
sys.modules["database"] = db_stub

from PySide6.QtWidgets import QApplication  # noqa: E402

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def make_institution(slug, name):
    root = os.path.join(SANDBOX, "institutions", slug)
    os.makedirs(os.path.join(root, "versions"), exist_ok=True)
    with open(os.path.join(root, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"name": name}, f)


def run():
    app = QApplication.instance() or QApplication(sys.argv)
    make_institution("kurum_a", "Kurum A")
    make_institution("kurum_b", "Kurum B")

    from home_dashboard import HomeDashboard

    auth = {"email": "user@example.com", "role": "user"}
    dash = HomeDashboard(auth_data=auth)

    print("\n[açılışta buluttan kontrol]")
    check("açılışta pull_all_from_rtdb çağrıldı", len(PULLS) >= 1, f"{len(PULLS)} çağrı")

    print("\n[Yenile düğmesi]")
    check("Yenile düğmesi var", hasattr(dash, "btn_refresh"))
    check("Yenile düğmesi görünür durumda", dash.btn_refresh.isEnabled())
    before = len(PULLS)
    dash._sync_in_flight = False
    dash._on_manual_refresh()
    import time
    deadline = time.time() + 5
    while time.time() < deadline and not dash.btn_refresh.isEnabled():
        app.processEvents()
        time.sleep(0.02)
    check("Yenile buluttan çekti", len(PULLS) > before, f"{before} -> {len(PULLS)}")
    check("Yenile bitince düğme tekrar aktif", dash.btn_refresh.isEnabled())

    print("\n[Veri Aktar düğmesi]")
    check("Veri Aktar düğmesi var", hasattr(dash, "btn_import"))
    check("yönetici olmayan kullanıcıda da açık", dash.btn_import.isEnabled())
    from api_client import api_client
    check("kullanıcı gerçekten yönetici değil", api_client.is_admin() is False)

    # Kurum secili degilken bile makul bir hedef secilmeli (uyari ile geri
    # cevrilmemeli); dialogu acmadan sadece hedef secimini dogruluyoruz.
    dash._selected_slug = None
    opened = {}
    import home_dashboard as hd

    class _FakeDlg:
        def __init__(self, slug, parent=None):
            opened["slug"] = slug

        def exec(self):
            return 0

    real_dlg = hd.CrossImportDialog
    hd.CrossImportDialog = _FakeDlg
    try:
        dash._on_cross_import_clicked()
    finally:
        hd.CrossImportDialog = real_dlg
    check("kurum seçili değilken de hedef bulundu", bool(opened.get("slug")),
          str(opened))

    dash.close()
    dash.deleteLater()


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # pragma: no cover
        import traceback
        traceback.print_exc()
        FAILED.append(("beklenmeyen hata", str(exc)))

    print("\n" + "=" * 60)
    print(f"geçen: {len(PASSED)}   kalan: {len(FAILED)}")
    for name, detail in FAILED:
        print(f"  - {name} {detail}")
    print("=" * 60)
    sys.exit(1 if FAILED else 0)
