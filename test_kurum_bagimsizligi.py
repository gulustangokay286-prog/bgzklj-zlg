"""
test_kurum_bagimsizligi.py — kurumlar zaman tablosu bakımından TAMAMEN bağımsız mı?

    python test_kurum_bagimsizligi.py

Hocaların şikâyeti: ortak öğretmenin zaman tablosu "kendi kendine" değişiyor,
kapatıp açtığı saate motor ders koymuyor. Bunun üç kaynağı vardı (bkz.
constraint_sync.INSTITUTIONS_INDEPENDENT). Bu dosya, bayrak AÇIKKEN — yani
uygulamanın her zaman çalıştığı kipte — hiçbir çapraz kurum verisinin hiçbir
yere sızmadığını sınar:

  * motor / ön kontrol      -> _build_teacher_timeoff_map, _build_cross_institution_map
  * elle yerleştirme        -> placement_engine snapshot, get_cross_institution_teacher_busy_slots
  * Zaman Tablosu ekranı    -> kilit yok, rezervasyon yok, açılan saat gerçekten açık
  * dışa yayın              -> publish hiçbir dosyaya yazmaz
  * planlayıcı iş parçacığı -> "Diğer Kurumları Yoksay" kapatılamaz
"""
import json
import os
import shutil
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SANDBOX = os.path.join(tempfile.gettempdir(), "chenki_bagimsiz_test")
shutil.rmtree(SANDBOX, ignore_errors=True)
os.makedirs(SANDBOX, exist_ok=True)
INST_ROOT = os.path.join(SANDBOX, "institutions")
GLOBAL_FILE = os.path.join(SANDBOX, "global_kisitlamalar.json")

import version_store  # noqa: E402
import constraint_sync  # noqa: E402

version_store._base_dir = lambda: INST_ROOT
constraint_sync._global_path = lambda: GLOBAL_FILE


class _NullCloud:
    def __getattr__(self, _name):
        return lambda *a, **k: True


sys.modules["cloud_sync"] = _NullCloud()

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


def make_store(slug, placements=()):
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
        "grid_placements": list(placements),
    }


