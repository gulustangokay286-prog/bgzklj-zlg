"""
advisor.py — "Danışman": tells the user WHY the timetable is the way it is.

This is deliberately not a second scheduler. It answers the question the user keeps
asking after a run — "why is this class not full?" — with arithmetic they can check
themselves, and with the one action that would actually change the answer.

Every finding carries:
    severity  "error" | "warning" | "info"
    title     one line
    detail    the numbers behind it
    action    what to change, or "" when nothing can be

Pure functions over data_store; no Qt, so it is testable headless.
"""
from collections import defaultdict

import lesson_hours


def _norm(value) -> str:
    return " ".join(str(value or "").split()).strip()


def _int(value, default=0):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _dims(data_store):
    settings = data_store.get("settings", {}) or {}
    days = settings.get("days")
    if not days:
        count = _int(settings.get("day_count", data_store.get("gun_sayisi", 5)), 5)
        days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma",
                "Cumartesi", "Pazar"][:count]
    periods = _int(settings.get("periods", data_store.get("ders_saati", 8)), 8) or 8
    return list(days), periods


def open_slots_per_class(data_store):
    """{class: number of periods NOT closed in the Zaman Tablosu screen}.

    timeoff is [day][period] with 2 = open. A class with no timeoff grid is fully
    open, which is what a freshly created class looks like.
    """
    days, periods = _dims(data_store)
    out = {}
    for c in data_store.get("siniflar", []) or []:
        if not isinstance(c, dict):
            continue
        name = _norm(c.get("ad") or c.get("name"))
        if not name:
            continue
        grid = c.get("timeoff")
        if not isinstance(grid, list) or not grid:
            out[name] = len(days) * periods
            continue
        count = 0
        for d in range(min(len(days), len(grid))):
            row = grid[d] if isinstance(grid[d], list) else []
            for p in range(min(periods, len(row))):
                if row[p] == 2:
                    count += 1
        out[name] = count
    return out


def demand_per_class(data_store):
    """{class: total weekly hours assigned to it}.

    Saatler lesson_hours üzerinden okunur — sınıf ekranı, öğretmen ekranı,
    istatistik ekranı ve otomatik planlayıcı ile aynı kaynak.
    """
    return lesson_hours.per_class(data_store)


def demand_per_teacher(data_store):
    return lesson_hours.per_teacher(data_store)


def teacher_capacity(data_store):
    """{teacher: how many hours the teacher COULD teach}.

    A teacher can only be in one room at a time, so their ceiling is the number of
    distinct periods in which at least one of their classes is open — intersected
    with their own time-off if they have one.
    """
    days, periods = _dims(data_store)
    class_open = {}
    for c in data_store.get("siniflar", []) or []:
        if not isinstance(c, dict):
            continue
        name = _norm(c.get("ad") or c.get("name"))
        grid = c.get("timeoff")
        slots = set()
        if not isinstance(grid, list) or not grid:
            slots = {(d, p) for d in range(len(days)) for p in range(periods)}
        else:
            for d in range(min(len(days), len(grid))):
                row = grid[d] if isinstance(grid[d], list) else []
                for p in range(min(periods, len(row))):
                    if row[p] == 2:
                        slots.add((d, p))
        class_open[name] = slots

    teacher_classes = defaultdict(set)
    for a in data_store.get("atamalar", []) or []:
        if isinstance(a, dict):
            t = _norm(a.get("teacher") or a.get("ogretmen"))
            c = _norm(a.get("class") or a.get("sinif"))
            if t and c:
                teacher_classes[t].add(c)

    own_off = {}
    for t in data_store.get("ogretmenler", []) or []:
        if isinstance(t, dict):
            own_off[_norm(t.get("ad") or t.get("name"))] = t.get("timeoff")

    out = {}
    for teacher, classes in teacher_classes.items():
        reachable = set()
        for cls in classes:
            reachable |= class_open.get(cls, set())
        grid = own_off.get(teacher)
        if isinstance(grid, list) and grid:
            personal = set()
            for d in range(min(len(days), len(grid))):
                row = grid[d] if isinstance(grid[d], list) else []
                for p in range(min(periods, len(row))):
                    if row[p] == 2:
                        personal.add((d, p))
            reachable &= personal
        out[teacher] = len(reachable)
    return out


