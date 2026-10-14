from pathlib import Path
import sys,unittest,ast
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
import stow_contact_slots as s
import cam_contact_native as n
from straight_envelope import whole_material

class NativeContactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows={side:s.build(side) for side in 'LR'}
    def test_original_material_and_root_bounds_retained(self):
        for original,new,rel,receipt,sweeps in self.rows.values():
            self.assertEqual(receipt['additional_original_material_removed_mm3'],0.)
            self.assertAlmostEqual(receipt['additional_V2_web_removed_mm3'],.00085750229716195,places=7)
            self.assertEqual(len(new.Solids()),1);self.assertFalse(receipt['dynamic_contact_friction_tolerance_or_strength_qualified'])
    def test_whole_STOP_stroke_rejects_V2_and_accepts_new(self):
        for side,(original,new,rel,receipt,sweeps) in self.rows.items():
            old=s.baseline.fixed_design(side)[1]
            for sweep in sweeps.values():
                self.assertGreater(n.common(old,sweep),.0004);self.assertEqual(n.common(new,sweep),0.)
    def test_all_four_complete_pin_paths_and_body_cages_clear_KEY(self):
        for side,(original,new,rel,receipt,sweeps) in self.rows.items():
            for i in range(2):
                p,pin,rest,raw=n.extract_profile(original['KEY'],original[f'STOP_{i}'],side)
                full,_=n.pin_path_envelope(p,side,*raw['pin_e_extent_mm']);self.assertEqual(n.common(full,original['KEY']),0.)
                cages=n.remainder_cages(rest,p,side);self.assertEqual(len(cages),3)
                self.assertTrue(all(n.common(c,original['KEY'])==0 for c,r in cages))
    def test_contact_enclosure_shift_into_floor_is_rejected(self):
        original=self.rows['L'][0];p,pin,rest,raw=n.extract_profile(original['KEY'],original['STOP_0'],'L')
        full,_=n.pin_path_envelope(p,'L',*raw['pin_e_extent_mm'])
        self.assertGreater(n.common(full.translate((0,0,-.001)),original['KEY']),1e-7)
    def test_changed_native_profile_is_not_silently_accepted(self):
        original=self.rows['L'][0]
        with self.assertRaises(ValueError):n.extract_profile(original['KEY'].translate((0,0,.01)),original['STOP_0'],'L')
    def test_no_state_following_root_and_no_unrelated_shape_change(self):
        for side,(original,new,rel,receipt,sweeps) in self.rows.items():
            changed=dict(original);changed.pop('KEY');changed['STOP_0']=changed['STOP_0'].translate((0,0,-.4))
            out,raw=s.repair_parts(changed,'STOW',side)
            self.assertTrue(out[s.ROOT_NAME].wrapped.IsSame(new.wrapped))
            self.assertTrue(all(out[k].wrapped.IsSame(v.wrapped) for k,v in changed.items() if k!=s.ROOT_NAME))
    def test_disabled_and_OPEN_keep_original_shapes(self):
        for side,(original,new,rel,receipt,sweeps) in self.rows.items():
            out,_=s.repair_parts(original,'STOW',side,enabled=False)
            self.assertTrue(all(out[k].wrapped.IsSame(v.wrapped) for k,v in original.items()))
            opened,_=s.parent.scene('OPEN',side);out,_=s.repair_parts(opened,'OPEN',side)
            self.assertTrue(all(out[k].wrapped.IsSame(v.wrapped) for k,v in opened.items()))
    def test_original_replays_not_weakened(self):
        for source,target in [('replay_continuous_sequence.py','replay_contact_sequence.py'),('replay_continuous_assembly.py','replay_contact_assembly.py'),('stow_installation_gate.py','contact_installation_gate.py')]:
            old=(ROOT/'integration'/source).read_text();new=(ROOT/'integration'/target).read_text()
            self.assertEqual(new,old.replace('import stow_continuous_slots_v2 as s','import stow_contact_slots as s'))
