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
        for asgn in assignments:
            hours = int(asgn.get("saat", 1))
            for _ in range(hours):
                lessons_to_place.append({
                    "class_name": asgn.get("sinif", ""),
                    "teacher_name": asgn.get("ogretmen", ""),
                    "subject_name": asgn.get("ders", "")
                })

        # Rastgele dağıt (Heuristic / Backtracking tabanlı)
        # Basit V1 Algoritması: Rastgele uygun boşluk ara
        random.shuffle(lessons_to_place)
        
        placed_lessons = {} # Key: (row(period), col(day_idx)), Value: list of lesson dicts or just unique per class
        # Actually in timetable_grid.py, placed_lessons is:
        # { (row, col): {"class_name": ..., "teacher_name": ..., "subject_name": ...} }
        # But wait, one cell can only hold ONE lesson in standard view?
        # No, a cell represents (period, day). If we are placing for the whole school, multiple classes have lessons at the same time.
        # But timetable_grid.py expects placed_lessons to be a flat dict for ONE view?
        # No, timetable_grid.py stores EVERYTHING in `_placed_lessons`.
        # However, the key `(row, col)` in standard view means (period, day). 
        # If two classes have a lesson at Monday 1st period, they would both try to occupy `(0, 0)` in `_placed_lessons`.
        # Wait, how did standard grid support multiple classes? 
        # `TimetableGrid` only shows one class at a time, or all classes.
        # In Bütün Okul view, row = class index, col = day * periods + period.
        # We should store the master schedule in SQLite. For now, we will return a structure that can be saved.
        # Structure: list of dicts: {"class_name", "teacher_name", "subject_name", "day_idx", "period"}
        
        schedule = []
        teacher_schedule = {} # teacher_name -> set of (day_idx, period)
        class_schedule = {}   # class_name -> set of (day_idx, period)
        
        # Optimize by precaching objects
        t_objs = {t["ad"]: t for t in self.data_store.get("ogretmenler", [])}
        c_objs = {c["ad"]: c for c in self.data_store.get("siniflar", [])}
        
        total = len(lessons_to_place)
        placed_count = 0
        
        for lesson in lessons_to_place:
            if not self._is_running:
                return
                
            c_name = lesson["class_name"]
            t_name = lesson["teacher_name"]
            
            if t_name not in teacher_schedule:
                teacher_schedule[t_name] = set()
            if c_name not in class_schedule:
                class_schedule[c_name] = set()
                
            # Uygun yuva bul (Geriye Dönük Arama - Backtracking olmadan basit greedy heuristik)
            placed = False
            
            # Gün ve saatleri karıştırarak dağıtımı homojen yap
            available_slots = [(d, p) for d in range(len(days)) for p in range(periods)]
            random.shuffle(available_slots)
            
            t_obj = t_objs.get(t_name, {})
            c_obj = c_objs.get(c_name, {})
            t_timeoff = t_obj.get("timeoff", [])
            c_timeoff = c_obj.get("timeoff", [])
            
            for (d, p) in available_slots:
                # Kısıtlamalar (Hard Constraints)
                if (d, p) in teacher_schedule[t_name]:
                    continue # Öğretmen bu saatte başka sınıfta dolu
                if (d, p) in class_schedule[c_name]:
                    continue # Sınıfın bu saatte zaten dersi var
                    
                # Time-off Kısıtlamaları (0 = Kapalı/Kırmızı Çarpı)
                if t_timeoff and d < len(t_timeoff) and p < len(t_timeoff[d]):
                    if t_timeoff[d][p] == 0:
                        continue
                if c_timeoff and d < len(c_timeoff) and p < len(c_timeoff[d]):
                    if c_timeoff[d][p] == 0:
                        continue
                    
                # Eğer buraya geldiyse uygundur
                teacher_schedule[t_name].add((d, p))
                class_schedule[c_name].add((d, p))
                
                schedule.append({
                    "class_name": c_name,
                    "teacher_name": t_name,
                    "subject_name": lesson["subject_name"],
                    "day_idx": d,
                    "period": p
                })
                placed = True
                break
                
            if placed:
                placed_count += 1
                if placed_count % 5 == 0:
                    self.progress_updated.emit(placed_count, total)
                    self.msleep(10) # UI'ın güncellenmesi için ufak gecikme
            else:
                # Kilitlenme yaşandı (Backtracking eklenmeli)
                # Şimdilik sadece atla
                pass

        self.progress_updated.emit(placed_count, total)
        self.finished_successfully.emit({"schedule": schedule})

    def stop(self):
        self._is_running = False
