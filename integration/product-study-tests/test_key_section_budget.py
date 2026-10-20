"""Formula and scaling checks; none establish a real boundary condition."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from key_section_budget import section_properties, cantilever_stiffness_N_per_mm, euler_load_N, build_study


class KeySectionBudgetTests(unittest.TestCase):
    def test_section_axes_and_dimensional_scaling(self):
        p = section_properties(.25, .30)
        self.assertAlmostEqual(p['area_mm2'], .075)
        self.assertAlmostEqual(p['I_about_x_mm4'], .0005625)
        self.assertAlmostEqual(p['I_about_z_mm4'], .000390625)
        doubled = section_properties(.50, .60)
        self.assertAlmostEqual(doubled['weak_I_mm4']/p['weak_I_mm4'], 16.)

    def test_span_and_effective_length_scaling_have_distinct_powers(self):
        e, inertia = 70., .000390625
        self.assertAlmostEqual(euler_load_N(e, 12., inertia, 1.)/euler_load_N(e, 6., inertia, 1.), .25)
        self.assertAlmostEqual(euler_load_N(e, 12., inertia, 2.)/euler_load_N(e, 12., inertia, 1.), .25)
        self.assertAlmostEqual(cantilever_stiffness_N_per_mm(e, 6., inertia)/cantilever_stiffness_N_per_mm(e, 12., inertia), 8.)
        r = build_study()
        self.assertFalse(r['actual_load_or_boundary_condition_known'])
        self.assertFalse(r['strength_qualified'])
        self.assertFalse(r['physical_failure_inferred'])


if __name__ == '__main__':
    unittest.main()
