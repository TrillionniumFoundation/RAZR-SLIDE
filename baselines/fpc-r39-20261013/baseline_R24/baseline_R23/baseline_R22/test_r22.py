"""R22 candidate screen tests. PASS != hardware qualification or tooling approval."""
import unittest, json, hashlib
from pathlib import Path
from dataclasses import replace
import cadquery as cq
from r22_mechanics import (ROOT,P,assembly_local,stop_contact_metrics,
   exact_axis_aligned_box_overlap_volume,
   stop_effectively_locked,qualifying_seat,regression_scenario,fault_scan)
from r22_electrical import (InterconnectInputs,selective_power_enable,sweep_logic,
                            trial_current_envelope,TE_2199001,HARWIN_S1961,MILL_MAX_0985)
from r22_oled import ideal_gap,report as oled_report

class Mechanical(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.f=fault_scan()
 def test_both_legacy_dogs_open_still_blocked(self):
  x=assembly_local(False,False,False,False,True,True)
  self.assertTrue(stop_effectively_locked(x))
 def test_both_new_sides_false_open_center_blocks(self):
  x=assembly_local(False,True,True,False,True,True)
  self.assertEqual(list(stop_contact_metrics(x).values())[:2],[0,0])
  self.assertGreater(stop_contact_metrics(x)['B_INDEPENDENT_CENTRE_STOP'],0)
 def test_centre_false_open_sides_block(self):
  x=assembly_local(False,False,False,True,True,True)
  self.assertGreater(stop_contact_metrics(x)['B_LOAD_FACE_BOLT_L'],0)
  self.assertGreater(stop_contact_metrics(x)['B_LOAD_FACE_BOLT_R'],0)
 def test_known_triple_release_still_unsafe(self):
  self.assertFalse(stop_effectively_locked(assembly_local(False,True,True,True,True,True)))
 def test_retracted_contact_clears_all_stops(self):
  for p in (False,True):
   x=assembly_local(True,p,p,p,True,True)
   self.assertFalse(stop_effectively_locked(x))
 def test_unseated_never_proxy_allowed(self):
  self.assertEqual(self.f['scenarios'],320)
  self.assertEqual(self.f['false_unlock_blocking_failures'],0)
  self.assertEqual(self.f['unseated_arrangements'],312)
 def test_station_both_keys_needed(self):
  for port,s,q in [('STOW',0,0),('OPEN',P.travel,P.z_travel)]:
   for fl,fr,fc in ((False,True,True),(True,False,True),(True,True,False)):
    self.assertFalse(qualifying_seat(port,s,q,fl,fr,fc)['captive_A_center_key_proxied_seated'])
 def test_departure_0p03_closes_stow(self):
  self.assertTrue(regression_scenario('STOW',.03,0.,True,True)['mechanically_blocks_forced_extension'])
 def test_deep_pre_dock_closes_open(self):
  self.assertTrue(regression_scenario('OPEN',P.travel,P.z_travel-.2,True,True)['mechanically_blocks_forced_extension'])
 def test_center_seated_is_not_manufacturing_permission(self):
  x=regression_scenario('OPEN',P.travel,P.z_travel,True,True)
  self.assertFalse(x['model_permission']);self.assertFalse(x['actual_hardware_verified'])
 def test_real_assembly_risks_not_claimed(self):
  data=json.loads((ROOT/'verification'/'R22_mechanical_results.json').read_text())
  self.assertFalse(data['assembly_load_faces_mated_mechanical_linkage_proof'])
  self.assertFalse(data['captive_cam_kicker_and_actual_spring_engineered'])
  self.assertFalse(data['manufacturing_go'])
 def test_box_metric_crosschecks_independent_OCC_boolean(self):
  from r22_mechanics import intersection
  for seating in ((False,False,False),(True,True,True),(True,False,False),(False,True,False),(True,True,False)):
   a=assembly_local(False,*seating)
   for k in ('B_LOAD_FACE_BOLT_L','B_LOAD_FACE_BOLT_R','B_INDEPENDENT_CENTRE_STOP'):
    fast=exact_axis_aligned_box_overlap_volume(a['B_CARRIAGE_SAFETY_TAB'],a[k])
    exact=intersection(a['B_CARRIAGE_SAFETY_TAB'],a[k])
    self.assertAlmostEqual(fast,exact,places=7)
 def test_3d_B_still_one_solid_and_no_extra_ill_fit(self):
  data=json.loads((ROOT/'verification'/'R22_mechanical_results.json').read_text())
  self.assertTrue(data['B_valid']);self.assertTrue(data['B_one_solid'])
  self.assertEqual(data['B_vs_R21_reference_max_overlap_mm3'],0.)
  self.assertEqual(data['extra_safety_moving_parts_vs_OLED_FPC_A_and_B_collision_count'],0)
  self.assertGreater(data['B_extra_removed_volume_mm3'],0)
 def test_new_B_not_in_B_battery_PCB_camera_proxies(self):
  a=json.loads((ROOT/'verification'/'R22_mechanical_results.json').read_text())
  self.assertEqual(sum(a['B_battery_interface'].values()),0.)

class Electrical(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.good=InterconnectInputs(stow_seat=True,independent_load_faces=True,
   center_seat_key=True,both_dogs_closed_or_seated=True,bms_A_healthy=True,
   bms_B_healthy=True,power_qualified=True,precharge_completed=True,
   voltage_delta_in_window=True,measured_contact_temp_ok=True,
   system_enabled=True,both_power_fets_verified_healthy=True)
 def test_8192_fully_exhaustive_with_mutant(self):
  s=sweep_logic();self.assertEqual(s['logic_states_checked'],8192)
  self.assertEqual(s['logic_false_energization_failures'],0)
  self.assertTrue(s['mutation_bad_controller_rejected'])
 def test_one_good_dock_ideal(self):
  self.assertTrue(selective_power_enable(self.good)['main_bus_enable'])
 def test_open_and_stow_simultaneous_blocks(self):
  self.assertFalse(selective_power_enable(replace(self.good,open_seat=True))['precharge_request'])
 def test_neither_open_nor_stow_blocks(self):
  self.assertFalse(selective_power_enable(replace(self.good,stow_seat=False))['precharge_request'])
 def test_unknown_contacts_cannot_even_precharge(self):
  self.assertFalse(selective_power_enable(replace(self.good,power_qualified=False))['precharge_request'])
 def test_center_not_seated_no_precharge(self):
  self.assertFalse(selective_power_enable(replace(self.good,center_seat_key=False))['precharge_request'])
 def test_legacy_dogs_unlocked_no_precharge(self):
  self.assertFalse(selective_power_enable(replace(self.good,both_dogs_closed_or_seated=False))['precharge_request'])
 def test_bms_fail_opens(self):
  for field in ('bms_A_healthy','bms_B_healthy','both_power_fets_verified_healthy'):
   self.assertFalse(selective_power_enable(replace(self.good,**{field:False}))['main_bus_enable'])
 def test_precharge_first(self):
  s=replace(self.good,precharge_completed=False)
  self.assertTrue(selective_power_enable(s)['precharge_request'])
  self.assertFalse(selective_power_enable(s)['main_bus_enable'])
 def test_thermal_fail_closed(self):
  self.assertFalse(selective_power_enable(replace(self.good,measured_contact_temp_ok=False))['precharge_request'])
 def test_te_signal_not_power_or_usb(self):
  self.assertEqual(TE_2199001['application'],'Signal')
  self.assertEqual(TE_2199001['rated_current_A'],1.5)
  self.assertFalse(TE_2199001['approved_for_power']);self.assertFalse(TE_2199001['approved_for_usb_high_speed'])
 def test_power_aging_vendor_screen_rejects(self):
  self.assertLess(HARWIN_S1961['manufacturer_durability_min_cycles'],300000)
  self.assertLess(MILL_MAX_0985['manufacturer_mechanical_life_cycles'],300000)
 def test_current_sensitivity_does_not_qualify_part(self):
  self.assertGreater(trial_current_envelope(12)['constant_power_current_A'],4.)
  self.assertFalse(trial_current_envelope(5)['rating_is_sufficient_to_approve_connector'])
 def test_no_claim_main_power_qualified(self):
  d=json.loads((ROOT/'verification'/'R22_electrical_results.json').read_text())
  self.assertFalse(d['qualified_power']);self.assertFalse(d['qualified_usb']);self.assertFalse(d['qualified_signal'])

class OLED(unittest.TestCase):
 def test_narrow_mechanical_stack_margin(self):
  self.assertAlmostEqual(ideal_gap(3.4)['nominal_residual_mm'],.34)
 def test_r5_would_break_assumed_cavity(self):
  self.assertFalse(ideal_gap(5)['ideal_geometry_screening_pass'])
 def test_r3_42_boundary_no_real_margin(self):
  self.assertAlmostEqual(ideal_gap(3.42)['nominal_residual_mm'],.3)
 def test_vendor_dimensions_missing(self):
  d=oled_report(write=False)
  self.assertFalse(d['seven_inch_module_oem_specifications_received'])
  self.assertFalse(d['module_lifetime_and_R3_4_qualified'])
 def test_0p15_per_side_breaks_clearance(self):
  d=oled_report(write=False)['r21_screen_edge_mm']
  self.assertFalse(d[1]['meets_0_30'])
 def test_IEC_method_not_life_approval(self):
  d=oled_report(write=False)
  self.assertIn('MEASUREMENT',d['IEC_62715_6_42_2026'])
  self.assertFalse(d['manufacture_go'])

class STEP(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.manifest=json.loads((ROOT/'verification'/'R22_STEP_manifest.json').read_text())
 def test_5_snapshot_source_and_integrity(self):
  self.assertEqual(len(self.manifest['STEP_records']),5)
  self.assertTrue(self.manifest['source_B_R22_cut_single_solid'])
  self.assertFalse(self.manifest['manufacturer_production_release'])
 def test_imported_part_counts_and_hashes(self):
  for r in self.manifest['STEP_records']:
   path=ROOT/'cad'/r['file']
   self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),r['sha256'])
   self.assertEqual(len(cq.importers.importStep(str(path)).solids().vals()),r['expected_solids'])
 def test_impossible_ghost_states_not_accepted(self):
  self.assertEqual(sum(x['ghost_collision'] for x in self.manifest['STEP_records']),2)

if __name__=='__main__':unittest.main()
