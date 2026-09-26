"""Altın referans: masaüstü (Python) motorunun ara çıktılarını JSON'a döker.

Web motoru aynı .roz için aynı dünyayı, aynı kuralları, aynı kilit
çelişkilerini, aynı tanıyı ve BİREBİR aynı tabu problem metnini üretmek
zorundadır. tools/golden.ts aynı dökümü TypeScript motorundan alır,
tools/compare.mjs ikisini karşılaştırır.

    python tools/golden.py VERI.roz all|locked|asis|unlock CIKTI_KLASORU

Kurum verisine dokunmaz: dosyayı okur, HOME'u geçici klasöre yönlendirir.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, APP)
_home = tempfile.mkdtemp(prefix='chenkron-golden-')
os.environ['USERPROFILE'] = _home
os.environ['HOME'] = _home


def cells(mask):
    out, i = [], 0
    while mask:
        if mask & 1:
            out.append(i)
        mask >>= 1
        i += 1
    return out


def prep(src, mode):
    import copy
    d = copy.deepcopy(src)
    gp = [p for p in d.get('grid_placements') or [] if isinstance(p, dict)]
    if mode == 'all':
        d['grid_placements'] = []
        d['auto_schedule_results'] = []
    elif mode in ('locked', 'unlock'):
        d['grid_placements'] = [p for p in gp if p.get('locked') or p.get('is_locked')]
    d['yerlesim'] = {}
    d['loose_unplaced_cards'] = []
    d['manual_unplaced_cards'] = []
    return d


def main(roz, mode, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    src = json.load(open(roz, encoding='utf-8'))
    data = prep(src, mode)
    from scheduler.worker import hazirla
    from scheduler.engine import _dunya_kur, kilit_catismalari
    from scheduler.problem import Problem, impossible_groups
    from scheduler.diagnostics import diagnose
    from scheduler.daybound import day_bound
    from scheduler.verify import validate
    from scheduler.native_bridge import native_binary

    slug = (data.get('settings') or {}).get('institution_slug')
    d, D, P, selected, engel, others = hazirla(data, None, slug)
    raw = d.get('planlama_iliskileri', [])
    w, rules, report, kilitler = _dunya_kur(d, D, P, engel, selected, raw)
    catisma = kilit_catismalari(w, rules, kilitler, d, True)
    if catisma and mode == 'unlock':
        atla = frozenset(n for k in catisma for n in k['ids'])
        w, rules, report, kilitler = _dunya_kur(d, D, P, engel, selected, raw, atla=atla)
    forced = impossible_groups(w)
    issues, ub = diagnose(w, rules)
    gun_ust = day_bound(w, rules, forced, seconds=20.0)
    pb = Problem(w, rules, completion_first=True)
    body = pb._body()
    with open(os.path.join(out_dir, 'problem.txt'), 'w', newline='\n') as f:
        f.write(pb.header(2.0, 1, w.total_hours()) + body)

    # Aynı konumları iki motorun denetimine vermek için tabu ile bir çizelge.
    exe = native_binary()
    with open(os.path.join(out_dir, 'problem.txt')) as stdin:
        run = subprocess.run([str(exe), '2', '17'], stdin=stdin, capture_output=True, text=True, timeout=60)
    last = [l for l in run.stdout.splitlines() if l.startswith(('P', 'F'))][-1].split()
    positions = [int(x) for x in last[5:]]
    errs, soft, bent = validate(w, rules, positions, bend_rules=True, forced=forced)
    first_p = [l for l in run.stdout.splitlines() if l.startswith('P')][0]

    dump = dict(
        D=D, P=P, selected=selected,
        engel={k: sorted([list(x) for x in v]) for k, v in sorted(engel.items())},
        world=dict(
            classes=w.classes, teachers=w.teachers, subjects=w.subjects,
            families=w.families, subject_family=w.subject_family,
            class_closed=[cells(m) for m in w.class_closed],
            teacher_closed=[cells(m) for m in w.teacher_closed],
            class_avoid=[cells(m) for m in w.class_avoid],
            teacher_avoid=[cells(m) for m in w.teacher_avoid],
            class_capacity=w.class_capacity, class_demand=w.class_demand,
            cards=[dict(cid=c.cid, classes=list(c.classes), subject=c.subject, teacher=c.teacher,
                        duration=c.duration, origin=c.origin, group=c.group, locked_at=c.locked_at,
                        family=c.family, slots=[s for s, _ in c.slots], subject_name=c.subject_name,
                        teacher_name=c.teacher_name, class_names=list(c.class_names))
                   for c in w.cards],
            total_hours=w.total_hours()),
        rules=[dict(kind=r.kind, axis=r.axis, hardness=r.hardness, param=r.param, param2=r.param2,
                    subjects=sorted(r.subjects), teachers=sorted(r.teachers), klasses=sorted(r.klasses),
                    label=r.label) for r in rules],
        report=dict(warnings=report.warnings, errors=report.errors,
                    skipped=[list(x) for x in report.skipped]),
        kilitler=[dict(kart=k['kart'], ids=k['ids'], d=k['d'], p=k['p']) for k in kilitler],
        catisma=[k['mesaj'] for k in catisma],
        forced=sorted('|'.join(str(x) for x in g) for g in forced),
        diagnostics=[x['message'] for x in issues], upper_bound=ub, day_bound=gun_ust,
        problem_sha256=hashlib.sha256(body.encode()).hexdigest(),
        problem_len=len(body),
        tabu_first_line=first_p,
        validate=dict(positions=positions, errors=errs, soft=soft, bent=bent),
    )
    with open(os.path.join(out_dir, 'golden_py.json'), 'w', encoding='utf-8') as f:
        json.dump(dump, f, ensure_ascii=False, indent=1)
    print(f"python: kart {len(w.cards)} saat {w.total_hours()} kural {len(rules)} "
          f"kenar {len(pb.edges)} faktör {len(pb.factors)} gün-tavanı {gun_ust} çelişki {len(catisma)}")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
