"""New assembly/admission and acquisition integrity regressions.

Numerical acquisition fixtures are created in temporary directories and are
explicitly synthetic; they are never retained as physical specimen records.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
FOLLOW = ROOT/'engineering/product-integration-20261018/physical-test-followon-20261019'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


motion = module('razr_motion_log_followon', FOLLOW/'analyse_motion_log.py')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


PHASES = ['LOCKED_BASELINE', 'UNLOCK_LEFT', 'UNLOCK_RIGHT', 'SLIDE_OUT', 'SEAT',
    'HOLD_LEFT_INSTALL', 'HOLD_RIGHT_INSTALL', 'SUPPORT_INSTALL', 'HANDS_OFF_OPEN',
    'SUPPORT_REMOVE', 'HOLD_RIGHT_REMOVE', 'HOLD_LEFT_REMOVE', 'UNSEAT',
    'SLIDE_IN', 'RELOCK_RIGHT', 'RELOCK_LEFT', 'LOCKED_FINAL']


class MotionAcquisition(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='razr-synthetic-acquisition-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repository = self.base/'repository'; (self.repository/'design').mkdir(parents=True)
        self.evidence = self.base/'acquisition'; self.evidence.mkdir()
        for name in ('product_geometry.json', 'product_interfaces.json'):
            (self.repository/'design'/name).write_text('{"synthetic_fixture_only": true}\n')
        original = self.evidence/'original.txt'
        original.write_text('Explicit synthetic calibration / phase / frame / sync fixture. No physical observation.\n')
        self.original_ref = {'path': original.name, 'sha256': sha(original)}
        channels = {**motion.MANDATORY, 'fpc_c01_ohm': 'ohm'}
        refs = {}
        for channel, unit in channels.items():
            p = self.evidence/(channel+'.calibration.json')
            gain, offset, error = (2., -.1, .02) if channel == 'operator_force_N' else (1., 0., .01)
            if unit == 'ohm': error = .1
            record = {'schema': 'razr-linear-sensor-calibration-v1', 'execution_kind': 'synthetic_fixture',
                'instrument_id': 'synthetic-'+channel, 'recorded_at_utc': '2026-10-19T00:00:00Z',
                'output_unit': unit, 'gain': gain, 'offset': offset,
                'absolute_error_bound': error, 'valid_raw_range': [-1000., 1000.],
                'original_evidence': [self.original_ref], 'calibration_method': 'synthetic arithmetic regression only'}
            p.write_text(json.dumps(record))
            refs[channel] = {'path': p.name, 'sha256': sha(p)}
        self.rows = []
        for i, phase in enumerate(PHASES):
            y = 79.75 if 3 <= i <= 12 else 0.
            z = 0. if 4 <= i <= 11 else 8.2
            row = {'t_s': float(i), 'cycle': 1, 'phase': phase,
                'hand_contact': 0 if phase == 'HANDS_OFF_OPEN' else 1,
                'left_y_mm': y, 'right_y_mm': y, 'left_z_mm': z, 'right_z_mm': z,
                'operator_force_N': 2. if phase == 'SLIDE_OUT' else .1, 'fpc_c01_ohm': 1.}
            self.rows.append(row)
            if phase == 'HANDS_OFF_OPEN':
                self.rows.extend([{**row, 't_s': i+.1, 'left_y_mm': y+.02, 'right_y_mm': y+.02, 'fpc_c01_ohm': 1.95},
                                  {**row, 't_s': i+.2, 'left_y_mm': y+.04, 'right_y_mm': y+.04, 'fpc_c01_ohm': 3.}])
        self.manifest_path = self.evidence/'acquisition.json'
        self.manifest = {'schema': 'razr-unpowered-motion-acquisition-v1',
            'execution_kind': 'synthetic_fixture', 'specimen_id': 'SYNTHETIC-UNIT-TEST-NO-HARDWARE',
            'recorded_at_utc': '2026-10-19T00:00:00Z',
            'design_binding': {'git_commit': 'a'*40, 'files_sha256': {
                'design/product_geometry.json': sha(self.repository/'design/product_geometry.json'),
                'design/product_interfaces.json': sha(self.repository/'design/product_interfaces.json')}},
            'phase_and_hand_contact_evidence': self.original_ref,
            'coordinate_frame_evidence': self.original_ref,
            'timebase': {'kind': 'monotonic', 'unit': 's', 'source': 'synthetic counter',
                'maximum_gap_s': 1.1, 'alignment_error_bound_s': .001, 'synchronization_evidence': self.original_ref},
            'planned_phase_order': PHASES, 'channels': refs,
            'continuity_threshold_ohm': 2., 'continuity_threshold_evidence': self.original_ref}
        self.write_rows()

    def write_manifest(self):
        self.manifest_path.write_text(json.dumps(self.manifest))

    def write_rows(self):
        p = self.evidence/'motion.csv'
        with p.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.rows[0]))
            writer.writeheader(); writer.writerows(self.rows)
        self.manifest['raw_csv'] = {'path': p.name, 'sha256': sha(p)}
        self.write_manifest()

    def analyse(self):
        return motion.analyse(self.manifest_path, self.repository)

    def test_calibrated_force_return_drift_and_resistance_uncertainty(self):
        report = self.analyse()
        self.assertEqual(report['execution_kind'], 'synthetic_fixture')
        self.assertFalse(report['physical_execution_declared_by_record'])
        self.assertEqual(report['phase_label_complete_cycles'], 1)
        self.assertAlmostEqual(report['external_operator_force_N']['maximum'], 3.9)
        self.assertAlmostEqual(report['cycles'][0]['return_offset_mean_y_mm'], 0.)
        hold = report['cycles'][0]['hands_off_segments'][0]
        self.assertAlmostEqual(hold['maximum_mean_y_drift_from_first_sample_mm'], .04)
        self.assertAlmostEqual(hold['conservative_displacement_error_bound_mm']['y'], .02)
        self.assertEqual([x['classification'] for x in report['FPC_threshold_crossings']],
                         ['uncertain_at_error_bound', 'above_even_with_error'])
        self.assertIsNone(report['optional_sampled_observations']['fpc_c26_ohm'])
        self.assertIsNone(report['structural_interpretation']['actual_KEY_axial_and_lateral_load_N'])
        self.assertFalse(report['physical_phone_verified'])

    def test_changed_raw_csv_is_rejected(self):
        with (self.evidence/'motion.csv').open('a') as stream: stream.write('\n')
        with self.assertRaisesRegex(ValueError, 'evidence bytes changed'):
            self.analyse()

    def test_monotonic_clock_and_calibrated_range_are_enforced(self):
        self.rows[4]['t_s'] = self.rows[3]['t_s']; self.write_rows()
        with self.assertRaisesRegex(ValueError, 'strictly increasing'):
            self.analyse()
        self.rows[4]['t_s'] = 4.; self.rows[3]['operator_force_N'] = 1001.; self.write_rows()
        with self.assertRaisesRegex(ValueError, 'outside calibrated range'):
            self.analyse()

    def test_gap_splits_hands_off_records_and_is_retained(self):
        self.manifest['timebase']['maximum_gap_s'] = .15
        self.rows[10]['t_s'] = 8.4; self.write_rows()
        report = self.analyse()
        self.assertGreater(len(report['sampling']['gap_exceedances']), 0)
        segments = report['cycles'][0]['hands_off_segments']
        self.assertEqual([x['sample_count'] for x in segments], [2, 1])
        self.assertFalse(report['sampling']['absence_of_unsampled_dropout_proved'])

    def test_physical_label_cannot_reuse_synthetic_calibration(self):
        self.manifest['execution_kind'] = 'physical'; self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'cannot be interchanged'):
            self.analyse()

    def test_physical_record_must_bind_real_commit_blob_not_dirty_workspace(self):
        # A disposable local Git repository provides a real old revision.
        subprocess.run(['git', 'init', '-q', str(self.repository)], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(self.repository), 'add', 'design'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(self.repository), '-c', 'user.name=Synthetic Test',
            '-c', 'user.email=synthetic-test@example.invalid', 'commit', '-q', '--no-verify', '--no-gpg-sign',
            '-m', 'Synthetic test fixture only'], check=True, capture_output=True)
        commit = subprocess.check_output(['git', '-C', str(self.repository), 'rev-parse', 'HEAD'], text=True).strip()
        self.manifest['execution_kind'] = 'physical'
        for ref in self.manifest['channels'].values():
            p = self.evidence/ref['path']; record = json.loads(p.read_text())
            record['execution_kind'] = 'physical'; p.write_text(json.dumps(record)); ref['sha256'] = sha(p)
        self.manifest['design_binding']['git_commit'] = commit
        # Workspace bytes and their declared digest agree, but this old commit
        # does not contain the changed geometry. That must be rejected.
        changed = self.repository/'design/product_geometry.json'; changed.write_text('{"new_synthetic_revision": true}\n')
        self.manifest['design_binding']['files_sha256']['design/product_geometry.json'] = sha(changed)
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'committed design bytes differ'):
            self.analyse()
        self.manifest['design_binding']['git_commit'] = '0'*40; self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'not an available Git commit'):
            self.analyse()

    def test_original_calibration_attachment_is_required(self):
        (self.evidence/'original.txt').unlink()
        with self.assertRaisesRegex(ValueError, 'missing'):
            self.analyse()

    def test_changed_design_and_escape_path_are_rejected(self):
        p = self.repository/'design/product_geometry.json'; saved = p.read_bytes()
        p.write_text('{"changed": true}')
        with self.assertRaisesRegex(ValueError, 'evidence bytes changed'):
            self.analyse()
        p.write_bytes(saved)
        self.manifest['coordinate_frame_evidence'] = {'path': '../outside.txt', 'sha256': 'a'*64}
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'relative descendant'):
            self.analyse()

    def test_overrange_missing_data_and_contradictory_hands_off_are_not_hidden(self):
        self.rows[3]['fpc_c01_ohm'] = 'OVER_RANGE'; self.rows[4]['fpc_c01_ohm'] = ''; self.write_rows()
        report = self.analyse()
        self.assertEqual(len(report['FPC_overrange_events']), 1)
        self.assertEqual(report['optional_sampled_observations']['fpc_c01_ohm']['missing_samples'], 2)
        self.rows[8]['hand_contact'] = 1; self.write_rows()
        with self.assertRaisesRegex(ValueError, 'contradicts'):
            self.analyse()


class CapturedFollowerAdmission(unittest.TestCase):
    def test_complete_split_assembly_restores_actual_native_geometry(self):
        study = module('razr_captured_follower_followon', FOLLOW/'captured_follower_assembly.py')
        with tempfile.TemporaryDirectory(prefix='razr-captured-follower-regression-') as td:
            r = study.run(ROOT/'integration/cam_coupling.py', Path(td)/'export', verify_native=True)
        self.assertEqual(len(r['original_axial_insertion_negative_controls']), 8)
        self.assertTrue(all(x['blocked'] for x in r['original_axial_insertion_negative_controls']))
        self.assertEqual(len(r['assembly_actions']), 12)
        self.assertFalse(any(x['rejected'] for x in r['assembly_actions']))
        self.assertEqual(r['split_parts_added_per_hand'], 7)
        self.assertEqual(r['original_nominal_geometry_changes_mm3'], {'added': 0., 'removed': 0.})
        self.assertEqual(len(r['source_template_comparisons']), 7)
        self.assertIsNone(r['joining']['selected_process'])
        self.assertFalse(r['manufacturing_go'])

    def test_changed_source_refuses_old_dimensional_reconstruction(self):
        study = module('razr_captured_follower_changed_identity', FOLLOW/'captured_follower_assembly.py')
        with tempfile.TemporaryDirectory(prefix='razr-changed-assembly-source-') as td:
            source = Path(td)/'cam_coupling.py'; source.write_text('# changed source\n')
            with self.assertRaisesRegex(ValueError, 'source changed'):
                study.run(source, Path(td)/'export')
            self.assertFalse((Path(td)/'export').exists())


if __name__ == '__main__':
    unittest.main()
