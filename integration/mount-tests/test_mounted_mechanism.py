from pathlib import Path
import hashlib,json,math,sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
import mounted_mechanism as m
import verify_mounted_mechanism as v

class MountedMechanismTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.refs,cls.parts,cls.frame,cls.panel,cls.screws,cls.details=m.build()

    def test_source_parts_all_preserved_except_added_inner_ears(self):
        self.assertEqual(len(self.parts),46)
        for k,b in self.refs.items():
            if not k.endswith('_ROOT_INNER'):self.assertEqual(v.equal(b,self.parts[k]),[0.,0.])

    def test_source_root_material_not_trimmed(self):
        for s in 'LR':
            old,new=self.refs[s+'_ROOT_INNER'],self.parts[s+'_ROOT_INNER']
            self.assertEqual(m.volume(old.cut(new)),0.)
            self.assertGreater(m.volume(new.cut(old)),0.)

    def test_ear_material_is_connected_to_parent(self):
        self.assertEqual(len(self.details['ears']),4)
        self.assertTrue(all(e['native_joint_overlap_mm3']>1e-7 for e in self.details['ears']))
        for s in 'LR':self.assertEqual(len(m.n.whole_material(self.parts[s+'_ROOT_INNER'])[0]),1)

    def test_exact_eight_nominal_screws(self):
        self.assertEqual(len(self.screws),8)
        original=m.parent_part('L','SPRING_SCREW_0_M1x3_NOMINAL')
        for b in self.screws.values():
            self.assertAlmostEqual(b.Volume(),original.Volume(),places=7)
            self.assertAlmostEqual(b.BoundingBox().zlen,3.45,places=7)
            self.assertAlmostEqual(b.BoundingBox().xmin+b.BoundingBox().xlen/2,b.Center().x,places=7)

    def test_frame_panel_are_each_single_valid_solid(self):
        for b in (self.frame,self.panel):self.assertEqual(len(m.n.whole_material(b)[0]),1)

    def test_frame_pad_recess_fixes_actual_overlap(self):
        self.assertEqual(m.n.common(self.frame,self.panel),0.)

    def test_no_recess_original_frame_rejects_new_panel(self):
        old=self.details['original_A_shell']
        plain=old.intersect(m.block(-40,40,-1,96,0,.65))
        frame=m.one(old.cut(plain).clean())
        self.assertGreater(m.n.common(frame,self.panel),.7)

    def test_all_actual_parts_within_A_study_outer(self):
        outer=self.details['original_A_outer']
        for b in [self.frame,self.panel,*self.parts.values(),*self.screws.values()]:
            self.assertEqual(m.volume(b.cut(outer)),0.)

    def test_component_depth_not_increased(self):
        for s in 'LR':
            body=m.cq.Compound.makeCompound([b for k,b in self.parts.items() if k.startswith(s+'_')])
            self.assertAlmostEqual(body.BoundingBox().zlen,6.6,places=7)

    def test_mounts_inside_explicit_planform(self):
        self.assertEqual(len(self.details['mounts_xy']),8)
        for x,y in self.details['mounts_xy'].values():
            self.assertLess(abs(x)+1.8,73.99/2)
            self.assertGreater(y-1.8,.65)
            self.assertLess(y+1.8,79.55)

    def test_frame_bosses_have_actual_material_connections(self):
        self.assertEqual(len(self.details['frame_boss_joint_overlaps_mm3']),4)
        self.assertTrue(all(x>1e-7 for x in self.details['frame_boss_joint_overlaps_mm3']))

    def test_screws_recessed_and_blind_tip_retained(self):
        for b in self.screws.values():
            self.assertAlmostEqual(b.BoundingBox().zmin,.1,places=7)
            self.assertAlmostEqual(b.BoundingBox().zmax,3.55,places=7)
        self.assertTrue(all(abs(x['blind_tip_clearance_mm']-.05)<1e-9 for x in self.details['ears']))

    def test_original_whole_component_shift_is_rigid(self):
        for s in 'LR':
            b=m.parent_part(s,'KEY');placed=m.mounted(b,s)
            self.assertAlmostEqual(b.Volume(),placed.Volume(),places=7)
            self.assertEqual(v.equal(placed,m.placement(b,s).translate((0,6.,0))),[0.,0.])

    def test_direct_coupling_origin_is_compatible(self):
        self.assertTrue(m.direct_coupling_residual(0,0,0)['direct_rigid_connection_compatible'])

    def test_direct_coupling_12mm_positive_control(self):
        self.assertTrue(m.direct_coupling_residual(12,0,12)['direct_rigid_connection_compatible'])

    def test_full_slide_requires_additional_67p75mm(self):
        x=m.direct_coupling_residual(79.75,0,12)
        self.assertFalse(x['direct_rigid_connection_compatible']);self.assertEqual(x['relative_Y_drift_mm'],67.75)

    def test_normal_seating_is_not_silently_KEY_motion(self):
        x=m.direct_coupling_residual(79.75,8.2,12)
        self.assertFalse(x['direct_rigid_connection_compatible']);self.assertEqual(x['relative_Z_drift_mm'],-8.2)

    def test_invalid_travel_and_phase_rejected(self):
        for args in [(0,0,13),(80,0,0),(0,.1,0),(79.75,8.3,12),(float('nan'),0,0),(True,0,0)]:
            with self.assertRaises(ValueError):m.direct_coupling_residual(*args)

    def test_invalid_sides_and_ear_ids_rejected(self):
        for s in ('X',None):
            with self.assertRaises(ValueError):m.parent_part(s,'KEY')
        for i in (True,-1,2,'0'):
            with self.assertRaises(ValueError):m.ear_point('L',i)

    def test_actual_finished_inputs_not_replaced_by_study(self):
        p=ROOT/'integration/assembly_inputs.json'
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),'7b7ebf0f48556f2feca175a35b882a9a48337de2bb5f54b1ba7a740f85e8ce6b')
        self.assertTrue(all(x is None for x in json.loads(p.read_text())['finished_geometry'].values()))
