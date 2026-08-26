"""
test_version_open_roundtrip.py — kaydedilmiş bir versiyonu açmak çizelgeyi GÖSTERMELİ,
kapatmak da onu BOŞALTMAMALI.

    python test_version_open_roundtrip.py

180/180 dolu bir versiyon kaydedildikten sonra dosyada `grid_placements: 0` ile
bulundu: dolu çizelge, açılıp kapanma sırasında kayboluyordu. Bu test o yolu
uçtan uca yürütür — versiyon dosyasından yükle, gridi tazele, kaydet, dosyadan
geri oku — ve hiçbir adımda ders saati eksilmediğini doğrular.

Her şey sandbox'ta çalışır; gerçek ~/.chenki_akademi'ye dokunulmaz.
"""
import json
import os
import shutil
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SANDBOX = os.path.join(tempfile.gettempdir(), "chenki_roundtrip_test")
shutil.rmtree(SANDBOX, ignore_errors=True)
os.makedirs(SANDBOX, exist_ok=True)
SANDBOX_DB = os.path.join(SANDBOX, "store.roz")
INST_ROOT = os.path.join(SANDBOX, "institutions")

import version_store  # noqa: E402

version_store._base_dir = lambda: INST_ROOT

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

PASSED, FAILED = [], []
SLUG = "test_kurumu"
DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
P = 8


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def timeoff(open_periods):
    return [[2 if p in open_periods else 0 for p in range(P)] for _ in DAYS]


def build_store():
    """İki sınıf, günde 2 açık saat, tamamı dolu bir çizelge (20 saat)."""
    classes = ["9A", "9B"]
    teachers = ["Ahmet Yılmaz", "Ayşe Demir"]
    store = {
        "settings": {"days": DAYS, "days_count": 5, "periods": P,
                     "institution_slug": SLUG},
        "siniflar": [{"ad": c, "timeoff": timeoff({0, 1})} for c in classes],
        "ogretmenler": [{"ad": t, "timeoff": timeoff(set(range(P)))} for t in teachers],
        "dersler": [{"ad": "Matematik"}, {"ad": "Fizik"}],
        "derslikler": [],
        "atamalar": [
            {"subject": "Matematik", "teacher": "Ahmet Yılmaz", "class": "9A",
             "duration": 10, "type": "2+2+2+2+2"},
            {"subject": "Fizik", "teacher": "Ayşe Demir", "class": "9B",
             "duration": 10, "type": "2+2+2+2+2"},
        ],
        "kisitlamalar": {},
        "grid_placements": [],
        "loose_unplaced_cards": [],
    }
    pl = []
    for d in range(5):
        for cls, subj, tch in (("9A", "Matematik", "Ahmet Yılmaz"),
                               ("9B", "Fizik", "Ayşe Demir")):
            pl.append({
                "row": 0, "col": d, "period": 0, "day": d,
                "class_name": cls, "class": cls,
                "subject_name": subj, "subject": subj,
                "teacher_name": tch, "teacher": tch,
                "duration": 2, "block_id": f"{cls}_{d}", "locked": False,
                "is_combined": False, "is_filler": False, "color": "#1E88E5",
            })
    store["grid_placements"] = pl
    return store


def hours_of(store):
    return sum(int(p.get("duration", 1) or 1)
               for p in store.get("grid_placements", []) or [])


def run():
    app = QApplication.instance() or QApplication(sys.argv)
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.Yes)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.Yes)
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)

    print("\n[versiyon kaydı]")
    os.makedirs(os.path.join(INST_ROOT, SLUG, "versions"), exist_ok=True)
    with open(os.path.join(INST_ROOT, SLUG, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"name": "Test Kurumu"}, f)

    store = build_store()
    check("başlangıç çizelgesi 20 saat", hours_of(store) == 20, str(hours_of(store)))
    fn = version_store.save_version(SLUG, store, note="test")
    saved = version_store.load_version(SLUG, fn)
    check("kaydedilen dosyada 20 saat duruyor", hours_of(saved) == 20,
          str(hours_of(saved)))

    print("\n[versiyonu açmak]")
    from main_window import MainWindow

    win = MainWindow(override_db_path=SANDBOX_DB, institution_slug=SLUG,
                     version_filename=fn)
    win._is_loading = False
    win.data_store.clear()
    win.data_store.update(version_store.load_version(SLUG, fn))
    win._refresh_grid()
    check("açılışta veri 20 saat", hours_of(win.data_store) == 20,
          str(hours_of(win.data_store)))

    rendered = 0
    table = getattr(win._grid, "table", None)
    if table is not None:
        for r in range(table.rowCount()):
            for c in range(table.columnCount()):
                if table.cellWidget(r, c) is not None or (
                        table.item(r, c) is not None and table.item(r, c).text().strip()):
                    rendered += 1
    check("grid boş değil (ekranda ders var)", rendered > 0, f"{rendered} hücre")

    print("\n[kapanış kaydı çizelgeyi boşaltmıyor]")
    win.save_db(sync_from_grid=True)
    check("kayıttan sonra bellekte 20 saat", hours_of(win.data_store) == 20,
          str(hours_of(win.data_store)))
    back = version_store.load_version(SLUG, fn)
    check("kayıttan sonra dosyada 20 saat", hours_of(back) == 20,
          f"{hours_of(back)} saat")

    print("\n[tek sınıf görünümündeyken kaydetmek diğer sınıfı silmiyor]")
    win.data_store.clear()
    win.data_store.update(version_store.load_version(SLUG, fn))
    if hasattr(win._grid, "set_mode_single_entity"):
        try:
            win._grid.set_mode_single_entity("9A", P, DAYS)
        except Exception:
            pass
    win.save_db(sync_from_grid=True)
    after = version_store.load_version(SLUG, fn)
    per_class = {}
    for p in after.get("grid_placements", []) or []:
        cls = p.get("class_name") or p.get("class")
        per_class[cls] = per_class.get(cls, 0) + int(p.get("duration", 1) or 1)
    check("9B'nin dersleri duruyor", per_class.get("9B", 0) == 10, str(per_class))
    check("9A'nın dersleri duruyor", per_class.get("9A", 0) == 10, str(per_class))

    win.close()
    win.deleteLater()


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
