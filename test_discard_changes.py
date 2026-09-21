import os
import sys
import json
import copy
import shutil
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication
import version_store
from main_window import MainWindow

app = QApplication.instance() or QApplication(sys.argv)

class TestDiscardChanges(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orig_base = version_store._base_dir
        version_store._base_dir = lambda: self.temp_dir

        self.slug = f"test_okul_{self._testMethodName}"
        self.inst_dir = os.path.join(self.temp_dir, self.slug, "versions")
        os.makedirs(self.inst_dir, exist_ok=True)

        self.initial_data = {
            "dersler": [{"ad": "Matematik"}],
            "ogretmenler": [{"ad": "Ahmet Yilmaz"}],
            "siniflar": [{"ad": "9A"}],
            "atamalar": [{"subject": "Matematik", "teacher": "Ahmet Yilmaz", "class": "9A", "duration": 1}],
            "settings": {"periods": 8, "days_count": 5, "institution_slug": self.slug},
            "grid_placements": [
                {"subject_name": "Matematik", "teacher_name": "Ahmet Yilmaz", "class_name": "9A", "day": 0, "period": 1, "duration": 1, "locked": True}
            ]
        }
        self.ver_fn = version_store.save_version(self.slug, self.initial_data, source="manual", note="v1 test")
        self.file_path = os.path.join(self.inst_dir, self.ver_fn)

    def tearDown(self):
        version_store._base_dir = self.orig_base
        try:
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass

    def test_content_changed_detection(self):
        win = MainWindow(
            override_db_path=self.file_path,
            institution_slug=self.slug,
            version_filename=self.ver_fn
        )
        try:
            self.assertFalse(win._content_changed())

            # Modify data_store in memory
            win.data_store["dersler"].append({"ad": "Fizik"})
            self.assertTrue(win._content_changed())
        finally:
            win.cleanup()
            win.deleteLater()
            app.processEvents()

    def test_discard_after_save_db_overwrites_disk(self):
        win = MainWindow(
            override_db_path=self.file_path,
            institution_slug=self.slug,
            version_filename=self.ver_fn
        )
        try:
            self.assertFalse(win._content_changed())

            # Simulate a subdialog or auto-scheduler calling save_db() during editing session
            win.data_store["dersler"].append({"ad": "Kimya"})
            win.data_store["grid_placements"].append(
                {"subject_name": "Kimya", "teacher_name": "Ayse", "class_name": "9A", "day": 1, "period": 0, "duration": 1}
            )
            win.save_db()

            # Verify that save_db() did write Kimya to disk
            with open(self.file_path, "r", encoding="utf-8") as f:
                disk_content = json.load(f)
            subjs = [d["ad"] for d in disk_content.get("dersler", [])]
            self.assertIn("Kimya", subjs)

            # Now simulate user exiting and clicking "Kaydetmeden Çık" (discard)
            from dialogs.save_location_dialog import SaveLocationDialog
            orig_choose = SaveLocationDialog.choose
            try:
                SaveLocationDialog.choose = classmethod(lambda cls, *args, **kwargs: (None, "discard", "", "", False))
                res = win._save_new_version_with_folder_picker("", force=False, allow_discard=True)
                self.assertTrue(res)
                self.assertTrue(win._discard_changes)
            finally:
                SaveLocationDialog.choose = orig_choose

            # Verify that disk file has been RESTORED to initial state without Kimya!
            with open(self.file_path, "r", encoding="utf-8") as f:
                restored_disk = json.load(f)
            restored_subjs = [d["ad"] for d in restored_disk.get("dersler", [])]
            self.assertNotIn("Kimya", restored_subjs)
            self.assertEqual(len(restored_disk.get("grid_placements", [])), 1)
            self.assertEqual(restored_disk["grid_placements"][0]["subject_name"], "Matematik")

            # Verify in-memory data_store is also restored
            self.assertNotIn("Kimya", [d["ad"] for d in win.data_store.get("dersler", [])])
        finally:
            win.cleanup()
            win.deleteLater()
            app.processEvents()

    def test_discard_preserves_explicit_save_as_new_baseline(self):
        win = MainWindow(
            override_db_path=self.file_path,
            institution_slug=self.slug,
            version_filename=self.ver_fn
        )
        try:
            # Step 1: Add Tarih and explicitly save
            win.data_store["dersler"].append({"ad": "Tarih"})
            win._mark_saved()
            win.save_db()

            # Step 2: Add Cografya (not explicitly saved, but save_db called)
            win.data_store["dersler"].append({"ad": "Cografya"})
            win.save_db()

            # Step 3: Discard
            from dialogs.save_location_dialog import SaveLocationDialog
            orig_choose = SaveLocationDialog.choose
            try:
                SaveLocationDialog.choose = classmethod(lambda cls, *args, **kwargs: (None, "discard", "", "", False))
                win._save_new_version_with_folder_picker("", force=False, allow_discard=True)
            finally:
                SaveLocationDialog.choose = orig_choose

            # Disk should have Tarih (explicitly saved), but NOT Cografya (discarded)
            with open(self.file_path, "r", encoding="utf-8") as f:
                disk_content = json.load(f)
            subjs = [d["ad"] for d in disk_content.get("dersler", [])]
            self.assertIn("Tarih", subjs)
            self.assertNotIn("Cografya", subjs)
        finally:
            win.cleanup()
            win.deleteLater()
            app.processEvents()

if __name__ == "__main__":
    unittest.main()
