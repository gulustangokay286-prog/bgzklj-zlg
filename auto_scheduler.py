import random
from PySide6.QtCore import QThread, Signal

class AutoSchedulerWorker(QThread):
    progress_updated = Signal(int, int) # placed_count, total_count
    finished_successfully = Signal(dict) # Returns placed_lessons dict
    failed = Signal(str)

    def __init__(self, data_store, parent=None):
        super().__init__(parent)
        self.data_store = data_store
        self._is_running = True

    def run(self):
        # 1. Hazırlık (Extract data)
        settings = self.data_store.get("settings", {})
        days = settings.get("days", ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])
        periods = int(settings.get("periods", 8))
        
        assignments = self.data_store.get("atamalar", [])
        if not assignments:
            self.failed.emit("Herhangi bir ders ataması bulunamadı.")
            return

        # 1.5 Load existing manual placements (grid_placements)
        grid_placements = self.data_store.get("grid_placements", [])
        
        placed_hours_map = {}
        manual_schedule = []
        for p in grid_placements:
            c_name = p.get("class_name", "")
            t_name = p.get("teacher_name", "")
            subj = p.get("subject_name", "")
            dur = p.get("duration", 1)
            day = p.get("day", 0)
            period = p.get("period", 0)
            
            key = (c_name, t_name, subj)
            placed_hours_map[key] = placed_hours_map.get(key, 0) + dur
            
            manual_schedule.append({
                "class_name": c_name, "teacher_name": t_name,
                "subject_name": subj, "day_idx": day, "period": period,
                "duration": dur, "is_manual": True
            })

        # 2. Parçala (blok yapısına ve saat sayısına göre kalan ders blokları oluştur)
        blocks_to_place = []
        teacher_hours = {}
        for asgn in assignments:
            hours = int(asgn.get("duration") or asgn.get("saat") or asgn.get("toplam_saat") or 1)
            t_name = asgn.get("teacher") or asgn.get("ogretmen") or asgn.get("teacher_name") or ""
            c_name = asgn.get("class") or asgn.get("sinif") or asgn.get("class_name") or ""
            subj_name = asgn.get("subject") or asgn.get("ders") or asgn.get("subject_name") or ""
            type_str = str(asgn.get("type", ""))
            
            if (t_name or c_name) and subj_name:
                key = (c_name, t_name, subj_name)
                already_placed = placed_hours_map.get(key, 0)
                remaining_hours = hours - already_placed
                
                if remaining_hours <= 0:
                    continue # This assignment is fully placed manually
                    
                teacher_hours[t_name] = teacher_hours.get(t_name, 0) + remaining_hours
                
                # Parse breakdown like "2+2", "3+1", "2+1", "1+1"
                parts = []
                if "+" in type_str:
                    for p in type_str.split("+"):
                        p_clean = p.strip()
                        if p_clean.isdigit(): parts.append(int(p_clean))
                        
                # Adjust parts to sum exactly to remaining_hours
                adjusted_parts = []
                rem = remaining_hours
                for p in parts:
                    if rem >= p:
                        adjusted_parts.append(p)
                        rem -= p
                    elif rem > 0:
                        adjusted_parts.append(rem)
                        rem = 0
                        break
                        
                while rem > 0:
                    if rem >= 2:
                        adjusted_parts.append(2)
                        rem -= 2
                    else:
                        adjusted_parts.append(1)
                        rem -= 1
                        
                for b_dur in adjusted_parts:
                    if b_dur > 0:
                        blocks_to_place.append({
                            "class_name": c_name,
                            "teacher_name": t_name,
                            "subject_name": subj_name,
                            "duration": b_dur
                        })

        # Optimize by precaching objects
        t_objs = {t["ad"]: t for t in self.data_store.get("ogretmenler", []) if t.get("ad")}
        c_objs = {c["ad"]: c for c in self.data_store.get("siniflar", []) if c.get("ad")}
        
        # total_hours is remaining blocks to place + manual blocks already placed
        manual_hours = sum(m["duration"] for m in manual_schedule)
        target_total_hours = sum(b["duration"] for b in blocks_to_place) + manual_hours
        
        best_schedule = []
        best_placed_count = -1
        
        # Multiple attempts with backtracking & random restarts
        for attempt in range(300):
            if not self._is_running:
                return
                
            # Block sıralaması: Öncelik büyük bloklara ve yoğun öğretmenlere
            random.shuffle(blocks_to_place)
            blocks_to_place.sort(key=lambda b: (b["duration"], teacher_hours.get(b["teacher_name"], 0)), reverse=True)
            
            schedule = list(manual_schedule) # Start with manual placements
            teacher_schedule = {} # t_name -> set of (day_idx, period)
            class_schedule = {}   # c_name -> set of (day_idx, period)
            class_day_subjects = {} # c_name -> dict of day_idx -> set of subjects
            
            placed_hours = manual_hours
            
            # Pre-fill schedules with manual placements
            for ms in manual_schedule:
                d = ms["day_idx"]
                p = ms["period"]
                b_dur = ms["duration"]
                t_name = ms["teacher_name"]
                c_name = ms["class_name"]
                subj = ms["subject_name"]
                
                if t_name and t_name not in teacher_schedule: teacher_schedule[t_name] = set()
                if c_name and c_name not in class_schedule: class_schedule[c_name] = set()
                if c_name and c_name not in class_day_subjects: class_day_subjects[c_name] = {}
                
                for off in range(b_dur):
                    if t_name: teacher_schedule[t_name].add((d, p + off))
                    if c_name:
                        class_schedule[c_name].add((d, p + off))
                        if d not in class_day_subjects[c_name]: class_day_subjects[c_name][d] = set()
                        class_day_subjects[c_name][d].add(subj)
            
            for block in blocks_to_place:
                if not self._is_running:
                    return
                    
                c_name = block["class_name"]
                t_name = block["teacher_name"]
                subj = block["subject_name"]
                b_dur = block["duration"]
                
                if t_name and t_name not in teacher_schedule: teacher_schedule[t_name] = set()
                if c_name and c_name not in class_schedule: class_schedule[c_name] = set()
                if c_name and c_name not in class_day_subjects: class_day_subjects[c_name] = {}
                
                t_obj = t_objs.get(t_name, {})
                c_obj = c_objs.get(c_name, {})
                t_timeoff = t_obj.get("timeoff", [])
                c_timeoff = c_obj.get("timeoff", [])
                
                best_slots = []
                fallback_slots = []
                emergency_slots = []
                
                # Try placing block of size b_dur on day d starting at period p
                for d in range(len(days)):
                    for p in range(periods - b_dur + 1):
                        can_place = True
                        for off in range(b_dur):
                            check_p = p + off
                            t_conflict = (t_name != "" and (d, check_p) in teacher_schedule.get(t_name, set()))
                            c_conflict = (c_name != "" and (d, check_p) in class_schedule.get(c_name, set()))
                            if t_conflict or c_conflict:
                                can_place = False; break
                            if t_timeoff and d < len(t_timeoff) and check_p < len(t_timeoff[d]) and t_timeoff[d][check_p] == 0:
                                can_place = False; break
                            if c_timeoff and d < len(c_timeoff) and check_p < len(c_timeoff[d]) and c_timeoff[d][check_p] == 0:
                                can_place = False; break
                                
                        if can_place:
                            if c_name and subj in class_day_subjects[c_name].get(d, set()):
                                fallback_slots.append((d, p))
                            else:
                                best_slots.append((d, p))
                        else:
                            # If no strict slot, consider emergency slot (ignoring soft limits)
                            no_hard_overlap = True
                            for off in range(b_dur):
                                check_p = p + off
                                if (t_name and (d, check_p) in teacher_schedule.get(t_name, set())) or (c_name and (d, check_p) in class_schedule.get(c_name, set())):
                                    no_hard_overlap = False; break
                            if no_hard_overlap:
                                emergency_slots.append((d, p))
                                
                chosen_slot = None
                if best_slots:
                    random.shuffle(best_slots)
                    chosen_slot = best_slots[0]
                elif fallback_slots:
                    random.shuffle(fallback_slots)
                    chosen_slot = fallback_slots[0]
                elif emergency_slots:
                    random.shuffle(emergency_slots)
                    chosen_slot = emergency_slots[0]
                    
                if chosen_slot:
                    d, p = chosen_slot
                    for off in range(b_dur):
                        check_p = p + off
                        if t_name: teacher_schedule[t_name].add((d, check_p))
                        if c_name:
                            class_schedule[c_name].add((d, check_p))
                            if d not in class_day_subjects[c_name]: class_day_subjects[c_name][d] = set()
                            class_day_subjects[c_name][d].add(subj)
                        
                    schedule.append({
                        "class_name": c_name, "teacher_name": t_name,
                        "subject_name": subj, "day_idx": d, "period": p,
                        "duration": b_dur
                    })
                    placed_hours += b_dur
            
            if placed_hours > best_placed_count:
                best_placed_count = placed_hours
                best_schedule = schedule
                self.progress_updated.emit(placed_hours, target_total_hours)
                
            if best_placed_count == target_total_hours:
                break # Tüm dersler %100 yerleşti!

        self.progress_updated.emit(best_placed_count, target_total_hours)
        self.finished_successfully.emit({"schedule": best_schedule})

    def stop(self):
        self._is_running = False
