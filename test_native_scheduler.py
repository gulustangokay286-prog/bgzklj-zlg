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
        self.assertEqual(validate(r.world,r.rules,r.positions)[0],[])
        return r

    def test_inactive_rule_is_not_reintroduced(self):
        d=store('1+1',D=1);d['planlama_iliskileri']=[dict(kural='Aynı ders aynı gün tekrar etmesin',aktif=False)]
        r=self.run_valid(d);self.assertTrue(r.complete);self.assertEqual(r.placed_hours,2)
        self.assertFalse(any(x.kind==R.X_SUBJECT_ONCE_DAY for x in r.rules))

    def test_repeat_is_forbidden_even_when_adjacent(self):
        d=store('1+1',D=1);d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin')]
        r=self.run_valid(d);self.assertFalse(r.complete);self.assertEqual(r.placed_hours,1)
        self.assertEqual(r.upper_bound,1)
        self.assertTrue(validate(r.world,r.rules,[0,1])[0])

    def test_double_block_counts_as_one_session(self):
        d=store('2+1');d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin')]
        r=self.run_valid(d);self.assertTrue(r.complete)
        self.assertEqual(sorted(x['duration'] for x in r.placements),[1,2])
        self.assertEqual(len({x['day'] for x in r.placements}),2)

    def test_teacher_rule_in_same_class_only(self):
        d=store('1');d['atamalar'] += [dict(**{'class':cn},subject='Geometri',teacher='Öğretmen A',type='1') for cn in ['9A','9B']]
        d['planlama_iliskileri']=[rule('Aynı öğretmen aynı gün tekrar etmesin')]
        r=self.run_valid(d);self.assertTrue(r.complete)
        self.assertEqual(len({x['day'] for x in r.placements if x['class']=='9A'}),2)

    def test_rule_filters_do_not_leak(self):
        d=store('1+1',D=1)
        d['atamalar'].append(dict(**{'class':'9B'},subject='Matematik',teacher='Öğretmen B',type='1+1'))
        d['planlama_iliskileri']=[rule('Aynı ders aynı gün tekrar etmesin',siniflar=['9A'])]
        r=self.run_valid(d);self.assertEqual(r.placed_hours,3)
        self.assertEqual(sum(x['duration'] for x in r.placements if x['class']=='9B'),2)

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
        r=self.run_valid(d);self.assertTrue(r.complete);self.assertEqual(r.positions,[9])

    def test_lock_on_closed_time_is_not_silently_dropped(self):
        d=store('2');d['grid_placements']=[dict(**{'class':'9A'},subject='Matematik',teacher='Öğretmen A',day=0,period=0,duration=2,locked=True)]
        d['siniflar'][0]['timeoff']=[[0]*4 for _ in range(3)]
        with self.assertRaises(ValueError): solve(d)

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
