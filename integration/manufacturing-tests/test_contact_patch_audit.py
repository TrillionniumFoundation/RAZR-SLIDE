from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import contact_patch_audit as m

TRI=np.array([[0.,0.],[1.,0.],[0.,1.]])
SQUARE=np.array([[0.,0.],[1.,0.],[1.,1.],[0.,1.]])

def nodes(t):return np.vstack([t,(t[0]+t[1])/2,(t[1]+t[2])/2,(t[2]+t[0])/2])

class ContactPatchAuditTests(unittest.TestCase):
    def test_shape_function_node_identity(self):
        c=m.triangle_coefficients(TRI,np.eye(6));np.testing.assert_allclose(m.evaluate(c,nodes(TRI)),np.eye(6),atol=1e-14)
    def test_constant_reproduction(self):
        c=m.triangle_coefficients(TRI,np.full(6,3.));np.testing.assert_allclose(c,[3,0,0,0,0,0],atol=1e-14)
    def test_affine_reproduction(self):
        c=np.array([.2,3,-4,0,0,0]);np.testing.assert_allclose(m.triangle_coefficients(TRI,m.evaluate(c,nodes(TRI))),c,atol=1e-14)
    def test_general_quadratic_reproduction(self):
        c=np.array([.2,3,-4,5,-6,7]);np.testing.assert_allclose(m.triangle_coefficients(TRI,m.evaluate(c,nodes(TRI))),c,atol=1e-14)
    def test_translated_coordinates_have_common_origin(self):
        o=np.array([34.8,70.]);c=np.array([1.,2,3,4,5,6]);t=TRI+o
        np.testing.assert_allclose(m.triangle_coefficients(t,m.evaluate(c,nodes(t),o),o),c,atol=1e-12)
    def test_skew_triangle_multiple_fields(self):
        t=np.array([[.1,.2],[2.,.5],[.3,1.7]]);c=np.arange(18,dtype=float).reshape(6,3)/13
        np.testing.assert_allclose(m.triangle_coefficients(t,m.evaluate(c,nodes(t))),c,atol=1e-12)
    def test_reversed_triangle_order(self):
        t=TRI[::-1];c=np.array([1.,2,3,4,5,6]);np.testing.assert_allclose(m.triangle_coefficients(t,m.evaluate(c,nodes(t))),c,atol=1e-13)
    def test_interior_minimum_not_vertices(self):
        c=np.array([.03,-.4,-.6,1.,0.,1.]);r=m.extrema(c,TRI)
        self.assertEqual(r['minimum_kind'],'interior_stationary');self.assertAlmostEqual(r['minimum'],-.10)
        self.assertGreater(m.evaluate(c,TRI).min(),0.)
    def test_edge_stationary_minimum(self):
        r=m.extrema([.25,-1,1,1,0,0],TRI);self.assertEqual(r['minimum_kind'],'edge_stationary');self.assertAlmostEqual(r['minimum'],0.)
    def test_interior_maximum(self):
        r=m.extrema([0,1,1,-1,0,-1],SQUARE);self.assertAlmostEqual(r['maximum'],.5);self.assertEqual(r['maximum_kind'],'interior_stationary')
    def test_saddle_extrema_on_boundary(self):
        r=m.extrema([0,0,0,0,1,0],SQUARE-0.5);self.assertAlmostEqual(r['minimum'],-.25);self.assertAlmostEqual(r['maximum'],.25)
    def test_flat_direction_kept_not_regularized(self):
        r=m.extrema([.25,-1,0,1,0,0],SQUARE);self.assertAlmostEqual(r['minimum'],0.);self.assertAlmostEqual(r['maximum'],.25)
    def test_constant_extrema(self):
        r=m.extrema([2.,0,0,0,0,0],TRI);self.assertEqual(r['minimum'],2.);self.assertEqual(r['maximum'],2.)
    def test_clockwise_polygon_and_closed_ring(self):
        r=m.extrema([0,1,2,0,0,0],np.vstack([SQUARE[::-1],SQUARE[-1]]));self.assertEqual(r['minimum'],0);self.assertEqual(r['maximum'],3)
    def test_nonconvex_polygon_refused(self):
        with self.assertRaises(ValueError):m.extrema([0]*6,[[0,0],[1,0],[.2,.2],[0,1]])
    def test_degenerate_triangle_refused(self):
        with self.assertRaises(ValueError):m.triangle_coefficients([[0,0],[1,0],[2,0]],np.zeros(6))
    def test_degenerate_polygon_refused(self):
        with self.assertRaises(ValueError):m.extrema([0]*6,[[0,0],[1,0],[2,0]])
    def test_nonfinite_coefficients_refused(self):
        with self.assertRaises(ValueError):m.extrema([float('nan')]*6,TRI)
    def test_boolean_triangle_refused(self):
        with self.assertRaises(ValueError):m.triangle_coefficients(np.ones((3,2),dtype=bool),np.zeros(6))
    def test_bad_field_shape_refused(self):
        with self.assertRaises(ValueError):m.triangle_coefficients(TRI,[1,2,3])
    def test_signed_mean_zero_not_local_pass(self):
        r=m.extrema([-.5,1,0,0,0,0],SQUARE);s=m.gap_status(r['minimum'],r['maximum'],tolerance_mm=1e-7,compressive_force=1)
        self.assertFalse(s['nonpenetration_satisfied']);self.assertFalse(s['loaded_patch_zero_gap_satisfied'])
    def test_open_unloaded_patch_is_admissible(self):
        s=m.gap_status(.1,.2,tolerance_mm=1e-7);self.assertTrue(s['resolved_contact_compatible_on_audited_domain'])
    def test_open_loaded_patch_is_not_admissible(self):
        s=m.gap_status(.1,.2,tolerance_mm=1e-7,compressive_force=1);self.assertFalse(s['loaded_patch_zero_gap_satisfied'])
    def test_closed_compressive_patch_allowed_not_hardware_release(self):
        s=m.gap_status(0.,0.,tolerance_mm=1e-7,compressive_force=1);self.assertTrue(s['resolved_contact_compatible_on_audited_domain']);self.assertFalse(s['manufacturing_go']);self.assertFalse(s['candidate_go'])
    def test_negative_tolerance_refused(self):
        with self.assertRaises(ValueError):m.gap_status(0,1,tolerance_mm=-1)
    def test_random_convex_quadratic_has_known_interior_minimum(self):
        rng=np.random.default_rng(8371)
        for _ in range(30):
            z=rng.uniform(.1,.3,2);A=rng.normal(size=(2,2));A=A.T@A+np.eye(2)*.5;b=-2*A@z;c=np.r_[z@A@z-.123,b,A[0,0],2*A[0,1],A[1,1]]
            r=m.extrema(c,TRI);self.assertAlmostEqual(r['minimum'],-.123,places=11);np.testing.assert_allclose(r['minimum_at'],z,atol=1e-11)
    def test_extrema_enclose_independent_dense_samples(self):
        rng=np.random.default_rng(611)
        xy=np.array([[i/30,j/30] for i in range(31) for j in range(31-i)])
        for _ in range(40):
            c=rng.normal(size=6);r=m.extrema(c,TRI);vals=m.evaluate(c,xy)
            self.assertLessEqual(r['minimum'],vals.min()+1e-12);self.assertGreaterEqual(r['maximum'],vals.max()-1e-12)
    def test_different_triangle_partitions_recover_same_field(self):
        from shapely.geometry import Polygon
        a=np.array([[0.,0.],[1.,0.],[1.,1.]]);b=np.array([[0.,0.],[1.,0.],[0.,1.]])
        ca=np.array([1.,2,3,4,5,6]);cb=np.array([-1.,2,0,1,0,2]);inter=Polygon(a).intersection(Polygon(b))
        r=m.extrema(m.triangle_coefficients(a,m.evaluate(ca,nodes(a)))-m.triangle_coefficients(b,m.evaluate(cb,nodes(b))),np.array(inter.exterior.coords))
        expected=m.extrema(ca-cb,np.array(inter.exterior.coords));self.assertAlmostEqual(r['minimum'],expected['minimum']);self.assertAlmostEqual(r['maximum'],expected['maximum'])
