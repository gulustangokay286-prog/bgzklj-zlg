import re

file_path = "/Users/fookay/ders program/dialogs/edit_forms.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update LessonAssignmentDialog.get_data to save both Turkish and English keys
old_lad_data = """                assignments.append({
                    "ogretmen": teacher_name,
                    "ders": subj,
                    "sinif": comb_str,
                    "ders_sayisi": duration,
                    "dagilim": type_val,
                    "renk": get_subject_color(subj),
                    "is_combined": True,
                    "combined_classes": list(comb_classes)
                })
            else:
                assigned_classes = r["classes"]
                if not assigned_classes:
                    QMessageBox.warning(self, "Eksik Sınıf Seçimi", f"Lütfen '{subj}' dersi için en az bir sınıf seçiniz!")
                    return None
                for c_name in assigned_classes:
                    cfg = r.get("class_configs", {}).get(c_name, {})
                    type_val = cfg.get("type", default_type_val)
                    if "+" in type_val:
                        parts = [int(p.strip()) for p in type_val.split("+") if p.strip().isdigit()]
                        duration = sum(parts) if parts else 2
                    else:
                        duration = int(type_val) if type_val.isdigit() else 2
                        
                    assignments.append({
                        "ogretmen": teacher_name,
                        "ders": subj,
                        "sinif": c_name,
                        "ders_sayisi": duration,
                        "dagilim": type_val,
                        "renk": get_subject_color(subj),
                        "is_combined": False,
                        "combined_classes": []
                    })"""

new_lad_data = """                assignments.append({
                    "ogretmen": teacher_name,
                    "teacher": teacher_name,
                    "ders": subj,
                    "subject": subj,
                    "sinif": comb_str,
                    "class": comb_str,
                    "ders_sayisi": duration,
                    "duration": duration,
                    "dagilim": type_val,
                    "type": type_val,
                    "renk": get_subject_color(subj),
                    "color": get_subject_color(subj),
                    "is_combined": True,
                    "combined_classes": list(comb_classes)
                })
            else:
                assigned_classes = r["classes"]
                if not assigned_classes:
                    QMessageBox.warning(self, "Eksik Sınıf Seçimi", f"Lütfen '{subj}' dersi için en az bir sınıf seçiniz!")
                    return None
                for c_name in assigned_classes:
                    cfg = r.get("class_configs", {}).get(c_name, {})
                    type_val = cfg.get("type", default_type_val)
                    if "+" in type_val:
                        parts = [int(p.strip()) for p in type_val.split("+") if p.strip().isdigit()]
                        duration = sum(parts) if parts else 2
                    else:
                        duration = int(type_val) if type_val.isdigit() else 2
                        
                    assignments.append({
                        "ogretmen": teacher_name,
                        "teacher": teacher_name,
                        "ders": subj,
                        "subject": subj,
                        "sinif": c_name,
                        "class": c_name,
                        "ders_sayisi": duration,
                        "duration": duration,
                        "dagilim": type_val,
                        "type": type_val,
                        "renk": get_subject_color(subj),
                        "color": get_subject_color(subj),
                        "is_combined": False,
                        "combined_classes": []
                    })"""

if old_lad_data in content:
    content = content.replace(old_lad_data, new_lad_data)
    print("1. Replaced LessonAssignmentDialog.get_data")
else:
    print("1. old_lad_data not found directly")

# 2. Update OgretmenEditDialog._build_ui assignments list rendering and _assign_lessons_for_this_teacher
old_ogretmen_block = """        atamalar = data_store.get("atamalar", [])
        my_name = self.existing_data.get("ad", "")
        my_atamalar = [a for a in atamalar if format_tr_name(a.get("ogretmen") or a.get("teacher", "")) == format_tr_name(my_name)]
        my_subjects = list({(a.get("ders") or a.get("subject", "")) for a in my_atamalar if (a.get("ders") or a.get("subject"))})
        
        for a in my_atamalar:
            s_name = a.get("ders") or a.get("subject", "")
            c_name = a.get("sinif") or a.get("class", "")
            dur = a.get("ders_sayisi") or a.get("duration", 0)
            item_text = f"• {s_name}  →  {c_name} ({dur} Saat)"
            item = QListWidgetItem(item_text)
            self.list_assignments.addItem(item)
        if not my_atamalar:
            self.list_assignments.addItem(QListWidgetItem("Henüz hiçbir derse veya sınıfa atanmadı."))
            
        lay_ders.addWidget(self.list_assignments)"""

new_ogretmen_block = """        lay_ders.addWidget(self.list_assignments)
        self._update_assignments_list(data_store)"""

