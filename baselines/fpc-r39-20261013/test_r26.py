"""R26 falsification-focused tests. PASS = only statements about a CAD proxy, never hardware qualification.
Recompute all R26 evidence by r26_checks.sh first; no stale packaged-JSON acceptance.
"""
import cadquery as cq
from pathlib import Path
import unittest,hashlib,json
from r25_capture import ROOT,P,intersection,to_global,pawl as old_pawl
from r26_open_mechanics import open_pawl,open_gate,open_carrier_ear,OPEN_GATE_STROKE
from r24_mechanics import outboard_jaws,INBOARD_OLED_X_HALF
from r22_mechanics import to_blocal
V=ROOT/'verification'
class R26Checks(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.A=cq.importers.importBrep(str(ROOT/'cad'/'R26_A_UNCHANGED.brep')).val()
  cls.B=cq.importers.importBrep(str(ROOT/'cad'/'R26_B_INBOARD_PAWL_OPEN_GATE_CUT.brep')).val()
  cls.integration=json.loads((V/'R26_integration.json').read_text())
  cls.dynamic=json.loads((V/'R26_dynamic.json').read_text())
  cls.faults=json.loads((V/'R26_faults.json').read_text())
  cls.tolerance=json.loads((V/'R26_tolerance.json').read_text())
  cls.steps=json.loads((V/'R26_STEP_manifest.json').read_text())
 def test_01_previous_R25_outboard_park_hits_full_A_shell(self):
  for side in 'LR':self.assertGreater(intersection(self.A,to_global(old_pawl('OPEN',side,False),'OPEN',P.travel,P.z_travel)),.020)
 def test_02_R26_inboard_park_no_longer_hits_complete_A_shell(self):
  for side in 'LR':self.assertLess(intersection(self.A,to_global(open_pawl(side,False),'OPEN',P.travel,P.z_travel)),1e-8)
 def test_03_R26_two_distinct_capture_states(self):
  for side in 'LR':self.assertGreater(abs(open_pawl(side,True).BoundingBox().xmin-open_pawl(side,False).BoundingBox().xmin),.54)
 def test_04_OPEN_stage2_gate_a_real_single_OCC_solid(self):
  for side in 'LR':
   for shift in (0.,.2,.9):
    a=open_gate(side,shift);self.assertTrue(a.isValid());self.assertEqual(len(a.Solids()),1)
 def test_05_OPEN_carrier_lower_load_path_a_real_single_OCC_solid(self):
  for side in 'LR':
   for ext in (0.,.15,.8):
    a=open_carrier_ear(side,ext);self.assertTrue(a.isValid());self.assertEqual(len(a.Solids()),1)
 def test_06_all_OPEN_gate_solid_inside_original_B_envelope(self):
  for side in 'LR':
   for shift in (0.,.9):
    b=to_blocal(open_gate(side,shift),'OPEN').BoundingBox()
    self.assertGreaterEqual(b.ymin,-1e-8);self.assertLessEqual(b.ymax,94.25+1e-8)
    self.assertGreaterEqual(b.zmin,-1e-8);self.assertLessEqual(b.zmax,7.2+1e-8)
    self.assertLessEqual(max(abs(b.xmin),abs(b.xmax)),36.995+1e-8)
 def test_07_closed_gate_has_no_collision_with_retracted_lower_ear(self):
  for side in 'LR':self.assertLess(intersection(open_gate(side,0),open_carrier_ear(side,0.)),1e-8)
 def test_08_closed_gate_blocks_intermediate_0p15_extension(self):
  for side in 'LR':self.assertGreater(intersection(open_gate(side,0),open_carrier_ear(side,.15)),1e-4)
 def test_09_fully_open_gate_allows_ext_0p15_and_ext_0p8(self):
  for side in 'LR':
   for ext in (.15,.8):self.assertLess(intersection(open_gate(side,.9),open_carrier_ear(side,ext)),1e-8)
 def test_10_parked_pawl_closed_gate_not_prejammed(self):
  for side in 'LR':self.assertLess(intersection(open_gate(side,0),open_pawl(side,False)),1e-8)
 def test_11_parked_pawl_interferes_0p2_manual_release(self):
  for side in 'LR':self.assertGreater(intersection(open_gate(side,.2),open_pawl(side,False)),1e-4)
 def test_12_captured_pawl_allows_entire_sampled_gate_path(self):
  for side in 'LR':
   for shift in (0.,.1,.2,.4,.6,.9):self.assertLess(intersection(open_gate(side,shift),open_pawl(side,True)),1e-8)
 def test_13_stationary_R24_jaw_plane_separation_still_holds(self):
  for side in 'LR':
   for jaw_shift in (0.,.4,1.,2.):
    jaw=outboard_jaws({s:jaw_shift for s in 'LR'})[f'B_R24_OUTBOARD_JAW_{side}']
    for gate_shift in (0.,.3,.9):self.assertLess(intersection(jaw,open_gate(side,gate_shift)),1e-8)
 def test_14_R26_close_after_already_extended_is_unsafe(self):
  self.assertTrue(self.faults['R26_stage2_gate_held_CLOSED_at_0p8_extension_does_not_physically_overlap'])
  for side in 'LR':self.assertLess(intersection(open_gate(side,0),open_carrier_ear(side,.8)),1e-8)
 def test_15_swept_motion_not_merely_endpoint(self):
  for x in self.faults['geometric']:
   sw=x['sweep_carrier_ext_mm'];self.assertEqual(sw[0]['clash_mm3'],0.)
   self.assertGreater(sum(t['clash_mm3']>1e-9 for t in sw),10)
 def test_16_safety_pawl_veto_applies_to_partial_sweep(self):
  for x in self.faults['geometric']:
   self.assertEqual(x['sweep_gate_shift_mm'][0]['veto_when_pawl_parked_mm3'],0.)
   self.assertTrue(any(t['veto_when_pawl_parked_mm3']>1e-5 for t in x['sweep_gate_shift_mm']))
 def test_17_full_A_B_OCC_shell_are_connected(self):
  self.assertTrue(self.A.isValid());self.assertEqual(len(self.A.Solids()),1)
  self.assertTrue(self.B.isValid());self.assertEqual(len(self.B.Solids()),1)
 def test_18_six_actual_B_cuts_with_nonzero_material_removed(self):
  v=self.integration;self.assertEqual(v['new_pockets'],6)
  self.assertTrue(all(t['newly_removed_B_mm3']>0 for t in v['pockets']))
 def test_19_B_removed_material_is_finite(self):
  self.assertGreater(self.integration['additional_B_cut_vs_R25_mm3'],5)
  self.assertLess(self.integration['additional_B_cut_vs_R25_mm3'],7)
 def test_20_unapproved_OLED_proximity_is_explicit(self):
  self.assertLess(self.dynamic['OPEN_gate_min_assumed_OLED_outer_edge_nominal_gap_mm'],.15)
  self.assertTrue(self.dynamic['OEM_OLED_width_material_tolerance_missing'])
 def test_21_top_lid_margin_remains_unqualified(self):
  self.assertLess(self.dynamic['OPEN_gate_native_shell_top_clearance_mm'],.12)
 def test_22_ten_nominal_poses_no_fatal_intersections_of_selected_solids(self):
  self.assertEqual(self.dynamic['pose_count'],10);self.assertEqual(self.dynamic['unexpected_count'],0)
 def test_23_all_NEW_R26_parked_poses_hypothetically_no_OLED_A_clash(self):
  rows=[x for x in self.dynamic['per_part_clashes'] if x.get('part')=='OPEN_PAWL_PARK']
  self.assertEqual(len(rows),20)
  self.assertTrue(all(x['clashes']['A']<1e-8 and x['clashes']['OLED']<1e-8 for x in rows))
 def test_24_new_nonOEM_pt02_park_gate_sweep_targeted_checks(self):
  g=self.tolerance['groups'][0];self.assertEqual(g['parked_pawl_cases'],54);self.assertEqual(g['ear_cases'],54)
  self.assertFalse(any(v for k,v in g.items() if k in ('A_shell_collision_at_seat','false_jam_gate_stays_closed','parked_pawl_fails_to_block_open_attempt_0p2','gate_jams_fully_retracted_carrier','gate_fails_arrest_carrier_at_ext_0p15')))
 def test_25_new_nonOEM_pt05_park_gate_sweep_targeted_checks(self):
  g=self.tolerance['groups'][1];self.assertEqual(g['parked_pawl_cases'],54);self.assertEqual(g['ear_cases'],54)
  self.assertFalse(any(v for k,v in g.items() if k in ('A_shell_collision_at_seat','false_jam_gate_stays_closed','parked_pawl_fails_to_block_open_attempt_0p2','gate_jams_fully_retracted_carrier','gate_fails_arrest_carrier_at_ext_0p15')))
 def test_26_still_216_NEW_independent_stress_observations(self):
  self.assertEqual(len(self.tolerance['rows']),216)
 def test_27_capture_original_tolerance_still_fails(self):
  g=json.loads((V/'R25_tolerance.json').read_text())['groups']
  self.assertGreater(g[0]['no_0p05_retention_contact'],0)
  self.assertGreater(g[1]['clashes_at_seat'],0)
 def test_28_old_R24_cam_still_unlocks_early(self):
  self.assertTrue(self.faults['undocked_old_R24_cam_still_early_clear'])
 def test_29_64_six_axis_joint_faults_with_unresolved_escape(self):
  self.assertEqual(self.faults['total_modeled_joint_fault_combinations'],64)
  self.assertGreater(self.faults['undocked_R26_second_gate_absent_or_broken_escape_rows'],0)
 def test_30_no_mechanical_prevent_false_pawl_capture_yet(self):
  self.assertTrue(self.faults['physically_prevent_FALSE_CAPTURE_fully_unbuilt'])
 def test_31_no_actuator_springs_bearings_qualifications(self):
  self.assertTrue(self.integration['true_mounting_guides_retention_spring_screws_unbuilt'])
 def test_32_new_OCC_without_FEA_is_not_load_certificate(self):
  self.assertTrue(self.integration['FEA_drop_torque_fatigue_and_corrosion_unverified'])
 def test_33_no_B_power_electric_safety_certificate(self):
  self.assertFalse(self.faults['power_HW_qualified']);self.assertTrue(self.faults['exposed_pad_battery_short_bypass_unmitigated'])
 def test_34_no_OLED_qualified_vendor_stack(self):
  self.assertFalse(self.faults['OLED_OEM_qualified'])
 def test_35_R26_exports_ten_STEP_real_reimport(self):
  self.assertEqual(self.steps['exported_scenes'],10)
  for item in self.steps['scenes']:
   p=ROOT/'cad'/item['STEP']
   self.assertTrue(p.exists());self.assertEqual(item['parts'],item['valid_solids_reimported'])
   self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),item['sha256'])
 def test_36_fault_ghost_export_explicit(self):
  self.assertGreaterEqual(sum(x['deliberate_fault_GHOST'] for x in self.steps['scenes']),5)
 def test_37_real_OLED_no_OEM_and_7_inch_constraints_preserved(self):
  self.assertTrue(all(x['OEM_OLED_not_present'] for x in self.steps['scenes']))
 def test_38_manufacturing_NOGO_all_r26_results(self):
  for v in (self.integration,self.dynamic,self.faults,self.tolerance,self.steps):self.assertIs(v['manufacturing_go'],False)
if __name__=='__main__':unittest.main()
