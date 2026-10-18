from pathlib import Path
import sys, unittest, warnings
import numpy as np
from scipy.linalg import LinAlgWarning
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contact_dual_active import _WorkingFactor, solve_force_qp

class ActiveEqualitySchurTests(unittest.TestCase):
    def direct(self,Q,E,p,b,F,allow=True):
        F=np.array(F,dtype=int);EF=E[:,F]
        A=np.block([[Q[np.ix_(F,F)],-EF.T],[EF,np.zeros((len(b),len(b)))]])
        rhs=np.r_[p[F],b];obj=_WorkingFactor(allow)
        with warnings.catch_warnings():
            warnings.simplefilter('error',LinAlgWarning)
            sol=obj.solve(Q,F,E,p,b,2e-10,A,rhs)
        np.testing.assert_allclose(A@sol,rhs,rtol=0,atol=2e-9)
        return sol,obj
    def test_global_independent_but_active_redundant_equalities(self):
        S=np.eye(3);d=np.array([1.,-2.,-2.]);G=np.array([[1.,0.],[0.,1.],[0.,-1.]])
        x=solve_force_qp(S,d,G,np.array([1.,0.]),free_prefix=0,initial=np.array([1.,0.,0.]),factor_reuse=True,rank_fallback='qr_pivot')
        self.assertTrue(x['passed']);np.testing.assert_allclose(x['forces'],[1.,0.,0.],atol=1e-12)
        self.assertGreater(x['factor_reuse_counts'].get('rank_schur',0),0)
    def test_rank_three_out_of_five_keeps_complete_equalities(self):
        E=np.vstack([np.eye(3),np.zeros((2,3))]);p=np.array([2.,3.,4.]);b=np.r_[p,np.zeros(2)]
        sol,obj=self.direct(np.eye(3),E,p,b,[0,1,2]);np.testing.assert_allclose(sol[:3],p,atol=1e-12)
        self.assertEqual(obj.counts['rank_schur'],1)
    def test_inconsistent_active_rhs_not_accepted(self):
        with self.assertRaises((np.linalg.LinAlgError,LinAlgWarning)):
            self.direct(np.eye(1),np.array([[1.],[0.]]),np.array([1.]),np.array([1.,1.]),[0])
    def test_default_path_does_not_enable_singular_schur(self):
        self.assertFalse(_WorkingFactor().allow_singular_equalities)
        with self.assertRaises((np.linalg.LinAlgError,LinAlgWarning)):
            self.direct(np.eye(1),np.array([[1.],[0.]]),np.array([1.]),np.array([1.,0.]),[0],False)
    def test_full_rank_linear_solution_unchanged(self):
        rng=np.random.default_rng(119)
        for n in [4,8,12]:
            A=rng.normal(size=(n,n));Q=A.T@A+np.eye(n);E=rng.normal(size=(2,n));p=rng.normal(size=n);b=rng.normal(size=2)
            a,oa=self.direct(Q,E,p,b,range(n),True);r,ob=self.direct(Q,E,p,b,range(n),False)
            np.testing.assert_array_equal(a,r);self.assertEqual(oa.counts,ob.counts)
    def test_no_equalities_unchanged(self):
        sol,obj=self.direct(np.eye(2),np.zeros((0,2)),np.array([1.,2.]),np.array([]),[1,0]);np.testing.assert_allclose(sol,[2.,1.]);self.assertNotIn('rank_schur',obj.counts)
    def test_positive_energy_is_not_regularized_for_force_dependence(self):
        # Singular force block is not cured by a dual-only reduction.
        with self.assertRaises((np.linalg.LinAlgError,LinAlgWarning)):
            self.direct(np.ones((2,2)),np.zeros((0,2)),np.ones(2),np.array([]),[0,1])
    def test_option_requires_exact_boolean(self):
        for value in [1,0,'yes',None]:
            with self.assertRaises(ValueError):_WorkingFactor(value)
