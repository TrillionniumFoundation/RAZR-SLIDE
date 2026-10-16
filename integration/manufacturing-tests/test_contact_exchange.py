from pathlib import Path
import sys, unittest
import numpy as np
from scipy.sparse import csc_matrix
from scipy.linalg import cho_factor, cho_solve
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
from contact_exchange import ExactResponseCache,QuadraticGapBatch,select_violations
from contact_patch_audit import extrema


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.rng=np.random.default_rng(456)
        A=self.rng.normal(size=(21,21));self.K=A.T@A+np.diag(np.arange(1,22))
        self.factor=cho_factor(self.K);self.response=lambda f:cho_solve(self.factor,f)
        self.C=self.rng.normal(size=(21,8));self.C[abs(self.C)<.6]=0
        self.identity={'K_sha256':'synthetic-identity','boundary':'none','mesh':'synthetic'}
    def cache(self):return ExactResponseCache(21,self.response,self.identity)
    def test_incremental_response_matches_full_matrix(self):
        c=self.cache();c.append(csc_matrix(self.C[:,:3]));c.append(csc_matrix(self.C[:,3:]))
        np.testing.assert_allclose(c.H,self.C.T@self.response(self.C),rtol=1e-13,atol=1e-14)
        self.assertEqual(c.calls,8)
    def test_restore_does_not_recompute_every_point(self):
        c=self.cache();H=self.C.T@self.response(self.C)
        q=c.restore(csc_matrix(self.C),H,self.identity,probes=3)
        self.assertEqual(c.calls,3);self.assertEqual(q.probes,3)
        np.testing.assert_allclose(c.H,H,atol=1e-14)
    def test_resume_extension_preserves_old_entries(self):
        c=self.cache();H=self.C[:,:4].T@self.response(self.C[:,:4]);c.restore(csc_matrix(self.C[:,:4]),H,self.identity,probes=2)
        old=c.H.copy();c.append(csc_matrix(self.C[:,4:]))
        np.testing.assert_array_equal(c.H[:4,:4],old)
        np.testing.assert_allclose(c.H,self.C.T@self.response(self.C),rtol=1e-13,atol=1e-14)
        self.assertEqual(c.calls,6)
    def test_one_combined_solve_reproduces_dense_superposition(self):
        c=self.cache();c.append(csc_matrix(self.C));f=self.rng.normal(size=21);lam=self.rng.normal(size=8)
        before=c.calls;u,rhs=c.reconstruct(f,lam)
        np.testing.assert_allclose(u,self.response(f)-self.response(self.C)@lam,rtol=1e-13,atol=1e-14)
        np.testing.assert_allclose(self.K@u,rhs,rtol=1e-13,atol=1e-14)
        self.assertEqual(c.calls-before,1)
    def test_rigid_field_is_separate_not_fixed(self):
        c=self.cache();c.append(csc_matrix(self.C));f=np.zeros(21);lam=np.ones(8);r=np.arange(21.)
        u,_=c.reconstruct(f,lam,rigid_displacement=r)
        np.testing.assert_allclose(u,self.response(-self.C@lam)+r,atol=1e-14)
    def test_independent_different_body_stiffness(self):
        from scipy.linalg import block_diag
        K=block_diag(self.K,self.K*19);C=np.vstack([self.C,-self.C]);f=np.r_[np.ones(21),np.zeros(21)]
        fac=cho_factor(K);solve=lambda f:cho_solve(fac,f)
        c=ExactResponseCache(42,solve,{'K':'two independently specified bodies'});c.append(csc_matrix(C))
        u,rhs=c.reconstruct(f,np.arange(8.)/10)
        np.testing.assert_allclose(K@u,rhs,rtol=1e-12,atol=1e-13)
        np.testing.assert_allclose(c.H,C.T@solve(C),rtol=1e-13,atol=1e-14)
    def test_negative_shape_weights_are_not_discarded(self):
        C=np.zeros((21,1));C[:3,0]=[-.125,.75,.375]
        c=self.cache();c.append(csc_matrix(C));np.testing.assert_array_equal(c.C.toarray(),C)
    def test_empty_append_is_no_op(self):
        c=self.cache();c.append(csc_matrix((21,0)));self.assertEqual(c.calls,0)
    def test_wrong_identity_rejected_before_response(self):
        c=self.cache()
        with self.assertRaises(ValueError):c.restore(csc_matrix(self.C),np.eye(8),{'K':'wrong'})
        self.assertEqual(c.calls,0)
    def test_changed_checkpoint_detected_by_full_operator(self):
        c=self.cache();H=self.C.T@self.response(self.C);H[0,0]+=.1
        with self.assertRaises(ValueError):c.restore(csc_matrix(self.C),H,self.identity)
        self.assertEqual(c.C.shape[1],0)
    def test_changed_force_map_rejected(self):
        c=self.cache();H=self.C.T@self.response(self.C);C=self.C.copy();C[:,0]*=2
        with self.assertRaises(ValueError):c.restore(csc_matrix(C),H,self.identity)
    def test_no_restore_into_occupied_cache(self):
        c=self.cache();c.append(csc_matrix(self.C))
        with self.assertRaises(ValueError):c.restore(csc_matrix(self.C),c.H,self.identity)
    def test_nonreciprocal_new_block_rejected_atomically(self):
        c=ExactResponseCache(21,lambda f:np.roll(f,1),self.identity)
        with self.assertRaises(ValueError):c.append(csc_matrix(self.C))
        self.assertEqual(c.H.shape,(0,0))
    def test_wrong_response_dimension_refused(self):
        c=ExactResponseCache(21,lambda f:f[:3],self.identity)
        with self.assertRaises(ValueError):c.append(csc_matrix(self.C))
    def test_nonfinite_and_boolean_maps_refused(self):
        for C in (np.full((21,2),np.nan),np.ones((21,2),dtype=bool)):
            with self.assertRaises(ValueError):self.cache().append(csc_matrix(C))
    def test_inconsistent_field_dimensions_refused(self):
        c=self.cache();c.append(csc_matrix(self.C))
        with self.assertRaises(ValueError):c.reconstruct(np.zeros(22),np.zeros(8))
        with self.assertRaises(ValueError):c.reconstruct(np.zeros(21),np.zeros(7))
    def test_storage_does_not_retain_N_by_m_responses(self):
        c=self.cache();c.append(csc_matrix(self.C))
        self.assertNotIn('U',vars(c));self.assertEqual(set(vars(c)),{'identity','size','response','C','H','calls','_busy'})
        self.assertGreater(c.storage_bytes(),c.H.nbytes)
    def test_random_energies_and_restore_orders(self):
        for n,m in ((8,4),(31,17),(61,40)):
            A=self.rng.normal(size=(n,n));K=A.T@A+np.eye(n);C=self.rng.normal(size=(n,m));fac=cho_factor(K)
            solve=lambda f:cho_solve(fac,f);H=C.T@solve(C)
            c=ExactResponseCache(n,solve,{'fixture':str(n)})
            c.restore(csc_matrix(C[:,:2]),H[:2,:2],{'fixture':str(n)},probes=2)
            for start in range(2,m,7):c.append(csc_matrix(C[:,start:start+7]))
            np.testing.assert_allclose(c.H,H,rtol=5e-12,atol=5e-13)
    def test_zero_and_negative_constructor_arguments(self):
        for n in (0,-1,True):
            with self.assertRaises(ValueError):ExactResponseCache(n,self.response,self.identity)
        with self.assertRaises(ValueError):ExactResponseCache(21,self.response,{})
    def test_invalid_restore_controls_refused(self):
        H=self.C.T@self.response(self.C)
        for p in (0,True,65):
            with self.assertRaises(ValueError):self.cache().restore(csc_matrix(self.C),H,self.identity,probes=p)
        with self.assertRaises(ValueError):self.cache().restore(csc_matrix(self.C),H,self.identity,relative_tolerance=.1)


