from pathlib import Path
import os,sys,math,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
import root_clearance as r
import verify_root_clearance as v


class RootClearanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest=os.environ.get('RAZR_ROOT_TEST_BASELINE')
        if manifest:
            _,cls.base,_=r.read(manifest)
            cls.inner,_=r.mounted_roots(os.environ['RAZR_ROOT_TEST_MOUNT'])
        else:
            import endpoint_joint_pawl as endpoint
            cls.base,_=endpoint.build()
            cls.inner,_=r.mounted_roots()
        cls.parts,cls.details=r.build(cls.base,cls.inner)
        cls.slots={s:v.slot_range(cls.parts[s+'_TAB']) for s in 'LR'}

    def test_exactly_twenty_three_complete_templates(self):
        self.assertEqual(len(self.parts),23)
        for body in self.parts.values():self.assertEqual(len(r.single(body).Solids()),1)

    def test_all_nineteen_unmodified_templates_stay_exact(self):
        names=set(self.base)-{'L_ROOT_OUTER','R_ROOT_OUTER'};self.assertEqual(len(names),19)
        for n in names:self.assertEqual(v.equal(self.parts[n],self.base[n]),[0.,0.])

    def test_two_outer_cut_fragments_are_not_discarded(self):
        for s in 'LR':
            d=self.details[s+'_ROOT_OUTER'];self.assertEqual(d['cut_only_components'],3)
            self.assertEqual(d['discarded_cut_material_mm3'],0.)

    def test_cut_only_candidate_is_rejected_as_one_root(self):
        _,cut=v.reconstruct(self.base['R_ROOT_OUTER'],'R',True)
        with self.assertRaises(ValueError):r.single(cut)

    def test_independent_full_material_reconstruction_matches(self):
        for s in 'LR':
            for role,out in [('ROOT_INNER',False),('ROOT_OUTER',True)]:
                old=self.base[s+'_'+role] if out else self.inner[s+'_'+role]
                shape,_=v.reconstruct(old,s,out);self.assertEqual(v.equal(shape,self.parts[s+'_'+role]),[0.,0.])

    def test_signed_material_balance_per_root(self):
        for d in self.details.values():
            self.assertAlmostEqual(d['old_volume_mm3']-d['removed_mm3']+d['added_mm3'],d['new_volume_mm3'],places=6)
            self.assertGreater(d['removed_mm3'],0)

    def test_inner_roots_receive_no_unreported_added_material(self):
        for s in 'LR':self.assertEqual(self.details[s+'_ROOT_INNER']['added_mm3'],0.)

    def test_both_outer_roots_have_real_connected_support_material(self):
        for s in 'LR':self.assertGreater(self.details[s+'_ROOT_OUTER']['added_mm3'],.8)

    def test_old_error_witnesses_reproduce_and_new_ones_clear(self):
        for s in 'LR':
            lift=self.slots[s]['origin']+self.slots[s]['halfwidth']
            for dy in (-.02,.02):
                body=self.base[s+'_PAWL'].translate((0,dy,lift))
                self.assertGreater(v.common(body,self.base[s+'_ROOT_OUTER']),.03)
                self.assertEqual(v.common(body,self.parts[s+'_ROOT_OUTER']),0.)

    def test_entire_declared_interface_error_box_has_margin(self):
        result=v.error_envelopes(self.parts,self.slots)
        self.assertTrue(result['all_envelopes_clear']);self.assertEqual(len(result['rows']),20)
        self.assertGreater(result['minimum_envelope_to_root_distance_mm'],.049)

    def test_larger_error_box_does_not_silently_pass(self):
        result=v.error_envelopes(self.parts,self.slots,(.3,.3,.3))
        self.assertFalse(result['all_envelopes_clear'])

    def test_proof_cover_refuses_an_uncovered_PAWL_addition(self):
        p=dict(self.parts)
        extra=r.block((15.,20.,6.1),(15.1,20.1,6.5))
        p['R_PAWL']=r.single(p['R_PAWL'].fuse(extra).clean())
        with self.assertRaises(ValueError):v.error_envelopes(p,self.slots)

    def test_no_change_to_manual_slot_datum_or_radius(self):
        for x in self.slots.values():
            self.assertAlmostEqual(x['origin'],.02,places=7);self.assertAlmostEqual(x['slope'],1.06/3,places=7)

    def test_left_and_right_roots_are_mirrors(self):
        for k in ('ROOT_INNER','ROOT_OUTER'):
            self.assertEqual(v.equal(self.parts['L_'+k],self.parts['R_'+k].mirror('YZ')),[0.,0.])

    def test_invalid_side_rejected(self):
        for side in ('','A','LR'):
            with self.assertRaises(ValueError):r.handed(self.parts['R_PAWL'],side)

    def test_ambiguous_root_kind_rejected(self):
        with self.assertRaises(ValueError):r.modify_root(self.base['R_ROOT_OUTER'],'R',outer=1)

    def test_nonfinite_or_boolean_boxes_rejected(self):
        for x in (True,float('nan'),float('inf')):
            with self.assertRaises(ValueError):r.block((x,0,0),(1,1,1))

    def test_zero_or_reverse_boxes_rejected(self):
        for upper in ((0,1,1),(-1,1,1)):
            with self.assertRaises(ValueError):r.block((0,0,0),upper)

    def test_invalid_error_specification_rejected(self):
        for values in ((.1,.1),(-.1,0,0),(True,0,0),(float('nan'),0,0)):
            with self.assertRaises(ValueError):v.error_envelopes(self.parts,self.slots,values)

    def test_nominal_pin_socket_and_locking_geometry_remain_exact(self):
        for s in 'LR':
            for role in ('PAWL','SHOULDER_PIN_NOMINAL','TAB'):
                self.assertEqual(v.equal(self.parts[s+'_'+role],self.base[s+'_'+role]),[0.,0.])
