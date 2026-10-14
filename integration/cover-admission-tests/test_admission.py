from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
import cover_admission as s
import cam_contact_native as n
from translation_regions import regions,checks

class AdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.d={side:s.design(side) for side in 'LR'}
    def test_cover_is_complete_single_solid_not_largest_fragment(self):
        for _,_,cover,_,r,_,cut in self.d.values():
            self.assertEqual(len(n.single(cover).Solids()),1);self.assertTrue(r['no_largest_fragment_selection'])
            self.assertEqual(len(n.whole_material(cut)[0]),2)
    def test_declared_tongue_removal_not_hidden(self):
        for _,_,_,_,r,_,_ in self.d.values():
            self.assertAlmostEqual(r['former_tongue_removal_mm3'],.2424,places=7)
            self.assertFalse(r['original_closed_locator_holes_preserved'])
    def test_bench_growth_and_phone_unknown_are_explicit(self):
        for _,_,_,_,r,_,_ in self.d.values():
            self.assertEqual(r['qmax_bench_growth_mm'],3.5);self.assertEqual(r['phone_cavity_fit'],'unknown')
            self.assertAlmostEqual(r['after_cover_bounds_eqr_mm'][1][1],12.5,places=7)
            self.assertFalse(r['candidate_go']);self.assertFalse(r['manufacturing_go'])
    def test_material_balance_matches_whole_payload(self):
        for _,_,cover,_,r,_,_ in self.d.values():
            self.assertAlmostEqual(r['source_cover_volume_mm3']+r['new_added_mm3']-r['source_original_removed_mm3'],cover.Volume(),places=7)
    def test_KEY_full_enclosure_stays_clear(self):
        for _,_,cover,_,r,key,_ in self.d.values():self.assertEqual(n.common(cover,key),0.)
    def test_root_geometry_identity_is_unchanged(self):
        for side,(_,root,_,_,r,_,_) in self.d.items():
            self.assertTrue(root.wrapped.IsSame(s.native_base(side)[0][s.ROOT_NAME].wrapped))
    def test_whole_lateral_paths_clear_new_cover(self):
        for side,(old,root,cover,_,r,_,_) in self.d.items():
            ex=-1 if side=='L' else 1
            for sh,v in [(old['ROOT_INNER'],(-ex*10,0,0)),(root,(ex*10,0,0))]:
                rr,_=regions(sh,v);self.assertTrue(checks(rr,cover)['all_regions_clear'])
                self.assertFalse(checks(rr,s.prior.design(side)[2])['all_regions_clear'])
    def test_no_runtime_adaptive_geometry_and_no_other_change(self):
        for side,(old,root,cover,_,r,_,_) in self.d.items():
            p,_=s.prior.scene('STOW',side);p.pop('KEY');p['STOP_0']=p['STOP_0'].translate((0,0,-.4))
            out,_=s.repair_parts(p,'STOW',side)
            self.assertTrue(out['OLD_COVER'].wrapped.IsSame(cover.wrapped))
            self.assertTrue(all(out[k].wrapped.IsSame(v.wrapped) for k,v in p.items() if k!='OLD_COVER'))
    def test_disable_OPEN_and_bad_inputs(self):
        for side in 'LR':
            p,_=s.prior.scene('STOW',side);out,_=s.repair_parts(p,'STOW',side,enabled=False)
            self.assertTrue(all(out[k].wrapped.IsSame(v.wrapped) for k,v in p.items()))
        with self.assertRaises(ValueError):s.repair_parts(p,'STOW','L',enabled=1)
    def test_regression_drivers_only_import_differs(self):
        for a,b in [('keycover_motion_gate.py','admission_motion_gate.py'),('replay_keycover_sequence.py','replay_admission_sequence.py'),('replay_keycover_assembly.py','replay_admission_assembly.py')]:
            self.assertEqual((ROOT/'integration'/b).read_text(),(ROOT/'integration'/a).read_text().replace('import keycover_bypass as s','import cover_admission as s'))
