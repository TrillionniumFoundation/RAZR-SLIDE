import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'integration'))
import stow_web_repair as repair
b=repair.b


class StowWebRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original={side:repair.parent.scene('STOW',side)[0] for side in 'LR'}
        cls.fixed={side:repair.repair_parts(p,'STOW',side) for side,p in cls.original.items()}
        cls.sweeps={side:repair.planar_translation_sweep(p['PAWL'],b.identity.evec('STOW',side,1.1))[0] for side,p in cls.original.items()}

    def test_disabling_patch_keeps_exact_original_shape_identities(self):
        for side,p in self.original.items():
            q,report=repair.repair_parts(p,'STOW',side,enabled=False)
            self.assertEqual(report['changed_parts'],[])
            self.assertTrue(all(q[k].wrapped.IsSame(v.wrapped) for k,v in p.items()))

    def test_OPEN_is_not_modified(self):
        for side in 'LR':
            p,_=repair.parent.scene('OPEN',side)
            q,report=repair.repair_parts(p,'OPEN',side)
            self.assertEqual(report['changed_parts'],[])
            self.assertTrue(all(q[k].wrapped.IsSame(v.wrapped) for k,v in p.items()))

    def test_only_outer_root_is_modified_and_remains_one_solid(self):
        for side,(q,report) in self.fixed.items():
            p=self.original[side]
            self.assertEqual(set(p),set(q));self.assertEqual(report['changed_parts'],[repair.ROOT_NAME])
            for k in p:
                if k!=repair.ROOT_NAME:self.assertTrue(p[k].wrapped.IsSame(q[k].wrapped))
            self.assertEqual(len(q[repair.ROOT_NAME].Solids()),1)
            b.participant(q[repair.ROOT_NAME])

    def test_envelope_and_material_accounting_are_preserved(self):
        for q,report in self.fixed.values():
            self.assertLess(max(abs(v) for v in report['bounds_delta_mm'].values()),1e-7)
            self.assertAlmostEqual(report['old_volume_mm3']+report['added_material_mm3']-report['removed_material_mm3'],report['new_volume_mm3'],places=7)
            self.assertTrue(report['all_material_outside_declared_motion_envelopes_retained'])
            self.assertFalse(report['mechanical_strength_qualified'])

    def test_removed_volume_is_only_the_two_declared_motion_interferences(self):
        for side,(q,report) in self.fixed.items():
            old=self.original[side][repair.ROOT_NAME]
            _,returned,insertion,_=repair.canonical_envelopes(side)
            residue=old.cut(q[repair.ROOT_NAME]).cut(returned).cut(insertion)
            self.assertLessEqual(sum(repair.volume_leaves(residue)),1e-7)
            self.assertLess(report['removed_material_mm3'],.03)

    def test_cut_only_negative_control_splits_root_into_three(self):
        for side,p in self.original.items():
            candidate=p[repair.ROOT_NAME]
            windows,_=repair.modification_geometry('STOW',side)
            for window in windows:candidate=candidate.cut(window).clean()
            self.assertEqual(len(candidate.Solids()),3)
            with self.assertRaises(ValueError):b.participant(candidate)

    def test_missing_high_ties_negative_control_splits_root_into_two(self):
        for side,p in self.original.items():
            windows,bridges=repair.modification_geometry('STOW',side)
            candidate=b.fuse([p[repair.ROOT_NAME],*[z for i,z in enumerate(bridges) if i%3!=2]])
            for window in windows:candidate=candidate.cut(window).clean()
            self.assertEqual(len(candidate.Solids()),2)
            with self.assertRaises(ValueError):b.participant(candidate)

    def test_full_translation_envelope_rejects_old_and_accepts_repaired_root(self):
        for side,(q,_) in self.fixed.items():
            old=b.strict_common(self.original[side][repair.ROOT_NAME],self.sweeps[side])
            new=b.strict_common(q[repair.ROOT_NAME],self.sweeps[side])
            self.assertGreater(old['checked_volume_mm3'],.003)
            self.assertEqual(new['checked_volume_mm3'],0.)
            self.assertTrue(new['OCC_boolean_was_run'])
            positives=0
            for i in range(23):
                pawn=self.original[side]['PAWL'].translate(b.identity.evec('STOW',side,1.1*i/22))
                positives += b.strict_common(self.original[side][repair.ROOT_NAME],pawn)['checked_volume_mm3']>b.EPS
                self.assertEqual(b.strict_common(q[repair.ROOT_NAME],pawn)['checked_volume_mm3'],0.)
            self.assertEqual(positives,9)


    def test_box_sweeps_match_analytical_volume_in_both_directions(self):
        cube=b.cq.Solid.makeBox(1,1,1)
        for vector in [(1.,0.,0.),(-1.,0.,0.),(0.,2.,0.),(0.,0.,-2.)]:
            swept,report=repair.planar_translation_sweep(cube,vector)
            self.assertAlmostEqual(swept.Volume(),1+sum(abs(v) for v in vector),places=8)
            self.assertFalse(report['is_discrete_pose_union'])

    def test_concave_sweep_matches_independent_rectangular_union(self):
        shape=b.fuse([b.cq.Solid.makeBox(2,1,1),b.cq.Solid.makeBox(1,2,1)])
        swept,_=repair.planar_translation_sweep(shape,(.5,0,0))
        expected=b.fuse([b.cq.Solid.makeBox(2.5,1,1),b.cq.Solid.makeBox(1.5,2,1)])
        self.assertAlmostEqual(swept.Volume(),4.,places=8)
        self.assertLessEqual(sum(repair.volume_leaves(swept.cut(expected))),1e-7)
        self.assertLessEqual(sum(repair.volume_leaves(expected.cut(swept))),1e-7)

    def test_curved_boundary_is_rejected_not_bounding_box_approximated(self):
        with self.assertRaises(ValueError):repair.planar_translation_sweep(b.cq.Solid.makeCylinder(1,2),(1,0,0))

    def test_zero_or_nonfinite_translation_is_rejected(self):
        cube=b.cq.Solid.makeBox(1,1,1)
        for v in [(0,0,0),(math.nan,0,0),(math.inf,0,0)]:
            with self.subTest(vector=v),self.assertRaises((ValueError,RuntimeError)):repair.planar_translation_sweep(cube,v)

    def test_invalid_scene_identity_or_switch_is_rejected(self):
        for args in [('STOW','X',True),('UNKNOWN','L',True),('STOW','L',1)]:
            with self.subTest(args=args),self.assertRaises(ValueError):repair.repair_parts(self.original['L'],args[0],args[1],enabled=args[2])

    def test_564_sequence_and_184_assembly_preserve_original_checks(self):
        old=(ROOT/'integration/continue_split_sequence.py').read_text()
        new=(ROOT/'integration/replay_stow_sequence.py').read_text()
        self.assertTrue(new.endswith(old.replace('import split_root_cartridges_v9 as s','import stow_web_repair as s')))
        old=Path(repair.parent.__file__).read_text();new=(ROOT/'integration/replay_stow_assembly.py').read_text()
        def main(src):return ast.get_source_segment(src,next(n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='main'))
        self.assertEqual(main(new),main(old).replace("HERE.parent/'inputs'/k","GROUP/'inputs'/k"))

    def test_all_frozen_spring_snapshot_files_remain_exact(self):
        snapshot=json.loads((repair.GROUP/'stable-snapshot.json').read_text())
        for row in snapshot['files']:
            with self.subTest(path=row['path']):
                self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),row['sha256'])

    def test_full_parked_insertion_envelope_rejects_old_not_candidate(self):
        for side,(q,_) in self.fixed.items():
            _,_,insertion,_=repair.canonical_envelopes(side)
            self.assertGreater(b.strict_common(self.original[side][repair.ROOT_NAME],insertion)['checked_volume_mm3'],.01)
            self.assertEqual(b.strict_common(q[repair.ROOT_NAME],insertion)['checked_volume_mm3'],0.)

    def test_actual_sweep_cuts_without_side_web_remain_disconnected(self):
        for side,p in self.original.items():
            _,returned,insertion,_=repair.canonical_envelopes(side)
            unconnected=p[repair.ROOT_NAME].cut(returned).cut(insertion).clean()
            self.assertGreater(len(unconnected.Solids()),1)
            with self.assertRaises(ValueError):b.participant(unconnected)

    def test_root_geometry_does_not_change_with_simulated_lift_or_key_state(self):
        for side,p in self.original.items():
            varied=dict(p);varied.pop('KEY');varied['STOP_0']=varied['STOP_0'].translate(b.rvec('STOW',-.5))
            q,report=repair.repair_parts(varied,'STOW',side)
            expected=self.fixed[side][0][repair.ROOT_NAME]
            self.assertAlmostEqual(q[repair.ROOT_NAME].Volume(),expected.Volume(),places=7)
            self.assertLessEqual(sum(repair.volume_leaves(q[repair.ROOT_NAME].cut(expected))),1e-7)
            self.assertTrue(report['root_not_recut_for_actual_lift_or_key_state'])
            self.assertTrue(q['STOP_0'].wrapped.IsSame(varied['STOP_0'].wrapped))
