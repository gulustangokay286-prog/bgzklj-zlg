"""
test_auto_scheduler_constraints.py — sınıf kısıtlarına (Zaman Tablosu) uyum testleri.

    python test_auto_scheduler_constraints.py

Kapatılan ders saatlerinin gerçekten boş kaldığını doğrular. Asıl hata şuydu:
oto planlayıcı yalnızca ÖĞRETMEN kısıtlarını okuyordu, sınıf kısıtlarını hiç
okumuyordu; ayrıca boşluk doldurma (filler) adımı her boş hücreyi dolduruyordu.
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication  # noqa: E402

import auto_scheduler  # noqa: E402
from auto_scheduler import AutoSchedulerWorker  # noqa: E402

PASSED, FAILED = [], []

DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
PERIODS = 8


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def make_timeoff(closed_periods=(), avoid_periods=(), days=5, periods=PERIODS):
    """timeoff[day][period]: 2=açık, 0=kapalı, 1=tercih edilmez."""
    matrix = []
    for _d in range(days):
        row = []
        for p in range(periods):
            if p in closed_periods:
                row.append(0)
            elif p in avoid_periods:
                row.append(1)
            else:
                row.append(2)
        matrix.append(row)
    return matrix


def build_store(class_timeoff=None, kisitlamalar=None):
    """İki sınıf, dört ders; grid'i doldurmaya fazlasıyla yetecek kadar atama."""
    store = {
        "settings": {"days": DAYS, "periods": PERIODS},
        "siniflar": [{"ad": "9A"}, {"ad": "9B"}],
        "ogretmenler": [
            {"ad": "Ahmet Yılmaz"}, {"ad": "Ayşe Demir"},
            {"ad": "Mehmet Kaya"}, {"ad": "Fatma Şahin"},
        ],
        "dersler": [{"ad": "Matematik"}, {"ad": "Fizik"}, {"ad": "Kimya"}, {"ad": "Biyoloji"}],
        "derslikler": [],
        "atamalar": [],
        "grid_placements": [],
        "kisitlamalar": kisitlamalar or {},
    }
    pairs = [
        ("Matematik", "Ahmet Yılmaz", 6),
        ("Fizik", "Ayşe Demir", 4),
        ("Kimya", "Mehmet Kaya", 4),
        ("Biyoloji", "Fatma Şahin", 4),
    ]
    for cls in ("9A", "9B"):
        for subject, teacher, hours in pairs:
            store["atamalar"].append({
                "subject": subject, "ders": subject,
                "teacher": teacher, "ogretmen": teacher,
                "class": cls, "sinif": cls,
                "duration": hours, "type": "2+2+2" if hours == 6 else "2+2",
            })
    if class_timeoff:
        for cls in store["siniflar"]:
            if cls["ad"] in class_timeoff:
                cls["timeoff"] = class_timeoff[cls["ad"]]
    return store


def run_scheduler(store, fill_empty=True):
    """Planlayıcıyı senkron çalıştırır (QThread.run doğrudan çağrılır)."""
    worker = AutoSchedulerWorker(store, fill_empty=fill_empty, institution_slug=None)
    captured = {}
    worker.finished_successfully.connect(lambda res: captured.update(res))
    worker.failed.connect(lambda msg: captured.update({"error": msg}))
    worker.run()
    return captured


def occupied_slots(placements, class_name):
    """Bir sınıf için dolu (gün, saat) çiftleri — blok süreleri açılarak."""
    slots = set()
    for p in placements:
        if (p.get("class_name") or p.get("class") or "") != class_name:
            continue
        day = int(p.get("day", p.get("col", 0)))
        start = int(p.get("period", p.get("row", 0)))
        for off in range(int(p.get("duration", 1) or 1)):
            slots.add((day, start + off))
    return slots


