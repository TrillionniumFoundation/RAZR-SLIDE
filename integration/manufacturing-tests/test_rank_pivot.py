from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rank_fallback import release_dependent_force
from contact_dual_active import solve_force_qp

def pivot(Q,p,x,E=None,b=None,free=0):
    n=len(x);E=np.zeros((0,n)) if E is None else np.asarray(E,dtype=float);b=np.zeros(len(E)) if b is None else np.asarray(b,dtype=float)
    A=np.block([[Q,-E.T],[E,np.zeros((len(E),len(E)))]])
    return release_dependent_force(A,Q,E,p,b,x,np.arange(n),free_prefix=free,tolerance=2e-10)

class RankPivotTests(unittest.TestCase):
    def test_exact_dependent_contact_reaches_zero(self):
        r=pivot(np.ones((2,2)),np.ones(2),np.array([.3,.7]));self.assertTrue(r['accepted']);self.assertEqual(r['scaled_forces'][r['release']],0.)
        self.assertAlmostEqual(sum(r['scaled_forces']),1.);self.assertFalse(r['constraints_removed'])
    def test_free_prefix_is_never_released(self):
        r=pivot(np.ones((2,2)),np.ones(2),np.array([.3,.7]),free=1)
        self.assertTrue(r['accepted']);self.assertEqual(r['release'],1);np.testing.assert_allclose(r['scaled_forces'],[1.,0.],atol=1e-12)
    def test_no_null_direction_does_not_change_state(self):
        r=pivot(np.eye(2),np.ones(2),np.ones(2));self.assertFalse(r['accepted'])
    def test_infeasible_initial_state_rejected(self):
        r=pivot(np.ones((2,2)),np.ones(2),np.array([.3,.7]),E=[[1.,1.]],b=[2.]);self.assertFalse(r['accepted']);self.assertEqual(r['reason'],'initial_not_feasible')
    def test_linear_descent_along_null_direction(self):
        r=pivot(np.ones((2,2)),np.array([2.,1.]),np.array([.3,.7]));self.assertTrue(r['accepted']);np.testing.assert_allclose(r['scaled_forces'],[1.,0.],atol=1e-12);self.assertLess(r['objective_change'],0.)
    def test_full_qp_with_inconsistent_active_stationarity(self):
        r=solve_force_qp(np.ones((2,2)),[2.,1.],np.zeros((2,0)),[],free_prefix=0,initial=[.3,.7],factor_reuse=True,rank_fallback='qr_pivot')
        self.assertTrue(r['passed'],r);np.testing.assert_allclose(r['forces'],[2.,0.],atol=1e-10);self.assertTrue(any('rank_release' in z for z in r['history']))
    def test_equality_and_nonnegative_reactions_preserved(self):
        r=pivot(np.ones((3,3)),np.full(3,3.),np.ones(3),E=[[1.,-1.,0.]],b=[0.]);self.assertTrue(r['accepted']);np.testing.assert_allclose(np.array([[1.,-1.,0.]])@r['scaled_forces'],[0.],atol=1e-12);self.assertGreaterEqual(r['scaled_forces'].min(),-1e-12)
    def test_input_arrays_unchanged(self):
        Q=np.ones((2,2));p=np.ones(2);x=np.array([.3,.7]);old=[a.copy() for a in [Q,p,x]];pivot(Q,p,x)
        for a,b in zip([Q,p,x],old):np.testing.assert_array_equal(a,b)
    def test_fifty_rank_deficient_energy_and_resultant_problems(self):
        rng=np.random.default_rng(18111)
        for i in range(50):
            C=rng.normal(size=(6,10));S=C.T@C;G=C.T@rng.normal(size=(6,2));lam=rng.uniform(.1,1.,10);rigid=rng.normal(size=2);d=S@lam-G@rigid
            r=solve_force_qp(S,d,G,G.T@lam,free_prefix=2,initial=lam,factor_reuse=True,rank_fallback='qr_pivot')
            self.assertTrue(r['passed'],r);np.testing.assert_allclose(C@r['forces'],C@lam,rtol=1e-7,atol=1e-8);self.assertFalse(r['regularization_added'])
    def test_permuted_duplicate_problem_keeps_physical_solution(self):
        for order in [[0,1,2],[2,0,1],[1,2,0]]:
            d=np.array([1.,2.,1.5])[order]
            r=solve_force_qp(np.ones((3,3)),d,np.zeros((3,0)),[],free_prefix=0,initial=[.3,.4,.3],factor_reuse=True,rank_fallback='qr_pivot')
            self.assertTrue(r['passed'],r);self.assertAlmostEqual(sum(r['forces']),2.);self.assertAlmostEqual(r['forces'][list(order).index(1)],2.)
