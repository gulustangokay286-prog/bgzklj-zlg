import math
import os
import random
import time
import re
import uuid as _uuid
from collections import defaultdict

import lesson_hours

_FILL_DEBUG = bool(os.environ.get("CHENKI_FILL_DEBUG"))
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


def norm_teacher(name: str) -> str:
    """Teacher key used by every map in this module.

    Teacher names reach the scheduler in several spellings — "H.barış Karataş" vs
    "H.Barış Karataş", extra middle names, stray whitespace. A constraint that fails
    to match because of casing is indistinguishable from no constraint at all, so
    everything here is keyed by one aggressively normalized form.
    """
    if not name:
        return ""
    try:
        from version_store import normalize_teacher_name
        return normalize_teacher_name(name)
    except Exception:
        return str(name).strip().upper()


def _merge_foreign_teacher_slots(data_store: dict, foreign_map: dict) -> dict:
    """Folds another institution's per-teacher slots onto THIS institution's teacher keys.

    norm_teacher() collapses casing, spacing and Turkish characters, but it is still an
    exact match — so the same person entered as "Şeyma Nur Aker" at one branch and
    "Şeyma Aker" at another produces two different keys, and every cross-institution
    check silently passes because it thinks they are two people. version_store's
    _matches_teacher already knows how to spot that (dropped middle names, punctuation
    around initials), so it is used as a second pass here.

    Returns a NEW map keyed by this institution's own teacher keys.
    """
    if not foreign_map:
        return {}
    try:
        from version_store import _matches_teacher
    except Exception:
        return dict(foreign_map)

    own = {}
    for t in data_store.get("ogretmenler", []) or []:
        if isinstance(t, dict):
            raw = (t.get("ad") or t.get("name") or "").strip()
            if raw:
                own[norm_teacher(raw)] = raw

    merged = {k: set(v) for k, v in foreign_map.items()}
    for own_key, own_raw in own.items():
        for foreign_key, slots in foreign_map.items():
            if foreign_key == own_key:
                continue
            if _matches_teacher(own_raw, foreign_key):
                merged.setdefault(own_key, set()).update(slots)
    return merged


def _build_teacher_timeoff_map(data_store: dict, institution_slug: str = None, include_shared: bool = True) -> tuple:
    """Closed and avoid slots per TEACHER, keyed by norm_teacher().

    Merges two sources so a teacher who works at several institutions is treated as
    one person:
      * this institution's own Zaman Tablosu / Kısıtlamalar matrix, and
      * every OTHER institution's published teacher constraints.

    A slot closed anywhere is closed everywhere — that is the whole point of sharing
    a teacher: if they are unavailable Monday 1st period at one branch, that hour is
    genuinely gone, not merely gone from one file.

    Returns (blocked, avoid): both {norm_teacher: {(day, period), ...}}.
    """
    import constraint_sync

    blocked = defaultdict(set)
    avoid = defaultdict(set)
    day_count, periods = constraint_sync.grid_dimensions(data_store)

    for t in data_store.get("ogretmenler", []) or []:
        if not isinstance(t, dict):
            continue
        t_ad = (t.get("ad") or t.get("name") or "").strip()
        if not t_ad:
            continue
        key = norm_teacher(t_ad)
        matrix = constraint_sync.get_matrix(t, t_ad, data_store)
        for d in range(len(matrix)):
            for p in range(len(matrix[d])):
                state = matrix[d][p]
                if state == constraint_sync.CLOSED:
                    blocked[key].add((d, p))
                elif state == constraint_sync.AVOID:
                    avoid[key].add((d, p))

    if include_shared:
        try:
            shared = constraint_sync.shared_teacher_states(institution_slug, day_count, periods)
            foreign_closed = {k: {s for s, st in v.items() if st == constraint_sync.CLOSED}
                              for k, v in shared.items()}
            foreign_avoid = {k: {s for s, st in v.items() if st == constraint_sync.AVOID}
                             for k, v in shared.items()}
            for key, slots in _merge_foreign_teacher_slots(data_store, foreign_closed).items():
                blocked[key].update(slots)
            for key, slots in _merge_foreign_teacher_slots(data_store, foreign_avoid).items():
                avoid[key].update(slots)
        except Exception as e:
            print(f"[AutoScheduler] shared teacher constraint merge note: {e}")

    return dict(blocked), dict(avoid)


# A cell the user has explicitly closed in the Zaman Tablosu screen. It is put into
# the working grid before scheduling starts, so every existing "is this cell free?"
# check treats it as occupied and nothing can be placed there — including the filler
# pass, which is what was painting over closed periods.
def _match_slot(open_classes, slot, grids, leftover_blocks, teacher_busy,
                teacher_timeoff, cross_inst_map, periods):
    """Fills ONE hour with as many classes as is mathematically possible.

    Maximum bipartite matching between the classes still empty at this hour and the
    teachers who can work it. A class may be matched to any teacher named by a lesson
    it still owes; a teacher may take at most one class in the hour.

    Placing lessons greedily — first class gets the first teacher that fits — throws
    away hours that were placeable, because a teacher handed to an early class can be
    the only option left for a later one. When a school's assignments exactly fill its
    open slots, every hour lost that way is a hole that can never be filled again.

    Kuhn's algorithm: for each class, walk an augmenting path that re-seats already
    matched classes onto other teachers if that frees one up. Optimal for a single
    hour, and at this size (a handful of classes, a couple dozen teachers) instant.

    Returns {class_name: (block, subject, teacher_display_name)}.
    """
    d, p = slot

    def _teacher_free(display_name):
        key = norm_teacher(display_name)
        if not key:
            return False  # a lesson with no named teacher cannot be scheduled here
        if slot in teacher_busy.get(key, ()):
            return False
        if slot in teacher_timeoff.get(key, ()):
            return False
        if key in cross_inst_map and slot in cross_inst_map[key]:
            return False
        return True

    # class -> [(teacher_key, block, subject, display_name), ...]
    options = {}
    for cn in open_classes:
        grid = grids.get(cn)
        entries = []
        seen_keys = set()
        for blk in (leftover_blocks.get(cn) or []):
            display = blk.get("teacher") or ""
            key = norm_teacher(display)
            if not key or key in seen_keys:
                continue
            if not _teacher_free(display):
                continue
            # Avoid stacking the same subject next to itself when there is a choice;
            # this is a preference, applied by ordering, never a veto.
            prev_subj = grid[d][p - 1]["subject"] if (p > 0 and grid[d][p - 1]) else None
            next_subj = grid[d][p + 1]["subject"] if (p + 1 < periods and grid[d][p + 1]) else None
            repeats = blk["subject"] in (prev_subj, next_subj)
            entries.append((repeats, key, blk, blk["subject"], display))
            seen_keys.add(key)
        if entries:
            entries.sort(key=lambda e: e[0])  # non-repeating subjects first
            options[cn] = [(k, b, s, n) for _r, k, b, s, n in entries]

    if not options:
        return {}

    teacher_to_class = {}

    def _augment(cn, visited):
        for key, blk, subject, display in options.get(cn, ()):
            if key in visited:
                continue
            visited.add(key)
            holder = teacher_to_class.get(key)
            if holder is None or _augment(holder[0], visited):
                teacher_to_class[key] = (cn, blk, subject, display)
                return True
        return False

    # Fewest options first: a class with only one possible teacher must be seated
    # before a flexible one takes that teacher away.
    for cn in sorted(options, key=lambda c: len(options[c])):
        _augment(cn, set())

    return {
        cn: (blk, subject, display)
        for cn, blk, subject, display in teacher_to_class.values()
    }


def repair_conflicts(grids, teacher_timeoff, cross_inst_map, D, P, rounds=400):
    """Settles a fully-filled grid into the best arrangement it allows.

    Used after "fill everything first, sort it out afterwards": the grid arrives
    complete but with the same teacher booked in several classes at the same hour.
    Every open cell is already taken, so nothing can simply move to an empty slot —
    the only legal move is to SWAP two lessons inside one class, which keeps that
    class full while changing which hour each teacher is needed at.

    A swap is applied only when it strictly reduces the total number of clashing
    teacher-hours, so the grid can never get worse than it started. This is the
    min-conflicts heuristic; it reaches arrangements that placing lessons one at a
    time cannot, because it can move a lesson that was placed correctly earlier.

    Some clashes are arithmetic rather than bad luck — a teacher owed more hours than
    the timetable has slots for them can never be untangled — so this stops when no
    improving swap is left rather than pretending it can always reach zero.

    Returns (remaining_clash_hours, swaps_applied).
    """
    def teacher_at(cn, slot):
        cell = grids[cn][slot[0]][slot[1]]
        if cell is None or cell.get("is_blocked"):
            return ""
        return norm_teacher(cell.get("teacher", ""))

    # (teacher, slot) -> how many classes want them then
    load = defaultdict(int)
    for cn in grids:
        for d in range(D):
            for p in range(P):
                tk = teacher_at(cn, (d, p))
                if tk:
                    load[(tk, (d, p))] += 1

    def clash_hours():
        return sum(v - 1 for v in load.values() if v > 1)

    def blocked(tk, slot):
        return slot in teacher_timeoff.get(tk, ()) or (
            tk in cross_inst_map and slot in cross_inst_map[tk])

    swaps = 0
    for _round in range(rounds):
        # Work on an hour that is actually contended.
        hot = [(tk, s) for (tk, s), n in load.items() if n > 1]
        if not hot:
            break
        random.shuffle(hot)

        improved = False
        for tk, slot in hot:
            holders = [cn for cn in grids if teacher_at(cn, slot) == tk]
            random.shuffle(holders)
            for cn in holders:
                grid = grids[cn]
                targets = [(d, p) for d in range(D) for p in range(P)
                           if (d, p) != slot and grid[d][p] is not None
                           and not grid[d][p].get("is_blocked")]
                random.shuffle(targets)

                for other in targets:
                    other_tk = teacher_at(cn, other)
                    if not other_tk or other_tk == tk:
                        continue
                    # Neither teacher may land on an hour they are closed for.
                    if blocked(tk, other) or blocked(other_tk, slot):
                        continue

                    before = (max(0, load[(tk, slot)] - 1)
                              + max(0, load[(other_tk, other)] - 1)
                              + max(0, load[(tk, other)] - 1)
                              + max(0, load[(other_tk, slot)] - 1))
                    after = (max(0, load[(tk, slot)] - 2)
                             + max(0, load[(other_tk, other)] - 2)
                             + max(0, load[(tk, other)])
                             + max(0, load[(other_tk, slot)]))
                    if after >= before:
                        continue

                    grid[slot[0]][slot[1]], grid[other[0]][other[1]] = (
                        grid[other[0]][other[1]], grid[slot[0]][slot[1]])
                    load[(tk, slot)] -= 1
                    load[(other_tk, other)] -= 1
                    load[(tk, other)] += 1
                    load[(other_tk, slot)] += 1
                    swaps += 1
                    improved = True
                    break
                if improved:
                    break
            if improved:
                break

        if not improved:
            break  # no swap improves anything — this is as settled as it gets

    return clash_hours(), swaps


class _AlwaysFreeTeachers(dict):
    """Stand-in for the teacher-busy map that reports every teacher as free.

    Used only by "Sınıfları Bağımsız Doldur". Returning a NEW empty set on every read
    means the placement passes see no clash, and the `.add(...)` they perform on the
    returned set simply goes nowhere — so the mode needs no special cases anywhere
    else in the scheduler.
    """

    def __getitem__(self, key):
        return set()

    def get(self, key, default=None):
        return set()

    def __contains__(self, key):
        return False


