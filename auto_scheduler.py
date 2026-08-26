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
            # Split by state first so the name-alias merge can run over plain slot sets.
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


def exact_fill(classes, class_blocks, blocked_by_class, teacher_timeoff,
               cross_inst_map, base_busy, D, P, time_budget=25.0, seed=None):
    """Bütün atanmış saatleri yerleştiren eksiksiz bir çizelge arar.

    Bulursa yerleşim listesi, bulamazsa None döner.
    """
    empty = frozenset()
    rng = random.Random(seed if seed is not None else 12345)
    deadline = time.time() + max(1.0, float(time_budget))

    blocks = []
    for cn in classes:
        for b in class_blocks.get(cn, []):
            if b.get("is_combined"):
                # Birleşik (eş zamanlı) dersler bu aramanın modelinde yok:
                # aynı bloğun iki sınıfta aynı saate düşmesi gerekir. Sezgisel
                # sonucu bozmamak için baştan çekiliyoruz.
                return None
            blocks.append({"cls": cn, "blk": b,
                           "size": max(1, int(b.get("duration") or 1)),
                           "tk": norm_teacher(b.get("teacher") or ""),
                           "day": 0})
    if not blocks:
        return None

    def tk_free(tk, d, p):
        return ((d, p) not in teacher_timeoff.get(tk, empty)
                and (d, p) not in cross_inst_map.get(tk, empty)
                and (d, p) not in base_busy.get(tk, empty))

    open_by_day = {}
    for cn in classes:
        closed = blocked_by_class.get(cn, set())
        open_by_day[cn] = {d: [p for p in range(P) if (d, p) not in closed]
                           for d in range(D)}
    # Bir öğretmenin bir günde verebileceği azami ders saati, kendi müsait
    # saatleriyle DEĞİL, o gün derse girdiği sınıfların açık saatleriyle sınırlıdır:
    # sınıf 4 saat açıkken öğretmenin 8 saat müsait olması bir şey değiştirmez.
    teacher_classes = defaultdict(set)
    for b in blocks:
        if b["tk"]:
            teacher_classes[b["tk"]].add(b["cls"])
    tcap = {}
    for tk, cls_set in teacher_classes.items():
        per_day = {}
        for d in range(D):
            usable = set()
            for cn in cls_set:
                usable.update(open_by_day[cn][d])
            per_day[d] = sum(1 for p in usable if tk_free(tk, d, p))
        tcap[tk] = per_day

    by_class = defaultdict(list)
    for b in blocks:
        by_class[b["cls"]].append(b)

    # Aritmetik olarak imkânsız kurulumda hiç aramaya girmeyelim: bir sınıfa açık
    # saatinden çok ders, bir öğretmene müsait saatinden çok ders atanmışsa
    # EKSİKSİZ bir çizelge yoktur; sezgisel sonuç neyse odur.
    for cn, blks in by_class.items():
        if sum(b["size"] for b in blks) > sum(len(v) for v in open_by_day[cn].values()):
            return None
    t_hours = defaultdict(int)
    for b in blocks:
        if b["tk"]:
            t_hours[b["tk"]] += b["size"]
    for tk, hours in t_hours.items():
        if hours > sum(tcap.get(tk, {}).get(d, 0) for d in range(D)):
            return None

    # ── SAAT PENCERESİ ────────────────────────────────────────────────────
    #
    # Bir sınıfa haftada 20 saat ders varsa ve 5 gün açıksa, günlük payı 4'tür.
    # Sınıfın 5. saatini açmak bu payı değiştirmez — koyacak 21. ders yoktur.
    # Ama açık bırakılan o fazladan saat aramayı bozuyordu: YALNIZ o sınıfın açık
    # olduğu bir saate ancak o sınıfın dersi konabilir; gün dağıtımı ise bir
    # öğretmene o gün 5 saat verebiliyor ve beşinci saat zorunlu olarak o tek
    # hücreye düşmek zorunda kalıyordu. Gün çözülemiyor, EKSİKSİZ çözüm hiç
    # bulunamıyor, çizelge sezgisel sonuca — yani boşluklara — düşüyordu.
    # "5. saati açtım, artık dolduramıyor" tam olarak buydu.
    #
    # Çözüm: her sınıf için günün İLK payı kadar saati pencere kabul edilir.
    # Dersler günün başından sıkışık dizilir, fazladan açık saatler günün sonunda
    # boş kalır — okulun zaten istediği şey budur. Pencere bir çözüm bulmayı
    # engellerse (öğretmen ancak öğleden sonra müsaitse) sonraki denemelerde
    # pencere kaldırılıp bütün açık saatler kullanılır.
    window_by_day = {}
    for cn in classes:
        need = sum(b["size"] for b in by_class.get(cn, []))
        share = max(1, -(-need // D)) if D else need
        window_by_day[cn] = {d: open_by_day[cn][d][:max(share, 1)] for d in range(D)}

    def build_tcap(win):
        out = {}
        for tk2, cls_set in teacher_classes.items():
            per_day2 = {}
            for d in range(D):
                usable = set()
                for cn2 in cls_set:
                    usable.update(win[cn2][d])
                per_day2[d] = sum(1 for p in usable if tk_free(tk2, d, p))
            out[tk2] = per_day2
        return out

    tcap_win = build_tcap(window_by_day)
    tcap_full = tcap

    active = {"win": window_by_day, "tcap": tcap_win}

    def hard_cost(cload, tload):
        h = 0
        win, tc = active["win"], active["tcap"]
        for (cn, d), v in cload.items():
            h += max(0, v - len(win[cn][d]))
        for (tk, d), v in tload.items():
            h += max(0, v - tc.get(tk, {}).get(d, P))
        return h



    for attempt in range(60):
        if time.time() > deadline:
            break
        # İlk yarıda sıkışık pencere, sonra bütün açık saatler.
        if attempt < 30:
            active["win"], active["tcap"] = window_by_day, tcap_win
        else:
            active["win"], active["tcap"] = open_by_day, tcap_full
        win = active["win"]

        # ── 1) blokları günlere dağıt ────────────────────────────────
        #
        # Günlük yük, açık saat sayısına değil DENGELİ PAYA göre sınırlanır.
        # Sınıfa haftada 20 saat ders var ve 5 gün açıksa günlük pay 4'tür;
        # sınıfın 5. saati açık olsa bile bir güne 5 saat yığmanın anlamı yok.
        #
        # Bunun ikinci ve asıl sebebi teknik: sınıfların açık saatleri farklı
        # olduğunda (biri 5, diğerleri 4 saat) yalnız o tek sınıfın açık olduğu
        # saate ancak o sınıfın dersi konabilir. Bir öğretmene o gün 5 saat
        # düşerse, beşincisi zorunlu olarak o hücreye denk gelmek zorundadır —
        # gün çoğu zaman çözülemez hale gelir. Dengeli pay bu tuzağı baştan
        # kurutur; sığmadığı durumda aşağıdaki gevşetme devreye girer.
        for cn, blks in by_class.items():
            cap = {d: len(win[cn][d]) for d in range(D)}
            for b in sorted(blks, key=lambda x: (-x["size"], rng.random())):
                days = [d for d in range(D) if cap[d] >= b["size"]] or list(range(D))
                rng.shuffle(days)
                days.sort(key=lambda d: -cap[d])
                b["day"] = days[0]
                cap[b["day"]] -= b["size"]

        cload, tload, sday = defaultdict(int), defaultdict(int), defaultdict(int)
        for b in blocks:
            cload[(b["cls"], b["day"])] += b["size"]
            if b["tk"]:
                tload[(b["tk"], b["day"])] += b["size"]
            sday[(b["cls"], b["day"], b["blk"].get("subject"))] += 1
        hard = hard_cost(cload, tload)
        soft = sum(v - 1 for v in sday.values() if v > 1)

        # Tavlama yokuş yukarı hamleyi de kabul eder, dolayısıyla BİTTİĞİ yer en
        # iyi bulduğu yer olmayabilir. En iyi gün dağıtımı ayrıca saklanır ve
        # sonunda ona dönülür; yoksa hard=0'a bir kez düşmüş bir deneme, sırf
        # yumuşak maliyeti kovalarken bozulup çöpe gidiyordu.
        best_state = (hard, soft, [b["day"] for b in blocks])
        rounds = 30000
        for it in range(rounds):
            if hard == 0 and soft == 0:
                break
            if (it & 1023) == 0 and time.time() > deadline:
                break
            b = rng.choice(blocks)
            d1 = b["day"]
            d2 = rng.randrange(D)
            if d1 == d2:
                continue
            cn, tk, k = b["cls"], b["tk"], b["size"]
            subj = b["blk"].get("subject")

            def over(v, cap_):
                return max(0, v - cap_)

            ccap1, ccap2 = len(win[cn][d1]), len(win[cn][d2])
            dh = (over(cload[(cn, d1)] - k, ccap1) - over(cload[(cn, d1)], ccap1)
                  + over(cload[(cn, d2)] + k, ccap2) - over(cload[(cn, d2)], ccap2))
            if tk:
                t1 = active["tcap"].get(tk, {}).get(d1, P)
                t2 = active["tcap"].get(tk, {}).get(d2, P)
                dh += (over(tload[(tk, d1)] - k, t1) - over(tload[(tk, d1)], t1)
                       + over(tload[(tk, d2)] + k, t2) - over(tload[(tk, d2)], t2))
            # Aynı dersin bir sınıfa aynı gün iki kez düşmesi: taşımanın bu
            # sayaca etkisi (her gün için max(0, adet-1) toplanır).
            s1, s2 = sday[(cn, d1, subj)], sday[(cn, d2, subj)]
            ds = (max(0, s1 - 2) - max(0, s1 - 1)
                  + max(0, s2) - max(0, s2 - 1))

            temp = max(0.05, 3.0 * (1.0 - it / rounds))
            delta = dh * 50 + ds
            if delta <= 0 or rng.random() < math.exp(-min(50.0, delta) / temp):
                cload[(cn, d1)] -= k
                cload[(cn, d2)] += k
                if tk:
                    tload[(tk, d1)] -= k
                    tload[(tk, d2)] += k
                sday[(cn, d1, subj)] -= 1
                sday[(cn, d2, subj)] += 1
                b["day"] = d2
                hard += dh
                soft += ds
                if (hard, soft) < best_state[:2]:
                    best_state = (hard, soft, [x["day"] for x in blocks])

        if best_state[:2] < (hard, soft):
            for b, d0 in zip(blocks, best_state[2]):
                b["day"] = d0
            hard, soft = best_state[0], best_state[1]
            cload, tload, sday = defaultdict(int), defaultdict(int), defaultdict(int)
            for b in blocks:
                cload[(b["cls"], b["day"])] += b["size"]
                if b["tk"]:
                    tload[(b["tk"], b["day"])] += b["size"]
                sday[(b["cls"], b["day"], b["blk"].get("subject"))] += 1

        if _FILL_DEBUG:
            cls_over = {(cn, d): (v, len(active["win"][cn][d]))
                        for (cn, d), v in cload.items() if v > len(active["win"][cn][d])}
            t_over = {(tk, d): (v, active["tcap"].get(tk, {}).get(d, P))
                      for (tk, d), v in tload.items()
                      if v > active["tcap"].get(tk, {}).get(d, P)}
            print(f"    [fill] deneme {attempt}: hard={hard} soft={soft} "
                  f"sinif_asimi={list(cls_over.items())[:3]} ogr_asimi={list(t_over.items())[:3]}")
        if hard > 0:
            continue

        # ── 2) her günü kendi içinde çöz ─────────────────────────────
        #
        # Önce sıkışık dizilişle (boş saatler günün sonunda) denenir; o gün
        # çözülemezse aynı gün için boşluklu dizilişlere izin verilip bir kez daha
        # denenir. Sıkışık deneme hem daha güzel bir çizelge verir hem de aramayı
        # hızlandırır; gevşek deneme ise bir öğretmen kısıtı gerçekten günün
        # ortasında boşluk gerektirdiğinde çözümü kurtarır.
        def solve_day(d):
            base_day = defaultdict(set)
            for tk, slots in base_busy.items():
                for (bd, bp) in slots:
                    if bd == d:
                        base_day[bp].add(tk)
            # Sıkışık diziliş küçük bir bütçeyle denenir: amaç, çözülemeyen günü
            # HIZLA anlayıp onarıma geçmek. Büyük bütçe yalnız son denemede
            # harcanır, yoksa tek bir çıkmaz gün bütün süreyi yiyor.
            for allow_gaps, budget in ((False, 20000), (True, 120000)):
                layouts, buildable = {}, True
                for cn in classes:
                    day_blocks = [b["blk"] for b in by_class[cn] if b["day"] == d]
                    if not day_blocks:
                        layouts[cn] = [{}]
                        continue
                    lays = _day_layouts(win[cn][d], day_blocks, tk_free, d,
                                        rng=rng, allow_gaps=allow_gaps)
                    if not lays:
                        buildable = False
                        break
                    layouts[cn] = lays
                if not buildable:
                    continue
                solved = _solve_one_day(layouts, base_day, rng, budget=budget)
                if solved is not None:
                    return solved
                if time.time() > deadline:
                    break
            return None

        def relocate_from(day):
            """Çözülemeyen günden bir bloğu, sığdığı başka bir güne taşır.

            Gün dağıtımının marjinal kontrolleri (sınıf-gün ve öğretmen-gün yükü)
            bir günün gerçekten kurulabilir olduğunu GARANTİ ETMEZ. Örnek: yalnız
            9A'nın 5. saati açıksa, o saatte ancak 9A'ya ders konabilir; bir
            öğretmenin o güne düşen 5 saatinin dördü başka sınıflardaysa gün
            çözülemez, ama marjinaller sorunsuz görünür.

            Bu yüzden çözülemeyen gün, denemeyi çöpe atmak yerine onarılır: o
            günden bir blok başka bir güne taşınır ve tekrar denenir. Aramanın
            "5. saati açınca hiç dolduramama" hâli tam olarak buydu.
            """
            movable = [b for b in blocks if b["day"] == day]
            rng.shuffle(movable)

            # Hedefli onarım: o gün, öğretmenin GERÇEKTEN kullanabileceği saatten
            # fazla dersi varsa gün asla çözülmez. Kullanılabilir saat, öğretmenin
            # o gün ders verdiği sınıfların açık olduğu saatlerdir — sınıfların
            # açık saatleri farklıysa (biri 5, diğerleri 4 saat) bu, gün dağıtımının
            # baktığı üst sınırdan küçük olabilir. Önce bu öğretmenlerin bloklarını
            # taşırız; rastgele blok taşımak aynı çıkmazda dönüp duruyordu.
            usable_today = {}
            for b in movable:
                tk = b["tk"]
                if not tk or tk in usable_today:
                    continue
                own = {x["cls"] for x in movable if x["tk"] == tk}
                slots = set()
                for cn2 in own:
                    slots.update(win[cn2][day])
                usable_today[tk] = sum(1 for p in slots if tk_free(tk, day, p))
            movable.sort(key=lambda b: 0 if (b["tk"] and tload[(b["tk"], day)]
                                             > usable_today.get(b["tk"], P)) else 1)

            for b in movable:
                cn, tk, k = b["cls"], b["tk"], b["size"]
                targets = [d2 for d2 in range(D) if d2 != day]
                rng.shuffle(targets)
                for d2 in targets:
                    if cload[(cn, d2)] + k > len(win[cn][d2]):
                        continue
                    if tk and tload[(tk, d2)] + k > tcap.get(tk, {}).get(d2, P):
                        continue
                    cload[(cn, day)] -= k
                    cload[(cn, d2)] += k
                    if tk:
                        tload[(tk, day)] -= k
                        tload[(tk, d2)] += k
                    b["day"] = d2
                    return True

            # Hiçbir blok taşınamıyorsa (her gün tam dolu olduğunda olur) TAKAS
            # dene: bu günden bir blokla başka gündeki bir bloğun yerini değiştir.
            # Taşıma yeri olmayan tam dolu çizelgelerde onarımın tek hamlesi budur.
            others = [x for x in blocks if x["day"] != day]
            rng.shuffle(others)
            for b in movable:
                cn, tk, k = b["cls"], b["tk"], b["size"]
                for b2 in others:
                    cn2, tk2, k2, d2 = b2["cls"], b2["tk"], b2["size"], b2["day"]
                    if cn2 == cn and k2 == k and tk2 == tk:
                        continue                     # aynı şeyi geri koymak
                    if cload[(cn, day)] - k + (k2 if cn2 == cn else 0) > len(win[cn][day]):
                        continue
                    if cload[(cn2, d2)] - k2 + (k if cn2 == cn else 0) > len(win[cn2][d2]):
                        continue
                    if cn != cn2:
                        if cload[(cn, d2)] + k > len(win[cn][d2]):
                            continue
                        if cload[(cn2, day)] + k2 > len(win[cn2][day]):
                            continue
                    if tk and tk != tk2:
                        if tload[(tk, d2)] + k > active["tcap"].get(tk, {}).get(d2, P):
                            continue
                    if tk2 and tk2 != tk:
                        if tload[(tk2, day)] + k2 > active["tcap"].get(tk2, {}).get(day, P):
                            continue
                    cload[(cn, day)] -= k
                    cload[(cn, d2)] += k
                    cload[(cn2, d2)] -= k2
                    cload[(cn2, day)] += k2
                    if tk:
                        tload[(tk, day)] -= k
                        tload[(tk, d2)] += k
                    if tk2:
                        tload[(tk2, d2)] -= k2
                        tload[(tk2, day)] += k2
                    b["day"], b2["day"] = d2, day
                    return True
            return False

        result, ok = {}, False
        for _repair in range(400):
            if time.time() > deadline:
                break
            result, failed_day = {}, None
            for d in range(D):
                if time.time() > deadline:
                    failed_day = d
                    break
                solved = solve_day(d)
                if solved is None:
                    failed_day = d
                    break
                result[d] = solved
            if failed_day is None:
                ok = True
                break
            if _FILL_DEBUG:
                print(f"    [fill] gun {failed_day} cozulemedi, blok tasiniyor")
            if not relocate_from(failed_day):
                break
        if not ok:
            continue

        placements = []
        for d, per_class in result.items():
            for cn, lay in per_class.items():
                done = set()
                for p in sorted(lay):
                    b = lay[p]
                    bid = b.get("block_id")
                    if (cn, d, id(b)) in done:
                        continue
                    done.add((cn, d, id(b)))
                    k = max(1, int(b.get("duration") or 1))
                    placements.append({
                        "class_name": cn, "class": cn,
                        "subject_name": b.get("subject"), "subject": b.get("subject"),
                        "teacher_name": b.get("teacher"), "teacher": b.get("teacher"),
                        "day": d, "day_idx": d, "col": d,
                        "period": p, "row": p,
                        "duration": k,
                        "is_combined": False,
                        "block_id": bid,
                        "is_filler": False,
                        "needs_review": False,
                    })
        return placements

    return None


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

        # Used by the fill phase to rank hours by how few teachers can work them, and
        # teachers by how little room they have left.
        empty_set = frozenset()
        teacher_pool = []
        for t in self.data_store.get("ogretmenler", []) or []:
            if isinstance(t, dict):
                tk_ = norm_teacher(t.get("ad") or t.get("name") or "")
                if tk_ and tk_ not in teacher_pool:
                    teacher_pool.append(tk_)
        teacher_capacity = {
            tk_: sum(
                1 for d in range(D) for p in range(P)
                if (d, p) not in teacher_timeoff.get(tk_, empty_set)
                and (d, p) not in cross_inst_map.get(tk_, empty_set)
            )
            for tk_ in teacher_pool
        }

        best_result = None
        best_score = (-1, 0, -1)
        best_violations = []
        best_leftovers = {}

        for attempt in range(50):
            if not self._is_running:
                break
            
            attempt_placements = list(other_placements)
            attempt_violations = []  # Track constraint bypasses
            if self.independent_classes:
                # Every teacher always looks free, so each class fills without regard
                # to what the others took. Reads return a fresh empty set, which also
                # makes the .add() calls scattered through the passes harmless no-ops
                # — no other code has to know this mode exists.
                attempt_teacher_busy = _AlwaysFreeTeachers()
            else:
                attempt_teacher_busy = defaultdict(set)
                for t, slots in global_teacher_busy.items():
                    attempt_teacher_busy[t] = set(slots)  # copy
            attempt_placed = 0
            attempt_real = 0   # spans that satisfy an actual assignment

            # Classes are filled one after another, and whoever goes first gets the
            # pick of a shared teacher's hours. With a FIXED order the same classes
            # were always served last and always ended up with the holes — all 50
            # attempts reshuffled the blocks inside a class but never the class order,
            # so every attempt starved the same ones. Rotating it lets a different
            # class go first each time and the best overall attempt win.
            attempt_classes = list(classes_to_schedule)
            if attempt > 0:
                random.shuffle(attempt_classes)

            grids = {}
            leftover_blocks = {}
            pending_by_class = {}

            # PHASE 0 — build every class's grid and block list up front, so the
            # scarce-hour pass below can see all classes at once instead of one at a
            # time.
            for cn in attempt_classes:
                # grid[day][period] = None (free) | BLOCKED_CELL (closed) | placement
                grid = [[None for _ in range(P)] for _ in range(D)]

                # Seed the closed cells BEFORE anything is placed. Every pass below
                # already tests "is this cell None?" to decide whether a slot is
                # free, so occupying closed cells up front makes all of them —
                # including the filler pass that caused this bug — leave those
                # periods alone, with no extra check to forget in one branch.
                for (bd, bp) in blocked_by_class.get(cn, set()):
                    grid[bd][bp] = BLOCKED_CELL
                grids[cn] = grid

                # Blokların KOPYASI alınır. Yerleştirme geçişleri kısmen konan bir
                # bloğun kalan saatini blk["duration"] -= 1 ile düşürüyor; liste
                # yüzeysel kopyalandığında bu, class_blocks içindeki asıl sözlüğü
                # değiştiriyordu. Sonuç: her deneme bir öncekinden daha az ders
                # saatiyle başlıyor, 50 denemenin çoğu daha en baştan eksik veriyle
                # koşuyordu (180 saatlik plan 6. denemede 161 saate düşüyordu).
                blocks = [dict(b) for b in class_blocks.get(cn, [])]
                random.shuffle(blocks)
                # Sort: bigger blocks first for better distribution
                blocks.sort(key=lambda b: (-b["duration"], random.random()))
                pending_by_class[cn] = blocks

            # PHASE 0.5 — claim the SCARCE hours first.
            #
            # Some hours have far fewer available teachers than open classes (here,
            # Thursday/Friday mornings: 9 classes open, 5-8 teachers free). Those
            # hours are the binding constraint on how full the week can get. Filling
            # classes one after another let whichever class went first spend a scarce
            # teacher's only free hour on an hour that had plenty of alternatives,
            # and the cell that teacher could have covered was then unfillable —
            # permanently, because the assignments exactly match the open slots.
            #
            # Reserving the tight hours up front, with an optimal matching across all
            # classes at once, spends each scarce teacher where they are irreplaceable.
            _reserve_scarce_hours(
                attempt_classes, grids, pending_by_class, attempt_teacher_busy,
                teacher_timeoff, cross_inst_map, teacher_pool, D, P,
            )

            # PHASE 1 — place each class's remaining blocks.
            for cn in attempt_classes:
                grid = grids[cn]
                cls_avoid = avoid_by_class.get(cn, set())
                blocks = pending_by_class[cn]

                unplaced = []

                for blk in blocks:
                    dur = blk["duration"]
                    t = blk["teacher"]
                    tk = norm_teacher(t)
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
                            if tk and tk in teacher_timeoff:
                                toff_hit = False
                                for off in range(dur):
                                    if (d, p + off) in teacher_timeoff[tk]:
                                        toff_hit = True
                                        break
                                if toff_hit:
                                    continue

                            # Check teacher busy (hard)
                            if tk:
                                t_busy = False
                                for off in range(dur):
                                    if (d, p + off) in attempt_teacher_busy[tk]:
                                        t_busy = True
                                        break
                                if t_busy:
                                    continue

                            # Teacher already teaching at ANOTHER institution: hard block.
                            # This used to be a mere +100 score penalty, easily outweighed
                            # by the same_subj_day*1000 term, so the auto-scheduler would
                            # cheerfully book a teacher into two branches at the same hour.
                            # Auto-placement must never do that; a human placing the lesson
                            # by hand still can (main_window warns and asks).
                            if tk and tk in cross_inst_map:
                                cross_hit = False
                                for off in range(dur):
                                    if (d, p + off) in cross_inst_map[tk]:
                                        cross_hit = True
                                        break
                                if cross_hit:
                                    continue

                            # Score: prefer contiguous placement, spread subjects across days
                            same_subj_day = sum(1 for pp in range(P) if grid[d][pp] and grid[d][pp]["subject"] == s)

                            # "Tercih edilmez" (yellow ?) is a soft constraint: usable,
                            # but only once genuinely preferred slots are exhausted.
                            avoid_pen = 0
                            if cls_avoid:
                                avoid_pen = 500 * sum(
                                    1 for off in range(dur) if (d, p + off) in cls_avoid
                                )
                            if tk and tk in teacher_avoid:
                                avoid_pen += 500 * sum(
                                    1 for off in range(dur) if (d, p + off) in teacher_avoid[tk]
                                )

                            score = same_subj_day * 1000 + p + avoid_pen + random.random() * 0.1
                            candidates.append((score, d, p))

                    if candidates:
                        candidates.sort()
                        _, best_d, best_p = candidates[0]

                        for off in range(dur):
                            grid[best_d][best_p + off] = {
                                "subject": s, "teacher": t, "block_id": bid,
                                "is_combined": blk["is_combined"], "block_start": best_p
                            }
                        if tk:
                            for off in range(dur):
                                attempt_teacher_busy[tk].add((best_d, best_p + off))
                    else:
                        unplaced.append(blk)
                
                still_unplaced = []
                # Second pass: retry the blocks the scored pass could not fit, this time
                # accepting any legal slot rather than the best-scoring one.
                #
                # It must NOT relax the teacher's closed hours. It used to, and that
                # silently placed 26 lessons into hours a teacher had explicitly marked
                # unavailable — the setting looked like it did nothing. A block that
                # genuinely has nowhere to go belongs in the unplaced dock, where it is
                # visible, not hidden inside a closed hour.
                for blk in unplaced:
                    dur = blk["duration"]
                    t = blk["teacher"]
                    tk = norm_teacher(t)
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
                            if tk:
                                t_busy = False
                                for off in range(dur):
                                    slot = (d, p + off)
                                    if slot in attempt_teacher_busy[tk]:
                                        t_busy = True
                                        break
                                    if tk in teacher_timeoff and slot in teacher_timeoff[tk]:
                                        t_busy = True
                                        break
                                if t_busy:
                                    continue

                            if tk and tk in cross_inst_map:
                                cross_hit = False
                                for off in range(dur):
                                    if (d, p + off) in cross_inst_map[tk]:
                                        cross_hit = True
                                        break
                                if cross_hit:
                                    continue

                            for off in range(dur):
                                grid[d][p + off] = {
                                    "subject": s, "teacher": t, "block_id": bid,
                                    "is_combined": blk["is_combined"], "block_start": p
                                }
                            if tk:
                                for off in range(dur):
                                    attempt_teacher_busy[tk].add((d, p + off))
                            placed = True
                            break
                        if placed:
                            break
                    if not placed:
                        still_unplaced.append(blk)

                grids[cn] = grid
                leftover_blocks[cn] = still_unplaced

            # ── PLACE WHAT IS STILL OWED ──────────────────────────────
            # Only real assigned lessons ever reach the grid. Earlier revisions padded
            # leftover cells with extra hours of a subject so the week looked full; that
            # invented lessons nobody had asked for, so it is gone. A cell with no
            # lesson simply stays empty, and the run reports why.
            #
            # What remains here is a genuine second chance for hours the scored passes
            # could not fit: taken hardest hour first (fewest teachers able to work it),
            # and covered by another teacher of the same subject when the assigned one
            # is unavailable. Closed hours are never opened and nobody is booked into
            # two classes at once.
            # Repeat until a whole sweep places nothing new.
            #
            # One sweep is not enough: filling an hour frees a teacher's OTHER hours
            # from contention, which can make an hour that was impossible earlier in
            # the same sweep possible now. Stopping after a single pass left hours on
            # the table that the very next pass could have taken. The loop is bounded
            # so a pathological case cannot spin.
            for _sweep in range(8):
                placed_this_sweep = 0
                slot_order = sorted(
                    ((d, p) for d in range(D) for p in range(P)),
                    key=lambda dp: sum(
                        1 for tk_ in teacher_pool
                        if dp not in teacher_timeoff.get(tk_, empty_set)
                    )
                )
                for (d, p) in slot_order:
                    # Fill this hour with a MAXIMUM BIPARTITE MATCHING between the
                    # classes that are still empty here and the teachers who can work
                    # it, rather than walking the classes in order and giving each the
                    # first teacher that fits.
                    #
                    # Greedy order loses hours that were placeable: hand teacher X to
                    # the first class that can use them and a later class for which X
                    # was the ONLY option is left with a hole, even though a different
                    # assignment of the same teachers would have filled both. With the
                    # assignments matching the open slots exactly (180 hours, 180 open
                    # cells) every such loss is a cell that can never be recovered, and
                    # that is what kept the result stuck around 134/180.
                    #
                    # Kuhn's augmenting-path algorithm is optimal for one hour and, at
                    # this size (≈9 classes × ≈21 teachers), effectively instant.
                    open_here = []
                    for cn in attempt_classes:
                        grid = grids.get(cn)
                        if grid is None or grid[d][p] is not None:
                            continue
                        if leftover_blocks.get(cn):
                            open_here.append(cn)

                    if open_here:
                        matched = _match_slot(
                            open_here, (d, p), grids, leftover_blocks,
                            attempt_teacher_busy, teacher_timeoff, cross_inst_map, P,
                        )
                        for cn, (blk, subject, teacher) in matched.items():
                            grid = grids[cn]
                            grid[d][p] = {
                                "subject": subject, "teacher": teacher,
                                "block_id": f"late_{_uuid.uuid4().hex[:8]}",
                                "is_combined": False, "block_start": p,
                                "is_filler": False,
                            }
                            tk_fill = norm_teacher(teacher)
                            if tk_fill:
                                attempt_teacher_busy[tk_fill].add((d, p))
                            pending_list = leftover_blocks.get(cn) or []
                            if blk["duration"] > 1:
                                blk["duration"] -= 1
                            elif blk in pending_list:
                                pending_list.remove(blk)
                            placed_this_sweep += 1

                    # Anything still empty at this hour genuinely had no free assigned
                    # teacher; the per-class loop below only handles the leftovers the
                    # matching could not reach.
                    fill_classes = list(attempt_classes)
                    random.shuffle(fill_classes)
                    for cn in fill_classes:
                        grid = grids.get(cn)
                        if grid is None or grid[d][p] is not None:
                            continue
                        pending = leftover_blocks.get(cn) or []
                        if not pending:
                            continue

                        prev_subj = grid[d][p - 1]["subject"] if (p > 0 and grid[d][p - 1] is not None) else None
                        next_subj = grid[d][p + 1]["subject"] if (p + 1 < P and grid[d][p + 1] is not None) else None

                        def _free(name):
                            key = norm_teacher(name)
                            if not key:
                                return True
                            slot = (d, p)
                            if slot in attempt_teacher_busy.get(key, empty_set):
                                return False
                            if key in cross_inst_map and slot in cross_inst_map[key]:
                                return False
                            if key in teacher_timeoff and slot in teacher_timeoff[key]:
                                return False
                            return True

                        # NOTE: there used to be a _cover() here that, when the
                        # assigned teacher was busy, substituted somebody else — and
                        # its candidate list was
                        #     subject_teachers[subject] + EVERY OTHER TEACHER
                        # so once the handful of real candidates were also busy it
                        # would hand the lesson to whoever happened to be free. That
                        # is why one teacher turned up across six unrelated subjects
                        # (Coğrafya, Fizik, Matematik, Türkçe...), why Edebiyat was
                        # shown under teachers who do not teach it, and why the grid
                        # disagreed with the Ders ve Öğretmen Atama Paneli.
                        #
                        # A timetable naming the wrong teacher is worse than an empty
                        # cell: it is confidently wrong, and it gets printed and handed
                        # out. The lesson now stays owed and drops into the
                        # "yerleştirilmeyenler" dock for the user to place by hand.

                        # Prefer a subject that does not repeat the neighbouring hour,
                        # but never leave an owed lesson unplaced just to avoid a repeat.
                        choice = None
                        for relaxed in (False, True):
                            for idx, blk in enumerate(pending):
                                if not relaxed and blk["subject"] in (prev_subj, next_subj):
                                    continue
                                # Only ever the teacher this class's assignment names.
                                if not _free(blk["teacher"]):
                                    continue
                                cover_t = blk["teacher"]
                                if cover_t:
                                    choice = (blk["subject"], cover_t)
                                    # One cell covers one hour; a 2-hour lesson keeps the
                                    # rest of its time owed instead of vanishing.
                                    if blk["duration"] > 1:
                                        blk["duration"] -= 1
                                    else:
                                        pending.pop(idx)
                                    break
                            if choice is not None:
                                break

                        if choice is None:
                            continue

                        s, t = choice
                        grid[d][p] = {
                            "subject": s, "teacher": t,
                            "block_id": f"late_{_uuid.uuid4().hex[:8]}",
                            "is_combined": False, "block_start": p, "is_filler": False,
                        }
                        tk_fill = norm_teacher(t)
                        if tk_fill:
                            attempt_teacher_busy[tk_fill].add((d, p))
                        placed_this_sweep += 1

                if not placed_this_sweep:
                    break  # a full sweep changed nothing; further sweeps cannot either

            # ── SETTLE PHASE ──────────────────────────────────────────
            # Independent mode fills every cell first and only then worries about who
            # can actually be where. The grid at this point is complete but has the
            # same teacher booked in several classes at once; swapping lessons WITHIN
            # a class keeps it full while moving those demands to different hours.
            # Whatever survives is arithmetic — a teacher owed more hours than there
            # are slots for them — not something a better arrangement could fix.
            if self.independent_classes:
                remaining, swaps = repair_conflicts(
                    grids, teacher_timeoff, cross_inst_map, D, P,
                )
                if swaps:
                    print(f"[AutoScheduler] yerleştirme sonrası {swaps} takas yapıldı, "
                          f"{remaining} saatlik çakışma kaldı")

            # ── CONVERT PHASE ─────────────────────────────────────────
            for cn in attempt_classes:
                grid = grids.get(cn)
                if grid is None:
                    continue
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
                            "is_filler": bool(cell.get("is_filler", False)),
                            # Independent mode places without checking whether the
                            # teacher is already busy, so anything it produces has to
                            # be reviewed. Marking it here is what lets the grid show
                            # it and the summary count it.
                            "needs_review": bool(self.independent_classes),
                        })
                        attempt_placed += span
                        if not cell.get("is_filler"):
                            attempt_real += span
                        p += span

            # Rank by cells filled FIRST, then — in independent mode — by how FEW
            # teacher clashes the arrangement leaves, then by real assignment hours.
            #
            # Without the clash term the run threw away its own best work: the settle
            # phase would get one attempt down to 32 clashing hours, and the attempt
            # chosen as "best" would be a different one with the same number of cells
            # and 45. Cells still come first, so this never trades a filled hour for a
            # tidier one — it only decides between equally full grids.
            attempt_clashes = 0
            if self.independent_classes:
                seen_load = defaultdict(set)
                for pl in attempt_placements:
                    tkey = norm_teacher(pl.get("teacher_name") or pl.get("teacher") or "")
                    if not tkey:
                        continue
                    d0 = int(pl.get("day", pl.get("col", 0)))
                    p0 = int(pl.get("period", pl.get("row", 0)))
                    cls0 = (pl.get("class_name") or pl.get("class") or "").strip()
                    for off in range(int(pl.get("duration", 1) or 1)):
                        seen_load[(tkey, d0, p0 + off)].add(cls0)
                attempt_clashes = sum(len(v) - 1 for v in seen_load.values() if len(v) > 1)

            attempt_score = (attempt_placed, -attempt_clashes, attempt_real)
            if attempt_score > best_score:
                best_score = attempt_score
                best_result = attempt_placements
                best_violations = attempt_violations
                best_leftovers = {
                    cn: [dict(b) for b in blks]
                    for cn, blks in leftover_blocks.items() if blks
                }

            if attempt_placed >= total_target and attempt_real >= total_assigned_hours:
                break

        # ── TAM DOLDURMA ──────────────────────────────────────────────
        # Sezgisel geçişler bir ders saatini bile açıkta bıraktıysa, çizelgeyi
        # bütün olarak kuran geri izlemeli arama devreye girer (exact_fill).
        # Yalnızca EKSİKSİZ bir sonuç döndürür; döndürdüğünde de ancak daha çok
        # gerçek ders saati yerleştiriyorsa sezgisel sonucun yerine geçer.
        if (best_score[2] < total_assigned_hours and self._is_running
                and not self.independent_classes):
            t_fill = time.time()
            exact = exact_fill(
                classes_to_schedule, class_blocks, blocked_by_class,
                teacher_timeoff, cross_inst_map, global_teacher_busy, D, P,
                time_budget=25.0,
            )
            exact_real = sum(int(p.get("duration", 1) or 1) for p in (exact or []))
            print(f"[AutoScheduler] tam doldurma {time.time() - t_fill:.1f}s — "
                  f"{exact_real if exact else 0}/{total_assigned_hours} ders saati")
            if exact and exact_real > best_score[2]:
                best_result = list(other_placements) + exact
                best_score = (exact_real, 0, exact_real)
                best_violations = []
                best_leftovers = {}

        if best_result is None:
            best_result = list(other_placements)
            best_violations = []
        # (cells, -clashes, real hours) — see the scoring note above.
        placed_cells, _neg_clashes, placed_real = (
            best_score if best_score[0] >= 0 else (0, 0, 0))

        # Which of this institution's own teachers were held back because they are
        # already teaching elsewhere. Reported so an unexpectedly gappy schedule can
        # be explained rather than looking like the scheduler simply gave up.
        cross_conflicts = []
        own_teachers = {
            norm_teacher(t.get("ad") or t.get("name") or ""): (t.get("ad") or t.get("name") or "")
            for t in self.data_store.get("ogretmenler", []) or []
            if isinstance(t, dict) and (t.get("ad") or t.get("name"))
        }
        for (tk, d, p), info in cross_inst_details.items():
            if tk in own_teachers:
                cross_conflicts.append({
                    "teacher": own_teachers[tk],
                    "day": d,
                    "period": p,
                    "institution": info.get("institution", ""),
                    "class": info.get("class", ""),
                    "subject": info.get("subject", ""),
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
