import sys,math,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'integration'))
from cam_contact_profile import ContactProfile

class ContactProfileTests(unittest.TestCase):
    def setUp(self):self.p=ContactProfile(.1,1.04,-.0011145618,2.,0.,-.02)
    def test_breakpoints_have_native_values(self):
        for actual,expected in zip(self.p.breakpoints,[.0011145618,.09055728089999159,.6429179606749895]):self.assertAlmostEqual(actual,expected,places=12)
    def test_measured_home_and_lower_stop(self):
        self.assertAlmostEqual(self.p.evaluate(0)[0],1.14,places=12);self.assertEqual(self.p.evaluate(12)[0],-.02)
    def test_ramp_tangent_distance_equals_pin_radius(self):
        for q in [.1,.15,.3,.55,.6]:
            h,dh,branch=self.p.evaluate(q);floor=self.p.floor_height+2*(-q-self.p.floor_corner_q)
            self.assertAlmostEqual((h-floor)/math.sqrt(5),.1,places=12);self.assertEqual(dh,-2);self.assertEqual(branch,'ramp')
    def test_corner_center_distance_equals_radius(self):
        for q in [.005,.025,.05,.075]:
            h,_,b=self.p.evaluate(q);self.assertEqual(b,'rounded_corner');self.assertAlmostEqual(math.hypot(-q-self.p.floor_corner_q,h-1.04),.1,places=12)
    def test_derivative_matches_symmetric_difference(self):
        for q in [.005,.025,.075,.15,.3,1.,10.]:
            h,d,_=self.p.evaluate(q);epsilon=1e-7
            observed=(self.p.evaluate(q+epsilon)[0]-self.p.evaluate(q-epsilon)[0])/(2*epsilon)
            self.assertAlmostEqual(observed,d,places=6)
    def test_all_joins_continuous(self):
        for q in self.p.breakpoints:self.assertLess(abs(self.p.evaluate(q-1e-10)[0]-self.p.evaluate(q+1e-10)[0]),1e-9)
    def test_rounding_and_plateau_are_C1(self):
        for q in self.p.breakpoints[:2]:self.assertLess(abs(self.p.evaluate(q-1e-10)[1]-self.p.evaluate(q+1e-10)[1]),1e-7)
    def test_lower_stop_impact_not_hidden_by_smoothing(self):
        q=self.p.breakpoints[-1];self.assertEqual(self.p.evaluate(q-1e-8)[1],-2.);self.assertEqual(self.p.evaluate(q+1e-8)[1],0.)
    def test_interval_extrema_are_at_endpoints(self):
        for a,b in [(0,.1),(.05,.6),(.6,12.),(.2,.4)]:
            lo,hi=self.p.height_bounds(a,b)
            for i in range(51):self.assertTrue(lo<=self.p.evaluate(a+(b-a)*i/50)[0]<=hi)
    def test_wrong_interval_rejected(self):
        with self.assertRaises(ValueError):self.p.height_bounds(.5,.1)
    def test_bad_travel_rejected(self):
        for q in [-1,12.1,math.nan,math.inf,True,'0']:
            with self.subTest(q=q),self.assertRaises(ValueError):self.p.evaluate(q)
    def test_nonfinite_profile_rejected(self):
        for r in [math.nan,math.inf,-.1,0,True]:
            with self.subTest(r=r),self.assertRaises(ValueError):ContactProfile(r,1.04,-.0011145618,2.,0.,-.02)
    def test_misordered_branch_rejected(self):
        with self.assertRaises(ValueError):ContactProfile(.1,1.04,.2,2.,0.,-.02)
    def test_offset_pin_height_keeps_same_kinematics(self):
        other=ContactProfile(.1,6.04,-.0011145618,2.,0.,4.98)
        for q in [0,.05,.1,.3,1.,12.]:self.assertAlmostEqual(other.evaluate(q)[0]-self.p.evaluate(q)[0],5.,places=12)
    def test_no_force_or_fatigue_release(self):
        x=self.p.receipt();self.assertTrue(x['selected_branch_requires_lower_restoring_force']);self.assertFalse(x['dynamic_force_friction_and_material_qualification']);self.assertFalse(x['manufacturing_go'])
