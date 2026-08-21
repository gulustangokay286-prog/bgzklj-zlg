"""
test_delete_propagation.py — silinen versiyonlar geri gelmemeli.

    python test_delete_propagation.py

Kullanıcının yaşadığı senaryoyu birebir kurar: bir cihazda silinen versiyon,
sunucudan ya da elinde hâlâ kopya bulunan başka bir cihazdan (Mac) geri geliyordu.
Ağ katmanı taklit edilir; disk ve tombstone mantığı gerçektir.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SANDBOX = os.path.join(tempfile.gettempdir(), "chenki_delete_test")
shutil.rmtree(SANDBOX, ignore_errors=True)
os.makedirs(SANDBOX, exist_ok=True)

import version_store  # noqa: E402

version_store._base_dir = lambda: os.path.join(SANDBOX, "institutions")


class _NullCloud:
    def __getattr__(self, _name):
        return lambda *a, **k: True


# Bu iki modulu susturmak ZORUNLU. version_store.create_institution /
# save_version / set_active_version, arka planda cloud_sync.push_institution_to_rtdb
# calistiriyor; stub konmazsa test kurumlari GERCEK VDS'e yukleniyor. Bir kez oldu:
# "Silme Testi" ve "Mac Kurumu" uretim sunucusunda belirdi ve elle temizlendi.
sys.modules["cloud_sync"] = _NullCloud()
sys.modules["database"] = _NullCloud()
# queue_cloud_delete de arka planda api_client'i import ediyor. Test ilerleyen
# bolumlerde gercegini bilerek yukluyor; buradaki stub, o ana kadar hicbir istegin
# disariya cikmamasini garantiler.
sys.modules["api_client"] = _NullCloud()

PASSED, FAILED = [], []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def schedule(tag):
    return {
        "dersler": [{"ad": "Matematik"}],
        "siniflar": [{"ad": "9A"}],
        "ogretmenler": [{"ad": "Test Hoca"}],
        "atamalar": [],
        "settings": {"periods": 8},
        "grid_placements": [
            {"day": 0, "period": 0, "subject_name": tag,
             "teacher_name": "Test Hoca", "class_name": "9A", "duration": 1}
        ],
    }


def version_files(slug):
    ver_dir = version_store._versions_dir(slug)
    return sorted(f for f in os.listdir(ver_dir) if f.endswith(".roz"))


def run():
    print("\n[hazırlık]")
    inst = version_store.create_institution("Silme Testi")
    slug = inst["slug"]
    victim = version_store.save_version(slug, schedule("Silinecek"),
                                        note="silinecek", allow_duplicate=True)
    keeper = version_store.save_version(slug, schedule("Kalacak"),
                                        note="kalacak", allow_duplicate=True)
    check("iki versiyon oluşturuldu", victim in version_files(slug) and keeper in version_files(slug))

    print("\n[silme]")
    version_store.delete_version(slug, victim)
    listed = {v["filename"] for v in version_store.list_versions(slug)}
    check("silinen versiyon listede yok", victim not in listed, str(listed))
    check("dosya diskten kaldırıldı", victim not in version_files(slug))
    check("tombstone kaydedildi", version_store.is_tombstoned(slug, victim))
    check("diğer versiyon duruyor", keeper in listed)

    print("\n[sunucu versiyonu geri göndermeye çalışıyor]")
    # Asıl hata: sunucudaki DELETE kalıcı olmadığı için sonraki poll dosyayı
    # geri yazıyordu. Şimdi tombstone bunu engellemeli.
    ver_dir = version_store._versions_dir(slug)
    version_store._atomic_write_json(os.path.join(ver_dir, victim), schedule("Silinecek"))
    version_store.invalidate_version_summary(slug, victim)
    listed = {v["filename"] for v in version_store.list_versions(slug)}
    check("diskte olsa bile listelenmiyor", victim not in listed, str(listed))

    removed = version_store.enforce_tombstones(slug)
    check("enforce_tombstones dosyayı temizledi", removed == 1 and victim not in version_files(slug),
          f"removed={removed}")

    print("\n[bekleyen silme kuyruğu]")
    # Ağ yokken yapılan silme, uygulama kapanıp açılsa bile kaybolmamalı.
    version_store._save_pending_deletes([])
    version_store.queue_cloud_delete(slug, victim)
    pending = version_store._load_pending_deletes()
    check("silme kuyruğa alındı", any(p["filename"] == victim for p in pending), str(pending))

    calls = []

    class _FailingClient:
        def delete_version_from_rtdb(self, s, f):
            calls.append((s, f))
            return False

    class _WorkingClient:
        def delete_version_from_rtdb(self, s, f):
            calls.append((s, f))
            return True

    import types
    fake = types.ModuleType("api_client")
    fake.api_client = _FailingClient()
    sys.modules["api_client"] = fake

    confirmed = version_store.flush_pending_deletes()
    check("sunucu erişilemezken kuyruk korunuyor",
          confirmed == 0 and version_store.pending_delete_count() == 1,
          f"confirmed={confirmed}, pending={version_store.pending_delete_count()}")
    check("yine de denendi", len(calls) == 1, str(calls))

    fake.api_client = _WorkingClient()
    confirmed = version_store.flush_pending_deletes()
    check("sunucu dönünce silme tamamlanıyor",
          confirmed == 1 and version_store.pending_delete_count() == 0,
          f"confirmed={confirmed}, pending={version_store.pending_delete_count()}")

    print("\n[ikinci cihaz (Mac) kopyayı geri yüklemeye çalışıyor]")
    # push_version_to_rtdb, tombstone'lu bir dosyayı ASLA yüklememeli.
    del sys.modules["api_client"]
    import api_client as real_api

    uploads = []
    original_request = real_api.APIClient._request_with_retry

    def spy(self, method, url, **kwargs):
        uploads.append((method, url))
        class _Resp:
            status_code = 200
            def json(self_inner):
                return {"msg": "ok"}
        return _Resp()

    real_api.APIClient._request_with_retry = spy
    try:
        version_store._save_pending_deletes([])
        ok = real_api.api_client.push_version_to_rtdb(slug, victim, schedule("Silinecek"))
        check("silinmiş versiyon yüklenmiyor", ok is False, str(ok))
        check("hiç PUT isteği gitmedi", not any(m == "PUT" for m, _ in uploads), str(uploads))
        check("silme yeniden kuyruğa alındı",
              any(p["filename"] == victim for p in version_store._load_pending_deletes()))

        uploads.clear()
        ok = real_api.api_client.push_version_to_rtdb(slug, keeper, schedule("Kalacak"))
        check("silinmemiş versiyon normal yükleniyor", ok is True and
              any(m == "PUT" for m, _ in uploads), f"ok={ok}, {uploads}")
    finally:
        real_api.APIClient._request_with_retry = original_request

    print("\n[tombstone'lar cihazlar arasında yayılıyor]")
    # Windows'ta silinen, Mac'in meta'sına birleşerek ulaşmalı.
    other = version_store.create_institution("Mac Kurumu")
    o_slug = other["slug"]
    mac_only = version_store.save_version(o_slug, schedule("MacDosyasi"),
                                          note="mac", allow_duplicate=True)
    check("mac kurumunda versiyon var", mac_only in version_files(o_slug))

    version_store.merge_tombstones(o_slug, [mac_only])
    check("uzaktan gelen tombstone birleşti", version_store.is_tombstoned(o_slug, mac_only))
    check("birleşme sonrası listeden düştü",
          mac_only not in {v["filename"] for v in version_store.list_versions(o_slug)})

    # Yerel tombstone, sunucudan boş liste gelse bile silinmemeli.
    local_before = version_store.list_tombstones(o_slug)
    version_store.merge_tombstones(o_slug, [])
    check("boş uzak liste yerel tombstone'u silmiyor",
          version_store.list_tombstones(o_slug) == local_before,
          f"{local_before} -> {version_store.list_tombstones(o_slug)}")

    print("\n[_merge_meta tombstone'u ezmiyor]")
    inst_dir = os.path.join(version_store._base_dir(), o_slug)
    real_api.APIClient._merge_meta(inst_dir, {"name": "Mac Kurumu", "color": "#FF0000"})
    check("sunucu meta'sı tombstone listesini silmedi",
          version_store.is_tombstoned(o_slug, mac_only),
          str(version_store.list_tombstones(o_slug)))

    real_api.APIClient._merge_meta(inst_dir, {"tombstones": ["baska_dosya.roz"]})
    tombs = version_store.list_tombstones(o_slug)
    check("uzak ve yerel tombstone'lar birleşti",
          mac_only in tombs and "baska_dosya.roz" in tombs, str(tombs))

    print("\n[geri yükleme açıkça yapılabiliyor]")
    version_store.remove_tombstone(o_slug, mac_only)
    check("tombstone kaldırılabiliyor", not version_store.is_tombstoned(o_slug, mac_only))

    print("\n[aktif versiyon silinirse]")
    a = version_store.save_version(slug, schedule("A"), allow_duplicate=True)
    version_store.set_active_version(slug, a)
    version_store.delete_version(slug, a)
    active = version_store.get_active_version(slug)
    remaining = {v["filename"] for v in version_store.list_versions(slug)}
    check("aktif versiyon silinince başkası aktif oldu",
          active in remaining and active != a, f"active={active}, kalan={remaining}")


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
        shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(1 if FAILED else 0)
