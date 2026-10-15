from pathlib import Path
from dataclasses import replace
import math
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
import phone_layout as p


class PhoneLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d=p.Dimensions(73.99,94.25,8.,79.75,8.2,.2,.65)
        cls.parts={side:p.build_cabin(cls.d,side,stepped=True) for side in 'AB'}
        cls.cages=p.operating_enclosures(cls.d)

    def test_nonfinite_and_boolean_dimensions_rejected(self):
        for value in (True,float('nan'),float('inf'),0,-1,'73.99'):
            with self.assertRaises(ValueError):replace(self.d,width_mm=value)

    def test_stowed_gap_not_silently_violated(self):
        with self.assertRaises(ValueError):replace(self.d,thickness_mm=8.1)

    def test_no_negative_cavity(self):
        with self.assertRaises(ValueError):replace(self.d,study_wall_mm=4.)

    def test_overlap_model_requires_positive_overlap(self):
        with self.assertRaises(ValueError):replace(self.d,height_mm=79.75)

    def test_fixed_dimensions_not_tied_to_one_nominal_case(self):
        d=replace(self.d,height_mm=95.,width_mm=74.5,thickness_mm=7.9)
        a=p.build_cabin(d,'A',stepped=True);b=p.build_cabin(d,'B',stepped=True)
        self.assertEqual(p.common(a['shell'],b['shell'].translate((0,d.slide_mm,0))),0.)

    def test_both_outer_bounds_equal(self):
        self.assertEqual(p.bounds(self.parts['A']['outer']),p.bounds(self.parts['B']['outer']))

    def test_shells_and_cavities_are_complete_connected_solids(self):
        for parts in self.parts.values():
            for body in parts.values():self.assertEqual(len(p.single(body).Solids()),1)

    def test_cavity_never_relabels_shell_material_as_free(self):
        for parts in self.parts.values():
            self.assertEqual(p.outside(parts['cavity'],parts['outer']),0.)
            self.assertEqual(p.common(parts['cavity'],parts['shell']),0.)
            self.assertAlmostEqual(p.volume(parts['shell'])+p.volume(parts['cavity']),p.volume(parts['outer']),places=6)

    def test_overlap_uses_current_motion(self):
        self.assertAlmostEqual(self.d.overlap,14.5)
        self.assertAlmostEqual(self.d.lap_length,14.7)

    def test_rectangular_negative_control_really_collides(self):
        a=p.build_cabin(self.d,'A',stepped=False);b=p.build_cabin(self.d,'B',stepped=False)
        self.assertGreater(p.common(a['shell'],b['shell'].translate((0,self.d.slide_mm,0))),1.)

    def test_three_study_poses_have_no_positive_interference(self):
        a,b=self.parts['A']['shell'],self.parts['B']['shell']
        for move in ((0,0,8.2),(0,79.75,8.2),(0,79.75,0)):
            self.assertEqual(p.common(a,b.translate(move)),0.)

    def test_whole_translation_enclosures_clear(self):
        for cage in self.cages.values():self.assertEqual(p.common(self.parts['A']['outer'],cage),0.)

    def test_enclosures_contain_mid_motion_not_only_endpoints(self):
        for distance in (0,17.3,39.875,79.75):
            self.assertEqual(p.outside(self.parts['B']['outer'].translate((0,distance,8.2)),self.cages['slide_outer_superset']),0.)
        seated=p.single(self.cages['seat_lap_superset'].fuse(self.cages['seat_body_superset']).clean())
        for z in (0,.1,4.1,8.2):
            self.assertEqual(p.outside(self.parts['B']['outer'].translate((0,79.75,z)),seated),0.)

    def test_removed_lap_clearance_reintroduces_collision(self):
        b=self.parts['B']['shell'].translate((0,79.75,-.25))
        self.assertGreater(p.common(self.parts['A']['shell'],b),0.)

    def test_usable_cavity_cost_is_not_hidden(self):
        expected=math.prod(self.d.cavity_size)
        self.assertAlmostEqual(p.volume(self.parts['A']['cavity']),expected,places=6)
        old=p.build_cabin(self.d,'A',stepped=False)
        self.assertGreater(p.volume(old['cavity']),expected)

    def test_exactly_24_proper_rotations_without_reflections(self):
        rotations=p.proper_axis_rotations();self.assertEqual(len(rotations),24)
        self.assertEqual(len({tuple(x for row in m for x in row) for m in rotations}),24)
        for m in rotations:
            det=m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1])-m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0])+m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0])
            self.assertEqual(det,1)

    def test_current_complete_reservation_rejected_in_limited_study(self):
        r=p.reservation_trials(self.d.cavity_size,(12.,16.445,21.21))
        self.assertEqual(r['accepted_count'],0)
        self.assertTrue(r['not_a_proof_against_arbitrary_tilt_or_actual_nonrectangular_material'])

    def test_reservation_search_can_pass_small_positive_control(self):
        self.assertEqual(p.reservation_trials(self.d.cavity_size,(1.,2.,3.))['accepted_count'],24)

    def test_invalid_reservations_rejected(self):
        for values in ((1,2), (1,2,float('nan')), (True,2,3),(1,0,3)):
            with self.assertRaises(ValueError):p.reservation_trials(self.d.cavity_size,values)

    def test_unknown_cabin_and_nonboolean_variant_rejected(self):
        with self.assertRaises(ValueError):p.build_cabin(self.d,'C',stepped=True)
        with self.assertRaises(ValueError):p.build_cabin(self.d,'A',stepped=1)
