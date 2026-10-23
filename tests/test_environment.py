import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('locked_environment', ROOT / 'tools/check_environment.py')
environment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(environment)


class EnvironmentContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = '''[project]
name = "sample"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = ["direct==1.0"]
'''
        self.lock = '''version = 1
requires-python = "==3.12.*"
[[package]]
name = "sample"
version = "0.1.0"
source = { virtual = "." }
dependencies = [{ name = "direct" }]
[package.metadata]
requires-dist = [{ name = "direct", specifier = "==1.0" }]
[[package]]
name = "direct"
version = "1.0"
source = { registry = "https://pypi.org/simple" }
dependencies = [{ name = "transitive" }]
[[package]]
name = "transitive"
version = "2.0"
source = { registry = "https://pypi.org/simple" }
'''
        self.installed = {'direct': '1.0', 'transitive': '2.0'}

    def inspect(self, *, python=(3, 12, 14)):
        (self.root / 'pyproject.toml').write_text(self.project)
        (self.root / 'uv.lock').write_text(self.lock)
        return environment.inspect_environment(self.root, installed=self.installed, python_version=python)

    def test_exact_all_package_versions_pass(self):
        report = self.inspect()
        self.assertTrue(report['passed'], report)
        self.assertEqual(report['checked_package_count'], 2)
        self.assertFalse(report['installation_artifact_provenance_verified'])

    def test_missing_transitive_package_fails(self):
        del self.installed['transitive']
        self.assertFalse(self.inspect()['passed'])

    def test_transitive_version_drift_fails(self):
        self.installed['transitive'] = '2.1'
        self.assertFalse(self.inspect()['passed'])

    def test_wrong_python_fails(self):
        for python in ((3, 11, 9), (3, 13, 0)):
            self.assertFalse(self.inspect(python=python)['passed'])

    def test_stale_root_dependency_lock_fails(self):
        self.project = self.project.replace('direct==1.0', 'direct==1.1')
        self.assertFalse(self.inspect()['passed'])

    def test_project_version_drift_fails(self):
        self.project = self.project.replace('0.1.0', '0.2.0')
        self.assertFalse(self.inspect()['passed'])

    def test_resolved_version_must_satisfy_declared_dependency(self):
        self.lock = self.lock.replace('name = "direct"\nversion = "1.0"', 'name = "direct"\nversion = "9.0"')
        self.installed['direct'] = '9.0'
        self.assertFalse(self.inspect()['passed'])

    def test_current_range_and_exact_post_constraints(self):
        self.assertTrue(environment.version_matches('1.18.1', '>=1.16.2,<2'))
        self.assertFalse(environment.version_matches('2.0', '>=1.16.2,<2'))
        self.assertTrue(environment.version_matches('7.8.1.1.post1', '==7.8.1.1.post1'))
        self.assertFalse(environment.version_matches('7.8.1.1.post2', '==7.8.1.1.post1'))
        with self.assertRaises(ValueError):
            environment.version_matches('1.0rc1', '>=1.0')
        with self.assertRaises(ValueError):
            environment.version_matches('invalid', '==invalid')

    def test_missing_lock_returns_failure_receipt(self):
        result = environment.inspect_environment(self.root, installed=self.installed)
        self.assertFalse(result['passed'])
        self.assertTrue(result['errors'])

    def test_incomplete_dependency_graph_fails(self):
        self.lock = self.lock.replace('name = "transitive"\nversion', 'name = "different"\nversion')
        self.assertFalse(self.inspect()['passed'])

    def test_duplicate_locked_distribution_fails(self):
        self.lock += '\n[[package]]\nname = "direct"\nversion = "9.0"\n'
        self.assertFalse(self.inspect()['passed'])

    def test_conditional_dependency_is_not_silently_ignored(self):
        self.lock = self.lock.replace('{ name = "transitive" }', '{ name = "transitive", marker = "sys_platform == \'linux\'" }')
        self.assertFalse(self.inspect()['passed'])

    def test_url_source_is_not_treated_as_registry_version(self):
        self.lock = self.lock.replace('source = { registry = "https://pypi.org/simple" }', 'source = { url = "https://example.invalid/direct.whl" }', 1)
        self.assertFalse(self.inspect()['passed'])

    def test_root_graph_omission_fails(self):
        self.lock = self.lock.replace('dependencies = [{ name = "direct" }]', 'dependencies = []', 1)
        self.assertFalse(self.inspect()['passed'])

    def test_version_comparison_boundary_and_unknown_forms(self):
        self.assertTrue(environment.python_matches('>=3.12,<3.13', (3, 12, 99)))
        self.assertTrue(environment.python_matches('==3.12.*', (3, 12, 0)))
        self.assertFalse(environment.python_matches('==3.12.*', (3, 13, 0)))
        self.assertFalse(environment.python_matches('!=3.12.*', (3, 12, 1)))
        with self.assertRaises(ValueError):
            environment.python_matches('arbitrary', (3, 12, 0))


if __name__ == '__main__':
    unittest.main()
