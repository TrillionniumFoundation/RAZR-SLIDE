"""Independent scalar regressions. This file never imports a CAD kernel."""
import json
import math
import unittest

import key_endcap_local_study as key


def segment_distance(point, start, end):
    delta = (end[0]-start[0], end[1]-start[1])
    t = sum((point[i]-start[i])*delta[i] for i in (0, 1))/sum(x*x for x in delta)
    t = min(1., max(0., t))
    closest = tuple(start[i]+t*delta[i] for i in (0, 1))
    return math.dist(point, closest)


class LocalKeyTests(unittest.TestCase):
    def test_common_external_tangents_are_actual_two_disc_tangents(self):
        g = key.geometry_parameters()
        for normal, p, q in zip(g['external_tangent_normals'], g['C_tangent_points'], g['E_tangent_points']):
            self.assertAlmostEqual(key.dot(normal, normal), 1., delta=1e-14)
            self.assertAlmostEqual(math.dist(p, g['C']), .95, delta=1e-13)
            self.assertAlmostEqual(math.dist(q, g['E']), 1.1, delta=1e-13)
            self.assertAlmostEqual(key.dot(key.sub(q, p), normal), 0., delta=2e-14)
            self.assertAlmostEqual(key.dot(key.sub(g['E'], g['C']), normal)+.15, 0., delta=2e-14)
        self.assertGreater(g['tangent'][0]-.15, 0.)
        self.assertAlmostEqual(g['C'][0]-.95, 6.2, delta=1e-14)

    def test_all_ideal_flanks_fit_finite_neck_eroded_capsule(self):
        g = key.geometry_parameters(); minimum = math.inf
        dx_limit = .025*math.hypot(1., 12./79.75)
        for q in (0., .5, 2., 6., 11.5, 12.):
            for dx_scale in (-1., -.5, 0., .5, 1.):
                for n_scale in (-1., -.5, 0., .5, 1.):
                    dx = dx_scale*dx_limit; normal = n_scale*.025
                    dq = dx-normal*math.sqrt(2.)
                    pin = (7.25+q+dx, 77.5-q-dq)
                    self.assertLessEqual(segment_distance(pin, g['C'], g['D']), .025+2e-14)
                    along = key.dot(key.sub(pin, g['C']), g['tangent'])
                    minimum = min(minimum, along)
                    self.assertGreater(along, 0.)
                    self.assertLess(along, g['slot_centerline_length_mm'])
        self.assertAlmostEqual(minimum, .08066801221648645, delta=2e-13)

    def test_uniform_axial_blocking_disk_is_wall_and_flange_material(self):
        g = key.geometry_parameters()
        for case in key.clearance_cases():
            for q in (0., 6., 12.):
                pin = key.pin_center(q, case)
                witness = key.add(pin, key.scale(g['normal'], .55))
                distance = segment_distance(witness, g['C'], g['D'])
                self.assertGreater(distance-.05, .425)
                self.assertLess(distance+.05, .95)
                self.assertGreater(math.dist(witness, pin)-.05, .4)
                self.assertLess(math.dist(witness, pin)+.05, .65)
                along = key.dot(key.sub(witness, g['C']), g['tangent'])
                self.assertGreater(along-.05, 0.)
                self.assertGreater(g['slot_centerline_length_mm']-along-.05, 0.)

    def test_q_parameter_and_lost_motion_are_not_silently_clamped(self):
        report = key.arithmetic_report(); domain = report['continuous_ideal_parameter_domain']
        self.assertLess(domain['actual_KEY_Y_translation_mm'][0], 0.)
        self.assertGreater(domain['actual_KEY_Y_translation_mm'][1], 12.)
        self.assertFalse(domain['manufacturing_tolerances_elasticity_and_preload_included'])
        for q in (-.1, 12.1):
            with self.assertRaises(ValueError): key.pin_center(q, key.clearance_cases()[0])

    def test_default_report_cannot_be_read_as_native_or_phone_acceptance(self):
        report = key.arithmetic_report()
        json.dumps(report, allow_nan=False)
        self.assertFalse(report['native_checks_executed'])
        self.assertTrue(report['reconstruction_changes_include_added_material'])
        for name in key.RELEASE: self.assertIs(report[name], False)
        self.assertGreater(report['nominal_near_radial_wall_mm'], .5)
        self.assertAlmostEqual(report['nominal_FPC_side_gap_mm'], .2, delta=1e-14)


if __name__ == '__main__':
    unittest.main()
