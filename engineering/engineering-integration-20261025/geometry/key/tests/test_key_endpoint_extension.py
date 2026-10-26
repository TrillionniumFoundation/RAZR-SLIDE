"""Pure finite-diagnostic contract tests; no CAD geometry is executed."""
import importlib.util
import itertools
import json
import os
from pathlib import Path
import signal
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('endpoint_probe', ROOT/'integration/probe_key_endpoint_extension.py')
probe = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(probe)
RUNNER_SPEC = importlib.util.spec_from_file_location('endpoint_runner', ROOT/'run_key_endpoint_trials.py')
runner = importlib.util.module_from_spec(RUNNER_SPEC); RUNNER_SPEC.loader.exec_module(runner)


MOVING_ROLES = ('KEY', 'CROSSHEAD', 'CROSSHEAD_TUBE_BOTTOM_CAP', 'KEY_FOLLOWER_LOWER_FLANGE',
                'TELESCOPE_1', 'TELESCOPE_1_BOTTOM_CAP', 'TELESCOPE_2', 'TELESCOPE_2_BOTTOM_CAP',
                'TELESCOPE_3', 'TELESCOPE_3_CORE_BOTTOM_SHOULDER', 'TELESCOPE_3_CAM_LOWER_FLANGE',
                'TELESCOPE_3_CAM_UPPER_FLANGE')


class FakeMaterial:
    def __init__(self, name, offset=(0., 0., 0.)):
        self.name, self.offset = name, offset

    def translate(self, vector):
        return FakeMaterial(self.name, tuple(a+b for a, b in zip(self.offset, vector)))


def names(count=154):
    moving = [side+'_'+role for side in 'LR' for role in MOVING_ROLES]
    # These retained mechanisms must not accidentally follow the offset groups.
    fixed = ['L_STOP_0', 'R_STOP_1', 'L_SPRING_0_OD_TOL_ENVELOPE', 'R_PAWL', 'B_SHELL']
    return moving+fixed+['synthetic_fixed_%03d' % i for i in range(count-len(moving)-len(fixed))]


