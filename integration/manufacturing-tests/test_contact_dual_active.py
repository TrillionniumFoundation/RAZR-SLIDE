from pathlib import Path
import sys,unittest,json
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contact_dual_active import solve_force_qp
from spatial_contact import solve_qp

class DualContactTests(unittest.TestCase):
    def test_one_closed_contact(self):
        r=solve_force_qp([[2.]],[3.],np.zeros((1,0)),[],free_prefix=0)
        self.assertTrue(r['passed'],r);self.assertAlmostEqual(r['forces'][0],1.5)
    def test_one_open_contact(self):
        r=solve_force_qp([[2.]],[-3.],np.zeros((1,0)),[],free_prefix=0)
        self.assertTrue(r['passed'],r);self.assertEqual(r['forces'],[0.])
    def test_explicit_rigid_equilibrium(self):
        r=solve_force_qp(np.eye(2),[.2,.1],[[1.],[1.]],[1.],free_prefix=0)
        self.assertTrue(r['passed'],r);self.assertAlmostEqual(sum(r['forces']),1.)
    def test_free_bolt_variable_not_clamped(self):
        r=solve_force_qp(np.eye(2),[-1.,1.],np.zeros((2,0)),[],free_prefix=1)
        self.assertTrue(r['passed'],r);np.testing.assert_allclose(r['forces'],[-1.,1.],atol=1e-10)
    def test_unrestrained_load_not_regularized(self):
        r=solve_force_qp(np.eye(2),[0.,0.],[[1.,0.],[1.,0.]],[0.,1.],free_prefix=0)
        self.assertFalse(r['passed']);self.assertEqual(r['status'],'unsupported_rigid_load')
    def test_neutral_mode_is_reported(self):
        r=solve_force_qp(np.eye(2),[0.,0.],[[1.,0.],[1.,0.]],[1.,0.],free_prefix=0)
        self.assertTrue(r['passed'],r);self.assertEqual(r['remaining_unsupported_rigid_directions'],1)
    def test_impossible_unilateral_support_refused(self):
        r=solve_force_qp(np.eye(2),[0.,0.],[[1.],[1.]],[-1.],free_prefix=0)
        self.assertFalse(r['passed'])
    def test_independent_qp_comparison_30_systems(self):
        rng=np.random.default_rng(801)
        for _ in range(30):
            m=8;Z=rng.normal(size=(m,m));S=Z.T@Z+np.eye(m);G=rng.normal(size=(m,2));l=np.r_[rng.normal(size=2),rng.uniform(0,1,size=m-2)];load=G.T@l;d=rng.normal(size=m)
            r=solve_force_qp(S,d,G,load,free_prefix=2)
            A=np.zeros((m-2,m));A[:,2:]=-np.eye(m-2)
            q=solve_qp(S,d,A,np.zeros(m-2),equality=G.T,equality_rhs=load)
            self.assertTrue(r['passed'],r);self.assertTrue(q['passed'],q);np.testing.assert_allclose(r['forces'],q['u'],atol=2e-7)
    def test_constructed_kkt_50_systems(self):
        rng=np.random.default_rng(802)
        for _ in range(50):
            m=10;X=rng.normal(size=(m,m));S=X.T@X+np.eye(m)*.3;G=rng.normal(size=(m,3))
            l=np.r_[rng.normal(size=2),rng.uniform(.1,1,4),np.zeros(4)];r0=rng.normal(size=3);left=np.r_[np.zeros(6),rng.uniform(.1,1,4)];d=S@l-G@r0-left
            r=solve_force_qp(S,d,G,G.T@l,free_prefix=2)
            self.assertTrue(r['passed'],r);np.testing.assert_allclose(r['forces'],l,atol=5e-7)
    def test_scaling_invariance(self):
        for scale in [1e-7,1.,1e7]:
            r=solve_force_qp(np.eye(2)*scale,np.array([1.,2.])*scale,[[1.],[1.]],[1.],free_prefix=0)
            self.assertTrue(r['passed'],r);np.testing.assert_allclose(r['forces'],[0.,1.],atol=1e-8)
    def test_warmstart_zero_extension(self):
        r=solve_force_qp(np.eye(3),[0.,1.,2.],[[1.],[1.],[1.]],[1.],free_prefix=0,initial=[0.,1.,0.])
        self.assertTrue(r['passed'],r);np.testing.assert_allclose(r['forces'],[0.,0.,1.],atol=1e-8)
    def test_iteration_limit_does_not_pass(self):
        r=solve_force_qp(np.eye(2),[1.,2.],[[1.],[1.]],[1.],free_prefix=0,initial=[1.,0.],max_iterations=1)
        self.assertFalse(r['passed'])
    def test_nonfinite_refused(self):
        with self.assertRaises(ValueError):solve_force_qp([[np.nan]],[1.],[[1.]],[1.],free_prefix=0)
    def test_boolean_refused(self):
        with self.assertRaises(ValueError):solve_force_qp([[True]],[1.],[[1.]],[1.],free_prefix=0)
    def test_negative_energy_refused(self):
        with self.assertRaises(ValueError):solve_force_qp([[1.,2.],[2.,1.]],[1.,1.],[[1.],[1.]],[1.],free_prefix=0)
    def test_nonreciprocal_refused(self):
        with self.assertRaises(ValueError):solve_force_qp([[1.,.2],[0.,1.]],[1.,1.],[[1.],[1.]],[1.],free_prefix=0)
    def test_no_input_mutation(self):
        S=np.eye(2);d=np.ones(2);G=np.ones((2,1));l=np.ones(1);old=[x.copy() for x in [S,d,G,l]];solve_force_qp(S,d,G,l,free_prefix=0)
        for a,b in zip([S,d,G,l],old):np.testing.assert_array_equal(a,b)
    def test_finite_json_no_hardware_go(self):
        r=solve_force_qp([[1.]],[1.],np.zeros((1,0)),[],free_prefix=0);json.dumps(r,allow_nan=False)
        for k in ['candidate_go','fixture_fabrication_go','manufacturing_go','regularization_added']:self.assertFalse(r[k])
