"""Small persistence/identity negative controls; no native geometry is loaded."""
from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path
import tempfile
import unittest

import seating_checkpoint as journal
import check_seating_checkpoint as reader


class JournalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='razr-seating-journal-test-', dir='/tmp')
        self.folder = Path(self.temporary.name)
        self.names = ['A', 'B', 'C']
        self.sources = {'synthetic-fixture.py': 'a' * 64}
        self.identity = {'repository_head': '0' * 40, 'environment': {'passed': True}}
        self.controls = {'seconds': 1740., 'minimum_available_disk_mib': 300,
                         'maximum_rss_mib': 1536, 'maximum_pair_calls': 20000, 'maximum_subdivision_depth': 3}
        self.context = journal.context_record('0' * 40, {'synthetic_test_not_native': True},
            self.names, self.sources, self.identity, self.controls)
        self.writer = journal.PairJournal(self.folder / 'pairs.jsonl', self.context)
        self.rows = [{'a': a, 'b': b, 'disposition': 'clear', 'method': 'continuous_relative_axis_gap',
                      'gap_lower_mm': 1.} for a, b in itertools.combinations(self.names, 2)]
        self.report = {'schema': 'razr-complete-seating-native-diagnostic-v2', 'expected_head': '0' * 40,
            'domain': self.context['domain'], 'complete_participant_names': self.names,
            'participant_count': 3, 'pairs': copy.deepcopy(self.rows), 'pair_count': 3, 'expected_pair_count': 3,
            'identity_before': self.identity, 'identity_after': self.identity,
            'adapter_source_sha256_before': self.sources, 'adapter_source_sha256_after': self.sources,
            'construction_completed': True, 'native_checks_executed': True,
            'native_scene_metadata': {'synthetic_test_not_native': True}, 'native_slot_halfwidth_mm': {'L': .027, 'R': .028},
            'rigid_Z_laws': {}, 'construction_probes': [], 'execution_limits': self.controls,
            'complete_native_diagnostic_executed': True, 'whole_declared_seating_external_pair_domain_clear': True,
            'all_unordered_pairs_present_once': True, 'source_bytes_unchanged': True,
            'evaluation_failure_count': 0, 'raw_evidence_validation_failure_count': 0,
            **{key: False for key in reader.FALSE_SCOPE_FLAGS}}
        self.writer.record_construction(self.report)

    def tearDown(self):
        self.writer.close()
        self.temporary.cleanup()

    def publish_complete_synthetic(self):
        for index, row in enumerate(self.rows):
            self.writer.record_pair(index, row)
        self.writer.record_postflight(self.report)
        self.writer.publish_report(self.folder / 'report.json', self.report)
        return self.folder / 'report.json'

    def test_each_pair_visible_without_rewriting_prefix_and_partial_never_complete(self):
        before = (self.folder / 'pairs.jsonl').read_bytes()
        self.writer.record_pair(0, self.rows[0])
        after = (self.folder / 'pairs.jsonl').read_bytes()
        self.assertTrue(after.startswith(before))
        parsed = journal.read_journal(self.folder / 'pairs.jsonl', expected_context=self.context)
        self.assertEqual(parsed['raw_pairs'], self.rows[:1])
        self.assertEqual(parsed['completed_pair_records'], 1)
        self.assertFalse(parsed['complete_native_diagnostic_executed'])
        self.assertIsNone(parsed['final_commit'])
        with self.assertRaises(FileNotFoundError):
            journal.validate_published(self.folder / 'report.json', expected_context=self.context)

    def test_truncated_final_line_preserves_only_complete_prefix(self):
        self.writer.record_pair(0, self.rows[0])
        self.writer.close()
        with (self.folder / 'pairs.jsonl').open('ab') as stream:
            stream.write(b'{"unfinished_pair":')
        parsed = journal.read_journal(self.folder / 'pairs.jsonl', expected_context=self.context)
        self.assertEqual(parsed['completed_pair_records'], 1)
        self.assertGreater(parsed['truncated_tail_bytes'], 0)
        self.assertFalse(parsed['complete_native_diagnostic_executed'])
        with self.assertRaises(ValueError):
            journal.read_journal(self.folder / 'pairs.jsonl', expected_context=self.context, allow_truncated_tail=False)

    def test_completed_publication_binds_raw_rows_but_is_not_geometry_qualification(self):
        path = self.publish_complete_synthetic()
        parsed = journal.validate_published(path, expected_context=self.context)
        self.assertTrue(parsed['complete_publication_chain_verified'])
        self.assertTrue(parsed['all_expected_pair_records_present'])
        self.assertFalse(parsed['complete_native_diagnostic_executed'])
        # A complete three-pair protocol fixture cannot masquerade as the
        # original 154-material SEATING proof, even with internally valid hashes.
        with self.assertRaises(ValueError):
            reader.complete_result(parsed['report'], parsed, self.identity, self.sources)

    def test_source_domain_and_cross_run_identity_changes_are_rejected(self):
        self.writer.record_pair(0, self.rows[0])
        for field, changed in (('domain', {'synthetic_test_not_native': False}),
                               ('adapter_source_sha256_before', {'synthetic-fixture.py': 'b' * 64}),
                               ('expected_head', '1' * 40)):
            different = copy.deepcopy(self.context); different[field] = changed
            with self.subTest(field=field), self.assertRaises(ValueError):
                journal.read_journal(self.folder / 'pairs.jsonl', expected_context=different)
        self.writer.close()
        lines = (self.folder / 'pairs.jsonl').read_bytes().splitlines()
        row = json.loads(lines[-1]); row.pop('record_sha256'); row['run_id'] = 'f' * 32
        row['record_sha256'] = journal.object_sha(row)
        lines[-1] = journal.canonical(row)
        (self.folder / 'pairs.jsonl').write_bytes(b'\n'.join(lines) + b'\n')
        with self.assertRaises(ValueError):
            journal.read_journal(self.folder / 'pairs.jsonl', expected_context=self.context)

    def test_duplicate_out_of_order_and_wrong_pair_cannot_be_appended(self):
        self.writer.record_pair(0, self.rows[0])
        before = (self.folder / 'pairs.jsonl').read_bytes()
        for index, row in ((0, self.rows[0]), (2, self.rows[2]), (1, self.rows[2])):
            with self.assertRaises(ValueError):
                self.writer.record_pair(index, row)
            self.assertEqual((self.folder / 'pairs.jsonl').read_bytes(), before)

    def test_missing_atomic_index_or_modified_final_raw_evidence_fails_closed(self):
        path = self.publish_complete_synthetic()
        index = self.folder / 'checkpoint-index.json'
        index_bytes = index.read_bytes()
        index.unlink()
        with self.assertRaises(FileNotFoundError):
            journal.validate_published(path, expected_context=self.context)
        index.write_bytes(index_bytes)
        report = json.loads(path.read_text())
        report['pairs'][0]['gap_lower_mm'] = -1.
        path.write_text(json.dumps(report))
        with self.assertRaises(ValueError):
            journal.validate_published(path, expected_context=self.context)

    def test_budget_and_error_payloads_are_retained_and_partial_seal_stays_incomplete(self):
        raw = {**self.rows[0], 'prior_attempt': {'disposition': 'unresolved_evaluation', 'error': 'retained native error'}}
        self.writer.record_pair(0, raw)
        interrupted = {**self.rows[1], 'disposition': 'unresolved_budget',
                       'completed_regions_in_interrupted_frame': [{'cage': 'actual-region-1',
                          'disposition': 'clear', 'common_upper_bound_mm3': 0.}]}
        self.writer.record_interruption('original wall-time budget', interrupted)
        report = self.report
        report['pairs'] = [raw, interrupted, {**self.rows[2], 'disposition': 'unresolved_budget'}]
        report['resource_stop'] = 'original wall-time budget'
        report['complete_native_diagnostic_executed'] = False
        report['whole_declared_seating_external_pair_domain_clear'] = False
        self.writer.record_postflight(report)
        self.writer.publish_report(self.folder / 'report.json', report)
        parsed = journal.validate_published(self.folder / 'report.json', expected_context=self.context)
        self.assertFalse(parsed['all_expected_pair_records_present'])
        self.assertFalse(parsed['complete_native_diagnostic_executed'])
        self.assertEqual(parsed['journal']['raw_pairs'][0]['prior_attempt']['error'], 'retained native error')
        self.assertEqual(parsed['journal']['interruption']['raw_interrupted_pair'], interrupted)
        self.assertGreater(reader.recursive_pending(report['pairs']), 0)


