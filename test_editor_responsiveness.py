"""UI regression checks with isolated storage and no network access."""
import copy
import json
import os
import tempfile
import unittest
from unittest.mock import patch

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
import requests
import version_store
from timetable_grid import TimetableGrid, StickyGhostWidget
from dialogs.auto_schedule_dialog import AutoScheduleDialog
from dialogs.master_data_dialog import MasterDataDialog

APP = QApplication.instance() or QApplication([])


def store():
    return {'settings': {'days': ['Pazartesi', 'Salı'], 'periods': 4},
            'dersler': [{'ad': 'Matematik'}], 'siniflar': [{'ad': '9A'}, {'ad': '9B'}],
            'ogretmenler': [{'ad': 'Ayşe Yılmaz'}], 'derslikler': [{'ad': 'Oda'}],
            'atamalar': [], 'grid_placements': []}


class EditorResponsivenessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = patch.object(version_store, '_base_dir', lambda: self.temp.name)
        self.base.start(); self.addCleanup(self.base.stop)
        network = patch.object(requests.Session, 'request', side_effect=AssertionError('Network is forbidden'))
        network.start(); self.addCleanup(network.stop)

    def grid(self):
        g = TimetableGrid()
        g.data_store = store()
        g.set_mode_all_classes(['9A', '9B'], 4, ['Pazartesi', 'Salı'])
        g.resize(900, 500); g.show(); APP.processEvents()
        self.addCleanup(g.deleteLater)
        return g

    def test_refresh_reuses_unchanged_items_and_removes_missing_lessons(self):
        g = self.grid()
        g.set_cell(0, 0, 'Matematik', '#123456', duration=2, class_name='9A')
        first = g.table.item(0, 0)
        g.set_cell(1, 2, 'Fizik', '#234567', class_name='9B')
        g.begin_cell_refresh(); g.clear_grid()
        g.set_cell(0, 0, 'Matematik', '#123456', duration=2, class_name='9A')
        g.end_cell_refresh()
        self.assertIs(g.table.item(0, 0), first)
        self.assertIsNone(g.table.item(1, 2))
        self.assertEqual(g.table.columnSpan(0, 0), 2)
        self.assertEqual(len(g._placed_lessons), 2)
        g.begin_cell_refresh(); g.clear_grid(); g.end_cell_refresh()
        self.assertFalse(g._placed_lessons)
        self.assertIsNone(g.table.item(0, 0))
        self.assertEqual(g.table.columnSpan(0, 0), 1)

    def test_span_split_replaces_old_span_and_preserves_exact_cells(self):
        g = self.grid()
        g.set_cell(0, 0, 'Matematik', '#123456', duration=2)
        g.begin_cell_refresh(); g.clear_grid()
        g.set_cell(0, 0, 'Matematik', '#123456')
        g.set_cell(0, 1, 'Fizik', '#234567')
        g.end_cell_refresh()
        self.assertEqual(g.table.columnSpan(0, 0), 1)
        self.assertEqual(g._placed_lessons[(0, 1)]['subject_name'], 'Fizik')
        self.assertTrue(g.table.item(0, 1).text())

    def test_hit_testing_uses_cursor_inside_every_part_of_merged_block(self):
        g = self.grid()
        g.set_cell(0, 0, 'Matematik', '#123456', duration=2)
        for column in (0, 1, 2):
            pt = QPoint(g.table.columnViewportPosition(column) + 2, g.table.rowViewportPosition(0) + 2)
            self.assertEqual(g.table._cell_at(pt), (0, column))

    def test_sticky_drag_updates_first_move_and_finishes_preview_when_cursor_stops(self):
        g = self.grid()
        pix = QPixmap(100, 30); pix.fill(Qt.blue)
        lesson = {'subject_name': 'Matematik', 'class_name': '9A', 'duration': 1}
        pt = g.table.viewport().mapToGlobal(QPoint(g.table.columnViewportPosition(1) + 5, 5))
        with patch.object(QCursor, 'pos', return_value=pt), patch.object(QApplication, 'widgetAt', return_value=g.table.viewport()):
            ghost = StickyGhostWidget(pix, lesson, g, grab_offset=QPoint(45, 15))
            self.assertEqual(ghost._anchor_global(pt), pt)
            ghost._update_pos()
            self.assertEqual(g.table._drag_preview_info['col'], 1)
            ghost.cancel()

    def test_management_dialog_only_populates_selected_tab_then_refreshes_other_tabs_lazily(self):
        d = MasterDataDialog(3, data_store=store())
        self.addCleanup(d.deleteLater)
        self.assertEqual(d.table_ogretmen.rowCount(), 1)
        self.assertEqual(d.table_sinif.rowCount(), 0)
        d._select_tab(1)
        self.assertEqual(d.table_sinif.rowCount(), 2)
        d.data_store['ogretmenler'].append({'ad': 'Ali Yılmaz'})
        d._load_existing_data()
        d._select_tab(3)
        self.assertEqual(d.table_ogretmen.rowCount(), 2)

    def test_required_scheduler_options_stay_on_after_click(self):
        d = AutoScheduleDialog(store())
        self.addCleanup(d.deleteLater)
        for switch in (d.sw_ignore_cross, d.sw_optimal, d.sw_split):
            self.assertTrue(switch.isChecked())
            self.assertFalse(switch.isEnabled())
            QTest.mouseClick(switch, Qt.LeftButton)
            self.assertTrue(switch.isChecked())


if __name__ == '__main__':
    unittest.main()
