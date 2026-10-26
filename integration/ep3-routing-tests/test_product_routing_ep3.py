"""Arithmetic contract tests; no CAD, actual donor, fabrication or motion test."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import product_routing_ep3 as ep3


class EP3ArithmeticTests(unittest.TestCase):
    def test_fixed_length_rejects_declaration_only_geometry_changes(self):
        c=ep3.load_config(); c['route']['free_length_mm']=140.
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.json'; p.write_text(json.dumps(c))
            with self.assertRaisesRegex(ValueError,'native route declaration changed'):
                ep3.load_config(p)

    def test_thin_jaw_does_not_implicitly_shorten_original_nominal_screw(self):
        c=ep3.load_config(); e=c['endpoint']
        self.assertEqual(e['M2_shaft_length_mm'],1.4)
        self.assertEqual(e['M2_legacy_shaft_length_mm'],2.45)
        self.assertFalse(e['joint_material_process_and_nominal_short_M2_selected'])
        c['endpoint']['M2_shaft_length_mm']=2.45
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.json'; p.write_text(json.dumps(c))
            with self.assertRaisesRegex(ValueError,'native endpoint declaration changed'):
                ep3.load_config(p)

    def test_full_ordered_motion_length_constraint_and_finite_head_are_distinct(self):
        c=ep3.load_config(); r=ep3.arithmetic_report(c)
        lo,hi=r['free_length_necessary_interval_mm']
        # Independent 16384-panel Simpson review, not a value copied from the
        # function's report: finite thickness removes .1 mm from the L upper bound.
        self.assertAlmostEqual(lo,98.6145824564731,places=8)
        self.assertAlmostEqual(hi,103.0592052049,places=8)
        self.assertLess(lo,100.); self.assertGreater(hi,100.)
        for name,s,d in ep3.POSES:
            row=ep3.pose_numbers(s,d,c)
            self.assertGreaterEqual(min(row['straight_A_mm'],row['straight_B_mm']),3.)
            self.assertAlmostEqual(row['length_sum_mm'],100.,places=12)
        self.assertLess(ep3.pose_numbers(0,0,c)['finite_head_world_Y_mm'],94.)

    def test_longer_material_does_not_fix_fixed_layer_radius(self):
        c=ep3.load_config(); old=ep3.pose_numbers(79.75,8.2,c)
        c['route']['free_length_mm']=140.; revised=ep3.pose_numbers(79.75,8.2,c)
        self.assertEqual(old['minimum_centerline_radius_mm'],revised['minimum_centerline_radius_mm'])
        self.assertAlmostEqual(revised['straight_A_mm']-old['straight_A_mm'],20.)
        self.assertGreater(revised['finite_head_world_Y_mm'],old['finite_head_world_Y_mm'])

    def test_predock_counterexample_is_positive_finite_material_outside_both_prisms(self):
        r=ep3.arithmetic_report(); w=r['PREDOCK_single_U_internal_counterexample']
        self.assertLess(w['A_low_straight_Z_interval_mm'][1],w['B_outer_prism_min_Z_mm'])
        self.assertAlmostEqual(w['low_straight_end_Y_mm'],123.4427087717634,places=8)
        self.assertAlmostEqual(w['finite_low_straight_volume_outside_outer_union_mm3'],35.0312505261,places=8)
        self.assertGreater(w['outside_low_straight_length_mm'],0.)
        self.assertAlmostEqual(w['outer_only_anchor_interval_shortfall_mm'],9.5)
        self.assertAlmostEqual(w['requested_anchor_interval_shortfall_mm'],10.35)
        self.assertFalse(w['native_solid_checks_executed_here'])

    def test_seating_before_full_slide_and_release_promotion_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'ordered slide/seating'):
            ep3.pose_numbers(30.,1.)
        c=ep3.load_config(); c['candidate_go']=True
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.json'; p.write_text(json.dumps(c))
            with self.assertRaisesRegex(ValueError,'cannot grant'):
                ep3.load_config(p)

    def test_reference_opposed_stack_budget_preserves_its_scope(self):
        r=ep3.arithmetic_report()['opposed_outer_jaw_reference_cavity']
        self.assertAlmostEqual(r['old_max_lane_difference_mm'],2.5)
        self.assertAlmostEqual(r['EP3_max_lane_difference_mm'],3.4)
        self.assertTrue(r['reference_cavity_is_not_proved_empty'])
        self.assertTrue(r['requires_shortened_1_4mm_nominal_M2_not_original_2_45mm_shaft'])


if __name__=='__main__': unittest.main()
