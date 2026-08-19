import re

file_path = "/Users/fookay/ders program/dialogs/print_preview.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update _group_teacher_atamalar_by_subject to read both Turkish and English keys
old_group = """def _group_teacher_atamalar_by_subject(atamalar):
    grouped = {}
    for a in atamalar:
        subj = str(a.get("subject", "")).strip()
        if not subj:
            continue
        if subj not in grouped:
            grouped[subj] = {
                "subject": subj,
                "classes": [],
                "duration": 0,
                "types": [],
                "color": a.get("color"),
                "is_combined": False
            }
        cls_str = str(a.get("class", "")).strip()
        if a.get("is_combined") or "+" in cls_str:
            grouped[subj]["is_combined"] = True
            combs = a.get("combined_classes") or [c.strip() for c in cls_str.replace("&", "+").replace(",", "+").split("+") if c.strip()]
            for cc in combs:
                if cc and cc not in grouped[subj]["classes"]:
                    grouped[subj]["classes"].append(cc)
        else:
            if cls_str and cls_str not in grouped[subj]["classes"]:
                grouped[subj]["classes"].append(cls_str)
                
        dur_val = int(a.get("duration", 1)) if str(a.get("duration", 1)).isdigit() else 1
        grouped[subj]["duration"] += dur_val
        typ = str(a.get("type", "")).strip()
        if typ and typ not in grouped[subj]["types"]:
            grouped[subj]["types"].append(typ)"""

new_group = """def _group_teacher_atamalar_by_subject(atamalar):
    grouped = {}
    for a in atamalar:
        subj = str(a.get("ders") or a.get("subject", "")).strip()
        if not subj:
            continue
        if subj not in grouped:
            grouped[subj] = {
                "subject": subj,
                "classes": [],
                "duration": 0,
                "types": [],
                "color": a.get("renk") or a.get("color"),
                "is_combined": False
            }
        cls_str = str(a.get("sinif") or a.get("class", "")).strip()
        if a.get("is_combined") or "+" in cls_str or "," in cls_str or "&" in cls_str:
            grouped[subj]["is_combined"] = True
            combs = a.get("combined_classes") or [c.strip() for c in cls_str.replace("&", "+").replace(",", "+").split("+") if c.strip()]
            for cc in combs:
                if cc and cc not in grouped[subj]["classes"]:
                    grouped[subj]["classes"].append(cc)
        else:
            if cls_str and cls_str not in grouped[subj]["classes"]:
                grouped[subj]["classes"].append(cls_str)
                
        dur_raw = a.get("ders_sayisi") or a.get("duration", 1)
        dur_val = int(dur_raw) if str(dur_raw).isdigit() else 1
        grouped[subj]["duration"] += dur_val
        typ = str(a.get("dagilim") or a.get("type", "")).strip()
        if typ and typ not in grouped[subj]["types"]:
            grouped[subj]["types"].append(typ)"""

if old_group in content:
    content = content.replace(old_group, new_group)
    print("1. Replaced _group_teacher_atamalar_by_subject")
else:
    print("1. old_group not found directly")

# 2. Update _populate_targets to enable combo for all modes
old_pop_targets = """    def _populate_targets(self):
        mode = self.mode_combo.currentText()
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        
        is_teacher_mode = bool(
            self.filters.get("teachers") or 
            self.filters.get("entity_type") in ["teacher", "teachers_all"] or 
            "Öğretmen" in mode
        )
        
        if mode == "Sınıf Dersleri & Atama Listesi (Liste Formatı)":
            self.target_combo.setEnabled(True)
            if is_teacher_mode:
                self.target_combo.addItem("Tüm Öğretmenler (Çoklu Sayfa)")
                for t in self.filtered_teachers:
                    if t.get("ad"): self.target_combo.addItem(t.get("ad", ""))
            else:
                self.target_combo.addItem("Tüm Sınıflar (Çoklu Sayfa)")
                for c in self.filtered_classes:
                    if c.get("ad"): self.target_combo.addItem(c.get("ad", ""))
        elif "Tüm Sınıflar" in mode or "Tüm Öğretmenler" in mode or "Ders Yükü" in mode or "Tablo Olarak" in mode:
            self.target_combo.addItem("Tümü (Çoklu Sayfa)")
            self.target_combo.setEnabled(False)
        elif "Çarşaf Liste" in mode:
            self.target_combo.setEnabled(True)
            self.target_combo.addItem("Tümü (Çoklu Sayfa)")
            if is_teacher_mode:
                for t in self.filtered_teachers:
                    if t.get("ad"): self.target_combo.addItem(t.get("ad", ""))
            else:
                for c in self.filtered_classes:
                    if c.get("ad"): self.target_combo.addItem(c.get("ad", ""))
        elif is_teacher_mode:
            self.target_combo.setEnabled(True)
            self.target_combo.addItem("Tüm Öğretmenler (Çoklu Sayfa)")
            for t in self.filtered_teachers:
                if t.get("ad"): self.target_combo.addItem(t.get("ad", ""))
        else:
            self.target_combo.setEnabled(True)
            self.target_combo.addItem("Tüm Sınıflar (Çoklu Sayfa)")
            for c in self.filtered_classes:
                if c.get("ad"): self.target_combo.addItem(c.get("ad", ""))
                
        # If filters specified selected_items or default_selection, select it
        sel = self.filters.get("selected_items") or ([self.filters.get("default_selection")] if self.filters.get("default_selection") else [])
        if sel and len(sel) > 0 and sel[0]:
            idx = self.target_combo.findText(sel[0])
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
        else:
            # Default to 'Tüm' if no specific selection
            idx = self.target_combo.findText("Tüm Öğretmenler (Çoklu Sayfa)" if is_teacher_mode else "Tüm Sınıflar (Çoklu Sayfa)")
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
                
        self.target_combo.blockSignals(False)"""

