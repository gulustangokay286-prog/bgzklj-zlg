"""Native engine contract tests. No institution files are modified."""
import copy
import os
import time
import unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from scheduler import solve,build_world,attach_slots,compile_rules
from scheduler.verify import validate
from scheduler.native_bridge import native_binary
from scheduler import rules as R


def rule(name,**kw):
    return dict(kural=name,aktif=True,onem='Sıkı (Kesinlikle uygulanmalı)',**kw)


def store(parts='2+1',D=3,P=4):
    return dict(settings=dict(days=['Pzt','Sal','Çar','Per','Cum'][:D],periods=P),
        siniflar=[{'ad':'9A'},{'ad':'9B'}],ogretmenler=[{'ad':'Öğretmen A'},{'ad':'Öğretmen B'}],
        dersler=[{'ad':'Matematik'},{'ad':'Geometri'}],
        atamalar=[dict(**{'class':'9A'},subject='Matematik',teacher='Öğretmen A',type=parts)],
        grid_placements=[],planlama_iliskileri=[])

class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): native_binary()

    def run_valid(self,data,**kw):
        before=copy.deepcopy(data)
        r=solve(data,time_budget=1,seed=17,**kw)
        self.assertEqual(data,before,'solver mutated input')
        self.assertTrue(r.valid)
        self.assertEqual(r.placed_hours+sum(c['hours'] for c in r.unplaced),r.total_hours)
        # Aritmetik taban dışında hiçbir sert kural esnemez.
        bend=kw.get('completion_first',True)
        self.assertEqual(validate(r.world,r.rules,r.positions,bend_rules=bend,
                                  pieces=r.split_pieces)[0],[])
        return r

    def run_strict(self,data,**kw):
        """Tamamlanma önceliği KAPALI: kural aritmetik taban için bile esnemez."""
        return self.run_valid(data,completion_first=False,**kw)

    def test_inactive_rule_is_not_reintroduced(self):
        d=store('1+1',D=1);d['planlama_iliskileri']=[dict(kural='Aynı ders aynı gün tekrar etmesin',aktif=False)]
        r=self.run_valid(d);self.assertTrue(r.complete);self.assertEqual(r.placed_hours,2)
        self.assertFalse(any(x.kind==R.X_SUBJECT_ONCE_DAY for x in r.rules))

    def test_adjacent_repeat_is_allowed(self):
        """1+1 YAN YANA gelebilir: bitişik iki kart tekrar değil, tek bloktur.

        Kural gün içinde AYRI AYRI iki oturumu engeller; öğrenci dersi iki saat
        arka arkaya görüyorsa bu tek oturumdur ve yasak değildir.
        """
        d=store('1+1',D=1);d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin')]
        r=self.run_strict(d);self.assertTrue(r.complete);self.assertEqual(r.placed_hours,2)
        per=sorted(x['period'] for x in r.placements)
        self.assertEqual(per[1]-per[0],1,f'kartlar bitişik değil: {per}')
        self.assertEqual(validate(r.world,r.rules,r.positions)[0],[])

    def test_separate_sessions_on_same_day_still_forbidden(self):
        """Bitişik olmayan iki kart hâlâ yasak: araya başka ders girerse tekrar olur."""
        d=store('1+1',D=1,P=4)
        w=build_world(d);rules,_=compile_rules([rule('Aynı ders aynı gün tekrar etmesin')],w)
        attach_slots(w,rules)
        self.assertTrue(validate(w,rules,[0,2])[0], 'araları açık iki kart ihlal sayılmalı')
        self.assertEqual(validate(w,rules,[0,1])[0], [], 'bitişik iki kart serbest olmalı')

    def test_arithmetic_floor_bends_only_the_impossible_group(self):
        # 9A Matematik iki kart, tek gün: kural bu grupta esner ve rapora yazılır.
        # 9B Matematik iki kart, iki günü var: kural orada ESNEMEZ.
        # Tek gün + 1+1: kartlar BİTİŞİK yerleşir, kural esnemeye gerek kalmaz.
        d=store('1+1',D=1);d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin')]
        r=self.run_valid(d);self.assertTrue(r.complete)
        per=sorted(x['period'] for x in r.placements)
        self.assertEqual(per[1]-per[0],1)
        # Üç kart tek güne sığmıyor (bitişik bile olsa gün 4 saat): esneme burada.
        d3=store('1+1+1',D=1,P=3)
        d3['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin'),
                                   rule('Aynı ders art arda gelmesin')]
        r3=self.run_valid(d3)
        self.assertTrue(r3.forced_minimums or not r3.complete)
        d2=store('1+1',D=2)
        d2['atamalar'].append(dict(**{'class':'9B'},subject='Matematik',teacher='Öğretmen B',type='1+1'))
        d2['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin')]
        r2=self.run_valid(d2);self.assertTrue(r2.complete);self.assertEqual(r2.forced_minimums,[])
        for cn in ('9A','9B'):
            yer=sorted((x['day'], x['period']) for x in r2.placements if x['class']==cn)
            # Kural esnemedi: kartlar ya AYRI GÜNLERDE ya da aynı gün BİTİŞİK.
            if yer[0][0] == yer[1][0]:
                self.assertEqual(yer[1][1]-yer[0][1], 1, f'{cn}: aynı gün ama bitişik değil {yer}')
            else:
                self.assertNotEqual(yer[0][0], yer[1][0])

    def test_double_block_counts_as_one_session(self):
        """2 saatlik blok tek oturumdur; 2+1 aynı güne BİTİŞİK de konabilir."""
        d=store('2+1');d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin')]
        r=self.run_valid(d);self.assertTrue(r.complete)
        self.assertEqual(sorted(x['duration'] for x in r.placements),[1,2])
        by_day={}
        for x in r.placements:
            by_day.setdefault(x['day'],[]).append((x['period'],x['duration']))
        for d_, lst in by_day.items():
            if len(lst)>1:
                lst.sort()
                for (p0,du0),(p1,_) in zip(lst,lst[1:]):
                    self.assertEqual(p0+du0,p1,f'aynı gündeki kartlar bitişik değil: {lst}')

    def test_teacher_rule_in_same_class_only(self):
        d=store('1');d['atamalar'] += [dict(**{'class':cn},subject='Geometri',teacher='Öğretmen A',type='1') for cn in ['9A','9B']]
        d['planlama_iliskileri']=[rule('Aynı öğretmen aynı gün tekrar etmesin')]
        r=self.run_valid(d);self.assertTrue(r.complete)
        self.assertEqual(len({x['day'] for x in r.placements if x['class']=='9A'}),2)

    def test_rule_filters_do_not_leak(self):
        d=store('1+1',D=1)
        d['atamalar'].append(dict(**{'class':'9B'},subject='Matematik',teacher='Öğretmen B',type='1+1'))
        d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin',siniflar=['9A'])]
        r=self.run_strict(d);self.assertEqual(r.placed_hours,4)
        self.assertEqual(sum(x['duration'] for x in r.placements if x['class']=='9B'),2)
        # 9A'nın iki kartı bitişik (kural bunu serbest bırakır), 9B'de kural yok.
        pa=sorted(x['period'] for x in r.placements if x['class']=='9A')
        self.assertEqual(pa[1]-pa[0],1)

    # ── Ders grupları: "Seçilen dersler aynı ders sayılsın" ──
    def _group_store(self,D=3,P=4):
        d=store('1',D=D,P=P)
        d['dersler']=[{'ad':'Mat1'},{'ad':'Mat2'},{'ad':'Geometri'}]
        d['atamalar']=[dict(**{'class':'9A'},subject='Mat1',teacher='Öğretmen A',type='1'),
                       dict(**{'class':'9A'},subject='Mat2',teacher='Öğretmen B',type='1')]
        return d

    def test_group_makes_two_names_one_subject_for_once_day(self):
        d=self._group_store(D=2)
        d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin'),
                                  rule('Seçilen dersler aynı ders sayılsın',dersler=['Mat1','Mat2'])]
        r=self.run_valid(d);self.assertTrue(r.complete)
        self.assertEqual(len({x['day'] for x in r.placements}),2)
        self.assertEqual(r.world.families[r.world.subject_family[0]],'Mat1 / Mat2')

    def test_without_group_two_names_may_share_a_day(self):
        d=self._group_store(D=1)
        d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin')]
        r=self.run_strict(d);self.assertTrue(r.complete)

    def test_group_expands_rule_subject_filter(self):
        # Kuralda yalnızca Mat1 seçili; grup Mat2'yi de kapsama alır.
        d=self._group_store(D=1)
        d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin',dersler=['Mat1']),
                                  rule('Seçilen dersler aynı ders sayılsın',dersler=['Mat1','Mat2']),
                                  rule('Aynı ders art arda gelmesin',dersler=['Mat1'])]
        # Grup Mat2'yi de kapsama alır: "art arda gelmesin" ile birlikte ikisi
        # ne aynı saate bitişik ne de ayrı oturum olarak aynı güne konabilir.
        r=self.run_strict(d);self.assertEqual(r.placed_hours,1)

    def test_group_with_single_subject_is_skipped_with_reason(self):
        d=self._group_store(D=1)
        d['planlama_iliskileri']=[rule('Seçilen dersler aynı ders sayılsın',dersler=['Mat1'])]
        r=self.run_valid(d);self.assertTrue(r.complete)
        self.assertTrue(any('UYGULANMADI' in x for x in r.warnings))

    def test_inactive_group_has_no_effect(self):
        d=self._group_store(D=1)
        d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin'),
                                  dict(kural='Seçilen dersler aynı ders sayılsın',aktif=False,dersler=['Mat1','Mat2'])]
        r=self.run_strict(d);self.assertTrue(r.complete)

    # ── Seçim = tek ders: "Aynı ders aynı gün tekrar etmesin: Mat1, Mat2" ──
    def test_selected_subjects_in_once_day_rule_are_one_lesson(self):
        d=self._group_store(D=1)
        d['dersler']+= [{'ad':'Fizik'},{'ad':'Kimya'},{'ad':'Tarih'}]
        d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin',dersler=['Mat1','Mat2']),
                                  rule('Aynı ders art arda gelmesin',dersler=['Mat1','Mat2'])]
        # Seçim tek ders sayıldığı için Mat1 ile Mat2 aynı güne ne bitişik
        # (art arda kuralı) ne ayrı (tekrar kuralı) konabilir: biri açıkta kalır.
        r=self.run_strict(d);self.assertEqual(r.placed_hours,1)
        self.assertTrue(any(x.kind==R.X_SUBJECT_GROUP for x in r.rules))

    def test_explicit_tek_ders_false_keeps_each_subject_separate(self):
        d=self._group_store(D=1)
        d['dersler']+= [{'ad':'Fizik'},{'ad':'Kimya'},{'ad':'Tarih'}]
        d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin',dersler=['Mat1','Mat2'],tek_ders=False)]
        r=self.run_strict(d);self.assertTrue(r.complete)

    def test_selecting_nearly_all_subjects_means_all_not_one_lesson(self):
        # Boğaziçi kaydı: 33 dersin 32'si seçili — "tüm dersler" niyeti.
        d=self._group_store(D=1)
        d['dersler']=[{'ad':'Mat1'},{'ad':'Mat2'},{'ad':'Geometri'}]
        d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin',dersler=['Mat1','Mat2'])]
        r=self.run_strict(d);self.assertTrue(r.complete)
        self.assertFalse(any(x.kind==R.X_SUBJECT_GROUP for x in r.rules))

    def test_grouped_pair_rule_keeps_groups_independent(self):
        # Mat1+Mat2 | Fizik+Kimya: Mat1 ile Fizik aynı güne gelebilir, Mat1 ile Mat2 gelemez.
        d=self._group_store(D=2)
        d['dersler']=[{'ad':'Mat1'},{'ad':'Mat2'},{'ad':'Fizik'},{'ad':'Kimya'},{'ad':'Tarih'}]
        d['atamalar']=[dict(**{'class':'9A'},subject=sb,teacher=t,type='1') for sb,t in
                       [('Mat1','Öğretmen A'),('Mat2','Öğretmen A'),('Fizik','Öğretmen B'),('Kimya','Öğretmen B')]]
        d['planlama_iliskileri']=[rule('İki ders aynı güne gelmesin',dersler=['Mat1','Mat2','Fizik','Kimya'],
                                       gruplar=[['Mat1','Mat2'],['Fizik','Kimya']])]
        r=self.run_strict(d);self.assertTrue(r.complete)
        day={x['subject']:x['day'] for x in r.placements}
        self.assertNotEqual(day['Mat1'],day['Mat2']);self.assertNotEqual(day['Fizik'],day['Kimya'])
        # Aynı dört ders TEK grup olsaydı iki güne sığmazdı.
        d['planlama_iliskileri']=[rule('İki ders aynı güne gelmesin',dersler=['Mat1','Mat2','Fizik','Kimya'])]
        self.assertFalse(self.run_strict(d).complete)

    def test_grouped_once_day_makes_each_group_one_lesson(self):
        d=self._group_store(D=2)
        d['dersler']=[{'ad':'Mat1'},{'ad':'Mat2'},{'ad':'Türkçe'},{'ad':'Edebiyat'},{'ad':'Tarih'}]
        d['atamalar']=[dict(**{'class':'9A'},subject=sb,teacher=t,type='1') for sb,t in
                       [('Mat1','Öğretmen A'),('Mat2','Öğretmen A'),('Türkçe','Öğretmen B'),('Edebiyat','Öğretmen B')]]
        d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin',dersler=['Mat1','Mat2','Türkçe','Edebiyat'],
                                       gruplar=[['Mat1','Mat2'],['Türkçe','Edebiyat']])]
        r=self.run_strict(d);self.assertTrue(r.complete)
        fams={r.world.family_name(r.world.subject_family[r.world.subjects.index(x)]) for x in ('Mat1','Türkçe')}
        self.assertEqual(fams,{'Mat1 / Mat2','Türkçe / Edebiyat'})

    def test_same_subject_not_adjacent(self):
        d=self._group_store(D=1,P=3)
        d['planlama_iliskileri']=[rule('Aynı ders art arda gelmesin'),
                                  rule('Seçilen dersler aynı ders sayılsın',dersler=['Mat1','Mat2'])]
        r=self.run_valid(d);self.assertTrue(r.complete)
        ps=sorted(x['period'] for x in r.placements);self.assertEqual(ps,[0,2])
        self.assertTrue(validate(r.world,r.rules,[0,1])[0])

    def test_hard_not_adjacent_treats_group_as_one_lesson(self):
        d=self._group_store(D=1,P=2)
        d['planlama_iliskileri']=[rule('İki zor ders art arda gelmesin',dersler=['Mat1','Mat2']),
                                  rule('Seçilen dersler aynı ders sayılsın',dersler=['Mat1','Mat2'])]
        r=self.run_strict(d);self.assertTrue(r.complete)

    def test_daily_hours_count_the_whole_family(self):
        d=self._group_store(D=1,P=4)
        d['atamalar'][0]['type']='2';d['atamalar'][1]['type']='1'
        d['planlama_iliskileri']=[rule('Günde maksimum ders sayısı',parametre=2),
                                  rule('Seçilen dersler aynı ders sayılsın',dersler=['Mat1','Mat2'])]
        r=self.run_strict(d);self.assertEqual(r.placed_hours,2)

    # ── CP-SAT bütün kuralları modeller (optimal kip yalnızca onu kullanır) ──
    def test_optimal_mode_respects_pair_not_same_day(self):
        d=self._group_store(D=2)
        d['planlama_iliskileri']=[rule('İki ders aynı güne gelmesin',dersler=['Mat1','Mat2'])]
        r=self.run_valid(d,optimal_mode=True,azami_saniye=20)
        self.assertTrue(r.complete);self.assertEqual(len({x['day'] for x in r.placements}),2)

    def test_day_bound_proves_ceiling_and_names_the_rule(self):
        """Gün-seviyesi kanıt: 'iki ders aynı güne gelmesin' + 'aynı ders aynı gün
        tekrar etmesin' birlikte kartları güne sığdıramıyorsa tavan toplamın
        altındadır; motor tavana ulaşınca kanıtla durur ve tanı kuralı söyler."""
        from scheduler.daybound import day_bound
        # Tek gün: Matematik ile Geometri aynı güne gelemez, dolayısıyla
        # ikisinden yalnızca biri yerleşebilir. Tavan toplamın altındadır.
        d=store(parts='1+1',D=1,P=6)
        d['atamalar'].append(dict(**{'class':'9A'},subject='Geometri',teacher='Öğretmen B',type='1+1'))
        d['planlama_iliskileri']=[rule('İki ders aynı güne gelmesin',dersler=['Matematik','Geometri'])]
        r=self.run_valid(d,optimal_mode=True,azami_saniye=20)
        # Gün modeli "aynı ders aynı gün" kısıtını artık kurmaz (bitişiklik
        # serbest), ama "iki ders aynı güne gelmesin" hâlâ sınırı düşürür.
        self.assertLess(r.upper_bound,r.total_hours)
        self.assertEqual(r.placed_hours,r.upper_bound)
        self.assertTrue(any('İki ders aynı güne gelmesin' in x['message'] for x in r.diagnostics),
                        [x['message'] for x in r.diagnostics])
        self.assertEqual(day_bound(r.world,r.rules,set()),r.upper_bound)

    def test_ceiling_is_reached_every_time(self):
        """Tavan bilinince motor ona ulaşır; kurallar tavanı düşürmüyorsa tam çizelge."""
        d=store(parts='2+2',D=4,P=4)
        d['atamalar'].append(dict(**{'class':'9A'},subject='Geometri',teacher='Öğretmen B',type='2+1'))
        d['atamalar'].append(dict(**{'class':'9B'},subject='Matematik',teacher='Öğretmen A',type='2+2'))
        d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin'),
                                  rule('İki ders aynı güne gelmesin',dersler=['Matematik','Geometri'])]
        for _ in range(3):
            r=self.run_valid(copy.deepcopy(d),optimal_mode=True,azami_saniye=20)
            self.assertEqual(r.placed_hours,r.upper_bound)
            self.assertEqual(r.placed_hours,r.total_hours)

    def test_optimal_mode_respects_daily_limit_and_min_days(self):
        d=store('1+1+1',D=3);d['planlama_iliskileri']=[rule('Günde maksimum ders sayısı',parametre=1)]
        r=self.run_valid(d,optimal_mode=True,azami_saniye=20)
        self.assertTrue(r.complete);self.assertEqual(len({x['day'] for x in r.placements}),3)
        d=store('1+1',D=3);d['planlama_iliskileri']=[rule('Aynı ders kartları arasında en az N gün olsun',parametre=2)]
        r=self.run_valid(d,optimal_mode=True,azami_saniye=20)
        self.assertTrue(r.complete);self.assertEqual(sorted(x['day'] for x in r.placements),[0,2])

    def test_optimal_mode_respects_teacher_max_days(self):
        d=store('1+1+1',D=3);d['planlama_iliskileri']=[rule('Öğretmen haftada en fazla N gün',parametre=2)]
        r=self.run_valid(d,optimal_mode=True,azami_saniye=20)
        self.assertTrue(r.complete);self.assertLessEqual(len({x['day'] for x in r.placements}),2)

    def test_optimal_mode_split_pieces_respect_windows(self):
        d=store('2',D=1,P=4);d['siniflar'][0]['timeoff']=[[2,0,2,2]]
        d['planlama_iliskileri']=[rule('X dersi belirli saatlerde kalmalı',period_start=1,period_end=3)]
        r=self.run_valid(d,optimal_mode=True,azami_saniye=20)
        # Tek günde 0 ve 2. saat: parçalar bitişik olamaz. Aynı güne düşen
        # parçalar yan yana olmak zorunda (araya ders giremez), bu yüzden
        # kart YERLEŞMEZ — sığmazsa sığmasın, bölünerek oturtulmaz.
        self.assertFalse(r.complete)
        self.assertEqual(r.placements, [])

    def test_validator_rejects_unforced_violation_even_when_bending(self):
        d=store('1+1',D=2,P=4);d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin')]
        w=build_world(d);rules,_=compile_rules(d['planlama_iliskileri'],w);attach_slots(w,rules)
        # Aynı günde ARALARI AÇIK iki kart: iki gün varken bu esnetilmez.
        errs,_,bent=validate(w,rules,[0,2],bend_rules=True)
        self.assertTrue(errs);self.assertEqual(bent,[])

    def test_validator_checks_split_pieces(self):
        d=store('2',D=2,P=4);d['siniflar'][0]['timeoff']=[[2,2,0,2],[2,2,2,2]]
        w=build_world(d);rules,_=compile_rules([],w);attach_slots(w,rules)
        errs,_,_=validate(w,rules,[-1],pieces={0:[1,2]})
        self.assertTrue(any('Kapalı' in e for e in errs))
        # Aynı günde araları açık parçalar: HATA (araya ders girmiş bölünme).
        self.assertTrue(any('yan yana' in e for e in validate(w,rules,[-1],pieces={0:[0,3]})[0]))
        # Ayrı günlerde iki parça: geçerli.
        self.assertEqual(validate(w,rules,[-1],pieces={0:[0,5]})[0],[])

    def test_unknown_filter_is_error_not_all_classes(self):
        d=store();d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin',siniflar=['Yok'])]
        with self.assertRaises(ValueError): solve(d)

    def test_teacher_filters_are_respected(self):
        d=store('1+1',D=1);d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin',ogretmenler=['Öğretmen B'])]
        self.assertTrue(self.run_valid(d).complete)

    def test_legacy_constraint_dictionary(self):
        d=store('2',D=1);d['kisitlamalar']={'9A':{'0,0':False,'0,1':False}}
        r=self.run_valid(d);self.assertTrue(r.complete);self.assertEqual(r.placements[0]['period'],2)

    def test_closed_teacher_and_cross_busy(self):
        d=store('1',D=1);d['ogretmenler'][0]['timeoff']=[[0,0,2,2]]
        r=self.run_valid(d,cross_busy={'Öğretmen A':{(0,2)}})
        self.assertTrue(r.complete);self.assertEqual(r.placements[0]['period'],3)

    def test_no_domain_never_looks_complete(self):
        d=store('2',D=1,P=1);r=self.run_valid(d)
        self.assertFalse(r.complete);self.assertEqual(r.placed_hours,0);self.assertEqual(len(r.unplaced),1)

    def test_whole_three_hour_card(self):
        d=store('3+1');r=self.run_valid(d)
        self.assertTrue(r.complete);self.assertEqual(sorted(x['duration'] for x in r.placements),[1,3])

    def test_combined_card_one_teacher_two_classes(self):
        d=store('2',D=1,P=2);d['atamalar'][0]['class']='9A+9B'
        r=self.run_valid(d);self.assertTrue(r.complete);self.assertEqual(r.placed_hours,4)
        self.assertEqual(len({x['block_id'] for x in r.placements}),1)

    def test_locked_card_preserved(self):
        d=store('2');d['grid_placements']=[dict(**{'class':'9A'},subject='Matematik',teacher='Öğretmen A',day=2,period=1,duration=2,locked=True)]
        r=self.run_valid(d);self.assertTrue(r.complete)
        locked_pls=[p for p in r.placements if p.get('locked')]
        self.assertEqual(len(locked_pls),1)
        self.assertEqual(locked_pls[0]['day'],2)
        self.assertEqual(locked_pls[0]['period'],1)

    def test_lock_on_closed_time_is_not_silently_accepted(self):
        # Motor kapalı saati kendiliğinden AÇMAZ. Eskiden kapalı saatteki kilit
        # olduğu gibi kabul ediliyor, çizelge "tam" görünüyordu (Birey: kilitli
        # yolda 267/267, aynı veride sıfırdan 266/267).
        from scheduler.engine import LockedConflict
        d=store('2');d['grid_placements']=[dict(**{'class':'9A'},subject='Matematik',teacher='Öğretmen A',day=0,period=0,duration=2,locked=True)]
        d['siniflar'][0]['timeoff']=[[0,0,2,2],[2,2,2,2],[2,2,2,2]]
        with self.assertRaises(LockedConflict) as ctx:
            solve(d,time_budget=1,seed=17)
        self.assertEqual(len(ctx.exception.catismalar),1)
        self.assertIn('KAPALI',str(ctx.exception))
        self.assertIn('9A · Matematik',str(ctx.exception))
        # Kullanıcı "çöz" derse ders kurallara uygun bir yere gider, kapalı
        # saate asla düşmez ve rapor kilidin neden çözüldüğünü söyler.
        r=self.run_valid(d,unlock_conflicting_locks=True);self.assertTrue(r.complete)
        self.assertFalse(any(p.get('locked') for p in r.placements))
        self.assertTrue(all(not (p['day']==0 and p['period']<2) for p in r.placements))
        self.assertTrue(any('KİLİT ÇÖZÜLDÜ' in x for x in r.warnings))

    def test_locked_lesson_counts_for_rules(self):
        # Kilitli ders modelin içindedir: "aynı ders aynı gün tekrar etmesin"
        # kilitli Matematiği görür, serbest Matematik aynı güne konmaz.
        d=store('1+1',D=2,P=4);d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin')]
        d['grid_placements']=[dict(**{'class':'9A'},subject='Matematik',teacher='Öğretmen A',day=0,period=3,duration=1,locked=True)]
        r=self.run_valid(d);self.assertTrue(r.complete)
        free=[p for p in r.placements if not p.get('locked')]
        self.assertEqual(len(free),1);self.assertEqual(free[0]['day'],1)

    def test_locked_block_stored_as_hourly_entries(self):
        # 2 saatlik blok sınıf başına 1'er saatlik iki kayıt olarak durabiliyor
        # (aynı block_id). Tek kilitli karttır; kayıtlar olduğu gibi geri döner.
        d=store('2+1',D=2,P=4)
        d['grid_placements']=[dict(**{'class':'9A'},subject='Matematik',teacher='Öğretmen A',day=1,period=p,duration=1,
                                   locked=True,block_id='blok-x',color='#123456') for p in (1,2)]
        r=self.run_valid(d);self.assertTrue(r.complete);self.assertEqual(r.placed_hours,3)
        locked=[p for p in r.placements if p.get('locked')]
        self.assertEqual(sorted(p['period'] for p in locked),[1,2])
        self.assertTrue(all(p['block_id']=='blok-x' and p['color']=='#123456' for p in locked))
        free=[p for p in r.placements if not p.get('locked')]
        self.assertEqual([p['duration'] for p in free],[1])

    def test_clashing_locks_blame_only_one(self):
        from scheduler.engine import LockedConflict
        d=store('1',D=1,P=2);d['atamalar'].append(dict(**{'class':'9B'},subject='Geometri',teacher='Öğretmen A',type='1'))
        d['grid_placements']=[dict(**{'class':'9A'},subject='Matematik',teacher='Öğretmen A',day=0,period=0,duration=1,locked=True),
                              dict(**{'class':'9B'},subject='Geometri',teacher='Öğretmen A',day=0,period=0,duration=1,locked=True)]
        with self.assertRaises(LockedConflict) as ctx:
            solve(d,time_budget=1,seed=17)
        self.assertEqual(len(ctx.exception.catismalar),1)
        self.assertIn('Öğretmen çakışması',str(ctx.exception))
        r=self.run_valid(d,unlock_conflicting_locks=True);self.assertTrue(r.complete)
        self.assertEqual(sum(1 for p in r.placements if p.get('locked')),1)

    def test_daily_hour_limit(self):
        d=store('1+1+1',D=2);d['planlama_iliskileri']=[rule('Günde maksimum ders sayısı',parametre=2)]
        r=self.run_valid(d);self.assertTrue(r.complete)
        self.assertTrue(all(sum(x['duration'] for x in r.placements if x['day']==day)<=2 for day in range(2)))

    def test_hard_window_applies_to_end_of_block(self):
        d=store('2',D=1);d['planlama_iliskileri']=[rule('X dersi belirli saatlerde kalmalı',period_start=2,period_end=3)]
        r=self.run_valid(d);self.assertTrue(r.complete);self.assertEqual(r.positions,[1])

    def test_soft_window_does_not_close_domain(self):
        d=store('2',D=1,P=4);d['siniflar'][0]['timeoff']=[[0,0,2,2]]
        d['planlama_iliskileri']=[dict(kural='X dersi belirli saatlerde kalmalı',onem='Normal',period_start=1,period_end=2)]
        r=self.run_valid(d);self.assertTrue(r.complete);self.assertTrue(r.warnings)

    def test_hard_not_adjacent_is_enforced(self):
        d=store('1',D=1,P=2);d['atamalar'].append(dict(**{'class':'9A'},subject='Geometri',teacher='Öğretmen B',type='1'))
        d['planlama_iliskileri']=[rule('İki zor ders art arda gelmesin',dersler=['Matematik','Geometri'])]
        r=self.run_valid(d);self.assertEqual(r.placed_hours,1)

    def test_cancellation_returns_valid_partial(self):
        d=store('1',D=1,P=2);d['atamalar']*=5
        start=time.monotonic();r=self.run_valid(d,cancelled=lambda:True)
        self.assertLess(time.monotonic()-start,2);self.assertTrue(r.valid)

    def test_independent_validator_rejects_teacher_clash(self):
        d=store('1',D=1);d['atamalar'].append(dict(**{'class':'9B'},subject='Geometri',teacher='Öğretmen A',type='1'))
        w=build_world(d);self.assertTrue(validate(w,[],[0,0])[0])

    def test_deadline_does_not_drop_unplaced_accounting(self):
        d=store('1+1+1');r=solve(d,time_budget=0)
        self.assertEqual(r.placed_hours+sum(x['hours'] for x in r.unplaced),3)

if __name__=='__main__': unittest.main(verbosity=2)
