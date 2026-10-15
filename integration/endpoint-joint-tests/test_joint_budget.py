from pathlib import Path
import sys, unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from roof_joint_budget import screen,FIELDS

class JointBudgetTests(unittest.TestCase):
    def data(self):
        return dict(zip(FIELDS,(5.,8.,20.,80.,3.,20.,20.,20.,20.)))
    def test_missing_strength_never_becomes_pass(self):
        r=screen({});self.assertEqual(r['status'],'undetermined');self.assertEqual(len(r['missing_inputs']),9)
    def test_two_spring_force_balance(self):
        r=screen(self.data());self.assertAlmostEqual(r['minimum_remaining_compression_N'],2.6);self.assertAlmostEqual(r['maximum_bolt_load_N_while_closed'],8.6)
        self.assertEqual(r['status'],'passes_this_axial_screen');self.assertFalse(r['candidate_go'])
    def test_separation_is_not_calculated_as_still_closed(self):
        d=self.data();d['external_axial_load_per_screw_N']=10.;r=screen(d)
        self.assertEqual(r['status'],'rejected_by_axial_screen');self.assertTrue(r['linear_result_is_invalid_after_separation'])
    def test_weakest_female_or_boss_capacity_governs(self):
        d=self.data();d['female_thread_allowable_N']=8.5
        self.assertEqual(screen(d)['status'],'rejected_by_axial_screen')
    def test_invalid_numeric_or_stiffness_rejected(self):
        for x in (True,float('nan'),float('inf'),-1.):
            d=self.data();d['preload_min_N']=x
            with self.assertRaises(ValueError):screen(d)
        d=self.data();d['bolt_stiffness_N_per_mm']=0.
        with self.assertRaises(ValueError):screen(d)
    def test_reversed_preload_rejected(self):
        d=self.data();d['preload_min_N']=9.
        with self.assertRaises(ValueError):screen(d)
