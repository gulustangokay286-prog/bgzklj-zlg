"""test_kart_kimligi.py — kart kimliği, sahte "değişti" ve sonsuz sürüm çekme.

    python test_kart_kimligi.py

Üç şikâyet tek köke iniyordu: ızgara → mağaza senkronu mağazayı ekrandaki
hücrelerden yeniden kuruyor, kimlikleri siliyor ve ekrana ait sayıları
(origin_row/origin_col) içerik diye kaydediyordu.

  1. Açıp bir sınıf seçince "kaydet" penceresi çıkıyordu   → çıkmamalı
  2. 6. saatteki Fizik indirilince 4. saatteki de iniyordu  → yalnızca 6.
  3. Aynı hocanın başka sınıftaki dersi de iniyordu         → inmemeli
  4. Sunucu özeti tutmayan sürüm her sorguda yeniden iniyordu → bir kez
"""
import copy
import json
import os
import shutil
import sys
import tempfile
import time
import faulthandler
faulthandler.dump_traceback_later(90, exit=True)

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["CHENKI_API_URL"] = "http://127.0.0.1:9"  # bulut kapalı
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SANDBOX = os.path.join(tempfile.gettempdir(), "chenki_kart_kimligi_test")
shutil.rmtree(SANDBOX, ignore_errors=True)
os.makedirs(os.path.join(SANDBOX, "institutions"), exist_ok=True)
SLUG = "test_kimlik_okulu"

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def placement(day, period, subject, teacher, cls, block=None, duration=1, **extra):
    p = {
        "day": day, "period": period, "row": period, "col": day,
        "class_name": cls, "class": cls,
        "teacher_name": teacher, "teacher": teacher,
        "subject_name": subject, "subject": subject,
        "duration": duration, "is_manual": True,
        "locked": False, "is_combined": False, "combined_classes": [],
    }
    if block:
        p["block_id"] = block
    p.update(extra)
    return p


def make_store():
    """Eski biçim: kimliksiz, saat saat bölünmüş, çizim alanları sızmış."""
    return {
        "settings": {"days": ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"],
                     "periods": 8, "institution_slug": SLUG},
        "siniflar": [{"ad": "9A"}, {"ad": "9B"}],
        "ogretmenler": [{"ad": "Selim Kurtaran"}, {"ad": "Ayşe Demir"}],
        "dersler": [{"ad": "Fizik"}, {"ad": "Matematik"}],
        "derslikler": [],
        "atamalar": [
            {"subject": "Fizik", "teacher": "Selim Kurtaran", "class": "9A", "duration": 4, "type": "2+1+1"},
            {"subject": "Fizik", "teacher": "Selim Kurtaran", "class": "9B", "duration": 1, "type": "1"},
            {"subject": "Matematik", "teacher": "Ayşe Demir", "class": "9A", "duration": 2, "type": "2"},
        ],
        "grid_placements": [
            # 9A Pazartesi: Fizik 0-1 (iki saatlik blok, saat saat bölünmüş),
            # Fizik 3, Fizik 5 (ayrı dersler), Matematik 6-7
            placement(0, 0, "Fizik", "Selim Kurtaran", "9A", origin_row=0, origin_col=0, day_idx=0),
            placement(0, 1, "Fizik", "Selim Kurtaran", "9A", origin_row=0, origin_col=0, day_idx=0),
            placement(0, 3, "Fizik", "Selim Kurtaran", "9A", origin_row=0, origin_col=3, day_idx=0),
            placement(0, 5, "Fizik", "Selim Kurtaran", "9A", origin_row=0, origin_col=5, day_idx=0),
            placement(0, 6, "Matematik", "Ayşe Demir", "9A", origin_row=0, origin_col=6, day_idx=0),
            placement(0, 7, "Matematik", "Ayşe Demir", "9A", origin_row=0, origin_col=6, day_idx=0),
            # 9B Pazartesi 4: aynı hocanın aynı dersi, başka sınıf
            placement(0, 4, "Fizik", "Selim Kurtaran", "9B", origin_row=1, origin_col=4, day_idx=0),
        ],
        "kisitlamalar": {},
    }


def slots(store, subject, cls):
    return sorted((int(p["day"]), int(p["period"])) for p in store.get("grid_placements", [])
                  if (p.get("subject_name") or p.get("subject")) == subject
                  and (p.get("class_name") or p.get("class")) == cls)


