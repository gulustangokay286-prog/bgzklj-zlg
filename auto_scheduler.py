import random
from PySide6.QtCore import QThread, Signal

def normalize_class_name(cls_name: str) -> str:
    if not cls_name:
        return ""
    s = str(cls_name).strip().upper().replace(" ", "")
    s = s.replace("-", "/").replace("\\", "/")
    return s

def format_tr_name(name_str: str) -> str:
    if not name_str: return ""
    return " ".join(w.capitalize() for w in str(name_str).strip().split())

class AutoSchedulerWorker(QThread):
    progress_updated = Signal(int, int) # placed_hours, total_hours
    finished_successfully = Signal(dict) # Returns results dict
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
        max_class_hours = len(days) * periods  # Haftalık maksimum sınıf ders saati (5 gün x 8 ders = 40 saat)
        
        assignments = self.data_store.get("atamalar", [])
        if not assignments:
            self.failed.emit("Herhangi bir ders ataması bulunamadı.")
            return

        # 1.5 Load existing manual placements (grid_placements)
        grid_placements = self.data_store.get("grid_placements", [])
        
        placed_hours_map = {}
        manual_schedule = []
        class_placed_hours = {}
        
        for p in grid_placements:
            c_name = normalize_class_name(p.get("class_name", ""))
            t_name = format_tr_name(p.get("teacher_name", ""))
            subj = p.get("subject_name", "")
            dur = int(p.get("duration", 1))
            day = int(p.get("day", 0))
            period = int(p.get("period", 0))
            
            key = (c_name, t_name, subj)
            placed_hours_map[key] = placed_hours_map.get(key, 0) + dur
            class_placed_hours[c_name] = class_placed_hours.get(c_name, 0) + dur
            
            manual_schedule.append({
                "class_name": c_name, "teacher_name": t_name,
                "subject_name": subj, "day_idx": day, "period": period,
                "duration": dur, "is_manual": True
            })

        # 2. Parçala (Sınıf başına max 40 saat sınırına ve blok yapısına göre dersleri oluştur)
        blocks_to_place = []
        teacher_hours = {}
        
        for asgn in assignments:
            hours = int(asgn.get("duration") or asgn.get("saat") or asgn.get("toplam_saat") or 1)
            t_name = format_tr_name(asgn.get("teacher") or asgn.get("ogretmen") or asgn.get("teacher_name") or "")
            c_name = normalize_class_name(asgn.get("class") or asgn.get("sinif") or asgn.get("class_name") or "")
            subj_name = asgn.get("subject") or asgn.get("ders") or asgn.get("subject_name") or ""
            type_str = str(asgn.get("type", ""))
            
            if (t_name or c_name) and subj_name:
                key = (c_name, t_name, subj_name)
                already_placed = placed_hours_map.get(key, 0)
                remaining_hours = hours - already_placed
                
                if remaining_hours <= 0:
                    continue
                    
                # Sınıf kapasitesi (40 saat) aşılmasını engelle
                cur_cls_hrs = class_placed_hours.get(c_name, 0)
                if cur_cls_hrs >= max_class_hours:
                    continue
                available_cls_capacity = max_class_hours - cur_cls_hrs
                allowed_hours = min(remaining_hours, available_cls_capacity)
                class_placed_hours[c_name] = cur_cls_hrs + allowed_hours
                
                teacher_hours[t_name] = teacher_hours.get(t_name, 0) + allowed_hours
                
                # Blok parçalama: 2+2, 3+1, 2+1 vb.
                parts = []
                if "+" in type_str:
                    for p in type_str.split("+"):
                        p_clean = p.strip()
                        if p_clean.isdigit(): parts.append(int(p_clean))
                        
                adjusted_parts = []
                rem = allowed_hours
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

        t_objs = {format_tr_name(t["ad"]): t for t in self.data_store.get("ogretmenler", []) if t.get("ad")}
        c_objs = {normalize_class_name(c["ad"]): c for c in self.data_store.get("siniflar", []) if c.get("ad")}
        
        manual_hours = sum(m["duration"] for m in manual_schedule)
        target_total_hours = sum(b["duration"] for b in blocks_to_place) + manual_hours
        
        best_schedule = []
        best_placed_hours = -1
        
        # Akıllı yerleştirme, dinamik blok bölme ve boşluksuz gün doldurma döngüsü
        for attempt in range(500):
            if not self._is_running:
                return
                
            cur_blocks = list(blocks_to_place)
            random.shuffle(cur_blocks)
            cur_blocks.sort(key=lambda b: (b["duration"], teacher_hours.get(b["teacher_name"], 0)), reverse=True)
            
            schedule = list(manual_schedule)
            teacher_schedule = {}
            class_schedule = {}
            class_day_count = {}   # (c_name, day) -> number of placed hours
            class_day_subjects = {} # (c_name, day) -> set of subjects
            
            placed_hours = manual_hours
            
            # Manuel yerleşimleri doldur
            for ms in manual_schedule:
                d = ms["day_idx"]
                p = ms["period"]
                b_dur = ms["duration"]
                t_name = ms["teacher_name"]
                c_name = ms["class_name"]
                subj = ms["subject_name"]
                
                if t_name and t_name not in teacher_schedule: teacher_schedule[t_name] = set()
                if c_name and c_name not in class_schedule: class_schedule[c_name] = set()
                
                for off in range(b_dur):
                    if t_name: teacher_schedule[t_name].add((d, p + off))
                    if c_name:
                        class_schedule[c_name].add((d, p + off))
                        class_day_count[(c_name, d)] = class_day_count.get((c_name, d), 0) + 1
                        if (c_name, d) not in class_day_subjects: class_day_subjects[(c_name, d)] = set()
                        class_day_subjects[(c_name, d)].add(subj)
            
            idx = 0
            while idx < len(cur_blocks):
                if not self._is_running:
                    return
                    
                block = cur_blocks[idx]
                idx += 1
                
                c_name = block["class_name"]
                t_name = block["teacher_name"]
                subj = block["subject_name"]
                b_dur = block["duration"]
                
                if t_name and t_name not in teacher_schedule: teacher_schedule[t_name] = set()
                if c_name and c_name not in class_schedule: class_schedule[c_name] = set()
                
                t_obj = t_objs.get(t_name, {})
                c_obj = c_objs.get(c_name, {})
                t_timeoff = t_obj.get("timeoff", [])
                c_timeoff = c_obj.get("timeoff", [])
                
                valid_slots = []
                
                for d in range(len(days)):
                    for p in range(periods - b_dur + 1):
                        hard_conflict = False
                        for off in range(b_dur):
                            check_p = p + off
                            if (t_name and (d, check_p) in teacher_schedule.get(t_name, set())) or (c_name and (d, check_p) in class_schedule.get(c_name, set())):
                                hard_conflict = True
                                break
                        if hard_conflict:
                            continue
                            
                        # Timeoff kısıt kontrolü
                        timeoff_blocked = False
                        for off in range(b_dur):
                            check_p = p + off
                            if t_timeoff and d < len(t_timeoff) and check_p < len(t_timeoff[d]) and t_timeoff[d][check_p] == 0:
                                timeoff_blocked = True; break
                            if c_timeoff and d < len(c_timeoff) and check_p < len(c_timeoff[d]) and c_timeoff[d][check_p] == 0:
                                timeoff_blocked = True; break
                                
                        cur_day_load = class_day_count.get((c_name, d), 0)
                        same_subj = subj in class_day_subjects.get((c_name, d), set())
                        
                        score = 0
                        if not timeoff_blocked: score += 1000
                        if not same_subj: score += 200
                        # Erken saatleri önceliklendir (öğrenci ders programında pencereli/boşluklu saat kalmasın)
                        score -= p * 10
                        # Günlük ders yükünü dengeli dağıt (günde 8 saat)
                        score -= cur_day_load * 50
                        
                        valid_slots.append((score, d, p))
                        
                if valid_slots:
                    valid_slots.sort(key=lambda s: s[0], reverse=True)
                    top_tier = [s for s in valid_slots if s[0] >= valid_slots[0][0] - 15]
                    chosen = random.choice(top_tier)
                    _, d, p = chosen
                    
                    for off in range(b_dur):
                        check_p = p + off
                        if t_name: teacher_schedule[t_name].add((d, check_p))
                        if c_name:
                            class_schedule[c_name].add((d, check_p))
                            class_day_count[(c_name, d)] = class_day_count.get((c_name, d), 0) + 1
                            if (c_name, d) not in class_day_subjects: class_day_subjects[(c_name, d)] = set()
                            class_day_subjects[(c_name, d)].add(subj)
                        
                    schedule.append({
                        "class_name": c_name, "teacher_name": t_name,
                        "subject_name": subj, "day_idx": d, "period": p,
                        "duration": b_dur
                    })
                    placed_hours += b_dur
                else:
                    # Blok sığmadıysa (örneğin 1 saatlik boşluklar kaldıysa), bloğu 1'er saatlik tekil derslere böl!
                    if b_dur > 1:
                        for _ in range(b_dur):
                            cur_blocks.append({
                                "class_name": c_name,
                                "teacher_name": t_name,
                                "subject_name": subj,
                                "duration": 1
                            })
                
            if placed_hours > best_placed_hours:
                best_placed_hours = placed_hours
                best_schedule = schedule
                self.progress_updated.emit(placed_hours, target_total_hours)
                
            if best_placed_hours == target_total_hours:
                break # Tüm dersler (40/40) eksiksiz ve boşluksuz yerleşti!
                
        self.progress_updated.emit(best_placed_hours, target_total_hours)
        self.finished_successfully.emit({"schedule": best_schedule, "placed_hours": best_placed_hours, "total_hours": target_total_hours})

    def stop(self):
        self._is_running = False
