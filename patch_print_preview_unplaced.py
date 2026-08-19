import os

file_path = "/Users/fookay/ders program/dialogs/print_preview.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# At the end of _draw_mini_grid, draw unplaced lessons.
# Let's find the end of the method
search_str = """        # Optional: Print Legend at bottom
        painter.setFont(make_font(7, False))
        painter.setPen(QPen(QColor("#64748B"), 1))
        painter.drawText(QRectF(grid_x, ry + row_h + 5, tbl_w, 15), Qt.AlignLeft, f"{school_name} - {acad_year} - {date_str}")"""

replacement_str = """        # 6. Unplaced Lessons calculation
        from auto_scheduler import normalize_clean
        target_norm = normalize_clean(target_name)
        total_hours_assigned = 0
        total_hours_placed = 0
        unplaced_subjects = {} # dict of subject -> unplaced hours

        # Calculate assigned hours from atamalar
        for atama in self.data_store.get("atamalar", []):
            s_name = (atama.get("ders") or "").strip()
            t_name = (atama.get("ogretmen") or "").strip()
            c_name = (atama.get("sinif") or "").strip()
            h_count = int(atama.get("ders_sayisi", 0))
            if h_count <= 0: continue
            
            match = False
            if is_teacher and normalize_clean(t_name) == target_norm: match = True
            elif not is_teacher and normalize_clean(c_name) == target_norm: match = True
                
            if match:
                unplaced_subjects[s_name] = unplaced_subjects.get(s_name, 0) + h_count
                total_hours_assigned += h_count

        # Subtract placed hours
        placed_slots = set()
        for p in self.data_store.get("grid_placements", []):
            dur = int(p.get("duration", 1))
            if dur <= 0: continue
            day = int(p.get("day", -1))
            period = int(p.get("period", -1))
            # Only count actually placed ones (not dummy ones with negative coords)
            if day < 0 or period < 0: continue
            
            p_s = (p.get("subject_name") or p.get("subject") or "").strip()
            p_t = (p.get("teacher_name") or p.get("teacher") or "").strip()
            p_c = (p.get("class_name") or p.get("class") or "").strip()
            
            match = False
            if is_teacher and normalize_clean(p_t) == target_norm: match = True
            elif not is_teacher and normalize_clean(p_c) == target_norm: match = True
            
            if match:
                for off in range(dur):
                    slot = (day, period + off, p_s, p_t, p_c)
                    if slot not in placed_slots:
                        placed_slots.add(slot)
                        if p_s in unplaced_subjects:
                            unplaced_subjects[p_s] -= 1
                            total_hours_placed += 1

        unplaced_texts = []
        for s, count in unplaced_subjects.items():
            if count > 0:
                unplaced_texts.append(f"{s} ({count} Saat)")

        unplaced_text = ""
        if unplaced_texts:
            unplaced_text = "DİKKAT: Atanmayan (Çizelgeye Yerleşmeyen) Dersler: " + ", ".join(unplaced_texts)
            painter.setFont(make_font(10 if is_single_page else 6, True))
            painter.setPen(QPen(QColor("#DC2626"), 1)) # Red warning
            painter.drawText(QRectF(grid_x, ry + row_h + 3, tbl_w, 20), Qt.AlignLeft | Qt.AlignVCenter, unplaced_text)

        # Optional: Print Legend at bottom
        painter.setFont(make_font(7, False))
        painter.setPen(QPen(QColor("#64748B"), 1))
        offset_y = 25 if unplaced_texts else 5
        painter.drawText(QRectF(grid_x, ry + row_h + offset_y, tbl_w, 15), Qt.AlignLeft, f"{school_name} - {acad_year} - {date_str}")"""

content = content.replace(search_str, replacement_str)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied for displaying unplaced lessons.")
