from pathlib import Path
import sys,unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
from spatial_contact import solve_reactions


class SpatialContactTests(unittest.TestCase):
    def test_single_stop(self):
        for q in (-2.,0.,.1,1.,3.):
            r=solve_reactions([[2.]],np.zeros((1,0)),[q],[],[],[],[.2])
            self.assertTrue(r['passed']);self.assertAlmostEqual(r['forces'][0],max(0.,(q-.2)/2),places=9)
    def test_rigid_stop(self):
        r=solve_reactions([[0.]],[[1.]],[0.],[2.],[],[],[.02])
        self.assertTrue(r['passed']);self.assertAlmostEqual(r['forces'][0],2.)
        self.assertAlmostEqual(r['rigid_coordinates'][0],.02)
    def test_rigid_unrestrained_direction_not_grounded(self):
        r=solve_reactions([[1.]],[[1.,0.]],[0.],[1.,1.],[],[],[0.])
        self.assertFalse(r['passed']);self.assertEqual(r['status'],'unsupported_rigid_load')
    def test_neutral_rigid_mode(self):
        r=solve_reactions([[1.]],[[1.,0.]],[0.],[1.,0.],[],[],[0.])
        self.assertTrue(r['passed']);self.assertEqual(r['unrestrained_rigid_modes'],1)
    def test_no_tensile_contact(self):
        r=solve_reactions([[1.]],[[1.]],[0.],[-1.],[],[],[0.])
        self.assertFalse(r['passed'])
    def test_one_spring(self):
        r=solve_reactions([[2.]],np.zeros((1,0)),[.5],[],[3.],[.4],[])
        self.assertTrue(r['passed']);self.assertAlmostEqual(r['forces'][0],(.5+1.2)/5.)
    def test_slack_spring_is_explicit(self):
        r=solve_reactions([[2.]],np.zeros((1,0)),[-2.],[],[3.],[.4],[])
        self.assertTrue(r['passed']);self.assertEqual(r['forces'][0],0.);self.assertEqual(r['slack_springs'],[0])
    def test_independent_spring_stiffness(self):
        r=solve_reactions(np.zeros((2,2)),np.ones((2,1)),[0.,0.],[3.],[1.,2.],[0.,0.],[])
        self.assertTrue(r['passed']);np.testing.assert_allclose(r['forces'],[2.,1.],atol=1e-10)
    def test_more_than_twelve_spatial_contacts(self):
        r=solve_reactions(np.eye(64),np.zeros((64,0)),np.linspace(-1,1,64),[],[],[],np.zeros(64))
        self.assertTrue(r['passed']);np.testing.assert_allclose(r['forces'],np.maximum(np.linspace(-1,1,64),0),atol=1e-10)
    def test_known_KKT_cases(self):
        rng=np.random.default_rng(123)
        for trial in range(40):
            n=5+trial%9;k=trial%3;A=rng.normal(size=(n,n));H=A.T@A+np.eye(n)
            G=rng.normal(size=(n,k));lam=np.maximum(0,rng.normal(size=n));r=rng.normal(size=k)
            gap=np.where(lam>0,0,rng.uniform(.05,.3,n));g=rng.uniform(0,.1,n)
            q0=g-gap+H@lam-G@r
            got=solve_reactions(H,G,q0,G.T@lam,[],[],g)
            self.assertTrue(got['passed'],got);np.testing.assert_allclose(got['forces'],lam,atol=1e-7)
    def test_warm_start_enrichment(self):
        r=solve_reactions([[2.,.3],[.3,1.]],np.zeros((2,0)),[1.,.6],[],[],[],[0.,0.],warm_start=[.5,0.])
        self.assertTrue(r['passed']);np.testing.assert_allclose(r['forces'],np.linalg.solve([[2.,.3],[.3,1.]],[1.,.6]),atol=1e-9)
    def test_redundant_contact_rows(self):
        r=solve_reactions(np.ones((2,2)),np.zeros((2,0)),[1.,1.],[],[],[],[0.,0.])
        self.assertTrue(r['passed']);self.assertAlmostEqual(sum(r['forces']),1.)
    def test_force_scale_invariance(self):
        for f in (1e-8,1.,1e8):
            r=solve_reactions([[1.]],[[1.]],[0.],[f],[],[],[.1])
            self.assertTrue(r['passed']);self.assertAlmostEqual(r['forces'][0]/f,1.)
    def test_nonboolean_arrays(self):
        with self.assertRaises(ValueError):solve_reactions([[True]],[[1.]],[0.],[1.],[],[],[0.])
    def test_nonfinite_rejected(self):
        for x in (float('nan'),float('inf')):
            with self.assertRaises(ValueError):solve_reactions([[x]],[[1.]],[0.],[1.],[],[],[0.])
    def test_negative_energy_rejected(self):
        with self.assertRaises(ValueError):solve_reactions([[-1.]],[[1.]],[0.],[1.],[],[],[0.])
    def test_nonsymmetric_rejected(self):
        with self.assertRaises(ValueError):solve_reactions([[1.,1.],[0.,1.]],np.zeros((2,0)),[0.,0.],[],[],[],[0.,0.])
    def test_negative_gap_rejected(self):
        with self.assertRaises(ValueError):solve_reactions([[1.]],[[1.]],[0.],[1.],[],[],[-.1])
    def test_zero_compliance_rejected(self):
        with self.assertRaises(ValueError):solve_reactions([[1.]],[[1.]],[0.],[1.],[0.],[0.],[])
    def test_iteration_limit_never_passes(self):
        r=solve_reactions(np.eye(3),np.zeros((3,0)),[1.,2.,3.],[],[],[],[0.,0.,0.],max_iterations=1)
        self.assertFalse(r['passed']);self.assertEqual(r['status'],'iteration_limit')
    def test_no_hardware_claim(self):
        r=solve_reactions([[1.]],np.zeros((1,0)),[1.],[],[],[],[0.])
        for k in ('candidate_go','fixture_fabrication_go','manufacturing_go'):self.assertFalse(r[k])
        self.assertTrue(r['between_point_gap_audit_required'])
