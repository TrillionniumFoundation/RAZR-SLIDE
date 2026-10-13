import math
import unittest
from bend_axis_sensitivity import loop_legs, section_index, station_curvature


class AxisWitnessTests(unittest.TestCase):
    def test_width_cannot_be_replaced_by_thickness(self):
        self.assertAlmostEqual(section_index(1.2, .15, 16.5, 0), .03636363636363636)
        self.assertAlmostEqual(section_index(1.2, .15, 16.5, 90), .004545454545454545)
        self.assertAlmostEqual(section_index(1.2, .15, 16.5, 0) /
                               section_index(1.2, .15, 16.5, 90), 8)

    def test_increased_thickness_affects_easy_axis(self):
        self.assertAlmostEqual(section_index(1.2, .30, 16.5, 90),
                               2 * section_index(1.2, .15, 16.5, 90))

    def test_larger_radius_reduces_index_and_reversal_keeps_magnitude(self):
        self.assertAlmostEqual(section_index(1.2, .15, 33, 45),
                               .5 * section_index(1.2, .15, 16.5, 45))
        self.assertAlmostEqual(section_index(1.2, .15, 16.5, 45),
                               section_index(1.2, .15, 16.5, 225))

    def test_fixed_station_experiences_bending_and_unbending(self):
        self.assertGreater(station_curvature(10, 0), 0)
        self.assertEqual(station_curvature(10, 79.75), 0)
        self.assertEqual(station_curvature(90, 0), 0)
        self.assertGreater(station_curvature(90, 79.75), 0)

    def test_length_conservation_at_different_slides(self):
        for slide in (0, 19.9375, 39.875, 59.8125, 79.75):
            a, b = loop_legs(slide)
            self.assertAlmostEqual(a + math.pi * 16.5 + b, 120)
        self.assertAlmostEqual(loop_legs(79.75)[0] - loop_legs(0)[0], 79.75 / 2)

    def test_bad_dimension_cannot_produce_clearance_number(self):
        for value in (0, -1, math.nan, math.inf, True, "0.15"):
            with self.assertRaises(ValueError):
                section_index(1.2, .15, value, 0)
        with self.assertRaises(ValueError):
            station_curvature(121, 0)
        with self.assertRaises(ValueError):
            loop_legs(80)


if __name__ == "__main__":
    unittest.main()
