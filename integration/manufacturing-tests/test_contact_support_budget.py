from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contact_support_budget import solve_support


def stop(q=.2,gap=.1):
    return solve_support([[1.]],np.empty((1,0)),[q],[],[],[],[gap])


def joint(load,pre=2.,kb=10.):
    return solve_support(np.zeros((2,2)),[[-1.],[1.]],[0.,0.],[-load],[1/kb],[pre],[0.])


class ContactSupportTests(unittest.TestCase):
    def test_open_stop_transmits_no_tension(self):
        r=stop(.05);self.assertTrue(r['passed']);self.assertEqual(r['contact_forces'],[0.]);self.assertAlmostEqual(r['remaining_contact_gaps'][0],.05)
    def test_closed_stop_positive_reaction(self):
        r=stop();self.assertAlmostEqual(r['contact_forces'][0],.1);self.assertAlmostEqual(r['remaining_contact_gaps'][0],0.)
    def test_unloaded_initial_preload_has_equal_compression(self):
        r=joint(0);np.testing.assert_allclose(r['forces'],[2.,2.],atol=1e-10)
    def test_clamped_joint_unloads_contact_not_bolt(self):
        r=joint(1);np.testing.assert_allclose(r['forces'],[2.,1.],atol=1e-10)
    def test_separated_joint_is_not_silently_clamped(self):
        r=joint(3);np.testing.assert_allclose(r['forces'],[3.,0.],atol=1e-10);self.assertAlmostEqual(r['remaining_contact_gaps'][0],.1)
    def test_zero_preload_not_assigned(self):
        r=joint(1,0);np.testing.assert_allclose(r['forces'],[1.,0.],atol=1e-10)
    def test_each_bolt_has_own_stiffness(self):
        r=solve_support(np.zeros((3,3)),[[-1.],[-1.],[1.]],[0.,0.,0.],[-3.],[.1,.2],[0.,0.],[0.]);np.testing.assert_allclose(r['bolt_forces'],[2.,1.],atol=1e-9)
    def test_rigid_contact_preserves_gap(self):
        r=solve_support([[0.]],[[1.]],[0.],[1.],[],[],[.02]);self.assertTrue(r['passed']);self.assertAlmostEqual(r['rigid_mode_coordinates'][0],.02);self.assertAlmostEqual(r['contact_forces'][0],1.)
    def test_missing_support_does_not_invent_ground(self):
        r=solve_support([[1.]],[[0.]],[0.],[1.],[],[],[.02]);self.assertFalse(r['passed'])
    def test_free_neutral_direction_is_reported(self):
        r=solve_support([[0.]],[[1.,0.]],[0.],[1.,0.],[],[],[.02]);self.assertTrue(r['passed']);self.assertEqual(r['unrestrained_global_rigid_modes'],1);self.assertGreater(r['selected_active_system_nullity'],0)
    def test_force_in_unrestrained_direction_is_rejected(self):
        r=solve_support([[0.]],[[1.,0.]],[0.],[1.,1.],[],[],[.02]);self.assertFalse(r['passed'])
    def test_unbalanced_moment_is_not_force_balance(self):
        r=solve_support([[1.]],[[1.,0.]],[0.],[1.,.1],[],[],[0.]);self.assertFalse(r['passed'])
    def test_mirrored_signed_rigid_map(self):
        a=solve_support([[1.]],[[1.]],[0.],[1.],[],[],[.2]);b=solve_support([[1.]],[[-1.]],[0.],[-1.],[],[],[.2]);np.testing.assert_allclose(a['forces'],b['forces']);self.assertAlmostEqual(a['rigid_mode_coordinates'][0],-b['rigid_mode_coordinates'][0])
    def test_relative_compliance_adds_bodies(self):
        r=solve_support([[.3]],np.empty((1,0)),[.4],[],[],[],[.1]);self.assertAlmostEqual(r['forces'][0],1.)
    def test_nonreciprocal_matrix_refused(self):
        with self.assertRaises(ValueError):solve_support([[1.,1.],[0.,1.]],np.empty((2,0)),[0,0],[],[],[],[0,0])
    def test_negative_energy_mode_refused(self):
        with self.assertRaises(ValueError):solve_support([[-1.]],np.empty((1,0)),[0],[],[],[],[0])
    def test_boolean_matrix_refused(self):
        with self.assertRaises(ValueError):solve_support([[True]],np.empty((1,0)),[0],[],[],[],[0])
    def test_nonfinite_matrix_refused(self):
        for x in (float('nan'),float('inf')):
            with self.assertRaises(ValueError):solve_support([[x]],np.empty((1,0)),[0],[],[],[],[0])
    def test_mismatched_shapes_refused(self):
        with self.assertRaises(ValueError):solve_support([[1.]],[[1,2]],[0],[1],[],[],[0])
    def test_zero_spring_compliance_refused(self):
        with self.assertRaises(ValueError):solve_support([[1.]],np.empty((1,0)),[0],[],[0],[1],[])
    def test_negative_preload_refused(self):
        with self.assertRaises(ValueError):solve_support([[1.]],np.empty((1,0)),[0],[],[1],[-1],[])
    def test_negative_gap_refused(self):
        with self.assertRaises(ValueError):stop(gap=-.1)
    def test_bounded_active_set_count(self):
        with self.assertRaises(ValueError):solve_support(np.eye(13),np.empty((13,0)),np.zeros(13),[],[],[],np.zeros(13))
    def test_never_hardware_release(self):
        r=joint(1);self.assertFalse(r['candidate_go']);self.assertFalse(r['manufacturing_go']);self.assertTrue(r['local_contact_pressure_and_pointwise_nonpenetration_not_solved'])
    def test_independent_single_stop_closed_form_sweep(self):
        for q in np.linspace(-1,1,17):
            for gap in (0.,.2,.7):
                r=stop(float(q),gap);self.assertAlmostEqual(r['contact_forces'][0],max(0,q-gap),places=9)
    def test_known_kkt_random_systems(self):
        rng=np.random.default_rng(117)
        for _ in range(16):
            M=rng.normal(size=(6,6));H=M.T@M+np.eye(6);G=rng.normal(size=(6,2));bc=np.array([.3,.7]);pre=np.array([.8,1.3]);lam=rng.uniform(.2,1.0,6);active=rng.integers(0,2,4).astype(bool);lam[2:][~active]=0
            gaps=rng.uniform(.1,.4,4);r=rng.normal(size=2);q=np.r_[bc*(lam[:2]-pre),gaps-np.where(active,0.,.3)];q0=q+H@lam-G@r
            answer=solve_support(H,G,q0,G.T@lam,bc,pre,gaps)
            self.assertTrue(answer['passed']);np.testing.assert_allclose(answer['forces'],lam,rtol=2e-7,atol=2e-8)
    def test_scale_does_not_add_stiffness_to_rigid_body(self):
        for f in (1e-6,1.,1e6):
            r=solve_support([[0.]],[[1.]],[0.],[f],[],[],[.02]);self.assertTrue(r['passed']);self.assertAlmostEqual(r['rigid_mode_coordinates'][0],.02,places=8);self.assertAlmostEqual(r['forces'][0]/f,1.,places=8)
