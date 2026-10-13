"""R31 adversarial regression: a PASS includes verifying known NO-GO cases."""
from __future__ import annotations
import hashlib,json,unittest
import cadquery as cq
from r25_capture import ROOT,P,intersection
from r31_presence import (a_occupied_shelf,interposer,follower_down,pawl_transit_block,
                           no_A_false_engagement_blocked)

REPORTS=('integration','dynamic','tolerance','faults','section','STEP_manifest')
class R31Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.data={k:json.loads((ROOT/'verification'/f'R31_{k}.json').read_text()) for k in REPORTS}
  cls.freeze=json.loads((ROOT/'audit'/'R31_R30_ORIGINAL_ZIP_MEMBERS.json').read_text())
 def test_01_ancestor_504(self):self.assertEqual(self.freeze['verified_count'],504)
 def test_02_ancestor_prior_not_mutated(self):self.assertTrue(self.freeze['prior_files_unchanged'])
 def test_03_ancestor_hash_has_length(self):self.assertEqual(len(self.freeze['original_zip_sha256']),64)
 def test_04_ancestor_hashes_still_equal(self):
  for f in self.freeze['entries']:
   self.assertEqual(hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest(),f['sha256'])
 def test_05_A_one_connected_actual(self):self.assertTrue(self.data['integration']['A_valid_single'])
 def test_06_B_one_connected_actual(self):self.assertTrue(self.data['integration']['B_valid_single'])
 def test_07_real_added_A_material(self):self.assertGreater(self.data['integration']['A_new_volume_mm3'],self.data['integration']['A_old_volume_mm3'])
 def test_08_actual_B_sweep_pockets(self):self.assertLess(self.data['integration']['B_new_volume_mm3'],self.data['integration']['B_old_volume_mm3'])
 def test_09_six_CAD_operations(self):self.assertEqual(len(self.data['integration']['operations']),6)
 def test_10_new_A_shelf_fused_with_existing_nose(self):
  for s in 'LR':
   self.assertTrue(a_occupied_shelf(s).isValid())
   self.assertGreater(next(x['previous_A_overlap_mm3'] for x in self.data['integration']['operations'] if x['side']==s and x['operation']=='FUSE_A_LATE_SHELF'),0)
 def test_11_two_connected_interposers(self):
  for s in 'LR':
   for down in (0.,.2,.4):
    p=interposer(s,down);self.assertTrue(p.isValid());self.assertEqual(len(p.Solids()),1)
 def test_12_no_A_default_blocks_mid_pawl(self):
  for s in 'LR':self.assertTrue(no_A_false_engagement_blocked(s))
 def test_13_late_8p15_remains_blocked(self):
  for s in 'LR':self.assertGreater(pawl_transit_block(s,follower_down(8.15))[2],0.)
 def test_14_nominal_full_seat_clear_of_pawl(self):
  for s in 'LR':self.assertTrue(all(x<1e-8 for x in pawl_transit_block(s,follower_down(8.2))))
 def test_15_already_stowed_no_A_never_releases(self):self.assertAlmostEqual(follower_down(0,False),0.)
 def test_16_mid_seat_without_A_never_releases(self):self.assertAlmostEqual(follower_down(8.2,False),0.)
 def test_17_ideal_kinematics_from_actual_shelf_plane(self):self.assertAlmostEqual(follower_down(8.),.2)
 def test_18_kinematic_q8p2_cap(self):self.assertAlmostEqual(follower_down(8.2),.4)
 def test_19_full_chassis_ten_poses(self):self.assertEqual(self.data['dynamic']['reference_poses'],10)
 def test_20_full_chassis_no_named_collision(self):self.assertEqual(self.data['dynamic']['unexpected_clashes'],0)
 def test_21_end_dock_twenty_cad_scenarios(self):self.assertEqual(self.data['dynamic']['near_seat_cases'],20)
 def test_22_unsafe_key_CAD_not_OEM(self):self.assertTrue(self.data['dynamic']['full_OEM_OLED_edge_envelope_not_available'])
 def test_23_tolerance_108(self):self.assertEqual(self.data['tolerance']['configurations'],108)
 def test_24_0p02_fails_to_release_seat(self):self.assertEqual(self.data['tolerance']['per_width'][0]['seat_refuses_to_release'],18)
 def test_25_0p02_no_early(self):self.assertEqual(self.data['tolerance']['per_width'][0]['false_release_before_seat'],0)
 def test_26_0p05_fails_to_release_seat(self):self.assertEqual(self.data['tolerance']['per_width'][1]['seat_refuses_to_release'],18)
 def test_27_0p05_early_release_detected(self):self.assertEqual(self.data['tolerance']['per_width'][1]['false_release_before_seat'],18)
 def test_28_0p05_B_pocket_jam_detected(self):self.assertEqual(self.data['tolerance']['per_width'][1]['B_cavity_interference_configurations'],44)
 def test_29_noA_guards_not_lost_in_scan(self):self.assertEqual(sum(x['no_A_guard_misses_middle_sweep'] for x in self.data['tolerance']['per_width']),0)
 def test_30_64_old_combined_fault_modes(self):self.assertEqual(self.data['faults']['old_R30_original_64_fault_modes'],64)
 def test_31_36_old_escape_counterexamples_retained(self):self.assertEqual(self.data['faults']['old_R30_original_36_escapes'],36)
 def test_32_two_default_plungers_defeat_old_escapes_only_under_assumption(self):
  self.assertEqual(self.data['faults']['cross_product_old_plus_two_independent_interposer_states'][0]['no_A_escaping_assuming_new_spring_default_and_hard_guides'],0)
 def test_33_both_plungers_stuck_down_reenable_36_hazards(self):
  self.assertEqual(self.data['faults']['cross_product_old_plus_two_independent_interposer_states'][-1]['no_A_escaping_assuming_new_spring_default_and_hard_guides'],36)
 def test_34_STOW_endpoint_is_still_unsafe(self):self.assertTrue(self.data['faults']['STOW_endpoint_false_capture_still_unremedied'])
 def test_35_no_real_return_spring(self):self.assertTrue(self.data['integration']['no_real_prismatic_bearing_spring_fastener_or_force_test'])
 def test_36_original_front_web_unfixed(self):self.assertTrue(self.data['section']['old_R29_lip_not_replaced_with_qualified_load_path'])
 def test_37_actual_section_sample_not_min_wall(self):self.assertEqual(len(self.data['section']['samples']),4)
 def test_38_no_vendor_electrical_mate_stroke(self):self.assertTrue(self.data['faults']['physical_electrical_contact_onset_unknown'])
 def test_39_no_force_limited_return(self):self.assertTrue(self.data['faults']['force_limited_stuck_carrier_recovery_unverified'])
 def test_40_STEP_eight(self):self.assertEqual(self.data['STEP_manifest']['scene_count'],8)
 def test_41_STEP_imports_and_member_hashes(self):
  for x in self.data['STEP_manifest']['scenes']:
   self.assertEqual(x['valid_reimported_solids'],x['parts'])
   self.assertEqual(hashlib.sha256((ROOT/'cad'/x['filename']).read_bytes()).hexdigest(),x['sha256'])
 def test_42_ghost_sample_cases(self):self.assertEqual(sum(x['ghost_known_unsafe'] for x in self.data['STEP_manifest']['scenes']),4)
 def test_43_all_reports_NO_GO(self):self.assertTrue(all(x['manufacturing_go'] is False for x in self.data.values()))
 def test_44_B_housing_frozen_outside_modified_cavities(self):
  self.assertTrue(all(x['connected'] for x in self.data['integration']['operations']))
 def test_45_key_is_external_OLED_assumption_only(self):self.assertTrue(self.data['section']['no_material_modulus_yield_tolerances_or_300k_cycles'])

if __name__=='__main__':unittest.main()