class BatchTests(unittest.TestCase):
    def compare(self,poly,c,origins):
        b=QuadraticGapBatch(poly,origins).extrema(c)
        for i,p in enumerate(poly):
            s=extrema(c[i],p,origins[i])
            self.assertAlmostEqual(b['minimum'][i],s['minimum'],places=10)
            self.assertAlmostEqual(b['maximum'][i],s['maximum'],places=10)
            self.assertEqual(b['candidate_count'][i],s['candidate_count'])
        return b
    def test_hidden_interior_minimum_not_lost(self):
        p=[[[0,0],[1,0],[1,1],[0,1]]];c=np.array([[.45,-1,-1,1,0,1.]])
        b=self.compare(p,c,[[0,0]])
        self.assertAlmostEqual(b['minimum'][0],-.05)
        np.testing.assert_allclose(b['minimum_at'][0],[.5,.5])
    def test_edge_minimum_not_lost(self):
        self.compare([[[0,0],[1,0],[0,1]]],np.array([[.16,-.8,2,1,0,0]]),[[0,0]])
    def test_mixed_polygon_sizes_clockwise_and_closure(self):
        p=[[[0,0],[0,1],[1,0]],[[0,0],[2,0],[2,1],[0,1],[0,0]]]
        self.compare(p,np.array([[0,1,2,-1,.2,2],[1,-.2,1,2,0,0]]),[[0,0],[1,2]])
    def test_singular_hessians_preserve_edge_answer(self):
        p=[[[0,0],[1,0],[1,1],[0,1]]]*3
        self.compare(p,np.array([[0,-1,0,1,0,0],[0,1,1,0,0,0],[1,0,0,0,0,0]]),np.zeros((3,2)))
    def test_origin_shift(self):
        p=np.array([[0,0],[1,0],[1,1],[0,1]])+np.array([1000,-2200]);c=np.array([[.45,-1,-1,1,0,1.]])
        self.compare([p],c,[[1000,-2200]])
    def test_random_polynomials_and_convex_polygons(self):
        rng=np.random.default_rng(986);polys=[];cs=[];origins=[]
        for i in range(700):
            N=int(rng.integers(3,9));t=np.arange(N)*2*np.pi/N;v=np.stack([np.cos(t),np.sin(t)],axis=1)
            A=rng.normal(size=(2,2));A+=np.eye(2)*2;o=rng.uniform(-50,50,2)
            polys.append(v@A+o);origins.append(o);cs.append(rng.normal(size=6))
        self.compare(polys,np.array(cs),origins)
    def test_nonfinite_data_refused(self):
        with self.assertRaises(ValueError):QuadraticGapBatch([[[0,0],[1,0],[0,1]]],[[np.nan,0]])
        b=QuadraticGapBatch([[[0,0],[1,0],[0,1]]],[[0,0]])
        with self.assertRaises(ValueError):b.extrema([[0,1,2,np.inf,0,1]])
    def test_concave_polygon_rejected(self):
        with self.assertRaises(ValueError):QuadraticGapBatch([[[0,0],[2,0],[.3,.3],[0,2]]],[[0,0]])
    def test_gap_sign_not_clamped(self):
        b=QuadraticGapBatch([[[0,0],[1,0],[0,1]]],[[0,0]]).extrema([[-3e-8,0,0,0,0,0]])
        self.assertEqual(b['minimum'][0],-3e-8)
    def test_no_interior_solution_outside_polygon(self):
        self.compare([[[0,0],[1,0],[0,1]]],np.array([[100,-20,-20,1,0,1]]),[[0,0]])


