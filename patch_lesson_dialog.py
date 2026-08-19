import os

file_path = "/Users/fookay/ders program/dialogs/edit_forms.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update get_data in LessonAssignmentDialog to save with Turkish keys
old_get_data = """                assignments.append({
                    "teacher": teacher_name,
                    "subject": subj,
                    "class": comb_str,
                    "duration": duration,
                    "type": type_val,
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
                        "teacher": teacher_name,
                        "subject": subj,
                        "class": c_name,
                        "duration": duration,
                        "type": type_val,
                        "color": get_subject_color(subj),
                        "is_combined": False,
                        "combined_classes": []
                    })
                    
        return assignments"""

new_get_data = """                assignments.append({
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
                    })
                    
        return assignments"""

content = content.replace(old_get_data, new_get_data)

# 2. Fix accept() to remove old assignments properly
old_accept = """            # Remove old assignments for this teacher
            self.data_store["atamalar"] = [
                a for a in self.data_store["atamalar"]
                if format_tr_name(a.get("teacher", "")) != teacher_name
            ]
            
            # Add new assignments
            self.data_store["atamalar"].extend(new_data)
            
            # Clean up grid placements, auto_schedule_results, and yerlesim for removed assignments
            active_tuples = {
                (format_tr_name(a.get("subject", "")), format_tr_name(a.get("class", "")), teacher_name)
                for a in new_data
            }"""

new_accept = """            # Remove old assignments for this teacher
            self.data_store["atamalar"] = [
                a for a in self.data_store["atamalar"]
                if format_tr_name(a.get("ogretmen") or a.get("teacher", "")) != teacher_name
            ]
            
            # Add new assignments
            self.data_store["atamalar"].extend(new_data)
            
            # Clean up grid placements, auto_schedule_results, and yerlesim for removed assignments
            active_tuples = {
                (format_tr_name(a.get("ders") or a.get("subject", "")), format_tr_name(a.get("sinif") or a.get("class", "")), teacher_name)
                for a in new_data
            }"""

content = content.replace(old_accept, new_accept)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Patched LessonAssignmentDialog")
