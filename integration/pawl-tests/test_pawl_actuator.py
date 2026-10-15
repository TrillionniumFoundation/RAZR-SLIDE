from pathlib import Path
import hashlib
import math
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
import pawl_actuator as a
import verify_cam_coupling as v


class PawlActuatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.p,cls.report=a.build()

    def test_thirteen_native_roles_are_complete_single_solids(self):
        self.assertEqual(len(self.p),13)
        for body in self.p.values():self.assertEqual(len(a.c.n.whole_material(body)[0]),1)

    def test_positive_both_way_stroke_ratio(self):
        for u,z in ((0.,0.),(1.5,.55),(3.,1.1)):
            self.assertAlmostEqual(a.displacement(u),z)
            self.assertAlmostEqual(a.displacement(3.-u),1.1-z)

    def test_invalid_numeric_inputs_rejected(self):
        for u in (True,None,'1',float('nan'),float('inf')):
            with self.assertRaises(ValueError):a.displacement(u)

    def test_manual_overtravel_rejected(self):
        for u in (-.001,3.001):
            with self.assertRaises(ValueError):a.displacement(u)

    def test_groove_play_not_silently_clamped(self):
        r=a.output_interval(0.)
        self.assertLess(r['lower_mm'],0.);self.assertGreater(r['upper_mm'],0.)
        self.assertFalse(r['unique_without_load_or_preload'])

    def test_positive_manual_end_play_retained(self):
        r=a.output_interval(3.)
        self.assertLess(r['lower_mm'],1.1);self.assertGreater(r['upper_mm'],1.1)
        self.assertAlmostEqual(r['slot_only_halfwidth_mm'],.025*math.hypot(1,1.1/3))

    def test_original_PAWL_is_not_trimmed(self):
        for side in 'LR':
            old=a.c.parent(side+'_PAWL')
            self.assertEqual(v.equal(old,self.p[side+'_ORIGINAL_PAWL']),[0.,0.])
            self.assertEqual(v.vol(old.cut(self.p[side+'_PAWL'])),0.)

    def test_pin_is_joined_not_floating(self):
        for side in 'LR':
            self.assertGreater(v.common(self.p[side+'_ORIGINAL_PAWL'],self.p[side+'_PIN']),1e-7)

    def test_guide_is_connected_to_panel(self):
        for row in self.report['joints']:
            if 'guide_to_panel_overlap_mm3' in row:self.assertGreater(row['guide_to_panel_overlap_mm3'],1e-7)

    def test_panel_cut_cost_reported(self):
        old=a.c.housing_study()[0]['A_BACK_PANEL'];new=self.p['A_BACK_PANEL']
        r=self.report['panel_material']
        self.assertGreater(r['removed_mm3'],0.)
        self.assertAlmostEqual(v.vol(old)-r['removed_mm3']+r['added_mm3'],v.vol(new),places=7)

    def test_fixed_root_passage_not_unreported_addition(self):
        for side in 'LR':
            old=a.c.parent(side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS');new=self.p[side+'_ROOT_OUTER']
            self.assertEqual(v.vol(new.cut(old)),0.)
            self.assertGreater(v.vol(old.cut(new)),0.)

    def test_original_root_negative_still_hits_pin(self):
        for side in 'LR':
            old=a.c.parent(side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS')
            self.assertGreater(v.common(old,self.p[side+'_PIN']),1e-7)

    def test_new_pin_passage_clears_three_positions(self):
        for side in 'LR':
            for z in (0.,.55,1.1):self.assertEqual(v.common(self.p[side+'_PIN'].translate((0,0,z)),self.p[side+'_ROOT_OUTER']),0.)

    def test_guide_actual_nominal_end_stops_clear(self):
        for side in 'LR':
            for u in (0.,3.):self.assertEqual(v.common(self.p[side+'_TAB'].translate((0,u,0)),self.p[side+'_GUIDE']),0.)

    def test_guide_overtravel_hits_positive_material(self):
        for side in 'LR':
            for u in (-.01,3.01):self.assertGreater(v.common(self.p[side+'_TAB'].translate((0,u,0)),self.p[side+'_GUIDE']),1e-7)

    def test_native_slot_flanks_support_both_directions(self):
        from verify_pawl_actuator import slot_checks
        rows=slot_checks(self.p)
        self.assertEqual(len(rows['flanks']),12);self.assertEqual(len(rows['travel_stops']),8)

    def test_actual_input_register_unchanged(self):
        self.assertEqual(hashlib.sha256((ROOT/'integration/assembly_inputs.json').read_bytes()).hexdigest(),'7b7ebf0f48556f2feca175a35b882a9a48337de2bb5f54b1ba7a740f85e8ce6b')

    def test_repeated_calls_do_not_recut_runtime_geometry(self):
        again,_=a.build();self.assertTrue(all(s.isSame(again[k]) for k,s in self.p.items()))

    def test_control_geometry_within_existing_A_outer(self):
        outer=a.c.parent('A_OUTER')
        for side in 'LR':
            for role in ('TAB','PAWL','ROOT_OUTER'):
                self.assertEqual(v.vol(self.p[side+'_'+role].cut(outer)),0.)

    def test_manual_not_spring_return_claim(self):
        self.assertTrue(self.report['manual_tabs_independent'])
        self.assertTrue(self.report['no_automatic_return_or_detent_implemented'])