new_pop_targets = """    def _populate_targets(self):
        mode = self.mode_combo.currentText()
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.setEnabled(True)
        
        is_teacher_mode = bool(
            self.filters.get("teachers") or 
            self.filters.get("entity_type") in ["teacher", "teachers_all"] or 
            "Öğretmen" in mode
        )
        
        teachers_list = [t.get("ad", "").strip() for t in (self.filtered_teachers or self.data_store.get("ogretmenler", [])) if t.get("ad")]
        teachers_list = sorted(list(set(teachers_list)))
        
        import re
        def natural_sort_key(s):
            m = re.match(r"(\d+)(.*)", str(s).strip())
            return (int(m.group(1)), m.group(2)) if m else (999, str(s))
            
        raw_classes = [c.get("ad", "").strip() for c in (self.filtered_classes or self.data_store.get("siniflar", [])) if c.get("ad")]
        classes_list = sorted(list(set(raw_classes)), key=natural_sort_key)
        
        if is_teacher_mode:
            self.target_combo.addItem("Tüm Öğretmenler (Çoklu Sayfa)")
            for t in teachers_list:
                self.target_combo.addItem(t)
        else:
            self.target_combo.addItem("Tüm Sınıflar (Çoklu Sayfa)")
            for c in classes_list:
                self.target_combo.addItem(c)
                
        # If filters specified selected_items or default_selection, select it
        sel = self.filters.get("selected_items") or ([self.filters.get("default_selection")] if self.filters.get("default_selection") else [])
        if sel and len(sel) > 0 and sel[0]:
            idx = self.target_combo.findText(sel[0])
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
        else:
            idx = self.target_combo.findText("Tüm Öğretmenler (Çoklu Sayfa)" if is_teacher_mode else "Tüm Sınıflar (Çoklu Sayfa)")
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
                
        self.target_combo.blockSignals(False)"""

if old_pop_targets in content:
    content = content.replace(old_pop_targets, new_pop_targets)
    print("2. Replaced _populate_targets")
else:
    print("2. old_pop_targets not found directly")

# 3. Update _paint to pass printer to _render_weekly_grid
old_paint_block = """        elif mode == "Sınıf Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)":
            self._render_weekly_grid(painter, VW, VH, is_teacher=False)
        elif mode == "Öğretmen Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)":
            self._render_weekly_grid(painter, VW, VH, is_teacher=True)
        elif mode == "Sınıf Dersleri & Atama Listesi (Liste Formatı)":
            self._render_class_lessons_list(painter, printer, VW, VH)
        elif mode == "Tüm Öğretmenlerin Ders Yükü Listesi":
            self._render_teacher_summary_list(painter, VW, VH)
        else:
            self._render_weekly_grid(painter, VW, VH, is_teacher=False)"""

new_paint_block = """        elif mode == "Sınıf Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)":
            self._render_weekly_grid(painter, printer, VW, VH, is_teacher=False)
        elif mode == "Öğretmen Haftalık Ders Programı (Tekil Çizelge - Tek Sayfa)":
            self._render_weekly_grid(painter, printer, VW, VH, is_teacher=True)
        elif mode == "Sınıf Dersleri & Atama Listesi (Liste Formatı)":
            self._render_class_lessons_list(painter, printer, VW, VH)
        elif mode == "Tüm Öğretmenlerin Ders Yükü Listesi":
            self._render_teacher_summary_list(painter, VW, VH)
        else:
            self._render_weekly_grid(painter, printer, VW, VH, is_teacher=False)"""

if old_paint_block in content:
    content = content.replace(old_paint_block, new_paint_block)
    print("3. Replaced _paint block")
else:
    print("3. old_paint_block not found directly")

# 4. Update _render_weekly_grid to handle both single and multi-page
old_weekly_grid = """    def _render_weekly_grid(self, painter, VW, VH, is_teacher=False):
        \"\"\"Single class or single teacher timetable on one page (Same exact layout as photo)\"\"\"
        target_name = self.target_combo.currentText() or ("Öğretmen" if is_teacher else "Sınıf")
        school_name = self.data_store.get("okul_adi") or self.data_store.get("settings", {}).get("school_name", "Özel Öğretim Kurumu")
        placements = self._get_pseudo_placements(target_name, is_teacher)
        
        margin_x = 35
        margin_y = 25
        grid_w = VW - (2 * margin_x)
        grid_h = VH - (2 * margin_y)
        
        self._draw_mini_grid(painter, margin_x, margin_y, grid_w, grid_h, target_name, school_name, placements, is_teacher=is_teacher, is_single_page=True)"""

