"""
perfect_scheduler.py — 180/180 ve sıfır çakışma için birleşik motor.

Tek bir yöntem yetmiyor; ikisi dönüşümlü çalışınca yetiyor:

  TABU (tabu_repair)      Bütün dersler MUTLAKA bir yerde. Sınıf hücreleri tam
                          dolu, ihlallere geçici izin var, hafızalı arama
                          (tabu + sarsma) maliyeti düşürüyor. Tek başına 180/180
                          yerleştiriyor ama 1-3 öğretmen çakışması bırakıyor.

  ZİNCİR (chain_scheduler) Dolu bir çizelgeye TEK dersi sokmakta güçlü: tahliye
                          zinciriyle onlarca dersi kaydırıp yer açıyor. Tek
                          başına baştan kurmakta zayıf.

Döngü şu: tabu çalışır, kalan çakışmalı derslerden biri SÖKÜLÜR (çizelge artık
çakışmasız ama eksik), zincir o dersi yeniden yerleştirmeye çalışır. Yerleşirse
çizelge eksiksiz ve çakışmasızdır. Yerleşmezse elde kalan hâl bir sonraki tabu
turuna tohum olur ve döngü sürer.

Her turda farklı rastgelelik kullanılır; kabul ölçütü serttir: sonuç ancak
doğrulamadan geçerse (hiç çakışma yok, kapalı saatte ders yok, bütün dersler
yerleşti) kabul edilir.
"""
import time
from collections import defaultdict

import chain_scheduler
import tabu_repair


def _conflicting(blocks, pos, teacher_ok):
    """Çakışan ya da kapalı saatte duran blokların indeksleri."""
    tcount = defaultdict(list)
    bad = set()
    for i, b in enumerate(blocks):
        if pos[i] is None or not b["tk"]:
            continue
        d, p = pos[i]
        for o in range(b["size"]):
            tcount[(b["tk"], d, p + o)].append(i)
            if not teacher_ok(b["tk"], d, p + o):
                bad.add(i)
    for v in tcount.values():
        if len(v) > 1:
            bad.update(v[1:])          # birini yerinde bırak, ötekileri sök
    return bad


def _validate(blocks, pos, class_open, teacher_ok, D, P):
    """Eksiksiz VE çakışmasız mı? Tek doğruluk kapısı."""
    cells, tcells = set(), set()
    for i, b in enumerate(blocks):
        if pos[i] is None:
            return False
        d, p = pos[i]
        if p + b["size"] > P:
            return False
        for o in range(b["size"]):
            slot = (d, p + o)
            if slot not in class_open.get(b["cls"], ()):
                return False
            ck = (b["cls"],) + slot
            if ck in cells:
                return False
            cells.add(ck)
            if b["tk"]:
                if not teacher_ok(b["tk"], d, p + o):
                    return False
                tk = (b["tk"],) + slot
                if tk in tcells:
                    return False
                tcells.add(tk)
    return True


def solve_perfect(classes, class_blocks, blocks, class_open, teacher_ok,
                  D, P, rng, time_budget=90.0, on_progress=None):
    """Eksiksiz ve çakışmasız çizelge ara.

    blocks, class_blocks ile AYNI sırada olmalı (sınıf sınıf, sıralı).
    Dönen: (yerleşimler, kalan_ihlal). kalan_ihlal 0 ise çizelge kusursuzdur.
    """
    deadline = time.time() + max(5.0, float(time_budget))
    best_pos, best_bad = None, None
    seed_pos = None
    round_no = 0

    while time.time() < deadline:
        round_no += 1
        # Tabu'ya YETERLİ süre: 10 saniyenin altında yakınsayamıyor, kısa
        # dilimlere bölmek turu da tabuyu da işe yaramaz hale getiriyordu.
        remaining = deadline - time.time()
        slice_s = max(12.0, min(20.0, remaining * 0.6))

        # 1) TABU: her şeyi yerleştir, ihlalleri erit
        rep = tabu_repair.TabuRepair(blocks, class_open, teacher_ok, D, P, rng,
                                     min(deadline, time.time() + slice_s))
        if not rep.seed(seed_pos):
            return (best_pos or []), (best_bad if best_bad is not None else -1)
        rep.run()
        pos = list(rep.pos)

        if _validate(blocks, pos, class_open, teacher_ok, D, P):
            return _as_placements(blocks, pos), 0

        # 2) Çakışanları sök, ZİNCİR ile yeniden yerleştir
        bad = _conflicting(blocks, pos, teacher_ok)
        for i in bad:
            pos[i] = None
        solver = chain_scheduler.ChainSolver(
            classes, class_blocks, class_open, teacher_ok, D, P, rng,
            min(deadline, time.time() + slice_s), max_depth=25, max_eject=3)
        solver.adopt(pos)
        for i in sorted(bad):
            if time.time() > deadline:
                break
            solver.place(i, 25)
        pos2 = list(solver.pos)

        if _validate(blocks, pos2, class_open, teacher_ok, D, P):
            return _as_placements(blocks, pos2), 0

        # 3) En iyiyi sakla, bir sonraki tura tohum yap
        missing = sum(blocks[i]["size"] for i in range(len(blocks))
                      if pos2[i] is None)
        score = missing + len(_conflicting(blocks, pos2, teacher_ok))
        if best_bad is None or score < best_bad:
            best_bad, best_pos = score, list(pos2)
        # Her tur TAZE rastgelelikle başlar: bozulmuş bir durumu tohum yapmak
        # aramayı aynı çıkmaza geri sokuyordu. En iyi hâl zaten saklı.
        seed_pos = None
        if on_progress:
            on_progress(round_no, score)

    if best_pos is not None and _validate(blocks, best_pos, class_open,
                                          teacher_ok, D, P):
        return _as_placements(blocks, best_pos), 0
    return _as_placements(blocks, best_pos or []), (best_bad if best_bad is not None else -1)


def _as_placements(blocks, pos):
    out = []
    for i, b in enumerate(blocks):
        if i >= len(pos) or pos[i] is None:
            continue
        d, p = pos[i]
        out.append({"cls": b["cls"], "day": d, "period": p,
                    "duration": b["size"], "subject": b.get("subject", ""),
                    "teacher": b.get("teacher", ""),
                    "block_id": b.get("block_id", "")})
    return out
