"""
test_placement_ui.py — sürükleme sırasında ızgaranın gerçekten renk yakması.

    python test_placement_ui.py

Motorun doğru cevap vermesi yetmez; o cevabın ekrana yansıması gerekir. Burada
gerçek TimetableGrid kurulup sürükleme başlatılıyor ve hücre hücre hangi görsel
durumun çıktığı kontrol ediliyor. Renk hesabı arayüzde DEĞİL: ızgara yalnızca
placement_engine'in verdiği duruma karşılık gelen jetonu boyar.
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication  # noqa: E402

import placement_engine as pe  # noqa: E402

PASSED, FAILED = [], []
DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
P = 4


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def timeoff(closed=(), avoid=()):
    grid = [[2] * P for _ in DAYS]
    for d, p in closed:
        grid[d][p] = 0
    for d, p in avoid:
        grid[d][p] = 1
    return grid


def build_store():
    return {
        "settings": {"days": DAYS, "days_count": 5, "periods": P},
        "siniflar": [{"ad": "9A"}, {"ad": "9B"}],
        "ogretmenler": [{"ad": "Ahmet Yılmaz", "timeoff": timeoff(closed=[(2, 0)],
                                                                 avoid=[(3, 1)])},
                        {"ad": "Ayşe Demir"}],
        "dersler": [{"ad": "Matematik"}, {"ad": "Fizik"}],
        "derslikler": [],
        "atamalar": [],
        "kisitlamalar": {},
        "grid_placements": [
            # 9A'nın kendi dersi: kırmızı olmalı (sınıf dolu)
            {"class_name": "9A", "subject_name": "Fizik", "teacher_name": "Ayşe Demir",
             "day": 0, "period": 1, "duration": 1, "block_id": "b_fizik"},
            # 9B'de AYNI öğretmen: 9A'nın hücresi boş ama öğretmen meşgul -> kırmızı
            {"class_name": "9B", "subject_name": "Matematik",
             "teacher_name": "Ahmet Yılmaz", "day": 1, "period": 2, "duration": 1,
             "block_id": "b_baska_sinif"},
        ],
    }


def run():
    app = QApplication.instance() or QApplication(sys.argv)
    from timetable_grid import TimetableGrid

    data = build_store()
    grid = TimetableGrid()
    # Gercek uygulamada data_store MainWindow'da durur; izgara tek basina
    # kullanildiginda ebeveyn zincirinden bulunur.
    grid.data_store = data
    grid.institution_slug = None
    grid.set_mode_all_classes(["9A", "9B"], P, DAYS)

    dragged = {"subject_name": "Matematik", "teacher_name": "Ahmet Yılmaz",
               "class_name": "9A", "duration": 1, "block_id": "dragged"}

    print("\n[analiz başlıyor]")
    grid.table.begin_placement_analysis(dragged)
    check("analiz haritası doldu", bool(grid.table._placement_map),
          str(len(grid.table._placement_map)))

    rows = grid.rows_for_lesson(dragged)
    check("yalnız dersin kendi sınıf satırı aday", rows == [0], str(rows))
    check("başka sınıfın satırı boyanmıyor",
          all(r == 0 for (r, _c) in grid.table._placement_map))

    def visual(day, period):
        col = day * P + period
        res = grid.table.placement_at(0, col)
        return res.visual if res else None

    print("\n[hücre durumları]")
    check("boş hücre YEŞİL", visual(0, 0) == pe.V_GREEN, str(visual(0, 0)))
    check("sınıfın dolu hücresi KIRMIZI", visual(0, 1) == pe.V_RED, str(visual(0, 1)))
    check("öğretmenin kapalı saati GRİ", visual(2, 0) == pe.V_GREY, str(visual(2, 0)))
    check("tercih edilmez saat MAVİ", visual(3, 1) == pe.V_BLUE, str(visual(3, 1)))

    print("\n[sınıf boş ama öğretmen başka sınıfta -> KIRMIZI]")
    check("9A boş olmasına rağmen kırmızı", visual(1, 2) == pe.V_RED, str(visual(1, 2)))
    res = grid.table.placement_at(0, 1 * P + 2)
    check("gerekçe öğretmen çakışması",
          any(c.type == pe.TEACHER_COLLISION for c in res.conflicts), str(res.conflicts))
    check("hangi sınıf olduğu yazıyor", "9B" in res.explanation, res.explanation)

    print("\n[başlık şeridi]")
    states = grid.table.header_placement_states()
    check("başlıkta durum var", bool(states), str(len(states)))
    check("başlık dolu saatte kırmızı", states.get(0 * P + 1) == pe.V_RED,
          str(states.get(0 * P + 1)))
    check("başlık kapalı saatte gri", states.get(2 * P + 0) == pe.V_GREY,
          str(states.get(2 * P + 0)))

    print("\n[2 saatlik ders: bütün ayak izi]")
    grid.table.end_placement_analysis()
    dragged2 = dict(dragged, duration=2)
    grid.table.begin_placement_analysis(dragged2)
    res = grid.table.placement_at(0, 0 * P + 0)   # 1-2. saat, 2. saatte Fizik var
    check("2 saatlik ders komşu çakışmayı görüyor", res.visual == pe.V_RED, res.visual)
    res2 = grid.table.placement_at(0, 0 * P + 3)  # gün sonuna taşar
    check("gün sonuna taşan aday gri", res2.visual == pe.V_GREY, res2.visual)

    print("\n[analiz veriye dokunmuyor]")
    import copy
    before = copy.deepcopy(data)
    grid.table.begin_placement_analysis(dragged)
    check("veri deposu aynı", data == before)

    print("\n[bırakınca temizleniyor]")
    grid.table.end_placement_analysis()
    check("harita boşaldı", not grid.table._placement_map)
    check("başlık durumu sıfırlandı", not grid.table.header_placement_states())

    print("\n[eski analiz yeniyi ezmiyor]")
    grid.table.begin_placement_analysis(dragged)
    first = dict(grid.table._placement_map)
    grid.table.begin_placement_analysis(dict(dragged, teacher_name="Ayşe Demir"))
    second = grid.table._placement_map
    check("son sürüklenen kart geçerli", second is not first)
    res = grid.table.placement_at(0, 1 * P + 2)
    check("yeni öğretmene göre yeniden hesaplandı", res.visual == pe.V_GREEN, res.visual)

    print("\n[aynı sınıfın farklı yazımı: '12 E(TM)' ile '12E(TM)']")
    # Uygulama bu ikisini AYNI sınıf sayar (matches_class). Motor birebir
    # karşılaştırınca hiçbir satır aday çıkmıyor, ızgarada tek hücre bile
    # boyanmıyordu — müsait yerler yeşil yanmıyor diye görünen buydu.
    data2 = {
        "settings": {"days": DAYS, "days_count": 5, "periods": P},
        "siniflar": [{"ad": "12 E(TM)"}, {"ad": "12 C(TM)"}],
        "ogretmenler": [{"ad": "Şeyma Nur Aker"}, {"ad": "Niyazi Kaya"}],
        "dersler": [{"ad": "Edebiyat"}, {"ad": "Coğrafya"}],
        "derslikler": [], "atamalar": [], "kisitlamalar": {},
        "grid_placements": [
            {"class_name": "12 E(TM)", "subject_name": "Coğrafya",
             "teacher_name": "Niyazi Kaya", "day": 0, "period": 0,
             "duration": 1, "block_id": "b_cog"}],
    }
    grid2 = TimetableGrid()
    grid2.data_store = data2
    grid2.institution_slug = None
    grid2.set_mode_all_classes(["12 E(TM)", "12 C(TM)"], P, DAYS)
    card = {"subject_name": "Edebiyat", "teacher_name": "Şeyma Nur Aker",
            "class_name": "12E(TM)", "duration": 1, "block_id": "dragged"}
    check("farklı yazım aynı satıra eşleşti", grid2.rows_for_lesson(card) == [0],
          str(grid2.rows_for_lesson(card)))
    grid2.table.begin_placement_analysis(card)
    r0 = grid2.table.placement_at(0, 0)
    r1 = grid2.table.placement_at(0, 1)
    check("dolu hücre kırmızı", r0 and r0.visual == pe.V_RED,
          str(r0.visual if r0 else None))
    check("MÜSAİT hücre YEŞİL", r1 and r1.visual == pe.V_GREEN,
          str(r1.visual if r1 else None))
    # Tek dolu hücre dışında BÜTÜN ızgara yeşil olmalı: kısıtlama yoksa
    # "müsait" demek yeşil demektir.
    total = 5 * P
    greens = sum(1 for res in grid2.table._placement_map.values()
                 if res.visual == pe.V_GREEN)
    reds = sum(1 for res in grid2.table._placement_map.values()
               if res.visual == pe.V_RED)
    check("kısıtsız ızgarada tek dolu hücre dışında hepsi yeşil",
          greens == total - 1 and reds == 1, f"{greens} yeşil / {reds} kırmızı / {total}")
    grid2.deleteLater()

    print("\n[koordinat çözümleyici]")
    pos = grid.resolve_cell(0, 2 * P + 3)
    check("sütun -> gün/saat", pos["day"] == 2 and pos["period"] == 3, str(pos))
    check("satır -> sınıf", pos["class_name"] == "9A", str(pos))
    grid.set_mode_all_teachers(["Ahmet Yılmaz", "Ayşe Demir"], P, DAYS)
    pos_t = grid.resolve_cell(1, 1 * P + 0)
    check("öğretmen görünümünde satır -> öğretmen",
          pos_t["teacher_name"] == "Ayşe Demir" and pos_t["day"] == 1, str(pos_t))

    grid.deleteLater()


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
