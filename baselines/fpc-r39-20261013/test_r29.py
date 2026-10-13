"""R29 adversarial research regressions; passing is NOT manufacture permission."""
from __future__ import annotations
import json,hashlib,unittest
from pathlib import Path
from r25_capture import ROOT,intersection
from r29_mechanics import (pullback_gate,carrier_with_pin,theoretical_extension,
                           nominal_planar_webs,OPEN_GATE_STROKE)

class R29Adversarial(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.j={k:json.loads((ROOT/'verification'/f'R29_{k}.json').read_text()) for k in
    ('integration','dynamic','faults','tolerance','clearance','presence','ear_section','STEP_manifest')}
  cls.r28=json.loads((ROOT/'verification'/'R28_results.json').read_text())
  cls.orig=json.loads((ROOT/'audit'/'R28_SHA256_MANIFEST.json').read_text())

 def test_01_two_valid_gates(self):
  for s in 'LR':
   a=pullback_gate(s,0.); self.assertTrue(a.isValid());self.assertEqual(len(a.Solids()),1)
 def test_02_two_valid_carriers(self):
  for s in 'LR':
   a=carrier_with_pin(s,0.);self.assertTrue(a.isValid());self.assertEqual(len(a.Solids()),1)
 def test_03_ideal_dwell(self):self.assertEqual(theoretical_extension(.36),0.)
 def test_04_ideal_end(self):self.assertAlmostEqual(theoretical_extension(.9),.8)
 def test_05_ideal_mid(self):self.assertAlmostEqual(theoretical_extension(.63),.4)
 def test_06_nominal_centerline_clear(self):
  for s in 'LR':
   for t in (0.,.45,.9):self.assertLess(intersection(pullback_gate(s,t),carrier_with_pin(s,theoretical_extension(t))),1e-8)
 def test_07_nominal_plate_thickness_improved(self):self.assertGreater(nominal_planar_webs()['plate_X_mm'],.085)
 def test_08_nominal_slot_Z_web_improved(self):self.assertGreater(min(nominal_planar_webs()['slot_end_Z_web_top_mm'],nominal_planar_webs()['slot_end_Z_web_bottom_mm']),.058)
 def test_09_front_lip_still_unqualified(self):self.assertLess(nominal_planar_webs()['front_Y_wall_after_0p025mm_cut_mm'],.1)
 def test_10_larger_backlash_not_certified(self):self.assertGreater(nominal_planar_webs()['pin_slot_radial_clearance_mm'],.032)
 def test_11_AB_valid(self):
  self.assertTrue(self.j['integration']['valid_single_A']);self.assertTrue(self.j['integration']['valid_single_B'])
 def test_12_shell_cut_in_actual_B(self):self.assertGreater(self.j['integration']['additional_B_removed_mm3'],0.)
 def test_13_four_real_boolean_pockets(self):self.assertEqual(len(self.j['integration']['subtractions']),4)
 def test_14_exact_R28_baseline_SHA(self):
  self.assertEqual(self.j['integration']['source_R28_B_SHA256'],self.r28['R28_A_B_BRep_SHA256']['R28_B_PULLOUT_CAM_RELIEVED.brep'])
 def test_15_ten_motion_poses(self):self.assertEqual(self.j['dynamic']['pose_count'],10)
 def test_16_reference_poses_no_overlap(self):self.assertEqual(self.j['dynamic']['unexpected_collision_count'],0)
 def test_17_true_OLED_missing(self):self.assertTrue(self.j['dynamic']['true_oled_full_stack_missing'])
 def test_18_clearance_scan_sample_count(self):self.assertEqual(self.j['clearance']['samples'],20)
 def test_19_outboard_0p05_no_A_clashes(self):self.assertEqual(self.j['clearance']['clashes_at_plus_0p05'],0)
 def test_20_108_exact_tolerance_configs(self):self.assertEqual(self.j['tolerance']['samples'],108)
 def test_21_324_OCC_checks(self):self.assertEqual(self.j['tolerance']['OCC_checks'],324)
 def test_22_0p02_nominal_scan_no_jam(self):self.assertEqual(self.j['tolerance']['summary'][0]['jam_configs'],0)
 def test_23_0p05_nominal_scan_no_jam(self):self.assertEqual(self.j['tolerance']['summary'][1]['jam_configs'],0)
 def test_24_no_positive_drive_proof(self):self.assertTrue(self.j['tolerance']['endpoint_force_or_contact_engagement_unverified'])
 def test_25_38_nominal_fault_witnesses(self):self.assertEqual(self.j['faults']['prescribed_pose_count'],38)
 def test_26_38_nominal_poses_clean(self):self.assertTrue(self.j['faults']['all_prescribed_nominal_geometries_valid'])
 def test_27_inherited_36_common_escapes(self):self.assertEqual(self.j['faults']['inherited_original_fault_escape_counterexamples'],36)
 def test_28_false_capture_not_prevented(self):self.assertFalse(self.j['faults']['prevent_false_capture_when_no_A'])
 def test_29_stuck_force_not_safely_retracted(self):self.assertFalse(self.j['faults']['powered_contact_jam_force_safe'])
 def test_30_loaded_carrier_static_interference(self):
  self.assertTrue(all(x['closed_gate_clash_mm3']>1e-8 for x in self.j['faults']['closed_gate_lost_motion'] if x['extension_mm']==.8))
 def test_31_unpowered_late_release_unknown(self):self.assertTrue(self.j['faults']['bearing_pin_shear_spring_retention_and_brake_unverified'])
 def test_32_presence_candidate_fits_B_but_hits_A(self):
  self.assertFalse(self.j['presence']['outside_B_envelope']);self.assertTrue(self.j['presence']['raised_plunger_interferes_with_A_at_final_seat'])
 def test_33_presence_not_integrated(self):self.assertTrue(self.j['presence']['candidate_rejected_not_integrated'])
 def test_34_original_ear_material_removed(self):self.assertTrue(all(x['removed_original_material_mm3']>0 for x in self.j['ear_section']['rows']))
 def test_35_original_ear_section_unqualified(self):self.assertTrue(self.j['ear_section']['minimum_cross_section_FEA_missing'])
 def test_36_original_ear_still_one_connected(self):self.assertTrue(all(x['one_connected_valid'] for x in self.j['ear_section']['rows']))
 def test_37_all_STEP_6_reimported(self):
  step=self.j['STEP_manifest'];self.assertEqual(step['scene_count'],6)
  for x in step['scenes']:self.assertEqual(x['valid_imported_solids'],x['exported_parts'])
 def test_38_STEP_member_checksums(self):
  for x in self.j['STEP_manifest']['scenes']:
   self.assertEqual(hashlib.sha256((ROOT/'cad'/x['filename']).read_bytes()).hexdigest(),x['sha256'])
 def test_39_R28_original_member_count(self):self.assertEqual(len(self.orig['entries']),374)
 def test_40_no_manufacturing_go_in_any_new_report(self):
  self.assertTrue(all(d['manufacturing_go'] is False for d in self.j.values()))

if __name__=='__main__':unittest.main()
