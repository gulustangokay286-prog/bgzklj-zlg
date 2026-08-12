# Chenki Akademi Ders Planlama - Automatic Scheduling Engine
# Backtracking + Heuristic Search Algorithm

import random
from typing import List, Dict, Set, Tuple, Optional
from core.timetable_data import TimetableData, TimetableSlot, Lesson


class ConflictError:
    def __init__(self, message: str, lesson_id: int = -1):
        self.message = message
        self.lesson_id = lesson_id


class SchedulerResult:
    def __init__(self):
        self.success = False
        self.assignments: List[TimetableSlot] = []
        self.conflicts: List[ConflictError] = []
        self.unplaced_lessons: List[int] = []
        self.iterations = 0


class Scheduler:
    def __init__(self, data: TimetableData):
        self.data = data
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def validate(self) -> List[str]:
        """Pre-scheduling validation - returns list of issues."""
        issues = []
        for lesson in self.data.lessons:
            if lesson.teacher_id < 0:
                subj = self.data.get_subject(lesson.subject_id)
                cls = self.data.get_class(lesson.class_id)
                issues.append(f"'{subj.name if subj else '?'}' dersinin öğretmeni atanmamış (Sınıf: {cls.name if cls else '?'})")
            if lesson.class_id < 0:
                issues.append(f"Ders ID={lesson.id} için sınıf atanmamış")
        return issues

    def generate(self, progress_callback=None) -> SchedulerResult:
        """Main scheduling entry point."""
        self._cancelled = False
        result = SchedulerResult()

        # Build list of (lesson, repeat_index) to place
        tasks = []
        for lesson in self.data.lessons:
            for _ in range(lesson.periods_per_week):
                tasks.append(lesson)

        # Sort by most constrained first (fewest available slots)
        tasks.sort(key=lambda l: self._count_available_slots(l, []))

        assignments = []
        unplaced = []

        for i, lesson in enumerate(tasks):
            if self._cancelled:
                break
            if progress_callback:
                progress_callback(int((i / len(tasks)) * 100))

            placed = self._place_lesson(lesson, assignments)
            if not placed:
                unplaced.append(lesson.id)
                result.conflicts.append(ConflictError(
                    f"Yerleştirilemedi: {self._lesson_description(lesson)}",
                    lesson.id
                ))
            result.iterations += 1

        result.assignments = assignments
        result.unplaced_lessons = list(set(unplaced))
        result.success = len(unplaced) == 0
        return result

    def _place_lesson(self, lesson: Lesson, existing: List[TimetableSlot]) -> bool:
        """Try to place one lesson instance using heuristic ordering."""
        slots = self._get_candidate_slots(lesson, existing)

        for day, period in slots:
            if self._is_valid(lesson, day, period, existing):
                existing.append(TimetableSlot(
                    lesson_id=lesson.id,
                    day=day,
                    period=period,
                    classroom_id=lesson.classroom_id
                ))
                return True
        return False

    def _get_candidate_slots(self, lesson: Lesson, existing: List[TimetableSlot]) -> List[Tuple[int, int]]:
        """Generate ordered list of candidate (day, period) slots."""
        slots = []
        for day in range(self.data.days_per_week):
            for period in range(self.data.periods_per_day):
                slots.append((day, period))

        # Apply heuristic ordering
        if lesson.prefer_morning:
            slots.sort(key=lambda s: s[1])
        elif lesson.prefer_afternoon:
            slots.sort(key=lambda s: -s[1])

        # Check teacher blocked periods
        teacher = self.data.get_teacher(lesson.teacher_id)
        if teacher:
            slots = [(d, p) for (d, p) in slots
                     if p not in teacher.blocked_periods.get(d, [])]

        # Shuffle within equal priority groups to avoid patterns
        random.shuffle(slots)
        return slots

    def _count_available_slots(self, lesson: Lesson, existing: List[TimetableSlot]) -> int:
        """Count how many slots are theoretically available for this lesson."""
        count = 0
        teacher = self.data.get_teacher(lesson.teacher_id)
        for day in range(self.data.days_per_week):
            for period in range(self.data.periods_per_day):
                if teacher and period in teacher.blocked_periods.get(day, []):
                    continue
                count += 1
        return count

    def _is_valid(self, lesson: Lesson, day: int, period: int, existing: List[TimetableSlot]) -> bool:
        """Check all constraints for placing lesson at (day, period)."""
        for slot in existing:
            if slot.day != day or slot.period != period:
                continue
            other = self.data.get_lesson(slot.lesson_id)
            if not other:
                continue

            # Teacher conflict
            if other.teacher_id == lesson.teacher_id and lesson.teacher_id >= 0:
                return False

            # Class conflict
            if other.class_id == lesson.class_id and lesson.class_id >= 0:
                return False

            # Classroom conflict
            if (other.classroom_id == lesson.classroom_id
                    and lesson.classroom_id >= 0
                    and slot.classroom_id >= 0):
                return False

        # Min days between same lesson
        if lesson.min_days_between > 0:
            same_lesson_days = [
                s.day for s in existing
                if s.lesson_id == lesson.id
            ]
            for existing_day in same_lesson_days:
                if abs(existing_day - day) < lesson.min_days_between:
                    return False

        return True

    def _lesson_description(self, lesson: Lesson) -> str:
        subj = self.data.get_subject(lesson.subject_id)
        cls = self.data.get_class(lesson.class_id)
        teacher = self.data.get_teacher(lesson.teacher_id)
        return (f"{subj.name if subj else '?'} - "
                f"{cls.name if cls else '?'} - "
                f"{teacher.name if teacher else '?'}")

    def check_all_conflicts(self, assignments: List[TimetableSlot]) -> List[str]:
        """Validate a full assignment set and return conflict descriptions."""
        conflicts = []
        for i, a in enumerate(assignments):
            for j, b in enumerate(assignments):
                if i >= j:
                    continue
                if a.day != b.day or a.period != b.period:
                    continue
                la = self.data.get_lesson(a.lesson_id)
                lb = self.data.get_lesson(b.lesson_id)
                if not la or not lb:
                    continue
                if la.teacher_id == lb.teacher_id and la.teacher_id >= 0:
                    t = self.data.get_teacher(la.teacher_id)
                    conflicts.append(
                        f"Öğretmen çakışması: {t.name if t else '?'} - "
                        f"Gün {a.day+1}, Saat {a.period+1}"
                    )
                if la.class_id == lb.class_id and la.class_id >= 0:
                    c = self.data.get_class(la.class_id)
                    conflicts.append(
                        f"Sınıf çakışması: {c.name if c else '?'} - "
                        f"Gün {a.day+1}, Saat {a.period+1}"
                    )
        return conflicts
