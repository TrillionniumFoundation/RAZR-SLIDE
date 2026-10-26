"""Small interruption/tamper counterexamples for the durable raw evidence path.

These fixtures do not contain native geometry and never qualify a SLIDE domain.
"""
from __future__ import annotations

import copy
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import slide_checkpoint as c
import check_slide_checkpoint as reader


class CheckpointDurabilityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='razr-slide-checkpoint-unit-')
        self.folder = Path(self.temporary.name)
        self.path = self.folder/'report.json'
        self.names = ['A', 'B', 'C']
        self.order = [2, 0, 1]
        self.context = c.context_record('synthetic-head', {'q': ['0', '12']}, self.names, self.order,
            {'synthetic-source': 'a'*64}, {'synthetic': True},
            reader.worker.execution_limits(2), self.path.name)
        self.report = {'identity_before': self.context['identity_before'],
            'scratch_source_sha256_before': self.context['scratch_source_sha256_before'],
            'domain': self.context['domain'], 'execution_limits': self.context['execution_limits'],
            'native_checks_executed': True, 'construction_probes_complete': True,
            'execution_completed': False, 'complete_native_diagnostic_executed': False,
            'whole_declared_slide_external_pair_domain_clear': False,
            'pairs': [{'a': a, 'b': b, 'pair_class': 'rigid_rigid', 'disposition': 'not_evaluated'}
                      for a, b in itertools.combinations(self.names, 2)]}
        self.journal = None

    def tearDown(self):
        if self.journal is not None:
            self.journal.close()
        self.temporary.cleanup()

    def begin(self):
        self.journal = c.PairJournal(self.folder/'pairs.jsonl', self.context)
        self.journal.record_construction(self.report)
        return self.journal

    def complete(self, index, **changes):
        row = self.report['pairs'][index]
        self.journal.record_start(index, row)
        row.update(disposition='unresolved_conservative_overlap', recorded_raw_index=index, **changes)
        self.journal.record_complete(index, row)

    def finish(self):
        self.journal.record_postflight(self.report)
        self.journal.publish_report(self.path, self.report)

    def full_fixture(self):
        self.begin()
        for i in self.order:
            self.complete(i)
        self.report['execution_completed'] = True
        self.finish()

    def records(self):
        return [c.parse(line) for line in (self.folder/'pairs.jsonl').read_bytes().splitlines()]

    def rewrite(self, records, change_context=False):
        previous = None
        raw = []
        context_sha = c.object_sha(records[0]['payload'])
        for i, original in enumerate(records):
            row = copy.deepcopy(original)
            row.pop('record_sha256')
            row['sequence'], row['previous_record_sha256'] = i, previous
            if change_context:
                row['context_sha256'] = context_sha
            previous = c.object_sha(row)
            raw.append(c.canonical({**row, 'record_sha256': previous}) + b'\n')
        (self.folder/'pairs.jsonl').write_bytes(b''.join(raw))

    def test_actual_abrupt_process_exit_retains_complete_prefix_and_active_start(self):
        source = str(Path(c.__file__).resolve().parent)
        specification = self.folder/'fixture.json'
        specification.write_bytes(c.canonical({'context': self.context, 'report': self.report}))
        program = '''import json,os,sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import slide_checkpoint as c
f=Path(sys.argv[2]); x=json.loads((f/'fixture.json').read_text())
j=c.PairJournal(f/'pairs.jsonl',x['context']); r=x['report']; j.record_construction(r)
j.record_start(2,r['pairs'][2]); r['pairs'][2]['disposition']='unresolved_conservative_overlap'
j.record_complete(2,r['pairs'][2]); j.record_start(0,r['pairs'][0]); os._exit(23)
'''
        result = subprocess.run([sys.executable, '-B', '-c', program, source, str(self.folder)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 23, result.stderr)
        prefix = c.read_journal(self.folder/'pairs.jsonl', self.context)
        self.assertEqual(prefix['completed_pair_records'], 1)
        self.assertEqual(prefix['active_pair_start']['raw_pair_index'], 0)
        self.assertEqual(prefix['completed_pairs'][0]['raw_pair_index'], 2)
        self.assertIsNone(prefix['postflight'])
        self.assertFalse(prefix['complete_native_diagnostic_executed'])
        self.assertFalse((self.folder/'checkpoint-index.json').exists())

    def test_torn_tail_keeps_only_intact_completions_and_active_pair(self):
        self.begin(); self.complete(2)
        self.journal.record_start(0, self.report['pairs'][0]); self.journal.close()
        fragment = b'{"schema":"razr-slide-pair-journal-r3","sequence":'
        with (self.folder/'pairs.jsonl').open('ab') as stream:
            stream.write(fragment)
        prefix = c.read_journal(self.folder/'pairs.jsonl', self.context)
        self.assertEqual(prefix['completed_pair_records'], 1)
        self.assertEqual(prefix['truncated_tail_bytes'], len(fragment))
        self.assertEqual(prefix['active_pair_start']['raw_pair_index'], 0)
        self.assertFalse(prefix['complete_native_diagnostic_executed'])
        with self.assertRaisesRegex(ValueError, 'truncated'):
            c.read_journal(self.folder/'pairs.jsonl', self.context, allow_truncated_tail=False)

    def test_full_nonlex_visit_order_binds_original_raw_indices_without_qualifying_geometry(self):
        self.full_fixture()
        result = c.validate_published(self.path, self.context)
        self.assertEqual([v['raw_pair_index'] for v in result['journal']['completed_pairs']], self.order)
        self.assertEqual([v['recorded_raw_index'] for v in result['report']['pairs']], [0, 1, 2])
        self.assertTrue(result['all_expected_pair_records_present'])
        self.assertFalse(result['complete_native_diagnostic_executed'])
        with patch.object(reader, 'source_state', return_value=(self.context['scratch_source_sha256_before'],
                                                              self.context['identity_before'])), \
             patch.object(reader, 'expected_context', return_value=self.context), \
             patch.object(reader.original_reader, 'check', return_value={
                 'report_sha256': c.sha(self.path),
                 'complete_native_diagnostic_executed': False,
                 'whole_declared_slide_external_pair_domain_clear': False}) as original:
            checked = reader.check_report(self.path, 'synthetic-head')
            self.assertTrue(checked['checkpoint_publication_chain_verified'])
            self.assertFalse(checked['complete_native_diagnostic_executed'])
            self.assertFalse(checked['resume_certificate'])
            original.assert_called_once()
            prefix = reader.inspect_prefix(self.folder/'pairs.jsonl', 'synthetic-head')
            self.assertEqual(prefix['completed_pair_records'], 3)
            self.assertTrue(prefix['final_commit_record_present'])
            self.assertFalse(prefix['complete_native_diagnostic_executed'])
            self.assertFalse(prefix['resume_certificate'])

    def test_semantic_loss_duplicate_and_reordering_rejected_even_after_chain_rehash(self):
        self.begin(); self.complete(2); self.complete(0); self.journal.close()
        original = self.records()
        # Header, construction, start2, complete2, start0, complete0.
        variants = [original[:2]+original[3:], original[:4]+[original[3]]+original[4:],
                    original[:3]+[original[5], original[4], original[3]]]
        for records in variants:
            with self.subTest(records=[v['kind'] for v in records]):
                self.rewrite(records)
                with self.assertRaises(ValueError):
                    c.read_journal(self.folder/'pairs.jsonl', self.context)

    def test_cross_run_source_and_domain_changes_rejected(self):
        self.begin(); self.complete(2); self.journal.close()
        original = self.records()
        cross = copy.deepcopy(original); cross[-1]['run_id'] = '1'*32
        self.rewrite(cross)
        with self.assertRaisesRegex(ValueError, 'cross-run'):
            c.read_journal(self.folder/'pairs.jsonl', self.context)
        for field, value in [('domain', {'q': ['0', '11']}),
                             ('scratch_source_sha256_before', {'synthetic-source': 'b'*64})]:
            changed = copy.deepcopy(original); changed[0]['payload'][field] = value
            self.rewrite(changed, change_context=True)
            with self.assertRaisesRegex(ValueError, 'context differs'):
                c.read_journal(self.folder/'pairs.jsonl', self.context)

    def test_missing_index_changed_report_and_changed_index_fail_closed(self):
        self.full_fixture()
        index_path = self.folder/'checkpoint-index.json'
        saved_index, saved_report = index_path.read_bytes(), self.path.read_bytes()
        index_path.unlink()
        with self.assertRaises(FileNotFoundError):
            c.validate_published(self.path, self.context)
        index_path.write_bytes(saved_index)
        report = c.parse(saved_report); report['pairs'][2]['disposition'] = 'clear'
        self.path.write_bytes(c.canonical(report))
        with self.assertRaisesRegex(ValueError, 'actual full report'):
            c.validate_published(self.path, self.context)
        self.path.write_bytes(saved_report)
        index = c.parse(saved_index); index['completed_pair_records'] = 2
        index_path.write_bytes(c.canonical(index))
        with self.assertRaisesRegex(ValueError, 'index differs'):
            c.validate_published(self.path, self.context)

    def test_budget_and_raw_error_records_survive_partial_publication(self):
        self.begin(); self.complete(2, error='synthetic native operator error')
        self.journal.record_start(0, self.report['pairs'][0])
        self.report['pairs'][0].update(disposition='unresolved_budget',
            children=[{'disposition': 'unresolved_error', 'error': 'synthetic child failure'}])
        self.report['terminal_failure'] = 'BudgetExceeded: synthetic fixed original bound'
        self.journal.record_interruption(self.report['terminal_failure'], self.report['pairs'][0])
        self.finish()
        result = c.validate_published(self.path, self.context)
        self.assertFalse(result['all_expected_pair_records_present'])
        self.assertFalse(result['complete_native_diagnostic_executed'])
        self.assertEqual(result['journal']['completed_pairs'][0]['raw_evidence']['error'],
                         'synthetic native operator error')
        self.assertEqual(result['journal']['interruption']['raw_interrupted_pair'], self.report['pairs'][0])

    def test_incomplete_journal_cannot_publish_spoofed_completion(self):
        self.begin(); self.complete(2)
        self.report.update(complete_native_diagnostic_executed=True,
                           whole_declared_slide_external_pair_domain_clear=True)
        self.journal.record_postflight(self.report)
        with self.assertRaisesRegex(ValueError, 'incomplete journal'):
            self.journal.publish_report(self.path, self.report)
        prefix = c.read_journal(self.folder/'pairs.jsonl', self.context)
        self.assertFalse(prefix['complete_native_diagnostic_executed'])
        self.assertIsNone(prefix['final_commit'])

    def test_interruption_between_full_report_and_index_is_not_complete(self):
        self.begin()
        for i in self.order:
            self.complete(i)
        self.journal.record_postflight(self.report)
        with patch.object(c, 'atomic_bytes', side_effect=OSError('synthetic index write loss')):
            with self.assertRaises(OSError):
                self.journal.publish_report(self.path, self.report)
        prefix = c.read_journal(self.folder/'pairs.jsonl', self.context)
        self.assertIsNotNone(prefix['final_commit'])
        self.assertFalse(prefix['complete_native_diagnostic_executed'])
        with self.assertRaises(FileNotFoundError):
            c.validate_published(self.path, self.context)

    def test_valid_full_chain_cannot_override_original_raw_reader_rejection(self):
        self.begin()
        for i in self.order:
            self.complete(i)
        self.report.update(execution_completed=True, complete_native_diagnostic_executed=True,
                           whole_declared_slide_external_pair_domain_clear=True)
        self.finish()
        with patch.object(reader, 'source_state', return_value=(self.context['scratch_source_sha256_before'],
                                                              self.context['identity_before'])), \
             patch.object(reader, 'expected_context', return_value=self.context), \
             patch.object(reader.original_reader, 'check', return_value={
                 'report_sha256': c.sha(self.path),
                 'complete_native_diagnostic_executed': False,
                 'whole_declared_slide_external_pair_domain_clear': False}):
            with self.assertRaisesRegex(ValueError, 'producer completion/clear claim differs'):
                reader.check_report(self.path, 'synthetic-head')

    def test_post_validation_report_or_index_edit_cannot_rebaseline_the_chain(self):
        self.full_fixture()
        index = self.folder/'checkpoint-index.json'
        saved = {self.path: self.path.read_bytes(), index: index.read_bytes()}
        validate = c.validate_published
        for altered in (self.path, index):
            with self.subTest(changed_file=altered.name):
                for path, raw in saved.items():
                    path.write_bytes(raw)
                def change_after_validation(path, context):
                    bound = validate(path, context)
                    edited = c.parse(altered.read_bytes())
                    edited['unbound_post_validation_note'] = 'synthetic injected edit'
                    altered.write_bytes(c.canonical(edited))
                    return bound
                def raw_result(path, head):
                    return {'report_sha256': c.sha(path), 'complete_native_diagnostic_executed': False,
                            'whole_declared_slide_external_pair_domain_clear': False}
                with patch.object(reader, 'source_state', return_value=(self.context['scratch_source_sha256_before'],
                                                                      self.context['identity_before'])), \
                     patch.object(reader, 'expected_context', return_value=self.context), \
                     patch.object(c, 'validate_published', side_effect=change_after_validation), \
                     patch.object(reader.original_reader, 'check', side_effect=raw_result):
                    with self.assertRaises(ValueError):
                        reader.check_report(self.path, 'synthetic-head')


if __name__ == '__main__':
    unittest.main()
