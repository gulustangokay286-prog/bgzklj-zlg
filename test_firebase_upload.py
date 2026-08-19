import requests
import json
import sqlite3
import re

API_KEY = "AIzaSyCyJzdfiv6ezzpfrsuwsuY84Ri2KTMO4bU"
RTDB_URL = "https://bogazicidersyonetim-default-rtdb.firebaseio.com"

def sanitize_keys(obj):
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            k_str = str(k)
            safe_k = re.sub(r'[\.\#\$\[\]]', '_', k_str)
            if safe_k == "": safe_k = "empty_key"
            new_obj[safe_k] = sanitize_keys(v)
        return new_obj
    elif isinstance(obj, list):
        return [sanitize_keys(i) for i in obj]
    else:
        return obj

def test_upload():
    auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    resp = requests.post(auth_url, json={"email": "demo@bgz.com", "password": "123456", "returnSecureToken": True})
    if resp.status_code != 200:
        print("Login failed:", resp.text)
        return
        
    auth_data = resp.json()
    token = auth_data["idToken"]
    uid = auth_data["localId"]
    
    import database
    database.init_db()
    data = {}
    data["siniflar"] = database.get_classes()
    data["ogretmenler"] = database.get_teachers()
    data["dersler"] = database.get_subjects()
    data["derslikler"] = database.get_rooms()
    data["atamalar"] = database.get_assignments()
    data["kisitlamalar"] = database.get_constraints()
    data["grid_placements"] = database.get_grid_placements()
            
    print("Data loaded. Keys:", data.keys())
    
    sanitized = sanitize_keys(data)
    clean_data = json.loads(json.dumps(sanitized, default=str))
    
    url = f"{RTDB_URL}/institutions/{uid}.json?auth={token}"
    print(f"Uploading to {url} ...")
    
    upload_resp = requests.put(url, json=clean_data)
    print("Upload Status:", upload_resp.status_code)
    print("Upload Response:", upload_resp.text)

if __name__ == "__main__":
    test_upload()