if old_ogretmen_block in content:
    content = content.replace(old_ogretmen_block, new_ogretmen_block)
    print("2. Replaced OgretmenEditDialog list rendering in _build_ui")
else:
    print("2. old_ogretmen_block not found directly")

# 3. Replace _assign_lessons_for_this_teacher and add _update_assignments_list
old_assign_method = """    def _assign_lessons_for_this_teacher(self):
        t_name = self.w_ad.text().strip()
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        d = LessonAssignmentDialog(data_store=data_store, parent=p or self, selected_teacher=t_name)
        if d.exec():
            data = d.get_data()
            if "atamalar" not in data_store:
                data_store["atamalar"] = []
            
            # Remove old assignments for this teacher
            current_teacher = format_tr_name(d.cb_ogretmen.currentText())
            data_store["atamalar"] = [
                a for a in data_store["atamalar"] 
                if format_tr_name(a.get("teacher", "")) != current_teacher
            ]
            
            # Add new ones
            if isinstance(data, list):
                data_store["atamalar"].extend(data)
            else:
                data_store["atamalar"].append(data)
                
            trigger_save_db(self, data_store)
            if hasattr(p, "save_db"): p.save_db()
            if hasattr(p, "_refresh_tree"): p._refresh_tree()
            if hasattr(p, "_refresh_unplaced_lessons"): p._refresh_unplaced_lessons()
            if hasattr(p, "_restore_grid_placements"): p._restore_grid_placements()
            if hasattr(p, "_refresh_grid"): p._refresh_grid()
            
            # Update local UI list
            self.list_assignments.clear()
            my_atamalar = [a for a in data_store["atamalar"] if format_tr_name(a.get("teacher", "")) == current_teacher]
            for a in my_atamalar:
                item_text = f"📚 {a.get('subject', '')} ➔ 🎓 {a.get('class', '')} ({a.get('duration', 0)} Saat)"
                self.list_assignments.addItem(QListWidgetItem(item_text))
            if not my_atamalar:
                self.list_assignments.addItem(QListWidgetItem("❌ Henüz hiçbir derse veya sınıfa atanmadı."))"""

new_assign_method = """    def _update_assignments_list(self, data_store=None):
        if data_store is None:
            p = self.parent()
            data_store = getattr(p, "data_store", {}) if p else {}
            if not data_store and hasattr(p, "main_window"):
                data_store = getattr(p.main_window, "data_store", {})
        
        self.list_assignments.clear()
        atamalar = data_store.get("atamalar", [])
        my_name = self.w_ad.text().strip() or self.existing_data.get("ad", "").strip()
        my_norm = format_tr_name(my_name)
        
        my_atamalar = [
            a for a in atamalar 
            if format_tr_name(a.get("ogretmen") or a.get("teacher") or "") == my_norm
        ]
        
        for a in my_atamalar:
            s_name = a.get("ders") or a.get("subject", "")
            c_name = a.get("sinif") or a.get("class", "")
            dur = a.get("ders_sayisi") or a.get("duration", 0)
            tip = a.get("dagilim") or a.get("type", str(dur))
            item_text = f"📚 {s_name}  ➔  🎓 {c_name} ({dur} Saat: {tip})"
            self.list_assignments.addItem(QListWidgetItem(item_text))
            
        if not my_atamalar:
            self.list_assignments.addItem(QListWidgetItem("❌ Henüz hiçbir derse veya sınıfa atanmadı."))

    def _assign_lessons_for_this_teacher(self):
        t_name = self.w_ad.text().strip() or self.existing_data.get("ad", "").strip()
        p = self.parent()
        data_store = getattr(p, "data_store", {}) if p else {}
        if not data_store and hasattr(p, "main_window"):
            data_store = getattr(p.main_window, "data_store", {})
        d = LessonAssignmentDialog(data_store=data_store, parent=p or self, selected_teacher=t_name)
        if d.exec():
            trigger_save_db(self, data_store)
            if hasattr(p, "save_db"): p.save_db()
            if hasattr(p, "_refresh_tree"): p._refresh_tree()
            if hasattr(p, "_refresh_unplaced_lessons"): p._refresh_unplaced_lessons()
            if hasattr(p, "_restore_grid_placements"): p._restore_grid_placements()
            if hasattr(p, "_refresh_grid"): p._refresh_grid()
            
            # Update local UI list
            self._update_assignments_list(data_store)"""

if old_assign_method in content:
    content = content.replace(old_assign_method, new_assign_method)
    print("3. Replaced _assign_lessons_for_this_teacher and added _update_assignments_list")
else:
    print("3. old_assign_method not found directly")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Finished patching edit_forms.py")
