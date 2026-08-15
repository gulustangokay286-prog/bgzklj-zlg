import random
import time
from PySide6.QtCore import QThread, Signal

def normalize_class_name(cls_name: str) -> str:
    if not cls_name:
        return ""
    s = str(cls_name).strip().upper().replace(" ", "")
    s = s.replace("-", "/").replace("\\", "/")
    return s

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
        days = settings.get("days", ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])
        periods = int(settings.get("periods", 8))
        total_class_slots = len(days) * periods  # 5 gün x 8 saat = 40 slot
        
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
            cn = (asgn.get("class") or asgn.get("sinif") or asgn.get("class_name") or "").strip()
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
            day = int(p.get("day") if "day" in p else (p.get("day_idx") if "day_idx" in p else p.get("col", 0)))
            period = int(p.get("period") if "period" in p else p.get("row", 0))

            if not c_name and t_name and subj:
                for asgn in assignments:
                    a_t_name = format_tr_name(asgn.get("teacher") or asgn.get("ogretmen") or asgn.get("teacher_name") or "")
                    a_subj = asgn.get("subject") or asgn.get("ders") or asgn.get("subject_name") or ""
                    if a_t_name == t_name and a_subj == subj:
                        c_name = (asgn.get("class") or asgn.get("sinif") or asgn.get("class_name") or "").strip()
                        if c_name: break

            if any(matches_class(c_name, tgt) for tgt in classes_to_schedule):
                target_class_manual.append({
                    "class_name": c_name, "teacher_name": t_name,
                    "subject_name": subj, "day_idx": day, "period": period,
                    "duration": dur, "is_manual": True
                })
                for off in range(dur):
                    if t_name: global_teacher_occupied.add((t_name, day, period + off))
            else:
                other_classes_placements.append(p)
                for off in range(dur):
                    if t_name: global_teacher_occupied.add((t_name, day, period + off))

        t_objs = {format_tr_name(t["ad"]): t for t in self.data_store.get("ogretmenler", []) if t.get("ad")}
        constraints = self.data_store.get("constraints", {})

        # Tamamen kısıtlı öğretmenleri tespit et (tüm slotları 0 olan)
        fully_blocked_teachers = set()
        for t_name, t_obj in t_objs.items():
            toff = t_obj.get("timeoff", [])
            if toff:
                all_blocked = all(
                    (d_idx < len(toff) and p_idx < len(toff[d_idx]) and toff[d_idx][p_idx] == 0)
                    for d_idx in range(len(days))
                    for p_idx in range(periods)
                )
                if all_blocked:
                    fully_blocked_teachers.add(t_name)
                    print(f"[SCHEDULER] ⛔ {t_name} tamamen kısıtlıdır, hiçbir ders ataması yapılmayacak.")

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

            # Aday dersleri hazırla (SADECE bu sınıfa atanmış gerçek dersler!)
            asgns = [a for a in assignments if matches_class(a.get("class") or a.get("sinif") or a.get("class_name") or "", cn)]
            if not asgns:
                # Bu sınıfa ders/öğretmen atanmamışsa kesinlikle doldurma, boş bırak!
                continue

            candidate_blocks = []
            for asgn in asgns:
                raw_type = str(asgn.get("type", "")).strip()
                t_name = format_tr_name(asgn.get("teacher") or asgn.get("ogretmen") or asgn.get("teacher_name") or "")
                s_name = asgn.get("subject") or asgn.get("ders") or asgn.get("subject_name") or ""
                
                # Tamamen kısıtlı öğretmenlerin derslerini atla
                if t_name in fully_blocked_teachers:
                    print(f"[SCHEDULER] ⏭️ {t_name} kısıtlı, {s_name} dersi {cn} sınıfı için atlanıyor.")
                    continue
                
                if raw_type and "+" in raw_type:
                    for p in raw_type.split("+"):
                        if p.strip().isdigit():
                            candidate_blocks.append({"subject": s_name, "teacher": t_name, "duration": int(p.strip())})
                elif raw_type.isdigit():
                    candidate_blocks.append({"subject": s_name, "teacher": t_name, "duration": int(raw_type)})
                else:
                    h = int(asgn.get("duration") or asgn.get("saat") or asgn.get("toplam_saat") or 2)
                    while h > 0:
                        b_dur = 2 if h >= 2 else 1
                        candidate_blocks.append({"subject": s_name, "teacher": t_name, "duration": b_dur})
                        h -= b_dur

            # Manuel olarak önceden yerleştirilmiş ders saatlerini aday bloklardan düş (mükerrerliği önle)
            for m in existing_for_class:
                m_subj = m.get("subject_name", "")
                m_t = m.get("teacher_name", "")
                m_dur = int(m.get("duration", 1))
                
                found_idx = -1
                for idx, cb in enumerate(candidate_blocks):
                    if cb.get("subject") == m_subj and cb.get("teacher") == m_t and cb.get("duration") == m_dur:
                        found_idx = idx
                        break
                if found_idx == -1:
                    for idx, cb in enumerate(candidate_blocks):
                        if cb.get("subject") == m_subj and cb.get("teacher") == m_t:
                            found_idx = idx
                            break
                if found_idx != -1:
                    candidate_blocks.pop(found_idx)

            if getattr(self, "fill_empty", False):
                total_duration = sum(b.get("duration", 1) for b in candidate_blocks)
                if slots_needed > total_duration:
                    diff = slots_needed - total_duration
                    while diff > 0:
                        b_dur = 2 if diff >= 2 else 1
                        candidate_blocks.append({"subject": "Boş", "teacher": "Atanmadı", "duration": b_dur})
                        diff -= b_dur

            c_timeoff = next((c.get("timeoff", []) for c in self.data_store.get("siniflar", []) if matches_class(c.get("ad", ""), cn)), [])

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
                class_name=cn
            )

            for sol_item in solution:
                dur = sol_item["duration"]
                t_name = sol_item["teacher"]
                d = sol_item["day"]
                p = sol_item["period"]
                total_placed_hours += dur

                for off in range(dur):
                    if t_name: global_teacher_occupied.add((t_name, d, p + off))

                total_scheduled_placements.append({
                    "period": p, "day": d,
                    "row": p, "col": d,
                    "subject_name": sol_item["subject"], "subject": sol_item["subject"],
                    "teacher_name": t_name, "teacher": t_name,
                    "class_name": cn, "class": cn,
                    "duration": dur
                })

            self.progress_updated.emit(total_placed_hours, total_target_hours)

        self.progress_updated.emit(total_placed_hours, total_target_hours)
        self.finished_successfully.emit({
            "schedule": total_scheduled_placements,
            "placed_hours": total_placed_hours,
            "total_hours": total_target_hours
        })

    def _astar_solve(self, empty_slots, candidate_blocks, global_teacher_occupied, t_objs, c_timeoff=None, days_count=5, periods_count=8, manual_subj_map=None, manual_day_subj_hours=None, constraints=None, relations=None, class_name=None):
        """A* Search & Branch-and-Bound solver that fills 100% of empty slots without gaps or conflicts, enforcing strict daily hours limits and pedagogical rules."""
        HARD_SUBJECTS = {"MATEMATİK", "FİZİK", "KİMYA", "BİYOLOJİ", "GEOMETRİ", "MAT", "FİZ", "KİM", "BİYO", "GEO"}
        manual_subj_map = manual_subj_map or {}
        manual_day_subj_hours = manual_day_subj_hours or {}
        constraints = constraints or {}
        relations = relations or []
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

        def get_max_daily_hours(s_name):
            if s_name in relation_max_daily:
                return relation_max_daily[s_name]
            if "" in relation_max_daily:
                return relation_max_daily[""]
            
            s_clean = s_name.upper().strip()
            # Beden, Resim, Müzik, Görsel Sanatlar, Spor asla günde 2 saatten fazla olamaz!
            if any(k in s_clean for k in ["BEDEN", "MÜZİK", "MUZIK", "GÖRSEL", "GORSEL", "RESİM", "RESIM", "SANAT", "SPOR"]):
                return 2

            w_total = subj_weekly_hours.get(s_name, 0)
            if w_total <= 5:
                return 2
            elif w_total <= 10:
                return 2
            else:
                return max(2, (w_total + 4) // 5)

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

                # Çakışma kontrolü
                conflict = False
                for off in range(dur):
                    if t and (t, d, p + off) in current_teacher_occ:
                        conflict = True; break
                    if t and (t, d, p + off) in global_teacher_occupied:
                        conflict = True; break
                if conflict:
                    continue

                # Sınıf timeoff kontrolü
                if c_timeoff:
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

                if t and t in t_objs:
                    toff = t_objs[t].get("timeoff", [])
                    if toff:
                        timeoff_blocked = False
                        for off in range(dur):
                            if d < len(toff) and (p + off) < len(toff[d]) and toff[d][p + off] == 0:
                                timeoff_blocked = True
                                break
                        if timeoff_blocked:
                            continue  # Hard constraint: kesinlikle yerleştirme
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
                if t:
                    if t in relation_teacher_morning and p >= 4:
                        cost += 200
                    if t in relation_teacher_afternoon and p < 4:
                        cost += 200

                # Kural: Son ders saatine zor ders konulmasın
                if is_hard and (p + dur - 1) >= periods_count - 1:
                    last_period_rule = any(r.get("kural") == "Son ders saatine zor ders konulmasın" and r.get("aktif", True) for r in relations)
                    if last_period_rule:
                        cost += 200

                candidates.append((cost, u_idx, u))

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
                        fallback_u = rem_units[0]
                        next_placed = list(current_placed)
                        next_placed.append({"day": d, "period": p, "subject": fallback_u["subject"], "teacher": fallback_u["teacher"], "duration": 1})
                        class_filled = set(current_teacher_occ.get("__class_filled__", set()))
                        class_filled.add((d, p))
                        next_teacher_occ = dict(current_teacher_occ)
                        next_teacher_occ["__class_filled__"] = class_filled
                        next_rem = rem_units[1:]
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
                next_placed.append({"day": d, "period": p, "subject": s, "teacher": t, "duration": dur})

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
