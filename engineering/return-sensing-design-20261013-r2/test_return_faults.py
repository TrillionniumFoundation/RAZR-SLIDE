import json, math, unittest
from pathlib import Path
from simulate_return_faults import HardwareLatch, amp_outputs, phantom_feed, return_split, threshold_interval, pgood_dc

class CircuitCounterexamples(unittest.TestCase):
 def test_parallel_reference_is_live_even_charger_positive_off(self):
  r=return_split(3.,{'main_N':.03,'charge_ground':.2});self.assertAlmostEqual(r['branch_A']['charge_ground'],.391304347826087)
 def test_alternate_ground_takes_entire_open_main_return(self):
  r=return_split(3.,{'main_N':None,'charge_ground':.2});self.assertEqual(r['branch_A']['main_N'],0.);self.assertEqual(r['branch_A']['charge_ground'],3.)
 def test_aggregate_sensor_cannot_detect_redistribution(self):
  r=return_split(3.,{'main_N':None,'charge_ground':.2});self.assertEqual(3.-sum(r['branch_A'].values()),0.)
 def test_return_open_without_any_alternate_is_not_forced_current(self):
  r=return_split(3.,{'main_N':None,'charge_ground':None});self.assertFalse(r['model_current_realizable']);self.assertIsNone(r['return_voltage_B_minus_A_V'])
 def test_signed_current_not_abs_before_amplifier(self):
  r=amp_outputs(-3.,-2.);self.assertAlmostEqual(r['difference_V'],1.45)
 def test_shunt_location_reference_and_package_are_exact(self):
  n=json.loads((Path(__file__).parent/'terminal_netlist.json').read_text());cs={c.get('logical_ref',c['ref']):c for c in n['components']}
  self.assertEqual(cs['U_N']['pins']['2']['net'],'A_RETURN_HARNESS');self.assertEqual(cs['U_N']['pins']['3']['net'],'A_PACK_N')
  self.assertEqual(cs['U_P']['pins']['2']['net'],'A_CUT_OUT');self.assertEqual(cs['U_P']['pins']['3']['net'],'A_TX_P')
  self.assertEqual(cs['U_DIFF']['pins']['1']['name'],'OUT');self.assertEqual(cs['U_DIFF']['pins']['4']['name'],'-IN')
 def test_healthy_and_fault_envelopes_overlap(self):self.assertFalse(threshold_interval([4.8076923077],[1.],.1,.05)['threshold_exists'])
 def test_narrow_conditional_example_separates(self):self.assertTrue(threshold_interval([.3913043478],[3.],.1,.05)['threshold_exists'])
 def test_zero_load_never_detects_open_by_current(self):self.assertFalse(threshold_interval([0.],[0.],0.,0.)['threshold_exists'])
 def test_missing_inputs_not_defaulted(self):self.assertIsNone(threshold_interval(None,None,None,None)['threshold_exists'])
 def test_current_and_resistance_invalid_inputs_rejected(self):
  for bad in [math.nan,math.inf,True]:
   with self.assertRaises(ValueError):return_split(bad,{'a':1.})
  for bad in [0.,-1.,math.nan,True]:
   with self.assertRaises(ValueError):return_split(1.,{'a':bad})
 def test_fault_dominates_simultaneous_arm(self):
  l=HardwareLatch();self.assertFalse(l.sample(True,False,True,True)['U_A2_enable_command'])
 def test_static_arm_does_not_retry_after_fault_clears(self):
  l=HardwareLatch();l.sample(True,True,True,False);self.assertTrue(l.sample(True,True,True,True)['U_A2_enable_command']);l.sample(True,False,True,True)
  self.assertFalse(l.sample(True,True,True,True)['U_A2_enable_command'])
 def test_power_good_drop_dominates_Q(self):
  l=HardwareLatch(True);self.assertFalse(l.sample(False,True,True,False)['U_A2_enable_command'])
 def test_broken_high_ok_wire_defaults_low(self):self.assertFalse(HardwareLatch(True).sample(True,False,True,False)['U_A2_enable_command'])
 def test_new_manual_edge_can_rearm_and_is_not_repair_proof(self):
  l=HardwareLatch();l.sample(True,False,True,True);l.sample(True,True,True,False);self.assertTrue(l.sample(True,True,True,True)['U_A2_enable_command'])
 def test_off_cut_phantom_feed_not_zero_voltage(self):
  r=phantom_feed(5.,.3,1000.,100000.,1e-4,0.,1.);self.assertAlmostEqual(r['equilibrium_V'],4.653465346534653);self.assertGreater(r['stored_energy_at_equilibrium_J'],.001)
 def test_saturation_reported_not_linear_certified(self):self.assertFalse(amp_outputs(20.,0.)['within_INA240_documented_gain_test_headroom'])
 def test_PCB_bypass_tests_target_each_actual_hazard_node(self):
  import importlib.util
  p=Path(__file__).resolve().parent.parent/'power-usb-design-20261013';s=importlib.util.spec_from_file_location('baseline_review_test',p/'design_review.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
  n=json.loads((p/'candidate_netlist.json').read_text())
  for x,c,h in [('raw_A_to_harness','A','A_TX_P'),('raw_B_to_harness','B','A_RX_P'),('system_bus_to_harness','B','A_RX_P')]:
   self.assertTrue(m.cell_load_loop(n,['A_PACK_PROTECT','B_PACK_PROTECT','U_B1','U_B2'],faults=[x],cabin=c,positive=h)['conductive_loop_exists'])
 def test_PGOOD_static_shared_input_leakage_default_low(self):
  r=pgood_dc(3.3,2200.,10000.,1e-5);self.assertLess(r['broken_driven_connection_max_V'],.8);self.assertGreater(r['healthy_high_V'],2.0);self.assertLess(r['supervisor_max_pullup_sink_A'],.002)
 def test_REJECTED_weak_pull_down_not_false_safe_for_two_inputs(self):
  r=pgood_dc(3.3,10000.,100000.,1e-5);self.assertGreater(r['broken_driven_connection_max_V'],.8)
 def test_REJECTED_equal_PGOOD_pullup_pulldown_loses_VIH(self):
  r=pgood_dc(3.3,10000.,10000.,1e-5);self.assertLess(r['healthy_high_V'],2.0)

if __name__=='__main__':unittest.main(verbosity=2)
