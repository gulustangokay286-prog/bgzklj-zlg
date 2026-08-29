"""
test_grid_swap.py — gride ders sürüklemek hiçbir dersi SİLMEMELİ.

    python test_grid_swap.py

Eskiden bir dersi doluya bırakınca oradaki ders tamamen gridden siliniyordu; öğretmen
çakışmasında ise BAŞKA bir sınıfın dersi siliniyordu. Artık:
  * grid içinde taşıma + dolu hedef  -> iki ders YER DEĞİŞTİRİR
  * dock'tan bırakma + dolu hedef    -> oradaki ders dock'a döner (silinmez)
  * öğretmen çakışması               -> uyarır, yerleştirir, hiçbir şey silmez
"""
import os
import shutil
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Her yazma islemi buraya gitmeli; gercek ~/.chenki_akademi'ye ASLA dokunulmamali.
SANDBOX = os.path.join(tempfile.gettempdir(), "chenki_swap_test")
shutil.rmtree(SANDBOX, ignore_errors=True)
os.makedirs(SANDBOX, exist_ok=True)
SANDBOX_DB = os.path.join(SANDBOX, "test_store.roz")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def placement(day, period, subject, teacher, cls, block, duration=1):
    return {
        "day": day, "period": period, "row": period, "col": day,
        "class_name": cls, "class": cls,
        "teacher_name": teacher, "teacher": teacher,
        "subject_name": subject, "subject": subject,
        "duration": duration, "block_id": block, "is_manual": True,
        "locked": False, "is_combined": False, "combined_classes": [],
    }


def make_store():
    return {
        "settings": {"days": ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"],
                     "periods": 8},
        "siniflar": [{"ad": "9A"}, {"ad": "9B"}],
        "ogretmenler": [{"ad": "Ahmet Yılmaz"}, {"ad": "Ayşe Demir"}],
        "dersler": [{"ad": "Matematik"}, {"ad": "Fizik"}],
        "derslikler": [],
        "atamalar": [
            {"subject": "Matematik", "teacher": "Ahmet Yılmaz", "class": "9A", "duration": 2, "type": "2"},
            {"subject": "Fizik", "teacher": "Ayşe Demir", "class": "9A", "duration": 2, "type": "2"},
        ],
        "grid_placements": [
            placement(0, 0, "Matematik", "Ahmet Yılmaz", "9A", "blk_mat"),
            placement(0, 3, "Fizik", "Ayşe Demir", "9A", "blk_fiz"),
        ],
        "kisitlamalar": {},
    }


def slot_of(store, subject, cls="9A"):
    for p in store.get("grid_placements", []):
        if ((p.get("subject_name") or p.get("subject")) == subject
                and (p.get("class_name") or p.get("class")) == cls):
            return (int(p.get("day", 0)), int(p.get("period", 0)))
    return None


