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
        cls.root_base=cls.base
        cls.covers,_=g.load_covers(os.environ.get('RAZR_GUIDE_TEST_MOUNT'))
        cls.new,cls.receipts=g.build(cls.root_base,cls.covers)
        cls.base={**cls.root_base,**cls.covers}

    def test_exact_25_templates(self):
        self.assertEqual(len(self.new),25)
        for body in self.new.values():self.assertEqual(len(v.single(body).Solids()),1)

    def test_21_nonmodified_templates_remain_exact(self):
        names=set(self.new)-{'L_ROOT_OUTER','R_ROOT_OUTER','L_OLD_COVER','R_OLD_COVER'};self.assertEqual(len(names),21)
        for k in names:self.assertEqual(v.equal(self.new[k],self.base[k]),[0.,0.])

    def test_no_original_root_material_removed(self):
        for side in 'LR':self.assertEqual(v.vol(self.base[side+'_ROOT_OUTER'].cut(self.new[side+'_ROOT_OUTER'])),0.)

    def test_positive_addition_and_complete_balance(self):
        for side in 'LR':
            key=side+'_ROOT_OUTER';r=self.receipts[key]
            self.assertAlmostEqual(r['added_mm3'],.196,places=6)
            self.assertAlmostEqual(v.vol(self.base[key])+r['added_mm3'],v.vol(self.new[key]),places=6)

    def test_rejected_spine_really_hits_actual_cover(self):
        spine=v.box((16.8,17.8,4.5),(17.,23.2,7.3))
        self.assertGreater(v.common(spine,self.base['R_OLD_COVER']),2.)

    def test_independent_reconstruction_has_full_material(self):
        for side in 'LR':
            root,cover=w.reconstruct(self.base[side+'_ROOT_OUTER'],self.base[side+'_OLD_COVER'],side)
            self.assertEqual(v.equal(root,self.new[side+'_ROOT_OUTER']),[0.,0.])
            self.assertEqual(v.equal(cover,self.new[side+'_OLD_COVER']),[0.,0.])

    def test_four_finite_lands_per_side(self):
        for side in 'LR':
            faces=w.native_lands(self.new[side+'_ROOT_OUTER'],self.new[side+'_OLD_COVER'],side);self.assertEqual(len(faces),4)
            self.assertEqual(len({f['native_face_id'] for f in faces}),3)
            for f in faces:self.assertGreater(f['selected_patch_area_mm2'],1.7)

    def test_land_reader_rejects_old_missing_outer_faces(self):
        with self.assertRaises(ValueError):w.native_lands(self.base['R_ROOT_OUTER'],self.base['R_OLD_COVER'],'R')

    def test_left_right_symmetry(self):
        self.assertEqual(v.equal(self.new['L_ROOT_OUTER'],self.new['R_ROOT_OUTER'].mirror('YZ')),[0.,0.])

    def test_nominal_pure_X_contact_not_positive_overlap(self):
        for sign in (-1,1):
            pawl=self.new['R_PAWL'].translate((sign*.05,0,.02))
            target=self.new['R_ROOT_OUTER' if sign<0 else 'R_OLD_COVER']
            self.assertEqual(v.common(pawl,target),0.)
            self.assertLess(pawl.distance(target),1e-6)

    def test_overtravel_physically_obstructed(self):
        for sign in (-1,1):
            p=self.new['R_PAWL'].translate((sign*.06,0,.02))
            self.assertGreater(v.common(p,self.new['R_ROOT_OUTER' if sign<0 else 'R_OLD_COVER']),.02)

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
        with self.assertRaises(ValueError):g.build(p,self.covers)

    def test_missing_existing_cover_rejected(self):
        with self.assertRaises(ValueError):g.build(self.root_base,{'R_OLD_COVER':self.covers['R_OLD_COVER']})

    def test_unknown_side_rejected(self):
        with self.assertRaises(ValueError):g.additions('Q')

    def test_nonfinite_dimensions_rejected(self):
        with self.assertRaises(ValueError):v.box((0,0,0),(1,1,float('nan')))

    def test_cover_only_declared_material_removed(self):
        for side in 'LR':
            row=self.receipts[side+'_OLD_COVER']
            self.assertAlmostEqual(row['removed_mm3'],.50904,places=6)
            self.assertEqual(row['added_mm3'],0.)

    def test_actual_old_outward_stop_was_not_point_one_mm(self):
        body=self.new['R_PAWL'].translate((.05,0,.02))
        self.assertGreater(v.common(body,self.base['R_OLD_COVER']),.3)
        self.assertEqual(v.common(body,self.new['R_OLD_COVER']),0.)
