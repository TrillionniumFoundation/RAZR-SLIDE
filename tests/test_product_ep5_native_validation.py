"""CI coverage and provenance regressions; all generated test reports are synthetic."""
import copy
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import verify_product_ep5_native as ep5

HEAD = 'a'*40
THIN_RECEIPT = 'engineering/thin-mechanism-20261015/native-verification.json.gz'
ROLES = {'local': {'design/product_geometry.json': 'synthetic local config'},
         'full': {'design/product_geometry.json': 'synthetic config',
                  THIN_RECEIPT: 'synthetic mandatory motion recipe',
                  'engineering/synthetic-native-payload.tar.gz': 'synthetic mandatory native archive'}}
SOURCES = {name: 'f'*64 for name in ep5.REQUIRED_INPUTS | {ep5.READER, ep5.HELPER, ep5.DRIVER, ep5.IDENTITY, ep5.MEMBER_HELPER} | set(ROLES['full'])}


def pair_fixture(pairs):
    rows = [{'a': a, 'b': b, 'common_mm3': 0., 'rejected': False} for a, b in pairs]
    return {'rows': rows, 'pair_count': len(rows), 'failures': [],
            'no_Common_above_tolerance_or_evaluation_error': True,
            'all_positive_Common_artifact_diagnostics_complete': True}


def reject_pair(matrix):
    row = matrix['rows'][0]
    row.update(common_mm3=.25, rejected=True, artifact_diagnostics_complete=True,
               common_material={'file': 'synthetic-Common.step'},
               local_material_context={'file': 'synthetic-context.step'})
    matrix['failures'] = [row]
    matrix['no_Common_above_tolerance_or_evaluation_error'] = False


def reject_native_fixture(report, mode):
    pose = report['poses'][0]
    reject_pair(pose['complete_pair_matrix'])
    if mode == 'full':
        pose['decisive_geometric_rejection_or_evaluation_failure'] = True
        pose['all_declared_finite_pose_checks_clear'] = False
        report['geometric_rejection_found'] = True
    else:
        report['all_declared_local_geometry_checks_clear'] = False


def native_fixture(root, mode):
    counts = ep5.COUNTS[mode]
    result = {'schema': ep5.SCHEMAS[mode], 'native_checks_executed': True, 'source_bytes_unchanged': True,
        'source_sha256': {str(root/name): digest for name, digest in SOURCES.items()},
        'selected_poses': list(ep5.POSES), 'poses': [], 'declared_input_roles': ROLES[mode], **{key: False for key in ep5.identity.NATIVE_GO_KEYS}}
    endpoint_names = {end: {end+'_part'+str(i) for i in range(20)} for end in ('A', 'B')}
    candidates = {'EP5_finite_material'} | endpoint_names['A'] | endpoint_names['B']
    for label, count in zip(ep5.POSES, counts):
        names = candidates | {'external'+str(i) for i in range(count-41)}
        contained = {'parts': 41, 'rows': [{'part': name, 'outside_outer_union_mm3': 0., 'rejected': False}
            for name in sorted(candidates)], 'failures': [], 'all_material_inside_optimistic_outer_union': True}
        result['poses'].append({'pose': label, 'combined_participants': count, 'candidate_participants': 41,
            'external_participants': count-41, 'parts': {name: {} for name in names},
            'complete_pair_matrix': pair_fixture(itertools.combinations(sorted(names), 2)),
            'containment': {'rows': [], 'executed': False} if mode == 'local' else contained,
            'decisive_geometric_rejection_or_evaluation_failure': False,
            'all_declared_finite_pose_checks_clear': True})
    if mode == 'local':
        result.update(whole_phone_obstacle_field_tested=False,
            shell_channels_generated_or_validated_by_this_mode=False, all_declared_local_geometry_checks_clear=True,
            continuous_complete_endpoints={
                'schema': 'razr-ep5-continuous-complete-endpoint-geometry-v1',
                'endpoint_metrics': {end: {name: {} for name in names} for end, names in endpoint_names.items()},
                'U1_to_all_20_B_endpoint_parts': pair_fixture(
                    ('U1_ALL_POSES_SMOOTH_ENCLOSURE', name) for name in sorted(endpoint_names['B'])),
                'other_segment_axis_separation_margins': {name: 1. for name in ep5.ENDPOINT_MARGIN_NAMES},
                'all_declared_continuous_endpoint_geometric_checks_clear': True,
                'current_PAWL_or_full_external_field_checked': False,
                'friction_strain_tolerance_and_physical_qualification_proved': False,
                **{key: False for key in ep5.identity.GO_KEYS}})
    else:
        result['geometric_rejection_found'] = False
    return result


