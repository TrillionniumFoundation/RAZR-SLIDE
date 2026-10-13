"""R27 adversarial CAD-only safety tests. PASS != hardware qualification.

Important: explicit assertions which REQUIRE known unsafe states to remain
UNQUALIFIED are passing tests; they are not safety barrier approvals.
"""
import hashlib,json,unittest
from pathlib import Path
import cadquery as cq
from r25_capture import ROOT,P,intersection,to_global
from r27_mechanics import open_gate_captive,swept_first_contact
from r26_open_mechanics import open_gate,open_carrier_ear,open_pawl
from r22_mechanics import to_blocal
from r27_power_faults import NAMES,evaluate
V=ROOT/'verification'
class R27SafetyResearch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.i=json.loads((V/'R27_integration.json').read_text())
  cls.f=json.loads((V/'R27_faults.json').read_text())
  cls.t=json.loads((V/'R27_tolerance.json').read_text())
  cls.d=json.loads((V/'R27_dynamic.json').read_text())
  cls.e=json.loads((V/'R27_power_faults.json').read_text())
  cls.m=json.loads((V/'R27_STEP_manifest.json').read_text())
  cls.A=cq.importers.importBrep(str(ROOT/'cad/R27_A_KEYED_UNCHANGED.brep')).val()
  cls.B=cq.importers.importBrep(str(ROOT/'cad/R27_B_CAPTIVE_OPEN_GATE_CUT.brep')).val()
 def test_01_new_gate_valid_one_solid_both_sides(self):
  for s in 'LR':
   for shift in (0.,.2,.45,.9):
    g=open_gate_captive(s,shift);self.assertTrue(g.isValid());self.assertEqual(len(g.Solids()),1)
 def test_02_old_gate_misses_fully_extended_carrier_endstate(self):
  for s in 'LR':self.assertLess(intersection(open_gate(s,0.),open_carrier_ear(s,.8)),1e-9)
 def test_03_new_gate_arrests_full_extension_endstate(self):
  for s in 'LR':self.assertGreater(intersection(open_gate_captive(s,0.),open_carrier_ear(s,.8)),.02)
 def test_04_retracted_carrier_is_clear_when_locked(self):
  for s in 'LR':self.assertLess(intersection(open_gate_captive(s,0.),open_carrier_ear(s,0.)),1e-9)
 def test_05_new_gate_intercepts_partial_extension_0p15(self):
  for s in 'LR':self.assertGreater(intersection(open_gate_captive(s,0.),open_carrier_ear(s,.15)),.005)
 def test_06_new_gate_open_allows_full_extension(self):
  for s in 'LR':self.assertLess(intersection(open_gate_captive(s,.9),open_carrier_ear(s,.8)),1e-9)
 def test_07_open_gate_ear_0p15_clear(self):
  for s in 'LR':self.assertLess(intersection(open_gate_captive(s,.9),open_carrier_ear(s,.15)),1e-9)
 def test_08_gate_first_swept_contact_sample_within_0p07_to_0p08(self):
  for g in self.f['geometry']:
   self.assertGreaterEqual(g['R27_first_sampled_contact_mm'],.070)
   self.assertLessEqual(g['R27_first_sampled_contact_mm'],.078)
   s=g['side']
   self.assertLess(intersection(open_gate_captive(s,0.),open_carrier_ear(s,.06)),1e-9)
   self.assertGreater(intersection(open_gate_captive(s,0.),open_carrier_ear(s,.08)),1e-8)
 def test_09_park_pawl_without_A_still_stops_manual_gate_motion(self):
  for s in 'LR':self.assertGreater(intersection(open_gate_captive(s,.2),open_pawl(s,False)),1e-4)
 def test_10_park_pawl_not_occupying_closed_position(self):
  for s in 'LR':self.assertLess(intersection(open_gate_captive(s,0.),open_pawl(s,False)),1e-9)
 def test_11_captured_pawl_allows_open_gate_path_sampled(self):
  for s in 'LR':
   for t in (0.,.2,.45,.9):self.assertLess(intersection(open_gate_captive(s,t),open_pawl(s,True)),1e-9)
 def test_12_new_gate_fits_equal_B_nominal_envelope(self):
  for s in 'LR':
   for t in (0.,.9):
    b=to_blocal(open_gate_captive(s,t),'OPEN').BoundingBox()
    self.assertGreaterEqual(b.ymin,0);self.assertLessEqual(b.ymax,94.25)
    self.assertGreaterEqual(b.zmin,0);self.assertLessEqual(b.zmax,7.2)
    self.assertLessEqual(max(abs(b.xmin),abs(b.xmax)),36.995)
 def test_13_gate_nominal_no_A_shell_overlap_seated(self):
  for s in 'LR':
   for t in (0.,.9):self.assertLess(intersection(self.A,to_global(open_gate_captive(s,t),'OPEN',P.travel,P.z_travel)),1e-8)
 def test_14_R27_A_B_valid_and_connected(self):
  self.assertTrue(self.A.isValid() and self.B.isValid());self.assertEqual(len(self.A.Solids()),1);self.assertEqual(len(self.B.Solids()),1)
 def test_15_A_reused_B_internal_preexisting_recess_no_new_cut(self):
  self.assertTrue(self.i['A_unmodified']);self.assertEqual(self.i['pocket_count'],2)
  self.assertEqual(self.i['additional_cut_over_R26_mm3'],0)
  self.assertTrue(self.i['all_shells_one_valid_body'])
 def test_16_no_unqualified_claim_of_new_guide_support(self):
  self.assertTrue(self.i['no_mounting_boss_screw_preload_or_return_spring'])
 def test_17_fault_r27_closed_all_steps_0p15_to_0p8(self):
  for g in self.f['geometry']:
   for p in g['sweep']:
    if p['extension_mm']>=.16:
     self.assertGreater(p['R27_closed_overlap_mm3'],1e-8)
 def test_18_open_swept_carrier_0p8_no_overlap(self):
  for g in self.f['geometry']:
   for p in g['sweep']:self.assertLess(p['R27_open_overlap_mm3'],1e-8)
 def test_19_old_endstate_safety_defect_witnessed(self):
  for g in self.f['geometry']:
   self.assertTrue(g['old_end_point_bypass_at_ext_0p8'])
   self.assertGreater(g['R27_endpoint_captive_contact_mm3'],0.)
 def test_20_64_joint_failures_still_36_escapes(self):
  self.assertEqual(self.f['joint_fault_cases'],64);self.assertEqual(self.f['joint_fault_escape_cases'],36)
 def test_21_false_capture_without_A_still_unresolved(self):
  self.assertTrue(self.f['absent_A_false_pawl_capture_not_mechanically_excluded'])
 def test_22_carrier_preextended_may_physically_jam_not_force_retract(self):
  self.assertTrue(self.f['pressed_extended_carrier_may_JAM_instead_of_force_RETRACT'])
 def test_23_r27_tolerance_hypothetical_two_widths(self):
  self.assertEqual(self.t['samples'],108);self.assertEqual([x['cases'] for x in self.t['groups']],[54,54])
 def test_24_r27_finite_tolerance_partial_witnesses_pass(self):
  for g in self.t['groups']:
   self.assertEqual(g['fully_retracted_false_jam_count'],0)
   self.assertEqual(g['fails_to_intercept_ext_0p15_count'],0)
   self.assertEqual(g['fails_to_intercept_ext_0p8_count'],0)
   self.assertEqual(g['fully_open_false_jam_0p8_count'],0)
 def test_25_10_nominal_reference_pose_samples(self):
  self.assertEqual(self.d['pose_count'],10);self.assertEqual(self.d['unexpected_collision_count'],0)
 def test_26_OLED_nominal_gap_unqualified_and_lid_thin(self):
  self.assertLess(self.d['nominal_OLED_edge_gap_worst_from_inherited_OPEN_gate_mm'],.15)
  self.assertLess(self.d['nominal_B_top_clearance_worst_inherited_R26_mm'],.12)
  self.assertTrue(self.d['OLED_edge_and_full_encapsulation_not_OEM_qualified'])
 def test_27_power_faults_all_512_states_evaluated(self):
  self.assertEqual(self.e['enumerated_fault_states'],512)
  self.assertGreater(self.e['dangerous_states'],0)
 def test_28_power_when_all_contact_isolators_off_theory(self):
  self.assertFalse(evaluate((False,)*len(NAMES)))
 def test_29_single_bypass_still_dangerous_architecture(self):
  for idx in (6,7,8):
   bits=[False]*len(NAMES);bits[idx]=True
   self.assertTrue(evaluate(bits))
 def test_30_power_minimal_fault_cut_sets_identified(self):
  self.assertEqual(len(self.e['minimal_cut_sets']),7)
  self.assertEqual(len(self.e['one_fault_dangerous_minimal_cuts']),3)
 def test_31_no_real_electrical_USB_or_OLED_conformance(self):
  self.assertTrue(self.e['no_real_hardware_qualifying_results'])
  self.assertTrue(self.e['independent_USB2_USB3_CC_pinout_and_SI_not_verified'])
 def test_32_twelve_real_STEP_imports_and_hash_match(self):
  self.assertEqual(self.m['exported_scenes'],12)
  for r in self.m['scenes']:
   p=ROOT/'cad'/r['STEP'];self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),r['sha256'])
   self.assertEqual(r['parts'],r['valid_solids_reimported']);self.assertEqual(r['parts'],18)
 def test_33_explicit_preextended_gate_ghost_is_contacting(self):
  r=next(x for x in self.m['scenes'] if x['scene'].startswith('11_OPEN_CLOSED_PREEXTENDED'))
  self.assertTrue(r['deliberate_fault_GHOST'])
  for side in r['explicit_carrier_blade_contact_witness']:self.assertGreater(side['R27_stage2_gate_carrier_overlap_mm3'],0.)
 def test_34_explicit_manual_unpowered_open_is_clear(self):
  r=next(x for x in self.m['scenes'] if x['scene'].startswith('12_OPEN_CAPTURED_MANUAL'))
  self.assertFalse(r['deliberate_fault_GHOST'])
  for side in r['explicit_carrier_blade_contact_witness']:self.assertEqual(side['R27_stage2_gate_carrier_overlap_mm3'],0.)
 def test_35_manufacturing_flag_must_always_be_rejected(self):
  for r in (self.i,self.f,self.t,self.d,self.e,self.m):self.assertIs(r['manufacturing_go'],False)
if __name__=='__main__':unittest.main()