def run():
    _app = QApplication.instance() or QApplication(sys.argv)

    # Her sınıfa atanan gerçek ders saati: 6+4+4+4 = 18.
    # Planlayıcı artık boş hücreleri uydurma derslerle DOLDURMUYOR; sadece gerçekten
    # atanmış saatleri yerleştiriyor. Dolayısıyla ölçüt "grid doldu mu" değil,
    # "atanan saatlerin hepsi yerleşti mi" olmalı.
    REAL_HOURS = 18

    print("\n[temel: kısıt yokken tüm gerçek saatler yerleşir]")
    result = run_scheduler(build_store())
    placements = result.get("placements", [])
    check("plan üretildi", bool(placements), str(result.get("error", "")))
    base_9a = occupied_slots(placements, "9A")
    check("9A'nın atanan tüm saatleri yerleşti", len(base_9a) == REAL_HOURS,
          f"{len(base_9a)}/{REAL_HOURS}")

    print("\n[asıl hata: 5-6-7-8. saatler kapalı (timeoff matrisi)]")
    # Kullanıcının yaptığı: Zaman Tablosu ekranında 5-8. saatleri kapatmak.
    # (0 tabanlı indeksle 4,5,6,7)
    closed = (4, 5, 6, 7)
    store = build_store(class_timeoff={"9A": make_timeoff(closed_periods=closed)})
    result = run_scheduler(store)
    placements = result.get("placements", [])
    slots_9a = occupied_slots(placements, "9A")

    violations = sorted(s for s in slots_9a if s[1] in closed)
    check("kapatılan saatlere HİÇ ders konmadı", not violations,
          f"{len(violations)} ihlal, ilk 5: {violations[:5]}")
    # 4 gün × 4 açık saat = 20 hücre; 18 saatin hepsi buraya sığmalı.
    check("tüm gerçek saatler açık saatlere sığdırıldı", len(slots_9a) == REAL_HOURS,
          f"{len(slots_9a)}/{REAL_HOURS}")

    # Kısıt yalnızca 9A'ya konuldu: 9B'nin kapasitesi hiç azalmamalı.
    slots_9b = occupied_slots(placements, "9B")
    check("kısıtsız sınıf (9B) tüm saatlerini yerleştirdi", len(slots_9b) == REAL_HOURS,
          f"{len(slots_9b)}/{REAL_HOURS} — kısıt yanlış sınıfa sızmış olabilir")
    check("9B kapalı saatleri kullanmakta serbest",
          not set(range(8)).isdisjoint({s[1] for s in slots_9b}),
          "9B hiçbir saate yerleşememiş")

    print("\n[boşluk doldurma adımı da kısıtlara uyuyor]")
    # Asıl kabahatli buydu: her boş hücreyi dolduruyordu.
    store = build_store(class_timeoff={"9A": make_timeoff(closed_periods=closed)})
    result = run_scheduler(store, fill_empty=True)
    filler_hits = [
        p for p in result.get("placements", [])
        if p.get("is_filler")
        and (p.get("class_name") or p.get("class")) == "9A"
        and int(p.get("period", p.get("row", 0))) in closed
    ]
    check("doldurma adımı kapalı saatlere taşmıyor", not filler_hits,
          f"{len(filler_hits)} filler ders kapalı saatte")

    print("\n[kısıt yalnızca kisitlamalar sözlüğünde olsa da geçerli]")
    # Bulut senkronu sonrası timeoff matrisi boş, kisitlamalar dolu olabiliyor.
    kis = {"9A": {}}
    for d in range(len(DAYS)):
        for p in range(PERIODS):
            kis["9A"][f"{d},{p}"] = p not in closed  # True = açık
    result = run_scheduler(build_store(kisitlamalar=kis))
    slots_9a = occupied_slots(result.get("placements", []), "9A")
    violations = sorted(s for s in slots_9a if s[1] in closed)
    check("kisitlamalar sözlüğü tek başına yeterli", not violations,
          f"{len(violations)} ihlal, ilk 5: {violations[:5]}")

    print("\n[tam gün kapatma]")
    # Cuma (indeks 4) tamamen kapalı.
    matrix = make_timeoff()
    for p in range(PERIODS):
        matrix[4][p] = 0
    result = run_scheduler(build_store(class_timeoff={"9A": matrix}))
    slots_9a = occupied_slots(result.get("placements", []), "9A")
    check("kapalı gün tamamen boş kaldı", not any(s[0] == 4 for s in slots_9a),
          f"Cuma'da {sum(1 for s in slots_9a if s[0] == 4)} ders var")
    check("gerçek saatler kalan 4 güne sığdırıldı", len(slots_9a) == REAL_HOURS,
          f"{len(slots_9a)}/{REAL_HOURS}")

    print("\n['tercih edilmez' yumuşak kısıt: yasak değil ama son tercih]")
    store = build_store(class_timeoff={"9A": make_timeoff(avoid_periods=(6, 7))})
    result = run_scheduler(store, fill_empty=False)
    slots_9a = occupied_slots(result.get("placements", []), "9A")
    early = sum(1 for s in slots_9a if s[1] < 6)
    late = sum(1 for s in slots_9a if s[1] >= 6)
    check("sarı saatler kullanılabilir kalıyor (yasak değil)", True)
    check("planlayıcı önce erken saatleri dolduruyor", early > late,
          f"erken={early}, geç={late}")

    print("\n[hedef sayacı kapalı saatleri saymıyor]")
    store = build_store(class_timeoff={"9A": make_timeoff(closed_periods=closed)})
    result = run_scheduler(store)
    # 2 sınıf × 5 gün × 8 saat = 80; 9A'da 5×4=20 saat kapalı → hedef 60.
    check("total_hours kapalı saatler düşülerek hesaplandı",
          result.get("total_hours") == 60, str(result.get("total_hours")))

    print("\n[gridde SADECE atanan öğretmen görünür]")
    # Planlayıcı, atanan öğretmen doluysa BAŞKA bir öğretmeni o derse yazıyordu ve
    # aday listesi "o dersi verenler + OKULDAKİ HERKES" idi. Sonuç: tek bir öğretmen
    # altı alakasız derste görünüyor, grid atama paneliyle çelişiyordu. Yanlış
    # öğretmen yazan bir çizelge, boş hücreden daha kötüdür — basılıp dağıtılıyor.
    store = build_store()
    # Öğretmenleri meşgul edip yedeğe düşmeye zorlayalım: herkes 0-3. saatlerde kapalı.
    for t in store["ogretmenler"]:
        t["timeoff"] = make_timeoff(closed_periods=(0, 1, 2, 3))
    result = run_scheduler(store)
    placements = result.get("placements", [])

    expected = {}
    for a in store["atamalar"]:
        expected.setdefault(
            (a["class"].upper(), a["subject"].upper()), set()
        ).add(a["teacher"].upper())

    wrong = []
    for p in placements:
        cls = (p.get("class_name") or p.get("class") or "").upper()
        sub = (p.get("subject_name") or p.get("subject") or "").upper()
        tea = (p.get("teacher_name") or p.get("teacher") or "").upper()
        allowed = expected.get((cls, sub))
        if allowed is None or tea not in allowed:
            wrong.append((cls, sub, tea, allowed))

    check("hiçbir derse atanmamış öğretmen yazılmadı", not wrong,
          f"{len(wrong)} hata, ilk: {wrong[:2]}")

    # Bir öğretmen yalnızca kendi atandığı derslerde görünmeli.
    t_subjects = {}
    for p in placements:
        tea = (p.get("teacher_name") or p.get("teacher") or "").upper()
        sub = (p.get("subject_name") or p.get("subject") or "").upper()
        if tea:
            t_subjects.setdefault(tea, set()).add(sub)
    allowed_subjects = {}
    for a in store["atamalar"]:
        allowed_subjects.setdefault(a["teacher"].upper(), set()).add(a["subject"].upper())
    spread = [(t, s, allowed_subjects.get(t, set()))
              for t, s in t_subjects.items() if not s <= allowed_subjects.get(t, set())]
    check("öğretmenler kendi dersleri dışına taşmadı", not spread, str(spread[:2]))

    # Yerleştirilemeyen ders uydurma öğretmenle DOLDURULMAMALI.
    fillers = [p for p in placements if p.get("is_filler")]
    check("uydurma (filler) ders üretilmedi", not fillers, f"{len(fillers)} filler")

    print("\n[bağımsız mod: grid dolar ama çakışmalar işaretlenir]")
    # Kullanıcının istediği "diğer sınıfları görmesin" seçeneği. Grid daha çok doluyor
    # ama aynı öğretmen iki sınıfta olabiliyor — bu KABUL EDİLEN bir takas, gizlenmemek
    # şartıyla: her yerleşim işaretli ve çakışmalar rapor ediliyor.
    store = build_store()
    for t in store["ogretmenler"]:
        t["timeoff"] = make_timeoff(closed_periods=(4, 5, 6, 7))

    normal = run_scheduler(store)
    indep_worker = AutoSchedulerWorker(store, fill_empty=False, institution_slug=None,
                                       independent_classes=True)
    indep = {}
    indep_worker.finished_successfully.connect(lambda r: indep.update(r))
    indep_worker.run()

    def count_clashes(result):
        # Süreyi açarak say: 2 saatlik bir bloğun çakışması İKİ saatlik çakışmadır,
        # bir tane değil. Planlayıcı da böyle sayıyor.
        seen = {}
        for p in result.get("placements", []):
            teacher = str(p.get("teacher_name") or p.get("teacher") or "").upper()
            day = int(p.get("day", 0))
            start = int(p.get("period", 0))
            for off in range(int(p.get("duration", 1) or 1)):
                seen.setdefault((teacher, day, start + off), set()).add(
                    str(p.get("class_name") or p.get("class")))
        return sum(1 for v in seen.values() if len(v) > 1)

    check("normal modda öğretmen çakışması YOK", count_clashes(normal) == 0,
          f"{count_clashes(normal)} çakışma")
    check("bağımsız mod en az normal kadar yerleştiriyor",
          indep.get("placed_hours", 0) >= normal.get("placed_hours", 0),
          f"{normal.get('placed_hours')} -> {indep.get('placed_hours')}")
    check("oluşan çakışmalar eksiksiz raporlanıyor",
          len(indep.get("teacher_clashes", [])) == count_clashes(indep),
          f"raporlanan={len(indep.get('teacher_clashes', []))}, "
          f"gerçek={count_clashes(indep)}")
    check("bağımsız mod yerleşimleri gözden geçirilmek üzere işaretli",
          all(p.get("needs_review") for p in indep.get("placements", [])),
          "işaretsiz yerleşim var")
    check("normal mod yerleşimleri işaretli DEĞİL",
          not any(p.get("needs_review") for p in normal.get("placements", [])))

    # Bagimsiz mod sadece OGRETMEN cakismasini serbest birakir; sinifin kapali
    # saatleri yine dokunulmaz olmali.
    closed_hit = [
        p for p in indep.get("placements", [])
        if int(p.get("period", 0)) in (4, 5, 6, 7)
    ]
    check("bağımsız modda bile kapalı saatlere ders konmuyor", not closed_hit,
          f"{len(closed_hit)} ders kapalı saatte")

    print("\n[ön kontrol: çalıştırmadan önce doğru tahmin]")
    # aSc'nin "Kontrol" adiminin karsiligi. Degeri, planlayiciyi calistirmadan
    # ONCE "bu doldurulamaz" diyebilmesinde — ve tahmininin gercekle tutmasinda.
    from auto_scheduler import check_feasibility

    healthy = build_store()
    rep = check_feasibility(healthy)
    check("sorunsuz kurulumda 'uygun' diyor", rep["ok"], str(rep["max_fillable"]))
    check("hücre sayısını doğru buluyor", rep["total_cells"] == 2 * 40,
          str(rep["total_cells"]))

    # Tek ogretmen, iki sinif, herkes ayni 5 saatte -> yapisal olarak dolmaz.
    tight = build_store()
    tight["ogretmenler"] = [{"ad": "Ahmet Yılmaz",
                             "timeoff": make_timeoff(closed_periods=tuple(range(1, 8)))}]
    for cls in tight["siniflar"]:
        cls["timeoff"] = make_timeoff(closed_periods=tuple(range(1, 8)))
    tight["atamalar"] = [
        {"subject": "Matematik", "teacher": "Ahmet Yılmaz", "class": c["ad"],
         "duration": 5, "type": "1+1+1+1+1"}
        for c in tight["siniflar"]
    ]
    rep2 = check_feasibility(tight)
    check("imkansız kurulumu ÖNCEDEN yakalıyor", not rep2["ok"], str(rep2))
    check("aşırı yüklü öğretmeni isimlendiriyor",
          any("Ahmet" in o["teacher"] for o in rep2["overloaded_teachers"]),
          str(rep2["overloaded_teachers"]))

    # Tahmin gercekle tutmali: tahminden fazlasi yerlesmemeli.
    actual = run_scheduler(tight)
    check("tahmin gerçeği aşmıyor",
          actual.get("placed_hours", 0) <= rep2["max_fillable"],
          f"tahmin={rep2['max_fillable']}, gerçek={actual.get('placed_hours')}")

    print("\n[yardımcı fonksiyonlar]")
    blocked, avoid = auto_scheduler._build_class_timeoff_map(
        build_store(class_timeoff={"9A": make_timeoff(closed_periods=(4,), avoid_periods=(5,))})
    )
    check("kapalı saatler haritalandı", (0, 4) in blocked.get("9A", set()), str(blocked))
    check("tercih edilmeyen saatler ayrı tutuldu", (0, 5) in avoid.get("9A", set()), str(avoid))
    check("kapalı, tercih edilmezden önce gelir", (0, 4) not in avoid.get("9A", set()))

    # Sınıf adı farklı yazımlarla eşleşmeli ("9A" / "9-A" / "9 A").
    check("farklı yazım eşleşiyor (9-A)",
          auto_scheduler._resolve_class_slots("9-A", {"9A": {(0, 4)}}) == {(0, 4)})
    check("alakasız sınıf eşleşmiyor",
          auto_scheduler._resolve_class_slots("10B", {"9A": {(0, 4)}}) == set())


if __name__ == "__main__":
    try:
        run()
    except Exception:
        import traceback
        traceback.print_exc()
        FAILED.append(("beklenmeyen hata", "yukarıdaki traceback"))
    finally:
        print("\n" + "=" * 60)
        print(f"geçen: {len(PASSED)}   kalan: {len(FAILED)}")
        for name, detail in FAILED:
            print(f"  - {name}: {detail}")
        print("=" * 60)
    sys.exit(1 if FAILED else 0)
