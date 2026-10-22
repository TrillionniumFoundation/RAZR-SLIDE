"""Temporary synthetic regressions; no retained file is physical evidence.

The physical-schema positive path uses fabricated fixture data only inside
TemporaryDirectory to exercise validation. It is never a project observation
and cannot promote manufacturing or whole-phone flags.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
FOLLOW = ROOT/'engineering/product-integration-20261018/physical-test-followon-20261019'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    item = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item)
    return item


motion = load('qualification_motion_test', FOLLOW/'analyse_motion_log.py')
contract = load('qualification_contract_test', FOLLOW/'qualification_contract.py')
PHASES = ['LOCKED_BASELINE', 'UNLOCK_LEFT', 'UNLOCK_RIGHT', 'SLIDE_OUT', 'SEAT',
    'HOLD_LEFT_INSTALL', 'HOLD_RIGHT_INSTALL', 'SUPPORT_INSTALL', 'HANDS_OFF_OPEN',
    'SUPPORT_REMOVE', 'HOLD_RIGHT_REMOVE', 'HOLD_LEFT_REMOVE', 'UNSEAT',
    'SLIDE_IN', 'RELOCK_RIGHT', 'RELOCK_LEFT', 'LOCKED_FINAL']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class QualificationContract(unittest.TestCase):
    def git(self, *args, date='2026-10-19T00:00:00Z'):
        env = os.environ.copy()
        env['GIT_AUTHOR_DATE'] = env['GIT_COMMITTER_DATE'] = date
        return subprocess.check_output(
            ['git', '-C', str(self.repo), '-c', 'user.name=Synthetic Qualification Test',
             '-c', 'user.email=synthetic-test@example.invalid',
             '-c', 'commit.gpgsign=false', *args], env=env, stderr=subprocess.STDOUT, text=True).strip()

    def write(self, relative, value):
        p = self.evidence/relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value) if isinstance(value, (dict, list)) else value)
        return {'path': relative, 'sha256': digest(p)}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='razr-synthetic-qualification-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base/'repository'; (self.repo/'design').mkdir(parents=True)
        self.evidence = self.base/'synthetic-evidence'; self.evidence.mkdir()
        files = ['design/product_geometry.json', 'design/product_interfaces.json']
        files += ['design/synthetic_' + role + '.json' for role in contract.REQUIRED_ROLES]
        for name in files:
            (self.repo/name).write_text('{"synthetic_fixture_only":true}\n')
        self.git('init', '-q')
        self.git('add', 'design')
        self.git('commit', '-qm', 'Synthetic initial identities only', '--no-verify')
        binding = {'git_commit': self.git('rev-parse', 'HEAD'),
                   'files_sha256': {name: digest(self.repo/name) for name in files},
                   'artifact_roles': {role: ['design/synthetic_' + role + '.json'] for role in contract.REQUIRED_ROLES}}
        self.raw_ref = self.write('synthetic-original.txt',
            'Synthetic unit fixture only; no instrument, specimen or physical observation exists.\n')
        self.calibrations = {}
        refs = {}
        for name, unit in {**motion.MANDATORY, **motion.OPTIONAL}.items():
            cal = {'schema': 'razr-linear-sensor-calibration-v1', 'execution_kind': 'synthetic_fixture',
                   'instrument_id': 'SYNTHETIC-' + name, 'recorded_at_utc': '2026-10-19T00:00:00Z',
                   'output_unit': unit, 'gain': 1., 'offset': 0., 'absolute_error_bound': .01,
                   'valid_raw_range': [-1000., 1000.], 'original_evidence': [self.raw_ref],
                   'calibration_method': 'SYNTHETIC UNIT TEST ONLY'}
            self.calibrations[name] = cal
            refs[name] = self.write(name + '.calibration.json', cal)
        self.rows = []
        for i, phase in enumerate(PHASES):
            for sample in range(3):
                y = 79.75 if 3 <= i <= 12 else 0.
                z = 0. if 4 <= i <= 11 else 8.2
                row = {'t_s': round((i * 3 + sample) * .1, 6), 'cycle': 1, 'phase': phase,
                       'hand_contact': 0 if phase == 'HANDS_OFF_OPEN' else 1,
                       'left_y_mm': y, 'right_y_mm': y, 'left_z_mm': z, 'right_z_mm': z,
                       'operator_force_N': 3. if phase == 'SLIDE_OUT' else .1,
                       'oled_tail_y_mm': y, 'oled_pull_force_N': 1.,
                       'oled_min_radius_mm': 5., 'fpc_min_radius_mm': 4.5}
                row.update({'fpc_c%02d_ohm' % j: 1. for j in range(1, 27)})
                self.rows.append(row)
        self.manifest = {
            'schema': 'razr-unpowered-motion-acquisition-v1', 'execution_kind': 'synthetic_fixture',
            'specimen_id': 'SYNTHETIC-UNIT-TEST-NO-HARDWARE',
            'recorded_at_utc': '2026-10-21T00:00:10Z',
            'acquisition_started_at_utc': '2026-10-21T00:00:00Z',
            'acquisition_ended_at_utc': '2026-10-21T00:00:10Z',
            'design_binding': binding, 'phase_and_hand_contact_evidence': self.raw_ref,
            'coordinate_frame_evidence': self.raw_ref,
            'timebase': {'kind': 'monotonic', 'unit': 's', 'source': 'synthetic monotonic counter',
                         'maximum_gap_s': .11, 'alignment_error_bound_s': .001,
                         'synchronization_evidence': self.raw_ref},
            'planned_phase_order': PHASES, 'channels': refs,
        }
        criteria = {}
        for metric, (unit, direction) in contract.METRICS.items():
            limits = {'minimum': 79., 'maximum': 80.} if direction == 'range' else (
                {'minimum': 4.} if direction == 'minimum' else {'maximum': 5.})
            if metric == 'stroke_z_mm': limits = {'minimum': 8., 'maximum': 8.4}
            criteria[metric] = {'unit': unit, **limits}
        self.plan = {
            'schema': contract.PLAN_SCHEMA, 'is_template': False, 'scope': 'unpowered_motion',
            'declared_at_utc': '2026-10-20T00:00:00Z',
            'approved_by': 'Synthetic unit test only', 'approval_evidence': [self.raw_ref],
            'design_binding': copy.deepcopy(binding), 'planned_phase_order': PHASES,
            'measurement_requirements': {'minimum_cycles': 1, 'minimum_samples_per_phase': 2,
                'minimum_hands_off_duration_s': .15, 'maximum_sampling_gap_s': .11,
                'maximum_alignment_error_s': .01},
            'criteria': criteria,
        }
        self.specimen = {
            'schema': contract.SPECIMEN_SCHEMA, 'is_template': False,
            'specimen_id': self.manifest['specimen_id'], 'execution_kind': 'synthetic_fixture',
            'design_binding': copy.deepcopy(binding),
            'role_observations': {role: {
                'part_or_lot_id': 'SYNTHETIC-' + role, 'method': 'SYNTHETIC UNIT TEST ONLY',
                'locator': 'synthetic attachment, all content', 'observed_at_utc': '2026-10-20T12:00:00Z',
                'design_paths': paths, 'original_evidence': [self.raw_ref]}
                for role, paths in binding['artifact_roles'].items()},
        }
        self.commit_plan()
        self.write_specimen()
        self.write_rows()
        self.review_root = self.base/'independent-synthetic-review'
        self.review_root.mkdir()
        (self.review_root/self.raw_ref['path']).write_bytes((self.evidence/self.raw_ref['path']).read_bytes())
        self.review = {
            'schema': contract.REVIEW_SCHEMA, 'is_template': False, 'scope': 'unpowered_motion',
            'conclusion': 'verified_preregistered_exact_plan',
            'reviewed_by': 'SYNTHETIC INDEPENDENT TEST REVIEWER',
            'reviewer_independent_of_acquisition': True,
            'verification_method': 'independently_reviewed_preregistration_document',
            'verified_registration_at_utc': '2026-10-20T00:00:00Z',
            'reviewed_at_utc': '2026-10-23T00:00:00Z',
            'verification_note': 'SYNTHETIC TEST ONLY; no real preregistration or reviewer exists.',
            'original_evidence': [self.raw_ref],
        }
        self.use_review = True
        self.refresh_review_binding = True

    def commit_plan(self, date='2026-10-20T00:00:00Z'):
        self.manifest['qualification_plan'] = self.write('qualification-plan.json', self.plan)
        path = 'design/synthetic_qualification_plan.json'
        (self.repo/path).write_bytes((self.evidence/'qualification-plan.json').read_bytes())
        self.git('add', path)
        self.git('commit', '-qm', 'Synthetic predeclared plan only', '--allow-empty', '--no-verify', date=date)
        self.manifest['qualification_plan_version'] = {
            'git_commit': self.git('rev-parse', 'HEAD'), 'path': path,
            'sha256': digest(self.repo/path)}

    def write_specimen(self):
        self.manifest['as_built_specimen_record'] = self.write('as-built.json', self.specimen)

    def write_rows(self):
        p = self.evidence/'motion.csv'
        with p.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.rows[0]))
            writer.writeheader(); writer.writerows(self.rows)
        self.manifest['raw_csv'] = {'path': p.name, 'sha256': digest(p)}
        self.write_manifest()

    def write_manifest(self):
        self.write('acquisition.json', self.manifest)

    def physical_schema_fixture(self):
        # This alters only temporary UNIT TEST bytes; no result is retained as
        # observed evidence. Positive validator paths must also be exercised.
        self.manifest['execution_kind'] = 'physical'
        self.specimen['execution_kind'] = 'physical'
        for name, calibration in self.calibrations.items():
            calibration['execution_kind'] = 'physical'
            self.manifest['channels'][name] = self.write(name + '.calibration.json', calibration)
        self.write_specimen()
        self.write_manifest()

    def write_review(self):
        if self.refresh_review_binding:
            self.review.update({
                'plan_sha256': self.manifest.get('qualification_plan', {}).get('sha256'),
                'specimen_id': self.manifest['specimen_id'],
                'design_binding_sha256': hashlib.sha256(json.dumps(
                    self.manifest['design_binding'], sort_keys=True, separators=(',', ':'),
                    allow_nan=False).encode()).hexdigest(),
                'acquisition_manifest_sha256': digest(self.evidence/'acquisition.json'),
            })
        path = self.review_root/'review.json'
        path.write_text(json.dumps(self.review))
        return path

    def analyse(self):
        self.write_manifest()
        review = self.write_review() if self.use_review else None
        return motion.analyse(self.evidence/'acquisition.json', self.repo, preregistration_review=review)

    def criterion(self, report, metric):
        return next(x for x in report['qualification']['criteria'] if x['metric'] == metric)

    def test_complete_sampled_contract_pass_does_not_release_hardware(self):
        self.physical_schema_fixture()
        r = self.analyse()
        self.assertEqual(r['qualification']['status'], 'pass')
        self.assertTrue(r['physical_cycle_acceptance_thresholds_applied'])
        self.assertFalse(r['qualification']['attachment_authenticity_independently_proved'])
        self.assertFalse(r['qualification']['manufacturing_go'])
        self.assertFalse(r['physical_phone_verified'])

    def test_synthetic_fixture_never_receives_physical_pass(self):
        r = self.analyse()
        self.assertEqual(r['qualification']['sampled_criteria_status'], 'pass')
        self.assertEqual(r['qualification']['status'], 'unknown')

    def test_legacy_observations_without_plan_remain_unknown(self):
        self.manifest.pop('qualification_plan')
        r = self.analyse()
        self.assertEqual(r['qualification']['status'], 'unknown')
        self.assertFalse(r['physical_cycle_acceptance_thresholds_applied'])

    def test_no_as_built_record_cannot_pass(self):
        self.physical_schema_fixture()
        self.manifest.pop('as_built_specimen_record')
        self.assertEqual(self.analyse()['qualification']['status'], 'unknown')

    def test_all_manufacturing_roles_must_be_bound(self):
        self.physical_schema_fixture()
        for target in (self.manifest['design_binding'], self.plan['design_binding'], self.specimen['design_binding']):
            target['artifact_roles'].pop('material')
        self.specimen['role_observations'].pop('material')
        self.commit_plan(); self.write_specimen()
        r = self.analyse()['qualification']
        self.assertEqual(r['status'], 'unknown')
        self.assertIn('material', r['missing_artifact_roles'])

    def test_exact_role_assignment_required_for_as_built_specimen(self):
        self.specimen['role_observations']['ep4']['design_paths'] = self.specimen['role_observations']['cad']['design_paths']
        self.write_specimen()
        with self.assertRaisesRegex(ValueError, 'exact assigned design'):
            self.analyse()

    def test_wrong_specimen_and_postdated_observation_rejected(self):
        self.specimen['specimen_id'] = 'OTHER'; self.write_specimen()
        with self.assertRaisesRegex(ValueError, 'different specimen'):
            self.analyse()
        self.specimen['specimen_id'] = self.manifest['specimen_id']
        self.specimen['role_observations']['cad']['observed_at_utc'] = '2026-10-22T00:00:00Z'
        self.write_specimen()
        with self.assertRaisesRegex(ValueError, 'postdates'):
            self.analyse()

    def test_missing_original_as_built_evidence_is_unknown(self):
        self.physical_schema_fixture()
        self.specimen['role_observations']['process']['original_evidence'] = []
        self.write_specimen()
        self.assertEqual(self.analyse()['qualification']['status'], 'unknown')

    def test_independently_reviewed_paper_plan_needs_no_git_version(self):
        self.physical_schema_fixture()
        self.manifest.pop('qualification_plan_version')
        self.assertEqual(self.analyse()['qualification']['status'], 'pass')

    def test_later_git_import_does_not_invalidate_reviewed_preregistration(self):
        self.physical_schema_fixture()
        self.commit_plan(date='2026-10-22T00:00:00Z')
        self.assertEqual(self.analyse()['qualification']['status'], 'pass')

    def test_early_local_git_date_alone_is_not_preregistration_verification(self):
        self.physical_schema_fixture()
        self.use_review = False
        r = self.analyse()['qualification']
        self.assertEqual(r['status'], 'unknown')
        self.assertIn('independent_preregistration_review_missing', r['blockers'])

    def test_manifest_cannot_select_its_own_independent_review(self):
        self.physical_schema_fixture()
        self.use_review = False
        self.manifest['preregistration_review'] = str(self.write_review())
        self.assertEqual(self.analyse()['qualification']['status'], 'unknown')

    def test_reviewed_controlled_version_is_supported(self):
        self.physical_schema_fixture()
        self.review['verification_method'] = 'observed_controlled_version_time'
        self.review['controlled_version'] = copy.deepcopy(self.manifest['qualification_plan_version'])
        r = self.analyse()['qualification']
        self.assertEqual(r['status'], 'pass')
        self.assertTrue(r['caller_supplied_review_attestation'])
        self.assertFalse(r['reviewer_identity_or_independence_authenticated_by_program'])

    def test_controlled_review_must_match_version(self):
        self.review['verification_method'] = 'observed_controlled_version_time'
        self.review['controlled_version'] = {}
        with self.assertRaisesRegex(ValueError, 'controlled plan version'):
            self.analyse()

    def test_stale_review_cannot_approve_changed_threshold_or_acquisition(self):
        self.physical_schema_fixture()
        self.write_review()
        self.refresh_review_binding = False
        self.plan['criteria']['operator_force_max_N']['maximum'] = 999.
        self.commit_plan()
        with self.assertRaisesRegex(ValueError, 'exact plan, acquisition and specimen'):
            self.analyse()

    def test_unverified_review_is_unknown(self):
        self.physical_schema_fixture()
        self.review['conclusion'] = 'unverified'
        self.assertEqual(self.analyse()['qualification']['status'], 'unknown')

    def test_self_review_or_missing_review_original_cannot_pass(self):
        self.physical_schema_fixture()
        self.review['reviewer_independent_of_acquisition'] = False
        self.assertEqual(self.analyse()['qualification']['status'], 'unknown')
        self.review['reviewer_independent_of_acquisition'] = True
        self.review['original_evidence'] = []
        self.assertEqual(self.analyse()['qualification']['status'], 'unknown')

    def test_reviewed_registration_after_test_is_rejected(self):
        self.review['verified_registration_at_utc'] = '2026-10-21T00:00:01Z'
        with self.assertRaisesRegex(ValueError, 'chronology'):
            self.analyse()

    def test_posthoc_declared_threshold_date_is_rejected(self):
        self.plan['declared_at_utc'] = '2026-10-21T00:00:01Z'; self.commit_plan()
        with self.assertRaisesRegex(ValueError, 'plan must precede'):
            self.analyse()

    def test_changed_plan_cannot_reuse_old_commit_blob(self):
        self.plan['criteria']['operator_force_max_N']['maximum'] = 999.
        self.manifest['qualification_plan'] = self.write('qualification-plan.json', self.plan)
        self.manifest['qualification_plan_version']['sha256'] = self.manifest['qualification_plan']['sha256']
        with self.assertRaisesRegex(ValueError, 'committed design bytes differ'):
            self.analyse()

    def test_missing_and_null_thresholds_are_unknown(self):
        self.physical_schema_fixture()
        self.plan['criteria'].pop('fpc_radius_min_mm')
        self.plan['criteria']['stroke_y_mm']['minimum'] = None
        self.commit_plan()
        r = self.analyse()
        self.assertEqual(self.criterion(r, 'fpc_radius_min_mm')['status'], 'unknown')
        self.assertEqual(self.criterion(r, 'stroke_y_mm')['status'], 'unknown')
        self.assertEqual(r['qualification']['status'], 'unknown')

    def test_explicit_measured_exceedance_fails(self):
        self.physical_schema_fixture()
        self.rows[9]['operator_force_N'] = 8.; self.write_rows()
        r = self.analyse()
        self.assertEqual(self.criterion(r, 'operator_force_max_N')['status'], 'fail')
        self.assertEqual(r['qualification']['status'], 'fail')

    def test_uncertainty_straddling_limit_is_unknown(self):
        self.physical_schema_fixture()
        self.rows[9]['operator_force_N'] = 4.995; self.write_rows()
        r = self.analyse()
        self.assertEqual(self.criterion(r, 'operator_force_max_N')['status'], 'unknown')
        self.assertEqual(r['qualification']['status'], 'unknown')

    def test_missing_twenty_sixth_conductor_cannot_pass(self):
        self.physical_schema_fixture()
        self.manifest['channels'].pop('fpc_c26_ohm')
        for row in self.rows: row.pop('fpc_c26_ohm')
        self.write_rows()
        self.assertEqual(self.criterion(self.analyse(), 'fpc_resistance_max_ohm')['status'], 'unknown')

    def test_missing_radius_or_overrange_is_not_zero(self):
        self.physical_schema_fixture()
        self.rows[5]['fpc_min_radius_mm'] = ''
        self.rows[9]['fpc_c01_ohm'] = 'OVER_RANGE'; self.write_rows()
        r = self.analyse()
        self.assertEqual(self.criterion(r, 'fpc_radius_min_mm')['status'], 'unknown')
        self.assertEqual(self.criterion(r, 'fpc_resistance_max_ohm')['status'], 'unknown')
        self.assertEqual(r['qualification']['status'], 'unknown')

    def test_bad_second_cycle_not_hidden_by_good_first_stroke(self):
        self.physical_schema_fixture()
        extra = []
        for row in self.rows:
            r = dict(row, t_s=row['t_s']+6., cycle=2)
            if r['left_y_mm'] > 0: r['left_y_mm'] = r['right_y_mm'] = 20.
            extra.append(r)
        self.rows += extra
        self.manifest['acquisition_ended_at_utc'] = '2026-10-21T00:00:20Z'
        self.manifest['recorded_at_utc'] = '2026-10-21T00:00:20Z'
        self.write_rows()
        self.assertEqual(self.criterion(self.analyse(), 'stroke_y_mm')['status'], 'fail')

    def test_incomplete_phase_and_sampling_gap_remain_unknown(self):
        self.physical_schema_fixture()
        self.rows = [r for r in self.rows if r['phase'] != 'SUPPORT_INSTALL']
        self.write_rows()
        r = self.analyse()['qualification']
        self.assertEqual(r['status'], 'unknown')
        self.assertIn('incomplete_or_misordered_cycle_observations', r['blockers'])
        self.assertIn('sampling_gap_exceeds_predeclared_limit', r['blockers'])

    def test_short_hands_off_cannot_pass(self):
        self.physical_schema_fixture()
        holds = [i for i, r in enumerate(self.rows) if r['phase'] == 'HANDS_OFF_OPEN']
        self.rows = [r for i, r in enumerate(self.rows) if i not in holds[1:]]
        self.write_rows()
        self.assertIn('insufficient_contiguous_hands_off_duration', self.analyse()['qualification']['blockers'])

    def test_changed_manufacturing_artifact_is_rejected(self):
        (self.repo/'design/synthetic_bom.json').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'evidence bytes changed'):
            self.analyse()

    def test_calibration_after_acquisition_is_rejected(self):
        name = 'operator_force_N'
        self.calibrations[name]['recorded_at_utc'] = '2026-10-22T00:00:00Z'
        self.manifest['channels'][name] = self.write(name+'.calibration.json', self.calibrations[name])
        with self.assertRaisesRegex(ValueError, 'calibration postdates'):
            self.analyse()

    def test_calibration_arithmetic_overflow_cannot_create_radius_pass(self):
        name = 'oled_min_radius_mm'
        self.calibrations[name]['gain'] = 1e308
        self.manifest['channels'][name] = self.write(name + '.calibration.json', self.calibrations[name])
        with self.assertRaisesRegex(ValueError, 'calibrated: finite'):
            self.analyse()

    def test_stale_review_cannot_approve_changed_acquisition_start(self):
        self.physical_schema_fixture()
        self.write_review()
        self.refresh_review_binding = False
        self.manifest['acquisition_started_at_utc'] = '2026-10-20T23:59:59Z'
        with self.assertRaisesRegex(ValueError, 'exact plan, acquisition and specimen'):
            self.analyse()

    def test_known_fpc_failure_survives_another_missing_sample(self):
        self.physical_schema_fixture()
        self.rows[9]['fpc_c01_ohm'] = 8.
        self.rows[10]['fpc_c26_ohm'] = ''
        self.write_rows()
        report = self.analyse()
        criterion = self.criterion(report, 'fpc_resistance_max_ohm')
        self.assertEqual(criterion['status'], 'fail')
        self.assertFalse(criterion['observation_coverage']['complete'])
        self.assertEqual(criterion['observation_coverage']['missing_observations'], 1)
        self.assertEqual(report['qualification']['status'], 'fail')

    def test_known_fpc_failure_survives_an_absent_conductor(self):
        self.physical_schema_fixture()
        self.rows[9]['fpc_c01_ohm'] = 8.
        self.manifest['channels'].pop('fpc_c26_ohm')
        for row in self.rows:
            row.pop('fpc_c26_ohm')
        self.write_rows()
        self.assertEqual(self.criterion(self.analyse(), 'fpc_resistance_max_ohm')['status'], 'fail')

    def test_known_radius_failure_survives_another_missing_sample(self):
        self.physical_schema_fixture()
        self.rows[9]['oled_min_radius_mm'] = 2.
        self.rows[10]['oled_min_radius_mm'] = ''
        self.write_rows()
        report = self.analyse()
        criterion = self.criterion(report, 'oled_radius_min_mm')
        self.assertEqual(criterion['status'], 'fail')
        self.assertFalse(criterion['observation_coverage']['complete'])
        self.assertEqual(report['qualification']['status'], 'fail')

    def test_partial_oled_range_can_still_prove_upper_limit_failure(self):
        self.physical_schema_fixture()
        self.rows[9]['oled_tail_y_mm'] = 100.
        self.rows[10]['oled_tail_y_mm'] = ''
        self.write_rows()
        self.assertEqual(self.criterion(self.analyse(), 'oled_tail_travel_mm')['status'], 'fail')

    def test_partial_oled_range_cannot_prove_lower_limit_failure(self):
        self.physical_schema_fixture()
        for row in self.rows:
            row['oled_tail_y_mm'] = 0.
        self.rows[10]['oled_tail_y_mm'] = ''
        self.write_rows()
        self.assertEqual(self.criterion(self.analyse(), 'oled_tail_travel_mm')['status'], 'unknown')

    def configure_extreme_y_fixture(self, *, physical=False, opposite=False):
        if physical:
            self.physical_schema_fixture()
        for name in ('left_y_mm', 'right_y_mm'):
            self.calibrations[name]['valid_raw_range'] = [-1.1e308, 1.1e308]
            self.manifest['channels'][name] = self.write(name + '.calibration.json', self.calibrations[name])
        for row in self.rows:
            row['left_y_mm'] = 1e308
            row['right_y_mm'] = -1e308 if opposite else 1e308
        self.plan['criteria']['stroke_y_mm']['minimum'] = 0.
        self.commit_plan()
        self.write_rows()

    def test_extreme_physical_readings_cannot_claim_unrepresentable_precision(self):
        self.configure_extreme_y_fixture(physical=True)
        with self.assertRaisesRegex(ValueError, 'numerical precision exceeds'):
            self.analyse()

    def test_stable_mean_does_not_create_nonfinite_results(self):
        self.configure_extreme_y_fixture()
        report = self.analyse()
        self.assertEqual(report['cycles'][0]['sampled_mean_y_range_mm'], 0.)
        self.assertEqual(report['qualification']['status'], 'unknown')
        json.dumps(report, allow_nan=False)

    def test_opposite_finite_readings_cannot_overflow_a_difference(self):
        self.configure_extreme_y_fixture(opposite=True)
        with self.assertRaisesRegex(ValueError, 'left-right y: finite'):
            self.analyse()

    def test_error_sum_overflow_is_rejected(self):
        for name in ('left_y_mm', 'right_y_mm'):
            self.calibrations[name]['absolute_error_bound'] = 1e308
            self.manifest['channels'][name] = self.write(name + '.calibration.json', self.calibrations[name])
        with self.assertRaisesRegex(ValueError, 'summed y error: finite'):
            self.analyse()

    def test_nonfinite_or_reversed_interval_cannot_pass_comparisons(self):
        for bounds in ([float('nan'), 1.], [0., float('inf')], [2., 1.]):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                contract.decide(bounds, {'minimum': 0., 'maximum': 5.})

    def test_cli_rejection_does_not_create_partial_output(self):
        self.configure_extreme_y_fixture(physical=True)
        self.write_manifest()
        review = self.write_review()
        output = self.evidence/'must-not-exist.json'
        process = subprocess.run([
            sys.executable, '-B', str(FOLLOW/'analyse_motion_log.py'),
            '--manifest', str(self.evidence/'acquisition.json'), '--repository', str(self.repo),
            '--preregistration-review', str(review), '--output', str(output)],
            capture_output=True, text=True, check=False)
        self.assertEqual(process.returncode, 2, process.stderr)
        self.assertIn('numerical precision', process.stderr)
        self.assertFalse(output.exists())

    def test_zero_additional_alignment_error_is_valid_for_shared_clock(self):
        self.physical_schema_fixture()
        self.manifest['timebase']['alignment_error_bound_s'] = 0.
        self.plan['measurement_requirements']['maximum_alignment_error_s'] = 0.
        self.commit_plan()
        self.assertEqual(self.analyse()['qualification']['status'], 'pass')

    def assert_changed_after_read_rejected(self, reference):
        original_read = motion.relative_file
        changed = False
        def read_then_change(root, ref):
            nonlocal changed
            data = original_read(root, ref)
            if not changed and ref == reference:
                (Path(root)/ref['path']).write_text('CHANGED AFTER VERIFIED READ')
                changed = True
            return data
        with mock.patch.object(motion, 'relative_file', side_effect=read_then_change):
            with self.assertRaisesRegex(ValueError, 'evidence bytes changed'):
                self.analyse()
        self.assertTrue(changed)

    def test_calibration_record_changed_after_initial_read_is_rejected(self):
        self.assert_changed_after_read_rejected(self.manifest['channels']['operator_force_N'])

    def test_calibration_original_changed_after_initial_read_is_rejected(self):
        reference = self.write('unique-calibration-original.txt', 'SYNTHETIC CALIBRATION ORIGINAL')
        name = 'operator_force_N'
        self.calibrations[name]['original_evidence'] = [reference]
        self.manifest['channels'][name] = self.write(name + '.calibration.json', self.calibrations[name])
        self.assert_changed_after_read_rejected(reference)

    def test_phase_frame_and_sync_originals_changed_after_read_are_rejected(self):
        for field in ('phase_and_hand_contact_evidence', 'coordinate_frame_evidence', 'synchronization_evidence'):
            with self.subTest(field=field):
                target = self.manifest['timebase'] if field == 'synchronization_evidence' else self.manifest
                previous = target[field]
                target[field] = self.write(field + '.txt', 'SYNTHETIC ' + field)
                self.assert_changed_after_read_rejected(target[field])
                target[field] = previous

    def test_finalized_record_time_cannot_predate_acquisition(self):
        self.manifest['recorded_at_utc'] = '2000-01-01T00:00:00Z'
        with self.assertRaisesRegex(ValueError, 'record timestamp predates'):
            self.analyse()

    def test_zero_normal_seating_travel_fails(self):
        self.physical_schema_fixture()
        for row in self.rows: row['left_z_mm'] = row['right_z_mm'] = 0.
        self.write_rows()
        self.assertEqual(self.criterion(self.analyse(), 'stroke_z_mm')['status'], 'fail')

    def test_acquisition_order_cannot_be_changed_after_predeclaration(self):
        changed = list(self.manifest['planned_phase_order'])
        changed[1], changed[2] = changed[2], changed[1]
        self.manifest['planned_phase_order'] = changed
        with self.assertRaisesRegex(ValueError, 'phase order differs'):
            self.analyse()

    def test_wrong_unit_or_reversed_bounds_are_rejected(self):
        self.plan['criteria']['operator_force_max_N']['unit'] = 'mm'; self.commit_plan()
        with self.assertRaisesRegex(ValueError, 'wrong unit'):
            self.analyse()
        self.plan['criteria']['operator_force_max_N']['unit'] = 'N'
        self.plan['criteria']['stroke_y_mm'] = {'unit': 'mm', 'minimum': 80., 'maximum': 79.}
        self.commit_plan()
        with self.assertRaisesRegex(ValueError, 'reversed'):
            self.analyse()


if __name__ == '__main__':
    unittest.main()

