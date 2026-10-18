from pathlib import Path
import itertools,math,sys,unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
import face_trace_space as f
from tetra_bubble_refinement import star_condense,p2_stiffness,p2_nodes,REF

class FaceTraceTests(unittest.TestCase):
    def setUp(self):
        self.v=np.array([REF,REF@np.array([[1.,.2,.1],[.1,.8,.2],[.05,.2,1.3]])+2])
    def test_positive_exact_degree4_quadrature(self):
        self.assertTrue(np.all(f.WEIGHTS>0))
        for i in range(5):
            for j in range(5-i):
                for k in range(5-i-j):
                    got=np.sum(f.WEIGHTS*np.prod(f.QUADRATURE**[i,j,k],axis=1))
                    want=math.factorial(i)*math.factorial(j)*math.factorial(k)/math.factorial(i+j+k+3)
                    self.assertAlmostEqual(got,want,places=14)
    def test_face_values_vanish_at_all_old_nodes(self):
        self.assertLess(np.max(abs(f.face_values(self.v,p2_nodes(self.v)))),1e-12)
    def test_one_on_own_face_centre_and_zero_on_other_faces(self):
        points=np.stack([self.v[:,face,:].mean(axis=1) for face in f.FACES],axis=1)
        np.testing.assert_allclose(f.face_values(self.v,points),np.broadcast_to(np.eye(4),(2,4,4)),atol=2e-13)
    def test_coarse_energy_block_is_not_modified(self):
        np.testing.assert_allclose(f.trace_element(self.v)[:,:30,:30],p2_stiffness(self.v),atol=2e-13)
    def test_two_refined_energy_blocks_equal_previous_spaces(self):
        for level in (1,2):
            np.testing.assert_allclose(f.trace_condense(self.v,level=level).stiffness[:,:30,:30],star_condense(self.v,level=level).stiffness,atol=3e-12)
    def test_symmetric_enriched_energy(self):
        k=f.trace_condense(self.v).stiffness
        np.testing.assert_allclose(k,k.transpose(0,2,1),atol=1e-13)
    def test_six_rigid_modes_and_positive_new_modes(self):
        k=f.trace_condense(self.v).stiffness
        for n in range(2):
            xyz=p2_nodes(self.v[n]);modes=[]
            for axis in np.eye(3):
                modes.append(np.r_[np.tile(axis,10),np.zeros(12)])
                modes.append(np.r_[np.cross(np.broadcast_to(axis,xyz.shape),xyz).ravel(),np.zeros(12)])
            self.assertLess(np.max(abs(k[n]@np.array(modes).T)),2e-12)
            vals=np.linalg.eigvalsh(k[n]);self.assertEqual(np.count_nonzero(vals>1e-9),36)
    def test_higher_order_bubble_really_adds_energy_directions(self):
        k=f.trace_condense(self.v).stiffness
        for body in k:
            self.assertGreater(np.min(np.linalg.eigvalsh(body[30:,30:])),.001)
    def test_rigid_translation_has_no_new_trace_coefficients(self):
        old=np.tile([1.,-2.,3.],(2,10)).reshape(2,30);b=np.zeros((2,12))
        _,res,en=f.recover_trace(self.v,old,b)
        self.assertLess(res,1e-12);self.assertLess(np.max(abs(en)),1e-12)
    def test_recovery_has_all_private_unknowns(self):
        rng=np.random.default_rng(1);old=rng.normal(size=(2,30));b=rng.normal(size=(2,12))
        for level,num in [(0,0),(1,15),(2,75)]:
            private,res,en=f.recover_trace(self.v,old,b,level=level)
            self.assertEqual(private.shape,(2,num));self.assertLess(res,1e-11)
            u=np.c_[old,b];k=f.trace_condense(self.v,level=level).stiffness
            np.testing.assert_allclose(en,np.einsum('ni,nij,nj->n',u,k,u),rtol=1e-11,atol=1e-11)
    def test_same_shared_face_function_both_adjacent_tets(self):
        a=REF.copy();b=a[[0,2,1,3]].copy();b[3]=[0,0,-2.]
        p=np.array([[.1,.2,0],[.3,.4,0],[.2,.2,0]])
        av=f.face_values(a[None],p[None])[0,:,3];bv=f.face_values(b[None],p[None])[0,:,3]
        np.testing.assert_allclose(av,bv,atol=2e-14)
    def test_orientation_reversal_is_not_rejected(self):
        k=f.trace_element(self.v[:,[1,0,2,3]])
        self.assertTrue(np.isfinite(k).all())
        self.assertGreater(np.trace(k[0]),0)
    def test_material_scaling(self):
        np.testing.assert_allclose(f.trace_condense(self.v,E=7).stiffness,7*f.trace_condense(self.v).stiffness,rtol=1e-11,atol=1e-11)
    def test_bad_material_rejected(self):
        for E,nu in [(0,.3),(True,.3),(1,.5),(1,-1),(1,float('nan'))]:
            with self.assertRaises(ValueError):f.trace_condense(self.v,E,nu)
    def test_bad_levels_rejected(self):
        for lv in (True,-1,3,1.5,None):
            with self.assertRaises(ValueError):f.trace_condense(self.v,level=lv)
    def test_degenerate_tet_rejected(self):
        v=REF.copy();v[3]=v[2]
        with self.assertRaises(ValueError):f.trace_element(v[None])
    def test_nonfinite_inputs_rejected(self):
        v=self.v.copy();v[0,0,0]=np.nan
        with self.assertRaises(ValueError):f.trace_element(v)
    def test_new_functions_not_representable_by_old_nodal_values(self):
        p=self.v.mean(axis=1)[:,None,:]
        val=f.face_values(self.v,p)
        self.assertGreater(np.min(val),.4)
        self.assertEqual(np.max(abs(f.face_values(REF[None],p2_nodes(REF)[None]))),0)
    def test_original_inputs_not_mutated(self):
        v=self.v.copy();f.trace_condense(v);np.testing.assert_array_equal(v,self.v)
    def test_no_false_hardware_or_mesh_qualification(self):
        self.assertIn('not complete P3',f.__doc__)

if __name__=='__main__':unittest.main()
