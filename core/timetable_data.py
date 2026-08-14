# Chenki Akademi Ders Planlama - Core Data Model

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import json
import xml.etree.ElementTree as ET
import xml.dom.minidom


@dataclass
class Teacher:
    id: int = 0
    name: str = ""
    short_name: str = ""
    color: str = "#4A90D9"
    # Availability: day (0=Mon..4=Fri) -> list of blocked periods
    blocked_periods: Dict[int, List[int]] = field(default_factory=dict)


@dataclass
class SchoolClass:
    id: int = 0
    name: str = ""
    short_name: str = ""
    home_teacher_id: int = -1


@dataclass
class Subject:
    id: int = 0
    name: str = ""
    short_name: str = ""
    color: str = "#7ED321"


@dataclass
class Classroom:
    id: int = 0
    name: str = ""
    short_name: str = ""
    capacity: int = 30


@dataclass
class Lesson:
    id: int = 0
    subject_id: int = -1
    teacher_id: int = -1
    class_id: int = -1
    classroom_id: int = -1
    periods_per_week: int = 1
    # Constraints
    prefer_morning: bool = False
    prefer_afternoon: bool = False
    min_days_between: int = 0


@dataclass
class TimetableSlot:
    lesson_id: int = -1
    day: int = 0       # 0=Monday .. 4=Friday
    period: int = 0    # 0=first period
    classroom_id: int = -1


@dataclass
class TimetableData:
    school_name: str = "Chenki Akademi"
    academic_year: str = "2026 - 2027/2026"
    periods_per_day: int = 8
    days_per_week: int = 5
    period_labels: List[str] = field(default_factory=lambda: [
        "08:00-08:45", "08:55-09:40", "09:50-10:35", "10:45-11:30",
        "11:40-12:25", "13:15-14:00", "14:10-14:55", "15:05-15:50"
    ])
    day_labels: List[str] = field(default_factory=lambda: [
        "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"
    ])

    teachers: List[Teacher] = field(default_factory=list)
    classes: List[SchoolClass] = field(default_factory=list)
    subjects: List[Subject] = field(default_factory=list)
    classrooms: List[Classroom] = field(default_factory=list)
    lessons: List[Lesson] = field(default_factory=list)
    assignments: List[TimetableSlot] = field(default_factory=list)

    _next_id: int = 1

    def next_id(self) -> int:
        nid = self._next_id
        self._next_id += 1
        return nid

    # --- Lookup helpers ---
    def get_teacher(self, tid: int) -> Optional[Teacher]:
        return next((t for t in self.teachers if t.id == tid), None)

    def get_class(self, cid: int) -> Optional[SchoolClass]:
        return next((c for c in self.classes if c.id == cid), None)

    def get_subject(self, sid: int) -> Optional[Subject]:
        return next((s for s in self.subjects if s.id == sid), None)

    def get_classroom(self, rid: int) -> Optional[Classroom]:
        return next((r for r in self.classrooms if r.id == rid), None)

    def get_lesson(self, lid: int) -> Optional[Lesson]:
        return next((l for l in self.lessons if l.id == lid), None)

    def get_assignment(self, day: int, period: int, class_id: int) -> Optional[TimetableSlot]:
        for a in self.assignments:
            lesson = self.get_lesson(a.lesson_id)
            if lesson and lesson.class_id == class_id and a.day == day and a.period == period:
                return a
        return None

    def get_assignments_for_class(self, class_id: int) -> List[TimetableSlot]:
        result = []
        for a in self.assignments:
            lesson = self.get_lesson(a.lesson_id)
            if lesson and lesson.class_id == class_id:
                result.append(a)
        return result

    def get_assignments_for_teacher(self, teacher_id: int) -> List[TimetableSlot]:
        result = []
        for a in self.assignments:
            lesson = self.get_lesson(a.lesson_id)
            if lesson and lesson.teacher_id == teacher_id:
                result.append(a)
        return result

    # --- File I/O ---
    def save_to_file(self, path: str):
        root = ET.Element("ChenKiTimetable", version="1.0")
        meta = ET.SubElement(root, "Meta")
        ET.SubElement(meta, "SchoolName").text = self.school_name
        ET.SubElement(meta, "AcademicYear").text = self.academic_year
        ET.SubElement(meta, "PeriodsPerDay").text = str(self.periods_per_day)
        ET.SubElement(meta, "DaysPerWeek").text = str(self.days_per_week)
        ET.SubElement(meta, "NextId").text = str(self._next_id)

        for label in self.period_labels:
            ET.SubElement(meta, "PeriodLabel").text = label

        def add_items(tag, items, attrs):
            parent = ET.SubElement(root, tag + "s")
            for item in items:
                el = ET.SubElement(parent, tag)
                for attr in attrs:
                    el.set(attr, str(getattr(item, attr, "") or ""))

        add_items("Teacher", self.teachers, ["id", "name", "short_name", "color"])
        add_items("Class", self.classes, ["id", "name", "short_name", "home_teacher_id"])
        add_items("Subject", self.subjects, ["id", "name", "short_name", "color"])
        add_items("Classroom", self.classrooms, ["id", "name", "short_name", "capacity"])
        add_items("Lesson", self.lessons, ["id", "subject_id", "teacher_id", "class_id",
                                            "classroom_id", "periods_per_week",
                                            "prefer_morning", "prefer_afternoon", "min_days_between"])
        add_items("Assignment", self.assignments, ["lesson_id", "day", "period", "classroom_id"])

        xml_str = ET.tostring(root, encoding="unicode")
        pretty = xml.dom.minidom.parseString(xml_str).toprettyxml(indent="  ")
        with open(path, "w", encoding="utf-8") as f:
            f.write(pretty)

    @classmethod
    def load_from_file(cls, path: str) -> "TimetableData":
        tree = ET.parse(path)
        root = tree.getroot()
        data = cls()

        meta = root.find("Meta")
        if meta is not None:
            data.school_name = meta.findtext("SchoolName", "")
            data.academic_year = meta.findtext("AcademicYear", "")
            data.periods_per_day = int(meta.findtext("PeriodsPerDay", "8"))
            data.days_per_week = int(meta.findtext("DaysPerWeek", "5"))
            data._next_id = int(meta.findtext("NextId", "1"))
            labels = meta.findall("PeriodLabel")
            if labels:
                data.period_labels = [l.text for l in labels]

        def load_items(tag, cls_type, attrs):
            items = []
            for el in root.iter(tag):
                obj = cls_type()
                for attr in attrs:
                    val = el.get(attr, "")
                    field_type = cls_type.__dataclass_fields__[attr].type
                    if "int" in str(field_type):
                        setattr(obj, attr, int(val) if val else 0)
                    elif "bool" in str(field_type):
                        setattr(obj, attr, val.lower() == "true")
                    else:
                        setattr(obj, attr, val)
                items.append(obj)
            return items

        data.teachers = load_items("Teacher", Teacher, ["id", "name", "short_name", "color"])
        data.classes = load_items("Class", SchoolClass, ["id", "name", "short_name", "home_teacher_id"])
        data.subjects = load_items("Subject", Subject, ["id", "name", "short_name", "color"])
        data.classrooms = load_items("Classroom", Classroom, ["id", "name", "short_name", "capacity"])
        data.lessons = load_items("Lesson", Lesson, ["id", "subject_id", "teacher_id", "class_id",
                                                      "classroom_id", "periods_per_week",
                                                      "prefer_morning", "prefer_afternoon", "min_days_between"])
        data.assignments = load_items("Assignment", TimetableSlot, ["lesson_id", "day", "period", "classroom_id"])
        return data
