#!/usr/bin/env python3
"""R79 *research* test suite: positive numerical checks AND negative safety gates."""
from __future__ import annotations
import csv,hashlib,json,math,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import r79_accel_robust as m

class R79HardgateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.r=json.loads((ROOT/'results/R79_results.json').read_text())
  cls.hp=json.loads((ROOT/'results/R79_independent_90digit.json').read_text())
  with (ROOT/'results/R79_C1_piecewise_quadratic_witness.csv').open(newline='') as fh:
   cls.sched=list(csv.DictReader(fh))

 def test_01_R78_pin_sha(self):self.assertEqual(m.PARENT_SHA['R78'],'7f6cc2be3f0bd08879b39db48ef85b292a43b344947b932ea2aeb21512f7ea52')
 def test_02_R77_ancestor_distinct(self):self.assertNotEqual(m.PARENT_SHA['R77'],m.PARENT_SHA['R78'])
 def test_03_R76_ancestor_distinct(self):self.assertNotEqual(m.PARENT_SHA['R76'],m.PARENT_SHA['R77'])
 def test_04_R78_optimum_matches_independent(self):self.assertAlmostEqual(m.r78_stationary()[1],.9277021685718772,places=12)
 def test_05_safe_mode_delayed(self):self.assertGreater(m.gate(),m.Y-math.sqrt(m.D*m.D-m.Z*m.Z))
 def test_06_terminal_stationary_unique_on_right(self):
  p=m.endpoint_minimum_acceleration();s=p['critical_s_mm'];self.assertTrue(m.Y<s<m.T);self.assertAlmostEqual(p['stationarity_residual'],0,delta=1e-11)
 def test_07_terminal_necessary_A_positive(self):self.assertAlmostEqual(m.endpoint_minimum_acceleration()['minimal_A_necessary_mm_per_mm2'],0.18798387608105406,places=11)
 def test_08_terminal_A0p18_fails_irrespective_peak_speed(self):self.assertLess(.18,m.endpoint_minimum_acceleration()['minimal_A_necessary_mm_per_mm2'])
 def test_09_endpoint_bound_independent_sample_pairs(self):
  A=m.endpoint_minimum_acceleration()['minimal_A_necessary_mm_per_mm2']
  for s in [56.,63.,70.,73.27,75.,78.]:
   bound=2*(m.lower(m.T)-m.upper(s))/(m.T-s)**2
   self.assertLessEqual(bound,A+1e-10)
 def test_10_start_rest_kstar_fails_finite_acc(self):
  sm,k=m.r78_stationary();A=.3;delta=m.lower(0)-m.upper(sm)
  max_drop=k*sm-k*k/(2*A)
  self.assertLess(max_drop,delta)
 def test_11_start_pair_bound_stronger_than_R78_k(self):self.assertGreater(m.start_rate_lower(.3)['minimum_k_pair_mm_per_mm'],m.r78_stationary()[1])
 def test_12_A0p3_start_nec_near_expected(self):self.assertAlmostEqual(m.start_rate_lower(.3)['minimum_k_pair_mm_per_mm'],.96440126350247,places=9)
 def test_13_k0p95_rejected_by_necessary_bound(self):self.assertLess(.95,m.start_rate_lower(.3)['minimum_k_pair_mm_per_mm'])
 def test_14_constructed_k_not_claimed_optimal(self):self.assertTrue(self.r['example_software_only']['nonoptimal_existence_witness_only'])
 def test_15_full_witness_has_many_nodes(self):self.assertGreaterEqual(len(self.sched),800)
 def test_16_start_stop_rest(self):
  self.assertAlmostEqual(float(self.sched[0]['derivative_dF_d_s']),0,delta=1e-12)
  self.assertAlmostEqual(float(self.sched[-1]['derivative_dF_d_s']),0,delta=1e-12)
 def test_17_continuum_lower_certificate_strict(self):self.assertGreater(self.r['example_software_only']['continuum_slide_LOWER_min_certified_mm'],0)
 def test_18_continuum_upper_certificate_strict(self):self.assertGreater(self.r['example_software_only']['continuum_slide_UPPER_min_certified_mm'],0)
 def test_19_acc_within_hypothetical(self):self.assertLessEqual(self.r['example_software_only']['maximum_abs_a'],.300000001)
 def test_20_speed_within_hypothetical(self):self.assertLessEqual(self.r['example_software_only']['maximum_abs_v'],.980000001)
 def test_21_interval_bound_works_all_dock(self):
  F=float(self.sched[-1]['F_free_mm'])
  for i in range(101):
   q=m.Q*i/100;self.assertGreaterEqual(F+1e-8,m.lower(m.T,q));self.assertLessEqual(F-1e-8,m.upper(m.T,q))
 def test_22_90digit_source_independent(self):self.assertTrue(self.hp['standalone_no_R79_import'])
 def test_23_90digit_independent_recurrence(self):self.assertLess(float(self.hp['witness_check']['max_node_recurrence_residual']),1e-10)
 def test_24_90digit_terminal_necessary(self):self.assertAlmostEqual(float(self.hp['R79_terminal_acceleration_A_nec']),m.endpoint_minimum_acceleration()['minimal_A_necessary_mm_per_mm2'],places=12)
 def test_25_90digit_start_necessary(self):self.assertAlmostEqual(float(self.hp['R79_start_pair_k_nec_A0p3']),m.start_rate_lower(.3)['minimum_k_pair_mm_per_mm'],places=11)
 def test_26_no_OEM_permission_or_CAD_claims(self):self.assertIs(self.r['CAD_modify_go'],False)
 def test_27_no_manufacturing_claim(self):self.assertIs(self.r['manufacturing_go'],False)
 def test_28_no_new_three_dimensional_FPC(self):self.assertEqual(self.r['real_FPC_copper_3D_OCC_swaps'],0)
 def test_29_no_supplier_or_real_USB_evidence(self):self.assertEqual(self.r['new_real_FPC_USB_power_OLED_supplier_evidence'],0)
 def test_30_not_time_acceleration(self):self.assertIn('p_time_dot²',self.r['real_time_domain_conversion'])
 def test_31_protected_no_parent_overwrite(self):
  for p in ('R78','R77','R76'):self.assertIn(p,self.r['parent_archives'])
 def test_32_require_total_material_not_exceeded(self):
  self.assertLess(max(float(x['F_free_mm']) for x in self.sched),m.L)
 def test_33_nonegative_free(self):self.assertGreater(min(float(x['F_free_mm']) for x in self.sched),0)
 def test_34_E0p08_pointwise_infeasible(self):
  e=.08;d0=m.Z
  self.assertLess(m.D*math.asin((d0-e)/m.D)-(d0+e),0)
 def test_35_corrupt_parent_rejected(self):
  from tempfile import TemporaryDirectory
  from zipfile import ZipFile
  with TemporaryDirectory() as temp:
   z=Path(temp)/'fake.zip'
   with ZipFile(z,'w') as f:f.writestr('dummy','not a trusted source')
   with self.assertRaises(ValueError):m.parent_check({'R78':z,'R77':z,'R76':z})

if __name__=='__main__':unittest.main(verbosity=2)
