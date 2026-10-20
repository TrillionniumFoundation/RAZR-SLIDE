"""Arithmetic and material-frame regressions; these do not execute native CAD."""
import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import product_routing_ep4 as ep4


def simpson(function, start=0., end=1., intervals=8192):
    h = (end-start)/intervals
    return h/3.*math.fsum([function(start), function(end), *[
        (4 if i % 2 else 2)*function(start+i*h) for i in range(1, intervals)]])


class EP4ArithmeticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = ep4.load_config()

    def test_arc_lengths_against_independent_simpson_and_refinement(self):
        for rise in (0., 2., 4.1, 8.2):
            direct = simpson(lambda u: math.sqrt(100.+(rise*30.*u*u*(1.-u)**2)**2))
            self.assertAlmostEqual(ep4.s_arc_length(rise), direct, delta=2e-11)
            self.assertAlmostEqual(ep4.s_arc_length(rise, order=192), direct, delta=2e-11)
        integral = simpson(lambda u: math.sin(math.pi*(3.*u*u-2.*u**3)))
        self.assertAlmostEqual(float(ep4.u_integral()[1]), integral, delta=2e-12)

    def test_inverse_uses_arc_length_instead_of_S_parameter(self):
        rise = 8.2
        for u in (.01, .15, .37, .5, .81, .99):
            distance = simpson(lambda q: math.sqrt(100.+(rise*30.*q*q*(1.-q)**2)**2), end=u)
            solved = ep4.s_parameter_at_arc(distance, rise)
            self.assertAlmostEqual(solved, u, delta=2e-12)
        u = .25
        self.assertGreater(abs(ep4.s_arc_length(rise, u)/ep4.s_arc_length(rise)-u), .02)

    def test_global_material_metric_and_signed_normal_derivative(self):
        n = ep4.pose_numbers(79.75, 0., self.config)
        signs = []
        for u in (.2, .4, .6, .8):
            s = n['A_straight_mm']+ep4.s_arc_length(n['S_rise_mm'], u)
            point, tangent, normal, curvature = ep4.evaluate_material_station(s, n, self.config)
            epsilon = 1e-4
            minus = ep4.evaluate_material_station(s-epsilon, n, self.config)
            plus = ep4.evaluate_material_station(s+epsilon, n, self.config)
            derivative = (plus[0]-minus[0])/(2.*epsilon)
            normal_derivative = (plus[2]-minus[2])/(2.*epsilon)
            np.testing.assert_allclose(derivative, tangent, atol=2e-8, rtol=0.)
            np.testing.assert_allclose(normal_derivative, -curvature*tangent, atol=2e-8, rtol=0.)
            self.assertLess(normal[1], 0.)
            self.assertGreater(normal[2], 0.)
            signs.append(math.copysign(1., curvature))
        self.assertEqual(signs, [1., 1., -1., -1.])

    def test_G2_joins_and_proper_endpoint_frames(self):
        for slide, descent in ((0., 0.), (20., 0.), (79.75, 0.), (79.75, 4.1), (79.75, 8.2)):
            sections, report = ep4.route_sections(slide, descent, self.config)
            self.assertAlmostEqual(report['length_sum_mm'], 100., delta=2e-12)
            self.assertTrue(np.all(np.diff(sections['s']) > 0.))
            self.assertGreater(float(np.min(np.diff(sections['s']))), 1e-10)
            np.testing.assert_allclose(sections['center'][0], [0., 51., 1.45], atol=1e-11, rtol=0.)
            np.testing.assert_allclose(sections['center'][-1], [0., 40.+slide, 13.05-descent], atol=1e-11, rtol=0.)
            for index in (0, -1):
                frame = np.column_stack([sections[k][index] for k in ('width_axis', 'tangent', 'normal')])
                np.testing.assert_allclose(frame.T@frame, np.eye(3), atol=1e-12, rtol=0.)
                self.assertAlmostEqual(float(np.linalg.det(frame)), 1., delta=1e-12)
            for s in report['exact_join_material_labels_mm'][1:-1]:
                exact = ep4.evaluate_material_station(s, report, self.config)
                self.assertAlmostEqual(exact[3], 0., delta=1e-12)
                for side in (-1., 1.):
                    near = ep4.evaluate_material_station(s+side*1e-7, report, self.config)
                    np.testing.assert_allclose(near[1], exact[1], atol=1e-10, rtol=0.)
                    self.assertLess(abs(near[3]), 1e-6)

    def test_continuous_bounds_have_honest_support_and_material_scope(self):
        report = ep4.arithmetic_report(self.config)
        bounds = report['continuous_necessary_bounds']
        self.assertGreater(bounds['minimum_bridge_straight_mm'], 0.)
        self.assertLess(bounds['minimum_bridge_straight_mm'], 1.)
        self.assertGreater(bounds['minimum_B_straight_mm'], 3.)
        self.assertLess(bounds['STOW_U_finite_head_upper_bound_using_S_chord_mm'], 94.)
        self.assertLess(bounds['maximum_STOW_bridge_if_head_limit_is_preserved_mm'], 3.)
        self.assertGreater(bounds['minimum_Jacobian_lower_bound'], .96)
        for label in ep4.POSES:
            sections, _ = ep4.route_sections(*ep4.POSES[label], self.config)
            self.assertGreaterEqual(float(np.min(sections['jacobian'])), bounds['minimum_Jacobian_lower_bound']-1e-12)
        self.assertFalse(bounds['empty_internal_channel_or_clearance_proved'])
        self.assertTrue(all(report[k] is False for k in ep4.GO_KEYS))

    def test_OPEN_keeps_old_single_U_analytic_geometry(self):
        n = ep4.pose_numbers(79.75, 8.2, self.config)
        old_sa = (100.-n['U_length_mm']+119.75-51.)/2.
        self.assertAlmostEqual(51.+old_sa, n['U_start_world_Y_mm'], delta=1e-11)
        for s in (1., 29., 35., 70., old_sa, 99.):
            point, tangent, _, _ = ep4.evaluate_material_station(s, n, self.config)
            if s <= old_sa:
                np.testing.assert_allclose(point, [0., 51.+s, 1.45], atol=1e-11, rtol=0.)
                np.testing.assert_allclose(tangent, [0., 1., 0.], atol=1e-12, rtol=0.)
            else:
                np.testing.assert_allclose(point, [0., 119.75+(100.-s), 4.85], atol=1e-11, rtol=0.)

    def test_numpy_pose_metadata_serializes_as_finite_python_numbers(self):
        n = ep4.pose_numbers(np.float64(79.75), np.float64(0.), self.config)
        json.dumps(n, allow_nan=False)
        for name in ('U_start_world_Y_mm', 'S_length_mm', 'U_length_mm', 'B_straight_mm'):
            self.assertIs(type(n[name]), float)
        for pose in ((0., 1.), (-1., 0.), (79.75, float('nan')), (True, 0.)):
            with self.assertRaises(ValueError): ep4.pose_numbers(*pose, self.config)

    def test_config_cannot_grant_release_or_silently_move_geometry(self):
        for edit in ('release', 'B_board', 'A_web'):
            changed = copy.deepcopy(self.config)
            if edit == 'release': changed['manufacturing_go'] = True
            elif edit == 'B_board': changed['endpoint']['PCB_B_tail_coordinate_Y_mm'] = [-14., -2.]
            else: changed['endpoint']['A_carrier_web_tail_Y_mm'] = [12.05, 12.5]
            with tempfile.TemporaryDirectory(prefix='ep4-config-test-') as folder:
                path = Path(folder)/'candidate.json'; path.write_text(json.dumps(changed))
                with self.assertRaises(ValueError): ep4.load_config(path)


if __name__ == '__main__':
    unittest.main()
