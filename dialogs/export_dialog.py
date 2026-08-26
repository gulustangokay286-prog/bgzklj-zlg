"""
export_dialog.py — "Aktar": choose what to export and to which format.

Backs the ribbon's Aktar button, which previously opened an empty message box.
Everything offered here is actually produced by exporters.py; nothing in this dialog
is decorative.
"""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QRadioButton, QVBoxLayout,
)

import exporters


class ExportDialog(QDialog):
    def __init__(self, data_store, parent=None):
        super().__init__(parent)
        self.data_store = data_store or {}
        self.setWindowTitle("Aktar — Excel / CSV")
        self.setMinimumWidth(520)
        self.setStyleSheet("""
            QDialog { background: #F8FAFC; }
            QLabel { color: #1E293B; font-size: 13px; }
            QCheckBox, QRadioButton { color: #1E293B; font-size: 13px; padding: 3px; }
            QPushButton {
                background: #2563EB; color: white; border: none;
                border-radius: 6px; padding: 8px 18px; font-weight: bold;
            }
            QPushButton:hover { background: #1D4ED8; }
            QPushButton#cancel {
                background: #FFFFFF; color: #475569; border: 1px solid #CBD5E1;
            }
            QPushButton#cancel:hover { background: #F1F5F9; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("<b>Dışa aktarılacak bölümleri seçin</b>")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(title)

        # Row counts up front, so the user does not export an empty sheet and
        # then wonder whether the export failed.
        self.checks = {}
        for kind, label in exporters.EXPORT_KINDS:
            try:
                _t, _h, rows = exporters.build_sheet(self.data_store, kind)
                count = len(rows)
            except Exception:
                count = 0
            box = QCheckBox(f"{label}   ({count} satır)")
            box.setChecked(count > 0 and kind.startswith("timetable_classes"))
            box.setEnabled(count > 0)
            if count == 0:
                box.setToolTip("Bu bölümde veri yok.")
            self.checks[kind] = box
            layout.addWidget(box)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #E2E8F0;")
        layout.addWidget(line)

        fmt_label = QLabel("<b>Biçim</b>")
        layout.addWidget(fmt_label)

        self.rb_xlsx = QRadioButton("Excel (.xlsx) — tüm bölümler ayrı sayfalarda")
        self.rb_csv = QRadioButton("CSV (.csv) — tek bölüm, Excel ile uyumlu")
        self.rb_xlsx.setChecked(exporters.HAS_XLSX)
        self.rb_csv.setChecked(not exporters.HAS_XLSX)
        if not exporters.HAS_XLSX:
            self.rb_xlsx.setEnabled(False)
            self.rb_xlsx.setToolTip("Excel çıktısı için 'openpyxl' paketi kurulu değil.")
            self.rb_xlsx.setText(self.rb_xlsx.text() + "  — kurulu değil")
        layout.addWidget(self.rb_xlsx)
        layout.addWidget(self.rb_csv)

        note = QLabel(
            "<i>CSV tek bir tablo tutabildiği için, seçtiğiniz ilk bölüm yazılır.</i>")
        note.setStyleSheet("color: #64748B; font-size: 11px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Vazgeç")
        cancel.setObjectName("cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        save = QPushButton("Kaydet...")
        save.clicked.connect(self._do_export)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _selected(self):
        return [k for k, box in self.checks.items() if box.isChecked() and box.isEnabled()]

    def _do_export(self):
        kinds = self._selected()
        if not kinds:
            QMessageBox.warning(self, "Seçim Yok",
                                "En az bir bölüm seçmelisiniz.")
            return

        use_xlsx = self.rb_xlsx.isChecked()
        ext = ".xlsx" if use_xlsx else ".csv"
        default_name = "ders_programi" + ext
        base = (self.data_store.get("settings", {}) or {}).get("school_name")
        if base:
            default_name = "".join(
                c for c in str(base) if c.isalnum() or c in " _-").strip().replace(" ", "_") + ext

        start_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.isdir(start_dir):
            start_dir = os.path.expanduser("~")

        path, _ = QFileDialog.getSaveFileName(
            self, "Dışa Aktar", os.path.join(start_dir, default_name),
            "Excel Dosyası (*.xlsx)" if use_xlsx else "CSV Dosyası (*.csv)")
        if not path:
            return
        if not path.lower().endswith(ext):
            path += ext

        try:
            written = exporters.export_to_file(self.data_store, path, kinds)
        except PermissionError:
            QMessageBox.critical(
                self, "Dosya Açık",
                "Dosya başka bir programda açık görünüyor.\n"
                "Excel'de kapatıp tekrar deneyin.")
            return
        except Exception as exc:
            QMessageBox.critical(self, "Dışa Aktarma Hatası", str(exc))
            return

        size_kb = os.path.getsize(written) / 1024
        note = ""
        if not use_xlsx and len(kinds) > 1:
            note = "\n\nNot: CSV tek tablo tuttuğu için yalnızca ilk bölüm yazıldı."
        QMessageBox.information(
            self, "Dışa Aktarıldı",
            f"{os.path.basename(written)} ({size_kb:.0f} KB) kaydedildi.\n\n{written}{note}")
        self.accept()
