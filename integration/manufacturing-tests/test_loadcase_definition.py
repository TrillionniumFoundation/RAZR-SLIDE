from pathlib import Path
import ast, sys, unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'engineering/consistent-load-20261017'))
from surface_archive import checked_external_load_scale, checked_study_controls

class LoadCaseDefinitionTests(unittest.TestCase):
    def test_omitted_scale_preserves_original_value(self):
        self.assertEqual(checked_external_load_scale(), 1e-5)
    def test_zero_is_unloaded_not_default(self):
        self.assertEqual(checked_external_load_scale(0),0.)
    def test_positive_scale_preserved(self):
        for x in [1e-6,1e-5,2e-5,1]:self.assertEqual(checked_external_load_scale(x),float(x))
    def test_negative_scale_rejected(self):
        with self.assertRaises(ValueError):checked_external_load_scale(-1e-10)
    def test_nonfinite_scale_rejected(self):
        for x in [float('nan'),float('inf'),float('-inf')]:
            with self.assertRaises(ValueError):checked_external_load_scale(x)
    def test_boolean_scale_rejected(self):
        for x in [True,False]:
            with self.assertRaises(ValueError):checked_external_load_scale(x)
    def test_string_scale_rejected(self):
        with self.assertRaises(ValueError):checked_external_load_scale('0')
    def test_nonscalar_scale_rejected(self):
        for x in [[0],{},np.array([0.])]:
            with self.assertRaises(ValueError):checked_external_load_scale(x)
    def test_case_matrix_preserves_four_positions_and_two_initial_states(self):
        for case in range(8):
            c,t,idx,initial=checked_study_controls(case,1e-7)
            self.assertEqual((c,t,idx,initial),(case,1e-7,case%4,0. if case<4 else 2e-4))
    def test_unloaded_scale_does_not_change_case_or_initial_force(self):
        self.assertEqual(checked_external_load_scale(0),0.)
        self.assertEqual(checked_study_controls(6,1e-7)[3],2e-4)
    def test_failed_QP_returns_false_before_field_use(self):
        tree=ast.parse((ROOT/'engineering/trace-enrichment-20261017/solve_trace_probe.py').read_text())
        candidates=[x for x in ast.walk(tree) if isinstance(x,ast.If) and ast.unparse(x.test)=="not qp['passed']"]
        self.assertEqual(len(candidates),1)
        self.assertTrue(any(isinstance(x,ast.Return) and isinstance(x.value,ast.Constant) and x.value.value is False for x in candidates[0].body))
    def test_driver_parses_optional_explicit_load_scale(self):
        s=(ROOT/'engineering/trace-enrichment-20261017/solve_trace_probe.py').read_text()
        self.assertIn("p.add_argument('--external-load-scale',type=float,default=None)",s)
        self.assertIn("P['F'][:,load_index]*external_scale",s)
