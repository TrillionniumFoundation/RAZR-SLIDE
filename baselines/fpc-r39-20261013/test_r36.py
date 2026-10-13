"""R36 research regression: a PASS can mean a hazardous failure is correctly detected."""
import json,hashlib,unittest
from pathlib import Path
import cadquery as cq
from r25_capture import ROOT
from r36_parts import metadata,keeper,catalog_m08x2_screw

class R36GeometryAndAdversarial(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.d={x:json.loads((ROOT/f'verification/R36_{x}.json').read_text())
         for x in ['integration','dynamic','tolerance','faults','STEP_manifest']}
  cls.anc=json.loads((ROOT/'audit/R36_R35_immutable.json').read_text())
  cls.A=cq.importers.importBrep(str(ROOT/'cad/R36_A_R35_UNCHANGED.brep')).val()
  cls.B=cq.importers.importBrep(str(ROOT/'cad/R36_B_INBOARD_KEEPER_BOSSES_AND_CLEARANCE_BORES.brep')).val()
 def test_01_frozen_ancestor_sha(self):self.assertEqual(self.anc['ancestor_archive_sha256'],'ee0b2eedc9f4b36c1e832b8d5dbdd3bbf121eb724e126d8fb84981f3ebd2a8c9')
 def test_02_frozen_ancestor_count(self):self.assertEqual(self.anc['original_file_count'],853)
 def test_03_frozen_ancestor_bytes(self):self.assertTrue(self.anc['original_bytes_unchanged'])
 def test_04_original_A_unchanged(self):self.assertEqual((ROOT/'cad/R36_A_R35_UNCHANGED.brep').read_bytes(),(ROOT/'cad/R35_A_R34_UNCHANGED.brep').read_bytes())
 def test_05_A_valid(self):self.assertTrue(self.A.isValid())
 def test_06_B_valid(self):self.assertTrue(self.B.isValid())
 def test_07_B_single_body(self):self.assertEqual(len(self.B.Solids()),1)
 def test_08_positive_B_added_net(self):self.assertGreater(self.d['integration']['revised_B_delta_mm3'],4.0)
 def test_09_fused_two_rear_bosses(self):self.assertEqual(sum(x['op']=='fuse_rear_support_boss' for x in self.d['integration']['operations']),2)
 def test_10_cut_two_clearance_bores(self):self.assertEqual(sum(x['op']=='clearance_bore_for_M0p8_proxy' for x in self.d['integration']['operations']),2)
 def test_11_bore_actually_removes_material(self):self.assertTrue(all(x['delta_mm3']<0 for x in self.d['integration']['operations'] if x['op']=='clearance_bore_for_M0p8_proxy'))
 def test_12_two_valid_single_keeper_solids(self):self.assertTrue(all(x['keeper_valid'] and x['keeper_solid_count']==1 for x in self.d['integration']['parts']))
 def test_13_keeper_vs_B_zero(self):self.assertTrue(all(x['keeper_vs_B']<1e-8 for x in self.d['integration']['parts']))
 def test_14_keeper_vs_original_bridge_zero(self):self.assertTrue(all(x['keeper_vs_bridge']<1e-8 for x in self.d['integration']['parts']))
 def test_15_keeper_vs_signal_surrogate_zero(self):self.assertTrue(all(x['keeper_vs_TE']<1e-8 for x in self.d['integration']['parts']))
 def test_16_keeper_vs_installed_R35_pin_zero(self):self.assertTrue(all(x['keeper_vs_pin']<1e-8 for x in self.d['integration']['parts']))
 def test_17_screw_nominal_clearance_vs_B(self):self.assertTrue(all(x['screw_vs_B']<1e-8 for x in self.d['integration']['parts']))
 def test_18_screw_nominal_clearance_vs_keeper(self):self.assertTrue(all(x['screw_vs_keeper']<1e-8 for x in self.d['integration']['parts']))
 def test_19_pin_head_axial_stop_positive(self):self.assertTrue(all(x['stopped_pin_0p05_overlap']>0.002 for x in self.d['integration']['parts']))
 def test_20_square_nut_does_not_fit_current_B(self):self.assertTrue(all(x['square_nut_catalogue_vs_B']>2.0 for x in self.d['integration']['parts']))
 def test_21_rejected_nut_pocket_records_both_sides(self):self.assertEqual(len(self.d['integration']['rejected_square_nut_pockets']),2)
 def test_22_ten_full_assembly_reference_poses(self):self.assertEqual(self.d['dynamic']['pose_count'],10)
 def test_23_nominal_reference_poses_no_named_clash(self):self.assertTrue(all(not r['unexpected_penetrations_mm3'] for r in self.d['dynamic']['poses']))
 def test_24_pin_is_arrested_by_present_keeper(self):self.assertTrue(self.d['faults']['old_R35_direct_pin_axial_loss_blocked_at_0p05_when_keeper_present'])
 def test_25_screw_can_withdraw_without_thread(self):self.assertTrue(self.d['faults']['M0p8_screw_unthreaded_bore_can_withdraw_without_OCC_contact'])
 def test_26_keeper_can_leave_after_screw(self):self.assertTrue(self.d['faults']['keeper_can_withdraw_after_screw_lost'])
 def test_27_three_stage_failure_remains(self):self.assertTrue(self.d['faults']['after_screw_then_keeper_loss_original_R35_pin_can_be_removed'])
 def test_28_pin_head_shear_is_single_failure(self):self.assertTrue(self.d['faults']['pin_head_shear_defeats_head_only_keeper'])
 def test_29_screw_thread_unimplemented(self):self.assertTrue(self.d['faults']['retaining_screw_tapped_thread_or_nut_engagement_unimplemented'])
 def test_30_catalogue_0p8_ring_not_suitable_for_0p22_pin(self):
  self.assertGreater(self.d['faults']['DIN6799_0p8_application_shaft_diameter_mm'],self.d['faults']['R35_original_shaft_diameter_mm']*5.)
 def test_31_tolerance_configurations_162(self):self.assertEqual(self.d['tolerance']['configurations'],162)
 def test_32_tolerance_intersections_648(self):self.assertEqual(self.d['tolerance']['configurations']*self.d['tolerance']['intersections_per_config'],648)
 def test_33_small_0p02_shank_no_collision(self):self.assertEqual(self.d['tolerance']['aggregation']['0.02']['keeper_M08_shank_hole_jam'],0)
 def test_34_0p05_pin_collision_failure_preserved(self):self.assertGreater(self.d['tolerance']['aggregation']['0.05']['keeper_installed_pin_jam'],0)
 def test_35_0p05_shank_collision_failure_preserved(self):self.assertGreater(self.d['tolerance']['aggregation']['0.05']['keeper_M08_shank_hole_jam'],0)
 def test_36_head_clamping_and_shank_collisions_separated(self):self.assertIn('keeper_M08_head_axial_contact',self.d['tolerance']['aggregation']['0.02'])
 def test_37_old_64_joint_modes(self):self.assertEqual(self.d['faults']['R35_original_fault_states'],64)
 def test_38_old_36_unsafe_survive(self):self.assertEqual(self.d['faults']['R35_original_joint_unsafe'],36)
 def test_39_old_three_single_point_bypasses(self):self.assertEqual(self.d['faults']['electrical_single_bypass'],3)
 def test_40_native_TE_and_screw_STEPS_not_imported(self):
  self.assertFalse(self.d['integration']['vendor_native_STEP_imported'])
  self.assertTrue(metadata()['screw_candidate_catalogue_AABB_only'])
 def test_41_no_battery_or_electronics_geometries(self):self.assertTrue(self.d['integration']['electronics_battery_occupied_envelope_not_imported'])
 def test_42_no_measured_contact_timing(self):self.assertTrue(self.d['faults']['real_force_displacement_contact_timing_not_measured'])
 def test_43_OLED_vendor_missing(self):self.assertTrue(self.d['faults']['OLED_oem_static_width_dynamic_radius_force_fatigue_absent'])
 def test_44_STOW_and_OPEN_fail_closed_missing(self):self.assertTrue(self.d['faults']['STOW_and_OPEN_fail_closed_capture_not_closed'])
 def test_45_step_eight_scenes(self):self.assertEqual(self.d['STEP_manifest']['count'],8)
 def test_46_step_five_ghosts(self):self.assertEqual(self.d['STEP_manifest']['ghosts'],5)
 def test_47_all_STEP_reimports(self):self.assertTrue(all(x['parts']==x['valid_reimport'] for x in self.d['STEP_manifest']['scenes']))
 def test_48_STEP_file_hashes_match(self):
  for x in self.d['STEP_manifest']['scenes']:
   self.assertEqual(hashlib.sha256((ROOT/'cad'/x['file']).read_bytes()).hexdigest(),x['sha256'])
 def test_49_keeper_BREPs_exist(self):
  for side in 'LR':self.assertTrue((ROOT/f'cad/R36_{side}_PIN_HEAD_STOPPER_UNQUALIFIED.brep').is_file())
 def test_50_screw_BREPs_exist(self):
  for side in 'LR':self.assertTrue((ROOT/f'cad/R36_{side}_M0p8x2_CATALOGUE_SCREW_PROXY.brep').is_file())
 def test_51_no_manufacturing_release_in_outputs(self):self.assertTrue(all(x['manufacturing_go'] is False for x in self.d.values()))
 def test_52_no_claim_of_real_thread_connection(self):self.assertTrue(self.d['integration']['screw_assembly_thread_retention_unproven'])
 def test_53_no_force_and_durability_proof(self):self.assertTrue(self.d['faults']['fastener_axial_retention_and_breakaway_force_not_measured'])
 def test_54_only_catalogue_screw_geometry(self):self.assertTrue(metadata()['screw_candidate_catalogue_AABB_only'])
if __name__=='__main__':unittest.main()
