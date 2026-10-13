"""Research-only R35 unit+adversarial checks; hazardous GHOSTs are expected evidence."""
import json,hashlib,unittest
import cadquery as cq
from r25_capture import ROOT,intersection
from r35_parts import bored_cap,pin,te_signal_envelope,part_metadata

class R35Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs={n:json.loads((ROOT/f'verification/R35_{n}.json').read_text())
                  for n in ('integration','dynamic','tolerance','faults','STEP_manifest')}
        cls.freeze=json.loads((ROOT/'audit/R35_R34_immutable.json').read_text())
        cls.A=cq.importers.importBrep(str(ROOT/'cad/R35_A_R34_UNCHANGED.brep')).val()
        cls.B=cq.importers.importBrep(str(ROOT/'cad/R35_B_INBOARD_RAILS_AND_GUIDES.brep')).val()

    def test_01_ancestor_zip_digest_recorded(self):
        self.assertEqual(len(self.freeze['R34_original_zip_sha256']),64)
    def test_02_ancestor_entries_783(self):
        self.assertEqual(self.freeze['original_member_count'],783)
    def test_03_ancestor_bytes_kept(self):
        self.assertTrue(self.freeze['all_ancestor_bytes_unchanged'])
    def test_04_A_source_exact(self):
        self.assertEqual((ROOT/'cad/R35_A_R34_UNCHANGED.brep').read_bytes(),
                         (ROOT/'cad/R34_A_R33_UNCHANGED.brep').read_bytes())
    def test_05_A_valid(self):
        self.assertTrue(self.A.isValid())
    def test_06_B_valid(self):
        self.assertTrue(self.B.isValid())
    def test_07_B_single_body(self):
        self.assertEqual(len(self.B.Solids()),1)
    def test_08_B_material_change_positive(self):
        self.assertGreater(self.docs['integration']['B_volume_delta_mm3'],8.)
    def test_09_real_reinforcement_two_sides(self):
        self.assertEqual(sum(o['operation']=='fuse_inboard_reinforcement' for o in self.docs['integration']['operations']),2)
    def test_10_actual_two_keyway_machining(self):
        self.assertEqual(sum(o['operation']=='machine_guide' for o in self.docs['integration']['operations']),2)
    def test_11_actual_two_pin_bores(self):
        self.assertEqual(sum(o['operation']=='machine_pin_bore' for o in self.docs['integration']['operations']),2)
    def test_12_actual_pin_bore_removed_material(self):
        self.assertGreater(sum(o['removed_mm3'] for o in self.docs['integration']['operations'] if o['operation']=='machine_pin_bore'),0)
    def test_13_both_caps_one_solid(self):
        self.assertTrue(all(x['cap_valid'] and x['cap_solids']==1 for x in self.docs['integration']['cap_and_pin']))
    def test_14_nominal_cap_B_clear(self):
        self.assertTrue(all(x['cap_B_intersection_mm3']<1e-7 for x in self.docs['integration']['cap_and_pin']))
    def test_15_nominal_cap_TE_clear(self):
        self.assertTrue(all(x['cap_TE_intersection_mm3']<1e-7 for x in self.docs['integration']['cap_and_pin']))
    def test_16_nominal_pin_body_clear(self):
        self.assertTrue(all(x['pin_B_intersection_mm3']<1e-7 for x in self.docs['integration']['cap_and_pin']))
    def test_17_nominal_pin_cap_clear(self):
        self.assertTrue(all(x['pin_cap_intersection_mm3']<1e-7 for x in self.docs['integration']['cap_and_pin']))
    def test_18_ten_assembled_reference_poses(self):
        self.assertEqual(self.docs['dynamic']['reference_poses'],10)
    def test_19_ten_named_poses_no_clash(self):
        self.assertTrue(all(not v['penetrations_mm3'] for v in self.docs['dynamic']['pose_rows']))
    def test_20_bridge_22_feed_samples(self):
        self.assertEqual(len(self.docs['dynamic']['cap_front_feed_samples']),22)
    def test_21_bridge_front_feeds_clear_B(self):
        self.assertTrue(all(x['cap_B']<1e-7 for x in self.docs['dynamic']['cap_front_feed_samples']))
    def test_22_bridge_front_feeds_clear_TE(self):
        self.assertTrue(all(x['cap_TE']<1e-7 for x in self.docs['dynamic']['cap_front_feed_samples']))
    def test_23_TE_negative_unpowered_stops(self):
        self.assertEqual(sum(x['dy']==-.08 and x['TE_cap_installed']>1e-6 for x in self.docs['dynamic']['catalogue_TE_front_withdrawal_samples']),2)
    def test_24_TE_can_be_extracted_when_bridge_gone(self):
        self.assertTrue(self.docs['faults']['after_pin_extraction_bridge_can_be_removed_then_TE_can_exit'])
    def test_25_bridge_retraction_0p1_with_pin_clashes(self):
        self.assertEqual(sum(x['bridge_withdrawal_y_mm']==-.10 and x['bridge_hits_installed_pin']>1e-8 for x in self.docs['faults']['removable_bridge_witness']),2)
    def test_26_axial_pin_withdrawal_unopposed(self):
        self.assertTrue(self.docs['faults']['axial_pin_extraction_unopposed_by_B_and_bridge'])
    def test_27_no_actual_axial_retainer(self):
        self.assertTrue(self.docs['faults']['pin_no_axial_clip_or_thread_or_locknut'])
    def test_28_measured_nominal_play_only(self):
        self.assertAlmostEqual(self.docs['faults']['radial_nominal_pin_hole_play_mm'],.09)
    def test_29_two_slack_sum_no_voltage_proof(self):
        self.assertAlmostEqual(self.docs['faults']['simple_sum_nominal_two_slack_mm'],.15)
        self.assertTrue(self.docs['faults']['two_slack_sum_not_an_electrical_make_break_measurement'])
    def test_30_tolerance_216_cases(self):
        self.assertEqual(self.docs['tolerance']['configurations'],216)
    def test_31_tolerance_648_occ_intersections(self):
        self.assertEqual(self.docs['tolerance']['configurations']*self.docs['tolerance']['checked_collisions_per_config'],648)
    def test_32_small_tolerance_no_named_clashes(self):
        for w in ('0.02','0.05'):
            row=self.docs['tolerance']['aggregation'][w]
            self.assertEqual(row['configurations'],54)
            self.assertEqual(row['cap_B_jams']+row['cap_TE_jams']+row['pin_cap_jams'],0)
    def test_33_tolerance_0p1_negative_cases(self):
        self.assertGreater(self.docs['tolerance']['aggregation']['0.1']['cap_B_jams'],0)
    def test_34_tolerance_0p12_negative_cases(self):
        self.assertGreater(self.docs['tolerance']['aggregation']['0.12']['pin_cap_jams'],0)
    def test_35_old_mechanical_36_survive(self):
        self.assertEqual(self.docs['faults']['original_R34_unsafe_joint_modes'],36)
        self.assertEqual(self.docs['faults']['original_R34_mechanical_joint_modes'],64)
    def test_36_three_single_point_electrical_faults_survive(self):
        self.assertEqual(self.docs['faults']['electrical_single_point_bypass_count'],3)
    def test_37_no_A_mating_contact(self):
        self.assertTrue(self.docs['faults']['A_side_mating_pad_not_designed'])
    def test_38_no_vendor_step(self):
        self.assertFalse(self.docs['integration']['vendor_native_TE_STEP_imported'])
    def test_39_real_electric_tests_missing(self):
        self.assertTrue(self.docs['faults']['circuit_isolation_test_not_performed'])
    def test_40_USB_unqualified(self):
        self.assertTrue(self.docs['faults']['USB_high_speed_signal_integrity_unverified'])
    def test_41_OLED_unqualified(self):
        self.assertTrue(self.docs['faults']['exact_OLED_module_bend_fatigue_unknown'])
    def test_42_finished_equal_external_shell_unproven(self):
        self.assertTrue(self.docs['faults']['complete_A_B_equal_finish_envelope_unverified'])
    def test_43_surrogate_cannot_claim_fastener_safety(self):
        self.assertTrue(part_metadata()['spring_breakaway_force_and_material_unqualified'])
    def test_44_step_seven_scenes(self):
        self.assertEqual(self.docs['STEP_manifest']['count'],7)
    def test_45_step_four_ghosts(self):
        self.assertEqual(self.docs['STEP_manifest']['ghosts'],4)
    def test_46_step_reimports_valid(self):
        self.assertTrue(all(x['parts']==x['valid_imported'] for x in self.docs['STEP_manifest']['scenes']))
    def test_47_step_hashes_current(self):
        for x in self.docs['STEP_manifest']['scenes']:
            self.assertEqual(hashlib.sha256((ROOT/'cad'/x['file']).read_bytes()).hexdigest(),x['sha256'])
    def test_48_cap_and_pin_exist_as_BRep(self):
        for side in 'LR':
            self.assertTrue((ROOT/f'cad/R35_{side}_UNQUALIFIED_CAPTURE_BRIDGE.brep').is_file())
            self.assertTrue((ROOT/f'cad/R35_{side}_UNQUALIFIED_STEEL_PIN_PROXY.brep').is_file())
    def test_49_no_manufacturing_go_claim(self):
        self.assertTrue(all(v['manufacturing_go'] is False for v in self.docs.values()))
    def test_50_no_lifetime_electronics_envelope_test(self):
        self.assertTrue(self.docs['tolerance']['real_battery_board_and_OLED_package_not_included'])

if __name__=='__main__':unittest.main()
