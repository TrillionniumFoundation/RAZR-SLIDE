"""Synthetic provider records exercise false-pass and replay boundaries."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('actions_inspection', ROOT / 'tools/inspect_actions_run.py')
actions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(actions)
HEAD = 'a' * 40


class ActionsInspectionTests(unittest.TestCase):
    def setUp(self):
        self.run = {'id': 1, 'head_sha': HEAD, 'run_attempt': 1, 'status': 'completed', 'conclusion': 'success'}
        self.jobs = [{'id': 2, 'name': 'unit', 'head_sha': HEAD, 'run_attempt': 1,
                      'status': 'completed', 'conclusion': 'success',
                      'created_at': '2026-10-19T00:00:00Z', 'completed_at': '2026-10-19T00:00:01Z',
                      'steps': [{'name': 'Run unit suites', 'started_at': '2026-10-19T00:00:00Z', 'conclusion': 'success'}]}]

    def report(self, annotations=None, expected=HEAD):
        return actions.summarize(self.run, self.jobs, annotations or {}, expected)

    def test_real_execution_records_required(self):
        self.assertTrue(self.report()['successful_hosted_report'])
        self.jobs[0]['steps'] = []
        self.assertFalse(self.report()['successful_hosted_report'])

    def test_missing_jobs_is_not_success(self):
        self.jobs = []
        self.assertFalse(self.report()['successful_hosted_report'])

    def test_requested_head_and_all_job_heads_must_match(self):
        self.assertFalse(self.report(expected='b' * 40)['successful_hosted_report'])
        self.jobs[0]['head_sha'] = 'b' * 40
        self.assertFalse(self.report()['successful_hosted_report'])

    def test_skipped_or_queued_step_is_not_execution(self):
        self.jobs[0]['steps'][0]['conclusion'] = 'skipped'
        self.assertFalse(self.report()['successful_hosted_report'])
        self.jobs[0]['steps'][0]['conclusion'] = None
        self.assertFalse(self.report()['successful_hosted_report'])

    def test_failure_is_not_turned_into_pass(self):
        self.run['conclusion'] = 'failure'
        self.assertFalse(self.report()['successful_hosted_report'])
        self.run['conclusion'] = 'success'
        self.jobs[0]['conclusion'] = 'failure'
        self.assertFalse(self.report()['successful_hosted_report'])

    def test_inherited_completion_does_not_mean_fresh_full_run(self):
        self.jobs[0]['created_at'] = '2026-10-19T01:00:00Z'
        report = self.report()
        self.assertEqual(report['inherited_job_result_ids'], [2])
        self.assertFalse(report['one_fresh_attempt_executed_all_jobs'])

    def test_billing_reason_requires_provider_annotation(self):
        self.assertEqual(self.report()['billing_block_job_ids'], [])
        report = self.report({'2': [{'message': 'The job was not started because recent account payments have failed or your spending limit needs to be increased.'}]})
        self.assertEqual(report['billing_block_job_ids'], [2])

    def test_duplicate_job_and_short_identity_rejected(self):
        with self.assertRaises(ValueError):
            self.report(expected='aaa')
        self.jobs.append(copy.deepcopy(self.jobs[0]))
        with self.assertRaises(ValueError):
            self.report()


if __name__ == '__main__':
    unittest.main()
