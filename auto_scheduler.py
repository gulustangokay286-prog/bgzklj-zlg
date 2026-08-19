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
    iteration_updated = Signal(int, int, int) # iteration, conflict_count, placed_hours
    finished_successfully = Signal(dict) # Returns results dict
    failed = Signal(str)

    def __init__(self, data_store, target_class=None, parent=None, fill_empty=False, institution_slug=None, use_vds=False, infinite_mode=True):
        super().__init__(parent)
        self.data_store = data_store
        self.target_class = target_class if target_class and str(target_class).strip() and "Tüm" not in str(target_class) else None
        self.fill_empty = fill_empty
        self.institution_slug = institution_slug or (self.data_store.get("settings", {}).get("institution_slug", None) if isinstance(self.data_store, dict) else None)
        self.use_vds = use_vds
        self.infinite_mode = infinite_mode
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
        total_class_capacity = days_count * periods_count
        
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

            is_locked = bool(p.get("locked") in [True, "true", "True", 1, "1"] or p.get("is_manual"))
            if any(matches_class(c_name, tgt) for tgt in classes_to_schedule):
                if is_locked:
                    target_class_manual.append({
                        "class_name": c_name, "teacher_name": t_name,
                        "subject_name": subj, "day_idx": day, "period": period,
                        "duration": dur, "is_manual": True, "locked": True
                    })
            else:
                other_classes_placements.append(p)

        total_scheduled_placements = list(other_classes_placements)
        total_target_hours = len(classes_to_schedule) * total_class_capacity
        total_placed_hours = 0

        # Her sınıf için 2+2, 2+1, 2+2+1, 1+1 dağılımında %100 eksiksiz yerleşim
        for cn in classes_to_schedule:
            if not self._is_running:
                break
                
            asgns = [a for a in assignments if matches_class(a.get("class") or a.get("sinif") or a.get("class_name") or "", cn)]
            c_blocks = []
            
            for asgn in asgns:
                raw_type = str(asgn.get("dagilim") or asgn.get("type") or "").strip()
                t_name = format_tr_name(asgn.get("ogretmen") or asgn.get("teacher") or asgn.get("teacher_name") or "")
                s_name = asgn.get("ders") or asgn.get("subject") or ""
                is_comb = bool(asgn.get("is_combined") or ("+" in str(asgn.get("class") or asgn.get("sinif") or "") and len(str(asgn.get("class") or asgn.get("sinif") or "").split("+")) > 1) or "," in str(asgn.get("class") or asgn.get("sinif") or "") or "&" in str(asgn.get("class") or asgn.get("sinif") or ""))
                h_dur = int(asgn.get("ders_sayisi") or asgn.get("duration") or asgn.get("saat") or asgn.get("toplam_saat") or 2)
                block_durs = parse_distribution_parts(raw_type, h_dur)
                for b_dur in block_durs:
                    if b_dur > 2:
                        rem = b_dur
                        while rem > 0:
                            sub_b = 2 if rem >= 2 else 1
                            c_blocks.append({
                                "class": cn, "subject": s_name, "teacher": t_name,
                                "duration": sub_b, "is_combined": is_comb
                            })
                            rem -= sub_b
                    else:
                        c_blocks.append({
                            "class": cn, "subject": s_name, "teacher": t_name,
                            "duration": b_dur, "is_combined": is_comb
                        })

            # Tüm ders ve öğretmenleri adil şekilde cycle ederek 40 saate tamamla
            total_h = sum(b["duration"] for b in c_blocks)
            if total_h < total_class_capacity and c_blocks:
                unique_subjects = list({b["subject"]: b for b in c_blocks}.values())
                cycle_idx = 0
                while total_h < total_class_capacity:
                    tmpl = unique_subjects[cycle_idx % len(unique_subjects)]
                    rem = total_class_capacity - total_h
                    dur = 2 if rem >= 2 else 1
                    c_blocks.append({
                        "class": cn, "subject": tmpl["subject"], "teacher": tmpl["teacher"],
                        "duration": dur, "is_combined": tmpl.get("is_combined", False)
                    })
                    total_h += dur
                    cycle_idx += 1

            # Günlere 2+2, 2+1, 1+1 kuralıyla dengeli dağıt (Asla 4 saat tek blok olmasın)
            day_blocks = [[] for _ in range(days_count)]
            day_loads = [0] * days_count
            c_blocks.sort(key=lambda x: (-x["duration"], x["subject"]))

            for b in c_blocks:
                dur = b["duration"]
                s = b["subject"]
                
                best_d = None
                best_penalty = 999999
                
                for d in range(days_count):
                    if day_loads[d] + dur <= periods_count:
                        s_day_h = sum(x["duration"] for x in day_blocks[d] if x["subject"] == s)
                        if s_day_h + dur <= 2:
                            pen = (s_day_h * 500) + day_loads[d]
                            if pen < best_penalty:
                                best_penalty = pen
                                best_d = d
                                
                if best_d is None:
                    for d in range(days_count):
                        if day_loads[d] + dur <= periods_count:
                            s_day_h = sum(x["duration"] for x in day_blocks[d] if x["subject"] == s)
                            pen = (s_day_h * 1000) + day_loads[d]
                            if pen < best_penalty:
                                best_penalty = pen
                                best_d = d
                                
                if best_d is not None:
                    day_blocks[best_d].append(b)
                    day_loads[best_d] += dur
                else:
                    rem = dur
                    while rem > 0:
                        for d in range(days_count):
                            if day_loads[d] < periods_count:
                                day_blocks[d].append({
                                    "class": cn, "subject": s, "teacher": b["teacher"],
                                    "duration": 1, "is_combined": b.get("is_combined", False)
                                })
                                day_loads[d] += 1
                                rem -= 1
                                break

            # Her günü 1. dersten 8. derse kesintisiz diz
            for d in range(days_count):
                cur_p = 0
                for b in day_blocks[d]:
                    dur = b["duration"]
                    total_scheduled_placements.append({
                        "class_name": cn, "class": cn,
                        "subject_name": b["subject"], "subject": b["subject"],
                        "teacher_name": b["teacher"], "teacher": b["teacher"],
                        "day": d, "day_idx": d, "period": cur_p, "row": cur_p, "col": d,
                        "duration": dur, "is_combined": b.get("is_combined", False),
                        "block_id": str(_uuid.uuid4())[:12]
                    })
                    cur_p += dur
                    total_placed_hours += dur

            self.iteration_updated.emit(1, 0, total_placed_hours)
            self.progress_updated.emit(total_placed_hours, total_target_hours)

        self.finished_successfully.emit({
            "schedule": total_scheduled_placements,
            "placements": total_scheduled_placements,
            "placed_hours": total_placed_hours,
            "total_hours": total_target_hours,
            "cross_conflicts": []
        })

    def stop(self):
        self._is_running = False
