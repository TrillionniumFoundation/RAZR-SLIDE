"""R38 safety NEGATIVE tests: passing deliberately does not mean manufacturing GO."""
import unittest,json,zipfile,hashlib
from r25_capture import ROOT
from r38_parts import *

class R38ArchitectureTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.i=json.loads((ROOT/'verification/R38_integration.json').read_text())
  cls.f=json.loads((ROOT/'verification/R38_faults.json').read_text())
  cls.e=json.loads((ROOT/'verification/R38_STEP_manifest.json').read_text())
 def test_exact_sku(self):self.assertEqual(SKU,'BM28B0.6-24DP/2-0.35V(53)')
 def test_dimensions(self):self.assertEqual((HEADER_LENGTH_MM,HEADER_WIDTH_MM,MATED_HEIGHT_MM),(6.12,1.5,.6))
 def test_native_model_absent(self):self.assertFalse(self.i['vendor']['native_VENDOR_STEP_downloaded_and_imported'])
 def test_source_reference(self):self.assertTrue(self.i['vendor']['product_url'].startswith('https://www.hirose.com/'))
 def test_supplier_rating_not_lifecycle(self):self.assertLess(PUBLISHED_MATING_CYCLES,TARGET_SLIDE_CYCLES_ASSUMED)
 def test_vendor_proxy_metadata(self):self.assertTrue(self.i['vendor']['only_catalogue_bounding_proxy'])
 def test_B_csg_valid(self):self.assertTrue(self.i['B_provisional_valid_single_solid'])
 def test_B_protected_core_cut_positive(self):self.assertGreater(self.i['B_protected_volume_cut_mm3'],0)
 def test_core_cut_not_authorized(self):self.assertTrue(self.i['B_material_removed_from_unapproved_protected_core'])
 def test_no_OEM_core(self):self.assertFalse(self.i['B_OEM_BOM_clearance_known'])
 def test_A_original_sha(self):self.assertEqual(len(self.i['R37_original_A_SHA256']),64)
 def test_B_original_sha(self):self.assertEqual(len(self.i['R37_original_B_SHA256']),64)
 def test_original_A_identical(self):self.assertEqual((ROOT/'cad/R38_A_R37_BYTE_IDENTICAL.brep').read_bytes(),(ROOT/'cad/R37_A_R36_IDENTICAL.brep').read_bytes())
 def test_original_B_source_unchanged(self):self.assertEqual(hashlib.sha256((ROOT/'cad/R37_B_INTEGRAL_FRONT_STOP_LIPS.brep').read_bytes()).hexdigest(),self.i['R37_original_B_SHA256'])
 def test_reference_poses_ten(self):self.assertEqual(self.i['reference_pose_count'],10)
 def test_reference_poses_reported(self):self.assertEqual(len(self.i['reference_poses']),10)
 def test_candidate_named_interference_recorded(self):self.assertTrue(all('specified_named_interference' in q for q in self.i['reference_poses']))
 def test_old_outboard_substitution_rejected(self):self.assertGreater(self.i['old_R37_mini_contact_bay_header_direct_substitution'][-1]['old_outboard_header_vs_A_mm3'],0)
 def test_old_outboard_name(self):self.assertEqual(self.i['old_R37_mini_contact_bay_header_direct_substitution'][-1]['pose'],'OPEN_SEATED')
 def test_no_cable_or_circuit(self):self.assertTrue(self.i['stow_and_open_connector_contacts_NOT_electrically_linked_in_CAD'])
 def test_multiaxis_fpc_not_generated(self):self.assertFalse(self.i['true_two_compartment_flex_service_loop_generated'])
 def test_planar_U_fails_open(self):self.assertFalse(self.i['simple_U_bend_feasibility']['simple_constant_plane_U_matches_open_endpoint'])
 def test_vertical_travel_propagates(self):self.assertEqual(self.i['simple_U_bend_feasibility']['vertical_dock_stroke_mm'],8.2)
 def test_length_budget(self):self.assertGreater(self.i['simple_U_bend_feasibility']['minimum_idealized_yz_centerline_length_mm'],60)
 def test_fault_states_count(self):self.assertEqual(self.f['hypothetical_fault_states'],32)
 def test_every_fault_unqualified(self):self.assertTrue(all(not q['operating_link_qualified'] for q in self.f['hypothetical_fault_matrix']))
 def test_joint_unsafe_unresolved(self):self.assertEqual(self.f['R37_legacy_unsafe_count'],36)
 def test_three_power_bypass_categories(self):self.assertEqual(self.i['legacy_PCB_single_bypass_categories_unresolved'],3)
 def test_no_real_SI(self):self.assertTrue(self.f['no_real_flex_strain_cycle_or_SI_results'])
 def test_oled_gate_still_open(self):self.assertTrue(self.i['OLED_OEM_data_missing'])
 def test_no_mfg_go(self):self.assertFalse(self.i['manufacturing_go'])
 def test_ghost_step_count(self):self.assertEqual(self.e['intentional_ghost_count'],1)
 def test_step_count(self):self.assertEqual(self.e['step_count'],5)
 def test_steps_valid(self):self.assertTrue(all(x['parts']==x['reimported_valid_solids'] for x in self.e['scenes']))
 def test_steps_hash_matches(self):self.assertTrue(all(hashlib.sha256((ROOT/'cad'/x['file']).read_bytes()).hexdigest()==x['sha256'] for x in self.e['scenes']))
 def test_no_real_link_step(self):self.assertTrue(all(not x['actual_FPC_cross_compartment_installed'] for x in self.e['scenes']))

if __name__=='__main__': unittest.main(verbosity=2)
