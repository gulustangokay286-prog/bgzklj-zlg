"""
test_cross_institution.py — aynı öğretmen 3-4 kurumda çalışırken kısıtlar nasıl işler?

    python test_cross_institution.py

Kural, üç katmanlı:

  1) KURUM KISITI  ("bu kurumda o saatte yok")
     Yalnız o kurumu bağlar. Yarım gün burada, öğleden sonra başka şubede olan bir
     öğretmenin durumu budur: burada kapattığınız saat DİĞER kurumda AÇIK kalmalıdır.
     Eskiden tersiydi — herkesin kapattığı saatler birleşiyor, öğretmen hiçbir yere
     yerleşemiyordu.

  2) KİŞİSEL KISIT ("bu saatte hiçbir yerde yok")
     Rapor, izin, okula hiç gelmediği yarım gün. BÜTÜN kurumları bağlar; ortak
     deftere yalnızca bu yazılır.

  3) SAHİPLİK      (rezervasyon ya da gerçekten konmuş ders)
     Bir saati X kurumu tuttuysa diğerlerinde kapalı görünür. Kurum sayısı artınca
     kural değişmez: defter tek, sahip tek.
"""
import json
import os
import shutil
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SANDBOX = os.path.join(tempfile.gettempdir(), "chenki_cross_test")
shutil.rmtree(SANDBOX, ignore_errors=True)
os.makedirs(SANDBOX, exist_ok=True)
INST_ROOT = os.path.join(SANDBOX, "institutions")
GLOBAL_FILE = os.path.join(SANDBOX, "global_kisitlamalar.json")

import version_store  # noqa: E402
import constraint_sync  # noqa: E402

version_store._base_dir = lambda: INST_ROOT
constraint_sync._global_path = lambda: GLOBAL_FILE

PASSED, FAILED = [], []
DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
P = 8
TEACHER = "Ali Veli"


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def make_store(slug):
    return {
        "settings": {"days": DAYS, "days_count": 5, "periods": P,
                     "institution_slug": slug},
        "siniflar": [{"ad": "9A"}],
        "ogretmenler": [{"ad": TEACHER}, {"ad": "Ayşe Can"}],
        "dersler": [{"ad": "Matematik"}],
        "derslikler": [],
        "atamalar": [{"class": "9A", "subject": "Matematik", "teacher": TEACHER,
                      "duration": 2, "type": "2"}],
        "kisitlamalar": {},
        "grid_placements": [],
    }


def make_institution(slug, name):
    os.makedirs(os.path.join(INST_ROOT, slug, "versions"), exist_ok=True)
    with open(os.path.join(INST_ROOT, slug, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"name": name}, f)


def closed_slots(slug, store):
    """slug kurumunun gözünden TEACHER'ın kapalı saatleri."""
    import auto_scheduler
    blocked, _avoid = auto_scheduler._build_teacher_timeoff_map(store, slug)
    return blocked.get(auto_scheduler.norm_teacher(TEACHER), set())


