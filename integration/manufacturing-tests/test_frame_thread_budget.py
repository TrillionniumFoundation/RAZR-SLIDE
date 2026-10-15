import copy
import itertools
import math
from pathlib import Path
import random
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "integration"))
from scipy.optimize import linprog
import numpy as np
import frame_thread_budget as m


def point_inputs(L=3.):
    return dict(zip(m.ENGAGEMENT_FIELDS,[[L,L],[2.,2.],[.8,.8],[0.,0.],[0.,0.],[0.,0.],[0.,0.]]))


def scenario(L=3.):
    return dict(zip(m.ENGAGEMENT_FIELDS,[[L-.05,L+.05],[1.96,2.04],[.75,.85],[0.,.5],[0.,.5],[0.,.1],[0.,.1]]))


def preload_inputs():
    return {'separating_load_N':[0.,2.], 'load_fraction':[.1,.3],
            'allowable_total_bolt_force_N':[20.,22.], 'preload_fractional_scatter':.2,
            'preload_loss_N':[0.,1.], 'preload_gain_N':[0.,0.],
            'required_remaining_clamp_N':[.5,.5]}


class EngagementTests(unittest.TestCase):
    def test_missing_limits_not_replaced_by_nominal(self):
        r=m.engagement_bounds({'underhead_length_mm':[3.,3.]})
        self.assertEqual(r['status'],'undetermined');self.assertEqual(len(r['missing_inputs']),6)
    def test_malformed_or_reversed_intervals(self):
        for v in ([3,2],[True,3],[0,float('nan')],[0,float('inf')],[1],3):
            with self.assertRaises(ValueError):m.engagement_bounds({'underhead_length_mm':v})
    def test_negative_loss_rejected(self):
        with self.assertRaises(ValueError):m.engagement_bounds({'male_tip_incomplete_mm':[-.1,.1]})
    def test_zero_size_rejected(self):
        p=point_inputs();p['nut_height_mm']=[0,0]
        with self.assertRaises(ValueError):m.engagement_bounds(p)
    def test_catalogue_solid_overlap_is_not_complete_teeth(self):
        r=m.engagement_bounds(point_inputs());self.assertAlmostEqual(r['complete_form_overlap_mm'][0],.8)
        self.assertIsNone(r['actual_complete_thread_count'])
    def test_longer_screw_cannot_create_nut_engagement_length(self):
        for L in (3.,4.,8.):
            r=m.engagement_bounds(point_inputs(L));self.assertAlmostEqual(r['complete_form_overlap_mm'][0],.8)
    def test_two_end_losses_are_deducted(self):
        p=point_inputs(4.);p['female_entry_incomplete_mm']=[.1,.1];p['female_exit_incomplete_mm']=[.1,.1]
        self.assertAlmostEqual(m.engagement_bounds(p)['complete_form_overlap_mm'][0],.6)
    def test_old_short_tip_worst_case_is_rejected_for_full_female_coverage(self):
        r=m.engagement_bounds(scenario());self.assertAlmostEqual(r['complete_form_overlap_mm'][0],.31)
        self.assertFalse(r['all_female_complete_form_axial_interval_covered']);self.assertAlmostEqual(r['upper_end_coverage_margin_mm'],-.44)
    def test_longer_candidate_covers_scenario_without_becoming_supplier_qualified(self):
        r=m.engagement_bounds(scenario(4.));self.assertAlmostEqual(r['complete_form_overlap_mm'][0],.55)
        self.assertTrue(r['all_female_complete_form_axial_interval_covered']);self.assertFalse(r['candidate_go'])
    def test_shared_nut_datum_not_double_counted(self):
        p=point_inputs(5.);p['nut_seat_from_screw_seat_mm']=[1.,3.]
        r=m.engagement_bounds(p);self.assertAlmostEqual(r['complete_form_overlap_mm'][0],.8)
    def test_no_axial_overlap(self):
        p=point_inputs();p['nut_seat_from_screw_seat_mm']=[4.,4.]
        self.assertEqual(m.engagement_bounds(p)['complete_form_overlap_mm'],[0.,0.])
    def test_whole_incomplete_thread_returns_zero_not_fake_count(self):
        p=point_inputs();p['female_entry_incomplete_mm']=[.8,.8]
        self.assertEqual(m.engagement_bounds(p)['complete_form_overlap_mm'],[0.,0.])
    def test_extrema_against_independent_linear_program_and_sample_box(self):
        rng=random.Random(481)
        # overlap=max(0,min of these four affine functions).
        mat=np.array([[1,0,0,-1,-1,0,0],[1,-1,0,0,-1,-1,0],
                      [0,1,1,-1,0,0,-1],[0,0,1,0,0,-1,-1]],float)
        for _ in range(40):
            bounds=[]
            for base,spread in [(2.,2.),(.5,3.),(.3,1.),(0.,.8),(0.,.8),(0.,.2),(0.,.2)]:
                lo=base+rng.random()*spread/2;bounds.append([lo,lo+rng.random()*spread/2])
            result=m.engagement_bounds(dict(zip(m.ENGAGEMENT_FIELDS,bounds)))
            objective=[0.]*7+[-1.]
            lp=linprog(objective,A_ub=np.column_stack((-mat,np.ones(4))),b_ub=np.zeros(4),
                       bounds=bounds+[(None,None)],method='highs')
            self.assertTrue(lp.success)
            self.assertAlmostEqual(result['complete_form_overlap_mm'][1],max(0.,-lp.fun),places=10)
            for _ in range(12):
                x=[rng.uniform(*b) for b in bounds];n=m.overlap(*x)
                self.assertGreaterEqual(n+1e-10,result['complete_form_overlap_mm'][0])
                self.assertLessEqual(n-1e-10,result['complete_form_overlap_mm'][1])


