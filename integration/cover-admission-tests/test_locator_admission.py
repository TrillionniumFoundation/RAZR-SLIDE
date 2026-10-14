import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
import cover_locator_slot as s
from admission_cells import translation_cells
from cover_admission_plan import fixture,stages
import cam_contact_native as n
from straight_envelope import whole_material

class LocatorAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old={side:s.base.scene('STOW',side)[0] for side in 'LR'}
        cls.new={side:s.design(side) for side in 'LR'}
    def test_exact_side_locator_window_and_single_solid(self):
        for side in 'LR':
            new=self.new[side][2];old=self.old[side]['OLD_COVER'];self.assertEqual(len(new.Solids()),1);self.assertAlmostEqual(old.Volume()-new.Volume(),.04416,places=7)
            self.assertEqual(whole_material(new.cut(old),empty=True)[1],0.)
    def test_old_bounds_and_other_window_material_retained(self):
        for side in 'LR':
            new=self.new[side][2];old=self.old[side]['OLD_COVER'];window=n.box(side,*self.new[side][4]['notch_eqr_mm'])
            self.assertEqual(whole_material(old.cut(new).cut(window),empty=True)[1],0.)
            self.assertTrue(all(abs(a-b)<1e-7 for x,y in zip(n.bounds(side,old),n.bounds(side,new)) for a,b in zip(x,y)))
    def test_locator_retention_change_not_claimed_qualified(self):
        for side in 'LR':
            report=self.new[side][4];self.assertTrue(report['original_locator_retention_boundary_changed']);self.assertTrue(report['locator_closing_keeper_not_designed']);self.assertFalse(report['load_capture_tolerance_or_phone_qualification'])
    def test_complete_inner_side_entry_clear_after_notch(self):
        for side in 'LR':
            cells,_=translation_cells(self.old[side]['ROOT_INNER'],(20 if side=='L' else -20,0,0));self.assertTrue(all(n.common(x,self.new[side][2])<=1e-7 for _,x in cells))
    def test_actual_closed_locator_negative_still_reproduces(self):
        for side in 'LR':
            moving=self.old[side]['ROOT_INNER'].translate((.05 if side=='L' else -.05,0,0))
            self.assertGreater(n.common(moving,self.old[side]['OLD_COVER']),1e-7);self.assertEqual(n.common(moving,self.new[side][2]),0.)
    def test_unparked_bottom_pawl_whole_path_clear(self):
        for side in 'LR':
            cells,_=translation_cells(self.old[side]['PAWL'],(0,0,-20));self.assertTrue(all(n.common(c,self.new[side][2])==0 for _,c in cells))
    def test_fixture_is_finite_two_valid_complete_parts(self):
        for side in 'LR':
            f=fixture(side);self.assertEqual(set(f),{'JIG_BASE_SUPPORTS','JIG_HOLD_DOWN'});self.assertTrue(all(len(n.single(x).Solids())==1 for x in f.values()))
    def test_old_key_motion_is_not_changed_or_widened(self):
        for side in 'LR':
            old=s.base.design(side);new=self.new[side];self.assertTrue(old[1].wrapped.IsSame(new[1].wrapped));self.assertTrue(old[5].wrapped.IsSame(new[5].wrapped));self.assertEqual(n.common(new[2],old[5]),0.)
    def test_plan_requires_cover_fixture_and_unparked_pawl_first(self):
        for side in 'LR':
            p=stages(side);self.assertEqual([x.part for x in p[:4]],['OLD_COVER','JIG_HOLD_DOWN','PAWL','PAWL']);self.assertEqual(p[2].end,p[3].start);self.assertEqual(p[-1].name,'OUTER_ROOT_CLOSE')
    def test_switch_preserves_baseline_and_OPEN(self):
        for side in 'LR':
            disabled,_=s.scene('STOW',side,enabled=False);self.assertEqual(whole_material(disabled['OLD_COVER'].cut(self.old[side]['OLD_COVER']),empty=True)[1],0.)
        with self.assertRaises(ValueError):s.scene('STOW','L',enabled=1)

    def test_pinned_native_part_set_complete(self):
        from admission_native_inputs import load_parts
        for side in 'LR':
            parts,ids=load_parts(side,original_closed_locator=True);self.assertEqual(len(parts),23);self.assertEqual(len(ids['native_part_identity']),23);self.assertFalse(ids['native_files_healed_or_rewritten'])
    def test_zero_pose_preserves_native_shape_and_outer_cells_valid(self):
        from admission_native_inputs import load_parts,at
        for side in 'LR':
            parts,_=load_parts(side);root=parts['ROOT_OUTER_CONNECTED_ALL_FRAGMENTS'];self.assertTrue(at(root,(0,0,0)).wrapped.IsSame(root.wrapped))
            cells,_=translation_cells(root,(-20 if side=='L' else 20,0,0));self.assertGreater(len(cells),2);self.assertTrue(all(x.isValid() and x.Volume()>0 for _,x in cells))
