import math
import unittest
import cadquery as cq
from occ_signed_volume import common, cells_against_body, check_common_volume, InconsistentGeometry


class SignedVolumeValidation(unittest.TestCase):
    def test_negative_valid_kernel_result_is_rejected(self):
        with self.assertRaises(InconsistentGeometry):
            check_common_volume(-0.01, 1., 5.)

    def test_common_cannot_exceed_cell(self):
        with self.assertRaises(InconsistentGeometry):
            check_common_volume(1.1, 1., 5.)

    def test_common_cannot_exceed_body(self):
        with self.assertRaises(InconsistentGeometry):
            check_common_volume(1.1, 5., 1.)

    def test_nonfinite_result_rejected(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.assertRaises(InconsistentGeometry):
                check_common_volume(value, 1., 5.)

    def test_nonpositive_input_rejected(self):
        for value in (-1., 0.):
            with self.assertRaises(InconsistentGeometry):
                check_common_volume(0., value, 5.)

    def test_tiny_negative_is_uncertain_never_clearance(self):
        with self.assertRaises(InconsistentGeometry):
            check_common_volume(-1e-12, 1., 5., 1e-7)

    def test_real_disjoint_boxes(self):
        a = cq.Workplane("XY").box(1, 1, 1).val()
        b = a.translate((2, 0, 0))
        self.assertEqual(common(a, b)["checked_volume_mm3"], 0.)

    def test_real_overlapping_boxes(self):
        a = cq.Workplane("XY").box(1, 1, 1).val()
        b = a.translate((.5, 0, 0))
        self.assertAlmostEqual(common(a, b)["checked_volume_mm3"], .5, places=8)

    def test_real_containment(self):
        a = cq.Workplane("XY").box(1, 1, 1).val()
        b = cq.Workplane("XY").box(2, 2, 2).val()
        self.assertAlmostEqual(common(a, b)["checked_volume_mm3"], 1., places=8)

    def test_multiple_loft_cells_must_not_claim_union_volume(self):
        a = cq.Workplane("XY").box(1, 1, 1).val()
        report = cells_against_body([a, a], a)
        self.assertAlmostEqual(report["sum_of_checked_cell_common_volumes_mm3"], 2., places=8)
        self.assertTrue(report["sum_is_not_union_or_authorized_cut_volume"])
        self.assertFalse(report["manufacturing_go"])


if __name__ == "__main__":
    unittest.main()
