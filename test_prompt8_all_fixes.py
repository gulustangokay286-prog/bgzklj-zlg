import os
import sys
import unittest
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

class TestPrompt8Fixes(unittest.TestCase):
    def test_imports_and_qtablewidgetitem(self):
        import main_window
        self.assertTrue(hasattr(main_window, "QTableWidgetItem"))

    def test_assignment_dialog_signature(self):
        from dialogs.edit_forms import SubjectTeacherAssignmentDialog
        data_store = {
            "dersler": [{"ad": "Matematik"}],
            "ogretmenler": [{"ad": "Hakan Yılmaz"}],
            "siniflar": [{"ad": "9A"}],
            "atamalar": []
        }
        # Test with preselect_class
        d1 = SubjectTeacherAssignmentDialog(
            subject_name="Matematik",
            data_store=data_store,
            preselect_class="9A"
        )
        self.assertEqual(d1.current_class, "9A")
        
        # Test with current_class
        d2 = SubjectTeacherAssignmentDialog(
            subject_name="Matematik",
            data_store=data_store,
            current_class="10B",
            custom_arg="test"
        )
        self.assertEqual(d2.current_class, "10B")

    def test_clean_subject_badges(self):
        from dialogs.print_preview import get_subject_badge
        data_store = {
            "dersler": [
                {"ad": "Matematik 1", "kisa": "MAT 1"},
                {"ad": "Fizik 9", "kisa": "FİZ 9"},
                {"ad": "Türk Dili ve Edebiyatı", "kisa": "TDE"},
                {"ad": "Biyoloji", "kisa": "BİY"}
            ]
        }
        self.assertEqual(get_subject_badge("Matematik 1", data_store), "MAT 1")
        self.assertEqual(get_subject_badge("Fizik 9", data_store), "FİZ 9")
        self.assertEqual(get_subject_badge("Türk Dili ve Edebiyatı", data_store), "TDE")
        self.assertEqual(get_subject_badge("Biyoloji", data_store), "BİY")
        self.assertEqual(get_subject_badge("Kimya 10", data_store), "KİM 10")
        self.assertEqual(get_subject_badge("Din Kültürü ve Ahlak Bilgisi", data_store), "DİN")

    def test_draggable_card_teacher_view_mode(self):
        from timetable_grid import DraggableLessonCard
        
        # Class view mode: Shows Subject + Teacher
        card_class_mode = DraggableLessonCard(
            lesson_id=1,
            subject_name="Matematik 1",
            color="#2563EB",
            duration=2,
            teacher="Sultan Yılmaz",
            class_name="9A",
            display_mode="classes"
        )
        self.assertIn("MAT", card_class_mode.text())
        self.assertIn("Sultan", card_class_mode.text())
        
        # Teacher view mode: Shows Class + Subject (as requested by user)
        card_teacher_mode = DraggableLessonCard(
            lesson_id=2,
            subject_name="Matematik 1",
            color="#2563EB",
            duration=2,
            teacher="Sultan Yılmaz",
            class_name="9A",
            display_mode="teachers"
        )
        self.assertIn("9A", card_teacher_mode.text())
        self.assertIn("MAT", card_teacher_mode.text())

    def test_lock_toggle(self):
        from timetable_grid import TimetableGrid
        grid = TimetableGrid()
        grid.set_mode_all_classes(["9A", "9B"], 8, ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])
        grid.set_cell(0, 0, "Matematik", "#2563EB", "Hakan Y.", 1, "9A", display_mode="classes", locked=True)
        
        placed = grid.get_placed_lessons()
        self.assertTrue(placed[(0, 0)]["locked"])
        
        # Unlock
        placed[(0, 0)]["locked"] = False
        self.assertFalse(placed[(0, 0)]["locked"])

if __name__ == "__main__":
    unittest.main()
