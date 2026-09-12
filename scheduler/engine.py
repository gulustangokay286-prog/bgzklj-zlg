"""Public entry point: snapshot -> rules -> native search -> independent audit."""
import time
import copy
import os
from .build import build_world, attach_slots
from .rules import compile_rules
from .problem import Problem
from .diagnostics import diagnose
from .native_bridge import search, search_portfolio
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
    """Bind saved blocks to demand cards; never silently discard a requested lock."""
    used=set()
    # Combined lessons produce one display row per class. Identical rows refer
    # to the same atomic card and must not consume another teacher/card.
    for pl in placements:
        if not (pl.get('locked') or pl.get('pinned')): continue
        cn=norm_class(pl.get('class_name') or pl.get('class'))
        sn=norm_key(pl.get('subject_name') or pl.get('subject'))
        tn=norm_key(pl.get('teacher_name') or pl.get('teacher'))
        d=int(pl.get('day',pl.get('col',0)));p=int(pl.get('period',pl.get('row',0)))
        dur=int(pl.get('duration') or 1);idx=d*world.P+p
        candidates=[c for c in world.cards if cn in {norm_class(x) for x in c.class_names}
                    and norm_key(c.subject_name)==sn and norm_key(c.teacher_name)==tn
                    and c.duration==dur]
        if any(c.locked_at==idx for c in candidates): continue
        c=next((c for c in candidates if c.cid not in used),None)
        if c is None:
            raise ValueError(f"Kilitli yerleşim atama dağılımıyla eşleşmiyor: {pl.get('class_name') or pl.get('class')} · {pl.get('subject_name') or pl.get('subject')}")
        if not (0<=d<world.D and 0<=p and p+dur<=world.P):
            raise ValueError('Kilitli yerleşim gün/saat sınırını aşıyor')
        c.locked_at=idx;used.add(c.cid)




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
    errors,soft,bent=validate(w,rules,res.positions,bend_rules=completion_first)
    if errors:
        raise RuntimeError('Çizelge son denetimden geçmedi; sonuç uygulanmadı:\n'+'\n'.join(errors[:12]))
    res.warnings.extend(soft)
    if res.status!='cancelled':
        res.status='complete' if res.placed_hours==res.total_hours else 'timeout'
    # Bu notlar KURAL İHLALİ DEĞİLDİR.
    #
    # "Aynı ders aynı gün tekrar etmesin" bir dersin kartlarını ayrı günlere
    # dağıtmayı ister. Bir dersin kart sayısı, o dersi veren öğretmenin okulda
    # olduğu gün sayısını aşıyorsa bu istek hiçbir çizelgede karşılanamaz:
    # 9A Matematik beş saat, bloklar en fazla iki saat olabildiği için en az
    # üç kart, öğretmen ise haftada iki gün okulda. Üç kartı iki güne koymak
    # zorunludur; alternatifi dersin hiç yapılmamasıdır.
    #
    # Programın ilk motoru da bu kuralı hep böyle uygulamıştı: gün sayısı
    # yetiyorsa günde bir, yetmiyorsa tavan ceil(kart/gün). Kuralın anlamı
    # "gün sayısının elverdiği ölçüde en fazla bir kez"dir. Aritmetiğin
    # dayattığı taban, kuralın ihlali değil uygulanabilir en sıkı hâlidir.
    #
    # Bu yüzden bu durumlar ihlal sayılmaz; nerede ve neden oluştuğu rapora
    # bilgi notu olarak yazılır, kullanıcı isterse öğretmenin gününü açarak
    # tabanı bire indirir.
    res.forced_minimums=bent
    res.bent_rules=[]
    for b in bent:
        res.warnings.append('ARİTMETİK TABAN — '+b+
                            ' (bu ders için mümkün olan en az tekrar)')
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
                locked=c.locked_at is not None,is_manual=c.locked_at is not None,is_filler=False,
                color=original.get('color') or original.get('renk')))
    if res.complete: res.status='complete'
    elif res.diagnostics and res.status!='cancelled': res.status='infeasible'
    res.elapsed=time.monotonic()-start
    return res


