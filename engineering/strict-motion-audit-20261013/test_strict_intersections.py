"""Real OCC participant witnesses plus explicit scalar common contracts."""
import math
import unittest

import cadquery as cq

from occ_signed_volume import InconsistentGeometry, check_common_volume
from strict_intersections import participant, strict_common


def reversed_shape(shape):
    return cq.Shape.cast(shape.wrapped.Reversed())


class StrictIntersectionTests(unittest.TestCase):
    def setUp(self):
        self.box = cq.Workplane("XY").box(1, 1, 1).val()

    def test_real_reversed_far_body_rejected_before_AABB(self):
        reversed_far = reversed_shape(self.box.translate((10, 0, 0)))
        self.assertTrue(reversed_far.isValid())
        self.assertEqual(len(reversed_far.Solids()), 1)
        self.assertLess(reversed_far.Volume(), 0.)
        with self.assertRaises(InconsistentGeometry):
            strict_common(self.box, reversed_far)

    def test_real_reversed_far_ribbon_rejected_before_AABB(self):
        with self.assertRaises(InconsistentGeometry):
            strict_common(reversed_shape(self.box), self.box.translate((10, 0, 0)))

    def test_real_valid_wire_with_positive_volume_is_not_solid(self):
        wire = cq.Workplane("XY").rect(1, 1).val()
        self.assertTrue(wire.isValid())
        self.assertGreater(wire.Volume(), 0.)
        self.assertEqual(len(wire.Solids()), 0)
        with self.assertRaises(InconsistentGeometry):
            strict_common(self.box, wire.translate((10, 0, 0)))

    def test_real_multi_solid_far_compound_rejected(self):
        compound = cq.Compound.makeCompound([self.box.translate((10, 0, 0)),
                                            self.box.translate((12, 0, 0))])
        with self.assertRaises(InconsistentGeometry):
            strict_common(self.box, compound)

    def test_real_single_solid_compound_allowed_without_discarding_topology(self):
        compound = cq.Compound.makeCompound([self.box])
        self.assertTrue(participant(compound)["pure_single_solid_compound_wrapper"])
        self.assertAlmostEqual(strict_common(self.box, compound)["checked_volume_mm3"], 1.)

    def test_real_single_solid_plus_loose_wire_rejected(self):
        wire = cq.Workplane("XY").rect(1, 1).val().translate((10, 0, 0))
        compound = cq.Compound.makeCompound([self.box, wire])
        self.assertTrue(compound.isValid())
        self.assertEqual(len(compound.Solids()), 1)
        with self.assertRaises(InconsistentGeometry):
            strict_common(self.box, compound)

    def test_real_repeated_existing_wire_is_rejected_despite_equal_counts_and_volume(self):
        alias_box = cq.Workplane("XY").box(1, 2, 3).val()
        compound = cq.Compound.makeCompound([alias_box, alias_box.Wires()[0]])
        for method in ("Vertices", "Edges", "Wires", "Faces", "Shells", "Solids"):
            self.assertEqual(len(getattr(compound, method)()), len(getattr(alias_box, method)()))
        self.assertEqual(compound.Volume(), alias_box.Volume())
        with self.assertRaises(InconsistentGeometry):
            strict_common(self.box, compound)

    def test_real_positive_separation_is_explicit_non_boolean_result(self):
        result = strict_common(self.box, self.box.translate((2, 0, 0)))
        self.assertFalse(result["OCC_boolean_was_run"])
        self.assertIsNone(result["raw_signed_volume_mm3"])
        self.assertEqual(result["checked_volume_mm3"], 0.)

    def test_disjoint_invalid_tolerance_is_rejected_before_AABB(self):
        for tolerance in (math.nan, math.inf, -1.):
            with self.assertRaises(InconsistentGeometry):
                strict_common(self.box, self.box.translate((2, 0, 0)), tolerance)

    def test_real_zero_gap_touch_is_not_pruned_as_positive_clearance(self):
        result = strict_common(self.box, self.box.translate((1, 0, 0)))
        self.assertTrue(result["OCC_boolean_was_run"])
        self.assertEqual(result["raw_signed_volume_mm3"], 0.)

    def test_real_overlap(self):
        result = strict_common(self.box, self.box.translate((.5, 0, 0)))
        self.assertTrue(result["OCC_boolean_was_run"])
        self.assertAlmostEqual(result["checked_volume_mm3"], .5)

    def test_real_tiny_reversed_common_witness_is_negative_not_numeric_zero(self):
        small = cq.Workplane("XY").box(1e-4, 1e-4, 1e-4).val()
        reversed_small = reversed_shape(small)
        raw = reversed_small.intersect(small)
        self.assertTrue(raw.isValid())
        self.assertLess(raw.Volume(), 0.)
        self.assertAlmostEqual(raw.Volume(), -1e-12, delta=1e-25)
        with self.assertRaises(InconsistentGeometry):
            strict_common(reversed_small, small)

    def test_explicit_scalar_contract_any_negative_common_is_rejected(self):
        for raw in (-.01, -1e-12, -1e-15):
            with self.assertRaises(InconsistentGeometry):
                check_common_volume(raw, 1., 2.)

    def test_explicit_scalar_contract_nonfinite_and_upper_bound_rejected(self):
        for raw in (math.nan, math.inf, -math.inf, 1.00001):
            with self.assertRaises(InconsistentGeometry):
                check_common_volume(raw, 1., 2.)


if __name__ == "__main__":
    unittest.main()