class SelectionTests(unittest.TestCase):
    def row(self,p,c,x,g=-1.):return {'patch':p,'cell':c,'minimum_at':[x,0.],'minimum':g}
    def test_patches_not_starved_by_first_patch(self):
        rows=[self.row('A',i,i,-100) for i in range(10)]+[self.row('B',11,0,-1)]
        v=select_violations(rows,{},maximum_new=2)
        self.assertEqual([x['patch'] for x in v],['A','B'])
    def test_deterministic_under_input_permutation(self):
        rows=[self.row('A',i,i,-i) for i in range(8)]
        self.assertEqual(select_violations(rows,{},maximum_new=5),select_violations(rows[::-1],{},maximum_new=5))
    def test_exact_prior_point_skipped_not_removed(self):
        old={'A':[[0,0]]};v=select_violations([self.row('A',0,0),self.row('A',1,1)],old)
        self.assertEqual([x['cell'] for x in v],[1]);self.assertEqual(old,{'A':[[0,0]]})
    def test_distinct_nearby_violations_not_dropped_by_spacing(self):
        v=select_violations([self.row('A',i,i*1e-5) for i in range(5)],{})
        self.assertEqual(len(v),5)
    def test_duplicate_within_new_batch_coalesced(self):
        v=select_violations([self.row('A',0,1),self.row('A',1,1)],{})
        self.assertEqual(len(v),1)
    def test_no_points_is_not_contact_acceptance(self):
        self.assertEqual(select_violations([self.row('A',0,1)],{'A':[[1,0]]}),[])
    def test_hard_limit_preserved(self):
        self.assertEqual(len(select_violations([self.row('A',i,i) for i in range(500)],{},maximum_new=31)),31)
    def test_bad_caps_and_positions_refused(self):
        with self.assertRaises(ValueError):select_violations([],{},maximum_new=True)
        with self.assertRaises(ValueError):select_violations([self.row('A',0,float('nan'))],{})
        with self.assertRaises(ValueError):select_violations([],{'A':[[np.inf,0]]})

class StrictPriorTests(unittest.TestCase):
    def test_prior_boolean_and_string_coordinates_are_rejected(self):
        for old in ({'A':[[True,False]]},{'A':[['1','2']]},{'A':''}):
            with self.assertRaises(ValueError):select_violations([],old)
    def test_prior_and_new_patch_identity_required(self):
        for old in ([],{'':[]}):
            with self.assertRaises(ValueError):select_violations([],old)
        with self.assertRaises(ValueError):
            select_violations([{'patch':'','cell':0,'minimum_at':[0.,0.],'minimum':-1.}],{})

if __name__=='__main__':unittest.main()
