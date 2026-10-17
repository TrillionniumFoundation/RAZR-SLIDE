from pathlib import Path
import importlib.util, json, tempfile, unittest, sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
from contact_exchange import QuadraticGapBatch
spec=importlib.util.spec_from_file_location('resume_serialization_candidate',ROOT/'engineering/preload-resume-20261016/resume_original.py')
writer=importlib.util.module_from_spec(spec);spec.loader.exec_module(writer)

class ResumeSerializationTests(unittest.TestCase):
    def roundtrip(self,value):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'report.json';writer.dump(p,value)
            return json.loads(p.read_text())

    def test_multi_element_matrix_preserves_shape(self):
        self.assertEqual(self.roundtrip(np.arange(6).reshape(2,3)),[[0,1,2],[3,4,5]])

    def test_length_one_array_remains_a_list(self):
        self.assertEqual(self.roundtrip(np.array([2.])),[2.])

    def test_numpy_scalar_types(self):
        self.assertEqual(self.roundtrip({'b':np.bool_(True),'i':np.int64(4),'f':np.float32(.5)}),{'b':True,'i':4,'f':.5})

    def test_nested_arrays_and_lists(self):
        self.assertEqual(self.roundtrip({'a':[np.array([1,2]),{'x':np.eye(2)}]}),{'a':[[1,2],{'x':[[1.,0.],[0.,1.]]}]})

    def test_empty_array_is_retained(self):
        self.assertEqual(self.roundtrip(np.empty((0,2))),[])

    def test_zero_dimensional_array_is_scalar(self):
        self.assertEqual(self.roundtrip(np.array(7)),7)

    def test_unsigned_integer_is_exact(self):
        self.assertEqual(self.roundtrip(np.uint64(2**63+7)),2**63+7)

    def test_nonfinite_rejected_before_overwriting_prior_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'result.json';p.write_text('KEEP')
            for x in (np.array([np.nan]),np.array([np.inf]),np.float64(-np.inf)):
                with self.assertRaises(ValueError):writer.dump(p,{'a':x})
                self.assertEqual(p.read_text(),'KEEP')

    def test_unknown_object_rejected_without_partial_file(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'new.json'
            with self.assertRaises(TypeError):writer.dump(p,{'bad':object()})
            self.assertFalse(p.exists())

    def test_real_batch_audit_arrays_and_negative_results_survive(self):
        polys=[np.array([[0.,0.],[1.,0.],[1.,1.],[0.,1.]])]*2
        batch=QuadraticGapBatch(polys,np.zeros((2,2)))
        coeff=np.array([[-.2,0.,0.,1.,0.,1.],[.1,0.,0.,0.,0.,0.]])
        a=batch.extrema(coeff);r=self.roundtrip(a)
        for k,v in a.items():np.testing.assert_array_equal(np.asarray(r[k]),v)
        self.assertEqual(r['minimum'][0],-.2)
