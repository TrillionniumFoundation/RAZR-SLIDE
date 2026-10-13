"""R32 adversarial CAD regression. PASS does not imply a manufacturable device."""
from __future__ import annotations
import hashlib,json,unittest
import cadquery as cq
from r25_capture import ROOT,intersection
from r32_cartridge import frame,gauge,nominal_frame_wall_budget

REPORTS=('integration','dynamic','tolerance','faults','STEP_manifest','vendor_fit','envelope')

class R32Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.j={n:json.loads((ROOT/'verification'/f'R32_{n}.json').read_text()) for n in REPORTS}
        cls.orig=json.loads((ROOT/'audit'/'R32_R31_FROZEN_SHA256.json').read_text())
    def test_01_ancestor_count(self):self.assertEqual(self.orig['verified_R31_original_files'],564)
    def test_02_ancestors_immutable_sha(self):
        for e in self.orig['entries']:
            self.assertEqual(hashlib.sha256((ROOT/e['path']).read_bytes()).hexdigest(),e['sha256'],e['path'])
    def test_03_ancestor_original_archive_identity(self):
        from r32_freeze import SOURCE
        self.assertEqual(self.orig['R31_original_SHA256'],hashlib.sha256(SOURCE.read_bytes()).hexdigest())
    def test_04_A_unchanged_brep(self):
        self.assertEqual(hashlib.sha256((ROOT/'cad'/'R32_A_R31_UNMODIFIED.brep').read_bytes()).hexdigest(),
                         hashlib.sha256((ROOT/'cad'/'R31_A_POSITIVE_OPEN_SHELVES.brep').read_bytes()).hexdigest())
    def test_05_A_and_B_single_valid_solids(self):
        for name in ('R32_A_R31_UNMODIFIED.brep','R32_B_REAR_CASSETTE_BAYS.brep'):
            solid=cq.importers.importBrep(str(ROOT/'cad'/name)).val()
            self.assertTrue(solid.isValid());self.assertEqual(len(solid.Solids()),1)
    def test_06_two_real_frame_fusions(self):self.assertEqual(len(self.j['integration']['frame_fuse']),2)
    def test_07_frame_not_disconnected(self):
        for c in self.j['integration']['frame_fuse']:
            self.assertTrue(c['connected']);self.assertGreater(c['preexisting_B_overlap_mm3'],0)
    def test_08_actual_material_added(self):self.assertGreater(self.j['integration']['actual_B_frame_added_mm3'],2.)
    def test_09_both_channels_real_cuts(self):
        self.assertEqual(len(self.j['integration']['channel_cuts']),2)
        self.assertTrue(all(c['actual_cut_mm3']>.4 and c['connected'] for c in self.j['integration']['channel_cuts']))
    def test_10_five_actual_material_cells(self):
        self.assertEqual(len(self.j['integration']['box_material_witnesses']),5)
        self.assertTrue(all(c['actual_final_B_material_fraction']==1. for c in self.j['integration']['box_material_witnesses']))
    def test_11_budget_is_not_certified_web(self):
        self.assertTrue(nominal_frame_wall_budget()['these_are_design_differences_not_actual_minimum_remaining_machined_wall'])
    def test_12_no_real_electrical_module(self):self.assertTrue(self.j['integration']['cassette_is_non_electrical_solid_envelope_only'])
    def test_13_reference_postures_all_ten(self):self.assertEqual(self.j['dynamic']['reference_pose_count'],10)
    def test_14_reference_collision_free_in_defined_scope(self):self.assertEqual(len(self.j['dynamic']['unexpected_reference_collisions']),0)
    def test_15_slide_in_ten_samples(self):self.assertEqual(len(self.j['dynamic']['insertion_cases']),10)
    def test_16_no_nominal_insertion_clash(self):self.assertEqual(self.j['dynamic']['insertion_clashes'],0)
    def test_17_no_collision_with_old_gate_or_carrier(self):self.assertEqual(self.j['dynamic']['legacy_part_collisions'],0)
    def test_18_offsets_162_combinations(self):self.assertEqual(self.j['tolerance']['configurations'],162)
    def test_19_offsets_0p02_no_jam(self):self.assertEqual(self.j['tolerance']['results_by_width'][0]['jam_count'],0)
    def test_20_offsets_0p05_no_jam(self):self.assertEqual(self.j['tolerance']['results_by_width'][1]['jam_count'],0)
    def test_21_offsets_0p10_fail(self):self.assertEqual(self.j['tolerance']['results_by_width'][2]['jam_count'],48)
    def test_22_positive_rear_stop(self):
        v=[x for x in self.j['tolerance']['hard_stop_and_withdrawal_probes'] if x['test']=='overshoot_y_0p20']
        self.assertEqual(len(v),2);self.assertTrue(all(x['interference_mm3']>0 for x in v))
    def test_23_transverse_escape_intercept(self):
        v=[x for x in self.j['tolerance']['hard_stop_and_withdrawal_probes'] if x['test'].startswith(('outboard','inboard'))]
        self.assertEqual(len(v),4);self.assertTrue(all(x['interference_mm3']>0 for x in v))
    def test_24_up_down_escape_intercept(self):
        v=[x for x in self.j['tolerance']['hard_stop_and_withdrawal_probes'] if x['test'].startswith('z_')]
        self.assertEqual(len(v),4);self.assertTrue(all(x['interference_mm3']>0 for x in v))
    def test_25_unretained_withdrawal_is_an_unresolved_failure(self):
        v=[x for x in self.j['tolerance']['hard_stop_and_withdrawal_probes'] if x['test'].startswith('withdraw')]
        self.assertEqual(len(v),2);self.assertTrue(all(x['interference_mm3']==0 for x in v))
    def test_26_same_follower_for_early_and_seated(self):
        for x in self.j['faults']['identical_follower_position_distinct_true_seat_witnesses']:
            self.assertEqual(x['early_shelf_stroke_mm'],x['seated_shelf_stroke_mm'])
            self.assertNotEqual(x['early_q_mm'],x['seated_q_mm'])
    def test_27_inherited_escape_reproduced_not_magically_erased(self):
        self.assertEqual(self.j['faults']['inherited_mechanical_fault_space'],64)
        self.assertEqual(self.j['faults']['inherited_mechanical_escape_counterexamples'],36)
    def test_28_legacy_single_point_power_short_risk(self):
        self.assertEqual(self.j['faults']['power_fault_model_states'],512)
        self.assertEqual(self.j['faults']['power_minimal_dangerous_cut_set_count'],7)
        self.assertEqual(self.j['faults']['power_single_fault_dangerous_minimal_cut_count'],3)
    def test_29_old_closed_gate_allows_e0p07(self):
        a=self.j['faults']['carrier_residual_clash']
        self.assertEqual(sum(x['closed_gate_intersection_mm3']==0 for x in a if x['carrier_extension_mm']==.07),2)
        self.assertEqual(sum(x['closed_gate_intersection_mm3']>0 for x in a if x['carrier_extension_mm']==.08),2)
    def test_30_7_valid_step_scenes(self):self.assertEqual(self.j['STEP_manifest']['scene_count'],7)
    def test_31_four_known_bad_step_scenes(self):
        self.assertEqual(sum(x['ghost_known_unsafe'] for x in self.j['STEP_manifest']['scenes']),4)
    def test_32_step_reimport_and_sha(self):
        for x in self.j['STEP_manifest']['scenes']:
            self.assertEqual(x['parts'],x['imported_valid_solids'])
            self.assertEqual(hashlib.sha256((ROOT/'cad'/x['filename']).read_bytes()).hexdigest(),x['sha256'])
    def test_33_no_hardware_qualifications(self):
        self.assertTrue(self.j['faults']['true_contact_voltage_contact_resistance_heating_thermal_arcing_not_measured'])
        self.assertTrue(self.j['faults']['no_exact_OLED_panel_full_packaging_CAD_or_Rmin_qualification'])
    def test_34_all_research_reports_NO_GO(self):
        self.assertTrue(all(x['manufacturing_go'] is False for x in self.j.values()))
    def test_35_unbuilt_load_path_and_no_fastener(self):
        self.assertTrue(self.j['integration']['no_evidence_new_support_receives_any_A_or_carrier_force'])
        self.assertTrue(self.j['integration']['independent_removable_fastener_not_designed'])

    def test_36_official_TE_dimensions_cited(self):
        t=self.j['vendor_fit']
        self.assertEqual(t['dimension_mm']['width'],1.05)
        self.assertEqual(t['dimension_mm']['uncompressed_height'],1.2)
        self.assertEqual(t['dimension_mm']['max_A'],1.5)
    def test_37_official_TE_axis_aligned_envelope_rejected(self):
        self.assertEqual(len(self.j['vendor_fit']['six_permutations']),6)
        self.assertEqual(self.j['vendor_fit']['axis_aligned_envelope_fit_count'],0)
    def test_38_vendor_geometry_and_electrical_not_qualified(self):
        self.assertTrue(self.j['vendor_fit']['requires_real_part_3D_mesh_and_assembly_fit'])
        self.assertTrue(self.j['vendor_fit']['real_USB_and_battery_power_connectors_NOT_SELECTED'])

    def test_39_baseline_chassis_bbox_x_equal_only(self):
        self.assertEqual(self.j['envelope']['A_minus_B_extent_xyz_mm'][0],0.)
        self.assertAlmostEqual(self.j['envelope']['A_minus_B_extent_xyz_mm'][1],-.35)
        self.assertAlmostEqual(self.j['envelope']['A_minus_B_extent_xyz_mm'][2],3.4)
    def test_40_finished_external_module_equality_not_yet_proven(self):
        self.assertTrue(self.j['envelope']['A_B_identical_finished_outer_shells_NOT_proven'])
        self.assertTrue(self.j['envelope']['product_equal_outer_size_requirement_unchanged'])
        self.assertTrue(self.j['envelope']['no_separate_outer_cosmetic_shell_CAD_or_OEM_authority'])

if __name__=='__main__':unittest.main()
