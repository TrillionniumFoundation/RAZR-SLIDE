import unittest,json,hashlib,itertools
from pathlib import Path
from r24_mechanics import (ROOT,P,KEY_X_CENTERS,KEY_W,INBOARD_OLED_X_HALF,
    a_keys,a_keyed_shell,guard_overlap,solve_jaw_shift_by_A_contact,
    central_open_key_counterexample,outboard_lugs,outboard_jaws,carrier_arms)
from r24_faults import r24_blocked
from r23_gate import carrier_lugs as r23_carrier_lugs,intersection
from r23_power import physical_energy_at_exposed_A_pad,IsolatorFault

v=ROOT/'verification'
class R24Test(unittest.TestCase):
  def load(self,name):return json.loads((v/(name+'.json')).read_text())
  def test_01_four_real_A_key_shapes(self):
    self.assertEqual(len(a_keys()),4)
    self.assertTrue(all(x.isValid() for x in a_keys().values()))
  def test_02_A_keyed_shell_single_connected(self):
    a=a_keyed_shell();self.assertTrue(a.isValid());self.assertEqual(len(a.Solids()),1)
  def test_03_candidate_keys_outside_screen_but_not_OEM(self):
    self.assertGreater(min(abs(x)-KEY_W/2 for x in KEY_X_CENTERS.values())-INBOARD_OLED_X_HALF,.80)
  def test_04_rejected_central_key_reproduces_collision(self):
    self.assertGreater(central_open_key_counterexample(),.20)
  def test_05_real_A_keys_72_probe_no_OLED_FPC(self):
    j=self.load('R24_mechanics');self.assertEqual(j['A_key_screen_FPC_probe_count'],72)
    self.assertEqual(j['A_key_screen_FPC_probe_failures'],[])
  def test_06_stow_cam_from_A_contact_no_pose_oracle(self):
    self.assertAlmostEqual(solve_jaw_shift_by_A_contact('STOW','R',0.,0.),2.,places=3)
    self.assertAlmostEqual(solve_jaw_shift_by_A_contact('STOW','R',1.,0.),1.,places=3)
    self.assertEqual(solve_jaw_shift_by_A_contact('STOW','R',3.,0.),0.)
  def test_07_open_cam_from_A_contact_no_pose_oracle(self):
    self.assertAlmostEqual(solve_jaw_shift_by_A_contact('OPEN','L',P.travel,8.2),2.,places=3)
    self.assertAlmostEqual(solve_jaw_shift_by_A_contact('OPEN','L',P.travel,7.),.8,places=3)
    self.assertEqual(solve_jaw_shift_by_A_contact('OPEN','L',P.travel,4.),0.)
  def test_08_lugs_closed_block_attempted_extension(self):
    d=guard_overlap(.8,0.,0.);self.assertTrue(all(x>0 for x in d.values()))
  def test_09_one_sided_open_both_mechanical_loadpaths(self):
    self.assertTrue(r24_blocked(.8,0.,2.))
    self.assertTrue(r24_blocked(.8,2.,0.))
  def test_10_both_falsely_open_again_unblocked(self):
    self.assertFalse(r24_blocked(.8,2.,2.))
  def test_11_fault_matrix_8192_rerun_logs(self):
    r=self.load('R24_fault_matrix')['inherited_states']
    self.assertEqual((r['states'],r['unseated']),(8192,7168))
    self.assertEqual(r['R24_both_fault_open_still_escapes'],56)
    self.assertEqual(r['one_R24_false_open_other_intact_unseated_escapes'],0)
  def test_12_nonseated_stow_early_cam_clear_is_failure(self):
    s=solve_jaw_shift_by_A_contact('STOW','L',1.59,0.)
    self.assertTrue(s>.4 and not r24_blocked(.8,s,s))
  def test_13_nonseated_open_early_cam_clear_is_failure(self):
    s=solve_jaw_shift_by_A_contact('OPEN','L',P.travel,6.61)
    self.assertTrue(s>.4 and not r24_blocked(.8,s,s))
  def test_14_early_release_report_is_not_euphemized_as_pass(self):
    r=self.load('R24_fault_matrix')
    self.assertTrue(r['current_R24_nominal_cam_fails_strict_seat_interlock'])
    self.assertGreater(r['early_clear_unseated_count'],0)
    self.assertFalse(r['manufacturing_go'])
  def test_15_real_occ_carrier_arm_link_reaches_outer_stop(self):
    for side in 'LR':
      m=outboard_lugs(0.)[f'B_R24_OUTBOARD_LUG_{side}'].fuse(
          carrier_arms(0.)[f'B_R24_ARM_{side}']).fuse(
          r23_carrier_lugs(0.)[f'B_R23_CARRIER_LUG_{side}']).clean()
      self.assertTrue(m.isValid());self.assertEqual(len(m.Solids()),1)
  def test_16_A_key_no_direct_carrier_clash_at_dock(self):
    from r24_mechanics import a_key,to_global
    for port,s,q in [('STOW',0.,0.),('OPEN',P.travel,P.z_travel)]:
     for side in 'LR':
      key=a_key(port,side)
      for ext in (0.,.8):
       for part in [outboard_lugs(ext)[f'B_R24_OUTBOARD_LUG_{side}'],
                    carrier_arms(ext)[f'B_R24_ARM_{side}']]:
        self.assertLess(intersection(key,to_global(part,port,s,q)),1e-8)
  def test_17_A_and_B_rebuilt_true_OCC_contiguous(self):
    a=self.load('R24_integration')
    self.assertTrue(a['A_with_four_keys_one_body'])
    self.assertTrue(a['R24_cut_B_one_body'])
    self.assertGreater(a['A_added_material_mm3'],0.)
    self.assertGreater(a['B_removed_R23_mm3'],100.)
    self.assertFalse(a['manufacturing_go'])
  def test_18_ten_assembly_poses_no_unexpected_clashes(self):
    d=self.load('R24_integration')
    self.assertEqual(d['sampled_poses'],10)
    self.assertEqual(d['sampled_unexpected_clashes'],[])
  def test_19_actual_carriers_including_OLED_FPC_clear(self):
    d=self.load('R24_dynamic')
    self.assertEqual(d['moving_parts_compared'],160)
    self.assertEqual(d['unexpected_interference_count'],0)
    self.assertTrue(d['carrier_links_all_one_solid'])
  def test_20_OEM_electrical_go_remains_false_and_bypass_exposed(self):
    self.assertTrue(physical_energy_at_exposed_A_pad(faults=IsolatorFault(raw_bat_to_pad_bypass=True)))
  def test_21_OLED_vendor_data_missing_remains_denial(self):
    x=json.loads((ROOT/'baseline_R23'/'verification'/'R23_OLED_tolerance_gate.json').read_text())
    self.assertFalse(x['sample_part_number_and_real_module_document_received'])
    self.assertFalse(x['manufacturing_go'])
  def test_22_scenes_traceable_and_ghosts_labeled(self):
    r=self.load('R24_STEP_manifest');self.assertEqual(r['exports'],8)
    self.assertTrue(r['NO_MANUFACTURING_RELEASE'])
    self.assertTrue(any(s['ghost_unsafe'] for s in r['scenes']))
    self.assertTrue(all(s['real_A_key_shape_modelled'] for s in r['scenes']))
    for s in r['scenes']:
      f=ROOT/'cad'/s['STEP'];self.assertTrue(f.exists())
      self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(),s['SHA256'])
      self.assertEqual(s['parts'],s['reimport_solids'])
  def test_24_long_lap_variant_rejected_against_old_pin(self):
    x=self.load('R24_longlap_rejected')
    self.assertFalse(x['premature_cam_clear_before_seat'])
    self.assertGreater(x['clash_with_R16_A_side_lock_pin_at_OPEN_mm3'],.46)
    self.assertFalse(x['manufacturing_go'])
  def test_25_side_rail_web_nominal_only(self):
    r=self.load('R24_side_rail_web')
    self.assertEqual(len(r['examined_bores']),4)
    self.assertAlmostEqual(r['min_nominal_remaining_sidewall_web_mm'],.22)
    self.assertFalse(r['confirmed_pin_retention_under_impact'])
    self.assertFalse(r['manufacturing_go'])
  def test_23_hard_denial_is_preserved(self):
    for fn in ('R24_mechanics','R24_integration','R24_dynamic','R24_fault_matrix'):
      self.assertFalse(self.load(fn)['manufacturing_go'])

if __name__=='__main__':unittest.main()
