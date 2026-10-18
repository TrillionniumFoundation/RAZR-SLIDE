from pathlib import Path
import sys,unittest,json
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rank_fallback import solve_rank_fallback
from contact_dual_active import solve_force_qp

class RankFallbackTests(unittest.TestCase):
    def test_full_rank_solution(self):
        A=np.array([[2.,1.],[1.,3.]]);b=np.array([1.,2.]);x,r=solve_rank_fallback(A,b,residual_limit=1e-10)
        np.testing.assert_allclose(x,np.linalg.solve(A,b),atol=1e-12);self.assertEqual(r['rank'],2);self.assertEqual(r['driver'],'gelsy')
    def test_singular_minimum_norm(self):
        A=np.array([[1.,1.],[2.,2.]]);b=np.array([1.,2.]);x,r=solve_rank_fallback(A,b,residual_limit=1e-10)
        np.testing.assert_allclose(x,[.5,.5],atol=1e-12);self.assertEqual(r['rank'],1)
    def test_rectangular_minimum_norm(self):
        x,r=solve_rank_fallback([[1.,1.,0.],[0.,0.,1.]],[2.,3.],residual_limit=1e-10)
        np.testing.assert_allclose(x,[1.,1.,3.],atol=1e-12)
    def test_inconsistent_equations_not_passed(self):
        x,r=solve_rank_fallback([[1.,1.],[1.,1.]],[1.,2.],residual_limit=1e-10)
        self.assertFalse(r['residual_passed']);self.assertEqual(r['driver'],'numpy_gelsd');self.assertGreater(r['residual_max'],.49)
    def test_zero_matrix_keeps_failure(self):
        x,r=solve_rank_fallback(np.zeros((2,2)),[1.,0.],residual_limit=1e-10)
        self.assertFalse(r['residual_passed']);np.testing.assert_array_equal(x,[0.,0.])
    def test_qr_exception_restores_original_svd(self):
        with patch('rank_fallback.scipy_lstsq',side_effect=np.linalg.LinAlgError('probe')):
            x,r=solve_rank_fallback(np.eye(2),[1.,2.],residual_limit=1e-10)
        self.assertEqual(r['driver'],'numpy_gelsd');self.assertTrue(r['residual_passed'])
    def test_qr_nonfinite_rejected(self):
        with patch('rank_fallback.scipy_lstsq',return_value=(np.array([np.nan,0.]),None,2,None)):
            x,r=solve_rank_fallback(np.eye(2),[1.,2.],residual_limit=1e-10)
        self.assertEqual(r['driver'],'numpy_gelsd');np.testing.assert_allclose(x,[1.,2.])
    def test_qr_bad_residual_does_not_override_svd(self):
        with patch('rank_fallback.scipy_lstsq',return_value=(np.zeros(2),None,2,None)):
            x,r=solve_rank_fallback(np.eye(2),[1.,2.],residual_limit=1e-10)
        self.assertEqual(r['driver'],'numpy_gelsd');self.assertTrue(r['residual_passed'])
    def test_no_input_mutation(self):
        A=np.array([[1.,1.],[2.,2.]]);b=np.array([1.,2.]);a0=A.copy();b0=b.copy()
        solve_rank_fallback(A,b,residual_limit=1e-10);np.testing.assert_array_equal(A,a0);np.testing.assert_array_equal(b,b0)
    def test_invalid_data_rejected(self):
        for A,b in [([[True]],[1.]),([[np.nan]],[1.]),([[1.]],[np.inf]),([['x']],[1.])]:
            with self.assertRaises(ValueError):solve_rank_fallback(A,b,residual_limit=1e-10)
    def test_invalid_dimensions_rejected(self):
        for A,b in [(np.zeros((0,2)),[]),(np.ones(2),[1.]),(np.eye(2),[1.]),(np.eye(2),np.ones((2,1)))]:
            with self.assertRaises(ValueError):solve_rank_fallback(A,b,residual_limit=1e-10)
    def test_invalid_numeric_controls_rejected(self):
        for key in ['residual_limit','cutoff']:
            for v in [True,0.,-1.,float('nan'),float('inf'),'x']:
                args={'residual_limit':1e-10,'cutoff':1e-13};args[key]=v
                with self.assertRaises(ValueError):solve_rank_fallback([[1.]],[1.],**args)
    def test_scale_consistent(self):
        for s in [1e-6,1.,1e6]:
            x,r=solve_rank_fallback(np.array([[1.,1.],[2.,2.]])*s,np.array([1.,2.])*s,residual_limit=1e-9*s)
            np.testing.assert_allclose(x,[.5,.5],atol=1e-10);self.assertTrue(r['residual_passed'])
    def test_known_nullspace_fifty_systems(self):
        rng=np.random.default_rng(18108)
        for i in range(50):
            U=np.linalg.qr(rng.normal(size=(12,12)))[0];V=np.linalg.qr(rng.normal(size=(10,10)))[0];rank=3+i%6
            A=(U[:,:rank]*np.linspace(1.,3.,rank))@V[:,:rank].T;x0=V[:,:rank]@rng.normal(size=rank);b=A@x0
            x,r=solve_rank_fallback(A,b,residual_limit=1e-10)
            np.testing.assert_allclose(x,x0,atol=1e-10);self.assertEqual(r['rank'],rank)
    def test_dependent_contact_qp_minimum_energy(self):
        r=solve_force_qp(np.ones((2,2)),[1.,1.],np.zeros((2,0)),[],free_prefix=0,initial=[.3,.7],factor_reuse=True,rank_fallback='qr')
        self.assertTrue(r['passed'],r);self.assertTrue(r['rank_fallback_records']);np.testing.assert_allclose(r['forces'],[.5,.5],atol=1e-10)
    def test_rank_deficient_qp_physical_result_twentyfive(self):
        rng=np.random.default_rng(18109)
        for _ in range(25):
            C=rng.normal(size=(6,10));S=C.T@C;G=C.T@rng.normal(size=(6,2));lam=rng.uniform(.2,1.,size=10);rigid=rng.normal(size=2);d=S@lam-G@rigid
            base=solve_force_qp(S,d,G,G.T@lam,free_prefix=2,initial=lam,factor_reuse=True)
            new=solve_force_qp(S,d,G,G.T@lam,free_prefix=2,initial=lam,factor_reuse=True,rank_fallback='qr')
            self.assertTrue(base['passed'],base);self.assertTrue(new['passed'],new)
            np.testing.assert_allclose(C@new['forces'],C@base['forces'],rtol=1e-7,atol=1e-8)
            self.assertFalse(new['regularization_added'])
    def test_default_dictionary_unchanged(self):
        args=(np.eye(3),[1.,2.,3.],np.zeros((3,0)),[])
        self.assertEqual(solve_force_qp(*args,free_prefix=0),solve_force_qp(*args,free_prefix=0,rank_fallback='svd'))
    def test_unsupported_load_still_rejected(self):
        r=solve_force_qp(np.eye(2),[0.,0.],[[1.,0.],[1.,0.]],[0.,1.],free_prefix=0,rank_fallback='qr')
        self.assertFalse(r['passed']);self.assertEqual(r['status'],'unsupported_rigid_load')
    def test_option_validation(self):
        for mode in [None,True,'fast',5]:
            with self.assertRaises(ValueError):solve_force_qp([[1.]],[1.],np.zeros((1,0)),[],free_prefix=0,rank_fallback=mode)
    def test_iteration_failure_and_false_hardware_flags(self):
        r=solve_force_qp(np.eye(2),[1.,2.],[[1.],[1.]],[1.],free_prefix=0,initial=[1.,0.],max_iterations=1,rank_fallback='qr')
        self.assertFalse(r['passed']);json.dumps(r,allow_nan=False)
        for key in ['candidate_go','fixture_fabrication_go','manufacturing_go']:self.assertFalse(r[key])
