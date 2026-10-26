"""Catch cross-work-package drift in actual common candidate declarations."""
import copy
import json
from pathlib import Path
import unittest

import product_contract as contract


class ProductContractTests(unittest.TestCase):
    def setUp(self):
        self.inputs = [json.loads((contract.ROOT / p).read_text()) for p in contract.INPUTS]

    def test_current_candidate_and_coupon_are_bound(self):
        result = contract.bind(*self.inputs)
        self.assertTrue(result['declarations_consistent'])
        self.assertFalse(result['solid_packing_or_full_motion_evaluated_here'])

    def test_motion_parameter_drift_is_rejected(self):
        self.inputs[2]['constraints']['B_slide_mm'] += .1
        with self.assertRaisesRegex(ValueError, 'slide'):
            contract.bind(*self.inputs)

    def test_exported_coupon_cannot_differ_from_route_width(self):
        self.inputs[2]['coupon']['width_mm'] += 1
        with self.assertRaisesRegex(ValueError, 'FPC width'):
            contract.bind(*self.inputs)

    def test_old_scene_cannot_be_used_for_current_candidate(self):
        self.inputs[2]['route_study']['common_scene_api'] = 'integration/product_assembly.py:native_scene'
        with self.assertRaisesRegex(ValueError, 'shared current scene'):
            contract.bind(*self.inputs)


if __name__ == '__main__':
    unittest.main()
