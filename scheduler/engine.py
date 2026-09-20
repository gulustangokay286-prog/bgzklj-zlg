"""Public entry point: snapshot -> rules -> native search -> independent audit."""
import time
import copy
import os
from .build import build_world, attach_slots, apply_subject_groups
from .rules import compile_rules
from .problem import Problem, impossible_groups
from .diagnostics import diagnose
from .native_bridge import search, search_portfolio, NativeEngineMissing
def _safe_search(pb, *a, **k):
    """Motor yoksa boş sonuç döndürür; arama olmadan da akış sürer."""
    try:
        return search(pb, *a, **k)
    except NativeEngineMissing as exc:
        print(f'[engine] {exc}')
        return dict(hours=0, steps=0, restarts=0, soft_cost=0,
                    cancelled=False, positions=[-1]*len(pb.world.cards))



from .verify import validate
from .model import norm_key, norm_class


class Result:
    def __init__(self):
        self.placements=[];self.unplaced=[];self.conflicts=[];self.violations=[]
        self.warnings=[];self.rules=[];self.diagnostics=[]
        self.elapsed=0.0;self.attempts=0;self.placed_hours=0;self.total_hours=0
        self.steps=0;self.chain_calls=0;self.status='not_started';self.upper_bound=0
        self.positions=[];self.soft_cost=0;self.bent_rules=[];self.forced_minimums=[]
        self.split_pieces={}

    @property
    def complete(self):
        return self.placed_hours==self.total_hours and not self.unplaced and self.valid

    @property
    def valid(self):
        return not self.conflicts and not self.violations

    def summary(self):
        note = (f" · {len(self.forced_minimums)} aritmetik taban"
                if self.forced_minimums else "")
        return (f"{self.placed_hours}/{self.total_hours} saat · "
                f"{len(self.conflicts)} çakışma · {len(self.violations)} kural ihlali"
                f"{note} · {self.elapsed:.2f} sn")


def bind_locks(world, placements):
    """Bind saved blocks to demand cards; never silently discard a requested lock.

    Split-piece handling
    --------------------
    When the engine splits a 2-hour block into two 1-hour pieces, each piece is
    stored with ``duration: 1`` and ``is_split: True``.  If the user locks the
    teacher row and resets, these pieces remain in ``grid_placements`` but the
    *world* still has the original card with ``duration: 2``.  An exact-duration
    match therefore fails.

    The fix:
    1. Separate split pieces from whole-block locks.
    2. Group split pieces by their parent card (``card_id`` or ``block_id``
       prefix ``cNbK`` → N).
    3. For each group find the parent card (class/subject/teacher match,
       ignoring duration) and lock it at the *earliest* piece position.
    4. For whole-block locks that still fail exact-duration match, retry with
       a relaxed duration (the stored duration may have changed between saves).
    5. Never crash; unmatched locks are collected and reported as warnings.
    """
    import re
    used = set()
    warnings = []

    # ── 1. Partition: split pieces vs normal locks ──────────────────────
    normal_locks = []
    split_pieces = []   # (placement, card_id_hint)
    for pl in placements:
        if not (pl.get('locked') or pl.get('pinned')):
            continue
        if pl.get('is_split'):
            # Try to extract original card id from block_id (format: "c{cid}b{k}")
            bid = str(pl.get('block_id') or '')
            m = re.match(r'c(\d+)b\d+', bid)
            hint = int(m.group(1)) if m else pl.get('card_id')
            split_pieces.append((pl, hint))
        else:
            normal_locks.append(pl)

    # ── 2. Normal (non-split) locks ─────────────────────────────────────
    for pl in normal_locks:
        cn = norm_class(pl.get('class_name') or pl.get('class'))
        sn = norm_key(pl.get('subject_name') or pl.get('subject'))
        tn = norm_key(pl.get('teacher_name') or pl.get('teacher'))
        d = int(pl.get('day', pl.get('col', 0)))
        p = int(pl.get('period', pl.get('row', 0)))
        dur = int(pl.get('duration') or 1)
        idx = d * world.P + p

        # Exact match (class + subject + teacher + duration)
        candidates = [c for c in world.cards
                      if cn in {norm_class(x) for x in c.class_names}
                      and norm_key(c.subject_name) == sn
                      and norm_key(c.teacher_name) == tn
                      and c.duration == dur]
        if any(c.locked_at == idx for c in candidates):
            continue
        c = next((c for c in candidates if c.cid not in used), None)

        # Relaxed match: ignore duration (assignment may have been edited)
        if c is None:
            candidates = [c for c in world.cards
                          if cn in {norm_class(x) for x in c.class_names}
                          and norm_key(c.subject_name) == sn
                          and norm_key(c.teacher_name) == tn]
            if any(c.locked_at == idx for c in candidates):
                continue
            c = next((c for c in candidates if c.cid not in used), None)

        if c is None:
            warnings.append(
                f"Kilitli yerleşim eşleşemedi (atlandı): "
                f"{pl.get('class_name') or pl.get('class')} · "
                f"{pl.get('subject_name') or pl.get('subject')} · "
                f"{pl.get('teacher_name') or pl.get('teacher')}")
            continue
        if not (0 <= d < world.D and 0 <= p and p + c.duration <= world.P):
            warnings.append(
                f"Kilitli yerleşim gün/saat sınırını aşıyor (atlandı): "
                f"{pl.get('class_name') or pl.get('class')} · "
                f"{pl.get('subject_name') or pl.get('subject')}")
            continue
        c.locked_at = idx
        used.add(c.cid)

    # ── 3. Split pieces: group by parent card, lock the original card ───
    from collections import defaultdict
    groups = defaultdict(list)  # key → [(pl, idx)]
    for pl, hint in split_pieces:
        cn = norm_class(pl.get('class_name') or pl.get('class'))
        sn = norm_key(pl.get('subject_name') or pl.get('subject'))
        tn = norm_key(pl.get('teacher_name') or pl.get('teacher'))
        d = int(pl.get('day', pl.get('col', 0)))
        p = int(pl.get('period', pl.get('row', 0)))
        idx = d * world.P + p
        key = (cn, sn, tn, hint)  # hint may be None
        groups[key].append((pl, idx))

    for (cn, sn, tn, hint), pieces in groups.items():
        # Find parent card (ignore duration — split pieces are always dur=1)
        candidates = [c for c in world.cards
                      if cn in {norm_class(x) for x in c.class_names}
                      and norm_key(c.subject_name) == sn
                      and norm_key(c.teacher_name) == tn]
        # Prefer card whose cid matches the hint
        if hint is not None:
            preferred = [c for c in candidates if c.cid == hint and c.cid not in used]
            if not preferred:
                preferred = [c for c in candidates if c.cid not in used]
        else:
            preferred = [c for c in candidates if c.cid not in used]
        # Already locked at the earliest piece position?
        earliest_idx = min(idx for _, idx in pieces)
        if any(c.locked_at == earliest_idx for c in candidates):
            continue
        c = preferred[0] if preferred else None
        if c is None:
            sample = pieces[0][0]
            warnings.append(
                f"Bölünmüş kilitli yerleşim eşleşemedi (atlandı): "
                f"{sample.get('class_name') or sample.get('class')} · "
                f"{sample.get('subject_name') or sample.get('subject')}")
            continue
        # Lock at earliest piece position
        d0, p0 = divmod(earliest_idx, world.P)
        if not (0 <= d0 < world.D and 0 <= p0 and p0 + c.duration <= world.P):
            # Try each piece individually — maybe one fits
            locked_any = False
            for _, pidx in sorted(pieces, key=lambda x: x[1]):
                dd, pp = divmod(pidx, world.P)
                if 0 <= dd < world.D and 0 <= pp and pp + c.duration <= world.P:
                    c.locked_at = pidx
                    used.add(c.cid)
                    locked_any = True
                    break
            if not locked_any:
                sample = pieces[0][0]
                warnings.append(
                    f"Bölünmüş kilitli yerleşim sınır aşımı (atlandı): "
                    f"{sample.get('class_name') or sample.get('class')} · "
                    f"{sample.get('subject_name') or sample.get('subject')}")
        else:
            c.locked_at = earliest_idx
            used.add(c.cid)

    return warnings




