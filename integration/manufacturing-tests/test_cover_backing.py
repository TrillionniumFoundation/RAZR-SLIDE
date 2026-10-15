"""Algorithm/geometry regressions; synthetic panel fixtures are not phone tests."""
from pathlib import Path
import math
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
import cover_backing as b
import verify_cover_backing as w


class CoverBackingTests(unittest.TestCase):
    def fixture(self):
        roles=('ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL','PAWL','SHOULDER_PIN_NOMINAL',
               'TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL','ROOF','GUIDE_REFERENCE','ROOT_OUTER','ROOT_INNER','OLD_COVER')
        result={s+'_'+r:b.single(b.box((0,0,0),(1,1,1))) for s in 'LR' for r in roles}
        result['A_BACK_PANEL']=b.single(b.box((-40,0,0),(40,90,.65)))
        return result

    def test_four_complete_posts(self):
        self.assertEqual(len(b.posts('L'))+len(b.posts('R')),4)
        for s in 'LR':
            for p in b.posts(s).values():self.assertEqual(len(p.Solids()),1)

    def test_invalid_side_rejected(self):
        for side in ('X','',True,None):
            with self.assertRaises(ValueError):b.posts(side)

    def test_mirror_is_material_equivalent(self):
        for l,r in zip(b.posts('L').values(),b.posts('R').values()):w.v.equal(l.mirror('YZ'),r)

    def test_post_cap_does_not_repeat_tall_collision(self):
        for p in b.posts('R').values():self.assertAlmostEqual(p.BoundingBox().zmax,7.0)

    def test_new_panel_one_solid(self):
        result,_=b.build(self.fixture());self.assertEqual(len(result['A_BACK_PANEL'].Solids()),1)

    def test_panel_original_material_retained(self):
        base=self.fixture();result,r=b.build(base)
        self.assertLessEqual(b.vol(base['A_BACK_PANEL'].cut(result['A_BACK_PANEL'])),1e-7)
        self.assertEqual(r['original_panel_removed_mm3'],0.)

    def test_added_material_volume_and_connections(self):
        _,r=b.build(self.fixture());self.assertAlmostEqual(r['new_panel_material_mm3'],33.655,places=6)
        self.assertEqual(len(r['joins']),4)
        self.assertTrue(all(x['overlap_with_original_panel_mm3']>0 for x in r['joins']))

    def test_only_panel_identity_changes(self):
        base=self.fixture();result,_=b.build(base)
        self.assertEqual(len(result),25)
        self.assertTrue(all(result[k].isSame(base[k]) for k in base if k!='A_BACK_PANEL'))

    def test_missing_component_rejected(self):
        base=self.fixture();base.pop('R_OLD_COVER')
        with self.assertRaises(ValueError):b.build(base)

    def test_extra_component_rejected(self):
        base=self.fixture();base['extra']=base['R_OLD_COVER']
        with self.assertRaises(ValueError):b.build(base)

    def test_disconnected_anchor_rejected(self):
        base=self.fixture();base['A_BACK_PANEL']=b.box((-40,0,-1),(40,90,-.5))
        with self.assertRaises(ValueError):b.build(base)

    def test_growing_cover_motion_not_hidden_as_fixed_guide(self):
        r=b.nominal_lateral_interval(.02)
        self.assertAlmostEqual(r['outboard_mm'],.07);self.assertAlmostEqual(r['inboard_mm'],-.05)
        self.assertTrue(r['not_whole_freeplay_or_process_qualification'])

    def test_unmoved_cover_retains_original_nominal_interval(self):
        self.assertEqual(b.nominal_lateral_interval(0.)['outboard_mm'],.05)

    def test_invalid_takeup_values_rejected(self):
        for v in (True,None,'0',float('nan'),float('inf'),-.001,.02001):
            with self.assertRaises(ValueError):b.nominal_lateral_interval(v)

    def test_no_contacts_cannot_hold_outward_force(self):
        self.assertFalse(w.equilibrium([], [0,0,0], [1,0,0], [0,0,0])['feasible'])

    def test_wrong_normal_cannot_hold_outward_force(self):
        c=[{'normal_into_cover':[1,0,0],'points_mm':[[0,0,0]]}]
        self.assertFalse(w.equilibrium(c,[0,0,0],[1,0,0],[0,0,0])['feasible'])

    def test_correct_normal_positive_control(self):
        c=[{'normal_into_cover':[-1,0,0],'points_mm':[[0,0,0]]}]
        r=w.equilibrium(c,[0,0,0],[1,0,0],[0,0,0]);self.assertTrue(r['feasible']);self.assertAlmostEqual(r['sum_coefficients_N'],1)

    def test_force_balance_alone_does_not_hide_moment(self):
        c=[{'normal_into_cover':[-1,0,0],'points_mm':[[0,0,0]]}]
        self.assertFalse(w.equilibrium(c,[0,0,0],[1,0,0],[0,1,0])['feasible'])

    def test_two_supports_can_balance_intermediate_point(self):
        c=[{'normal_into_cover':[-1,0,0],'points_mm':[[0,-1,0],[0,1,0]]}]
        r=w.equilibrium(c,[0,0,0],[1,0,0],[0,0,0]);self.assertTrue(r['feasible']);self.assertLess(r['residual'],1e-8)

    def test_invalid_wrench_or_normal_rejected(self):
        with self.assertRaises(ValueError):w.equilibrium([], [0,0], [1,0,0], [0,0,0])
        with self.assertRaises(ValueError):w.equilibrium([{'normal_into_cover':[2,0,0],'points_mm':[[0,0,0]]}], [0,0,0], [1,0,0], [0,0,0])
        with self.assertRaises(ValueError):w.equilibrium([], [0,0,0], [float('nan'),0,0], [0,0,0])
