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

        # Parçala (saat sayısına göre 1 saatlik ders blokları oluştur)
        lessons_to_place = []
        teacher_hours = {}
        for asgn in assignments:
            hours = int(asgn.get("duration") or asgn.get("saat") or 1)
            t_name = asgn.get("teacher") or asgn.get("ogretmen") or ""
            c_name = asgn.get("class") or asgn.get("sinif") or ""
            subj_name = asgn.get("subject") or asgn.get("ders") or ""
            
            if t_name and c_name and subj_name:
                teacher_hours[t_name] = teacher_hours.get(t_name, 0) + hours
                for _ in range(hours):
                    lessons_to_place.append({
                        "class_name": c_name,
                        "teacher_name": t_name,
                        "subject_name": subj_name
                    })

        # Optimize by precaching objects
        t_objs = {t["ad"]: t for t in self.data_store.get("ogretmenler", []) if t.get("ad")}
        c_objs = {c["ad"]: c for c in self.data_store.get("siniflar", []) if c.get("ad")}
        
        total = len(lessons_to_place)
        best_schedule = []
        best_placed_count = -1
        
        # 20 kez farklı kurgularla dene (Random Restarts)
        for attempt in range(20):
            if not self._is_running:
                return
                
            # Dersleri karmaşıklaştır ama öğretmeni yoğun olanlara öncelik ver
            random.shuffle(lessons_to_place)
            # %50 ihtimalle yoğunluğa göre sırala, %50 tamamen rastgele (çeşitlilik için)
            if random.random() < 0.5:
                lessons_to_place.sort(key=lambda x: teacher_hours.get(x["teacher_name"], 0), reverse=True)
                
            schedule = []
            teacher_schedule = {} # t_name -> set of (day_idx, period)
            class_schedule = {}   # c_name -> set of (day_idx, period)
            class_day_subjects = {} # c_name -> dict of day_idx -> set of subjects
            
            placed_count = 0
            
            for lesson in lessons_to_place:
                if not self._is_running:
                    return
                    
                c_name = lesson["class_name"]
                t_name = lesson["teacher_name"]
                subj = lesson["subject_name"]
                
                if t_name not in teacher_schedule: teacher_schedule[t_name] = set()
                if c_name not in class_schedule: class_schedule[c_name] = set()
                if c_name not in class_day_subjects: class_day_subjects[c_name] = {}
                
                placed = False
                
                available_slots = [(d, p) for d in range(len(days)) for p in range(periods)]
                random.shuffle(available_slots)
                
                t_obj = t_objs.get(t_name, {})
                c_obj = c_objs.get(c_name, {})
                t_timeoff = t_obj.get("timeoff", [])
                c_timeoff = c_obj.get("timeoff", [])
                
                # Önce aynı gün aynı dersin olmadığı slotları dene
                best_slots = []
                fallback_slots = []
                for (d, p) in available_slots:
                    if (d, p) in teacher_schedule[t_name] or (d, p) in class_schedule[c_name]: continue
                    if t_timeoff and d < len(t_timeoff) and p < len(t_timeoff[d]) and t_timeoff[d][p] == 0: continue
                    if c_timeoff and d < len(c_timeoff) and p < len(c_timeoff[d]) and c_timeoff[d][p] == 0: continue
                    
                    if subj in class_day_subjects[c_name].get(d, set()):
                        fallback_slots.append((d, p))
                    else:
                        best_slots.append((d, p))
                        
                # Best slots preferred
                chosen_slot = None
                if best_slots: chosen_slot = best_slots[0]
                elif fallback_slots: chosen_slot = fallback_slots[0]
                
                if chosen_slot:
                    d, p = chosen_slot
                    teacher_schedule[t_name].add((d, p))
                    class_schedule[c_name].add((d, p))
                    if d not in class_day_subjects[c_name]: class_day_subjects[c_name][d] = set()
                    class_day_subjects[c_name][d].add(subj)
                    
                    schedule.append({
                        "class_name": c_name, "teacher_name": t_name,
                        "subject_name": subj, "day_idx": d, "period": p
                    })
                    placed_count += 1
            
            if placed_count > best_placed_count:
                best_placed_count = placed_count
                best_schedule = schedule
                self.progress_updated.emit(placed_count, total)
                
            if best_placed_count == total:
                break # Tüm dersler yerleşti!

        self.progress_updated.emit(best_placed_count, total)
        self.finished_successfully.emit({"schedule": best_schedule})

    def stop(self):
        self._is_running = False
