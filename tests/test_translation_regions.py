from pathlib import Path
import sys,unittest,math
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'integration'))
import translation_regions as r

class TranslationRegionsTests(unittest.TestCase):
    def test_boxes_cover_whole_straight_travel(self):
        a=r.cq.Solid.makeBox(1,1,1);parts,m=r.regions(a,(3,0,0))
        self.assertTrue(m['complete_translation_not_pose_samples'])
        expected=r.cq.Solid.makeBox(4,1,1)
        self.assertEqual(r.whole_material(r.subtract_regions(expected,parts),empty=True)[1],0.)
    def test_axial_hole_is_not_filled(self):
        a=r.cq.Solid.makeCylinder(2,1).cut(r.cq.Solid.makeCylinder(1,1)).clean();parts,m=r.regions(a,(0,0,4))
        hole=r.cq.Solid.makeCylinder(.9,5)
        self.assertTrue(r.checks(parts,hole)['all_regions_clear']);self.assertTrue(m['axial_cylinder_faces_without_advancing_normal'])
    def test_reverse_boxes_cover_same_material(self):
        a=r.cq.Solid.makeBox(1,2,3);f,_=r.regions(a,(5,0,0));b,_=r.regions(a.translate((5,0,0)),(-5,0,0))
        for p in f:self.assertEqual(r.whole_material(r.subtract_regions(p,b),empty=True)[1],0.)
    def test_actual_obstacle_inside_sweep_is_detected(self):
        parts,_=r.regions(r.cq.Solid.makeBox(1,1,1),(3,0,0));hit=r.cq.Solid.makeBox(.1,.1,.1,r.cq.Vector(2,.4,.4))
        self.assertFalse(r.checks(parts,hit)['all_regions_clear'])
    def test_unsupported_surface_rejected(self):
        with self.assertRaises(ValueError):r.regions(r.cq.Solid.makeSphere(1),(1,0,0))
    def test_invalid_motion_rejected(self):
        for vector in [(0,0,0),(math.inf,0,0),(math.nan,1,0)]:
            with self.subTest(vector=vector),self.assertRaises(ValueError):r.regions(r.cq.Solid.makeBox(1,1,1),vector)
