from pathlib import Path
import sys,unittest,ast
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
import stow_continuous_slots_v2 as s
b=s.b

class ContinuousSlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixed={side:s.fixed_design(side) for side in 'LR'}
    def test_one_root_all_original_material_outside_pawl_collision_retained(self):
        for side,(old,new,env,report) in self.fixed.items():
            b.participant(new);self.assertEqual(len(new.Solids()),1)
            self.assertTrue(report['no_largest_component_selection'])
            self.assertLessEqual(report['removed_outside_pawl_envelopes_mm3'],1e-7)
            self.assertAlmostEqual(report['removed_original_mm3'],.0256,places=7)
    def test_material_balance_and_unexpanded_outer_bounds(self):
        for old,new,env,r in self.fixed.values():
            self.assertAlmostEqual(r['old_root_volume_mm3']+r['added_mm3']-r['removed_original_mm3'],r['new_root_volume_mm3'],places=7)
            self.assertTrue(r['full_root_bounds_unchanged']);self.assertFalse(r['manufacturing_go'])
    def test_complete_relative_root_installation_envelopes_clear(self):
        for old,new,env,r in self.fixed.values():
            self.assertEqual(set(env),{'ROOT_INNER','STOP_0','STOP_1','PARKED_PAWL'})
            for part in env.values():self.assertEqual(b.strict_common(new,part)['checked_volume_mm3'],0.)
    def test_unchanged_old_pawl_return_failure_reproduces(self):
        for side,(old,new,env,r) in self.fixed.items():
            _,sweep,_,_=s.previous.canonical_envelopes(side)
            self.assertGreater(b.strict_common(old[s.ROOT_NAME],sweep)['checked_volume_mm3'],.01)
            self.assertEqual(b.strict_common(new,sweep)['checked_volume_mm3'],0.)
    def test_patch_cannot_move_with_key_or_stop(self):
        for side,(old,new,env,r) in self.fixed.items():
            moved=dict(old);moved.pop('KEY');moved['STOP_0']=moved['STOP_0'].translate((0,0,-.5));out,a=s.repair_parts(moved,'STOW',side)
            self.assertTrue(out[s.ROOT_NAME].wrapped.IsSame(new.wrapped))
            self.assertTrue(all(out[n].wrapped.IsSame(p.wrapped) for n,p in moved.items() if n!=s.ROOT_NAME))
    def test_disable_and_OPEN_keep_unmodified_part_identities(self):
        for side,(old,new,env,r) in self.fixed.items():
            out,_=s.repair_parts(old,'STOW',side,enabled=False);self.assertTrue(all(out[n].wrapped.IsSame(p.wrapped) for n,p in old.items()))
            opened,_=s.parent.scene('OPEN',side);out,_=s.repair_parts(opened,'OPEN',side);self.assertTrue(all(out[n].wrapped.IsSame(p.wrapped) for n,p in opened.items()))
    def test_unexpected_original_root_is_rejected(self):
        old=self.fixed['L'][0];bad=dict(old);bad[s.ROOT_NAME]=bad[s.ROOT_NAME].translate((.1,0,0))
        with self.assertRaises(ValueError):s.repair_parts(bad,'STOW','L')
        with self.assertRaises(ValueError):s.repair_parts(old,'STOW','L',enabled=1)
    def test_original_564_and_184_checks_not_weakened(self):
        old=(ROOT/'integration/continue_split_sequence.py').read_text();new=(ROOT/'integration/replay_continuous_sequence.py').read_text()
        self.assertTrue(new.endswith(old.replace('import split_root_cartridges_v9 as s','import stow_continuous_slots_v2 as s')))
        def main(text):return ast.get_source_segment(text,next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='main'))
        self.assertEqual(main((ROOT/'integration/replay_continuous_assembly.py').read_text()),main(Path(s.parent.__file__).read_text()).replace("HERE.parent/'inputs'/k","GROUP/'inputs'/k"))
