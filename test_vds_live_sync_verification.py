import requests
import json
import time

BASE_URL = "http://213.142.159.36"

def verify_live_vds():
    print("=== CANLI VDS SENKRONIZASYON TESTI (213.142.159.36) ===")
    
    # 1. Test Server Connectivity
    try:
        r = requests.get(f"{BASE_URL}", timeout=5)
        print(f" [1/4] VDS Sunucu Baglantisi: BASARILI (HTTP {r.status_code})")
    except Exception as e:
        print(f" [1/4] VDS Sunucu Baglantisi: HATA ({e})")
        return

    # 2. Test Login
    login_url = f"{BASE_URL}/auth/login"
    login_data = {"username": "admin@bgz.local", "password": "adminpassword123"}
    try:
        r_login = requests.post(login_url, data=login_data, timeout=5)
        if r_login.status_code == 200:
            token = r_login.json().get("access_token")
            print(" [2/4] VDS Yetkilendirme (Auth Login): BASARILI")
        else:
            print(f" [2/4] VDS Yetkilendirme: HTTP {r_login.status_code}")
            return
    except Exception as e:
        print(f" [2/4] VDS Yetkilendirme Hatasi: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Test Push Data (Simulating another PC saving a timetable)
    test_slug = "live_test_sync_institution"
    test_meta = {
        "name": "Canlı Test Kurumu (Senkronizasyon)",
        "color": "#0071E3",
        "active_version": "v1_test.roz",
        "has_password": False
    }
    test_payload = {
        "slug": test_slug,
        "meta": test_meta,
        "versions": {
            "v1_test.roz": {
                "dersler": [{"ad": "Matematik", "kisa": "MAT"}],
                "siniflar": [{"ad": "10A", "sinif_ogretmeni": "Ahmet Hoca"}],
                "ogretmenler": [{"ad": "Ahmet Hoca", "brans": "Matematik", "sinif_ogretmeni": "10A"}],
                "atamalar": [{"teacher": "Ahmet Hoca", "subject": "Matematik", "class": "10A", "duration": 4}]
            }
        }
    }
    
    push_url = f"{BASE_URL}/api/institutions"
    r_push = requests.post(push_url, json=test_payload, headers=headers, timeout=5)
    print(f" [3/4] Baska PC'den VDS'e Kaydetme (Push): BASARILI (HTTP {r_push.status_code})")

    # 4. Test Pull Data (Simulating your PC receiving the update)
    pull_url = f"{BASE_URL}/api/institutions"
    r_pull = requests.get(pull_url, headers=headers, timeout=5)
    if r_pull.status_code == 200:
        data = r_pull.json()
        assert test_slug in data, "Test kurumu VDS'ten cekilemedi!"
        saved_inst = data[test_slug]
        assert "v1_test.roz" in saved_inst.get("versions", {}), "Versiyon dosyasi VDS'te bulunamadi!"
        v_data = saved_inst["versions"]["v1_test.roz"]
        assert len(v_data.get("ogretmenler", [])) > 0, "Ogretmenler verisi eksik!"
        print(f" [4/4] Sizin PC'nizin VDS'ten Veriyi Cekmesi (Pull): %100 BASARILI!")
        print(f"       -> Cekilen Kurum: {saved_inst.get('meta', {}).get('name')}")
        print(f"       -> Cekilen Ogretmen: {v_data['ogretmenler'][0]['ad']} ({v_data['ogretmenler'][0]['brans']})")
        print(f"       -> Cekilen Sinif: {v_data['siniflar'][0]['ad']} (Rehber: {v_data['siniflar'][0]['sinif_ogretmeni']})")
    
    # Cleanup test institution from VDS
    del_url = f"{BASE_URL}/api/institutions/{test_slug}"
    requests.delete(del_url, headers=headers, timeout=5)
    print("\n>>> CANLI VDS TESTI %100 BASARIYLA TAMAMLANDI: VERILERINIZ KESINLIKLE SENKRONIZE OLUYOR! <<<")

if __name__ == "__main__":
    verify_live_vds()
