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

from .model import World, Card, norm_key, norm_class
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

    # Ders AİLESİ: varsayılan olarak her ders kendi ailesidir (aile indeksi =
    # ders indeksi). "Seçilen dersler aynı ders sayılsın" kuralı derlendikten
    # sonra apply_subject_groups() aileleri birleştirir.
    subject_family_ix = list(range(len(subject_names)))
    for c in cards:
        c.family = c.subject if c.subject >= 0 else -1

    world = World(D=D, P=P, classes=class_names, teachers=teacher_names,
                  subjects=subject_names, cards=cards,
                  class_closed=class_closed, teacher_closed=teacher_closed,
                  class_avoid=class_avoid, teacher_avoid=teacher_avoid,
                  class_capacity=[], class_demand=[],
                  families=list(subject_names), subject_family=subject_family_ix)

    full = (1 << (D * P)) - 1
    world.class_capacity = [bin(full & ~m).count("1") for m in class_closed]
    demand = [0] * nC
    for c in cards:
        for ci in c.classes:
            demand[ci] += c.duration
    world.class_demand = demand
    return world


def apply_subject_groups(world, rule_list):
    """"Seçilen dersler aynı ders sayılsın" kurallarını dünyaya işler.

    Üç şey yapar ve üçü de gereklidir:

      1. Aileleri birleştirir. Kesişen gruplar tek aile olur (Mat1+Mat2 ve
         Mat2+Mat 11 -> {Mat1, Mat2, Mat 11}). world.families görünen adı,
         world.subject_family[ders] aile indeksini, card.family kartın
         ailesini taşır.

      2. Kural kapsamlarını aileye genişletir. Kullanıcı "Aynı ders aynı gün
         tekrar etmesin" kuralında yalnızca Türkçe'yi seçtiyse ve Türkçe ile
         Edebiyat aynı dersse, Edebiyat kartları da kuralın kapsamındadır —
         aksi hâlde "aynı ders" tanımı ekranda bir şey, motorda başka bir şey
         anlamına gelir.

      3. Grubun kendisi kural listesinde kalır (raporda görünsün diye) ama
         hiçbir yerleştirme kararında okunmaz.

    Ders adı kartlarda geçip dersler listesinde olmayan adlar build_world
    tarafından zaten dizine alınmıştır; burada bilinmeyen ad kalmaz.
    """
    groups = [r for r in rule_list if r.kind == R.X_SUBJECT_GROUP]
    n = len(world.subjects)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for r in groups:
        members = sorted(r.subjects)
        for s in members[1:]:
            a, b = find(members[0]), find(s)
            if a != b:
                parent[max(a, b)] = min(a, b)

    root_ix, fam_names, members_of = {}, [], {}
    subject_family = [0] * n
    for s in range(n):
        root = find(s)
        if root not in root_ix:
            root_ix[root] = len(fam_names)
            fam_names.append(None)
            members_of[root] = []
        subject_family[s] = root_ix[root]
        members_of[root].append(s)
    for root, fi in root_ix.items():
        fam_names[fi] = " / ".join(world.subjects[s] for s in members_of[root])

    world.families = fam_names
    world.subject_family = subject_family
    for c in world.cards:
        c.family = subject_family[c.subject] if c.subject >= 0 else -1

    # Kural kapsamını aileye genişlet.
    if groups:
        by_family = {}
        for s in range(n):
            by_family.setdefault(subject_family[s], set()).add(s)
        for r in rule_list:
            if r.kind == R.X_SUBJECT_GROUP or not r.subjects:
                continue
            wide = set()
            for s in r.subjects:
                wide |= by_family.get(subject_family[s], {s})
            r.subjects = frozenset(wide)
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
                # Kilitli kart: kullanıcının açık kararı kısıtları geçersiz kılar.
                if card.locked_at is not None and world.idx(d, p) == card.locked_at:
                    if fp == 0:
                        continue
                    allowed.append((world.idx(d, p), fp))
                    continue
                if fp == 0 or (fp & base_block):
                    continue
                if window_ok(world, windows, card, p, card.duration):
                    allowed.append((world.idx(d, p), fp))
        card.slots = tuple(allowed)
    return world


def noon_of(P):
    """Öğle sınırı: bu saatten önce başlayıp bitenler "öğleden önce"dir."""
    return 4 if P >= 6 else (P + 1) // 2


def window_breaks(rule, p, dur, P):
    """Pencere kuralı bu başlangıç/süre için bozuluyor mu?"""
    noon = noon_of(P)
    k = rule.kind
    if k == R.X_MORNING_ONLY:
        return p + dur > noon
    if k == R.X_AFTERNOON_ONLY:
        return p < noon
    if k == R.X_NOT_LAST_PERIOD:
        return p + dur > P - 1
    if k == R.X_NOT_FIRST_PERIOD:
        return p == 0
    if k == R.X_TIME_WINDOW:
        return p < rule.param or (p + dur - 1) > rule.param2
    return False


def window_ok(world, windows, card, p, dur):
    """Karta uygulanan bütün (sert) pencere kuralları bu yerleşime izin veriyor mu?

    Hem 2 saatlik bütün blok hem de bölünmüş 1 saatlik parça için aynı işlev
    kullanılır; CP-SAT'in parçaları da bu süzgeçten geçer. Eskiden parçalar
    yalnızca kapalı hücreye bakıyordu ve "öğleden önce" kuralı açık bir dersin
    parçası öğleden sonraya düşebiliyordu.
    """
    for r in windows:
        if r.applies_card(card) and window_breaks(r, p, dur, world.P):
            return False
    return True
