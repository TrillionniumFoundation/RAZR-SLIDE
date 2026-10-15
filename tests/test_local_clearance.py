import importlib.util
import math
from pathlib import Path
import unittest

p=Path(__file__).resolve().parents[1]/'integration/local_clearance.py'
spec=importlib.util.spec_from_file_location('local_clearance_under_test',p)
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


class LocalClearanceTests(unittest.TestCase):
    def test_nonmonotone_both_ends_collide_but_middle_is_clear(self):
        f=lambda r: 0.0 if .5 <= r <= .7 else .1
        x=c.sampled_clearance_bracket(f,[-.02,0.,.2,.4,.6,.8,1.2])
        self.assertGreaterEqual(x['clear_position'],.5)
        self.assertLess(x['clear_position'],.50000001)
        self.assertFalse(x['global_monotonicity_assumed'])
        self.assertFalse(x['continuous_path_qualified'])

    def test_monotone_transition(self):
        x=c.sampled_clearance_bracket(lambda r:max(0.,1-r),[0.,.5,1.2])
        self.assertLess(abs(x['clear_position']-1),1e-8)

    def test_no_clear_sample_is_explicit_rejection(self):
        with self.assertRaises(c.NoClearSample) as e:
            c.sampled_clearance_bracket(lambda _:1.,[0.,.5,1.])
        self.assertEqual(len(e.exception.samples),3)

    def test_first_point_clear_does_not_invent_negative_bracket(self):
        x=c.sampled_clearance_bracket(lambda _:0.,[0.,1.])
        self.assertEqual(x['clear_position'],0.)
        self.assertIsNone(x['colliding_bracket_position'])

    def test_invalid_grids_are_rejected(self):
        for pts in [[],[0.,0.],[1.,0.],[0.,math.nan],[0.,math.inf]]:
            with self.subTest(pts=pts),self.assertRaises(ValueError):
                c.sampled_clearance_bracket(lambda _:0.,pts)

    def test_negative_signed_volume_is_not_abs_or_zero(self):
        with self.assertRaises(ValueError):
            c.sampled_clearance_bracket(lambda _:-1e-12,[0.,1.])

    def test_nonfinite_common_is_not_clearance(self):
        for bad in [math.nan,math.inf,-math.inf]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                c.sampled_clearance_bracket(lambda _:bad,[0.,1.])

    def test_invalid_tolerances_iterations_rejected(self):
        for kw in [{'threshold':-1},{'threshold':math.nan},{'iterations':True},{'iterations':-1},{'iterations':61}]:
            with self.subTest(kw=kw),self.assertRaises(ValueError):
                c.sampled_clearance_bracket(lambda _:0.,[0.,1.],**kw)
