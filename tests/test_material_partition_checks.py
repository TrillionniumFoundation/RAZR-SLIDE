"""Regressions for one tolerance budget per complete material/obstacle pair."""
from pathlib import Path
import copy
import math
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integration'))
import cadquery as cq
from material_partition_checks import stop_key_partition_checks
from straight_envelope import whole_material
from translation_regions import regions


def records(values=(0., 0., 0., 0.)):
    return [{'side': side, 'stop': stop, 'pin_common_mm3': values[0],
             'remainder_common_mm3': list(values[1:])}
            for side in 'LR' for stop in range(2)]


class MaterialPartitionChecksTests(unittest.TestCase):
    def test_complete_zero_partitions_clear(self):
        checks = stop_key_partition_checks(records())
        self.assertEqual(len(checks), 4)
        self.assertTrue(all(x['whole_STOP_KEY_proved_clear'] for x in checks))

    def test_order_does_not_change_pair_identity(self):
        checks = stop_key_partition_checks(list(reversed(records())))
        self.assertEqual({(x['side'], x['stop']) for x in checks}, {('L', 0), ('L', 1), ('R', 0), ('R', 1)})

    def test_native_translation_subthreshold_pieces_hide_real_overlap(self):
        body = cq.Solid.makeBox(1., 1., 1.)
        enclosures, _ = regions(body, (2., 2., 0.))
        obstacle = cq.Solid.makeBox(.01, .01, .0018, cq.Vector(1.495, 1.495, .4))
        values = [whole_material(part.intersect(obstacle), empty=True)[1] for part in enclosures]
        actual = whole_material(body.translate((1., 1., 0.)).intersect(obstacle), empty=True)[1]
        self.assertEqual(len(values), 4)
        self.assertTrue(all(value <= 1e-7 for value in values))
        self.assertGreater(actual, 1e-7)
        checks = stop_key_partition_checks(records(values))
        self.assertTrue(all(not x['whole_STOP_KEY_proved_clear'] for x in checks))
        self.assertTrue(all(x['common_upper_bound_mm3'] >= actual - 1e-14 for x in checks))

    def test_same_pair_shares_one_tolerance_budget(self):
        checks = stop_key_partition_checks(records((3e-8, 3e-8, 3e-8, 3e-8)))
        self.assertTrue(all(not x['whole_STOP_KEY_proved_clear'] for x in checks))
        self.assertAlmostEqual(checks[0]['common_upper_bound_mm3'], 1.2e-7)

    def test_distinct_pairs_do_not_share_a_tolerance_budget(self):
        checks = stop_key_partition_checks(records((9e-8, 0., 0., 0.)))
        self.assertGreater(sum(x['common_upper_bound_mm3'] for x in checks), 1e-7)
        self.assertTrue(all(x['whole_STOP_KEY_proved_clear'] for x in checks))

    def test_exact_tolerance_is_inclusive(self):
        checks = stop_key_partition_checks(records((1e-7, 0., 0., 0.)))
        self.assertTrue(all(x['whole_STOP_KEY_proved_clear'] for x in checks))

    def test_missing_or_extra_partitions_reject(self):
        for entries in (records()[:3], records() + records()[:1]):
            with self.subTest(count=len(entries)), self.assertRaises(ValueError):
                stop_key_partition_checks(entries)

    def test_duplicate_partition_cannot_replace_missing_pair(self):
        entries = records()
        entries[3] = copy.deepcopy(entries[2])
        with self.assertRaises(ValueError):
            stop_key_partition_checks(entries)

    def test_invalid_identity_rejects(self):
        for key, value in (('side', 'X'), ('side', None), ('stop', True), ('stop', 0.), ('stop', 2)):
            entries = records()
            entries[0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                stop_key_partition_checks(entries)

    def test_all_three_remainder_members_are_required(self):
        for remainder in ([], [0., 0.], [0.] * 4, None, '000'):
            entries = records()
            entries[0]['remainder_common_mm3'] = remainder
            with self.subTest(remainder=remainder), self.assertRaises(ValueError):
                stop_key_partition_checks(entries)

    def test_invalid_member_values_fail_closed(self):
        for value in (-1., math.nan, math.inf, True, '0', None):
            for member in ('pin', 'remainder'):
                entries = records()
                if member == 'pin':
                    entries[0]['pin_common_mm3'] = value
                else:
                    entries[0]['remainder_common_mm3'][1] = value
                with self.subTest(value=value, member=member), self.assertRaises(ValueError):
                    stop_key_partition_checks(entries)

    def test_invalid_tolerance_rejects(self):
        for tolerance in (0., -1., math.nan, math.inf, True, '1e-7', None):
            with self.subTest(tolerance=tolerance), self.assertRaises(ValueError):
                stop_key_partition_checks(records(), tolerance)


if __name__ == '__main__':
    unittest.main()
