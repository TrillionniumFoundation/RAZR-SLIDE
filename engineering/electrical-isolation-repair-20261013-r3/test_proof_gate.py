import itertools,json,unittest
from pathlib import Path
from proof_gate import ProofGate,disconnected_proof_voltage
class HardwarePermission(unittest.TestCase):
 def test_missing_proof_dominates_every_arm_and_sensor_combination(self):
  for pg,win,arm in itertools.product([False,True],repeat=3):
   self.assertFalse(ProofGate(True).sample(pg,win,False,arm)['EN_command'])
 def test_manual_arm_does_not_override_missing_proof(self):
  g=ProofGate();g.sample(True,True,False,False);self.assertFalse(g.sample(True,True,False,True)['EN_command'])
 def test_proof_loss_clears_previously_armed_latch(self):
  g=ProofGate();self.assertTrue(g.sample(True,True,True,True)['EN_command']);self.assertFalse(g.sample(True,True,False,True)['EN_command'])
 def test_proof_return_with_static_arm_does_not_restart(self):
  g=ProofGate();g.sample(True,True,True,True);g.sample(True,True,False,True);self.assertFalse(g.sample(True,True,True,True)['EN_command'])
 def test_new_edge_requires_good_window_and_supply_and_proof(self):
  for pg,win,proof in itertools.product([False,True],repeat=3):
   self.assertEqual(ProofGate().sample(pg,win,proof,True)['EN_command'],pg and win and proof)
 def test_reset_drops_stored_permission(self):
  g=ProofGate(True);g.reset();self.assertFalse(g.sample(True,True,True,False)['EN_command'])
 def test_actual_pin_map_has_three_separate_proof_gates(self):
  n=json.loads((Path(__file__).parent/'terminal_netlist.json').read_text());c={x['logical_ref']:x for x in n['components']}
  self.assertEqual(c['U_LATCH']['pins']['2']['net'],'PROBE_FRESH_OK')
  self.assertEqual(c['U_PROOF_CLEAR_AND']['pins']['2']['net'],'PROBE_FRESH_OK')
  self.assertEqual(c['U_PROOF_CLEAR_AND']['pins']['4']['net'],'CLEARn')
  self.assertEqual(c['U_PROOF_ENABLE_AND']['pins']['2']['net'],'PROBE_FRESH_OK')
  self.assertEqual(c['U_PROOF_ENABLE_AND']['pins']['4']['net'],'EN_DRV')
  self.assertFalse(n['continuity_proof_generation_implemented'])
 def test_fault_counterexample_stuck_high_proof_can_enable(self):
  # No false safety claim: the gate cannot distinguish a broken line from a
  # lying proof input. A diagnosed physical probe/watchdog is still required.
  self.assertTrue(ProofGate().sample(True,True,True,True)['EN_command'])
 def test_failures_just_after_diagnostic_remain_undetectable(self):
  g=ProofGate();g.sample(True,True,True,True)
  self.assertTrue(g.sample(True,True,True,False)['EN_command'])
 def test_unknown_values_not_defaulted(self):
  for v in [None,0,1,'true']:
   with self.assertRaises(ValueError):ProofGate().sample(True,True,v,True)
 def test_three_input_leakage_does_not_get_counted_as_one(self):
  self.assertAlmostEqual(disconnected_proof_voltage([5e-6]*3,1e4),.15)
  self.assertLess(disconnected_proof_voltage([5e-6]*3,1e4),.8)
 def test_rejected_100k_pull_down_loses_low_level_margin(self):
  self.assertGreater(disconnected_proof_voltage([5e-6]*3,1e5),.8)
if __name__=='__main__':unittest.main(verbosity=2)
