import os
import json
import time
import requests
from collections import deque
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

# Firebase Web Config (User Provided)
FIREBASE_PROJECT_ID = "bogazicidersyonetim"
FIREBASE_API_KEY = "AIzaSyCyJzdfiv6ezzpfrsuwsuY84Ri2KTMO4bU"

# Realtime Database URL
RTDB_URL = "https://bogazicidersyonetim-default-rtdb.firebaseio.com"

class CloudSyncWorker(QThread):
    """
    Arka planda çalışan Local-First Firebase Sync Motoru (Offline Queue destekli)
    Firestore yerine Realtime Database (RTDB) kullanır (Maliyet 0'a yakın).
    """
    sync_status_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True
        self._queue = deque()
        self._mutex = QMutex()
        self._auth_data = None
        
    def set_auth(self, auth_data):
        self._auth_data = auth_data
        if auth_data:
            self._id_token = auth_data.get("idToken")
            self._token_expires_at = time.time() + int(auth_data.get("expiresIn", 3600)) - 300
        
    def add_to_queue(self, collection: str, document_id: str, data: dict):
        """Yerel SQLite'da yapılan değişiklikleri bulut kuyruğına ekler"""
        with QMutexLocker(self._mutex):
            self._queue.append({
                "collection": collection,
                "document_id": document_id,
                "data": data,
                "timestamp": time.time()
            })
            
    def authenticate(self):
        if not self._auth_data: return False
        
        email = self._auth_data.get("email")
        password = self._auth_data.get("password")
        api_key = FIREBASE_API_KEY
        
        sign_in_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        
        try:
            resp = requests.post(sign_in_url, json=payload, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                self._id_token = data.get("idToken")
                self._token_expires_at = time.time() + int(data.get("expiresIn", 3600)) - 300
                return True
            else:
                err_data = resp.json()
                if "EMAIL_NOT_FOUND" in str(err_data):
                    sign_up_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}"
                    sup_resp = requests.post(sign_up_url, json=payload, timeout=5)
                    if sup_resp.status_code == 200:
                        sdata = sup_resp.json()
                        self._id_token = sdata.get("idToken")
                        self._token_expires_at = time.time() + int(sdata.get("expiresIn", 3600)) - 300
                        return True
        except Exception:
            pass
        return False
            
    def run(self):
        while self._is_running:
            # Token yenileme kontrolü
            if not getattr(self, "_id_token", None) or time.time() > getattr(self, "_token_expires_at", 0):
                self.sync_status_changed.emit("Bulut: Güvenli Giriş (Auth)...")
                if not self.authenticate():
                    self.sync_status_changed.emit("Bulut: Auth Hatası")
                    time.sleep(5)
                    continue
                    
            item_to_sync = None
            
            with QMutexLocker(self._mutex):
                if len(self._queue) > 0:
                    item_to_sync = self._queue[0]
                    
            if item_to_sync:
                col = item_to_sync["collection"]
                doc_id = item_to_sync["document_id"]
                data = item_to_sync["data"]
                
                # Token ekleyerek RTDB'ye gönder (Temiz JSON formatına dönüştür)
                url = f"{RTDB_URL}/{col}/{doc_id}.json?auth={self._id_token}"
                
                try:
                    self.sync_status_changed.emit("Bulut: Senkronize ediliyor...")
                    
                    def sanitize_keys(obj):
                        import re
                        if isinstance(obj, dict):
                            new_obj = {}
                            for k, v in obj.items():
                                k_str = str(k)
                                safe_k = re.sub(r'[\.\#\$\[\]\/]', '_', k_str)
                                if safe_k == "": safe_k = "empty_key"
                                new_obj[safe_k] = sanitize_keys(v)
                            return new_obj
                        elif isinstance(obj, list):
                            return [sanitize_keys(i) for i in obj]
                        else:
                            return obj
                            
                    sanitized = sanitize_keys(data)
                    clean_data = json.loads(json.dumps(sanitized, default=str))
                    
                    response = requests.put(url, json=clean_data, timeout=5)
                    
                    if response.status_code in [200, 201]:
                        with QMutexLocker(self._mutex):
                            self._queue.popleft() # Başarılı, kuyruktan sil
                        self.sync_status_changed.emit("Bulut: Senkronize (Tüm veriler güvende)")
                    elif response.status_code in [401, 403]:
                        print(f"Firebase Auth Permission Error: {response.status_code} - {response.text}")
                        # Token yenilemeyi dene
                        self.authenticate()
                        self.sync_status_changed.emit("Bulut: Yetki Hatası (Rules Ayarını İnceleyin)")
                        time.sleep(5)
                    else:
                        print(f"Firebase RTDB Error: {response.status_code} - {response.text}")
                        self.sync_status_changed.emit(f"Bulut: Hata ({response.status_code}) - Tekrar Deneniyor")
                        time.sleep(5)
                        
                except (requests.ConnectionError, requests.Timeout):
                    self.sync_status_changed.emit("Bulut: Çevrimdışı (Veriler kuyrukta bekliyor)")
                    time.sleep(5)
            else:
                # Check connection status if queue is empty
                if getattr(self, "_last_ping", 0) + 10 < time.time():
                    try:
                        resp = requests.get(f"{RTDB_URL}/ping.json?auth={self._id_token}", timeout=3)
                        if resp.status_code == 200:
                            self.sync_status_changed.emit("Bulut: Bağlı (Güvenli)")
                        elif resp.status_code in [401, 403]:
                            self.sync_status_changed.emit("Bulut: Yetki Yok (Kuralları İnceleyin)")
                        else:
                            self.sync_status_changed.emit(f"Bulut: Bekliyor ({resp.status_code})")
                    except Exception:
                        self.sync_status_changed.emit("Bulut: Çevrimdışı")
                    self._last_ping = time.time()
                time.sleep(1)

    def stop(self):
        self._is_running = False
        self.wait()
