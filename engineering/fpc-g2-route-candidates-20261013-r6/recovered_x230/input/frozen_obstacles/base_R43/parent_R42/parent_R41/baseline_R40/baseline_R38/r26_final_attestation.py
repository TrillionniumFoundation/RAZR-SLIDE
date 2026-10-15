"""Independent final R26 snapshot verification (model-only, manufacturing explicitly NO-GO)."""
from pathlib import Path
import re,json,hashlib,platform,importlib.metadata
import cadquery as cq
from r25_capture import ROOT
V=ROOT/'verification'
FILES={
  'R21':ROOT/'baseline_R24/verification/R24_R21_baseline.log',
  'R22':ROOT/'baseline_R24/verification/R24_R22_baseline.log',
  'R22_adversarial':ROOT/'baseline_R24/verification/R24_R22_adversarial.log',
  'R23':ROOT/'baseline_R24/verification/R24_R23_baseline.log',
  'R24':ROOT/'baseline_R24/verification/R24_new_25.log',
  'R25':V/'R25_new_30.log',
  'R26':V/'R26_new_38.log',
}
assert (V/'R26_inherited_done.flag').read_text().strip()=='FINISHED'
assert (V/'R26_geometry_export_done.flag').read_text().strip()=='FINISHED'
counts={}
for tag,path in FILES.items():
 content=path.read_text(errors='replace')
 matched=re.search(r'Ran\s+(\d+)\s+tests',content)
 assert matched and 'OK' in content[-200:],(tag,path)
 counts[tag]=dict(tests=int(matched.group(1)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),log=str(path.relative_to(ROOT)))
assert sum(x['tests'] for x in counts.values())==191,counts
inst=json.loads((V/'R26_integration.json').read_text())
dyn=json.loads((V/'R26_dynamic.json').read_text())
fault=json.loads((V/'R26_faults.json').read_text())
tol=json.loads((V/'R26_tolerance.json').read_text())
steps=json.loads((V/'R26_STEP_manifest.json').read_text())
assert inst['R26_B_is_single_solid'] and inst['new_pockets']==6
assert dyn['unexpected_count']==0 and dyn['pose_count']==10
assert len(tol['rows'])==216
assert fault['undocked_R26_second_gate_absent_or_broken_escape_rows']>0
assert steps['exported_scenes']==10
assert sum(x['deliberate_fault_GHOST'] for x in steps['scenes'])>=5
for datum in (inst,dyn,fault,tol,steps):assert datum['manufacturing_go'] is False
for step in steps['scenes']:
    p=ROOT/'cad'/step['STEP']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==step['sha256']
    assert step['valid_solids_reimported']==step['parts']==18
A=ROOT/'cad/R26_A_UNCHANGED.brep'
B=ROOT/'cad/R26_B_INBOARD_PAWL_OPEN_GATE_CUT.brep'
for p in (A,B):
 body=cq.importers.importBrep(str(p)).val()
 assert body.isValid() and len(body.Solids())==1
stats=dict(
 revision='R26 real OCC CAD + adversarial, NOT manufacturing-qualified',
 product_constraints=dict(A_B_same_external_nominal_mm=[94.25,73.99],B_slides_up_mm=79.75,
         B_Z_docking_mm=8.2,one_main_OLED_inches_approx=7,independent_back_screen=False,
         A_prioritized_battery=True,battery_capacity_mAh_target=4700,target_not_measured=True),
 inherited_and_new_tests=counts,total_regression_tests=sum(x['tests'] for x in counts.values()),
 every_reported_test_passed=True,
 new_OPEN_stage2_OCC_valid=True,old_R25_uncovered_pawl_A_full_shell_clash_mm3_per_side=.02112,
 R26_six_B_actual_pockets=inst['new_pockets'],R26_extra_B_cut_mm3=inst['additional_B_cut_vs_R25_mm3'],
 ten_reference_poses_checked=dyn['pose_count'],reference_pose_collision_failures=dyn['unexpected_count'],
 new_partial_tolerance_case_count=len(tol['rows']),new_targeted_issues_by_width=tol['groups'],
 old_R25_capture_GDT_still_unqualified=True,
 joint_fault_modes=fault['total_modeled_joint_fault_combinations'],joint_fault_escape_counterexamples=fault['undocked_R26_second_gate_absent_or_broken_escape_rows'],
 first_closed_gate_carrier_sweep_contact_mm=fault['first_sweep_carrier_collision_at_mm'],
 initial_0p8_carrier_extension_not_blocked_in_end_pose=fault['R26_stage2_gate_held_CLOSED_at_0p8_extension_does_not_physically_overlap'],
 assembled_STEP_count=steps['exported_scenes'],parts_each_STEP=18,
 sample_OLED_nominal_X_gap_to_OPEN_gate_mm=dyn['OPEN_gate_min_assumed_OLED_outer_edge_nominal_gap_mm'],
 B_native_top_clearance_near_gate_mm=dyn['OPEN_gate_native_shell_top_clearance_mm'],
 OEM_OLED_suppliers_authorization_missing=True,real_power_hardware_and_electrical_isolation_missing=True,
 physical_spring_guide_endstop_and_mechanical_capture_proof_missing=True,
 R24_side_rail_min_web_thickness_prev_model_mm=.22,
 qualified_battery_mAh=None,full_OLED_external_package_width_mm=None,
 manufacturing_go=False)
path=V/'R26_results.json'
path.write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n')
receipt=dict(reason='Attests reproducible research-only CAD/offline tests; explicitly no experimental product qualification',
 code_cadquery=importlib.metadata.version('cadquery'),
 cadquery_ocp=importlib.metadata.version('cadquery-ocp'),
 python_version=platform.python_version(),
 A_brep_sha256=hashlib.sha256(A.read_bytes()).hexdigest(),
 B_brep_sha256=hashlib.sha256(B.read_bytes()).hexdigest(),
 R26_results_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
 STEP_manifest_sha256=hashlib.sha256((V/'R26_STEP_manifest.json').read_bytes()).hexdigest(),
 STEP_SHA256_all_pass=True,all_191_tests_success=True,
 confirmed_missing_physical_spring_and_OLED_BMS_integration=True,manufacturing_go=False)
(ROOT/'audit'/'R26_independent_attestation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print('R26 independently verified 191 PASS; manufacture NO-GO',stats['R26_extra_B_cut_mm3'])