def check_feasibility(data_store, institution_slug=None):
    """Says whether a full timetable is possible BEFORE spending time building one.

    This is the step the app was missing. It would run, produce a grid with holes,
    and leave the user guessing whether the scheduler had failed or the schedule was
    impossible — two very different problems with very different fixes. Professional
    timetabling tools check first and refuse to start on input that cannot work.

    Three independent limits are tested, each of which caps the result on its own:

      1. Demand vs cells   — more lesson-hours assigned than the open grid can hold.
      2. Cover per hour    — every open hour needs one teacher per open class; if
                             fewer are available then, those cells cannot be filled.
      3. Load per teacher  — a teacher can be in one class at a time, so their hours
                             cannot exceed the hours they are actually available.

    Returns a dict with a 'max_fillable' figure and the specific problems behind it.
    """
    settings = data_store.get("settings", {}) or {}
    days = settings.get("days")
    if not days:
        count = int(settings.get("day_count", data_store.get("gun_sayisi", 5)))
        days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"][:count]
    D = len(days)
    P = int(settings.get("periods", data_store.get("ders_saati", 8))) or 8

    blocked_by_class, _ = _build_class_timeoff_map(data_store)
    teacher_timeoff, _ = _build_teacher_timeoff_map(data_store, institution_slug)

    classes = [(c.get("ad") or c.get("name") or "").strip()
               for c in data_store.get("siniflar", []) or [] if isinstance(c, dict)]
    classes = [c for c in classes if c]

    open_by_class = {}
    for cn in classes:
        shut = blocked_by_class.get(cn, set())
        open_by_class[cn] = {(d, p) for d in range(D) for p in range(P) if (d, p) not in shut}

    total_cells = sum(len(v) for v in open_by_class.values())

    load = defaultdict(int)
    display = {}
    for a in data_store.get("atamalar", []) or []:
        if not isinstance(a, dict):
            continue
        name = format_tr_name(a.get("teacher") or a.get("ogretmen") or a.get("teacher_name") or "")
        tk = norm_teacher(name)
        if not tk:
            continue
        display.setdefault(tk, name)
        raw_type = str(a.get("type") or a.get("dagilim") or "").strip()
        hours = sum(parse_distribution_parts(
            raw_type, lesson_hours.hours(a) or 2))
        raw_c = (a.get("class") or a.get("sinif") or a.get("class_name") or "").strip()
        for cn in classes:
            if matches_class(raw_c, cn):
                load[tk] += hours

    total_demand = sum(load.values())

    # 2 — cover per hour
    understaffed = []
    cover_gap = 0
    for d in range(D):
        for p in range(P):
            slot = (d, p)
            need = sum(1 for cn in classes if slot in open_by_class[cn])
            if not need:
                continue
            free = sum(1 for tk in load if slot not in teacher_timeoff.get(tk, ()))
            if free < need:
                cover_gap += need - free
                understaffed.append({
                    "day": d, "period": p, "needed": need, "available": free,
                    "shortfall": need - free,
                })
    understaffed.sort(key=lambda x: -x["shortfall"])

    # 3 — load per teacher
    overloaded = []
    load_gap = 0
    for tk, assigned in load.items():
        usable = {s for s in set().union(*open_by_class.values()) if open_by_class} if classes else set()
        usable = {s for s in usable if s not in teacher_timeoff.get(tk, ())}
        cap = len(usable)
        if assigned > cap:
            load_gap += assigned - cap
            overloaded.append({
                "teacher": display.get(tk, tk), "assigned": assigned,
                "available": cap, "shortfall": assigned - cap,
            })
    overloaded.sort(key=lambda x: -x["shortfall"])

    # The binding limit is whichever bites hardest; they are not additive.
    max_fillable = min(total_cells, total_demand, total_demand - load_gap,
                       total_cells - cover_gap)

    idle = []
    for t in data_store.get("ogretmenler", []) or []:
        if not isinstance(t, dict):
            continue
        name = (t.get("ad") or t.get("name") or "").strip()
        if name and norm_teacher(name) not in load:
            idle.append(name)

    return {
        "ok": max_fillable >= min(total_cells, total_demand),
        "classes": len(classes),
        "open_hours_per_class": len(open_by_class[classes[0]]) if classes else 0,
        "total_cells": total_cells,
        "total_demand": total_demand,
        "max_fillable": max_fillable,
        "teachers_with_lessons": len(load),
        "idle_teachers": idle,
        "understaffed_slots": understaffed,
        "overloaded_teachers": overloaded,
        "days": days,
    }


def analyse_teacher_capacity(class_blocks, blocked_by_class, teacher_timeoff,
                             cross_inst_map, D, P):
    """Which teachers are assigned more hours than they can physically work.

    This is almost always the real reason a week will not fill, and it is invisible
    from the assignment screen: that screen shows hours per CLASS, and a class can
    look perfectly balanced (20 hours assigned, 20 open) while the schedule is still
    impossible.

    The limit is per TEACHER. A teacher can be in one class at a time, so their
    ceiling is the number of hours where they are free AND at least one of their
    classes is open. Assign more than that and the surplus cannot be placed by any
    algorithm — no amount of searching creates an hour that does not exist.

    Returns a list of dicts, worst first, each naming the teacher, the hours assigned
    to them, the hours actually available, and the shortfall.
    """
    # teacher -> hours assigned, and which classes they teach
    hours = defaultdict(int)
    classes_of = defaultdict(set)
    display_of = {}
    for cn, blocks in class_blocks.items():
        for blk in blocks:
            name = blk.get("teacher") or ""
            key = norm_teacher(name)
            if not key:
                continue
            hours[key] += int(blk.get("duration", 1) or 1)
            classes_of[key].add(cn)
            display_of.setdefault(key, name)

    report = []
    for key, assigned in hours.items():
        # Hours this teacher could actually teach: free for them, and at least one
        # of their own classes is open then.
        usable = set()
        for cn in classes_of[key]:
            shut = blocked_by_class.get(cn, set())
            for d in range(D):
                for p in range(P):
                    slot = (d, p)
                    if slot in shut:
                        continue
                    if slot in teacher_timeoff.get(key, ()):
                        continue
                    if key in cross_inst_map and slot in cross_inst_map[key]:
                        continue
                    usable.add(slot)
        available = len(usable)
        if assigned > available:
            report.append({
                "teacher": display_of.get(key, key),
                "assigned": assigned,
                "available": available,
                "shortfall": assigned - available,
                "classes": sorted(classes_of[key]),
            })

    report.sort(key=lambda r: -r["shortfall"])
    return report


def _reserve_scarce_hours(classes, grids, pending_by_class, teacher_busy,
                          teacher_timeoff, cross_inst_map, teacher_pool, D, P):
    """Fills the hours with the fewest available teachers, before anything else.

    A week's fill rate is capped by its tightest hours, not its average. When only
    five teachers can work Friday first period but nine classes are open then, four
    of those cells can never be filled — and if one of those five teachers has
    already been booked into an hour where six others could have covered, a fifth
    cell is lost too, for no reason.

    So the tight hours are claimed first, matched optimally across every class at
    once. Hours with plenty of slack are left to the ordinary block placement, which
    keeps multi-hour lessons contiguous.

    Only hours where availability is genuinely short are touched; everything else is
    left alone so this does not fragment lessons that could have been placed as
    proper 2-hour blocks.
    """
    # How many teachers can work each hour at all.
    availability = {}
    for d in range(D):
        for p in range(P):
            slot = (d, p)
            free = 0
            for tk in teacher_pool:
                if slot in teacher_timeoff.get(tk, ()):
                    continue
                if tk in cross_inst_map and slot in cross_inst_map[tk]:
                    continue
                free += 1
            availability[slot] = free

    def _open_classes(slot):
        d, p = slot
        return [
            cn for cn in classes
            if grids.get(cn) is not None
            and grids[cn][d][p] is None
            and pending_by_class.get(cn)
        ]

    # Only the hours that are actually contended: fewer teachers free than classes
    # needing one. Sorted tightest-first so the very scarcest is served before an
    # hour that merely happens to be a little short.
    tight = []
    for slot, free in availability.items():
        needed = len(_open_classes(slot))
        if needed and free < needed:
            tight.append((free - needed, free, slot))
    if not tight:
        return
    tight.sort()

    for _deficit, _free, slot in tight:
        open_here = _open_classes(slot)
        if not open_here:
            continue
        matched = _match_slot(
            open_here, slot, grids, pending_by_class,
            teacher_busy, teacher_timeoff, cross_inst_map, P,
        )
        d, p = slot
        for cn, (blk, subject, teacher) in matched.items():
            grids[cn][d][p] = {
                "subject": subject, "teacher": teacher,
                "block_id": f"tight_{_uuid.uuid4().hex[:8]}",
                "is_combined": False, "block_start": p, "is_filler": False,
            }
            tk = norm_teacher(teacher)
            if tk:
                teacher_busy[tk].add(slot)
            pending = pending_by_class.get(cn) or []
            if blk["duration"] > 1:
                blk["duration"] -= 1
            elif blk in pending:
                pending.remove(blk)


BLOCKED_CELL = {
    "subject": None,
    "teacher": "",
    "block_id": "__blocked__",
    "is_blocked": True,
    "block_start": -1,
}


def _build_class_timeoff_map(data_store: dict) -> tuple:
    """Closed and avoid slots per CLASS.

    Each class is read individually through constraint_sync, which merges the two
    stored representations (entity["timeoff"] and data_store["kisitlamalar"]) and
    keeps the more restrictive value when they disagree. That matters because one
    class ending after the 4th period and another after the 5th is exactly the kind
    of per-class difference that gets flattened when only one representation is read.

    Returns (blocked, avoid): both {class_name: {(day, period), ...}}.
    """
    import constraint_sync

    blocked = defaultdict(set)
    avoid = defaultdict(set)

    for cls in data_store.get("siniflar", []) or []:
        if not isinstance(cls, dict):
            continue
        name = (cls.get("ad") or cls.get("name") or "").strip()
        if not name:
            continue
        matrix = constraint_sync.get_matrix(cls, name, data_store)
        for d in range(len(matrix)):
            for p in range(len(matrix[d])):
                state = matrix[d][p]
                if state == constraint_sync.CLOSED:
                    blocked[name].add((d, p))
                elif state == constraint_sync.AVOID:
                    avoid[name].add((d, p))

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


def _build_cross_institution_map(institution_slug: str) -> tuple:
    """Hours a teacher is already teaching at OTHER institutions.

    Keyed by norm_teacher() so "H.barış Karataş" at one branch matches
    "H.Barış Karataş" at another — the previous format_tr_name() key only
    capitalized, so most real-world spelling differences silently missed and the
    conflict was never seen.

    Returns (occupied, details):
      occupied -> {norm_teacher: {(day, period), ...}}
      details  -> {(norm_teacher, day, period): {institution, class, subject}}
    """
    occupied = defaultdict(set)
    details = {}
    try:
        import version_store
        for inst in version_store.list_institutions():
            s = inst.get("slug", "")
            if s == institution_slug or not s:
                continue
            active = version_store.get_active_version(s)
            if not active:
                continue
            data = version_store.load_version(s, active)
            if not data:
                continue
            inst_name = inst.get("name", s)
            for p in data.get("grid_placements", []) or []:
                raw_name = p.get("teacher_name") or p.get("teacher") or ""
                key = norm_teacher(raw_name)
                if not key:
                    continue
                try:
                    d = int(p.get("day", p.get("col", -1)))
                    per = int(p.get("period", p.get("row", -1)))
                    dur = int(p.get("duration", 1))
                except (TypeError, ValueError):
                    continue
                if d < 0 or per < 0:
                    continue
                for off in range(dur):
                    slot = (d, per + off)
                    occupied[key].add(slot)
                    details.setdefault((key, d, per + off), {
                        "institution": inst_name,
                        "class": p.get("class_name") or p.get("class") or "",
                        "subject": p.get("subject_name") or p.get("subject") or "",
                    })
    except Exception as e:
        print(f"[AutoScheduler] Cross-institution map error: {e}")
    return dict(occupied), details


