from pathlib import Path
import hashlib
import json
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
import thin_mechanism as t
import verify_thin_mechanism as v


class ThinMechanismTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.designs={side:t.design(side) for side in 'LR'}
        cls.cavity=t.n.single(t.n.cq.importers.importStep(str(ROOT/'engineering/phone-layout-study-20261015/native/stepped_A_cavity.step')).val())

    def test_twenty_three_named_positive_parts_not_discarded(self):
        for old,new,_ in self.designs.values():
            self.assertEqual(set(new),t.PARTS)
            self.assertEqual(len(new),23)
            for body in new.values():self.assertEqual(len(t.n.whole_material(body)[0]),1)

    def test_KEY_and_PAWL_native_geometry_unchanged(self):
        for old,new,_ in self.designs.values():
            for name in ('KEY','PAWL'):self.assertEqual(v.equal(old[name],new[name]),[0.,0.])

    def test_contact_core_not_scaled_or_repositioned(self):
        for side,(old,new,_) in self.designs.items():
            for i in (0,1):
                a=t.cropped(side,old['STOP_'+str(i)],-1.,.4)
                b=t.cropped(side,new['STOP_'+str(i)],-1.,.4)
                self.assertEqual(v.equal(a,b),[0.,0.])

    def test_all_screw_nominal_sizes_preserved(self):
        for side,(old,new,_) in self.designs.items():
            for name in old:
                if 'SCREW' in name:
                    self.assertAlmostEqual(old[name].Volume(),new[name].Volume(),places=7)
                    a=t.n.bounds(side,old[name]);b=t.n.bounds(side,new[name])
                    for (a0,a1),(b0,b1) in zip(a,b):self.assertAlmostEqual(a1-a0,b1-b0,places=7)

    def test_lower_cap_screw_translation_is_declared(self):
        for old,new,_ in self.designs.values():
            for j,shift in enumerate((3.35,7.9)):
                self.assertEqual(v.equal(old['SCREW_0_'+str(j)].translate((0,shift,0)),new['SCREW_0_'+str(j)]),[0.,0.])

    def test_whole_static_depth_is_6p6(self):
        for side,(_,new,_) in self.designs.items():
            e=t.n.bounds(side,t.n.cq.Compound.makeCompound(list(new.values())))[0]
            self.assertAlmostEqual(e[1]-e[0],6.6,places=7)

    def test_active_pawl_position_does_not_expand_depth(self):
        for side,(_,new,_) in self.designs.items():
            e=t.n.bounds(side,t.n.cq.Compound.makeCompound(list(new.values())+[t.parked(side,new['PAWL'])]))[0]
            self.assertAlmostEqual(e[1]-e[0],6.6,places=7)

    def test_fixed_shape_does_not_change_with_repeated_calls(self):
        for side,(_,new,_) in self.designs.items():
            again=t.scene(side)
            self.assertTrue(all(again[k].isSame(s) for k,s in new.items()))

    def test_disable_keeps_the_exact_wide_baseline(self):
        for side,(old,_,_) in self.designs.items():
            p=t.scene(side,enabled=False)
            self.assertTrue(all(p[k].isSame(s) for k,s in old.items()))

    def test_bad_side_and_nonboolean_switch_rejected(self):
        for side in ('X','',None):
            with self.assertRaises(ValueError):t.scene(side)
        for enabled in (0,1,'yes',None):
            with self.assertRaises(ValueError):t.scene('L',enabled=enabled)

    def test_nominal_spring_envelope_not_a_new_spring_qualification(self):
        for side,(old,new,report) in self.designs.items():
            self.assertFalse(report['spring_force_and_changed_stop_arm_stiffness_qualified'])
            for i in (0,1):self.assertAlmostEqual(old[f'SPRING_{i}_OD_TOL_ENVELOPE'].Volume(),new[f'SPRING_{i}_OD_TOL_ENVELOPE'].Volume(),places=7)

    def test_all_changed_material_is_accounted(self):
        for old,new,report in self.designs.values():
            for name,d in report['changes'].items():
                self.assertAlmostEqual(d['old_mm3']-d['removed_mm3']+d['added_mm3'],d['new_mm3'],places=7)
                self.assertAlmostEqual(d['new_mm3'],new[name].Volume(),places=7)

    def test_channels_have_positive_connections(self):
        for _,_,report in self.designs.values():
            self.assertEqual(len(report['channel_joins']),2)
            self.assertTrue(all(x['positive_channel_joint_mm3']>1e-7 for x in report['channel_joins']))

    def test_tenth_mm_nominal_uplift_gap_not_old_twentieth(self):
        for _,new,_ in self.designs.values():
            for root in t.ROOT_NAMES:
                self.assertEqual(t.n.common(new['OLD_COVER'].translate((0,0,.09)),new[root]),0.)
                self.assertGreater(t.n.common(new['OLD_COVER'].translate((0,0,.12)),new[root]),1e-7)

    def test_whole_components_fit_assumed_cavity_without_scaling(self):
        for side,(_,new,_) in self.designs.items():
            for part in new.values():
                placed=t.placed(part,side)
                self.assertAlmostEqual(part.Volume(),placed.Volume(),places=7)
                self.assertEqual(v.vol(placed.cut(self.cavity)),0.)

    def test_old_component_retains_real_placement_rejection(self):
        for side,(old,_,_) in self.designs.items():
            self.assertGreater(sum(v.vol(t.placed(p,side).cut(self.cavity)) for p in old.values()),1e-7)

    def test_two_proposed_component_placements_do_not_overlap(self):
        left=t.n.cq.Compound.makeCompound([t.placed(p,'L') for p in self.designs['L'][1].values()])
        right=t.n.cq.Compound.makeCompound([t.placed(p,'R') for p in self.designs['R'][1].values()])
        self.assertEqual(v.vol(left.intersect(right)),0.)

    def test_placement_is_one_rigid_rule_per_component(self):
        for side,(_,new,_) in self.designs.items():
            for p in new.values():self.assertEqual(v.equal(t.placed(p,side),v.placement(p,side)),[0.,0.])

    def test_assembly_plan_covers_all_noncoupled_parts_once(self):
        for side in 'LR':
            names=[x[0] for x in v.stage_plan(side)]
            self.assertEqual(len(names),len(set(names)))
            actual=set(names)-{'JAW_UPPER'}
            self.assertEqual(actual,(t.PARTS-{'KEY','PAWL'})|{'PARKED_PAWL'})

    def test_actual_phone_input_register_not_promoted(self):
        p=ROOT/'integration/assembly_inputs.json'
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),'7b7ebf0f48556f2feca175a35b882a9a48337de2bb5f54b1ba7a740f85e8ce6b')
        self.assertTrue(all(v is None for v in json.loads(p.read_text())['finished_geometry'].values()))
