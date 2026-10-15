from pathlib import Path
import os,sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
import pawl_box_guide as g
import verify_pawl_box_guide as w
v=w.v

class BodyGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=os.environ.get('RAZR_BOX_GUIDE_BASELINE')
        if path:_,cls.base,_=w.w.load_new(path)
        else:
            import endpoint_joint_pawl as ep, catalogue_roof_joint as cat, root_clearance as rc, pawl_lateral_guide as lat
            p,_=ep.build();p,_=cat.build(p);inner,_=rc.mounted_roots();p,_=rc.build(p,inner);covers,_=lat.load_covers();cls.base,_=lat.build(p,covers)
        cls.new,cls.material=g.build(cls.base)
        cls.slot=v.slot_range(cls.new['R_TAB'])

    def test_25_whole_templates(self):
        self.assertEqual(len(self.new),25)
        for body in self.new.values():self.assertEqual(len(v.single(body).Solids()),1)

    def test_18_other_templates_exact(self):
        changed={'A_BACK_PANEL'}|{s+'_'+r for s in 'LR' for r in ('ROOT_OUTER','ROOF','GUIDE_REFERENCE')}
        self.assertEqual(len(set(self.base)-changed),18)
        for k in set(self.base)-changed:self.assertEqual(v.equal(self.base[k],self.new[k]),[0.,0.])

    def test_root_material_never_removed(self):
        for s in 'LR':self.assertEqual(v.vol(self.base[s+'_ROOT_OUTER'].cut(self.new[s+'_ROOT_OUTER'])),0.)

    def test_bearing_addition_recorded(self):
        for s in 'LR':self.assertAlmostEqual(self.material[s+'_ROOT_OUTER']['added_mm3'],.191,places=6)

    def test_panel_removal_recorded(self):
        self.assertAlmostEqual(self.material['A_BACK_PANEL']['removed_mm3'],.70356319581,places=6)

    def test_roof_removal_recorded(self):
        for s in 'LR':self.assertAlmostEqual(self.material[s+'_ROOF']['removed_mm3'],.10440001247,places=6)

    def test_all_changes_balance(self):
        for key,rec in self.material.items():
            if isinstance(rec,dict):self.assertAlmostEqual(v.vol(self.base[key])-rec['removed_mm3']+rec['added_mm3'],v.vol(self.new[key]),places=6)

    def test_mirrored_actual_roots(self):
        self.assertEqual(v.equal(self.new['L_ROOT_OUTER'],self.new['R_ROOT_OUTER'].mirror('YZ')),[0.,0.])

    def test_independent_root_and_relief(self):
        for s in 'LR':
            self.assertEqual(v.equal(w.expected_root(self.base[s+'_ROOT_OUTER'],s),self.new[s+'_ROOT_OUTER']),[0.,0.])
            self.assertEqual(v.equal(g.hand(g.carrier_relief(),s),w.relief(s)),[0.,0.])

    def test_old_root_lacks_new_bearing_faces(self):
        with self.assertRaises(ValueError):w.native_y_faces(self.base,'R')

    def test_new_actual_faces(self):
        for s in 'LR':
            r=w.native_y_faces(self.new,s);self.assertEqual(len(r),2)
            for f in r:self.assertAlmostEqual(f['native_face_area_mm2'],2.8,places=6)

    def test_coupled_slot_equation(self):
        for u in (0.,1.5,3.):
            for dy in (-.075,0.,.075):
                z=w.coupled_lift(self.slot,u,dy)
                self.assertAlmostEqual(z+self.slot['slope']*dy,self.slot['origin']+u*self.slot['slope'])

    def test_illegal_numbers_rejected(self):
        for x in (True,float('nan'),float('inf'),'0'):
            with self.assertRaises(ValueError):w.coupled_lift(self.slot,0,x)

    def test_out_of_diagnostic_range_rejected(self):
        for args in ((-1.,0.,0),(4.,0.,0),(0.,.1,0),(0.,0.,2)):
            with self.assertRaises(ValueError):w.coupled_lift(self.slot,*args)

    def test_body_contact_and_old_edge_witnesses(self):
        r=w.contact_records(self.new,self.base);self.assertEqual(len(r['body_contact_rows']),16);self.assertEqual(len(r['prior_pin_edge_witnesses']),8)
        for q in r['direction_records']:
            self.assertEqual(q['rank'],5);self.assertTrue(q['not_active_or_force_closure']);self.assertEqual(q['remaining_null_direction'],'Z translation')

    def test_body_overtravel_really_hits(self):
        for dy in (-.085,.085):
            p=self.new['R_PAWL'].translate((0,dy,w.coupled_lift(self.slot,0,dy)))
            self.assertGreater(v.common(p,self.new['R_ROOT_OUTER']),.01)

    def test_full_material_envelopes(self):
        r=w.complete_envelopes(self.new);self.assertEqual(len(r['comparisons']),40)
        self.assertTrue(r['complete_nominal_u_and_Y_and_slot_flanks'])

    def test_existing_rigid_error_scope_still_only_two_hundredths(self):
        r=w.w.bounded_error(self.new)
        self.assertFalse(r['old_0p05_margin_rule_passes']);self.assertAlmostEqual(r['minimum_distance_mm'],.02,places=6)

    def test_original_manual_slot_exact(self):
        for s in 'LR':self.assertEqual(v.equal(self.base[s+'_TAB'],self.new[s+'_TAB']),[0.,0.])

    def test_all_named_fasteners_unchanged(self):
        for k in self.base:
            if 'SCREW' in k or 'PIN' in k:self.assertEqual(v.equal(self.base[k],self.new[k]),[0.,0.])

    def test_no_new_physical_part(self):
        self.assertEqual(set(self.base),set(self.new))

    def test_incomplete_base_rejected(self):
        p=dict(self.base);p.pop('R_OLD_COVER')
        with self.assertRaises(ValueError):g.build(p)

    def test_unneeded_crown_removal_is_stopped(self):
        for side in 'LR':
            for x in (10.9,12.3):
                patch=v.hand(v.box((x-.05,19.9,7.13),(x+.05,20.1,7.3)),side)
                self.assertEqual(v.vol(patch.cut(self.new[side+'_ROOF'])),0.)
        self.assertAlmostEqual(g.carrier_relief().BoundingBox().zmin,4.57,places=6)
        self.assertAlmostEqual(g.carrier_relief().BoundingBox().zmax,7.13,places=6)
