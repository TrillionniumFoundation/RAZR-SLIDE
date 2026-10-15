from pathlib import Path
import os,sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
import pawl_lateral_guide as g
import verify_pawl_lateral_guide as w
import verify_root_clearance as v


class LateralGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=os.environ.get('RAZR_GUIDE_TEST_BASELINE')
        if path:
            _,cls.base,_=v.load_new(path)
        else:
            import endpoint_joint_pawl as ep
            import catalogue_roof_joint as cat
            import root_clearance as root
            p,_=ep.build();p,_=cat.build(p);inner,_=root.mounted_roots();cls.base,_=root.build(p,inner)
        cls.new,cls.receipts=g.build(cls.base)

    def test_exact_23_templates(self):
        self.assertEqual(len(self.new),23)
        for body in self.new.values():self.assertEqual(len(v.single(body).Solids()),1)

    def test_21_nonmodified_templates_remain_exact(self):
        names=set(self.new)-{'L_ROOT_OUTER','R_ROOT_OUTER'};self.assertEqual(len(names),21)
        for k in names:self.assertEqual(v.equal(self.new[k],self.base[k]),[0.,0.])

    def test_no_original_root_material_removed(self):
        for side in 'LR':self.assertEqual(v.vol(self.base[side+'_ROOT_OUTER'].cut(self.new[side+'_ROOT_OUTER'])),0.)

    def test_positive_addition_and_complete_balance(self):
        for side in 'LR':
            key=side+'_ROOT_OUTER';r=self.receipts[key]
            self.assertGreater(r['added_mm3'],3.7)
            self.assertAlmostEqual(v.vol(self.base[key])+r['added_mm3'],v.vol(self.new[key]),places=6)

    def test_missing_spine_is_rejected_connected_root(self):
        cut,_=w.reconstruct(self.base['R_ROOT_OUTER'],'R',spine=False)
        self.assertEqual(len(cut.Solids()),3)
        with self.assertRaises(ValueError):v.single(cut)

    def test_independent_reconstruction_has_full_material(self):
        for side in 'LR':
            rebuilt,_=w.reconstruct(self.base[side+'_ROOT_OUTER'],side)
            self.assertEqual(v.equal(rebuilt,self.new[side+'_ROOT_OUTER']),[0.,0.])

    def test_four_finite_lands_per_side(self):
        for side in 'LR':
            faces=w.native_lands(self.new[side+'_ROOT_OUTER'],side);self.assertEqual(len(faces),4)
            for f in faces:self.assertAlmostEqual(f['area_mm2'],1.96,places=6)

    def test_land_reader_rejects_old_missing_outer_faces(self):
        with self.assertRaises(ValueError):w.native_lands(self.base['R_ROOT_OUTER'],'R')

    def test_left_right_symmetry(self):
        self.assertEqual(v.equal(self.new['L_ROOT_OUTER'],self.new['R_ROOT_OUTER'].mirror('YZ')),[0.,0.])

    def test_nominal_pure_X_contact_not_positive_overlap(self):
        for sign in (-1,1):
            pawl=self.new['R_PAWL'].translate((sign*.05,0,.02))
            self.assertEqual(v.common(pawl,self.new['R_ROOT_OUTER']),0.)
            self.assertLess(pawl.distance(self.new['R_ROOT_OUTER']),1e-6)

    def test_overtravel_physically_obstructed(self):
        for sign in (-1,1):
            p=self.new['R_PAWL'].translate((sign*.06,0,.02))
            self.assertGreater(v.common(p,self.new['R_ROOT_OUTER']),.02)

    def test_old_unconstrained_lateral_witness_retained(self):
        for sign in (-1,1):
            p=self.base['R_PAWL'].translate((sign*.06,0,.02))
            self.assertEqual(v.common(p,self.base['R_ROOT_OUTER']),0.)

    def test_prior_error_box_retains_explicit_smaller_positive_margin(self):
        r=w.bounded_error(self.new)
        self.assertTrue(r['new_0p02_margin_rule_passes'])
        self.assertFalse(r['old_0p05_margin_rule_passes'])
        self.assertAlmostEqual(r['minimum_distance_mm'],.02,places=6)

    def test_contact_directions_do_not_claim_all_six_DOF(self):
        r=w.contact_checks(self.new,self.base)
        self.assertEqual(len(r['native_contact_rows']),16)
        for row in r['land_direction_records']:
            self.assertEqual(row['direction_matrix_rank'],3)
            self.assertIn('rotation about X',row['unconstrained_by_these_lands_alone'])
            self.assertTrue(row['not_an_active_contact_or_force_closure_claim'])

    def test_uncut_original_locking_and_slot_parts(self):
        for side in 'LR':
            for role in ('PAWL','TAB','SHOULDER_PIN_NOMINAL'):
                self.assertEqual(v.equal(self.base[side+'_'+role],self.new[side+'_'+role]),[0.,0.])

    def test_large_error_box_not_silently_accepted(self):
        r=v.error_envelopes(self.new,{s:v.slot_range(self.new[s+'_TAB']) for s in 'LR'},(.2,.1,.03))
        self.assertTrue(any(x['common_mm3']>v.TOL for x in r['rows']))

    def test_incomplete_base_rejected(self):
        p=dict(self.base);p.pop('R_ROOT_INNER')
        with self.assertRaises(ValueError):g.build(p)

    def test_ambiguous_flag_rejected(self):
        with self.assertRaises(ValueError):w.reconstruct(self.base['R_ROOT_OUTER'],'R',spine=1)

    def test_unknown_side_rejected(self):
        with self.assertRaises(ValueError):g.additions('Q')

    def test_nonfinite_dimensions_rejected(self):
        with self.assertRaises(ValueError):v.box((0,0,0),(1,1,float('nan')))
