"""
test_carsaf_rozet_renk.py — çarşaf: rozet/dok tutarlılığı, sınıf renkleri, ad tıklaması,
geri al/yinele düğmeleri.

    python test_carsaf_rozet_renk.py

Dört ayrı şikâyetin regresyon kilidi:

1. Sol başlıktaki kırmızı rozet ile alttaki dokun içeriği birbirini tutmuyordu. Rozet
   atanan saatten yerleşeni düpedüz çıkarıyor, dok ise dağılım bloklarını grup grup
   eşleştirip her grubu sıfırda kesiyordu; üstelik rozet ham ad "içinde geçiyor mu"
   diye bakıyordu ("1A" ⊂ "11A"). Artık rozet dokun kendi hesabını çağırıyor, yani
   iki sayının sapması tanım gereği imkânsız.

2. Öğretmen adına tıklayınca dok dolmuyordu: QTableView yalnızca kendi kurduğu
   başlığı tıklanabilir yapıyor, setVerticalHeader() ile takılan özel başlıkta
   sectionClicked hiç yayılmıyordu.

3. Öğretmen çarşafında hücre rengi öğretmenden geliyordu; aynı sınıf her öğretmende
   başka renk, iki ayrı sınıf da aynı renk çıkabiliyordu. Artık renk sınıftan geliyor
   ve palet çakışmasız bir permütasyonla dağıtılıyor.

4. Şeritteki Geri Al / Yinele düğmeleri hiçbir zaman sönmüyor, ne yapacaklarını da
   söylemiyorlardı.
"""
import json
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt, QPoint  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bgz_database.json")


def load_store():
    with open(DB, encoding="utf-8") as f:
        return json.load(f)


def make_host(ds, teachers, classes, mode):
    """_grid'i taklit eden, gerçek MainWindow metotlarını taşıyan bir kabuk."""
    import main_window as MW

    class _Dock:
        def load_unplaced(self, cards, **kw):
            self.cards = cards

    class _Grid:
        pass

    win = MW.MainWindow.__new__(MW.MainWindow)
    win.data_store = ds
    g = _Grid()
    g.teacher_list = list(teachers)
    g.class_list = list(classes)
    g.current_view_mode = mode
    g._placed_lessons = None
    g._periods = int(ds.get("settings", {}).get("periods", 8)) or 8
    g.unplaced_dock = _Dock()
    g.table = None
    win._grid = g
    return win, g


def dock_hours(win, entity, placements):
    cards = win._refresh_unplaced_lessons(
        target_entity=entity, _compute_only=True, _placements=placements) or []
    return sum(int(c.get("duration", 1) or 1) * int(c.get("count", 1) or 1) for c in cards)


# ── 1. Rozet ile dok her senaryoda aynı sayıyı vermeli ────────────────────────
def test_rozet_dok_ayni():
    print("\n[rozet ile dok aynı sayıyı gösteriyor]")
    import random

    base = load_store()
    teachers = [t["ad"] for t in base["ogretmenler"]]
    classes = [c["ad"] for c in base["siniflar"]]

    for mode, ents in (("teachers", teachers), ("classes", classes)):
        for frac, seed in ((0.0, 0), (0.25, 1), (0.5, 2), (0.9, 3), (1.0, 4)):
            ds = json.loads(json.dumps(base))
            rnd = random.Random(seed)
            ds["grid_placements"] = [p for p in ds.get("grid_placements", [])
                                     if rnd.random() > frac]
            win, _g = make_host(ds, teachers, classes, mode)
            badge = win.unplaced_hours_by_entity()
            shared = win._active_grid_placements()
            bad = [(e, int(badge.get(e, 0)), dock_hours(win, e, shared))
                   for e in ents
                   if int(badge.get(e, 0)) != dock_hours(win, e, shared)]
            check(f"{mode}: %{int(frac*100)} yerleşim silinince rozet=dok",
                  not bad, str(bad[:3]))


