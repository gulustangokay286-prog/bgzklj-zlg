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
    clean_target = norm_target.split("(")[0].strip()
    clean_asgn = norm_asgn.split("(")[0].strip()
    if clean_target and clean_asgn and clean_target == clean_asgn:
        return True
    for part in str(asgn_class_str).replace("&", ",").replace("+", ",").split(","):
        p_norm = normalize_class_name(part)
        if p_norm == norm_target:
            return True
        p_clean = p_norm.split("(")[0].strip()
        if clean_target and p_clean and p_clean == clean_target:
            return True
    return False

def format_tr_name(name_str: str) -> str:
    if not name_str: return ""
    return " ".join(w.capitalize() for w in str(name_str).strip().split())

def parse_distribution_parts(type_str: str, total_duration: int = 0) -> list:
    """Parses distribution: '2+2' -> [2,2], '2+1+1' -> [2,1,1], or auto-splits total into max-2 blocks."""
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
            b = min(2, rem)
            parts.append(b)
            rem -= b
    if not parts and total_duration > 0:
        rem = total_duration
        while rem > 0:
            b = min(2, rem)
            parts.append(b)
            rem -= b
    return parts or ([total_duration] if total_duration > 0 else [2])


def _build_teacher_timeoff_map(data_store: dict) -> dict:
    """Builds teacher_name -> set of (day_idx, period_idx) that are BLOCKED."""
    blocked = defaultdict(set)
    for t in data_store.get("ogretmenler", []):
        t_ad = t.get("ad", "").strip()
        if not t_ad:
            continue
        toff = t.get("timeoff", [])
        if not toff:
            continue
        for d_idx, day_slots in enumerate(toff):
            if isinstance(day_slots, list):
                for p_idx, val in enumerate(day_slots):
                    if val == 0:
                        blocked[t_ad].add((d_idx, p_idx))
                        blocked[format_tr_name(t_ad)].add((d_idx, p_idx))
    return blocked


# A cell the user has explicitly closed in the Zaman Tablosu screen. It is put into
# the working grid before scheduling starts, so every existing "is this cell free?"
# check treats it as occupied and nothing can be placed there — including the filler
# pass, which is what was painting over closed periods.
BLOCKED_CELL = {
    "subject": None,
    "teacher": "",
    "block_id": "__blocked__",
    "is_blocked": True,
    "block_start": -1,
}


def _entity_timeoff_states(entity: dict, name: str, kisitlamalar: dict) -> dict:
    """Reads one entity's closed/avoid slots from BOTH places they are stored.

    TimeoffDialog writes the matrix twice: as entity["timeoff"][day][period] holding
    2=open / 0=closed / 1=avoid, and as data_store["kisitlamalar"][name]["d,p"]
    holding True=open / False=closed. Either copy can be the stale one depending on
    how the schedule was created or synced, so both are read and anything marked
    closed in either is treated as closed.

    Returns {(day, period): 0 or 1}; slots that are open are simply absent.
    """
    states = {}

    toff = entity.get("timeoff") or []
    for d_idx, day_slots in enumerate(toff):
        if not isinstance(day_slots, list):
            continue
        for p_idx, val in enumerate(day_slots):
            try:
                val = int(val)
            except (TypeError, ValueError):
                continue
            if val == 0:
                states[(d_idx, p_idx)] = 0
            elif val == 1:
                states.setdefault((d_idx, p_idx), 1)

    entry = (kisitlamalar or {}).get(name)
    if isinstance(entry, dict):
        for key, is_open in entry.items():
            try:
                d_str, p_str = str(key).split(",")
                slot = (int(d_str), int(p_str))
            except (ValueError, TypeError):
                continue
            if not is_open:
                states[slot] = 0

    return states


