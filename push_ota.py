import requests
import json

API_KEY = "AIzaSyCyJzdfiv6ezzpfrsuwsuY84Ri2KTMO4bU"
RTDB_URL = "https://bogazicidersyonetim-default-rtdb.firebaseio.com"

def push_ota():
    auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    resp = requests.post(auth_url, json={"email": "demo@bgz.com", "password": "123456", "returnSecureToken": True})
    if resp.status_code != 200:
        print("Login failed:", resp.text)
        return
        
    auth_data = resp.json()
    token = auth_data["idToken"]
    
    update_data = {
        "version": "2.6 Pro (Kritik Düzeltmeler)",
        "notes": "1. Sınıflar ekranı (MasterDataDialog) yeniden tasarlandı ve artık sahte sütunlar yerine gerçek kayıtlı verileri gösteriyor.\n2. Çizelgeden silinen derslerin yan panele (Yerleştirilmeyenler listesine) düşmeme sorunu onarıldı.\n3. Firebase 400 'Bad Request' senkronizasyon problemi ('/' işareti kaynaklı) tamamen çözüldü.",
        "url": "https://github.com/gulustangokay286-prog/bgzklj-zlg/archive/refs/heads/main.zip"
    }
    
    url = f"{RTDB_URL}/updates.json?auth={token}"
    upload_resp = requests.put(url, json=update_data)
    print("OTA Update Push Status:", upload_resp.status_code)
    print("OTA Update Push Response:", upload_resp.text)

if __name__ == "__main__":
    push_ota()
