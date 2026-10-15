from pathlib import Path
import hashlib
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
import serviceable_pawl as s
import verify_serviceable_pawl as v


class ServiceableControlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.new,cls.detail=s.build();cls.old=s.parent()

    def test_twenty_one_complete_native_roles(self):
        expected={side+'_'+k for side in 'LR' for k in v.ROLES}|{'A_BACK_PANEL'}
        self.assertEqual(set(self.new),expected)
        for b in self.new.values():self.assertEqual(len(s.c.n.whole_material(b)[0]),1)

    def test_original_PAWL_contact_material_is_preserved(self):
        for side in 'LR':self.assertEqual(v.vol(self.old[side+'_ORIGINAL_PAWL'].cut(self.new[side+'_PAWL'])),0.)

    def test_socket_boss_has_real_positive_joint(self):
        for r in self.detail['sides'].values():self.assertGreater(r['socket_to_original_PAWL_joint_mm3'],1e-7)

    def test_pin_is_separate_and_does_not_interpenetrate_socket(self):
        for side in 'LR':
            self.assertEqual(v.common(self.new[side+'_PAWL'],self.new[side+'_SHOULDER_PIN_NOMINAL']),0.)
            self.assertGreater(v.vol(self.new[side+'_SHOULDER_PIN_NOMINAL']),0.)

    def test_closed_active_slot_is_unchanged(self):
        roi=v.box((-40,0,4.6),(40,40,10.))
        for side in 'LR':self.assertEqual(v.w.v.equal(self.new[side+'_TAB'].intersect(roi),self.old[side+'_TAB'].intersect(roi)),[0.,0.])

    def test_original_pad_no_longer_has_to_pass_through_guide_floor(self):
        for side in 'LR':
            self.assertGreater(self.new[side+'_TAB'].BoundingBox().zmin,.59)
            self.assertLess(self.new[side+'_THUMB_PAD'].BoundingBox().zmax,.61)
            self.assertEqual(v.common(self.new[side+'_TAB'],self.new[side+'_THUMB_PAD']),0.)

    def test_root_only_loses_declared_corridor_material(self):
        for side in 'LR':
            old=self.old[side+'_ROOT_OUTER'];new=self.new[side+'_ROOT_OUTER']
            self.assertEqual(v.vol(new.cut(old)),0.)
            delta=old.cut(new);self.assertGreater(v.vol(delta),0.)
            bb=delta.BoundingBox();self.assertGreaterEqual(bb.ymin,19.3-1e-7);self.assertLessEqual(bb.ymax,20.7+1e-7)

    def test_panel_material_cost_is_not_hidden(self):
        r=self.detail['panel_material']
        self.assertGreater(r['removed_mm3'],0.);self.assertGreater(r['added_mm3'],0.)
        self.assertAlmostEqual(r['old_mm3']-r['removed_mm3']+r['added_mm3'],r['new_mm3'],places=7)

    def test_guide_roof_separation_has_no_positive_interference(self):
        for side in 'LR':self.assertEqual(v.common(self.new['A_BACK_PANEL'],self.new[side+'_ROOF']),0.)

    def test_nominal_fasteners_have_empty_final_mating_space(self):
        for side in 'LR':
            for i in (0,1):
                screw=self.new[f'{side}_ROOF_SCREW_{i}_M1_NOMINAL']
                self.assertEqual(v.common(screw,self.new['A_BACK_PANEL']),0.)
                self.assertEqual(v.common(screw,self.new[side+'_ROOF']),0.)
            screw=self.new[side+'_PAD_SCREW_M06_NOMINAL']
            self.assertEqual(v.common(screw,self.new[side+'_THUMB_PAD']),0.)
            self.assertEqual(v.common(screw,self.new[side+'_TAB']),0.)

    def test_blind_tip_gaps_remain_explicit_hypotheses(self):
        for row in self.detail['sides'].values():
            for key in ('roof_blind_tip_gap_mm','pad_blind_tip_gap_mm','pin_blind_tip_gap_mm'):self.assertAlmostEqual(row[key],.05)
        self.assertIn('no preload',self.detail['fasteners'])

    def test_insertion_plan_covers_every_new_detachable_body_once(self):
        for side in 'LR':
            names=[k for k,_ in v.plan(side)]
            self.assertEqual(len(names),7);self.assertEqual(set(names),{side+'_'+r for r in v.INSERT_ROLES})
            self.assertLess(names.index(side+'_TAB'),names.index(side+'_SHOULDER_PIN_NOMINAL'))
            self.assertLess(names.index(side+'_ROOF'),names.index(side+'_ROOF_SCREW_0_M1_NOMINAL'))

    def test_old_closed_guide_retains_true_top_entry_obstruction(self):
        for side in 'LR':self.assertGreater(v.common(self.old[side+'_TAB'].translate((0,0,1.)),self.old[side+'_GUIDE']),1e-7)

    def test_old_integral_head_retains_true_axial_entry_obstruction(self):
        for side in 'LR':self.assertGreater(v.common(self.old[side+'_TAB'].translate((-.3 if side=='R' else .3,0,0)),self.old[side+'_PAWL']),1e-7)

    def test_split_roof_and_manual_endstops_do_not_change_nominal_travel(self):
        p={side+'_TAB':self.new[side+'_TAB'] for side in 'LR'}
        for side in 'LR':p[side+'_GUIDE']=s.cq.Compound.makeCompound([self.new['A_BACK_PANEL'],self.new[side+'_ROOF']])
        c=v.w.slot_checks(p);self.assertEqual(len(c['flanks']),12);self.assertEqual(len(c['travel_stops']),8)

    def test_assembled_scene_keeps_all_seventy_nine_participants(self):
        scene=s.scene();self.assertEqual(len(scene),79)
        for side in 'LR':
            self.assertIn(side+'_SHOULDER_PIN_NOMINAL',scene);self.assertIn(side+'_THUMB_PAD',scene)

    def test_button_and_screw_move_as_one_input(self):
        scene=s.scene(left=1.5,right=0.)
        for role in ('TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL'):
            self.assertEqual(v.w.v.equal(scene['L_'+role],self.new['L_'+role].translate((0,1.5,0))),[0.,0.])
            self.assertEqual(v.w.v.equal(scene['R_'+role],self.new['R_'+role]),[0.,0.])

    def test_invalid_manual_inputs_are_not_clamped(self):
        for u in (-.01,3.01,True,float('nan')):
            with self.assertRaises(ValueError):s.a.displacement(u)

    def test_actual_phone_input_register_not_replaced(self):
        p=ROOT/'integration/assembly_inputs.json'
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),'7b7ebf0f48556f2feca175a35b882a9a48337de2bb5f54b1ba7a740f85e8ce6b')

    def test_nominal_control_parts_stay_in_A_outer(self):
        outer=s.c.parent('A_OUTER')
        for key,b in self.new.items():
            if not key.endswith('GUIDE_REFERENCE'):self.assertEqual(v.vol(b.cut(outer)),0.)

    def test_admission_mouth_clears_earlier_root_closure_and_old_root_fails(self):
        import json,tarfile,tempfile
        folder=ROOT/'engineering/serviceable-pawl-20261015'
        gm=json.loads((folder/'geometry-manifest.json').read_text())
        arc=folder/gm['archive']
        self.assertEqual(hashlib.sha256(arc.read_bytes()).hexdigest(),gm['archive_sha256'])
        for side in 'LR':
            self.assertTrue(v.root_closure_check(self.new,side)['result']['all_regions_clear'])
            name=side+'_ROOT_OUTER.step';rec=next(r for r in gm['files'] if r['path']==name)
            with tarfile.open(arc,'r:gz') as stream:raw=stream.extractfile(name).read()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),rec['sha256'])
            with tempfile.TemporaryDirectory() as td:
                p=Path(td)/name;p.write_bytes(raw);roots=s.cq.importers.importStep(str(p)).vals()
            self.assertEqual(len(roots),1);oldroot=s.c.n.single(roots[0])
            self.assertGreater(v.common(oldroot.translate((0,0,1.5)),self.new[side+'_PAWL'].translate((0,0,1.1))),1e-7)
