from pathlib import Path
import json
import sys
import unittest
import numpy as np
from scipy.optimize import minimize
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spatial_contact import solve_qp, solve_spatial_contact, GapCell
from contact_patch_audit import evaluate, extrema, triangle_coefficients

V = np.array([[0.,0.],[1.,0.],[1.,1.],[0.,1.]])
CONST = np.array([1.,0.,0.,0.,0.,0.])


def cell(c, response=CONST[:,None], name='p', vertices=V):
    return GapCell(name,vertices,np.asarray(c,dtype=float),np.asarray(response,dtype=float))


class SpatialContactTests(unittest.TestCase):
    def test_closed_stop_has_positive_reaction(self):
        r=solve_qp([[1.]],[1.],[[1.]],[0.]); self.assertTrue(r['passed']);self.assertAlmostEqual(r['multipliers'][0],1.)

    def test_separated_stop_carries_zero_force(self):
        r=solve_qp([[1.]],[-1.],[[1.]],[0.]);self.assertTrue(r['passed']);self.assertAlmostEqual(r['u'][0],-1.);self.assertEqual(r['multipliers'][0],0.)

    def test_elastic_free_solution_not_clipped(self):
        r=solve_qp([[2.]],[1.],[[1.]],[3.]);self.assertTrue(r['passed']);self.assertAlmostEqual(r['u'][0],.5)

    def test_rigid_loaded_body_reaches_actual_stop(self):
        r=solve_qp([[0.]],[3.],[[1.]],[.02]);self.assertTrue(r['passed']);self.assertAlmostEqual(r['u'][0],.02);self.assertAlmostEqual(r['multipliers'][0],3.)

    def test_unsupported_load_is_unbounded(self):
        r=solve_qp(np.zeros((2,2)),[0.,1.],[[1.,0.]],[.02]);self.assertFalse(r['passed']);self.assertEqual(r['status'],'unbounded_free_mode');self.assertGreater(r['recession_witness']['load_work'],0.)

    def test_unloaded_neutral_mode_not_artificially_fixed(self):
        r=solve_qp(np.zeros((2,2)),[1.,0.],[[1.,0.]],[.02]);self.assertTrue(r['passed']);self.assertEqual(r['remaining_neutral_modes'],1)

    def test_no_constraints_unbounded_is_json_finite(self):
        r=solve_qp([[0.]],[1.],np.empty((0,1)),[]);self.assertFalse(r['passed']);json.dumps(r,allow_nan=False)

    def test_negative_stiffness_is_rejected(self):
        with self.assertRaises(ValueError):solve_qp([[-1.]],[1.],[[1.]],[0.])

    def test_nonreciprocal_stiffness_is_rejected(self):
        with self.assertRaises(ValueError):solve_qp([[1.,.1],[0.,1.]],[1.,1.],[[1.,0.]],[0.])

    def test_boolean_inputs_are_rejected(self):
        with self.assertRaises(ValueError):solve_qp([[True]],[1.],[[1.]],[0.])

    def test_nonfinite_inputs_are_rejected(self):
        for a in (np.inf,np.nan):
            with self.assertRaises(ValueError):solve_qp([[a]],[1.],[[1.]],[0.])

    def test_shape_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):solve_qp([[1.]],[1.,1.],[[1.]],[0.])

    def test_impossible_zero_row_is_infeasible(self):
        r=solve_qp([[1.]],[0.],[[0.]],[-.1]);self.assertFalse(r['passed'])

    def test_contradictory_constraints_are_infeasible(self):
        r=solve_qp([[1.]],[0.],[[1.],[-1.]],[0.,-1.]);self.assertFalse(r['passed']);self.assertEqual(r['status'],'infeasible')

    def test_explicit_equality_is_enforced(self):
        r=solve_qp(np.eye(2),[2.,-1.],np.zeros((0,2)),[],equality=[[1.,1.]],equality_rhs=[.5]);self.assertTrue(r['passed']);self.assertAlmostEqual(sum(r['u']),.5)

    def test_inconsistent_equalities_rejected(self):
        r=solve_qp([[1.]],[0.],np.zeros((0,1)),[],equality=[[1.],[1.]],equality_rhs=[0.,1.]);self.assertFalse(r['passed'])

    def test_equality_eliminates_all_variables(self):
        r=solve_qp([[2.]],[1.],[[1.]],[3.],equality=[[1.]],equality_rhs=[2.]);self.assertTrue(r['passed']);self.assertAlmostEqual(r['u'][0],2.)

    def test_redundant_equalities_keep_same_result(self):
        r=solve_qp(np.eye(2),[1.,2.],np.zeros((0,2)),[],equality=[[1.,1.],[2.,2.]],equality_rhs=[1.,2.]);self.assertTrue(r['passed']);np.testing.assert_allclose(r['u'],[0.,1.],atol=1e-8)

    def test_duplicate_inequalities_do_not_double_force(self):
        r=solve_qp([[1.]],[1.],[[1.],[1.]],[0.,0.]);self.assertTrue(r['passed']);self.assertAlmostEqual(sum(r['multipliers']),1.)

    def test_constraint_row_scaling_changes_force_not_displacement(self):
        r=solve_qp([[1.]],[2.],[[100.]],[0.]);self.assertTrue(r['passed']);self.assertAlmostEqual(r['multipliers'][0],.02)

    def test_energy_scale_invariance(self):
        for scale in (1e-8,1.,1e8):
            r=solve_qp([[scale]],[2*scale],[[1.]],[.3]);self.assertTrue(r['passed']);self.assertAlmostEqual(r['u'][0],.3);self.assertAlmostEqual(r['multipliers'][0]/scale,1.7)

    def test_iteration_limit_is_not_success(self):
        r=solve_qp([[1.]],[2.],[[1.]],[1.],max_iterations=1);self.assertFalse(r['passed'])

    def test_known_kkt_100_systems(self):
        rng=np.random.default_rng(615)
        for _ in range(100):
            n=5;m=11;X=rng.normal(size=(n,n));K=X.T@X+np.eye(n)*.2
            u=rng.normal(size=n);A=rng.normal(size=(m,n));lam=np.zeros(m);lam[:3]=rng.uniform(.2,2.,3)
            b=A@u+np.r_[np.zeros(3),rng.uniform(.3,2.,m-3)];f=K@u+A.T@lam
            r=solve_qp(K,f,A,b,tolerance=2e-9)
            self.assertTrue(r['passed'],r);np.testing.assert_allclose(r['u'],u,atol=3e-7)

    def test_independent_slsqp_20_systems(self):
        rng=np.random.default_rng(617)
        for _ in range(20):
            X=rng.normal(size=(4,4));K=X.T@X+np.eye(4);f=rng.normal(size=4);A=np.r_[np.eye(4),-np.eye(4),rng.normal(size=(4,4))];b=np.ones(12)*.3
            r=solve_qp(K,f,A,b)
            independent=minimize(lambda u:.5*u@K@u-f@u,np.zeros(4),jac=lambda u:K@u-f,
                                 method='SLSQP',constraints={'type':'ineq','fun':lambda u:b-A@u,'jac':lambda u:-A},options={'ftol':1e-12,'maxiter':1000})
            self.assertTrue(independent.success);self.assertTrue(r['passed']);np.testing.assert_allclose(r['u'],independent.x,atol=2e-6)

    def test_interior_penetration_missed_by_vertices_is_repaired(self):
        c=cell([.08,-.4,-.6,1.,0.,1.])
        self.assertGreater(evaluate(c.offset,V).min(),0.)
        r=solve_spatial_contact([[1.]],[0.],[c],gap_tolerance=1e-9)
        self.assertTrue(r['passed']);self.assertAlmostEqual(r['u'][0],.05);self.assertEqual(len(r['history']),2)
        self.assertEqual(r['history'][0]['violating_cells'],1)
        self.assertTrue(any(x['origin']=='minimum_exchange' and x['reaction']>0 for x in r['local_reactions']))

    def test_edge_stationary_point_enrichment(self):
        c=cell([.04,-.6,.2,1.,0.,0.])
        r=solve_spatial_contact([[1.]],[0.],[c],gap_tolerance=1e-9)
        self.assertTrue(r['passed']);self.assertAlmostEqual(r['u'][0],.05)
        self.assertEqual(r['rejected_intermediate_fields'][0]['negative_cells'][0]['minimum_kind'],'edge_stationary')

    def test_reaction_not_assigned_to_open_points(self):
        c=cell([.08,-.4,-.6,1.,0.,1.]);r=solve_spatial_contact([[1.]],[0.],[c])
        for x in r['local_reactions']:
            if x['gap']>1e-6:self.assertLess(abs(x['reaction']),1e-8)

    def test_no_contact_patch_stiffness_inserted(self):
        c=cell([.02,0.,0.,0.,0.,0.],-CONST[:,None]);r=solve_spatial_contact([[0.]],[1.],[c]);self.assertTrue(r['passed']);self.assertAlmostEqual(r['u'][0],.02)

    def test_moving_minimum_multiple_exchange(self):
        B=np.zeros((6,2));B[0,0]=1.;B[1,1]=1.
        c=cell([.06,-.44,-.4,1.,0.,1.],B)
        r=solve_spatial_contact(np.eye(2),[0.,0.],[c],gap_tolerance=1e-9,max_exchanges=50)
        self.assertTrue(r['passed'],r);self.assertGreater(len(r['history']),2);self.assertGreaterEqual(r['cell_extrema'][0]['minimum'],-1e-9)

    def test_exchange_limit_keeps_bad_field_failed(self):
        r=solve_spatial_contact([[1.]],[0.],[cell([.08,-.4,-.6,1.,0.,1.])],max_exchanges=1)
        self.assertFalse(r['passed']);self.assertEqual(r['status'],'exchange_limit')

    def test_constraint_limit_not_mislabeled(self):
        r=solve_spatial_contact([[1.]],[0.],[cell([.08,-.4,-.6,1.,0.,1.])],max_constraints=4)
        self.assertFalse(r['passed']);self.assertEqual(r['status'],'constraint_limit')

    def test_infeasible_constant_gap_not_fixed_by_clipping(self):
        c=cell([-.1,0.,0.,0.,0.,0.],np.zeros((6,1)))
        r=solve_spatial_contact([[1.]],[0.],[c]);self.assertFalse(r['passed'])

    def test_same_field_split_into_cells_is_equivalent(self):
        offset=np.array([.08,-.4,-.6,1.,0.,1.])
        whole=solve_spatial_contact([[1.]],[0.],[cell(offset)])
        triangles=[V[[0,1,2]],V[[0,2,3]]]
        split=solve_spatial_contact([[1.]],[0.],[cell(offset,name=str(i),vertices=t) for i,t in enumerate(triangles)])
        self.assertTrue(split['passed']);np.testing.assert_allclose(whole['u'],split['u'],atol=1e-8)

    def test_duplicate_cell_ids_rejected(self):
        c=cell([1.,0.,0.,0.,0.,0.])
        with self.assertRaises(ValueError):solve_spatial_contact([[1.]],[0.],[c,c])

    def test_nonconvex_cell_rejected(self):
        c=cell([1.,0.,0.,0.,0.,0.],vertices=np.array([[0.,0.],[1.,0.],[.2,.2],[0.,1.]]))
        with self.assertRaises(ValueError):solve_spatial_contact([[1.]],[0.],[c])

    def test_no_hardware_or_area_pressure_claim(self):
        r=solve_spatial_contact([[1.]],[0.],[cell([1.,0.,0.,0.,0.,0.])]);self.assertTrue(r['passed'])
        for key in ('candidate_go','fixture_fabrication_go','manufacturing_go','finite_area_pressure_reconstruction','full_FE_outside_supplied_displacement_space_verified','continuum_or_mesh_convergence_verified','certified_interval_arithmetic'):self.assertFalse(r[key])

    def test_rigid_support_missing_in_spatial_model_is_failed(self):
        B=np.zeros((6,2));B[0,0]=-1.
        r=solve_spatial_contact(np.zeros((2,2)),[0.,1.],[cell([.02,0.,0.,0.,0.,0.],B)])
        self.assertFalse(r['passed']);self.assertEqual(r['qp']['status'],'unbounded_free_mode')

    def test_shape_function_reproduction_supplied_to_real_auditor(self):
        tri=np.array([[0.,0.],[1.,0.],[0.,1.]]);B=triangle_coefficients(tri,np.eye(6))
        nodal=np.array([0.,1.,2.,.25,.75,.5]);c=cell(np.zeros(6),B,name='P2',vertices=tri)
        p=tri.mean(axis=0)[None,:]
        self.assertAlmostEqual(float(evaluate(c.response,p)[0]@nodal),float(evaluate(B@nodal,p)[0]))

    def test_invalid_options_rejected(self):
        for tol in (True,-1.,0.,np.nan):
            with self.assertRaises(ValueError):solve_spatial_contact([[1.]],[0.],[cell([1.,0.,0.,0.,0.,0.])],gap_tolerance=tol)

    def test_no_input_mutation(self):
        K=np.eye(2);f=np.array([1.,2.]);A=np.eye(2);b=np.zeros(2)
        old=[a.copy() for a in (K,f,A,b)];solve_qp(K,f,A,b)
        for a,v in zip((K,f,A,b),old):np.testing.assert_array_equal(a,v)

    def test_json_roundtrip(self):
        r=solve_spatial_contact([[1.]],[0.],[cell([.08,-.4,-.6,1.,0.,1.])]);self.assertEqual(json.loads(json.dumps(r,allow_nan=False))['passed'],True)

if __name__=='__main__':unittest.main()
