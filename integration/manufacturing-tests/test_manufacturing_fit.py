from dataclasses import replace
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from manufacturing_fit import CatalogueScrew,axial_fit,signed_error_bound,clearance_screen,thermal_chain

class FitTests(unittest.TestCase):
    def test_named_screw_dimensions(self):
        s=CatalogueScrew();self.assertEqual((s.diameter_mm,s.pitch_mm,s.length_under_head_mm,s.head_diameter_mm,s.head_height_mm),(1.,.25,5.,1.8,.45))
    def test_original_seat_has_no_engagement(self):
        r=axial_fit(.55);self.assertEqual(r['nominal_axial_overlap_mm'],0.);self.assertFalse(r['nominal_axial_fit'])
    def test_new_seat_preserves_nominal_overlap(self):
        r=axial_fit(1.95);self.assertAlmostEqual(r['nominal_axial_overlap_mm'],1.25);self.assertAlmostEqual(r['nominal_blind_gap_mm'],.05)
    def test_head_is_recessed_not_protruding(self):
        self.assertAlmostEqual(axial_fit(1.95)['head_back_mm'],1.5)
    def test_blind_bottom_is_not_a_fit(self):
        self.assertFalse(axial_fit(2.)['nominal_axial_fit']);self.assertFalse(axial_fit(2.1)['nominal_axial_fit'])
    def test_torque_ceiling_does_not_prescribe_torque(self):
        self.assertEqual(CatalogueScrew().published_max_torque_Nm,.02);self.assertIsNone(axial_fit(1.95)['tightening_torque_prescribed_Nm'])
    def test_nominal_fit_never_manufacturing_release(self):
        r=axial_fit(1.95);self.assertFalse(r['candidate_go']);self.assertFalse(r['effective_threads_qualified'])
    def test_invalid_or_boolean_dimensions(self):
        for value in (True,float('inf'),float('nan'),0,-1,'5'):
            with self.assertRaises(ValueError):replace(CatalogueScrew(),length_under_head_mm=value)
    def test_invalid_blind_hole(self):
        with self.assertRaises(ValueError):axial_fit(1.95,female_start_mm=7.,blind_end_mm=7.)
    def test_same_datum_cancels_once(self):
        self.assertEqual(signed_error_bound([('datum',1.,.05),('datum',-1.,.05)]),0.)
    def test_different_features_do_not_cancel(self):
        self.assertAlmostEqual(signed_error_bound([('a',1,.05),('b',-1,.05)]),.1)
    def test_repeated_source_inconsistent_bound_rejected(self):
        with self.assertRaises(ValueError):signed_error_bound([('a',1,.05),('a',-1,.04)])
    def test_signed_lever_arm(self):
        self.assertAlmostEqual(signed_error_bound([('x',2,.1),('x',-1,.1),('y',-3,.2)]),.7)
    def test_nonfinite_chains_rejected(self):
        for terms in [[('',1,.1)],[('a',True,.1)],[('a',1,float('inf'))],[('a',1,-1)],[('a',float('nan'),.1)]]:
            with self.assertRaises(ValueError):signed_error_bound(terms)
    def test_generic_tolerance_rejected_for_current_gap(self):
        r=clearance_screen(.0034853293,[('a',1,.05),('b',-1,.05)]);self.assertLess(r['lower_bound_mm'],0);self.assertTrue(r['not_a_collision_proof'])
    def test_even_five_um_per_feature_is_not_certified(self):
        r=clearance_screen(.0034853293,[('a',1,.005),('b',-1,.005)]);self.assertEqual(r['status'],'not_certified_for_this_bounded_chain')
    def test_exact_zero_is_not_positive_clearance(self):
        self.assertEqual(clearance_screen(.1,[('a',1,.1)])['status'],'not_certified_for_this_bounded_chain')
    def test_positive_control_can_certify_only_its_chain(self):
        r=clearance_screen(.2,[('a',1,.05)]);self.assertEqual(r['status'],'certified_for_this_bounded_chain');self.assertFalse(r['actual_process_qualification'])
    def test_shared_thermal_error_cancels(self):
        self.assertEqual(thermal_chain(20.,11.3e-6,20.,11.3e-6,60.),0.)
    def test_independent_temperature_not_common_mode(self):
        self.assertAlmostEqual(thermal_chain(20.,11.3e-6,20.,11.3e-6,60.,shared_temperature=False),.02712)
