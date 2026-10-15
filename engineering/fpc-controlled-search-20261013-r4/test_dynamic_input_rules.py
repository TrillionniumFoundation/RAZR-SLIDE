import copy,json,math,unittest
from pathlib import Path
from dynamic_input_rules import dynamic_profile_screen,bm28_contact_screen,source_conflict_screen,illustrative_copper_loop

FACTS=json.loads(Path(__file__).with_name('input_audit.json').read_text())

class PublicInputAdversarialTests(unittest.TestCase):
    def test_thin_single_layer_static_profile_does_not_become_dynamic(self):
        r=dynamic_profile_screen(FACTS['vendor_standard_profiles'][0],16.5)
        self.assertTrue(r['generic_radius_screen_only_passed'])
        self.assertAlmostEqual(r['generic_dynamic_min_radius_mm'],14.7)
        self.assertFalse(r['public_profile_suitable_for_project_dynamic_use'])
        self.assertIn('RA_copper_not_specified_in_delivered_profile',r['rejection_reasons'])

    def test_nominal_two_layer_radius_pass_is_reversed_by_real_supplier_tolerance(self):
        p=FACTS['vendor_standard_profiles'][1]
        self.assertGreaterEqual(16.5,100*p['flex_thickness_mm'])
        r=dynamic_profile_screen(p,16.5)
        self.assertAlmostEqual(r['generic_dynamic_min_radius_mm'],17)
        self.assertFalse(r['generic_radius_screen_only_passed'])

    def test_large_radius_does_not_qualify_plated_static_material(self):
        r=dynamic_profile_screen(FACTS['vendor_standard_profiles'][1],100)
        self.assertTrue(r['generic_radius_screen_only_passed'])
        self.assertIn('plated_copper_in_dynamic_zone_requires_specific_review',r['rejection_reasons'])
        self.assertFalse(r['public_profile_suitable_for_project_dynamic_use'])

    def test_missing_tolerance_is_not_treated_as_zero(self):
        p=copy.deepcopy(FACTS['vendor_standard_profiles'][0]);p['flex_thickness_tolerance_plus_mm']=None
        r=dynamic_profile_screen(p,100)
        self.assertIsNone(r['generic_radius_screen_only_passed'])
        self.assertIn('maximum_total_stackup_thickness_uncontrolled',r['rejection_reasons'])

    def test_radius_screen_cannot_approve_hard_axis_or_twist(self):
        for axis,twist in [('WIDTH',False),('THICKNESS',True)]:
            with self.subTest(axis=axis,twist=twist):
                r=dynamic_profile_screen(FACTS['vendor_standard_profiles'][0],100,axis,twist)
                self.assertIn('3D_hard_axis_or_twist_is_outside_generic_radius_guidance',r['rejection_reasons'])

    def test_invalid_dimensions_and_bools_rejected(self):
        p=FACTS['vendor_standard_profiles'][0]
        for x in [0,-1,float('inf'),float('nan'),True,'16.5']:
            with self.subTest(radius=x),self.assertRaises(ValueError):dynamic_profile_screen(p,x)

    def test_source_actual_unused_layer_and_zero_tolerance_are_rejected(self):
        r=source_conflict_screen(FACTS['FLEX2_machine_readable_conflict'])
        self.assertFalse(r['automatic_import_allowed'])
        self.assertEqual(len(r['rejection_reasons']),3)
        self.assertFalse(r['supplier_source_silently_repaired'])

    def test_5A_cannot_be_assigned_to_24_signal_contacts(self):
        r=bm28_contact_screen([5]*24,[],1,False)
        self.assertIn('signal_contact_above_0.3A',r['rejection_reasons'])

    def test_simultaneous_individual_ratings_exceed_total(self):
        r=bm28_contact_screen([.3]*24,[5,5],1,False)
        self.assertEqual(r['rejection_reasons'],['catalog_total_current_above_10A'])

    def test_double_power_lands_are_not_four_independent_fittings(self):
        with self.assertRaises(ValueError):bm28_contact_screen([],[1,1,1,1],1,False)

    def test_static_connector_must_not_repeatedly_disconnect_on_sliding(self):
        r=bm28_contact_screen([.1],[1],300000,True)
        self.assertIn('above_specified_10_mating_cycles',r['rejection_reasons'])
        self.assertIn('sliding_motion_must_not_mate_or_unmate_BM28',r['rejection_reasons'])

    def test_bounded_static_contact_check_is_not_harness_or_manufacturing_approval(self):
        r=bm28_contact_screen([.1]*24,[1,1],10,False)
        self.assertTrue(r['contact_rating_screen_passed'])
        self.assertFalse(r['rated_current_is_FPC_capacity'])
        self.assertFalse(r['manufacturing_go'])

    def test_round_trip_resistance_and_square_current_loss_not_single_leg(self):
        low=illustrative_copper_loop(120,1.2,.018,.3);high=illustrative_copper_loop(120,1.2,.018,5)
        self.assertAlmostEqual(high['ideal_loop_ohm'],.19155555555555556)
        self.assertAlmostEqual(high['ideal_loop_loss_W'],4.788888888888889)
        self.assertAlmostEqual(high['ideal_loop_drop_V'],.9577777777777778)
        self.assertAlmostEqual(high['ideal_loop_loss_W']/low['ideal_loop_loss_W'],(5/.3)**2)
        self.assertFalse(high['is_actual_FPC_ampacity_or_temperature_result'])

if __name__=='__main__':unittest.main(verbosity=2)
