"""Local geometry regressions for fixed operation-slotted candidate, not full release."""
from pathlib import Path
import ast
import gzip
import hashlib
import json
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
import stow_motion_slots as s


class FixedMotionSlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original={side:s.parent.scene('STOW',side)[0] for side in 'LR'}
        cls.repaired={side:s.repair_parts(parts,'STOW',side) for side,parts in cls.original.items()}

    def test_single_root_retains_all_unrelated_parts_and_bounds(self):
        for side,(parts,receipt) in self.repaired.items():
            before=self.original[side]
            self.assertEqual(receipt['changed_parts'],[s.ROOT_NAME])
            s.b.participant(parts[s.ROOT_NAME]);self.assertEqual(receipt['final_root_solids'],1)
            self.assertLess(max(abs(v) for v in receipt['bounds_delta_mm'].values()),1e-7)
            self.assertTrue(all(parts[k].wrapped.IsSame(v.wrapped) for k,v in before.items() if k!=s.ROOT_NAME))
            self.assertFalse(receipt['mechanical_strength_qualified'])

    def test_fixed_cutters_bind_original_failure_not_relabelled_pass(self):
        payload=gzip.decompress((ROOT/'engineering/workplan-execution-20261014/integration/sequence-native-report.json.gz').read_bytes())
        self.assertEqual(hashlib.sha256(payload).hexdigest(),s.HISTORY_SHA256)
        history=json.loads(payload);self.assertEqual(history['unexpected_positive_rows'],18)
        for _,receipt in self.repaired.values():
            self.assertEqual(receipt['fixed_design_slots']['fixed_cutter_count'],84)
            self.assertEqual(receipt['fixed_design_slots']['original_operation_sha256'],s.HISTORY_SHA256)

    def test_two_root_envelopes_clear_and_original_negative_controls_preserved(self):
        for side,(parts,_) in self.repaired.items():
            _,returned,insertion,_=s.canonical_envelopes(side)
            for envelope in (returned,insertion):
                self.assertEqual(s.b.strict_common(parts[s.ROOT_NAME],envelope)['checked_volume_mm3'],0.)
                self.assertGreater(s.b.strict_common(self.original[side][s.ROOT_NAME],envelope)['checked_volume_mm3'],.01)

    def test_only_original_motion_conflict_material_is_removed(self):
        for side,(parts,receipt) in self.repaired.items():
            old=self.original[side][s.ROOT_NAME];new=parts[s.ROOT_NAME]
            _,returned,insertion,_=s.canonical_envelopes(side)
            residue=old.cut(new).cut(returned).cut(insertion)
            self.assertLessEqual(sum(s.volume_leaves(residue)),1e-7)
            self.assertAlmostEqual(receipt['removed_material_mm3'],.0256,places=7)
            self.assertAlmostEqual(old.Volume()+receipt['added_material_mm3']-receipt['removed_material_mm3'],new.Volume(),places=7)

    def test_original_sampled_stop_and_key_positions_remain_clear(self):
        history=json.loads(gzip.decompress((ROOT/'engineering/workplan-execution-20261014/integration/sequence-native-report.json.gz').read_bytes()))
        for side,(parts,_) in self.repaired.items():
            source=self.original[side];root=parts[s.ROOT_NAME]
            for row in history['cam_brackets']:
                if row['port']!='STOW' or row['side']!=side:continue
                key=source['KEY'].translate(s.b.identity.qvec('STOW',row['q_mm']))
                self.assertLessEqual(s.b.strict_common(root,key)['checked_volume_mm3'],1e-7)
                for i,lift in enumerate(row['actual_cam_collision_free_lifts_mm']):
                    stop=source['STOP_'+str(i)].translate(s.b.rvec('STOW',lift-1.14))
                    self.assertLessEqual(s.b.strict_common(root,stop)['checked_volume_mm3'],1e-7)

    def test_disabling_preserves_original_failure_geometry(self):
        for side,parts in self.original.items():
            result,receipt=s.repair_parts(parts,'STOW',side,enabled=False)
            self.assertEqual(receipt['changed_parts'],[])
            self.assertTrue(all(result[k].wrapped.IsSame(v.wrapped) for k,v in parts.items()))

    def test_root_cannot_change_with_simulated_stop_or_key_state(self):
        for side,parts in self.original.items():
            other=dict(parts);other.pop('KEY');other['STOP_0']=other['STOP_0'].translate(s.b.rvec('STOW',-.5))
            result,receipt=s.repair_parts(other,'STOW',side)
            expected=self.repaired[side][0][s.ROOT_NAME]
            self.assertLessEqual(sum(s.volume_leaves(result[s.ROOT_NAME].cut(expected))),1e-7)
            self.assertLessEqual(sum(s.volume_leaves(expected.cut(result[s.ROOT_NAME]))),1e-7)
            self.assertTrue(receipt['root_not_recut_for_actual_lift_or_key_state'])

    def test_replay_preserves_all_original_positions_and_thresholds(self):
        old=(ROOT/'integration/continue_split_sequence.py').read_text()
        new=(ROOT/'integration/replay_slotted_sequence.py').read_text()
        self.assertTrue(new.endswith(old.replace('import split_root_cartridges_v9 as s','import stow_motion_slots as s')))
        def main(source):return ast.get_source_segment(source,next(node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef) and node.name=='main'))
        self.assertEqual(main((ROOT/'integration/replay_slotted_assembly.py').read_text()),main(Path(s.parent.__file__).read_text()).replace("HERE.parent/'inputs'/k","GROUP/'inputs'/k"))
