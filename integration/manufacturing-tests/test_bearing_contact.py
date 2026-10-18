import unittest
import numpy as np
from bearing_contact import (real,plane_basis,bearing_id,equilibrium_map,split_coordinates,gap,axial_adjustment,resultants)
from installation_control import force_equalities
from contact_dual_active import solve_force_qp

class BearingContactTests(unittest.TestCase):
    def model(self,weights=None):
        centers=np.array([[-2.,0.],[2.,0.],[-2.,4.],[2.,4.]])
        points=[{'kind':'bolt','index':i} for i in range(4)]
        for body in ['panel','frame']:
            for i in range(4):
                for xy in [[1.,0.],[0.,1.],[-1.,0.],[0.,-1.]]:
                    points.append({'kind':'bearing','body':body,'index':i,'xy':(centers[i]+xy).tolist()})
        G=equilibrium_map(np.zeros((36,0)),points,centers)
        S=np.diag(np.r_[np.full(4,5.),np.ones(32) if weights is None else weights])
        return centers,points,G,S
    def test_head_nut_ids(self):
        self.assertEqual(bearing_id('panel',3),3);self.assertEqual(bearing_id('frame',0),4)
    def test_reject_unknown_body(self):
        with self.assertRaises(ValueError):bearing_id('head',0)
    def test_reject_bad_bolt_index(self):
        for v in [-1,4,True,1.5]:
            with self.assertRaises(ValueError):bearing_id('panel',v)
    def test_plane_basis_preserves_affine_work(self):
        np.testing.assert_allclose(plane_basis([[3,5],[4,6]],[2,3])@np.array([1,2,3]),[9,14])
    def test_rigid_translation_gap_sign(self):
        self.assertAlmostEqual(gap([.2],[[0,0]],[0,0],[.1,0,0],'panel')[0],.1)
        self.assertAlmostEqual(gap([-.2],[[0,0]],[0,0],[.1,0,0],'frame')[0],.1)
    def test_plane_tilt_is_not_fixed(self):
        np.testing.assert_allclose(gap([.2,-.2],[[1,0],[-1,0]],[0,0],[0,.2,0],'panel'),[0,0])
    def test_physical_and_bearing_coordinates_separate(self):
        r,p=split_coordinates(np.arange(30.),6);np.testing.assert_array_equal(r,np.arange(6));self.assertEqual(p.shape,(8,3))
    def test_wrong_coordinate_count_rejected(self):
        with self.assertRaises(ValueError):split_coordinates(np.ones(34),6)
    def test_first_four_connectors_have_no_member_tractions(self):
        c,p,G,S=self.model();phys=np.zeros((36,6));phys[0,2]=1
        with self.assertRaises(ValueError):equilibrium_map(phys,p,c)
    def test_bolt_identity_order_rejected(self):
        c,p,_,_=self.model();p[0]['index']=1
        with self.assertRaises(ValueError):equilibrium_map(np.zeros((36,6)),p,c)
    def test_contact_kind_rejected(self):
        c,p,_,_=self.model();p[4]['kind']='weld'
        with self.assertRaises(ValueError):equilibrium_map(np.zeros((36,6)),p,c)
    def test_original_equilibrium_unchanged(self):
        c,p,_,_=self.model();g=np.zeros((36,6));g[4:]=np.arange(192.).reshape(32,6);v=g.copy()
        h=equilibrium_map(g,p,c);np.testing.assert_array_equal(h[:,:6],v);np.testing.assert_array_equal(g,v)
    def test_equal_target_not_equal_external_sharing(self):
        c,p,G,S=self.model();t=np.array([.1,.2,.3,.4]);GG,b=force_equalities(G,np.zeros(24),t)
        r=solve_force_qp(S,np.zeros(36),GG,b,factor_reuse=True,rank_fallback='qr_pivot');self.assertTrue(r['passed'])
        f=np.array(r['forces']);np.testing.assert_allclose(f[:4],t,atol=1e-10)
        rr=resultants(f,p,c);np.testing.assert_allclose(rr[:,0],np.tile(t,2),atol=1e-10);np.testing.assert_allclose(rr[:,1:],0,atol=1e-10)
        np.testing.assert_allclose(f[4:],np.repeat(np.tile(t,2)/4,4),atol=1e-10)
    def test_installation_then_fixed_adjustment(self):
        c,p,G,S=self.model();t=np.full(4,.2);GG,b=force_equalities(G,np.zeros(24),t)
        r=solve_force_qp(S,np.zeros(36),GG,b,factor_reuse=True,rank_fallback='qr_pivot');self.assertTrue(r['passed'])
        z=np.array(r['rigid_mode_coordinates']);_,planes=split_coordinates(z[:-4],0);delta=axial_adjustment(t,np.full(4,5.),planes)
        np.testing.assert_allclose(delta,1.1,atol=1e-9);np.testing.assert_allclose(delta,z[-4:],atol=1e-9)
        d=np.r_[delta,np.zeros(32)];lock=solve_force_qp(S,d,G,np.zeros(24),factor_reuse=True,rank_fallback='qr_pivot');self.assertTrue(lock['passed']);np.testing.assert_allclose(lock['forces'],r['forces'],atol=1e-9)
    def test_nonuniform_compliance_redistributes_pressure(self):
        c,p,G,S=self.model(np.tile([1.,2.,3.,4.],8));GG,b=force_equalities(G,np.zeros(24),[.2]*4)
        r=solve_force_qp(S,np.zeros(36),GG,b,factor_reuse=True,rank_fallback='qr_pivot');self.assertTrue(r['passed'])
        f=np.array(r['forces']);self.assertGreater(np.ptp(f[4:8]),.001);rr=resultants(f,p,c)
        np.testing.assert_allclose(rr[:,0],.2,atol=1e-9);np.testing.assert_allclose(rr[:,1:],0,atol=1e-9)
    def test_separation_gives_zero_contact_force(self):
        c,p,G,S=self.model();p.append({'kind':'bearing','body':'panel','index':0,'xy':c[0].tolist()});G=equilibrium_map(np.zeros((37,0)),p,c);S=np.diag(np.r_[np.full(4,5.),np.ones(33)]);d=np.zeros(37);d[-1]=-10.;GG,b=force_equalities(G,np.zeros(24),[.2]*4)
        r=solve_force_qp(S,d,GG,b,factor_reuse=True,rank_fallback='qr_pivot');self.assertTrue(r['passed']);self.assertAlmostEqual(r['forces'][-1],0,places=9)
        self.assertGreater(r['reduced_gradient'][-1],0);self.assertGreaterEqual(min(r['forces'][4:]),-1e-10)
    def test_moment_without_support_is_rejected(self):
        c,p,G,S=self.model();G[4:,2]=0.;load=np.zeros(24);load[2]=.1
        r=solve_force_qp(S,np.zeros(36),G,load,factor_reuse=True,rank_fallback='qr_pivot');self.assertFalse(r['passed'])
    def test_manufactured_random_diagonal_models(self):
        rng=np.random.default_rng(638)
        for _ in range(12):
            c,p,G,S=self.model(rng.uniform(.2,3,32));t=rng.uniform(.01,.3,4);GG,b=force_equalities(G,np.zeros(24),t)
            r=solve_force_qp(S,np.zeros(36),GG,b,factor_reuse=True,rank_fallback='qr_pivot');self.assertTrue(r['passed'])
            f=np.array(r['forces']);nu=np.array(r['rigid_mode_coordinates']);grad=S@f-GG@nu
            self.assertLess(np.max(abs(GG.T@f-b)),1e-9);self.assertLess(np.max(abs(grad[:4])),1e-9)
            self.assertGreaterEqual(min(grad[4:]),-1e-9);self.assertLess(np.max(abs(f[4:]*grad[4:])),1e-9)
    def test_zero_target_allowed_without_fake_compression(self):
        c,p,G,S=self.model();GG,b=force_equalities(G,np.zeros(24),[0,.2,0,.2])
        r=solve_force_qp(S,np.zeros(36),GG,b,factor_reuse=True,rank_fallback='qr_pivot');self.assertTrue(r['passed']);np.testing.assert_allclose(resultants(r['forces'],p,c)[:,0],np.tile([0,.2,0,.2],2),atol=1e-9)
    def test_adjustment_positive_compliance_required(self):
        with self.assertRaises(ValueError):axial_adjustment(np.ones(4),np.zeros(4),np.zeros((8,3)))
    def test_tensile_branch_rejects_negative_bolt(self):
        with self.assertRaises(ValueError):axial_adjustment([-1,1,1,1],np.ones(4),np.zeros((8,3)))
    def test_no_nonfinite_plane(self):
        with self.assertRaises(ValueError):gap([0],[[0,0]],[0,0],[np.nan,0,0],'panel')
    def test_vectors_copy_inputs(self):
        x=np.ones(3);y=real(x,1,'x');y[0]=0;self.assertEqual(x[0],1)
    def test_resultant_invalid_length(self):
        c,p,_,_=self.model()
        with self.assertRaises(ValueError):resultants(np.ones(3),p,c)

if __name__=='__main__':unittest.main()