new_weekly_grid = """    def _render_weekly_grid(self, painter, printer, VW, VH, is_teacher=False):
        \"\"\"Single class or single teacher timetable on one page (Same exact layout as photo)\"\"\"
        import re
        def natural_sort_key(s):
            m = re.match(r"(\d+)(.*)", str(s).strip())
            return (int(m.group(1)), m.group(2)) if m else (999, str(s))
            
        sel_target = self.target_combo.currentText().strip()
        school_name = self.data_store.get("okul_adi") or self.data_store.get("settings", {}).get("school_name", "Özel Öğretim Kurumu")
        
        if is_teacher:
            all_items = sorted([t.get("ad", "Öğretmen") for t in (self.filtered_teachers if self.filtered_teachers else self.data_store.get("ogretmenler", [])) if t.get("ad")])
        else:
            all_items = sorted([c.get("ad", "Sınıf") for c in (self.filtered_classes if self.filtered_classes else self.data_store.get("siniflar", [])) if c.get("ad")], key=natural_sort_key)
            
        if sel_target and "Çoklu Sayfa" not in sel_target and sel_target != "Tümü" and not sel_target.startswith("Tüm "):
            items = [sel_target]
        else:
            items = all_items
            
        if not items:
            items = ["Örnek 1"]
            
        margin_x = 35
        margin_y = 25
        grid_w = VW - (2 * margin_x)
        grid_h = VH - (2 * margin_y)
        
        for i, item_name in enumerate(items):
            if i > 0:
                printer.newPage()
                painter.fillRect(0, 0, VW, VH, Qt.white)
            placements = self._get_pseudo_placements(item_name, is_teacher)
            self._draw_mini_grid(painter, margin_x, margin_y, grid_w, grid_h, item_name, school_name, placements, is_teacher=is_teacher, is_single_page=True)"""

if old_weekly_grid in content:
    content = content.replace(old_weekly_grid, new_weekly_grid)
    print("4. Replaced _render_weekly_grid")
else:
    print("4. old_weekly_grid not found directly")

# 5. Fix raw_atamalar filters across print_preview.py to support both Turkish and English keys
content = content.replace(
    'raw_teacher_atamalar = [a for a in raw_atamalar if a.get("teacher") == ent_name or format_tr_name(a.get("teacher", "")) == format_tr_name(ent_name)]',
    'raw_teacher_atamalar = [a for a in raw_atamalar if (a.get("ogretmen") or a.get("teacher")) == ent_name or format_tr_name(a.get("ogretmen") or a.get("teacher", "")) == format_tr_name(ent_name)]'
)

content = content.replace(
    'atamalar = [a for a in raw_atamalar if matches_class(a.get("class", ""), ent_name) or (a.get("is_combined") and any(matches_class(cc, ent_name) for cc in a.get("combined_classes", [])))]',
    'atamalar = [a for a in raw_atamalar if matches_class(a.get("sinif") or a.get("class", ""), ent_name) or (a.get("is_combined") and any(matches_class(cc, ent_name) for cc in a.get("combined_classes", [])))]'
)

content = content.replace(
    'raw_t_atamalar = [a for a in raw_atamalar if a.get("teacher") == selected_teacher or format_tr_name(a.get("teacher", "")) == format_tr_name(selected_teacher)]',
    'raw_t_atamalar = [a for a in raw_atamalar if (a.get("ogretmen") or a.get("teacher")) == selected_teacher or format_tr_name(a.get("ogretmen") or a.get("teacher", "")) == format_tr_name(selected_teacher)]'
)

content = content.replace(
    'atamalar = [a for a in raw_atamalar if matches_class(a.get("class", ""), selected_class) or (a.get("is_combined") and any(matches_class(cc, selected_class) for cc in a.get("combined_classes", [])))]',
    'atamalar = [a for a in raw_atamalar if matches_class(a.get("sinif") or a.get("class", ""), selected_class) or (a.get("is_combined") and any(matches_class(cc, selected_class) for cc in a.get("combined_classes", [])))]'
)

content = content.replace(
    't_atamalar = [a for a in atamalar if a.get("teacher") == tname]',
    't_atamalar = [a for a in atamalar if format_tr_name(a.get("ogretmen") or a.get("teacher", "")) == format_tr_name(tname)]'
)

content = content.replace(
    'subs_str = ", ".join(list({a.get("subject", "") for a in t_atamalar})) or "—"',
    'subs_str = ", ".join(list({(a.get("ders") or a.get("subject", "")) for a in t_atamalar if (a.get("ders") or a.get("subject"))})) or "—"'
)

content = content.replace(
    'tot_hours = sum(a.get("duration", 1) for a in t_atamalar)',
    'tot_hours = sum(int(a.get("ders_sayisi") or a.get("duration", 1)) for a in t_atamalar if str(a.get("ders_sayisi") or a.get("duration", 1)).isdigit())'
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Finished patching print_preview.py")
