"""Composite mechanics identities and actual missing-input counterexamples."""
import unittest, math
from layer_stackup import Layer,section,build_report

class SectionTests(unittest.TestCase):
    def test_unknown_moduli_do_not_become_midplane(self):
        x=section([Layer('BASE',12),Layer('RA_COPPER',18),Layer('TOP',26)])
        self.assertIsNone(x['neutral_axis_um']);self.assertIsNone(x['finished_thickness_max_um'])
    def test_single_copper_layer_has_true_midplane(self):
        x=section([Layer('RA_COPPER',18,110)])
        self.assertEqual(x['neutral_axis_um'],9);self.assertEqual(x['copper_distance_um'],9)
    def test_symmetric_identical_skins_leave_copper_centered(self):
        x=section([Layer('BASE',12,3),Layer('RA_COPPER',18,110),Layer('TOP',12,3)])
        self.assertAlmostEqual(x['neutral_axis_um'],21)
    def test_equal_moduli_recover_geometric_midplane(self):
        x=section([Layer('BASE',12,1),Layer('RA_COPPER',18,1),Layer('TOP',26,1)])
        self.assertAlmostEqual(x['neutral_axis_um'],28)
    def test_common_modulus_scale_does_not_change_plane(self):
        a=[Layer('BASE',12,2),Layer('RA_COPPER',18,20),Layer('TOP',26,3)]
        b=[Layer(x.name,x.thickness_um,x.modulus_GPa*17) for x in a]
        self.assertAlmostEqual(section(a)['neutral_axis_um'],section(b)['neutral_axis_um'])
    def test_coverlay_changes_copper_distance(self):
        a=section([Layer('BASE',12,1),Layer('RA_COPPER',18,1)])
        b=section([Layer('BASE',12,1),Layer('RA_COPPER',18,1),Layer('TOP',26,1)])
        self.assertNotEqual(a['copper_distance_um'],b['copper_distance_um'])
    def test_swapped_stack_reverses_plane(self):
        a=[Layer('BASE',12,3),Layer('RA_COPPER',18,110),Layer('TOP',26,1)]
        x,y=section(a),section(list(reversed(a)))
        self.assertAlmostEqual(x['neutral_axis_um']+y['neutral_axis_um'],56)
        self.assertAlmostEqual(x['copper_distance_um'],y['copper_distance_um'])
    def test_unknown_modulus_bound_contains_extreme_examples(self):
        a=[Layer('BASE',12),Layer('RA_COPPER',18),Layer('TOP',26)];bound=section(a)
        for e in [(1e8,1,1),(1,1e8,1),(1,1,1e8)]:
            x=section([Layer(r.name,r.thickness_um,m) for r,m in zip(a,e)])
            self.assertLessEqual(x['copper_distance_um'],bound['conditional_max_copper_distance_upper_um'])
    def test_true_nominal_56_is_not_bare_30(self):
        x=build_report()['sections'][0];self.assertEqual(x['nominal_unprocessed_thickness_um'],56)
        self.assertIsNone(x['finished_thickness_max_um']);self.assertFalse(x['manufacturing_go'])
    def test_invalid_physical_values_reject(self):
        for v in [0,-1,math.inf,math.nan,True]:
            with self.assertRaises(ValueError):section([Layer('RA_COPPER',v,1)])
            with self.assertRaises(ValueError):section([Layer('RA_COPPER',18,v)])

if __name__=='__main__':unittest.main(verbosity=2)
