import sys, os

file1 = "/Users/fookay/ders program/auto_scheduler.py"
with open(file1, "r", encoding="utf-8") as f:
    content1 = f.read()

target1 = """            class_assigned_hours = sum(b.get("duration", 1) for b in candidate_blocks)
            total_target_hours += (class_assigned_hours + len(occupied_slots))

            if not candidate_blocks:
                continue"""

replace1 = """            class_assigned_hours = sum(b.get("duration", 1) for b in candidate_blocks)
            total_target_hours += (class_assigned_hours + len(occupied_slots))

            # --- DUMMY BLOCK INJECTION ---
            if candidate_blocks:
                deficit = total_class_slots - (class_assigned_hours + len(occupied_slots))
                if deficit > 0:
                    import random
                    base_blocks = list(candidate_blocks)
                    while deficit > 0:
                        chosen = dict(random.choice(base_blocks))
                        chosen_dur = min(chosen.get("duration", 1), deficit)
                        chosen["duration"] = chosen_dur
                        candidate_blocks.append(chosen)
                        deficit -= chosen_dur
                        total_target_hours += chosen_dur
            # -----------------------------

            if not candidate_blocks:
                continue"""
content1 = content1.replace(target1, replace1)
with open(file1, "w", encoding="utf-8") as f:
    f.write(content1)


file2 = "/Users/fookay/ders program/main_window.py"
with open(file2, "r", encoding="utf-8") as f:
    content2 = f.read()

target2 = """                    })
                    
        has_assignments = bool(scoped_atamalar) if target_entity else bool(atamalar)
        self._grid.unplaced_dock.load_unplaced("""

replace2 = """                    })
                    
        # --- DUMMY INJECTION FOR DOCK ---
        if target_entity and scoped_atamalar:
            settings = self.data_store.get("settings", {})
            d_len = len(settings.get("days", [])) or int(settings.get("day_count", self.data_store.get("gun_sayisi", 5)))
            p_len = int(settings.get("periods", self.data_store.get("ders_saati", 8)))
            total_slots = d_len * p_len
            
            placed_for_target = 0
            for p in grid_placements:
                dur = int(p.get("duration", 1))
                if dur <= 0: continue
                p_c = (p.get("class_name") or p.get("class") or "").strip()
                p_t = format_tr_name(p.get("teacher_name") or p.get("teacher") or "")
                
                match = False
                if display_mode == "classes":
                    from auto_scheduler import matches_class
                    if matches_class(target_entity, p_c) or matches_class(p_c, target_entity):
                        match = True
                    elif p.get("combined_classes"):
                        if any(matches_class(target_entity, x) for x in p["combined_classes"]):
                            match = True
                    elif "+" in p_c or "&" in p_c or "," in p_c:
                        if any(matches_class(target_entity, x.strip()) for x in p_c.replace("&", "+").replace(",", "+").split("+")):
                            match = True
                else:
                    if _matches_teacher(p_t, target_entity) or p_t == format_tr_name(target_entity):
                        match = True
                        
                if match:
                    placed_for_target += dur
                    
            deficit = total_slots - placed_for_target
            if deficit > 0:
                import random
                import uuid
                base_atamalar = list(scoped_atamalar)
                while deficit > 0:
                    chosen = random.choice(base_atamalar)
                    c_name = chosen.get("class", "")
                    t_name = chosen.get("teacher", "")
                    s_name = chosen.get("subject", "")
                    is_comb = bool(chosen.get("is_combined") or ("+" in c_name or "&" in c_name or "," in c_name))
                    t_classes = chosen.get("combined_classes", [])
                    if not t_classes and is_comb:
                        t_classes = [x.strip() for x in c_name.replace("&", "+").replace(",", "+").split("+") if x.strip()]
                    elif not t_classes:
                        t_classes = [c_name]
                    color = resolve_subject_color(s_name, self.data_store)
                    dur = 1
                    unplaced.append({
                        "id": f"dummy_{uuid.uuid4().hex[:8]}",
                        "subject_name": s_name,
                        "color": color,
                        "teacher": t_name,
                        "class_name": c_name,
                        "duration": dur,
                        "is_combined": is_comb,
                        "combined_classes": t_classes
                    })
                    deficit -= dur
        # --------------------------------

        has_assignments = bool(scoped_atamalar) if target_entity else bool(atamalar)
        self._grid.unplaced_dock.load_unplaced("""
content2 = content2.replace(target2, replace2)
with open(file2, "w", encoding="utf-8") as f:
    f.write(content2)

print("Patch applied successfully.")
