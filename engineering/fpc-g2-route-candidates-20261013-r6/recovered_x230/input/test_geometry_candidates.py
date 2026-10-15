#!/usr/bin/env python3
"""Meaningful geometry identities and retained infeasible boundary cases."""
import sys
sys.dont_write_bytecode = True
import unittest
import numpy as np
from geometry_candidates import Config, GeometryRejected, build_candidate, candidate_configs, poses, polyline_self_intersections


class GeometryTests(unittest.TestCase):
    def test_fixed_length_anchors_and_all_eight_g2_joins(self):
        for config in candidate_configs():
            for s,q in ((0.,0.),(39.875,0.),(79.75,0.),(79.75,8.2)):
                curve=build_candidate(config,s,q)
                self.assertAlmostEqual(curve.bounds[-1],config.target_length_mm,places=8)
                p,t,k=curve.evaluate([0.,curve.target])
                np.testing.assert_allclose(p,[[32.7,70.,6.05],[32.7,15+s,-3.4+q]],atol=1e-10)
                for error in curve.joint_errors():
                    self.assertLess(error['position_error_mm'],1e-10)
                    self.assertLess(error['tangent_error'],1e-10)
                    self.assertLess(error['curvature_error_per_mm'],1e-9)

    def test_fixed_material_station_arclength_roundtrip(self):
        curve=build_candidate(Config(dA_mm=1.,dB_mm=1.,dJ_mm=.5),79.75,4.1)
        for seg in curve.segments:
            u=np.linspace(0.,1.,23)
            distance=seg.partial_length(u)
            recovered=seg.inverse_length(distance)
            np.testing.assert_allclose(recovered,u,atol=2e-9)

    def test_gauss_length_independently_matches_adaptive_integral(self):
        for s,q in ((0.,0.),(79.75,0.),(79.75,8.2)):
            curve=build_candidate(Config(dA_mm=1.,dB_mm=1.,dJ_mm=.5),s,q)
            adaptive=sum(seg.adaptive_length()[0] for seg in curve.segments)
            self.assertLess(abs(adaptive-curve.target),2e-8)

    def test_b_stub_trim_cannot_eat_fixed_B_endpoint(self):
        with self.assertRaises(GeometryRejected):
            build_candidate(Config(dB_mm=1.31),0.,0.)

    def test_short_target_rejected_without_stretching_material(self):
        with self.assertRaises(GeometryRejected):
            build_candidate(Config(target_length_mm=20.),0.,0.)

    def test_slide_and_dock_cannot_overlap(self):
        with self.assertRaises(GeometryRejected):
            build_candidate(Config(),20.,4.)

    def test_relocating_U_not_silently_allowed(self):
        with self.assertRaises(GeometryRejected):
            build_candidate(Config(cx_mm=20.),0.,0.)

    def test_fixed_sigma_domain_is_enforced(self):
        curve=build_candidate(Config(),0.,0.)
        with self.assertRaises(GeometryRejected):
            curve.evaluate([-1.,curve.target+1.])

    def test_exact_sequence_121_poses_has_no_dock_duplicate(self):
        states=poses()
        self.assertEqual(len(states),121)
        self.assertEqual(len(set(states)),121)
        self.assertEqual(states[-1],(79.75,8.2))

    def test_actual_crossed_chords_are_detected(self):
        screen=polyline_self_intersections([[-1,-1,0],[1,1,0],[-1,1,0],[1,-1,0]])
        self.assertEqual(screen['intersecting_chord_pairs'],1)
        self.assertLess(screen['first_witnesses'][0]['distance_mm'],1e-12)

    def test_projected_crossing_of_skew_3d_chords_is_not_a_true_intersection(self):
        screen=polyline_self_intersections([[-1,-1,0],[1,1,0],[-1,1,1],[1,-1,1]])
        self.assertEqual(screen['intersecting_chord_pairs'],0)

    def test_position_only_material_curvature_finite_difference(self):
        # The old 2e-10 mm inverse residual gave a retained 0.00750/mm error.
        # Tightened inverse precision must fix that actual numerical failure.
        for config in candidate_configs():
            curve=build_candidate(config,0.,0.)
            sigma=(curve.bounds[:-1]+curve.bounds[1:])/2
            h=2e-4
            p,t,k=curve.evaluate(sigma)
            pm=curve.evaluate(sigma-h)[0]
            pp=curve.evaluate(sigma+h)[0]
            first=(pp-pm)/(2*h)
            second=(pp-2*p+pm)/(h*h)
            self.assertLess(np.max(np.linalg.norm(first-t,axis=1)),5e-5)
            self.assertLess(np.max(np.linalg.norm(second-k,axis=1)),1e-3)


if __name__=='__main__':
    unittest.main(verbosity=2)
