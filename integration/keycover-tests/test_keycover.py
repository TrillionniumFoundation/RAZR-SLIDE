from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
import keycover_bypass as s
import cam_contact_native as n
from straight_envelope import whole_material

class KeyCoverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.c={side:s.design(side) for side in 'LR'}
    def test_actual_KEY_subset_separates_old_cover_box(self):
        for original,root,cover,rel,r,sweep,free in self.c.values():
            p=r['native_subset_separation_proof'];self.assertTrue(p['native_KEY_subset_not_conservative_carrier']);self.assertEqual(p['free_components'],2)
            self.assertGreater(p['free_region_min_distance_mm'],1e-7);self.assertTrue(all(v['outside_native_KEY_mm3']==0 for v in p['source_subset_checks']))
    def test_only_cutting_cover_remains_two_complete_components(self):
        for original,root,cover,rel,r,sweep,free in self.c.values():self.assertEqual(len(whole_material(original['OLD_COVER'].cut(sweep))[0]),2)
    def test_two_repaired_parts_remain_single_solids(self):
        for original,root,cover,rel,r,sweep,free in self.c.values():self.assertEqual(len(n.single(root).Solids()),1);self.assertEqual(len(n.single(cover).Solids()),1)
    def test_original_cover_material_outside_KEY_motion_retained(self):
        for original,root,cover,rel,r,sweep,free in self.c.values():
            self.assertEqual(whole_material(original['OLD_COVER'].cut(cover).cut(sweep),empty=True)[1],0.)
            self.assertAlmostEqual(r['cover_original_removed_mm3'],.048,places=7);self.assertAlmostEqual(r['cover_added_mm3'],1.848,places=7)
    def test_cover_original_lower_plates_holes_unchanged(self):
        for side,(original,root,cover,rel,r,sweep,free) in self.c.items():
            eb,qb,rb=n.bounds(side,original['OLD_COVER']);zone=n.box(side,eb[0]-.01,eb[1]+.01,qb[0]-.01,qb[1]+.01,rb[0]-.01,-6.4)
            self.assertEqual(whole_material(original['OLD_COVER'].cut(cover).intersect(zone),empty=True)[1],0.)
            self.assertEqual(whole_material(cover.cut(original['OLD_COVER']).intersect(zone),empty=True)[1],0.)
    def test_cover_growth_explicit_but_bench_envelope_unchanged(self):
        for original,root,cover,rel,r,sweep,free in self.c.values():
            self.assertEqual(r['cover_local_q_min_extension_mm'],2.1);self.assertAlmostEqual(r['cover_part_bounds_after_eqr_mm'][1][0],-.4)
            self.assertTrue(all(abs(x)<1e-7 for x in r['whole_bench_bounds_delta_mm'].values()));self.assertTrue(r['actual_finished_phone_cavity_clearance_unknown'])
    def test_root_channel_uses_no_additional_v9_material(self):
        for original,root,cover,rel,r,sweep,free in self.c.values():self.assertEqual(r['extra_original_v9_root_removed_mm3'],0.);self.assertAlmostEqual(r['root_KEY_channel_removed_mm3'],.026,places=7)
    def test_old_actual_pose_failures_still_reproduce_and_new_clear(self):
        for side,(original,root,cover,rel,r,sweep,free) in self.c.items():
            oldroot=s.base.build(side)[1]
            for q,new,old in [(5.,cover,original['OLD_COVER']),(2.5,root,oldroot),(3.,root,oldroot)]:
                key=original['KEY'].translate((0,-q,0));self.assertGreater(n.common(key,old),1e-7);self.assertEqual(n.common(key,new),0.)
    def test_full_KEY_motion_clear_not_only_old_samples(self):
        for original,root,cover,rel,r,sweep,free in self.c.values():self.assertEqual(n.common(root,sweep),0.);self.assertEqual(n.common(cover,sweep),0.)
    def test_runtime_pose_does_not_recut_and_other_parts_unchanged(self):
        for side,(original,root,cover,rel,r,sweep,free) in self.c.items():
            source=dict(original);source.pop('KEY');source['STOP_0']=source['STOP_0'].translate((0,0,-.3));out,_=s.repair_parts(source,'STOW',side)
            self.assertTrue(out['OLD_COVER'].wrapped.IsSame(cover.wrapped));self.assertTrue(out[s.ROOT_NAME].wrapped.IsSame(root.wrapped))
            self.assertTrue(all(out[k].wrapped.IsSame(v.wrapped) for k,v in source.items() if k not in (s.ROOT_NAME,'OLD_COVER')))
    def test_disable_OPEN_and_wrong_original_identity(self):
        for side,(original,root,cover,rel,r,sweep,free) in self.c.items():
            out,_=s.repair_parts(original,'STOW',side,enabled=False);self.assertTrue(all(out[k].wrapped.IsSame(v.wrapped) for k,v in original.items()))
            opened,_=s.parent.scene('OPEN',side);out,_=s.repair_parts(opened,'OPEN',side);self.assertTrue(all(out[k].wrapped.IsSame(v.wrapped) for k,v in opened.items()))
        bad=dict(self.c['L'][0]);bad['OLD_COVER']=bad['OLD_COVER'].translate((.1,0,0))
        with self.assertRaises(ValueError):s.repair_parts(bad,'STOW','L')
    def test_original_drivers_only_scene_import_changed(self):
        for a,b in [('contact_motion_gate.py','keycover_motion_gate.py'),('replay_contact_sequence.py','replay_keycover_sequence.py'),('replay_contact_assembly.py','replay_keycover_assembly.py'),('contact_installation_gate.py','keycover_installation_gate.py')]:
            expected=(ROOT/'integration'/a).read_text().replace('import stow_contact_slots as s','import keycover_bypass as s')
            # Geometry operations, sample positions and thresholds unchanged;
            # only scene selection and serialized metadata scope are updated.
            if b=='keycover_motion_gate.py':expected=expected.replace(';v2=s.baseline.fixed_design(side)[1]',';audit=s.design(side)[4];v2=s.baseline.fixed_design(side)[1]')
            if b=='keycover_installation_gate.py':expected=expected.replace("'construction':construction,","'construction':s.design(side)[4],").replace("'all_original_non_root_parts_unchanged':True","'all_original_non_root_parts_unchanged':False,'unchanged_except_outer_root_and_cover':True")
            self.assertEqual((ROOT/'integration'/b).read_text(),expected)
