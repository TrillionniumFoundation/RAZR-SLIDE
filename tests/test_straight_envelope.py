import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'integration'))
import straight_envelope as e
c=e.cq

class StraightEnvelopeTests(unittest.TestCase):
    def test_planar_box(self):
        s,r=e.envelope(c.Solid.makeBox(1,1,1),(2,0,0))
        self.assertAlmostEqual(s.Volume(),3.,places=7); self.assertFalse(r['conservative_superset_not_exact_for_partial_or_inner_cylinders'])
    def test_axial_cylinder_both_directions(self):
        for sign in (-1,1):
            s,r=e.envelope(c.Solid.makeCylinder(1,2),(0,0,sign*3))
            self.assertAlmostEqual(s.Volume(),5*math.pi,places=7)
    def test_orthogonal_cylinder_capsule_volume(self):
        s,r=e.envelope(c.Solid.makeCylinder(1,2),(3,0,0))
        self.assertAlmostEqual(s.Volume(),(math.pi+6)*2,places=7)
        self.assertTrue(r['conservative_superset_not_exact_for_partial_or_inner_cylinders'])
    def test_reverse_full_capsule_is_same(self):
        a=c.Solid.makeCylinder(.5,1.3);f,_=e.envelope(a,(2,0,0));b,_=e.envelope(a.translate((2,0,0)),(-2,0,0))
        self.assertLess(e.whole_material(f.cut(b),empty=True)[1],1e-7);self.assertLess(e.whole_material(b.cut(f),empty=True)[1],1e-7)
    def test_planar_hole_kept(self):
        a=c.Solid.makeBox(3,3,1).cut(c.Solid.makeBox(1,1,2,c.Vector(1,1,-.5))).clean()
        s,_=e.envelope(a,(0,0,2));self.assertAlmostEqual(s.Volume(),24.,places=7)
    def test_sphere_not_silently_boxed(self):
        with self.assertRaises(ValueError):e.envelope(c.Solid.makeSphere(1),(1,0,0))
    def test_oblique_cylinder_motion_rejected(self):
        with self.assertRaises(ValueError):e.envelope(c.Solid.makeCylinder(1,2),(1,0,1))
    def test_degenerate_translation_rejected(self):
        for v in [(0,0,0),(math.nan,0,0),(math.inf,0,0)]:
            with self.subTest(v=v),self.assertRaises(ValueError):e.envelope(c.Solid.makeBox(1,1,1),v)
    def test_free_topology_rejected(self):
        a=c.Compound.makeCompound([c.Solid.makeBox(1,1,1),c.Edge.makeLine((4,0,0),(5,0,0))])
        with self.assertRaises(ValueError):e.envelope(a,(1,0,0))
    def test_separate_solids_not_filtered(self):
        a=c.Compound.makeCompound([c.Solid.makeBox(1,1,1),c.Solid.makeBox(1,1,1,c.Vector(5,0,0))])
        with self.assertRaises(ValueError):e.envelope(a,(1,0,0))