def make_institution(slug, name):
    os.makedirs(os.path.join(INST_ROOT, slug, "versions"), exist_ok=True)
    with open(os.path.join(INST_ROOT, slug, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"name": name}, f)


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def run():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841

    print("\n[kurulum: A ve B; ortak öğretmen B'de pazartesi 1-2'de derste, "
          "B'de kişisel kısıtı ve rezervasyonu var]")
    make_institution("kurum_a", "Kurum A")
    make_institution("kurum_b", "Kurum B")
    a = make_store("kurum_a")
    b = make_store("kurum_b", placements=[
        {"day": 0, "period": 0, "duration": 2, "teacher_name": TEACHER,
         "subject_name": "Matematik", "class_name": "9A"}])
    fn_b = version_store.save_version("kurum_b", b, note="b")
    version_store.set_active_version("kurum_b", fn_b)

    # Paylaşım verisini bayrak KAPALIYKEN üret — mekanizma çalışıyor olsun ki
    # bağımsız kipte "okumuyor" iddiası anlamlı olsun.
    constraint_sync.INSTITUTIONS_INDEPENDENT = False
    tb = b["ogretmenler"][0]
    personal = constraint_sync.get_personal(tb, TEACHER, b)
    personal[2][0] = True
    constraint_sync.set_personal(tb, TEACHER, b, personal)
    constraint_sync.publish("kurum_b", b)
    check("B rezervasyon yazabildi (mekanizma sağlam)",
          constraint_sync.set_reservation("kurum_b", TEACHER, (3, 1), True))
    import auto_scheduler
    version_store.invalidate_cross_busy_cache()
    blocked_shared, _ = auto_scheduler._build_teacher_timeoff_map(a, "kurum_a")
    check("paylaşım açıkken B'nin kişisel kısıtı A'ya sızıyor (kontrol)",
          (2, 0) in blocked_shared.get(auto_scheduler.norm_teacher(TEACHER), set()))
    occ, _ = auto_scheduler._build_cross_institution_map("kurum_a")
    check("paylaşım açıkken B'nin dersi A'da meşgul (kontrol)",
          (0, 0) in occ.get(auto_scheduler.norm_teacher(TEACHER), set()))
    constraint_sync.INSTITUTIONS_INDEPENDENT = True
    version_store.invalidate_cross_busy_cache()
    check("uygulama kipi: bayrak açık", constraint_sync.institutions_independent())

    print("\n[1) motor ve ön kontrol: A yalnızca kendi tablosunu görür]")
    blocked, avoid = auto_scheduler._build_teacher_timeoff_map(a, "kurum_a")
    key = auto_scheduler.norm_teacher(TEACHER)
    check("B'nin kişisel kısıtı A'da kapalı değil", (2, 0) not in blocked.get(key, set()),
          str(sorted(blocked.get(key, set()))))
    check("A'da hiç kapalı saat yok", not blocked.get(key), str(blocked))
    occ, det = auto_scheduler._build_cross_institution_map("kurum_a")
    check("B'deki ders A'nın motorunda meşgul değil", not occ and not det, str(occ))
    check("rezervasyon defteri A için boş",
          not constraint_sync.reserved_by_others("kurum_a"))
    check("reservations_for boş", not constraint_sync.reservations_for(TEACHER))
    check("shared_teacher_states boş",
          not constraint_sync.shared_teacher_states("kurum_a", 5, P))
    rep = auto_scheduler.check_feasibility(a, "kurum_a")
    check("ön kontrol: A uygun (B'nin verisi sayılmadı)", rep.get("ok"), str(rep)[:200])

    print("\n[2) elle yerleştirme: çapraz çakışma yok]")
    check("get_cross_institution_teacher_busy_slots boş",
          not version_store.get_cross_institution_teacher_busy_slots(exclude_slug="kurum_a"))
    import placement_engine
    snap = placement_engine.TimetableSnapshot(a, institution_slug="kurum_a")
    check("snapshot.cross_busy boş", not snap.cross_busy, str(snap.cross_busy))
    check("snapshot.reserved boş", not snap.reserved, str(snap.reserved))

    print("\n[3) dışa yayın kapalı: publish hiçbir dosyaya yazmaz]")
    meta_a = os.path.join(INST_ROOT, "kurum_a", "meta.json")
    before_meta = read(meta_a)
    before_global = read(GLOBAL_FILE) if os.path.exists(GLOBAL_FILE) else None
    ta = a["ogretmenler"][0]
    pa = constraint_sync.get_personal(ta, TEACHER, a)
    pa[4][0] = True
    constraint_sync.set_personal(ta, TEACHER, a, pa)
    constraint_sync.publish("kurum_a", a)
    after_global = read(GLOBAL_FILE) if os.path.exists(GLOBAL_FILE) else None
    check("meta.json değişmedi", read(meta_a) == before_meta)
    check("ortak dosya değişmedi", after_global == before_global)
    check("rezervasyon yazılamaz",
          constraint_sync.set_reservation("kurum_a", TEACHER, (1, 1), True) is False)

    print("\n[4) planlayıcı iş parçacığı: 'Diğer Kurumları Yoksay' kapatılamaz]")
    w = auto_scheduler.AutoSchedulerWorker(a, institution_slug="kurum_a",
                                           ignore_other_institutions=False)
    check("False verilse de True", w.ignore_other_institutions is True)

    print("\n[5) Zaman Tablosu ekranı: kilit yok, açılan saat gerçekten açık]")
    from dialogs.timeoff_dialog import TimeoffDialog
    # Öğretmende kişisel kısıt var: çarşamba 1. saat
    ta = a["ogretmenler"][0]
    dlg = TimeoffDialog(ta, "Öğretmen", a)
    check("çapraz kilit yok", not dlg.cross_institution_locks, str(dlg.cross_institution_locks))
    check("başka kurum rezervasyonu görünmüyor", not dlg.other_reserved)
    check("cuma 1. saat açılıştan kişisel-kapalı", dlg.timeoff_data[4][0] == 0 and dlg._is_personal(4, 0))
    dlg._on_cell_clicked(0, 4)          # row=saat, col=gün
    check("sol tık: kurum matrisi açıldı", dlg.timeoff_data[4][0] == 2)
    check("sol tık: kişisel katman da kalktı", not dlg._is_personal(4, 0))
    # Kaydetme yolundaki tek yazma noktası: set_matrix + set_personal
    constraint_sync.set_matrix(ta, TEACHER, a, dlg.timeoff_data)
    constraint_sync.set_personal(ta, TEACHER, a, dlg.personal_data)
    check("kayıt sonrası saat gerçekten açık",
          constraint_sync.get_matrix(ta, TEACHER, a)[4][0] == constraint_sync.OPEN)
    blocked, _ = auto_scheduler._build_teacher_timeoff_map(a, "kurum_a")
    check("motor da açık görüyor", (4, 0) not in blocked.get(key, set()))
    # Tümünü Aç da kişisel katmanı temizler
    pa = constraint_sync.get_personal(ta, TEACHER, a)
    pa[1][1] = True
    constraint_sync.set_personal(ta, TEACHER, a, pa)
    dlg2 = TimeoffDialog(ta, "Öğretmen", a)
    dlg2._make_all_open()
    check("Tümünü Aç: kişisel katman temiz",
          not any(any(r) for r in dlg2.personal_data))
    dlg.deleteLater(); dlg2.deleteLater()

    print("\n[6) yükleme temizliği yalnızca kurum sarmalayıcısını siler]")
    kis = {
        TEACHER: {"0,0": 0, "0,1": 2},                     # birim girdisi — kalmalı
        "bogazici_egitim_kurumlari": {"X": {"0,0": 0}},    # sarmalayıcı — gitmeli
        "kurum_z": {"Y": {"1,1": 0}},                      # adı bilinmeyen sarmalayıcı — gitmeli
    }
    n = constraint_sync.strip_institution_wrappers(kis)
    check("iki sarmalayıcı silindi", n == 2 and set(kis) == {TEACHER}, str(kis))
    check("birim girdisi olduğu gibi", kis[TEACHER] == {"0,0": 0, "0,1": 2})

    print(f"\n{len(PASSED)} geçti, {len(FAILED)} kaldı")
    for name, detail in FAILED:
        print(f"  - {name}: {detail}")
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(run())
