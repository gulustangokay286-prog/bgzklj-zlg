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

    # ── veri okuma ───────────────────────────────────────────────────────
    def _entity(self, group, name, label):
        items = [x for x in self.store.get(group, []) if isinstance(x, dict)]
        names = [(x.get("ad") or x.get("name") or "").strip() for x in items]
        q = _fold(name)
        if not q:
            return None, {"ok": False, "message": f"{label} adı verilmedi."}
        try:
            from scheduler.model import norm_class
            key = norm_class
        except Exception:
            key = _fold
        exact = [x for x, n in zip(items, names) if key(n) == key(name)]
        if len(exact) == 1:
            return exact[0], None
        part = [x for x, n in zip(items, names) if q in _fold(n)]
        if len(part) == 1:
            return part[0], None
        if not part:
            return None, {"ok": False, "message": f"'{name}' adında {label.lower()} yok.",
                          "available": names[:80]}
        return None, {"ok": False, "message": f"'{name}' birden çok kayda uyuyor.",
                      "candidates": [(x.get("ad") or "") for x in part][:10]}

    def list_classes(self):
        out = []
        for c in self.store.get("siniflar", []) or []:
            if isinstance(c, dict):
                out.append({"name": (c.get("ad") or "").strip(), "type": c.get("sinif_tipi", "")})
        return {"ok": True, "classes": out, "message": f"{len(out)} sınıf."}

    def list_subjects(self):
        names = [(d.get("ad") or "").strip() for d in self.store.get("dersler", []) if isinstance(d, dict)]
        return {"ok": True, "subjects": names, "message": f"{len(names)} ders."}

    def list_assignments(self, class_name=None, teacher=None):
        import lesson_hours
        out = []
        for a in self.store.get("atamalar", []) or []:
            if not isinstance(a, dict):
                continue
            cn = lesson_hours.class_name(a)
            tn = lesson_hours.teacher(a)
            if class_name and _fold(class_name) not in _fold(cn):
                continue
            if teacher and not (_matches(teacher, tn) or _fold(teacher) in _fold(tn)):
                continue
            out.append({"class": cn, "subject": lesson_hours.subject(a), "teacher": tn,
                        "hours": lesson_hours.hours(a), "distribution": lesson_hours.type_str(a)})
        return {"ok": True, "assignments": out[:200], "message": f"{len(out)} atama."}

    def _placements(self):
        for p in self.store.get("grid_placements", []) or []:
            if not isinstance(p, dict):
                continue
            yield {"class": (p.get("class_name") or p.get("class") or "").strip(),
                   "subject": (p.get("subject_name") or p.get("subject") or "").strip(),
                   "teacher": (p.get("teacher_name") or p.get("teacher") or "").strip(),
                   "day": int(p.get("day", p.get("col", 0)) or 0),
                   "period": int(p.get("period", p.get("row", 0)) or 0),
                   "duration": int(p.get("duration") or 1),
                   "locked": bool(p.get("locked")), "_raw": p}

    def teacher_schedule(self, teacher):
        t, err = self._find_teacher(teacher)
        if err:
            return err
        name = (t.get("ad") or t.get("name") or "").strip()
        days = self._days()
        by_day = {d: [] for d in days}
        for pl in self._placements():
            if _matches(pl["teacher"], name) and pl["day"] < len(days):
                for k in range(pl["duration"]):
                    by_day[days[pl["day"]]].append(f"{pl['period'] + 1 + k}. saat {pl['subject']} ({pl['class']})")
        for d in by_day:
            by_day[d].sort(key=lambda s: int(s.split(".")[0]))
        total = sum(len(v) for v in by_day.values())
        return {"ok": True, "teacher": name, "days": by_day, "message": f"{name}: haftada {total} saat yerleşmiş."}

    def class_schedule(self, class_name):
        c, err = self._entity("siniflar", class_name, "Sınıf")
        if err:
            return err
        name = (c.get("ad") or "").strip()
        days = self._days()
        by_day = {d: [] for d in days}
        for pl in self._placements():
            if _fold(pl["class"]) == _fold(name) and pl["day"] < len(days):
                for k in range(pl["duration"]):
                    by_day[days[pl["day"]]].append(f"{pl['period'] + 1 + k}. saat {pl['subject']} — {pl['teacher']}")
        for d in by_day:
            by_day[d].sort(key=lambda s: int(s.split(".")[0]))
        return {"ok": True, "class": name, "days": by_day,
                "message": f"{name}: {sum(len(v) for v in by_day.values())} saat yerleşmiş."}

    def free_slots(self, teacher):
        """Öğretmenin açık VE boş saatleri."""
        import constraint_sync as cs
        t, err = self._find_teacher(teacher)
        if err:
            return err
        name = (t.get("ad") or t.get("name") or "").strip()
        m = cs.get_matrix(t, name, self.store)
        busy = set()
        for pl in self._placements():
            if _matches(pl["teacher"], name):
                for k in range(pl["duration"]):
                    busy.add((pl["day"], pl["period"] + k))
        days = self._days()
        out = {}
        for d in range(min(len(m), len(days))):
            out[days[d]] = [p + 1 for p in range(len(m[d])) if m[d][p] != cs.CLOSED and (d, p) not in busy]
        return {"ok": True, "teacher": name, "free": out,
                "message": f"{name}: " + "; ".join(f"{k} {len(v)} boş" for k, v in out.items())}

    def unplaced_lessons(self):
        import lesson_hours
        placed = {}
        for pl in self._placements():
            key = (_fold(pl["class"]), _fold(pl["subject"]), _norm(pl["teacher"]))
            placed[key] = placed.get(key, 0) + pl["duration"]
        out = []
        for a in self.store.get("atamalar", []) or []:
            if not isinstance(a, dict):
                continue
            for cn in lesson_hours.classes(a) or [lesson_hours.class_name(a)]:
                key = (_fold(cn), _fold(lesson_hours.subject(a)), _norm(lesson_hours.teacher(a)))
                need = lesson_hours.hours(a)
                have = placed.get(key, 0)
                if have < need:
                    out.append({"class": cn, "subject": lesson_hours.subject(a),
                                "teacher": lesson_hours.teacher(a), "missing_hours": need - have})
        rep = self.store.get("auto_schedule_report") or {}
        return {"ok": True, "unplaced": out[:100],
                "diagnostics": [x.get("message") for x in (rep.get("diagnostics") or [])][:6],
                "message": f"{sum(x['missing_hours'] for x in out)} saat açıkta ({len(out)} ders)."}

    def list_rules(self):
        out = []
        for i, r in enumerate(self.store.get("planlama_iliskileri", []) or []):
            if not isinstance(r, dict):
                continue
            out.append({"index": i, "rule": r.get("kural"), "active": bool(r.get("aktif", True)),
                        "importance": r.get("onem"), "subjects": r.get("dersler") or [],
                        "classes": r.get("siniflar") or [], "teachers": r.get("ogretmenler") or [],
                        "param": r.get("parametre")})
        return {"ok": True, "rules": out, "message": f"{len(out)} kural."}

    def precheck(self):
        """Ön Kontrol: bu veriyle çizelge dolar mı? (auto_scheduler.check_feasibility)"""
        from auto_scheduler import check_feasibility
        rep = check_feasibility(self.store, getattr(self.win, "institution_slug", None)) or {}
        keys = ("ok", "total_cells", "total_demand", "max_fillable", "idle_teachers",
                "understaffed_slots", "overloaded_teachers")
        out = {k: rep.get(k) for k in keys}
        out["message"] = ("Uygun: bütün saatler yerleşebilir." if rep.get("ok")
                          else f"Sorun var: en fazla {rep.get('max_fillable')}/{rep.get('total_demand')} saat yerleşir.")
        return out

    def verify_schedule(self):
        """Son Kontrol: her yerleşmiş dersi motorla aynı analizden geçirir."""
        import placement_engine as pe
        snap = pe.TimetableSnapshot(self.store, institution_slug=getattr(self.win, "institution_slug", None))
        issues = []
        seen = set()
        for pl in self._placements():
            raw = pl["_raw"]
            lesson = dict(raw)
            snap2 = pe.TimetableSnapshot(self.store, exclude_block_id=raw.get("block_id")) \
                if raw.get("block_id") else snap
            cand = pe.CandidatePlacement(lesson, pl["day"], pl["period"], pl["duration"])
            res = pe.analyze(snap2, lesson, cand)
            for c in res.conflicts:
                if c.severity < pe.SEV_SOFT:
                    continue
                key = (c.type, c.message)
                if key in seen:
                    continue
                seen.add(key)
                issues.append({"severity": "sert" if c.severity >= pe.SEV_HARD else "kural",
                               "message": c.message})
            if len(issues) >= 60:
                break
        return {"ok": not issues, "issues": issues,
                "message": "Çizelge temiz: çakışma ve kural ihlali yok." if not issues
                else f"{len(issues)} sorun bulundu."}

    # ── kurumlar arası (yalnızca OKUMA) ──────────────────────────────────
    def list_institutions(self):
        import version_store as vs
        out = []
        for inst in vs.list_institutions() or []:
            out.append({"slug": inst.get("slug"), "name": inst.get("name", inst.get("slug")),
                        "active_version": inst.get("active_version")})
        return {"ok": True, "institutions": out,
                "current": getattr(self.win, "institution_slug", None),
                "message": f"{len(out)} kurum."}

    def _find_institution(self, institution):
        """(slug, ad) — ada ya da kısaltmaya göre kurum bulur."""
        import version_store as vs
        q = _fold(institution)
        if not q:
            return None, None
        best = None
        for inst in vs.list_institutions() or []:
            name, slug = _fold(inst.get("name", "")), _fold(inst.get("slug", ""))
            if q == name or q == slug:
                return inst.get("slug"), inst.get("name", inst.get("slug"))
            if q in name or q in slug:
                best = best or inst
        if best:
            return best.get("slug"), best.get("name", best.get("slug"))
        return None, None

    def _institution_store(self, institution):
        """(veri, kurum adı, sürüm etiketi) — kurumun EN SON çizelgesi.

        Kullanıcı başka kurumu sorduğunda "en son durumu" bekler; aktif
        sürüm günler önce işaretlenmiş olabilir. Bu yüzden en yeni sürüm
        (list_versions zaten en yeniden sıralar) esas alınır; kurum şu anda
        açık olan kurumsa bellekteki veri kullanılır.
        """
        import version_store as vs
        slug, name = self._find_institution(institution)
        if not slug:
            return None, None, ""
        if slug == getattr(self.win, "institution_slug", None):
            vm = self.store.get("_version_meta") or {}
            return self.store, name, (vm.get("custom_name") or vm.get("filename") or "açık çizelge")
        vers = vs.list_versions(slug, source_filter="all") or []
        if not vers:
            return None, name, ""
        # "En son" = en son DEĞİŞTİRİLEN. Liste dosya adına göre sıralı; sürüm
        # numarası büyük olan her zaman en son düzenlenen olmayabilir.
        try:
            v = max(vers, key=lambda x: x.get("datetime"))
        except Exception:
            v = vers[0]
        data = vs.load_version(slug, v["filename"])
        etiket = (v.get("custom_name") or v["filename"]) + f" ({v.get('date_str','')} {v.get('time_str','')})"
        return data, name, etiket

    # Aşağıdaki araçlar BAŞKA kurumları yalnızca OKUR; hiçbiri yazmaz.
    def institution_info(self, institution):
        """Bir kurumun en son çizelgesinden özet: öğretmen/sınıf/ders sayısı, saatler."""
        import lesson_hours
        data, name, etiket = self._institution_store(institution)
        if data is None:
            return {"ok": False, "message": f"'{institution}' kurumu bulunamadı ya da çizelgesi yok.",
                    "institutions": [i.get("name") for i in __import__("version_store").list_institutions() or []]}
        teachers = [t for t in data.get("ogretmenler", []) if isinstance(t, dict)]
        classes = [c for c in data.get("siniflar", []) if isinstance(c, dict)]
        subjects = [d for d in data.get("dersler", []) if isinstance(d, dict)]
        assigned = 0
        for a in data.get("atamalar", []) or []:
            try:
                assigned += lesson_hours.hours(a) * max(1, len(lesson_hours.classes(a)))
            except Exception:
                pass
        placed = sum(int(p.get("duration") or 1) for p in data.get("grid_placements", []) or []
                     if isinstance(p, dict))
        return {"ok": True, "institution": name, "version": etiket,
                "teacher_count": len(teachers), "class_count": len(classes),
                "subject_count": len(subjects), "assigned_hours": assigned, "placed_hours": placed,
                "message": f"{name} ({etiket}): {len(teachers)} öğretmen, {len(classes)} sınıf, "
                           f"{len(subjects)} ders, {placed}/{assigned} saat yerleşmiş."}

    def institution_teachers(self, institution):
        """Bir kurumun en son çizelgesindeki öğretmen adları (ve ders saatleri)."""
        import lesson_hours
        data, name, etiket = self._institution_store(institution)
        if data is None:
            return {"ok": False, "message": f"'{institution}' kurumu bulunamadı ya da çizelgesi yok."}
        load = {}
        for a in data.get("atamalar", []) or []:
            try:
                t = lesson_hours.teacher(a)
                load[t] = load.get(t, 0) + lesson_hours.hours(a) * max(1, len(lesson_hours.classes(a)))
            except Exception:
                pass
        out = []
        for t in data.get("ogretmenler", []) or []:
            if isinstance(t, dict):
                ad = (t.get("ad") or t.get("name") or "").strip()
                if ad:
                    out.append({"name": ad, "branch": t.get("brans", ""),
                                "assigned_hours": load.get(ad, 0)})
        return {"ok": True, "institution": name, "version": etiket, "teachers": out,
                "message": f"{name} ({etiket}): {len(out)} öğretmen."}

    def institution_classes(self, institution):
        """Bir kurumun en son çizelgesindeki sınıflar."""
        data, name, etiket = self._institution_store(institution)
        if data is None:
            return {"ok": False, "message": f"'{institution}' kurumu bulunamadı ya da çizelgesi yok."}
        names = [(c.get("ad") or "").strip() for c in data.get("siniflar", []) if isinstance(c, dict)]
        return {"ok": True, "institution": name, "version": etiket, "classes": names,
                "message": f"{name} ({etiket}): {len(names)} sınıf."}

    def institution_teacher_schedule(self, institution, teacher):
        """Bir öğretmenin BAŞKA kurumdaki haftalık programı (gün gün ders)."""
        import constraint_sync as cs
        data, name_i, etiket = self._institution_store(institution)
        if data is None:
            return {"ok": False, "message": f"'{institution}' kurumu bulunamadı ya da çizelgesi yok."}
        teachers = [t for t in data.get("ogretmenler", []) if isinstance(t, dict)]
        hits = [t for t in teachers if _matches(teacher, t.get("ad") or "")
                or _fold(teacher) in _fold(t.get("ad") or "")]
        if not hits:
            return {"ok": False, "message": f"{name_i}: '{teacher}' adında öğretmen yok.",
                    "teachers": [(t.get("ad") or "") for t in teachers][:80]}
        name = (hits[0].get("ad") or "").strip()
        days = cs.day_names(data)
        by_day = {d: [] for d in days}
        for p in data.get("grid_placements", []) or []:
            if not isinstance(p, dict):
                continue
            if not _matches(p.get("teacher_name") or p.get("teacher") or "", name):
                continue
            d = int(p.get("day", p.get("col", 0)) or 0)
            pr = int(p.get("period", p.get("row", 0)) or 0)
            if d >= len(days):
                continue
            for k in range(int(p.get("duration") or 1)):
                by_day[days[d]].append(
                    f"{pr + 1 + k}. saat {(p.get('subject_name') or p.get('subject') or '')}"
                    f" ({(p.get('class_name') or p.get('class') or '')})")
        for d in by_day:
            by_day[d].sort(key=lambda x: int(x.split(".")[0]))
        total = sum(len(v) for v in by_day.values())
        return {"ok": True, "institution": name_i, "version": etiket, "teacher": name,
                "days": by_day, "message": f"{name_i} ({etiket}) — {name}: {total} saat dersi var."}

    def institution_teacher_availability(self, institution, teacher):
        import constraint_sync as cs
        data, name_i, etiket = self._institution_store(institution)
        if data is None:
            return {"ok": False, "message": f"'{institution}' kurumu bulunamadı ya da çizelgesi yok."}
        teachers = [t for t in data.get("ogretmenler", []) if isinstance(t, dict)]
        hits = [t for t in teachers if _matches(teacher, t.get("ad") or "") or _fold(teacher) in _fold(t.get("ad") or "")]
        if not hits:
            return {"ok": False, "message": f"{name_i}: '{teacher}' adında öğretmen yok.",
                    "teachers": [(t.get("ad") or "") for t in teachers][:60]}
        t = hits[0]
        name = (t.get("ad") or "").strip()
        m = cs.get_matrix(t, name, data)
        days = cs.day_names(data)
        out = {}
        busy = {}
        for p in data.get("grid_placements", []) or []:
            if isinstance(p, dict) and _matches(p.get("teacher_name") or p.get("teacher") or "", name):
                d = int(p.get("day", p.get("col", 0)) or 0)
                pr = int(p.get("period", p.get("row", 0)) or 0)
                for k in range(int(p.get("duration") or 1)):
                    busy.setdefault(d, []).append(pr + 1 + k)
        for d in range(min(len(m), len(days))):
            out[days[d]] = {"kapali_saatler": [p + 1 for p, v in enumerate(m[d]) if v == cs.CLOSED],
                            "ders_saatleri": sorted(busy.get(d, []))}
        return {"ok": True, "institution": name_i, "version": etiket, "teacher": name, "days": out,
                "message": f"{name_i} ({etiket}) — {name}: " + "; ".join(
                    f"{k}: kapalı {v['kapali_saatler'] or '-'}, ders {v['ders_saatleri'] or '-'}"
                    for k, v in out.items())}

    # ── yazma: sınıf tablosu, kurallar, atamalar, dersler ────────────────
    def set_class_day(self, class_name, day, open):
        import constraint_sync as cs
        c, err = self._entity("siniflar", class_name, "Sınıf")
        if err:
            return err
        d = self._day_index(day)
        if d is None:
            return {"ok": False, "message": f"Gün anlaşılmadı: {day}."}
        name = (c.get("ad") or "").strip()
        m = cs.get_matrix(c, name, self.store)
        for p in range(len(m[d])):
            m[d][p] = cs.OPEN if open else cs.CLOSED
        cs.set_matrix(c, name, self.store, m)
        self._after_change(f"{name} {self._days()[d]}")
        return {"ok": True, "message": f"{name}: {self._days()[d]} {'açıldı' if open else 'kapatıldı'}."}

    def set_class_period(self, class_name, day, period, open):
        import constraint_sync as cs
        c, err = self._entity("siniflar", class_name, "Sınıf")
        if err:
            return err
        d = self._day_index(day)
        if d is None:
            return {"ok": False, "message": f"Gün anlaşılmadı: {day}."}
        name = (c.get("ad") or "").strip()
        m = cs.get_matrix(c, name, self.store)
        p = int(period) - 1
        if not (0 <= p < len(m[d])):
            return {"ok": False, "message": f"Ders saati 1-{len(m[d])} arasında olmalı."}
        m[d][p] = cs.OPEN if open else cs.CLOSED
        cs.set_matrix(c, name, self.store, m)
        self._after_change(f"{name} {self._days()[d]} {p + 1}. saat")
        return {"ok": True, "message": f"{name}: {self._days()[d]} {p + 1}. saat {'açıldı' if open else 'kapatıldı'}."}

    _RULE_KINDS = {
        "ayni_ders_ayni_gun": "Aynı ders aynı gün tekrar etmesin",
        "iki_ders_ayni_gune_gelmesin": "İki ders aynı güne gelmesin",
        "ayni_ders_sayilsin": "Seçilen dersler aynı ders sayılsın",
        "ayni_ders_art_arda_gelmesin": "Aynı ders art arda gelmesin",
        "iki_zor_ders_art_arda": "İki zor ders art arda gelmesin",
        "gunde_maksimum_ders": "Günde maksimum ders sayısı",
        "ayni_ogretmen_ayni_gun": "Aynı öğretmen aynı gün tekrar etmesin",
        "ogretmen_haftada_en_fazla_n_gun": "Öğretmen haftada en fazla N gün",
        "sinif_gunde_en_fazla_n_saat": "Sınıf günde en fazla N saat",
        "ogretmen_gunde_en_fazla_n_saat": "Öğretmen günde en fazla N saat",
        "sinifta_bos_saat_kalmasin": "Sınıfta boş saat kalmasın",
        "ogretmende_bos_saat_kalmasin": "Öğretmende boş saat kalmasın",
        "ders_ogleden_once": "Öğretmenin dersleri öğleden önce toplansın",
        "ders_ogleden_sonra": "Öğretmenin dersleri öğleden sonra toplansın",
        "son_derse_zor_ders_konulmasin": "Son ders saatine zor ders konulmasın",
        "ilk_derse_konulmasin": "İlk ders saatine konulmasın",
    }

    def add_rule(self, kind, subjects=None, classes=None, teachers=None, importance="sıkı", param=None):
        label = self._RULE_KINDS.get(_fold(kind).replace(" ", "_"))
        if not label:
            # serbest metin: bilinen adlardan birine yakınsa kabul et
            for k, v in self._RULE_KINDS.items():
                if _fold(kind) in _fold(v) or _fold(v) in _fold(kind):
                    label = v
                    break
        if not label:
            return {"ok": False, "message": f"Bilinmeyen kural: {kind}.",
                    "kinds": list(self._RULE_KINDS)}
        onem = "Sıkı (Kesinlikle uygulanmalı)" if _fold(importance).startswith("s") or _fold(importance) == "hard" \
            else "Yüksek" if _fold(importance).startswith("y") else "Normal"
        # ad doğrulama: ders/sınıf/öğretmen listelerinde olmalı
        subj_all = {_fold(d.get("ad") or ""): (d.get("ad") or "") for d in self.store.get("dersler", []) if isinstance(d, dict)}
        cls_all = {_fold(c.get("ad") or ""): (c.get("ad") or "") for c in self.store.get("siniflar", []) if isinstance(c, dict)}
        tch_all = [(t.get("ad") or "") for t in self.store.get("ogretmenler", []) if isinstance(t, dict)]
        subs, bad = [], []
        for sname in (subjects or []):
            m = subj_all.get(_fold(sname)) or next((v for k, v in subj_all.items() if _fold(sname) in k), None)
            (subs if m else bad).append(m or sname)
        if bad:
            return {"ok": False, "message": f"Ders bulunamadı: {', '.join(bad)}", "subjects": list(subj_all.values())[:80]}
        clss, bad = [], []
        for cname in (classes or []):
            m = cls_all.get(_fold(cname)) or next((v for k, v in cls_all.items() if _fold(cname) in k), None)
            (clss if m else bad).append(m or cname)
        if bad:
            return {"ok": False, "message": f"Sınıf bulunamadı: {', '.join(bad)}", "classes": list(cls_all.values())}
        tchs, bad = [], []
        for tname in (teachers or []):
            m = next((n for n in tch_all if _matches(tname, n) or _fold(tname) in _fold(n)), None)
            (tchs if m else bad).append(m or tname)
        if bad:
            return {"ok": False, "message": f"Öğretmen bulunamadı: {', '.join(bad)}"}
        if label in ("İki ders aynı güne gelmesin", "Seçilen dersler aynı ders sayılsın") and len(subs) < 2:
            return {"ok": False, "message": f"'{label}' için en az iki ders seçilmeli."}
        rec = {"kural": label, "aktif": True, "onem": onem, "dersler": subs, "siniflar": clss,
               "ogretmenler": tchs, "parametre": param, "period_start": None, "period_end": None}
        self.store.setdefault("planlama_iliskileri", []).append(rec)
        self._after_change(f"Kural eklendi: {label}")
        return {"ok": True, "message": f"Kural eklendi: {label}" + (f" ({' + '.join(subs)})" if subs else "")
                + (f" — sınıflar: {', '.join(clss)}" if clss else "") + f" [{onem}]."}

    def _rule_at(self, index):
        rules = self.store.get("planlama_iliskileri", []) or []
        try:
            i = int(index)
        except (TypeError, ValueError):
            return None, {"ok": False, "message": "Kural numarası gerekli (list_rules ile bak)."}
        if not (0 <= i < len(rules)):
            return None, {"ok": False, "message": f"Kural numarası 0-{len(rules) - 1} arasında olmalı."}
        return i, None

    def remove_rule(self, index):
        i, err = self._rule_at(index)
        if err:
            return err
        r = self.store["planlama_iliskileri"].pop(i)
        self._after_change("Kural silindi")
        return {"ok": True, "message": f"Kural silindi: {r.get('kural')}."}

    def set_rule_active(self, index, active):
        i, err = self._rule_at(index)
        if err:
            return err
        self.store["planlama_iliskileri"][i]["aktif"] = bool(active)
        self._after_change("Kural durumu")
        return {"ok": True, "message": f"Kural {'açıldı' if active else 'kapatıldı'}: "
                                       f"{self.store['planlama_iliskileri'][i].get('kural')}."}

    def add_assignment(self, class_name, subject, teacher, distribution):
        c, err = self._entity("siniflar", class_name, "Sınıf")
        if err:
            return err
        d, err = self._entity("dersler", subject, "Ders")
        if err:
            return err
        t, err = self._find_teacher(teacher)
        if err:
            return err
        import lesson_hours
        dist = str(distribution or "").replace(" ", "")
        if not re.fullmatch(r"\d+(\+\d+)*", dist):
            return {"ok": False, "message": "Dağılım '2+2+1' biçiminde olmalı."}
        rec = {"class": c.get("ad"), "subject": d.get("ad"), "teacher": t.get("ad"),
               "type": dist, "duration": sum(int(x) for x in dist.split("+")),
               "renk": d.get("renk") or d.get("color"), "color": d.get("color") or d.get("renk"),
               "is_combined": False, "combined_classes": []}
        for a in self.store.get("atamalar", []) or []:
            if (_fold(lesson_hours.class_name(a)) == _fold(rec["class"])
                    and _fold(lesson_hours.subject(a)) == _fold(rec["subject"])):
                return {"ok": False, "message": f"{rec['class']} sınıfında {rec['subject']} zaten atanmış "
                                                f"({lesson_hours.teacher(a)}, {lesson_hours.type_str(a)})."}
        self.store.setdefault("atamalar", []).append(rec)
        self._after_change(f"Atama: {rec['class']} {rec['subject']}")
        try:
            self.win._refresh_unplaced_lessons()
        except Exception:
            pass
        return {"ok": True, "message": f"{rec['class']}: {rec['subject']} — {rec['teacher']} ({dist}) atandı."}

    def remove_assignment(self, class_name, subject):
        import lesson_hours
        arr = self.store.get("atamalar", []) or []
        hit = [a for a in arr if isinstance(a, dict) and _fold(class_name) in _fold(lesson_hours.class_name(a))
               and _fold(subject) == _fold(lesson_hours.subject(a))]
        if not hit:
            return {"ok": False, "message": f"{class_name} sınıfında {subject} ataması yok."}
        arr.remove(hit[0])
        self._after_change("Atama silindi")
        return {"ok": True, "message": f"{class_name}: {subject} ataması kaldırıldı."}

    def add_subject(self, name, short=None):
        if any(_fold(d.get("ad") or "") == _fold(name) for d in self.store.get("dersler", []) if isinstance(d, dict)):
            return {"ok": False, "message": f"'{name}' dersi zaten var."}
        self.store.setdefault("dersler", []).append({"ad": name.strip(), "kisa": (short or name[:6]).upper(),
                                                     "renk": "#C4C4F0", "color": "#4F6BED", "ozel_alanlar": {}})
        self._after_change(f"Ders: {name}")
        return {"ok": True, "message": f"'{name}' dersi eklendi."}

    def add_teacher(self, name, branch=None):
        if any(_matches(name, t.get("ad") or "") for t in self.store.get("ogretmenler", []) if isinstance(t, dict)):
            return {"ok": False, "message": f"'{name}' zaten kayıtlı."}
        self.store.setdefault("ogretmenler", []).append({"ad": name.strip(), "kisa": "", "brans": branch or "", "ozel_alanlar": {}})
        self._after_change(f"Öğretmen: {name}")
        return {"ok": True, "message": f"'{name}' öğretmen olarak eklendi."}

    # ── yazma: çizelge ───────────────────────────────────────────────────
    def clear_schedule(self):
        """Çizelgeyi sıfırlar — onay SORULMAZ.

        Kullanıcı bunu zaten asistana söyledi; üstüne bir de evet/hayır
        kutusu çıkarmak aynı kararı iki kez sormaktır. Geri alınabilir:
        işlem öncesi durum geçmişe konur (Ctrl+Z).
        """
        before = len(self.store.get("grid_placements", []) or [])
        if before == 0:
            return {"ok": True, "message": "Çizelge zaten boştu."}
        try:
            self.win._push_undo_state("Çizelge sıfırlandı (asistan)")
        except Exception:
            pass
        self.store["grid_placements"] = []
        self.store["auto_schedule_results"] = []
        self.store["yerlesim"] = {}
        self.store["loose_unplaced_cards"] = []
        self.store["manual_unplaced_cards"] = []
        g = getattr(self.win, "_grid", None)
        if g is not None and hasattr(g, "clear_grid"):
            g.clear_grid()
        try:
            self.win.mark_dirty()
        except Exception:
            pass
        try:
            self.win.save_db(sync_from_grid=False)
        except Exception:
            pass
        for fn in ("_refresh_grid", "_refresh_unplaced_lessons", "_refresh_tree"):
            try:
                getattr(self.win, fn)()
            except Exception:
                pass
        return {"ok": True, "message": f"Çizelge sıfırlandı: {before} yerleşim kaldırıldı "
                                       f"(geri almak için Ctrl+Z)."}

    def _find_placement(self, class_name, subject, teacher=None):
        hits = [pl for pl in self._placements()
                if _fold(class_name) in _fold(pl["class"]) and _fold(subject) == _fold(pl["subject"])
                and (not teacher or _matches(teacher, pl["teacher"]))]
        return hits

    def move_lesson(self, class_name, subject, day, period, teacher=None):
        """Bir sınıfın bir dersini (ilk bloğunu) verilen gün/saate taşır; çakışma varsa taşımaz."""
        import placement_engine as pe
        hits = self._find_placement(class_name, subject, teacher)
        if not hits:
            return {"ok": False, "message": f"{class_name} sınıfında yerleşmiş {subject} dersi yok."}
        d = self._day_index(day)
        if d is None:
            return {"ok": False, "message": f"Gün anlaşılmadı: {day}."}
        p = int(period) - 1
        pl = hits[0]
        raw = pl["_raw"]
        snap = pe.TimetableSnapshot(self.store, exclude_block_id=raw.get("block_id"))
        cand = pe.CandidatePlacement(dict(raw), d, p, pl["duration"])
        res = pe.analyze(snap, dict(raw), cand)
        if res.status in (pe.FORBIDDEN, pe.INVALID_GEOMETRY, pe.CONFLICT):
            return {"ok": False, "message": f"Taşınamadı: {res.explanation}",
                    "conflicts": [c.message for c in res.conflicts[:4]]}
        if hasattr(self.win, "_push_undo_state"):
            self.win._push_undo_state("Asistan taşıdı")
        raw["day"] = d; raw["col"] = d; raw["period"] = p; raw["row"] = p
        self._after_change("Ders taşındı")
        try:
            self.win._refresh_grid()
        except Exception:
            pass
        warn = [c.message for c in res.rule_violations] if hasattr(res, "rule_violations") else []
        return {"ok": True, "message": f"{pl['class']} {pl['subject']} → {self._days()[d]} {p + 1}. saat.",
                "warnings": warn}

    def lock_lesson(self, class_name, subject, locked=True):
        hits = self._find_placement(class_name, subject)
        if not hits:
            return {"ok": False, "message": f"{class_name} sınıfında yerleşmiş {subject} dersi yok."}
        for pl in hits:
            pl["_raw"]["locked"] = bool(locked)
            pl["_raw"]["is_manual"] = bool(locked)
        self._after_change("Kilit")
        try:
            self.win._refresh_grid()
        except Exception:
            pass
        return {"ok": True, "message": f"{len(hits)} blok {'kilitlendi' if locked else 'serbest bırakıldı'}."}

    def remove_lesson_from_grid(self, class_name, subject):
        hits = self._find_placement(class_name, subject)
        if not hits:
            return {"ok": False, "message": f"{class_name} sınıfında yerleşmiş {subject} dersi yok."}
        arr = self.store.get("grid_placements", [])
        for pl in hits:
            if pl["_raw"] in arr:
                arr.remove(pl["_raw"])
        self._after_change("Ders çizelgeden alındı")
        try:
            self.win._refresh_grid(); self.win._refresh_unplaced_lessons()
        except Exception:
            pass
        return {"ok": True, "message": f"{class_name} {subject}: {len(hits)} blok çizelgeden alındı (açıkta)."}

    def go_home(self):
        top = self.win.window()
        for name in ("_go_home", "go_home", "show_dashboard"):
            fn = getattr(top, name, None) or getattr(self.win, name, None)
            if callable(fn):
                fn()
                return {"ok": True, "message": "Anasayfaya dönüldü."}
        return {"ok": False, "message": "Anasayfa geçişi bulunamadı."}

    def print_preview(self):
        self.win._act_preview()
        return {"ok": True, "message": "Yazdırma önizlemesi açıldı."}

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
