#!/usr/bin/env python3
"""R44 true/negative assertions. Passing means test models identified known limitations, NOT qualification."""
import json,hashlib,unittest,math,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class R44(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.s=json.loads((ROOT/'evidence/R44_rear_bypass_OCC.json').read_text())
  cls.f=json.loads((ROOT/'evidence/R44_direct_feedthrough_rejected.json').read_text())
  cls.b=json.loads((ROOT/'evidence/R44_analytic_bounds.json').read_text())
  cls.c=json.loads((ROOT/'evidence/R44_STOW_exact_clearance.json').read_text())
  cls.d=json.loads((ROOT/'evidence/R44_dense_121_OCC.json').read_text())
 def test_frozen_R43_source_sha(self):
  p=ROOT/'baseline/RAZR_SLIDE_R43_FPC_full_verified_20261013.zip'
  with p.open('rb') as f:self.assertEqual(hashlib.file_digest(f,'sha256').hexdigest(),'d79c33b2a0e8eae2d05c5dc318b442bdffb1420e5361e87e0317a4d9191de7a0')
 def test_source_zip_crc_and_count(self):
  with zipfile.ZipFile(ROOT/'baseline/RAZR_SLIDE_R43_FPC_full_verified_20261013.zip') as z:
   self.assertIsNone(z.testzip());self.assertEqual(len(z.namelist()),33)
 def test_rear_four_branches(self):self.assertEqual(len(self.s['options']),4)
 def test_rear_nine_poses_each(self):self.assertEqual(len(self.s['rows']),36)
 def test_rear_model_zero_intersection(self):self.assertTrue(all(not any(v>1e-6 for v in r['volume_overlap_mm3'].values()) for r in self.s['rows']))
 def test_rear_model_finite_swept_length(self):self.assertLess(self.s['max_abs_wire_length_error_mm'],1e-5)
 def test_analytic_length_exact(self):self.assertTrue(all(abs(r['length_mm']-120.)<1e-8 for r in self.s['rows']))
 def test_positive_straights(self):self.assertTrue(all(r['straight_A_mm']>0 and r['straight_B_mm']>0 for r in self.s['rows']))
 def test_dock_curvature_decrease(self):
  r=[v for v in self.s['rows'] if v['branch']=='NEAR_REAR_INSIDE_BUDGET_Z_MINUS_7_95']
  self.assertAlmostEqual(r[0]['minimum_centerline_curvature_radius_mm'],16.5,places=5)
  self.assertLess(r[-1]['minimum_centerline_curvature_radius_mm'],16.1)
 def test_near_rear_inside_nominal_Z_budget(self):
  self.assertTrue(all(r['research_z_envelope_excess_below_minus_8p2_mm']==0 for r in self.s['rows'] if r['branch']=='NEAR_REAR_INSIDE_BUDGET_Z_MINUS_7_95'))
 def test_external_rear_exceeds_Z_budget(self):
  self.assertGreater(max(r['research_z_envelope_excess_below_minus_8p2_mm'] for r in self.s['rows'] if r['branch']=='REAR_Z_MINUS_8_7_B_FOLLOWS_Q'),0.57)
 def test_near_rear_no_y_overhang(self):
  self.assertTrue(all(r['research_y_excess_beyond_case_mm']==0 for r in self.s['rows'] if r['branch']=='NEAR_REAR_INSIDE_BUDGET_Z_MINUS_7_95'))
 def test_9_ghosts_are_valid_reimport(self):
  imported=[r for r in self.s['rows'] if 'ghost_STEP' in r]
  self.assertEqual(len(imported),6)
  for row in imported:
   m=row['ghost_STEP'];p=ROOT/'cad'/m['filename']
   self.assertTrue(p.is_file());self.assertGreaterEqual(m['valid_solids'],5)
   self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),m['sha256'])
 def test_untethered_is_unqualified(self):
  self.assertTrue(self.s['actual_A_terminal_cannot_reach_unapproved_exterior_without_feedthrough'])
  self.assertTrue(all(r['not_an_integrated_cable'] for r in self.s['rows']))
 def test_feedthrough_three_reject_poses(self):self.assertEqual(len(self.f['rows']),3)
 def test_A_feedthrough_hits_protected_A(self):
  self.assertTrue(all(row['protected_intersections_mm3']['A_BOARD_TO_UNBUILT_REAR_ANCHOR']['A_R38_CORE']>0.6 for row in self.f['rows']))
 def test_B_feedthrough_hits_protected_B(self):
  self.assertTrue(all(row['protected_intersections_mm3']['B_BOARD_TO_UNBUILT_REAR_ANCHOR']['B_R38_CORE']>2.0 for row in self.f['rows']))
 def test_negative_stub_cannot_disprove_other_routes(self):self.assertTrue(self.f['any_route_still_requires_OEM_feedthrough_and_PCBA_mounting'])
 def test_rear_clearance_stow_has_OLED_risk(self):
  self.assertAlmostEqual(self.c['nominal_min_distances_mm']['OLED_PROXY'],0.395,places=5)
 def test_clearance_is_not_full_sweep(self):self.assertTrue(self.c['no_claim_continuous_dynamics_or_tolerance'])
 def test_necessary_stow_length_bound(self):self.assertAlmostEqual(self.b['max_total_constant_length_mm'],121.13627878423,places=6)
 def test_conditional_stress_relief_misses(self):self.assertAlmostEqual(self.b['hypothetical_10mm_A_leg_Y_excess_mm'],2.85,places=6)
 def test_dense_121_positions(self):self.assertEqual(self.d['pose_count'],121)
 def test_dense_101_plus_20(self):self.assertEqual((self.d['slide_poses'],self.d['dock_poses']),(101,20))
 def test_dense_no_protected_body_overlap(self):self.assertEqual(self.d['core_or_display_Occ_intersection_pose_count'],0)
 def test_dense_in_declared_reference_envelope(self):self.assertEqual(self.d['max_envelope_XZ_violation_mm'],0.0);self.assertEqual(self.d['max_envelope_Y_violation_mm'],0.0)
 def test_dense_curvature_min_is_below_nominal_R(self):self.assertLess(self.d['smallest_centerline_curvature_radius_mm'],16.1)
 def test_dense_not_continuous_swept_clearance(self):self.assertTrue(self.d['discrete_Occ_only_no_full_continuous_swept_clearance'])
 def test_dense_ends_unterminated(self):self.assertTrue(self.d['no_terminal_or_FPC_OEM_layerstack_or_rear_cassette'])
 def test_thickness_is_assumption(self):self.assertTrue(self.s['wire_bend_life_unproven'])
 def test_no_vendor_or_oem_approval(self):self.assertTrue(self.s['A_B_finished_design_and_OEM_3D_missing'])
 def test_never_auto_promote_from_ghost(self):
  self.assertFalse(self.s['candidate_go']);self.assertFalse(self.s['manufacturing_go']);self.assertFalse(self.f['manufacturing_go']);self.assertFalse(self.b['manufacturing_go'])
if __name__=='__main__':unittest.main()
