from pathlib import Path
import copy,json,tempfile,unittest
import numpy as np
from installation_control import (SCHEMA,vector,binding_digest,force_equalities,split_coordinates,adjustment_from_state,locked_force,decode_control,read_control,seal_locked_state,sha256)
from contact_dual_active import solve_force_qp

class InstallationControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.plan={'schema':SCHEMA,'mode':'force_targets','bolt_ids':['bolt0','bolt1','bolt2','bolt3'],'units':'force/Epanel:mm2;Epanel/k:1/mm;adjustment:mm','physical_measurement':False,'compliance_Epanel_over_k_per_mm':[5.,6.,7.,8.],'target_force_over_Epanel_mm2':[.2,.3,.4,.5]}
        self.identity=binding_digest({'K':'frozen','surface':'512','support':'unchanged'})
    def tearDown(self):self.tmp.cleanup()
    def decode(self,d,load=0.):return decode_control(d,model_identity=self.identity,external_scale=load)
    def sealed(self):
        f=self.plan['target_force_over_Epanel_mm2'];c=self.plan['compliance_Epanel_over_k_per_mm'];q=[-.1,-.2,-.3,-.4]
        state={'mode':'force_targets','model_identity':self.identity,'assembly_force_over_Epanel_mm2':f,'assembly_separation_mm':q,'compliance_Epanel_over_k_per_mm':c,'adjustment_mm':adjustment_from_state(f,q,c).tolist()}
        rp=self.root/'report.json';fp=self.root/'full-fields.npz';ap=self.root/'audit.json';out=self.root/'lock.json'
        rp.write_text(json.dumps({'passed':True,'external_load_scale_over_Epanel_mm2':0.,'installation_control':state}));np.savez(fp,forces=f)
        ap.write_text(json.dumps({'passed':True,'input_sha256':{str(rp):sha256(rp),str(fp):sha256(fp)}}))
        seal_locked_state(self.root,ap,out);return out
    def test_vector_copy_not_input_mutation(self):
        a=np.ones(4);b=vector(a,'v');b[0]=3;self.assertEqual(a[0],1)
    def test_boolean_targets_rejected(self):
        for a in [[True]*4,[.2,False,.2,.2]]:
            with self.assertRaises(ValueError):vector(a,'v')
    def test_vector_shape_rejected(self):
        for a in [[],[1,2,3],[[1,2,3,4]],2.]:
            with self.assertRaises(ValueError):vector(a,'v')
    def test_nan_inf_complex_rejected(self):
        for a in [[1,2,3,float('nan')],[1,2,3,float('inf')],[1,2,3,1j]]:
            with self.assertRaises(ValueError):vector(a,'v')
    def test_nonpositive_compliance_rejected(self):
        for n in [0,-1]:
            p=copy.deepcopy(self.plan);p['compliance_Epanel_over_k_per_mm'][1]=n
            with self.assertRaises(ValueError):self.decode(p)
    def test_negative_force_rejected(self):
        p=copy.deepcopy(self.plan);p['target_force_over_Epanel_mm2'][1]=-1
        with self.assertRaises(ValueError):self.decode(p)
    def test_force_targets_allow_unequal_and_zero(self):
        p=copy.deepcopy(self.plan);p['target_force_over_Epanel_mm2'][0]=0
        np.testing.assert_array_equal(self.decode(p)['targets'],[0,.3,.4,.5])
    def test_force_control_rejects_external_service_load(self):
        with self.assertRaises(ValueError):self.decode(self.plan,1e-5)
    def test_explicit_normalization_required(self):
        p=copy.deepcopy(self.plan);p['units']='N'
        with self.assertRaises(ValueError):self.decode(p)
    def test_bolt_identity_and_order_required(self):
        p=copy.deepcopy(self.plan);p['bolt_ids'].reverse()
        with self.assertRaises(ValueError):self.decode(p)
    def test_no_physical_measurement_fabrication(self):
        p=copy.deepcopy(self.plan);p['physical_measurement']=True
        with self.assertRaises(ValueError):self.decode(p)
    def test_unknown_schema_mode_rejected(self):
        for k in ['schema','mode']:
            p=copy.deepcopy(self.plan);p[k]='other'
            with self.assertRaises(ValueError):self.decode(p)
    def test_binding_stable_order_sensitive_values(self):
        self.assertEqual(binding_digest({'a':1,'b':2}),binding_digest({'b':2,'a':1}))
        self.assertNotEqual(binding_digest({'K':1}),binding_digest({'K':2}))
    def test_binding_rejects_nonfinite(self):
        with self.assertRaises(ValueError):binding_digest({'E':float('nan')})
    def test_added_equations_are_actuator_selector(self):
        G=np.arange(30.).reshape(10,3);load=np.array([1.,2.,3.]);GG,ll=force_equalities(G,load,[.2]*4)
        np.testing.assert_array_equal(GG[:,:3],G);np.testing.assert_array_equal(GG[:4,3:],np.eye(4));self.assertFalse(GG[4:,3:].any());np.testing.assert_array_equal(ll[:3],load)
    def test_physical_maps_not_mutated(self):
        G=np.ones((8,3));load=np.ones(3);force_equalities(G,load,[.2]*4)
        np.testing.assert_array_equal(G,np.ones((8,3)));np.testing.assert_array_equal(load,np.ones(3))
    def test_bad_map_dimensions_rejected(self):
        for G,load in [(np.ones((3,2)),np.ones(2)),(np.ones((8,3)),np.ones(2))]:
            with self.assertRaises(ValueError):force_equalities(G,load,[.2]*4)
    def test_actuator_multipliers_not_rigid_coordinates(self):
        rigid,act=split_coordinates(np.arange(10.),6,force_control=True)
        np.testing.assert_array_equal(rigid,np.arange(6.));np.testing.assert_array_equal(act,np.arange(6.,10.))
    def test_legacy_six_coordinates_unchanged(self):
        r,a=split_coordinates(np.arange(6.),6,force_control=False);self.assertEqual(len(a),0);np.testing.assert_array_equal(r,np.arange(6.))
    def test_wrong_coordinate_dimensions_rejected(self):
        with self.assertRaises(ValueError):split_coordinates(np.ones(6),6,force_control=True)
    def test_adjustment_and_force_inverse(self):
        rng=np.random.default_rng(151)
        for _ in range(25):
            f=rng.uniform(0,1,4);q=rng.normal(size=4);c=rng.uniform(.1,10,4)
            np.testing.assert_allclose(locked_force(q,c,adjustment_from_state(f,q,c)),f,atol=1e-14)
    def test_lock_does_not_hold_force_constant(self):
        f=np.full(4,.2);q=np.full(4,-.1);c=np.full(4,5.);d=adjustment_from_state(f,q,c)
        np.testing.assert_allclose(locked_force(q+.05,c,d),f+.01)
    def test_force_and_lock_full_QP_match_closed_form(self):
        rng=np.random.default_rng(811)
        for _ in range(8):
            M=rng.normal(size=(4,4));H=M@M.T+.5*np.eye(4);c=rng.uniform(1,4,4);S=H+np.diag(c);t=rng.uniform(.1,.3,4)
            G,l=force_equalities(np.zeros((4,0)),np.zeros(0),t)
            a=solve_force_qp(S,np.zeros(4),G,l,free_prefix=4,factor_reuse=True,rank_fallback='qr_pivot');self.assertTrue(a['passed'])
            f=np.array(a['forces']);q=-H@f;delta=c*f-q
            np.testing.assert_allclose(a['rigid_mode_coordinates'],delta,atol=1e-9)
            b=solve_force_qp(S,delta,np.zeros((4,0)),np.zeros(0),free_prefix=4);self.assertTrue(b['passed']);np.testing.assert_allclose(b['forces'],t,atol=1e-9)
            service=rng.uniform(0,.03,4);b=solve_force_qp(S,delta+service,np.zeros((4,0)),np.zeros(0),free_prefix=4)
            np.testing.assert_allclose(b['forces'],np.linalg.solve(S,delta+service),atol=1e-9)
    def test_unilateral_contacts_retained_under_force_control(self):
        rng=np.random.default_rng(82)
        for _ in range(10):
            M=rng.normal(size=(8,8));S=M@M.T+np.eye(8);d=rng.normal(size=8);t=rng.uniform(.1,.3,4)
            G,l=force_equalities(np.zeros((8,0)),np.zeros(0),t)
            a=solve_force_qp(S,d,G,l,free_prefix=4,rank_fallback='qr_pivot',factor_reuse=True);self.assertTrue(a['passed'])
            b=solve_force_qp(S[4:,4:],d[4:]-S[4:,:4]@t,np.zeros((4,0)),np.zeros(0),free_prefix=0);self.assertTrue(b['passed'])
            np.testing.assert_allclose(a['forces'][:4],t,atol=1e-9);np.testing.assert_allclose(a['forces'][4:],b['forces'],atol=1e-9)
    def test_seal_and_read_locked_state(self):
        p=self.sealed();r,h=read_control(p,model_identity=self.identity,external_scale=1e-5)
        self.assertEqual(r['mode'],'locked_adjustment');self.assertEqual(len(h),4)
    def test_locked_state_rejects_changed_model(self):
        p=self.sealed()
        with self.assertRaises(ValueError):read_control(p,model_identity='different',external_scale=1e-5)
    def test_locked_state_rejects_changed_source_field(self):
        p=self.sealed();(self.root/'full-fields.npz').write_bytes(b'changed')
        with self.assertRaises(ValueError):read_control(p,model_identity=self.identity,external_scale=1e-5)
    def test_locked_state_rejects_altered_adjustment(self):
        p=self.sealed();r=json.loads(p.read_text());r['adjustment_mm'][0]+=.01;p.write_text(json.dumps(r))
        with self.assertRaises(ValueError):read_control(p,model_identity=self.identity,external_scale=1e-5)
    def test_seal_rejects_failure_and_unbound_audit(self):
        self.sealed();ap=self.root/'audit.json';ap.write_text(json.dumps({'passed':False}))
        with self.assertRaises(ValueError):seal_locked_state(self.root,ap,self.root/'other.json')
        ap.write_text(json.dumps({'passed':True,'input_sha256':{}}))
        with self.assertRaises(ValueError):seal_locked_state(self.root,ap,self.root/'other.json')
    def test_no_overwrite_of_existing_installed_state(self):
        p=self.sealed()
        with self.assertRaises(FileExistsError):seal_locked_state(self.root,self.root/'audit.json',p)

if __name__=='__main__':unittest.main()