def _kayitli_yer(data_store, world, card):
    """Kartın KAYITLI çizelgedeki yeri (ızgara indeksi) — yoksa None.

    Optimal kipin ikinci aşaması "mevcut tablodan en az sapma"yı arar; sapma
    ancak mevcut tablo bilinirse ölçülebilir. Eşleme kart kimliğiyle değil
    sınıf/ders/öğretmen/süre ile yapılır: kullanıcı elle yerleştirdiğinde
    kart kimlikleri tutmuyor.
    """
    if not hasattr(data_store, 'get'):
        return None
    eslesme = getattr(_kayitli_yer, '_tablo', None)
    if eslesme is None or eslesme.get('_kaynak') is not data_store:
        eslesme = {'_kaynak': data_store}
        for pl in data_store.get('grid_placements') or []:
            try:
                d=int(pl.get('day',pl.get('col',0)));p=int(pl.get('period',pl.get('row',0)))
            except (TypeError,ValueError):
                continue
            anahtar=(norm_class(pl.get('class_name') or pl.get('class')),
                     norm_key(pl.get('subject_name') or pl.get('subject')),
                     norm_key(pl.get('teacher_name') or pl.get('teacher')),
                     int(pl.get('duration') or 1))
            eslesme.setdefault(anahtar,[]).append(d*world.P+p)
        _kayitli_yer._tablo = eslesme
    for cn in card.class_names:
        anahtar=(norm_class(cn), norm_key(card.subject_name),
                 norm_key(card.teacher_name), card.duration)
        yerler=eslesme.get(anahtar)
        if yerler:
            return yerler.pop(0)
    return None


