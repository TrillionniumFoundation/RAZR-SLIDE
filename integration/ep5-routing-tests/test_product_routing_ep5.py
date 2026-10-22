"""Independent numerical/kinematic regressions for the new EP5 study.

Native Boolean checks are run by --native; these tests do not assert supplier
material, manufactured thickness, fatigue, force or complete-phone motion.
"""
import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import product_routing_ep5 as ep5


def simpson(function, intervals=4096):
    h = 1./intervals
    return h/3.*math.fsum([function(0.),function(1.),*[
        (4 if i % 2 else 2)*function(i*h) for i in range(1,intervals)]])


class EP5RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = ep5.load_config()

    def test_fixed_total_length_against_independent_quadrature(self):
        c = self.c; r = c['route']
        integral = simpson(lambda u:math.sin(math.pi*(3*u*u-2*u**3)))
        for slide,descent in ((0,0),(40,0),(79.75,0),(79.75,4.1),(79.75,7.65),(79.75,8.2)):
            n = ep5.pose_numbers(slide,descent,c)
            s_length = simpson(lambda u:math.hypot(10.,n['S_rise_mm']*30*u*u*(1-u)**2))
            up = (r['B_high_lane_z_mm']-r['B_low_lane_z_mm'])/integral
            down = (r['B_high_lane_z_mm']-r['B_anchor_local_mm'][2])/integral
            direct = n['A_straight_mm']+s_length+n['bridge_straight_mm']+up+n['middle_reverse_straight_mm']+down+n['B_straight_mm']
            self.assertAlmostEqual(direct,164.,delta=2e-10)

    def test_global_material_derivatives_in_all_three_curves(self):
        n = ep5.pose_numbers(79.75,4.1,self.c); j = ep5.joins(n,self.c)
        intervals = ((j[1],j[2]),(j[3],j[4]),(j[5],j[6]))
        for lo,hi in intervals:
            for fraction in (.2,.4,.6,.8):
                station = lo+(hi-lo)*fraction
                value = ep5.evaluate_material_station(station,n,self.c)
                minus = ep5.evaluate_material_station(station-1e-4,n,self.c)
                plus = ep5.evaluate_material_station(station+1e-4,n,self.c)
                np.testing.assert_allclose((plus[0]-minus[0])/2e-4,value[1],atol=2e-8,rtol=0)
                np.testing.assert_allclose((plus[2]-minus[2])/2e-4,-value[3]*value[1],atol=2e-8,rtol=0)

    def test_joins_remain_G2_with_forward_B_endpoint(self):
        for pose in (*ep5.POSES.values(),(79.75,7.65)):
            sec,n = ep5.route_sections(*pose,self.c)
            self.assertTrue(np.all(np.diff(sec['s'])>1e-10))
            np.testing.assert_allclose(sec['center'][[0,-1]],[n['A_endpoint_world_mm'],n['B_endpoint_world_mm']],atol=1e-10,rtol=0)
            np.testing.assert_allclose(sec['tangent'][[0,-1]],[[0,1,0],[0,1,0]],atol=1e-12,rtol=0)
            np.testing.assert_allclose(sec['normal'][[0,-1]],[[0,0,1],[0,0,1]],atol=1e-12,rtol=0)
            for index in (0,-1):
                frame = np.column_stack([sec[k][index] for k in ('width_axis','tangent','normal')])
                self.assertAlmostEqual(float(np.linalg.det(frame)),1.,delta=1e-12)
            for station in n['exact_join_material_labels_mm'][1:-1]:
                value = ep5.evaluate_material_station(station,n,self.c)
                self.assertAlmostEqual(value[3],0.,delta=1e-12)
                for sign in (-1,1):
                    near = ep5.evaluate_material_station(station+sign*1e-7,n,self.c)
                    np.testing.assert_allclose(near[1],value[1],atol=1e-10,rtol=0)
                    self.assertLess(abs(near[3]),1e-6)

    def test_continuous_extrema_include_interior_flat_S(self):
        report = ep5.arithmetic_report(self.c); bounds = report['continuous_necessary_bounds']
        self.assertAlmostEqual(report['interior_seating_S_flat_critical_point']['S_rise_mm'],0.,delta=1e-12)
        self.assertLess(report['interior_seating_S_flat_critical_point']['S_length_mm'],report['poses']['OPEN']['S_length_mm'])
        for slide,descent in [*( (float(s),0.) for s in np.linspace(0,79.75,257)),
                              *( (79.75,float(d)) for d in np.linspace(0,8.2,257))]:
            n = ep5.pose_numbers(slide,descent,self.c)
            self.assertGreaterEqual(n['bridge_straight_mm'],bounds['minimum_bridge_straight_mm']-1e-11)
            self.assertGreaterEqual(n['B_straight_mm'],bounds['minimum_B_straight_mm']-1e-11)
            self.assertGreaterEqual(n['middle_reverse_straight_mm'],bounds['minimum_turn_separation_mm']-1e-11)
            self.assertGreaterEqual(n['finite_thickness_Jacobian_continuous_lower_bound'],bounds['minimum_Jacobian_lower_bound']-1e-11)
        self.assertGreater(bounds['minimum_Jacobian_lower_bound'],.96)
        self.assertFalse(bounds['obstacle_or_self_clearance_proved'])
        self.assertFalse(report['complete_motion_accepted'])

    def test_taper_is_fixed_material_cut_and_stays_in_straight_regions(self):
        r = self.c['route']; end = r['free_length_mm']
        self.assertEqual(float(ep5.material_width(0,self.c)),12.)
        self.assertEqual(float(ep5.material_width(end,self.c)),12.)
        self.assertEqual(float(ep5.material_width(end/2,self.c)),10.8)
        samples = np.linspace(0,4,65)
        np.testing.assert_allclose(ep5.material_width(samples,self.c),ep5.material_width(end-samples,self.c),atol=1e-12,rtol=0)
        for pose in ep5.POSES.values():
            sec,_ = ep5.route_sections(*pose,self.c)
            mask = (sec['s']<=4.)|(sec['s']>=end-4.)
            np.testing.assert_allclose(sec['tangent'][mask],np.tile([0.,1.,0.],(sum(mask),1)),atol=1e-12,rtol=0)
            self.assertTrue(np.all(sec['material_width_mm']>=10.8))
            self.assertTrue(np.all(sec['material_width_mm']<=12.))

    def test_research_identity_cannot_grant_release_or_change_cabins(self):
        for key in ep5.GO_KEYS:
            bad = copy.deepcopy(self.c); bad[key] = True
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder)/'config.json'; path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):ep5.load_config(path)
        for key,value in (('free_length_mm',120),('middle_width_mm',12)):
            bad = copy.deepcopy(self.c); bad['route'][key] = value
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder)/'config.json'; path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):ep5.load_config(path)

    def test_invalid_poses_and_material_labels_fail_closed(self):
        for pose in ((True,0),(0,1),(-1,0),(79.75,float('nan')),(float('inf'),0)):
            with self.assertRaises(ValueError):ep5.pose_numbers(*pose,self.c)
        n = ep5.pose_numbers(0,0,self.c)
        for s in (-1,165,float('nan')):
            with self.assertRaises(ValueError):ep5.evaluate_material_station(s,n,self.c)


if __name__ == '__main__':
    unittest.main()
