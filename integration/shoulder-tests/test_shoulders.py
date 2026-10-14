from pathlib import Path
import sys, unittest, math
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
import shoulder_clearance as s

class ShoulderTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.fixed={side:s.fixed_geometry(side) for side in 'LR'}
 def test_original_R4_stop_material_is_retained(self):
  old,_=s.b.source('STOW')
  for side,(parts,report) in self.fixed.items():
   for i in (0,1):
    original=old[side]['STOP_'+str(i)].translate((0,0,-.06))
    self.assertLessEqual(s.material_volume(original.cut(parts['STOP_'+str(i)])),1e-7)
 def test_roots_and_stops_are_whole_positive_single_solids(self):
  for parts,report in self.fixed.values():
   for name in ('STOP_0','STOP_1',s.ROOT_NAME):
    self.assertEqual(len(parts[name].Solids()),1);s.b.participant(parts[name])
 def test_old_insertion_failure_and_new_clearance(self):
  for side,(parts,report) in self.fixed.items():
   old,_=s.previous.scene('STOW',side);_,returned,insertion,_=s.canonical_envelopes(side)
   for i in (0,1):
    name='STOP_'+str(i)
    self.assertGreater(s.b.strict_common(old[name],insertion)['checked_volume_mm3'],1e-7)
    self.assertEqual(s.b.strict_common(parts[name],insertion)['checked_volume_mm3'],0.)
    self.assertEqual(s.b.strict_common(parts[name],returned)['checked_volume_mm3'],0.)
 def test_other_parts_preserved_and_no_strength_claim(self):
  for side,(parts,report) in self.fixed.items():
   old,_=s.previous.scene('STOW',side)
   for name in old:
    if name in ('STOP_0','STOP_1',s.ROOT_NAME):continue
    self.assertLessEqual(s.material_volume(old[name].cut(parts[name])),1e-7)
    self.assertLessEqual(s.material_volume(parts[name].cut(old[name])),1e-7)
   self.assertFalse(report['mechanical_load_path_strength_qualified'])
   self.assertFalse(report['manufacturing_go'])
 def test_fixed_root_reused_for_motion_states(self):
  for side in 'LR':
   a=s.fixed_geometry(side);b=s.fixed_geometry(side)
   self.assertIs(a,b)
   self.assertTrue(a[1]['root_is_fixed_across_all_lift_key_states'])
   self.assertLessEqual(a[1]['root_removed_outside_declared_grooves_mm3'],1e-7)
 def test_invalid_states_fail_before_geometry(self):
  for args in [('BAD','L',1.),('STOW','?',1.),('STOW','L',math.nan),('STOW','L',2.)]:
   with self.assertRaises(ValueError):s.scene(*args)
