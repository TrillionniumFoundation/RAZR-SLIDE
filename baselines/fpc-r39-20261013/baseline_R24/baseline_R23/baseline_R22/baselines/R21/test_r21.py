"""R21 tests include explicit failure gates. Passing unit tests != hardware approval."""
import unittest,json,hashlib
from pathlib import Path
from r21_geom import ROOT,P,STOW_Y,open_contact_cradle,stow_pocketed_shell,run_dock_integration,local_assembly,intersection
from r21_verify import nearest

class TestR21(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.r=json.loads((ROOT/'verification'/'R21_results.json').read_text())
  cls.m=json.loads((ROOT/'verification'/'R21_step_manifest.json').read_text())
 def test_01_two_equal_cabins(self):self.assertEqual(self.r['common_design']['each_cabin_H_mm'],94.25)
 def test_02_maintain_no_rear_screen(self):self.assertTrue(self.r['common_design']['no_rear_external_screen'])
 def test_03_body_contiguous(self):self.assertTrue(self.r['altered_compared_to_R20']['B_one_connected_proxy_solid'])
 def test_04_stow_relocated(self):self.assertEqual(STOW_Y,18.5)
 def test_05_original_battery_collision_detected(self):self.assertGreater(self.r['altered_compared_to_R20']['battery_proxy_old_recess_intersection_mm3'],27.)
 def test_06_new_battery_cut_zero(self):self.assertAlmostEqual(self.r['altered_compared_to_R20']['battery_proxy_new_recess_intersection_mm3'],0,places=6)
 def test_07_intentionally_bad_guides_removed(self):self.assertTrue(self.r['altered_compared_to_R20']['abandoned_old_guides_original_intended_core_attachment_overlap_mm3']>62.)
 def test_08_sidewall_positive(self):self.assertGreater(self.r['altered_compared_to_R20']['side_rail_ear_remaining_nominal_mm'],2.8)
 def test_09_stow_cavity_cuts_solid(self):self.assertGreater(self.r['altered_compared_to_R20']['stow_machine_cut_away_mm3'],35.)
 def test_10_open_cradle_nonfloating(self):self.assertGreater(self.r['altered_compared_to_R20']['open_carriage_guide_volume_added_mm3'],200.)
 def test_11_floor_nominal_screen(self):self.assertGreaterEqual(self.r['altered_compared_to_R20']['open_island_min_floor_stated_0_7mm_before_tolerance'],.70)
 def test_12_floor_assumed_minus015(self):self.assertGreaterEqual(self.r['altered_compared_to_R20']['open_island_floor_after_hypothetical_minus0_15mm'],.70)
 def test_13_all_pose_body(self):self.assertTrue(all(p['b_model_one_connected_solid'] for p in self.r['poses']))
 def test_14_pose_intersection(self):self.assertTrue(all(not any(v>1e-6 for v in p['cad_intersections'].values()) for p in self.r['poses']))
 def test_15_movable_pose_collision(self):self.assertTrue(all(not p['carriage_vs_B_illegal_intersections'] for p in self.r['poses']))
 def test_16_screen_active_nominal(self):self.assertGreaterEqual(self.r['oled_screening_mm'][0]['min_clearance_mm'],.30)
 def test_17_screen_015mm_each_border_fails(self):self.assertFalse(self.r['oled_screening_mm'][3]['passes_screening'])
 def test_18_screen_020mm_each_border_fails(self):self.assertFalse(self.r['oled_screening_mm'][4]['passes_screening'])
 def test_19_original_dual_dogs_false_open(self):self.assertTrue(self.r['hazards']['R20_both_dogs_false_open_yet_carriage_free'])
 def test_20_real_hard_stop_not_claimed(self):self.assertFalse(self.r['hazards']['actual_hard_stop_release_mechanism'])
 def test_21_oled_vendor_permission_false(self):self.assertFalse(self.r['hazards']['OEM_OLED_R3_4_dynamic_permission'])
 def test_22_vendor_step_missing(self):self.assertFalse(self.r['hazards']['vendor_TE_STEP_present'])
 def test_23_power_not_qualified(self):self.assertFalse(self.r['hazards']['cross_cabin_battery_current_path_qualified'])
 def test_24_no_manufacturing_release(self):self.assertFalse(self.r['hazards']['complete_manufacturing_release'])
 def test_25_seven_step(self):self.assertEqual(len(self.m['CAD']),7)
 def test_26_step_hash_files(self):
  for entry in self.m['CAD']:
   f=ROOT/'cad'/entry['STEP']
   self.assertTrue(f.exists());self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(),entry['sha256'])
 def test_27_oled_length_stays_invariant(self):self.assertLess(self.r['original_R17_analytic_path']['oled_max_length_drift_mm'],1e-9)
 def test_28_internal_FPC_length_stays_invariant(self):self.assertLess(self.r['original_R17_analytic_path']['fpc_max_length_drift_mm'],1e-9)

if __name__=='__main__':unittest.main()