def run():
    print("\n[kurulum: 4 kurum]")
    slugs = ["kurum_a", "kurum_b", "kurum_c", "kurum_d"]
    for i, s in enumerate(slugs):
        make_institution(s, f"Kurum {chr(65 + i)}")
    stores = {s: make_store(s) for s in slugs}
    check("4 kurum oluştu", all(os.path.isfile(os.path.join(INST_ROOT, s, "meta.json"))
                                for s in slugs))

    print("\n[1) kurum kısıtı yalnız kendi kurumunu bağlar]")
    a = stores["kurum_a"]
    teacher_a = a["ogretmenler"][0]
    matrix = constraint_sync.get_matrix(teacher_a, TEACHER, a)
    for p in range(4):                      # A'da pazartesi sabah gelmiyor
        matrix[0][p] = constraint_sync.CLOSED
    constraint_sync.set_matrix(teacher_a, TEACHER, a, matrix)
    constraint_sync.publish("kurum_a", a)

    check("A kendi ekranında kapalı görüyor",
          (0, 0) in closed_slots("kurum_a", a), str(sorted(closed_slots("kurum_a", a))[:5]))
    b_closed = closed_slots("kurum_b", stores["kurum_b"])
    check("B'de o saatler AÇIK kaldı", not b_closed, str(sorted(b_closed)[:5]))
    c_closed = closed_slots("kurum_c", stores["kurum_c"])
    check("C'de de açık", not c_closed, str(sorted(c_closed)[:5]))

    print("\n[2) kişisel kısıt bütün kurumları bağlar]")
    personal = constraint_sync.get_personal(teacher_a, TEACHER, a)
    personal[2][0] = True                   # çarşamba 1. saat: hiçbir yerde yok
    constraint_sync.set_personal(teacher_a, TEACHER, a, personal)
    constraint_sync.publish("kurum_a", a)

    check("A'da kapalı", (2, 0) in closed_slots("kurum_a", a))
    check("B'de de kapalı", (2, 0) in closed_slots("kurum_b", stores["kurum_b"]),
          str(sorted(closed_slots("kurum_b", stores["kurum_b"]))))
    check("C'de de kapalı", (2, 0) in closed_slots("kurum_c", stores["kurum_c"]))
    check("D'de de kapalı", (2, 0) in closed_slots("kurum_d", stores["kurum_d"]))
    check("kişisel dışındaki A kısıtları B'ye sızmadı",
          closed_slots("kurum_b", stores["kurum_b"]) == {(2, 0)},
          str(sorted(closed_slots("kurum_b", stores["kurum_b"]))))

    print("\n[3) iki kurum ayrı ayrı yarım gün kapatınca üst üste binmiyor]")
    c = stores["kurum_c"]
    teacher_c = c["ogretmenler"][0]
    m_c = constraint_sync.get_matrix(teacher_c, TEACHER, c)
    for p in range(4, P):                   # C'de pazartesi öğleden sonra gelmiyor
        m_c[0][p] = constraint_sync.CLOSED
    constraint_sync.set_matrix(teacher_c, TEACHER, c, m_c)
    constraint_sync.publish("kurum_c", c)

    a_view = closed_slots("kurum_a", a)
    c_view = closed_slots("kurum_c", c)
    check("A hâlâ yalnız kendi sabahını kapalı görüyor",
          {(0, p) for p in range(4)} <= a_view and (0, 5) not in a_view,
          str(sorted(a_view)))
    check("C hâlâ yalnız kendi öğleden sonrasını kapalı görüyor",
          {(0, p) for p in range(4, P)} <= c_view and (0, 0) not in c_view,
          str(sorted(c_view)))
    check("D iki kurumun saatlerinden de etkilenmedi",
          closed_slots("kurum_d", stores["kurum_d"]) == {(2, 0)},
          str(sorted(closed_slots("kurum_d", stores["kurum_d"]))))

    print("\n[4) rezervasyon: saati tutan kurum onu diğerlerinden alır]")
    ok = constraint_sync.set_reservation("kurum_b", TEACHER, (3, 1), True)
    check("B saati rezerve etti", ok)
    res = constraint_sync.reservations_for(TEACHER)
    check("defterde B görünüyor", res.get((3, 1)) == "kurum_b", str(res))
    check("aynı saati C alamaz",
          constraint_sync.set_reservation("kurum_c", TEACHER, (3, 1), True) is False)

    print("\n[5) kişisel kısıt her iki gösterime de yazıldı]")
    check("öğretmen kaydında personal_off var",
          isinstance(teacher_a.get("personal_off"), list))
    check("data_store'da kisitlamalar_kisisel var",
          "2,0" in (a.get("kisitlamalar_kisisel", {}).get(TEACHER) or {}),
          str(a.get("kisitlamalar_kisisel")))
    check("kişisel saat, kurum matrisinde de kapalı görünüyor",
          constraint_sync.get_matrix(teacher_a, TEACHER, a)[2][0] == constraint_sync.CLOSED)

    print("\n[6) eski (zarfsız) ortak kayıtlar artık kimseyi kapatmıyor]")
    with open(GLOBAL_FILE, "r", encoding="utf-8") as f:
        gdata = json.load(f)
    gdata["kurum_eski"] = {TEACHER: {f"{d},{p}": 0 for d in range(5) for p in range(P)}}
    with open(GLOBAL_FILE, "w", encoding="utf-8") as f:
        json.dump(gdata, f)
    check("eski kayıt yok sayıldı",
          closed_slots("kurum_b", stores["kurum_b"]) == {(2, 0)},
          str(sorted(closed_slots("kurum_b", stores["kurum_b"]))))

    print("\n[7) 'kaydedersem ne olur' kopyası gerçek veriye dokunmuyor]")
    before = json.dumps(a["kisitlamalar"], sort_keys=True)
    probe_matrix = [[constraint_sync.CLOSED] * P for _ in DAYS]
    probe = constraint_sync.candidate_store(a, teacher_a, TEACHER, probe_matrix)
    check("kopyada her saat kapalı",
          all(probe["kisitlamalar"][TEACHER][f"{d},{p}"] == 0
              for d in range(5) for p in range(P)))
    check("asıl veri değişmedi",
          json.dumps(a["kisitlamalar"], sort_keys=True) == before)

    print("\n[8) anında devam butonu]")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from dialogs.preflight_dialog import PreflightDialog, run_preflight
    report = {"ok": False, "total_cells": 20, "max_fillable": 12, "total_demand": 20,
              "classes": 1, "open_hours_per_class": 20,
              "overloaded_teachers": [{"teacher": TEACHER, "assigned": 20,
                                       "available": 12, "shortfall": 8}],
              "understaffed_slots": [], "idle_teachers": []}
    dlg = PreflightDialog(report, DAYS, mode="save")
    check("devam düğmesi hemen aktif (kullanıcıyı bekletmez)", dlg.btn_go.isEnabled())
    check("düğmede onay metni var", "Yine de Kaydet" in dlg.btn_go.text() or "Yoksay" in dlg.btn_go.text(), dlg.btn_go.text())
    check("geri dön düğmesi hep açık", dlg.btn_fix.isEnabled())
    dlg.deleteLater()

    print("\n[9) sorun yoksa hiç pencere açılmaz]")
    fine = make_store("kurum_a")
    fine["siniflar"] = [{"ad": "9A", "timeoff": [[2] * P for _ in DAYS]}]
    fine["atamalar"] = [{"class": "9A", "subject": "Matematik", "teacher": TEACHER,
                         "duration": 2, "type": "2"}]
    check("uygun kurulumda doğrudan devam", run_preflight(fine, "kurum_a", None) is True)


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