# ─────────────────────────────────────────────────────────────────────────────
# TAM DOLDURMA
#
# Sezgisel geçişler bloğu tek tek ve geri dönüşsüz yerleştirir: bir sınıfa erken
# verilen saat, sonradan sıkışan bir öğretmenin tek boş saati çıkar ve o dersin
# yerleşecek yeri kalmaz. Grid 171/180'de takılır, oysa çizelge matematiksel
# olarak tamamen doldurulabilir durumdadır.
#
# Aşağıdaki arama aynı işi geri izlemeli olarak yapar:
#   1) her blok ÖNCE bir güne atanır — sınıfın o gün kaç açık saati, öğretmenin
#      o gün kaç müsait saati varsa o kadar (tavlama benzetimi),
#   2) sonra her gün kendi içinde çözülür: o günün blokları açık saatlere,
#      2 saatlikler bitişik kalacak ve hiçbir öğretmen aynı saatte iki sınıfta
#      olmayacak şekilde dizilir (tam geri izleme).
# Bir gün çözülemezse gün dağıtımı yeniden denenir. Sonuç ya EKSİKSİZ bir
# çizelgedir ya da None: yarım sonuç döndürülmez, çünkü sezgisel sonuç zaten
# elde vardır ve bu arama yalnızca onu geçmek için çalışır.
# ─────────────────────────────────────────────────────────────────────────────
def _day_layouts(open_periods, blocks, tk_free, day, cap=600, rng=None,
                 allow_gaps=False):
    """Bir sınıfın bir gününe düşen blokların o günün açık saatlerine dizilişleri.

    Her diziliş {saat: blok} sözlüğüdür. Bir blok ancak açık ve ardışık saatlere,
    öğretmeni o saatlerde müsaitse konur.

    allow_gaps=False (varsayılan): dersler günün BAŞINDAN itibaren sıkışık dizilir,
    boş saatler yalnızca günün sonunda kalır. Bunun iki sebebi var:
      * sınıf günün ortasında boş saat görmez, erken çıkar — istenen budur,
      * arama uzayı küçülür. Sınıfa 5 saat açıp 4 saat ders atandığında, boş saati
        günün herhangi bir yerine koymayı denemek dizilişleri katlıyordu; arama
        düğüm bütçesini aşıp EKSİKSİZ çözümü hiç bulamıyor ve sezgisel sonuca
        düşüyordu. "5. saati açtım, artık dolduramıyor" şikâyetinin sebebi buydu.
    allow_gaps=True: sıkışık diziliş bir günü çözemezse ikinci deneme için açılır.
    """
    ops = sorted(open_periods)
    out, assign = [], {}
    order = list(blocks)
    if rng:
        rng.shuffle(order)
    used = [False] * len(order)

    def rec(i):
        if len(out) >= cap:
            return
        if i == len(ops):
            # Bir gün ancak O GÜNE düşen bütün blokları yerleştirebiliyorsa
            # geçerlidir; yarım diziliş üretmek, aramanın eksik bir çizelgeyi
            # "eksiksiz" sanmasına yol açardı.
            if all(used):
                out.append(dict(assign))
            return
        p = ops[i]
        seen = set()
        for j, b in enumerate(order):
            if used[j]:
                continue
            sig = (b.get("subject"), b.get("teacher"), b.get("duration"))
            if sig in seen:          # aynı görünümlü blokları tekrar denemeyelim
                continue
            seen.add(sig)
            k = max(1, int(b.get("duration") or 1))
            if i + k > len(ops) or any(ops[i + o] != p + o for o in range(k)):
                continue             # bitişik açık saat yok
            tk = norm_teacher(b.get("teacher") or "")
            if tk and not all(tk_free(tk, day, p + o) for o in range(k)):
                continue
            used[j] = True
            for o in range(k):
                assign[p + o] = b
            rec(i + k)
            used[j] = False
            for o in range(k):
                assign.pop(p + o, None)
        remaining = sum(max(1, int(b.get("duration") or 1))
                        for j, b in enumerate(order) if not used[j])
        if remaining == 0 or (allow_gaps and remaining < len(ops) - i):
            # remaining == 0: bütün bloklar yerleşti, günün kalanı boş kalabilir.
            rec(i + 1)

    rec(0)
    if rng:
        rng.shuffle(out)
    return out


def _solve_one_day(day_layouts, base_busy_day, rng, budget=200000):
    """Bir günün bütün sınıflarına birer diziliş seçer; öğretmen çakışması olmaz."""
    classes = sorted(day_layouts, key=lambda c: len(day_layouts[c]))
    busy = {p: set(v) for p, v in base_busy_day.items()}
    chosen, nodes = {}, [0]

    def rec(i):
        if i == len(classes):
            return True
        if nodes[0] > budget:
            return False
        cn = classes[i]
        for lay in day_layouts[cn]:
            nodes[0] += 1
            keys = [(p, norm_teacher(b.get("teacher") or ""))
                    for p, b in lay.items()]
            if any(tk and tk in busy.setdefault(p, set()) for p, tk in keys):
                continue
            for p, tk in keys:
                if tk:
                    busy[p].add(tk)
            chosen[cn] = lay
            if rec(i + 1):
                return True
            for p, tk in keys:
                if tk:
                    busy[p].discard(tk)
            chosen.pop(cn, None)
        return False

    return chosen if rec(0) else None


