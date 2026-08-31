import os
import sys
import shutil

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

import version_store
slug = 'test_inst_flow'
os.makedirs(os.path.join(version_store._base_dir(), slug, 'versions'), exist_ok=True)

# 1. Create two folders
f1, _ = version_store.create_folder(slug, 'Ağustos 2. Hafta')
f2, _ = version_store.create_folder(slug, 'Eylül 1. Hafta')

# 2. Save initial version in Folder 1
ds = {'okul_adi': 'Test Okulu', 'siniflar': [{'ad': '9A'}], 'ders_saati': 8, 'gun_sayisi': 5}
v1 = version_store.save_version(slug, ds, source='manual', note='Ilk kayit', folder_id=f1['id'], allow_duplicate=True)
print('Created v1:', v1, 'in folder:', f1['name'])

# Verify v1 folder
v1_fid = version_store.get_version_folder_id(slug, v1)
assert v1_fid == f1['id'], f"Expected {f1['id']}, got {v1_fid}"

# 3. Simulate COPY action to Folder 2
v2 = version_store.save_version(slug, ds, source='manual', note='Kopya kayit', folder_id=f2['id'], allow_duplicate=True)
print('Created v2 (Copy):', v2, 'in folder:', f2['name'])

# Check version bump and folders
assert v2 != v1, 'v2 should be a new version'
v2_fid = version_store.get_version_folder_id(slug, v2)
assert v2_fid == f2['id'], f"Expected {f2['id']}, got {v2_fid}"

# Check that v1 is STILL intact in Folder 1!
v1_fid_after = version_store.get_version_folder_id(slug, v1)
assert v1_fid_after == f1['id'], f"Original v1 should still be in Folder 1, got {v1_fid_after}"

# 4. Test UI Dialog rendering
from dialogs.save_location_dialog import FolderTransferChoiceDialog, SaveLocationDialog
td = FolderTransferChoiceDialog('Ağustos 2. Hafta', 'Eylül 1. Hafta')
td.show()
pm = td.grab()
pm.save('test_folder_transfer_dialog.png')
print('Saved test_folder_transfer_dialog.png')

# Cleanup test institution
shutil.rmtree(os.path.join(version_store._base_dir(), slug), ignore_errors=True)
print('ALL TESTS PASSED SUCCESSFULLY!')