class EndpointProbeTests(unittest.TestCase):
    def test_correlated_native_slot_constraints_reject_the_independent_box_corner(self):
        cam, yoke, half = probe.clearance_constants()
        parts = {name: FakeMaterial(name) for name in names()}
        # Both scalar bounds can hold while the actual coupled groove does not.
        self.assertLessEqual(abs(-cam), cam)
        self.assertLessEqual(abs(half), half)
        self.assertGreater(abs(-cam-half), yoke)
        with self.assertRaisesRegex(ValueError, 'coupled native groove'):
            probe.rigid_trial(parts, half, -cam)
        probe.rigid_trial(parts, half, cam)
        probe.rigid_trial(parts, -half, -cam)

    def test_all_six_declared_trials_lie_outside_profile_but_inside_coupled_slots(self):
        cam, yoke, half = probe.clearance_constants()
        trials = probe.endpoint_trials('STOW')+probe.endpoint_trials('OPEN')
        self.assertEqual(len(trials), 6)
        self.assertEqual(len({row['label'] for row in trials}), 6)
        for row in trials:
            dq, dx = row['KEY_offset_mm'], row['crosshead_offset_mm']
            q = row['nominal_q_mm']+dq
            self.assertTrue(q < 0. or q > 12.)
            self.assertLessEqual(abs(dx), cam+1e-15)
            self.assertLessEqual(abs(dx-dq), yoke+1e-15)
        with self.assertRaises(ValueError): probe.endpoint_trials('PREDOCK')

    def test_complete_changed_pair_partition_preserves_all_fixed_reused_pairs(self):
        for count, expected in ((154, 3396), (161, 3564)):
            values = names(count)
            changed, fixed = probe.pair_partition(values)
            moving = probe.moving_inventory(values)
            self.assertEqual(len(moving), 24)
            self.assertEqual(len(changed), expected)
            self.assertFalse(set(changed) & set(fixed))
            self.assertEqual(set(changed) | set(fixed), set(itertools.combinations(sorted(values), 2)))
            self.assertTrue(all(a not in moving and b not in moving for a, b in fixed))
            self.assertTrue(all(a in moving or b in moving for a, b in changed))

    def test_one_missing_captured_flange_or_repeated_part_cannot_pass_complete_inventory(self):
        values = names()
        for missing in ('R_TELESCOPE_3_CAM_UPPER_FLANGE', 'L_KEY_FOLLOWER_LOWER_FLANGE'):
            with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, 'complete moving'):
                probe.pair_partition([v for v in values if v != missing])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            probe.pair_partition(values+[values[0]])

    def test_key_and_complete_crosshead_groups_follow_distinct_handed_motion_laws(self):
        parts = {name: FakeMaterial(name) for name in names()}
        moved = probe.rigid_trial(parts, .01, .005)
        self.assertEqual(set(moved), set(parts))
        for name in parts:
            if name.endswith('_KEY'):
                self.assertEqual(moved[name].offset, (0., .01, 0.))
            elif name in probe.moving_inventory(parts):
                self.assertEqual(moved[name].offset, (-.005 if name.startswith('L_') else .005, 0., 0.))
            else:
                self.assertIs(moved[name], parts[name])

    def test_invalid_or_nonfinite_offsets_are_not_evidence(self):
        parts = {name: FakeMaterial(name) for name in names()}
        for value in (True, float('nan'), float('inf'), -.1, '0.0'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                probe.rigid_trial(parts, value, 0.)

    def test_native_contact_inverse_preserves_handed_axes_and_the_nominal_key_offset(self):
        expected = (-.4, .8, 1.04)
        for side, sign in (('L', -1.), ('R', 1.)):
            world = (sign*(23.85+expected[2]), 14.8+12.+expected[1], 4.2+expected[0])
            actual = probe.contact_coordinates(side, world, 12.)
            for a, b in zip(actual, expected): self.assertAlmostEqual(a, b, places=13)

    def test_witness_export_failure_retains_actual_positive_volume_and_error(self):
        row = {'a': 'L_KEY', 'b': 'synthetic_fixed', 'common_mm3': .125,
               'method': 'native_common', 'rejected': True}
        def broken_export(): raise OSError('synthetic full output volume')
        positives = []
        failure = probe.retain_positive(row, positives, broken_export)
        self.assertEqual(len(positives), 1)
        self.assertEqual(positives[0]['common_mm3'], .125)
        self.assertTrue(positives[0]['rejected'])
        self.assertIn('synthetic full output volume', positives[0]['STEP_export_failure'])
        self.assertEqual(failure['failure_stage'], 'positive_Common_STEP_export')
        self.assertEqual(failure['actual_common_mm3_preserved'], .125)
        self.assertNotIn('actual_Common_STEP', positives[0])
        self.assertNotIn('evaluation_failed', row)
        with self.assertRaisesRegex(ValueError, 'actual positive'):
            probe.retain_positive({**row, 'common_mm3': 0.}, positives, broken_export)


class CheckpointTests(unittest.TestCase):
    def report(self, pairs):
        report = probe.initial_report('STOW_OUTSIDE_HALF_BAND', '0'*40,
                                      ROOT/'integration/probe_key_endpoint_extension.py')
        report['expected_changed_pairs'] = [list(pair) for pair in pairs]
        report['status'] = 'evaluating'
        return report

    def test_initial_checkpoint_preserves_complete_changed_and_fixed_inventory(self):
        changed, fixed = probe.pair_partition(names())
        report = self.report(changed)
        report['complete_participant_names'] = sorted(names())
        report['reused_unchanged_pairs'] = [list(pair) for pair in fixed]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'report.json'
            probe.Checkpoint(report, path).save()
            raw = json.loads(path.read_text())
            self.assertEqual(len(raw['pending_changed_pairs']), 3396)
            self.assertEqual(len(raw['reused_unchanged_pairs']), 8385)
            self.assertEqual(raw['processed_pair_count'], 0)
            self.assertFalse(raw['execution_completed'])
            self.assertFalse(raw['finite_trial_material_clear'])

    def test_duplicate_or_skipped_raw_pair_cannot_be_written_as_a_prefix(self):
        pairs = [('A', 'B'), ('A', 'C'), ('B', 'C')]
        for bad in ([pairs[0], pairs[0]], [pairs[1]]):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as tmp:
                report = self.report(pairs)
                report['actual_native_changed_pairs'] = [{'a': a, 'b': b} for a, b in bad]
                with self.assertRaisesRegex(ValueError, 'processed prefix'):
                    probe.Checkpoint(report, Path(tmp)/'report.json').save()
                self.assertFalse((Path(tmp)/'report.json').exists())

    def test_positive_numeric_pair_is_durable_before_failed_witness_export(self):
        pair = ('L_KEY', 'synthetic_fixed')
        report = self.report([pair])
        row = {'a': pair[0], 'b': pair[1], 'common_mm3': .125,
               'method': 'native_common', 'axis_gap_lower_mm': 0., 'rejected': True}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'report.json'
            checkpoint = probe.Checkpoint(report, path)
            checkpoint.save()
            report['actual_native_changed_pairs'].append(row)
            def failing_export():
                durable = json.loads(path.read_text())
                self.assertEqual(durable['actual_native_changed_pairs'], [row])
                self.assertEqual(durable['positive_actual_Common'], [row])
                self.assertFalse(durable['execution_completed'])
                raise OSError('synthetic export failure after durable numeric evidence')
            failure = probe.retain_positive(row, report['positive_actual_Common'], failing_export, checkpoint.save)
            report['evaluation_failures'].append(failure)
            checkpoint.save()
            raw = json.loads(path.read_text())
            self.assertEqual(raw['positive_actual_Common'][0]['common_mm3'], .125)
            self.assertEqual(raw['evaluation_failures'][0]['actual_common_mm3_preserved'], .125)
            self.assertEqual(raw['processed_pair_count'], 1)
            self.assertEqual(raw['pending_changed_pairs'], [])
            self.assertFalse(raw['diagnostic_execution_checks_passed'])

    def test_atomic_replace_failure_keeps_original_bytes_and_removes_only_temporary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'report.json'
            probe.atomic_json(path, {'generation': 1})
            original = path.read_bytes()
            with mock.patch.object(probe.os, 'replace', side_effect=OSError('synthetic replace refusal')):
                with self.assertRaises(OSError):
                    probe.atomic_json(path, {'generation': 2})
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ['report.json'])

    def test_nonfinite_serialization_cannot_destroy_last_valid_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'report.json'
            probe.atomic_json(path, {'common_mm3': .1})
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                probe.atomic_json(path, {'common_mm3': float('nan')})
            self.assertEqual(path.read_bytes(), original)

    def test_completed_pair_prefix_still_cannot_claim_postflight_completion(self):
        report = self.report([('A', 'B'), ('A', 'C')])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'report.json'
            checkpoint = probe.Checkpoint(report, path)
            checkpoint.save()
            for a, b in report['expected_changed_pairs']:
                report['actual_native_changed_pairs'].append({'a': a, 'b': b, 'common_mm3': 0., 'rejected': False})
                checkpoint.save()
            raw = json.loads(path.read_text())
            self.assertEqual(raw['checkpoint_generation'], 3)
            self.assertEqual(raw['processed_pair_count'], 2)
            self.assertEqual(raw['pending_changed_pairs'], [])
            self.assertEqual(raw['status'], 'evaluating')
            self.assertFalse(raw['execution_completed'])
            self.assertFalse(raw['source_bytes_unchanged'])

    def test_source_closure_rejects_missing_or_linked_reviewed_file_and_detects_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in probe.STUDY_SOURCE_PATHS:
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(name)
            before = probe.study_source_snapshot(root)
            self.assertEqual(set(before), set(probe.STUDY_SOURCE_PATHS))
            path = root/probe.STUDY_SOURCE_PATHS[0]
            path.write_text('changed')
            self.assertNotEqual(before, probe.study_source_snapshot(root))
            path.unlink()
            with self.assertRaisesRegex(ValueError, 'missing or linked'):
                probe.study_source_snapshot(root)
            path.symlink_to(root/probe.STUDY_SOURCE_PATHS[1])
            with self.assertRaisesRegex(ValueError, 'missing or linked'):
                probe.study_source_snapshot(root)

    def test_trial_selector_rejects_duplicate_unknown_or_reordered_trials(self):
        self.assertEqual(probe.selected_trials(probe.TRIAL_LABELS), list(probe.TRIAL_LABELS))
        self.assertEqual(probe.selected_trials([probe.TRIAL_LABELS[2], probe.TRIAL_LABELS[5]]),
                         [probe.TRIAL_LABELS[2], probe.TRIAL_LABELS[5]])
        for values in ([], [probe.TRIAL_LABELS[0]]*2, list(reversed(probe.TRIAL_LABELS)), ['STOW_ARBITRARY']):
            with self.subTest(values=values), self.assertRaisesRegex(ValueError, 'canonical order'):
                probe.selected_trials(values)


