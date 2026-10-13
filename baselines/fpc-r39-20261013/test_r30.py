"""R30 adversarial CAD assertions; NO physical certification or safety release.
Positive tests include checking dangerous states are still honestly reported.
"""
from __future__ import annotations
import hashlib,json,unittest
import cadquery as cq
from r25_capture import ROOT,intersection
from r30_mechanics import gate,carrier,extension_at,web_budget

REPORTS=('integration','dynamic','tolerance','retention','faults','section','STEP_manifest')
class R30ResearchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
    cls.r={name:json.loads((ROOT/'verification'/f'R30_{name}.json').read_text()) for name in REPORTS}
    cls.original=json.loads((ROOT/'audit'/'R30_R29_ORIGINAL_ZIP_MEMBERS.json').read_text())
 def test_01_unchanged_R29_member_count(self):self.assertEqual(self.original['R29_zip_member_count_verified'],441)
 def test_02_R29_original_zip_frozen(self):self.assertTrue(self.original['prior_artifacts_unchanged'])
 def test_03_two_B_rebases_really_differ(self):
    v=self.r['section']['model'];self.assertNotEqual(v[-1]['sha256'],v[2]['sha256'])
 def test_04_A_valid_one_body(self):self.assertTrue(self.r['integration']['A_valid_single_body'])
 def test_05_B_valid_one_body(self):self.assertTrue(self.r['integration']['B_valid_single_body'])
 def test_06_reuses_R27_prior_to_R28_R29_cut(self):
    self.assertIn('R27-shell rebase',self.r['integration']['revision'])
 def test_07_real_boss_fused_to_shell(self):
    self.assertGreater(self.r['integration']['actual_boss_added_over_R27_mm3'],0.)
 def test_08_bearing_pocketing_has_real_subtractions(self):self.assertEqual(len(self.r['integration']['subtractions']),8)
 def test_09_two_valid_shutters(self):
    for s in 'LR':
        g=gate(s,0.);self.assertTrue(g.isValid());self.assertEqual(len(g.Solids()),1)
 def test_10_two_valid_carrier_follower_bodies(self):
    for s in 'LR':
        e=carrier(s,0.);self.assertTrue(e.isValid());self.assertEqual(len(e.Solids()),1)
 def test_11_kinematic_closed(self):self.assertEqual(extension_at(0.),0.)
 def test_12_kinematic_mid(self):self.assertAlmostEqual(extension_at(.63),.4)
 def test_13_kinematic_open(self):self.assertAlmostEqual(extension_at(.9),.8)
 def test_14_local_nominal_gate_ear_no_clash(self):
    for s in 'LR':
        for t in (0.,.45,.9):self.assertLess(intersection(gate(s,t),carrier(s,extension_at(t))),1e-8)
 def test_15_nominal_front_lip_better_but_not_safety(self):
    self.assertTrue(web_budget()['thin_front_edge_not_structurally_fixed'])
 def test_16_minimal_guide_ideal_Y_lip(self):self.assertLessEqual(web_budget()['R29_original_hypothetical_front_wall_mm'],.031)
 def test_17_nominal_OLED_10_poses(self):self.assertEqual(self.r['dynamic']['pose_count'],10)
 def test_18_B_boss_entire_A_OLED_FPC_nominal_collision_zero(self):
    self.assertEqual(self.r['dynamic']['unexpected_collision_count'],0)
 def test_19_OEM_OLED_not_verified(self):self.assertTrue(self.r['dynamic']['parametric_OLED_only_not_OEM_full_packaging'])
 def test_20_GDT_cube_108(self):self.assertEqual(self.r['tolerance']['number_configurations'],108)
 def test_21_GDT_324_OCC(self):self.assertEqual(self.r['tolerance']['occ_pair_checks'],324)
 def test_22_both_nominal_width_stresses_no_jam(self):
    self.assertEqual([s['jam_configs'] for s in self.r['tolerance']['summary']],[0,0])
 def test_23_rear_guide_324_cube_samples(self):self.assertEqual(self.r['retention']['xyz_guide_configurations'],324)
 def test_24_rear_guide_0p05_stress_clearance(self):self.assertEqual(self.r['retention']['guide_jam_configs'],0)
 def test_25_rear_guide_0p10_hard_obstructions(self):
    self.assertEqual(self.r['retention']['hard_axis_probes'],24)
    self.assertEqual(self.r['retention']['hard_axis_fail_to_intercept'],0)
 def test_26_actual_guide_engagement_length(self):
    self.assertGreaterEqual(self.r['retention']['guide_overlap_min_mm'],1.5)
 def test_27_four_wall_sample_cells_not_entirely_cut(self):
    for _,v in self.r['section']['sampled_cross_sections'].items():
        self.assertGreaterEqual(v['R30_material_occupation_fraction'],.899999)
 def test_28_cad_motion38(self):self.assertEqual(self.r['faults']['normal_nominal_positions'],38)
 def test_29_kinematic_nominal_position(self):self.assertTrue(self.r['faults']['normal_poses_all_collision_free'])
 def test_30_joint_fault_escape_still_present(self):self.assertEqual(self.r['faults']['inherited_original_fault_escape_counterexamples'],36)
 def test_31_no_A_key_false_engagement_still_possible(self):self.assertTrue(self.r['faults']['no_A_key_false_capture_still_possible'])
 def test_32_stuck_power_carrier_unsafe(self):self.assertTrue(self.r['faults']['pin_break_or_stuck_carrier_has_no_force_limited_recovery'])
 def test_33_captive_path_not_electrical_isolation(self):self.assertTrue(self.r['faults']['guide_boss_is_not_a_power_isolation_device'])
 def test_34_stuck_0p8_collision_is_detected(self):
    self.assertTrue(all(x['collision_mm3']>1e-8 for x in self.r['faults']['stuck_carrier_rows'] if x['shutter_mm']==0.))
 def test_35_six_scene_STEP(self):self.assertEqual(self.r['STEP_manifest']['scene_count'],6)
 def test_36_STEP_each_reimported_and_valid(self):
    for x in self.r['STEP_manifest']['scenes']:
        self.assertEqual(x['valid_imported_solids'],x['exported_parts'])
 def test_37_STEP_hashed_members(self):
    for x in self.r['STEP_manifest']['scenes']:
        self.assertEqual(hashlib.sha256((ROOT/'cad'/x['filename']).read_bytes()).hexdigest(),x['sha256'])
 def test_38_full_archive_441_untouched(self):
    for f in self.original['entries']:
        self.assertEqual(hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest(),f['sha256'],f['path'])
 def test_39_all_seven_reports_hold_NO_GO(self):
    self.assertTrue(all(d['manufacturing_go'] is False for d in self.r.values()))
 def test_40_actual_material_strength_unqualified(self):
    self.assertTrue(self.r['section']['joint_and_pullout_strength_not_measured'])

if __name__=='__main__':unittest.main()