def reader_fixture(native_path, mode):
    return {'schema': 'razr-ep5-independent-step-readback-v1', 'native_report_sha256': ep5.sha(native_path),
        'reader_sha256': SOURCES[ep5.READER], 'helper_sha256': SOURCES[ep5.HELPER],
        'execution_completed': True, 'declared_readback_checks_passed': True, 'failures': [],
        'independent_process_from_generator': True, 'geometry_generator_modules_imported': False,
        'full_source_material_equivalence_proved': False, 'STEP_label_identity_proved': False,
        'continuous_interference_clearance_proved': False,
        'continuous_endpoint_readback': {'cage': {'flat_solids': 1}, 'endpoint_pair_count': 20,
                                        'all_endpoint_pairs_present_once': True},
        'poses': [{'pose': label, 'assembly': {'flat_solids': count},
            'full_pair_count': count*(count-1)//2, 'all_pairs_present_once': True}
            for label, count in zip(ep5.POSES, ep5.COUNTS[mode])],
        **{key: False for key in ep5.identity.GO_KEYS}}


class ProductEP5NativeValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base/'repo'; self.root.mkdir()
        self.addCleanup(self.temp.cleanup)

    def test_empty_unexecuted_or_unidentified_native_report_cannot_pass(self):
        for field, value in [('poses', []), ('native_checks_executed', False), ('source_sha256', {})]:
            with self.subTest(field=field):
                data = native_fixture(self.root, 'full'); data[field] = value
                if field == 'poses': data['selected_poses'] = []
                with self.assertRaises(ValueError): ep5.validate_native_envelope(data, self.root, SOURCES, 'full', ROLES['full'])

    def test_partial_or_duplicated_pose_set_cannot_claim_three_pose_coverage(self):
        for labels in (['STOW'], ['STOW', 'STOW', 'OPEN']):
            data = native_fixture(self.root, 'full'); data['selected_poses'] = labels
            data['poses'] = [copy.deepcopy(next(p for p in data['poses'] if p['pose']==label)) for label in labels]
            with self.assertRaisesRegex(ValueError, 'three ordered'):
                ep5.validate_native_envelope(data, self.root, SOURCES, 'full', ROLES['full'])

    def test_local_evidence_cannot_substitute_for_complete_phone_scope(self):
        data = native_fixture(self.root, 'local')
        with self.assertRaises(ValueError): ep5.validate_native_envelope(data, self.root, SOURCES, 'full', ROLES['full'])
        for field in ('whole_phone_obstacle_field_tested', 'shell_channels_generated_or_validated_by_this_mode'):
            altered = copy.deepcopy(data); altered[field] = True
            with self.assertRaisesRegex(ValueError, 'relabelled'):
                ep5.validate_native_envelope(altered, self.root, SOURCES, 'local', ROLES['local'])

    def test_complete_scene_requires_external_external_pairs(self):
        data = native_fixture(self.root, 'full')
        self.assertEqual(ep5.validate_native_envelope(data, self.root, SOURCES, 'full', ROLES['full'])['declared_pairs'], 36442)
        pose = data['poses'][0]
        pose['complete_pair_matrix']['pair_count'] -= 113*112//2
        with self.assertRaisesRegex(ValueError, 'external/external'):
            ep5.validate_native_envelope(data, self.root, SOURCES, 'full', ROLES['full'])

    def test_missing_changed_or_outside_source_identity_is_rejected(self):
        for change in ('missing', 'changed', 'outside', 'role_closure'):
            with self.subTest(change=change):
                data = native_fixture(self.root, 'full'); sources = data['source_sha256']
                if change == 'missing': sources.pop(str(self.root/ep5.GENERATOR))
                elif change == 'changed': sources[str(self.root/ep5.GENERATOR)] = '0'*64
                elif change == 'outside': sources[str(self.base/'outside.py')] = 'f'*64
                else: data['declared_input_roles'] = {}
                with self.assertRaises(ValueError): ep5.validate_native_envelope(data, self.root, SOURCES, 'full', ROLES['full'])

    def test_geometric_rejection_is_retained_without_product_release(self):
        data = native_fixture(self.root, 'full'); reject_native_fixture(data, 'full')
        result = ep5.validate_native_envelope(data, self.root, SOURCES, 'full', ROLES['full'])
        self.assertEqual(result['finite_geometry'], 'rejected')
        for key in ep5.identity.NATIVE_GO_KEYS:
            altered = copy.deepcopy(data); altered[key] = True
            with self.assertRaisesRegex(ValueError, 'claims release'):
                ep5.validate_native_envelope(altered, self.root, SOURCES, 'full', ROLES['full'])

    def test_full_pose_and_global_dispositions_cannot_hide_actual_pair_rejection(self):
        for field in ('geometric_rejection_found', 'decisive_geometric_rejection_or_evaluation_failure',
                      'all_declared_finite_pose_checks_clear'):
            data = native_fixture(self.root, 'full'); reject_native_fixture(data, 'full')
            if field == 'geometric_rejection_found': data[field] = False
            else: data['poses'][0][field] = field.startswith('all_')
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'disposition'):
                ep5.validate_native_envelope(data, self.root, SOURCES, 'full', ROLES['full'])

    def test_pair_or_containment_raw_failures_cannot_be_erased_from_summaries(self):
        for field in ('pair', 'containment'):
            data = native_fixture(self.root, 'full'); pose = data['poses'][0]
            if field == 'pair': pose['complete_pair_matrix']['rows'][0]['common_mm3'] = .25
            else: pose['containment']['rows'][0]['outside_outer_union_mm3'] = .25
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'masked'):
                ep5.validate_native_envelope(data, self.root, SOURCES, 'full', ROLES['full'])

    def test_local_or_continuous_endpoint_rejections_cannot_be_masked_by_clear_flag(self):
        for scope in ('finite', 'continuous'):
            data = native_fixture(self.root, 'local')
            if scope == 'finite': reject_native_fixture(data, 'local')
            else:
                continuous = data['continuous_complete_endpoints']
                reject_pair(continuous['U1_to_all_20_B_endpoint_parts'])
                continuous['all_declared_continuous_endpoint_geometric_checks_clear'] = False
                data['all_declared_local_geometry_checks_clear'] = False
            self.assertEqual(ep5.validate_native_envelope(data, self.root, SOURCES, 'local', ROLES['local'])['finite_geometry'], 'rejected')
            data['all_declared_local_geometry_checks_clear'] = True
            with self.subTest(scope=scope), self.assertRaisesRegex(ValueError, 'disposition'):
                ep5.validate_native_envelope(data, self.root, SOURCES, 'local', ROLES['local'])

    def test_omitted_endpoint_pair_margin_or_local_readback_cannot_pass(self):
        for change in ('pair', 'margin', 'nonfinite_margin', 'continuous_flag'):
            data = native_fixture(self.root, 'local'); continuous = data['continuous_complete_endpoints']
            if change == 'pair': continuous['U1_to_all_20_B_endpoint_parts']['rows'].pop()
            elif change == 'margin': continuous['other_segment_axis_separation_margins'].pop(next(iter(ep5.ENDPOINT_MARGIN_NAMES)))
            elif change == 'nonfinite_margin': continuous['other_segment_axis_separation_margins'][next(iter(ep5.ENDPOINT_MARGIN_NAMES))] = float('nan')
            else: continuous['all_declared_continuous_endpoint_geometric_checks_clear'] = False
            with self.subTest(change=change), self.assertRaises(ValueError):
                ep5.validate_native_envelope(data, self.root, SOURCES, 'local', ROLES['local'])
        path = self.base/'synthetic-native.json'; path.write_text('{}\n')
        data = reader_fixture(path, 'local'); data.pop('continuous_endpoint_readback')
        with self.assertRaisesRegex(ValueError, 'endpoint cage or pairs'):
            ep5.validate_readback(data, path, SOURCES, 'local')

    def test_reader_must_cover_all_bodies_pairs_and_each_pose(self):
        path = self.base/'synthetic-native.json'; path.write_text('{}\n')
        for change in ('empty', 'one', 'body', 'pair'):
            with self.subTest(change=change):
                data = reader_fixture(path, 'full')
                if change == 'empty': data['poses'] = []
                elif change == 'one': data['poses'] = data['poses'][:1]
                elif change == 'body': data['poses'][0]['assembly']['flat_solids'] = 46
                else: data['poses'][0]['full_pair_count'] -= 1
                with self.assertRaises(ValueError): ep5.validate_readback(data, path, SOURCES, 'full')

    def test_reader_must_bind_fresh_native_and_executed_reader_bytes(self):
        path = self.base/'synthetic-native.json'; path.write_text('{}\n')
        for field, value in [('native_report_sha256', '0'*64), ('reader_sha256', '0'*64),
                             ('helper_sha256', '0'*64), ('declared_readback_checks_passed', False),
                             ('continuous_interference_clearance_proved', True)]:
            with self.subTest(field=field):
                data = reader_fixture(path, 'local'); data[field] = value
                with self.assertRaises(ValueError): ep5.validate_readback(data, path, SOURCES, 'local')

    def committed_fixture(self):
        paths = set(SOURCES) | {ep5.identity.GENERATOR, ep5.identity.READER, ep5.MOUNTED_ARCHIVE,
                                'engineering/unconsumed-historical/native-geometry.tar.gz'}
        for name in paths:
            path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('# synthetic identity fixture\n')
        role_code = ("def native_input_roles(mode, verified_mounted_members=False):\n"
                     "    roles = "+repr(ROLES['full'])+"\n"
                     "    if not verified_mounted_members: roles["+repr(ep5.MOUNTED_ARCHIVE)+"] = 'required original archive'\n"
                     "    return roles\n")
        (self.root/ep5.ROLE_HELPER).write_text(role_code)
        payload = self.root/'engineering/synthetic-native-payload.tar.gz'
        payload.write_bytes(b'synthetic identity payload, never a native archive')
        (self.root/'.gitignore').write_text('.venv/\n')
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.root), '-c', 'user.name=Synthetic identity test',
                '-c', 'user.email=synthetic@example.invalid', '-c', 'commit.gpgsign=false', *args],
                text=True, stderr=subprocess.STDOUT).strip()
        git('init', '-q'); git('add', '.'); git('commit', '-qm', 'Synthetic identity fixture', '--no-verify')
        return payload, git

    def test_hidden_native_payload_change_cannot_reuse_clean_head_identity(self):
        payload, git = self.committed_fixture()
        ep5.source_snapshot(self.root)
        git('update-index', '--skip-worktree', str(payload.relative_to(self.root)))
        payload.write_bytes(b'changed payload hidden from status')
        self.assertEqual(git('status', '--porcelain'), '')
        with self.assertRaisesRegex(ValueError, 'native input differs from HEAD blob'):
            ep5.source_snapshot(self.root)

    def test_installed_venv_dependencies_are_not_misclassified_as_project_source(self):
        _, git = self.committed_fixture()
        dependency = self.root/'.venv/lib/python3.12/site-packages/example/__init__.py'
        dependency.parent.mkdir(parents=True); dependency.write_text('# locked runtime dependency fixture\n')
        first = ep5.source_snapshot(self.root)
        dependency.write_text('# dependency bytes are runtime provenance, not a tracked project source\n')
        self.assertEqual(first, ep5.source_snapshot(self.root))
        self.assertEqual(git('status', '--porcelain'), '')
        self.assertFalse(any('.venv/' in name for name in first))

    def test_default_archive_is_required_and_only_explicit_member_mode_excludes_it(self):
        _, git = self.committed_fixture()
        archive = self.root/ep5.MOUNTED_ARCHIVE
        git('update-index', '--skip-worktree', ep5.MOUNTED_ARCHIVE); archive.unlink()
        with self.assertRaisesRegex(ValueError, 'missing or linked required native input'):
            ep5.source_snapshot(self.root)
        snapshot = ep5.source_snapshot(self.root, True)
        self.assertNotIn(ep5.MOUNTED_ARCHIVE, snapshot)
        self.assertIn(THIN_RECEIPT, snapshot)

    def test_actual_gzip_recipe_is_required_even_with_explicit_members(self):
        _, git = self.committed_fixture()
        git('update-index', '--skip-worktree', THIN_RECEIPT); (self.root/THIN_RECEIPT).unlink()
        with self.assertRaisesRegex(ValueError, 'missing or linked required native input'):
            ep5.source_snapshot(self.root, True)

    def test_unconsumed_historical_archive_is_not_in_native_input_closure(self):
        _, git = self.committed_fixture()
        before = ep5.source_snapshot(self.root)
        unrelated = 'engineering/unconsumed-historical/native-geometry.tar.gz'
        git('update-index', '--skip-worktree', unrelated); (self.root/unrelated).unlink()
        self.assertEqual(before, ep5.source_snapshot(self.root))
        self.assertEqual(git('status', '--porcelain'), '')
        self.assertNotIn(unrelated, before)

    def test_running_driver_cannot_masquerade_as_different_checkout_source(self):
        with self.assertRaisesRegex(ValueError, 'outside the checked commit'):
            ep5.bind_running_sources(self.root, SOURCES)

    def run_mocked(self, process, members=None, member_validation=None):
        with mock.patch.object(ep5.identity, 'git', side_effect=lambda _root, *args: HEAD if args[0]=='rev-parse' else ''), \
             mock.patch.object(ep5, 'source_snapshot', return_value=SOURCES), \
             mock.patch.object(ep5, 'bind_running_sources'), \
             mock.patch.object(ep5, 'input_roles', side_effect=lambda _r, _s, mode, *_a, **_k: ROLES[mode]), \
             mock.patch.object(ep5, 'verify_explicit_members', side_effect=member_validation), \
             mock.patch.object(ep5.subprocess, 'run', side_effect=process):
            return ep5.execute(self.root, self.base/'output', HEAD, 30., members)

    def test_failed_command_retains_failure_report_without_execution_pass(self):
        result = self.run_mocked(lambda *_args, **_kwargs: types.SimpleNamespace(returncode=23))
        saved = json.loads((self.base/'output/report.json').read_text())
        self.assertFalse(result['execution_checks_passed'])
        self.assertEqual(saved['commands'][0]['exit_code'], 23)
        self.assertFalse(saved['G2_acceptance_granted_by_this_job'])
        self.assertEqual(saved['research_scopes'], {})

    def test_orchestration_requires_both_generators_and_separate_readers(self):
        commands = []
        def process(command, **kwargs):
            commands.append(command)
            if '--output' in command:
                folder = Path(command[command.index('--output')+1]); folder.mkdir()
                if command[2] == str(self.root/ep5.GENERATOR):
                    mode = 'local' if '--native-local-motion' in command else 'full'
                    data = native_fixture(self.root, mode)
                    if mode == 'full': reject_native_fixture(data, mode)
                    (folder/'native-report.json').write_text(json.dumps(data))
                else:
                    path = Path(command[command.index('--manifest')+1]); mode = path.parent.name
                    (folder/'report.json').write_text(json.dumps(reader_fixture(path, mode)))
            return types.SimpleNamespace(returncode=0)
        result = self.run_mocked(process)
        self.assertEqual(len(commands), 5)
        self.assertTrue(all(command[:2] == [sys.executable, '-B'] for command in commands))
        self.assertEqual([row['stage'] for row in result['commands']],
            ['entrypoints', 'local-native', 'local-independent-readback', 'full-native', 'full-independent-readback'])
        self.assertIn('--native-local-motion', commands[1])
        self.assertEqual(commands[3][-4:], ['--poses', 'STOW', 'PREDOCK', 'OPEN'])
        self.assertTrue(result['execution_checks_passed'])
        self.assertEqual(result['research_scopes']['full']['finite_geometry'], 'rejected')
        self.assertFalse(result['G2_acceptance_granted_by_this_job'])
        self.assertTrue(all(result[key] is False for key in ep5.identity.NATIVE_GO_KEYS))
        self.assertTrue(all('--verified-mounted-members' not in command for command in commands))


    def execute_explicit_member_fixture(self, changed_after=False):
        directory = self.base/'synthetic-members'; directory.mkdir()
        proof = {'directory': str(directory), 'source_sha256': {str(directory/'part.step'): 'e'*64},
                 'recovery_receipt_sha256': 'd'*64, 'members': {'fixture': 'synthetic only'}}
        changed = copy.deepcopy(proof)
        if changed_after: changed['recovery_receipt_sha256'] = '0'*64
        commands = []
        def process(command, **kwargs):
            commands.append(command)
            if '--output' in command:
                folder = Path(command[command.index('--output')+1]); folder.mkdir()
                if command[2] == str(self.root/ep5.GENERATOR):
                    mode = 'local' if '--native-local-motion' in command else 'full'
                    data = native_fixture(self.root, mode)
                    if mode == 'full':
                        data.update(verified_mounted_members_before=proof, verified_mounted_members_after=proof)
                        data['source_sha256'].update(proof['source_sha256'])
                    (folder/'native-report.json').write_text(json.dumps(data))
                else:
                    path = Path(command[command.index('--manifest')+1]); mode = path.parent.name
                    data = reader_fixture(path, mode)
                    if mode == 'full': data['verified_original_member_input_rechecked'] = proof
                    (folder/'report.json').write_text(json.dumps(data))
            return types.SimpleNamespace(returncode=0)
        return self.run_mocked(process, directory, [proof, changed]), commands

    def test_explicit_member_input_is_passed_only_to_full_run_and_reread(self):
        result, commands = self.execute_explicit_member_fixture()
        self.assertTrue(result['execution_checks_passed'])
        self.assertFalse(result['archive_available'])
        self.assertTrue(result['verified_original_members'])
        self.assertNotIn('--verified-mounted-members', commands[1])
        self.assertIn('--verified-mounted-members', commands[3])
        self.assertEqual(result['verified_mounted_members_before'], result['verified_mounted_members_after'])
        self.assertFalse(result['full_checkout_verified'])
        self.assertFalse(result['all_configured_unit_suites_executed'])

    def test_changed_explicit_member_receipt_fails_final_validation(self):
        result, _ = self.execute_explicit_member_fixture(changed_after=True)
        self.assertFalse(result['execution_checks_passed'])
        self.assertFalse(result['verified_original_members'])
        self.assertIn('explicit member inputs changed', result['final_identity_error'])

    def test_invalid_explicit_member_input_stops_before_any_native_execution(self):
        called = []
        def process(command, **kwargs):
            called.append(command); return types.SimpleNamespace(returncode=0)
        result = self.run_mocked(process, self.base/'invalid-members', ValueError('original member bytes differ'))
        self.assertFalse(result['execution_checks_passed'])
        self.assertEqual(called, [])
        self.assertEqual(result['commands'], [])
        self.assertIn('original member bytes differ', result['error']['message'])


if __name__ == '__main__':
    unittest.main()
