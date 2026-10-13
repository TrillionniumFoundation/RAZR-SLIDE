"""R33 research regression; all PASS means reproducible GOOD and BAD witnesses.
Manufacturing qualification remains explicitly false.
"""
from __future__ import annotations
import unittest,hashlib,json
import cadquery as cq
from r25_capture import ROOT,intersection
from r33_parts import keeper_pin,bored_gauge,bore,catalogue_TE_box, constraints
from r33_freeze import SOURCE,EXTERNAL

FILES=('integration','retention','catalogue','expansion_rejected','dynamic','STEP_manifest')

class R33Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d={name:json.loads((ROOT/'verification'/f'R33_{name}.json').read_text()) for name in FILES}
        cls.freeze=json.loads((ROOT/'audit/R33_R32_immutable.json').read_text())
        cls.B=cq.importers.importBrep(str(ROOT/'cad/R33_B_BILATERAL_PIN_PORTS.brep')).val()

    def test_01_r32_archive_matches_external_sha(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),EXTERNAL.read_text().split()[0])
    def test_02_frozen_636_members(self):self.assertEqual(self.freeze['R32_ancestor_count'],636)
    def test_03_old_members_byte_preserved(self):
        for x in self.freeze['records']:
            self.assertEqual(hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest(),x['sha256'],x['path'])
    def test_04_original_envelope_A_unchanged_bytes(self):
        self.assertEqual((ROOT/'cad/R33_A_R32_BYTE_IDENTICAL.brep').read_bytes(),(ROOT/'cad/R32_A_R31_UNMODIFIED.brep').read_bytes())
    def test_05_A_B_remain_valid_single(self):
        self.assertTrue(self.d['integration']['A_valid_single']);self.assertTrue(self.d['integration']['B_valid_single'])
        self.assertTrue(self.B.isValid());self.assertEqual(len(self.B.Solids()),1)
    def test_06_exactly_two_bore_operations(self):self.assertEqual(len(self.d['integration']['bored_channels']),2)
    def test_07_both_B_ports_actually_cut(self):
        self.assertTrue(all(x['actual_B_removed_mm3']>.02 for x in self.d['integration']['bored_channels']))
    def test_08_net_B_cut_approx(self):self.assertAlmostEqual(self.d['integration']['bore_cut_mm3'],.055546762,places=7)
    def test_09_bored_guages_valid(self):
        for s in 'LR':
            g=bored_gauge(s);self.assertTrue(g.isValid());self.assertEqual(len(g.Solids()),1)
    def test_10_keeper_pins_valid(self):
        for s in 'LR':
            p=keeper_pin(s);self.assertTrue(p.isValid());self.assertEqual(len(p.Solids()),1)
    def test_11_nominal_no_B_pin_collision_live(self):
        for s in 'LR':self.assertLess(intersection(self.B,keeper_pin(s)),1e-8)
    def test_12_nominal_no_pin_gauge_collision_live(self):
        for s in 'LR':self.assertLess(intersection(bored_gauge(s),keeper_pin(s)),1e-8)
    def test_13_nominal_no_B_gauge_collision_live(self):
        for s in 'LR':self.assertLess(intersection(bored_gauge(s),self.B),1e-8)
    def test_14_pin_0p17_not_catalogue_qualified(self):self.assertAlmostEqual(constraints()['pin_shaft_diameter_mm'],.17)
    def test_15_bore_0p28(self):self.assertAlmostEqual(constraints()['pin_hole_diameter_mm'],.28)
    def test_16_local_nominal_radial_slack(self):self.assertAlmostEqual(constraints()['pin_nominal_radial_play_mm'],.055)
    def test_17_weakened_gauge_wall_both_sides(self):
        c=constraints();self.assertAlmostEqual(c['remaining_gauge_top_web_mm'],.09);self.assertAlmostEqual(c['remaining_gauge_bottom_web_mm'],.09)
    def test_18_assembled_10_nominal_poses(self):self.assertEqual(self.d['dynamic']['reference_pose_count'],10)
    def test_19_no_named_reference_collisions(self):self.assertEqual(len(self.d['dynamic']['unexpected_collisions']),0)
    def test_20_no_OEM_OLED_illusion(self):self.assertTrue(self.d['dynamic']['no_actual_true_OLED_package_or_cof_fpc_geometry'])
    def test_21_retention_22_sweep_cases(self):self.assertEqual(self.d['retention']['sweep_cases'],22)
    def test_22_nominal_no_pin_collision(self):self.assertTrue(self.d['retention']['seated_assembly_zero_interference'])
    def test_23_both_pin_keepers_intercept_retreat(self):self.assertEqual(self.d['retention']['withdrawal_barrier_paths'],2)
    def test_24_live_both_pin_retreat_contact(self):
        for s in 'LR':self.assertGreater(intersection(keeper_pin(s),bored_gauge(s,-.10)),.001)
    def test_25_avoid_endpoint_tunneling_false_success(self):
        self.assertTrue(self.d['retention']['fully_withdrawn_endpoint_misses_intermediate_barrier'])
    def test_26_unretained_if_pin_absent(self):self.assertTrue(self.d['retention']['pin_missing_full_gauge_exit_not_resisted'])
    def test_27_no_keeper_pin_axial_stop(self):self.assertTrue(self.d['retention']['pin_axial_no_B_stop_all_offsets'])
    def test_28_no_real_clip(self):self.assertTrue(self.d['retention']['pin_has_no_axial_capture_or_retaining_clip'])
    def test_29_assumed_2d_misalignment_36(self):self.assertEqual(len(self.d['retention']['misalignment_cases']),36)
    def test_30_misalignment_jam_8_not_hidden(self):self.assertEqual(self.d['retention']['misalignment_jam_count'],8)
    def test_31_prior_mechanical_failures_not_waived(self):self.assertEqual(self.d['retention']['legacy_mechanical_escape_counterexamples'],36)
    def test_32_TE_OFFICIAL_1p5A_signal_only(self):
        d=self.d['catalogue']['te_catalogue_dimensions'];self.assertEqual((d['width'],d['length'],d['uncompressed_height']),(1.05,2.4,1.2));self.assertEqual(d['max_current_A'],1.5);self.assertEqual(d['application'],'Signal')
    def test_33_TE_12_orientation_cases(self):self.assertEqual(self.d['catalogue']['configurations'],12)
    def test_34_TE_fits_no_current_channel_orientation(self):self.assertEqual(self.d['catalogue']['axis_aligned_channel_fit_count'],0)
    def test_35_TE_boxes_intersect_actual_B(self):self.assertTrue(all(x['B_shell_interference_mm3']>1 for x in self.d['catalogue']['rows']))
    def test_36_enlarged_box_conflicts_keeper_every_reference(self):self.assertEqual(self.d['expansion_rejected']['keeper_conflicts'],20)
    def test_37_enlarged_box_strips_all_web_witnesses(self):
        b=self.d['expansion_rejected']['witness_fraction_vs_R32_material_cells'];self.assertTrue(all(x['R33_rejected_B_final_occupancy']==0 for x in b if x['cell']!='R_REAR_STOP'))
    def test_38_rejected_B_not_selected_as_design(self):
        self.assertTrue(self.d['expansion_rejected']['enlarged_bay_is_REJECTED_due_to_retainer_and_structural_safety_gaps'])
    def test_39_seven_STEP_with_four_hazard_scenes(self):
        d=self.d['STEP_manifest'];self.assertEqual(d['count'],7);self.assertEqual(d['ghost_unsafe_count'],4)
    def test_40_STEP_provenance_valid_and_safe_status_false(self):
        for x in self.d['STEP_manifest']['scenes']:
            self.assertEqual(x['parts'],x['valid_solids_imported'])
            self.assertEqual(hashlib.sha256((ROOT/'cad'/x['file']).read_bytes()).hexdigest(),x['sha256'])
            self.assertFalse(x['manufacturer_TE_STEP_imported'])
        self.assertTrue(all(x['manufacturing_go'] is False for x in self.d.values()))
        self.assertFalse(self.d['catalogue']['real_battery_main_power_connection_NOT_SELECTED']==False)

if __name__=='__main__': unittest.main()
