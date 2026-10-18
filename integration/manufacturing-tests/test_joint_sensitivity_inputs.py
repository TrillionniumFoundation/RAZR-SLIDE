from pathlib import Path
import copy,json,sys,unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'engineering/consistent-load-20261017'))
from surface_archive import checked_study_controls,frozen_trace_selection

class StudyInputTests(unittest.TestCase):
    def setUp(self):
        self.r={'schema':'razr-frozen-traces-v1','mesh_sha256':{'panel':'a'*64,'frame':'b'*64},
          'source_report_sha256':'c'*64,'source_selection_sha256':'d'*64,
          'selected_faces':[{'body':name,'patch':'pad0','vertices':[0,1,2]} for name in ('panel','frame')]}
    def selected(self):return frozen_trace_selection(self.r,'panel','a'*64)
    def test_legacy_defaults_preserved(self):self.assertEqual(checked_study_controls(),(6,1e-7,2,2e-4))
    def test_all_historical_cases_select_correct_load(self):
        for i in range(8):self.assertEqual(checked_study_controls(i)[2],i%4)
    def test_zero_initial_force_cases(self):
        for i in range(4):self.assertEqual(checked_study_controls(i)[3],0.)
    def test_preloaded_cases_have_same_synthetic_initial_force(self):
        for i in range(4,8):self.assertEqual(checked_study_controls(i)[3],2e-4)
    def test_invalid_case_type(self):
        for i in (True,6.,'6',np.int64(6),None):
            with self.assertRaises(ValueError):checked_study_controls(i)
    def test_case_bounds(self):
        for i in (-1,8):
            with self.assertRaises(ValueError):checked_study_controls(i)
    def test_stricter_target_accepted_unchanged(self):self.assertEqual(checked_study_controls(6,2e-8)[1],2e-8)
    def test_looser_target_rejected(self):
        with self.assertRaises(ValueError):checked_study_controls(6,1.00001e-7)
    def test_nonfinite_and_nonpositive_targets_rejected(self):
        for x in (0.,-1.,float('nan'),float('inf'),True,'1e-7',None):
            with self.assertRaises(ValueError):checked_study_controls(6,x)
    def test_frozen_body_selection(self):self.assertEqual(self.selected(),[self.r['selected_faces'][0]])
    def test_frozen_selection_is_a_deep_copy(self):
        x=self.selected();x[0]['vertices'][0]=123;self.assertEqual(self.r['selected_faces'][0]['vertices'][0],0)
    def test_wrong_mesh_rejected(self):
        with self.assertRaises(ValueError):frozen_trace_selection(self.r,'panel','e'*64)
    def test_wrong_schema_rejected(self):
        self.r['schema']='other'
        with self.assertRaises(ValueError):self.selected()
    def test_missing_body_hash_rejected(self):
        self.r['mesh_sha256'].pop('frame')
        with self.assertRaises(ValueError):self.selected()
    def test_bad_hash_length_rejected(self):
        self.r['source_report_sha256']='c'*63
        with self.assertRaises(ValueError):self.selected()
    def test_nonhex_hash_rejected(self):
        self.r['source_selection_sha256']='z'*64
        with self.assertRaises(ValueError):self.selected()
    def test_duplicate_face_different_label_rejected(self):
        self.r['selected_faces'].append({'body':'panel','patch':'other','vertices':[0,1,2]})
        with self.assertRaises(ValueError):self.selected()
    def test_vertex_alias_and_invalid_types_rejected(self):
        for ids in ([0,0,2],[True,1,2],[0,1.,2],[-1,0,1]):
            self.r['selected_faces'][0]['vertices']=ids
            with self.assertRaises(ValueError):self.selected()
    def test_noncanonical_order_rejected(self):
        self.r['selected_faces'][0]['vertices']=[2,0,1]
        with self.assertRaises(ValueError):self.selected()
    def test_unknown_or_absent_body_rejected(self):
        with self.assertRaises(ValueError):frozen_trace_selection(self.r,'other','a'*64)
        self.r['selected_faces']=self.r['selected_faces'][1:]
        with self.assertRaises(ValueError):self.selected()
    def test_empty_face_list_or_patch_rejected(self):
        self.r['selected_faces'][0]['patch']=''
        with self.assertRaises(ValueError):self.selected()
        self.r['selected_faces']=[]
        with self.assertRaises(ValueError):self.selected()
    def test_committed_source_selection_is_exactly86_faces(self):
        r=json.loads((ROOT/'engineering/joint-sensitivity-20261017/frozen-selection.json').read_text())
        a=frozen_trace_selection(r,'panel',r['mesh_sha256']['panel']);b=frozen_trace_selection(r,'frame',r['mesh_sha256']['frame'])
        self.assertEqual((len(a),len(b)),(46,40));self.assertEqual(3*(len(a)+len(b)),258)
