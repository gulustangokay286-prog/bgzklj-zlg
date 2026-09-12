"""
scheduler/cpsat.py — CP-SAT arka ucu.

Tabu araması çizelgenin tamamına hızla yaklaşır ama son bir iki kartta takılır:
her adımda tek kart oynattığı için, ancak üç dört kartın birlikte kaymasıyla
ulaşılabilen çözümleri göremez. v188'de 60 saniye ile 180 saniye aynı sonucu
veriyordu — sorun süre değil, hamlenin kendisi.

CP-SAT tam bu boşluğu doldurur: kartların hepsini aynı anda değerlendirir,
"şu kart şuraya giderse şu üçü şöyle kayar" türü çıkarımları kendisi yapar.
Sıkı yerleşim problemleri (her sınıfın açık hücresi gereken saate tam eşit)
onun güçlü olduğu yerdir.

Eski motorda da CP-SAT vardı ve kaldırılmıştı; sebebi tekniğin kendisi değil,
kurulumun bozuk olmasıydı — planlama ilişkileri modele hiç girmiyordu (hepsi
yalnızca hiç çalışmayan ikinci fazın ceza listesine yazılıyordu). Burada
kurallar doğrudan sert kısıt olarak yazılır.

Model:
    x[i][s]  kart i, s numaralı aday yerine konuldu mu

    her kart            sum(x[i]) <= 1        (yerleşti ya da yerleşmedi)
    sınıf hücresi       o hücreyi kaplayan bütün x'lerin toplamı <= 1
    öğretmen hücresi    aynısı
    aynı ders/gün       (sınıf, gün, ders ailesi) başına <= 1
    aynı öğretmen/gün   (sınıf, gün, öğretmen) başına <= 1
    zor ders bitişik    komşu hücre çiftlerinde ikisi birden olamaz

    amaç                yerleşen SAAT sayısını en büyüklemek
"""

import time
from collections import defaultdict
from . import rules as R


def solve_cpsat(world, rule_list, seconds=60.0, seed=0, workers=8,
                warm_start=None, log=False):
    """World + kurallar -> (positions, placed_hours, status).

    positions[i] = kart i'nin ızgara indeksi, yerleşmediyse -1.
    """
    from ortools.sat.python import cp_model

    w = world
    P = w.P
    model = cp_model.CpModel()

    subject_once = any(r.kind == R.X_SUBJECT_ONCE_DAY and r.is_hard() for r in rule_list)
    teacher_once = any(r.kind == R.X_TEACHER_ONCE_DAY and r.is_hard() for r in rule_list)
    hard_adj = set()
    for r in rule_list:
        if r.kind == R.X_HARD_NOT_ADJACENT and r.is_hard():
            hard_adj |= set(r.subjects)

    xs = []                      # xs[i] = [(slot_idx, var), ...]
    cls_cell = defaultdict(list)
    tch_cell = defaultdict(list)
    fam_day = defaultdict(list)
    tch_day = defaultdict(list)

    for i, c in enumerate(w.cards):
        row = []
        for idx, _ in c.slots:
            v = model.NewBoolVar(f"x{i}_{idx}")
            row.append((idx, v))
            d = idx // P
            for off in range(c.duration):
                cell = idx + off
                for ci in c.classes:
                    cls_cell[(ci, cell)].append(v)
                if c.teacher >= 0:
                    tch_cell[(c.teacher, cell)].append(v)
            for ci in c.classes:
                if subject_once:
                    fam_day[(ci, d, c.family)].append(v)
                if teacher_once and c.teacher >= 0:
                    tch_day[(ci, d, c.teacher)].append(v)
        xs.append(row)
        if row:
            if c.locked_at is not None:
                for idx, v in row:
                    model.Add(v == (1 if idx == c.locked_at else 0))
            else:
                model.AddAtMostOne(v for _, v in row)

    # Y ekseni — çakışma. Pazarlık yok.
    for vs in cls_cell.values():
        if len(vs) > 1: model.AddAtMostOne(vs)
    for vs in tch_cell.values():
        if len(vs) > 1: model.AddAtMostOne(vs)

    # X ekseni — gün kuralları.
    for vs in fam_day.values():
        if len(vs) > 1: model.AddAtMostOne(vs)
    for vs in tch_day.values():
        if len(vs) > 1: model.AddAtMostOne(vs)

    # Zor ders bitişikliği: aynı sınıfta, aynı gün, uç uca gelen iki zor ders.
    if hard_adj:
        ends = defaultdict(list)     # (sınıf, gün, saat) -> burada BİTEN zor ders
        starts = defaultdict(list)   # (sınıf, gün, saat) -> burada BAŞLAYAN zor ders
        for i, c in enumerate(w.cards):
            if c.subject not in hard_adj:
                continue
            for idx, v in xs[i]:
                d, p = divmod(idx, P)
                for ci in c.classes:
                    starts[(ci, d, p)].append(v)
                    ends[(ci, d, p + c.duration - 1)].append(v)
        for (ci, d, p), evs in ends.items():
            svs = starts.get((ci, d, p + 1))
            if not svs:
                continue
            for a in evs:
                for b in svs:
                    if a is not b:
                        model.AddAtMostOne([a, b])

    # Amaç: yerleşen saat sayısı en büyük olsun.
    terms = []
    for i, c in enumerate(w.cards):
        agirlik = c.duration * len(c.classes)
        for _, v in xs[i]:
            terms.append(agirlik * v)
    model.Maximize(sum(terms))

    # Sıcak başlangıç: tabu sonucunu ipucu olarak ver. CP-SAT iyi bir başlangıcı
    # doğrulayıp üstüne çıkmaya odaklanır; sıfırdan aramak zorunda kalmaz.
    if warm_start:
        for i, idx in enumerate(warm_start):
            if i < len(xs) and idx is not None and idx >= 0:
                for sidx, v in xs[i]:
                    model.AddHint(v, 1 if sidx == idx else 0)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(seconds)
    solver.parameters.num_workers = int(workers)
    if seed:
        solver.parameters.random_seed = int(seed) & 0x7fffffff
    solver.parameters.log_search_progress = bool(log)

    st = solver.Solve(model)
    positions = [-1] * len(w.cards)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for i, row in enumerate(xs):
            for idx, v in row:
                if solver.Value(v):
                    positions[i] = idx
                    break
    placed = sum(w.cards[i].duration * len(w.cards[i].classes)
                 for i, idx in enumerate(positions) if idx >= 0)
    return positions, placed, solver.StatusName(st)