class NativeMetadataNegativeControls(unittest.TestCase):
    """Synthetic source-owned metadata; these fixtures claim no CAD execution."""
    def setUp(self):
        names = reader.worker.expected_inventory()
        self.laws = reader.domain.rigid_laws(names, {'L': .027, 'R': .028}, names)
        probes = []
        for descent in (reader.F('2.6'), reader.F('4.1'), reader.F('8.2')):
            vertices = reader.domain.joints_at(descent)
            probes.append({'descent_mm': float(descent),
                'joints_by_side_mm': {'L': list(map(float, vertices[0])), 'R': list(map(float, vertices[-1]))},
                'flanks': [-.4, .65], 'rigid_materials_checked': len(self.laws),
                'maximum_bidirectional_material_difference_mm3': 0.,
                'complete_factory_reconstructed_including_both_flexible_bodies': True,
                'samples_do_not_establish_continuous_law': True})
        self.scene = {
            'factory': 'integration/product_split_assembly.py:split_scene',
            'parent_factory': 'integration/product_assembly.py:product_scene',
            'slide_mm': 79.75, 'descent_mm': 0., 'left_tab_mm': 3., 'right_tab_mm': 3.,
            'slot_flanks': [0., 0.], 'KEY_offsets_mm': [0., 0.], 'crosshead_offsets_mm': [0., 0.],
            'telescope_offsets_by_side_mm': {side: [float(reader.domain.REFERENCE_JOINT)] * 3 for side in 'LR'},
            'telescope_allocation': 'explicit admissible joint allocation',
            'B_translation_mm': [0., 79.75, 8.2], 'installed_mechanical_parts': 108,
            'expected_scene_participants': 108, 'OPEN_hold_screws_installed': False,
            'OPEN_display_support_insert_installed': False,
            **{key: False for key in reader.SCENE_FALSE_FLAGS}}
        self.report = {'construction_completed': True, 'native_checks_executed': True,
            'construction_probes': probes, 'native_scene_metadata': {
                'combined_participants': 154, 'mechanical_participants': 108,
                'candidate_participants': 41, 'scene': self.scene}}

    def test_actual_reference_controls_required_and_bool_nonfinite_rejected(self):
        reader.construction_valid(self.report, self.laws)
        changes = [('descent_mm', False), ('descent_mm', float('nan')),
            ('slide_mm', float('inf')), ('left_tab_mm', 0.), ('right_tab_mm', 2.9),
            ('slot_flanks', [1., -1.]), ('slot_flanks', [False, 0.]),
            ('KEY_offsets_mm', [.03, 0.]), ('crosshead_offsets_mm', [0., .02]),
            ('B_translation_mm', [0., 79.75, 0.]), ('B_translation_mm', [False, 79.75, 8.2]),
            ('telescope_offsets_by_side_mm', {'L': [.1] * 3, 'R': [.1] * 3}),
            ('telescope_offsets_by_side_mm', {'L': [float(reader.domain.REFERENCE_JOINT)] * 3}),
            ('telescope_offsets_by_side_mm', {'L': [float('nan')] * 3, 'R': [float(reader.domain.REFERENCE_JOINT)] * 3}),
            ('telescope_allocation', 'nominal equal allocation, not physically enforced')]
        for key, value in changes:
            changed = copy.deepcopy(self.report)
            changed['native_scene_metadata']['scene'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                reader.construction_valid(changed, self.laws)
        changed = copy.deepcopy(self.report)
        changed['construction_probes'][0]['maximum_bidirectional_material_difference_mm3'] = False
        with self.assertRaises(ValueError):
            reader.construction_valid(changed, self.laws)

    def test_factory_scope_flags_must_remain_actual_false(self):
        for key in reader.SCENE_FALSE_FLAGS:
            for value in (True, 0, None):
                changed = copy.deepcopy(self.report)
                changed['native_scene_metadata']['scene'][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    reader.construction_valid(changed, self.laws)

    def test_complete_payload_set_sha_and_no_overlay_are_required(self):
        current = {'head_bound_source_sha256': {
            'engineering/panel/native-templates.tar.gz': 'a' * 64,
            'engineering/pawl/geometry-manifest.json': 'b' * 64,
            'engineering/thin/native-verification.json.gz': 'c' * 64,
            'engineering/panel/generator.py': 'd' * 64}}
        scene = {'archive': 'engineering/panel/native-templates.tar.gz', 'archive_sha256': 'a' * 64,
            'source_inputs': {'engineering/pawl/geometry-manifest.json': 'b' * 64,
                              'engineering/thin/native-verification.json.gz': 'c' * 64}}
        reader.factory_payload_valid(scene, current)
        missing = copy.deepcopy(scene)
        missing['source_inputs'].pop('engineering/thin/native-verification.json.gz')
        bad_sha = copy.deepcopy(scene)
        bad_sha['source_inputs']['engineering/pawl/geometry-manifest.json'] = 'f' * 64
        extra = copy.deepcopy(scene)
        extra['source_inputs']['engineering/unaccounted.json'] = 'e' * 64
        overlay = copy.deepcopy(scene)
        overlay['external_verified_source_inputs'] = {'/tmp/synthetic-overlay.step': 'f' * 64}
        for changed in (missing, bad_sha, extra, overlay):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                reader.factory_payload_valid(changed, current)


if __name__ == '__main__':
    unittest.main(verbosity=2)