class LeadTests(unittest.TestCase):
    def test_pure_axial_pull_not_welded_or_free_slide(self):
        self.assertFalse(m.lead_branch(.1,0,0,.25,.02,.8)['on_selected_engaged_branch'])
    def test_correct_rotation_matches_pitch(self):
        self.assertTrue(m.lead_branch(.1,144,0,.25,.02,.8)['on_selected_engaged_branch'])
    def test_relative_nut_rotation_matters(self):
        self.assertFalse(m.lead_branch(.1,144,90,.25,.02,.8)['on_selected_engaged_branch'])
    def test_do_not_wrap_axial_pitch_as_a_clearance_pass(self):
        self.assertFalse(m.lead_branch(.25,0,0,.25,.02,.8)['on_selected_engaged_branch'])
    def test_disengaged_has_no_false_retention(self):
        r=m.lead_branch(1.,0,0,.25,.02,.8*0)
        self.assertIsNone(r['on_selected_engaged_branch']);self.assertTrue(r['disengaged_motion_unconstrained_by_this_law'])
    def test_invalid_lead_inputs(self):
        for p in (0,True,-1,float('nan')):
            with self.assertRaises(ValueError):m.lead_branch(0,0,0,p,.02,.8)


class PreloadTests(unittest.TestCase):
    def test_actual_missing_inputs_undetermined(self):
        self.assertEqual(m.preload_window({})['status'],'undetermined')
    def test_bounds_give_robust_not_mean_load_result(self):
        r=m.preload_window(preload_inputs());self.assertAlmostEqual(r['nominal_preload_lower_N'],4.125)
        self.assertAlmostEqual(r['nominal_preload_upper_N'],19.4/1.2)
    def test_inconsistent_scatter_rejected(self):
        for x in (1.,-.1,True,float('nan')):
            p=preload_inputs();p['preload_fractional_scatter']=x
            with self.assertRaises(ValueError):m.preload_window(p)
    def test_infeasible_window_not_clamped_to_zero(self):
        p=preload_inputs();p['allowable_total_bolt_force_N']=[2.,2.]
        self.assertEqual(m.preload_window(p)['status'],'no_robust_window')
    def test_gain_and_relaxation_shrink_opposite_ends(self):
        p=preload_inputs();r=m.preload_window(p);p['preload_loss_N']=[0,2];p['preload_gain_N']=[0,1]
        z=m.preload_window(p);self.assertGreater(z['nominal_preload_lower_N'],r['nominal_preload_lower_N'])
        self.assertLess(z['nominal_preload_upper_N'],r['nominal_preload_upper_N'])
    def test_two_spring_corner_check(self):
        p=preload_inputs();r=m.preload_window(p)
        for nominal in (r['nominal_preload_lower_N'],r['nominal_preload_upper_N']):
            for c,f,loss,gain,P in itertools.product((.1,.3),(-.2,.2),(0,1),(0,0),(0,2)):
                minimum=nominal*(1+f)-loss-(1-c)*P
                maximum=nominal*(1+f)+gain+c*P
                self.assertGreaterEqual(minimum+1e-10,.5);self.assertLessEqual(maximum-1e-10,20)
    def test_required_clamp_must_be_positive(self):
        p=preload_inputs();p['required_remaining_clamp_N']=[0,0]
        with self.assertRaises(ValueError):m.preload_window(p)
    def test_invalid_load_fraction(self):
        p=preload_inputs();p['load_fraction']=[.1,1.]
        with self.assertRaises(ValueError):m.preload_window(p)


class TorqueTests(unittest.TestCase):
    def test_torque_window_respects_both_friction_bounds(self):
        r=m.torque_window(m.Span(10,40),m.Span(.1,.3),1,.1,m.Span(0,0),.02)
        self.assertEqual(r['status'],'conditional_window_exists')
        self.assertAlmostEqual(r['commanded_torque_lower_Nm'],.003/.9)
        self.assertAlmostEqual(r['commanded_torque_upper_Nm'],.004/1.1)
    def test_torque_window_can_be_empty_despite_preload_window(self):
        r=m.torque_window(m.Span(20,30),m.Span(.1,.3),1,.1,m.Span(0,0),.02)
        self.assertEqual(r['status'],'no_robust_torque_window')
    def test_catalogue_ceiling_is_not_setpoint(self):
        r=m.torque_window(m.Span(1,1000),m.Span(.1,.3),1,.1,m.Span(0,0),.02)
        self.assertAlmostEqual(r['commanded_torque_upper_Nm'],.02/1.1)
        self.assertTrue(r['not_an_installation_instruction'])
    def test_prevailing_torque_must_be_subtracted_from_useful_preload(self):
        r=m.torque_window(m.Span(10,40),m.Span(.1,.3),1,.1,m.Span(.0001,.0002),.02)
        self.assertAlmostEqual(r['commanded_torque_lower_Nm'],.0032/.9)
        self.assertAlmostEqual(r['commanded_torque_upper_Nm'],.0041/1.1)
    def test_invalid_torque_ranges(self):
        with self.assertRaises(ValueError):m.torque_window(m.Span(1,2),m.Span(0,.2),1,.1,m.Span(0,0),.02)
        with self.assertRaises(ValueError):m.torque_window(m.Span(1,2),m.Span(.1,.2),1,1,m.Span(0,0),.02)


if __name__=='__main__':unittest.main(verbosity=2)
