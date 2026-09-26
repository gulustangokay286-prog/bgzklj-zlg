"""Adapter for the existing Qt dialog and cross-institution availability helpers."""
import copy
from collections import defaultdict
from .engine import solve
from .model import norm_class


def hazirla(data_store, target_class=None, institution_slug=None):
    """Planlamanın girdisi: veri kopyası, boyutlar, sınıflar, dış meşguliyet.

    run_worker ve planlama öncesi kilit denetimi AYNI girdiyi buradan alır;
    ön kontrolün gördüğü dünya motorun göreceği dünyanın birebir aynısıdır.
    """
    import constraint_sync
    from auto_scheduler import _build_teacher_timeoff_map, norm_teacher, matches_class
    data=copy.deepcopy(data_store)
    D,P=constraint_sync.grid_dimensions(data)
    names=[c.get('ad') or c.get('name') for c in data.get('siniflar',[])]
    selected=names if not target_class else [n for n in names if matches_class(n,target_class)]
    if not selected: raise ValueError('Planlanacak sınıf bulunamadı')
    if not data.get('atamalar'): raise ValueError('Herhangi bir ders ataması bulunamadı.')
    # Expand a target to all members of a combined lesson.
    import lesson_hours
    for _ in names:
        changed=False
        for a in data.get('atamalar',[]):
            members=lesson_hours.classes(a)
            if any(matches_class(n,m) for n in selected for m in members):
                for n in names:
                    if n not in selected and any(matches_class(n,m) for m in members):
                        selected.append(n);changed=True
        if not changed: break
    # ÇAPRAZ KURUM MOTORA HİÇ SORULMAZ. Kurumlar bağımsızdır
    # (constraint_sync.INSTITUTIONS_INDEPENDENT): başka kurumdaki ders,
    # rezervasyon ya da yayınlanmış kısıt bu çizelgeyi bağlamaz. Eskiden bu
    # veriler okunup öğretmenin meşguliyetine ekleniyordu; diğer kurumun ESKİ
    # aktif sürümü yüzünden burada saatler kapalı görünüyordu.
    closed,avoid=_build_teacher_timeoff_map(data,institution_slug,include_shared=False)
    cross={}
    others=[]
    selected_keys={norm_class(n) for n in selected}
    for pl in data.get('grid_placements',[]):
        if norm_class(pl.get('class_name') or pl.get('class')) in selected_keys: continue
        others.append(pl)
        key=norm_teacher(pl.get('teacher_name') or pl.get('teacher'))
        d=int(pl.get('day',pl.get('col',0)));p=int(pl.get('period',pl.get('row',0)))
        for off in range(int(pl.get('duration') or 1)): cross.setdefault(key,set()).add((d,p+off))
    # Öğretmenin KENDİ zaman tablosuna dokunulmaz.
    #
    # Burada eskiden çapraz kurum kısıtları ve paylaşılan öğretmen saatleri
    # doğrudan t['timeoff'] içine yazılıyordu. Sonuç kaydedildiğinde o saatler
    # öğretmenin kalıcı müsaitliği hâline geliyor ve bir daha geri gelmiyordu:
    # planlayıcı her çalıştığında zaman tablosu biraz daha daralıyordu.
    # Birey'de tam olarak bu oldu — 10 Eylül'de 237/237 oturan çizelgenin
    # kullandığı 35 saat, üç PAYLAŞILAN öğretmende (Mesut Çolak, Niyazi Kaya,
    # Muharrem Yavuz) kapanmıştı; kapananların hepsinin paylaşılan hocalar
    # olması da sebebin bu birleştirme olduğunu gösteriyor.
    #
    # Doğrusu: kısıtlar çözücüye AYRI bir parametre olarak verilir, kullanıcının
    # verisine yazılmaz. Zaman tablosunu yalnızca kullanıcı değiştirir.
    # Öğretmenin KENDİ kaydına hiçbir şey yazılmaz — kopyaya bile. Motor
    # müsaitliği constraint_sync.get_matrix ile okur; buradaki tek iş, aynı
    # kurumun başka sınıflarındaki yerleşimlerden doğan meşguliyeti AYRI bir
    # parametre olarak toplamaktır.
    engel={}
    for t in data.get('ogretmenler',[]):
        name=t.get('ad') or t.get('name');key=norm_teacher(name)
        ek=closed.get(key,set()) | cross.get(key,set())
        if ek: engel[name]={(d,p) for d,p in ek if 0<=d<D and 0<=p<P}
    return data,D,P,selected,engel,others


