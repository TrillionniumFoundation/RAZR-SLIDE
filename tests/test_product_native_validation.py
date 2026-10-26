"""Guard against omitted scenes, stale evidence and false native CI passes."""
import copy
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('product_native_validation', ROOT/'tools/verify_product_native.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
HEAD = 'a'*40
SOURCES = {name: 'f'*64 for name in native.NATIVE_SOURCE_FILES}


def pairs(names):
    rows = [{'a': a, 'b': b, 'common_mm3': 0., 'rejected': False} for a, b in sorted(names)]
    return {'rows': rows, 'pair_count': len(rows), 'failures': [],
            'no_Common_above_tolerance_or_evaluation_error': True,
            'all_positive_Common_artifact_diagnostics_complete': True}


def fixture():
    local = {f'part{i}': {} for i in range(20)}
    ends = {end: {end+'_'+n for n in local} for end in ('A', 'B')}
    candidates = ends['A'] | ends['B'] | {'EP4_finite_material'}
    report = {'schema': 'razr-ep4-bounded-native-v1', 'source_commit': HEAD,
        'source_sha256': SOURCES.copy(), 'source_bytes_unchanged': True,
        'native_checks_executed': True, 'selected_poses': list(native.POSES),
        'endpoint_exports': {end: {'parts': copy.deepcopy(local)} for end in ends},
        'endpoint_self_checks': {end: pairs(itertools.combinations(sorted(names), 2)) for end, names in ends.items()},
        'poses': [], 'geometric_rejection_found': False, **{k: False for k in native.NATIVE_GO_KEYS}}
    for label, (external_count, total) in native.POSES.items():
        external = {f'external{i}' for i in range(external_count)}
        report['poses'].append({'pose': label, 'candidate_participants': 41,
            'external_participants': external_count, 'combined_participants': total,
            'parts': {n: {} for n in candidates | external},
            'all_assembly_source_parts_have_native_bounds_and_volume': True,
            'external': pairs(itertools.product(candidates, external)),
            'A_to_B_endpoints': pairs(itertools.product(ends['A'], ends['B'])),
            'material_to_all_40_endpoint_parts': pairs(('EP4_finite_material', n) for n in ends['A'] | ends['B']),
            'containment': {'parts': 41, 'rows': [{'part': n, 'outside_outer_union_mm3': 0., 'rejected': False}
                for n in sorted(candidates)], 'failures': [], 'all_material_inside_optimistic_outer_union': True},
            'decisive_geometric_rejection_or_evaluation_failure': False,
            'all_declared_checks_clear_at_this_finite_pose': True})
    return report


def retain_collision(report):
    pose = report['poses'][0]
    group = pose['external']
    row = group['rows'][0]
    row.update(common_mm3=.25, rejected=True, artifact_diagnostics_complete=True,
               common_material={'file': 'Common.step'}, local_material_context={'file': 'context.step'})
    group['failures'] = [row]
    group['no_Common_above_tolerance_or_evaluation_error'] = False
    pose['decisive_geometric_rejection_or_evaluation_failure'] = True
    pose['all_declared_checks_clear_at_this_finite_pose'] = False
    report['geometric_rejection_found'] = True


class ProductNativeValidationTests(unittest.TestCase):
    def setUp(self):
        self.report = fixture()

    def validate(self):
        return native.validate_native(self.report, HEAD, SOURCES)

    def hidden_source_change(self, flag):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in (native.GENERATOR, native.READER):
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('# original temporary identity fixture\n')
            def git(*args):
                return subprocess.check_output(['git', '-C', str(root),
                    '-c', 'user.name=Synthetic identity test',
                    '-c', 'user.email=synthetic@example.invalid',
                    '-c', 'commit.gpgsign=false', *args], text=True, stderr=subprocess.STDOUT).strip()
            git('init', '-q'); git('add', '.'); git('commit', '-qm', 'Synthetic identity fixture', '--no-verify')
            snapshot = native.source_snapshot(root)
            self.assertEqual(snapshot[native.GENERATOR], native.sha(root/native.GENERATOR))
            git('update-index', flag, native.GENERATOR)
            (root/native.GENERATOR).write_text('# changed bytes outside the actual commit\n')
            self.assertEqual(git('status', '--porcelain'), '')
            with self.assertRaisesRegex(ValueError, 'source bytes differ from HEAD blob'):
                native.source_snapshot(root)

    def test_assume_unchanged_cannot_bind_modified_source_to_clean_head(self):
        self.hidden_source_change('--assume-unchanged')

    def test_skip_worktree_cannot_bind_modified_source_to_clean_head(self):
        self.hidden_source_change('--skip-worktree')

    def test_completed_negative_geometry_is_retained_without_product_release(self):
        retain_collision(self.report)
        result = self.validate()
        self.assertTrue(result['geometric_rejected'])
        self.assertEqual(result['declared_pairs'], 15886)
        self.assertEqual([p['bodies'] for p in result['poses']], [154, 161, 154])
        self.assertTrue(all(self.report[k] is False for k in native.NATIVE_GO_KEYS))

    def test_one_pose_default_cannot_be_reported_as_whole_scene_coverage(self):
        self.report['selected_poses'] = ['PREDOCK']
        self.report['poses'] = self.report['poses'][:1]
        with self.assertRaisesRegex(ValueError, 'all three'):
            self.validate()

    def test_missing_or_duplicate_pair_is_not_a_pass_even_if_count_matches_rows(self):
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate):
                self.report = fixture()
                group = self.report['poses'][0]['external']
                if duplicate:
                    group['rows'][-1] = group['rows'][0].copy()
                else:
                    group['rows'].pop()
                    group['pair_count'] -= 1
                with self.assertRaisesRegex(ValueError, 'pair inventory'):
                    self.validate()

    def test_boolean_kernel_and_positive_artifact_failures_stop_execution_gate(self):
        for key in ('evaluation_failed', 'diagnostic_artifact_failure'):
            with self.subTest(key=key):
                self.report = fixture()
                self.report['poses'][0]['external']['rows'][0][key] = True
                with self.assertRaisesRegex(ValueError, 'evaluation/export failed'):
                    self.validate()

    def test_fresh_source_identity_is_required(self):
        for field, value in [('source_commit', 'b'*40), ('source_bytes_unchanged', False),
                             ('source_sha256', {**SOURCES, native.GENERATOR: '0'*64}),
                             ('source_sha256', {native.GENERATOR: SOURCES[native.GENERATOR]})]:
            with self.subTest(field=field):
                self.report = fixture()
                self.report[field] = value
                with self.assertRaises(ValueError):
                    self.validate()

    def test_research_cannot_grant_manufacturing_or_hardware_release(self):
        for field in native.NATIVE_GO_KEYS:
            with self.subTest(field=field):
                self.report = fixture()
                self.report[field] = True
                with self.assertRaisesRegex(ValueError, 'claims release'):
                    self.validate()

    def test_containment_omission_and_kernel_error_are_execution_failures(self):
        for error in (False, True):
            with self.subTest(error=error):
                self.report = fixture()
                containment = self.report['poses'][0]['containment']
                if error:
                    containment['rows'][0]['evaluation_failed'] = True
                else:
                    containment['rows'].pop()
                with self.assertRaises(ValueError):
                    self.validate()

    def test_positive_common_and_global_disposition_cannot_be_hidden(self):
        self.report['poses'][0]['external']['rows'][0]['common_mm3'] = .25
        with self.assertRaisesRegex(ValueError, 'masked'):
            self.validate()
        self.report = fixture()
        retain_collision(self.report)
        self.report['geometric_rejection_found'] = False
        with self.assertRaisesRegex(ValueError, 'disposition'):
            self.validate()

    def test_positive_common_requires_exported_material_context(self):
        retain_collision(self.report)
        self.report['poses'][0]['external']['rows'][0].pop('local_material_context')
        with self.assertRaisesRegex(ValueError, 'lacks diagnostics'):
            self.validate()

    def test_seven_regression_groups_and_original_negative_control_are_required(self):
        r = {'schema': 'razr-ep4-small-native-regressions-v1', 'source_commit': HEAD,
             'source_sha256': SOURCES, 'source_bytes_unchanged': True,
             'cases': [{'case': n, 'pass': True} for n in sorted(native.REGRESSION_CASES)],
             'native_regressions_passed': True, **{k: False for k in native.NATIVE_GO_KEYS}}
        native.validate_regressions(r, HEAD, SOURCES)
        r['cases'] = [c for c in r['cases'] if not c['case'].startswith('retained_A33')]
        with self.assertRaisesRegex(ValueError, 'negative control'):
            native.validate_regressions(r, HEAD, SOURCES)

    def readback(self, path, summary):
        return {'schema': 'razr-ep4-independent-step-readback-v1', 'native_source_commit': HEAD,
            'reader_observed_repository_head': HEAD, 'native_report': {'sha256': native.sha(path)},
            'independent_process_from_generator': True, 'geometry_generator_modules_imported': False,
            'execution_completed': True, 'declared_readback_checks_passed': True,
            'all_assembly_parts_have_metric_comparison': True, 'failures': [], 'changed_during_readback': [],
            'full_source_material_equivalence_proved': False, 'STEP_label_identity_proved': False,
            'continuous_interference_clearance_proved': False,
            'poses': {p: {'all_source_objects_compared': total, 'external_source_objects_compared': ext,
                          'candidate_source_objects_compared': 41} for p, (ext, total) in native.POSES.items()},
            'pair_scope_coverage': [{k: s[k] for k in ('scope', 'declared_pairs', 'positive_Common_exports_read')}
                                    for s in summary['pair_scope_coverage']], **{k: False for k in native.GO_KEYS}}

    def test_stale_or_failed_reader_cannot_validate_fresh_native_artifacts(self):
        summary = self.validate()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'native.json'
            path.write_text('{}\n')
            good = self.readback(path, summary)
            native.validate_readback(good, path, HEAD, summary)
            for field, value in [('reader_observed_repository_head', 'b'*40),
                                 ('native_report', {'sha256': '0'*64}),
                                 ('declared_readback_checks_passed', False),
                                 ('continuous_interference_clearance_proved', True),
                                 ('changed_during_readback', ['changed.step'])]:
                with self.subTest(field=field):
                    bad = copy.deepcopy(good); bad[field] = value
                    with self.assertRaises(ValueError):
                        native.validate_readback(bad, path, HEAD, summary)

    def test_reader_must_compare_every_body_and_positive_common_scope(self):
        summary = self.validate()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'native.json'; path.write_text('{}\n')
            for missing_pair in (False, True):
                with self.subTest(missing_pair=missing_pair):
                    bad = self.readback(path, summary)
                    if missing_pair:
                        bad['pair_scope_coverage'].pop()
                    else:
                        bad['poses']['STOW']['all_source_objects_compared'] = 41
                    with self.assertRaises(ValueError):
                        native.validate_readback(bad, path, HEAD, summary)

    def test_nonzero_command_retains_report_and_cannot_pass_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder); root = base/'source'; root.mkdir()
            with mock.patch.object(native, 'git', side_effect=lambda _r, *a: HEAD if a[0] == 'rev-parse' else ''), \
                 mock.patch.object(native, 'source_snapshot', return_value=SOURCES), \
                 mock.patch.object(native.subprocess, 'run', return_value=types.SimpleNamespace(returncode=23)):
                result = native.execute(root, base/'output', HEAD, 10.)
            saved = json.loads((base/'output/report.json').read_text())
            self.assertFalse(result['execution_checks_passed'])
            self.assertEqual(saved['commands'][0]['exit_code'], 23)
            self.assertEqual(saved['finite_geometry'], 'not_evaluated')
            self.assertFalse(saved['manufacturing_go'])


if __name__ == '__main__':
    unittest.main()
