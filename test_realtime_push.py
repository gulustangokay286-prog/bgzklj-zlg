"""
test_realtime_push.py — WebSocket anlik bildirim testi (canli sunucu).

    python test_realtime_push.py

Bir cihaz degisiklik yazdiginda, digerinin WebSocket uzerinden kac milisaniyede
haberdar oldugunu olcer. Gecici bir kurum kullanir ve sonunda temizler.
"""
import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests  # noqa: E402

BASE = os.environ.get("CHENKI_API_URL", "http://213.142.159.36")
WS_BASE = BASE.replace("https://", "wss://").replace("http://", "ws://")
SLUG = "__realtime_testi__"

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def main():
    try:
        import websockets  # noqa: F401
        from websockets.sync.client import connect
    except ImportError:
        print("  ATLANDI: 'websockets' paketi kurulu degil (pip install websockets)")
        print("  Not: uygulama QtWebSockets kullaniyor, bu test sadece sunucuyu dogruluyor.")
        return

    tok = requests.post(f"{BASE}/auth/login",
                        data={"username": "sehersanli@chenki.net", "password": "seher2311"},
                        timeout=20).json()["access_token"]
    hdr = {"Authorization": f"Bearer {tok}"}

    print("\n[baglanti]")
    received = []
    connected = threading.Event()
    stop = threading.Event()

    def listener():
        try:
            with connect(f"{WS_BASE}/ws/{SLUG}?token={tok}", open_timeout=15) as ws:
                connected.set()
                while not stop.is_set():
                    try:
                        raw = ws.recv(timeout=1)
                    except TimeoutError:
                        continue
                    except Exception:
                        break
                    received.append((time.time(), raw))
        except Exception as exc:
            print(f"        listener hatasi: {exc}")
            connected.set()

    t = threading.Thread(target=listener, daemon=True)
    t.start()
    check("websocket baglandi", connected.wait(timeout=20))
    time.sleep(1.0)  # sunucunun aboneligi kaydetmesi icin

    print("\n[A yazar -> B ne kadar sonra haber alir]")
    body = {
        "dersler": [{"ad": "Test"}],
        "grid_placements": [{"day": 0, "period": 0, "subject_name": "Anlik"}],
        "_version_meta": {"filename": "v001_rt_manual.roz"},
    }
    sent_at = time.time()
    requests.put(f"{BASE}/api/sync/{SLUG}/v001_rt_manual_roz", json=body, headers=hdr, timeout=30)

    deadline = time.time() + 10
    while time.time() < deadline and not received:
        time.sleep(0.02)

    check("bildirim geldi", bool(received), "10 saniyede hicbir sey gelmedi")
    if received:
        arrived_at, raw = received[0]
        latency_ms = (arrived_at - sent_at) * 1000
        print(f"        gecikme: {latency_ms:.0f} ms")
        print(f"        mesaj  : {raw}")
        check("gecikme 2 saniyenin altinda", latency_ms < 2000, f"{latency_ms:.0f} ms")
        try:
            msg = json.loads(raw)
            check("mesaj 'sync' tipinde", msg.get("type") == "sync", str(msg))
            check("mesaj dogru kurumu isaret ediyor", msg.get("slug") == SLUG, str(msg))
        except Exception as exc:
            check("mesaj JSON olarak cozuldu", False, str(exc))

    print("\n[silme de bildiriliyor]")
    received.clear()
    sent_at = time.time()
    requests.delete(f"{BASE}/api/sync/{SLUG}/v001_rt_manual_roz", headers=hdr, timeout=30)
    deadline = time.time() + 10
    while time.time() < deadline and not received:
        time.sleep(0.02)
    check("silme bildirimi geldi", bool(received))
    if received:
        print(f"        gecikme: {(received[0][0] - sent_at) * 1000:.0f} ms")

    stop.set()

    print("\n[temizlik]")
    requests.delete(f"{BASE}/api/institutions/{SLUG}", headers=hdr, timeout=30)
    idx = requests.get(f"{BASE}/api/sync/index", headers=hdr, timeout=30).json()
    check("test kurumu silindi", SLUG not in idx, str(sorted(idx)))
    print(f"        kalan gercek kurumlar: {sorted(idx)}")


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
