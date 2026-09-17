"""Timefold Solver ile aynı çizelge problemi — motor karşılaştırması için.

    JAVA_HOME=~/.local/jdk/jdk-21.0.12.1+1/Contents/Home \\
    .venv-timefold/bin/python tools/timefold_bench.py INPUT.roz --seconds 60

Aynı dünya (scheduler.build), aynı kurallar (scheduler.rules). Her kart
1 saatlik parçalara ayrılır; parça bir hücreye atanır ya da boşta kalır.

  SERT   öğretmen çakışması, sınıf çakışması, kapalı hücre (değer aralığından
         zaten dışarıda), aynı kartın aynı güne düşen parçaları BİTİŞİK,
         "aynı ders aynı gün tekrar etmesin" (farklı kartlar),
         "aynı öğretmen aynı gün tekrar etmesin", "iki ders aynı güne gelmesin".
  ORTA   boşta kalan saat (en aza indirilir — yerleşen saat en çoğa).
  YUMUŞAK bölünen kart (kaç ayrı güne yayıldıysa o kadar).

Not: Timefold Community tek iş parçacıklıdır (çoklu iş parçacığı Enterprise);
CP-SAT 8 işçiyle koşar. Karşılaştırmada bunu göz önünde tut.
"""
import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from timefold.solver import SolverFactory
from timefold.solver.config import (SolverConfig, ScoreDirectorFactoryConfig,
                                    TerminationConfig, Duration)
from timefold.solver.domain import (planning_entity, planning_solution, PlanningId,
                                    PlanningVariable, PlanningScore,
                                    PlanningEntityCollectionProperty,
                                    ProblemFactCollectionProperty, ValueRangeProvider)
from timefold.solver.score import (HardMediumSoftScore, constraint_provider,
                                   ConstraintFactory, Joiners, ConstraintCollectors)

from scheduler.build import build_world, apply_subject_groups, attach_slots
from scheduler.rules import compile_rules
import scheduler.rules as R
from scheduler.problem import impossible_groups


@dataclass(frozen=True)
class Slot:
    id: Annotated[int, PlanningId]
    day: int
    period: int


@planning_entity
@dataclass
class Piece:
    id: Annotated[int, PlanningId]
    card: int                      # kart indeksi
    k: int                         # kart içindeki parça sırası
    teacher: int
    classes: frozenset
    weight: int                    # saat ağırlığı = sınıf sayısı
    family: int
    subject: int
    once_classes: frozenset        # "aynı ders aynı gün" bu sınıflarda geçerli
    tonce_classes: frozenset       # "aynı öğretmen aynı gün" bu sınıflarda geçerli
    pair_tags: frozenset           # {(kural, sınıf)} — "iki ders aynı güne gelmesin"
    allowed: Annotated[list[Slot], ValueRangeProvider(id="allowed")]
    slot: Annotated[Optional[Slot], PlanningVariable(value_range_provider_refs=["allowed"],
                                                    allows_unassigned=True)] = None


@planning_solution
@dataclass
class Plan:
    slots: Annotated[list[Slot], ProblemFactCollectionProperty]
    pieces: Annotated[list[Piece], PlanningEntityCollectionProperty]
    score: Annotated[Optional[HardMediumSoftScore], PlanningScore] = None


def shares(a: frozenset, b: frozenset) -> bool:
    return not a.isdisjoint(b)


