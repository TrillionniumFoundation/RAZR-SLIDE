from pathlib import Path
import tempfile,json,hashlib,sys,unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'engineering/consistent-load-20261017'))
from surface_archive import SurfaceArchive

class SurfaceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)
        for name in ('panel','frame'):
            np.savez(self.p/(name+'.npz'),C=np.ones((6,4)),F=np.zeros((6,4)))
            row={'body':name,'patch':'bolt0','kind':'C','index':0,'vertices':[0,1,2],
                 'work_coefficients':[0,0,0,1/3,1/3,1/3,.45],'bubble_load':[0,0,-.45],'resultant_scalar':1.}
            (self.p/(name+'-faces.json')).write_text(json.dumps([row]))
        self.meta={'original_nodal_vectors_reproduced':True,'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.p.iterdir()}}
        self.write();self.original={'C':np.full((6,4),2.),'F':np.zeros((6,4))}
    def write(self):(self.p/'manifest.json').write_text(json.dumps(self.meta))
    def tearDown(self):self.tmp.cleanup()
    def test_byte_change_rejected(self):
        (self.p/'panel-faces.json').write_text('[]')
        with self.assertRaises(ValueError):SurfaceArchive(self.p)
    def test_traversal_rejected(self):
        self.meta['files_sha256']['../other']='a'*64;self.write()
        with self.assertRaises(ValueError):SurfaceArchive(self.p)
    def test_symlink_rejected(self):
        p=self.p/'alias';p.symlink_to(self.p/'panel.npz');self.meta['files_sha256']['alias']=hashlib.sha256(p.read_bytes()).hexdigest();self.write()
        with self.assertRaises(ValueError):SurfaceArchive(self.p)
    def test_unverified_original_rejected(self):
        self.meta['original_nodal_vectors_reproduced']=False;self.write()
        with self.assertRaises(ValueError):SurfaceArchive(self.p)
    def test_selected_load_face_adds_three_components(self):
        a=SurfaceArchive(self.p);chosen=a.extend_selection('panel',[],1);self.assertEqual(len(chosen),1)
        C,Cb,F,Fb=a.vectors('panel',chosen,self.original,'consistent');np.testing.assert_array_equal(Cb[:,0],[0,0,-.45]);self.assertEqual(Cb.shape,(3,4))
    def test_no_selected_face_has_no_bubble_load(self):
        a=SurfaceArchive(self.p);C,Cb,F,Fb=a.vectors('panel',[],self.original,'consistent');self.assertEqual(Cb.shape,(0,4))
    def test_discrete_option_retains_original(self):
        a=SurfaceArchive(self.p);chosen=a.extend_selection('panel',[],1);C,Cb,F,Fb=a.vectors('panel',chosen,self.original,'discrete')
        np.testing.assert_array_equal(C,self.original['C']);self.assertEqual(float(abs(Cb).sum()),0.)
    def test_invalid_mode_or_cap_rejected(self):
        a=SurfaceArchive(self.p)
        with self.assertRaises(ValueError):a.vectors('panel',[],self.original,'maybe')
        for n in (True,-1,5,1.5):
            with self.assertRaises(ValueError):a.extend_selection('panel',[],n)
    def test_existing_selected_face_not_duplicated(self):
        a=SurfaceArchive(self.p);old=[{'vertices':[0,1,2]}];self.assertEqual(a.extend_selection('panel',old,1),old)
    def test_original_input_unchanged(self):
        a=SurfaceArchive(self.p);a.vectors('panel',[],self.original,'consistent');np.testing.assert_array_equal(self.original['C'],np.full((6,4),2.))
