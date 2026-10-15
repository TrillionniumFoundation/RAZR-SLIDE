from pathlib import Path
import sys,math,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
import panel_bearing_web as a
from verify_panel_bearing_web import additions

class PanelBearingWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        v=a.v
        panel=v.box((-15.,12.,0.),(15.,32.,.65))
        for x in (-11.6,11.6):
            panel=v.single(panel.fuse(v.box((x-.95,13.4,.6),(x+.95,30.7,3.))).clean())
            for y in (14.5,29.6):
                panel=v.single(panel.cut(a.cq.Solid.makeCylinder(.95,2.05,a.cq.Vector(x,y,-.1))).clean())
        cls.before=panel
        keys=a.BODY_ROLES|{'A_FRAME'}|{f'FRAME_{i}_{r}' for i in range(4) for r in ('M1x3_NOMINAL','NUT_SHNS_M1_NOMINAL')}
        cls.parts={k:panel for k in keys};cls.after,cls.report=a.build(cls.parts)

    def test_only_panel_identity_changes(self):
        self.assertEqual([k for k in self.parts if not self.parts[k].isSame(self.after[k])],['A_BACK_PANEL'])
    def test_panel_remains_single_solid(self):
        self.assertEqual(len(self.after['A_BACK_PANEL'].Solids()),1);self.assertTrue(self.after['A_BACK_PANEL'].isValid())
    def test_original_material_not_removed(self):
        self.assertEqual(a.v.vol(self.before.cut(self.after['A_BACK_PANEL'])),0.)
    def test_eight_connected_strips(self):
        self.assertEqual(len(self.report['joins']),8)
        self.assertTrue(all(x['initial_native_overlap_mm3']>1e-7 for x in self.report['joins']))
    def test_finite_nominal_wall(self):
        self.assertAlmostEqual(self.report['minimum_nominal_wall_mm'],.15)
    def test_old_tangent_wall_record(self):
        self.assertEqual(self.report['old_guide_halfwidth_minus_bore_mm'],0.)
    def test_bore_cylinder_is_not_filled(self):
        added=self.after['A_BACK_PANEL'].cut(self.before)
        for x in (-11.6,11.6):
            for y in (14.5,29.6):
                hole=a.cq.Solid.makeCylinder(.95,1.35,a.cq.Vector(x,y,.6))
                self.assertEqual(a.v.common(added,hole),0.)
    def test_analytical_added_volume(self):
        self.assertAlmostEqual(self.report['panel_added_mm3'],8*.15*2.2*1.35,places=7)
    def test_material_balance(self):
        self.assertAlmostEqual(a.v.vol(self.before)+self.report['panel_added_mm3'],a.v.vol(self.after['A_BACK_PANEL']),places=7)
    def test_mirrored_complete_material(self):
        a.v.equal(self.after['A_BACK_PANEL'],self.after['A_BACK_PANEL'].mirror('YZ'))
    def test_fixed_height_and_width(self):
        for body in a.web(11.6,29.6):
            b=body.BoundingBox();self.assertAlmostEqual(b.zmin,.6);self.assertAlmostEqual(b.zmax,2.);self.assertAlmostEqual(b.xlen,.15)
    def test_exact_independent_reconstruction(self):
        body=self.before
        for piece in additions().values():body=a.v.single(body.fuse(piece).clean())
        a.v.equal(body,self.after['A_BACK_PANEL'])
    def test_missing_template_rejected(self):
        p=dict(self.parts);p.pop('A_FRAME')
        with self.assertRaises(ValueError):a.build(p)
    def test_extra_template_rejected(self):
        with self.assertRaises(ValueError):a.build({**self.parts,'EXTRA':self.before})
    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):a.web(True,1.)
    def test_nonfinite_rejected(self):
        for x in (float('nan'),float('inf')):
            with self.assertRaises(ValueError):a.web(x,1.)
    def test_nonpositive_wall_rejected(self):
        for half in (.95,.9,0.):
            with self.assertRaises(ValueError):a.web(11.6,14.5,half=half)
    def test_zero_bore_rejected(self):
        with self.assertRaises(ValueError):a.web(11.6,14.5,radius=0.)
    def test_reversed_height_rejected(self):
        with self.assertRaises(ValueError):a.web(11.6,14.5,z0=2.,z1=.6)
    def test_strips_disconnected_from_parent_rejected(self):
        p=dict(self.parts);p['A_BACK_PANEL']=a.v.box((50.,50.,50.),(51.,51.,51.))
        with self.assertRaises(ValueError):a.build(p)

    def test_whole_material_partition_closes(self):
        from verify_panel_bearing_web import partition_certificate
        r=partition_certificate(self.before,self.after['A_BACK_PANEL'])
        self.assertTrue(r['all_material_partitioned']);self.assertAlmostEqual(r['gain_mm3'],3.564,places=7)
    def test_loss_outside_windows_rejected(self):
        from verify_panel_bearing_web import partition_certificate
        broken=self.after['A_BACK_PANEL'].cut(a.v.box((0.,20.,-.1),(1.,21.,1.)))
        with self.assertRaises(ValueError):partition_certificate(self.before,broken)
    def test_incomplete_local_web_rejected(self):
        from verify_panel_bearing_web import partition_certificate
        broken=self.after['A_BACK_PANEL'].cut(a.v.box((12.65,13.4,.65),(12.7,15.6,2.)))
        with self.assertRaises(ValueError):partition_certificate(self.before,broken)