def solve(data_store, time_budget=10.0, D=None, P=None, cross_busy=None,
          only_classes=None, seed=None, max_attempts=6, progress=None,
          relations=None, cancelled=None, completion_first=True, use_cpsat=True,
          optimal_mode=False, allow_split=True, azami_saniye=3600.0):
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
    locked=[pl for pl in data_store.get('grid_placements',[]) if not only_classes or
            norm_class(pl.get('class_name') or pl.get('class')) in {norm_class(x) for x in only_classes}]
    bind_locks(w,locked)
    attach_slots(w,rules)
    res.world=w;res.rules=rules;res.warnings=list(report.warnings)
    res.total_hours=w.total_hours();res.positions=[-1]*len(w.cards)
    res.diagnostics,res.upper_bound=diagnose(w,rules)
    # diagnose(), kuralların DELİNEMEZ olduğunu varsayarak bir üst sınır
    # hesaplar: v188'de 9A Matematik'in üç kartı iki güne sığmadığı için bu
    # sınır 284 çıkar. Bu sayı tanı olarak doğrudur ama ARAMA HEDEFİ olarak
    # yanlıştır: tamamlanma öncelikli kipte o kural, tam olarak bu grup için
    # ve gereken en az ölçüde esneyebilir, dolayısıyla 285 ulaşılabilir.
    #
    # Sınır hedef olarak kullanıldığında çekirdek 284'e varınca "bitti" deyip
    # duruyordu; son saat, aranmadığı için değil, aranmasına izin verilmediği
    # için boş kalıyordu. Rapor eski sınırı göstermeye devam eder, arama ise
    # gerçek hedefi kovalar.
    search_target=res.total_hours if completion_first else res.upper_bound
    res.warnings.extend(x['message'] for x in res.diagnostics)
    for c in w.cards:
        if c.locked_at is not None and not c.slots:
            raise ValueError(f"Kilitli kart kapalı saate veya planlama kuralına aykırı: {c}")
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
                progress(rec.get('saat', 0), res.total_hours, rec.get('tur', 1))
        pos, parcalar, placed, durum, tur = solve_optimal(
            w, rules, referans=mevcut, allow_split=allow_split,
            azami_saniye=azami_saniye, progress=_ilerle, cancelled=cancelled)
        res.positions = pos
        res.split_pieces = parcalar
        res.status = 'optimal' if durum == 'OPTIMAL' else durum.lower()
        res.warnings.append(
            f"Optimal kip: {tur} tur, {placed}/{res.total_hours} saat, CP-SAT {durum}."
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
                cp_sonuc['r']=_c(w,rules,seconds=max(1.0,time_budget*0.9),
                                 allow_split=True,workers=2)
            except Exception as exc:
                cp_sonuc['hata']=exc
        cp_is=threading.Thread(target=_cp_kosu,daemon=True); cp_is.start()
        cp_is.join(min(0.6,max(0.2,time_budget*0.25)))
        if 'r' in cp_sonuc:
            pos0,placed0,durum0=cp_sonuc['r']
            if all(i>=0 for i in pos0):
                hata0,_,_=validate(w,rules,pos0,bend_rules=completion_first)
                if not hata0:
                    res.positions=pos0; cozuldu=True
                    res.warnings.append(f"CP-SAT tam çizelgeyi buldu ({durum0}).")
        # Yoklamada harcanan süre ana aramadan düşülmez.
        start=time.monotonic()

    if w.cards and not cozuldu:
        def on_progress(rec):
            if callable(progress): progress(rec['hours'],res.total_hours,rec['restarts']+1)
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
                and sum(w.cards[i].duration*len(w.cards[i].classes) for i in omitted)==res.total_hours-res.upper_bound):
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
        rec=search(problem,remaining*stage1_share*(0.7 if trial is not w else 1),
                   seed if seed is not None else 20260912,search_target,
                   progress=on_progress,cancelled=cancelled)
        if trial is not w and rec['hours']<search_target and not rec['cancelled']:
            remaining=max(0,time_budget-(time.monotonic()-start))
            if remaining>0:
                problem=Problem(w,rules,completion_first=completion_first)
                retry=search(problem,remaining*stage1_share,(seed if seed is not None else 20260912)+7919,
                             search_target,progress=on_progress,cancelled=cancelled)
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
            alt=search_portfolio(pr,span,seeds,search_target,
                                 progress=on_progress,cancelled=cancelled)
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
                    rec2=search(stage2,remaining,
                                (seed if seed is not None else 20260912)+104729,
                                search_target,progress=on_progress,cancelled=cancelled)
                    placed1=sum(c.duration*len(c.classes)
                                for c,i in zip(w.cards,res.positions) if i>=0)
                    placed2=sum(c.duration*len(c.classes)
                                for c,i in zip(w.cards,rec2['positions']) if i>=0)
                    if placed2>placed1:
                        errs2,_,_=validate(w,rules,rec2['positions'],bend_rules=True)
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
            pos2, placed2, durum = cp_sonuc['r']
            placed1 = sum(c.duration * len(c.classes)
                          for c, i in zip(w.cards, res.positions) if i >= 0)
            if placed2 > placed1:
                hata, _, _ = validate(w, rules, pos2, bend_rules=completion_first)
                if not hata:
                    res.positions = pos2
                    res.warnings.append(
                        f"CP-SAT {placed2 - placed1} saat daha yerleştirdi ({durum}).")
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
            fin = Finisher(w, rules, res.positions)
            yeni, kazanc = fin.run()
            if kazanc > 0:
                hata, _, _ = validate(w, rules, yeni, bend_rules=completion_first)
                if not hata:
                    res.positions = yeni
                    res.warnings.append(f"Bitirme geçişi {kazanc} saat daha yerleştirdi.")
        except Exception as exc:
            res.warnings.append(f"Bitirme geçişi çalışmadı: {exc}")

    return _bitir(res,w,rules,data_store,completion_first,start)
