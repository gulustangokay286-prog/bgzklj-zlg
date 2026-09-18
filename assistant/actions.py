"""Araçların uygulamadaki karşılığı.

Her yöntem GUI iş parçacığında çağrılır (agent.py bunu garanti eder) ve
JSON'a çevrilebilir bir sözlük döndürür: {"ok": bool, "message": str, ...}.
Sözlük olduğu gibi modele gider; mesaj kullanıcının okuyacağı dilde yazılır.

Bir ekranı açan araçlar (open_screen, start_auto_schedule) pencere kapanana
kadar döner; böylece "planlamayı başlat, sonra kaydet" gibi sıralı işler
doğru sırayla yürür.
"""
import re


def _norm(s):
    try:
        from version_store import normalize_teacher_name
        return normalize_teacher_name(s or "")
    except Exception:
        return (s or "").strip().upper()


def _matches(a, b):
    try:
        from version_store import _matches_teacher
        return _matches_teacher(a, b)
    except Exception:
        return _norm(a) == _norm(b)


_DAY_ALIASES = {
    "pazartesi": 0, "pzt": 0, "pts": 0, "monday": 0,
    "sali": 1, "salı": 1, "sal": 1, "tuesday": 1,
    "carsamba": 2, "çarşamba": 2, "car": 2, "çar": 2, "wednesday": 2,
    "persembe": 3, "perşembe": 3, "per": 3, "thursday": 3,
    "cuma": 4, "cum": 4, "friday": 4,
    "cumartesi": 5, "cmt": 5, "saturday": 5,
    "pazar": 6, "paz": 6, "sunday": 6,
}


def _fold(s):
    return (s or "").strip().lower().translate(str.maketrans("çğıöşüİ", "cgiosui"))