def kilit_catismalari(data_store, target_class=None, institution_slug=None):
    """Planlamadan ÖNCE: veriyle ya da birbiriyle çelişen kilitli dersler.

    Boş liste = kilitler tutarlı. Her öğe dict(mesaj, neden, ids, ...).
    """
    from .engine import kilit_catismalari_verisi
    data,D,P,selected,engel,_=hazirla(data_store,target_class,institution_slug)
    return kilit_catismalari_verisi(data,D=D,P=P,cross_busy=engel,only_classes=selected)


def run_worker(worker):
    data,D,P,selected,engel,others=hazirla(worker.data_store,worker.target_class,
                                           worker.institution_slug)
    def progress(hours,total,attempt):
        worker.progress_updated.emit(hours,total)
        worker.iteration_updated.emit(attempt,0,hours)
    # OPTİMAL KİP — worker üzerinde açıksa süre hedef değil emniyet sübabıdır:
    # motor CP-SAT'in OPTIMAL kanıtını bekler, kanıt gelince durur. Bloklar
    # gerekirse 1 saatlik parçalara bölünür ve ikinci aşamada mevcut tablodan
    # en az sapmayı veren çözüm seçilir.
    optimal=bool(getattr(worker,'optimal_mode',False))
    result=solve(data,D=D,P=P,only_classes=selected,cross_busy=engel,
                 time_budget=3.0,   # normal kipte tavan; motor tam çizelgeyi bulunca erken durur
                 optimal_mode=optimal,
                 allow_split=bool(getattr(worker,'allow_split',True)),
                 azami_saniye=float(getattr(worker,'azami_saniye',3600.0)),
                 progress=progress,cancelled=lambda:not worker._is_running,
                 ask_continue=getattr(worker,'ask_continue',None),
                 # Kullanıcı ön kontrolde "çelişen kilitleri çöz" dediyse.
                 unlock_conflicting_locks=bool(getattr(worker,'unlock_conflicting_locks',False)))
    per_key=defaultdict(int)
    for x in result.unplaced: per_key[x['class'],x['subject'],x['teacher']]+=x['hours']
    unplaced=[dict(**{'class':cn},subject=subj,teacher=tch,hours=h)
              for (cn,subj,tch),h in per_key.items()]
    if worker.independent_classes:
        for pl in result.placements:
            pl['needs_review']=True
    schedule=others+result.placements
    # Legacy total_hours remains available cell capacity; progress and completeness
    # use actual assignment demand, so an intentionally short week is complete.
    capacity=sum(result.world.class_capacity[i] for i,n in enumerate(result.world.classes) if n in selected)
    worker.finished_successfully.emit(dict(schedule=schedule,placements=schedule,
        placed_hours=result.placed_hours,placed_real_hours=result.placed_hours,
        total_hours=capacity,total_assigned_hours=result.total_hours,
        status=result.status,complete=result.complete,engine='native-cpp',
        upper_bound=result.upper_bound,diagnostics=result.diagnostics,warnings=result.warnings,
        constraint_violations=[],cross_conflicts=[],understaffed_slots=[],capacity_problems=[],teacher_clashes=[],
        unplaced_summary=unplaced,unplaced_cards=result.unplaced,
        elapsed_seconds=round(result.elapsed,3)))
