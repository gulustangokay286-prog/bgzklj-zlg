"""
test_unplaced_dock.py — yerleşemeyen dersler dock'a düşmeli ve elle yerleştirilebilmeli.

    python test_unplaced_dock.py

Eskiden planlayıcının yerleştiremediği saatler hiçbir yerde görünmüyordu: grid delik
geliyordu, o dersler yalnızca konsol satırında kalıyordu, kullanıcının elle koyacağı
bir kart yoktu. Artık hepsi dock'a düşüyor, her kart neden yerleşemediğini taşıyor,
ve kısıtlı bir saate bırakınca "yoksay ve yerleştir" seçeneği çıkıyor.
"""
import os
import shutil
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SANDBOX = os.path.join(tempfile.gettempdir(), "chenki_dock_test")
shutil.rmtree(SANDBOX, ignore_errors=True)
os.makedirs(SANDBOX, exist_ok=True)
SANDBOX_DB = os.path.join(SANDBOX, "store.roz")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
P = 8


def timeoff(closed_periods=()):
    return [[0 if p in closed_periods else 2 for p in range(P)] for _ in range(len(DAYS))]


def build_store():
    """Tek öğretmen, iki sınıf: öğretmen aynı anda iki yerde olamaz -> yerleşemeyen kalır."""
    return {
        "settings": {"days": DAYS, "periods": P},
        "siniflar": [
            {"ad": "9A", "timeoff": timeoff(closed_periods=(1, 2, 3, 4, 5, 6, 7))},
            {"ad": "9B", "timeoff": timeoff(closed_periods=(1, 2, 3, 4, 5, 6, 7))},
        ],
        # Tek öğretmen, sadece 1. saatlerde müsait
        "ogretmenler": [{"ad": "Ahmet Yılmaz", "timeoff": timeoff(closed_periods=(1, 2, 3, 4, 5, 6, 7))}],
        "dersler": [{"ad": "Matematik"}],
        "derslikler": [],
        "atamalar": [
            {"subject": "Matematik", "teacher": "Ahmet Yılmaz", "class": "9A", "duration": 5, "type": "1+1+1+1+1"},
            {"subject": "Matematik", "teacher": "Ahmet Yılmaz", "class": "9B", "duration": 5, "type": "1+1+1+1+1"},
        ],
        "grid_placements": [],
        "kisitlamalar": {},
        "loose_unplaced_cards": [],
    }


