import requests
import json
import os

BASE_URL = "http://213.142.159.36"

def _get_token_file_path():
    base_dir = os.path.join(os.path.expanduser("~"), ".chenki_akademi")
    try:
        os.makedirs(base_dir, exist_ok=True)
    except Exception:
        pass
    return os.path.join(base_dir, "bgz_auth_token.json")

class APIClient:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = self.load_token()

    def load_token(self):
        token_path = _get_token_file_path()
        if os.path.exists(token_path):
            try:
                with open(token_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("access_token")
            except Exception:
                pass
        return None

    def save_token(self, token_data):
        self.token = token_data.get("access_token") if isinstance(token_data, dict) else None
        try:
            token_path = _get_token_file_path()
            with open(token_path, "w", encoding="utf-8") as f:
                json.dump(token_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[APIClient] save_token warning: {e}")

    def delete_token(self):
        self.token = None
        try:
            token_path = _get_token_file_path()
            if os.path.exists(token_path):
                os.remove(token_path)
        except Exception:
            pass

    def login(self, email, password):
        url = f"{self.base_url}/auth/login"
        data = {"username": email, "password": password}
        # OAuth2PasswordRequestForm expects form-data
        resp = requests.post(url, data=data, timeout=10)
        
        if resp.status_code == 200:
            token_data = resp.json()
            self.save_token(token_data)
            return True, token_data
        else:
            try:
                err = resp.json().get("detail", "Login failed")
            except:
                err = "Server connection failed"
            return False, err

    def get_headers(self):
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def pull_all_from_rtdb(self, auth_data=None):
        """Replacement for Firebase pull_all_from_rtdb"""
        url = f"{self.base_url}/api/institutions"
        resp = requests.get(url, headers=self.get_headers(), timeout=15)
        if resp.status_code != 200:
            return False, f"Buluttan veri çekilemedi (HTTP {resp.status_code})", 0
            
        data = resp.json()
        if not data or not isinstance(data, dict):
            return True, "Bulutta kayıtlı kurum bulunamadı.", 0
            
        import version_store
        base_dir = version_store._ensure_base()
        synced_count = 0
        
        for slug, inst_obj in data.items():
            if not isinstance(inst_obj, dict):
                continue
                
            inst_dir = os.path.join(base_dir, slug)
            ver_dir = os.path.join(inst_dir, "versions")
            os.makedirs(ver_dir, exist_ok=True)
            
            meta_data = inst_obj.get("meta", {})
            if meta_data:
                with open(os.path.join(inst_dir, "meta.json"), "w", encoding="utf-8") as f:
                    json.dump(meta_data, f, ensure_ascii=False, indent=2)
                    
            cloud_versions = meta_data.get("versions", {}) or inst_obj.get("versions", {})
            for v_key, roz_content in cloud_versions.items():
                if not isinstance(roz_content, dict):
                    continue
                orig_fn = roz_content.get("_version_meta", {}).get("filename", "")
                if not orig_fn:
                    orig_fn = f"{v_key.replace('_roz', '.roz')}"
                if not orig_fn.endswith(".roz"):
                    orig_fn += ".roz"
                    
                target_file = os.path.join(ver_dir, orig_fn)
                with open(target_file, "w", encoding="utf-8") as f:
                    json.dump(roz_content, f, ensure_ascii=False, indent=2)
                synced_count += 1
                
        return True, f"VDS Senkronizasyonu tamamlandı ({len(data)} kurum, {synced_count} versiyon).", synced_count

    def push_version_to_rtdb(self, slug, filename, roz_data, auth_data=None):
        """Replacement for Firebase push_version_to_rtdb"""
        import re
        v_key = re.sub(r'[\.\$#\[\]/]', '_', filename)
        url = f"{self.base_url}/api/sync/{slug}/{v_key}"
        resp = requests.put(url, json=roz_data, headers=self.get_headers(), timeout=15)
        if resp.status_code in (200, 201):
            return True
        return False

# Singleton instance
api_client = APIClient()