def placed_per_class(data_store):
    out = defaultdict(int)
    for p in data_store.get("grid_placements", []) or []:
        if isinstance(p, dict):
            cls = _norm(p.get("class_name") or p.get("class"))
            if cls:
                out[cls] += max(1, _int(p.get("duration", 1), 1))
    return dict(out)


def teacher_clashes(data_store):
    """[(teacher, day, period, [subject/class, ...]), ...] — teacher in two places."""
    slots = defaultdict(list)
    for p in data_store.get("grid_placements", []) or []:
        if not isinstance(p, dict):
            continue
        teacher = _norm(p.get("teacher_name") or p.get("teacher"))
        if not teacher:
            continue
        day = _int(p.get("day", p.get("col", 0)))
        start = _int(p.get("period", p.get("row", 0)))
        for off in range(max(1, _int(p.get("duration", 1), 1))):
            slots[(teacher, day, start + off)].append(p)

    out = []
    for (teacher, day, period), items in sorted(slots.items()):
        classes = {_norm(i.get("class_name") or i.get("class")) for i in items}
        blocks = {i.get("block_id") or id(i) for i in items}
        if len(items) > 1 and len(blocks) > 1 and len(classes) > 1:
            out.append((teacher, day, period, sorted(classes)))
    return out


def unknown_teachers(data_store):
    """Teachers that appear on the grid but were never assigned that lesson."""
    allowed = set()
    for a in data_store.get("atamalar", []) or []:
        if isinstance(a, dict):
            allowed.add((_norm(a.get("class") or a.get("sinif")),
                         _norm(a.get("subject") or a.get("ders")),
                         _norm(a.get("teacher") or a.get("ogretmen"))))
    bad = []
    for p in data_store.get("grid_placements", []) or []:
        if not isinstance(p, dict):
            continue
        key = (_norm(p.get("class_name") or p.get("class")),
               _norm(p.get("subject_name") or p.get("subject")),
               _norm(p.get("teacher_name") or p.get("teacher")))
        if key[2] and key not in allowed:
            bad.append(key)
    return bad


def gaps_per_teacher(data_store):
    """{teacher: free periods sandwiched between two taught periods}."""
    days, _periods = _dims(data_store)
    busy = defaultdict(lambda: defaultdict(set))
    for p in data_store.get("grid_placements", []) or []:
        if not isinstance(p, dict):
            continue
        teacher = _norm(p.get("teacher_name") or p.get("teacher"))
        if not teacher:
            continue
        day = _int(p.get("day", p.get("col", 0)))
        start = _int(p.get("period", p.get("row", 0)))
        for off in range(max(1, _int(p.get("duration", 1), 1))):
            busy[teacher][day].add(start + off)

    out = {}
    for teacher, by_day in busy.items():
        total = 0
        for day in range(len(days)):
            hours = sorted(by_day.get(day, ()))
            if len(hours) > 1:
                total += (hours[-1] - hours[0] + 1) - len(hours)
        if total:
            out[teacher] = total
    return out