def _build_class_timeoff_map(data_store: dict) -> tuple:
    """Closed and avoid slots per CLASS.

    The scheduler only ever built this for teachers. Class constraints — closing
    e.g. periods 5-8 for a class so it goes home early — were read by nothing, so
    the auto-scheduler happily filled them in and the user's setting appeared to do
    nothing at all.

    Returns (blocked, avoid): both {class_name: {(day, period), ...}}.
    """
    blocked = defaultdict(set)
    avoid = defaultdict(set)
    kisitlamalar = data_store.get("kisitlamalar") or {}

    for cls in data_store.get("siniflar", []):
        if not isinstance(cls, dict):
            continue
        name = (cls.get("ad") or cls.get("name") or "").strip()
        if not name:
            continue
        for slot, state in _entity_timeoff_states(cls, name, kisitlamalar).items():
            if state == 0:
                blocked[name].add(slot)
            else:
                avoid[name].add(slot)

    return dict(blocked), dict(avoid)


def _resolve_class_slots(class_name: str, slot_map: dict) -> set:
    """Finds a class's slots in a map keyed by however the name was written.

    Class names reach the scheduler in several spellings ("9A", "9-A", "9 A"), and a
    constraint that silently fails to match is exactly the bug this map exists to
    fix, so three passes are tried in decreasing strictness.

    The last one uses normalize_clean rather than matches_class because
    matches_class deliberately rewrites "-" to "/" (it treats a dash as a combined-
    class separator), which makes it consider "9-A" and "9A" different. That rule is
    right for assignment matching and must not be changed, but for looking up a
    class's own constraints the looser comparison is what the user means.
    """
    if not class_name or not slot_map:
        return set()

    direct = slot_map.get(class_name)
    if direct:
        return set(direct)

    for key, slots in slot_map.items():
        if matches_class(key, class_name) or matches_class(class_name, key):
            return set(slots)

    target = normalize_clean(class_name)
    if target:
        for key, slots in slot_map.items():
            if normalize_clean(key) == target:
                return set(slots)

    return set()


def _build_cross_institution_map(institution_slug: str) -> dict:
    occupied = defaultdict(set)
    try:
        import version_store
        all_insts = version_store.list_institutions()
        for inst in all_insts:
            s = inst.get("slug", "")
            if s == institution_slug or not s:
                continue
            active = version_store.get_active_version(s)
            if not active:
                continue
            data = version_store.load_version(s, active)
            if not data:
                continue
            for p in data.get("grid_placements", []):
                t_name = format_tr_name(p.get("teacher_name") or p.get("teacher") or "")
                if not t_name:
                    continue
                d = int(p.get("day", p.get("col", -1)))
                per = int(p.get("period", p.get("row", -1)))
                dur = int(p.get("duration", 1))
                if d >= 0 and per >= 0:
                    for off in range(dur):
                        occupied[t_name].add((d, per + off))
    except Exception as e:
        print(f"[AutoScheduler] Cross-institution map error: {e}")
    return dict(occupied)


