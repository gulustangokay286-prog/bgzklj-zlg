"""
test_screen_hours_agree.py — SAAT GÖSTEREN HER EKRAN AYNI SAYIYI SÖYLEMELİ.

    python test_screen_hours_agree.py

Şikâyet şuydu: "sınıflar ekranında toplam ders saati daha fazla, öğretmenler
ekranında saçma sapan şekilde daha az görünüyor."

Sebebi, bir atama satırının aynı bilgiyi birden çok alanda taşıması ve her ekranın
farklı alanı okumasıydı:
  * sınıf ekranı        -> duration + type
  * öğretmen ekranı     -> ders_sayisi (sınıf ekranından değiştirilince bayatlıyor)
  * İstatistik ekranı   -> hiç yazılmayan saat/ogretmen (182 saatlik okulda 72 saat
                           ve bomboş öğretmen tablosu gösteriyordu)
  * grid "Böl/Birleştir" -> tek dersi çok satıra bölüyor, kayıtta teke inince
                           geriye hours=1 taşıyan bir satır kalıyordu

Aşağıdaki veri o tuzakların HEPSİNİ bilerek taşır. Test, dokuz ekranın da aynı
toplamı ürettiğini doğrular; biri kendi alanını okumaya dönerse burada patlar.
"""
import os
import re
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication  # noqa: E402

import lesson_hours  # noqa: E402

PASSED, FAILED = [], []
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
    """Bayat alanların hepsini taşıyan gerçekçi veri. Doğru toplam: 24 saat."""
    classes = ["9A", "10A", "11A (MF)"]
    return {
        "settings": {"days": DAYS, "days_count": 5, "periods": P},
        "siniflar": [{"ad": c, "timeoff": timeoff({0, 1, 2, 3})} for c in classes],
        "ogretmenler": [
            {"ad": "Sultan Yılmaz", "kisa": "S. YILMAZ", "timeoff": timeoff(set(range(P)))},
            {"ad": "Nuray Samut", "kisa": "N. SAMUT", "timeoff": timeoff(set(range(P)))},
            {"ad": "H.barış Karataş", "kisa": "H. KARATAŞ", "timeoff": timeoff(set(range(P)))},
        ],
        "dersler": [{"ad": "Matematik"}, {"ad": "Türkçe"}, {"ad": "Biyoloji"}],
        "derslikler": [],
        "atamalar": [
            # aynı ders, üç sınıfa FARKLI saatlerle (öğretmen ekranı bunları tek
            # satırda gruplar; grupladıktan sonra da toplam bozulmamalı)
            {"class": "9A", "subject": "Matematik", "teacher": "Sultan Yılmaz",
             "duration": 4, "type": "2+2"},
            {"class": "10A", "subject": "Matematik", "teacher": "Sultan Yılmaz",
             "duration": 2, "type": "2"},
            {"class": "11A (MF)", "subject": "Matematik", "teacher": "Sultan Yılmaz",
             "duration": 1, "type": "1"},
            # sınıf ekranından 3'e çekilmiş ama ders_sayisi/saat 2'de kalmış satır
            {"class": "9A", "subject": "Türkçe", "teacher": "Nuray Samut",
             "duration": 3, "type": "2+1", "ders_sayisi": 2, "saat": 2},
            # "Böl/Birleştir" menüsünün bıraktığı satır: hours=1 ama gerçekte 5
            {"class": "10A", "subject": "Biyoloji", "teacher": "H.barış Karataş",
             "duration": 5, "type": "2+2+1", "hours": 1, "distribution": [2, 2, 1]},
            # farklı yazım: kayıtta 'H.barış Karataş'
            {"class": "11A (MF)", "subject": "Biyoloji", "teacher": "H.Barış Karataş",
             "duration": 9, "type": "2+2+2+2+1"},
        ],
        "kisitlamalar": {},
        "grid_placements": [],
        "loose_unplaced_cards": [],
    }


