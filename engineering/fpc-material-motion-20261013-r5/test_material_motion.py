import unittest,math,numpy as np
from scipy.spatial.transform import Rotation
import material_motion as m

class MaterialMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r50,cls.r47,cls.r,cls.A,cls.B=m.source_modules();cls.c=cls.r.CANDIDATES[2];cls.L=cls.r.target_length(cls.c)
    def curve(self,s,q):return m.MaterialCurve(self.r,self.c,s,q,self.L)

    def test_arclength_inverse_reproduces_109_original_vertices_with_docking(self):
        for s,q in [(0,0),(40.125,0),(79.75,8.2)]:
            curve=self.curve(s,q);old,_,_,_=self.r47.full_centerline(self.r,self.c,s,q,self.L)
            np.testing.assert_allclose(curve.evaluate(curve.source_vertex_stations())[0],old,rtol=0,atol=1e-8)

    def test_node24_is_not_a_material_identity(self):
        a=self.curve(0,0).source_vertex_stations()[24];b=self.curve(79.75,8.2).source_vertex_stations()[24]
        self.assertGreater(b-a,38)

    def test_constant_material_station_moves_between_leg_and_arc(self):
        early=self.curve(0,0).evaluate([70]);late=self.curve(79.75,8.2).evaluate([70])
        self.assertEqual(int(early[3][0]),2);self.assertEqual(int(late[3][0]),1)
        self.assertGreater(np.linalg.norm(early[0]-late[0]),10)
        self.assertNotEqual(float(early[0][0,2]),float(late[0][0,2]))

    def test_analytical_two_axis_curvature_matches_fixed_station_tangent_derivative(self):
        curve=self.curve(79.75,8.2);sigma=np.array([40.,60.,90.,120.,140.]);h=1e-4
        _,_,k,_,_=curve.evaluate(sigma)
        _,tm,*_=curve.evaluate(sigma-h);_,tp,*_=curve.evaluate(sigma+h)
        np.testing.assert_allclose((tp-tm)/(2*h),k,rtol=0,atol=1e-8)

    def test_bishop_has_zero_spatial_twist_on_smooth_parts(self):
        curve=self.curve(79.75,4.013);sigma=np.array([5.,40.,60.,100.,130.,150.,159.8]);h=.01
        f,(_,t,*_)=m.bishop_frames(curve,sigma)
        fm,_=m.bishop_frames(curve,sigma-h);fp,_=m.bishop_frames(curve,sigma+h)
        rv=Rotation.from_matrix(np.einsum('nji,njk->nik',fm,fp)).as_rotvec()
        rate=np.einsum('nij,nj->ni',fm,rv)/(2*h)
        np.testing.assert_allclose(np.sum(rate*t,axis=1),0,rtol=0,atol=1e-9)
        np.testing.assert_allclose(np.linalg.det(f),1,atol=1e-12)

    def test_two_original_zero_radius_joints_never_get_finite_curvature_or_strain(self):
        curve=self.curve(79.75,8.2);sigma=[curve.bounds[1],curve.bounds[4]]
        sample=m.bishop_kinematics(curve,sigma)
        self.assertTrue(np.all(sample['sharp']));self.assertTrue(np.all(np.isnan(sample['curvatures'])));self.assertTrue(np.all(np.isnan(sample['twist'])))
        self.assertTrue(np.all(np.isnan(sample['frames'])))

    def test_conditional_endpoint_directors_do_not_equal_actual_supplier_clamp(self):
        for s,q in [(0,0),(79.75,0),(79.75,8.2)]:
            f,_=m.bishop_frames(self.curve(s,q),[0,self.L])
            np.testing.assert_allclose(f[:,:,0],[[0,1,0],[0,1,0]],atol=1e-12)

    def test_wrong_pose_or_station_is_rejected(self):
        with self.assertRaises(ValueError):self.curve(40,1)
        with self.assertRaises(ValueError):self.curve(80,0)
        for sigma in [-1,self.L+1,float('nan')]:
            with self.assertRaises(ValueError):self.curve(0,0).evaluate([sigma])

    def test_fixed_station_bishop_preserves_smooth_leg_to_arc_frame(self):
        curve=self.curve(79.75,8.2)
        for join in (curve.bounds[2],curve.bounds[3]):
            f,_=m.bishop_frames(curve,[join-1e-7,join+1e-7])
            self.assertLess(np.linalg.norm(f[1]-f[0]),1e-7)

    def test_unfixed_proxy_endpoint_frame_rotation_is_retained_separately(self):
        curves=[self.curve(s,q) for s,q in [(0,0),(79.75,8.2)]];width=[]
        for curve in curves:
            pts,_,_,_=self.r47.full_centerline(self.r,self.c,curve.s,curve.q,self.L)
            f,_,_,_=m.associated_frames(curve,[self.L],curve.source_vertex_stations(),m.faithful_R50_frames(pts));width.append(f[0,:,0])
        angle=math.degrees(math.acos(float(np.clip(np.dot(width[0],width[1]),-1,1))))
        self.assertGreater(angle,70)

if __name__=='__main__':unittest.main(verbosity=2)
