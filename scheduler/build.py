"""
scheduler/build.py — data_store -> World.

Ham veriyi TEK SEFERDE normalize eder. Motorun geri kalanı data_store'u hiç
görmez; bütün yazım farkları, eş anlamlı alan adları ve tarihsel biçimler
burada biter.

Kart üretimi, kullanıcının dağılım alanına yazdığı şeyi harfiyen uygular:

    "2+2"   -> 2 saatlik BİTİŞİK kart + 2 saatlik BİTİŞİK kart
    "2+1"   -> 2 saatlik kart + 1 saatlik kart
    "2+2+1" -> 2 + 2 + 1
    "4"     -> dağılım yazılmamış: 2+2 olarak bölünür
    "3+2"   -> 3 saatlik BİTİŞİK kart + 2 saatlik BİTİŞİK kart

Eski motor 3 ve üzeri parçayı o kadar bağımsız 1 saate parçalıyordu; "3 saatlik
blok" yazan kullanıcı haftaya dağılmış üç ayrı saat alıyordu. Burada 3 saatlik
parça 3 saatlik tek karttır ve bitişik oturur.
"""

import constraint_sync
import lesson_hours

from .model import World, Card, norm_key, norm_class, subject_family
from . import rules as R


def _states(matrix, D, P):
    """timeoff matrisi -> (kapalı maske, kaçın maske).  0=KAPALI 1=KAÇIN 2=AÇIK"""
    closed = 0
    avoid = 0
    if not isinstance(matrix, list):
        return 0, 0
    for d in range(min(D, len(matrix))):
        row = matrix[d]
        if not isinstance(row, list):
            continue
        for p in range(min(P, len(row))):
            try:
                v = int(row[p])
            except (TypeError, ValueError):
                v = 2
            bit = 1 << (d * P + p)
            if v == 0:
                closed |= bit
            elif v == 1:
                avoid |= bit
    return closed, avoid


def parse_distribution(type_str, total):
    """Dağılım metnini kart uzunluklarına çevirir."""
    t = str(type_str or "").strip()
    parts = []
    if "+" in t:
        for piece in t.split("+"):
            piece = piece.strip()
            if piece.isdigit() and int(piece) > 0:
                parts.append(int(piece))
    elif t.isdigit() and int(t) > 0:
        rem = int(t)
        while rem > 0:
            b = min(2, rem)
            parts.append(b)
            rem -= b
    if not parts and total > 0:
        rem = int(total)
        while rem > 0:
            b = min(2, rem)
            parts.append(b)
            rem -= b
    return parts or ([int(total)] if total else [])


def _split_classes(raw):
    out = []
    for sep in ("&", ",", "/"):
        raw = raw.replace(sep, "+")
    for piece in raw.split("+"):
        piece = piece.strip()
        if piece:
            out.append(piece)
    return out