def run():
    app = QApplication.instance() or QApplication(sys.argv)
    store = build_store()

    truth = lesson_hours.total(store)
    per_teacher = lesson_hours.per_teacher(store)
    per_class = lesson_hours.per_class(store)
    print(f"\n[doğru kaynak] toplam {truth} saat | "
          f"sınıf {sum(per_class.values())} | öğretmen {sum(per_teacher.values())}")
    check("kaynak kendi içinde tutarlı",
          truth == sum(per_class.values()) == sum(per_teacher.values()) == 24,
          f"{truth}/{sum(per_class.values())}/{sum(per_teacher.values())}")

    print("\n[sınıf tarafı]")
    from dialogs.edit_forms import (ClassComprehensiveAssignmentDialog,
                                    LessonAssignmentDialog)
    total = 0
    for c in store["siniflar"]:
        dlg = ClassComprehensiveAssignmentDialog(c["ad"], store, None)
        txt = re.sub("<[^>]+>", " ", dlg.lbl_summary.text())
        m = re.search(r"(\d+)\s*/", txt)
        total += int(m.group(1)) if m else -1
        dlg.deleteLater()
    check("Sınıfa Bütünsel Ders Atama toplamı", total == truth, f"{total} != {truth}")

    print("\n[öğretmen tarafı]")
    total = 0
    for t in store["ogretmenler"]:
        dlg = LessonAssignmentDialog(data_store=store, parent=None)
        idx = dlg.cb_ogretmen.findText(t["ad"])
        if idx >= 0:
            dlg.cb_ogretmen.setCurrentIndex(idx)
            dlg._populate_from_teacher()
            txt = re.sub("<[^>]+>", " ", dlg.lbl_ozet.text())
            m = re.search(r"Toplam Haftal.k Saat:\s*(\d+)", txt)
            total += int(m.group(1)) if m else -1
        dlg.deleteLater()
    check("Öğretmen ders atama paneli toplamı", total == truth, f"{total} != {truth}")

    from dialogs.master_data_dialog import is_teacher_match
    tobjs = store["ogretmenler"]
    total = sum(
        sum(lesson_hours.hours(a) for a in store["atamalar"]
            if is_teacher_match(a.get("ogretmen") or a.get("teacher", ""), t["ad"], tobjs))
        for t in tobjs)
    check("Öğretmen kartı bannerı toplamı", total == truth, f"{total} != {truth}")

    print("\n[baskı raporları]")
    from auto_scheduler import format_tr_name
    from dialogs.print_preview import _group_teacher_atamalar_by_subject
    total = 0
    for t in tobjs:
        raw = [a for a in store["atamalar"]
               if format_tr_name(a.get("ogretmen") or a.get("teacher", "")) == format_tr_name(t["ad"])]
        total += sum(int(g.get("duration", 1)) for g in _group_teacher_atamalar_by_subject(raw)
                     if str(g.get("duration", 1)).isdigit())
    check("Gruplu ders listesi toplamı", total == truth, f"{total} != {truth}")

    print("\n[istatistik / danışman / planlayıcı]")
    from dialogs.statistics_dialog import StatisticsDialog
    dlg = StatisticsDialog(store)
    stat_total = 0
    for r in range(dlg.table.rowCount()):
        stat_total += int(re.search(r"(\d+)", dlg.table.item(r, 1).text()).group(1))
    header = " ".join(
        dlg.layout().itemAt(0).widget().layout().itemAt(i).widget().text()
        for i in range(dlg.layout().itemAt(0).widget().layout().count()))
    dlg.deleteLater()
    check("İstatistik öğretmen tablosu toplamı", stat_total == truth,
          f"{stat_total} != {truth}")
    check("İstatistik başlık satırı doğru toplamı yazıyor",
          f"Atanan Toplam Ders Saati: {truth}" in header, header[:120])

    import advisor
    check("Danışman öğretmen talebi",
          sum(advisor.demand_per_teacher(store).values()) == truth)
    check("Danışman sınıf talebi",
          sum(advisor.demand_per_class(store).values()) == truth)

    from auto_scheduler import parse_distribution_parts
    sched = sum(sum(parse_distribution_parts(a.get("type"), lesson_hours.hours(a) or 2))
                for a in store["atamalar"])
    check("Otomatik planlayıcı aynı saati alıyor", sched == truth, f"{sched} != {truth}")

    print("\n[farklı yazımla girilen öğretmen kaybolmuyor]")
    audit = lesson_hours.audit(store)
    check("iki taraf eşit", audit["class_total"] == audit["teacher_total"] == truth,
          f"{audit['class_total']} / {audit['teacher_total']}")
    check("tanınmayan öğretmen bildiriliyor", len(audit["unknown_teachers"]) == 1,
          str(audit["unknown_teachers"]))
    check("çelişen satırlar bildiriliyor", len(audit["stale_rows"]) == 2,
          str(len(audit["stale_rows"])))

    print("\n[kayıttan sonra çelişki kalmıyor]")
    import version_store
    store["atamalar"] = version_store.sanitize_atamalar(store["atamalar"])
    after = lesson_hours.audit(store)
    check("kayıt sonrası bayat alan yok", after["stale_rows"] == [],
          str(after["stale_rows"]))
    check("kayıt toplamı değiştirmedi", lesson_hours.total(store) == truth,
          str(lesson_hours.total(store)))


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