class AutoSchedulerWorker(QThread):
    progress_updated = Signal(int, int)
    iteration_updated = Signal(int, int, int)
    finished_successfully = Signal(dict)
    failed = Signal(str)

    def __init__(self, data_store, target_class=None, parent=None, fill_empty=True, institution_slug=None, use_vds=False, infinite_mode=True):
        super().__init__(parent)
        self.data_store = data_store
        self.target_class = target_class if target_class and str(target_class).strip() and "Tum" not in str(target_class) and "Tüm" not in str(target_class) else None
        self.fill_empty = fill_empty
        self.institution_slug = institution_slug or (self.data_store.get("settings", {}).get("institution_slug", None) if isinstance(self.data_store, dict) else None)
        self.use_vds = use_vds
        self.infinite_mode = infinite_mode
        self._is_running = True

    def run(self):
        t_start = time.time()
        settings = self.data_store.get("settings", {})
        days = settings.get("days")
        if not days:
            cnt = int(settings.get("day_count", self.data_store.get("gun_sayisi", 5)))
            all_days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
            days = all_days[:cnt]
        periods = int(settings.get("periods", self.data_store.get("ders_saati", 8)))
        D = len(days)
        P = periods

        assignments = self.data_store.get("atamalar", [])
        if not assignments:
            self.failed.emit("Herhangi bir ders ataması bulunamadı.")
            return

        teacher_timeoff = _build_teacher_timeoff_map(self.data_store)
        class_blocked_map, class_avoid_map = _build_class_timeoff_map(self.data_store)
        cross_inst_map = _build_cross_institution_map(self.institution_slug) if self.institution_slug else {}

        # Collect classes
        all_class_names = []
        for c in self.data_store.get("siniflar", []):
            cn = c.get("ad", "").strip()
            if cn and cn not in all_class_names:
                all_class_names.append(cn)

        assigned_class_names = set()
        for asgn in assignments:
            raw_c = (asgn.get("class") or asgn.get("sinif") or asgn.get("class_name") or "").strip()
            if raw_c:
                raw_c_clean = raw_c.replace("&", "+").replace(",", "+")
                parts = [p.strip() for p in raw_c_clean.split("+") if p.strip()]
                for p_clean in (parts if parts else [raw_c]):
                    for full_c in all_class_names:
                        if matches_class(full_c, p_clean):
                            assigned_class_names.add(full_c)

        if self.target_class:
            matched = [c for c in all_class_names if matches_class(c, self.target_class)]
            classes_to_schedule = matched if matched else [self.target_class]
        else:
            classes_to_schedule = [c for c in all_class_names if any(matches_class(c, ac) or matches_class(ac, c) for ac in assigned_class_names)]
            if not classes_to_schedule and assigned_class_names:
                classes_to_schedule = list(assigned_class_names)
            if not classes_to_schedule:
                classes_to_schedule = all_class_names

        # Parse all assignments into per-class block lists
        class_blocks = defaultdict(list)  # cn -> list of {subject, teacher, duration, block_id, is_combined}
        
        for asgn in assignments:
            raw_c = (asgn.get("class") or asgn.get("sinif") or asgn.get("class_name") or "").strip()
            if not raw_c:
                continue
            target_cls = [cn for cn in classes_to_schedule if matches_class(raw_c, cn)]
            if not target_cls:
                continue
            t_name = format_tr_name(asgn.get("ogretmen") or asgn.get("teacher") or asgn.get("teacher_name") or "")
            s_name = (asgn.get("ders") or asgn.get("subject") or "").strip()
            raw_type = str(asgn.get("dagilim") or asgn.get("type") or "").strip()
            h_dur = int(asgn.get("ders_sayisi") or asgn.get("duration") or asgn.get("saat") or asgn.get("toplam_saat") or 2)
            is_comb = bool(asgn.get("is_combined") or len(target_cls) > 1 or "+" in raw_c or "&" in raw_c or "," in raw_c)
            
            durs = parse_distribution_parts(raw_type, h_dur)
            for dur in durs:
                bid = f"b_{_uuid.uuid4().hex[:8]}"
                for cn in target_cls:
                    class_blocks[cn].append({
                        "subject": s_name,
                        "teacher": t_name,
                        "duration": dur,
                        "block_id": bid,
                        "is_combined": is_comb
                    })

        # Global teacher busy tracker
        global_teacher_busy = defaultdict(set)  # teacher -> set of (day, period)

        # Pre-fill teacher busy from OTHER classes' placements
        other_placements = []
        for p in self.data_store.get("grid_placements", []):
            c_name = (p.get("class_name") or p.get("class") or "").strip()
            if not any(matches_class(c_name, tgt) for tgt in classes_to_schedule):
                other_placements.append(p)
                t = format_tr_name(p.get("teacher_name") or p.get("teacher") or "")
                if t:
                    d = int(p.get("day", p.get("col", 0)))
                    per = int(p.get("period", p.get("row", 0)))
                    dur = int(p.get("duration", 1))
                    for off in range(dur):
                        global_teacher_busy[t].add((d, per + off))

        # Resolve each class's closed/avoid slots once, up front.
        blocked_by_class = {}
        avoid_by_class = {}
        for cn in classes_to_schedule:
            blocked_by_class[cn] = {
                (d, p) for (d, p) in _resolve_class_slots(cn, class_blocked_map)
                if 0 <= d < D and 0 <= p < P
            }
            avoid_by_class[cn] = {
                (d, p) for (d, p) in _resolve_class_slots(cn, class_avoid_map)
                if 0 <= d < D and 0 <= p < P
            }

        total_blocked = sum(len(s) for s in blocked_by_class.values())
        if total_blocked:
            print(f"[AutoScheduler] {total_blocked} closed slot(s) will be left empty "
                  f"across {sum(1 for s in blocked_by_class.values() if s)} class(es)")

        # ── CLASS-BY-CLASS SCHEDULING ─────────────────────────────────
        # Closed slots are not part of the target. Counting them made the scheduler
        # believe it had failed to reach a full grid and keep retrying all 50
        # attempts, and it is what drove the filler pass to paint over them.
        total_target = len(classes_to_schedule) * D * P - total_blocked

        best_result = None
        best_score = -1
        best_violations = []

        for attempt in range(50):
            if not self._is_running:
                break
            
            attempt_placements = list(other_placements)
            attempt_violations = []  # Track constraint bypasses
            attempt_teacher_busy = defaultdict(set)
            for t, slots in global_teacher_busy.items():
                attempt_teacher_busy[t] = set(slots)  # copy
            attempt_placed = 0
            
            for cn in classes_to_schedule:
                # grid[day][period] = None (free) | BLOCKED_CELL (closed) | placement
                grid = [[None for _ in range(P)] for _ in range(D)]

                # Seed the closed cells BEFORE anything is placed. Every pass below
                # already tests "is this cell None?" to decide whether a slot is
                # free, so occupying closed cells up front makes all of them —
                # including the filler pass that caused this bug — leave those
                # periods alone, with no extra check to forget in one branch.
                cls_blocked = blocked_by_class.get(cn, set())
                cls_avoid = avoid_by_class.get(cn, set())
                for (bd, bp) in cls_blocked:
                    grid[bd][bp] = BLOCKED_CELL

                blocks = list(class_blocks.get(cn, []))
                random.shuffle(blocks)
                # Sort: bigger blocks first for better distribution
                blocks.sort(key=lambda b: (-b["duration"], random.random()))
                
                unplaced = []
                
                for blk in blocks:
                    dur = blk["duration"]
                    t = blk["teacher"]
                    s = blk["subject"]
                    bid = blk["block_id"]
                    
                    # Find best day+period for this block
                    candidates = []
                    
                    for d in range(D):
                        for p in range(P - dur + 1):
                            # Check grid availability
                            ok = True
                            for off in range(dur):
                                if grid[d][p + off] is not None:
                                    ok = False
                                    break
                            if not ok:
                                continue
                            
                            # Check teacher timeoff (hard)
                            if t and t in teacher_timeoff:
                                toff_hit = False
                                for off in range(dur):
                                    if (d, p + off) in teacher_timeoff[t]:
                                        toff_hit = True
                                        break
                                if toff_hit:
                                    continue
                            
                            # Check teacher busy (hard)
                            if t:
                                t_busy = False
                                for off in range(dur):
                                    if (d, p + off) in attempt_teacher_busy[t]:
                                        t_busy = True
                                        break
                                if t_busy:
                                    continue
                            
                            # Score: prefer contiguous placement, spread subjects across days
                            same_subj_day = sum(1 for pp in range(P) if grid[d][pp] and grid[d][pp]["subject"] == s)
                            cross_pen = 0
                            if t and t in cross_inst_map:
                                for off in range(dur):
                                    if (d, p + off) in cross_inst_map[t]:
                                        cross_pen = 100

                            # "Tercih edilmez" (yellow ?) is a soft constraint: usable,
                            # but only once genuinely preferred slots are exhausted.
                            avoid_pen = 0
                            if cls_avoid:
                                avoid_pen = 500 * sum(
                                    1 for off in range(dur) if (d, p + off) in cls_avoid
                                )

                            score = same_subj_day * 1000 + p + cross_pen + avoid_pen + random.random() * 0.1
                            candidates.append((score, d, p))
                    
                    if candidates:
                        candidates.sort()
                        _, best_d, best_p = candidates[0]
                        
                        for off in range(dur):
                            grid[best_d][best_p + off] = {
                                "subject": s, "teacher": t, "block_id": bid,
                                "is_combined": blk["is_combined"], "block_start": best_p
                            }
                        if t:
                            for off in range(dur):
                                attempt_teacher_busy[t].add((best_d, best_p + off))
                    else:
                        unplaced.append(blk)
                
                # Second pass: try to place unplaced blocks with relaxed constraints
                for blk in unplaced:
                    dur = blk["duration"]
                    t = blk["teacher"]
                    s = blk["subject"]
                    bid = blk["block_id"]
                    
                    placed = False
                    for d in range(D):
                        for p in range(P - dur + 1):
                            ok = True
                            for off in range(dur):
                                if grid[d][p + off] is not None:
                                    ok = False
                                    break
                            if not ok:
                                continue
                            # Skip teacher busy but allow timeoff override
                            if t:
                                t_busy = False
                                for off in range(dur):
                                    if (d, p + off) in attempt_teacher_busy[t]:
                                        t_busy = True
                                        break
                                if t_busy:
                                    continue
                            
                            for off in range(dur):
                                grid[d][p + off] = {
                                    "subject": s, "teacher": t, "block_id": bid,
                                    "is_combined": blk["is_combined"], "block_start": p
                                }
                            if t:
                                for off in range(dur):
                                    attempt_teacher_busy[t].add((d, p + off))
                            placed = True
                            break
                        if placed:
                            break
                
                # Fill remaining empty cells with filler lessons (cycle through this class's
                # own assigned subjects), so the schedule has no visual gaps.
                #
                # IMPORTANT: this places MORE hours of a subject than were actually assigned
                # (e.g. an assigned 5h "Kimya" can end up with 8-9h actually on the grid). That
                # used to silently break the unplaced-dock bookkeeping: removing one placed
                # copy never returned anything to the dock, because the reconciliation counted
                # these filler copies as "real placed hours" too, so the assignment always
                # looked over-satisfied. Every block placed here is tagged is_filler=True so
                # the rest of the app can tell padding apart from a real assignment: the
                # reconciliation in _refresh_unplaced_lessons ignores filler hours when
                # deciding how many REAL hours are still unplaced, and removing a filler block
                # instead drops it straight into the dock as its own loose, re-placeable card
                # (see _delete_lesson_at / loose_unplaced_cards).
                templates = class_blocks.get(cn, [])
                if self.fill_empty and templates:
                    tmpl_idx = 0
                    for d in range(D):
                        p = 0
                        while p < P:
                            if grid[d][p] is None:
                                dur = 2 if (p + 1 < P and grid[d][p + 1] is None) else 1

                                prev_subj = grid[d][p - 1]["subject"] if (p > 0 and grid[d][p - 1] is not None) else None
                                next_subj = grid[d][p + dur]["subject"] if (p + dur < P and grid[d][p + dur] is not None) else None

                                chosen_tmpl = None
                                for off_idx in range(len(templates)):
                                    cand = templates[(tmpl_idx + off_idx) % len(templates)]
                                    if cand["subject"] != prev_subj and cand["subject"] != next_subj:
                                        chosen_tmpl = cand
                                        tmpl_idx = (tmpl_idx + off_idx + 1) % len(templates)
                                        break
                                if not chosen_tmpl:
                                    chosen_tmpl = templates[tmpl_idx % len(templates)]
                                    tmpl_idx += 1

                                t = chosen_tmpl["teacher"]
                                s = chosen_tmpl["subject"]

                                # Check teacher constraints
                                can_place = True
                                if t:
                                    for off in range(dur):
                                        if (d, p + off) in attempt_teacher_busy.get(t, set()):
                                            can_place = False
                                            break
                                        if t in teacher_timeoff and (d, p + off) in teacher_timeoff[t]:
                                            can_place = False
                                            break

                                if not can_place and dur == 2:
                                    dur = 1
                                    can_place = True
                                    if t:
                                        if (d, p) in attempt_teacher_busy.get(t, set()):
                                            can_place = False
                                        if t in teacher_timeoff and (d, p) in teacher_timeoff[t]:
                                            can_place = False

                                if not can_place:
                                    for alt in templates:
                                        alt_t = alt["teacher"]
                                        if alt["subject"] == prev_subj:
                                            continue
                                        alt_ok = True
                                        if alt_t:
                                            if (d, p) in attempt_teacher_busy.get(alt_t, set()) or (alt_t in teacher_timeoff and (d, p) in teacher_timeoff[alt_t]):
                                                alt_ok = False
                                        if alt_ok:
                                            t = alt_t
                                            s = alt["subject"]
                                            dur = 1
                                            can_place = True
                                            break

                                bid = f"fill_{_uuid.uuid4().hex[:8]}"
                                for off in range(dur):
                                    grid[d][p + off] = {
                                        "subject": s, "teacher": t, "block_id": bid,
                                        "is_combined": False, "block_start": p, "is_filler": True
                                    }
                                if t:
                                    for off in range(dur):
                                        attempt_teacher_busy[t].add((d, p + off))
                                p += dur
                            else:
                                p += 1
                
                # Convert grid to placement records
                for d in range(D):
                    p = 0
                    while p < P:
                        cell = grid[d][p]
                        if cell is None or cell.get("is_blocked"):
                            # A closed period produces no placement record at all, so
                            # it stays visibly empty on the grid.
                            p += 1
                            continue
                        # Find span of same block_id (strictly max 2 hours per block)
                        bid = cell["block_id"]
                        span = 1
                        while p + span < P and span < 2 and grid[d][p + span] is not None and grid[d][p + span]["block_id"] == bid:
                            span += 1
                        
                        attempt_placements.append({
                            "class_name": cn, "class": cn,
                            "subject_name": cell["subject"], "subject": cell["subject"],
                            "teacher_name": cell["teacher"], "teacher": cell["teacher"],
                            "day": d, "day_idx": d, "col": d,
                            "period": p, "row": p,
                            "duration": span,
                            "is_combined": cell["is_combined"],
                            "block_id": bid,
                            "is_filler": bool(cell.get("is_filler", False))
                        })
                        attempt_placed += span
                        p += span
            
            if attempt_placed > best_score:
                best_score = attempt_placed
                best_result = attempt_placements
                best_violations = attempt_violations
            
            if attempt_placed >= total_target:
                break

        if best_result is None:
            best_result = list(other_placements)
            best_violations = []

        elapsed = time.time() - t_start
        n_violations = len(best_violations) if best_violations else 0
        print(f"[AutoScheduler] {elapsed:.2f}s — {best_score}/{total_target} hours placed, {n_violations} constraint violations ({len(classes_to_schedule)} classes × {D}d × {P}p)")

        self.iteration_updated.emit(1, 0, best_score)
        self.progress_updated.emit(best_score, max(total_target, best_score))

        self.finished_successfully.emit({
            "schedule": best_result,
            "placements": best_result,
            "placed_hours": best_score,
            "total_hours": total_target,
            "cross_conflicts": [],
            "constraint_violations": best_violations or [],
            "elapsed_seconds": round(elapsed, 2)
        })

    def stop(self):
        self._is_running = False
