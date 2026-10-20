"""Constitutive counterexamples, independent small active-set oracle, limits."""
from pathlib import Path
import sys
import unittest
from itertools import combinations

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from slack_spring_contact import solve_tension_contact
from contact_dual_active import solve_force_qp


def enumerated_minimum(s, d, g, load):
    """Independent tiny exhaustive KKT enumeration, used only by this test."""
    solutions = []
    n = len(d)
    for count in range(n+1):
        for active in combinations(range(n), count):
            ids = np.array(active, dtype=int)
            a = np.block([[s[np.ix_(ids, ids)], -g[ids]],
                          [g[ids].T, np.zeros((len(load), len(load)))]])
            rhs = np.r_[d[ids], load]
            answer = np.linalg.lstsq(a, rhs, rcond=None)[0]
            if np.max(abs(a@answer-rhs), initial=0) > 1e-9:
                continue
            f = np.zeros(n)
            f[ids] = answer[:count]
            slack = s@f-d-g@answer[count:]
            if f.min() < -1e-9 or slack.min() < -1e-9 or np.max(abs(f*slack)) > 1e-9:
                continue
            solutions.append((.5*f@s@f-d@f, f))
    if not solutions:
        raise AssertionError("test fixture has no admissible active set")
    return min(solutions, key=lambda pair: pair[0])[1]


class SlackSpringContactTests(unittest.TestCase):
    def test_tensile_branch_and_true_release(self):
        for q in (-2., -1.2, .5):
            r = solve_tension_contact([[2.]], np.zeros((1, 0)), [q], [], [3.], [.4], [])
            self.assertTrue(r['passed'], r)
            self.assertAlmostEqual(r['forces'][0], max(0., (q+1.2)/5), places=12)
            self.assertGreaterEqual(r['spring_constitutive_slacks'][0], -1e-12)
        free = solve_force_qp([[5.]], [-.8], np.zeros((1, 0)), [], free_prefix=1)
        self.assertTrue(free['passed'])
        self.assertAlmostEqual(free['forces'][0], -.16)
        released = solve_tension_contact([[2.]], np.zeros((1, 0)), [-2.], [], [3.], [.4], [])
        self.assertEqual(released['slack_springs'], [0])
        self.assertAlmostEqual(released['spring_constitutive_slacks'][0], .8)

    def test_coupled_springs_and_contact_match_independent_enumeration(self):
        h = np.array([[2., .3, -.2], [.3, 1.5, .2], [-.2, .2, 1.]])
        g = np.array([[1.], [1.], [-1.]])
        c, pre, gaps, load = np.array([.5, 2.]), np.array([.1, .3]), np.array([.1]), np.array([.4])
        s = h+np.diag([*c, 0.])
        for q in ([.3, -.9, .8], [-2., 1., -.3], [.8, .2, .4]):
            d = np.array(q)+np.r_[c*pre, -gaps]
            expected = enumerated_minimum(s, d, g, load)
            r = solve_tension_contact(h, g, q, load, c, pre, gaps)
            self.assertTrue(r['passed'], r)
            np.testing.assert_allclose(r['forces'], expected, rtol=1e-9, atol=1e-10)
            np.testing.assert_allclose(g.T@r['forces'], load, atol=1e-10)

    def test_missing_support_and_tensile_contact_stay_rejected(self):
        missing = solve_tension_contact([[1.]], [[1., 0.]], [0.], [1., 1.], [], [], [0.])
        self.assertFalse(missing['passed'])
        self.assertEqual(missing['status'], 'unsupported_rigid_load')
        tensile = solve_tension_contact([[1.]], [[1.]], [0.], [-1.], [], [], [0.])
        self.assertFalse(tensile['passed'])
        for r in (missing, tensile):
            for key in ('candidate_go', 'fixture_fabrication_go', 'manufacturing_go'):
                self.assertFalse(r[key])

    def test_negative_body_energy_is_not_hidden_by_spring_compliance(self):
        with self.assertRaisesRegex(ValueError, 'negative complementary'):
            solve_tension_contact([[-1.]], np.zeros((1, 0)), [0.], [], [2.], [1.], [])

    def test_zero_response_rigid_stop_is_outside_thin_backend_scope(self):
        with self.assertRaisesRegex(ValueError, 'nonpositive'):
            solve_tension_contact([[0.]], [[1.]], [0.], [2.], [], [], [.02])
        r = solve_tension_contact(np.zeros((2, 2)), np.ones((2, 1)), [0., 0.], [3.], [1., 2.], [0., 0.], [])
        self.assertTrue(r['passed'], r)
        np.testing.assert_allclose(r['forces'], [2., 1.], atol=1e-10)


if __name__ == '__main__':
    unittest.main()
