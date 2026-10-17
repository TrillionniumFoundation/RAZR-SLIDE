from pathlib import Path
import sys, unittest
import numpy as np
from scipy.sparse import csc_matrix
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
from contact_exchange import ExactResponseCache

class BlockResponseTests(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(927)
        A=rng.normal(size=(9,9));self.K=A.T@A+np.eye(9)
        self.C=csc_matrix(rng.normal(size=(9,7)))
        self.response=lambda v:np.linalg.solve(self.K,v)
        self.identity={'K':'known SPD calibration, not phone'}

    def cache(self,block=None,size=4):
        return ExactResponseCache(9,self.response,self.identity,response_block=block,response_batch_size=size)

    def test_default_vector_path_unchanged(self):
        c=self.cache();c.append(self.C);self.assertEqual(c.calls,7)
        np.testing.assert_allclose(c.H,self.C.T@self.response(self.C.toarray()),atol=1e-12)

    def test_callback_chunk_counts_and_full_columns(self):
        calls=[]
        def b(v):calls.append(v.shape);return self.response(v)
        c=self.cache(b);c.append(self.C)
        self.assertEqual(calls,[(9,4),(9,3)]);self.assertEqual(c.calls,7)

    def test_block_and_scalar_full_response_identical(self):
        a=self.cache();b=self.cache(self.response)
        a.append(self.C);b.append(self.C)
        np.testing.assert_allclose(a.H,b.H,rtol=1e-12,atol=1e-12)

    def test_append_old_new_cross_responses(self):
        c=self.cache(self.response);c.append(self.C[:,:2]);c.append(self.C[:,2:])
        np.testing.assert_allclose(c.H,self.C.T@self.response(self.C.toarray()),atol=1e-12)

    def test_restored_old_columns_do_not_need_per_column_solves(self):
        a=self.cache();a.append(self.C[:,:4]);c=self.cache(self.response)
        c.restore(self.C[:,:4],a.H,c.identity,probes=2);self.assertEqual(c.calls,2)
        c.append(self.C[:,4:]);self.assertEqual(c.calls,5)
        np.testing.assert_allclose(c.H,self.C.T@self.response(self.C.toarray()),atol=1e-12)

    def test_reconstruct_uses_full_vector_operator(self):
        c=self.cache(self.response);c.append(self.C)
        f=np.arange(9.)/9;lam=np.arange(7.)/7;u,rhs=c.reconstruct(f,lam)
        np.testing.assert_allclose(u,self.response(f-self.C@lam),atol=1e-12)
        np.testing.assert_allclose(rhs,f-self.C@lam)

    def test_callback_mutation_does_not_change_sparse_inputs(self):
        old=self.C.copy()
        def b(v):u=self.response(v);v[:]=0.;return u
        c=self.cache(b);c.append(self.C)
        np.testing.assert_array_equal(self.C.toarray(),old.toarray())
        np.testing.assert_allclose(c.H,old.T@self.response(old.toarray()),atol=1e-12)

    def test_bad_block_shape_is_refused(self):
        c=self.cache(lambda v:np.zeros((8,v.shape[1])))
        with self.assertRaises(ValueError):c.append(self.C)
        self.assertEqual(c.H.shape,(0,0))

    def test_nonfinite_block_is_refused(self):
        c=self.cache(lambda v:np.full(v.shape,np.nan))
        with self.assertRaises(ValueError):c.append(self.C)
        self.assertEqual(c.C.shape[1],0)

    def test_nonreciprocal_response_is_refused(self):
        A=np.eye(9);A[0,1]=10.
        c=self.cache(lambda v:A@v)
        with self.assertRaises(ValueError):c.append(csc_matrix(np.eye(9)))
        self.assertEqual(c.C.shape[1],0)

    def test_late_callback_failure_does_not_publish_partial_append(self):
        count=[0]
        def b(v):
            count[0]+=1
            if count[0]==2:raise RuntimeError('injected response failure')
            return self.response(v)
        c=self.cache(b)
        with self.assertRaises(RuntimeError):c.append(self.C)
        self.assertEqual(c.C.shape[1],0);self.assertEqual(c.H.shape,(0,0));self.assertFalse(c._busy)

    def test_invalid_batch_sizes_rejected(self):
        for n in (True,0,-1,65,2.5):
            with self.assertRaises(ValueError):self.cache(self.response,n)

    def test_noncallable_block_rejected(self):
        with self.assertRaises(ValueError):self.cache(5)

    def test_recursive_response_rejected(self):
        box={}
        def b(v):return box['cache']._response(v[:,0])[:,None]
        c=self.cache(b);box['cache']=c
        with self.assertRaises(RuntimeError):c.append(self.C)
        self.assertFalse(c._busy)

    def test_single_rhs_block_preserves_two_dimensions(self):
        calls=[]
        def b(v):calls.append(v.shape);return self.response(v)
        c=self.cache(b,1);c.append(self.C[:,:1])
        self.assertEqual(calls,[(9,1)]);self.assertEqual(c.H.shape,(1,1))

    def test_partial_previous_state_is_immutable_on_late_failure(self):
        c=self.cache();c.append(self.C[:,:2]);old=c.H.copy();maps=c.C.copy()
        c.response_block=lambda v:np.full(v.shape,np.inf)
        with self.assertRaises(ValueError):c.append(self.C[:,2:])
        np.testing.assert_array_equal(c.H,old);np.testing.assert_array_equal(c.C.toarray(),maps.toarray())
