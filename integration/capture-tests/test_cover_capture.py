from pathlib import Path
import sys,unittest,math
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'integration'))
import cover_capture as c
from translation_regions import regions,checks

class CoverCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.designs={side:c.build(side) for side in 'LR'}
    def test_all_root_material_preserved(self):
        for side,(old,new,rows) in self.designs.items():
            for row in rows:
                self.assertEqual(row['old_material_removed_mm3'],0.)
                self.assertGreater(row['positive_joint_overlap_mm3'] if 'positive_joint_overlap_mm3' in row else row['joint_overlap_mm3'],0.)
    def test_complete_positive_roots_not_fragment_selection(self):
        for old,new,rows in self.designs.values():
            for name in c.ROOT_NAMES:self.assertEqual(len(c.n.single(new[name]).Solids()),1)
    def test_no_extra_external_space(self):
        for old,new,rows in self.designs.values():
            for row in rows:self.assertTrue(all(abs(v)<1e-7 for v in row['bounds_delta_mm'].values()))
    def test_nonroot_parts_unchanged(self):
        for old,new,rows in self.designs.values():self.assertTrue(all(new[k].wrapped.IsSame(old[k].wrapped) for k in old if k not in c.ROOT_NAMES))
    def test_actual_nominal_anti_lift_contacts(self):
        for side in 'LR':
            self.assertTrue(all(v>1e-7 for v in c.positive_uplift(side,.05).values()))
            self.assertTrue(all(v==0 for v in c.positive_uplift(side,.019).values()))
    def test_disabled_reference_retains_old_failure(self):
        for side in 'LR':self.assertTrue(all(v==0 for v in c.positive_uplift(side,.05,False).values()))
    def test_whole_old_1mm_upward_path_clear(self):
        for old,new,rows in self.designs.values():
            rr,_=regions(old['OLD_COVER'],(0,0,1))
            self.assertTrue(all(checks(rr,v)['all_regions_clear'] for k,v in old.items() if k!='OLD_COVER'))
    def test_floating_lip_cannot_be_accepted_as_root(self):
        old=self.designs['L'][0]['ROOT_INNER'];lip=c.n.box('L',-3.3,-2.2,6.5,7.,-6.42,-6.22)
        with self.assertRaises(ValueError):c.n.single(old.fuse(lip).clean())
    def test_bad_inputs_rejected(self):
        for side in ['X','',None]:
            with self.assertRaises(ValueError):c.baseline(side)
        for d in [float('nan'),float('inf'),True,-1.,1.1]:
            with self.assertRaises(ValueError):c.positive_uplift('L',d)
    def test_full_KEY_and_STOP_motion_clear_of_new_material(self):
        for side in 'LR':
            for name in c.ROOT_NAMES:
                channel=c.channel(side,name)
                for role in ['KEY_COMPLETE_Q','STOP_0_COMPLETE_R','STOP_1_COMPLETE_R']:
                    self.assertEqual(c.n.common(channel,c.read_shape('motion/'+side+'_'+role+'.step')),0.)