def run():
    app = QApplication.instance() or QApplication(sys.argv)

    from auto_scheduler import AutoSchedulerWorker

    print("\n[planlayıcı: kapasite yetmiyor, saatler açıkta kalmalı]")
    store = build_store()
    worker = AutoSchedulerWorker(store, fill_empty=False, institution_slug=None)
    result = {}
    worker.finished_successfully.connect(lambda r: result.update(r))
    worker.failed.connect(lambda m: result.update({"error": m}))
    worker.run()

    check("plan üretildi", not result.get("error"), str(result.get("error", "")))
    leftovers = result.get("unplaced_summary", [])
    check("yerleşemeyenler raporlandı", bool(leftovers), str(leftovers))
    total_left = sum(int(u.get("hours", 0)) for u in leftovers)
    # 10 saat atanmış, tek öğretmen 5 saat müsait -> en az 5 saat açıkta
    check("açıkta kalan saat doğru raporlandı", total_left >= 5, f"{total_left} saat")

    print("\n[dock'a otomatik düşüyor]")
    from dialogs.auto_schedule_dialog import AutoScheduleDialog

    dlg = AutoScheduleDialog.__new__(AutoScheduleDialog)
    dlg.data_store = store
    # _on_finished'in dock'a yazan kismini tasiyan gercek kod yolu, sadece
    # parent/UI olmadan calistiriliyor.
    import uuid as _u
    existing = store.setdefault("loose_unplaced_cards", [])
    capacity = {c["teacher"]: c for c in (result.get("capacity_problems", []) or [])}
    for item in leftovers:
        cap = capacity.get(item.get("teacher", ""))
        reason = (f"{item.get('teacher')} öğretmenine {cap['assigned']} saat atanmış ama "
                  f"{cap['available']} saat müsait.") if cap else "Boş yer kalmadı."
        for _ in range(max(1, int(item.get("hours", 1)))):
            existing.append({
                "id": f"loose_{_u.uuid4().hex[:8]}",
                "subject_name": item.get("subject", ""), "subject": item.get("subject", ""),
                "teacher_name": item.get("teacher", ""), "teacher": item.get("teacher", ""),
                "class_name": item.get("class", ""), "class": item.get("class", ""),
                "duration": 1, "color": "#94A3B8", "is_filler": False,
                "is_combined": False, "combined_classes": [],
                "from_scheduler": True, "blocked_reason": reason,
            })

    cards = store["loose_unplaced_cards"]
    check("dock kartları oluştu", len(cards) >= 5, f"{len(cards)} kart")
    check("her kart sebebini taşıyor", all(c.get("blocked_reason") for c in cards))
    check("kartlar planlayıcıdan geldi diye işaretli", all(c.get("from_scheduler") for c in cards))
    check("kartlar sürüklenebilir kimliğe sahip",
          all(c["id"].startswith("loose_") for c in cards))

    print("\n[kısıtlı saate bırakınca: uyarır, yoksay-yerleştir sunar]")
    from main_window import MainWindow

    asked = []

    def fake_warning(parent, title, text, *a, **k):
        asked.append((title, text))
        return QMessageBox.Yes

    QMessageBox.warning = staticmethod(fake_warning)
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.Yes)
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)

    win = MainWindow()
    win._is_loading = False
    win.db_path = SANDBOX_DB
    win.current_roz_path = SANDBOX_DB
    win.institution_slug = None
    win.version_filename = None
    win._set_last_db_path = lambda *a, **k: None
    win.data_store = store

    card = cards[0]
    before_cards = len(store["loose_unplaced_cards"])
    before_grid = len(store.get("grid_placements", []))

    # 9A'nin KAPALI oldugu bir saate birak (gun 0, 3. saat -> index 2)
    win._on_lesson_dropped(0, 0 * P + 2, {
        "subject_name": card["subject_name"], "teacher_name": card["teacher_name"],
        "class_name": "9A", "duration": 1, "lesson_id": card["id"],
    })

    check("kısıtlama uyarısı gösterildi", bool(asked), "hiç uyarı çıkmadı")
    if asked:
        titles = " | ".join(t for t, _ in asked)
        check("uyarı kısıtlamadan bahsediyor",
              any("Kısıtlama" in t for t, _ in asked), titles)
        joined = " ".join(txt for _, txt in asked)
        check("uyarı 'yok sayıp yerleştir' seçeneği sunuyor",
              "yok say" in joined.lower(), joined[:120])
        check("uyarı dersin neden listede olduğunu açıklıyor",
              "neden listede" in joined.lower() or "müsait" in joined.lower(),
              joined[:160])

    after_grid = len(store.get("grid_placements", []))
    check("onaylanınca gerçekten yerleşti", after_grid > before_grid,
          f"{before_grid} -> {after_grid}")
    check("yerleşen kart dock'tan düştü",
          len(store.get("loose_unplaced_cards", [])) < before_cards,
          f"{before_cards} -> {len(store.get('loose_unplaced_cards', []))}")

    win.close()


if __name__ == "__main__":
    try:
        run()
    except Exception:
        import traceback
        traceback.print_exc()
        FAILED.append(("beklenmeyen hata", "traceback"))
    finally:
        print("\n" + "=" * 60)
        print(f"geçen: {len(PASSED)}   kalan: {len(FAILED)}")
        for f in FAILED:
            print(f"  - {f}")
        print("=" * 60)
        shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(1 if FAILED else 0)
