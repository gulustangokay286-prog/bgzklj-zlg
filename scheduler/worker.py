"""Adapter for the existing Qt dialog and cross-institution availability helpers."""
import copy
from collections import defaultdict
from .engine import solve
from .model import norm_class


def run_worker(worker):
    import constraint_sync
    from auto_scheduler import (_build_teacher_timeoff_map, _build_cross_institution_map,
                                _merge_foreign_teacher_slots, norm_teacher, matches_class)
    data=copy.deepcopy(worker.data_store)
    D,P=constraint_sync.grid_dimensions(data)
    names=[c.get('ad') or c.get('name') for c in data.get('siniflar',[])]
    selected=names if not worker.target_class else [n for n in names if matches_class(n,worker.target_class)]
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
    closed,avoid=_build_teacher_timeoff_map(data,worker.institution_slug,
                                           include_shared=not worker.ignore_other_institutions)
    cross={}
    if worker.institution_slug and not worker.ignore_other_institutions:
        cross,_=_build_cross_institution_map(worker.institution_slug)
        for key,slots in constraint_sync.reserved_by_others(worker.institution_slug).items():
            cross.setdefault(key,set()).update(slots)
        cross=_merge_foreign_teacher_slots(data,cross)
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
    engel={}
    for t in data.get('ogretmenler',[]):
        name=t.get('ad') or t.get('name');key=norm_teacher(name)
        t['timeoff']=constraint_sync.get_matrix(t,name,data)
        ek=closed.get(key,set()) | cross.get(key,set())
        if ek: engel[name]={(d,p) for d,p in ek if 0<=d<D and 0<=p<P}
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
                 progress=progress,cancelled=lambda:not worker._is_running)
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
