"""Independent checks of terminal material budgets and full native endpoints.

The three native tests are mandatory in the repository's native runtime. A
partial scratch checkout may execute only the eleven arithmetic tests; that
run must retain its three skips and cannot be reported as fourteen passes.
"""
import copy
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'integration'))
import product_routing_diagnostic as r


class RoutingArithmeticTests(unittest.TestCase):
    def setUp(self):
        self.config = r.load_config()
        self.spec = json.loads(r.GEOMETRY.read_text())['oled_storage_study']

    def test_user_constraints_cannot_change_in_diagnostic(self):
        changed = copy.deepcopy(self.config)
        changed['constraints']['slide_mm'] = 80.
        # Validate through a temporary config file, keeping the real design intact.
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'bad.json'
            path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                r.load_config(path)

    def test_g2_radius_matches_retained_route_and_is_length_independent(self):
        c = r.g2_coefficient()
        report = r.arithmetic_report()
        self.assertAlmostEqual(c['R_per_delta_Z_approx']*.5, .2182854, places=6)
        self.assertAlmostEqual(c['R_per_delta_Z_approx']*8.7, 3.798166, places=5)
        self.assertTrue(report['legacy_endpoint_lanes']['radius_depends_on_Z_lane_separation_not_total_material_length'])
        lo, hi = c['R_per_delta_Z_conservative_numeric_interval']
        self.assertLess(lo, c['R_per_delta_Z_approx'])
        self.assertGreater(hi, c['R_per_delta_Z_approx'])
        self.assertFalse(c['formal_directed_rounding_certificate'])

    def test_fixed_EP2_config_cannot_relabel_unchanged_native_geometry(self):
        import tempfile
        for key,value in [('board_y_mm',[-16.,-4.]),('DS_z_mm',[2.,2.8]),
                          ('carrier_width_mm',12.),('boards_across_both_ends',2)]:
            changed = copy.deepcopy(self.config)
            changed['endpoint_candidate'][key] = value
            with tempfile.TemporaryDirectory() as td:
                path = Path(td)/'relabeled.json'
                path.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    r.load_config(path)

    def test_zero_retention_window_reconstructs_original_family(self):
        q = r.oled_retention(self.spec, 0.)
        self.assertAlmostEqual(q['interval_width_mm'], .6, places=10)
        self.assertAlmostEqual(q['current_PREDOCK_flat_tail_mm'], .13119675101886, places=9)
        self.assertTrue(q['nonempty_interval'])
        self.assertTrue(q['lower_limit_is_strict_if_zero_reserve'])

    def test_finite_clamp_is_not_free_extra_display_length(self):
        q = r.oled_retention(self.spec, 1.)
        self.assertFalse(q['nonempty_interval'])
        self.assertFalse(q['current_material_meets_flat_tail_request'])
        self.assertIsNone(q['current_COF_envelope'])
        self.assertIsNone(q['actual_inactive_edge_available_for_clamp_mm'])

    def test_three_mm_tail_exposes_minimum_material_and_storage_changes(self):
        q = r.oled_retention(self.spec, 3.)
        self.assertAlmostEqual(q['minimum_added_material_to_current_trial_mm'], 2.86880324898116, places=9)
        self.assertAlmostEqual(q['minimum_storage_extension_toward_B_foot_if_turn_unchanged_mm'], 2.4, places=10)
        self.assertAlmostEqual(q['maximum_B_storage_y_min_if_turn_unchanged_mm'], 3., places=10)

    def test_optimistic_turn_shift_cannot_supply_three_mm_tail(self):
        q = r.oled_retention(self.spec, 3.)
        self.assertAlmostEqual(q['optimistic_turn_forward_allowance_mm'], .475, places=9)
        self.assertAlmostEqual(q['minimum_storage_extension_even_with_optimistic_turn_shift_mm'], 1.925, places=9)
        self.assertTrue(q['head_bound_is_not_a_free_cavity_or_native_clearance_proof'])

    def test_old_full_endpoint_cannot_fit_under_return_guide_by_anchor_shift(self):
        for flipped in (False, True):
            q = r.endpoint_anchor_interval(.65, 5.65, 'legacy', flipped=flipped)
            self.assertFalse(q['necessary_envelope_fit_possible'])
            self.assertAlmostEqual(q['full_endpoint_z_span_mm'], 5.7, places=10)
            self.assertAlmostEqual(q['height_shortfall_mm'], .7, places=10)

    def test_EP2_carrier_width_and_margin_cannot_be_hidden(self):
        bounds = r.endpoint_stack_bounds('EP2')
        self.assertEqual(bounds['width_by_end_mm'], {'A':14.6,'B':14.6})
        self.assertAlmostEqual(bounds['height_mm'], 4.65)
        q = r.endpoint_anchor_interval(.65, 5.65, 'EP2', gap=.2)
        self.assertFalse(q['necessary_envelope_fit_possible'])
        self.assertAlmostEqual(q['height_shortfall_mm'], .05, places=10)

    def test_invalid_dimensions_are_not_silently_accepted(self):
        for bad in (True, float('nan'), float('inf'), -1.):
            with self.assertRaises(ValueError):
                r.oled_retention(self.spec, bad)
        with self.assertRaises(ValueError):
            r.endpoint_anchor_interval(2., 1.)
        with self.assertRaises(ValueError):
            r.g2_coefficient(63)

    def test_arithmetic_report_never_asserts_native_or_physical_completion(self):
        q = r.arithmetic_report()
        for key in ('native_checks_executed','candidate_go','fixture_fabrication_go',
                    'manufacturing_go','full_cycle_internal_route_accepted',
                    'selected_OLED_COF_and_dynamic_stack'):
            self.assertIs(q[key], False)
        self.assertEqual(q['candidate_definition']['boards_across_both_ends'], 4)
        self.assertFalse(q['candidate_definition']['individual_static_conductors_routed'])


