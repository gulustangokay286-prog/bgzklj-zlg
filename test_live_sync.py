"""
test_live_sync.py — canli VDS uzerinde iki-cihaz senkron testi.

    python test_live_sync.py

Gecici bir kurum uzerinde calisir ve sonunda temizler; gercek kurumlara dokunmaz.
En kritik kontrol: istemcinin hash'i ile sunucunun hash'inin AYNI olmasi. Farkli
olsalardi her yoklamada her versiyon "degismis" gorunur ve 11.59 MB yeniden inerdi.
"""
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests  # noqa: E402

BASE = os.environ.get("CHENKI_API_URL", "http://213.142.159.36")
SLUG = "__canli_senkron_testi__"

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def schedule(tag, extra=0):
    return {
        "dersler": [{"ad": "Matematik"}],
        "siniflar": [{"ad": "9A"}],
        "ogretmenler": [{"ad": "Test Hoca"}],
        "atamalar": [],
        "settings": {"periods": 8},
        "grid_placements": [
            {"day": i, "period": 0, "subject_name": tag,
             "teacher_name": "Test Hoca", "class_name": "9A", "duration": 1}
            for i in range(1 + extra)
        ],
    }


def main():
    import version_store

    tok = requests.post(f"{BASE}/auth/login",
                        data={"username": "sehersanli@chenki.net", "password": "seher2311"},
                        timeout=20).json()["access_token"]
    hdr = {"Authorization": f"Bearer {tok}"}

    print("\n[hash uyumu — en kritik kontrol]")
    body = schedule("HashTesti")
    body["_version_meta"] = {"filename": "v001_hash_manual.roz", "note": "n",
                             "last_modified": "2026-01-01T00:00:00"}
    requests.put(f"{BASE}/api/sync/{SLUG}/v001_hash_manual_roz", json=body, headers=hdr, timeout=30)

    idx = requests.get(f"{BASE}/api/sync/index", headers=hdr, timeout=30).json()
    entry = next((e for e in idx.get(SLUG, {}).get("index", [])
                  if e["filename"] == "v001_hash_manual.roz"), None)
    check("sunucu indekste kayit dondu", entry is not None, str(idx.get(SLUG, {}).get("index")))
    if entry:
        local_hash = version_store.compute_data_hash(body)
        check("istemci ve sunucu hash'i AYNI", entry["hash"] == local_hash,
              f"sunucu={entry['hash'][:16]} istemci={local_hash[:16]}")

    # Ayni icerik, sadece volatile alan degisti -> hash DEGISMEMELI.
    body2 = dict(body)
    body2["_version_meta"] = {"filename": "v001_hash_manual.roz", "note": "n",
                              "last_modified": "2026-09-09T09:09:09"}
    check("volatile alan hash'i degistirmiyor",
          version_store.compute_data_hash(body2) == version_store.compute_data_hash(body))

    print("\n[indeks boyutu]")
    t0 = time.time()
    r_idx = requests.get(f"{BASE}/api/sync/index", headers=hdr, timeout=60)
    idx_t = time.time() - t0
    check("indeks hizli", idx_t < 3.0, f"{idx_t:.2f} saniye")
    check("indeks kucuk", len(r_idx.content) < 500_000,
          f"{len(r_idx.content):,} bayt")
    print(f"        {len(r_idx.content):,} bayt / {idx_t:.2f} saniye")

    print("\n[iki cihaz: A yazar, B okur]")
    sandbox = os.path.join(tempfile.gettempdir(), "chenki_device_b")
    shutil.rmtree(sandbox, ignore_errors=True)
    os.makedirs(sandbox, exist_ok=True)
    version_store._base_dir = lambda: os.path.join(sandbox, "institutions")

    from api_client import api_client
    api_client._supports_index = None

    # Cihaz B ilk kez senkron oluyor
    t0 = time.time()
    ok, msg, n = api_client.pull_all_from_rtdb()
    first_t = time.time() - t0
    check("cihaz B ilk senkronu yapti", ok, msg)
    got = {v["filename"] for v in version_store.list_versions(SLUG)}
    check("A'nin yazdigi versiyon B'ye ulasti", "v001_hash_manual.roz" in got, str(got))
    print(f"        ilk senkron: {first_t:.1f} saniye, {n} degisiklik")

    # Ikinci senkron: hicbir sey degismedi -> hicbir sey inmemeli
    t0 = time.time()
    ok, msg, n2 = api_client.pull_all_from_rtdb()
    second_t = time.time() - t0
    check("degisiklik yokken hicbir sey inmiyor", n2 == 0, f"{n2} degisiklik indi")
    check("bos senkron hizli", second_t < 3.0, f"{second_t:.2f} saniye")
    print(f"        bos senkron: {second_t:.2f} saniye")

    # A yeni bir versiyon yazar -> B bir sonraki senkronda gormeli
    new_body = schedule("YeniDers", extra=2)
    new_body["_version_meta"] = {"filename": "v002_yeni_manual.roz", "note": "yeni"}
    requests.put(f"{BASE}/api/sync/{SLUG}/v002_yeni_manual_roz",
                 json=new_body, headers=hdr, timeout=30)

    t0 = time.time()
    ok, msg, n3 = api_client.pull_all_from_rtdb()
    third_t = time.time() - t0
    got = {v["filename"] for v in version_store.list_versions(SLUG)}
    check("A'nin YENI versiyonu B'ye geldi", "v002_yeni_manual.roz" in got, str(got))
    check("sadece degisen indi", n3 == 1, f"{n3} degisiklik")
    print(f"        degisiklik senkronu: {third_t:.1f} saniye, {n3} dosya")

    print("\n[A siler, B'de de gitmeli]")
    requests.delete(f"{BASE}/api/sync/{SLUG}/v002_yeni_manual_roz", headers=hdr, timeout=30)
    api_client.pull_all_from_rtdb()
    got = {v["filename"] for v in version_store.list_versions(SLUG)}
    check("silinen versiyon B'den de gitti", "v002_yeni_manual.roz" not in got, str(got))
    check("digeri duruyor", "v001_hash_manual.roz" in got, str(got))

    print("\n[temizlik]")
    requests.delete(f"{BASE}/api/institutions/{SLUG}", headers=hdr, timeout=30)
    remaining = requests.get(f"{BASE}/api/sync/index", headers=hdr, timeout=30).json()
    check("test kurumu sunucudan silindi", SLUG not in remaining, str(sorted(remaining)))
    print(f"        kalan gercek kurumlar: {sorted(remaining)}")
    shutil.rmtree(sandbox, ignore_errors=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        FAILED.append(("beklenmeyen hata", "traceback"))
    finally:
        print("\n" + "=" * 60)
        print(f"gecen: {len(PASSED)}   kalan: {len(FAILED)}")
        for f in FAILED:
            print(f"  - {f}")
        print("=" * 60)
    sys.exit(1 if FAILED else 0)