class RunnerContractTests(unittest.TestCase):
    def fake_process(self):
        process = mock.Mock()
        process.pid = 424242
        process.poll.return_value = None
        process.wait.return_value = 0
        return process

    def test_resource_reader_exception_stops_and_reaps_the_child(self):
        process = self.fake_process()
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(runner.subprocess, 'Popen', return_value=process), \
                mock.patch.object(runner, 'resources', side_effect=OSError('synthetic missing cgroup')), \
                mock.patch.object(runner.os, 'killpg') as kill:
            with self.assertRaisesRegex(OSError, 'missing cgroup'):
                runner.run(['fake-no-child'], Path(tmp)/'log', {}, time.monotonic()+10, root=tmp, output=tmp)
            kill.assert_called_once_with(process.pid, signal.SIGTERM)
            process.wait.assert_called_once()

    def test_deadline_before_Popen_cannot_claim_native_started(self):
        callback = mock.Mock()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(runner.subprocess, 'Popen') as popen:
            with self.assertRaisesRegex(ValueError, 'budget exhausted before command'):
                runner.run(['fake-no-child'], Path(tmp)/'log', {}, 0., root=tmp, output=tmp, on_started=callback)
            callback.assert_not_called()
            popen.assert_not_called()

    def test_started_callback_failure_preserves_error_and_reaps_actual_child(self):
        process = self.fake_process()
        callback = mock.Mock(side_effect=OSError('synthetic start receipt failure'))
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(runner.subprocess, 'Popen', return_value=process), \
                mock.patch.object(runner.os, 'killpg') as kill:
            with self.assertRaisesRegex(OSError, 'start receipt failure'):
                runner.run(['fake-no-child'], Path(tmp)/'log', {}, time.monotonic()+10,
                           root=tmp, output=tmp, on_started=callback)
            callback.assert_called_once_with(process.pid)
            kill.assert_called_once_with(process.pid, signal.SIGTERM)
            process.wait.assert_called_once()

    def test_runtime_memory_guard_preserves_original_125_and_reaps(self):
        process = self.fake_process()
        budget = {'writeable_disk_bytes': 1000*1024**2,
                  'shared_unreclaimable_memory_bytes': int(6.8*1024**3)+1}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(runner.subprocess, 'Popen', return_value=process), \
                mock.patch.object(runner, 'resources', return_value=budget), \
                mock.patch.object(runner.os, 'killpg') as kill:
            result = runner.run(['fake-no-child'], Path(tmp)/'log', {}, time.monotonic()+10, root=tmp, output=tmp)
            self.assertEqual(result['exit_code'], 125)
            self.assertEqual(result['stop_event']['kind'], 'shared_runtime_resource_budget')
            kill.assert_called_once_with(process.pid, signal.SIGTERM)
            process.wait.assert_called_once()

    def test_shared_trial_deadline_includes_every_child_and_kills_on_expiry(self):
        process = self.fake_process()
        budget = {'writeable_disk_bytes': 1000*1024**2, 'shared_unreclaimable_memory_bytes': 0}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(runner.subprocess, 'Popen', return_value=process), \
                mock.patch.object(runner, 'resources', return_value=budget), \
                mock.patch.object(runner.time, 'monotonic', side_effect=[0., 2., 2.]), \
                mock.patch.object(runner.os, 'killpg') as kill:
            result = runner.run(['fake-no-child'], Path(tmp)/'log', {}, 1., root=tmp, output=tmp)
            self.assertEqual(result['exit_code'], 124)
            kill.assert_called_once_with(process.pid, signal.SIGKILL)
            process.wait.assert_called_once()

    def test_already_exited_kill_race_is_reaped_without_masking_original_error(self):
        process = self.fake_process()
        with mock.patch.object(runner.os, 'killpg', side_effect=ProcessLookupError):
            runner.stop(process, time.monotonic()+10)
        process.wait.assert_called_once()

    def test_resume_bundle_locator_rejects_ambiguous_or_stdout_only_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'native.log').write_text('{"native_pairs":3396}\n')
            with self.assertRaisesRegex(ValueError, 'original raw report'):
                runner.existing_bundle(root)
            (root/'report.json').write_text('{}')
            self.assertEqual(runner.existing_bundle(root), root/'report.json')
            (root/'native').mkdir()
            (root/'native/report.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'exactly one'):
                runner.existing_bundle(root)


if __name__ == '__main__': unittest.main()
