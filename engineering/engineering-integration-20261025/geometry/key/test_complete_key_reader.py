"""Adversarial raw-evidence tests; no CAD imported or geometry results mocked."""
from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path
import tempfile
import unittest

import read_key_trial as reader
import stow_face_relief as relief


def complete_fixture():
    names = ['part%03d' % i for i in range(154)]
    body = {'volume_mm3': 1., 'solid_count': 1, 'bounds_mm': [0., 1., 0., 1., 0., 1.],
            'material_assignment_present': False, 'old_PR34_structural_result_applicable': False}
    pairs = [{'a': a, 'b': b, 'common_mm3': 0., 'rejected': False,
              'method': 'positive_axis_gap', 'axis_gap_lower_mm': 1.}
             for a, b in itertools.combinations(names, 2)]
    return {'schema': 'razr-complete-finite-KEY-trial-20261025-v1',
            **{key: False for key in reader.FALSE_FLAGS},
            'trial': {'pose': 'STOW'}, 'complete_participant_names': names,
            'participant_count': len(names), 'expected_pair_count': len(pairs),
            'nominal_parts': {name: body.copy() for name in names},
            'current_parts': {name: body.copy() for name in names},
            'pairs': pairs, 'positive_actual_Common': [], 'evaluation_failures': [],
            'execution_completed': True, 'finite_trial_clear': True,
            'all_unordered_pairs_present_once': True,
            'identity_after': {'source_bytes_and_locked_environment_unchanged': True,
                               'changed_or_late_sources': [], 'exact_commit_execution_claimed': False},
            'in_domain_factory_crosscheck': {'all_participants_compared': len(names),
                  'bidirectional_material_difference_mm3': dict.fromkeys(names, 0.)},
            'production_profile_rejections': [{}, {}, {}, {}]}


class RawEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.report = complete_fixture()

    def test_complete_disjoint_inventory_accepted(self):
        self.assertEqual(reader.validate_report(self.report)['completed_pair_count'], 11781)

    def test_missing_last_pair_cannot_claim_completion(self):
        self.report['pairs'].pop()
        with self.assertRaises(ValueError):
            reader.validate_report(self.report)

    def test_duplicate_pair_cannot_replace_missing_pair(self):
        self.report['pairs'][-1] = self.report['pairs'][0]
        with self.assertRaises(ValueError):
            reader.validate_report(self.report)

    def test_positive_pair_cannot_be_hidden(self):
        self.report['pairs'][0].update(common_mm3=.0012382, rejected=True, method='native_common', axis_gap_lower_mm=0.)
        self.report['finite_trial_clear'] = False
        with self.assertRaises(ValueError):
            reader.validate_report(self.report)

    def test_positive_pair_is_complete_but_not_clear(self):
        row = self.report['pairs'][0]
        row.update(common_mm3=.0012382, rejected=True, method='native_common', axis_gap_lower_mm=0.)
        self.report['positive_actual_Common'] = [dict(row)]
        self.report['finite_trial_clear'] = False
        result = reader.validate_report(self.report)
        self.assertTrue(result['execution_completed'])
        self.assertFalse(result['finite_trial_clear'])
        self.assertEqual(result['rejected_pair_count'], 1)

    def test_false_clear_and_relaxed_threshold_rejected(self):
        row = self.report['pairs'][0]
        row.update(common_mm3=1.001e-7, rejected=False, method='native_common', axis_gap_lower_mm=0.)
        self.report['positive_actual_Common'] = [dict(row)]
        with self.assertRaises(ValueError):
            reader.validate_report(self.report)

    def test_export_failure_prevents_complete_execution(self):
        self.report['evaluation_failures'] = [{'a': 'part000', 'b': 'part001', 'error': 'export failed'}]
        with self.assertRaises(ValueError):
            reader.validate_report(self.report)

    def test_source_changes_prevent_completion(self):
        self.report['identity_after']['changed_or_late_sources'] = ['changed.py']
        with self.assertRaises(ValueError):
            reader.validate_report(self.report)

    def test_one_missing_body_or_wrong_old_FE_claim_fails(self):
        del self.report['current_parts']['part000']
        with self.assertRaises(ValueError):
            reader.validate_report(self.report)
        self.report = complete_fixture()
        self.report['current_parts']['part000']['old_PR34_structural_result_applicable'] = True
        with self.assertRaises(ValueError):
            reader.validate_report(self.report)

    def test_nonfinite_common_rejected(self):
        self.report['pairs'][0]['common_mm3'] = float('nan')
        with self.assertRaises(ValueError):
            reader.validate_report(self.report)

    def test_continuous_or_original_v4_claim_rejected(self):
        for flag in reader.FALSE_FLAGS:
            with self.subTest(flag=flag):
                self.report[flag] = True
                with self.assertRaises(ValueError):
                    reader.validate_report(self.report)
                self.report[flag] = False

    def test_raw_journal_truncation_and_pair_mutation_rejected(self):
        small = {'pairs': self.report['pairs'][:2]}
        events = [event for row in small['pairs'] for event in (
            {'event': 'selected', 'a': row['a'], 'b': row['b']}, {'event': 'completed', 'row': row})]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'pairs.jsonl'
            path.write_text(''.join(json.dumps(event)+'\n' for event in events))
            self.assertTrue(reader.validate_journal(path, small)['all_selected_pairs_have_matching_completed_raw_record'])
            path.write_text(''.join(json.dumps(event)+'\n' for event in events[:-1]))
            with self.assertRaises(ValueError):
                reader.validate_journal(path, small)
            changed = copy.deepcopy(events)
            changed[1]['row']['common_mm3'] = 1.
            path.write_text(''.join(json.dumps(event)+'\n' for event in changed))
            with self.assertRaises(ValueError):
                reader.validate_journal(path, small)


