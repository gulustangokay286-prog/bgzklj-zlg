"""
dialogs/statistics_dialog.py — "Analiz / İstatistik" ekranı.

Saatler lesson_hours üzerinden okunur; sınıf ekranı, öğretmen ekranı ve otomatik
planlayıcı ile AYNI kaynak. Bu ekran eskiden hiçbir ekranın yazmadığı `saat` ve
`ogretmen` alanlarını okuyordu: 182 saatlik bir okul için "Atanan Toplam Ders
Saati: 72" yazıyor, öğretmen yükü tablosu ise tamamen boş geliyordu. Sınıf ve
öğretmen tarafının tutmadığı izlenimi büyük ölçüde buradan doğuyordu.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor

import lesson_hours


class StatisticsDialog(QDialog):
    def __init__(self, data_store, parent=None):
        super().__init__(parent)
        self.data_store = data_store if data_store is not None else {}
        self.setWindowTitle("İstatistikler ve Analiz")
        self.resize(760, 620)

        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; }
            QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid #CBD5E1; border-radius: 4px; margin-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; color: #334155; }
            QLabel { font-size: 13px; color: #475569; }
            QTableWidget { background-color: white; border: 1px solid #E2E8F0; }
            QHeaderView::section { background-color: #F1F5F9; font-weight: bold; border: 1px solid #E2E8F0; }
            QPushButton { background-color: #3B82F6; color: white; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #2563EB; }
        """)

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)

        per_class = lesson_hours.per_class(self.data_store)
        per_teacher = lesson_hours.per_teacher(self.data_store)
        audit = lesson_hours.audit(self.data_store)

        try:
            import advisor
            capacity = advisor.teacher_capacity(self.data_store)
            open_slots = advisor.open_slots_per_class(self.data_store)
            placed_c = advisor.placed_per_class(self.data_store)
        except Exception:
            capacity, open_slots, placed_c = {}, {}, {}

        # 1. Genel özet -------------------------------------------------
        grp_summary = QGroupBox("Genel Okul Özeti")
        sum_layout = QVBoxLayout(grp_summary)
        sum_layout.addWidget(QLabel(
            f"Toplam Sınıf Sayısı: {len(self.data_store.get('siniflar', []) or [])}"))
        sum_layout.addWidget(QLabel(
            f"Toplam Öğretmen Sayısı: {len(self.data_store.get('ogretmenler', []) or [])}"))
        sum_layout.addWidget(QLabel(
            f"Atanan Toplam Ders Saati: {audit['lesson_total']} Saat"))
        sum_layout.addWidget(QLabel(
            f"Sınıf tarafı toplamı: {audit['class_total']} Saat  |  "
            f"Öğretmen tarafı toplamı: {audit['teacher_total']} Saat"))

        warn = self._mismatch_text(audit)
        if warn:
            lbl = QLabel(warn)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #B91C1C; font-weight: bold;")
            sum_layout.addWidget(lbl)
        else:
            ok = QLabel("Sınıf ekranı ile öğretmen ekranı birebir tutuyor ✔")
            ok.setStyleSheet("color: #15803D; font-weight: bold;")
            sum_layout.addWidget(ok)
        layout.addWidget(grp_summary)

        # 2. Öğretmen yükleri ------------------------------------------
        grp_teachers = QGroupBox("Öğretmen Ders Yükü Dağılımı")
        t_layout = QVBoxLayout(grp_teachers)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ["Öğretmen", "Haftalık Toplam Saat", "En Fazla Mümkün"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        known = [(t.get("ad") or t.get("name") or "").strip()
                 for t in self.data_store.get("ogretmenler", []) or []]
        names = sorted(set([n for n in known if n]) | set(per_teacher), key=lambda n:
                       (-per_teacher.get(n, 0), n))
        self.table.setRowCount(len(names))
        for row, name in enumerate(names):
            hours = per_teacher.get(name, 0)
            cap = capacity.get(name)
            self.table.setItem(row, 0, QTableWidgetItem(name))
            h_item = QTableWidgetItem(f"{hours} Saat")
            h_item.setTextAlignment(Qt.AlignCenter)
            c_item = QTableWidgetItem("—" if cap is None else f"{cap} Saat")
            c_item.setTextAlignment(Qt.AlignCenter)
            if cap is not None and hours > cap:
                # Bu satır çizelgenin neden dolmadığını tek başına açıklar.
                for it in (h_item, c_item):
                    it.setBackground(QBrush(QColor("#FEE2E2")))
                    it.setForeground(QBrush(QColor("#B91C1C")))
                c_item.setText(f"{cap} Saat  (+{hours - cap} fazla)")
            self.table.setItem(row, 1, h_item)
            self.table.setItem(row, 2, c_item)
        t_layout.addWidget(self.table)
        layout.addWidget(grp_teachers)

        # 3. Sınıf yükleri ----------------------------------------------
        grp_classes = QGroupBox("Sınıf Ders Yükü Dağılımı")
        c_layout = QVBoxLayout(grp_classes)
        self.table_c = QTableWidget(0, 4)
        self.table_c.setHorizontalHeaderLabels(
            ["Sınıf", "Atanan Saat", "Açık Saat", "Yerleşen"])
        self.table_c.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in (1, 2, 3):
            self.table_c.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table_c.setEditTriggers(QTableWidget.NoEditTriggers)

        class_names = [(c.get("ad") or c.get("name") or "").strip()
                       for c in self.data_store.get("siniflar", []) or []]
        class_names = [c for c in class_names if c] or sorted(per_class)
        self.table_c.setRowCount(len(class_names))
        for row, cls in enumerate(class_names):
            need = per_class.get(cls, 0)
            have = open_slots.get(cls)
            got = placed_c.get(cls, 0)
            self.table_c.setItem(row, 0, QTableWidgetItem(cls))
            for col, text in ((1, f"{need}"), (2, "—" if have is None else f"{have}"),
                              (3, f"{got}")):
                it = QTableWidgetItem(text)
                it.setTextAlignment(Qt.AlignCenter)
                if col == 1 and have is not None and need > have:
                    it.setBackground(QBrush(QColor("#FEE2E2")))
                    it.setForeground(QBrush(QColor("#B91C1C")))
                self.table_c.setItem(row, col, it)
        c_layout.addWidget(self.table_c)
        layout.addWidget(grp_classes)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton("Kapat")
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    @staticmethod
    def _mismatch_text(audit):
        """İki tarafın tutmadığı durumu, kullanıcının düzeltebileceği dille anlatır."""
        parts = []
        if audit["stale_rows"]:
            parts.append(f"{len(audit['stale_rows'])} atamada saat alanları birbirini "
                         f"tutmuyor (ör. {audit['stale_rows'][0][0]} — "
                         f"{audit['stale_rows'][0][1]}).")
        if audit["unknown_teachers"]:
            sample = ", ".join(f"{t}" for _c, _s, t, _h in audit["unknown_teachers"][:3])
            parts.append(f"{len(audit['unknown_teachers'])} atamanın öğretmeni öğretmen "
                         f"listesinde yok: {sample}")
        if audit["unknown_classes"]:
            sample = ", ".join(c for c, _s, _t, _h in audit["unknown_classes"][:3])
            parts.append(f"{len(audit['unknown_classes'])} atamanın sınıfı sınıf "
                         f"listesinde yok: {sample}")
        if audit["combined_extra"]:
            parts.append(f"{audit['combined_extra']} saat birleşik (eş zamanlı) ders "
                         f"olduğu için sınıf tarafı toplamı daha yüksek görünür.")
        return "  ".join(parts)
