"""Independent, small arithmetic regressions. No CAD is imported or executed."""
from __future__ import annotations

from fractions import Fraction as F
from itertools import combinations, product
import json
import math
from pathlib import Path
import random
import sys
import unittest

import numpy as np

import seating_domain as domain
import seating_enclosures as enclosure
import verify_seating_native as adapter


def solve_exact(matrix, values):
    """Independent Gaussian elimination for five active affine constraints."""
    n = len(values)
    a = [[F(v) for v in row] + [F(b)] for row, b in zip(matrix, values)]
    for column in range(n):
        pivot = next((row for row in range(column, n) if a[row][column]), None)
        if pivot is None:
            return None
        a[column], a[pivot] = a[pivot], a[column]
        scale = a[column][column]
        a[column] = [value / scale for value in a[column]]
        for row in range(n):
            if row != column:
                scale = a[row][column]
                a[row] = [v - scale * p for v, p in zip(a[row], a[column])]
    return tuple(row[-1] for row in a)


def independent_active_constraint_vertices(low, high):
    """Enumerate every nonsingular set of five facets of the original H-polytope.

    This oracle never calls joints_at/critical_descents/coupled_vertices, and
    therefore detects an incorrect shared-descent branch decomposition.
    """
    low, high = F(str(low)), F(str(high))
    facets = [((1, 0, 0, 0, 0), high), ((-1, 0, 0, 0, 0), -low)]
    for index in range(1, 5):
        vector = [0] * 5
        vector[index] = 1
        facets.append((tuple(vector), F('2.9')))
        facets.append((tuple(-v for v in vector), F('-.1')))
    for indices in ((0, 1, 2), (0, 3, 4)):
        vector = tuple(int(i in indices) for i in range(5))
        # .1 <= 8.5 - d - j1 - j2 <= 2.9
        facets.append((vector, F('8.4')))
        facets.append((tuple(-v for v in vector), F('-5.6')))
    result = set()
    for chosen in combinations(facets, 5):
        point = solve_exact([row for row, _ in chosen], [b for _, b in chosen])
        if point is not None and all(sum(a * x for a, x in zip(row, point)) <= b for row, b in facets):
            result.add(point)
    return result


def all_corners_inside_one_box(corners, boxes, tolerance=1e-10):
    lower = np.min(corners, axis=0)
    upper = np.max(corners, axis=0)
    return any(np.all(lower >= np.asarray(box['low_mm']) - tolerance)
               and np.all(upper <= np.asarray(box['high_mm']) + tolerance) for box in boxes)


class ExactDomainTests(unittest.TestCase):
    def test_full_and_partial_h_polytope_vertex_oracle(self):
        for low, high in ((0, 8.2), (.2, 7.8), (2.7, 5.3)):
            with self.subTest(low=low, high=high):
                actual = set(domain.coupled_vertices(F(str(low)), F(str(high))))
                self.assertEqual(actual, independent_active_constraint_vertices(low, high))
        self.assertEqual(len(domain.coupled_vertices()), 28)
        self.assertEqual(domain.critical_descents(), (F(0), F('2.6'), F('5.4'), F('8.2')))

    def test_vertex_state_feasibility_and_shared_descent(self):
        for point in domain.coupled_vertices():
            state = domain.allocation(point + (F(-1), F(1)))
            for side in ('L', 'R'):
                self.assertEqual(sum(state['joints'][side]), F('8.5') - point[0])
                self.assertTrue(all(F('.1') <= v <= F('2.9') for v in state['joints'][side]))

    def test_random_exact_projection_against_independent_facets_and_flanks(self):
        rng = random.Random(20261023)
        vertices = independent_active_constraint_vertices(.7, 6.8)
        for _ in range(32):
            law = domain.ZLaw(F(rng.randrange(-9, 10), 7),
                              tuple(F(rng.randrange(-9, 10), 11) for _ in range(7)))
            direct = [law.evaluate(point + flanks) for point in vertices
                      for flanks in product((F(-1), F(1)), repeat=2)]
            self.assertEqual(law.projection('.7', '6.8'), (min(direct), max(direct)))

    def test_rigid_inventory_correlations_and_reference_frame(self):
        names = json.loads(Path(__file__).with_name('seating-inventory.json').read_text())['names']
        laws = domain.rigid_laws(names, {'L': '.027', 'R': '.028'}, names)
        self.assertEqual(len(laws), 152)
        self.assertEqual(laws['L_TELESCOPE_3'].relative_to(laws['R_TELESCOPE_3']).projection(), (0, 0))
        self.assertEqual(laws['L_TELESCOPE_3'].relative_to(laws['B_SHELL']).projection(), (0, 0))
        pair = laws['L_TELESCOPE_1'].relative_to(laws['R_TELESCOPE_1'])
        self.assertEqual(pair.projection(), (F('-2.8'), F('2.8')))
        self.assertEqual(pair.projection(0, 0), (F('-.2'), F('.2')))
        self.assertEqual(laws['B_SHELL'].in_frame('B').projection(), (0, 0))
        self.assertEqual(laws['A_FRAME'].in_frame('B').projection(), (0, F('8.2')))
        flank = laws['L_PAWL'].relative_to(laws['R_SHOULDER_PIN_NOMINAL'])
        self.assertEqual(flank.projection(), (F('-.055'), F('.055')))
        reference = (F(0),) + (domain.REFERENCE_JOINT,) * 4 + (F(0), F(0))
        self.assertTrue(all(law.evaluate(reference) == 0 for law in laws.values()))

    def test_invalid_domains_and_incomplete_material_fail_closed(self):
        for low, high in ((-1, 1), (0, 8.3), (4, 3), (float('nan'), 2), (True, 2)):
            with self.subTest(low=low, high=high), self.assertRaises(ValueError):
                domain.interval(low, high)
        with self.assertRaises(ValueError):
            domain.allocation((0, .1, .1, 2.8, 2.8, 0, 0))
        names = json.loads(Path(__file__).with_name('seating-inventory.json').read_text())['names']
        with self.assertRaises(ValueError):
            domain.rigid_laws(names[:-1], {'L': '.027', 'R': '.028'}, names)
        changed = [name if name != 'L_TELESCOPE_3' else 'UNCLASSIFIED_NEW_MATERIAL' for name in names]
        with self.assertRaises(ValueError):
            domain.rigid_laws(changed, {'L': '.027', 'R': '.028'}, changed)


class FiniteMaterialEnclosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = enclosure.configuration()
        cls.pose_sections = {d: enclosure.ep5.route_sections(79.75, d, cls.config)
                             for d in (0., 2.6, 4.1, 5.4, 7.65, 8.2)}

    def test_actual_finite_polygon_entire_adjacent_cells_and_tapers(self):
        checked = 0
        for d, (sections, report) in self.pose_sections.items():
            stations = sections['s']
            joins = np.asarray(report['exact_join_material_labels_mm'])
            prefixes = ('A_straight_core', 'S_', 'bridge', 'U1_', 'upper_reverse', 'U2_', 'B_final_core')
            core = sections['corners'].copy()
            core[:, :, 0] = np.array([-1, 1, 1, -1])[None, :] * 5.4
            for frame in ('A', 'B'):
                shift = np.array([0., 0., d if frame == 'B' else 0.])
                for bounds in ((0., 8.2), (d, d)):
                    boxes = enclosure.fpc_cells(*bounds, frame)
                    for i in range(len(stations) - 1):
                        segment = int(np.searchsorted(joins[1:], (stations[i] + stations[i + 1]) / 2., side='left'))
                        relevant = [b for b in boxes if b['label'].startswith(prefixes[segment])]
                        corners = core[i:i + 2].reshape(-1, 3) + shift
                        self.assertTrue(all_corners_inside_one_box(corners, relevant),
                                        (d, frame, bounds, i, prefixes[segment], stations[i:i + 2]))
                        checked += 1
                    for end, mask in (('A', stations <= 4. + 1e-12), ('B', stations >= 160. - 1e-12)):
                        actual = sections['corners'][mask].reshape(-1, 3) + shift
                        wing = [b for b in boxes if b['label'] == end + '_taper_wings']
                        self.assertTrue(all_corners_inside_one_box(actual, wing), (d, frame, bounds, end))
        self.assertGreater(checked, 6000)

    def test_complete_cell_inventory_and_native_group_coordinate_equivalence(self):
        for frame in ('A', 'B'):
            rows = enclosure.fpc_cells(frame=frame)
            self.assertEqual(len(rows), 150)
            self.assertEqual(len({row['label'] for row in rows}), 150)
            groups = enclosure.fpc_grouped(frame=frame)
            self.assertEqual(len(groups), 9)
            for prefix in ('S', 'U1', 'U2'):
                source = [r for r in rows if r['label'].startswith(prefix + '_')]
                group = next(g for g in groups if g['label'] == prefix)
                self.assertEqual(group['cell_count'], 48)
                self.assertEqual(group['rectangles_yz'], [[r['low_mm'][1:], r['high_mm'][1:]] for r in source])

    def test_interior_flat_S_extremum_must_not_be_dropped(self):
        values = [enclosure.ep5.pose_numbers(79.75, d, self.config)['U1_start_world_Y_mm']
                  for d in (0., 7.65, 8.2)]
        self.assertGreater(values[1] - max(values[0], values[2]), .01)
        bridge = next(r for r in enclosure.fpc_cells() if r['label'] == 'bridge')
        self.assertGreaterEqual(bridge['high_mm'][1], values[1])
        self.assertLess(bridge['high_mm'][1] - values[1], 2e-7)

    def test_nested_OLED_disks_contain_the_original_annulus_family(self):
        for frame in ('A', 'B'):
            for low, high in ((0., 8.2), (.5, 4.5), (7., 7.9)):
                front, turn, tail = enclosure.oled_cages(low, high, frame)
                self.assertEqual(turn['kind'], 'nested_half_disks')
                for d in np.linspace(low, high, 17):
                    original = enclosure.oled_state(float(d))
                    center = original['center_z'] + (d if frame == 'B' else 0.)
                    r = original['radius']; half_t = original['spec']['thickness_mm'] / 2.
                    # Entire outer disk containment; smallest excluded inner
                    # disk is contained in every original inner disk.
                    self.assertLessEqual(abs(center - turn['outer_center_z_mm']) + r + half_t,
                                         turn['outer_radius_mm'] + 1e-12)
                    self.assertLessEqual(abs(center - turn['inner_center_z_mm']) + turn['inner_radius_mm'],
                                         r - half_t + 1e-12)
                    self.assertGreaterEqual(original['turn_y'] - original['tail'], tail['low_mm'][1] - 1e-12)

    def test_flex_flex_gaps_and_cell_nondegeneracy_are_positive(self):
        report = enclosure.flex_flex_certificate()
        self.assertGreater(min(report['gap_lower_mm'].values()), .49)
        self.assertFalse(report['actual_native_Common_executed'])
        self.assertFalse(report['complete_G2_or_physical_qualification'])
        for row in enclosure.chord_cell_contract()['records']:
            self.assertGreater(row['signed_cell_Jacobian_over_arc_length_lower'], .96)

    def test_no_CAD_module_loaded(self):
        self.assertNotIn('cadquery', sys.modules)
        self.assertFalse(any(key == 'OCP' or key.startswith('OCP.') for key in sys.modules))