class AppActions:
    def __init__(self, win):
        self.win = win

    # ── yardımcılar ──────────────────────────────────────────────────────
    @property
    def store(self):
        return self.win.data_store

    def _days(self):
        import constraint_sync
        return constraint_sync.day_names(self.store)

    def _day_index(self, day):
        days = self._days()
        text = str(day or "").strip()
        if text.isdigit():
            i = int(text) - 1
            return i if 0 <= i < len(days) else None
        f = _fold(text)
        for i, name in enumerate(days):
            fn = _fold(name)
            if f == fn or (len(f) >= 3 and fn.startswith(f)):
                return i
        i = _DAY_ALIASES.get(f)
        return i if i is not None and i < len(days) else None

    def _find_teacher(self, name):
        """(kayıt, hata sözlüğü). Belirsizlik varsa adayları söyler."""
        teachers = [t for t in self.store.get("ogretmenler", []) if isinstance(t, dict)]
        names = [(t.get("ad") or t.get("name") or "").strip() for t in teachers]
        q = (name or "").strip()
        if not q:
            return None, {"ok": False, "message": "Öğretmen adı verilmedi."}
        exact = [t for t, n in zip(teachers, names) if _matches(q, n)]
        if len(exact) == 1:
            return exact[0], None
        fq = _fold(q)
        partial = [t for t, n in zip(teachers, names) if fq and fq in _fold(n)]
        if len(partial) == 1:
            return partial[0], None
        cands = [n for n in names if fq and any(w and w in _fold(n) for w in fq.split())]
        if not cands and not partial:
            return None, {"ok": False, "message": f"'{q}' adında bir öğretmen bulunamadı.",
                          "teachers": names[:60]}
        return None, {"ok": False, "message": f"'{q}' birden çok öğretmene uyuyor; hangisi?",
                      "candidates": (cands or [(t.get('ad') or '') for t in partial])[:10]}

    def _after_change(self, label):
        w = self.win
        try:
            if hasattr(w, "_push_undo_state"):
                w._push_undo_state(label)
        except Exception:
            pass
        try:
            w.mark_dirty()
        except Exception:
            pass
        try:
            w.save_db(sync_from_grid=False)
        except Exception:
            pass
        try:
            w._refresh_tree()
        except Exception:
            pass

    # ── araçlar ──────────────────────────────────────────────────────────
    def list_teachers(self):
        names = [(t.get("ad") or t.get("name") or "").strip()
                 for t in self.store.get("ogretmenler", []) if isinstance(t, dict)]
        return {"ok": True, "teachers": names, "message": f"{len(names)} öğretmen."}

    def teacher_availability(self, teacher):
        import constraint_sync as cs
        t, err = self._find_teacher(teacher)
        if err:
            return err
        name = (t.get("ad") or t.get("name") or "").strip()
        m = cs.get_matrix(t, name, self.store)
        days = self._days()
        out = {}
        for d, row in enumerate(m):
            if d >= len(days):
                break
            acik = [p + 1 for p, v in enumerate(row) if v != cs.CLOSED]
            kapali = [p + 1 for p, v in enumerate(row) if v == cs.CLOSED]
            out[days[d]] = {"acik_saatler": acik, "kapali_saatler": kapali}
        return {"ok": True, "teacher": name, "days": out,
                "message": f"{name}: " + "; ".join(
                    f"{k} {len(v['acik_saatler'])} açık" for k, v in out.items())}

    def set_teacher_day(self, teacher, day, open):
        import constraint_sync as cs
        t, err = self._find_teacher(teacher)
        if err:
            return err
        d = self._day_index(day)
        if d is None:
            return {"ok": False, "message": f"Gün anlaşılmadı: {day}. Günler: {', '.join(self._days())}"}
        name = (t.get("ad") or t.get("name") or "").strip()
        m = cs.get_matrix(t, name, self.store)
        state = cs.OPEN if open else cs.CLOSED
        for p in range(len(m[d])):
            m[d][p] = state
        cs.set_matrix(t, name, self.store, m)
        if open:
            personal = cs.get_personal(t, name, self.store)
            for p in range(len(personal[d])):
                personal[d][p] = False
            cs.set_personal(t, name, self.store, personal)
        self._after_change(f"{name} {self._days()[d]} {'açıldı' if open else 'kapatıldı'}")
        return {"ok": True, "message": f"{name}: {self._days()[d]} günü tamamen "
                                       f"{'açıldı' if open else 'kapatıldı'} ({len(m[d])} saat)."}

    def set_teacher_period(self, teacher, day, period, open):
        import constraint_sync as cs
        t, err = self._find_teacher(teacher)
        if err:
            return err
        d = self._day_index(day)
        if d is None:
            return {"ok": False, "message": f"Gün anlaşılmadı: {day}."}
        name = (t.get("ad") or t.get("name") or "").strip()
        m = cs.get_matrix(t, name, self.store)
        try:
            p = int(period) - 1
        except (TypeError, ValueError):
            return {"ok": False, "message": f"Ders saati anlaşılmadı: {period}."}
        if not (0 <= p < len(m[d])):
            return {"ok": False, "message": f"Ders saati 1-{len(m[d])} arasında olmalı."}
        m[d][p] = cs.OPEN if open else cs.CLOSED
        cs.set_matrix(t, name, self.store, m)
        if open:
            personal = cs.get_personal(t, name, self.store)
            personal[d][p] = False
            cs.set_personal(t, name, self.store, personal)
        self._after_change(f"{name} {self._days()[d]} {p + 1}. saat")
        return {"ok": True, "message": f"{name}: {self._days()[d]} {p + 1}. saat "
                                       f"{'açıldı' if open else 'kapatıldı'}."}

    def schedule_summary(self):
        import lesson_hours
        placements = self.store.get("grid_placements", []) or []
        placed = sum(int(p.get("duration") or 1) for p in placements if isinstance(p, dict))
        total = 0
        for a in self.store.get("atamalar", []) or []:
            try:
                total += lesson_hours.hours(a) * max(1, len(lesson_hours.classes(a)))
            except Exception:
                pass
        rep = self.store.get("auto_schedule_report") or {}
        vm = self.store.get("_version_meta") or {}
        return {"ok": True, "placed_hours": placed, "assigned_hours": total,
                "institution": getattr(self.win, "institution_slug", ""),
                "version": vm.get("custom_name") or vm.get("filename") or "",
                "last_report": {k: rep.get(k) for k in ("status", "placed_real_hours",
                                                       "total_assigned_hours") if k in rep},
                "diagnostics": [x.get("message") for x in (rep.get("diagnostics") or [])][:5],
                "message": f"{placed}/{total} saat yerleşmiş."}

    def start_auto_schedule(self):
        w = self.win
        if not self.store.get("atamalar"):
            return {"ok": False, "message": "Ders ataması yok; önce Sınıflar > Ders & Öğretmen Ata."}
        try:
            w._act_auto_schedule(auto_start=True)
        except TypeError:
            w._act_auto_schedule()
        rep = self.store.get("auto_schedule_report") or {}
        placed = rep.get("placed_real_hours")
        total = rep.get("total_assigned_hours")
        diags = [x.get("message") for x in (rep.get("diagnostics") or [])][:4]
        msg = (f"Planlama bitti: {placed}/{total} saat." if placed is not None
               else "Planlama penceresi kapandı.")
        return {"ok": True, "placed_hours": placed, "assigned_hours": total,
                "diagnostics": diags, "message": msg}

    _SCREENS = {
        "ogretmenler": "_open_teachers", "ogretmen": "_open_teachers",
        "dersler": "_open_subjects", "siniflar": "_open_classes",
        "derslikler": "_open_rooms", "secmeli": "_open_electives",
        "planlama_iliskileri": "_open_relations", "iliskiler": "_open_relations",
        "on_kontrol": "_act_test_timetable", "son_kontrol": "_act_verify_timetable",
        "temel_bilgiler": "_open_school_info", "yardim": "_act_help",
        "otomatik_planla": "_act_auto_schedule",
    }

    def open_screen(self, screen):
        key = _fold(screen).replace(" ", "_").replace("-", "_")
        meth = self._SCREENS.get(key)
        if not meth or not hasattr(self.win, meth):
            return {"ok": False, "message": f"Bilinmeyen ekran: {screen}.",
                    "screens": sorted(set(self._SCREENS))}
        getattr(self.win, meth)()
        return {"ok": True, "message": f"{screen} ekranı açıldı ve kapatıldı."}

    def save_schedule(self):
        self.win.save_db(sync_from_grid=True)
        return {"ok": True, "message": "Kaydedildi."}

    def undo(self):
        self.win._act_undo()
        return {"ok": True, "message": "Geri alındı."}

    def redo(self):
        self.win._act_redo()
        return {"ok": True, "message": "Yinelendi."}

    def unlock_all_lessons(self):
        g = getattr(self.win, "_grid", None)
        if g is None or not hasattr(g, "_unlock_all_lessons"):
            return {"ok": False, "message": "Çizelge açık değil."}
        g._unlock_all_lessons()
        return {"ok": True, "message": "Bütün kilitler açıldı."}

    # ── dağıtıcı ─────────────────────────────────────────────────────────
    def execute(self, name, args):
        fn = getattr(self, name, None)
        if fn is None or name.startswith("_") or name == "execute":
            return {"ok": False, "message": f"Bilinmeyen araç: {name}"}
        try:
            return fn(**(args or {}))
        except TypeError as exc:
            return {"ok": False, "message": f"Araç argümanları hatalı: {exc}"}
        except Exception as exc:
            return {"ok": False, "message": f"Hata: {exc}"}
