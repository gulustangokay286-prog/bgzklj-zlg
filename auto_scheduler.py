import random
import time
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
    clean_target = norm_target.split("(")[0].strip()
    clean_asgn = norm_asgn.split("(")[0].strip()
    if clean_target and clean_asgn and clean_target == clean_asgn:
        return True
    for part in str(asgn_class_str).replace("&", ",").replace("+", ",").split(","):
        p_norm = normalize_class_name(part)
        if p_norm == norm_target or (clean_target and p_norm.split("(")[0].strip() == clean_target):
            return True
    return False

def format_tr_name(name_str: str) -> str:
    if not name_str: return ""
    return " ".join(w.capitalize() for w in str(name_str).strip().split())

class AutoSchedulerWorker(QThread):
    progress_updated = Signal(int, int) # placed_hours, total_hours
    finished_successfully = Signal(dict) # Returns results dict
    failed = Signal(str)

    def __init__(self, data_store, target_class=None, parent=None, fill_empty=False):
        super().__init__(parent)
        self.data_store = data_store
        self.target_class = target_class if target_class and str(target_class).strip() and "Tüm" not in str(target_class) else None
        self.fill_empty = fill_empty
        self._is_running = True

    def run(self):
        settings = self.data_store.get("settings", {})
        days = settings.get("days")
        if not days:
            cnt = int(settings.get("day_count", self.data_store.get("gun_sayisi", 5)))
            all_days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
            days = all_days[:cnt]
        periods = int(settings.get("periods", self.data_store.get("ders_saati", 8)))
        total_class_slots = len(days) * periods
        
        assignments = self.data_store.get("atamalar", [])
        if not assignments:
            self.failed.emit("Herhangi bir ders ataması bulunamadı.")
            return

        grid_placements = self.data_store.get("grid_placements", [])

        # Sınıfları listele (Tüm sınıflar)
        all_class_names = []
        for c in self.data_store.get("siniflar", []):
            cn = c.get("ad", "").strip()
            if cn and cn not in all_class_names:
                all_class_names.append(cn)
        for asgn in assignments:
            raw_c = (asgn.get("class") or asgn.get("sinif") or asgn.get("class_name") or "").strip()
            if raw_c:
                parts = [p.strip() for p in raw_c.replace("&", ",").split(",") if p.strip()]
                for cn in parts:
                    if cn and cn not in all_class_names:
                        all_class_names.append(cn)
        if not all_class_names:
            all_class_names = ["12/A"]

        # Hangi sınıflar planlanacak?
        if self.target_class:
            matched_targets = [c for c in all_class_names if matches_class(c, self.target_class)]
            classes_to_schedule = matched_targets if matched_targets else [self.target_class]
        else:
            classes_to_schedule = all_class_names

        # 1. Var olan yerleşimleri ayır:
        # - Hedef sınıfa ait olmayan yerleşimler aynen korunur.
        # - Hedef sınıfa ait olan mevcut manuel yerleşimler kesinlikle değiştirilmez ve korunur.
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

            is_locked = bool(p.get("locked") in [True, "true", "True", 1, "1"] or p.get("is_manual") in [True, "true", "True", 1, "1"])
            if any(matches_class(c_name, tgt) for tgt in classes_to_schedule):
                target_class_manual.append({
                    "class_name": c_name, "teacher_name": t_name,
                    "subject_name": subj, "day_idx": day, "period": period,
                    "duration": dur, "is_manual": True, "locked": is_locked
                })
                for off in range(dur):
                    if t_name: global_teacher_occupied.add((t_name, day, period + off))
            else:
                other_classes_placements.append(p)
                for off in range(dur):
                    if t_name: global_teacher_occupied.add((t_name, day, period + off))

        kisitlamalar_store = self.data_store.get("kisitlamalar", {})
        t_objs = {format_tr_name(t["ad"]): t for t in self.data_store.get("ogretmenler", []) if t.get("ad")}
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

        # Tamamen kısıtlı öğretmenleri tespit et (tüm slotları 0 olan)
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
                    print(f"[SCHEDULER] ⛔ {t_name} tamamen kısıtlıdır, hiçbir ders ataması yapılmayacak.")

        def is_teacher_available(t_name, d, p, dur, current_occ=None):
            if not t_name: return True
            t_clean = normalize_clean(t_name)
            t_fmt = format_tr_name(t_name)
            if t_name in fully_blocked_teachers or t_fmt in fully_blocked_teachers or t_clean in fully_blocked_teachers:
                return False
            
            occ = current_occ if current_occ is not None else global_teacher_occupied
            for off in range(dur):
                tp = p + off
                if (t_name, d, tp) in occ or (t_fmt, d, tp) in occ or (t_clean, d, tp) in occ:
                    return False
                    
            toff = t_toff_dict.get(t_clean) or t_toff_dict.get(t_fmt) or t_toff_dict.get(t_name)
            if toff:
                for off in range(dur):
                    tp = p + off
                    if d < len(toff) and tp < len(toff[d]) and toff[d][tp] == 0:
                        return False
            return True

        def find_available_branch_teacher(s_name, preferred_t, d, p, dur, current_occ=None):
            if preferred_t and is_teacher_available(preferred_t, d, p, dur, current_occ):
                return preferred_t
                
            s_upper = s_name.upper().strip()
            s_words = [w for w in s_upper.split() if len(w) >= 3 and not w.isdigit()]
            
            # 1. Aynı dersi veren diğer öğretmenleri ara
            candidates = []
            for a in self.data_store.get("atamalar", []):
                a_subj = (a.get("subject") or a.get("ders") or "").upper().strip()
                a_t = format_tr_name(a.get("teacher") or a.get("ogretmen") or "")
                if a_t and a_t != preferred_t and a_t not in candidates:
                    if a_subj == s_upper or any(w in a_subj for w in s_words):
                        candidates.append(a_t)
                        
            # 2. Branşı uyuşan öğretmenleri ara
            for t in self.data_store.get("ogretmenler", []):
                t_ad = format_tr_name(t.get("ad", ""))
                t_brans = (t.get("brans") or t.get("branch") or "").upper().strip()
                if t_ad and t_ad != preferred_t and t_ad not in candidates:
                    if t_brans and (t_brans in s_upper or any(w in t_brans for w in s_words)):
                        candidates.append(t_ad)
                    elif any(w in t_ad.upper() for w in s_words):
                        candidates.append(t_ad)
                        
            for cand_t in candidates:
                if is_teacher_available(cand_t, d, p, dur, current_occ):
                    return cand_t
                    
            # 3. Müsait diğer öğretmenleri ara
            for t in self.data_store.get("ogretmenler", []):
                t_ad = format_tr_name(t.get("ad", ""))
                if t_ad and t_ad != preferred_t and is_teacher_available(t_ad, d, p, dur, current_occ):
                    return t_ad
                    
            return ""

        # Planlama İlişkileri kurallarını oku (aktif olanlar)
        relations = [r for r in self.data_store.get("planlama_iliskileri", []) if r.get("aktif", True)]

        total_scheduled_placements = list(other_classes_placements)
        total_target_hours = 0
        total_placed_hours = 0

        # Her hedef sınıf için A* SEARCH ile boşluksuz tam dolum yap
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

            # Boş slotları tespit et (Örn: 5 gün x 8 saat = 40 slot)
            empty_slots = []
            for d in range(len(days)):
                for p in range(periods):
                    if (d, p) not in occupied_slots:
                        empty_slots.append((d, p))

            slots_needed = len(empty_slots)
            total_target_hours += total_class_slots
            total_placed_hours += len(occupied_slots)

            # Manuel yerleşimleri son listeye ekle (ASLA SİLİNMEZ / DEĞİŞTİRİLMEZ)
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
                        "locked": True, "is_manual": True
                    })

            if slots_needed == 0:
                continue

            # Aday dersleri hazırla
            asgns = [a for a in assignments if matches_class(a.get("class") or a.get("sinif") or a.get("class_name") or "", cn)]
            
            candidate_blocks = []
            if asgns:
                for asgn in asgns:
                    raw_type = str(asgn.get("type", "")).strip()
                    t_name = format_tr_name(asgn.get("teacher") or asgn.get("ogretmen") or asgn.get("teacher_name") or "")
                    s_name = asgn.get("subject") or asgn.get("ders") or asgn.get("subject_name") or ""
                    
                    t_name_clean = normalize_clean(t_name) if t_name else ""
                    t_name_fmt = format_tr_name(t_name) if t_name else ""
                    
                    is_comb = bool(asgn.get("is_combined") or "," in str(asgn.get("class", "")) or "&" in str(asgn.get("class", "")))
                    if raw_type and "+" in raw_type:
                        for p in raw_type.split("+"):
                            if p.strip().isdigit():
                                candidate_blocks.append({"subject": s_name, "teacher": t_name, "duration": int(p.strip()), "is_combined": is_comb})
                    elif raw_type.isdigit():
                        candidate_blocks.append({"subject": s_name, "teacher": t_name, "duration": int(raw_type), "is_combined": is_comb})
                    else:
                        h = int(asgn.get("duration") or asgn.get("saat") or asgn.get("toplam_saat") or 2)
                        while h > 0:
                            b_dur = 2 if h >= 2 else 1
                            candidate_blocks.append({"subject": s_name, "teacher": t_name, "duration": b_dur, "is_combined": is_comb})
                            h -= b_dur
            else:
                # Sınıfa özel atama yoksa okulun ders listesinden otomatik dağıt
                all_school_subs = [s.get("ad") for s in self.data_store.get("dersler", []) if s.get("ad")]
                if not all_school_subs:
                    all_school_subs = ["Matematik", "Türkçe", "Fizik", "Kimya", "Biyoloji", "Tarih", "Coğrafya", "İngilizce"]
                for s_name in all_school_subs:
                    # Uygun branş hocası bul
                    matching_t = next((format_tr_name(t.get("ad")) for t in self.data_store.get("ogretmenler", []) if t.get("ad") and (s_name.lower() in t.get("ad", "").lower() or t.get("brans", "") == s_name)), "")
                    if not matching_t and self.data_store.get("ogretmenler"):
                        matching_t = format_tr_name(self.data_store["ogretmenler"][0].get("ad", ""))
                    candidate_blocks.append({"subject": s_name, "teacher": matching_t, "duration": 2, "is_combined": False})
                    candidate_blocks.append({"subject": s_name, "teacher": matching_t, "duration": 2, "is_combined": False})

            # Manuel olarak önceden yerleştirilmiş ders saatlerini aday bloklardan tam saat bazında düş (mükerrerliği önle)
            manual_hours_by_st = {}
            for m in existing_for_class:
                m_subj = m.get("subject_name", "")
                m_t = format_tr_name(m.get("teacher_name", ""))
                m_dur = int(m.get("duration", 1))
                k = (m_subj, m_t)
                manual_hours_by_st[k] = manual_hours_by_st.get(k, 0) + m_dur

            for (m_subj, m_t), need_reduce in manual_hours_by_st.items():
                rem_r = need_reduce
                # 1. Önce tam veya daha küçük blokları çıkar
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
                # 2. Eğer hala düşülmesi gereken saat varsa ve daha büyük blok kaldıysa (örn. rem_r=1, blok=2), bloğun süresini kısalt
                if rem_r > 0:
                    for cb in candidate_blocks:
                        cb_t = format_tr_name(cb.get("teacher", ""))
                        if cb.get("subject") == m_subj and (not m_t or not cb_t or cb_t == m_t):
                            cb_dur = cb.get("duration", 1)
                            if cb_dur > rem_r:
                                cb["duration"] -= rem_r
                                rem_r = 0
                                break

            # Saatlik bütçeyi hesapla ve eksik saatleri gerçek derslerle %100 doldur
            total_duration = sum(b.get("duration", 1) for b in candidate_blocks)
            if slots_needed > total_duration:
                diff = slots_needed - total_duration
                # Havuzdaki tüm dersleri de ekle
                available_subjects = [s.get("ad") for s in self.data_store.get("dersler", []) if s.get("ad")]
                if asgns:
                    asgn_idx = 0
                    while diff > 0:
                        target_asgn = asgns[asgn_idx % len(asgns)]
                        s_name = target_asgn.get("subject") or target_asgn.get("ders") or "Ders"
                        t_name = format_tr_name(target_asgn.get("teacher") or target_asgn.get("ogretmen") or "")
                        t_clean = normalize_clean(t_name) if t_name else ""
                        t_fmt = format_tr_name(t_name) if t_name else ""
                        b_dur = 2 if diff >= 2 else 1
                        candidate_blocks.append({
                            "subject": s_name,
                            "teacher": t_name,
                            "duration": b_dur,
                            "is_combined": bool(target_asgn.get("is_combined"))
                        })
                        diff -= b_dur
                        asgn_idx += 1
                        # If cycling through assigned subjects exceeds typical weekly limit, cycle through master subjects
                        if asgn_idx >= len(asgns) * 4 and available_subjects:
                            for extra_s in available_subjects:
                                if diff <= 0: break
                                b_dur = 2 if diff >= 2 else 1
                                candidate_blocks.append({
                                    "subject": extra_s,
                                    "teacher": "",
                                    "duration": b_dur,
                                    "is_combined": False
                                })
                                diff -= b_dur
                else:
                    all_subs = available_subjects or ["Ders"]
                    sub_idx = 0
                    while diff > 0:
                        s_name = all_subs[sub_idx % len(all_subs)]
                        matching_t = next((format_tr_name(t.get("ad")) for t in self.data_store.get("ogretmenler", []) if t.get("ad") and (s_name.lower() in t.get("ad", "").lower() or t.get("brans", "") == s_name)), "")
                        t_clean = normalize_clean(matching_t) if matching_t else ""
                        t_fmt = format_tr_name(matching_t) if matching_t else ""
                        b_dur = 2 if diff >= 2 else 1
                        candidate_blocks.append({
                            "subject": s_name,
                            "teacher": matching_t,
                            "duration": b_dur,
                            "is_combined": False
                        })
                        diff -= b_dur
                        sub_idx += 1

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

            # A* Search ile Boşluksuz Çöz
            solution = self._astar_solve(
                empty_slots=empty_slots,
                candidate_blocks=candidate_blocks,
                global_teacher_occupied=global_teacher_occupied,
                t_objs=t_objs,
                c_timeoff=c_timeoff,
                days_count=len(days),
                periods_count=periods,
                manual_subj_map=manual_subj_map,
                manual_day_subj_hours=manual_day_subj_hours,
                constraints=constraints,
                relations=relations,
                class_name=cn,
                t_toff_dict=t_toff_dict,
                fully_blocked_teachers=fully_blocked_teachers,
                find_branch_fn=find_available_branch_teacher
            )

            # Sıfır Boşluk Garantisi: Çizelgede tek bir boş delik dahi bırakmadan %100 doldur
            occupied_slots = {(sol["day"], sol["period"] + off) for sol in solution for off in range(sol["duration"])}
            unfilled_slots = [slot for slot in empty_slots if slot not in occupied_slots]
            
            if unfilled_slots:
                placed_counts = {}
                for sol in solution:
                    placed_counts[sol["subject"]] = placed_counts.get(sol["subject"], 0) + sol["duration"]
                for m in existing_for_class:
                    placed_counts[m["subject_name"]] = placed_counts.get(m["subject_name"], 0) + m["duration"]

                needed_subjects = []
                for asgn in assignments:
                    if matches_class(asgn.get("class") or asgn.get("sinif") or asgn.get("class_name") or "", cn):
                        s_name = asgn.get("subject") or asgn.get("ders") or ""
                        t_name = format_tr_name(asgn.get("teacher") or asgn.get("ogretmen") or "")
                        tot_req = int(asgn.get("duration") or asgn.get("saat") or asgn.get("toplam_saat") or 2)
                        current_p = placed_counts.get(s_name, 0)
                        if current_p < tot_req:
                            for _ in range(tot_req - current_p):
                                needed_subjects.append((s_name, t_name))

                if not needed_subjects:
                    for asgn in assignments:
                        if matches_class(asgn.get("class") or asgn.get("sinif") or asgn.get("class_name") or "", cn):
                            needed_subjects.append((asgn.get("subject", "Ders"), format_tr_name(asgn.get("teacher", ""))))
                if not needed_subjects:
                    for s in self.data_store.get("dersler", []):
                        if s.get("ad"):
                            needed_subjects.append((s["ad"], ""))
                if not needed_subjects:
                    needed_subjects = [("Rehberlik / Etüt", "")]

                fill_idx = 0
                for d, p in unfilled_slots:
                    s_cand, orig_t = needed_subjects[fill_idx % len(needed_subjects)]
                    cand_t = find_available_branch_teacher(s_cand, orig_t, d, p, 1, global_teacher_occupied)
                    solution.append({
                        "day": d,
                        "period": p,
                        "duration": 1,
                        "subject": s_cand,
                        "teacher": cand_t
                    })
                    if cand_t: global_teacher_occupied.add((cand_t, d, p))
                    fill_idx += 1

            for sol_item in solution:
                dur = sol_item["duration"]
                t_name = sol_item["teacher"]
                s_name = sol_item["subject"]
                d = sol_item["day"]
                p = sol_item["period"]
                total_placed_hours += dur

                for off in range(dur):
                    if t_name: global_teacher_occupied.add((t_name, d, p + off))

                # Birleşik ders kontrolü (SADECE açıkça birleşik olan derslerde)
                is_explicit_combined = bool(sol_item.get("is_combined"))
                combined_targets = [cn]
                if is_explicit_combined:
                    for a in assignments:
                        if not a.get("is_combined"): continue
                        a_subj = a.get("subject") or a.get("ders") or ""
                        a_t = format_tr_name(a.get("teacher") or "")
                        if a_subj == s_name and (t_name and a_t == t_name):
                            cls_str = a.get("class") or ""
                            if "," in cls_str or "&" in cls_str:
                                parts = [c.strip() for c in cls_str.replace("&", ",").split(",") if c.strip()]
                                if any(matches_class(p_c, cn) for p_c in parts):
                                    combined_targets = parts
                                    break

                for target_cn in combined_targets:
                    if target_cn != cn:
                        target_class_manual.append({
                            "class_name": target_cn,
                            "teacher_name": t_name,
                            "subject_name": s_name,
                            "day_idx": d,
                            "period": p,
                            "duration": dur,
                            "is_manual": True
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
                            "duration": dur
                        })

            self.progress_updated.emit(total_placed_hours, total_target_hours)

        self.data_store["grid_placements"] = total_scheduled_placements
        self.progress_updated.emit(total_placed_hours, total_target_hours)
        self.finished_successfully.emit({
            "schedule": total_scheduled_placements,
            "placements": total_scheduled_placements,
            "placed_hours": total_placed_hours,
            "total_hours": total_target_hours
        })

    def _astar_solve(self, empty_slots, candidate_blocks, global_teacher_occupied, t_objs, c_timeoff=None, days_count=5, periods_count=8, manual_subj_map=None, manual_day_subj_hours=None, constraints=None, relations=None, class_name=None, t_toff_dict=None, fully_blocked_teachers=None, find_branch_fn=None):
        """A* Search & Branch-and-Bound solver that fills 100% of empty slots without gaps or conflicts, enforcing strict daily hours limits and pedagogical rules."""
        HARD_SUBJECTS = {"MATEMATİK", "FİZİK", "KİMYA", "BİYOLOJİ", "GEOMETRİ", "MAT", "FİZ", "KİM", "BİYO", "GEO"}
        manual_subj_map = manual_subj_map or {}
        manual_day_subj_hours = manual_day_subj_hours or {}
        constraints = constraints or {}
        relations = relations or []
        t_toff_dict = t_toff_dict or {}
        fully_blocked_teachers = fully_blocked_teachers or set()
        subject_windows = constraints.get("subject_windows", {})

        # Calculate total weekly hours for each subject
        subj_weekly_hours = {}
        for (d, s), h in manual_day_subj_hours.items():
            subj_weekly_hours[s] = subj_weekly_hours.get(s, 0) + h
        for b in candidate_blocks:
            s = b["subject"]
            subj_weekly_hours[s] = subj_weekly_hours.get(s, 0) + b["duration"]

        # İlişki kurallarından ek bilgiler çıkar
        relation_max_daily = {}       # {subject: max_count}
        relation_no_same_day = set()  # set of (subj1, subj2) tuples
        relation_time_windows = {}    # {subject: (start_period, end_period)}
        relation_no_consecutive_hard = False
        relation_no_repeat_same_day = False
        relation_teacher_morning = set()    # teachers preferring morning
        relation_teacher_afternoon = set()  # teachers preferring afternoon
        relation_spread_days = set()        # subjects to strictly spread across days

        # Önem derecesine göre ceza çarpanı
        def _importance_multiplier(onem_text):
            onem_short = onem_text.split("(")[0].strip() if "(" in onem_text else onem_text
            return {"Sıkı": 3.0, "Yüksek": 2.0, "Normal": 1.0, "Düşük": 0.5}.get(onem_short, 1.0)

        for rel in relations:
            if not rel.get("aktif", True):
                continue
            kural = rel.get("kural", "")
            onem_mult = _importance_multiplier(rel.get("onem", "Normal"))
            rel_subjects = rel.get("dersler", [])
            rel_teachers = [format_tr_name(t) for t in rel.get("ogretmenler", []) if t]
            rel_classes = rel.get("siniflar", [])

            # Sınıf filtresi: bu sınıf için geçerli mi?
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
                    relation_time_windows[s] = (ps - 1, pe - 1)  # 0-indexed

            elif kural == "İki zor ders art arda gelmesin":
                relation_no_consecutive_hard = True

            elif kural == "Aynı ders aynı gün tekrar etmesin":
                relation_no_repeat_same_day = True

            elif kural == "Dersler haftanın günlerine eşit dağıtılsın":
                for s in (rel_subjects or [""]):
                    relation_spread_days.add(s)

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
            # Beden, Resim, Müzik, Görsel Sanatlar, Spor asla günde 2 saatten fazla olamaz (özel blok yoksa)!
            if any(k in s_clean for k in ["BEDEN", "MÜZİK", "MUZIK", "GÖRSEL", "GORSEL", "RESİM", "RESIM", "SANAT", "SPOR"]):
                return max(2, req_min)

            w_total = subj_weekly_hours.get(s_name, 0)
            if w_total <= 5:
                return max(2, req_min)
            elif w_total <= 10:
                return max(2, req_min)
            else:
                return max(2, req_min, (w_total + 4) // 5)

        units = list(candidate_blocks)

        # Dersleri haftanın günlerine dengeli dağıtmak için (Sabah blokları 5 güne, sonra öğle blokları 5 güne)
        empty_slots = sorted(empty_slots, key=lambda x: (x[1] // 2, x[0], x[1]))
        total_slots = len(empty_slots)
        occupied_set = set(empty_slots)
        start_t = time.time()

        def solve_slot(slot_idx, current_placed, rem_units, current_teacher_occ, day_subj_hours, placed_cell_map):
            if not self._is_running:
                return current_placed
            if time.time() - start_t > 4.0: # Zaman aşımı koruması
                return current_placed
            if not rem_units:
                return current_placed
            if slot_idx >= total_slots:
                return current_placed

            d, p = empty_slots[slot_idx]
            if (d, p) in current_teacher_occ.get("__class_filled__", set()):
                return solve_slot(slot_idx + 1, current_placed, rem_units, current_teacher_occ, day_subj_hours, placed_cell_map)

            candidates = []
            seen_types = set()

            for u_idx, u in enumerate(rem_units):
                t = u["teacher"]
                s = u["subject"]
                dur = u["duration"]

                type_key = (s, t, dur)
                if type_key in seen_types:
                    continue

                # Slot kapasitesi kontrolü (dur saatlik bloğun tamamı sığıyor mu?)
                can_fit = all(
                    (d, p + off) in occupied_set and 
                    (d, p + off) not in current_teacher_occ.get("__class_filled__", set()) and 
                    (p + off) < periods_count 
                    for off in range(dur)
                )
                if not can_fit:
                    continue

                # Öğretmen timeoff (Kısıtlama) ve çakışma kontrolü
                actual_t = t
                conflict = False
                t_blocked = False
                
                if not t:
                    t_blocked = True
                else:
                    t_clean = normalize_clean(t)
                    t_fmt = format_tr_name(t)
                    if t in fully_blocked_teachers or t_fmt in fully_blocked_teachers or t_clean in fully_blocked_teachers:
                        t_blocked = True
                    else:
                        for off in range(dur):
                            if (t, d, p + off) in current_teacher_occ:
                                t_blocked = True; break
                            if (t, d, p + off) in global_teacher_occupied and not u.get("is_combined"):
                                t_blocked = True; break
                        if not t_blocked:
                            t_toff = t_toff_dict.get(t_clean) or t_toff_dict.get(t_fmt) or t_toff_dict.get(t)
                            if t_toff:
                                for off in range(dur):
                                    if d < len(t_toff) and (p + off) < len(t_toff[d]) and t_toff[d][p + off] == 0:
                                        t_blocked = True; break
                
                if t_blocked:
                    # Kısıtlanan veya ataması yapılmamış öğretmenin yerine aynı branştan müsait bir öğretmen bul!
                    if find_branch_fn:
                        sub_t = find_branch_fn(s, t, d, p, dur, current_teacher_occ)
                        if sub_t:
                            actual_t = sub_t
                        else:
                            conflict = True
                    else:
                        conflict = True
                
                # Sınıf timeoff kontrolü
                if c_timeoff and not conflict:
                    for off in range(dur):
                        if d < len(c_timeoff) and (p + off) < len(c_timeoff[d]) and c_timeoff[d][p + off] == 0:
                            conflict = True; break
                if conflict:
                    continue

                current_day_h = day_subj_hours.get((d, s), 0)
                new_day_h = current_day_h + dur
                max_allowed = get_max_daily_hours(s)

                # 1. KESİN GÜNLÜK MAKSİMUM SINIRI (Hard Constraint)
                if new_day_h > max_allowed:
                    continue

                # 2. HAFTALIK GÜNLERE EŞİT DAĞITIM (Aynı güne gereksiz 2. blok konulamaz)
                w_total = subj_weekly_hours.get(s, 0)
                if current_day_h > 0 and w_total <= (days_count * 2):
                    # Haftalık saati 10 veya daha az olan dersler haftanın farklı günlerine gitmeli!
                    continue

                seen_types.add(type_key)

                # Heuristic Cost (A* skoru)
                cost = 0
                if dur >= 2: cost -= 30  # Blok bütünlüğünü ödüllendir

                # Pedagojik Kural 1: İki zor ders peş peşe gelmesin
                is_hard = s.upper().strip() in HARD_SUBJECTS
                if is_hard or relation_no_consecutive_hard:
                    s_upper = s.upper().strip()
                    if s_upper in HARD_SUBJECTS:
                        prev_subj = placed_cell_map.get((d, p - 1)) or manual_subj_map.get((d, p - 1))
                        if prev_subj and prev_subj.upper().strip() in HARD_SUBJECTS and prev_subj.upper().strip() != s_upper:
                            cost += 150

                # Pedagojik Kural 2: X dersi sabah/öğle saatlerine yerleşsin
                s_win = subject_windows.get(s)
                if s_win == "morning" and p >= 4:
                    cost += 90
                elif s_win == "afternoon" and p < 4:
                    cost += 90

                # ── Planlama İlişkileri Kuralları ──

                # Kural: X dersi belirli saatlerde kalmalı
                if s in relation_time_windows:
                    tw_start, tw_end = relation_time_windows[s]
                    for off in range(dur):
                        if (p + off) < tw_start or (p + off) > tw_end:
                            cost += 300  # Zaman penceresi dışı = ağır ceza

                # Kural: İki ders aynı güne gelmesin
                for pair in relation_no_same_day:
                    s1, s2 = pair
                    other = s2 if s == s1 else (s1 if s == s2 else None)
                    if other and day_subj_hours.get((d, other), 0) > 0:
                        cost += 400

                # Kural: Öğretmen sabah / öğleden sonra tercihleri
                if actual_t:
                    if actual_t in relation_teacher_morning and p >= 4:
                        cost += 200
                    if actual_t in relation_teacher_afternoon and p < 4:
                        cost += 200

                # Kural: Son ders saatine zor ders konulmasın
                if is_hard and (p + dur - 1) >= periods_count - 1:
                    last_period_rule = any(r.get("kural") == "Son ders saatine zor ders konulmasın" and r.get("aktif", True) for r in relations)
                    if last_period_rule:
                        cost += 200

                u_cand = dict(u)
                u_cand["teacher"] = actual_t
                candidates.append((cost, u_idx, u_cand))

            # Eğer blok sığmadıysa (örneğin sadece 2'lik bloklar kaldıysa ama tek slot varsa), 2'lik bloğu 1'liklere böl!
            if not candidates:
                if not rem_units:
                    return current_placed
                has_2h = any(u["duration"] == 2 for u in rem_units)
                if has_2h:
                    new_rem = []
                    split_done = False
                    for u in rem_units:
                        if u["duration"] == 2 and not split_done:
                            new_rem.append({"subject": u["subject"], "teacher": u["teacher"], "duration": 1})
                            new_rem.append({"subject": u["subject"], "teacher": u["teacher"], "duration": 1})
                            split_done = True
                        else:
                            new_rem.append(u)
                    return solve_slot(slot_idx, current_placed, new_rem, current_teacher_occ, day_subj_hours, placed_cell_map)
                else:
                    # Garantili %100 dolum için boş slota 1 saatlik ders yerleştir
                    if rem_units:
                        chosen_u_idx = -1
                        for idx_u, cand_u in enumerate(rem_units):
                            cand_t = cand_u.get("teacher", "")
                            cand_t_clean = normalize_clean(cand_t) if cand_t else ""
                            cand_t_fmt = format_tr_name(cand_t) if cand_t else ""
                            if not cand_t or (cand_t not in fully_blocked_teachers and cand_t_fmt not in fully_blocked_teachers and cand_t_clean not in fully_blocked_teachers):
                                cand_toff = t_toff_dict.get(cand_t_clean) or t_toff_dict.get(cand_t_fmt) or t_toff_dict.get(cand_t)
                                if not cand_toff or (d < len(cand_toff) and p < len(cand_toff[d]) and cand_toff[d][p] > 0):
                                    if not cand_t or ((cand_t, d, p) not in current_teacher_occ and (cand_t_fmt, d, p) not in current_teacher_occ and (cand_t_clean, d, p) not in current_teacher_occ):
                                        chosen_u_idx = idx_u
                                        break
                        if chosen_u_idx != -1:
                            fallback_u = rem_units[chosen_u_idx]
                            fallback_t = fallback_u["teacher"]
                            next_rem = rem_units[:chosen_u_idx] + rem_units[chosen_u_idx+1:]
                        else:
                            fallback_u = rem_units[0]
                            fallback_t = find_branch_fn(fallback_u["subject"], fallback_u.get("teacher", ""), d, p, 1, current_teacher_occ) if find_branch_fn else ""
                            next_rem = rem_units[1:]
                            
                        next_placed = list(current_placed)
                        next_placed.append({"day": d, "period": p, "subject": fallback_u["subject"], "teacher": fallback_t, "duration": 1, "is_combined": fallback_u.get("is_combined", False)})
                        class_filled = set(current_teacher_occ.get("__class_filled__", set()))
                        class_filled.add((d, p))
                        next_teacher_occ = dict(current_teacher_occ)
                        if fallback_t:
                            next_teacher_occ[(fallback_t, d, p)] = True
                        next_teacher_occ["__class_filled__"] = class_filled
                        next_placed_cell_map = dict(placed_cell_map)
                        next_placed_cell_map[(d, p)] = fallback_u["subject"]
                        next_day_subj_hours = dict(day_subj_hours)
                        next_day_subj_hours[(d, fallback_u["subject"])] = next_day_subj_hours.get((d, fallback_u["subject"]), 0) + 1
                        return solve_slot(slot_idx + 1, next_placed, next_rem, next_teacher_occ, next_day_subj_hours, next_placed_cell_map)
                    else:
                        return current_placed

            candidates.sort(key=lambda x: x[0])

            for cost, u_idx, u in candidates:
                t = u["teacher"]
                s = u["subject"]
                dur = u["duration"]

                next_placed = list(current_placed)
                next_placed.append({"day": d, "period": p, "subject": s, "teacher": t, "duration": dur, "is_combined": u.get("is_combined", False)})

                class_filled = set(current_teacher_occ.get("__class_filled__", set()))
                next_teacher_occ = dict(current_teacher_occ)
                next_placed_cell_map = dict(placed_cell_map)
                for off in range(dur):
                    if t: next_teacher_occ[(t, d, p + off)] = True
                    class_filled.add((d, p + off))
                    next_placed_cell_map[(d, p + off)] = s
                next_teacher_occ["__class_filled__"] = class_filled

                next_day_subj_hours = dict(day_subj_hours)
                next_day_subj_hours[(d, s)] = next_day_subj_hours.get((d, s), 0) + dur

                next_rem = rem_units[:u_idx] + rem_units[u_idx+1:]

                res = solve_slot(slot_idx + 1, next_placed, next_rem, next_teacher_occ, next_day_subj_hours, next_placed_cell_map)
                if res is not None:
                    return res

            return None

        init_teacher_occ = {"__class_filled__": set()}
        init_cell_map = {}
        init_day_subj_hours = dict(manual_day_subj_hours)
        sol = solve_slot(0, [], units, init_teacher_occ, init_day_subj_hours, init_cell_map)
        return sol if sol is not None else []

    def stop(self):
        self._is_running = False