class DiagnosticAccountingTests(unittest.TestCase):
    @staticmethod
    def native_common(value):
        return {'disposition': 'clear', 'method': 'identical_relative_pose',
                'common_upper_bound_mm3': value, 'maximum_region_common_mm3': value,
                'region_count': 1, 'common_upper_bound_is_sum_not_union_volume': True}

    @staticmethod
    def synthetic_flex_interval(flexible, law, low=F(0), high=domain.SEATING):
        cages = (enclosure.fpc_grouped(float(low), float(high), 'A')
                 if flexible == 'EP5_finite_material' else enclosure.oled_cages(float(low), float(high), 'A'))
        raw = [{'cage': cage['label'], 'disposition': 'clear', 'method': 'continuous_relative_axis_gap',
                'gap_lower_mm': 1.} for cage in cages]
        attempt = {**adapter.aggregate_material_regions(raw), 'reference_frame': 'A',
                   'rigid_relative_Z_interval_exact': list(map(str, law.in_frame('A').projection(low, high)))}
        return {'disposition': 'clear', 'method': 'whole_material_relative_cage',
                'descent_interval_exact': list(map(str, (low, high))), 'attempts': [attempt]}

    def test_one_volume_tolerance_for_all_material_regions(self):
        clear = self.native_common
        result = adapter.aggregate_material_regions([clear(6e-8), clear(6e-8)])
        self.assertEqual(result['disposition'], 'unresolved_enclosure_overlap')
        self.assertAlmostEqual(result['common_upper_bound_mm3'], 1.2e-7)
        self.assertEqual(adapter.aggregate_material_regions([clear(4e-8), clear(4e-8)])['disposition'], 'clear')
        for rows in ([], [clear(float('nan'))], [clear(-1.)], [{'disposition': 'clear'}]):
            with self.assertRaises(ValueError):
                adapter.aggregate_material_regions(rows)
        for gap in (-1., 0., float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                adapter.aggregate_material_regions([{'disposition': 'clear',
                    'method': 'continuous_relative_axis_gap', 'gap_lower_mm': gap}])

    def test_failed_native_attempt_is_not_erased_by_clear_reference_frame(self):
        row = {'disposition': 'clear', 'attempts': [
            {'disposition': 'unresolved_evaluation', 'error': 'first exact evaluation failed'},
            {'disposition': 'clear', 'regions': [{'disposition': 'clear',
             'initial_reference_frame_result': {'disposition': 'unresolved_evaluation', 'error': 'reverse needed'}}]}]}
        errors = adapter.collect_evaluation_errors(row)
        self.assertEqual({e['error'] for e in errors}, {'first exact evaluation failed', 'reverse needed'})

    def test_inventory_pending_source_environment_and_scope_are_fail_closed(self):
        names = adapter.expected_inventory()
        laws = domain.rigid_laws(names, {'L': '.027', 'R': '.028'}, names)
        rows = []
        for a, b in combinations(names, 2):
            flexible = {a, b} & domain.FLEXIBLE
            if not flexible:
                evidence = {'disposition': 'clear', 'method': 'continuous_relative_axis_gap',
                            'gap_lower_mm': 1., 'pair_class': 'rigid_rigid_shared_descent_polytope',
                            'exact_relative_Z_interval_mm': list(map(str, laws[a].relative_to(laws[b]).projection()))}
            elif len(flexible) == 2:
                evidence = {'disposition': 'clear', 'pair_class': 'complete_FPC_OLED_material',
                            **enclosure.flex_flex_certificate()}
            else:
                flex = next(iter(flexible)); rigid = b if a == flex else a
                evidence = {**self.synthetic_flex_interval(flex, laws[rigid]),
                            'pair_class': 'deforming_flexible_complete_rigid_material'}
            rows.append({'a': a, 'b': b, **evidence})
        identity = {'environment': {'passed': True}, 'repository_head': '0' * 40}
        own = {'scratch.py': 'a' * 64}
        check = lambda records=rows, before=identity, after=identity, own_after=own, construction=True, failure=False: (
            adapter.check_complete_result(names, records, before, after, own, own_after, construction, failure, laws))
        good = check()
        self.assertEqual(len(rows), 11781)
        self.assertTrue(good['complete_native_diagnostic_executed'])
        self.assertTrue(good['whole_declared_seating_external_pair_domain_clear'])
        self.assertFalse(good['canonical_execution_checks_passed'])
        self.assertFalse(good['whole_declared_seating_domain_clear'])
        for changed in (rows[:-1], rows + [rows[0]], [{**rows[0], 'disposition': 'unresolved_budget'}] + rows[1:]):
            self.assertFalse(check(changed)['complete_native_diagnostic_executed'])
        self.assertFalse(check(after={**identity, 'repository_head': '1' * 40})['complete_native_diagnostic_executed'])
        self.assertFalse(check(own_after={'scratch.py': 'b' * 64})['complete_native_diagnostic_executed'])
        failed_environment = {'environment': {'passed': False}}
        self.assertFalse(check(before=failed_environment, after=failed_environment)['complete_native_diagnostic_executed'])
        self.assertFalse(check(construction=False)['complete_native_diagnostic_executed'])
        self.assertFalse(check(failure=True)['complete_native_diagnostic_executed'])
        failed_try = [{**rows[0], 'prior_attempt': {'disposition': 'unresolved_evaluation', 'error': 'retained'}}] + rows[1:]
        self.assertFalse(check(failed_try)['complete_native_diagnostic_executed'])
        negative_gap = [{**rows[0], 'gap_lower_mm': -1.}] + rows[1:]
        self.assertFalse(check(negative_gap)['whole_declared_seating_external_pair_domain_clear'])

    def test_missing_cage_bad_sum_and_incomplete_interval_partition_rejected(self):
        import copy
        flex = 'EP5_finite_material'; law = domain.B_FOLLOWING
        baseline = self.synthetic_flex_interval(flex, law)
        self.assertTrue(adapter.validate_flexible_interval(baseline, flex, law, F(0), domain.SEATING))
        bad = copy.deepcopy(baseline); bad['attempts'][0]['regions'].pop()
        with self.assertRaises(ValueError):
            adapter.validate_flexible_interval(bad, flex, law, F(0), domain.SEATING)
        bad = copy.deepcopy(baseline); bad['attempts'][0]['regions'][1]['cage'] = bad['attempts'][0]['regions'][0]['cage']
        with self.assertRaises(ValueError):
            adapter.validate_flexible_interval(bad, flex, law, F(0), domain.SEATING)
        bad = copy.deepcopy(baseline); bad['attempts'][0]['common_upper_bound_mm3'] = -1.
        with self.assertRaises(ValueError):
            adapter.validate_flexible_interval(bad, flex, law, F(0), domain.SEATING)
        partition = copy.deepcopy(baseline)
        partition['method'] = 'closed_interval_partition_with_complete_material_cages'
        partition['children'] = [self.synthetic_flex_interval(flex, law, F(0), F('4.1')),
                                 self.synthetic_flex_interval(flex, law, F('4.1'), domain.SEATING)]
        self.assertTrue(adapter.validate_flexible_interval(partition, flex, law, F(0), domain.SEATING))
        partition['children'].pop()
        with self.assertRaises(ValueError):
            adapter.validate_flexible_interval(partition, flex, law, F(0), domain.SEATING)
        partition['children'].append(self.synthetic_flex_interval(flex, law, F('4.2'), domain.SEATING))
        with self.assertRaises(ValueError):
            adapter.validate_flexible_interval(partition, flex, law, F(0), domain.SEATING)


if __name__ == '__main__':
    unittest.main(verbosity=2)
