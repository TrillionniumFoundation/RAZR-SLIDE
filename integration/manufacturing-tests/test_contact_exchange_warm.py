from pathlib import Path
import sys, unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
from contact_exchange import feasible_force_guess
from contact_dual_active import solve_force_qp

class FeasibleWarmGuessTests(unittest.TestCase):
    def test_already_feasible_is_copied(self):
        old=np.array([1.,2.]);r=feasible_force_guess(np.ones((2,1)),np.array([3.]),old,free_prefix=0)
        self.assertEqual(r['status'],'already_feasible');self.assertFalse(np.shares_memory(r['forces'],old))

    def test_changed_load_gets_feasible_nonnegative_guess(self):
        r=feasible_force_guess(np.ones((2,1)),np.array([3.]),np.array([1.,1.]),free_prefix=0)
        self.assertEqual(r['status'],'projected_feasible');self.assertAlmostEqual(r['forces'].sum(),3.)
        self.assertGreaterEqual(r['forces'].min(),0.)

    def test_free_prefix_can_carry_signed_force(self):
        r=feasible_force_guess(np.ones((2,1)),np.array([-2.]),np.array([0.,1.]),free_prefix=1)
        self.assertIsNotNone(r['forces']);self.assertAlmostEqual(r['forces'].sum(),-2.)
        self.assertGreaterEqual(r['forces'][1],0.)

    def test_unsupported_load_has_no_guess_not_fake_anchor(self):
        r=feasible_force_guess(np.zeros((2,1)),np.array([1.]),np.array([0.,1.]),free_prefix=0)
        self.assertIsNone(r['forces']);self.assertEqual(r['status'],'no_feasible_guess')

    def test_neutral_zero_load_mode_is_not_fixed(self):
        g=np.array([[1.,0.],[1.,0.]])
        r=feasible_force_guess(g,np.array([3.,0.]),np.array([1.,1.]),free_prefix=0)
        np.testing.assert_allclose(g.T@r['forces'],[3.,0.],atol=1e-12)
        self.assertTrue(r['optimizer_guess_only'])

    def test_force_scaling_preserves_feasibility(self):
        for scale in (1e-8,1.,1e8):
            r=feasible_force_guess(np.ones((2,1)),np.array([3.])*scale,np.ones(2)*scale,free_prefix=0)
            self.assertAlmostEqual(r['forces'].sum()/scale,3.)

    def test_bad_numeric_arrays_are_refused(self):
        for g in (np.ones((2,1),dtype=bool),np.array([[np.nan],[1.]]),np.array([[np.inf],[1.]])):
            with self.assertRaises(ValueError):feasible_force_guess(g,[1.],[0.,1.],free_prefix=0)

    def test_mismatched_dimensions_are_refused(self):
        with self.assertRaises(ValueError):feasible_force_guess(np.ones((3,1)),[1.],[0.,1.],free_prefix=0)
        with self.assertRaises(ValueError):feasible_force_guess(np.ones((2,1)),[1.,2.],[0.,1.],free_prefix=0)

    def test_invalid_free_prefix_refused(self):
        for f in (True,-1,3,1.5):
            with self.assertRaises(ValueError):feasible_force_guess(np.ones((2,1)),[1.],[0.,1.],free_prefix=f)

    def test_input_arrays_unchanged(self):
        g=np.ones((2,1));b=np.array([3.]);old=np.array([1.,1.]);copies=[x.copy() for x in (g,b,old)]
        feasible_force_guess(g,b,old,free_prefix=0)
        for x,y in zip((g,b,old),copies):np.testing.assert_array_equal(x,y)

    def test_infeasible_previous_is_only_a_guess(self):
        r=feasible_force_guess(np.ones((2,1)),[1.],[-.2,1.2],free_prefix=0)
        self.assertGreaterEqual(r['forces'].min(),0.);self.assertAlmostEqual(r['forces'].sum(),1.)

    def test_energy_QP_still_solves_independently_after_warm_guess(self):
        S=np.diag([2.,1.,3.]);g=np.ones((3,1));load=np.array([2.]);d=np.array([.3,.7,.9])
        r=feasible_force_guess(g,load,[.3,.5,.2],free_prefix=1)
        cold=solve_force_qp(S,d,g,load,free_prefix=1)
        warm=solve_force_qp(S,d,g,load,free_prefix=1,initial=r['forces'])
        self.assertTrue(cold['passed'] and warm['passed'])
        np.testing.assert_allclose(cold['forces'],warm['forces'],atol=1e-11)
