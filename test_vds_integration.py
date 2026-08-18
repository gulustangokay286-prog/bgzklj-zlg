import sys
import os
import time

sys.path.append(r"c:\Users\gokay\Desktop\aSc\ChenKi_v2")

def test_vds_full_flow():
    from api_client import api_client
    print("--- 1. Testing Login ---")
    success, res = api_client.login("admin@bgz.local", "admin")
    if not success:
        print("LOGIN FAILED:", res)
        return False
    print("LOGIN SUCCESS. Token:", api_client.token[:15] + "...")
    
    print("\n--- 2. Testing Institution Push (meta) ---")
    # Simulate a fake institution meta
    fake_slug = "test_institution_99"
    fake_meta = {"name": "Test Kurum", "license": "aktif"}
    from cloud_sync import push_institution_to_rtdb
    
    # Normally cloud_sync gets auth_data internally via worker, but we can call it directly
    success = push_institution_to_rtdb(fake_slug, {"dummy_auth": True})
    # Wait, push_institution_to_rtdb tries to read from local file `version_store._ensure_base()/slug/meta.json`!
    # If the folder doesn't exist, it returns False.
    print(f"Push Institution returned: {success} (Expected False if local folder missing)")
    
    print("\n--- 3. Testing Pull All from RTDB ---")
    from cloud_sync import pull_all_from_rtdb
    success, msg, count = pull_all_from_rtdb({"dummy_auth": True})
    print(f"Pull All: Success={success}, Msg='{msg}', Count={count}")
    
    return True

if __name__ == "__main__":
    test_vds_full_flow()