def build_world(data_store, D=None, P=None, cross_busy=None,
                locked=None, only_classes=None):
    """data_store'dan donmuş World üretir."""
    settings = data_store.get("settings") or {}
    default_D, default_P = constraint_sync.grid_dimensions(data_store)
    if D is None:
        D = default_D
    if P is None:
        P = default_P
    if D <= 0 or P <= 0:
        raise ValueError("Gün ve saat sayısı pozitif olmalı")

    class_names, teacher_names = [], []
    class_ix, teacher_ix, subject_ix = {}, {}, {}
    subject_names = []

    for c in data_store.get("siniflar") or []:
        n = (c.get("ad") or c.get("name") or "").strip()
        if n and norm_class(n) not in class_ix:
            class_ix[norm_class(n)] = len(class_names)
            class_names.append(n)
    for t in data_store.get("ogretmenler") or []:
        n = (t.get("ad") or t.get("name") or "").strip()
        if n and norm_key(n) not in teacher_ix:
            teacher_ix[norm_key(n)] = len(teacher_names)
            teacher_names.append(n)
    for s in data_store.get("dersler") or []:
        n = (s.get("ad") or s.get("name") or "").strip()
        if n and norm_key(n) not in subject_ix:
            subject_ix[norm_key(n)] = len(subject_names)
            subject_names.append(n)

    # Atamalarda geçip listede olmayan adları da tanı.
    for a in data_store.get("atamalar") or []:
        s = lesson_hours.subject(a)
        if s and norm_key(s) not in subject_ix:
            subject_ix[norm_key(s)] = len(subject_names)
            subject_names.append(s)
        t = lesson_hours.teacher(a)
        if t and t not in ("—", "Atanmadı") and norm_key(t) not in teacher_ix:
            teacher_ix[norm_key(t)] = len(teacher_names)
            teacher_names.append(t)

    nC, nT = len(class_names), len(teacher_names)
    class_closed = [0] * nC
    class_avoid = [0] * nC
    teacher_closed = [0] * nT
    teacher_avoid = [0] * nT

    for c in data_store.get("siniflar") or []:
        n = (c.get("ad") or c.get("name") or "").strip()
        i = class_ix.get(norm_class(n))
        if i is None:
            continue
        cl, av = _states(constraint_sync.get_matrix(c, n, data_store), D, P)
        class_closed[i] |= cl
        class_avoid[i] |= av
    for t in data_store.get("ogretmenler") or []:
        n = (t.get("ad") or t.get("name") or "").strip()
        i = teacher_ix.get(norm_key(n))
        if i is None:
            continue
        cl, av = _states(constraint_sync.get_matrix(t, n, data_store), D, P)
        teacher_closed[i] |= cl
        teacher_avoid[i] |= av

    # Çapraz kurum: başka şubede ders veren öğretmenin saati KAPALIDIR.
    for name, slots in (cross_busy or {}).items():
        i = teacher_ix.get(norm_key(name))
        if i is None:
            continue
        for (d, p) in slots:
            if 0 <= d < D and 0 <= p < P:
                teacher_closed[i] |= 1 << (d * P + p)

    want = None
    if only_classes:
        want = {norm_class(x) for x in only_classes}

    cards = []
    for ai, a in enumerate(data_store.get("atamalar") or []):
        raw_c = (a.get("class") or a.get("sinif") or a.get("class_name") or "").strip()
        if not raw_c:
            continue
        parts_c = [raw_c] if norm_class(raw_c) in class_ix else _split_classes(raw_c)
        extra = a.get("combined_classes") or []
        for e in extra:
            if e and e.strip() not in parts_c:
                parts_c.append(e.strip())
        idxs = []
        for pc in parts_c:
            i = class_ix.get(norm_class(pc))
            if i is not None and i not in idxs:
                idxs.append(i)
        if not idxs:
            raise ValueError(f"Atamadaki sınıf bulunamadı: {raw_c}")
        if want and not any(norm_class(class_names[i]) in want for i in idxs):
            continue

        s_name = lesson_hours.subject(a)
        t_name = lesson_hours.teacher(a)
        s_idx = subject_ix.get(norm_key(s_name), -1)
        t_idx = teacher_ix.get(norm_key(t_name), -1)
        total = lesson_hours.hours(a)
        durs = parse_distribution(lesson_hours.type_str(a), total)

        for dur in durs:
            cards.append(Card(
                cid=len(cards), classes=tuple(idxs), subject=s_idx,
                teacher=t_idx, duration=int(dur), origin=ai, group=ai,
                subject_name=s_name, teacher_name=t_name,
                class_names=tuple(class_names[i] for i in idxs),
            ))

    # Her karta ders AİLESİ indeksi: "Matematik9" ile "Matematik11" aynı aile.
    fam_ix, fam_names = {}, []
    for c in cards:
        key = subject_family(c.subject_name)
        if key not in fam_ix:
            fam_ix[key] = len(fam_names)
            fam_names.append(key)
        c.family = fam_ix[key]

    world = World(D=D, P=P, classes=class_names, teachers=teacher_names,
                  subjects=subject_names, cards=cards,
                  class_closed=class_closed, teacher_closed=teacher_closed,
                  class_avoid=class_avoid, teacher_avoid=teacher_avoid,
                  class_capacity=[], class_demand=[])

    full = (1 << (D * P)) - 1
    world.class_capacity = [bin(full & ~m).count("1") for m in class_closed]
    demand = [0] * nC
    for c in cards:
        for ci in c.classes:
            demand[ci] += c.duration
    world.class_demand = demand
    return world


def attach_slots(world, rule_list):
    """Her karta aday hücre listesini yazar.

    Pencere kuralları (öğleden önce/sonra, saat aralığı, son saat yasağı) ve
    kapalı hücreler BURADA uygulanır — bir kez, kurulumda. Yerleştirme
    döngüsünde bir daha bakılmaz. Eski motorda bu filtreler her denemede
    yeniden değerlendiriliyordu.
    """
    windows = [r for r in rule_list if r.kind in R.WINDOW_RULES and r.is_hard()]
    D, P = world.D, world.P
    noon = 4 if P >= 6 else (P + 1) // 2

    for card in world.cards:
        allowed = []
        base_block = 0
        for ci in card.classes:
            base_block |= world.class_closed[ci]
        if card.teacher >= 0:
            base_block |= world.teacher_closed[card.teacher]

        for d in range(D):
            for p in range(P - card.duration + 1):
                fp = world.footprint(d, p, card.duration)
                if card.locked_at is not None and world.idx(d, p) != card.locked_at:
                    continue
                if fp == 0 or (fp & base_block):
                    continue
                ok = True
                for r in windows:
                    if not r.applies_card(card):
                        continue
                    if r.kind == R.X_MORNING_ONLY and p + card.duration > noon:
                        ok = False
                    elif r.kind == R.X_AFTERNOON_ONLY and p < noon:
                        ok = False
                    elif r.kind == R.X_NOT_LAST_PERIOD and p + card.duration > P - 1:
                        ok = False
                    elif r.kind == R.X_NOT_FIRST_PERIOD and p == 0:
                        ok = False
                    elif r.kind == R.X_TIME_WINDOW:
                        if p < r.param or (p + card.duration - 1) > r.param2:
                            ok = False
                    if not ok:
                        break
                if ok:
                    allowed.append((world.idx(d, p), fp))
        card.slots = tuple(allowed)
    return world
