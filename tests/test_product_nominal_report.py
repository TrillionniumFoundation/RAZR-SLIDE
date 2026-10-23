"""Synthetic receipt corruption regressions; these tests do not execute CAD."""
import contextlib
import copy
import io
import itertools
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import validate_product_nominal_report as guard

HEAD = 'a'*40
PAYLOAD = 'engineering/synthetic/native.tar.gz'
MANIFEST = 'engineering/synthetic/manifest.json'


def synthetic_fixture(pose='STOW'):
    current = {'repository_head': HEAD, 'head_bound_source_sha256': {
        PAYLOAD: '1'*64, MANIFEST: '2'*64, 'integration/synthetic.py': '3'*64},
        'executed_source_sha256': {'/synthetic/repo/integration/synthetic.py': '3'*64},
        'executed_source_overlay': False, 'outside_repository_executed_files': [],
        'environment': {'passed': True, 'scope': 'synthetic runtime fixture only'}}
    names = ['synthetic_part_%03d' % i for i in range(guard.COUNTS[pose])]
    rows = [{'a': a, 'b': b, 'disposition': 'clear', 'method': 'continuous_relative_axis_gap',
             'gap_lower_mm': 1., 'relative_telescope_z_projection_mm': [0., 0.]}
            for a, b in itertools.combinations(names, 2)]
    report = {'schema': 'razr-ep5-independent-control-domain-v2', 'pose': pose,
        'domain': guard.expected_domain(pose), 'expected_head': HEAD,
        'identity_before': copy.deepcopy(current), 'identity_after': copy.deepcopy(current),
        **{key: True for key in guard.TRUE_FLAGS}, **{key: False for key in guard.FALSE_FLAGS},
        'complete_participant_names': names, 'participant_count': len(names),
        'pairs': rows, 'pair_count': len(rows), 'expected_pair_count': len(rows),
        'counts': {'clear': len(rows)}, 'methods': {'continuous_relative_axis_gap': len(rows)},
        'unresolved_pairs': [], 'confirmed_collision_witnesses': [], 'evaluation_failures': [],
        'evaluation_failure_count': 0,
        'construction_check': {'participants': len(names), 'maximum_bidirectional_material_difference_mm3': 0.,
                               'affine_law_is_code_owned_not_inferred_from_samples': True},
        'native_scene_metadata': {'combined_participants': len(names), 'candidate_participants': 41,
            'mechanical_participants': len(names)-46, 'scene': {
                'installed_mechanical_parts': len(names)-46,
                'factory': 'integration/product_split_assembly.py:split_scene',
                'slide_mm': 0. if pose == 'STOW' else 79.75, 'descent_mm': 8.2 if pose == 'OPEN' else 0.,
                'OPEN_hold_screws_installed': pose == 'OPEN',
                'OPEN_display_support_insert_installed': pose == 'OPEN',
                'physical_holding_and_force_qualified': False, 'OPEN_thread_retention_load_qualified': False,
                'loose_OPEN_accessories_have_onboard_storage': False, 'complete_functional_phone': False,
                'candidate_go': False, 'manufacturing_go': False,
                'source_inputs': {MANIFEST: '2'*64}, 'archive': PAYLOAD, 'archive_sha256': '1'*64}}}
    return report, current


