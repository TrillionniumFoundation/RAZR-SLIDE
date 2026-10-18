from pathlib import Path
import sys,unittest,math
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import surface_load_functional as s

class SurfaceLoadTests(unittest.TestCase):
    def setUp(self):
        self.t=np.array([[0.,0.],[1.,0.],[0.,1.]])
        self.d=s.fit_density([self.t],[1/3,1/3])
    def test_unit_total(self):self.assertAlmostEqual(s.integrate_face(self.t,self.t,self.d)['resultant'],1.)
    def test_affine_first_moment(self):
        r=s.integrate_face(self.t,self.t,self.d);np.testing.assert_allclose(r['first_moment'],[1/3,1/3],atol=1e-14)
    def test_uniform_quadratic_vertex_loads_zero(self):
        r=s.integrate_face(self.t,self.t,self.d);np.testing.assert_allclose(r['work_coefficients'][:3],0.,atol=1e-14)
    def test_uniform_quadratic_edge_loads(self):
        r=s.integrate_face(self.t,self.t,self.d);np.testing.assert_allclose(r['work_coefficients'][3:6],1/3,atol=1e-14)
    def test_uniform_bubble_work_is_nonzero(self):
        r=s.integrate_face(self.t,self.t,self.d);self.assertAlmostEqual(r['work_coefficients'][6],.45)
    def test_generalized_bubble_not_extra_resultant(self):
        r=s.integrate_face(self.t,self.t,self.d);self.assertAlmostEqual(sum(r['work_coefficients'][:6]),1.);self.assertAlmostEqual(sum(r['work_coefficients']),1.45)
    def test_old_node_evaluation_cannot_see_bubble(self):
        p=np.vstack((self.t,(self.t[0]+self.t[1])/2,(self.t[0]+self.t[2])/2,(self.t[1]+self.t[2])/2))
        self.assertEqual(float(abs(s.shape_values(self.t,p)[:,6]).max()),0.)
    def test_virtual_work_direct_equals_coefficients(self):
        rng=np.random.default_rng(94);u=rng.normal(size=7);x,w=s.polygon_quadrature(self.t,order=6)
        direct=np.dot(w*self.d.values(x),s.shape_values(self.t,x)@u)
        self.assertAlmostEqual(direct,s.integrate_face(self.t,self.t,self.d)['work_coefficients']@u,places=13)
    def test_parent_orientation_reversal(self):
        rev=self.t[[0,2,1]];r=s.integrate_face(rev,self.t,self.d);self.assertAlmostEqual(r['work_coefficients'][6],.45)
    def test_translation_and_scale_invariant_normalized_work(self):
        t=self.t*5+np.array([300.,-200.]);d=s.fit_density([t],t.mean(axis=0))
        np.testing.assert_allclose(s.integrate_face(t,t,d)['work_coefficients'],s.integrate_face(self.t,self.t,self.d)['work_coefficients'],atol=1e-12)
    def test_clipping_halftriangle_area(self):
        p=s.clip_triangle(self.t,[[1.,0.]],[.5]);x,w=s.polygon_quadrature(p);self.assertAlmostEqual(w.sum(),.375)
    def test_empty_clip_returns_empty(self):self.assertEqual(s.clip_triangle(self.t,[[1.,0.]],[-1.]).shape,(0,2))
    def test_no_clip_preserves_triangle(self):np.testing.assert_array_equal(s.clip_triangle(self.t,np.empty((0,2)),[]),self.t)
    def test_touching_line_has_no_area(self):self.assertEqual(s.clip_triangle(self.t,[[1.,0.]],[0.]).shape,(0,2))
    def test_multiple_clip_planes(self):
        p=s.clip_triangle(self.t,[[1.,0.],[-1.,0.],[0.,1.]],[.6,-.2,.2]);self.assertAlmostEqual(s.polygon_quadrature(p)[1].sum(),.08)
    def test_does_not_mutate_inputs(self):
        t=self.t.copy();s.clip_triangle(t,[[1.,0.]],[.4]);s.integrate_face(t,t,self.d);np.testing.assert_array_equal(t,self.t)
    def test_degenerate_parent_rejected(self):
        with self.assertRaises(ValueError):s.triangle([[0,0],[1,0],[2,0]])
    def test_boolean_triangle_rejected(self):
        with self.assertRaises(ValueError):s.triangle(self.t.astype(bool))
    def test_nonfinite_rejected(self):
        t=self.t.copy();t[0,0]=np.nan
        with self.assertRaises(ValueError):s.triangle(t)
    def test_bad_halfplane_rejected(self):
        with self.assertRaises(ValueError):s.clip_triangle(self.t,[[0,0]],[1])
    def test_tensile_fit_rejected(self):
        with self.assertRaises(ValueError):s.fit_density([self.t],[.9,.9])
    def test_empty_fit_rejected(self):
        with self.assertRaises(ValueError):s.fit_density([],[0,0])
    def test_domain_outside_triangle_rejected(self):
        with self.assertRaises(ValueError):s.integrate_face(self.t,self.t+2,self.d)
    def test_clockwise_polygon_rejected(self):
        with self.assertRaises(ValueError):s.polygon_quadrature(self.t[::-1])
    def test_invalid_quadrature_rejected(self):
        for order in [True,2,13,3.2]:
            with self.assertRaises(ValueError):s.polygon_quadrature(self.t,order=order)
    def test_inscribed_circle_area_is_not_true_circle(self):
        n=64;norm,b=s.circle_halfplanes([0,0],1.,n);t=np.array([[-4.,-4.],[4.,-4.],[0.,6.]])
        p=s.clip_triangle(t,norm,b);area=s.polygon_quadrature(p)[1].sum();self.assertAlmostEqual(area,n*.5*math.sin(2*math.pi/n),places=12);self.assertLess(area,math.pi)
    def test_invalid_circle_parameters_rejected(self):
        for radius,n in [(True,8),(0,8),(1,True),(1,7),(1,4097)]:
            with self.assertRaises(ValueError):s.circle_halfplanes([0,0],radius,n)
    def test_affine_density_over_polygon_positive(self):
        d=s.fit_density([self.t],[.35,.30]);r=s.integrate_face(self.t,self.t,d)
        self.assertGreater(d.minimum,0.);np.testing.assert_allclose(r['first_moment'],[.35,.30],atol=1e-14)
    def test_fan_subdivision_invariance(self):
        center=self.t.mean(axis=0);parts=[np.stack((self.t[i],self.t[(i+1)%3],center)) for i in range(3)]
        d=s.fit_density(parts,[1/3,1/3]);got=sum(s.integrate_face(self.t,p,d)['work_coefficients'] for p in parts)
        np.testing.assert_allclose(got,s.integrate_face(self.t,self.t,self.d)['work_coefficients'],atol=1e-14)
    def test_degree4_integration(self):
        x,w=s.polygon_quadrature(self.t);self.assertAlmostEqual(np.dot(w,x[:,0]**2*x[:,1]**2),1/180,places=14)
    def test_explicit_no_hardware_claim(self):self.assertFalse(s.integrate_face(self.t,self.t,self.d)['real_material_preload_or_pressure_assigned'])
