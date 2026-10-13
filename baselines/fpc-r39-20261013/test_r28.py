"""R28 evidence-checked adversarial OCC RESEARCH tests. PASS != manufacturing."""
from __future__ import annotations
import hashlib,json,unittest
import cadquery as cq
from r25_capture import ROOT,P,intersection,to_global
from r22_mechanics import to_blocal
from r28_retraction import pullback_gate,carrier_with_pin,theoretical_extension,CAM_DWELL_MM,OPEN_GATE_STROKE
from r28_presence import blocker,pawl_transit,SENSE_RISE_MM
from r27_power_faults import evaluate,NAMES

V=ROOT/'verification'
class TestR28SafeResearch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.i=json.loads((V/'R28_integration.json').read_text())
  cls.d=json.loads((V/'R28_dynamic.json').read_text())
  cls.f=json.loads((V/'R28_faults.json').read_text())
  cls.t=json.loads((V/'R28_tolerance.json').read_text())
  cls.p=json.loads((V/'R28_presence.json').read_text())
  cls.m=json.loads((V/'R28_STEP_manifest.json').read_text())
  cls.c=json.loads((V/'R28_clearance.json').read_text())
  cls.A=cq.importers.importBrep(str(ROOT/'cad/R28_A_KEYED_UNCHANGED.brep')).val()
  cls.B=cq.importers.importBrep(str(ROOT/'cad/R28_B_PULLOUT_CAM_RELIEVED.brep')).val()
 def test_01_cam_gate_single_solid_each_side(self):
  for s in 'LR':
   for t in (0.,.45,.9):
    v=pullback_gate(s,t);self.assertTrue(v.isValid());self.assertEqual(len(v.Solids()),1)
 def test_02_carrier_pin_monolithic(self):
  for s in 'LR':
   for e in (0.,.4,.8):
    v=carrier_with_pin(s,e);self.assertTrue(v.isValid());self.assertEqual(len(v.Solids()),1)
 def test_03_dwell_state_retraction_is_zero(self):
  for t in (0.,.1,.2,CAM_DWELL_MM):self.assertAlmostEqual(theoretical_extension(t),0.,places=9)
 def test_04_endstate_full_open_relation(self):self.assertAlmostEqual(theoretical_extension(OPEN_GATE_STROKE),.8,places=8)
 def test_05_intermediate_relation(self):self.assertAlmostEqual(theoretical_extension(.63),.4,places=8)
 def test_06_nominal_path_38_witnesses(self):
  self.assertEqual(self.f['trajectory_samples'],38)
  for r in self.f['real_Occ_shutter_and_pin_trajectory']:
   self.assertEqual(len(r['nominal_dwell_and_pullback']),19)
   for p in r['nominal_dwell_and_pullback']:
    self.assertTrue(p['physically_one_piece_gate']);self.assertTrue(p['physically_one_piece_carrier_and_pin'])
    self.assertLess(p['gate_pin_carrier_interference_mm3'],1e-7)
 def test_07_closed_unextended_clear(self):
  for side in 'LR':self.assertLess(intersection(pullback_gate(side,0.),carrier_with_pin(side,0.)),1e-8)
 def test_08_closed_partly_extended_blocked(self):
  for side in 'LR':self.assertGreater(intersection(pullback_gate(side,0.),carrier_with_pin(side,.15)),.001)
 def test_09_closed_fully_extended_blocked(self):
  for side in 'LR':self.assertGreater(intersection(pullback_gate(side,0.),carrier_with_pin(side,.8)),.01)
 def test_10_open_fully_extended_clear(self):
  for side in 'LR':self.assertLess(intersection(pullback_gate(side,.9),carrier_with_pin(side,.8)),1e-8)
 def test_11_nominal_midstroke_clear(self):
  for side in 'LR':self.assertLess(intersection(pullback_gate(side,.63),carrier_with_pin(side,.4)),1e-8)
 def test_12_stuck_full_carrier_causes_unsafe_gate_jam(self):
  for side in self.f['real_Occ_shutter_and_pin_trajectory']:
   self.assertEqual(side['held_carrier_fault_scan'][0]['OCC_jam_mm3'],0.)
   self.assertGreater(side['held_carrier_fault_scan'][-1]['OCC_jam_mm3'],.01)
 def test_13_real_force_spring_pins_unqualified(self):
  self.assertTrue(self.f['stuck_carrier_causes_JAM_not_demonstrated_safe_retraction'])
  self.assertTrue(self.f['pin_is_not_axially_captive_no_backing_clips_or_screws'])
 def test_14_inherited_joint_faults_64(self):self.assertEqual(self.f['original_fault_family_cases'],64)
 def test_15_inherited_joint_escapes_36(self):self.assertEqual(self.f['original_fault_escape_counterexamples'],36)
 def test_16_extended_faults_are_never_success_certificates(self):
  self.assertEqual(self.f['R28_extended_fault_family_cases'],256)
  self.assertGreater(self.f['R28_extended_hazard_heuristic_cases'],200)
 def test_17_AB_valid_single_solid(self):
  self.assertTrue(self.i['A_valid_single_body'] and self.i['B_valid_single_body'])
  self.assertEqual(len(self.A.Solids()),len(self.B.Solids()))
 def test_18_four_real_boolean_pockets(self):
  self.assertEqual(self.i['cut_count'],4)
  self.assertTrue(all(x['new_shell_valid'] and x['new_shell_solids']==1 for x in self.i['cuts']))
  self.assertGreater(self.i['additional_B_removed_mm3'],3.)
 def test_19_front_boundary_margin_is_not_approved(self):
  self.assertLessEqual(self.i['presumed_min_front_B_margin_after_relief_mm'],.015001)
  self.assertTrue(self.i['near_boundary_hypothetical_lip_unqualified'])
 def test_20_r24_old_rail_web_unqualified(self):self.assertTrue(self.i['inherited_R24_0p22mm_side_rail_unqualified'])
 def test_21_ten_full_nominal_poses(self):
  self.assertEqual(self.d['pose_count'],10)
  self.assertEqual(self.d['unexpected_collision_count'],0)
 def test_22_actual_A_NO_clash_nominal_gate(self):
  for s in 'LR':
   for t in (0.,.9):self.assertLess(intersection(self.A,to_global(pullback_gate(s,t),'OPEN',P.travel,P.z_travel)),1e-7)
 def test_23_tolerance_configs_and_occ_samples(self):
  self.assertEqual(self.t['samples'],108);self.assertEqual(self.t['OCC_checks'],324)
 def test_24_hypothetical_0p02_all_coupled_configs_clear(self):
  self.assertEqual(self.t['groups'][0]['reported_nominal_coupled_motion_jam'],0)
 def test_25_hypothetical_0p05_shows_failures(self):
  self.assertGreaterEqual(self.t['groups'][1]['reported_nominal_coupled_motion_jam'],45)
 def test_26_presence_missing_A_blocks_partial_pawl_stroke(self):
  for s in 'LR':self.assertGreater(intersection(blocker(s,0.),pawl_transit(s,.3)),.001)
 def test_27_presence_retracted_releases_pawl_path(self):
  for s in 'LR':self.assertLess(intersection(blocker(s,SENSE_RISE_MM),pawl_transit(s,.3)),1e-8)
 def test_28_presence_rejected_due_to_B_thickness(self):
  self.assertGreater(self.p['raised_plunger_exceeds_B_nominal_envelope_by_mm'],.7)
  self.assertTrue(self.p['candidate_rejected_not_integrated_into_B'])
 def test_29_presence_no_actual_spring_return(self):self.assertFalse(self.p['actually_spring_loaded'])
 def test_30_power_zero_fault_logic_NOT_hardware_evidence(self):self.assertFalse(evaluate((False,)*len(NAMES)))
 def test_31_power_single_bypass_is_dangerous(self):
  for k in (6,7,8):
   inp=[False]*len(NAMES);inp[k]=True;self.assertTrue(evaluate(inp))
 def test_32_new_Steps_reimported_and_hashes(self):
  self.assertEqual(self.m['scene_count'],6)
  for x in self.m['scenes']:
   f=ROOT/'cad'/x['filename'];self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(),x['sha256'])
   self.assertEqual(x['exported_parts'],x['valid_imported_solids'])
 def test_33_stuck_fault_STEP_explicit_collision(self):
  r=next(x for x in self.m['scenes'] if x['scene'].startswith('04'))
  self.assertTrue(r['ghost_known_failure']);self.assertTrue(all(v>.01 for v in r['endstate_overlap_mm3'].values()))
 def test_34_presence_rejected_STEP_20_parts(self):
  r=next(x for x in self.m['scenes'] if x['scene'].startswith('06'))
  self.assertTrue(r['ghost_known_failure']);self.assertEqual(r['exported_parts'],20)
 def test_35_no_manufacturing_promotion_any_report(self):
  for r in (self.i,self.d,self.f,self.t,self.p,self.m):self.assertIs(r['manufacturing_go'],False)
 def test_36_OLED_full_package_still_unknown(self):self.assertTrue(self.d['true_oled_full_stack_missing'])
 def test_37_real_spring_mount_qualified_false(self):self.assertTrue(self.i['no_machinable_bearing_anchor_screw_boss_FEA'])
 def test_38_faults_early_false_capture_remains(self):self.assertTrue(self.f['absent_A_pawl_false_capture_STILL_undefeated'])

 def test_39_cam_actual_plate_is_extremely_thin(self):
  self.assertLess(self.c['original_outboard_plate_X_thickness_mm'],.1)
 def test_40_slots_have_only_0p058_nominal_end_web(self):
  self.assertLessEqual(self.c['planar_slot_min_residual_Z_web_mm'],.058001)
 def test_41_A_side_key_hit_at_outward_0p05(self):
  self.assertEqual(self.c['outward_0p05_nominal_A_collision_cases'],4)
 def test_42_A_side_key_clear_at_outward_0p02(self):
  self.assertEqual(self.c['outward_0p02_nominal_A_collision_cases'],0)

if __name__=='__main__':unittest.main()