class ProductNominalReportTests(unittest.TestCase):
    def test_complete_synthetic_three_pose_receipts_and_reverse_proof_are_accepted(self):
        for pose in guard.COUNTS:
            with self.subTest(pose=pose):
                report, identity = synthetic_fixture(pose)
                row = report['pairs'][0]
                row.update(relative_reference_frame_reversed=True, initial_reference_frame_result={
                    'disposition': 'unresolved_enclosure_overlap', 'method': 'continuous_relative_axis_translation',
                    'examined_region_common_sum_mm3': 2e-7, 'positive_enclosure_common_mm3': 1e-7,
                    'regions_examined': 2, 'total_region_count': 3, 'collision_proved': False})
                result = guard.validate_report(report, pose, HEAD, identity)
                self.assertEqual(result['unique_unordered_pairs'], len(report['pairs']))
                self.assertFalse(result['geometry_recomputed_by_postcheck'])

    def test_same_count_duplicate_reversed_self_or_unknown_pairs_are_rejected(self):
        for change in ('all_repeated', 'one_duplicate', 'reversed', 'self', 'outside'):
            report, identity = synthetic_fixture()
            rows = report['pairs']
            if change == 'all_repeated': report['pairs'] = [rows[0]]*len(rows)
            elif change == 'one_duplicate': rows[-1] = copy.deepcopy(rows[0])
            elif change == 'reversed': rows[0]['a'], rows[0]['b'] = rows[0]['b'], rows[0]['a']
            elif change == 'self': rows[0]['b'] = rows[0]['a']
            else: rows[0]['a'] = 'synthetic_outside_inventory'
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'unordered pairs'):
                guard.validate_report(report, 'STOW', HEAD, identity)

    def test_missing_duplicate_or_wrong_size_participant_inventory_is_rejected(self):
        for change in ('absent', 'empty', 'duplicate', 'wrong_size'):
            report, identity = synthetic_fixture()
            if change == 'absent': del report['complete_participant_names']
            elif change == 'empty': report['complete_participant_names'] = []
            elif change == 'duplicate': report['complete_participant_names'][-1] = report['complete_participant_names'][0]
            else: report['complete_participant_names'].pop()
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'participant inventory'):
                guard.validate_report(report, 'STOW', HEAD, identity)

    def test_equal_pair_count_cannot_relabel_pose_or_shrink_any_declared_domain(self):
        for change in ('pose', 'slide', 'tabs', 'flank', 'key', 'crosshead', 'vertices', 'independence', 'projection_bounds'):
            report, identity = synthetic_fixture()
            domain = report['domain']
            if change == 'pose': report['pose'] = 'PREDOCK'
            elif change == 'slide': domain['slide_mm'] = 79.75
            elif change == 'tabs': domain['right_tab_mm'] = [0., 0.]
            elif change == 'flank': domain['slot_flanks'][1] = [0., 0.]
            elif change == 'key': domain['KEY_offsets_mm'] = [0., .01]
            elif change == 'crosshead': domain['crosshead_offsets_mm'] = [0., .01]
            elif change == 'vertices': domain['telescope_allocation']['vertices_joint_mm'].pop()
            elif change == 'independence': domain['telescope_allocation']['left_right_allocations_independent'] = False
            else: domain['telescope_allocation']['parameter_bounds_delta_j1_delta_j2_mm'][0] = [0., 0.]
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'domain differs'):
                guard.validate_report(report, 'STOW', HEAD, identity)

    def test_scope_overclaims_missing_completion_and_overlay_flags_are_rejected(self):
        for key in guard.TRUE_FLAGS + guard.FALSE_FLAGS:
            report, identity = synthetic_fixture()
            report[key] = not report[key]
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'scope flags'):
                guard.validate_report(report, 'STOW', HEAD, identity)

    def test_raw_numeric_evidence_cannot_be_masked_by_clear_disposition(self):
        for value in (0., -1., float('nan'), float('inf'), True):
            report, identity = synthetic_fixture(); report['pairs'][0]['gap_lower_mm'] = value
            with self.subTest(gap=value), self.assertRaisesRegex(ValueError, 'separation'):
                guard.validate_report(report, 'STOW', HEAD, identity)
        for maximum, upper in ((0., 2e-7), (2e-7, 0.), (-1., 0.), (0., float('nan'))):
            report, identity = synthetic_fixture()
            report['pairs'][0].update(method='identical_relative_pose', region_count=1,
                maximum_region_common_mm3=maximum, common_upper_bound_mm3=upper,
                common_upper_bound_is_sum_not_union_volume=True)
            with self.subTest(maximum=maximum, upper=upper), self.assertRaisesRegex(ValueError, 'Common bounds'):
                guard.validate_report(report, 'STOW', HEAD, identity)

    def test_reverse_clear_result_cannot_hide_an_initial_kernel_error(self):
        report, identity = synthetic_fixture()
        report['pairs'][0].update(relative_reference_frame_reversed=True,
            initial_reference_frame_result={'disposition': 'unresolved_evaluation', 'error': 'synthetic kernel failure'})
        with self.assertRaisesRegex(ValueError, 'evaluation failure'):
            guard.validate_report(report, 'STOW', HEAD, identity)

    def test_inconsistent_pair_counts_and_summary_arrays_are_rejected(self):
        for key, value in (('pair_count', 11780), ('expected_pair_count', 11780), ('participant_count', 153),
                           ('counts', {'clear': 1}), ('methods', {}), ('unresolved_pairs', [{}]),
                           ('confirmed_collision_witnesses', [{}]), ('evaluation_failures', [{}]),
                           ('evaluation_failure_count', False)):
            report, identity = synthetic_fixture(); report[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                guard.validate_report(report, 'STOW', HEAD, identity)

    def test_missing_or_rejected_full_material_construction_cannot_pass(self):
        for key, value in (('participants', 153), ('maximum_bidirectional_material_difference_mm3', 2e-7),
                           ('maximum_bidirectional_material_difference_mm3', float('nan')),
                           ('affine_law_is_code_owned_not_inferred_from_samples', False)):
            report, identity = synthetic_fixture(); report['construction_check'][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'construction check'):
                guard.validate_report(report, 'STOW', HEAD, identity)

    def test_source_map_environment_and_both_before_after_identities_are_bound(self):
        for checkpoint in ('identity_before', 'identity_after'):
            for key, value in (('repository_head', 'b'*40), ('head_bound_source_sha256', {}),
                               ('executed_source_sha256', {}), ('executed_source_overlay', True),
                               ('outside_repository_executed_files', ['/synthetic/overlay.py']),
                               ('environment', {'passed': True, 'scope': 'different synthetic runtime'})):
                report, identity = synthetic_fixture(); report[checkpoint][key] = value
                with self.subTest(checkpoint=checkpoint, key=key), self.assertRaisesRegex(ValueError, 'identity differs'):
                    guard.validate_report(report, 'STOW', HEAD, identity)

    def test_factory_payload_omission_changed_bytes_or_scope_cannot_pass(self):
        for change in ('omission', 'digest', 'outside', 'accessory', 'physical'):
            report, identity = synthetic_fixture(); scene = report['native_scene_metadata']['scene']
            if change == 'omission': scene['source_inputs'] = {}
            elif change == 'digest': scene['archive_sha256'] = '0'*64
            elif change == 'outside': scene['external_verified_source_inputs'] = {'/synthetic/outside.step': '0'*64}
            elif change == 'accessory': scene['OPEN_hold_screws_installed'] = True
            else: scene['physical_holding_and_force_qualified'] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                guard.validate_report(report, 'STOW', HEAD, identity)

    def test_executed_inventory_is_rebuilt_and_rejects_untracked_dirty_or_linked_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); snapshot = {}
            names = ['integration/a.py', 'design/a.json', 'engineering/a.py', PAYLOAD,
                     'tools/verify_product_ep5_native.py', 'tools/verify_product_native.py', 'tools/check_environment.py']
            for name in names:
                path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('synthetic bytes\n')
                snapshot[name] = guard.native.sha(path)
            roles = {PAYLOAD: 'synthetic native input'}
            self.assertEqual(set(guard.expected_executed_sources(root, snapshot, roles)), {str(root/name) for name in names})
            added = root/'integration/untracked.py'; added.write_text('synthetic untracked\n')
            with self.assertRaisesRegex(ValueError, 'untracked'): guard.expected_executed_sources(root, snapshot, roles)
            added.unlink(); dirty = root/'integration/a.py'; original = dirty.read_text(); dirty.write_text('changed\n')
            with self.assertRaisesRegex(ValueError, 'differs from HEAD'): guard.expected_executed_sources(root, snapshot, roles)
            dirty.write_text(original); linked = root/'integration/alias.py'; linked.symlink_to(dirty)
            with self.assertRaisesRegex(ValueError, 'linked'): guard.expected_executed_sources(root, snapshot, roles)

    def test_cli_rechecks_current_identity_after_the_report_and_rejects_mutation(self):
        report, identity = synthetic_fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'synthetic-only.json'; path.write_text(json.dumps(report))
            argv = ['--report', str(path), '--pose', 'STOW', '--expected-head', HEAD]
            with mock.patch.object(guard, 'current_identity', return_value=identity) as inspect, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(guard.main(argv), 0)
                self.assertEqual(inspect.call_count, 2)
            changed = copy.deepcopy(identity); changed['environment']['scope'] = 'synthetic mutation'
            with mock.patch.object(guard, 'current_identity', side_effect=[identity, changed]), self.assertRaisesRegex(ValueError, 'changed during postcheck'):
                guard.main(argv)


if __name__ == '__main__':
    unittest.main()
