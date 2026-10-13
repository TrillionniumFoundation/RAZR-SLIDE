"""R37 CAD model verification: PASS means failures correctly recognized, NOT safe."""
import unittest,json,hashlib
import cadquery as cq
from r25_capture import ROOT,intersection
from r35_parts import bored_cap,pin,te_signal_envelope
from r36_parts import keeper,catalog_m08x2_screw
from r37_parts import lip,metadata
from r37_freeze import EXPECTED_SHA

class ResearchHardgateR37(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.report={n:json.loads((ROOT/f'verification/R37_{n}.json').read_text())
      for n in ('integration','dynamic','tolerance','faults','catalogue','STEP_manifest')}
  cls.anc=json.loads((ROOT/'audit/R37_R36_immutable.json').read_text())
  cls.B=cq.importers.importBrep(str(ROOT/'cad/R37_B_INTEGRAL_FRONT_STOP_LIPS.brep')).val()
  cls.A=cq.importers.importBrep(str(ROOT/'cad/R37_A_R36_IDENTICAL.brep')).val()
 def test_01_original_977_immutable(self):self.assertEqual(self.anc['immutable_original_files'],977)
 def test_02_source_hash(self):self.assertEqual(self.anc['source_sha256'],EXPECTED_SHA)
 def test_03_original_byte_comparison(self):self.assertTrue(self.anc['all_bytes_identical'])
 def test_04_source_zip_crc(self):self.assertTrue(self.anc['source_zip_crc_ok'])
 def test_05_original_A_exact_bytes(self):self.assertEqual((ROOT/'cad/R37_A_R36_IDENTICAL.brep').read_bytes(),(ROOT/'cad/R36_A_R35_UNCHANGED.brep').read_bytes())
 def test_06_A_and_B_valid(self):self.assertTrue(self.A.isValid() and self.B.isValid())
 def test_07_integral_B_one_solid(self):self.assertEqual(len(self.B.Solids()),1)
 def test_08_two_new_lips(self):self.assertEqual(len(self.report['integration']['lips']),2)
 def test_09_material_actually_added(self):self.assertGreater(self.report['integration']['added_B_volume_mm3'],.06)
 def test_10_each_lip_joined_to_shell(self):self.assertTrue(all(r['root_shell_overlap_mm3']>.01 for r in self.report['integration']['lips']))
 def test_11_cap_at_rest_no_lip_collision(self):self.assertTrue(all(r['cap_installed_overlap_mm3']<1e-9 for r in self.report['integration']['lips']))
 def test_12_forward_pull_new_stop_collision(self):self.assertTrue(all(r['cap_forced_pull_0p05_overlap_mm3']>.004 for r in self.report['integration']['lips']))
 def test_13_lip_does_not_touch_TE_proxy(self):self.assertTrue(all(r['te_gauge_overlap_mm3']==0 for r in self.report['integration']['lips']))
 def test_14_lip_does_not_touch_old_pin(self):self.assertTrue(all(r['original_pin_overlap_mm3']==0 for r in self.report['integration']['lips']))
 def test_15_lip_does_not_touch_R36_untapped_screw(self):self.assertTrue(all(r['R36_M08_screw_overlap_mm3']==0 for r in self.report['integration']['lips']))
 def test_16_pose_count(self):self.assertEqual(self.report['integration']['reference_pose_count'],10)
 def test_17_all_pose_named_proxy_collisions_absent(self):self.assertTrue(all(not r['unexpected_occupied_intersections_mm3'] for r in self.report['integration']['reference_poses']))
 def test_18_existing_front_install_path_rejected(self):self.assertGreater(self.report['dynamic']['original_front_assembly_interfering_positions'],20)
 def test_19_two_currently_healthy_lips_block_0p05(self):self.assertTrue(self.report['dynamic']['forward_motion_0p05_blocked_each_side'])
 def test_20_cannot_claim_snap_or_flex(self):self.assertTrue(self.report['dynamic']['real_snap_installation_not_shown'])
 def test_21_rigid_shift_not_qualified_latch(self):self.assertTrue(self.report['dynamic']['no_valid_spring_deflection_or_overmolding_assembly_sequence'])
 def test_22_162_tolerance_cases(self):self.assertEqual(self.report['tolerance']['configuration_count'],162)
 def test_23_324_tolerance_intersections(self):self.assertEqual(self.report['tolerance']['OCC_intersections'],324)
 def test_24_pm002_install_jams(self):self.assertGreater(self.report['tolerance']['aggregation']['0.02']['installed_clash'],0)
 def test_25_pm005_jams_and_no_stop(self):
  a=self.report['tolerance']['aggregation']['0.05'];self.assertGreater(a['installed_clash'],0);self.assertGreater(a['no_catch_by_0p05'],0)
 def test_26_pm01_stop_failures(self):self.assertGreater(self.report['tolerance']['aggregation']['0.1']['no_catch_by_0p05'],0)
 def test_27_oversimplified_GDT_not_qualified(self):self.assertFalse(self.report['tolerance']['tolerance_relaxed_without_supplier_GDT'])
 def test_28_original_R35_36_unsafe_preserved(self):self.assertEqual(self.report['faults']['previous_legacy_unsafe_mechanical_modes'],36)
 def test_29_original_64_cases_preserved(self):self.assertEqual(self.report['faults']['previous_legacy_mechanical_modes'],64)
 def test_30_three_PCB_power_short_modes_preserved(self):self.assertEqual(self.report['faults']['previous_single_point_electric_bypasses'],3)
 def test_31_single_lip_loss_reexposes_captive_bridge(self):self.assertTrue(self.report['faults']['single_integral_lip_fracture_exposes_that_side'])
 def test_32_independence_from_R36_untapped_screw_geometrically(self):self.assertTrue(self.report['faults']['intact_lip_blocks_cap_with_unthreaded_M08_screw_absent'])
 def test_33_vendor_top_sheet_thicker_than_original(self):self.assertTrue(all(r['thickness_shortfall_mm']>.4 for r in self.report['catalogue']['rows']))
 def test_34_PEM_top_hole_splits_too_narrow_keeper(self):self.assertTrue(all(r['bigger_top_sheet_drill_makes_disconnected_solids']==2 for r in self.report['catalogue']['rows']))
 def test_35_PEM_base_new_drill_oversize(self):self.assertTrue(all(r['base_hole_cut_net_B_volume_loss_mm3']>.4 for r in self.report['catalogue']['rows']))
 def test_36_PEM_direct_drop_in_rejected(self):self.assertFalse(self.report['catalogue']['suitable_existing_assembly'])
 def test_37_vendor_models_not_substituted(self):self.assertFalse(self.report['catalogue']['real_3D_supplier_model_acquired'])
 def test_38_real_material_still_unqualified(self):self.assertTrue(metadata()['no_material_spring_force_or_creep'])
 def test_39_seven_STEP_scenes(self):self.assertEqual(self.report['STEP_manifest']['count'],7)
 def test_40_four_GHOST_scenes(self):self.assertEqual(self.report['STEP_manifest']['ghost_count'],4)
 def test_41_every_STEP_reimported_valid(self):self.assertTrue(all(s['parts']==s['reimported_valid_solids'] for s in self.report['STEP_manifest']['scenes']))
 def test_42_every_STEP_hash_matches(self):
  for s in self.report['STEP_manifest']['scenes']:
   self.assertEqual(hashlib.sha256((ROOT/'cad'/s['file']).read_bytes()).hexdigest(),s['sha256'])
 def test_43_original_power_USB_OLED_not_acquired(self):self.assertTrue(self.report['faults']['OEM_power_USB_OLED_qualification_missing'])
 def test_44_every_result_no_manufacturing_release(self):self.assertTrue(all(v['manufacturing_go'] is False for v in self.report.values()))
 def test_45_live_geometry_cap_pull_positive(self):
  self.assertGreater(intersection(lip('R'),bored_cap('R').translate((0,-.05,0))),.004)
 def test_46_live_geometry_nominal_gap(self):self.assertLess(intersection(lip('L'),bored_cap('L')),1e-9)
 def test_47_predecessor_still_unthreaded(self):self.assertTrue(metadata()['integral_base_instead_of_M08_screw'])
 def test_48_no_physical_pullout_force_test(self):self.assertTrue(self.report['faults']['physical_pullout_force_not_measured'])
if __name__=='__main__':unittest.main()
