import requests
import json
import os
import shutil
import re

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

    def login(self, email="admin@bgz.local", password="admin"):
        url = f"{self.base_url}/auth/login"
        data = {"username": email, "password": password}
        try:
            resp = requests.post(url, data=data, timeout=8)
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
        except Exception as e:
            return False, f"Sunucu bağlantı hatası: {e}"

    def ensure_authenticated(self):
        if not self.token:
            self.token = self.load_token()
        if not self.token:
            ok, _ = self.login("admin@bgz.local", "admin")
            if not ok:
                # Retry once
                self.login("admin@bgz.local", "admin")
        return bool(self.token)

    def get_headers(self):
        self.ensure_authenticated()
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def _request_with_retry(self, method, url, **kwargs):
        headers = kwargs.pop("headers", None) or self.get_headers()
        timeout = kwargs.pop("timeout", 8)
        try:
            resp = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
            if resp.status_code == 401:
                # Token expired or invalid, re-login and retry
                self.login("admin@bgz.local", "admin")
                headers = self.get_headers()
                resp = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
            return resp
        except Exception as e:
            return None

    def pull_all_from_rtdb(self, auth_data=None):
        """Pulls all institutions from VDS backend, synchronizes newer versions, and auto-purges deleted institutions locally."""
        url = f"{self.base_url}/api/institutions"
        resp = self._request_with_retry("GET", url)
        if resp is None or resp.status_code != 200:
            status_code = resp.status_code if resp else "timeout"
            return False, f"Buluttan veri çekilemedi (HTTP {status_code})", 0
            
        try:
            data = resp.json()
        except Exception as e:
            return False, f"Sunucu yanıtı okunamadı ({e})", 0
            
        if not isinstance(data, dict):
            return True, "Bulutta kayıtlı kurum bulunamadı.", 0
            
        import version_store
        base_dir = version_store._ensure_base()
        synced_count = 0
        valid_cloud_slugs = set(data.keys())
        
        # 1. Clean up locally deleted institutions that no longer exist on VDS
        try:
            for item in os.listdir(base_dir):
                item_path = os.path.join(base_dir, item)
                if os.path.isdir(item_path) and item not in valid_cloud_slugs and item not in ("backups", "temp", "cache"):
                    try:
                        shutil.rmtree(item_path)
                        print(f"[APIClient] Purged deleted institution locally: {item}")
                    except Exception as pe:
                        print(f"[APIClient] Notice purging {item}: {pe}")
        except Exception as e:
            print(f"[APIClient] Cleanup scan notice: {e}")
        
        # 2. Sync all active cloud institutions and versions
        for slug, inst_obj in data.items():
            if not isinstance(inst_obj, dict):
                continue
                
            inst_dir = os.path.join(base_dir, slug)
            ver_dir = os.path.join(inst_dir, "versions")
            os.makedirs(ver_dir, exist_ok=True)
            
            meta_data = inst_obj.get("meta", {})
            if meta_data:
                try:
                    with open(os.path.join(inst_dir, "meta.json"), "w", encoding="utf-8") as f:
                        json.dump(meta_data, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                    
            cloud_versions = meta_data.get("versions", {}) or inst_obj.get("versions", {})
            valid_cloud_filenames = set()
            
            for v_key, roz_content in cloud_versions.items():
                if not isinstance(roz_content, dict):
                    continue
                orig_fn = roz_content.get("_version_meta", {}).get("filename", "")
                if not orig_fn:
                    orig_fn = f"{v_key.replace('_roz', '.roz')}"
                if not orig_fn.endswith(".roz"):
                    orig_fn += ".roz"
                    
                valid_cloud_filenames.add(orig_fn)
                target_file = os.path.join(ver_dir, orig_fn)
                
                # Check if we should update or write local file
                write_file = False
                if not os.path.exists(target_file):
                    write_file = True
                else:
                    try:
                        with open(target_file, "r", encoding="utf-8") as existing_f:
                            local_content = json.load(existing_f)
                        # Check last modified or structural inequality
                        remote_meta = roz_content.get("_version_meta", {})
                        local_meta = local_content.get("_version_meta", {})
                        if remote_meta.get("last_modified") != local_meta.get("last_modified") or len(roz_content.get("grid_placements", [])) != len(local_content.get("grid_placements", [])):
                            write_file = True
                    except Exception:
                        write_file = True
                        
                if write_file:
                    try:
                        with open(target_file, "w", encoding="utf-8") as f:
                            json.dump(roz_content, f, ensure_ascii=False, indent=2)
                        synced_count += 1
                    except Exception:
                        pass
                        
            # Clean up local versions that were deleted in cloud
            try:
                for local_fn in os.listdir(ver_dir):
                    if local_fn.endswith(".roz") and local_fn not in valid_cloud_filenames and len(valid_cloud_filenames) > 0:
                        try:
                            os.remove(os.path.join(ver_dir, local_fn))
                            print(f"[APIClient] Removed obsolete local version: {local_fn}")
                        except Exception:
                            pass
            except Exception:
                pass
                
        return True, f"Merkezi veritabanı senkronizasyonu tamamlandı ({len(data)} kurum, {synced_count} güncellenen versiyon).", synced_count

    def push_version_to_rtdb(self, slug, filename, roz_data, auth_data=None):
        """Pushes version and syncs institution meta to VDS backend."""
        try:
            v_key = re.sub(r'[\.\$#\[\]/]', '_', filename)
            url = f"{self.base_url}/api/sync/{slug}/{v_key}"
            resp = self._request_with_retry("PUT", url, json=roz_data)
            if resp and resp.status_code in (200, 201):
                # Also push institution metadata to update last_modified
                try:
                    import version_store
                    meta = version_store.get_institution_meta(slug)
                    if meta:
                        inst_url = f"{self.base_url}/api/institutions"
                        self._request_with_retry("POST", inst_url, json={"slug": slug, "meta": meta, "versions": {v_key: roz_data}})
                except Exception:
                    pass
                return True
        except Exception as e:
            print(f"[APIClient] push_version_to_rtdb notice: {e}")
        return False

    def delete_institution_from_rtdb(self, slug: str, auth_data: dict = None) -> bool:
        url = f"{self.base_url}/api/institutions/{slug}"
        resp = self._request_with_retry("DELETE", url)
        return resp is not None and resp.status_code in (200, 204)

    def delete_version_from_rtdb(self, slug: str, filename: str, auth_data: dict = None) -> bool:
        v_key = re.sub(r'[\.\$#\[\]/]', '_', filename)
        url = f"{self.base_url}/api/sync/{slug}/{v_key}"
        resp = self._request_with_retry("DELETE", url)
        return resp is not None and resp.status_code in (200, 204)

# Singleton instance
api_client = APIClient()