def run():
    app = QApplication.instance() or QApplication(sys.argv)

    # Her onay kutusuna "Evet" de — kullanıcı "evet evet evet" basıyor senaryosu.
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.Yes)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.Yes)
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)

    import main_window
    from main_window import MainWindow

    print("\n[pencere kurulumu]")
    # override_db_path ZORUNLU. Kurumsuz bir MainWindow, yapici icinde son
    # kullanilan .roz yolunu okuyup ona baglaniyor — yani KULLANICININ aktif
    # versiyonuna. Yolu yapicidan SONRA degistirmek gec kaliyor: kurulum sirasinda
    # gercek dosyaya yaziliyor (iki kez oldu, v082 yedekten geri alindi).
    win = MainWindow(override_db_path=SANDBOX_DB)
    win._is_loading = False

    # MainWindow'u kurumsuz acmak, onu son kullanilan .roz dosyasina baglıyor —
    # yani GERCEK aktif versiyona. save_db cagrildiginda test verisi kullanicinin
    # cizelgesinin uzerine yaziliyordu (bir kez oldu: v082 3 atamalik test verisiyle
    # degisti, yedekten geri alindi). Kayit yolunu sandbox'a sabitle ve bulut
    # senkronunu tamamen kapat.
    win.db_path = SANDBOX_DB
    win.current_roz_path = SANDBOX_DB
    win.institution_slug = None
    win.version_filename = None
    win._set_last_db_path = lambda *a, **k: None

    check("MainWindow açıldı", win is not None)
    check("kayıt yolu sandbox'a sabitlendi", win.db_path == SANDBOX_DB, str(win.db_path))

    periods = 8

    print("\n[grid içinde takas: Matematik -> Fizik'in üstüne]")
    win.data_store = make_store()
    before = len(win.data_store["grid_placements"])
    mat_before = slot_of(win.data_store, "Matematik")
    fiz_before = slot_of(win.data_store, "Fizik")
    check("başlangıçta iki ders var", before == 2 and mat_before and fiz_before,
          f"{before} yerleşim")

    # Matematik'i (gün 0, saat 0) Fizik'in yerine (gün 0, saat 3) sürükle.
    win._on_lesson_dropped(0, 0 * periods + 3, {
        "subject_name": "Matematik", "teacher_name": "Ahmet Yılmaz",
        "class_name": "9A", "duration": 1,
        "is_move": True, "origin_row": 0, "origin_col": 0 * periods + 0,
    })

    after = len(win.data_store["grid_placements"])
    mat_after = slot_of(win.data_store, "Matematik")
    fiz_after = slot_of(win.data_store, "Fizik")

    check("HİÇBİR DERS SİLİNMEDİ", after == before, f"{before} -> {after} yerleşim")
    check("Matematik hedefe taşındı", mat_after == (0, 3), str(mat_after))
    check("Fizik kaynak hücreye taşındı (takas)", fiz_after == (0, 0), str(fiz_after))
    check("iki ders farklı hücrede", mat_after != fiz_after, f"{mat_after} / {fiz_after}")

    print("\n[dock'tan bırakma: yerinden olan ders dock'a döner]")
    win.data_store = make_store()
    win.data_store["loose_unplaced_cards"] = []
    before = len(win.data_store["grid_placements"])

    # Dock'tan yeni bir ders, Fizik'in üstüne (is_move yok).
    win._on_lesson_dropped(0, 0 * periods + 3, {
        "subject_name": "Matematik", "teacher_name": "Ahmet Yılmaz",
        "class_name": "9A", "duration": 1,
    })

    grid_subjects = [(p.get("subject_name") or p.get("subject"))
                     for p in win.data_store["grid_placements"]]
    dock = win.data_store.get("loose_unplaced_cards", [])
    dock_subjects = [(c.get("subject_name") or c.get("subject")) for c in dock]

    check("yeni ders hedefe yerleşti", "Matematik" in grid_subjects, str(grid_subjects))
    check("yerinden olan ders SİLİNMEDİ, dock'a düştü",
          "Fizik" in dock_subjects, f"grid={grid_subjects} dock={dock_subjects}")
    check("dock kartı yeniden yerleştirilebilir",
          bool(dock) and dock[0].get("id", "").startswith("loose_"), str(dock[:1]))

    print("\n[öğretmen çakışması: uyarır ama silmez]")
    store = make_store()
    # Aynı öğretmen, başka sınıfta, aynı saatte.
    store["grid_placements"] = [
        placement(1, 2, "Matematik", "Ahmet Yılmaz", "9B", "blk_other"),
    ]
    store["atamalar"].append(
        {"subject": "Matematik", "teacher": "Ahmet Yılmaz", "class": "9B",
         "duration": 2, "type": "2"})
    win.data_store = store
    before = len(win.data_store["grid_placements"])

    win._on_lesson_dropped(0, 1 * periods + 2, {
        "subject_name": "Matematik", "teacher_name": "Ahmet Yılmaz",
        "class_name": "9A", "duration": 1,
    })

    after = win.data_store["grid_placements"]
    classes = {(p.get("class_name") or p.get("class")) for p in after}
    check("çakışmaya rağmen yerleşti", "9A" in classes, str(classes))
    check("DİĞER SINIFIN DERSİ SİLİNMEDİ", "9B" in classes, str(classes))
    check("yerleşim sayısı arttı, azalmadı", len(after) > before, f"{before} -> {len(after)}")

    conflicted = [p for p in after if p.get("has_conflict")]
    check("çakışma kayda geçti (sonra düzenlenebilsin)", bool(conflicted),
          "has_conflict işareti yok")

    print("\n[2 saatlik ders 1 saatlikleri YUTMAMALI]")
    store = make_store()
    # 3. ve 4. saatte birer 1 saatlik ders
    store["grid_placements"] = [
        placement(0, 3, "Fizik", "Ayşe Demir", "9A", "blk_f"),
        placement(0, 4, "Kimya", "Ayşe Demir", "9A", "blk_k"),
    ]
    store["loose_unplaced_cards"] = []
    win.data_store = store

    # 2 saatlik Matematik'i 3. saate birak -> 3 ve 4'u kaplar
    win._on_lesson_dropped(0, 0 * periods + 3, {
        "subject_name": "Matematik", "teacher_name": "Ahmet Yılmaz",
        "class_name": "9A", "duration": 2,
    })

    dock_subjects = [(c.get("subject_name") or c.get("subject"))
                     for c in win.data_store.get("loose_unplaced_cards", [])]
    grid_subjects = [(p.get("subject_name") or p.get("subject"))
                     for p in win.data_store["grid_placements"]]

    check("2 saatlik ders yerleşti", "Matematik" in grid_subjects, str(grid_subjects))
    check("İLK 1 saatlik ders kurtarıldı", "Fizik" in dock_subjects, str(dock_subjects))
    check("İKİNCİ 1 saatlik ders de kurtarıldı (yutulmadı)",
          "Kimya" in dock_subjects, f"dock={dock_subjects} grid={grid_subjects}")
    check("hiçbir ders yok olmadı",
          len(set(dock_subjects) | set(grid_subjects)) >= 3,
          f"dock={dock_subjects} grid={grid_subjects}")

    print("\n[sürüklerken imlecin altındaki hücre dersin 1. saatidir]")
    from PySide6.QtCore import QPoint
    table = win._grid.table

    # Kart nereden tutulursa tutulsun, bırakma hücresi imlecin altındaki hücredir.
    table.resize(900, 300)
    target = table.visualRect(table.model().index(0, 2)).center()
    for payload in ({}, {"grab_dx": 999, "grab_dy": 999}, {"grab_dx": 40, "grab_dy": 12}):
        anchor = table._drop_anchor(target, payload)
        check(f"tutma noktası hücreyi kaydırmıyor ({payload or 'ofset yok'})",
              table._cell_at(anchor) == (0, 2),
              f"{table._cell_at(anchor)} != (0, 2)")

    # 2 saatlik ders: önizleme her zaman gelinen saatten BAŞLAR (1. saatteysen 1-2,
    # 2. saatteysen 2-3). Eskiden 2. saatin üzerindeyken 1. saati kapsıyordu.
    info2 = {"subject_name": "Matematik", "teacher_name": "Ahmet Yılmaz",
             "class_name": "9A", "duration": 2}
    for col in (0, 1, 2):
        table.set_drag_preview(0, col, info2)
        prev = table._drag_preview_info or {}
        check(f"{col + 1}. saate gelince önizleme {col + 1}-{col + 2}. saatler",
              prev.get("col") == col and prev.get("duration") == 2,
              f"col={prev.get('col')} dur={prev.get('duration')}")
    table.clear_drag_preview()

    from timetable_grid import DraggableLessonCard
    import inspect
    src = inspect.getsource(DraggableLessonCard._start_standard_drag)
    check("dock kartı ilk hücresinden tutuluyor", "2 * dur" in src, src[:140])

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
    sys.exit(1 if FAILED else 0)
