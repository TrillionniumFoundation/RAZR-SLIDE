"""Synthetic full-inventory resume contracts; no native geometry is generated."""
from collections import Counter
import copy
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

STUDY = Path(__file__).resolve().parents[1]
REPO = Path('/workspace/scratch/95cd2986fdf2/RAZR-SLIDE')
sys.path[:0] = [str(STUDY/'tools'), str(REPO/'tools')]
import key_endpoint_resume as reader
import validate_product_nominal_report as canonical


class CompleteTrialResumeContracts(unittest.TestCase):
    """The current identity is a declared synthetic fixture, not a real repo scan."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='razr-key-resume-synthetic-', dir='/tmp')
        self.directory = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.head = 'a'*40
        self.sources = {name: hashlib.sha256(('synthetic '+name).encode()).hexdigest()
                        for name in reader.SOURCE_FILES}
        self.profile_digest = reader.sha(REPO/reader.PROFILE_INPUT)
        original = json.loads(gzip.decompress((REPO/reader.PROFILE_INPUT).read_bytes()))
        self.profiles = {(side, index): row['profile'] for side in 'LR'
                         for index, row in enumerate(original['sides'][side]['contacts'])}
        self.current = {'repository_head': self.head, 'executed_source_overlay': False,
                        'outside_repository_executed_files': [],
                        'head_bound_source_sha256': {'engineering/fixture.json': 'e'*64,
                                                    'engineering/fixture.tar.gz': 'd'*64,
                                                    reader.PROFILE_INPUT: self.profile_digest},
                        'executed_source_sha256': {},
                        'environment': {'passed': True, 'checked_package_count': 43,
                                        'synthetic_identity_not_runtime_execution': True}}
        self.build('STOW_OUTSIDE_HALF_BAND')

    def build(self, label):
        self.label = label
        pose = label.split('_')[0]
        n = 154 if pose == 'STOW' else 161
        self.names = sorted(reader.MOVING+['SYNTHETIC_FIXED_%03d' % i for i in range(n-24)])
        scope = reader.expected_scope(pose)
        scene = {'factory': 'integration/product_split_assembly.py:split_scene',
                 'installed_mechanical_parts': n-46, 'slide_mm': scope['slide_mm'],
                 'descent_mm': scope['descent_mm'], 'left_tab_mm': 3., 'right_tab_mm': 3.,
                 'slot_flanks': [0., 0.], 'KEY_offsets_mm': [0., 0.], 'crosshead_offsets_mm': [0., 0.],
                 'telescope_offsets_by_side_mm': {side: scope['telescope_offsets_each_mm'][:] for side in 'LR'},
                 'OPEN_hold_screws_installed': pose == 'OPEN',
                 'OPEN_display_support_insert_installed': pose == 'OPEN',
                 'source_inputs': {'engineering/fixture.json': 'e'*64,
                                   reader.PROFILE_INPUT: self.profile_digest},
                 'archive': 'engineering/fixture.tar.gz', 'archive_sha256': 'd'*64}
        scene.update(dict.fromkeys(('physical_holding_and_force_qualified', 'OPEN_thread_retention_load_qualified',
            'loose_OPEN_accessories_have_onboard_storage', 'complete_functional_phone', 'candidate_go', 'manufacturing_go'), False))
        metadata = {'combined_participants': n, 'candidate_participants': 41,
                    'mechanical_participants': n-46, 'scene': scene}
        pairs = list(itertools.combinations(self.names, 2))
        base_rows = [{'a': a, 'b': b, 'disposition': 'clear', 'method': 'continuous_relative_axis_gap',
                      'gap_lower_mm': .25, 'relative_telescope_z_projection_mm': [0., 0.]} for a, b in pairs]
        self.baseline = {'schema': 'razr-ep5-independent-control-domain-v2', 'pose': pose,
            'domain': canonical.expected_domain(pose), 'expected_head': self.head,
            'identity_before': self.current, 'identity_after': self.current,
            **dict.fromkeys(canonical.TRUE_FLAGS, True), **dict.fromkeys(canonical.FALSE_FLAGS, False),
            'complete_participant_names': self.names, 'pairs': base_rows, 'participant_count': n,
            'pair_count': len(pairs), 'expected_pair_count': len(pairs),
            'counts': {'clear': len(pairs)}, 'methods': {'continuous_relative_axis_gap': len(pairs)},
            'unresolved_pairs': [], 'confirmed_collision_witnesses': [], 'evaluation_failures': [],
            'evaluation_failure_count': 0, 'construction_check': {'participants': n,
                'maximum_bidirectional_material_difference_mm3': 0.,
                'affine_law_is_code_owned_not_inferred_from_samples': True},
            'native_scene_metadata': metadata}
        self.baseline_path = self.directory/(pose+'-synthetic-baseline.json')
        self.write_baseline()
        receipt = canonical.validate_report(self.baseline, pose, self.head, self.current)
        moving = set(reader.MOVING)
        changed = [list(pair) for pair in pairs if moving.intersection(pair)]
        fixed = [list(pair) for pair in pairs if not moving.intersection(pair)]
        rows = [{'a': a, 'b': b, 'common_mm3': 0., 'method': 'positive_axis_gap',
                 'axis_gap_lower_mm': .125, 'rejected': False} for a, b in changed]
        cam = (.425-.4)*math.hypot(1., 12./79.75)
        half = cam+(.425-.4)*math.sqrt(2.)
        inward = (min(profile['pin_q']-profile['floor_corner_q'] for profile in self.profiles.values())/4
                  if pose == 'STOW' else -.001)
        pose_record = {'pose': pose, 'participants': n, 'complete_participant_names': self.names,
            'moving_participants': reader.MOVING, 'native_scene_metadata': copy.deepcopy(metadata),
            'tabs_mm': [3., 3.], 'slot_flanks': [0., 0.],
            'telescope_allocation': copy.deepcopy(scene['telescope_offsets_by_side_mm']),
            'in_domain_factory_crosscheck': {'KEY_offset_mm': inward, 'crosshead_offset_mm': inward*cam/half,
                'all_participants_compared': n, 'bidirectional_material_difference_mm3': dict.fromkeys(self.names, 0.)}}
        if pose == 'OPEN':
            pose_record.update(selected_lower_stop_positions_retained=True, new_lower_stop_force_or_retention_proof=False)
        else:
            pose_record['native_plateau_contact_extension'] = {
                'schema': 'razr-native-finite-plateau-extension-v1',
                'rows': [{'side': side, 'STOP': index, 'native_plateau_extension_supported': False,
                          'negative_KEY_interval_mm': [-half, 0.],
                          'floor_candidates': [], 'pin_candidates': []} for side, index in itertools.product('LR', (0, 1))],
                'all_four_current_native_floors_support_the_declared_negative_q_contact': False,
                'restoring_force_and_physical_contact_qualified': False, 'formal_directed_rounding_certificate': False}
        self.record = {'schema': 'razr-KEY-endpoint-single-trial-v2', 'source_commit': self.head,
            'trial_label': label, 'trial_inputs': reader.expected_inputs(label), 'scope': scope,
            **dict.fromkeys(reader.TRUE_FLAGS, True), **dict.fromkeys(reader.FALSE_FLAGS, False),
            'status': 'complete', 'checkpoint_generation': 27, 'seconds': .1,
            'complete_participant_names': self.names, 'moving_participants': reader.MOVING,
            'expected_changed_pairs': changed, 'reused_unchanged_pairs': fixed,
            'actual_native_changed_pairs': rows, 'pending_changed_pairs': [], 'processed_pair_count': len(rows),
            'positive_actual_Common': [], 'evaluation_failures': [],
            'positive_Common_STEP_export_limit_per_trial': 8, 'finite_trial_material_clear': True,
            'existing_profile_rejections': [{'side': side, 'STOP': index, 'error': 'synthetic outside-profile rejection'}
                                            for side, index in itertools.product('LR', (0, 1))],
            'pose_record': pose_record,
            'baseline_report': {'pose': pose, 'path': str(self.baseline_path), 'sha256': reader.sha(self.baseline_path)},
            'baseline_receipt_postcheck': receipt, 'identity_before': self.current, 'identity_after': self.current,
            'study_source_sha256_before': self.sources, 'study_source_sha256_after': self.sources,
            'executed_study_source': {'path': str(STUDY/'integration/probe_key_endpoint_extension.py'),
                                      'sha256': self.sources['integration/probe_key_endpoint_extension.py']}}

    def write_baseline(self):
        self.baseline_path.write_text(json.dumps(self.baseline, allow_nan=False))

    def check(self, record=None):
        return reader.validate_completed_trial(self.record if record is None else record,
            expected_head=self.head, expected_label=self.label, current_identity=self.current,
            expected_study_sources=self.sources, baseline_report=self.baseline,
            baseline_path=self.baseline_path, report_directory=self.directory)

    def make_positive(self, count=1):
        for index, row in enumerate(self.record['actual_native_changed_pairs'][:count]):
            row.update(common_mm3=2e-7, method='native_common', axis_gap_lower_mm=0., rejected=True)
            positive = dict(row)
            if index < 8:
                path = self.directory/('synthetic-positive-%02d.step' % index)
                path.write_bytes(('synthetic test bytes only '+str(index)).encode())
                positive['actual_Common_STEP'] = {'path': path.name, 'sha256': reader.sha(path)}
            self.record['positive_actual_Common'].append(positive)
        self.record['finite_trial_material_clear'] = False

    def make_supported_plateau(self):
        """Invent finite native-like records, using only the frozen profile scalars."""
        cam = (.425-.4)*math.hypot(1., 12./79.75)
        half = cam+(.425-.4)*math.sqrt(2.)
        plateau = self.record['pose_record']['native_plateau_contact_extension']
        for row in plateau['rows']:
            side, index = row['side'], row['STOP']
            profile = self.profiles[(side, index)]
            sign = -1. if side == 'L' else 1.
            e, q = [-.6, -.2], [-.1, .2]
            floor = {'face': 10+index, 'e_extent_mm': e, 'q_extent_mm': q,
                     'area_mm2': (e[1]-e[0])*(q[1]-q[0]),
                     'complete_trimmed_face_is_rectangle': True,
                     'vertices_eqr_mm': [[a, b, profile['floor_height']] for a, b in itertools.product(e, q)],
                     'wire_count': 1, 'edge_geometry_types': ['LINE']*4,
                     'normal_xyz': [sign, 0., 0.],
                     'center_eqr_mm': [(e[0]+e[1])/2, (q[0]+q[1])/2, profile['floor_height']]}
            pin_q, radius = profile['pin_q'], profile['pin_radius']
            pin_r = profile['floor_height']+radius
            pin_e = [-.5, -.3]
            pin = {'face': 20+index, 'e_extent_mm': pin_e, 'pin_q_mm': pin_q,
                   'pin_r_mm': pin_r, 'radius_mm': radius, 'axis_direction_xyz': [0., 0., 1.],
                   'cylinder_location_xyz': [sign*(23.85+pin_r), 14.8+pin_q, 4.2],
                   'vertices_eqr_mm': [[v, pin_q+radius, pin_r] for v in pin_e],
                   'full_pin_outside_STOP_mm3': 0.}
            row.update(floor_candidates=[floor], pin_candidates=[pin],
                       contact_q_interval_mm=[pin_q, pin_q+half],
                       finite_floor_q_edge_margins_mm=[pin_q-q[0], q[1]-pin_q-half],
                       contact_e_overlap_mm=pin_e[1]-pin_e[0],
                       native_plateau_extension_supported=True)
        plateau['all_four_current_native_floors_support_the_declared_negative_q_contact'] = True
        return plateau

    def test_complete_STOW_and_OPEN_accounting_invokes_actual_canonical_postguard(self):
        result = self.check()
        self.assertEqual((result['changed_pairs'], result['unchanged_pairs']), (3396, 8385))
        self.build('OPEN_OUTSIDE_FULL_BAND')
        result = self.check()
        self.assertEqual((result['changed_pairs'], result['unchanged_pairs']), (3564, 9316))
        self.assertFalse(result['continuous_backlash_domain_proved'])
        self.assertFalse(result['physical_qualification'])
        self.assertFalse(any(name.startswith(('cadquery', 'OCP')) for name in sys.modules))

    def test_complete_actual_positive_can_resume_with_all_numeric_rows_and_first_eight_steps(self):
        self.make_positive(9)
        result = self.check()
        self.assertEqual(result['positive_actual_pairs'], 9)
        self.assertEqual(result['verified_positive_STEP_files'], 8)
        self.assertFalse(result['finite_trial_material_clear'])

    def test_partial_status_or_raw_prefix_never_resumes(self):
        for status in ('pending', 'constructing', 'evaluating', 'interrupted', 'failed'):
            with self.subTest(status=status):
                altered = dict(self.record, status=status)
                with self.assertRaises(ValueError): self.check(altered)
        self.record['actual_native_changed_pairs'].pop()
        self.record['processed_pair_count'] -= 1
        self.record['pending_changed_pairs'] = [self.record['expected_changed_pairs'][-1]]
        with self.assertRaises(ValueError): self.check()

    def test_duplicate_or_reordered_changed_raw_rows_rejected(self):
        original = self.record['actual_native_changed_pairs']
        for replacement in (original[:1]+original[:1]+original[2:], [original[1], original[0]]+original[2:]):
            with self.subTest(kind=replacement[0]['a']):
                with self.assertRaises(ValueError): self.check(dict(self.record, actual_native_changed_pairs=replacement))

    def test_incomplete_fixed_partition_and_changed_inventory_rejected(self):
        for field in ('expected_changed_pairs', 'reused_unchanged_pairs', 'moving_participants', 'complete_participant_names'):
            with self.subTest(field=field):
                with self.assertRaises(ValueError): self.check(dict(self.record, **{field: self.record[field][:-1]}))

    def test_nonfinite_negative_or_boolean_raw_Common_rejected(self):
        row = self.record['actual_native_changed_pairs'][0]
        for value in (-1e-12, float('nan'), float('inf'), True):
            with self.subTest(value=value):
                row['common_mm3'] = value
                with self.assertRaises(ValueError): self.check()

    def test_gap_method_and_original_rejection_threshold_must_match_raw(self):
        row = self.record['actual_native_changed_pairs'][0]
        row['axis_gap_lower_mm'] = 0.
        with self.assertRaises(ValueError): self.check()
        row.update(method='native_common', common_mm3=1.8e-7, rejected=False)
        with self.assertRaises(ValueError): self.check()

    def test_positive_numeric_cannot_be_dropped_or_relabelled_clear(self):
        self.make_positive()
        positive = self.record['positive_actual_Common'].pop()
        with self.assertRaises(ValueError): self.check()
        self.record['positive_actual_Common'] = [positive]
        self.record['finite_trial_material_clear'] = True
        with self.assertRaises(ValueError): self.check()

    def test_missing_changed_or_escaped_positive_STEP_rejected(self):
        self.make_positive()
        step = self.record['positive_actual_Common'][0]['actual_Common_STEP']
        original = dict(step)
        for name in ('../outside.step', str(self.directory/'absolute.step'), 'missing.step'):
            with self.subTest(name=name):
                step['path'] = name
                with self.assertRaises(ValueError): self.check()
        step.update(original)
        (self.directory/step['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError): self.check()

    def test_symlink_positive_STEP_rejected(self):
        self.make_positive()
        step = self.record['positive_actual_Common'][0]['actual_Common_STEP']
        actual = self.directory/step['path']
        link = self.directory/'linked.step'; link.symlink_to(actual)
        step['path'] = link.name
        with self.assertRaises(ValueError): self.check()

    def test_nested_error_and_export_failure_never_resumes(self):
        for extra in ({'evaluation_failed': True}, {'diagnostic': {'error': 'kernel failure'}}, {'budget_exceeded': True}):
            with self.subTest(extra=extra):
                altered = copy.deepcopy(self.record)
                altered['actual_native_changed_pairs'][0].update(extra)
                with self.assertRaises(ValueError): self.check(altered)
        self.make_positive()
        self.record['positive_actual_Common'][0]['STEP_export_failure'] = 'disk failure'
        with self.assertRaises(ValueError): self.check()

    def test_wrong_HEAD_runtime_or_study_source_after_rejected(self):
        with self.assertRaises(ValueError): self.check(dict(self.record, source_commit='b'*40))
        altered = copy.deepcopy(self.record); altered['identity_after']['environment']['passed'] = False
        with self.assertRaises(ValueError): self.check(altered)
        altered = copy.deepcopy(self.record); altered['study_source_sha256_after'][reader.SOURCE_FILES[0]] = 'f'*64
        with self.assertRaises(ValueError): self.check(altered)

    def test_wrong_baseline_bytes_or_actual_canonical_baseline_pair_rejected(self):
        with self.baseline_path.open('a') as stream: stream.write(' ')
        with self.assertRaises(ValueError): self.check()
        self.write_baseline()
        self.baseline['pairs'][0]['gap_lower_mm'] = -.1
        self.write_baseline()
        self.record['baseline_report']['sha256'] = reader.sha(self.baseline_path)
        with self.assertRaises(ValueError): self.check()

    def test_wrong_trial_offsets_or_independent_flank_scope_rejected(self):
        altered = copy.deepcopy(self.record); altered['trial_inputs']['KEY_offset_mm'] *= .5
        with self.assertRaises(ValueError): self.check(altered)
        altered = copy.deepcopy(self.record); altered['scope']['slot_flanks'] = [-1., 1.]
        with self.assertRaises(ValueError): self.check(altered)
        altered = copy.deepcopy(self.record); altered['scope']['slot_flanks'] = [False, False]
        with self.assertRaises(ValueError): self.check(altered)

    def test_missing_whole_material_factory_crosscheck_rejected(self):
        self.record['pose_record']['in_domain_factory_crosscheck']['bidirectional_material_difference_mm3'].pop(self.names[0])
        with self.assertRaises(ValueError): self.check()

    def test_original_profile_rejections_and_noncanonical_scope_are_required(self):
        with self.assertRaises(ValueError): self.check(dict(self.record, existing_profile_rejections=[]))
        for flag in reader.FALSE_FLAGS:
            with self.subTest(flag=flag):
                with self.assertRaises(ValueError): self.check(dict(self.record, **{flag: True}))

    def test_old_stdout_or_previous_full_report_schema_cannot_resume(self):
        for altered in ({'trial': self.label, 'native_pairs': 3396, 'positive_pairs': 0},
                        dict(self.record, schema='razr-complete-KEY-endpoint-outside-finite-diagnostic-v1')):
            with self.assertRaises(ValueError): self.check(altered)

    def test_json_reader_rejects_duplicate_keys_and_nonfinite_literals(self):
        path = self.directory/'bad.json'
        for value in ('{"status":"partial","status":"complete"}', '{"x":NaN}', '{"x":Infinity}'):
            path.write_text(value)
            with self.assertRaises(ValueError): reader.read_json(path)

    def test_supported_plateau_recomputed_from_complete_face_pin_and_original_profiles(self):
        self.make_supported_plateau()
        result = self.check()
        self.assertEqual(result['original_profile_input']['sha256'], self.profile_digest)
        self.assertFalse(result['CAD_executed_by_validator'])

    def test_forged_positive_margins_cannot_hide_actual_floor_interval_gap(self):
        plateau = self.make_supported_plateau()
        floor = plateau['rows'][0]['floor_candidates'][0]
        q = [.05, .2]
        e = floor['e_extent_mm']
        floor.update(q_extent_mm=q, area_mm2=(e[1]-e[0])*(q[1]-q[0]),
                     vertices_eqr_mm=[[a, b, self.profiles[('L', 0)]['floor_height']]
                                     for a, b in itertools.product(e, q)],
                     center_eqr_mm=[(e[0]+e[1])/2, (q[0]+q[1])/2, self.profiles[('L', 0)]['floor_height']])
        self.assertGreater(min(plateau['rows'][0]['finite_floor_q_edge_margins_mm']), 0.)
        with self.assertRaisesRegex(ValueError, 'edge margins'): self.check()

    def test_plateau_interval_and_overlap_summaries_must_match_raw_extents(self):
        self.make_supported_plateau()
        for key, value in (('negative_KEY_interval_mm', [-.001, 0.]),
                           ('contact_q_interval_mm', [0., .001]),
                           ('contact_e_overlap_mm', .8),
                           ('finite_floor_q_edge_margins_mm', [True, 1.])):
            with self.subTest(key=key):
                altered = copy.deepcopy(self.record)
                altered['pose_record']['native_plateau_contact_extension']['rows'][0][key] = value
                with self.assertRaises(ValueError): self.check(altered)
        self.record['pose_record']['native_plateau_contact_extension']['all_four_current_native_floors_support_the_declared_negative_q_contact'] = False
        with self.assertRaises(ValueError): self.check()

    def test_floor_rectangle_requires_actual_vertices_wires_edges_area_and_plane(self):
        self.make_supported_plateau()
        for key, value in (('wire_count', 2), ('edge_geometry_types', ['LINE']*3+['CIRCLE']),
                           ('area_mm2', .5), ('normal_xyz', [1., 0., 0.]),
                           ('center_eqr_mm', [-.4, .05, 9.]), ('q_extent_mm', [False, .2])):
            with self.subTest(key=key):
                altered = copy.deepcopy(self.record)
                altered['pose_record']['native_plateau_contact_extension']['rows'][0]['floor_candidates'][0][key] = value
                with self.assertRaises(ValueError): self.check(altered)
        altered = copy.deepcopy(self.record)
        vertices = altered['pose_record']['native_plateau_contact_extension']['rows'][0]['floor_candidates'][0]['vertices_eqr_mm']
        vertices[0] = vertices[1]
        with self.assertRaises(ValueError): self.check(altered)

    def test_pin_world_axis_radius_and_actual_endpoints_must_match(self):
        self.make_supported_plateau()
        for key, value in (('axis_direction_xyz', [1., 0., 0.]), ('radius_mm', .2),
                           ('cylinder_location_xyz', [0., 0., 0.]), ('e_extent_mm', [-.5, -.1]),
                           ('pin_q_mm', .1), ('full_pin_outside_STOP_mm3', -1e-12)):
            with self.subTest(key=key):
                altered = copy.deepcopy(self.record)
                altered['pose_record']['native_plateau_contact_extension']['rows'][0]['pin_candidates'][0][key] = value
                with self.assertRaises(ValueError): self.check(altered)

    def test_unsupported_complete_raw_plateau_remains_finite_diagnostic_without_contact_claim(self):
        plateau = self.make_supported_plateau()
        row = plateau['rows'][0]
        row['pin_candidates'][0]['full_pin_outside_STOP_mm3'] = 2e-7
        row['native_plateau_extension_supported'] = False
        plateau['all_four_current_native_floors_support_the_declared_negative_q_contact'] = False
        result = self.check()
        self.assertTrue(result['completed_trial_resumable'])
        self.assertFalse(result['physical_qualification'])
        row['native_plateau_extension_supported'] = True
        with self.assertRaises(ValueError): self.check()

    def test_STOW_factory_crosscheck_uses_exact_quarter_original_plateau_not_ramp(self):
        cam = (.425-.4)*math.hypot(1., 12./79.75)
        half = cam+(.425-.4)*math.sqrt(2.)
        for inward in (.03, .001, False):
            with self.subTest(inward=inward):
                altered = copy.deepcopy(self.record)
                altered['pose_record']['in_domain_factory_crosscheck'].update(
                    KEY_offset_mm=inward, crosshead_offset_mm=inward*cam/half)
                with self.assertRaises(ValueError): self.check(altered)

    def test_scope_zero_scalars_cannot_be_boolean(self):
        for field in ('slide_mm', 'descent_mm'):
            altered = copy.deepcopy(self.record)
            altered['scope'][field] = False
            with self.assertRaises(ValueError): self.check(altered)

    def test_original_profiles_must_be_bound_to_current_identity(self):
        altered = copy.deepcopy(self.current)
        altered['head_bound_source_sha256'][reader.PROFILE_INPUT] = 'f'*64
        with self.assertRaises(ValueError): reader._original_profiles(altered)


if __name__ == '__main__':
    unittest.main()
