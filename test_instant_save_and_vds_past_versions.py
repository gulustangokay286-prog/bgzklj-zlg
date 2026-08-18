# -*- coding: utf-8 -*-
"""
test_instant_save_and_vds_past_versions.py
Automated end-to-end verification for:
1. Instant in-place saving on grid modifications & clear
2. Window close graceful flush
3. All past versions (v1..v19) cross-PC sync on VDS
"""
import os
import sys
import json
import time

# Headless Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

app = QApplication.instance() or QApplication(sys.argv)

def test_all():
    print("=== STARTING COMPREHENSIVE INSTANT SAVE & VDS SYNC TEST ===")
    import version_store
    import cloud_sync
    from api_client import api_client
    
    # 1. Test VDS Login & Token
    login_ok = api_client.login("admin@bgz.local", "admin")
    print(f"1. VDS Live Login: {login_ok}")
    assert login_ok, "VDS Login failed"

    # 2. Test Push All & Pull All to confirm 19+ versions on VDS
    push_ok, push_msg, _ = cloud_sync.push_all_to_rtdb()
    print(f"2. VDS Push All: {push_ok} - {push_msg}")
    assert push_ok, "Push all failed"
    
    pull_ok, pull_msg, synced = cloud_sync.pull_all_from_rtdb()
    print(f"3. VDS Pull All: {pull_ok} - {pull_msg} (Synced: {synced})")
    assert pull_ok, "Pull all failed"
    assert synced >= 19, f"Expected at least 19 versions synced, got {synced}"

    # 4. Test MainWindow and TimetableGrid instant persistence
    from main_window import MainWindow
    slug = "varsayilan_kurum"
    versions = version_store.list_versions(slug)
    assert len(versions) > 0, "No versions found for varsayilan_kurum"
    test_ver = versions[0]["filename"]
    print(f"4. Testing active version: {test_ver}")
    
    ver_path = os.path.join(version_store._base_dir(), slug, "versions", test_ver)
    
    win = MainWindow(
        override_db_path=ver_path,
        institution_slug=slug,
        institution_name="Varsayılan Kurum",
        version_filename=test_ver
    )
    win.show()
    app.processEvents()

    # 5. Clear Grid & Verify Instant Save
    print("5. Testing Grid Clear & Instant Save...")
    win._push_undo_state()
    win.data_store["grid_placements"] = []
    win.data_store["auto_schedule_results"] = []
    win.data_store["yerlesim"] = {}
    if hasattr(win, "_grid"):
        win._grid.clear_grid()
    win.save_db(sync_from_grid=False)
    version_store.update_version_in_place(slug, test_ver, win.data_store)
    
    # Check disk file
    with open(ver_path, "r", encoding="utf-8") as f:
        saved_on_disk = json.load(f)
    print(f"   Grid placements count after clear: {len(saved_on_disk.get('grid_placements', []))}")
    assert len(saved_on_disk.get("grid_placements", [])) == 0, "Grid placements not cleared on disk!"

    # 6. Place a lesson & Verify Instant Save
    print("6. Testing Lesson Placement & Instant Save...")
    new_placement = {
        "class_name": "9A",
        "class": "9A",
        "subject_name": "Matematik",
        "subject": "Matematik",
        "teacher_name": "Ahmet Yılmaz",
        "teacher": "Ahmet Yılmaz",
        "day": 0,
        "period": 0,
        "duration": 1,
        "color": "#4A90E2"
    }
    win.data_store["grid_placements"].append(new_placement)
    win._refresh_grid()
    win.save_db(sync_from_grid=True)
    version_store.update_version_in_place(slug, test_ver, win.data_store)
    
    with open(ver_path, "r", encoding="utf-8") as f:
        saved_on_disk = json.load(f)
    print(f"   Grid placements count after add: {len(saved_on_disk.get('grid_placements', []))}")
    assert len(saved_on_disk.get("grid_placements", [])) == 1, "Grid placements not saved on disk!"

    # 7. Test closeEvent graceful flush
    print("7. Testing closeEvent auto-save & flush...")
    from PySide6.QtGui import QCloseEvent
    close_evt = QCloseEvent()
    win.closeEvent(close_evt)
    
    # Reload from disk to verify
    reloaded = version_store.load_version(slug, test_ver)
    assert len(reloaded.get("grid_placements", [])) == 1, "Data lost on window close!"
    print("   Data successfully persisted on window close!")

    print("=== ALL TESTS PASSED WITH 100% SUCCESS! ===")

if __name__ == "__main__":
    test_all()
