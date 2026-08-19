import random
import time
import re
import uuid as _uuid
from PySide6.QtCore import QThread, Signal

def normalize_class_name(cls_name: str) -> str:
    if not cls_name:
        return ""
    s = str(cls_name).strip().upper().replace(" ", "")
    s = s.replace("-", "/").replace("\\", "/")
    return s

def normalize_clean(s: str) -> str:
    if not s: return ""
    tr_map = str.maketrans({'İ': 'i', 'I': 'ı', 'ı': 'i', 'Ş': 's', 'ş': 's', 'Ğ': 'g', 'ğ': 'g', 'Ü': 'u', 'ü': 'u', 'Ö': 'o', 'ö': 'o', 'Ç': 'c', 'ç': 'c'})
    return "".join(c for c in str(s).translate(tr_map).lower() if c.isalnum())

def matches_class(asgn_class_str: str, target_cn: str) -> bool:
    if not asgn_class_str or not target_cn:
        return False
    norm_target = normalize_class_name(target_cn)
    norm_asgn = normalize_class_name(asgn_class_str)
    if norm_asgn == norm_target:
        return True
        
    target_has_paren = "(" in norm_target and ")" in norm_target
    asgn_has_paren = "(" in norm_asgn and ")" in norm_asgn
    
    clean_target = norm_target.split("(")[0].strip()
    clean_asgn = norm_asgn.split("(")[0].strip()
    
    if target_has_paren and asgn_has_paren:
        if norm_asgn == norm_target:
            return True
    elif clean_target and clean_asgn and clean_target == clean_asgn:
        return True
        
    for part in str(asgn_class_str).replace("&", ",").replace("+", ",").split(","):
        p_norm = normalize_class_name(part)
        if p_norm == norm_target:
            return True
        p_has_paren = "(" in p_norm and ")" in p_norm
        p_clean = p_norm.split("(")[0].strip()
        if target_has_paren and p_has_paren:
            if p_norm == norm_target:
                return True
        elif clean_target and p_clean and p_clean == clean_target:
            return True
    return False

def format_tr_name(name_str: str) -> str:
    if not name_str: return ""
    return " ".join(w.capitalize() for w in str(name_str).strip().split())

def parse_distribution_parts(type_str: str, total_duration: int = 0) -> list:
    """
    Parses aSc distribution strings into list of block durations (cards).
    Rules:
    - '2+2+1' -> [2, 2, 1]
    - '2+2' -> [2, 2]
    - '2+1' -> [2, 1]
    - '3+1' -> [3, 1]
    - '3+2' -> [3, 2]
    - '4+2' -> [4, 2]
    - '1+1' -> [1, 1]
    - '2' -> [2]
    - '1' -> [1]
    - '3' -> [2, 1]
    - '4' -> [2, 2]
    - '5' -> [2, 2, 1]
    - '6' -> [2, 2, 2]
    """
    type_str = str(type_str or "").strip()
    parts = []
    
    if "+" in type_str:
        raw_parts = [p.strip() for p in type_str.split("+") if p.strip().isdigit()]
        for p in raw_parts:
            val = int(p)
            if val > 0:
                parts.append(val)
    elif type_str.isdigit() and int(type_str) > 0:
        val = int(type_str)
        rem = val
        while rem > 0:
            b = 2 if rem >= 2 else 1
            parts.append(b)
            rem -= b
            
    if not parts and total_duration > 0:
        rem = total_duration
        while rem > 0:
            b = 2 if rem >= 2 else 1
            parts.append(b)
            rem -= b
            
    return parts or ([total_duration] if total_duration > 0 else [2])