def analyse(data_store):
    """The full advisor report, most severe first."""
    findings = []
    days, periods = _dims(data_store)

    open_slots = open_slots_per_class(data_store)
    demand_c = demand_per_class(data_store)
    placed = placed_per_class(data_store)
    demand_t = demand_per_teacher(data_store)
    capacity = teacher_capacity(data_store)

    if not data_store.get("atamalar"):
        findings.append((
            "error", "Hiç ders ataması yok",
            "Toplu Atama Listesi boş; planlayacak bir şey yok.",
            "Tanımlama İşlemleri → Toplu Atama Listesi'nden dersleri girin."))
        return findings

    # 0. Sınıf tarafı ile öğretmen tarafı birbirini tutuyor mu?
    #
    # Kullanıcının "sınıflarda 182 saat görünüyor ama öğretmenleri topladığımda
    # başka bir sayı çıkıyor" dediği yer burası. Bir atama satırı hem duration hem
    # eski ders_sayisi alanını taşıyabildiği ve ekranlar farklı alanı okuduğu için
    # iki taraf ayrışabiliyordu; artık hepsi lesson_hours'tan okuyor, bu kontrol de
    # geriye kalan gerçek tutarsızlıkları (tanınmayan öğretmen/sınıf adı) bildiriyor.
    audit = lesson_hours.audit(data_store)
    if audit["stale_rows"]:
        sample = "\n".join(
            f"  • {cls} — {subj} ({tch}): {vals}"
            for cls, subj, tch, vals in audit["stale_rows"][:8])
        findings.append((
            "error",
            f"{len(audit['stale_rows'])} atamada saat alanları çelişiyor",
            f"Aynı ders için farklı saat değerleri kayıtlı; ekranlar farklı alanı "
            f"okuduğunda farklı toplam çıkar:\n\n{sample}",
            "Bu dersleri sınıf ekranından bir kez kaydedin; kayıt sırasında bütün "
            "alanlar tek değere eşitlenir."))
    if audit["unknown_teachers"]:
        sample = "\n".join(f"  • {cls} — {subj}: {tch} ({hrs} saat)"
                           for cls, subj, tch, hrs in audit["unknown_teachers"][:8])
        hours_lost = sum(h for *_x, h in audit["unknown_teachers"])
        findings.append((
            "error",
            f"{len(audit['unknown_teachers'])} atama, öğretmen listesinde olmayan "
            f"bir isme yazılmış — {hours_lost} saat",
            f"Bu saatler sınıf ekranında görünür ama öğretmen ekranlarında hiçbir "
            f"öğretmenin üzerinde çıkmaz; iki tarafın toplamı bu yüzden farklıdır:"
            f"\n\n{sample}",
            "Öğretmen adını Öğretmenler ekranındaki yazımıyla düzeltin veya "
            "öğretmeni tanımlayın."))
    if audit["unknown_classes"]:
        sample = "\n".join(f"  • {cls} — {subj} ({tch}): {hrs} saat"
                           for cls, subj, tch, hrs in audit["unknown_classes"][:8])
        findings.append((
            "error",
            f"{len(audit['unknown_classes'])} atama, sınıf listesinde olmayan bir "
            f"sınıfa yazılmış",
            f"Bu dersler hiçbir sınıfın çizelgesine düşmez:\n\n{sample}",
            "Sınıf adını Sınıflar ekranındaki yazımıyla düzeltin."))

    # 1. A class asked to hold more hours than it has open periods can never fill.
    for cls, need in sorted(demand_c.items()):
        have = open_slots.get(cls)
        if have is None:
            continue
        if need > have:
            findings.append((
                "error", f"{cls}: {need} saat ders, {have} açık saat",
                f"Sınıfa haftada {need} saat ders atanmış ama Zaman Tablosu'nda yalnızca "
                f"{have} saat açık. {need - have} saat hiçbir şekilde yerleşemez.",
                f"Ya {cls} için kapalı saatleri açın ya da {need - have} saat dersi azaltın."))

    # 2. The one that actually explains this school's 133/180: teachers who are
    #    assigned more hours than the classes' open periods can ever give them.
    over = []
    for teacher, need in sorted(demand_t.items()):
        have = capacity.get(teacher)
        if have is not None and need > have:
            over.append((teacher, need, have))
    if over:
        total_excess = sum(n - h for _t, n, h in over)
        lines = "\n".join(f"  • {t}: {n} saat atanmış, en fazla {h} saat mümkün (+{n - h})"
                          for t, n, h in sorted(over, key=lambda x: x[2] - x[1])[:12])
        findings.append((
            "error",
            f"{len(over)} öğretmen fizik olarak yetişemiyor — {total_excess} saat boşta kalacak",
            f"Bir öğretmen aynı anda tek sınıfta olabilir. Sınıflarının açık olduğu "
            f"saat sayısı bu öğretmenlerin ders yüküne yetmiyor:\n\n{lines}\n\n"
            f"Bu {total_excess} saat, planlayıcı ne yaparsa yapsın yerleşemez; "
            f"çizelgenin dolabileceği üst sınır bu kadar azalır.",
            "Bu öğretmenlerin bazı derslerini başka bir öğretmene devredin veya "
            "sınıfların kapalı saatlerini açın."))

    # 3. Under-filled classes, only when the cause is not already reported above.
    for cls, have in sorted(open_slots.items()):
        got = placed.get(cls, 0)
        need = demand_c.get(cls, 0)
        if got < min(have, need):
            findings.append((
                "warning", f"{cls}: {got}/{min(have, need)} saat yerleşti",
                f"{min(have, need) - got} saat açıkta. Sınıfın {have} açık saati, "
                f"{need} saat dersi var.",
                "Yerleşmeyen dersler alttaki listede; oradan elle sürükleyebilir "
                "veya öğretmen devrederek çözebilirsiniz."))

    # 4. Hard errors on the grid itself.
    clashes = teacher_clashes(data_store)
    if clashes:
        sample = "\n".join(
            f"  • {t} — {days[d] if d < len(days) else d + 1}. gün {p + 1}. saat: "
            f"{', '.join(cs)}" for t, d, p, cs in clashes[:10])
        findings.append((
            "error", f"{len(clashes)} öğretmen çakışması",
            f"Aynı öğretmen aynı saatte birden fazla sınıfta görünüyor:\n\n{sample}",
            "Çakışan derslerden birini başka bir saate taşıyın."))

    unknown = unknown_teachers(data_store)
    if unknown:
        sample = "\n".join(f"  • {c} — {s}: {t}" for c, s, t in unknown[:10])
        findings.append((
            "error", f"{len(unknown)} derste atanmamış öğretmen",
            f"Gridde, atama listesinde olmayan öğretmen–ders eşleşmeleri var:\n\n{sample}",
            "Planlama / Yerleştirme → Tabloyu Temizle sonrası yeniden plan oluşturun, "
            "veya bu dersleri sağ tıkla düzeltin."))

    # 5. Soft quality signals.
    gaps = gaps_per_teacher(data_store)
    if gaps:
        worst = sorted(gaps.items(), key=lambda kv: -kv[1])[:8]
        total = sum(gaps.values())
        findings.append((
            "warning", f"Öğretmen boşlukları: toplam {total} saat",
            "Gün içinde iki dersin arasında kalan boş saatler:\n\n" + "\n".join(
                f"  • {t}: {n} boş saat" for t, n in worst),
            "İyileştirme Uygula ile boşluklar azaltılmaya çalışılır."))

    loose = data_store.get("loose_unplaced_cards") or []
    if loose:
        findings.append((
            "info", f"{len(loose)} ders alt listede bekliyor",
            "Bu dersler yerleştirilemedi ve silinmedi; alttaki listede duruyorlar.",
            "Karta çift tıklayıp neden yerleşemediğini görebilir, sürükleyerek elle "
            "yerleştirebilirsiniz."))

    if not findings:
        total_open = sum(open_slots.values())
        total_placed = sum(placed.values())
        findings.append((
            "info", "Sorun bulunamadı",
            f"{total_placed}/{total_open} saat dolu, çakışma yok, "
            f"atanmamış öğretmen yok.", ""))

    order = {"error": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: order.get(f[0], 3))
    return findings
