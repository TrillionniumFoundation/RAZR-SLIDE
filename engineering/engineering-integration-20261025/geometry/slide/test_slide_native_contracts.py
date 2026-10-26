"""Synthetic arithmetic contract tests only; never execute or import CAD."""
import copy
import json
from dataclasses import replace
from fractions import Fraction as F
import sys
import unittest
from unittest.mock import patch

import slide_domain as d
import slide_evidence as e
import verify_slide_native as runner
from cam_contact_profile import ContactProfile


def clear_raw(value=0.):
    return {'disposition': 'clear', 'method': 'identical_relative_pose', 'region_count': 1,
            'maximum_region_common_mm3': value, 'common_upper_bound_mm3': value,
            'common_upper_bound_is_sum_not_union_volume': True}


def interval(contract, a, b, low=F(0), high=d.QMAX, frame='A', value=0.):
    records = [{'specification': spec, 'raw': clear_raw(value)}
               for spec in contract.specifications(a, b, low, high, frame)]
    attempt = {'reference_frame': frame, 'records': records, **e.aggregate(records)}
    return {'q_interval_exact': [str(low), str(high)], 'attempts': [attempt],
            'disposition': attempt['disposition'], 'method': 'whole_material_relative_enclosure',
            'collision_proved': False}


class SlideNativeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.names = e.expected_names()
        cls.profiles = (ContactProfile(.1, 1., .1, 2., .12, .2),)*4
        cls.laws = d.rigid_laws(cls.names, {'L': .02, 'R': .03}, cls.names)
        cls.springs = {name: e.Spring(name, (0., 1., -.43, .43, -.43, .43)) for name in d.SPRINGS}
        cls.contract = e.Contract(cls.names, cls.laws, cls.profiles, cls.springs)

    def pair(self, a, b, **kwargs):
        a, b = sorted((a, b))
        return {'a': a, 'b': b, 'pair_class': e.pair_class(a, b), **interval(self.contract, a, b, **kwargs)}

    def test_complete_pair_inventory_preserves_springs_and_both_flexible_materials(self):
        from collections import Counter
        self.assertEqual(dict(Counter(e.pair_class(a, b) for a, b in self.contract.pairs)), e.CLASS_COUNTS)
        self.assertEqual(sum(e.CLASS_COUNTS.values()), 11781)
        self.assertEqual(sum(e.CLASS_COUNTS[k] for k in ('rigid_rigid', 'spring_rigid', 'spring_spring')), 11476)

    def test_relative_law_cancels_shared_q_before_any_enclosure(self):
        a, b = sorted(('L_TELESCOPE_1', 'L_CROSSHEAD'))
        spec = self.contract.specifications(a, b, F(0), d.QMAX)[0]
        self.assertEqual(spec['coefficients'][0], [0., 0., 0.])
        self.assertEqual(spec['relative_law']['q_xyz'], ['0', '0', '0'])
        self.assertEqual(spec['parameter_intervals'][-1], list(map(float, self.laws[a].relative_to(self.laws[b]).z_interval())))

    def test_B_frame_subtracts_only_shared_slide_Y(self):
        original = self.laws['B_tail']
        self.assertEqual(e.in_frame(original, 'B'), d.ZERO)
        pawl = e.in_frame(self.laws['L_PAWL'], 'B')
        self.assertEqual(pawl.q_xyz, (F(0), -d.SLIDE_PER_Q, F(0)))
        self.assertEqual(pawl.flank_z, self.laws['L_PAWL'].flank_z)

    def test_spring_is_complete_monotone_growth_not_rigid_translation(self):
        for name, spring in self.springs.items():
            base = spring.record(self.profiles, 0, 0)
            whole = spring.record(self.profiles, 0, 12)
            self.assertLessEqual(whole['axis_start_mm'][0], base['axis_start_mm'][0])
            self.assertGreaterEqual(whole['axis_end_mm'][0], base['axis_end_mm'][0])
            self.assertGreater(whole['axis_end_mm'][0]-whole['axis_start_mm'][0], 1.)
            self.assertEqual(whole['radius_mm'], .43)
        with self.assertRaises(ValueError):
            e.Spring('L_SPRING_0_OD_TOL_ENVELOPE', (0., 1., -.1, .1, -.43, .43))

    def test_all_9_and_3_and_27_region_cartesian_material_cages_present(self):
        for flex, expected in (('EP5_finite_material', 9), ('OLED_GEOMETRIC_TRIAL', 3)):
            row = self.pair(flex, 'A_FRAME')
            self.assertEqual(len(row['attempts'][0]['records']), expected)
            self.assertTrue(e.validate_pair(row, self.contract))
        row = self.pair(*sorted(d.FLEX))
        self.assertEqual(len(row['attempts'][0]['records']), 27)
        self.assertTrue(e.validate_pair(row, self.contract))

    def test_missing_or_repeated_cage_fails_closed(self):
        for modify in ('missing', 'duplicate', 'wrong_hash'):
            row = self.pair('EP5_finite_material', 'A_FRAME')
            records = row['attempts'][0]['records']
            if modify == 'missing': records.pop()
            elif modify == 'duplicate': records[-1] = copy.deepcopy(records[0])
            else: records[0]['specification']['fixed']['cage_sha256'] = '0'*64
            with self.assertRaises(ValueError):
                e.validate_pair(row, self.contract)

    def test_region_values_use_one_whole_material_budget(self):
        row = self.pair('OLED_GEOMETRIC_TRIAL', 'A_FRAME', value=6e-8)
        self.assertEqual(row['attempts'][0]['disposition'], 'unresolved_enclosure_overlap')
        self.assertAlmostEqual(row['attempts'][0]['common_upper_bound_mm3'], 1.8e-7)
        row.update(disposition='clear')
        with self.assertRaises(ValueError):
            e.validate_pair(row, self.contract)

    def test_negative_gap_and_hidden_reverse_error_rejected(self):
        for raw in ({'disposition': 'clear', 'method': 'continuous_relative_axis_gap', 'gap_lower_mm': -1.},
                    {**clear_raw(), 'relative_reference_frame_reversed': True,
                     'initial_reference_frame_result': {'disposition': 'unresolved_evaluation', 'error': 'real kernel error'}}):
            row = self.pair('A_FRAME', 'B_SHELL')
            row['attempts'][0]['records'][0]['raw'] = raw
            with self.assertRaises(ValueError):
                e.validate_pair(row, self.contract)

    def test_actual_command_domain_descriptor_bound_to_pair(self):
        for change in ('interval', 'moving', 'relative'):
            row = self.pair('A_FRAME', 'B_SHELL')
            spec = row['attempts'][0]['records'][0]['specification']
            if change == 'interval': spec['parameter_intervals'][0] = [0., 6.]
            elif change == 'moving': spec['moving']['material'] = 'L_KEY'
            else: spec['relative_law']['q_xyz'] = ['0', '0', '0']
            with self.assertRaises(ValueError):
                e.validate_pair(row, self.contract)

    def partition_row(self, split='all_actual_profile_breakpoints'):
        row = self.pair('A_FRAME', 'B_SHELL')
        raw = {'disposition': 'unresolved_enclosure_overlap', 'method': 'identical_relative_pose',
               'examined_region_common_sum_mm3': 1., 'positive_enclosure_common_mm3': 1.,
               'regions_examined': 1, 'total_region_count': 1, 'collision_proved': False}
        row['attempts'][0]['records'][0]['raw'] = raw
        row['attempts'][0].update(e.aggregate(row['attempts'][0]['records']))
        row.update(method='complete_closed_interval_partition', split=split,
                   children=[interval(self.contract, row['a'], row['b'], low, high)
                             for low, high in self.contract.child_intervals(F(0), d.QMAX, split)])
        return row

    def test_complete_real_breakpoint_partition_accepted_without_sampling(self):
        self.assertTrue(e.validate_pair(self.partition_row(), self.contract))

    def test_partition_missing_child_or_gap_or_duplicate_rejected(self):
        for modify in ('missing', 'gap', 'duplicate'):
            row = self.partition_row()
            if modify == 'missing': row['children'].pop()
            elif modify == 'gap': row['children'][0]['q_interval_exact'][0] = '1/1000'
            else: row['children'][-1] = copy.deepcopy(row['children'][0])
            with self.assertRaises(ValueError):
                e.validate_pair(row, self.contract)

    def test_budget_stop_preserves_current_attempt_and_original_call_descriptor(self):
        class Budget:
            def __init__(self): self.calls = 0
            def check(self, operator=False):
                if operator:
                    self.calls += 1
                    if self.calls == 2: raise runner.BudgetExceeded('synthetic capacity stop')
        class Nominal:
            def continuous_pair(self, *args, **kwargs): return clear_raw()
        class Bodies:
            nominal = Nominal()
            def material(self, descriptor, low, high): return descriptor
        a, b = sorted(('A_FRAME', 'EP5_finite_material'))
        with self.assertRaises(runner.BudgetExceeded) as caught:
            runner.evaluate_interval(a, b, F(0), d.QMAX, self.contract, Bodies(), Budget())
        row = caught.exception.partial
        self.assertEqual(row['disposition'], 'unresolved_budget')
        self.assertEqual(len(row['attempts'][0]['records']), 1)
        self.assertEqual(row['attempts'][0]['records'][0]['specification'],
                         self.contract.specifications(a, b, F(0), d.QMAX)[0])

    def test_complete_result_cannot_pass_omission_duplicate_runtime_or_terminal_failure(self):
        # Full native-like records here are fabricated to test bookkeeping.
        # This test never constructs native geometry or asserts product clearance.
        rows = [self.pair(a, b) for a, b in self.contract.pairs]
        identity = {'repository_head': 'a'*40, 'environment': {'passed': True}, 'executed_source_overlay': False}
        sources = {'scratch': 'b'*64}
        report = {'expected_head': 'a'*40, 'complete_participant_names': self.names, 'pairs': rows,
                  'domain': e.recorded_domain(self.profiles), 'native_scene_metadata': {},
                  'participant_count': 154, 'pair_count': 11781, 'expected_pair_count': 11781,
                  'pair_class_counts': dict(e.CLASS_COUNTS), 'native_checks_executed': True, 'execution_completed': True,
                  'construction_probes_complete': True, 'identity_before': identity, 'identity_after': identity,
                  'scratch_source_sha256_before': sources, 'scratch_source_sha256_after': sources,
                  **{flag: False for flag in e.FALSE_FLAGS}}
        with patch.object(e, 'validate_metadata'), patch.object(e, 'validate_construction'):
            result = e.complete_result(json.loads(json.dumps(report)), self.contract, identity, sources)
            self.assertTrue(result['complete_native_diagnostic_executed'])
            self.assertTrue(result['whole_declared_slide_external_pair_domain_clear'])
            self.assertFalse(result['canonical_execution_checks_passed'])
            self.assertFalse(result['whole_declared_slide_domain_clear'])
            report['pairs'] = rows[:-1]
            self.assertFalse(e.complete_result(report, self.contract, identity, sources)['complete_native_diagnostic_executed'])
            report['pairs'] = rows[:-1]+[rows[0]]
            self.assertFalse(e.complete_result(report, self.contract, identity, sources)['all_unordered_pairs_present_once'])
            report['pairs'] = rows; report['terminal_failure'] = 'synthetic stop'
            self.assertFalse(e.complete_result(report, self.contract, identity, sources)['complete_native_diagnostic_executed'])
            del report['terminal_failure']
            self.assertFalse(e.complete_result(report, self.contract, identity, {'changed': 'c'})['complete_native_diagnostic_executed'])
            report['postflight_failure'] = 'synthetic late source change'
            self.assertFalse(e.complete_result(report, self.contract, identity, sources)['complete_native_diagnostic_executed'])

    def test_construction_boolean_alone_cannot_pass_and_source_inventory_is_explicit(self):
        with self.assertRaises(ValueError):
            runner.validate_construction({'source_laws_not_inferred_from_samples': True}, self.contract)
        paths = runner.source_identity()
        self.assertIn(str(e.HERE/'slide_domain.py'), paths)
        self.assertIn(str(evidence_path := e.HELPER_DIR/'slide_enclosures.py'), paths)
        self.assertIn(str(e.cages.shared.__file__), paths)
        self.assertEqual(len(paths), 17)

    def test_saved_domain_roundtrip_and_real_profile_identity_are_arithmetic_only(self):
        self.assertEqual(json.loads(json.dumps(e.recorded_domain(self.profiles))), e.recorded_domain(self.profiles))
        originals = e.original_profiles()
        self.assertEqual(len(originals), 4)
        self.assertTrue(all(profile.q_max == 12. for profile in originals))
        self.assertFalse(any(name == 'cadquery' or name == 'OCP' or name.startswith('OCP.') for name in sys.modules))

    def test_hidden_budget_attempt_cannot_be_lost_by_a_clear_top_level_label(self):
        row = self.pair('OLED_GEOMETRIC_TRIAL', 'A_FRAME')
        row['attempts'].append({'reference_frame': 'B', 'disposition': 'unresolved_budget', 'records': []})
        self.assertEqual(e.pending_in(row), 1)

    def test_executed_entrypoint_cannot_claim_a_different_source_file(self):
        with patch.object(runner, '__file__', '/tmp/unbound-verifier.py'):
            with self.assertRaises(ValueError):
                runner.source_identity()

    def test_base_factory_metadata_and_scope_fail_closed(self):
        with self.assertRaises(ValueError): e.validate_metadata({})
        self.assertFalse(any(n == 'cadquery' or n == 'OCP' or n.startswith('OCP.') for n in sys.modules))


if __name__ == '__main__':
    unittest.main()
