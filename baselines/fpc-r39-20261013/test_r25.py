"""R25 falsification tests.  'pass' never means mechanical manufacturing released."""
import json,hashlib,unittest
from pathlib import Path
from r25_capture import ROOT,P,PORT_DATA,capture_witness,run as captures,pawl,a_key,to_global,intersection
from r25_gate import study as gate_study,new_carrier_ear,shutter_stow
from r25_faults import run as faults

V=ROOT/'verification'
class R25Test(unittest.TestCase):
 def j(self,n):return json.loads((V/n).read_text())
 def test_01_all_four_positive_capture_ideal_solid(self):
  x=self.j('R25_capture.json');self.assertEqual(x['retention_witness_count'],4)
 def test_02_parked_capture_docking_trajectory_clear(self):
  self.assertTrue(self.j('R25_capture.json')['docking_with_parked_pawl_all_nominal_zero_clash'])
 def test_03_false_engagement_can_collide_and_stall(self):
  self.assertTrue(self.j('R25_capture.json')['too_early_false_engagement_causes_arrival_collision'])
 def test_04_false_engagement_far_away_not_mechanically_excluded(self):
  self.assertTrue(self.j('R25_capture.json')['pawl_can_be_activated_without_A_present'])
 def test_05_0p05_reverse_lock_is_real_occ(self):
  for port in ('STOW','OPEN'):
   for side in 'LR':
    a=capture_witness(port,side)
    self.assertEqual(a['dock_key_pawl_interference_mm3'],0.)
    self.assertGreater(a['forced_reverse_0p05_interference_mm3'],0.)
 def test_06_retention_is_not_measure_of_force(self):
  x=self.j('R25_capture.json')
  self.assertFalse(x['seat_capture_shear_strength_measured'])
  self.assertFalse(x['spring_and_bearing_measured'])
 def test_07_stow_new_ears_single_connected(self):
  for side in 'LR':
   for ext in (0.,.8):
    a=new_carrier_ear(side,ext)
    self.assertTrue(a.isValid());self.assertEqual(len(a.Solids()),1)
 def test_08_stow_stage2_shutters_single_connected(self):
  for side in 'LR':
   for stroke in (0.,2.):
    a=shutter_stow(side,stroke)
    self.assertTrue(a.isValid());self.assertEqual(len(a.Solids()),1)
 def test_09_stow_closed_shutter_blocks_both_ear_extensions(self):
  for side in 'LR':
   self.assertGreater(intersection(new_carrier_ear(side,.8),shutter_stow(side,0.)),.01)
 def test_10_stow_manually_open_shutter_frees_both_ear_extensions(self):
  for side in 'LR':
   self.assertLess(intersection(new_carrier_ear(side,.8),shutter_stow(side,2.)),1e-8)
 def test_11_stow_retracted_carrier_clear_in_closed_gate(self):
  for side in 'LR':
   self.assertLess(intersection(new_carrier_ear(side,0.),shutter_stow(side,0.)),1e-8)
 def test_12_pawl_parked_blocks_stage2_release_by_real_occ(self):
  x=self.j('R25_gate.json')
  self.assertTrue(x['parked_pawl_physically_vetoes_manual_shutter_motion'])
 def test_13_pawl_engaged_allows_stage2_release_by_real_occ(self):
  self.assertTrue(self.j('R25_gate.json')['captured_pawl_shutter_path_clear'])
 def test_14_open_copy_geometry_hard_denied(self):
  g=self.j('R25_gate.json')
  self.assertAlmostEqual(g['naive_open_copy_intrudes_outside_equal_envelope_mm'],.56)
  self.assertLess(g['open_capture_pawl_min_outer_shell_edge_margin_mm'],.3)
  self.assertTrue(g['naive_open_copy_rejected'])
 def test_15_B_rework_OCC_one_solid(self):
  g=self.j('R25_integration.json')
  self.assertTrue(g['B_shell_R25_valid']);self.assertEqual(g['B_shell_R25_solids'],1)
  self.assertEqual(g['new_pockets'],8)
  self.assertGreater(g['B_cut_vs_R24_mm3'],12.)
 def test_16_open_capture_relieving_B_base_material_zero(self):
  g=self.j('R25_integration.json')
  x=[p for p in g['per_pocket'] if p['pocket'].startswith('OPEN')]
  self.assertEqual(len(x),2)
  self.assertEqual([p['new_B_material_removed_mm3'] for p in x],[0.,0.])
 def test_17_pose_probe_no_nominal_parked_clash(self):
  d=self.j('R25_dynamic.json')
  self.assertEqual(d['samples'],10)
  self.assertEqual(d['unintended_contact_during_parked_travel'],[])
  self.assertTrue(d['B_R25_one_body'])
 def test_18_new_ghosts_keep_old_unsafe_line(self):
  d=self.j('R25_faults.json')
  self.assertEqual(d['inherited_R24_combined_states'],8192)
  self.assertEqual(d['inherited_R24_old_both_fault_open_escape'],56)
  self.assertTrue(d['inherited_R24_normal_early_release'])
  self.assertTrue(d['STOW_both_stage2_false_open_remains_unsafe'])
  self.assertTrue(d['OPEN_old_early_fault_remains_unsafe'])
 def test_19_stow_nominal_latched_stops_override_legacy(self):
  d=self.j('R25_faults.json')
  self.assertEqual(d['STOW_when_both_stage2_closed_ears_intact_escapes'],0)
  self.assertEqual(d['total_new_fault_samples'],32)
 def test_20_R25_STEP_manifest_reimport_verified(self):
  manifest=self.j('R25_STEP_manifest.json')
  self.assertEqual(manifest['exports'],7)
  self.assertGreaterEqual(sum(x['legacy_fault_ghost'] for x in manifest['scenes']),3)
  for row in manifest['scenes']:
   f=ROOT/'cad'/row['STEP'];self.assertTrue(f.exists());self.assertEqual(row['parts'],row['reimport_valid_solids'])
   self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(),row['sha256'])
 def test_21_tallied_no_manufacturing_claim(self):
  for x in ('R25_capture.json','R25_gate.json','R25_integration.json','R25_dynamic.json','R25_faults.json','R25_STEP_manifest.json'):
   self.assertFalse(self.j(x)['manufacturing_go'],x)
 def test_22_power_exposed_bypass_still_unsafe(self):
  from r23_power import physical_energy_at_exposed_A_pad,IsolatorFault
  self.assertTrue(physical_energy_at_exposed_A_pad(faults=IsolatorFault(raw_bat_to_pad_bypass=True)))
 def test_23_OLED_no_OEM_signed_radius(self):
  j=json.loads((ROOT/'baseline_R24'/'baseline_R23'/'verification'/'R23_OLED_tolerance_gate.json').read_text())
  self.assertFalse(j['real_panel_qualified']);self.assertFalse(j['manufacturing_go'])
 def test_24_R24_cams_still_early_release(self):
  from r24_mechanics import solve_jaw_shift_by_A_contact,guard_overlap
  a=solve_jaw_shift_by_A_contact('STOW','R',1.59,0.)
  b=solve_jaw_shift_by_A_contact('OPEN','R',P.travel,6.61)
  self.assertGreater(a,.4);self.assertGreater(b,.4)
  self.assertEqual([x for x in guard_overlap(.8,a,a).values() if x>1e-8],[])
 def test_25_inherited_R24_legacy_NO_GO_preserved(self):
  j=json.loads((ROOT/'baseline_R24'/'audit'/'R24_independent_attestation.json').read_text())
  self.assertFalse(j.get('manufacturing_go',False))
 def test_26_perturbed_capture_GDT_not_rated(self):
  d=self.j('R25_tolerance.json');self.assertEqual(len(d['all_rows']),216)
  a,b=d['groups'];self.assertEqual(a['sample_count'],108);self.assertEqual(b['sample_count'],108)
  self.assertEqual((a['clashes_at_seat'],a['no_0p05_retention_contact']),(0,36))
  self.assertEqual((b['clashes_at_seat'],b['no_0p05_retention_contact']),(36,36))
 def test_27_footprint_does_not_imply_mounting(self):
  d=self.j('R25_integration.json')
  self.assertTrue(d['newly_added_solid_fasteners_springs_and_slider_guides_not_modeled'])
  self.assertFalse(d['manufacturing_go'])
 def test_28_open_station_remains_missing_real_2nd_stage(self):
  self.assertTrue(self.j('R25_integration.json')['open_port_second_stage_not_in_CAD'])
  self.assertTrue(self.j('R25_faults.json')['OPEN_old_early_fault_remains_unsafe'])
 def test_29_all_snapshots_explicitly_research(self):
  d=self.j('R25_STEP_manifest.json')
  self.assertTrue(all(x['research_OLED_is_not_vendor_part'] for x in d['scenes']))
  self.assertTrue(all(x['no_power_interconnect_or_materials_qualified'] for x in d['scenes']))
 def test_30_every_stage_still_NO_GO(self):
  for filename in ('R25_capture.json','R25_gate.json','R25_faults.json','R25_integration.json','R25_dynamic.json','R25_STEP_manifest.json','R25_tolerance.json'):
   self.assertFalse(self.j(filename)['manufacturing_go'],filename)
if __name__=='__main__':unittest.main()
