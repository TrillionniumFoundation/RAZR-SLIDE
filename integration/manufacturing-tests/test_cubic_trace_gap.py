from pathlib import Path
import sys,unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
import cubic_trace_gap as c

class CubicGapTests(unittest.TestCase):
    def setUp(self):self.tri=np.array([[0.,0.],[1.,0.],[0.,1.]])
    def check(self,f,**kw):return c.audit_polygon(self.tri,f,**kw)
    def test_partition_of_unity(self):
        rng=np.random.default_rng(2);l=rng.dirichlet([1,1,1],100)
        np.testing.assert_allclose(c.bernstein_values(l).sum(axis=1),1.,atol=1e-14)
    def test_coefficients_round_trip(self):
        rng=np.random.default_rng(4)
        for _ in range(30):
            b=rng.normal(size=10);got,guard=c.coefficients_from_samples(c.SAMPLES@b)
            np.testing.assert_allclose(got,b,atol=1e-14);self.assertGreater(guard,0)
    def test_subdivision_is_convex(self):
        self.assertGreaterEqual(c.SUBDIVISION.min(),0)
        np.testing.assert_array_equal(c.SUBDIVISION.sum(axis=2),np.ones((4,10)))
    def test_subdivision_preserves_polynomial(self):
        rng=np.random.default_rng(5);b=rng.normal(size=10);l=rng.dirichlet([1,1,1],20)
        for vertices,m in zip(c.CHILDREN,c.SUBDIVISION):
            np.testing.assert_allclose(c.bernstein_values(l)@(m@b),c.bernstein_values(l@vertices)@b,atol=2e-15)
    def test_constant_positive_passes(self):
        r=self.check(lambda xy:np.full(len(xy),.1));self.assertTrue(r['passed']);self.assertGreater(r['covered_lower_bound'],.099)
    def test_negative_witness_is_not_clamped(self):
        r=self.check(lambda xy:-np.ones(len(xy)));self.assertFalse(r['passed']);self.assertEqual(r['minimum_witness'],-1.)
    def test_interior_negative_invisible_at_P2_nodes(self):
        f=lambda p:.01-27*p[:,0]*p[:,1]*(1-p.sum(axis=1))
        oldnodes=np.array([[0,0],[1,0],[0,1],[.5,0],[0,.5],[.5,.5]])
        self.assertTrue(np.all(f(oldnodes)>0));r=self.check(f);self.assertEqual(r['status'],'negative_witness')
    def test_hidden_offcentre_negative_found(self):
        f=lambda p:((p[:,0]-.16)**2+(p[:,1]-.43)**2)-.0001
        r=self.check(f);self.assertFalse(r['passed']);self.assertEqual(r['status'],'negative_witness')
        self.assertLess(f(np.array([r['minimum_at']]))[0],-1e-7)
    def test_positive_polynomial_needs_subdivision(self):
        r=self.check(lambda p:(p[:,0]-.2)**2+(p[:,1]-.3)**2+1e-5)
        self.assertTrue(r['passed']);self.assertGreater(r['subtriangles'],1)
    def test_budget_exhaustion_not_pass(self):
        r=self.check(lambda p:(p[:,0]-.2)**2+(p[:,1]-.3)**2+1e-5,max_triangles=1)
        self.assertFalse(r['passed']);self.assertEqual(r['status'],'budget_exhausted')
    def test_depth_exhaustion_not_pass(self):
        r=self.check(lambda p:(p[:,0]-.2)**2+(p[:,1]-.3)**2+1e-5,max_depth=0)
        self.assertFalse(r['passed']);self.assertEqual(r['status'],'depth_exhausted')
    def test_all_convex_polygon_fan_triangles_checked(self):
        square=np.array([[0.,0.],[1.,0.],[1.,1.],[0.,1.]])
        r=c.audit_polygon(square,lambda p:1-p[:,1]*1.1)
        self.assertFalse(r['passed'])
    def test_nonfinite_callback_rejected(self):
        with self.assertRaises(ValueError):self.check(lambda p:np.full(len(p),np.nan))
    def test_quartic_callback_rejected_by_extra_probe(self):
        with self.assertRaises(ValueError):self.check(lambda p:p[:,0]**4)
    def test_invalid_budget_and_tolerance_rejected(self):
        for kwargs in [{'gap_tolerance':True},{'max_depth':True},{'max_depth':25},{'max_triangles':0}]:
            with self.assertRaises(ValueError):self.check(lambda p:np.ones(len(p)),**kwargs)
    def test_no_interval_or_hardware_claim(self):
        r=self.check(lambda p:np.ones(len(p)));self.assertFalse(r['strict_zero_or_interval_certificate'])

if __name__=='__main__':unittest.main()