def _bitir(res, w, rules, data_store, completion_first, start):
    """Doğrulama + çizelgenin kurulması. Bütün kipler buradan çıkar."""
    # Kilitli kartlar motora sokulmadı; verify.py'de hata vermemesi için
    # dünyada kalmış olabilecek kilit işaretlerini temizle.
    for c in w.cards:
        c.locked_at = None
    forced=impossible_groups(w) if completion_first else set()
    errors,soft,bent=validate(w,rules,res.positions,bend_rules=completion_first,
                              forced=forced,pieces=getattr(res,'split_pieces',None))
    if errors:
        raise RuntimeError('Çizelge son denetimden geçmedi; sonuç uygulanmadı:\n'+'\n'.join(errors[:12]))
    res.warnings.extend(soft)
    res.forced_minimums=bent
    res.bent_rules=[]
    for b in bent:
        res.warnings.append('ARİTMETİK TABAN — '+b+
                            ' (bu ders için mümkün olan en az tekrar)')
    # Kilitli yerleşimleri olduğu gibi geri ekle (motor bunlara dokunmadı).
    for pl in getattr(res, '_locked_placements', []):
        dur = int(pl.get('duration') or 1)
        res.placed_hours += dur
        p_copy = dict(pl)
        d = int(pl.get('day', pl.get('col', 0)))
        p = int(pl.get('period', pl.get('row', 0)))
        cn = pl.get('class_name') or pl.get('class')
        sn = pl.get('subject_name') or pl.get('subject')
        tn = pl.get('teacher_name') or pl.get('teacher')
        p_copy.update({
            'class_name': cn, 'class': cn,
            'subject_name': sn, 'subject': sn,
            'teacher_name': tn, 'teacher': tn,
            'day': d, 'day_idx': d, 'col': d,
            'period': p, 'row': p,
            'duration': dur,
            'locked': True, 'is_manual': True, 'is_filler': False
        })
        res.placements.append(p_copy)
    parcalar=getattr(res,'split_pieces',None) or {}
    for i,(c,idx) in enumerate(zip(w.cards,res.positions)):
        if idx<0 and i in parcalar:
            # BÖLÜNMÜŞ KART — 1 saatlik parçalar halinde yerleşti.
            original=data_store.get('atamalar',[])[c.origin]
            for k,pidx in enumerate(parcalar[i]):
                d,p=divmod(pidx,w.P)
                res.placed_hours+=len(c.classes)
                for cn in c.class_names:
                    res.placements.append(dict(class_name=cn,**{'class':cn},subject_name=c.subject_name,
                        subject=c.subject_name,teacher_name=c.teacher_name,teacher=c.teacher_name,
                        day=d,day_idx=d,col=d,period=p,row=p,duration=1,
                        is_combined=len(c.classes)>1,combined_classes=list(c.class_names) if len(c.classes)>1 else [],
                        block_id=f'c{c.cid}b{k}',card_id=c.cid,assignment_index=c.origin,
                        locked=False,is_manual=False,is_filler=False,is_split=True,
                        color=original.get('color') or original.get('renk')))
            continue
        if idx<0:
            for cn in c.class_names:
                res.unplaced.append(dict(card_id=c.cid,**{'class':cn},subject=c.subject_name,
                                         teacher=c.teacher_name,duration=c.duration,hours=c.duration,
                                         block_id=f'c{c.cid}'))
            continue
        d,p=divmod(idx,w.P)
        res.placed_hours+=c.duration*len(c.classes)
        original=data_store.get('atamalar',[])[c.origin]
        for cn in c.class_names:
            res.placements.append(dict(class_name=cn,**{'class':cn},subject_name=c.subject_name,
                subject=c.subject_name,teacher_name=c.teacher_name,teacher=c.teacher_name,
                day=d,day_idx=d,col=d,period=p,row=p,duration=c.duration,
                is_combined=len(c.classes)>1,combined_classes=list(c.class_names) if len(c.classes)>1 else [],
                block_id=f'c{c.cid}',card_id=c.cid,assignment_index=c.origin,
                locked=False,is_manual=False,is_filler=False,
                color=original.get('color') or original.get('renk')))
    if res.status!='cancelled':
        res.status='complete' if res.placed_hours==res.total_hours else 'timeout'
    if res.complete:
        res.status='complete'
        # Tanı, kuralların DELİNEMEZ olduğu varsayımıyla bir üst sınır
        # hesaplar ("en az 1 sınıf-saati yerleşemez"). Çizelge tamamlandıysa
        # bu tahmin boşa çıkmıştır; 285/285'in yanında "1 saat oturmaz"
        # yazması kullanıcıyı çizelgenin eksik olduğuna inandırıyordu.
        eski=[x['message'] for x in res.diagnostics]
        res.diagnostics=[]
        res.warnings=[w for w in res.warnings if w not in eski]
    elif res.diagnostics and res.status!='cancelled': res.status='infeasible'
    res.elapsed=time.monotonic()-start
    return res


