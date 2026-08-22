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
        self.entity_name = name

        # Load cross-institution locks & busy slots
        self.cross_institution_locks = set()
        self.cross_institution_conflicts = {}
        self.my_reserved = set()        # slots this institution has reserved
        self.other_reserved = {}        # slot -> owning institution name
        self.inst_slug = None
        self.is_teacher = str(entity_type).strip().lower().startswith("öğretmen") or \
            str(entity_type).strip().lower().startswith("ogretmen")
        try:
            import constraint_sync
            from version_store import (
                get_cross_institution_teacher_busy_slots, normalize_teacher_name,
                get_last_active_institution_slug,
            )
            inst_slug = self.data_store.get("settings", {}).get("institution_slug") \
                or get_last_active_institution_slug()
            norm_name = normalize_teacher_name(name)

            # Constraints this teacher has at OTHER institutions. Matched on the
            # normalized name so a different spelling of the same person still lines
            # up — an exact-string lookup missed most real cases.
            day_count, periods = constraint_sync.grid_dimensions(self.data_store)
            shared = constraint_sync.shared_teacher_states(inst_slug, day_count, periods)
            for slot, state in (shared.get(norm_name) or {}).items():
                if state == constraint_sync.CLOSED:
                    self.cross_institution_locks.add(slot)

            # Hours this teacher is actually teaching elsewhere right now.
            cross_busy = get_cross_institution_teacher_busy_slots(exclude_slug=inst_slug)
            for (t_norm, d, p_slot), conflict_info in cross_busy.items():
                if t_norm == norm_name or conflict_info.get("teacher_name") == name:
                    self.cross_institution_locks.add((d, p_slot))
                    self.cross_institution_conflicts[(d, p_slot)] = conflict_info

            # Manual reservations: which institution has claimed each hour.
            self.inst_slug = inst_slug
            if self.is_teacher:
                import version_store as _vs
                slug_to_name = {}
                try:
                    for inst in _vs.list_institutions():
                        slug_to_name[inst.get("slug")] = inst.get("name", inst.get("slug"))
                except Exception:
                    pass
                for slot, owner in constraint_sync.reservations_for(name).items():
                    if owner == inst_slug:
                        self.my_reserved.add(slot)
                    else:
                        self.other_reserved[slot] = slug_to_name.get(owner, owner)
                        self.cross_institution_locks.add(slot)
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

        # Gün/saat boyutları ve müsaitlik matrisi artık constraint_sync üzerinden okunur;
        # Kısıtlamalar ekranı da aynı kaynağı kullandığı için iki ekran birbirini ezemez.
        import constraint_sync
        self._cs = constraint_sync
        self.days = constraint_sync.day_names(self.data_store)
        _, self.periods = constraint_sync.grid_dimensions(self.data_store)

        self.timeoff_data = constraint_sync.get_matrix(self.entity_dict, name, self.data_store)

        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Üst Bilgi
        info_text = ("💡 <b>Kısıtlama Ayarı:</b> Y ekseninde ders saatleri (1-" + str(self.periods) +
                     "), X ekseninde günler yer alır.<br>"
                     "Hücreye tıklayarak durumu değiştirin (Yeşil ✔ -> Kırmızı ✖ -> Sarı ? -> Yeşil ✔).")
        if self.is_teacher:
            info_text += ("<br>🔒 = bu öğretmen o saatte başka kurumda meşgul. "
                          "⚑ = saat bu kuruma rezerve. Rezerve etmek/kaldırmak için hücreye <b>sağ tıklayın</b>.")
        info_lbl = QLabel(info_text)
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
        if self.is_teacher:
            self.table.setContextMenuPolicy(Qt.CustomContextMenu)
            self.table.customContextMenuRequested.connect(self._on_context_menu)
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
        
        slot = (d_idx, p_idx)
        is_cross_locked = slot in getattr(self, "cross_institution_locks", set())
        c_info = getattr(self, "cross_institution_conflicts", {}).get(slot)
        owner_other = getattr(self, "other_reserved", {}).get(slot)
        is_mine = slot in getattr(self, "my_reserved", set())

        if c_info:
            c_inst = c_info.get("institution_name", "Başka Kurum")
            c_cls = c_info.get("class", "")
            c_subj = c_info.get("subject", "Ders")
            item.setToolTip(f"⚠️ ÇAKIŞMA UYARISI: Bu öğretmen {c_inst} kurumunda {c_cls} ({c_subj}) dersindedir!")
        elif owner_other:
            item.setToolTip(f"🔒 Bu saat '{owner_other}' kurumuna rezerve edilmiş. Serbest bırakması gereken o kurumdur.")
        elif is_mine:
            item.setToolTip("⚑ Bu saat bu kuruma rezerve edildi — diğer kurumlarda kapalı görünür.\n"
                            "Kaldırmak için sağ tıklayın.")
        elif is_cross_locked:
            item.setToolTip("⚠️ Dikkat: Bu öğretmen bu saatte BAŞKA BİR KURUMDA (şubede) derse girmektedir veya kısıtlanmıştır!")
        elif getattr(self, "is_teacher", False):
            item.setToolTip("Bu saati kurumunuza rezerve etmek için sağ tıklayın.")
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
            
        if is_mine:
            # Ours by explicit reservation — shown in blue so it reads as "claimed",
            # not as a restriction.
            base_text += " ⚑"
            bg_color = "#DBEAFE"
            fg_color = "#1D4ED8"
        elif is_cross_locked:
            base_text += " 🔒"
            if state != 0:
                # If they leave it open locally but it's locked elsewhere, warn them heavily
                bg_color = "#FFEDD5" # Orange
                fg_color = "#C2410C"

        item.setText(base_text)
        item.setForeground(QBrush(QColor(fg_color)))
        item.setBackground(QBrush(QColor(bg_color)))
            
    def _on_context_menu(self, pos):
        """Reserve/release this teacher's hour for the current institution.

        Reserving is how an institution claims a shared teacher's time BEFORE any
        lesson is placed there; every other institution then sees the hour as closed.
        """
        from PySide6.QtWidgets import QMenu, QMessageBox
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        p_idx, d_idx = index.row(), index.column()
        slot = (d_idx, p_idx)

        if not self.inst_slug:
            return

        owner_other = self.other_reserved.get(slot)
        menu = QMenu(self)
        if owner_other:
            act = menu.addAction(f"🔒 '{owner_other}' kurumuna rezerve — değiştirilemez")
            act.setEnabled(False)
            menu.exec_(self.table.viewport().mapToGlobal(pos))
            return

        if slot in self.my_reserved:
            act_toggle = menu.addAction("⚑ Rezervasyonu Kaldır")
            want = False
        else:
            act_toggle = menu.addAction("⚑ Bu Saati Kurumumuza Rezerve Et")
            want = True

        chosen = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if chosen != act_toggle:
            return

        import constraint_sync
        ok = constraint_sync.set_reservation(self.inst_slug, self.entity_name, slot, want)
        if not ok:
            QMessageBox.warning(self, "Rezervasyon",
                                "Bu saat başka bir kuruma ait. Serbest bırakması gereken o kurumdur.")
            return

        if want:
            self.my_reserved.add(slot)
        else:
            self.my_reserved.discard(slot)

        item = self.table.item(p_idx, d_idx)
        if item:
            self._update_item_visuals(item, self.timeoff_data[d_idx][p_idx], d_idx, p_idx)

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
        # Tek yazma noktası: timeoff ve kisitlamalar birlikte, 3 durumlu olarak yazılır.
        ent_name = (self.entity_dict.get("ad") or "").strip()
        self._cs.set_matrix(self.entity_dict, ent_name, self.data_store, self.timeoff_data)

        try:
            from database import trigger_save_db
            trigger_save_db(self, self.data_store)
        except Exception as e:
            print(f"[TIMEOFF_SAVE_ERR] local save failed: {e}")

        # Öğretmen kısıtlamalarını kurumlar arası ortak dosyaya yayınla; böylece diğer
        # kurumların planlayıcısı bu öğretmenin kapalı saatlerini görür.
        try:
            inst_slug = self.data_store.get("settings", {}).get("institution_slug")
            if not inst_slug:
                import version_store
                inst_slug = version_store.get_last_active_institution_slug()
            if inst_slug:
                self._cs.publish(inst_slug, self.data_store)
        except Exception as e:
            print(f"[TIMEOFF_SAVE_ERR] global constraint save failed: {e}")

        self.accept()
