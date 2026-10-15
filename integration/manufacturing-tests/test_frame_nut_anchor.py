from pathlib import Path
import math,sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
import frame_nut_anchor as a
import verify_frame_nut_anchor as r
v=a.v


class FrameNutAnchorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame=v.box((-37.,45.,1.2),(37.,75.,4.2))
        for x,y in a.CENTERS:cls.frame=v.single(cls.frame.cut(a.cylinder(.5,1.1,3.6,x,y)).clean())
        roles=('PAWL','SHOULDER_PIN_NOMINAL','TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL','ROOF','ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL','GUIDE_REFERENCE','ROOT_OUTER','ROOT_INNER','OLD_COVER')
        sample=v.box((0.,0.,0.),(1.,1.,1.))
        cls.base={s+'_'+k:sample for s in 'LR' for k in roles};cls.base['A_BACK_PANEL']=sample
        cls.screws={f'FRAME_{i}_M1x3_NOMINAL':v.single(a.cylinder(.5,.55,3.55,x,y).fuse(a.cylinder(.9,.1,.55,x,y)).clean()) for i,(x,y) in enumerate(a.CENTERS)}
        cls.parts,cls.material=a.build(cls.base,cls.frame,cls.screws)

    def test_complete_template_set_and_four_new_physical_parts(self):
        self.assertEqual(len(self.parts),34);self.assertEqual(self.material['new_physical_parts'],4)

    def test_original25_template_material_unchanged(self):
        for k,b in self.base.items():self.assertTrue(b.isSame(self.parts[k]))

    def test_all_original_frame_screws_unchanged(self):
        for k,b in self.screws.items():self.assertTrue(b.isSame(self.parts[k]))

    def test_frame_is_one_solid_and_only_loses_material(self):
        self.assertEqual(len(v.single(self.parts['A_FRAME']).Solids()),1)
        self.assertLessEqual(v.vol(self.parts['A_FRAME'].cut(self.frame)),1e-7)

    def test_frame_material_balance(self):
        self.assertAlmostEqual(v.vol(self.frame)-self.material['frame_removed_mm3'],v.vol(self.parts['A_FRAME']),places=6)

    def test_hex_volume_matches_analytic_area(self):
        body=a.hex_prism(2.5,0.,.8)
        self.assertAlmostEqual(v.vol(body),math.sqrt(3)/2*2.5**2*.8,places=8)

    def test_independent_hex_reconstruction_matches(self):
        self.assertLessEqual(max(v.equal(a.hex_prism(2.5,2.55,3.35,34.8,50.),r.hexagon(2.5,2.55,3.35,34.8,50.))),1e-7)

    def test_finite_dimensions_reject_boolean_nan_and_infinity(self):
        for val in (True,float('nan'),float('inf'),'2.5'):
            with self.assertRaises(ValueError):a.hex_prism(val,0.,1.)

    def test_ordered_positive_dimensions_required(self):
        for args in ((0.,0.,1.),(2.5,1.,1.),(-1.,0.,1.),(2.5,1.,0.)):
            with self.assertRaises(ValueError):a.hex_prism(*args)

    def test_invalid_cylinders_rejected(self):
        for args in ((0.,0.,1.,0.,0.),(.5,1.,0.,0.,0.),(True,0.,1.,0.,0.)):
            with self.assertRaises(ValueError):a.cylinder(*args)

    def test_nut_installed_positions_clear(self):
        for i in range(4):self.assertLessEqual(v.common(self.parts[f'FRAME_{i}_NUT_SHNS_M1_NOMINAL'],self.parts['A_FRAME']),1e-7)

    def test_old_frame_rejects_unpocketed_nut(self):
        for i in range(4):self.assertGreater(v.common(self.parts[f'FRAME_{i}_NUT_SHNS_M1_NOMINAL'],self.frame),1e-7)

    def test_shoulders_block_downward_nut(self):
        for i in range(4):self.assertGreater(v.common(self.parts[f'FRAME_{i}_NUT_SHNS_M1_NOMINAL'].translate((0,0,-.01)),self.parts['A_FRAME']),1e-7)

    def test_nut_not_falsely_claimed_captive_when_unscrewed(self):
        for i in range(4):self.assertLessEqual(v.common(self.parts[f'FRAME_{i}_NUT_SHNS_M1_NOMINAL'].translate((0,0,2.)),self.parts['A_FRAME']),1e-7)

    def test_both_rotation_directions_hit_pocket(self):
        for i,(x,y) in enumerate(a.CENTERS):
            for angle in (-5.,5.):self.assertGreater(v.common(self.parts[f'FRAME_{i}_NUT_SHNS_M1_NOMINAL'].rotate((x,y,0),(x,y,1),angle),self.parts['A_FRAME']),1e-7)

    def test_top_prismatic_insertion_not_just_endpoint(self):
        for x,y in a.CENTERS:self.assertLessEqual(v.common(a.hex_prism(2.5,2.55,11.35,x,y),self.parts['A_FRAME']),1e-7)

    def test_nut_inside_existing_frame_material(self):
        for i in range(4):self.assertLessEqual(v.vol(self.parts[f'FRAME_{i}_NUT_SHNS_M1_NOMINAL'].cut(self.frame)),1e-7)

    def test_thread_omission_is_not_native_axial_retention(self):
        for i in range(4):self.assertLessEqual(v.common(self.screws[f'FRAME_{i}_M1x3_NOMINAL'].translate((0,0,-.1)),self.parts[f'FRAME_{i}_NUT_SHNS_M1_NOMINAL']),1e-7)

    def test_catalogue_overlap_and_protrusion(self):
        d=a.dimensions();self.assertAlmostEqual(d['nominal_axial_overlap_mm'],.8);self.assertAlmostEqual(d['nominal_tip_protrusion_mm'],.2)

    def test_nominal_height_over_pitch_not_complete_thread_count(self):
        d=a.dimensions();self.assertAlmostEqual(d['nominal_nut_height_over_pitch'],3.2);self.assertIsNone(d['actual_complete_engaged_threads'])

    def test_no_max_torque_relabel_as_installation_torque(self):
        d=a.dimensions();self.assertIsNone(d['screw_tightening_torque_Nm']);self.assertEqual(d['catalogue_max_torque_NOT_installation_setpoint_Nm'],.02)

    def test_missing_or_extra_inputs_rejected(self):
        for b in ({},dict(self.base,EXTRA=self.frame)):
            with self.assertRaises(ValueError):a.build(b,self.frame,self.screws)
        with self.assertRaises(ValueError):a.build(self.base,self.frame,{})

    def test_mismatched_screw_material_rejected(self):
        wrong=dict(self.screws);name='FRAME_0_M1x3_NOMINAL';wrong[name]=wrong[name].translate((0,0,.01))
        with self.assertRaises(ValueError):a.build(self.base,self.frame,wrong)

    def test_missing_frame_mount_location_rejected(self):
        with self.assertRaises(ValueError):a.build(self.base,v.box((0.,0.,0.),(1.,1.,1.)),self.screws)


class CompleteFrameAdmissionTests(unittest.TestCase):
    def test_closed_front_skin_rejects_original_top_drop(self):
        front=v.box((-37.,45.,7.35),(37.,75.,8.))
        for x,y in a.CENTERS:
            self.assertGreater(v.common(a.hex_prism(2.5,2.55,11.35,x,y),front),1e-7)
            self.assertGreater(v.common(a.nominal_nut(x,y).translate((0,0,4.8)),front),1e-7)

    def test_dogleg_avoids_front_skin_and_connected_boss(self):
        for x,y in a.CENTERS:
            obstacle=v.box((-37.,45.,7.35),(37.,75.,8.)).fuse(a.cylinder(1.8,1.2,4.2,x,y))
            obstacle=obstacle.cut(a.pocket(x,y)).cut(a.cylinder(.55,1.1,4.4,x,y)).clean()
            for cage in r.nut_route_cages(x,y):self.assertLessEqual(v.common(cage,obstacle),1e-7)