class ReliefDomainTests(unittest.TestCase):
    def test_original_full_groove_band_is_not_reduced(self):
        record = relief.definition()
        a, b = record['original_cam_halfwidth_mm'], record['original_yoke_halfwidth_mm']
        vertices = [(dx, dx-difference) for dx in (-a, a) for difference in (-b, b)]
        minimum_q = min(q for dx, q in vertices)
        self.assertEqual(record['control_domain']['dq_mm'], [minimum_q, 0.])
        self.assertFalse(record['q_or_other_control_domain_removed'])
        self.assertFalse(record['contact_law_changed'])

    def test_cut_face_preserves_original_gap_at_worst_key_vertex(self):
        record = relief.definition()
        original_gap = record['original_KEY_face_Y_mm']-record['original_native_face_Y_mm']
        displaced_key_face = record['original_KEY_face_Y_mm']+record['KEY_full_negative_offset_mm']
        self.assertAlmostEqual(displaced_key_face-record['cut_face_Y_mm'], original_gap, places=13)
        self.assertGreater(original_gap, 0.)

    def test_only_four_reproduced_fixed_bodies_receive_finite_cuts(self):
        record = relief.definition()
        self.assertEqual({r['part'] for r in record['parts']},
                         {'L_CAP_0', 'R_CAP_0', 'L_ROOT_INNER', 'R_ROOT_INNER'})
        self.assertEqual(sum(len(row['cut_boxes']) for row in record['parts']), 6)
        for row in record['parts']:
            for box in row['cut_boxes']:
                self.assertTrue(all(hi > lo for lo, hi in zip(box['lo_mm'], box['hi_mm'])))
                self.assertAlmostEqual(box['lo_mm'][1], record['cut_face_Y_mm'])
        self.assertFalse(record['production_default_changed'])
        self.assertFalse(record['strength_or_tolerance_qualified'])

    def test_left_and_right_cut_packages_are_exact_mirrors(self):
        rows = {row['part']: row['cut_boxes'] for row in relief.definition()['parts']}
        for role in ('CAP_0', 'ROOT_INNER'):
            for left, right in zip(rows['L_'+role], rows['R_'+role]):
                self.assertEqual(left['lo_mm'][0], -right['hi_mm'][0])
                self.assertEqual(left['hi_mm'][0], -right['lo_mm'][0])
                self.assertEqual(left['lo_mm'][1:], right['lo_mm'][1:])
                self.assertEqual(left['hi_mm'][1:], right['hi_mm'][1:])


if __name__ == '__main__':
    unittest.main()
