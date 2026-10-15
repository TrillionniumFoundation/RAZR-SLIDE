from pathlib import Path
import json,math,sys,unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
import pawl_longitudinal_guide as g
import verify_pawl_longitudinal_guide as w


class LongitudinalGuideTests(unittest.TestCase):
    # Analytic tests run without any external baseline. Native tests are in
    # the independent manifest-to-manifest verifier; do not silently skip them.
    def simple_rows(self):
        rows=[];gaps=[]
        for normal,locations,gap in [
            ((1,0,0),[(1,y,z) for y in (-2,2) for z in (-1,1)],.05),
            ((-1,0,0),[(-1,y,z) for y in (-2,2) for z in (-1,1)],.05),
            ((0,1,0),[(x,2,z) for x in (-1,1) for z in (-1,1)],.08),
            ((0,-1,0),[(x,-2,z) for x in (-1,1) for z in (-1,1)],.08)]:
            for p in locations:rows.append([*normal,*np.cross(p,normal)]);gaps.append(gap)
        return rows,gaps

    def test_finite_capsule_volume(self):
        body=w.capsule_x(0.,2.,0.,0.,3.,.5)
        self.assertAlmostEqual(w.v.v.vol(body),(math.pi*.5**2+2*.5*3)*2,places=7)

    def test_capsule_requires_finite_ordered_input(self):
        for args in [(0,0,0,0,1,1),(0,1,0,1,0,1),(0,1,0,0,1,-1),(0,1,0,0,1,float('nan'))]:
            with self.assertRaises(ValueError):w.capsule_x(*args)

    def test_both_cheek_carriers_single_solids(self):
        for side in 'LR':
            for s in g.reliefs(side):self.assertEqual(len(s.Solids()),1)

    def test_lands_exact_nominal_gaps(self):
        self.assertAlmostEqual(18.15-g.LANDS[0][2][1],.08)
        self.assertAlmostEqual(g.LANDS[1][1][1]-22.15,.08)

    def test_land_mirror_preserves_volume(self):
        right=g.additions('R');left=g.additions('L')
        self.assertEqual(len(right),2)
        for (_,a),(_,b) in zip(right,left):self.assertAlmostEqual(a.Volume(),b.Volume(),places=7)

    def test_invalid_side_rejected(self):
        for s in ('', 'LR', 'Q',None):
            with self.assertRaises(ValueError):g.additions(s)

    def test_missing_baseline_not_accepted(self):
        with self.assertRaises(ValueError):g.build({})

    def test_pure_X_and_Y_faces_span_five_directions(self):
        A,b=self.simple_rows();r=w.first_order_bounds(A,b)
        self.assertEqual(r['rank'],5)
        self.assertTrue(r['remaining_nominal_axial_column_zero'])

    def test_each_unwanted_linearized_direction_bounded(self):
        A,b=self.simple_rows();r=w.first_order_bounds(A,b)
        self.assertTrue(all(x['status']=='bounded_first_order_only' for x in r['bounds']))
        self.assertEqual([x['axis'] for x in r['bounds']],[0,1,3,4,5])

    def test_pure_translation_linear_bounds(self):
        A,b=self.simple_rows();r=w.first_order_bounds(A,b)['bounds']
        self.assertAlmostEqual(r[0]['upper'],.05);self.assertAlmostEqual(r[0]['lower'],-.05)
        self.assertAlmostEqual(r[1]['upper'],.08);self.assertAlmostEqual(r[1]['lower'],-.08)

    def test_lateral_only_retains_missing_Y_and_roll(self):
        A,b=self.simple_rows();r=w.first_order_bounds(A[:8],b[:8])
        self.assertEqual(r['rank'],3)
        d={x['axis']:x for x in r['bounds']}
        self.assertEqual(d[1]['status'],'unbounded');self.assertEqual(d[3]['status'],'unbounded')

    def test_rank_five_alone_is_not_unilateral_boundedness(self):
        A,b=self.simple_rows();r=w.first_order_bounds(A[:12],b[:12])
        self.assertEqual(r['rank'],5)
        self.assertTrue(any(x['status']=='unbounded' for x in r['bounds']))

    def test_gap_scaling_affects_motion_not_rank(self):
        A,b=self.simple_rows();a=w.first_order_bounds(A,b);z=w.first_order_bounds(A,[2*x for x in b])
        self.assertEqual(a['rank'],z['rank'])
        for x,y in zip(a['bounds'],z['bounds']):self.assertAlmostEqual(y['upper'],2*x['upper'])

    def test_no_preload_or_rating_inferred(self):
        A,b=self.simple_rows();r=w.first_order_bounds(A,b)
        self.assertFalse(r['actual_contacts_active_at_centered_pose'])
        self.assertIsNone(r['preload_stiffness_load_rating'])

    def test_invalid_matrix_rejected(self):
        for A,b in [([[1]*5],[1]),([[1]*6],[-1]),([[1]*6],[float('inf')]),([[float('nan')]*6],[1])]:
            with self.assertRaises(ValueError):w.first_order_bounds(A,b)

    def test_invalid_gap_shape_rejected(self):
        A,b=self.simple_rows()
        with self.assertRaises(ValueError):w.first_order_bounds(A,b[:-1])

    def test_tangent_guide_not_zero_clearance_claim(self):
        A,b=self.simple_rows();r=w.first_order_bounds(A,b)
        self.assertGreater(r['bounds'][0]['upper']-r['bounds'][0]['lower'],0.)

    def test_slot_coupling_sign(self):
        slope=1.06/3.;u=1.5
        for dy in (-.08,0.,.08):
            z=.02+slope*(u-dy)
            self.assertAlmostEqual(z+slope*dy,.02+slope*u)

    def test_full_slot_shift_enclosure_not_centerline_only(self):
        slope=1.06/3.;half=.025*math.hypot(1,slope)
        low=.02-half-slope*.08;high=1.08+half+slope*.08
        self.assertLess(low,.02-half);self.assertGreater(high,1.08+half)

    def test_collar_radial_enclosure_covers_all_rectangle_corners(self):
        slope=1.06/3.;half=.025*math.hypot(1,slope);bound=math.hypot(.08,slope*.08+half)
        for dy in (-.08,.08):
            for f in (-1,1):self.assertLessEqual(math.hypot(dy,-slope*dy+f*half),bound+1e-14)
        self.assertLess(.65+bound,.78)


if __name__=='__main__':unittest.main(verbosity=2)
