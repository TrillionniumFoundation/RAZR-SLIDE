from pathlib import Path
import sys,unittest
import numpy as np
from scipy.linalg import solve
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
from contact_dual_active import solve_force_qp,_WorkingFactor

class ContactFactorReuseTests(unittest.TestCase):
    def test_append_delete_preserve_factor_and_transformed_rhs(self):
        rng=np.random.default_rng(8201);a=rng.normal(size=(24,24));Q=a.T@a+np.eye(24);p=rng.normal(size=24);E=rng.normal(size=(3,24));w=_WorkingFactor()
        seq=[[0,2,5,8,12],[0,2,5,8,12,6],[0,5,8,12,6],[5,8,12,6],[5,8,12,6,21],[5,8,12,6,21,7],[5,8,12,6,21],[5,8,6,21]]
        for ids in seq:
            w._factor(Q,np.array(ids),p,E)
            np.testing.assert_allclose(w.L@w.L.T,Q[np.ix_(ids,ids)],rtol=1e-11,atol=1e-11)
            np.testing.assert_allclose(w.L@w.T,np.column_stack([p[ids],E[:,ids].T]),rtol=1e-11,atol=1e-11)
        self.assertGreater(w.counts['append'],0);self.assertGreater(w.counts['delete'],0)

    def test_empty_working_set_then_first_contact(self):
        q=solve_force_qp([[2.]],[3.],np.zeros((1,0)),[],free_prefix=0,factor_reuse=True)
        self.assertTrue(q['passed']);self.assertAlmostEqual(q['forces'][0],1.5)

    def test_duplicate_semidefinite_active_contacts_fall_back_without_regularizing(self):
        q=solve_force_qp(np.ones((2,2)),[1.,1.],np.zeros((2,0)),[],free_prefix=0,initial=[.5,.5],factor_reuse=True)
        self.assertTrue(q['passed']);self.assertAlmostEqual(sum(q['forces']),1.)
        self.assertGreater(q['factor_reuse_counts']['fallback'],0);self.assertFalse(q['regularization_added'])

    def test_corrupt_cache_fails_residual_and_uses_original_pivoted_solve(self):
        Q=np.diag([1.,2.,3.]);p=np.array([1.,2.,3.]);E=np.ones((1,3));b=np.array([2.]);ids=np.arange(3)
        A=np.block([[Q,-E.T],[E,np.zeros((1,1))]]);rhs=np.r_[p,b];w=_WorkingFactor()
        expected=solve(A,rhs);np.testing.assert_allclose(w.solve(Q,ids,E,p,b,2e-10,A,rhs),expected,atol=1e-12)
        w.L[0,0]*=1.4
        np.testing.assert_allclose(w.solve(Q,ids,E,p,b,2e-10,A,rhs),expected,atol=1e-12)
        self.assertEqual(w.counts['fallback'],1)

    def test_known_kkt_systems_match_original_solver(self):
        rng=np.random.default_rng(76182)
        for trial in range(40):
            n=5+trial%11;a=rng.normal(size=(n,n));S=a.T@a+np.eye(n)*(.2 if trial%2 else 1.);G=np.column_stack([rng.normal(size=n),np.zeros(n)])
            lam=rng.uniform(.1,1.,n);lam[:2]=rng.normal(size=2);lam[2:][rng.random(n-2)<.45]=0.
            grad=np.zeros(n);grad[2:]=np.where(lam[2:]==0,rng.uniform(.1,1.,n-2),0.)
            rigid=np.array([.2,0.]);d=S@lam-G@rigid-grad;load=G.T@lam
            old=solve_force_qp(S,d,G,load,free_prefix=2);new=solve_force_qp(S,d,G,load,free_prefix=2,factor_reuse=True)
            self.assertTrue(old['passed'] and new['passed'],(trial,old['status'],new['status']))
            np.testing.assert_allclose(new['forces'],old['forces'],rtol=1e-8,atol=1e-8)
            np.testing.assert_allclose(new['forces'],lam,rtol=1e-8,atol=1e-8)

    def test_known_scaled_energy_problem(self):
        for magnitude in (1e-8,1.,1e5):
            S=np.diag([1.,1e-3,4.]);d=np.array([2.,.001,-1.])*magnitude;G=np.zeros((3,0))
            a=solve_force_qp(S,d,G,[],free_prefix=0);b=solve_force_qp(S,d,G,[],free_prefix=0,factor_reuse=True)
            self.assertTrue(a['passed'] and b['passed']);np.testing.assert_allclose(a['forces'],b['forces'],rtol=1e-8,atol=1e-10*magnitude)

    def test_reuse_option_must_be_boolean(self):
        for flag in (1,'yes',None,[],0.):
            with self.assertRaises(ValueError):solve_force_qp([[1.]],[1.],np.zeros((1,0)),[],free_prefix=0,factor_reuse=flag)

    def test_inputs_and_physical_matrix_are_not_modified(self):
        S=np.diag([1.,2.,3.]);d=np.array([1.,2.,3.]);G=np.ones((3,1));b=np.array([2.]);copies=[x.copy() for x in (S,d,G,b)]
        q=solve_force_qp(S,d,G,b,free_prefix=1,factor_reuse=True);self.assertTrue(q['passed']);self.assertFalse(q['regularization_added'])
        for actual,expected in zip((S,d,G,b),copies):np.testing.assert_array_equal(actual,expected)

    def test_unsupported_rigid_load_still_rejected(self):
        for reuse in (False,True):
            r=solve_force_qp(np.eye(2),np.ones(2),np.zeros((2,1)),[1.],free_prefix=0,factor_reuse=reuse)
            self.assertFalse(r['passed']);self.assertEqual(r['status'],'unsupported_rigid_load')

    def test_iteration_limit_still_rejected(self):
        r=solve_force_qp(np.eye(6),np.ones(6),np.zeros((6,0)),[],free_prefix=0,max_iterations=1,factor_reuse=True)
        self.assertFalse(r['passed']);self.assertIn('iteration_limit',r['status'])
