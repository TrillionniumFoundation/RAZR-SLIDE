import sys,math,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'integration'))
from admission_cells import vector3,Stage,AssemblyState,translation_cells
import cadquery as cq
import cam_contact_native as n

class AssemblyStateTests(unittest.TestCase):
    def setUp(self):self.state=AssemblyState({'fixture':(0,0,0)})
    def test_introduced_part_checks_every_present_part(self):
        s=Stage('in','part',(2,0,0),(0,0,0));self.assertEqual(self.state.fixed_names(s),('fixture',));self.state.finish(s,True,['fixture']);self.assertEqual(self.state.poses['part'],(0.,0.,0.))
    def test_omitting_fixture_rejected(self):
        with self.assertRaises(ValueError):self.state.finish(Stage('in','part',(2,0,0),(0,0,0)),True,[])
    def test_duplicate_fixed_obstacle_rejected(self):
        with self.assertRaises(ValueError):self.state.finish(Stage('in','part',(2,0,0),(0,0,0)),True,['fixture','fixture'])
    def test_teleport_between_stages_rejected(self):
        self.state.poses['part']=(0.,0.,0.)
        with self.assertRaises(ValueError):self.state.fixed_names(Stage('next','part',(1,0,0),(2,0,0)))
    def test_failed_part_not_added(self):
        s=Stage('fail','part',(2,0,0),(0,0,0));self.state.finish(s,False,['fixture']);self.assertNotIn('part',self.state.poses);self.assertEqual(self.state.blocked,'fail')
    def test_failure_blocks_downstream(self):
        self.state.finish(Stage('fail','p',(2,0,0),(0,0,0)),False,['fixture'])
        with self.assertRaises(ValueError):self.state.fixed_names(Stage('next','q',(2,0,0),(0,0,0)))
    def test_moving_existing_body_not_counted_as_own_obstacle(self):
        self.state.poses['part']=(0.,0.,0.);s=Stage('shift','part',(0,0,0),(1,0,0));self.assertEqual(self.state.fixed_names(s),('fixture',));self.state.finish(s,True,['fixture'])
    def test_duplicate_stage_rejected(self):
        s=Stage('one','p',(2,0,0),(0,0,0));self.state.finish(s,True,['fixture'])
        with self.assertRaises(ValueError):self.state.fixed_names(Stage('one','q',(2,0,0),(0,0,0)))
    def test_nonboolean_pass_rejected(self):
        with self.assertRaises(ValueError):self.state.finish(Stage('one','p',(2,0,0),(0,0,0)),1,['fixture'])
    def test_invalid_stage_or_vector_rejected(self):
        for v in [(0,0,math.nan),(0,math.inf,0),(False,0,0),(0,0),(0,0,'0')]:
            with self.subTest(v=v),self.assertRaises(ValueError):vector3(v)
        with self.assertRaises(ValueError):Stage('','p',(0,0,0),(1,0,0))
        with self.assertRaises(ValueError):Stage('x','p',(0,0,0),(0,0,0))

class TranslationCellTests(unittest.TestCase):
    def test_box_complete_cells_overlap_not_volume_sum(self):
        shape=cq.Solid.makeBox(1,1,1);cells,report=translation_cells(shape,(2,0,0));self.assertEqual(len(cells),3);self.assertAlmostEqual(sum(x.Volume() for _,x in cells),4.)
        self.assertFalse(report['global_boolean_fusion_used']);self.assertTrue(report['cell_volume_sum_is_not_swept_volume'])
    def test_thin_midmotion_collision_not_missed(self):
        body=cq.Solid.makeBox(.1,1,1);obstacle=cq.Solid.makeBox(.01,1,1,cq.Vector(.5,0,0));cells,_=translation_cells(body,(1,0,0))
        self.assertEqual(n.common(body,obstacle),0.);self.assertEqual(n.common(body.translate((1,0,0)),obstacle),0.);self.assertTrue(any(n.common(c,obstacle)>1e-7 for _,c in cells))
    def test_far_obstacle_no_cell_collision(self):
        cells,_=translation_cells(cq.Solid.makeBox(1,1,1),(2,0,0));far=cq.Solid.makeBox(1,1,1,cq.Vector(0,3,0));self.assertTrue(all(n.common(x,far)==0 for _,x in cells))
    def test_unsupported_surface_rejected(self):
        with self.assertRaises(ValueError):translation_cells(cq.Solid.makeSphere(1),(1,0,0))
    def test_multi_solid_not_silently_selected(self):
        shape=cq.Compound.makeCompound([cq.Solid.makeBox(1,1,1),cq.Solid.makeBox(1,1,1,cq.Vector(3,0,0))])
        with self.assertRaises(ValueError):translation_cells(shape,(1,0,0))
    def test_zero_or_bad_move_rejected(self):
        for v in [(0,0,0),(math.nan,0,0),(True,0,0)]:
            with self.subTest(v=v),self.assertRaises(ValueError):translation_cells(cq.Solid.makeBox(1,1,1),v)
    def test_cylinder_carriers_explicitly_conservative(self):
        cells,report=translation_cells(cq.Solid.makeCylinder(.1,.5),(1,0,0));self.assertTrue(any(d.get('whole_cylinder_is_conservative') for d in report['cells']));self.assertTrue(all(x.isValid() and x.Volume()>0 for _,x in cells))
    def test_reverse_translation_checks_same_midpoint(self):
        shape=cq.Solid.makeBox(.1,1,1);obstacle=cq.Solid.makeBox(.01,1,1,cq.Vector(.5,0,0))
        cells,_=translation_cells(shape.translate((1,0,0)),(-1,0,0));self.assertTrue(any(n.common(x,obstacle)>1e-7 for _,x in cells))