class AutoSchedulerWorker(QThread):
    progress_updated = Signal(int, int) # placed_hours, total_hours
    finished_successfully = Signal(dict) # Returns results dict
    failed = Signal(str)

    def __init__(self, data_store, target_class=None, parent=None, fill_empty=False, institution_slug=None):
        super().__init__(parent)
        self.data_store = data_store
        self.target_class = target_class if target_class and str(target_class).strip() and "Tüm" not in str(target_class) else None
        self.fill_empty = fill_empty
        self.institution_slug = institution_slug or (self.data_store.get("settings", {}).get("institution_slug", None) if isinstance(self.data_store, dict) else None)
        self._is_running = True

    def run(self):
        settings = self.data_store.get("settings", {})
        days = settings.get("days")
        if not days:
            cnt = int(settings.get("day_count", self.data_store.get("gun_sayisi", 5)))
            all_days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
            days = all_days[:cnt]
        periods = int(settings.get("periods", self.data_store.get("ders_saati", 8)))
        
        assignments = self.data_store.get("atamalar", [])
        if not assignments:
            self.failed.emit("Herhangi bir ders ataması bulunamadı.")
            return

        grid_placements = self.data_store.get("grid_placements", [])

        # Sınıfları listele
        all_class_names = []
        for c in self.data_store.get("siniflar", []):
            cn = c.get("ad", "").strip()
            if cn and cn not in all_class_names:
                all_class_names.append(cn)
                
        assigned_class_names = set()
        for asgn in assignments:
            raw_c = (asgn.get("class") or asgn.get("sinif") or asgn.get("class_name") or "").strip()
            if raw_c:
                for p_c in raw_c.replace("&", ",").replace("+", ",").split(","):
                    p_clean = p_c.strip()
                    if p_clean:
                        assigned_class_names.add(p_clean)
                        for full_c in all_class_names:
                            if matches_class(full_c, p_clean):
                                assigned_class_names.add(full_c)

        if self.target_class:
            matched_targets = [c for c in all_class_names if matches_class(c, self.target_class)]
            classes_to_schedule = matched_targets if matched_targets else [self.target_class]
        else:
            classes_to_schedule = [c for c in all_class_names if any(matches_class(c, ac) or matches_class(ac, c) for ac in assigned_class_names)]
            if not classes_to_schedule and assigned_class_names:
                classes_to_schedule = list(assigned_class_names)
            if not classes_to_schedule:
                classes_to_schedule = all_class_names

        other_classes_placements = []
        target_class_manual = []
        global_teacher_occupied = set() # (teacher_name, day, period)

        for p in grid_placements:
            c_name = (p.get("class_name") or p.get("class") or p.get("sinif") or "").strip()
            t_name = format_tr_name(p.get("teacher_name") or p.get("teacher") or p.get("ogretmen") or "")
            subj = p.get("subject_name") or p.get("subject") or p.get("ders") or ""
            dur = int(p.get("duration", 1))
            if "day" in p and "period" in p:
                day = int(p["day"])
                period = int(p["period"])
            elif "day_idx" in p and "period" in p:
                day = int(p["day_idx"])
                period = int(p["period"])
            elif "col" in p and "row" in p:
                col_val = int(p["col"])
                row_val = int(p["row"])
                if col_val >= len(days):
                    day = col_val // periods if periods > 0 else 0
                    period = col_val % periods if periods > 0 else 0
                else:
                    day = col_val
                    period = row_val
            else:
                day = int(p.get("day", p.get("col", 0)))
                period = int(p.get("period", p.get("row", 0)))

            if not c_name and t_name and subj:
                for asgn in assignments:
                    a_t_name = format_tr_name(asgn.get("teacher") or asgn.get("ogretmen") or asgn.get("teacher_name") or "")
                    a_subj = asgn.get("subject") or asgn.get("ders") or asgn.get("subject_name") or ""
                    if a_t_name == t_name and a_subj == subj:
                        c_name = (asgn.get("class") or asgn.get("sinif") or asgn.get("class_name") or "").strip()
                        if c_name: break

            is_locked = bool(p.get("locked") in [True, "true", "True", 1, "1"] or p.get("is_manual"))
            if any(matches_class(c_name, tgt) for tgt in classes_to_schedule):
                if is_locked:
                    target_class_manual.append({
                        "class_name": c_name, "teacher_name": t_name,
                        "subject_name": subj, "day_idx": day, "period": period,
                        "duration": dur, "is_manual": True, "locked": True
                    })
                    for off in range(dur):
                        if t_name:
                            global_teacher_occupied.add((t_name, day, period + off))
                            global_teacher_occupied.add((normalize_clean(t_name), day, period + off))
                            global_teacher_occupied.add((format_tr_name(t_name), day, period + off))
            else:
                other_classes_placements.append(p)
                for off in range(dur):
                    if t_name:
                        global_teacher_occupied.add((t_name, day, period + off))
                        global_teacher_occupied.add((normalize_clean(t_name), day, period + off))
                        global_teacher_occupied.add((format_tr_name(t_name), day, period + off))

        # Çapraz Kurum Öğretmen Meşguliyetleri
        cross_busy = {}
        try:
            import version_store
            current_slug = self.institution_slug or self.data_store.get("settings", {}).get("institution_slug", None)
            if current_slug:
                cross_busy = version_store.get_cross_institution_teacher_busy_slots(exclude_slug=current_slug)
                for (t_norm, d, p_slot), conflict_info in cross_busy.items():
                    global_teacher_occupied.add((t_norm, d, p_slot))
                    t_raw = conflict_info.get("teacher_name", "")
                    if t_raw:
                        global_teacher_occupied.add((t_raw, d, p_slot))
                        global_teacher_occupied.add((format_tr_name(t_raw), d, p_slot))
                        global_teacher_occupied.add((normalize_clean(t_raw), d, p_slot))
        except Exception as e:
            print(f"[AUTO_SCHEDULER] Cross-institution busy load notice: {e}")

        kisitlamalar_store = dict(self.data_store.get("kisitlamalar", {}))
        try:
            from version_store import load_global_kisitlamalar
            global_k = load_global_kisitlamalar()
            inst_slug = self.institution_slug or "varsayilan_kurum"
            for slug, k_data in global_k.items():
                if slug != inst_slug and isinstance(k_data, dict):
                    for entity_name, timeoff in k_data.items():
                        if entity_name not in kisitlamalar_store:
                            kisitlamalar_store[entity_name] = {}
                        if isinstance(timeoff, dict):
                            for k, v in timeoff.items():
                                if not v:
                                    kisitlamalar_store[entity_name][k] = False
        except Exception as e:
            print("AutoScheduler global constraints merge error:", e)

        t_toff_dict = {}
        for t in self.data_store.get("ogretmenler", []):
            t_ad = t.get("ad", "")
            if not t_ad: continue
            toff = t.get("timeoff", [])
            t_kisit = kisitlamalar_store.get(t_ad) or kisitlamalar_store.get(format_tr_name(t_ad)) or kisitlamalar_store.get(normalize_clean(t_ad))
            if t_kisit:
                new_toff = []
                for d_idx in range(len(days)):
                    row_toff = []
                    for p_idx in range(periods):
                        cell_k = f"{d_idx},{p_idx}"
                        if cell_k in t_kisit:
                            row_toff.append(2 if t_kisit[cell_k] else 0)
                        elif toff and d_idx < len(toff) and p_idx < len(toff[d_idx]):
                            row_toff.append(toff[d_idx][p_idx])
                        else:
                            row_toff.append(2)
                    new_toff.append(row_toff)
                toff = new_toff
                
            if toff:
                t_toff_dict[normalize_clean(t_ad)] = toff
                t_toff_dict[format_tr_name(t_ad)] = toff
                t_toff_dict[t_ad] = toff
                
        constraints = self.data_store.get("constraints", {})

        fully_blocked_teachers = set()
        for t_name, toff in t_toff_dict.items():
            if toff:
                all_blocked = all(
                    (d_idx < len(toff) and p_idx < len(toff[d_idx]) and toff[d_idx][p_idx] == 0)
                    for d_idx in range(len(days))
                    for p_idx in range(periods)
                )
                if all_blocked:
                    fully_blocked_teachers.add(t_name)
                    fully_blocked_teachers.add(format_tr_name(t_name))
                    fully_blocked_teachers.add(normalize_clean(t_name))

        relations = [r for r in self.data_store.get("planlama_iliskileri", []) if r.get("aktif", True)]

        total_scheduled_placements = list(other_classes_placements)
        total_target_hours = 0
        total_placed_hours = 0

        # Her sınıf için aday blokları hazırla
        for cn in classes_to_schedule:
            if not self._is_running:
                return

            existing_for_class = [m for m in target_class_manual if matches_class(m["class_name"], cn)]
            occupied_slots = set()
            manual_subj_map = {}
            manual_day_subj_hours = {}
            for m in existing_for_class:
                d = m["day_idx"]
                p = m["period"]
                dur = m["duration"]
                s = m["subject_name"]
                for off in range(dur):
                    occupied_slots.add((d, p + off))
                    manual_subj_map[(d, p + off)] = s
                manual_day_subj_hours[(d, s)] = manual_day_subj_hours.get((d, s), 0) + dur

            empty_slots = []
            for d in range(len(days)):
                for p in range(periods):
                    if (d, p) not in occupied_slots:
                        empty_slots.append((d, p))

            for m in existing_for_class:
                already_in = any(
                    (p_chk.get("day") == m["day_idx"] and 
                     p_chk.get("period") == m["period"] and 
                     matches_class(p_chk.get("class_name", ""), cn))
                    for p_chk in total_scheduled_placements
                )
                if not already_in:
                    total_scheduled_placements.append({
                        "period": m["period"], "day": m["day_idx"],
                        "row": m["period"], "col": m["day_idx"],
                        "subject_name": m["subject_name"], "subject": m["subject_name"],
                        "teacher_name": m["teacher_name"], "teacher": m["teacher_name"],
                        "class_name": cn, "class": cn,
                        "duration": m["duration"],
                        "locked": True, "is_manual": True,
                        "block_id": m.get("block_id") or str(_uuid.uuid4())[:12]
                    })
                    total_placed_hours += m["duration"]

            asgns = [a for a in assignments if matches_class(a.get("class") or a.get("sinif") or a.get("class_name") or "", cn)]
            
            if not asgns and not existing_for_class:
                continue
            
            candidate_blocks = []
            if asgns:
                for asgn in asgns:
                    raw_type = str(asgn.get("dagilim") or asgn.get("type") or "").strip()
                    t_name = format_tr_name(asgn.get("ogretmen") or asgn.get("teacher") or asgn.get("teacher_name") or "")
                    s_name = asgn.get("ders") or asgn.get("subject") or asgn.get("subject_name") or ""
                    
                    is_comb = bool(asgn.get("is_combined") or ("+" in str(asgn.get("class") or asgn.get("sinif") or "") and len(str(asgn.get("class") or asgn.get("sinif") or "").split("+")) > 1) or "," in str(asgn.get("class") or asgn.get("sinif") or "") or "&" in str(asgn.get("class") or asgn.get("sinif") or ""))
                    h_dur = int(asgn.get("ders_sayisi") or asgn.get("duration") or asgn.get("saat") or asgn.get("toplam_saat") or 2)
                    block_durs = parse_distribution_parts(raw_type, h_dur)
                    for b_dur in block_durs:
                        candidate_blocks.append({"subject": s_name, "teacher": t_name, "duration": b_dur, "is_combined": is_comb})

            # Manuel yerleşimleri düş
            manual_hours_by_st = {}
            for m in existing_for_class:
                m_subj = m.get("subject_name", "")
                m_t = format_tr_name(m.get("teacher_name", ""))
                m_dur = int(m.get("duration", 1))
                k = (m_subj, m_t)
                manual_hours_by_st[k] = manual_hours_by_st.get(k, 0) + m_dur

            for (m_subj, m_t), need_reduce in manual_hours_by_st.items():
                rem_r = need_reduce
                i = 0
                while i < len(candidate_blocks) and rem_r > 0:
                    cb = candidate_blocks[i]
                    cb_t = format_tr_name(cb.get("teacher", ""))
                    if cb.get("subject") == m_subj and (not m_t or not cb_t or cb_t == m_t):
                        cb_dur = cb.get("duration", 1)
                        if cb_dur <= rem_r:
                            rem_r -= cb_dur
                            candidate_blocks.pop(i)
                            continue
                    i += 1
                if rem_r > 0:
                    for cb in candidate_blocks:
                        cb_t = format_tr_name(cb.get("teacher", ""))
                        if cb.get("subject") == m_subj and (not m_t or not cb_t or cb_t == m_t):
                            cb_dur = cb.get("duration", 1)
                            if cb_dur > rem_r:
                                cb["duration"] -= rem_r
                                rem_r = 0
                                break

            if self.fill_empty:
                assigned_h = sum(b.get("duration", 1) for b in candidate_blocks) + len(occupied_slots)
                deficit = (len(days) * periods) - assigned_h
                while deficit > 0:
                    b_sz = 2 if deficit >= 2 else 1
                    candidate_blocks.append({
                        "subject": "Etüt / Serbest Çalışma",
                        "teacher": "",
                        "duration": b_sz,
                        "is_combined": False
                    })
                    deficit -= b_sz

            class_assigned_hours = sum(b.get("duration", 1) for b in candidate_blocks)
            total_target_hours += (class_assigned_hours + len(occupied_slots))

            if not candidate_blocks:
                continue

            c_timeoff = next((c.get("timeoff", []) for c in self.data_store.get("siniflar", []) if matches_class(c.get("ad", ""), cn)), [])
            c_kisit = kisitlamalar_store.get(cn) or kisitlamalar_store.get(format_tr_name(cn)) or kisitlamalar_store.get(normalize_clean(cn))
            if c_kisit:
                new_c_toff = []
                for d_idx in range(len(days)):
                    row_toff = []
                    for p_idx in range(periods):
                        cell_k = f"{d_idx},{p_idx}"
                        if cell_k in c_kisit:
                            row_toff.append(2 if c_kisit[cell_k] else 0)
                        elif c_timeoff and d_idx < len(c_timeoff) and p_idx < len(c_timeoff[d_idx]):
                            row_toff.append(c_timeoff[d_idx][p_idx])
                        else:
                            row_toff.append(2)
                    new_c_toff.append(row_toff)
                c_timeoff = new_c_toff

            # CSP Çözücü
            solution = self._csp_solve(
                candidate_blocks=candidate_blocks,
                empty_slots=empty_slots,
                global_teacher_occupied=global_teacher_occupied,
                c_timeoff=c_timeoff,
                days_count=len(days),
                periods_count=periods,
                manual_subj_map=manual_subj_map,
                manual_day_subj_hours=manual_day_subj_hours,
                constraints=constraints,
                relations=relations,
                class_name=cn,
                t_toff_dict=t_toff_dict,
                fully_blocked_teachers=fully_blocked_teachers
            )

            for sol_item in solution:
                dur = sol_item["duration"]
                t_name = sol_item["teacher"]
                s_name = sol_item["subject"]
                d = sol_item["day"]
                p = sol_item["period"]
                total_placed_hours += dur

                for off in range(dur):
                    if t_name:
                        global_teacher_occupied.add((t_name, d, p + off))
                        global_teacher_occupied.add((format_tr_name(t_name), d, p + off))
                        global_teacher_occupied.add((normalize_clean(t_name), d, p + off))

                # Birleşik ders kontrolü
                is_explicit_combined = bool(sol_item.get("is_combined"))
                combined_targets = [cn]
                if is_explicit_combined:
                    for a in assignments:
                        if not (a.get("is_combined") or ("+" in str(a.get("class") or a.get("sinif") or "") and len(str(a.get("class") or a.get("sinif") or "").split("+")) > 1) or "," in str(a.get("class") or a.get("sinif") or "") or "&" in str(a.get("class") or a.get("sinif") or "")):
                            continue
                        a_subj = a.get("ders") or a.get("subject") or ""
                        a_t = format_tr_name(a.get("ogretmen") or a.get("teacher") or "")
                        if a_subj == s_name and (not t_name or a_t == t_name):
                            if a.get("combined_classes"):
                                combined_targets = [str(c).strip() for c in a["combined_classes"] if str(c).strip()]
                                break
                            cls_str = a.get("sinif") or a.get("class") or ""
                            parts = [c.strip() for c in cls_str.replace("&", "+").replace(",", "+").split("+") if c.strip()]
                            if len(parts) > 1 and any(matches_class(p_c, cn) for p_c in parts):
                                combined_targets = parts
                                break

                _sol_block_id = str(_uuid.uuid4())[:12]
                for target_cn in combined_targets:
                    if target_cn != cn:
                        target_class_manual.append({
                            "class_name": target_cn,
                            "teacher_name": t_name,
                            "subject_name": s_name,
                            "day_idx": d,
                            "period": p,
                            "duration": dur,
                            "is_manual": True,
                            "block_id": _sol_block_id
                        })
                    already_in = any(
                        (p_chk.get("day") == d and 
                         p_chk.get("period") == p and 
                         matches_class(p_chk.get("class_name", ""), target_cn))
                        for p_chk in total_scheduled_placements
                    )
                    if not already_in:
                        total_scheduled_placements.append({
                            "period": p, "day": d,
                            "row": p, "col": d,
                            "subject_name": s_name, "subject": s_name,
                            "teacher_name": t_name, "teacher": t_name,
                            "class_name": target_cn, "class": target_cn,
                            "duration": dur,
                            "block_id": _sol_block_id,
                            "is_combined": is_explicit_combined,
                            "combined_classes": list(combined_targets) if is_explicit_combined else []
                        })

            self.progress_updated.emit(total_placed_hours, total_target_hours)

        self.data_store["grid_placements"] = total_scheduled_placements
        self.progress_updated.emit(total_placed_hours, total_target_hours)
        
        # Çapraz kurum çakışmalarını tespit et
        cross_conflicts = []
        try:
            for item in total_scheduled_placements:
                t_name = item.get("teacher_name") or item.get("teacher") or ""
                if not t_name:
                    continue
                norm_t = normalize_clean(t_name)
                t_fmt = format_tr_name(t_name)
                d = int(item.get("day_idx") if "day_idx" in item else item.get("day", 0))
                p = int(item.get("period", 0))
                dur = int(item.get("duration", 1))
                for off in range(dur):
                    slot_p = p + off
                    k_match = None
                    if (norm_t, d, slot_p) in cross_busy:
                        k_match = cross_busy[(norm_t, d, slot_p)]
                    elif (t_fmt, d, slot_p) in cross_busy:
                        k_match = cross_busy[(t_fmt, d, slot_p)]
                    elif (t_name, d, slot_p) in cross_busy:
                        k_match = cross_busy[(t_name, d, slot_p)]
                        
                    if k_match:
                        c_info = k_match
                        cross_conflicts.append({
                            "teacher": t_name,
                            "day": days[d] if d < len(days) else f"{d+1}. Gün",
                            "period": slot_p + 1,
                            "day_idx": d,
                            "period_idx": slot_p,
                            "other_institution": c_info.get("institution_name", "Diğer Kurum"),
                            "other_class": c_info.get("class_name", ""),
                            "other_subject": c_info.get("subject_name", ""),
                            "this_class": item.get("class_name") or item.get("class") or "",
                            "this_subject": item.get("subject_name") or item.get("subject") or ""
                        })
        except Exception as ce:
            print(f"[AUTO_SCHEDULER] Cross conflict scan notice: {ce}")

        self.finished_successfully.emit({
            "schedule": total_scheduled_placements,
            "placements": total_scheduled_placements,
            "placed_hours": total_placed_hours,
            "total_hours": total_target_hours,
            "cross_conflicts": cross_conflicts
        })

    def _csp_solve(self, candidate_blocks, empty_slots, global_teacher_occupied, c_timeoff=None, days_count=5, periods_count=8, manual_subj_map=None, manual_day_subj_hours=None, constraints=None, relations=None, class_name=None, t_toff_dict=None, fully_blocked_teachers=None):
        HARD_SUBJECTS = {"MATEMATİK", "FİZİK", "KİMYA", "BİYOLOJİ", "GEOMETRİ", "MAT", "FİZ", "KİM", "BİYO", "GEO"}
        manual_subj_map = manual_subj_map or {}
        manual_day_subj_hours = manual_day_subj_hours or {}
        constraints = constraints or {}
        relations = relations or []
        t_toff_dict = t_toff_dict or {}
        fully_blocked_teachers = fully_blocked_teachers or set()
        subject_windows = constraints.get("subject_windows", {})

        subj_weekly_hours = {}
        for (d, s), h in manual_day_subj_hours.items():
            subj_weekly_hours[s] = subj_weekly_hours.get(s, 0) + h
        for b in candidate_blocks:
            s = b["subject"]
            subj_weekly_hours[s] = subj_weekly_hours.get(s, 0) + b["duration"]

        relation_max_daily = {}
        relation_no_same_day = set()
        relation_time_windows = {}
        relation_no_consecutive_hard = False
        relation_teacher_morning = set()
        relation_teacher_afternoon = set()

        for rel in relations:
            if not rel.get("aktif", True):
                continue
            kural = rel.get("kural", "")
            rel_subjects = rel.get("dersler", [])
            rel_teachers = [format_tr_name(t) for t in rel.get("ogretmenler", []) if t]
            rel_classes = rel.get("siniflar", [])

            if rel_classes and class_name:
                if class_name not in [normalize_class_name(c) for c in rel_classes]:
                    continue

            if kural in ["Günde maksimum ders sayısı", "Beden Eğitimi / Uygulamalı dersler günde en fazla 2 saat olsun"]:
                max_val = int(rel.get("parametre", 2))
                for s in (rel_subjects or [""]):
                    relation_max_daily[s] = max_val
            elif kural == "İki ders aynı güne gelmesin":
                if len(rel_subjects) >= 2:
                    for i in range(len(rel_subjects)):
                        for j in range(i + 1, len(rel_subjects)):
                            relation_no_same_day.add((rel_subjects[i], rel_subjects[j]))
            elif kural == "X dersi belirli saatlerde kalmalı":
                ps = rel.get("period_start", 1)
                pe = rel.get("period_end", 4)
                for s in rel_subjects:
                    relation_time_windows[s] = (ps - 1, pe - 1)
            elif kural == "İki zor ders art arda gelmesin":
                relation_no_consecutive_hard = True
            elif kural == "Öğretmenin dersleri öğleden önce toplansın":
                for t in rel_teachers:
                    relation_teacher_morning.add(t)
            elif kural == "Öğretmenin dersleri öğleden sonra toplansın":
                for t in rel_teachers:
                    relation_teacher_afternoon.add(t)

        max_block_by_subj = {}
        for b in candidate_blocks:
            s = b["subject"]
            max_block_by_subj[s] = max(max_block_by_subj.get(s, 0), b.get("duration", 1))

        def get_max_daily_hours(s_name):
            if s_name in relation_max_daily:
                return relation_max_daily[s_name]
            if "" in relation_max_daily:
                return relation_max_daily[""]
            
            s_clean = s_name.upper().strip()
            req_min = max_block_by_subj.get(s_name, 2)
            if any(k in s_clean for k in ["BEDEN", "MÜZİK", "MUZIK", "GÖRSEL", "GORSEL", "RESİM", "RESIM", "SANAT", "SPOR"]):
                return max(2, req_min)

            w_total = subj_weekly_hours.get(s_name, 0)
            if w_total <= 5:
                return max(2, req_min)
            elif w_total <= 10:
                return max(2, req_min)
            else:
                return max(2, req_min, (w_total + 4) // 5)

        def block_priority_key(b):
            t = b.get("teacher", "")
            dur = b.get("duration", 1)
            s = b.get("subject", "")
            is_comb = 1 if b.get("is_combined") else 0
            is_hard = 1 if s.upper().strip() in HARD_SUBJECTS else 0
            
            t_busy = 0
            if t:
                t_clean = normalize_clean(t)
                t_fmt = format_tr_name(t)
                t_toff = t_toff_dict.get(t_clean) or t_toff_dict.get(t_fmt) or t_toff_dict.get(t)
                if t_toff:
                    t_busy = sum(1 for row in t_toff for cell in row if cell == 0)
                    
            return (-is_comb, -t_busy, -dur, -is_hard)

        empty_set = set(empty_slots)
        start_time = time.time()

        def is_valid_placement(d, p, dur, s, t, current_class_occ, current_teacher_occ, day_subj_hours, placed_cell_map, relax_daily=False):
            if p + dur > periods_count:
                return False
            for off in range(dur):
                slot = (d, p + off)
                if slot not in empty_set:
                    return False
                if slot in current_class_occ:
                    return False

            if c_timeoff:
                for off in range(dur):
                    if d < len(c_timeoff) and (p + off) < len(c_timeoff[d]) and c_timeoff[d][p + off] == 0:
                        return False

            if t:
                t_clean = normalize_clean(t)
                t_fmt = format_tr_name(t)
                if t in fully_blocked_teachers or t_fmt in fully_blocked_teachers or t_clean in fully_blocked_teachers:
                    return False
                for off in range(dur):
                    slot = (d, p + off)
                    if (t, d, p + off) in current_teacher_occ or (t_fmt, d, p + off) in current_teacher_occ or (t_clean, d, p + off) in current_teacher_occ:
                        return False
                    if (t, d, p + off) in global_teacher_occupied or (t_fmt, d, p + off) in global_teacher_occupied or (t_clean, d, p + off) in global_teacher_occupied:
                        return False
                t_toff = t_toff_dict.get(t_clean) or t_toff_dict.get(t_fmt) or t_toff_dict.get(t)
                if t_toff:
                    for off in range(dur):
                        if d < len(t_toff) and (p + off) < len(t_toff[d]) and t_toff[d][p + off] == 0:
                            return False

            curr_h = day_subj_hours.get((d, s), 0)
            if not relax_daily:
                if curr_h + dur > get_max_daily_hours(s):
                    return False
                w_total = subj_weekly_hours.get(s, 0)
                if curr_h > 0 and w_total <= (days_count * 2):
                    return False

            if s in relation_time_windows:
                tw_start, tw_end = relation_time_windows[s]
                for off in range(dur):
                    if (p + off) < tw_start or (p + off) > tw_end:
                        return False

            for pair in relation_no_same_day:
                s1, s2 = pair
                other = s2 if s == s1 else (s1 if s == s2 else None)
                if other and day_subj_hours.get((d, other), 0) > 0:
                    return False

            return True

        def score_slot(d, p, dur, s, t, current_class_occ, current_teacher_occ, day_subj_hours, placed_cell_map):
            cost = 0
            day_total = sum(1 for (cd, cp) in current_class_occ if cd == d)
            cost += day_total * 15

            if t:
                has_adj = (p > 0 and (t, d, p - 1) in current_teacher_occ) or (p + dur < periods_count and (t, d, p + dur) in current_teacher_occ)
                if has_adj:
                    cost -= 25

            is_hard = s.upper().strip() in HARD_SUBJECTS
            if is_hard or relation_no_consecutive_hard:
                if p > 0:
                    prev_s = placed_cell_map.get((d, p - 1)) or manual_subj_map.get((d, p - 1))
                    if prev_s and prev_s.upper().strip() in HARD_SUBJECTS:
                        cost += 80
                if p + dur < periods_count:
                    next_s = placed_cell_map.get((d, p + dur)) or manual_subj_map.get((d, p + dur))
                    if next_s and next_s.upper().strip() in HARD_SUBJECTS:
                        cost += 80

            if is_hard and (p + dur) >= periods_count:
                cost += 60

            s_win = subject_windows.get(s)
            if s_win == "morning" and p >= 4:
                cost += 50
            elif s_win == "afternoon" and p < 4:
                cost += 50

            if t:
                if t in relation_teacher_morning and p >= 4:
                    cost += 70
                if t in relation_teacher_afternoon and p < 4:
                    cost += 70

            return cost

        def search(rem_blocks, current_placed, current_class_occ, current_teacher_occ, day_subj_hours, placed_cell_map, relax_daily=False):
            if not rem_blocks:
                return current_placed
            if not self._is_running:
                return current_placed
            if time.time() - start_time > 10.0:
                return None

            b = rem_blocks[0]
            s = b["subject"]
            t = b["teacher"]
            dur = b["duration"]

            valid_slots = []
            for d in range(days_count):
                for p in range(periods_count - dur + 1):
                    if is_valid_placement(d, p, dur, s, t, current_class_occ, current_teacher_occ, day_subj_hours, placed_cell_map, relax_daily=relax_daily):
                        sc = score_slot(d, p, dur, s, t, current_class_occ, current_teacher_occ, day_subj_hours, placed_cell_map)
                        valid_slots.append((sc, d, p))

            valid_slots.sort(key=lambda x: x[0])

            for sc, d, p in valid_slots:
                next_placed = list(current_placed)
                next_placed.append({
                    "day": d, "period": p, "subject": s, "teacher": t, 
                    "duration": dur, "is_combined": b.get("is_combined", False)
                })

                next_class_occ = set(current_class_occ)
                next_teacher_occ = set(current_teacher_occ)
                next_cell_map = dict(placed_cell_map)
                for off in range(dur):
                    next_class_occ.add((d, p + off))
                    if t:
                        next_teacher_occ.add((t, d, p + off))
                        next_teacher_occ.add((format_tr_name(t), d, p + off))
                        next_teacher_occ.add((normalize_clean(t), d, p + off))
                    next_cell_map[(d, p + off)] = s

                next_day_subj = dict(day_subj_hours)
                next_day_subj[(d, s)] = next_day_subj.get((d, s), 0) + dur

                res = search(rem_blocks[1:], next_placed, next_class_occ, next_teacher_occ, next_day_subj, next_cell_map, relax_daily=relax_daily)
                if res is not None:
                    return res

            if dur > 1:
                split_blocks = [{"subject": s, "teacher": t, "duration": 1, "is_combined": b.get("is_combined", False)}, 
                                {"subject": s, "teacher": t, "duration": dur - 1, "is_combined": b.get("is_combined", False)}] + rem_blocks[1:]
                res = search(split_blocks, current_placed, current_class_occ, current_teacher_occ, day_subj_hours, placed_cell_map, relax_daily=relax_daily)
                if res is not None:
                    return res

            return None

        sorted_blocks = sorted(list(candidate_blocks), key=block_priority_key)
        
        # 1. Faz: Sıkı Kurallarla Çözüm
        init_class_occ = set()
        init_teacher_occ = set()
        init_cell_map = {}
        init_day_subj = dict(manual_day_subj_hours)
        
        sol = search(sorted_blocks, [], init_class_occ, init_teacher_occ, init_day_subj, init_cell_map, relax_daily=False)
        if sol is not None and len(sol) >= len(candidate_blocks):
            return sol

        # 2. Faz: Esnetilmiş Günlük Dağıtımla Çözüm
        start_time = time.time()
        sol = search(sorted_blocks, [], init_class_occ, init_teacher_occ, init_day_subj, init_cell_map, relax_daily=True)
        return sol or []

    def stop(self):
        self._is_running = False

    def _astar_solve(self, *args, **kwargs):
        return self._csp_solve(
            candidate_blocks=kwargs.get("candidate_blocks", []),
            empty_slots=kwargs.get("empty_slots", []),
            global_teacher_occupied=kwargs.get("global_teacher_occupied", set()),
            c_timeoff=kwargs.get("c_timeoff"),
            days_count=kwargs.get("days_count", 5),
            periods_count=kwargs.get("periods_count", 8),
            manual_subj_map=kwargs.get("manual_subj_map"),
            manual_day_subj_hours=kwargs.get("manual_day_subj_hours"),
            constraints=kwargs.get("constraints"),
            relations=kwargs.get("relations"),
            class_name=kwargs.get("class_name"),
            t_toff_dict=kwargs.get("t_toff_dict"),
            fully_blocked_teachers=kwargs.get("fully_blocked_teachers")
        )
