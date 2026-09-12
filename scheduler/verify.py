"""Independent validation of returned card placements, rebuilt from zero.

This module does not use native conflict tables, search counters, or Occupancy.
"""
from collections import defaultdict
from . import rules as R


def validate(world, rules, positions, bend_rules=False):
    """Çizelgeyi sıfırdan denetler.

    bend_rules=True iken SERT planlama ilişkisi ihlalleri hata sayılmaz, ayrı
    bir listeye ('bent') yazılır. Bu yalnızca tamamlanma öncelikli ikinci
    aşamada kullanılır: orada kuralın bilerek ve en az sayıda delindiği
    bilinir, delinen yerin gizlenmesi değil RAPORLANMASI istenir.

    Fiziksel kısıtlar bu bayraktan etkilenmez. Öğretmen çakışması, sınıf
    çakışması, kapalı saat ve kilit ihlali her koşulda hatadır; öyle bir
    çizelge okulda uygulanamaz.
    """
    errors, soft, bent = [], [], []
    if len(positions) != len(world.cards):
        return ['Motorun döndürdüğü kart sayısı atamalarla eşleşmiyor'], []
    class_cells, teacher_cells = {}, {}
    rows=[]
    for c,idx in zip(world.cards, positions):
        label=f"{' + '.join(c.class_names)} · {c.subject_name}"
        if idx < 0:
            if c.locked_at is not None: errors.append(f"Kilitli kart yerleşmedi: {label}")
            continue
        d,p=divmod(idx,world.P)
        if not 0<=d<world.D or p+c.duration>world.P:
            errors.append(f"Gün/saat sınırı aşıldı: {label}");continue
        if c.locked_at is not None and idx!=c.locked_at:
            errors.append(f"Kilit değişti: {label}")
        for off in range(c.duration):
            cell=idx+off
            for ci in c.classes:
                if (ci,cell) in class_cells: errors.append(f"Sınıf çakışması: {world.classes[ci]}, gün {d+1}, saat {p+off+1}")
                class_cells[ci,cell]=c.cid
                if world.class_closed[ci]>>cell&1: errors.append(f"Kapalı sınıf saati: {label}")
            if c.teacher>=0:
                if (c.teacher,cell) in teacher_cells: errors.append(f"Öğretmen çakışması: {c.teacher_name}, gün {d+1}, saat {p+off+1}")
                teacher_cells[c.teacher,cell]=c.cid
                if world.teacher_closed[c.teacher]>>cell&1: errors.append(f"Kapalı öğretmen saati: {c.teacher_name}")
        rows.append((c,d,p))
    for r in rules:
        selected=[x for x in rows if r.applies_card(x[0])]
        def hit(detail):
            msg = f"{r.label}: {detail}"
            if not r.is_hard(): soft.append(msg)
            elif bend_rules: bent.append(msg)
            else: errors.append(msg)
        by_class=defaultdict(list);by_teacher=defaultdict(list)
        for c,d,p in selected:
            for ci in c.classes:
                if r.applies_class(ci): by_class[ci].append((c,d,p))
            if c.teacher>=0: by_teacher[c.teacher].append((c,d,p))
        if r.kind in R.WINDOW_RULES:
            noon=4 if world.P>=6 else (world.P+1)//2
            for c,d,p in selected:
                if ((r.kind==R.X_MORNING_ONLY and p+c.duration>noon)
                    or (r.kind==R.X_AFTERNOON_ONLY and p<noon)
                    or (r.kind==R.X_NOT_FIRST_PERIOD and p==0)
                    or (r.kind==R.X_NOT_LAST_PERIOD and p+c.duration>world.P-1)
                    or (r.kind==R.X_TIME_WINDOW and (p<r.param or p+c.duration-1>r.param2))):
                    hit(f"{c.subject_name}, gün {d+1}, saat {p+1}")
        elif r.kind in (R.X_SUBJECT_ONCE_DAY,R.X_TEACHER_ONCE_DAY,R.X_PAIR_NOT_SAME_DAY,
                         R.X_HARD_NOT_ADJACENT,R.X_MIN_DAYS_BETWEEN):
            for ci,lst in by_class.items():
                for i,(a,ad,ap) in enumerate(lst):
                    for b,bd,bp in lst[:i]:
                        same_day=ad==bd
                        bad=((r.kind==R.X_SUBJECT_ONCE_DAY and same_day and a.subject==b.subject)
                            or (r.kind==R.X_TEACHER_ONCE_DAY and same_day and a.teacher>=0 and a.teacher==b.teacher)
                            or (r.kind==R.X_PAIR_NOT_SAME_DAY and same_day and a.subject!=b.subject)
                            or (r.kind==R.X_HARD_NOT_ADJACENT and same_day and a.subject!=b.subject
                                and (ap+a.duration==bp or bp+b.duration==ap))
                            or (r.kind==R.X_MIN_DAYS_BETWEEN and a.subject==b.subject and abs(ad-bd)<max(1,r.param)))
                        if bad: hit(f"{world.classes[ci]}, gün {ad+1}: {a.subject_name} / {b.subject_name}")
        elif r.kind in (R.X_SUBJECT_MAX_HOURS,R.X_PRACTICAL_MAX_HOURS,R.X_SUBJECT_MAX_SESSIONS,R.X_EVEN_SPREAD):
            for ci,lst in by_class.items():
                counts=defaultdict(lambda:[0]*world.D)
                for c,d,p in lst: counts[c.subject][d]+=1 if r.kind in (R.X_SUBJECT_MAX_SESSIONS,R.X_EVEN_SPREAD) else c.duration
                for subject,values in counts.items():
                    limit=r.param
                    if r.kind==R.X_EVEN_SPREAD:
                        if max(values)-min(values)>1: hit(f"{world.classes[ci]}, {world.subjects[subject]}: {values}")
                    elif any(v>limit for v in values): hit(f"{world.classes[ci]}, {world.subjects[subject]}: {values}")
        elif r.kind in (R.X_CLASS_MAX_HOURS,R.X_TEACHER_MAX_HOURS,R.X_TEACHER_MAX_DAYS):
            groups=by_class if r.kind==R.X_CLASS_MAX_HOURS else by_teacher
            for key,lst in groups.items():
                counts=[0]*world.D
                for c,d,p in lst: counts[d]+=c.duration
                if r.kind==R.X_TEACHER_MAX_DAYS:
                    if sum(v>0 for v in counts)>r.param: hit(f"Öğretmenin gün sayısı {r.param} sınırını aşıyor")
                elif any(v>r.param for v in counts): hit(f"Günlük saat sınırı {r.param} aşıldı: {counts}")
        elif r.kind in (R.X_SAME_DAY_ADJACENT,R.X_NO_CLASS_GAP,R.X_NO_TEACHER_GAP,R.X_TEACHER_MAX_RUN):
            groups=by_teacher if r.kind in (R.X_NO_TEACHER_GAP,R.X_TEACHER_MAX_RUN) else by_class
            for key,lst in groups.items():
                days=defaultdict(set)
                for c,d,p in lst: days[d].update(range(p,p+c.duration))
                for d,periods in days.items():
                    if not periods: continue
                    if r.kind==R.X_TEACHER_MAX_RUN:
                        run=0
                        for p in range(world.P):
                            run=run+1 if p in periods else 0
                            if run>r.param: hit(f"Gün {d+1}: ardışık saat sınırı aşıldı");break
                    elif len(periods)!=max(periods)-min(periods)+1: hit(f"Gün {d+1}: dersler arasında boşluk var")
        elif r.kind in (R.Y_SUBJECT_MAX_PARALLEL,R.Y_TEACHER_MAX_PARALLEL):
            counts=defaultdict(int)
            for c,d,p in selected:
                key=c.subject if r.kind==R.Y_SUBJECT_MAX_PARALLEL else c.teacher
                for off in range(c.duration): counts[key,d,p+off]+=len(c.classes)
            if any(v>r.param for v in counts.values()): hit('Eşzamanlı sınıf sınırı aşıldı')
    return errors,soft,bent
