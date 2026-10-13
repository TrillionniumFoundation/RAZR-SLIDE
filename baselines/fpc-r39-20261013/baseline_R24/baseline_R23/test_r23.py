import unittest,json,hashlib
from pathlib import Path
from r23_gate import (ROOT,guard_overlap,guard_blocked,local_interference_checks,
        scan_independent_faults,independent_guard_frames,
        independent_guard_jaws,carrier_lugs,intersection,GUARD_Z,LUG_Z_RETRACTED)
from r23_power import (IsolatorFault,physical_energy_at_exposed_A_pad,commanded_bus,analysis)
from r23_oled import study,residual
from baseline_R22.r22_adversarial import full_release_matrix

class R23Test(unittest.TestCase):
    def test_01_R22_original_unsafe_not_hidden(self):
        b=full_release_matrix()
        self.assertEqual(b['states'],512)
        self.assertEqual(b['unseated_unblocked'],56)
    def test_02_occ_analytic_independent(self):
        self.assertEqual(local_interference_checks()['local_occ_vs_aabb_cases'],28)
    def test_03_parked_clear_when_gates_closed(self):
        self.assertTrue(all(v==0 for v in guard_overlap(0,False,False).values()))
    def test_04_both_new_jaws_closed_block_extension(self):
        self.assertTrue(guard_blocked(.8,False,False))
    def test_05_only_left_jaw_still_blocks(self):
        self.assertTrue(guard_blocked(.8,False,True))
    def test_06_only_right_jaw_still_blocks(self):
        self.assertTrue(guard_blocked(.8,True,False))
    def test_07_both_jaws_misopen_not_safe(self):
        self.assertFalse(guard_blocked(.8,True,True))
    def test_08_r22_common_tab_absent_new_carrier_hardpoints_exist(self):
        self.assertEqual(set(carrier_lugs(.8)),{'B_R23_CARRIER_LUG_L','B_R23_CARRIER_LUG_R'})
        self.assertTrue(guard_blocked(.8,False,False))
    def test_09_both_new_tabs_sheared_must_fail(self):
        self.assertFalse(guard_blocked(.8,False,False,False,False))
    def test_10_one_tab_sheared_other_still_blocks(self):
        self.assertTrue(guard_blocked(.8,True,False,False,True))
        self.assertTrue(guard_blocked(.8,False,True,True,False))
    def test_11_local_2048_fault_enumeration(self):
        s=scan_independent_faults()
        self.assertEqual((s['states'],s['unseated']), (2048,1792))
        self.assertEqual(s['R22_dangerous_now_blocked_both_new_closed'],56)
        self.assertEqual(s['all_R22_open_both_new_open_unseated_escape'],56)
        self.assertEqual(s['any_one_new_jaw_closed_both_lugs_intact_escape'],0)
    def test_12_roofs_no_overlap_with_jaws(self):
        roof=independent_guard_frames()
        for v in (False,True):
            jaws=independent_guard_jaws(v,v)
            for side in 'LR':
                self.assertLess(intersection(jaws[f'B_R23_A_KEY_JAW_{side}'],roof[f'B_R23_FRAME_{side}_ROOF']),1e-8)
    def test_13_local_clearance_not_same_as_tolerance(self):
        self.assertAlmostEqual(GUARD_Z[0]-LUG_Z_RETRACTED[1],.14)
    def test_14_off_two_stage_blocks_one_stuck_switch(self):
        for f in (IsolatorFault(upstream_welded=True),IsolatorFault(main_pair_welded=True),
                  IsolatorFault(precharge_welded=True)):
            self.assertFalse(physical_energy_at_exposed_A_pad(faults=f))
    def test_15_bypass_is_single_point_failure(self):
        self.assertTrue(physical_energy_at_exposed_A_pad(faults=IsolatorFault(raw_bat_to_pad_bypass=True)))
    def test_16_two_simultaneous_welds_are_unsafe(self):
        self.assertTrue(physical_energy_at_exposed_A_pad(faults=IsolatorFault(upstream_welded=True,main_pair_welded=True)))
        self.assertTrue(physical_energy_at_exposed_A_pad(faults=IsolatorFault(upstream_welded=True,precharge_welded=True)))
    def test_17_logic_no_ungated_bus_command(self):
        self.assertFalse(commanded_bus(False,False,True,True,True,True,True,True,False)['main'])
    def test_18_faulttree_enumeration(self):
        r=analysis(write=False)
        self.assertEqual(r['modeled_weld_short_bypass_combinations'],16)
        self.assertEqual(r['number_unsafe_cases_excluding_bypass'],3)
        self.assertFalse(r['manufacturing_go'])
    def test_19_oled_baseline_and_stress(self):
        r=study(write=False)
        self.assertAlmostEqual(residual(),.04)
        self.assertEqual(r['stress_cases'],36)
        self.assertEqual(r['stress_cases_nominal_geometric_screen_pass'],1)
        self.assertEqual(r['hypothetical_required_cavity_depth_mm'],7.76)
    def test_20_nobody_qualifies_product_without_material(self):
        for f in ['R23_lock_fault_results.json','R23_power_faulttree.json','R23_OLED_tolerance_gate.json']:
            obj=json.loads((ROOT/'verification'/f).read_text())
            self.assertFalse(obj['manufacturing_go'])
    def test_21_actual_B_dock_still_unqualified(self):
        obj=json.loads((ROOT/'verification'/'R23_B_integration.json').read_text())
        self.assertTrue(obj['B_final_one_solid'])
        self.assertEqual(obj['selected_pose_clash_count'],0)
        self.assertFalse(obj['physically_modelled_A_positive_key_wedge'])
        self.assertFalse(obj['manufacturing_go'])
    def test_22_step_ghosts_labeled(self):
        obj=json.loads((ROOT/'verification'/'R23_STEP_manifest.json').read_text())
        self.assertEqual(obj['valid_exports'],6)
        self.assertTrue(obj['NO_MANUFACTURING_RELEASE'])
        self.assertTrue(any(x['ghost_fault_injection'] for x in obj['scenes']))
        for row in obj['scenes']:
            p=ROOT/'cad'/row['STEP']
            self.assertTrue(p.exists())
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),row['sha256'])
            self.assertEqual(row['parts'],row['valid_reimport'])
            self.assertTrue(row['A_keys_not_modelled'])

if __name__=='__main__':unittest.main()
