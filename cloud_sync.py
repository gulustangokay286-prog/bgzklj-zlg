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
        self.auth_data = None
        
    def set_auth(self, auth_data):
        self.auth_data = auth_data
        
    def add_to_queue(self, collection: str, document_id: str, data: dict):
        """Yerel SQLite'da yapılan değişiklikleri bulut kuyruğına ekler"""
        with QMutexLocker(self._mutex):
            self._queue.append({
                "collection": collection,
                "document_id": document_id,
                "data": data,
                "timestamp": time.time()
            })
            
    def run(self):
        while self._is_running:
            item_to_sync = None
            
            with QMutexLocker(self._mutex):
                if len(self._queue) > 0:
                    item_to_sync = self._queue[0]
                    
            if item_to_sync:
                col = item_to_sync["collection"]
                doc_id = item_to_sync["document_id"]
                data = item_to_sync["data"]
                
                url = f"{RTDB_URL}/{col}/{doc_id}.json"
                params = {}
                if self.auth_data and "idToken" in self.auth_data:
                    params["auth"] = self.auth_data["idToken"]
                
                try:
                    self.sync_status_changed.emit("Bulut: Senkronize ediliyor...")
                    # RTDB directly accepts raw JSON
                    response = requests.put(url, json=data, params=params, timeout=5)
                    
                    if response.status_code in [200, 201]:
                        with QMutexLocker(self._mutex):
                            self._queue.popleft() # Başarılı, kuyruktan sil
                        self.sync_status_changed.emit("Bulut: Senkronize (Tüm veriler güvende)")
                    else:
                        print(f"Firebase RTDB Error: {response.status_code} - {response.text}")
                        self.sync_status_changed.emit("Bulut: Hata (Tekrar denenecek)")
                        time.sleep(5)
                        
                except (requests.ConnectionError, requests.Timeout):
                    self.sync_status_changed.emit("Bulut: Çevrimdışı (Veriler kuyrukta bekliyor)")
                    time.sleep(5)
            else:
                # Check connection status if queue is empty
                if getattr(self, "_last_ping", 0) + 10 < time.time():
                    try:
                        resp = requests.get(f"{RTDB_URL}/ping.json", timeout=3)
                        if resp.status_code == 200:
                            self.sync_status_changed.emit("Bulut: Bağlı (Eşitlendi)")
                        else:
                            self.sync_status_changed.emit("Bulut: Bekliyor")
                    except Exception:
                        self.sync_status_changed.emit("Bulut: Çevrimdışı")
                    self._last_ping = time.time()
                time.sleep(1)

    def stop(self):
        self._is_running = False
        self.wait()