@constraint_provider
def constraints(cf: ConstraintFactory):
    return [
        # SERT
        cf.for_each_unique_pair(Piece,
                                Joiners.equal(lambda p: p.teacher),
                                Joiners.equal(lambda p: p.slot))
          .filter(lambda a, b: a.teacher >= 0)
          .penalize(HardMediumSoftScore.ONE_HARD)
          .as_constraint("öğretmen çakışması"),
        cf.for_each_unique_pair(Piece, Joiners.equal(lambda p: p.slot))
          .filter(lambda a, b: shares(a.classes, b.classes))
          .penalize(HardMediumSoftScore.ONE_HARD)
          .as_constraint("sınıf çakışması"),
        # Aynı kartın aynı güne düşen parçaları bitişik olsun (blok bütünlüğü).
        cf.for_each(Piece)
          .group_by(lambda p: (p.card, p.slot.day),
                    ConstraintCollectors.count(),
                    ConstraintCollectors.min(lambda p: p.slot.period),
                    ConstraintCollectors.max(lambda p: p.slot.period))
          .filter(lambda key, n, lo, hi: hi - lo + 1 != n)
          .penalize(HardMediumSoftScore.ONE_HARD, lambda key, n, lo, hi: abs(hi - lo + 1 - n))
          .as_constraint("blok bütünlüğü"),
        # Aynı ders aynı gün tekrar etmesin (farklı kartlar, ortak sınıf).
        cf.for_each_unique_pair(Piece,
                                Joiners.equal(lambda p: p.family),
                                Joiners.equal(lambda p: p.slot.day))
          .filter(lambda a, b: a.card != b.card and shares(a.once_classes, b.once_classes))
          .penalize(HardMediumSoftScore.ONE_HARD)
          .as_constraint("aynı ders aynı gün"),
        cf.for_each_unique_pair(Piece,
                                Joiners.equal(lambda p: p.teacher),
                                Joiners.equal(lambda p: p.slot.day))
          .filter(lambda a, b: a.card != b.card and a.teacher >= 0
                  and shares(a.tonce_classes, b.tonce_classes))
          .penalize(HardMediumSoftScore.ONE_HARD)
          .as_constraint("aynı öğretmen aynı gün"),
        cf.for_each_unique_pair(Piece, Joiners.equal(lambda p: p.slot.day))
          .filter(lambda a, b: a.subject != b.subject and shares(a.pair_tags, b.pair_tags))
          .penalize(HardMediumSoftScore.ONE_HARD)
          .as_constraint("iki ders aynı güne gelmesin"),
        # ORTA: boşta kalan saat
        cf.for_each_including_unassigned(Piece)
          .filter(lambda p: p.slot is None)
          .penalize(HardMediumSoftScore.ONE_MEDIUM, lambda p: p.weight)
          .as_constraint("boşta kalan saat"),
        # YUMUŞAK: bölünen kart
        cf.for_each(Piece)
          .group_by(lambda p: p.card, ConstraintCollectors.count_distinct(lambda p: p.slot.day))
          .filter(lambda card, days: days > 1)
          .penalize(HardMediumSoftScore.ONE_SOFT, lambda card, days: days - 1)
          .as_constraint("bölünen kart"),
    ]


