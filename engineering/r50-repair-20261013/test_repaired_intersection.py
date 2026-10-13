import unittest
from pathlib import Path
import sys
import cadquery as cq

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from r50_full_span_finite_ribbon import solid_intersection
from occ_signed_volume import InconsistentGeometry


class ParticipatingSolidValidation(unittest.TestCase):
    def test_disjoint_valid_body_and_cell(self):
        body = cq.Workplane("XY").box(1, 1, 1).val()
        cell = body.translate((5, 0, 0))
        result = solid_intersection([cell], body)
        self.assertEqual(result["mm3"], 0.)
        self.assertTrue(result["per_cell_signed_volumes_checked"])

    def test_reversed_valid_body_cannot_bypass_guard_when_disjoint(self):
        normal = cq.Workplane("XY").box(1, 1, 1).val()
        reversed_body = cq.Shape.cast(normal.wrapped.Reversed())
        self.assertTrue(reversed_body.isValid())
        self.assertLess(reversed_body.Volume(), 0.)
        with self.assertRaises(InconsistentGeometry):
            solid_intersection([normal.translate((5, 0, 0))], reversed_body)

    def test_reversed_disjoint_cell_is_also_rejected(self):
        body = cq.Workplane("XY").box(1, 1, 1).val()
        translated = body.translate((5, 0, 0))
        reversed_cell = cq.Shape.cast(translated.wrapped.Reversed())
        with self.assertRaises(InconsistentGeometry):
            solid_intersection([reversed_cell], body)

    def test_disjoint_zero_thickness_cell_is_not_a_solid(self):
        body = cq.Workplane("XY").box(1, 1, 1).val()
        degenerate_cell = cq.Workplane("XY").rect(1, 1).wire().val().translate((5, 0, 0))
        self.assertGreater(degenerate_cell.BoundingBox().xmin, body.BoundingBox().xmax)
        self.assertEqual(len(degenerate_cell.Solids()), 0)
        with self.assertRaises(InconsistentGeometry):
            solid_intersection([degenerate_cell], body)


if __name__ == "__main__":
    unittest.main()
