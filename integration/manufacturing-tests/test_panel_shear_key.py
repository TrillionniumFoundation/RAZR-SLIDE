from pathlib import Path
import math
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
import panel_shear_key as k
import verify_panel_shear_key as r


class PanelShearKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=k.box((-36.995,0,0),(36.995,94.25,.65))
        cls.panel,cls.material=k.add_keys(cls.old)
        cls.base={s+'_'+role:k.box((0,0,0),(1,1,1)) for s in 'LR' for role in k.ROLES}
        cls.base['A_BACK_PANEL']=cls.old

    def test_original_candidate_key_dimensions(self):
        b=k.key_material('R').BoundingBox()
        self.assertAlmostEqual(b.xlen,.625);self.assertAlmostEqual(b.ylen,7.5);self.assertAlmostEqual(b.zlen,1.5)

    def test_mirrored_complete_material(self):
        self.assertEqual(r.v.equal(k.key_material('L').mirror('YZ'),k.key_material('R')),[0.,0.])

    def test_invalid_side_rejected(self):
        for side in ('front','',None):
            with self.assertRaises(ValueError):k.key_material(side)

    def test_single_connected_new_panel(self):
        self.assertEqual(len(k.single(self.panel).Solids()),1)

    def test_original_panel_never_removed(self):
        self.assertEqual(k.vol(self.old.cut(self.panel)),0.)

    def test_new_volume_and_both_join_areas(self):
        self.assertAlmostEqual(self.material['added_mm3'],12.65625)
        self.assertTrue(all(abs(x['original_panel_overlap_mm3']-.703125)<1e-8 for x in self.material['joins']))

    def test_disconnected_panel_rejected(self):
        with self.assertRaises(ValueError):k.add_keys(k.box((-5,0,0),(5,90,.65)))

    def test_wrong_panel_embed_not_tolerated(self):
        with self.assertRaises(ValueError):k.add_keys(k.box((-36.995,0,0),(36.995,94.25,.60)))

    def test_exactly_one_identity_changes(self):
        new,_=k.build(self.base)
        self.assertEqual(len(new),25)
        self.assertTrue(all(new[n].isSame(self.base[n]) for n in self.base if n!='A_BACK_PANEL'))

    def test_missing_or_extra_part_rejected(self):
        for case in (dict(self.base,EXTRA=self.old),{n:b for n,b in self.base.items() if n!='L_OLD_COVER'}):
            with self.assertRaises(ValueError):k.build(case)

    def test_all_added_material_inside_existing_outer(self):
        outer=k.box((-36.995,0,0),(36.995,94.25,8.))
        self.assertEqual(k.vol(self.panel.cut(outer)),0.)

    def test_nominal_frame_contact_before_overtravel(self):
        framewall=k.box((36.345,0,.65),(36.995,94.25,8.))
        self.assertAlmostEqual(k.key_material('R').distance(framewall),.02)
        self.assertEqual(k.common(k.key_material('R').translate((.02,0,0)),framewall),0.)
        self.assertGreater(k.common(k.key_material('R').translate((.03,0,0)),framewall),1e-7)

    def test_composed_outboard_coordinate_is_not_old_limit(self):
        values=k.original_orientation_offsets(.02,.02)
        self.assertAlmostEqual(values['R']['body_outboard_global_X_mm'],.09)
        self.assertAlmostEqual(k.original_orientation_offsets(-.02,.02)['L']['body_outboard_global_X_mm'],-.09)

    def test_inboard_coordinate_accounts_for_panel_shift(self):
        self.assertAlmostEqual(k.original_orientation_offsets(-.02,0)['R']['body_inboard_global_X_mm'],-.07)

    def test_numeric_input_not_silently_clamped(self):
        for x in (True,float('nan'),float('inf'),'.01'):
            with self.assertRaises(ValueError):k.original_orientation_offsets(x,0.)
        for x in (-.001,.021):
            with self.assertRaises(ValueError):k.original_orientation_offsets(0.,x)

    def test_rigid_group_requires_all_original_participants(self):
        with self.assertRaises(ValueError):r.groups({'A_FRAME':self.old})

    def test_movement_rejects_invalid_or_excessive_input(self):
        for x in (True,None,float('nan'),.0201):
            with self.assertRaises(ValueError):r.shift_deck({},x)

    def test_normal_contact_does_not_invent_tension(self):
        patch={'neighbor':'A_FRAME','normal_into_cover':[1.,0,0],'points_mm':[(0.,0,0)]}
        self.assertFalse(r.w.equilibrium([patch],(0,0,0),(1,0,0),(0,0,0))['feasible'])

    def test_reaction_accounting_follows_actual_point_count(self):
        p=[{'neighbor':'A_FRAME','normal_into_cover':[-1.,0,0],'points_mm':[(0,0,0),(0,1,0)]}]
        fit={'feasible':True,'coefficients_N':[.25,.75]}
        self.assertEqual(r.reaction_by_part(p,fit),{'A_FRAME':[-1.,0.,0.]})
        with self.assertRaises(ValueError):r.reaction_by_part(p,{'feasible':True,'coefficients_N':[1.]})

    def test_force_balance_does_not_erase_unbalanced_moment(self):
        p=[{'neighbor':'A_FRAME','normal_into_cover':[-1.,0,0],'points_mm':[(0,-1,0),(0,1,0)]}]
        self.assertTrue(r.w.equilibrium(p,(0,0,0),(1,0,0),(0,0,0))['feasible'])
        self.assertFalse(r.w.equilibrium(p,(0,0,0),(1,0,0),(0,2,0))['feasible'])


class ExactRelativeSweepTests(unittest.TestCase):
    def screw(self):
        return r.v.single(r.disk_sweep(.5,0,0,0,.55,3.55).fuse(r.disk_sweep(.9,0,0,0,.1,.55)).clean())

    def test_sweep_volume_matches_complete_capsule_extrusion(self):
        b=r.disk_sweep(.5,-.02,.02,0,0,3.)
        self.assertAlmostEqual(r.v.vol(b),(math.pi*.5**2+2*.5*.04)*3,places=7)
        self.assertAlmostEqual(r.v.vol(r.disk_sweep(.5,0,0,0,0,3)),math.pi*.5**2*3,places=7)

    def test_invalid_sweep_parameters_rejected(self):
        for vals in ((True,0,1,0,0,1),(.5,1,0,0,0,1),(.5,0,1,0,1,0),(.5,0,float('nan'),0,0,1)):
            with self.assertRaises(ValueError):r.disk_sweep(*vals)

    def test_hollow_panel_full_path_and_real_overtravel(self):
        panel=r.v.box((-2,-2,0),(2,2,1.2))
        panel=r.v.single(panel.cut(r.disk_sweep(.55,0,0,0,-.1,1.3)).cut(r.disk_sweep(.95,0,0,0,-.1,.55)).clean())
        self.assertEqual(r.v.common(panel.translate((-.02,0,0)),r.inverse_screw_sweep(self.screw(),.04)),0.)
        self.assertGreater(r.v.common(panel.translate((-.06,0,0)),r.inverse_screw_sweep(self.screw(),.12)),1e-7)

    def test_unmodeled_screw_material_cannot_be_dropped(self):
        changed=r.v.single(self.screw().fuse(r.v.box((.4,-.1,.7),(.65,.1,.9))).clean())
        with self.assertRaises(ValueError):r.inverse_screw_sweep(changed,.04)


if __name__=='__main__':unittest.main(verbosity=2)