@unittest.skipUnless((ROOT/'integration/straight_envelope.py').is_file(),
                     'partial scratch checkout lacks integration/straight_envelope.py; not a complete suite pass')
class RoutingNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import product_interfaces as interfaces
        import product_fpc as f
        cls.f = f
        cls.cfg = interfaces.load_config()
        cls.legacy = {e:f.local_endpoint_parts(cls.cfg,e) for e in ('A','B')}
        cls.ep2 = {e:r.ep2_local_parts(cls.cfg,e) for e in ('A','B')}
        cls.legacy_checks = {e:r.native_pair_checks(cls.legacy[e]) for e in ('A','B')}
        cls.ep2_checks = {e:r.native_pair_checks(cls.ep2[e]) for e in ('A','B')}

    def test_actual_legacy_negative_control_detects_jaw_transfer_collision(self):
        for end,expected in [('A',71.55),('B',164.565)]:
            check = self.legacy_checks[end]
            self.assertEqual(check['pair_count'],190)
            row = next(x for x in check['pairs'] if {x['a'],x['b']} == {'lower_jaw','static_26wire_transfer_reservation'})
            self.assertTrue(row['positive_material_common'])
            self.assertAlmostEqual(row['common_mm3'], expected, places=6)
            self.assertFalse(check['no_positive_common_or_evaluation_error'])

    def test_complete_EP2_self_pairs_are_clear_with_connected_carrier(self):
        import product_assembly as p
        for end in ('A','B'):
            parts = self.ep2[end]
            self.assertEqual(len(parts),20)
            self.assertEqual(len([k for k in parts if k.endswith('_PCB')]),2)
            self.assertEqual(len(parts['lower_jaw'].Solids()),1)
            self.assertTrue(parts['lower_jaw'].isValid())
            self.assertEqual(self.ep2_checks[end]['pair_count'],190)
            self.assertTrue(self.ep2_checks[end]['no_positive_common_or_evaluation_error'],self.ep2_checks[end]['failures'])
            b = p.bounds(parts['lower_jaw'])
            self.assertAlmostEqual(b[1]-b[0],14.6,places=7)
            self.assertAlmostEqual(b[3]-b[2],35.,places=7)

    def test_full_EP2_material_pairs_preserve_OPEN_B_clamp_negative_control(self):
        # Native report at 1c970e3 rejects OPEN: the retained free ribbon cuts
        # both B clamp screws and the B lower jaw. Endpoint self-pair clearance
        # does not imply that the complete moving material clears the endpoints.
        open_b_overlaps = {
            ('finite_material','B_M2_clamp_screw_1'): .314159265358978,
            ('finite_material','B_M2_clamp_screw_2'): .314159265358978,
            ('finite_material','B_lower_jaw'): 16.039734577831304,
        }

        def assert_pairs(check, expected_pairs, expected_overlaps):
            self.assertTrue(check['all_pairs_evaluated'])
            self.assertEqual(check['pair_count'],len(expected_pairs))
            self.assertEqual(len(check['pairs']),len(expected_pairs))
            rows = {(row['a'],row['b']):row for row in check['pairs']}
            self.assertEqual(set(rows),expected_pairs)
            self.assertFalse(any(row.get('evaluation_failed') for row in check['pairs']),check['failures'])
            self.assertEqual(len(check['failures']),len(expected_overlaps))
            self.assertEqual({(row['a'],row['b']) for row in check['failures']},set(expected_overlaps))
            self.assertIs(check['no_positive_common_or_evaluation_error'],not bool(expected_overlaps))
            for pair,row in rows.items():
                self.assertIs(row['positive_material_common'],pair in expected_overlaps)
                self.assertTrue(math.isfinite(row['common_mm3']))
                self.assertGreaterEqual(row['common_mm3'],0.)
                if pair in expected_overlaps:
                    self.assertEqual(row['method'],'native_common')
                    self.assertEqual(row['axis_gap_lower_mm'],0.)
                    self.assertGreater(row['common_mm3'],r.TOL)
                    self.assertAlmostEqual(row['common_mm3'],expected_overlaps[pair],places=6)
                else:
                    self.assertLessEqual(row['common_mm3'],r.TOL)

        for pose,slide,descent in (('STOW',0.,0.),('PREDOCK',79.75,0.),('OPEN',79.75,8.2)):
            sections,_ = self.f.route_pose(self.cfg,slide,descent)
            material,_ = self.f.finite_material_solid(sections['corners'])
            placed = {e:self.f.place_endpoint(self.ep2[e],sections,e) for e in ('A','B')}
            for end in ('A','B'):
                with self.subTest(pose=pose,group='material_to_'+end+'_endpoint'):
                    self.assertEqual(len(placed[end]),20)
                    check = r.native_pair_checks({'finite_material':material},placed[end])
                    expected = open_b_overlaps if (pose,end)==('OPEN','B') else {}
                    assert_pairs(check,{('finite_material',name) for name in placed[end]},expected)
            with self.subTest(pose=pose,group='A_to_B_endpoints'):
                check = r.native_pair_checks(placed['A'],placed['B'])
                self.assertEqual(check['pair_count'],400)
                assert_pairs(check,{(a,b) for a in placed['A'] for b in placed['B']},{})


if __name__ == '__main__':
    unittest.main()
