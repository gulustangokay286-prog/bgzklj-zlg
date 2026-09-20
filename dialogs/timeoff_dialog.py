from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QLabel, QMessageBox, QHeaderView, QAbstractItemView, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QIcon, QFont, QPainter, QPen
from ui_icons import icon, pixmap

FONT_FAMILY = ".AppleSystemUIFont, SF Pro Text, -apple-system, Helvetica Neue, Segoe UI, sans-serif"

class TimeoffDialog(QDialog):
    """
    Öğretmen, Sınıf veya Derslik için Modern Zaman-Kısıtlama Matrisi (Time-off Matrix).
    Y Ekseni (Satırlar): 1. Ders ... 16. Ders
    X Ekseni (Sütunlar): Pazartesi ... Cuma
    Durumlar:
      2 = Müsait (Yeşil)
      0 = Kapalı / Kısıtlı (Kırmızı)
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
        # Kurumlar bağımsız (constraint_sync.INSTITUTIONS_INDEPENDENT): başka
        # kurumdaki ders, rezervasyon ve kişisel kısıt bu ekranda görünmez,
        # hücreleri kilitlemez. Kullanıcının gördüğü tablo kaydedilen tablodur.
        try:
            import constraint_sync
            from version_store import (
                get_cross_institution_teacher_busy_slots, normalize_teacher_name,
                get_last_active_institution_slug,
            )
            inst_slug = self.data_store.get("settings", {}).get("institution_slug") \
                or get_last_active_institution_slug()
            norm_name = normalize_teacher_name(name)
            self.independent = constraint_sync.institutions_independent()

            # Only lock slots where the teacher is actually scheduled/reserved in another institution.
            # Slots closed at another institution mean the teacher is FREE for this institution.

            cross_busy = {} if self.independent else \
                get_cross_institution_teacher_busy_slots(exclude_slug=inst_slug)
            for (t_norm, d, p_slot), conflict_info in cross_busy.items():
                if t_norm == norm_name or conflict_info.get("teacher_name") == name:
                    self.cross_institution_locks.add((d, p_slot))
                    self.cross_institution_conflicts[(d, p_slot)] = conflict_info

            self.inst_slug = inst_slug
            if self.is_teacher and not self.independent:
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

        self.setWindowTitle(f"Zaman Tablosu (Kısıtlamalar) — {name} ({self.entity_type})")
        self.resize(780, 560)
        self.setMinimumSize(700, 500)
        
        # Tema ve CSS
        self.setStyleSheet(f"""
            QDialog {{ background-color: #F8FAFC; font-family: {FONT_FAMILY}; }}
            QLabel {{ color: #1E293B; font-size: 13px; font-family: {FONT_FAMILY}; }}
            QTableWidget {{
                background-color: #FFFFFF;
                gridline-color: #E2E8F0;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                font-family: {FONT_FAMILY};
            }}
            QHeaderView::section {{
                background-color: #F8FAFC;
                font-weight: 600;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #E2E8F0;
                border-right: 1px solid #F1F5F9;
                color: #0F172A;
                font-size: 12px;
                font-family: {FONT_FAMILY};
            }}
            QPushButton {{
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                font-family: {FONT_FAMILY};
            }}
        """)
        
        self.settings = self.data_store.get("settings", {})

        import constraint_sync
        self._cs = constraint_sync
        self.days = constraint_sync.day_names(self.data_store)
        _, self.periods = constraint_sync.grid_dimensions(self.data_store)

        self.timeoff_data = constraint_sync.get_matrix(self.entity_dict, name, self.data_store)
        # Kişisel kısıt ayrı katman: "bu kurumda yok" ile "hiçbir yerde yok" aynı
        # şey değil. İlki yalnız burayı, ikincisi bütün kurumları bağlar.
        self.personal_data = constraint_sync.get_personal(
            self.entity_dict, name, self.data_store)

        # Çizelgede hangi saatlerin dolu olduğu, hücreler kurulmadan önce
        # bilinmeli: _update_item_visuals buna bakıyor.
        self._busy_slots = self._load_busy_slots()

        self._build_ui()

    def _is_personal(self, d_idx, p_idx):
        try:
            return bool(self.personal_data[d_idx][p_idx])
        except (IndexError, TypeError):
            return False

    def _set_personal(self, d_idx, p_idx, on):
        self.personal_data[d_idx][p_idx] = bool(on)
        if on:
            self.timeoff_data[d_idx][p_idx] = 0
        item = self.table.item(p_idx, d_idx)
        if item:
            self._update_item_visuals(item, self.timeoff_data[d_idx][p_idx], d_idx, p_idx)
        self._update_counters()

    def _apply_half_day(self, d_idx, first_half, personal):
        """Yarım gün: günün ilk ya da ikinci yarısını kapatır."""
        half = self.periods // 2 or 1
        rng = range(0, half) if first_half else range(half, self.periods)
        for p in rng:
            if personal:
                self._set_personal(d_idx, p, True)
            else:
                self.personal_data[d_idx][p] = False
                self.timeoff_data[d_idx][p] = 0
                item = self.table.item(p, d_idx)
                if item:
                    self._update_item_visuals(item, 0, d_idx, p)
        self._update_counters()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        
        # AÇIKLAMA EKRANDA DEĞİL, İSTENDİĞİNDE.
        #
        # Üstte üç satırlık mavi bir kart vardı ve tablonun nasıl
        # kullanılacağını anlatıyordu: tıkla, sağ tıkla, başlığa tıkla.
        # Bu ekranı ilk kez açan bir kez okur, sonraki her açılışta aynı
        # üç satır tablonun yerini kaplar. Yardım artık sağ üstteki tek
        # düğmede duruyor; açılınca küçük bir sayfada aynı şeyleri anlatıp
        # kapanıyor.
        head = QHBoxLayout()
        head.setContentsMargins(2, 0, 2, 0)
        head.setSpacing(8)
        title = QLabel(self.entity_name)
        title.setStyleSheet("color: #0F172A; font-size: 15px; font-weight: 700;"
                            " background: transparent; border: none;")
        head.addWidget(title)
        subtitle = QLabel("zaman tablosu")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 12px;"
                               " background: transparent; border: none;")
        head.addWidget(subtitle)
        head.addStretch(1)
        btn_help = QPushButton("?")
        btn_help.setCursor(Qt.PointingHandCursor)
        btn_help.setFixedSize(24, 24)
        btn_help.setToolTip("Bu tablo nasıl kullanılır?")
        btn_help.setStyleSheet("""
            QPushButton {
                background: #F1F5F9; color: #475569;
                border: 1px solid #E2E8F0; border-radius: 12px;
                font-weight: 700; font-size: 12px;
            }
            QPushButton:hover { background: #E2E8F0; color: #0F172A; }
        """)
        btn_help.clicked.connect(self._show_help)
        head.addWidget(btn_help)
        layout.addLayout(head)
        
        # Grid: Y-Ekseni = Periyotlar (1..periods), X-Ekseni = Günler (Pzt..Cuma)
        self.table = QTableWidget(self.periods, len(self.days))
        self.table.setVerticalHeaderLabels([f"{i+1}. Ders" for i in range(self.periods)])
        self.table.setHorizontalHeaderLabels(self.days)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setShowGrid(True)
        
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
        
        # Hızlı Butonlar ve Lejand
        bar_layout = QHBoxLayout()
        bar_layout.setSpacing(12)
        
        btn_all_open = QPushButton("Tümünü Müsait Yap")
        btn_all_open.setStyleSheet("""
            QPushButton {
                background: #ECFDF5;
                color: #065F46;
                border: 1px solid #A7F3D0;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { background: #D1FAE5; }
        """)
        btn_all_open.clicked.connect(self._make_all_open)
        
        btn_all_close = QPushButton("Tümünü Kısıtla")
        btn_all_close.setStyleSheet("""
            QPushButton {
                background: #FFF1F2;
                color: #9F1239;
                border: 1px solid #FECDD3;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { background: #FFE4E6; }
        """)
        btn_all_close.clicked.connect(self._make_all_close)
        
        bar_layout.addWidget(btn_all_open)
        bar_layout.addWidget(btn_all_close)
        bar_layout.addSpacing(16)
        
        # Lejand (Legend Chips)
        self.lbl_musait = self._create_legend_item("Müsait (0)", "#059669", "#ECFDF5", "#A7F3D0")
        self.lbl_kapali = self._create_legend_item("Kapalı / Kısıtlı (0)", "#E11D48", "#FFF1F2", "#FECDD3")
        bar_layout.addWidget(self.lbl_musait)
        bar_layout.addWidget(self.lbl_kapali)
        if getattr(self, "_busy_slots", None):
            bar_layout.addWidget(self._create_legend_item(
                f"Çizelgede dolu: {len(self._busy_slots)}", "#475569", "#ECEEF2", "#D3D8E0"))
        bar_layout.addStretch(1)
        
        layout.addLayout(bar_layout)
        
        self._update_counters()
        
        # Alt Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch(1)
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                padding: 8px 20px;
                min-height: 36px;
                border-radius: 8px;
            }
            QPushButton:hover { background: #F8FAFC; color: #1E293B; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_save = QPushButton("Kaydet ve Uygula")
        btn_save.setStyleSheet("""
            QPushButton {
                background: #0071E3;
                color: #FFFFFF;
                border: none;
                padding: 8px 24px;
                min-height: 36px;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:hover { background: #0062C4; }
        """)
        btn_save.clicked.connect(self._save_data)
        btn_layout.addWidget(btn_save)
        
        layout.addLayout(btn_layout)
        
    def _load_busy_slots(self):
        """Bu kişinin çizelgede DOLU olduğu saatler: {(gün, saat): "9A · Matematik"}.

        Müsaitlik ayarlanırken eksik olan bilgi buydu: hangi saatlerde zaten
        ders var? Bir saati kapatmadan önce oraya bir şey yerleşmiş mi
        görünmüyordu, bakmak için başka ekrana geçmek gerekiyordu.

        Aynı blok gride her saati için bir kayıt olarak durabiliyor ve her
        kayıt bloğun TOPLAM süresini taşıyor; süreleri toplamak iki katı
        sayardı. Saatler kümede toplanıyor, her (gün, saat) bir kez.
        """
        out = {}
        if not self.is_teacher:
            return out
        try:
            from auto_scheduler import format_tr_name
            want = format_tr_name(self.entity_name)
            for p in self.data_store.get("grid_placements", []) or []:
                if not isinstance(p, dict):
                    continue
                who = format_tr_name(p.get("teacher_name") or p.get("teacher") or "")
                if who != want:
                    continue
                d = int(p.get("day") if "day" in p else p.get("col", 0))
                per = int(p.get("period") if "period" in p else p.get("row", 0))
                dur = max(1, int(p.get("duration", 1) or 1))
                cls = (p.get("class_name") or p.get("class") or "").strip()
                subj = (p.get("subject_name") or p.get("subject") or "").strip()
                label = " · ".join(x for x in (cls, subj) if x) or "Ders"
                for off in range(dur):
                    out.setdefault((d, per + off), label)
        except Exception as exc:
            print(f"[Zaman tablosu] dolu saatler okunamadı: {exc}")
            return {}
        return out

    def _show_help(self):
        """Kullanımı anlatan küçük sayfa — ekranda değil, istendiğinde."""
        sheet = QDialog(self)
        sheet.setWindowTitle("Zaman tablosu nasıl kullanılır?")
        sheet.setModal(True)
        sheet.setFixedWidth(430)
        lay = QVBoxLayout(sheet)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(12)

        head = QLabel("Zaman tablosu")
        head.setStyleSheet("color: #0F172A; font-size: 15px; font-weight: 700;")
        lay.addWidget(head)

        rows = [
            ("Hücreye tıklayın", "Saati müsait ✓ ile kısıtlı ✕ arasında çevirir."),
            ("Gün veya saat başlığına tıklayın", "O günün ya da o saatin tamamını birden çevirir."),
            ("Gri hücreler", "Çizelgede o saate bir ders yerleşmiş demektir; "
                             "hangisi olduğunu görmek için üzerine gelin."),
        ]
        if self.is_teacher:
            rows.append(("Sağ tıklayın",
                         "Bir saati bu kuruma rezerve edebilir, kişisel kısıt "
                         "koyabilir ya da yarım gün kapatabilirsiniz."))
        for t, d in rows:
            box = QVBoxLayout()
            box.setSpacing(2)
            lt = QLabel(t)
            lt.setStyleSheet("color: #0F172A; font-size: 12.5px; font-weight: 600;")
            ld = QLabel(d)
            ld.setStyleSheet("color: #64748B; font-size: 12px;")
            ld.setWordWrap(True)
            box.addWidget(lt)
            box.addWidget(ld)
            lay.addLayout(box)

        btn = QPushButton("Anladım")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(32)
        btn.setStyleSheet("""
            QPushButton {
                background: #0F4AAB; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 0 18px; font-weight: 600; font-size: 12.5px;
            }
            QPushButton:hover { background: #0C3C8C; }
        """)
        btn.clicked.connect(sheet.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(btn)
        lay.addLayout(row)
        sheet.exec()

    def _create_legend_item(self, text, fg, bg, border):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"""
            QLabel {{
                color: {fg};
                background: {bg};
                border: 1px solid {border};
                border-radius: 12px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 11px;
            }}
        """)
        return lbl
        
    def _update_counters(self):
        c_musait = 0
        c_kapali = 0
        for d in range(len(self.days)):
            for p in range(self.periods):
                state = self.timeoff_data[d][p]
                if state == 2: c_musait += 1
                elif state == 0: c_kapali += 1
                
        c_kisisel = sum(1 for d in range(len(self.days)) for p in range(self.periods)
                        if self._is_personal(d, p))

        self.lbl_musait.setText(f"● Müsait: {c_musait}")
        self.lbl_kapali.setText(f"● Kısıtlı: {c_kapali}"
                                + (f" ({c_kisisel} kişisel)" if c_kisisel else ""))

    def _update_item_visuals(self, item, state, d_idx, p_idx):
        item.setTextAlignment(Qt.AlignCenter)
        font = QFont(".AppleSystemUIFont", 12, QFont.Bold)
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
            item.setToolTip(f"Çakışma: Bu öğretmen {c_inst} kurumunda {c_cls} ({c_subj}) dersindedir.")
        elif owner_other:
            item.setToolTip(f"Bu saat '{owner_other}' kurumuna rezerve edilmiş.")
        elif is_mine:
            item.setToolTip("Bu saat bu kuruma rezerve edildi.\nKaldırmak için sağ tıklayın.")
        elif is_cross_locked:
            item.setToolTip("Bu öğretmen bu saatte başka bir kurumda derse girmektedir.")
        elif getattr(self, "is_teacher", False):
            item.setToolTip("Bu saati kurumunuza rezerve etmek için sağ tıklayın.")
        else:
            item.setToolTip("")

        base_text = ""
        fg_color = ""
        bg_color = ""

        busy_label = getattr(self, "_busy_slots", {}).get(slot)

        if state == 2:
            base_text = "✓"
            if busy_label:
                # Müsait AMA dolu: çizelgede o saate bir ders yerleşmiş.
                # Yeşil "burası boş, kullanılabilir" demektir; burası boş
                # değil. Aynı işaret, sakin bir zeminde.
                fg_color = "#64748B"
                bg_color = "#ECEEF2"
                item.setToolTip(f"Çizelgede bu saatte ders var: {busy_label}")
            else:
                fg_color = "#059669"
                bg_color = "#ECFDF5"
        elif state == 0:
            base_text = "✕"
            fg_color = "#E11D48"
            bg_color = "#FFF1F2"

        # Kişisel kısıt kurum kısıtının üstünde durur ve farklı görünür: bu saat
        # yalnız burada değil, öğretmenin çalıştığı BÜTÜN kurumlarda kapalıdır.
        if self._is_personal(d_idx, p_idx):
            base_text = "✕ Kişisel"
            fg_color = "#FFFFFF"
            bg_color = "#7F1D1D"
            item.setToolTip("Kişisel kısıt: öğretmen bu saatte hiçbir kurumda müsait "
                            "değil.\nKaldırmak için sağ tıklayın.")

        if is_mine:
            base_text += " [Rezerve]"
            bg_color = "#EFF6FF"
            fg_color = "#2563EB"

        item.setText(base_text)
        item.setForeground(QBrush(QColor(fg_color)))
        item.setBackground(QBrush(QColor(bg_color)))
            
    def _on_context_menu(self, pos):
        """Reserve/release this teacher's hour for the current institution."""
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
        independent = getattr(self, "independent", True)
        act_toggle = None
        want = False
        if not independent:
            if owner_other:
                info_act = menu.addAction(icon("info", 14, "#64748B"),
                                          f"'{owner_other}' kurumunda planlı")
                info_act.setEnabled(False)
                menu.addSeparator()

            if slot in self.my_reserved:
                act_toggle = menu.addAction(icon("flag", 14, "#94A3B8"), "Rezervasyonu Kaldır")
                want = False
            else:
                act_toggle = menu.addAction(icon("flag", 14, "#2563EB"),
                                            "Bu Saati Kurumumuza Rezerve Et")
                want = True

        act_personal = act_half_am = act_half_pm = act_half_clear = None
        if self.is_teacher:
            if not independent:
                menu.addSeparator()
            if self._is_personal(d_idx, p_idx):
                act_personal = menu.addAction(icon("unlock", 14, "#059669"), "Kişisel kısıtı kaldır")
            elif independent:
                act_personal = menu.addAction(icon("lock", 14, "#7F1D1D"),
                                              "Kişisel kısıt (izin/rapor) olarak kapat")
            else:
                act_personal = menu.addAction(icon("lock", 14, "#7F1D1D"),
                                              "Kişisel: hiçbir kurumda müsait değil")
            menu.addSeparator()
            act_half_am = menu.addAction(icon("sun", 14, "#B45309"),
                                         "Bu gün: sabah gelmiyor (yarım gün)")
            act_half_pm = menu.addAction(icon("moon", 14, "#4338CA"),
                                         "Bu gün: öğleden sonra gelmiyor (yarım gün)")
            act_half_clear = menu.addAction(icon("refresh", 14, "#059669"),
                                            "Bu günü tamamen aç")

        chosen = menu.exec_(self.table.viewport().mapToGlobal(pos))

        if chosen is not None and chosen is act_personal:
            self._set_personal(d_idx, p_idx, not self._is_personal(d_idx, p_idx))
            return
        if chosen is not None and chosen in (act_half_am, act_half_pm, act_half_clear):
            if chosen is act_half_clear:
                for p in range(self.periods):
                    self.personal_data[d_idx][p] = False
                    self.timeoff_data[d_idx][p] = 2
                    it = self.table.item(p, d_idx)
                    if it:
                        self._update_item_visuals(it, 2, d_idx, p)
                self._update_counters()
            else:
                # Yarım gün varsayılan olarak KURUM kısıtıdır: öğretmen o yarım
                # günü büyük ihtimalle başka şubede geçiriyor, orada müsait olmalı.
                self._apply_half_day(d_idx, first_half=(chosen is act_half_am),
                                     personal=False)
            return

        if act_toggle is None or chosen != act_toggle:
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
        # İki durumlu: açık <-> kapalı. Eskiden araya "? tercih edilmez" giriyordu
        # (2 -> 0 -> 1 -> 2), yani kapalı bir saati açmak için iki tıklama
        # gerekiyordu ve arada sarı bir durum kalıyordu. Kullanıcı bu durumu
        # istemiyor; tek tıklama artık durumu doğrudan tersine çeviriyor.
        new_state = 0 if current_state == 2 else 2

        # Açılan saat GERÇEKTEN açılır. Kişisel kısıt (sağ tık) ayrı bir
        # katmanda durur ve kurum matrisini ezer; eskiden sol tık yalnızca
        # kurum matrisini açıyor, kişisel katman kalıyordu — kullanıcı ✕'i
        # tıklıyor, hücre "✕ Kişisel" kalıyor, kayıtta saat kapalı çıkıyor ve
        # motor oraya ders koymuyordu. Şimdi açmak iki katmanı da açar.
        if new_state == 2:
            self.personal_data[col][row] = False
        self.timeoff_data[col][row] = new_state
        item = self.table.item(row, col)
        self._update_item_visuals(item, new_state, col, row)
        self._update_counters()

    def _toggle_column(self, col):
        # col = d_idx (toggle entire day)
        any_open = any(self.timeoff_data[col][p] > 0 for p in range(self.periods))
        new_st = 0 if any_open else 2
        for p in range(self.periods):
            if new_st == 2:
                self.personal_data[col][p] = False
            self.timeoff_data[col][p] = new_st
            item = self.table.item(p, col)
            if item: self._update_item_visuals(item, new_st, col, p)
        self._update_counters()

    def _toggle_row(self, row):
        # row = p_idx (toggle entire period)
        any_open = any(self.timeoff_data[d][row] > 0 for d in range(len(self.days)))
        new_st = 0 if any_open else 2
        for d in range(len(self.days)):
            if new_st == 2:
                self.personal_data[d][row] = False
            self.timeoff_data[d][row] = new_st
            item = self.table.item(row, d)
            if item: self._update_item_visuals(item, new_st, d, row)
        self._update_counters()

    def _make_all_open(self):
        for d in range(len(self.days)):
            for p in range(self.periods):
                self.personal_data[d][p] = False
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
        ent_name = (self.entity_dict.get("ad") or "").strip()

        # ÖN KONTROL: kaydetmeden önce "bu ayarla plan dolar mı?" diye sor.
        #
        # Öğretmenler kısıtlamayı kendi kafalarına göre giriyor ve sonuç ancak
        # otomatik planlayıcı çalıştığında ortaya çıkıyordu. Artık daha kaydet
        # anında, kaç saatin nerede açıkta kalacağı sayıyla söyleniyor ve devam
        # düğmesi 5 saniye kilitli kalıyor. Engellemiyoruz — sadece görmeden
        # geçilmesin diye.
        try:
            from dialogs.preflight_dialog import run_preflight
            probe = self._cs.candidate_store(
                self.data_store, self.entity_dict, ent_name,
                self.timeoff_data, self.personal_data)
            note = ""
            if self.is_teacher and not getattr(self, "independent", True):
                note = ("Bu saatleri BU kurum için kapattınız; öğretmen diğer "
                        "kurumlarda bu saatlerde müsait sayılmaya devam eder. "
                        "Hiçbir yerde olmadığı saatler için hücreye sağ tıklayıp "
                        "'Kişisel' işaretleyin.")
            if not run_preflight(probe, self.inst_slug, self, mode="save",
                                 extra_note=note):
                return
        except Exception as exc:
            print(f"[TIMEOFF_SAVE] ön kontrol atlandı: {exc}")

        # Tek yazma noktası: timeoff ve kisitlamalar birlikte, 3 durumlu olarak yazılır.
        self._cs.set_matrix(self.entity_dict, ent_name, self.data_store, self.timeoff_data)
        self._cs.set_personal(self.entity_dict, ent_name, self.data_store,
                              self.personal_data)
        # Müsaitlik meşru olarak değişti: koruma yeni hâli esas alsın.
        try:
            _w = self.parent()
            while _w is not None and not hasattr(_w, "mark_availability_authorized"):
                _w = _w.parent() if hasattr(_w, "parent") else None
            if _w is not None:
                _w.mark_availability_authorized()
        except Exception:
            pass

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
