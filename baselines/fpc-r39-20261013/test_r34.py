"""R34 research acceptance: assertions intentionally RETAIN known hazards.
Passing tests validate evidence consistency only, NOT device qualification.
"""
from __future__ import annotations
import hashlib,json,unittest
import cadquery as cq
from r25_capture import ROOT,intersection
from r34_parts import frame_dimensions,te_signal_envelope

class R34Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs={n:json.loads((ROOT/f'verification/R34_{n}.json').read_text())
                  for n in ('integration','dynamic','tolerance','faults','STEP_manifest')}
        cls.original=json.loads((ROOT/'audit/R34_R33_immutable.json').read_text())
        cls.a=cq.importers.importBrep(str(ROOT/'cad/R34_A_R33_UNCHANGED.brep')).val()
        cls.b=cq.importers.importBrep(str(ROOT/'cad/R34_B_OPEN_SIGNAL_ENVELOPE_CRADLES.brep')).val()

    def test_01_original_sha_attested(self):
        self.assertEqual(len(self.original['ancestor_zip_sha256']),64)
        self.assertTrue(self.original['all_ancestor_bytes_unchanged'])

    def test_02_original_member_count_706(self):
        self.assertEqual(self.original['ancestor_files_verified'],706)

    def test_03_A_bytewise_identical(self):
        self.assertEqual((ROOT/'cad/R34_A_R33_UNCHANGED.brep').read_bytes(),
                         (ROOT/'cad/R33_A_R32_BYTE_IDENTICAL.brep').read_bytes())

    def test_04_A_valid_one_body(self):
        self.assertTrue(self.a.isValid())
        self.assertEqual(len(self.a.Solids()),1)

    def test_05_B_valid_one_body(self):
        self.assertTrue(self.b.isValid())
        self.assertEqual(len(self.b.Solids()),1)

    def test_06_actual_cut_not_just_symbolic(self):
        d=self.docs['integration']
        self.assertEqual(sum(s['op']=='frame_fuse' for s in d['operations']),2)
        self.assertEqual(sum(s['op']=='pocket_cut' for s in d['operations']),2)
        self.assertEqual(sum(s['op']=='front_throat_cut' for s in d['operations']),2)
        self.assertGreater(d['front_throat_actual_added_cut_mm3'],.14)

    def test_07_R32_orphan_material_removed_from_final(self):
        d=self.docs['integration']
        self.assertEqual(d['final_orphan_solids'],0)
        self.assertAlmostEqual(d['interim_orphan_volume_removed_by_throat_mm3'],.1328,places=6)
        self.assertEqual(len(d['orphan_R32_frame_chips_removed']),2)

    def test_08_nominal_web_budget_from_parameters(self):
        d=frame_dimensions()
        self.assertEqual(d['nominal_left_x_wall_mm'],.25)
        self.assertEqual(d['nominal_right_x_wall_mm'],.25)
        self.assertEqual(d['nominal_rear_y_wall_mm'],.33)
        self.assertEqual(d['nominal_bottom_z_wall_mm'],.3)

    def test_09_no_false_qualified_wall_language(self):
        d=frame_dimensions()
        self.assertTrue(d['not_finished_wall_thickness_or_structural_fea'])
        self.assertTrue(d['front_open'])
        self.assertTrue(d['top_open'])

    def test_10_local_eight_real_material_witnesses(self):
        w=self.docs['integration']['section_witnesses']
        self.assertEqual(len(w),8)
        self.assertTrue(all(x['actual_solid_occupancy_fraction']>.999999 for x in w))

    def test_11_nominal_TE_rectangle_dims(self):
        from r33_parts import TE_CATALOGUE_MM
        self.assertEqual(tuple(TE_CATALOGUE_MM[x] for x in ('width','length','uncompressed_height')),(1.05,2.4,1.2))

    def test_12_catalogue_box_clear_B_both_sides(self):
        for side in 'LR':
            with self.subTest(side=side):
                self.assertLess(intersection(te_signal_envelope(side),self.b),1e-7)

    def test_13_miniature_R33_bay_not_supported(self):
        d=json.loads((ROOT/'verification/R33_catalogue.json').read_text())
        self.assertEqual(d['axis_aligned_channel_fit_count'],0)

    def test_14_full_named_geometry_reference_count(self):
        self.assertEqual(self.docs['dynamic']['reference_poses'],10)

    def test_15_no_unexpected_named_poses(self):
        self.assertEqual(self.docs['dynamic']['unexpected_named_pose_collisions'],[])

    def test_16_actual_front_feed_samples(self):
        d=self.docs['dynamic']
        self.assertEqual(d['front_feed_cases'],28)
        self.assertEqual(d['front_feed_interference_cases'],0)

    def test_17_top_feed_is_rejected(self):
        d=self.docs['dynamic']
        self.assertEqual(d['rejected_top_feed_cases'],22)
        self.assertEqual(d['top_feed_interference_cases'],10)

    def test_18_front_unretained_escapes(self):
        self.assertTrue(self.docs['faults']['front_feed_reverse_escape_unopposed'])

    def test_19_offset_sample_size(self):
        self.assertEqual(self.docs['tolerance']['cases'],216)

    def test_20_small_offset_grid_no_box_interference(self):
        for w in ('0.02','0.05'):
            self.assertEqual(self.docs['tolerance']['offset_aggregation'][w],{'cases':54,'hits':0})

    def test_21_large_offset_negative_witness(self):
        d=self.docs['tolerance']['offset_aggregation']
        self.assertEqual(d['0.12']['cases'],54)
        self.assertEqual(d['0.12']['hits'],42)

    def test_22_borderline_0p1_has_no_margin_qualification(self):
        self.assertEqual(self.docs['tolerance']['offset_aggregation']['0.1']['hits'],0)
        self.assertTrue(self.docs['tolerance']['no_GDT_from_real_connector'])

    def test_23_original_combined_fault_escape_still_36(self):
        d=self.docs['faults']
        self.assertEqual(d['legacy_mechanical_combined_fault_states'],64)
        self.assertEqual(d['legacy_mechanical_combined_fault_escapes'],36)

    def test_24_electrical_single_point_bypass_not_resolved(self):
        self.assertEqual(self.docs['faults']['electrical_single_fault_bypass_count'],3)

    def test_25_no_vendor_native_step_import(self):
        self.assertFalse(self.docs['faults']['supplier_native_TE_STEP_file_present'])

    def test_26_no_mechanical_fastener_or_cap(self):
        self.assertTrue(self.docs['faults']['zero_front_cap_or_lid_fitted'])
        self.assertFalse(self.docs['integration']['physical_retention_or_axial_capture_installed'])

    def test_27_no_A_side_contact_mechanics(self):
        self.assertFalse(self.docs['integration']['A_side_mating_pad_and_controlled_contact_sequence'])

    def test_28_power_not_signal_pin(self):
        self.assertTrue(self.docs['faults']['TE_2199001_1_for_SIGNAL_only_and_not_power'])
        self.assertTrue(self.docs['faults']['power_connectors_and_battery_4700mAh_OEM_unselected'])

    def test_29_USB_not_qualified(self):
        self.assertTrue(self.docs['faults']['USB_contact_pinout_TDR_eye_and_EMI_unverified'])

    def test_30_OLED_lifetime_not_qualified(self):
        self.assertTrue(self.docs['faults']['actual_OLED_full_width_dynamic_radius_flatten_force_lifetime_unverified'])

    def test_31_equal_finished_chassis_not_qualified(self):
        self.assertTrue(self.docs['faults']['finished_A_B_identical_outer_shell_not_proven'])

    def test_32_step_six_imported_valid(self):
        d=self.docs['STEP_manifest']
        self.assertEqual(d['count'],6)
        self.assertTrue(all(x['parts']==x['valid_imported']==6 for x in d['scenes']))

    def test_33_step_negative_cases_preserved(self):
        self.assertEqual(self.docs['STEP_manifest']['ghost_count'],3)

    def test_34_step_hashes_equal(self):
        for row in self.docs['STEP_manifest']['scenes']:
            with self.subTest(row=row['file']):
                self.assertEqual(hashlib.sha256((ROOT/'cad'/row['file']).read_bytes()).hexdigest(),row['sha256'])

    def test_35_all_cad_stages_manufacturing_no_go(self):
        self.assertTrue(all(x['manufacturing_go'] is False for x in self.docs.values()))

    def test_36_legacy_power_fault_witness_is_still_hazardous(self):
        self.assertGreater(self.docs['faults']['electrical_fault_tree_enumerated_states'],0)
        self.assertEqual(len(self.docs['faults']['electrical_minimal_cut_sets']),7)

if __name__=='__main__':unittest.main()
