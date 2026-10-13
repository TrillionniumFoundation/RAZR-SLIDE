"""R39 negative-screen verification: PASS means hazards are detected, NOT manufacturing GO."""
import hashlib,json,unittest
from r25_capture import ROOT,P
from r39_path import Candidate,CANDIDATES as BASIC,curve,anchors,FPC_WIDTH_MM,FPC_THICKNESS_MM
from r39_screen import SCENES,CANDIDATES

class R39DynamicFPCNegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((ROOT/'verification/R39_path_screen.json').read_text())
        cls.s=json.loads((ROOT/'verification/R39_STEP_manifest.json').read_text())
        cls.h=json.loads((ROOT/'verification/R39_inherited_results.json').read_text())
    def test_all_stages_22(self):self.assertEqual(self.r['scenes'],22)
    def test_four_nonidentical_routes(self):self.assertEqual(len(CANDIDATES),4)
    def test_eighty_eight_combinations(self):self.assertEqual(self.r['scenario_count'],88)
    def test_cartesian_combinations(self):self.assertEqual(len(self.r['rows']),88)
    def test_slide_stroke(self):self.assertAlmostEqual(self.r['product_travel_y_mm'],79.75,6)
    def test_dock_stroke(self):self.assertAlmostEqual(self.r['product_final_dock_z_mm'],8.2,6)
    def test_each_pose_only_once(self):self.assertEqual(len({r['pose'] for r in self.r['rows']}),22)
    def test_final_z_included(self):self.assertTrue(any(r['dock_mm']==8.2 for r in self.r['rows']))
    def test_all_fixed_lengths_at_requested_numeric_tolerance(self):self.assertLess(max(r['length_absolute_error_mm'] for r in self.r['rows']),1e-8)
    def test_nonzero_actual_polyline_discretization(self):self.assertTrue(all(r['sampled_polyline_length_mm']>0 for r in self.r['rows']))
    def test_four_candidate_rows_22(self):self.assertTrue(all(d['poses']==22 for d in self.r['constraints_summary'].values()))
    def test_inboard_collision_all_poses(self):self.assertEqual(self.r['constraints_summary']['INBOARD_SERPENTINE_125']['poses_with_observed_any_solid_penetration'],22)
    def test_inner_side_collision_all_poses(self):self.assertEqual(self.r['constraints_summary']['INNER_SIDE_SERPENTINE_125']['poses_with_observed_any_solid_penetration'],22)
    def test_outer_collision_all_poses(self):self.assertEqual(self.r['constraints_summary']['OUTBOARD_SINGLE_BOW_125']['poses_with_observed_any_solid_penetration'],22)
    def test_gentle_collision_all_poses(self):self.assertEqual(self.r['constraints_summary']['GENTLE_INBOARD_SINGLE_BOW_150']['poses_with_observed_any_solid_penetration'],22)
    def test_both_serpentines_below_2p5(self):
        for k in ('INBOARD_SERPENTINE_125','INNER_SIDE_SERPENTINE_125'): self.assertEqual(self.r['constraints_summary'][k]['poses_passing_assumed_R2p5'],0)
    def test_outer_below_2p5_at_all_poses(self):self.assertEqual(self.r['constraints_summary']['OUTBOARD_SINGLE_BOW_125']['poses_passing_assumed_R2p5'],0)
    def test_gentle_not_all_R7p5(self):self.assertLess(self.r['constraints_summary']['GENTLE_INBOARD_SINGLE_BOW_150']['poses_passing_assumed_R7p5'],22)
    def test_all_R15_fail(self):self.assertTrue(all(d['poses_passing_assumed_R15']==0 for d in self.r['constraints_summary'].values()))
    def test_outboard_exceeds_width(self):self.assertEqual(self.r['constraints_summary']['OUTBOARD_SINGLE_BOW_125']['poses_exceeding_chassis_width'],22)
    def test_inboard_not_outside_width_in_proxy(self):self.assertEqual(self.r['constraints_summary']['INBOARD_SERPENTINE_125']['poses_exceeding_chassis_width'],0)
    def test_all_gentle_exceed_z(self):self.assertEqual(self.r['constraints_summary']['GENTLE_INBOARD_SINGLE_BOW_150']['poses_exceeding_assembled_proxy_z'],22)
    def test_no_route_approved(self):self.assertTrue(self.r['all_candidates_rejected'])
    def test_no_route_passes_joint_screen(self):self.assertTrue(all(d['poses_passing_all_design_screens']==0 for d in self.r['constraints_summary'].values()))
    def test_includes_all_four_chassis_display_colliders(self):self.assertEqual(set(self.r['rows'][0]['sample_inside_solid_counts']),{'A_chassis','B_chassis','OLED_hypothesis','old_display_FPC_not_cross_chamber'})
    def test_sections_five_points(self):self.assertEqual(self.r['section_samples_per_location'],5)
    def test_section_count_405(self):self.assertEqual(self.r['rows'][0]['full_width_ribbon_sample_count'],405)
    def test_width_1p2(self):self.assertAlmostEqual(self.r['tested_physical_footprint_width_mm'],1.2)
    def test_thickness_0p15(self):self.assertAlmostEqual(self.r['tested_physical_footprint_thickness_mm'],.15)
    def test_explicit_discrete_not_continuous_pass(self):self.assertTrue(self.r['strictly_finite_sampling_not_entire_swept_continuum'])
    def test_no_OEM_stackup(self):self.assertTrue(self.r['no_OEM_FPC_stackup_clamp_harness_or_tail_step'])
    def test_no_functional_circuit(self):self.assertTrue(self.r['no_live_electrical_connection_implemented'])
    def test_no_fatigue_qualification(self):self.assertTrue(self.r['materials_and_fatigue_lifetime_not_qualified'])
    def test_six_step_files(self):self.assertEqual(len(self.s['scenarios']),6)
    def test_all_steps_seven_valid_solids(self):self.assertTrue(all(s['parts']==s['valid_solids']==7 for s in self.s['scenarios']))
    def test_every_step_is_a_ghost(self):self.assertTrue(all(s['intentional_unsafe_ghost'] for s in self.s['scenarios']))
    def test_step_hashes_actual_bytes(self):
        for s in self.s['scenarios']:
            self.assertEqual(hashlib.sha256((ROOT/'cad'/s['step']).read_bytes()).hexdigest(),s['sha256'])
    def test_no_OEM_harness_in_step(self):self.assertFalse(self.s['real_supplier_harness_present'])
    def test_nonfunctional_step(self):self.assertFalse(self.s['actual_electrical_link_implemented'])
    def test_frozen_R38_archive_sha(self):self.assertEqual(self.h['source_R38_sha'],'649c89711e5bd25a357fbac972d1c0e4ac8144841dd34e8b261cd67aa50bb7a6')
    def test_frozen_R38_archived_count(self):self.assertEqual(self.h['source_R38_members'],1094)
    def test_fresh_history_passed(self):self.assertTrue(self.h['all_passed'])
    def test_fresh_697_exact(self):self.assertEqual(self.h['historical_reexecuted_tests'],697)
    def test_no_manufacturing_release(self):self.assertFalse(self.r['manufacturing_go'])
    def test_not_a_legacy_screen_tail(self):
        a,b=anchors(P.travel,8.2);self.assertAlmostEqual(b[1]-a[1],24.75)
    def test_endpoints_match_at_stow(self):
        for _,c,L in CANDIDATES:
            pp=curve(c,0,0,n=81,target=L)
            a,b=anchors(0,0)
            self.assertTrue((abs(pp['points'][0]-a)<1e-10).all())
            self.assertTrue((abs(pp['points'][-1]-b)<1e-10).all())
    def test_two_axis_movement_changes_end_z(self):
        a,b=anchors(79.75,0);c,d=anchors(79.75,8.2)
        self.assertAlmostEqual(float(d[2]-b[2]),8.2)
    def test_stow_Open_not_identical(self):
        p=curve(CANDIDATES[0][1],0,0,n=81,target=125)['points']
        q=curve(CANDIDATES[0][1],79.75,8.2,n=81,target=125)['points']
        self.assertGreater(float(abs(p-q).max()),20.)
    def test_analytical_outer_x_exceeds_nominal_shell(self):
        p=curve(CANDIDATES[2][1],0,0,n=401,target=125)
        self.assertAlmostEqual(p['point_bounds']['x'][1],49.7,5)
        self.assertGreater(p['point_bounds']['x'][1],36.995)

if __name__=='__main__':unittest.main(verbosity=2)