def solve_cpsat(classes_to_schedule, assignments_or_blocks, blocked_by_class, avoid_by_class,
                teacher_timeoff, teacher_avoid, cross_inst_map, global_teacher_busy,
                D, P, time_limit=5.0, independent_classes=False, planning_relations=None,
                locked_placements=None, progress_callback=None):
    """
    Google OR-Tools CP-SAT Timetable Solver.
    Guarantees 100% mathematical optimum and conflict-free placement in < 1 second.
    Enforces class constraints, teacher timeoff, cross-institution reserved hours,
    all user-defined Planning Relations, and preserves existing locked/pinned placements.
    Returns (placements_list, total_placed_hours, elapsed_time_seconds, status_str)
    """
    import time
    import uuid
    from collections import defaultdict
    import lesson_hours
    
    t0 = time.time()
    
    try:
        from ortools.sat.python import cp_model
    except Exception as e:
        print(f"[AutoScheduler] ortools yuklenirken hata olustu: {e}")
        return None, 0, 0.0, "ORTOOLS_MISSING"

    class _CpsatProgressBridge(cp_model.CpSolverSolutionCallback):
        def __init__(self, r_blocks, x_vars, d_cnt, p_cnt, tot_target, cb):
            super().__init__()
            self._r_blocks = r_blocks
            self._x_vars = x_vars
            self._d_cnt = d_cnt
            self._p_cnt = p_cnt
            self._tot_target = tot_target
            self._cb = cb

        def on_solution_callback(self):
            if not callable(self._cb):
                return
            try:
                cur_placed = 0
                for b in self._r_blocks:
                    bid, dur = b["id"], b["duration"]
                    for d in range(self._d_cnt):
                        for p in range(self._p_cnt - dur + 1):
                            if (bid, d, p) in self._x_vars and self.Value(self._x_vars[bid, d, p]) == 1:
                                cur_placed += dur * len(b["classes"])
                                break
                self._cb(cur_placed, self._tot_target)
            except Exception:
                pass

    raw_blocks = []
    
    # Check if assignments_or_blocks is list of assignments or dict of class_blocks
    if isinstance(assignments_or_blocks, list):
        for asgn in assignments_or_blocks:
            if not isinstance(asgn, dict):
                continue
            raw_c = (asgn.get("class") or asgn.get("sinif") or asgn.get("class_name") or "").strip()
            if not raw_c:
                continue
            target_cls = [cn for cn in classes_to_schedule if matches_class(raw_c, cn)]
            if not target_cls:
                continue
                
            t_name = format_tr_name(asgn.get("ogretmen") or asgn.get("teacher") or asgn.get("teacher_name") or "")
            s_name = (asgn.get("ders") or asgn.get("subject") or "").strip()
            raw_type = str(asgn.get("dagilim") or asgn.get("type") or "").strip()
            h_dur = lesson_hours.hours(asgn) or 2
            is_comb = bool(asgn.get("is_combined") or len(target_cls) > 1 or "+" in raw_c or "&" in raw_c or "," in raw_c)
            durs = parse_distribution_parts(raw_type, h_dur)
            
            for dur in durs:
                bid = f"b_{uuid.uuid4().hex[:8]}"
                if is_comb and len(target_cls) > 1:
                    raw_blocks.append({
                        "id": len(raw_blocks),
                        "classes": target_cls,
                        "subject": s_name,
                        "teacher": t_name,
                        "duration": dur,
                        "is_combined": True,
                        "block_id": bid,
                        "tk": norm_teacher(t_name)
                    })
                else:
                    for cn in target_cls:
                        raw_blocks.append({
                            "id": len(raw_blocks),
                            "classes": [cn],
                            "subject": s_name,
                            "teacher": t_name,
                            "duration": dur,
                            "is_combined": False,
                            "block_id": bid,
                            "tk": norm_teacher(t_name)
                        })
    elif isinstance(assignments_or_blocks, dict):
        by_bid = {}
        for cn in classes_to_schedule:
            for b in assignments_or_blocks.get(cn, []):
                bid = b.get("block_id") or f"b_{uuid.uuid4().hex[:8]}"
                t_name = format_tr_name(b.get("teacher") or b.get("teacher_name") or "")
                s_name = (b.get("subject") or b.get("subject_name") or "").strip()
                dur = max(1, int(b.get("duration") or 1))
                is_comb = bool(b.get("is_combined", False))
                if bid not in by_bid:
                    by_bid[bid] = {
                        "id": len(by_bid),
                        "classes": [cn],
                        "subject": s_name,
                        "teacher": t_name,
                        "duration": dur,
                        "is_combined": is_comb,
                        "block_id": bid,
                        "tk": norm_teacher(t_name)
                    }
                else:
                    if cn not in by_bid[bid]["classes"]:
                        by_bid[bid]["classes"].append(cn)
        raw_blocks = list(by_bid.values())

    if not raw_blocks:
        return [], 0, 0.0, "EMPTY"

    total_assigned_hours = sum(b["duration"] * len(b["classes"]) for b in raw_blocks)
    blocked_by_class = blocked_by_class or {}
    avoid_by_class = avoid_by_class or {}
    teacher_timeoff = teacher_timeoff or {}
    teacher_avoid = teacher_avoid or {}
    cross_inst_map = cross_inst_map or {}
    global_teacher_busy = global_teacher_busy or {}

    # Bind locked/pinned placements with contiguous block merging
    locked_block_bindings = {}  # block_id -> (day, period)
    if locked_placements:
        # First merge contiguous slices of same lesson
        lk_groups = defaultdict(list)
        for p in locked_placements:
            lp_cn = (p.get("class_name") or p.get("class") or "").strip()
            lp_s = (p.get("subject_name") or p.get("subject") or "").strip().lower()
            lp_t = norm_teacher(p.get("teacher_name") or p.get("teacher") or "")
            lp_d = int(p.get("day", p.get("col", 0)))
            lp_p = int(p.get("period", p.get("row", 0)))
            lp_dur = int(p.get("duration", 1))
            lk_groups[(lp_cn, lp_s, lp_t, lp_d)].append((lp_p, lp_dur, p))

        merged_locked = []
        for (lp_cn, lp_s, lp_t, lp_d), items in lk_groups.items():
            items.sort(key=lambda x: x[0])
            i = 0
            while i < len(items):
                cur_p, cur_dur, orig = items[i]
                span = cur_dur
                j = i + 1
                while j < len(items) and items[j][0] == cur_p + span:
                    span += items[j][1]
                    j += 1
                new_item = dict(orig)
                new_item["day"] = lp_d
                new_item["period"] = cur_p
                new_item["duration"] = span
                merged_locked.append(new_item)
                i = j

        for lp in merged_locked:
            lp_cn = (lp.get("class_name") or lp.get("class") or "").strip()
            lp_s = (lp.get("subject_name") or lp.get("subject") or "").strip().lower()
            lp_t = norm_teacher(lp.get("teacher_name") or lp.get("teacher") or "")
            lp_d = int(lp.get("day", lp.get("col", 0)))
            lp_p = int(lp.get("period", lp.get("row", 0)))
            lp_dur = int(lp.get("duration", 1))

            # Zaman Tablosu mutlak esastır: Kilitli hücre kapalı saate denk geliyorsa kilidi yok say
            if any((lp_d, lp_p + off) in blocked_by_class.get(lp_cn, set()) for off in range(lp_dur)):
                continue
            if lp_t and any((lp_d, lp_p + off) in teacher_timeoff.get(lp_t, set()) for off in range(lp_dur)):
                continue

            for b in raw_blocks:
                bid = b["id"]
                if bid in locked_block_bindings:
                    continue
                if b["duration"] == lp_dur and any(matches_class(cn, lp_cn) for cn in b["classes"]):
                    if b["subject"].strip().lower() == lp_s and (not lp_t or b["tk"] == lp_t):
                        locked_block_bindings[bid] = (lp_d, lp_p)
                        break

    def _norm_s(s: str) -> str:
        return normalize_clean(s or "").strip().lower()

    def _match_relation_subject(subj_name: str, filter_subjs: list) -> bool:
        if not filter_subjs:
            return True
        sn = _norm_s(subj_name)
        for f in filter_subjs:
            fn = _norm_s(f)
            if fn == sn or fn in sn or sn in fn:
                return True
        return False

    def _match_relation_class(class_name: str, filter_classes: list) -> bool:
        if not filter_classes:
            return True
        for fc in filter_classes:
            if matches_class(class_name, fc) or matches_class(fc, class_name):
                return True
        return False

    def _match_relation_teacher(teacher_name: str, filter_teachers: list) -> bool:
        if not filter_teachers:
            return True
        tn = norm_teacher(teacher_name)
        for ft in filter_teachers:
            if norm_teacher(ft) == tn:
                return True
        return False

    def _is_practical_subject(name: str) -> bool:
        norm = normalize_clean(name or "").upper()
        return any(k in norm for k in ["BEDEN", "MUZIK", "MÜZİK", "GORSEL", "GÖRSEL", "RESIM", "RESİM", "SANAT", "SPOR", "UYGULAMA", "ATOLYE", "ATÖLYE"])

    def _is_slot_forbidden_by_relations(b: dict, d: int, p: int, dur: int) -> bool:
        s_name = b["subject"]
        t_name = b["teacher"]
        classes = b["classes"]
        HARD_KEYWORDS = ["MAT", "FİZ", "FIZ", "KİM", "KIM", "BİYO", "BIYO", "GEO", "FEN"]

        for rel in (planning_relations or []):
            if not rel.get("aktif", True):
                continue
            r_type = rel.get("kural", "")
            f_subjs = rel.get("dersler", [])
            f_teach = rel.get("ogretmenler", [])
            f_classes = rel.get("siniflar", [])

            if f_classes and not any(_match_relation_class(cn, f_classes) for cn in classes):
                continue
            if f_teach and not _match_relation_teacher(t_name, f_teach):
                continue
            if f_subjs and not _match_relation_subject(s_name, f_subjs):
                continue

            if "öğleden önce toplansın" in r_type or "Sabah" in r_type:
                noon_p = 4 if P >= 6 else (P + 1) // 2
                if p + dur > noon_p:
                    return True
            elif "öğleden sonra toplansın" in r_type:
                noon_p = 4 if P >= 6 else P // 2
                if p < noon_p:
                    return True
            elif "Son ders saatine zor ders" in r_type:
                is_hard = any(k in _norm_s(s_name).upper() for k in HARD_KEYWORDS) or bool(f_subjs)
                if is_hard and (p + dur > P - 1):
                    return True
            elif "belirli saatlerde kalmalı" in r_type or "saatlerde kalmalı" in r_type:
                p_start = (rel.get("period_start") or 1) - 1
                p_end = (rel.get("period_end") or P) - 1
                if p < p_start or (p + dur - 1) > p_end:
                    return True
        return False

    def _get_block_day_sessions(bid: str, d: int, block_solvers: dict) -> list:
        meta = block_solvers.get(bid, {})
        res = []
        dur = meta.get("type", 1)
        if dur == 1:
            for v, d_i, _ in meta.get("vars_1h", []):
                if d_i == d: res.append(v)
        elif dur == 2:
            for v2, d_i, _ in meta.get("vars_2h", []):
                if d_i == d: res.append(v2)
            for vh1, d_i, _ in meta.get("vars_s1", []):
                if d_i == d: res.append(vh1)
            for vh2, d_i, _ in meta.get("vars_s2", []):
                if d_i == d: res.append(vh2)
        elif dur >= 3:
            u_splits = meta.get("vars_u", [])
            if u_splits:
                for vu, d_i, _ in u_splits[0]:
                    if d_i == d: res.append(vu)
        return res

    def _get_block_day_hours(bid: str, d: int, block_solvers: dict) -> list:
        meta = block_solvers.get(bid, {})
        res = []
        dur = meta.get("type", 1)
        if dur == 1:
            for v, d_i, _ in meta.get("vars_1h", []):
                if d_i == d: res.append((v, 1))
        elif dur == 2:
            for v2, d_i, _ in meta.get("vars_2h", []):
                if d_i == d: res.append((v2, 2))
            for vh1, d_i, _ in meta.get("vars_s1", []):
                if d_i == d: res.append((vh1, 1))
            for vh2, d_i, _ in meta.get("vars_s2", []):
                if d_i == d: res.append((vh2, 1))
        elif dur >= 3:
            for u_list in meta.get("vars_u", []):
                for vu, d_i, _ in u_list:
                    if d_i == d: res.append((vu, 1))
        return res

    def _apply_planning_relations_constraints(model, raw_blocks, block_solvers, is_phase1=True, obj_list=None):
        class_subj_blocks = defaultdict(lambda: defaultdict(list))
        for b in raw_blocks:
            s_norm = _norm_s(b["subject"])
            for cn in b["classes"]:
                class_subj_blocks[cn][s_norm].append(b)

        # 1. TEMEL KURAL: "Aynı ders aynı gün tekrar etmesin" / Günlük Yayılım
        for cn in classes_to_schedule:
            for s_norm, b_list in class_subj_blocks[cn].items():
                tot_hours = sum(b["duration"] for b in b_list)
                tot_blocks = len(b_list)
                max_daily_hours = max(2, (tot_hours + D - 1) // D)
                max_sessions_per_day = max(1, (tot_blocks + D - 1) // D)
                
                for d in range(D):
                    # Günlük saat sınırı (Örn: 2+2 Matematik veya 8 saat İngilizce için günde en fazla 2 saat)
                    day_hours = []
                    for b in b_list:
                        for v, h in _get_block_day_hours(b["id"], d, block_solvers):
                            day_hours.append(v * h)
                    if day_hours:
                        if is_phase1:
                            model.Add(sum(day_hours) <= max_daily_hours)
                        elif obj_list is not None:
                            exc = model.NewIntVar(0, P, f"exc_dh_{cn}_{s_norm}_{d}")
                            model.Add(exc >= sum(day_hours) - max_daily_hours)
                            obj_list.append(exc * (-25000))

                    # Günlük ayrı blok/oturum sınırı (Örn: 2+2 Matematik aynı güne 2 ayrı parça konulamaz)
                    day_sessions = []
                    for b in b_list:
                        day_sessions.extend(_get_block_day_sessions(b["id"], d, block_solvers))
                    if len(day_sessions) > 1:
                        if is_phase1:
                            model.Add(sum(day_sessions) <= max_sessions_per_day)
                        elif obj_list is not None:
                            exc = model.NewIntVar(0, len(day_sessions), f"exc_ds_{cn}_{s_norm}_{d}")
                            model.Add(exc >= sum(day_sessions) - max_sessions_per_day)
                            obj_list.append(exc * (-25000))

        for rel in (planning_relations or []):
            if not rel.get("aktif", True):
                continue
            r_type = rel.get("kural", "")
            val = rel.get("parametre", 2)
            f_subjs = rel.get("dersler", [])
            f_teach = rel.get("ogretmenler", [])
            f_classes = rel.get("siniflar", [])
            is_strict = (rel.get("onem") == "Sıkı (Kesinlikle uygulanmalı)" or not rel.get("onem"))

            if "Günde maksimum" in r_type or "Günlük maksimum" in r_type or "maksimum ders" in r_type:
                max_h = int(val) if str(val).isdigit() else 2
                for cn in classes_to_schedule:
                    if not _match_relation_class(cn, f_classes): continue
                    for d in range(D):
                        day_hours = []
                        for b in raw_blocks:
                            if cn in b["classes"] and _match_relation_subject(b["subject"], f_subjs) and _match_relation_teacher(b["teacher"], f_teach):
                                for v, h in _get_block_day_hours(b["id"], d, block_solvers):
                                    day_hours.append(v * h)
                        if day_hours:
                            if is_phase1 or is_strict:
                                model.Add(sum(day_hours) <= max_h)
                            elif obj_list is not None:
                                exc = model.NewIntVar(0, P, f"excm_h_{cn}_{d}")
                                model.Add(exc >= sum(day_hours) - max_h)
                                obj_list.append(exc * (-15000))

            elif "Uygulamalı dersler" in r_type or "Beden Eğitimi" in r_type:
                max_h = int(val) if str(val).isdigit() else 2
                for cn in classes_to_schedule:
                    if not _match_relation_class(cn, f_classes): continue
                    for d in range(D):
                        day_hours = []
                        for b in raw_blocks:
                            if cn in b["classes"] and (_is_practical_subject(b["subject"]) or _match_relation_subject(b["subject"], f_subjs)):
                                for v, h in _get_block_day_hours(b["id"], d, block_solvers):
                                    day_hours.append(v * h)
                        if day_hours:
                            if is_phase1 or is_strict:
                                model.Add(sum(day_hours) <= max_h)
                            elif obj_list is not None:
                                exc = model.NewIntVar(0, P, f"excm_prac_{cn}_{d}")
                                model.Add(exc >= sum(day_hours) - max_h)
                                obj_list.append(exc * (-15000))

            elif "aynı güne gelmesin" in r_type or "İki ders aynı güne" in r_type:
                target_subjs = f_subjs if f_subjs else []
                if len(target_subjs) >= 2:
                    for cn in classes_to_schedule:
                        if not _match_relation_class(cn, f_classes): continue
                        for d in range(D):
                            subj_indicators = []
                            for s_name in target_subjs:
                                s_sessions = []
                                for b in raw_blocks:
                                    if cn in b["classes"] and _match_relation_subject(b["subject"], [s_name]):
                                        s_sessions.extend(_get_block_day_sessions(b["id"], d, block_solvers))
                                if s_sessions:
                                    y = model.NewBoolVar(f"y_excl_{cn}_{_norm_s(s_name)}_{d}")
                                    model.Add(sum(s_sessions) <= len(s_sessions) * y)
                                    model.Add(sum(s_sessions) >= y)
                                    subj_indicators.append(y)
                            if len(subj_indicators) >= 2:
                                if is_phase1 or is_strict:
                                    model.Add(sum(subj_indicators) <= 1)
                                elif obj_list is not None:
                                    exc = model.NewIntVar(0, len(subj_indicators), f"exc_excl_{cn}_{d}")
                                    model.Add(exc >= sum(subj_indicators) - 1)
                                    obj_list.append(exc * (-20000))

            elif "eşit dağıtılsın" in r_type or "günlerine eşit" in r_type:
                for cn in classes_to_schedule:
                    if not _match_relation_class(cn, f_classes): continue
                    for s_norm, b_list in class_subj_blocks[cn].items():
                        if f_subjs and not _match_relation_subject(s_norm, f_subjs): continue
                        tot_blocks = len(b_list)
                        min_distinct_days = min(D, tot_blocks)
                        day_y = []
                        for d in range(D):
                            s_sessions = []
                            for b in b_list:
                                s_sessions.extend(_get_block_day_sessions(b["id"], d, block_solvers))
                            if s_sessions:
                                y = model.NewBoolVar(f"y_spread_{cn}_{s_norm}_{d}")
                                model.Add(sum(s_sessions) <= len(s_sessions) * y)
                                model.Add(sum(s_sessions) >= y)
                                day_y.append(y)
                        if len(day_y) >= min_distinct_days:
                            if is_phase1:
                                model.Add(sum(day_y) >= min_distinct_days)
                            elif obj_list is not None:
                                obj_list.append(sum(day_y) * 5000)

            elif "İki zor ders art arda" in r_type:
                HARD_KEYWORDS = ["MAT", "FİZ", "FIZ", "KİM", "KIM", "BİYO", "BIYO", "GEO", "FEN"]
                for cn in classes_to_schedule:
                    if not _match_relation_class(cn, f_classes): continue
                    for d in range(D):
                        for p in range(P - 1):
                            hard_p = []
                            hard_p_next = []
                            for b in raw_blocks:
                                if cn in b["classes"]:
                                    is_h = any(k in _norm_s(b["subject"]).upper() for k in HARD_KEYWORDS) or _match_relation_subject(b["subject"], f_subjs)
                                    if is_h:
                                        dur_b = b["duration"]
                                        meta = block_solvers.get(b["id"], {})
                                        if dur_b == 1:
                                            for v, d_i, p_i in meta.get("vars_1h", []):
                                                if d_i == d and p_i == p: hard_p.append(v)
                                                if d_i == d and p_i == p + 1: hard_p_next.append(v)
                                        elif dur_b == 2:
                                            for vh1, d_i, p_i in meta.get("vars_s1", []):
                                                if d_i == d and p_i == p: hard_p.append(vh1)
                                                if d_i == d and p_i == p + 1: hard_p_next.append(vh1)
                                            for vh2, d_i, p_i in meta.get("vars_s2", []):
                                                if d_i == d and p_i == p: hard_p.append(vh2)
                                                if d_i == d and p_i == p + 1: hard_p_next.append(vh2)
                            if hard_p and hard_p_next:
                                if obj_list is not None:
                                    exc = model.NewIntVar(0, 2, f"exc_hard_bb_{cn}_{d}_{p}")
                                    model.Add(exc >= sum(hard_p) + sum(hard_p_next) - 1)
                                    obj_list.append(exc * (-5000))

    # ── FAZ 1: ESNEK BLOK DESTEKLİ %100 TAM YERLEŞTİRME (Exact Satisfaction) ──
    model1 = cp_model.CpModel()
    occ_class1 = defaultdict(list)
    occ_teacher1 = defaultdict(list)
    block_solvers1 = {}
    obj1 = []

    for b in raw_blocks:
        bid, dur, tk = b["id"], b["duration"], b["tk"]
        target_cls = b["classes"]
        block_solvers1[bid] = {"b": b, "type": dur}

        if dur == 1:
            u_vars = []
            for d in range(D):
                for p in range(P):
                    if bid in locked_block_bindings:
                        if (d, p) != locked_block_bindings[bid]: continue
                    if any((d, p) in blocked_by_class.get(cn, set()) for cn in target_cls): continue
                    if tk and not independent_classes:
                        if (d, p) in teacher_timeoff.get(tk, set()): continue
                        if (d, p) in global_teacher_busy.get(tk, set()): continue
                    elif tk and independent_classes:
                        if (d, p) in teacher_timeoff.get(tk, set()): continue
                    if _is_slot_forbidden_by_relations(b, d, p, 1): continue
                    
                    v = model1.NewBoolVar(f"x1_{bid}_1h_{d}_{p}")
                    u_vars.append((v, d, p))
                    for cn in target_cls: occ_class1[cn, d, p].append(v)
                    if tk and not independent_classes: occ_teacher1[tk, d, p].append(v)

                    pen = p * 2
                    if any((d, p) in avoid_by_class.get(cn, set()) for cn in target_cls): pen += 5
                    if tk and (d, p) in teacher_avoid.get(tk, set()): pen += 5
                    if tk and (d, p) in cross_inst_map.get(tk, set()): pen += 3000
                    if pen > 0: obj1.append(v * (-pen))
            
            if u_vars:
                model1.AddExactlyOne([v for v, _, _ in u_vars])
                block_solvers1[bid]["vars_1h"] = u_vars
            else:
                block_solvers1[bid]["unavail"] = True

        elif dur == 2:
            v_2h = []
            for d in range(D):
                for p in range(P - 1):
                    if bid in locked_block_bindings:
                        if (d, p) != locked_block_bindings[bid]: continue
                    if any((d, p + off) in blocked_by_class.get(cn, set()) for cn in target_cls for off in range(2)): continue
                    if tk and not independent_classes:
                        if any((d, p + off) in teacher_timeoff.get(tk, set()) for off in range(2)): continue
                        if any((d, p + off) in global_teacher_busy.get(tk, set()) for off in range(2)): continue
                    elif tk and independent_classes:
                        if any((d, p + off) in teacher_timeoff.get(tk, set()) for off in range(2)): continue
                    if _is_slot_forbidden_by_relations(b, d, p, 2): continue
                    
                    v2 = model1.NewBoolVar(f"x1_{bid}_2h_{d}_{p}")
                    v_2h.append((v2, d, p))
                    for cn in target_cls:
                        occ_class1[cn, d, p].append(v2)
                        occ_class1[cn, d, p + 1].append(v2)
                    if tk and not independent_classes:
                        occ_teacher1[tk, d, p].append(v2)
                        occ_teacher1[tk, d, p + 1].append(v2)
                    
                    pen = p * 2
                    if any((d, p + off) in avoid_by_class.get(cn, set()) for cn in target_cls for off in range(2)): pen += 5
                    if tk and any((d, p + off) in teacher_avoid.get(tk, set()) for off in range(2)): pen += 5
                    if tk and any((d, p + off) in cross_inst_map.get(tk, set()) for off in range(2)): pen += 3000
                    obj1.append(v2 * (50 - pen))

            v_s1, v_s2 = [], []
            if bid not in locked_block_bindings:
                for d in range(D):
                    for p in range(P):
                        if any((d, p) in blocked_by_class.get(cn, set()) for cn in target_cls): continue
                        if tk and not independent_classes:
                            if (d, p) in teacher_timeoff.get(tk, set()): continue
                            if (d, p) in global_teacher_busy.get(tk, set()): continue
                        elif tk and independent_classes:
                            if (d, p) in teacher_timeoff.get(tk, set()): continue
                        if _is_slot_forbidden_by_relations(b, d, p, 1): continue
                        
                        vh1 = model1.NewBoolVar(f"x1_{bid}_s1_{d}_{p}")
                        vh2 = model1.NewBoolVar(f"x1_{bid}_s2_{d}_{p}")
                        v_s1.append((vh1, d, p))
                        v_s2.append((vh2, d, p))
                        for cn in target_cls:
                            occ_class1[cn, d, p].append(vh1)
                            occ_class1[cn, d, p].append(vh2)
                        if tk and not independent_classes:
                            occ_teacher1[tk, d, p].append(vh1)
                            occ_teacher1[tk, d, p].append(vh2)
                        
                        pen = p * 2
                        if any((d, p) in avoid_by_class.get(cn, set()) for cn in target_cls): pen += 5
                        if tk and (d, p) in teacher_avoid.get(tk, set()): pen += 5
                        if tk and (d, p) in cross_inst_map.get(tk, set()): pen += 3000
                        if pen > 0:
                            obj1.append(vh1 * (-pen))
                            obj1.append(vh2 * (-pen))

            if v_2h or v_s1:
                s_2h = sum(v for v, _, _ in v_2h)
                s_s1 = sum(v for v, _, _ in v_s1)
                s_s2 = sum(v for v, _, _ in v_s2)
                model1.Add(s_2h + s_s1 == 1)
                model1.Add(s_2h + s_s2 == 1)
                block_solvers1[bid]["vars_2h"] = v_2h
                block_solvers1[bid]["vars_s1"] = v_s1
                block_solvers1[bid]["vars_s2"] = v_s2
            else:
                block_solvers1[bid]["unavail"] = True

        elif dur >= 3:
            u_splits = []
            for u_idx in range(dur):
                u_list = []
                for d in range(D):
                    for p in range(P):
                        if any((d, p) in blocked_by_class.get(cn, set()) for cn in target_cls): continue
                        if tk and not independent_classes:
                            if (d, p) in teacher_timeoff.get(tk, set()): continue
                            if (d, p) in global_teacher_busy.get(tk, set()): continue
                        elif tk and independent_classes:
                            if (d, p) in teacher_timeoff.get(tk, set()): continue
                        if _is_slot_forbidden_by_relations(b, d, p, 1): continue
                        vu = model1.NewBoolVar(f"x1_{bid}_u{u_idx}_{d}_{p}")
                        u_list.append((vu, d, p))
                        for cn in target_cls: occ_class1[cn, d, p].append(vu)
                        if tk and not independent_classes: occ_teacher1[tk, d, p].append(vu)
                u_splits.append(u_list)
                if u_list:
                    model1.AddExactlyOne([v for v, _, _ in u_list])
                else:
                    block_solvers1[bid]["unavail"] = True
            block_solvers1[bid]["vars_u"] = u_splits

    all_blocks_have_vars = not any(meta.get("unavail") for meta in block_solvers1.values())

    if all_blocks_have_vars:
        for var_list in occ_class1.values(): model1.AddAtMostOne(var_list)
        for var_list in occ_teacher1.values(): model1.AddAtMostOne(var_list)

        _apply_planning_relations_constraints(model1, raw_blocks, block_solvers1, is_phase1=True, obj_list=obj1)

        if obj1:
            model1.Maximize(sum(obj1))

        solver1 = cp_model.CpSolver()
        solver1.parameters.num_workers = 8
        solver1.parameters.max_time_in_seconds = float(time_limit)
        st1 = solver1.Solve(model1)

        if st1 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            placements = []
            for bid, meta in block_solvers1.items():
                b = meta["b"]
                dur = meta["type"]
                cn = b["classes"][0]
                is_lk = (bid in locked_block_bindings)
                if dur == 1:
                    for v, d_i, p_i in meta.get("vars_1h", []):
                        if solver1.Value(v) == 1:
                            placements.append({
                                "class_name": cn, "class": cn,
                                "subject_name": b["subject"], "subject": b["subject"],
                                "teacher_name": b["teacher"], "teacher": b["teacher"],
                                "day": d_i, "day_idx": d_i, "col": d_i,
                                "period": p_i, "row": p_i,
                                "duration": 1,
                                "is_combined": b["is_combined"],
                                "block_id": b["block_id"],
                                "locked": is_lk,
                                "is_manual": is_lk,
                                "is_filler": False,
                                "needs_review": bool(independent_classes)
                            })
                elif dur == 2:
                    done_2h = False
                    for v, d_i, p_i in meta.get("vars_2h", []):
                        if solver1.Value(v) == 1:
                            placements.append({
                                "class_name": cn, "class": cn,
                                "subject_name": b["subject"], "subject": b["subject"],
                                "teacher_name": b["teacher"], "teacher": b["teacher"],
                                "day": d_i, "day_idx": d_i, "col": d_i,
                                "period": p_i, "row": p_i,
                                "duration": 2,
                                "is_combined": b["is_combined"],
                                "block_id": b["block_id"],
                                "locked": is_lk,
                                "is_manual": is_lk,
                                "is_filler": False,
                                "needs_review": bool(independent_classes)
                            })
                            done_2h = True
                            break
                    if not done_2h:
                        s1_res, s2_res = None, None
                        for v, d_i, p_i in meta.get("vars_s1", []):
                            if solver1.Value(v) == 1: s1_res = (d_i, p_i); break
                        for v, d_i, p_i in meta.get("vars_s2", []):
                            if solver1.Value(v) == 1: s2_res = (d_i, p_i); break
                        if s1_res and s2_res:
                            if s1_res[0] == s2_res[0] and abs(s1_res[1] - s2_res[1]) == 1:
                                min_p = min(s1_res[1], s2_res[1])
                                placements.append({
                                    "class_name": cn, "class": cn,
                                    "subject_name": b["subject"], "subject": b["subject"],
                                    "teacher_name": b["teacher"], "teacher": b["teacher"],
                                    "day": s1_res[0], "day_idx": s1_res[0], "col": s1_res[0],
                                    "period": min_p, "row": min_p,
                                    "duration": 2,
                                    "is_combined": b["is_combined"],
                                    "block_id": b["block_id"],
                                    "locked": is_lk,
                                    "is_manual": is_lk,
                                    "is_filler": False,
                                    "needs_review": bool(independent_classes)
                                })
                            else:
                                for (d_i, p_i) in [s1_res, s2_res]:
                                    placements.append({
                                        "class_name": cn, "class": cn,
                                        "subject_name": b["subject"], "subject": b["subject"],
                                        "teacher_name": b["teacher"], "teacher": b["teacher"],
                                        "day": d_i, "day_idx": d_i, "col": d_i,
                                        "period": p_i, "row": p_i,
                                        "duration": 1,
                                        "is_combined": b["is_combined"],
                                        "block_id": b["block_id"],
                                        "locked": is_lk,
                                        "is_manual": is_lk,
                                        "is_filler": False,
                                        "needs_review": bool(independent_classes)
                                    })
                elif dur >= 3:
                    for u_list in meta.get("vars_u", []):
                        for v, d_i, p_i in u_list:
                            if solver1.Value(v) == 1:
                                placements.append({
                                    "class_name": cn, "class": cn,
                                    "subject_name": b["subject"], "subject": b["subject"],
                                    "teacher_name": b["teacher"], "teacher": b["teacher"],
                                    "day": d_i, "day_idx": d_i, "col": d_i,
                                    "period": p_i, "row": p_i,
                                    "duration": 1,
                                    "is_combined": b["is_combined"],
                                    "block_id": b["block_id"],
                                    "locked": is_lk,
                                    "is_manual": is_lk,
                                    "is_filler": False,
                                    "needs_review": bool(independent_classes)
                                })
            return placements, total_assigned_hours, time.time() - t0, "OPTIMAL_100_PERCENT"

    # ── FAZ 2: MAKSİMUM SIĞDIRMA OPTİMİZASYONU (Model 2) ──
    model2 = cp_model.CpModel()
    occ_class2 = defaultdict(list)
    occ_teacher2 = defaultdict(list)
    block_solvers2 = {}
    obj2 = []

    for b in raw_blocks:
        bid, dur, tk = b["id"], b["duration"], b["tk"]
        target_cls = b["classes"]
        block_solvers2[bid] = {"b": b, "type": dur}

        if dur == 1:
            u_vars = []
            for d in range(D):
                for p in range(P):
                    if bid in locked_block_bindings:
                        if (d, p) != locked_block_bindings[bid]: continue
                    if any((d, p) in blocked_by_class.get(cn, set()) for cn in target_cls): continue
                    if tk and not independent_classes:
                        if (d, p) in global_teacher_busy.get(tk, set()): continue
                    if _is_slot_forbidden_by_relations(b, d, p, 1): continue
                    
                    v = model2.NewBoolVar(f"x2_{bid}_1h_{d}_{p}")
                    u_vars.append((v, d, p))
                    for cn in target_cls: occ_class2[cn, d, p].append(v)
                    if tk and not independent_classes: occ_teacher2[tk, d, p].append(v)
                    
                    pen = p * 2
                    if tk and (d, p) in teacher_timeoff.get(tk, set()): pen += 25000
                    if any((d, p) in avoid_by_class.get(cn, set()) for cn in target_cls): pen += 5
                    if tk and (d, p) in teacher_avoid.get(tk, set()): pen += 5
                    if tk and (d, p) in cross_inst_map.get(tk, set()): pen += 3000
                    obj2.append(v * (500000 - pen))
            if u_vars:
                model2.AddAtMostOne([v for v, _, _ in u_vars])
                block_solvers2[bid]["vars_1h"] = u_vars

        elif dur == 2:
            v_2h = []
            for d in range(D):
                for p in range(P - 1):
                    if bid in locked_block_bindings:
                        if (d, p) != locked_block_bindings[bid]: continue
                    if any((d, p + off) in blocked_by_class.get(cn, set()) for cn in target_cls for off in range(2)): continue
                    if tk and not independent_classes:
                        if any((d, p + off) in global_teacher_busy.get(tk, set()) for off in range(2)): continue
                    if _is_slot_forbidden_by_relations(b, d, p, 2): continue
                    
                    v2 = model2.NewBoolVar(f"x2_{bid}_2h_{d}_{p}")
                    v_2h.append((v2, d, p))
                    for cn in target_cls:
                        occ_class2[cn, d, p].append(v2)
                        occ_class2[cn, d, p + 1].append(v2)
                    if tk and not independent_classes:
                        occ_teacher2[tk, d, p].append(v2)
                        occ_teacher2[tk, d, p + 1].append(v2)
                    
                    pen = p * 2
                    if tk and any((d, p + off) in teacher_timeoff.get(tk, set()) for off in range(2)): pen += 25000
                    if any((d, p + off) in avoid_by_class.get(cn, set()) for cn in target_cls for off in range(2)): pen += 5
                    if tk and any((d, p + off) in teacher_avoid.get(tk, set()) for off in range(2)): pen += 5
                    if tk and any((d, p + off) in cross_inst_map.get(tk, set()) for off in range(2)): pen += 3000
                    obj2.append(v2 * (1050000 - pen))

            v_s1, v_s2 = [], []
            if bid not in locked_block_bindings:
                for d in range(D):
                    for p in range(P):
                        if any((d, p) in blocked_by_class.get(cn, set()) for cn in target_cls): continue
                        if tk and not independent_classes:
                            if (d, p) in global_teacher_busy.get(tk, set()): continue
                        if _is_slot_forbidden_by_relations(b, d, p, 1): continue
                        
                        vh1 = model2.NewBoolVar(f"x2_{bid}_s1_{d}_{p}")
                        vh2 = model2.NewBoolVar(f"x2_{bid}_s2_{d}_{p}")
                        v_s1.append((vh1, d, p))
                        v_s2.append((vh2, d, p))
                        for cn in target_cls:
                            occ_class2[cn, d, p].append(vh1)
                            occ_class2[cn, d, p].append(vh2)
                        if tk and not independent_classes:
                            occ_teacher2[tk, d, p].append(vh1)
                            occ_teacher2[tk, d, p].append(vh2)
                        
                        pen = p * 2
                        if tk and (d, p) in teacher_timeoff.get(tk, set()): pen += 25000
                        if any((d, p) in avoid_by_class.get(cn, set()) for cn in target_cls): pen += 5
                        if tk and (d, p) in teacher_avoid.get(tk, set()): pen += 5
                        if tk and (d, p) in cross_inst_map.get(tk, set()): pen += 3000
                        obj2.append(vh1 * (500000 - pen))
                        obj2.append(vh2 * (500000 - pen))

            if v_2h or v_s1:
                s_2h = sum(v for v, _, _ in v_2h)
                s_s1 = sum(v for v, _, _ in v_s1)
                s_s2 = sum(v for v, _, _ in v_s2)
                model2.Add(s_2h + s_s1 <= 1)
                model2.Add(s_2h + s_s2 <= 1)
                model2.Add(s_s1 == s_s2)
                block_solvers2[bid]["vars_2h"] = v_2h
                block_solvers2[bid]["vars_s1"] = v_s1
                block_solvers2[bid]["vars_s2"] = v_s2

        elif dur >= 3:
            u_splits = []
            for u_idx in range(dur):
                u_list = []
                for d in range(D):
                    for p in range(P):
                        if any((d, p) in blocked_by_class.get(cn, set()) for cn in target_cls): continue
                        if tk and not independent_classes:
                            if (d, p) in global_teacher_busy.get(tk, set()): continue
                        if _is_slot_forbidden_by_relations(b, d, p, 1): continue
                        vu = model2.NewBoolVar(f"x2_{bid}_u{u_idx}_{d}_{p}")
                        u_list.append((vu, d, p))
                        for cn in target_cls: occ_class2[cn, d, p].append(vu)
                        if tk and not independent_classes: occ_teacher2[tk, d, p].append(vu)
                        pen = p * 2
                        if tk and (d, p) in teacher_timeoff.get(tk, set()): pen += 25000
                        obj2.append(vu * (500000 - pen))
                u_splits.append(u_list)
                model2.AddAtMostOne([v for v, _, _ in u_list])
            if u_splits:
                for i in range(len(u_splits) - 1):
                    model2.Add(sum(v for v, _, _ in u_splits[i]) == sum(v for v, _, _ in u_splits[i + 1]))
                block_solvers2[bid]["vars_u"] = u_splits

    for var_list in occ_class2.values(): model2.AddAtMostOne(var_list)
    for var_list in occ_teacher2.values(): model2.AddAtMostOne(var_list)

    _apply_planning_relations_constraints(model2, raw_blocks, block_solvers2, is_phase1=False, obj_list=obj2)

    model2.Maximize(sum(obj2))
    solver2 = cp_model.CpSolver()
    solver2.parameters.num_workers = 8
    solver2.parameters.max_time_in_seconds = float(time_limit)
    cb2 = _CpsatProgressBridge(raw_blocks, occ_class2, D, P, total_assigned_hours, progress_callback) if progress_callback else None
    st2 = solver2.Solve(model2, cb2) if cb2 else solver2.Solve(model2)

    placements = []
    if st2 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for bid, meta in block_solvers2.items():
            b = meta["b"]
            dur = meta["type"]
            cn = b["classes"][0]
            is_lk = (bid in locked_block_bindings)
            if dur == 1:
                for v, d_i, p_i in meta.get("vars_1h", []):
                    if solver2.Value(v) == 1:
                        placements.append({
                            "class_name": cn, "class": cn,
                            "subject_name": b["subject"], "subject": b["subject"],
                            "teacher_name": b["teacher"], "teacher": b["teacher"],
                            "day": d_i, "day_idx": d_i, "col": d_i,
                            "period": p_i, "row": p_i,
                            "duration": 1,
                            "is_combined": b["is_combined"],
                            "block_id": b["block_id"],
                            "locked": is_lk,
                            "is_manual": is_lk,
                            "is_filler": False,
                            "needs_review": bool(independent_classes)
                        })
            elif dur == 2:
                done_2h = False
                for v, d_i, p_i in meta.get("vars_2h", []):
                    if solver2.Value(v) == 1:
                        placements.append({
                            "class_name": cn, "class": cn,
                            "subject_name": b["subject"], "subject": b["subject"],
                            "teacher_name": b["teacher"], "teacher": b["teacher"],
                            "day": d_i, "day_idx": d_i, "col": d_i,
                            "period": p_i, "row": p_i,
                            "duration": 2,
                            "is_combined": b["is_combined"],
                            "block_id": b["block_id"],
                            "locked": is_lk,
                            "is_manual": is_lk,
                            "is_filler": False,
                            "needs_review": bool(independent_classes)
                        })
                        done_2h = True
                        break
                if not done_2h:
                    s1_res, s2_res = None, None
                    for v, d_i, p_i in meta.get("vars_s1", []):
                        if solver2.Value(v) == 1: s1_res = (d_i, p_i); break
                    for v, d_i, p_i in meta.get("vars_s2", []):
                        if solver2.Value(v) == 1: s2_res = (d_i, p_i); break
                    if s1_res and s2_res:
                        if s1_res[0] == s2_res[0] and abs(s1_res[1] - s2_res[1]) == 1:
                            min_p = min(s1_res[1], s2_res[1])
                            placements.append({
                                "class_name": cn, "class": cn,
                                "subject_name": b["subject"], "subject": b["subject"],
                                "teacher_name": b["teacher"], "teacher": b["teacher"],
                                "day": s1_res[0], "day_idx": s1_res[0], "col": s1_res[0],
                                "period": min_p, "row": min_p,
                                "duration": 2,
                                "is_combined": b["is_combined"],
                                "block_id": b["block_id"],
                                "locked": is_lk,
                                "is_manual": is_lk,
                                "is_filler": False,
                                "needs_review": bool(independent_classes)
                            })
                        else:
                            for (d_i, p_i) in [s1_res, s2_res]:
                                placements.append({
                                    "class_name": cn, "class": cn,
                                    "subject_name": b["subject"], "subject": b["subject"],
                                    "teacher_name": b["teacher"], "teacher": b["teacher"],
                                    "day": d_i, "day_idx": d_i, "col": d_i,
                                    "period": p_i, "row": p_i,
                                    "duration": 1,
                                    "is_combined": b["is_combined"],
                                    "block_id": b["block_id"],
                                    "locked": is_lk,
                                    "is_manual": is_lk,
                                    "is_filler": False,
                                    "needs_review": bool(independent_classes)
                                })
            elif dur >= 3:
                for u_list in meta.get("vars_u", []):
                    for v, d_i, p_i in u_list:
                        if solver2.Value(v) == 1:
                            placements.append({
                                "class_name": cn, "class": cn,
                                "subject_name": b["subject"], "subject": b["subject"],
                                "teacher_name": b["teacher"], "teacher": b["teacher"],
                                "day": d_i, "day_idx": d_i, "col": d_i,
                                "period": p_i, "row": p_i,
                                "duration": 1,
                                "is_combined": b["is_combined"],
                                "block_id": b["block_id"],
                                "locked": is_lk,
                                "is_manual": is_lk,
                                "is_filler": False,
                                "needs_review": bool(independent_classes)
                            })
    placed_hrs = sum(p["duration"] for p in placements)
    return placements, placed_hrs, time.time() - t0, "MAX_FIT"


def perfect_fill(classes, class_blocks, blocked_by_class, teacher_timeoff,
                 cross_inst_map, base_busy, D, P, time_budget=10.0, seed=None, planning_relations=None):
    """EKSİKSİZ ve ÇAKIŞMASIZ çizelge arar (Google OR-Tools CP-SAT motoru)."""
    try:
        placements, placed_hrs, elapsed, mode = solve_cpsat(
            classes_to_schedule=classes,
            assignments_or_blocks=class_blocks,
            blocked_by_class=blocked_by_class,
            avoid_by_class={},
            teacher_timeoff=teacher_timeoff,
            teacher_avoid={},
            cross_inst_map=cross_inst_map,
            global_teacher_busy=base_busy,
            D=D, P=P,
            time_limit=time_budget,
            planning_relations=planning_relations
        )
        if mode in ("OPTIMAL_100_PERCENT", "OPTIMAL_SOFT_RELATIONS") or (placements and placed_hrs > 0):
            return placements
    except Exception as e:
        print(f"[AutoScheduler] CP-SAT solver note: {e}")
    
    # Fallback to chain solver if needed
    try:
        import chain_scheduler
        empty = frozenset()
        def teacher_ok(tk, d, p):
            return ((d, p) not in teacher_timeoff.get(tk, empty)
                    and (d, p) not in cross_inst_map.get(tk, empty)
                    and (d, p) not in base_busy.get(tk, empty))

        class_open, prepared = {}, defaultdict(list)
        for cn in classes:
            closed = blocked_by_class.get(cn, set())
            class_open[cn] = {(d, p) for d in range(D) for p in range(P) if (d, p) not in closed}
        total = 0
        for cn in classes:
            for blk in class_blocks.get(cn, []):
                rec = dict(blk)
                rec["_tk"] = norm_teacher(blk.get("teacher") or "")
                prepared[cn].append(rec)
                total += max(1, int(blk.get("duration") or 1))
        if not total:
            return None

        placements, missing = chain_scheduler.solve_chain(
            classes, prepared, class_open, teacher_ok, D, P,
            random.Random(seed if seed is not None else 20260828),
            time_budget=min(5.0, time_budget), restarts=5
        )
        if missing == 0 and placements:
            out = []
            for pl in placements:
                out.append({
                    "class_name": pl["cls"], "class": pl["cls"],
                    "subject_name": pl.get("subject"), "subject": pl.get("subject"),
                    "teacher_name": pl.get("teacher"), "teacher": pl.get("teacher"),
                    "day": pl["day"], "day_idx": pl["day"], "col": pl["day"],
                    "period": pl["period"], "row": pl["period"],
                    "duration": int(pl["duration"]),
                    "is_combined": False, "block_id": pl.get("block_id", ""),
                    "is_filler": False, "needs_review": False,
                })
            return out
    except Exception:
        pass
    return None


def exact_fill(classes, class_blocks, blocked_by_class, teacher_timeoff,
               cross_inst_map, base_busy, D, P, time_budget=5.0, seed=None):
    """Bütün atanmış saatleri yerleştiren eksiksiz bir çizelge arar."""
    return perfect_fill(classes, class_blocks, blocked_by_class, teacher_timeoff,
                        cross_inst_map, base_busy, D, P, time_budget=time_budget, seed=seed)


class AutoSchedulerWorker(QThread):
    progress_updated = Signal(int, int)
    iteration_updated = Signal(int, int, int)
    finished_successfully = Signal(dict)
    failed = Signal(str)

    def __init__(self, data_store, target_class=None, parent=None, fill_empty=True, institution_slug=None, use_vds=False, infinite_mode=True, ignore_other_institutions=False, independent_classes=False):
        super().__init__(parent)
        self.data_store = data_store
        self.target_class = target_class if target_class and str(target_class).strip() and "Tum" not in str(target_class) and "Tüm" not in str(target_class) else None
        self.fill_empty = fill_empty
        self.institution_slug = institution_slug or (self.data_store.get("settings", {}).get("institution_slug", None) if isinstance(self.data_store, dict) else None)
        self.use_vds = use_vds
        self.infinite_mode = infinite_mode
        # "Diğer kurumları yoksay": hours a shared teacher owes to another branch stop
        # being treated as unavailable, so this institution can fill its own grid on
        # its own terms. Off by default — double-booking a teacher is normally a
        # mistake, not a preference.
        self.ignore_other_institutions = ignore_other_institutions
        # "Sınıfları bağımsız doldur": each class is filled as if it were the only one,
        # so a teacher may end up booked in two classes at the same hour. That fills
        # the grid, and it is sometimes what the user wants — they will resolve the
        # clashes by hand afterwards. Off by default, and every lesson placed this way
        # is marked has_conflict so the result is honest about what it is rather than
        # looking finished when it cannot be run.
        self.independent_classes = independent_classes
        self._is_running = True

    def run(self):
        t_start = time.time()
        import constraint_sync

        settings = self.data_store.get("settings", {})
        days = settings.get("days")
        if not days:
            all_days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
            cnt, _ = constraint_sync.grid_dimensions(self.data_store)
            days = all_days[:cnt]
        # Dimensions come from the same helper the two constraint screens use, so a
        # matrix built there can never be indexed with a different period count here.
        _, periods = constraint_sync.grid_dimensions(self.data_store)
        D = len(days)
        P = periods

        assignments = self.data_store.get("atamalar", [])
        if not assignments:
            self.failed.emit("Herhangi bir ders ataması bulunamadı.")
            return

        teacher_timeoff, teacher_avoid = _build_teacher_timeoff_map(
            self.data_store, self.institution_slug,
            include_shared=not self.ignore_other_institutions,
        )
        class_blocked_map, class_avoid_map = _build_class_timeoff_map(self.data_store)

        if self.institution_slug and not self.ignore_other_institutions:
            cross_inst_map, cross_inst_details = _build_cross_institution_map(self.institution_slug)
            # Hours another branch has explicitly reserved for a shared teacher count
            # exactly like hours they are already teaching: the teacher is spoken for.
            try:
                for key, slots in constraint_sync.reserved_by_others(self.institution_slug).items():
                    cross_inst_map.setdefault(key, set()).update(slots)
                    for slot in slots:
                        cross_inst_details.setdefault((key, slot[0], slot[1]), {
                            "institution": "Rezerve edilmiş", "class": "", "subject": "",
                        })
            except Exception as e:
                print(f"[AutoScheduler] reservation merge note: {e}")
            # Resolve spelling differences so a teacher written slightly differently at
            # another branch is still recognised as the same person.
            cross_inst_map = _merge_foreign_teacher_slots(self.data_store, cross_inst_map)
        else:
            cross_inst_map, cross_inst_details = {}, {}
            if self.ignore_other_institutions:
                print("[AutoScheduler] 'Diğer kurumları yoksay' açık — çapraz kurum kısıtları uygulanmıyor.")

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
            # Saat, sınıf ekranındaki toplu atamanın gösterdiği değerle AYNI
            # kaynaktan okunur (lesson_hours). Eskiden ders_sayisi önce
            # okunuyordu; sınıf ekranından değiştirilen bir ders için o alan eski
            # değerinde kaldığından planlayıcı sınıfa atanandan farklı sayıda saat
            # yerleştiriyordu.
            h_dur = lesson_hours.hours(asgn) or 2
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

        # Who else could cover an hour, and for which subject. Used only as the filler's
        # last resort: when every one of a class's own teachers is unavailable, a hole in
        # the middle of the day is worse than a stand-in, and standing someone in is the
        # only option left that neither overrides a teacher's closed hours nor books them
        # into two classes at once.
        subject_teachers = defaultdict(list)   # subject -> [teacher display names]
        teacher_subjects = defaultdict(list)   # teacher -> [subjects they teach]
        for asgn in assignments:
            a_t = format_tr_name(asgn.get("ogretmen") or asgn.get("teacher") or asgn.get("teacher_name") or "")
            a_s = (asgn.get("ders") or asgn.get("subject") or "").strip()
            if not a_t or not a_s:
                continue
            if a_t not in subject_teachers[a_s]:
                subject_teachers[a_s].append(a_t)
            if a_s not in teacher_subjects[a_t]:
                teacher_subjects[a_t].append(a_s)

        # Teachers who carry no assignment at all still belong in the stand-in pool.
        # Building it from the assignment list alone left them out entirely, so hours
        # they were free for stayed empty while they sat idle — the single biggest
        # source of holes in an otherwise open day. They are registered with no subject
        # of their own: the SUBJECT always comes from the class being filled, so what
        # lands on the grid is a real lesson of that class, never a generic study hour.
        for t in self.data_store.get("ogretmenler", []) or []:
            if not isinstance(t, dict):
                continue
            t_name = format_tr_name(t.get("ad") or t.get("name") or "")
            if t_name:
                teacher_subjects.setdefault(t_name, [])

        # Global teacher busy tracker
        global_teacher_busy = defaultdict(set)  # teacher -> set of (day, period)

        # Pre-fill teacher busy from OTHER classes' placements
        other_placements = []
        for p in self.data_store.get("grid_placements", []):
            c_name = (p.get("class_name") or p.get("class") or "").strip()
            if not any(matches_class(c_name, tgt) for tgt in classes_to_schedule):
                other_placements.append(p)
                t = norm_teacher(p.get("teacher_name") or p.get("teacher") or "")
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
        total_assigned_hours = sum(
            blk["duration"] for blocks in class_blocks.values() for blk in blocks
        )
        
        empty_set = frozenset()
        teacher_pool = []
        for t in self.data_store.get("ogretmenler", []) or []:
            if isinstance(t, dict):
                tk_ = norm_teacher(t.get("ad") or t.get("name") or "")
                if tk_ and tk_ not in teacher_pool:
                    teacher_pool.append(tk_)

        best_result = None
        best_violations = []
        best_leftovers = {}

        def _on_cpsat_progress(placed_hrs, tot_hrs):
            self.iteration_updated.emit(1, 0, placed_hrs)
            self.progress_updated.emit(placed_hrs, max(total_target, tot_hrs))

        self.iteration_updated.emit(1, 0, 0)
        self.progress_updated.emit(0, max(total_target, total_assigned_hours))

        # Collect locked/pinned placements that must be preserved
        locked_placements = []
        for p in self.data_store.get("grid_placements", []):
            if p.get("locked") or p.get("pinned"):
                c_name = (p.get("class_name") or p.get("class") or "").strip()
                t_name = norm_teacher(p.get("teacher_name") or p.get("teacher") or "")
                d_p = int(p.get("day", p.get("col", 0)))
                per_p = int(p.get("period", p.get("row", 0)))
                dur_p = int(p.get("duration", 1))
                # Zaman Tablosu kontrolü: Kapalı hücreye denk gelen eski kayıt kilitlenemez
                if any((d_p, per_p + off) in blocked_by_class.get(c_name, set()) for off in range(dur_p)):
                    continue
                if t_name and any((d_p, per_p + off) in teacher_timeoff.get(t_name, set()) for off in range(dur_p)):
                    continue
                if any(matches_class(c_name, tgt) for tgt in classes_to_schedule):
                    locked_placements.append(p)

        # Extract active planning relations
        planning_relations = [r for r in self.data_store.get("planlama_iliskileri", []) if r.get("aktif", True)]

        # Solve using Google OR-Tools CP-SAT Solver
        placements, placed_real, elapsed_solve, mode = solve_cpsat(
            classes_to_schedule=classes_to_schedule,
            assignments_or_blocks=class_blocks,
            blocked_by_class=blocked_by_class,
            avoid_by_class=avoid_by_class,
            teacher_timeoff=teacher_timeoff,
            teacher_avoid=teacher_avoid,
            cross_inst_map=cross_inst_map,
            global_teacher_busy=global_teacher_busy,
            D=D, P=P,
            time_limit=max(25.0, len(classes_to_schedule) * 3.0),
            independent_classes=self.independent_classes,
            planning_relations=planning_relations,
            locked_placements=locked_placements,
            progress_callback=_on_cpsat_progress
        )

        # Fallback to perfect_fill if CP-SAT was missing or failed
        if placements is None:
            placements = perfect_fill(
                classes_to_schedule, class_blocks, blocked_by_class,
                teacher_timeoff, cross_inst_map, global_teacher_busy, D, P,
                time_budget=max(8.0, len(classes_to_schedule) * 1.0), planning_relations=planning_relations
            ) or []
            placed_real = sum(int(p.get("duration", 1) or 1) for p in placements)

        best_result = list(other_placements) + (placements or [])
        placed_cells = placed_real

        # Find leftover unplaced lessons if any
        placed_block_ids = {p.get("block_id") for p in (placements or []) if p.get("block_id")}
        for cn in classes_to_schedule:
            unplaced = [b for b in class_blocks.get(cn, []) if b.get("block_id") not in placed_block_ids]
            if unplaced:
                best_leftovers[cn] = unplaced

        # Which of this institution's own teachers were held back because they are
        # already teaching elsewhere. Reported so an unexpectedly gappy schedule can
        # be explained rather than looking like the scheduler simply gave up.
        # Real cross-institution conflicts (actual grid placements colliding with other institutions)
        cross_conflicts = []
        for item in best_result:
            t = item.get("teacher_name") or item.get("teacher") or ""
            tk = norm_teacher(t)
            d = int(item.get("day_idx") if "day_idx" in item else item.get("day", item.get("col", 0)))
            p = int(item.get("period", item.get("row", 0)))
            dur = int(item.get("duration", 1))
            for off in range(dur):
                if (tk, d, p + off) in cross_inst_details:
                    info = cross_inst_details[(tk, d, p + off)]
                    cross_conflicts.append({
                        "teacher": t,
                        "day": d,
                        "period": p + off,
                        "institution": info.get("institution", ""),
                        "other_institution": info.get("institution", ""),
                        "other_class": info.get("class", ""),
                        "other_subject": info.get("subject", ""),
                        "class": item.get("class_name") or item.get("class", ""),
                        "this_class": item.get("class_name") or item.get("class", ""),
                        "subject": item.get("subject_name") or item.get("subject", ""),
                        "this_subject": item.get("subject_name") or item.get("subject", ""),
                    })

        # Hours where the schedule simply cannot be filled: more classes are open than
        # there are teachers able to work that hour. Reported so a gappy grid reads as
        # "not enough teachers on Friday morning" rather than as the scheduler giving up.
        understaffed = []
        open_classes_at = defaultdict(int)
        for cn in classes_to_schedule:
            blocked_set = blocked_by_class.get(cn, set())
            for d in range(D):
                for p in range(P):
                    if (d, p) not in blocked_set:
                        open_classes_at[(d, p)] += 1
        for (d, p), n_classes in open_classes_at.items():
            available = sum(
                1 for tk_ in teacher_pool
                if (d, p) not in teacher_timeoff.get(tk_, empty_set)
                and (d, p) not in cross_inst_map.get(tk_, empty_set)
            )
            if available < n_classes:
                understaffed.append({
                    "day": d, "period": p,
                    "classes": n_classes, "teachers": available,
                    "shortfall": n_classes - available,
                })
        understaffed.sort(key=lambda x: -x["shortfall"])
        if understaffed:
            total_short = sum(u["shortfall"] for u in understaffed)
            print(f"[AutoScheduler] {total_short} hücre doldurulamaz: o saatlerde açık sınıf sayısı "
                  f"müsait öğretmen sayısını aşıyor.")
            for u in understaffed[:5]:
                print(f"    gün {u['day'] + 1}, {u['period'] + 1}. saat: "
                      f"{u['classes']} sınıf açık ama {u['teachers']} öğretmen müsait")

        # In independent mode, count the clashes that were deliberately allowed so the
        # user is told exactly what they traded the full grid for.
        teacher_clashes = []
        if self.independent_classes:
            occupied = defaultdict(set)
            for pl in (best_result or []):
                tkey = norm_teacher(pl.get("teacher_name") or pl.get("teacher") or "")
                if not tkey:
                    continue
                d0 = int(pl.get("day", pl.get("col", 0)))
                p0 = int(pl.get("period", pl.get("row", 0)))
                for off in range(int(pl.get("duration", 1) or 1)):
                    occupied[(tkey, d0, p0 + off)].add(
                        (pl.get("class_name") or pl.get("class") or "").strip())
            for (tkey, d0, p0), classes in occupied.items():
                if len(classes) > 1:
                    teacher_clashes.append({
                        "teacher": tkey, "day": d0, "period": p0,
                        "classes": sorted(classes),
                    })
            if teacher_clashes:
                print(f"[AutoScheduler] BAĞIMSIZ MOD: {len(teacher_clashes)} öğretmen "
                      f"çakışması oluşturuldu (elle düzeltilmeli)")

        # Why the week cannot fill, in the terms the user can act on.
        #
        # The assignment screen shows hours per CLASS, so a class can look perfectly
        # balanced — 20 assigned, 20 open — while the week is still impossible,
        # because the real limit is per TEACHER: one teacher, one class at a time.
        # Assign someone 28 hours when their classes are only open 20 and 8 of those
        # hours cannot exist, no matter how long the scheduler searches.
        capacity_problems = analyse_teacher_capacity(
            class_blocks, blocked_by_class, teacher_timeoff, cross_inst_map, D, P,
        )
        if capacity_problems:
            impossible = sum(c["shortfall"] for c in capacity_problems)
            print(f"[AutoScheduler] {impossible} saat HİÇBİR ŞEKİLDE yerleşemez — "
                  f"öğretmenlere müsait olduklarından fazla ders atanmış:")
            for c in capacity_problems[:6]:
                print(f"    {c['teacher']}: {c['assigned']} saat atanmış, "
                      f"{c['available']} saat müsait -> {c['shortfall']} saat fazla")

        # What could not be placed, grouped for the post-run report.
        unplaced_summary = []
        for cn, blks in (best_leftovers or {}).items():
            per_key = defaultdict(int)
            for b in blks:
                per_key[(b.get("subject", ""), b.get("teacher", ""))] += int(b.get("duration", 1))
            for (subj, tch), hours in per_key.items():
                unplaced_summary.append({
                    "class": cn, "subject": subj, "teacher": tch, "hours": hours,
                })
        unplaced_summary.sort(key=lambda x: (-x["hours"], x["class"]))

        elapsed = time.time() - t_start
        n_violations = len(best_violations) if best_violations else 0
        print(f"[AutoScheduler] {elapsed:.2f}s — {placed_cells}/{total_target} hücre dolu "
              f"({placed_real}/{total_assigned_hours} gerçek ders saati), "
              f"{n_violations} constraint violations, {len(cross_conflicts)} cross-institution slot(s) reserved "
              f"({len(classes_to_schedule)} classes × {D}d × {P}p)")

        self.iteration_updated.emit(1, 0, placed_cells)
        self.progress_updated.emit(placed_cells, max(total_target, placed_cells))

        self.finished_successfully.emit({
            "schedule": best_result,
            "placements": best_result,
            "placed_hours": placed_cells,
            "placed_real_hours": placed_real,
            "total_hours": total_target,
            "cross_conflicts": cross_conflicts,
            "constraint_violations": best_violations or [],
            "understaffed_slots": understaffed,
            "unplaced_summary": unplaced_summary,
            "capacity_problems": capacity_problems,
            "teacher_clashes": teacher_clashes,
            "elapsed_seconds": round(elapsed, 2)
        })

    def stop(self):
        self._is_running = False