def run():
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication.instance() or QApplication(sys.argv)
    for n in ("question", "warning", "critical", "information"):
        setattr(QMessageBox, n, staticmethod(lambda *a, **k: QMessageBox.Yes))

    import version_store
    version_store._base_dir = lambda: os.path.join(SANDBOX, "institutions")
    import sync_coordinator
    sync_coordinator.enqueue = lambda *a, **k: None

    # ── 1. Onarım: kimlik, bloklama, çizim alanları ───────────────────
    print("\n[placement_identity.normalize_store]")
    import placement_identity as pi
    st = make_store()
    n = pi.normalize_store(st)
    pl = st["grid_placements"]
    check("onarım bir şey yaptı", n > 0, str(n))
    check("hiçbir kayıtta çizim alanı kalmadı",
          not any(k in p for p in pl for k in pi.RENDER_KEYS))
    check("her kaydın kimliği var", all(p.get("block_id") for p in pl))
    ids = {(p["period"], p["class_name"]): p["block_id"] for p in pl}
    check("Fizik 0-1 aynı blok (ızgara da birleştiriyor)", ids[(0, "9A")] == ids[(1, "9A")])
    check("Fizik 3 ayrı blok", ids[(3, "9A")] not in (ids[(0, "9A")], ids[(5, "9A")]))
    check("Fizik 5 ayrı blok", ids[(5, "9A")] != ids[(3, "9A")])
    check("9B'nin Fizik'i 9A'nınkilerden ayrı", ids[(4, "9B")] not in {v for k, v in ids.items() if k[1] == "9A"})
    check("Matematik 6-7 aynı blok", ids[(6, "9A")] == ids[(7, "9A")])
    check("ikinci onarım hiçbir şey yapmıyor (idempotent)", pi.normalize_store(st) == 0)
    # üç ardışık saat: ızgara 2+1 çizer, onarım da öyle bloklamalı
    st3 = {"grid_placements": [placement(1, 2, "Kimya", "X", "9A"), placement(1, 3, "Kimya", "X", "9A"),
                               placement(1, 4, "Kimya", "X", "9A")]}
    pi.normalize_store(st3)
    b = [p["block_id"] for p in sorted(st3["grid_placements"], key=lambda p: p["period"])]
    check("üç ardışık saat 2+1 bloklanıyor", b[0] == b[1] and b[2] != b[0], str(b))

    # ── 2. Pencere: açıp görünüm değiştirmek "değişti" saymamalı ─────
    print("\n[açılışta ve görünüm değişince değişiklik yok]")
    inst_dir = os.path.join(SANDBOX, "institutions", SLUG)
    os.makedirs(os.path.join(inst_dir, "versions"), exist_ok=True)
    with open(os.path.join(inst_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"name": "Test"}, f)
    fn = version_store.save_version(SLUG, make_store(), note="t")
    roz = os.path.join(inst_dir, "versions", fn)

    from main_window import MainWindow
    win = MainWindow(override_db_path=roz, institution_slug=SLUG,
                     institution_name="Test", version_filename=fn)
    win._set_last_db_path = lambda *a, **k: None
    check("açılışta değişiklik yok", not win._content_changed())
    check("açılışta bellekteki kayıtların kimliği var",
          all(p.get("block_id") for p in win.data_store["grid_placements"]))
    check("açılışta 7 kayıt duruyor (bölünme/çoğalma yok)",
          len(win.data_store["grid_placements"]) == 7, str(len(win.data_store["grid_placements"])))

    win._restore_grid_placements("class", "9A")
    check("9A seçildi → değişiklik yok", not win._content_changed())
    try:
        win._grid.current_view_mode = "teachers"
        win._refresh_grid()
        check("öğretmen görünümü → değişiklik yok", not win._content_changed())
        win._grid.current_view_mode = "classes"
        win._refresh_grid()
    except Exception as exc:
        check("öğretmen görünümü → değişiklik yok", False, str(exc))
    for _ in range(3):
        win._refresh_grid(); win._refresh_tree()
    check("üç kez tazeleme → değişiklik yok", not win._content_changed())

    import dialogs.save_location_dialog as sld
    calls = []
    orig_choose = sld.SaveLocationDialog.choose

    def fake_choose(*a, **k):
        calls.append(1)
        return (None, None, "", "", True)   # vazgeç
    sld.SaveLocationDialog.choose = staticmethod(fake_choose)
    win.go_home_requested = lambda: None
    win._go_home()
    check("ana sayfaya dönerken kaydet penceresi AÇILMADI", not calls)

    # gerçek bir değişiklik: Fizik 3 → Salı 0
    periods = 8
    win._on_lesson_dropped(0, 1 * periods + 0, {
        "subject_name": "Fizik", "teacher_name": "Selim Kurtaran", "class_name": "9A",
        "duration": 1, "is_move": True, "origin_row": 0, "origin_col": 3,
    })
    check("ders taşınınca değişiklik VAR", win._content_changed())
    win._go_home()
    check("değişiklik varken kaydet penceresi açıldı", len(calls) == 1)
    win._mark_saved()
    check("kaydedince değişiklik yok", not win._content_changed())

    # ── 3. Tepsiye indirmek yalnızca tutulan kartı indirir ───────────
    print("\n[tepsiye indirme: yalnızca tutulan kart]")
    win.data_store.clear()
    win.data_store.update(make_store())
    pi.normalize_store(win.data_store)
    win._refresh_grid(); win._refresh_tree()
    table = win._grid.table
    before_9a = slots(win.data_store, "Fizik", "9A")
    before_9b = slots(win.data_store, "Fizik", "9B")
    check("başlangıç: 9A Fizik 0,1,3,5", before_9a == [(0, 0), (0, 1), (0, 3), (0, 5)], str(before_9a))
    # 6. saatteki (indeks 5) Fizik'i indir
    table._delete_lesson_at(0, 0 * periods + 5)
    after_9a = slots(win.data_store, "Fizik", "9A")
    after_9b = slots(win.data_store, "Fizik", "9B")
    check("yalnızca 6. saat gitti", after_9a == [(0, 0), (0, 1), (0, 3)], str(after_9a))
    check("4. saatteki Fizik yerinde", (0, 3) in after_9a)
    check("9B'deki Fizik (aynı hoca) yerinde", after_9b == before_9b, str(after_9b))
    mat = slots(win.data_store, "Matematik", "9A")
    check("komşu Matematik yerinde", mat == [(0, 6), (0, 7)], str(mat))
    # iki saatlik bloğun ikinci saatinden tutup indirmek bloğun tamamını indirir
    table._delete_lesson_at(0, 0 * periods + 1)
    after_9a = slots(win.data_store, "Fizik", "9A")
    check("iki saatlik blok bütün olarak indi, 4. saat kaldı", after_9a == [(0, 3)], str(after_9a))

    # KİMLİKSİZ eski veri (başka bilgisayardan gelmiş olabilir): yine yalnızca tutulan
    print("\n[kimliksiz eski veri: yine yalnızca tutulan kart]")
    win.data_store.clear()
    legacy = make_store()
    for p in legacy["grid_placements"]:
        p.pop("block_id", None)
    win.data_store.update(legacy)          # onarım YOK: kimliksiz kalsın
    win._refresh_grid(); win._refresh_tree()
    table._delete_lesson_at(0, 0 * periods + 5)
    after_9a = slots(win.data_store, "Fizik", "9A")
    after_9b = slots(win.data_store, "Fizik", "9B")
    check("kimliksiz: yalnızca 6. saat gitti", after_9a == [(0, 0), (0, 1), (0, 3)], str(after_9a))
    check("kimliksiz: 9B'deki Fizik yerinde", after_9b == [(0, 4)], str(after_9b))

    # ── 4. Sunucu özeti tutmayan sürüm bir kez iner, sonra susar ─────
    print("\n[sürüm çekme: özet tutmasa da bir kez]")
    from api_client import api_client as ac
    # Dosya az önce kaydedildi ve "gönderilmeyi bekliyor" işaretli; bekleyen
    # dosya hiç indirilmez. Sunucuya gitmiş sayalım.
    data = version_store.load_version(SLUG, fn)
    data["_sync_meta"] = {"revision": 1, "slug": SLUG, "key": fn.replace(".roz", "_roz")}
    version_store._atomic_write_json(roz, data)
    key = fn.replace(".roz", "_roz")
    index_payload = {SLUG: {"meta": {}, "tombstones": [], "index": [
        {"filename": fn, "key": key, "hash": "SUNUCU-FARKLI-OZET",
         "sync_revision": 1, "last_modified": "x"}]}}
    fetched = []

    class _Resp:
        def __init__(self, status, body):
            self.status_code = status; self._b = body
        def json(self):
            return self._b

    def fake_request(method, url, **kw):
        if url.endswith("/api/sync/index"):
            return _Resp(200, index_payload)
        fetched.append(url)
        return _Resp(200, copy.deepcopy(data))

    ac._request_with_retry = fake_request
    ac.get_stored_auth_data = lambda: {}
    ac.is_on_dashboard = False
    ac._index_cache = {}
    for i in range(4):
        ac._pull_index()
    check("özet tutmayan sürüm yalnızca BİR kez indirildi (4 sorguda)",
          len(fetched) == 1, f"{len(fetched)} indirme")
    # sunucuda gerçekten değişince yeniden bakar
    index_payload[SLUG]["index"][0]["sync_revision"] = 2
    ac._pull_index()
    check("sunucu revizyonu değişince yeniden indirdi", len(fetched) == 2, f"{len(fetched)} indirme")

    win._mark_saved()
    win._discard_changes = True     # kapanışta hiçbir şey yazma, pencere açma
    win.close(); win.deleteLater()
    sld.SaveLocationDialog.choose = orig_choose


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
        print(f"  ✗ {name}: {detail}")
    shutil.rmtree(SANDBOX, ignore_errors=True)
    os._exit(1 if FAILED else 0)
