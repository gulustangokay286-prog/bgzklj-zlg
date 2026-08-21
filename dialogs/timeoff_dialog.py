from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QLabel, QMessageBox, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QIcon, QFont

class TimeoffDialog(QDialog):
    """
    Öğretmen, Sınıf veya Derslik için Zaman-Kilit Matrisi (Time-off Matrix).
    Y Ekseni (Satırlar): 1. Ders ... 16. Ders (Temel Bilgiler ayarına göre dinamik)
    X Ekseni (Sütunlar): Pazartesi ... Cuma / Pazar
    Durumlar:
      2 = Yeşil Tik (Uygundur)
      0 = Kırmızı Çarpı (Çalışamaz / Kapalı)
      1 = Sarı Soru İşareti (Zorunlu olmadıkça atanmasın)
    """
    def __init__(self, entity_dict, entity_type, data_store, parent=None):
        super().__init__(parent)
        self.entity_dict = entity_dict
        self.entity_type = entity_type
        self.data_store = data_store if data_store is not None else {}
        
        name = self.entity_dict.get("ad", "İsimsiz")
        
        # Load cross-institution locks & busy slots
        self.cross_institution_locks = set()
        self.cross_institution_conflicts = {}
        try:
            from version_store import load_global_kisitlamalar, get_cross_institution_teacher_busy_slots, normalize_teacher_name
            global_k = load_global_kisitlamalar()
            inst_slug = self.data_store.get("settings", {}).get("institution_slug", "bogazici_egitim_kurumlari")
            for slug, k_data in global_k.items():
                if slug != inst_slug and isinstance(k_data, dict):
                    other_toff = k_data.get(name)
                    if other_toff and isinstance(other_toff, dict):
                        for k, v in other_toff.items():
                            if not v: # locked
                                try:
                                    parts = k.split(",")
                                    if len(parts) == 2:
                                        self.cross_institution_locks.add((int(parts[0]), int(parts[1])))
                                except: pass
            
            # Load actual timetable busy slots from other branches/institutions
            cross_busy = get_cross_institution_teacher_busy_slots(exclude_slug=inst_slug)
            norm_name = normalize_teacher_name(name)
            for (t_norm, d, p_slot), conflict_info in cross_busy.items():
                if t_norm == norm_name or conflict_info.get("teacher_name") == name:
                    self.cross_institution_locks.add((d, p_slot))
                    self.cross_institution_conflicts[(d, p_slot)] = conflict_info
        except Exception as e:
            print("Cross-institution lock load error:", e)

        self.setWindowTitle(f"Zaman Tablosu (Kısıtlamalar) - {name} ({self.entity_type})")
        self.resize(740, 520)
        
        # Tema ve CSS
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; font-family: 'Segoe UI', Tahoma, sans-serif; }
            QLabel { color: #1E293B; font-size: 13px; }
            QTableWidget { background-color: white; gridline-color: #CBD5E1; border: 1px solid #CBD5E1; border-radius: 6px; }
            QHeaderView::section { background-color: #F1F5F9; font-weight: bold; padding: 6px; border: 1px solid #E2E8F0; color: #1E293B; font-size: 12px; }
            QPushButton { background-color: #2563EB; color: white; border-radius: 4px; padding: 8px 18px; font-weight: bold; font-size: 13px; border: none; }
            QPushButton:hover { background-color: #1D4ED8; }
            QPushButton#btn_cancel { background-color: #FFFFFF; color: #475569; border: 1px solid #CBD5E1; }
            QPushButton#btn_cancel:hover { background-color: #F1F5F9; }
        """)
        
        self.settings = self.data_store.get("settings", {})
        
        # Günleri oku
        self.days = self.settings.get("days")
        if not self.days:
            days_count = int(self.settings.get("days_count", self.settings.get("day_count", self.data_store.get("gun_sayisi", 5))))
            from timetable_grid import DAYS
            self.days = DAYS[:days_count]
            
        # Periyot / Günlük ders saatini Temel Bilgiler'den dinamik oku (Örn: 8, 10, 12, 16)
        self.periods = int(self.settings.get("periods", self.data_store.get("ders_saati", 8)))
        if self.periods <= 0:
            self.periods = 8
            
        # `timeoff` verisini dinamik periyot ve gün sayısına göre boyutlandır ve senkronize et
        current_toff = self.entity_dict.get("timeoff", [])
        new_toff = []
        for d_idx in range(len(self.days)):
            row = []
            for p_idx in range(self.periods):
                if d_idx < len(current_toff) and p_idx < len(current_toff[d_idx]):
                    row.append(current_toff[d_idx][p_idx])
                else:
                    row.append(2)  # Varsayılan: Açık / Uygun
            new_toff.append(row)
            
        self.entity_dict["timeoff"] = new_toff
        self.timeoff_data = self.entity_dict["timeoff"]
        
        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Üst Bilgi
        info_lbl = QLabel("💡 <b>Kısıtlama Ayarı:</b> Y ekseninde ders saatleri (1-" + str(self.periods) + "), X ekseninde günler yer alır.<br>Hücreye tıklayarak durumu değiştirin (Yeşil ✔ -> Kırmızı ✖ -> Sarı ? -> Yeşil ✔).")
        info_lbl.setStyleSheet("color: #475569; font-size: 12px;")
        layout.addWidget(info_lbl)
        
        # Grid: Y-Ekseni = Periyotlar (1..periods), X-Ekseni = Günler (Pzt..Cuma)
        self.table = QTableWidget(self.periods, len(self.days))
        self.table.setVerticalHeaderLabels([f"{i+1}. Ders" for i in range(self.periods)])
        self.table.setHorizontalHeaderLabels(self.days)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # Satır ve Sütun boyutları
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Hücreleri Doldur
        for p_idx in range(self.periods):
            for d_idx in range(len(self.days)):
                state = self.timeoff_data[d_idx][p_idx]
                item = QTableWidgetItem()
                self._update_item_visuals(item, state, d_idx, p_idx)
                self.table.setItem(p_idx, d_idx, item)
                
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.horizontalHeader().sectionClicked.connect(self._toggle_column)
        self.table.verticalHeader().sectionClicked.connect(self._toggle_row)
        layout.addWidget(self.table, 1)
        
        # Hızlı Butonlar (Tümünü Kapat / Tümünü Aç)
        quick_bar = QHBoxLayout()
        btn_all_open = QPushButton("Tümünü Müsait Yap (✔)")
        btn_all_open.setStyleSheet("background: #DCFCE7; color: #15803D; border: 1px solid #86EFAC; font-size: 11px;")
        btn_all_open.clicked.connect(self._make_all_open)
        
        btn_all_close = QPushButton("Tümünü Kapat / Kısıtla (✖)")
        btn_all_close.setStyleSheet("background: #FEE2E2; color: #B91C1C; border: 1px solid #FCA5A5; font-size: 11px;")
        btn_all_close.clicked.connect(self._make_all_close)
        
        quick_bar.addWidget(btn_all_open)
        quick_bar.addWidget(btn_all_close)
        quick_bar.addStretch(1)
        layout.addLayout(quick_bar)
        
        # Lejand (Legend)
        legend_layout = QHBoxLayout()
        self.lbl_musait = self._create_legend_item("✔ Müsait (0)", "#15803D")
        self.lbl_kapali = self._create_legend_item("✖ Kapalı / Kısıtlı (0)", "#B91C1C")
        self.lbl_tercih = self._create_legend_item("? Tercih Edilmez (0)", "#A16207")
        legend_layout.addWidget(self.lbl_musait)
        legend_layout.addWidget(self.lbl_kapali)
        legend_layout.addWidget(self.lbl_tercih)
        legend_layout.addStretch()
        layout.addLayout(legend_layout)
        
        self._update_counters()
        
        # Alt Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setObjectName("btn_cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_save = QPushButton("Kaydet ve Uygula")
        btn_save.clicked.connect(self._save_data)
        btn_layout.addWidget(btn_save)
        
        layout.addLayout(btn_layout)
        
    def _create_legend_item(self, text, color):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {color}; font-weight: bold; margin-right: 15px;")
        return lbl
        
    def _update_counters(self):
        c_musait = 0
        c_kapali = 0
        c_tercih = 0
        for d in range(len(self.days)):
            for p in range(self.periods):
                state = self.timeoff_data[d][p]
                if state == 2: c_musait += 1
                elif state == 0: c_kapali += 1
                elif state == 1: c_tercih += 1
                
        self.lbl_musait.setText(f"✔ Müsait ({c_musait})")
        self.lbl_kapali.setText(f"✖ Kapalı / Kısıtlı ({c_kapali})")
        self.lbl_tercih.setText(f"? Tercih Edilmez ({c_tercih})")


    def _update_item_visuals(self, item, state, d_idx, p_idx):
        item.setTextAlignment(Qt.AlignCenter)
        font = QFont("Segoe UI", 11, QFont.Bold)
        item.setFont(font)
        
        is_cross_locked = (d_idx, p_idx) in getattr(self, "cross_institution_locks", set())
        c_info = getattr(self, "cross_institution_conflicts", {}).get((d_idx, p_idx))
        if c_info:
            c_inst = c_info.get("institution_name", "Başka Kurum")
            c_cls = c_info.get("class", "")
            c_subj = c_info.get("subject", "Ders")
            item.setToolTip(f"⚠️ ÇAKIŞMA UYARISI: Bu öğretmen {c_inst} kurumunda {c_cls} ({c_subj}) dersindedir!")
        elif is_cross_locked:
            item.setToolTip("⚠️ Dikkat: Bu öğretmen bu saatte BAŞKA BİR KURUMDA (şubede) derse girmektedir veya kısıtlanmıştır!")
        else:
            item.setToolTip("")

        base_text = ""
        fg_color = ""
        bg_color = ""

        if state == 2:
            base_text = "✔"
            fg_color = "#15803D"
            bg_color = "#DCFCE7"
        elif state == 0:
            base_text = "✖"
            fg_color = "#B91C1C"
            bg_color = "#FEE2E2"
        elif state == 1:
            base_text = "?"
            fg_color = "#A16207"
            bg_color = "#FEF9C3"
            
        if is_cross_locked:
            base_text += " 🔒"
            if state != 0:
                # If they leave it open locally but it's locked elsewhere, warn them heavily
                bg_color = "#FFEDD5" # Orange
                fg_color = "#C2410C"
                
        item.setText(base_text)
        item.setForeground(QBrush(QColor(fg_color)))
        item.setBackground(QBrush(QColor(bg_color)))
            
    def _on_cell_clicked(self, row, col):
        # row = p_idx (period), col = d_idx (day)
        current_state = self.timeoff_data[col][row]
        # Cycle: 2 -> 0 -> 1 -> 2
        if current_state == 2:
            new_state = 0
        elif current_state == 0:
            new_state = 1
        else:
            new_state = 2
            
        self.timeoff_data[col][row] = new_state
        item = self.table.item(row, col)
        self._update_item_visuals(item, new_state, col, row)
        self._update_counters()

    def _toggle_column(self, col):
        # col = d_idx (toggle entire day)
        any_open = any(self.timeoff_data[col][p] > 0 for p in range(self.periods))
        new_st = 0 if any_open else 2
        for p in range(self.periods):
            self.timeoff_data[col][p] = new_st
            item = self.table.item(p, col)
            if item: self._update_item_visuals(item, new_st, col, p)
        self._update_counters()

    def _toggle_row(self, row):
        # row = p_idx (toggle entire period)
        any_open = any(self.timeoff_data[d][row] > 0 for d in range(len(self.days)))
        new_st = 0 if any_open else 2
        for d in range(len(self.days)):
            self.timeoff_data[d][row] = new_st
            item = self.table.item(row, d)
            if item: self._update_item_visuals(item, new_st, d, row)
        self._update_counters()

    def _make_all_open(self):
        for d in range(len(self.days)):
            for p in range(self.periods):
                self.timeoff_data[d][p] = 2
                item = self.table.item(p, d)
                if item: self._update_item_visuals(item, 2, d, p)
        self._update_counters()

    def _make_all_close(self):
        for d in range(len(self.days)):
            for p in range(self.periods):
                self.timeoff_data[d][p] = 0
                item = self.table.item(p, d)
                if item: self._update_item_visuals(item, 0, d, p)
        self._update_counters()

    def _save_data(self):
        self.entity_dict["timeoff"] = self.timeoff_data
        if "kisitlamalar" not in self.data_store:
            self.data_store["kisitlamalar"] = {}
        ent_name = self.entity_dict.get("ad", "")
        if ent_name:
            if ent_name not in self.data_store["kisitlamalar"]:
                self.data_store["kisitlamalar"][ent_name] = {}
            for d in range(len(self.days)):
                for p in range(self.periods):
                    st = self.timeoff_data[d][p]
                    self.data_store["kisitlamalar"][ent_name][f"{d},{p}"] = (st > 0)

        # Both of these calls were wrong, and because they shared one try/except the
        # first failure skipped the second silently:
        #   * trigger_save_db lives in database.py, not version_store, so importing
        #     it from there raised ImportError and nothing below ever ran;
        #   * save_global_kisitlamalar takes (institution_slug, kisitlamalar) and was
        #     being called with a single argument.
        # The constraints survived only because master_data_dialog happens to call
        # trigger_save_db itself afterwards; the cross-institution copy was never
        # written at all.
        try:
            from database import trigger_save_db
            trigger_save_db(self, self.data_store)
        except Exception as e:
            print(f"[TIMEOFF_SAVE_ERR] local save failed: {e}")

        try:
            from version_store import save_global_kisitlamalar
            inst_slug = self.data_store.get("settings", {}).get(
                "institution_slug", "bogazici_egitim_kurumlari"
            )
            save_global_kisitlamalar(inst_slug, self.data_store["kisitlamalar"])
        except Exception as e:
            print(f"[TIMEOFF_SAVE_ERR] global constraint save failed: {e}")

        self.accept()
