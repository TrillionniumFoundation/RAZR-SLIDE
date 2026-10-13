"""Keep NO-GO as a tested requirement, not as an afterthought."""
import unittest
from r22_adversarial import full_release_matrix, first_hard_stop_interference, qualification_contract
from r22_supplier_review import oem_radius_screen, source_review

class AdversarialR22(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix=full_release_matrix()
    def test_512_independent_release_sweep(self):
        self.assertEqual(self.matrix['states'],512)
        self.assertEqual(self.matrix['unseated'],448)
    def test_retain_counterexample_instead_of_masking_failure(self):
        self.assertEqual(self.matrix['unseated_unblocked'],56)
        self.assertEqual(self.matrix['premature_all_three_open'],56)
        self.assertFalse(self.matrix['engineering_gate_pass'])
    def test_centre_guards_dual_new_side_false_release_only_as_proxy(self):
        self.assertEqual(self.matrix['one_stop_remaining_unseated_failures'],0)
        self.assertEqual(self.matrix['legacy_both_open_centre_still_closed_blocked'],14)
        self.assertTrue(self.matrix['no_actual_A_side_mechanical_capture_or_spring_model'])
    def test_carriage_continuous_travel_stop_before_full_extension_in_box_model(self):
        r=first_hard_stop_interference((True,True,False))
        self.assertGreater(r['first_positive_solid_intersection']['extension_mm'],.25)
        self.assertLess(r['first_positive_solid_intersection']['extension_mm'],.26)
        self.assertEqual(r['contact_make_travel_mm'].split()[0],'UNKNOWN')
    def test_known_triple_false_open_clears_tab_whole_travel(self):
        r=first_hard_stop_interference((True,True,True))
        self.assertIsNone(r['first_positive_solid_intersection'])
    def test_no_hardware_gate_can_be_reclassified(self):
        c=qualification_contract()
        self.assertFalse(all(c[gate]['qualified'] for gate in ('M_LOCK','E_SEPARATE','D_OLED')))
        self.assertEqual(c['overall'],'MANUFACTURING_NO_GO')
    def test_box_extension_bracket_agrees_with_occ(self):
        from cadquery import Vector
        from r22_mechanics import carriage_tab,three_deadbolts,intersection
        parked=carriage_tab(True)
        center=three_deadbolts(True,True,False)['B_INDEPENDENT_CENTRE_STOP']
        self.assertAlmostEqual(intersection(parked.translate(Vector(0,0,.249)),center),0,places=7)
        self.assertGreater(intersection(parked.translate(Vector(0,0,.251)),center),0)
    def test_old_dog_false_release_independent_in_existing_proxy(self):
        from r22_mechanics import assembly_local,stop_contact_metrics
        expected=None
        for left in (False,True):
            for right in (False,True):
                v=stop_contact_metrics(assembly_local(False,True,True,False,left,right))
                if expected is None:expected=v
                else:self.assertEqual(expected,v)
        self.assertGreater(expected['B_INDEPENDENT_CENTRE_STOP'],0.)
    def test_common_carriage_tab_failure_is_not_excluded(self):
        # If all three stops bear against the SAME tab and the tab detaches,
        # the stop collision results alone cannot establish a real latch.
        from r22_mechanics import assembly_local
        d=assembly_local(False,False,False,False,True,True)
        self.assertIn('B_CARRIAGE_SAFETY_TAB',d)
        self.assertNotIn('B_CARRIAGE_SAFETY_TAB_TEAROFF_GUARD',d)
        self.assertFalse(qualification_contract()['M_LOCK']['positive_load_bearing_faces_with_material_FEA_and_safety_factor'])
    def test_depth_robustness_breaks_by_small_packaging_change(self):
        a=oem_radius_screen()['scenarios']
        self.assertTrue(a[0]['ideal_geometry_screening_pass'])
        self.assertFalse(a[1]['ideal_geometry_screening_pass'])
        self.assertFalse(a[2]['ideal_geometry_screening_pass'])
        self.assertFalse(a[3]['ideal_geometry_screening_pass'])
    def test_primary_vendor_evidence_does_not_certify_slide_product(self):
        v=source_review()
        self.assertEqual(v['TE_2199001_1']['qualification_report_nominal_repeated_mating_cycles'],10)
        self.assertFalse(v['MILLMAX_0900_0_15_20_76_14_11_0']['OEM_300k_cycle_our_orientation_and_loading_qualified'])
        self.assertFalse(v['VISIONOX_2026_MWC']['project_R3p4_permission'])
        self.assertFalse(v['IEC_62715_6_42_2026']['30万次_life_certificate'])
if __name__=='__main__':unittest.main()
