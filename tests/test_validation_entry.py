import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

worker = module('validation_worker', 'tools/run_suite.py')
verify = module('validation_driver', 'tools/verify.py')

class ValidationEntryTests(unittest.TestCase):
    def result(self, count=1):
        r = unittest.TestResult()
        r.testsRun = count
        return r

    def test_zero_discovery_is_failure(self):
        self.assertFalse(worker.acceptable(self.result(0), 1))

    def test_missing_expected_tests_is_failure(self):
        self.assertFalse(worker.acceptable(self.result(2), 3))

    def test_import_error_is_failure(self):
        r = self.result(); r.errors.append(('test', 'ImportError'))
        self.assertFalse(worker.acceptable(r, 1))

    def test_skip_is_not_pass(self):
        r = self.result(); r.skipped.append(('test', 'dependency absent'))
        self.assertFalse(worker.acceptable(r, 1))

    def test_expected_failure_cannot_hide_failed_case(self):
        r = self.result(); r.expectedFailures.append(('test', 'expected'))
        self.assertFalse(worker.acceptable(r, 1))

    def test_positive_complete_suite(self):
        self.assertTrue(worker.acceptable(self.result(5), 5))

    def test_nonpositive_or_boolean_count_invalid(self):
        for n in (0, -1, True):
            self.assertFalse(worker.acceptable(self.result(10), n))

    def test_output_cannot_replace_immutable_evidence(self):
        for name in ('archive', 'engineering', 'baselines', 'docs', 'integration', '.git', '.venv'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                verify.output_location(ROOT, ROOT / name / 'generated')
        self.assertEqual(verify.output_location(ROOT, ROOT / '.runs' / 'new'), ROOT / '.runs' / 'new')


class ManifestTests(unittest.TestCase):
    def manifest(self):
        return {"suites": [{"id": "one", "minimum_tests": 2}], "minimum_total_tests": 2}

    def test_matching_total_accepted(self):
        verify.validate_manifest(self.manifest())

    def test_missing_suite_cannot_keep_larger_declared_total(self):
        m=self.manifest();m["minimum_total_tests"]=5
        with self.assertRaises(ValueError):verify.validate_manifest(m)

    def test_duplicate_or_empty_suite_set_rejected(self):
        for suites in ([], [{"id":"one","minimum_tests":1}]*2):
            m=self.manifest();m["suites"]=suites
            with self.assertRaises(ValueError):verify.validate_manifest(m)

    def test_invalid_or_boolean_minimum_rejected(self):
        for n in (True,0,-1,1.5):
            m=self.manifest();m["suites"][0]["minimum_tests"]=n
            with self.assertRaises(ValueError):verify.validate_manifest(m)


class OutputAliasTests(unittest.TestCase):
    def test_symlinked_protected_tree_rejected_through_both_names(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            base=Path(td).resolve();root=base/'repo';root.mkdir()
            actual=base/'shared-env';actual.mkdir()
            (root/'.venv').symlink_to(actual,target_is_directory=True)
            for p in (root/'.venv'/'new',actual/'new'):
                with self.assertRaises(ValueError):verify.output_location(root,p)
            self.assertEqual(verify.output_location(root,base/'results'),base/'results')
