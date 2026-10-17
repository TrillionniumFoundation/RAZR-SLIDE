from pathlib import Path
import sys,unittest,itertools
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
import tetra_bubble_refinement as t

class TetraBubbleTests(unittest.TestCase):
    def setUp(self):
        self.v=np.array([t.REF,t.REF@np.array([[1.2,.1,.2],[.2,.9,-.1],[.1,.2,1.4]])+[3.,-1.,2.]])
        self.k=t.p2_stiffness(self.v);self.s=t.star_condense(self.v)
    def test_shapes_and_singleton_batch(self):
        self.assertEqual(self.k.shape,(2,30,30));self.assertEqual(self.s.internal_extension.shape,(2,15,30))
    def test_four_subvolumes_sum_to_parent(self):
        v=np.concatenate((self.v,self.v.mean(axis=1)[:,None]),axis=1)
        np.testing.assert_allclose(sum(t._vertices(v[:,c])[2] for c in t.CHILDREN),t._vertices(self.v)[2],rtol=1e-13)
    def test_faces_and_original_nodes_unchanged(self):
        self.assertEqual(len(t.STAR_NODES),15)
        for i in range(4):
            faces=[]
            for c in t.CHILDREN:
                for f in itertools.combinations(c,3):
                    if 4 not in f:faces.append(tuple(sorted(f)))
            self.assertIn(tuple(j for j in range(4) if j!=i),faces)
        np.testing.assert_array_equal(t.STAR_NODES[:10],t.p2_nodes(t.REF))
    def test_coarse_quadratic_energy_reproduced_on_refined_mesh(self):
        p=t.prolong_p2(self.v)
        np.testing.assert_allclose(p.transpose(0,2,1)@self.s.uncondensed@p,self.k,rtol=1e-12,atol=1e-12)
    def test_refinement_cannot_stiffen_original_boundary_energy(self):
        for d in self.k-self.s.stiffness:self.assertGreater(np.linalg.eigvalsh(d).min(),-1e-11)
    def test_second_nested_level_cannot_stiffen(self):
        s2=t.star_condense(self.v,level=2)
        for d in self.s.stiffness-s2.stiffness:self.assertGreater(np.linalg.eigvalsh(d).min(),-1e-11)
    def test_symmetry(self):
        np.testing.assert_allclose(self.s.stiffness,self.s.stiffness.transpose(0,2,1),atol=1e-14)
    def test_six_rigid_modes(self):
        nodes=t.p2_nodes(self.v)
        for axis in np.eye(3):
            for u in (np.broadcast_to(axis,nodes.shape),np.cross(axis,nodes)):
                np.testing.assert_allclose(np.einsum('tij,tj->ti',self.s.stiffness,u.reshape(2,30)),0,atol=3e-12)
    def test_affine_strain_response_preserved(self):
        rng=np.random.default_rng(15)
        for _ in range(6):
            u=(t.p2_nodes(self.v)@rng.normal(size=(3,3))).reshape(2,30)
            np.testing.assert_allclose(np.einsum('tij,tj->ti',self.s.stiffness-self.k,u),0,atol=2e-12)
    def test_exact_internal_equilibrium_after_recovery(self):
        u=self.s.recover(np.random.default_rng(4).normal(size=(2,30)))
        np.testing.assert_allclose(np.einsum('tij,tj->ti',self.s.uncondensed[:,30:],u),0,atol=1e-12)
    def test_recovered_energy_equals_condensed_energy(self):
        b=np.random.default_rng(5).normal(size=(2,30));u=self.s.recover(b)
        np.testing.assert_allclose(np.einsum('ti,tij,tj->t',u,self.s.uncondensed,u),np.einsum('ti,tij,tj->t',b,self.s.stiffness,b),rtol=1e-12)
    def test_fixed_internal_dofs_are_not_condensation(self):
        self.assertGreater(np.linalg.norm(self.s.uncondensed[:,:30,:30]-self.s.stiffness),.1)
    def test_young_modulus_scaling(self):
        np.testing.assert_allclose(t.star_condense(self.v,E=7.).stiffness,7*self.s.stiffness,rtol=1e-12,atol=1e-12)
    def test_length_scaling_in_3d(self):
        np.testing.assert_allclose(t.star_condense(self.v*2).stiffness,2*self.s.stiffness,rtol=1e-12,atol=1e-12)
    def test_translation_invariance(self):
        np.testing.assert_allclose(t.star_condense(self.v+10).stiffness,self.s.stiffness,atol=2e-12)
    def test_orientation_reversal_preserves_energy(self):
        rev=self.v[:,[1,0,2,3]];kr=t.star_condense(rev).stiffness
        old=t.p2_nodes(self.v[0]);new=t.p2_nodes(rev[0]);perm=[np.argmin(np.linalg.norm(old-x,axis=1)) for x in new];ids=(3*np.array(perm)[:,None]+np.arange(3)).ravel()
        np.testing.assert_allclose(kr,self.s.stiffness[:,ids[:,None],ids[None,:]],atol=2e-12)
    def test_batch_matches_individual(self):
        for i in range(2):np.testing.assert_allclose(t.star_condense(self.v[i:i+1]).stiffness[0],self.s.stiffness[i],atol=1e-14)
    def test_bad_dimensions_refused(self):
        for v in ([],np.zeros((4,3)),np.zeros((1,4,2))):
            with self.assertRaises(ValueError):t.star_condense(v)
    def test_nonfinite_or_boolean_geometry_refused(self):
        for x in (np.nan,np.inf):
            v=self.v.copy();v[0,0,0]=x
            with self.assertRaises(ValueError):t.star_condense(v)
        with self.assertRaises(ValueError):t.star_condense(np.ones((1,4,3),dtype=bool))
    def test_degenerate_tetra_refused(self):
        v=self.v.copy();v[:,3]=v[:,2]
        with self.assertRaises(ValueError):t.star_condense(v)
    def test_invalid_material_refused(self):
        for E in (True,0.,-1.,np.inf):
            with self.assertRaises(ValueError):t.star_condense(self.v,E=E)
        for nu in (True,-1.,.5,np.nan):
            with self.assertRaises(ValueError):t.star_condense(self.v,nu=nu)
    def test_explicit_level_limits(self):
        for level in (True,0,3,1.5):
            with self.assertRaises(ValueError):t.star_condense(self.v,level=level)
    def test_recovery_bad_boundary_refused(self):
        for b in (np.zeros((2,29)),np.full((2,30),np.nan),np.ones((2,30),dtype=bool)):
            with self.assertRaises(ValueError):self.s.recover(b)
    def test_inputs_not_mutated(self):
        v=self.v.copy();self.s.recover(np.zeros((2,30)));t.star_condense(v,level=2);np.testing.assert_array_equal(v,self.v)
    def audit_module(self):
        import importlib.util
        p=ROOT/'engineering/volume-convergence-20261017/frozen_load_response.py'
        spec=importlib.util.spec_from_file_location('volume_recovery_audit',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    def test_direct_strain_energy_matches_matrix_for_random_fields(self):
        u=np.random.default_rng(4).normal(size=(2,30));m=self.audit_module()
        np.testing.assert_allclose(m.strain_energy(self.v,u),np.einsum('ti,tij,tj->t',u,self.k,u),rtol=1e-12)
    def test_direct_strain_energy_has_no_rigid_energy(self):
        m=self.audit_module();u=np.cross([.2,.3,.4],t.p2_nodes(self.v))+[7.,11.,13.]
        self.assertLess(np.max(m.strain_energy(self.v,u)),1e-24)
    def test_rigid_translation_cancellation_does_not_change_strain(self):
        m=self.audit_module();u=np.random.default_rng(51).normal(size=(2,10,3))*1e-4
        a=m.strain_energy(self.v,u);b=m.strain_energy(self.v,u+123.)
        np.testing.assert_allclose(a,b,rtol=2e-9,atol=1e-18)
    def test_level2_recovered_finest_strain_matches_condensed_energy(self):
        m=self.audit_module();u=np.random.default_rng(65).normal(size=(2,30));obj=t.star_condense(self.v,level=2)
        inside,res,en=m.recovered(self.v,u,2);self.assertEqual(inside.shape,(2,75));self.assertLess(res,1e-11)
        np.testing.assert_allclose(en,np.einsum('ti,tij,tj->t',u,obj.stiffness,u),rtol=1e-11)
