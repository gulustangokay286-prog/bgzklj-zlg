import random
import time
import re
import uuid as _uuid
from collections import defaultdict
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
        HARD_SUBJECTS = {"MATEMATİK", "FİZİK", "KİMYA", "BİYOLOJİ", "GEOMETRİ", "MAT", "FİZ", "KİM", "BİYO", "GEO"}
        settings = self.data_store.get("settings", {})
        days = settings.get("days")
        if not days:
            cnt = int(settings.get("day_count", self.data_store.get("gun_sayisi", 5)))
            all_days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
            days = all_days[:cnt]
        periods = int(settings.get("periods", self.data_store.get("ders_saati", 8)))
        days_count = len(days)
        periods_count = periods
        
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
                
        # Build cards across target classes
        all_cards = []
        card_id = 0
        total_target_hours = 0
        total_placed_hours = 0
        total_scheduled_placements = list(other_classes_placements)

        # Pre-populate manual locked lessons
        manual_by_class = defaultdict(dict) # cn -> (d, p) -> manual_item
        for m in target_class_manual:
            cn = m["class_name"]
            d = m["day_idx"]
            p = m["period"]
            dur = m["duration"]
            for off in range(dur):
                manual_by_class[cn][(d, p + off)] = m
            total_scheduled_placements.append({
                "period": p, "day": d, "row": p, "col": d,
                "subject_name": m["subject_name"], "subject": m["subject_name"],
                "teacher_name": m["teacher_name"], "teacher": m["teacher_name"],
                "class_name": cn, "class": cn, "duration": dur,
                "locked": True, "is_manual": True,
                "block_id": m.get("block_id") or str(_uuid.uuid4())[:12]
            })
            total_placed_hours += dur

        for cn in classes_to_schedule:
            asgns = [a for a in assignments if matches_class(a.get("class") or a.get("sinif") or a.get("class_name") or "", cn)]
            c_blocks = []
            
            for asgn in asgns:
                raw_type = str(asgn.get("dagilim") or asgn.get("type") or "").strip()
                t_name = format_tr_name(asgn.get("ogretmen") or asgn.get("teacher") or asgn.get("teacher_name") or "")
                s_name = asgn.get("ders") or asgn.get("subject") or asgn.get("subject_name") or ""
                is_comb = bool(asgn.get("is_combined") or ("+" in str(asgn.get("class") or asgn.get("sinif") or "") and len(str(asgn.get("class") or asgn.get("sinif") or "").split("+")) > 1) or "," in str(asgn.get("class") or asgn.get("sinif") or "") or "&" in str(asgn.get("class") or asgn.get("sinif") or ""))
                h_dur = int(asgn.get("ders_sayisi") or asgn.get("duration") or asgn.get("saat") or asgn.get("toplam_saat") or 2)
                block_durs = parse_distribution_parts(raw_type, h_dur)
                for b_dur in block_durs:
                    c_blocks.append({
                        "id": card_id, "class": cn, "subject": s_name, "teacher": t_name,
                        "duration": b_dur, "is_combined": is_comb
                    })
                    card_id += 1

            # Reduce manual hours
            occupied_count = len(manual_by_class[cn])
            assigned_h = sum(b["duration"] for b in c_blocks) + occupied_count
            total_target_hours += (days_count * periods_count) if self.fill_empty else assigned_h

            if self.fill_empty:
                deficit = (days_count * periods_count) - (sum(b["duration"] for b in c_blocks) + occupied_count)
                while deficit > 0:
                    b_sz = 2 if deficit >= 2 else 1
                    c_blocks.append({
                        "id": card_id, "class": cn, "subject": "Etüt / Serbest Çalışma",
                        "teacher": "", "duration": b_sz, "is_combined": False
                    })
                    card_id += 1
                    deficit -= b_sz

            all_cards.extend(c_blocks)

        # Group cards by class and schedule with Min-Conflicts
        placed_cards_map = {c["id"]: c for c in all_cards}
        class_grid = {cn: {} for cn in classes_to_schedule} # cn -> (d, p) -> cid
        card_placement = {} # cid -> (d, p)

        # Populate manual slots in class_grid
        for cn in classes_to_schedule:
            for (d, p), m_item in manual_by_class[cn].items():
                class_grid[cn][(d, p)] = -1 # marked as occupied

        # Initial Greedy Construction
        cards_by_class = defaultdict(list)
        for c in all_cards:
            cards_by_class[c["class"]].append(c)

        for cn in classes_to_schedule:
            c_cards = cards_by_class[cn]
            c_cards.sort(key=lambda x: (-x["duration"], x["subject"]))
            day_load = [0] * days_count
            unplaced = []

            for c in c_cards:
                dur = c["duration"]
                s = c["subject"]
                t = c["teacher"]
                cid = c["id"]

                best_slot = None
                best_cost = 999999

                for d in range(days_count):
                    for p in range(periods_count - dur + 1):
                        if any((d, p + off) in class_grid[cn] for off in range(dur)):
                            continue
                        cost = day_load[d] * 10
                        # Teacher conflict penalty
                        if t:
                            for other_cn in classes_to_schedule:
                                if other_cn == cn: continue
                                for off in range(dur):
                                    occ_id = class_grid[other_cn].get((d, p + off))
                                    if occ_id is not None and occ_id != -1:
                                        occ_card = placed_cards_map.get(occ_id)
                                        if occ_card and occ_card["teacher"] == t:
                                            cost += 1000
                            # Global teacher occupied
                            for off in range(dur):
                                if (t, d, p + off) in global_teacher_occupied:
                                    cost += 2000
                                t_toff = t_toff_dict.get(normalize_clean(t)) or t_toff_dict.get(format_tr_name(t))
                                if t_toff and d < len(t_toff) and (p + off) < len(t_toff[d]) and t_toff[d][p + off] == 0:
                                    cost += 3000

                        # Same day subject penalty
                        same_day_s = sum(1 for (gd, gp), gcid in class_grid[cn].items() if gd == d and gcid != -1 and placed_cards_map.get(gcid, {}).get("subject") == s)
                        cost += same_day_s * 250
                        
                        if cost < best_cost:
                            best_cost = cost
                            best_slot = (d, p)

                if best_slot:
                    d, p = best_slot
                    for off in range(dur):
                        class_grid[cn][(d, p + off)] = cid
                    card_placement[cid] = (d, p)
                    day_load[d] += dur
                else:
                    unplaced.append(c)

            # Fit unplaced by splitting
            for c in unplaced:
                dur = c["duration"]
                cid = c["id"]
                free_cells = [(d, p) for d in range(days_count) for p in range(periods_count) if (d, p) not in class_grid[cn]]
                if len(free_cells) >= dur:
                    for off in range(dur):
                        d, p = free_cells[off]
                        sub_cid = cid if off == 0 else card_id
                        if off > 0:
                            card_id += 1
                            sub_card = dict(c)
                            sub_card["id"] = sub_cid
                            sub_card["duration"] = 1
                            placed_cards_map[sub_cid] = sub_card
                        else:
                            c["duration"] = 1
                        class_grid[cn][(d, p)] = sub_cid
                        card_placement[sub_cid] = (d, p)

        # Min-Conflicts Local Search Repair
        def get_conflicts():
            t_slots = defaultdict(list)
            for cid, (d, p) in card_placement.items():
                card = placed_cards_map.get(cid)
                if not card or not card["teacher"]: continue
                dur = card["duration"]
                t = card["teacher"]
                for off in range(dur):
                    t_slots[(t, d, p + off)].append(cid)
                    if (t, d, p + off) in global_teacher_occupied:
                        t_slots[(t, d, p + off)].append(-999) # penalty
                    t_toff = t_toff_dict.get(normalize_clean(t)) or t_toff_dict.get(format_tr_name(t))
                    if t_toff and d < len(t_toff) and (p + off) < len(t_toff[d]) and t_toff[d][p + off] == 0:
                        t_slots[(t, d, p + off)].append(-999)
            conf_count = sum(len(cids) - 1 for cids in t_slots.values() if len(cids) > 1)
            return conf_count, t_slots

        conf_count, t_slots = get_conflicts()

        for it in range(2500):
            if not self._is_running:
                return
            if conf_count == 0:
                break
            conf_slots = [s for s, cids in t_slots.items() if len(cids) > 1]
            if not conf_slots: break
            slot = random.choice(conf_slots)
            valid_cids = [x for x in t_slots[slot] if x != -999]
            if not valid_cids: continue
            cid = random.choice(valid_cids)
            card = placed_cards_map.get(cid)
            if not card: continue
            cn = card["class"]
            dur = card["duration"]
            if cid not in card_placement: continue
            orig_d, orig_p = card_placement[cid]

            # Pick random target slot in same class
            target_d = random.randint(0, days_count - 1)
            target_p = random.randint(0, periods_count - dur)
            if target_d == orig_d and target_p == orig_p: continue

            target_cids = list(set(class_grid[cn].get((target_d, target_p + off)) for off in range(dur) if (target_d, target_p + off) in class_grid[cn]))
            target_cids = [x for x in target_cids if x is not None and x != cid and x != -1]

            if len(target_cids) <= 1:
                other_cid = target_cids[0] if target_cids else None
                other_card = placed_cards_map.get(other_cid) if other_cid is not None else None
                if other_card is None or other_card["duration"] == dur:
                    for off in range(dur):
                        class_grid[cn].pop((orig_d, orig_p + off), None)
                        if other_cid is not None:
                            class_grid[cn].pop((target_d, target_p + off), None)
                    for off in range(dur):
                        class_grid[cn][(target_d, target_p + off)] = cid
                        if other_cid is not None:
                            class_grid[cn][(orig_d, orig_p + off)] = other_cid
                    card_placement[cid] = (target_d, target_p)
                    if other_cid is not None:
                        card_placement[other_cid] = (orig_d, orig_p)
                    new_conf, new_slots = get_conflicts()
                    if new_conf < conf_count or (new_conf == conf_count and random.random() < 0.08):
                        conf_count = new_conf
                        t_slots = new_slots
                    else:
                        # Revert
                        for off in range(dur):
                            class_grid[cn].pop((target_d, target_p + off), None)
                            if other_cid is not None:
                                class_grid[cn].pop((orig_d, orig_p + off), None)
                        for off in range(dur):
                            class_grid[cn][(orig_d, orig_p + off)] = cid
                            if other_cid is not None:
                                class_grid[cn][(target_d, target_p + off)] = other_cid
                        card_placement[cid] = (orig_d, orig_p)
                        if other_cid is not None:
                            card_placement[other_cid] = (target_d, target_p)

        # Assemble final scheduled placements
        for cid, (d, p) in card_placement.items():
            card = placed_cards_map.get(cid)
            if not card: continue
            dur = card["duration"]
            cn = card["class"]
            s_name = card["subject"]
            t_name = card["teacher"]
            is_comb = card.get("is_combined", False)
            total_placed_hours += dur

            total_scheduled_placements.append({
                "period": p, "day": d, "row": p, "col": d,
                "subject_name": s_name, "subject": s_name,
                "teacher_name": t_name, "teacher": t_name,
                "class_name": cn, "class": cn,
                "duration": dur, "is_combined": is_comb,
                "block_id": str(_uuid.uuid4())[:12]
            })

        # Emit progress
        self.progress_updated.emit(total_placed_hours, total_target_hours)

        # Cross conflict scan
        cross_conflicts = []
        try:
            for item in total_scheduled_placements:
                t_name = item.get("teacher_name") or item.get("teacher") or ""
                if not t_name: continue
                norm_t = normalize_clean(t_name)
                t_fmt = format_tr_name(t_name)
                d = int(item.get("day_idx") if "day_idx" in item else item.get("day", 0))
                p = int(item.get("period", 0))
                dur = int(item.get("duration", 1))
                for off in range(dur):
                    slot_p = p + off
                    k_match = cross_busy.get((norm_t, d, slot_p)) or cross_busy.get((t_fmt, d, slot_p)) or cross_busy.get((t_name, d, slot_p))
                    if k_match:
                        cross_conflicts.append({
                            "teacher": t_name, "day": days[d] if d < len(days) else f"{d+1}. Gün",
                            "period": slot_p + 1, "day_idx": d, "period_idx": slot_p,
                            "other_institution": k_match.get("institution_name", "Diğer Kurum"),
                            "other_class": k_match.get("class", ""),
                            "other_subject": k_match.get("subject", ""),
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

    def stop(self):
        self._is_running = False