def build_plan(data):
    w = build_world(data)
    rules, rep = compile_rules(data.get("planlama_iliskileri", []), w)
    apply_subject_groups(w, rules)
    attach_slots(w, rules)
    forced = impossible_groups(w)
    D, P = w.D, w.P
    slots = [Slot(d * P + p, d, p) for d in range(D) for p in range(P)]
    once = [r for r in rules if r.is_hard() and r.kind == R.X_SUBJECT_ONCE_DAY]
    tonce = [r for r in rules if r.is_hard() and r.kind == R.X_TEACHER_ONCE_DAY]
    pairs = [(i, r) for i, r in enumerate(rules) if r.is_hard() and r.kind == R.X_PAIR_NOT_SAME_DAY]
    pieces = []
    for c in w.cards:
        allowed = []
        for s in slots:
            fp = 1 << s.id
            if any(fp & w.class_closed[ci] for ci in c.classes):
                continue
            if c.teacher >= 0 and (fp & w.teacher_closed[c.teacher]):
                continue
            allowed.append(s)
        once_cls = frozenset(ci for ci in c.classes
                             if any(r.applies_card(c) and r.applies_class(ci) for r in once)
                             and ('s', ci, c.family) not in forced)
        tonce_cls = frozenset(ci for ci in c.classes
                              if any(r.applies_card(c) and r.applies_class(ci) for r in tonce)
                              and ('t', ci, c.teacher) not in forced)
        tags = frozenset((ri, ci) for ri, r in pairs for ci in c.classes
                         if r.applies_card(c) and r.applies_class(ci))
        for k in range(c.duration):
            if c.locked_at is not None:
                al = [slots[c.locked_at + k]]
            else:
                al = allowed
            pieces.append(Piece(len(pieces), c.cid, k, c.teacher, frozenset(c.classes),
                                len(c.classes), c.family, c.subject, once_cls, tonce_cls,
                                tags, al))
    return w, rules, Plan(slots, pieces)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--search", default="default",
                    help="default | tabu | annealing | late (yerel arama türü)")
    args = ap.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    t0 = time.time()
    w, rules, plan = build_plan(data)
    total = w.total_hours()
    print(f"dünya: {len(w.cards)} kart, {len(plan.pieces)} parça, {total} saat, "
          f"{len(w.classes)} sınıf, {len(w.teachers)} öğretmen, kural: "
          f"{[r.kind for r in rules if r.kind.startswith('X_')]} ({time.time()-t0:.1f}s)")

    cfg = SolverConfig(
        solution_class=Plan, entity_class_list=[Piece],
        score_director_factory_config=ScoreDirectorFactoryConfig(constraint_provider_function=constraints),
        termination_config=TerminationConfig(
            spent_limit=Duration(seconds=int(args.seconds)),
            # Tam ve çakışmasız çizelge bulunur bulunmaz dur (bölme cezası ne olursa olsun).
            best_score_limit="0hard/0medium/-999999soft"),
    )
    # Yerel arama türü yalnızca XML ile seçilebiliyor (Python API'de alan yok).
    ls = {"tabu": "<localSearchType>TABU_SEARCH</localSearchType>",
          "annealing": ("<acceptor><simulatedAnnealingStartingTemperature>0hard/1medium/20soft"
                        "</simulatedAnnealingStartingTemperature></acceptor>"
                        "<forager><acceptedCountLimit>1</acceptedCountLimit></forager>"),
          "late": ("<acceptor><lateAcceptanceSize>400</lateAcceptanceSize></acceptor>"
                   "<forager><acceptedCountLimit>1</acceptedCountLimit></forager>")}.get(args.search)
    if ls:
        cfg.xml_source_text = f"""<solver xmlns="https://timefold.ai/xsd/solver">
  <constructionHeuristic/>
  <localSearch>{ls}</localSearch>
</solver>"""
    solver = SolverFactory.create(cfg).build_solver()
    t_start = time.time()
    marks = []

    def on_best(event):
        sc = event.new_best_score
        marks.append((time.time() - t_start, str(sc)))

    solver.add_event_listener(on_best)
    sol = solver.solve(plan)
    dt = time.time() - t_start
    sc = sol.score
    placed = sum(p.weight for p in sol.pieces if p.slot is not None)
    hard = sc.hard_score if hasattr(sc, "hard_score") else None
    print(f"Timefold: {placed}/{total} saat, skor {sc}, {dt:.1f}s")
    # ilerleme: ilk kez sert=0'a düşüş ve her orta iyileşmesi
    last = None
    for t, s in marks:
        h, m, _ = [int(x.rstrip("hardmediumsoft")) for x in s.split("/")]
        key = (h == 0, m)
        if key != last:
            print(f"   {t:6.1f}s  {s}")
            last = key
    # doğrulama (kendi başına): çakışma sayımı
    occ = {}
    clash = 0
    for p in sol.pieces:
        if p.slot is None:
            continue
        if p.teacher >= 0:
            k = ("t", p.teacher, p.slot.id)
            clash += occ.get(k, 0); occ[k] = occ.get(k, 0) + 1
        for ci in p.classes:
            k = ("c", ci, p.slot.id)
            clash += occ.get(k, 0); occ[k] = occ.get(k, 0) + 1
    print(f"bağımsız sayım: çakışma {clash}, boşta {total - placed} saat")


if __name__ == "__main__":
    main()
