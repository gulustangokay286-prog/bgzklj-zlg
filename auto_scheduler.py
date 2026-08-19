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

        # Sadece GERÇEK ders kartlarını oluştur (Asla sahte Etüt üretme)
        all_cards = []
        card_id = 0
        cards_by_class = defaultdict(list)
        total_target_hours = 0
        total_placed_hours = 0
        total_scheduled_placements = list(other_classes_placements)

        # Manuel kilitli dersleri ekle
        for m in target_class_manual:
            cn = m["class_name"]
            d = m["day_idx"]
            p = m["period"]
            dur = m["duration"]
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
            
            for asgn in asgns:
                raw_type = str(asgn.get("dagilim") or asgn.get("type") or "").strip()
                t_name = format_tr_name(asgn.get("ogretmen") or asgn.get("teacher") or asgn.get("teacher_name") or "")
                s_name = asgn.get("ders") or asgn.get("subject") or asgn.get("subject_name") or ""
                is_comb = bool(asgn.get("is_combined") or ("+" in str(asgn.get("class") or asgn.get("sinif") or "") and len(str(asgn.get("class") or asgn.get("sinif") or "").split("+")) > 1) or "," in str(asgn.get("class") or asgn.get("sinif") or "") or "&" in str(asgn.get("class") or asgn.get("sinif") or ""))
                h_dur = int(asgn.get("ders_sayisi") or asgn.get("duration") or asgn.get("saat") or asgn.get("toplam_saat") or 2)
                block_durs = parse_distribution_parts(raw_type, h_dur)
                for b_dur in block_durs:
                    card = {
                        "id": card_id, "class": cn, "subject": s_name, "teacher": t_name,
                        "duration": b_dur, "is_combined": is_comb
                    }
                    cards_by_class[cn].append(card)
                    all_cards.append(card)
                    card_id += 1

            total_target_hours += sum(c["duration"] for c in cards_by_class[cn])

        # Sıfır Boşluklu (Penceresiz) ve Çakışmasız Çizelge Motoru
        best_placements = []
        min_collisions = 999999
        
        for restart in range(4):
            if not self._is_running:
                return
                
            class_day_blocks = {cn: [[] for _ in range(days_count)] for cn in cards_by_class}
            cards_map = {c["id"]: dict(c) for c_list in cards_by_class.values() for c in c_list}
            
            # Günlük kapasiteleri sınıfın gerçek haftalık saatine göre tam dengeli böl
            for cn, c_cards in cards_by_class.items():
                total_h = sum(c["duration"] for c in c_cards)
                base_d = total_h // days_count
                rem_d = total_h % days_count
                daily_caps = [base_d + (1 if d < rem_d else 0) for d in range(days_count)]
                
                shuffled_cards = list(c_cards)
                if restart > 0:
                    random.shuffle(shuffled_cards)
                shuffled_cards.sort(key=lambda x: -x["duration"])
                
                day_sums = [0] * days_count
                day_cards = [[] for _ in range(days_count)]
                
                for c in shuffled_cards:
                    dur = c["duration"]
                    s = c["subject"]
                    cid = c["id"]
                    
                    best_d = None
                    best_pen = 999999
                    
                    days_order = list(range(days_count))
                    if restart > 0:
                        random.shuffle(days_order)
                        
                    for d in days_order:
                        if day_sums[d] + dur <= daily_caps[d]:
                            subj_count = sum(1 for xid in day_cards[d] if cards_map[xid]["subject"] == s)
                            pen = (subj_count * 100) + day_sums[d]
                            if pen < best_pen:
                                best_pen = pen
                                best_d = d
                                
                    if best_d is not None:
                        day_cards[best_d].append(cid)
                        day_sums[best_d] += dur
                    else:
                        rem_dur = dur
                        while rem_dur > 0:
                            placed_one = False
                            for d in range(days_count):
                                if day_sums[d] < daily_caps[d]:
                                    sub_id = cid if rem_dur == dur else card_id
                                    if sub_id != cid:
                                        card_id += 1
                                        sub_card = dict(c)
                                        sub_card["id"] = sub_id
                                        sub_card["duration"] = 1
                                        cards_map[sub_id] = sub_card
                                    else:
                                        cards_map[sub_id]["duration"] = 1
                                    day_cards[d].append(sub_id)
                                    day_sums[d] += 1
                                    rem_dur -= 1
                                    placed_one = True
                                    break
                            if not placed_one:
                                break
                                
                class_day_blocks[cn] = day_cards

            def evaluate_schedule():
                t_slots = defaultdict(list)
                card_locs = {}
                for cn, d_list in class_day_blocks.items():
                    for d in range(days_count):
                        cur_p = 0
                        for cid in d_list[d]:
                            card = cards_map[cid]
                            dur = card["duration"]
                            t = card["teacher"]
                            card_locs[cid] = (cn, d, cur_p)
                            if t:
                                for off in range(dur):
                                    t_slots[(t, d, cur_p + off)].append(cid)
                                    if (t, d, cur_p + off) in global_teacher_occupied:
                                        t_slots[(t, d, cur_p + off)].append(-999)
                                    t_toff = t_toff_dict.get(normalize_clean(t)) or t_toff_dict.get(format_tr_name(t))
                                    if t_toff and d < len(t_toff) and (cur_p + off) < len(t_toff[d]) and t_toff[d][cur_p + off] == 0:
                                        t_slots[(t, d, cur_p + off)].append(-999)
                            cur_p += dur
                conf_count = sum(len(cids) - 1 for cids in t_slots.values() if len(cids) > 1)
                return conf_count, t_slots, card_locs

            conf_count, t_slots, card_locs = evaluate_schedule()

            for it in range(3500):
                if not self._is_running:
                    return
                if conf_count == 0:
                    break
                    
                conf_slots = [slot for slot, cids in t_slots.items() if len(cids) > 1]
                if not conf_slots: break
                slot = random.choice(conf_slots)
                valid_cids = [x for x in t_slots[slot] if x != -999]
                if not valid_cids: continue
                cid = random.choice(valid_cids)
                card = cards_map[cid]
                cn, orig_d, orig_p = card_locs[cid]
                
                move_type = random.choice(["reorder_day", "swap_same_dur", "swap_same_dur", "rotate_day"])
                
                if move_type == "reorder_day":
                    d_cards = class_day_blocks[cn][orig_d]
                    if len(d_cards) >= 2:
                        idx1 = d_cards.index(cid)
                        idx2 = random.randint(0, len(d_cards) - 1)
                        if idx1 != idx2:
                            d_cards[idx1], d_cards[idx2] = d_cards[idx2], d_cards[idx1]
                            new_conf, new_slots, new_locs = evaluate_schedule()
                            if new_conf < conf_count or (new_conf == conf_count and random.random() < 0.08):
                                conf_count = new_conf
                                t_slots = new_slots
                                card_locs = new_locs
                            else:
                                d_cards[idx1], d_cards[idx2] = d_cards[idx2], d_cards[idx1]
                                
                elif move_type == "swap_same_dur":
                    target_d = random.randint(0, days_count - 1)
                    if target_d != orig_d:
                        target_cards = class_day_blocks[cn][target_d]
                        same_dur_cids = [x for x in target_cards if cards_map[x]["duration"] == card["duration"]]
                        if same_dur_cids:
                            other_cid = random.choice(same_dur_cids)
                            idx1 = class_day_blocks[cn][orig_d].index(cid)
                            idx2 = target_cards.index(other_cid)
                            
                            class_day_blocks[cn][orig_d][idx1] = other_cid
                            class_day_blocks[cn][target_d][idx2] = cid
                            
                            new_conf, new_slots, new_locs = evaluate_schedule()
                            if new_conf < conf_count or (new_conf == conf_count and random.random() < 0.08):
                                conf_count = new_conf
                                t_slots = new_slots
                                card_locs = new_locs
                            else:
                                class_day_blocks[cn][orig_d][idx1] = cid
                                class_day_blocks[cn][target_d][idx2] = other_cid

                elif move_type == "rotate_day":
                    d_cards = class_day_blocks[cn][orig_d]
                    if len(d_cards) >= 3:
                        rot = random.choice([1, -1])
                        class_day_blocks[cn][orig_d] = d_cards[rot:] + d_cards[:rot]
                        new_conf, new_slots, new_locs = evaluate_schedule()
                        if new_conf < conf_count or (new_conf == conf_count and random.random() < 0.08):
                            conf_count = new_conf
                            t_slots = new_slots
                            card_locs = new_locs
                        else:
                            class_day_blocks[cn][orig_d] = d_cards

            restart_placements = []
            for cn, d_list in class_day_blocks.items():
                for d in range(days_count):
                    cur_p = 0
                    for cid in d_list[d]:
                        card = cards_map[cid]
                        dur = card["duration"]
                        restart_placements.append({
                            "class_name": cn, "class": cn,
                            "subject_name": card["subject"], "subject": card["subject"],
                            "teacher_name": card["teacher"], "teacher": card["teacher"],
                            "day": d, "day_idx": d, "period": cur_p, "row": cur_p, "col": d,
                            "duration": dur, "is_combined": card.get("is_combined", False),
                            "block_id": str(_uuid.uuid4())[:12]
                        })
                        cur_p += dur

            if conf_count < min_collisions:
                min_collisions = conf_count
                best_placements = restart_placements
                
            if min_collisions == 0:
                break

        total_placed_hours += sum(p["duration"] for p in best_placements)
        total_scheduled_placements.extend(best_placements)

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
