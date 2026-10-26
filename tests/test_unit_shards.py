import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('unit_shards', ROOT / 'tools/aggregate_unit_shards.py')
shards = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(shards)


class UnitShardCoverageTests(unittest.TestCase):
    def setUp(self):
        self.head = 'a' * 40
        self.sources = {'tools/verify.py': 'b' * 64}
        self.config = {'minimum_total_tests': 2, 'suites': [
            {'id': 'first', 'directory': 'tests/first', 'minimum_tests': 1},
            {'id': 'second', 'directory': 'tests/second', 'minimum_tests': 1}]}
        self.kwargs = {'expected_head': self.head, 'manifest_sha256': 'manifest',
                       'lock_sha256': 'lock', 'project_sha256': 'project',
                       'locked_packages': {'package': '1.0'}, 'python_constraint': '==3.12.*',
                       'expected_sources': self.sources, 'run_id': '123', 'run_attempt': '1'}
        self.reports = [self.report(name) for name in ('first', 'second')]

    def report(self, name):
        row = {'id': name, 'passed': True, 'exit_code': 0, 'tests_run': 1, 'test_ids': ['tests.case'],
               'minimum_tests': 1, 'failures': 0, 'errors': 0, 'skipped': 0,
               'expected_failures': 0, 'unexpected_successes': 0,
               'command': ['/repo/.venv/bin/python', '-B', '/repo/tools/run_suite.py',
                           '--directory', '/repo/tests/' + name, '--minimum', '1',
                           '--report', '/output/' + name + '.json']}
        return {'schema': 'razr-unit-execution-v2', 'scope': 'selected',
                'selected_suite_ids': [name], 'suite_results': [row], 'tests_run': 1,
                'configured_minimum_tests': 1, 'expected_head': self.head,
                'repository_root': '/repo', 'output_directory': '/output', 'python_executable': '/repo/.venv/bin/python',
                'base_commit': self.head, 'source_head_after': self.head,
                'github_run_id': '123', 'github_run_attempt': '1', 'github_job': 'unit-shard',
                'runner_name': 'hosted', 'passed': True, 'execution_completed': True,
                'environment_verified': True, 'source_identity_verified': True,
                'source_bytes_unchanged': True, 'present_tracked_bytes_match_head': True,
                'diagnostic_unlocked': False, 'syntax_errors': [], 'changed_during_tests': [],
                'candidate_go': False, 'manufacturing_go': False, 'hardware_qualification': False,
                'full_motion_reexecuted': False, 'native_KiCad_reexecuted': False,
                'suite_manifest_sha256': 'manifest', 'uv_lock_sha256': 'lock', 'pyproject_sha256': 'project',
                'source_hashes_before': self.sources.copy(), 'source_hashes_after': self.sources.copy(),
                'environment': {'passed': True, 'uv_lock_sha256': 'lock', 'pyproject_sha256': 'project',
                    'errors': [], 'python_version': '3.12.14', 'checked_package_count': 1,
                    'checked_packages': {'package': {'expected': '1.0', 'observed': '1.0', 'matches': True}}}}

    def aggregate(self):
        return shards.aggregate(self.config, self.reports, **self.kwargs)

    def test_complete_exact_run_passes(self):
        result = self.aggregate()
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['tests_run'], 2)
        self.assertFalse(result['manufacturing_go'])

    def test_missing_suite_is_failure(self):
        self.reports.pop()
        self.assertFalse(self.aggregate()['passed'])

    def test_duplicate_cannot_replace_missing_suite(self):
        self.reports[1] = copy.deepcopy(self.reports[0])
        self.assertFalse(self.aggregate()['passed'])

    def test_stale_commit_is_failure(self):
        self.reports[0]['base_commit'] = 'c' * 40
        self.assertFalse(self.aggregate()['passed'])

    def test_another_attempt_is_failure(self):
        self.reports[0]['github_run_attempt'] = '2'
        self.assertFalse(self.aggregate()['passed'])

    def test_manifest_lock_or_project_mismatch_is_failure(self):
        for key in ('suite_manifest_sha256', 'uv_lock_sha256', 'pyproject_sha256'):
            old = self.reports[0][key]
            self.reports[0][key] = 'stale'
            self.assertFalse(self.aggregate()['passed'], key)
            self.reports[0][key] = old

    def test_wrong_scope_is_failure(self):
        self.reports[0]['scope'] = 'all_current_unit_suites'
        self.assertFalse(self.aggregate()['passed'])

    def test_source_mutation_is_failure_even_if_boolean_claims_pass(self):
        self.reports[0]['source_hashes_after']['tools/verify.py'] = 'different'
        self.assertFalse(self.aggregate()['passed'])

    def test_package_drift_is_failure_even_if_environment_claims_pass(self):
        self.reports[0]['environment']['checked_packages']['package']['observed'] = '2.0'
        self.assertFalse(self.aggregate()['passed'])

    def test_missing_transitive_package_is_failure(self):
        self.reports[0]['environment']['checked_packages'] = {}
        self.assertFalse(self.aggregate()['passed'])

    def test_missing_actual_test_is_failure(self):
        self.reports[0]['suite_results'][0]['test_ids'] = []
        self.assertFalse(self.aggregate()['passed'])

    def test_duplicate_directory_cannot_masquerade_as_two_suites(self):
        self.reports[1]['suite_results'][0]['command'][4] = '/repo/tests/first'
        self.assertFalse(self.aggregate()['passed'])

    def test_worker_command_and_report_path_are_bound(self):
        command = self.reports[0]['suite_results'][0]['command']
        for index, replacement in ((0, '/wrong/python'), (2, '/wrong/run_suite.py'),
                                   (4, '/repo/tests/second'), (6, '0'), (8, '/output/second.json')):
            saved = command[index]
            command[index] = replacement
            self.assertFalse(self.aggregate()['passed'], index)
            command[index] = saved
        self.config['suites'][0]['extra_paths'] = ['engineering/source']
        self.assertFalse(self.aggregate()['passed'])
        command.extend(['--extra-path', '/repo/engineering/source'])
        self.assertTrue(self.aggregate()['passed'])

    def test_malformed_suite_identity_is_a_failed_receipt(self):
        self.reports[0]['selected_suite_ids'] = [{'bad': 'identity'}]
        self.assertFalse(self.aggregate()['passed'])

    def test_duplicate_test_ids_is_failure(self):
        report = self.reports[0]
        report['tests_run'] = 2
        report['suite_results'][0].update(tests_run=2, test_ids=['same', 'same'])
        self.assertFalse(self.aggregate()['passed'])

    def test_skips_errors_or_timeout_cannot_pass(self):
        row = self.reports[0]['suite_results'][0]
        for key in ('skipped', 'errors', 'failures', 'expected_failures', 'unexpected_successes'):
            row[key] = 1
            self.assertFalse(self.aggregate()['passed'], key)
            row[key] = 0
        row['exit_code'] = 'TIMEOUT'
        self.assertFalse(self.aggregate()['passed'])

    def test_boolean_test_count_is_not_an_integer_count(self):
        self.reports[0]['suite_results'][0]['tests_run'] = True
        self.assertFalse(self.aggregate()['passed'])

    def test_diagnostic_and_hardware_overclaims_are_rejected(self):
        for key in ('diagnostic_unlocked', 'manufacturing_go', 'hardware_qualification'):
            self.reports[0][key] = True
            self.assertFalse(self.aggregate()['passed'], key)
            self.reports[0][key] = False

    def test_matrix_uses_every_manifest_suite(self):
        self.assertEqual(shards.matrix(self.config), {'include': [{'id': 'first'}, {'id': 'second'}]})
        self.config['suites'][0]['id'] = '../escape'
        with self.assertRaises(ValueError):
            shards.matrix(self.config)


if __name__ == '__main__':
    unittest.main()