# ── 2. Öğretmen adına tıklayınca dok dolmalı ─────────────────────────────────
def test_ad_tiklamasi():
    print("\n[satır başlığına (öğretmen adına) tıklama]")
    import main_window as MW
    import timetable_grid as TG

    ds = load_store()
    teachers = [t["ad"] for t in ds["ogretmenler"]]
    classes = [c["ad"] for c in ds["siniflar"]]
    days = TG.DAYS[:5]

    calls = []

    class Host(MW.MainWindow):
        def __init__(self):
            pass

        data_store = ds

        def _refresh_unplaced_lessons(self, target_entity=None, _compute_only=False,
                                      _placements=None):
            if not _compute_only:
                calls.append(target_entity)
            return MW.MainWindow._refresh_unplaced_lessons(
                self, target_entity, _compute_only, _placements)

    grid = TG.TimetableGrid()
    host = Host()
    host._grid = grid
    grid.window = lambda: host
    grid.set_mode_all_teachers(teachers, 8, days)
    vh = grid.table.verticalHeader()

    check("satır başlığı tıklanabilir (sectionsClickable)", vh.sectionsClickable())

    for row in (0, 3, len(teachers) - 1):
        calls.clear()
        y = vh.sectionViewportPosition(row) + vh.sectionSize(row) // 2
        QTest.mouseClick(vh.viewport(), Qt.LeftButton, Qt.NoModifier,
                         QPoint(vh.viewport().width() // 2, y))
        check(f"{row}. öğretmenin adına basınca dok o öğretmene dolar",
              calls and calls[-1] == teachers[row], f"{calls!r}")
        check(f"{row}. satır: dok tam bir kez yenilenir (titremez)",
              len(calls) == 1, f"{len(calls)} kez")
        check(f"{row}. satır: geçerli satır gerçekten değişir",
              grid.table.currentRow() == row, str(grid.table.currentRow()))

    grid.deleteLater()


# ── 3. Sınıf renkleri: aynı sınıf hep aynı, farklı sınıflar hep farklı ───────
def test_sinif_renkleri():
    print("\n[sınıf renkleri]")
    from dialogs.color_picker_dialog import resolve_class_color, clear_class_color_cache

    ds = load_store()
    names = [c["ad"] for c in ds["siniflar"]]

    clear_class_color_cache()
    cols = {n: resolve_class_color(n, ds) for n in names}
    check("gerçek veride her sınıf ayrı renk",
          len(set(cols.values())) == len(names),
          f"{len(set(cols.values()))}/{len(names)}")

    for a, b in (("11C (ea)", "11C(EA)"), ("10A", "10-A"), ("10A", " 10 A ")):
        check(f"yazım farkı rengi değiştirmez: {a!r} = {b!r}",
              resolve_class_color(a, ds) == resolve_class_color(b, ds))

    check("birleşik derste sıra rengi değiştirmez (9A+9B = 9B+9A)",
          resolve_class_color("9A + 9B", ds) == resolve_class_color("9B + 9A", ds))

    # Sınıf listesinin sırası rengi etkilememeli.
    import copy
    import random
    stable = True
    for seed in range(5):
        d2 = copy.deepcopy(ds)
        random.Random(seed).shuffle(d2["siniflar"])
        clear_class_color_cache()
        if any(resolve_class_color(n, d2) != cols[n] for n in names):
            stable = False
    clear_class_color_cache()
    check("sınıf listesi karışsa da renkler sabit", stable)

    # Palet 28 renk; ötesinde de çakışma olmamalı.
    for count in (28, 29, 60, 200):
        big = {"siniflar": [{"ad": f"{9 + i // 26}{chr(65 + i % 26)}"} for i in range(count)]}
        clear_class_color_cache()
        got = {resolve_class_color(c["ad"], big) for c in big["siniflar"]}
        check(f"{count} sınıfta çakışma yok", len(got) == count, f"{len(got)} ayrı renk")

    # SinifEditDialog eskiden her sınıfa aynı varsayılanı yazıyordu; bu renkleri
    # tek renge düşürmemeli.
    clear_class_color_cache()
    trap = {"siniflar": [{"ad": n, "color": "#A30F37", "renk": "#A30F37"} for n in names]}
    got = {resolve_class_color(n, trap) for n in names}
    check("aynı varsayılan renkli kayıtlar tek renge düşmez", len(got) == len(names))

    # Kullanıcının bilerek verdiği (tek olan) renk korunmalı.
    clear_class_color_cache()
    pref = json.loads(json.dumps(ds))
    pref["siniflar"][0]["color"] = "#123456"
    check("kullanıcının seçtiği renk korunur",
          resolve_class_color(pref["siniflar"][0]["ad"], pref) == "#123456")
    clear_class_color_cache()


# ── 4. Öğretmen adı yazım farkları ders kaybettirmemeli ─────────────────────
def test_ad_esleme_dayanikli():
    print("\n[öğretmen adı yazım farkları ders kaybettirmiyor]")
    base = load_store()
    teachers = [t["ad"] for t in base["ogretmenler"]]
    classes = [c["ad"] for c in base["siniflar"]]
    known = set(teachers)
    baseline = sum(int(a.get("duration", 1) or 1) for a in base["atamalar"]
                   if (a.get("teacher") or "").strip() in known)

    variants = {
        "küçük harf": lambda s: s.lower(),
        "baş harfler büyük": lambda s: s.title(),
        "çift boşluk": lambda s: s.replace(" ", "  "),
        "baştan/sondan boşluk": lambda s: f"  {s}  ",
        "İ -> i": lambda s: s.replace("İ", "i"),
        "I -> ı": lambda s: s.replace("I", "ı"),
    }
    for label, fn in variants.items():
        ds = json.loads(json.dumps(base))
        ds["grid_placements"] = []
        for a in ds["atamalar"]:
            t = (a.get("teacher") or "").strip()
            if t in known:
                a["teacher"] = fn(t)
        win, _g = make_host(ds, teachers, classes, "teachers")
        shared = win._active_grid_placements()
        total = sum(dock_hours(win, t, shared) for t in teachers)
        check(f"{label}: hiçbir saat kaybolmuyor", total == baseline,
              f"{total} != {baseline}")


# ── 5. Geri Al / Yinele düğmeleri durumu ve ne yapacağını göstermeli ────────
def test_geri_al_dugmeleri():
    print("\n[şeritteki Geri Al / Yinele düğmeleri]")
    import main_window as MW
    from ribbon_widget import RibbonButton

    ds = load_store()
    w = MW.MainWindow.__new__(MW.MainWindow)
    w.data_store = ds
    w._history_stack, w._redo_stack, w._undo_labels = [], [], []
    for a in ("btn_undo_main", "btn_redo_main", "btn_undo_view", "btn_redo_view"):
        setattr(w, a, RibbonButton("x", "geri_al"))

    w._update_undo_redo_ui()
    check("yapacak iş yokken Geri Al sönük", not w.btn_undo_main.isEnabled())
    check("yapacak iş yokken Yinele sönük", not w.btn_redo_main.isEnabled())

    ds["atamalar"].append({"subject": "X", "class": "9A",
                           "teacher": ds["ogretmenler"][0]["ad"], "duration": 1})
    w._push_undo_state("Ders eklendi")
    check("işlem sonrası Geri Al etkin", w.btn_undo_main.isEnabled())
    check("ipucu ne geri alınacağını yazıyor",
          "Ders eklendi" in w.btn_undo_main.toolTip(), w.btn_undo_main.toolTip())

    ds["atamalar"].append({"subject": "Y", "class": "9A",
                           "teacher": ds["ogretmenler"][0]["ad"], "duration": 2})
    w._push_undo_state("Otomatik planlama")
    check("ipucu en son işlemi gösteriyor",
          "Otomatik planlama" in w.btn_undo_main.toolTip(), w.btn_undo_main.toolTip())

    same = all(getattr(w, a).isEnabled() == getattr(w, a.replace("_view", "_main")).isEnabled()
               and getattr(w, a).toolTip() == getattr(w, a.replace("_view", "_main")).toolTip()
               for a in ("btn_undo_view", "btn_redo_view"))
    check("iki şerit sekmesindeki kopyalar aynı durumda", same)

    check("etkin düğme vurgulu görünüyor",
          w.btn_undo_main.styleSheet() == RibbonButton.ACTIONABLE_QSS)
    check("sönük düğme nötr görünüyor",
          w.btn_redo_main.styleSheet() == RibbonButton.BASE_QSS)


def run():
    test_rozet_dok_ayni()
    test_ad_tiklamasi()
    test_sinif_renkleri()
    test_ad_esleme_dayanikli()
    test_geri_al_dugmeleri()


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
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
