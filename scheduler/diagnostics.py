"""Necessary feasibility checks with explicit, reproducible witnesses."""
from collections import defaultdict
from . import rules as R


def diagnose(world, rules):
    issues = []
    deficits = []
    seen = set()
    for r in rules:
        if not r.is_hard() or r.kind not in (R.X_SUBJECT_ONCE_DAY, R.X_TEACHER_ONCE_DAY):
            continue
        groups = defaultdict(list)
        for c in world.cards:
            if not r.applies_card(c): continue
            resource = c.subject if r.kind == R.X_SUBJECT_ONCE_DAY else c.teacher
            if resource < 0: continue
            for ci in c.classes:
                if r.applies_class(ci): groups[ci, resource].append(c)
        for (ci, resource), cards in groups.items():
            # Maximum-weight matching between whole cards and allowed days.
            # Each successful augmentation retains all previously matched cards.
            owner = {}
            allowed = {c.cid: sorted({s//world.P for s,_ in c.slots}) for c in cards}
            def augment(cid, visited):
                for day in allowed[cid]:
                    if day in visited: continue
                    visited.add(day)
                    if day not in owner or augment(owner[day], visited):
                        owner[day] = cid
                        return True
                return False
            matched = []
            for c in sorted(cards, key=lambda x: -x.duration*len(x.classes)):
                if augment(c.cid, set()): matched.append(c)
            missing = sum(c.duration*len(c.classes) for c in cards)-sum(c.duration*len(c.classes) for c in matched)
            ids = frozenset(c.cid for c in cards)
            if missing <= 0 or ids in seen: continue
            seen.add(ids)
            days = sorted(set().union(*(set(x) for x in allowed.values())))
            name = world.subjects[resource] if r.kind == R.X_SUBJECT_ONCE_DAY else world.teachers[resource]
            message = (f"{world.classes[ci]} · {name}: {len(cards)} ayrı kart "
                       f"({'+'.join(str(c.duration) for c in cards)}) için "
                       f"{len(days)} uygun gün var. ‘{r.label}’ kuralıyla "
                       f"en az {missing} sınıf-saati yerleşemez.")
            issues.append(dict(kind='day_capacity', rule=r.label, message=message,
                               **{'class': world.classes[ci]}, resource=name,
                               cards=sorted(ids), available_days=days,
                               min_unplaced_hours=missing,
                               suggested_unplaced=sorted(ids-set(owner.values()))))
            deficits.append((missing, ids))
    for ci, (demand, capacity) in enumerate(zip(world.class_demand,world.class_capacity)):
        if demand > capacity:
            ids=frozenset(c.cid for c in world.cards if ci in c.classes)
            missing=demand-capacity
            issues.append(dict(kind='class_capacity', message=f"{world.classes[ci]}: {demand} saat ders, {capacity} açık saat.",
                               min_unplaced_hours=missing,cards=sorted(ids)))
            deficits.append((missing,ids))
    for ti, name in enumerate(world.teachers):
        cards=[c for c in world.cards if c.teacher==ti]
        needed=sum(c.duration for c in cards)
        available=0
        for c in cards:
            for _,mask in c.slots: available |= mask
        capacity=bin(available).count('1')
        if needed>capacity:
            ids=frozenset(c.cid for c in cards)
            missing=needed-capacity
            issues.append(dict(kind='teacher_capacity',message=f"{name}: {needed} saat ders, sınıflarıyla ortak {capacity} uygun saat.",
                               teacher=name,assigned=needed,available=capacity,
                               min_unplaced_hours=missing,cards=sorted(ids)))
            deficits.append((missing,ids))
    for c in world.cards:
        if not c.slots:
            missing=c.duration*len(c.classes)
            issues.append(dict(kind='no_slot',message=f"{' + '.join(c.class_names)} · {c.subject_name}: {c.duration} saatlik kart için uygun başlangıç yok.",
                               min_unplaced_hours=missing,cards=[c.cid]))
            deficits.append((missing,frozenset([c.cid])))
    # Sum only disjoint witnesses, so the same missing hour is never counted twice.
    used=set();missing_bound=0
    for missing,ids in sorted(deficits,key=lambda x:(-x[0],len(x[1]))):
        if not used.intersection(ids):
            used.update(ids);missing_bound+=missing
    return issues, max(0,world.total_hours()-missing_bound)