def solve(data_store, time_budget=10.0, D=None, P=None, cross_busy=None,
          only_classes=None, seed=None, max_attempts=6, progress=None,
          relations=None, cancelled=None, completion_first=True, use_cpsat=True,
          optimal_mode=False, allow_split=True, azami_saniye=3600.0,
          ask_continue=None):
    """Çizelgeyi kurar.

    completion_first VARSAYILAN OLARAK AÇIKTIR: çizelgenin tamamlanması
    önceliklidir. Kural ile veri çelişiyorsa motor dersi yerleştirmez ve
    nedenini söyler — 284/285 çıkar ve hangi kuralın hangi dersi engellediği
    rapora yazılır. Sessizce dolmuş ama kuralı çiğnemiş bir çizelge, eksik
    ama dürüst bir çizelgeden daha pahalıdır: biri fark edilip düzeltilir,
    diğeri okula dağıtılır.

    Kullanıcı raporu görüp "yine de yerleştir" derse completion_first=True
    ile çağrılır. O zaman kural yalnızca aritmetiğin imkânsız kıldığı grupta
    ve gereken en az ölçüde esner; esneyen her nokta sonuçta listelenir.
    """
    start=time.monotonic();res=Result()
    w=build_world(data_store,D=D,P=P,cross_busy=cross_busy,only_classes=only_classes)
    raw=relations if relations is not None else data_store.get('planlama_iliskileri',[])
    rules,report=compile_rules(raw,w)
    if report.errors:
        raise ValueError('Planlama ilişkileri uygulanamadı:\n'+'\n'.join(report.errors))
    # "Seçilen dersler aynı ders sayılsın": aileler burada kurulur, kural
    # kapsamları aileye genişler. Bundan sonra "aynı ders" her katmanda aynı
    # şeyi ifade eder — arama, CP-SAT, bitirme geçişi ve bağımsız denetim.
    apply_subject_groups(w,rules)
    if only_classes:
        active={norm_class(cn) for c in w.cards for cn in c.class_names}
        teachers={norm_key(n):i for i,n in enumerate(w.teachers)}
        for pl in data_store.get('grid_placements',[]):
            if norm_class(pl.get('class_name') or pl.get('class')) in active:
                continue
            ti=teachers.get(norm_key(pl.get('teacher_name') or pl.get('teacher')))
            if ti is None: continue
            d=int(pl.get('day',pl.get('col',0)));p=int(pl.get('period',pl.get('row',0)))
            for off in range(int(pl.get('duration') or 1)):
                if 0<=d<w.D and 0<=p+off<w.P:
                    w.teacher_closed[ti] |= 1 << (d*w.P+p+off)
    # ── KİLİTLİ YERLEŞİMLER ──
    # Kilitli dersler motora GİRMEZ. Olduğu yerde kalır:
    # 1) Saatleri meşgul olarak işaretlenir (başka ders konmaz)
    # 2) Eşleşen kart aramadan çıkarılır (çift yerleşim olmasın)
    # 3) Sonuçta oldukları gibi geri eklenir
    all_grid = data_store.get('grid_placements', [])
    locked_pls = [pl for pl in all_grid if isinstance(pl, dict)
                  and (pl.get('locked') in (True, 'True', 'true', 1, '1') or
                       pl.get('pinned') in (True, 'True', 'true', 1, '1'))
                  and (not only_classes or
                       norm_class(pl.get('class_name') or pl.get('class'))
                       in {norm_class(x) for x in only_classes})]
    teachers_idx = {norm_key(n): i for i, n in enumerate(w.teachers)}
    classes_idx = {norm_class(n): i for i, n in enumerate(w.classes)}
    neutralized_cids = set()
    # 1) Mark locked slots as busy
    for pl in locked_pls:
        tn = norm_key(pl.get('teacher_name') or pl.get('teacher'))
        cn = norm_class(pl.get('class_name') or pl.get('class'))
        ti = teachers_idx.get(tn)
        ci = classes_idx.get(cn)
        d = int(pl.get('day', pl.get('col', 0)))
        p = int(pl.get('period', pl.get('row', 0)))
        dur = int(pl.get('duration') or 1)
        for off in range(dur):
            cell = d * w.P + p + off
            if 0 <= cell < w.D * w.P:
                if ti is not None: w.teacher_closed[ti] |= 1 << cell
                if ci is not None: w.class_closed[ci] |= 1 << cell
    # 2) Deduplicate (combined lessons have one entry per class)
    seen_inst = set()
    unique_locked = []
    for pl in locked_pls:
        sn = norm_key(pl.get('subject_name') or pl.get('subject'))
        tn = norm_key(pl.get('teacher_name') or pl.get('teacher'))
        cn = norm_class(pl.get('class_name') or pl.get('class'))
        d = int(pl.get('day', pl.get('col', 0)))
        p = int(pl.get('period', pl.get('row', 0)))
        is_comb = bool(pl.get('is_combined')) or bool(pl.get('combined_classes'))
        key = ('_comb_', sn, tn, d, p) if is_comb else (cn, sn, tn, d, p)
        if key not in seen_inst:
            seen_inst.add(key)
            unique_locked.append(pl)
    # 3) Find and remove matching world cards (or reduce duration)
    for pl in unique_locked:
        cn = norm_class(pl.get('class_name') or pl.get('class'))
        sn = norm_key(pl.get('subject_name') or pl.get('subject'))
        tn = norm_key(pl.get('teacher_name') or pl.get('teacher'))
        needed_dur = int(pl.get('duration') or 1)
        while needed_dur > 0:
            candidates = [c for c in w.cards
                          if cn in {norm_class(x) for x in c.class_names}
                          and norm_key(c.subject_name) == sn
                          and norm_key(c.teacher_name) == tn
                          and c.cid not in neutralized_cids]
            if not candidates:
                break
            exact = [c for c in candidates if c.duration == needed_dur]
            chosen = exact[0] if exact else candidates[0]
            if chosen.duration <= needed_dur:
                needed_dur -= chosen.duration
                neutralized_cids.add(chosen.cid)
            else:
                chosen.duration -= needed_dur
                needed_dur = 0
    if neutralized_cids:
        w.cards = [c for c in w.cards if c.cid not in neutralized_cids]
        for new_id, c in enumerate(w.cards):
            c.cid = new_id
    # Store for _bitir
    res._locked_placements = locked_pls
    locked_hours = sum(int(pl.get('duration') or 1) for pl in locked_pls)
    attach_slots(w, rules)
    res.world = w; res.rules = rules; res.warnings = list(report.warnings)
    res.total_hours = w.total_hours() + locked_hours; res.positions = [-1] * len(w.cards)
    res.diagnostics,res.upper_bound=diagnose(w,rules)
    # Aritmetiğin dayattığı gruplar bir kez hesaplanır; her denetim aynı kümeyi
    # kullanır. Tamamlanma öncelikli kip kapalıysa hiçbir grup esnemez.
    forced=impossible_groups(w) if completion_first else set()
    search_target=w.total_hours() if completion_first else res.upper_bound
    gun_ust=None
    if w.cards:
        try:
            from .daybound import day_bound, explain_day_bound
            gun_ust=day_bound(w,rules,forced,seconds=2.0)
        except Exception as exc:
            res.warnings.append(f"Gün-seviyesi sınır hesaplanamadı: {exc}")
    if gun_ust is not None:
        if gun_ust<min(w.total_hours(),res.upper_bound):
            try:
                res.diagnostics.extend(explain_day_bound(w,rules,forced,gun_ust,seconds=5.0))
            except Exception as exc:
                res.warnings.append(f"Gün-seviyesi tanı çalışmadı: {exc}")
        if gun_ust<res.upper_bound: res.upper_bound=gun_ust
        if gun_ust<search_target: search_target=gun_ust
    res.warnings.extend(x['message'] for x in res.diagnostics)
    for c in w.cards:
        if c.locked_at is not None and not c.slots:
            res.warnings.append(f"Kilitli kart kapalı saate veya planlama kuralına aykırı (kilit kaldırıldı): {c}")
            c.locked_at = None
    # ── OPTİMAL KİP ──
    #
    # "Optimale çıkana kadar durmasın, optimale ulaşınca dursun; uzun sürmesi
    # önemli değil, sürekli takas yapa yapa ilerlesin."
    #
    # Burada süre bir hedef değil, yalnızca emniyet sübabıdır: motor CP-SAT'in
    # OPTIMAL kanıtını bekler. Kanıt geldiğinde ikinci aşama başlar ve aynı
    # saat sayısına ulaşan çözümler arasından kullanıcının mevcut tablosuna
    # EN AZ TAKASLA ulaşanı seçilir. Bloklar gerekirse 1 saatlik parçalara
    # bölünür (2 saat -> 1+1, 2+2+1 -> 1+1+1+1+1).
    if w.cards and optimal_mode:
        from .cpsat import solve_optimal
        mevcut = {i: c.locked_at for i, c in enumerate(w.cards) if c.locked_at is not None}
        for i, c in enumerate(w.cards):
            if i in mevcut: continue
            yer = _kayitli_yer(data_store, w, c)
            if yer is not None: mevcut[i] = yer
        def _ilerle(rec):
            res.diagnostics = res.diagnostics
            if callable(progress):
                progress(rec.get('saat', 0) + locked_hours, res.total_hours, rec.get('tur', 1))
        pos, parcalar, placed, durum, tur = solve_optimal(
            w, rules, referans=mevcut, allow_split=allow_split,
            azami_saniye=azami_saniye, progress=_ilerle, cancelled=cancelled,
            ask_continue=ask_continue, bilinen_ust=gun_ust)
        res.positions = pos
        res.split_pieces = parcalar
        res.status = 'optimal' if durum == 'OPTIMAL' else durum.lower()
        # Son kartlar için derin arama: CP-SAT durgunlaştıysa (278'de kaldıysa)
        # açıkta kalan bir iki kart için tahliye zinciri denenir. Ucuz, ve
        # çoğu zaman tam olarak eksik olan o son saati bulur.
        if durum in ('STALLED', 'FEASIBLE') and any(i < 0 for i in pos) \
                and not (callable(cancelled) and cancelled()):
            try:
                from .finish import Finisher
                fin = Finisher(w, rules, pos, forced=forced, pieces=parcalar)
                yeni, kazanc = fin.run()
                if kazanc > 0:
                    hata, _, _ = validate(w, rules, yeni, bend_rules=completion_first,
                                          forced=forced, pieces=parcalar)
                    if not hata:
                        res.positions = yeni
                        placed += kazanc
                        res.warnings.append(f"Bitirme geçişi {kazanc} saat daha yerleştirdi.")
            except Exception as exc:
                res.warnings.append(f"Bitirme geçişi çalışmadı: {exc}")
        # Açıkta kalan her kart için SAAT düzeyinde sebep: öğretmenin açık
        # saati, sınıfla ORTAK açık saati ve yükü. Gün-seviyesi tanı bunu
        # göremez (kapasite gün gün yeterken saatler örtüşmeyebilir).
        try:
            P_ = w.P
            parca = res.split_pieces or {}
            for i, c in enumerate(w.cards):
                if res.positions[i] >= 0 or i in parca or c.teacher < 0:
                    continue
                ti = c.teacher
                t_open = [cell for cell in range(w.D * P_) if not (w.teacher_closed[ti] >> cell) & 1]
                ortak = [cell for cell in t_open
                         if not any((w.class_closed[ci] >> cell) & 1 for ci in c.classes)]
                yuk = sum(x.duration for x in w.cards if x.teacher == ti)
                gunler = sorted({cell // P_ for cell in ortak})
                res.diagnostics.append(dict(
                    message=(f"Yerleşmedi — {' + '.join(c.class_names)} · {c.subject_name} "
                             f"({c.duration} saat, {c.teacher_name}): öğretmenin haftalık açık saati "
                             f"{len(t_open)}, yükü {yuk} saat; bu sınıfla ORTAK açık saat {len(ortak)} "
                             f"(gün: {', '.join(str(d + 1) for d in gunler) or '-'}). Ortak saatler "
                             f"öğretmenin diğer derslerine gidince bu karta yer kalmıyor; öğretmenin "
                             f"ya da sınıfın tablosunda saat açmak gerekir."),
                    cards=[i], kind='hour_level'))
        except Exception as exc:
            res.warnings.append(f"Saat düzeyi tanı çalışmadı: {exc}")
        if durum == 'STALLED':
            aciklama = "iki tur üst üste ilerleme olmadı, daha fazla beklenmedi"
        elif durum == 'OPTIMAL' and placed < w.total_hours():
            aciklama = ("bu kurallarla daha fazlası mümkün değil (gün-seviyesi kanıt)"
                        if gun_ust is not None and placed >= gun_ust
                        else "bu kurallar ve zaman tablolarıyla daha fazlası mümkün değil (CP-SAT kanıtı)")
        else:
            aciklama = f"CP-SAT {durum}"
        res.warnings.append(
            f"Optimal kip: {tur} tur, {placed + locked_hours}/{res.total_hours} saat, {aciklama}."
            + (f" {len(parcalar)} blok parçalara bölündü." if parcalar else ""))
        return _bitir(res, w, rules, data_store, completion_first, start)

    cozuldu=False
    cp_is=None; cp_sonuc={}
    # ── CP-SAT PARALEL ATIŞ ──
    #
    # Birey'de CP-SAT tam çizelgeyi 0,4 saniyede OPTIMAL olarak buluyor;
    # tabu araması aynı veride 235'te takılıyor. Boğaziçi'de ise tam tersi:
    # CP-SAT süre dolana dek yalnızca FEASIBLE veriyor, tabu 285'e ulaşıyor.
    # Hangisinin kazanacağı veriye bağlı, o yüzden ikisi de çalışır.
    #
    # CP-SAT sıraya konduğunda (önce ya da sonra fark etmez) diğerinin
    # bütçesini yiyordu: başa alınca Boğaziçi 285'ten 273'e düşüyor, sona
    # alınca 3 saniyelik bütçede sırası hiç gelmiyor ve Birey 235'te kalıyordu.
    # Çözüm ikisini yarıştırmak: CP-SAT ayrı bir iş parçacığında koşar
    # (OR-Tools yerel kodda GIL'i bırakır), ana aramanın saati ise kısa
    # yoklamadan SONRA başlar. Böylece tabu bütçesinden tek saniye gitmez.
    if w.cards and use_cpsat:
        import threading
        def _cp_kosu():
            try:
                from .cpsat import solve_cpsat as _c
                # Az iş parçacığı: tabu portföyü 16 çekirdeği kullanıyor,
                # CP-SAT varsayılan 8 işçiyle açılınca ikisi birbirini
                # aç bırakıyor ve Boğaziçi 279'dan 275'e düşüyordu.
                # Kolay örnekleri CP-SAT 2 işçiyle de saniyenin yarısında
                # çözüyor; zor örneklerde zaten kazanan tabu.
                # Bölünmüş kartlar da sonuçtur: parçalar alınmazsa CP-SAT'in
                # 1+1 diye yerleştirdiği kart "yerleşmedi" sayılır ve tam
                # çizelge iki saat eksik görünür.
                parca=[]
                pos,placed,durum=_c(w,rules,seconds=max(1.0,time_budget*0.9),
                                    allow_split=True,workers=2,forced=forced,
                                    pieces_out=parca)
                cp_sonuc['r']=(pos,placed,durum,dict(parca))
            except Exception as exc:
                cp_sonuc['hata']=exc
        cp_is=threading.Thread(target=_cp_kosu,daemon=True); cp_is.start()
        cp_is.join(min(0.6,max(0.2,time_budget*0.25)))
        if 'r' in cp_sonuc:
            pos0,placed0,durum0,parca0=cp_sonuc['r']
            if placed0>=w.total_hours():
                hata0,_,_=validate(w,rules,pos0,bend_rules=completion_first,forced=forced,pieces=parca0)
                if not hata0:
                    res.positions=pos0; res.split_pieces=parca0; cozuldu=True
                    res.warnings.append(f"CP-SAT tam çizelgeyi buldu ({durum0})."
                                        + (f" {len(parca0)} blok parçalara bölündü." if parca0 else ""))
        # Yoklamada harcanan süre ana aramadan düşülmez.
        start=time.monotonic()

    if w.cards and not cozuldu:
        def on_progress(rec):
            if callable(progress): progress(rec['hours'] + locked_hours, res.total_hours, rec['restarts']+1)
        # A proved day-capacity deficit gives a candidate set of absent cards.
        # Try that subset first. It is only a search seed, never a change to the
        # assignment data. If it cannot reach the bound, reopen all cards.
        omitted=set()
        for issue in res.diagnostics:
            omitted.update(issue.get('suggested_unplaced', []))
        omitted={i for i in omitted if w.cards[i].locked_at is None}
        trial=w
        # Tamamlanma öncelikli kipte hiçbir kart aramadan çıkarılmaz.
        # Bu sezgisel, tanıda "yerleşemez" görünen kartı baştan devre dışı
        # bırakıp aramayı hızlandırıyordu; ama kural o grup için esneyebildiği
        # anda o kart yerleşebilir hâle gelir ve devre dışı bırakılmış olması
        # çizelgeyi kendi kendine eksik bırakır.
        if (not completion_first and omitted
                and sum(w.cards[i].duration*len(w.cards[i].classes) for i in omitted)==w.total_hours()-res.upper_bound):
            trial=copy.deepcopy(w)
            for i in omitted: trial.cards[i].slots=()
        problem=Problem(trial,rules,completion_first=completion_first)
        if problem.errors: raise ValueError('\n'.join(problem.errors))
        remaining=max(0,time_budget-(time.monotonic()-start))
        # Bütçenin bir kısmı ikinci aşamaya ayrılır. Birinci aşama süreyi son
        # saniyesine kadar kullanırsa, açıkta kalan kartları yerleştirecek
        # ikinci aşamaya hiç zaman kalmaz ve motor çözebileceği bir çizelgeyi
        # eksik bırakır — sebebi arama gücü değil, bütçe paylaşımıdır.
        # Sıralı ilk arama yalnızca bir başlangıç noktasıdır; asıl gücü
        # paralel şeritler taşır. Bu yüzden ona bütçenin küçük bir dilimi
        # ayrılır, kalanın tamamı şeritlere gider. Daha önce tersiydi:
        # sıralı arama sürenin yarısını alıyor, sekiz şeride toplamda on
        # saniye kalıyordu — yani makinenin yedi çekirdeği boş bekliyordu.
        # Paylaşım kipe bağlı DEĞİLDİR. Sıkı kipte de asıl gücü paralel
        # şeritler taşır; sıralı aramaya bütçenin tamamını vermek makinenin
        # yedi çekirdeğini boş bırakır ve tek bir tohuma mahkûm eder.
        stage1_share=0.18
        # C++ motoru olmayabilir (Windows kurulumunda .exe derlenmemiş
        # olabiliyor). O zaman arama aşaması boş geçilir ve çizelgeyi
        # CP-SAT kurar; planlayıcı hiç açılmamak yerine çalışmaya devam
        # eder.
        def _no_engine(pb):
            return dict(hours=0, steps=0, restarts=0, soft_cost=0,
                        cancelled=False, positions=[-1]*len(pb.world.cards))

        try:
            rec=search(problem,remaining*stage1_share*(0.7 if trial is not w else 1),
                       seed if seed is not None else 20260912,search_target,
                       progress=on_progress,cancelled=cancelled)
        except NativeEngineMissing as exc:
            print(f'[engine] {exc}')
            native_ok=False
            rec=_no_engine(problem)
        else:
            native_ok=True
        if native_ok and trial is not w and rec['hours']<search_target and not rec['cancelled']:
            remaining=max(0,time_budget-(time.monotonic()-start))
            if remaining>0:
                problem=Problem(w,rules,completion_first=completion_first)
                try:
                    retry=search(problem,remaining*stage1_share,(seed if seed is not None else 20260912)+7919,
                                 search_target,progress=on_progress,cancelled=cancelled)
                except NativeEngineMissing:
                    retry=rec
                if retry['hours']>rec['hours']: rec=retry
        res.positions=rec['positions'];res.steps=rec['steps'];res.attempts=rec['restarts']+1
        res.soft_cost=rec['soft_cost']
        res.status='cancelled' if rec['cancelled'] else 'timeout'

        # ── PARALEL ÇOK TOHUMLU PORTFÖY ──
        #
        # Tek tohumla daha uzun beklemek yerel vadiden çıkarmaz; başka tohumla
        # baştan başlamak çıkarır. Tohumları sırayla denemek bu şansı süreye
        # böler — paralel denemek bölmez, çünkü arama zaten ayrı süreçte koşar.
        # Sonuç, "hangi tohumu seçtim" sorusunun sonucu belirlemekten çıkması.
        base_seed=seed if seed is not None else 20260912
        # Tek bir tohum kuşağı yetmeyebilir: şeritler aynı taban tohumdan
        # türediği için hepsi birden şanssız düşebilir. Süre bittikçe yeni
        # kuşaklar denenir; her kuşak tamamen farklı bir tohum ailesinden
        # başlar. İlk tam çizelge bulunduğunda döngü hemen biter.
        pr=Problem(w,rules,completion_first=completion_first)
        generation=0
        # Tabu turlarina butcenin en fazla YARISI verilir; kalan yari CP-SAT'e
        # ayrilir. Olcum bunu gerektirdi: v190'da tabu 283'te plato yapiyor,
        # son iki saati CP-SAT buluyor. Tabu butcenin sonuna kadar kosarsa
        # CP-SAT'e zaman kalmiyor ve cizelge, cozulebilir oldugu halde eksik
        # bitiyor — kullanicinin gordugu 284/285 tam olarak buydu.
        tabu_deadline = start + time_budget * 0.5
        while (rec['hours']<search_target and not rec['cancelled'] and generation<40):
            left=min(time_budget-(time.monotonic()-start),
                     tabu_deadline-time.monotonic())
            if left<=1.0: break
            generation+=1
            lanes=max(2,(os.cpu_count() or 4))
            # Kuşak SÜRESİ kısa tutulur. Ölçüm şunu gösteriyor: bir tohum
            # başaracaksa ilk saniyelerde başarıyor; başaramayacaksa ne kadar
            # beklenirse beklensin başaramıyor. Uzun kuşak, ölmüş bir tohumun
            # başında bekleyip diğer tohumlara sıra gelmesini engelliyor.
            # Kısa kuşak aynı sürede kat kat fazla tohum dener.
            span=min(left*0.92,max(3.0,time_budget*0.12))
            seeds=[base_seed*generation+k*15485863+generation*2654435761
                   for k in range(1,lanes+1)]
            try:
                alt=search_portfolio(pr,span,seeds,search_target,
                                     progress=on_progress,cancelled=cancelled)
            except NativeEngineMissing as exc:
                # Motor yok (ör. Windows kurulumunda .exe derlenmemiş):
                # arama aşaması atlanıyor, CP-SAT eldeki sonucu sürdürüyor.
                print(f'[engine] {exc}')
                break
            res.steps+=alt['steps'];res.attempts+=alt['restarts']+1
            if alt['hours']>rec['hours'] or (alt['hours']==rec['hours']
                                             and alt['soft_cost']<rec['soft_cost']):
                rec=alt
                res.positions=alt['positions'];res.soft_cost=alt['soft_cost']

        # ── AŞAMA 2: tamamlanma önceliği ──
        #
        # Birinci aşama kuralları harfiyen uygular ve kuralların izin verdiği
        # en dolu çizelgeyi bulur. Geriye ders kalıyorsa sebebi çoğu zaman
        # aramanın yetersizliği değil, aritmetiğin kendisidir: v188'de 9A
        # Matematik dersi üç ayrı karta bölünmüş ama öğretmeni haftada yalnızca
        # iki gün okulda. Üç kartı üç ayrı güne koymak hiçbir çizelgede mümkün
        # değil.
        #
        # Böyle bir durumda dersi boş bırakmak, kuralı korumaktan daha pahalı
        # bir karardır: o saat okulda gerçekten yapılmayacak demektir. Bu
        # yüzden ikinci aşama devreye girer — ama körlemesine değil.
        #
        # Birinci aşamanın yerleştirdiği HER KART OLDUĞU YERE KİLİTLENİR ve
        # arama yalnızca açıkta kalan kartlar için tekrar çalışır. Böylece
        # kurallar yalnızca o kartların gerektirdiği kadar, en az sayıda ve
        # yalnızca gereken noktada esner; geri kalan çizelge birinci aşamanın
        # kusursuz hâliyle kalır. Esnetilen her nokta rapora yazılır.
        if completion_first and any(i<0 for i in res.positions):
            remaining=max(0,time_budget-(time.monotonic()-start))
            if remaining>0.5:
                locked=copy.deepcopy(w)
                for card,idx in zip(locked.cards,res.positions):
                    if idx>=0:
                        d0,p0=divmod(idx,locked.P)
                        card.slots=((idx,locked.footprint(d0,p0,card.duration)),)
                stage2=Problem(locked,rules,completion_first=True)
                if not stage2.errors:
                    rec2=_safe_search(stage2,remaining,
                                (seed if seed is not None else 20260912)+104729,
                                search_target,progress=on_progress,cancelled=cancelled)
                    placed1=sum(c.duration*len(c.classes)
                                for c,i in zip(w.cards,res.positions) if i>=0)
                    placed2=sum(c.duration*len(c.classes)
                                for c,i in zip(w.cards,rec2['positions']) if i>=0)
                    if placed2>placed1:
                        errs2,_,_=validate(w,rules,rec2['positions'],bend_rules=True,forced=forced)
                        if not errs2:
                            res.positions=rec2['positions']
                            res.steps+=rec2['steps']
                            res.attempts+=rec2['restarts']+1
    # ── CP-SAT BİTİRİCİ ──
    #
    # Tabu araması çizelgenin tamamına hızla yaklaşır ama son bir iki kartta
    # takılır: her adımda tek kart oynattığı için, ancak üç dört kartın
    # birlikte kaymasıyla ulaşılabilen çözümleri göremez. v188'de 60 saniye
    # ile 180 saniye aynı sonucu veriyordu — sorun süre değil, hamlenin
    # kendisi.
    #
    # CP-SAT tam bu boşluğu doldurur; kartların hepsini aynı anda değerlendirir
    # ve "şu kart şuraya giderse şu üçü şöyle kayar" türü çıkarımları kendisi
    # yapar. Tabu sonucu ipucu olarak verilir: sıfırdan aramak yerine eldeki
    # çizelgeyi doğrulayıp üstüne çıkmaya odaklanır.
    #
    # Sonuç yalnızca DAHA İYİYSE ve denetimden geçerse alınır; CP-SAT'in
    # bulduğu bir çizelge, ana aramanınkini hiçbir koşulda kötüleştiremez.
    if use_cpsat and not cozuldu and any(i < 0 for i in res.positions):
        # Paralel CP-SAT hâlâ koşuyor olabilir; kalan bütçe kadar beklenir.
        # Sonuç yalnızca DAHA İYİYSE ve denetimden geçerse alınır — CP-SAT'in
        # çizelgesi ana aramanınkini hiçbir koşulda kötüleştiremez.
        if cp_is is not None:
            cp_is.join(max(0.0, time_budget - (time.monotonic() - start)))
        if 'hata' in cp_sonuc:
            res.warnings.append(f"CP-SAT çalışmadı: {cp_sonuc['hata']}")
        elif 'r' in cp_sonuc:
            pos2, placed2, durum, parca2 = cp_sonuc['r']
            placed1 = sum(c.duration * len(c.classes)
                          for c, i in zip(w.cards, res.positions) if i >= 0)
            if placed2 > placed1:
                hata, _, _ = validate(w, rules, pos2, bend_rules=completion_first,
                                      forced=forced, pieces=parca2)
                if not hata:
                    res.positions = pos2
                    res.split_pieces = parca2
                    res.warnings.append(
                        f"CP-SAT {placed2 - placed1} saat daha yerleştirdi ({durum})."
                        + (f" {len(parca2)} blok parçalara bölündü." if parca2 else ""))
            elif durum == "OPTIMAL" and placed2 == placed1:
                res.warnings.append(
                    "CP-SAT bu kurallarla daha fazlasının mümkün olmadığını kanıtladı.")

    # ── BİTİRME GEÇİŞİ ──
    #
    # Tabu araması her adımda TEK kart oynatır. Son kartın yerleşmesi için
    # çoğu zaman üç dört kartın birlikte kayması gerekir ve böyle bir hamle,
    # tek kartlık adımların hiçbir dizilişinde ara durumu kötüleştirmeden
    # görünmez. v188'de 60 saniye ile 180 saniye aynı sonucu veriyordu: sorun
    # süre değil, hamlenin kendisiydi.
    #
    # Bu geçiş yalnızca açıkta kalan kartları hedefler ve onlar için tüketici
    # arama yapar — alan küçük olduğu için hesaplı. Ana aramanın çizelgesini
    # bozmaz: dal tutmazsa her şey birebir eski hâline döner.
    if not cozuldu and any(i < 0 for i in res.positions):
        try:
            from .finish import Finisher
            fin = Finisher(w, rules, res.positions, forced=forced,
                           pieces=getattr(res, 'split_pieces', None))
            yeni, kazanc = fin.run()
            if kazanc > 0:
                hata, _, _ = validate(w, rules, yeni, bend_rules=completion_first,
                                      forced=forced, pieces=getattr(res, 'split_pieces', None))
                if not hata:
                    res.positions = yeni
                    res.warnings.append(f"Bitirme geçişi {kazanc} saat daha yerleştirdi.")
        except Exception as exc:
            res.warnings.append(f"Bitirme geçişi çalışmadı: {exc}")

    return _bitir(res,w,rules,data_store,completion_first,start)
