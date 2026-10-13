"""R27 independent offline attestation, CAD-only: NO MANUFACTURING RELEASE."""
from pathlib import Path
import json,re,hashlib,platform,importlib.metadata
import cadquery as cq
from r25_capture import ROOT,P
V=ROOT/'verification';C=ROOT/'cad'
labels={'R21':28,'R22':37,'R22_adversarial':11,'R23':22,'R24':25,'R25':30,'R26':38}
counts={}
for label,expected in labels.items():
    log=V/f'R27_inherited_{label}.log'
    content=log.read_text()
    match=re.search(r'Ran\s+(\d+)\s+tests',content)
    assert match and int(match.group(1))==expected and 'OK' in content[-300:],label
    counts[label]=dict(tests=expected,log=str(log.relative_to(ROOT)),sha256=hashlib.sha256(log.read_bytes()).hexdigest())
assert (V/'R27_inherited_unit_tests_exit.log').read_text().strip().endswith('RC=0')
new=V/'R27_new_35.log';log=new.read_text()
assert 'Ran 35 tests' in log and 'OK' in log[-300:]
counts['R27']=dict(tests=35,log=str(new.relative_to(ROOT)),sha256=hashlib.sha256(new.read_bytes()).hexdigest())
assert sum(v['tests'] for v in counts.values())==226
R={k:json.loads((V/f'R27_{k}.json').read_text()) for k in ('integration','faults','tolerance','dynamic','power_faults','STEP_manifest')}
assert all(v['manufacturing_go'] is False for v in R.values())
assert R['integration']['all_shells_one_valid_body']
assert R['integration']['additional_cut_over_R26_mm3']==0.
assert R['faults']['joint_fault_cases']==64 and R['faults']['joint_fault_escape_cases']==36
assert all(r['R27_endpoint_captive_contact_mm3']>.02 for r in R['faults']['geometry'])
assert all(r['old_end_point_bypass_at_ext_0p8'] for r in R['faults']['geometry'])
assert R['tolerance']['samples']==108 and sum(r['cases'] for r in R['tolerance']['groups'])==108
assert R['dynamic']['pose_count']==10 and R['dynamic']['unexpected_collision_count']==0
assert R['power_faults']['enumerated_fault_states']==512
assert R['power_faults']['dangerous_states']==487
assert len(R['power_faults']['one_fault_dangerous_minimal_cuts'])==3
assert R['STEP_manifest']['exported_scenes']==12
for row in R['STEP_manifest']['scenes']:
 p=C/row['STEP']
 assert p.exists() and row['parts']==18 and row['valid_solids_reimported']==18
 assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
for n in ('R27_A_KEYED_UNCHANGED.brep','R27_B_CAPTIVE_OPEN_GATE_CUT.brep'):
 sh=cq.importers.importBrep(str(C/n)).val()
 assert sh.isValid() and len(sh.Solids())==1
report={
 'revision':'R27 OCC double-side captive OPEN shutter research; no hardware released',
 'product_form_locked':{'equal_A_B_external_nominal_mm':[94.25,73.99],
  'B_upward_slide_mm':P.travel,'B_Z_seat_mm':P.z_travel,
  'OLED_main_screen_inch_approx':7,'separate_external_screen':False,
  'A_battery_priority':True,'4700mAh_target_not_verified':True},
 'test_suites':counts,'total_unittest_cases':226,'unittest_passed':True,
 'R27_new_unittest_cases':35,
 'R27_OPEN_mechanical_endpoint_defect_fixed_locally':True,
 'first_sampled_ext_contact_mm':{r['side']:r['R27_first_sampled_contact_mm'] for r in R['faults']['geometry']},
 'R26_old_full_0p8_carrier_gate_escapes_but_R27_intersects':True,
 'R27_new_gate_open_lateral_free_at_ext_0p8':True,
 'R27_closed_gate_cannot_auto_retract_preextended_contact':True,
 'R27_workpiece_B_additional_cut_mm3':R['integration']['additional_cut_over_R26_mm3'],
 'R27_B_existing_cavity_reused_no_new_mounting_support':True,
 'R27_10_nominal_poses_checked':10,'R27_10_pose_unexpected_selected_clashes':0,
 'R27_tolerance_hypothetical_XYZ_configurations':108,
 'R27_tolerance_OCP_contact_evaluations':108*4,
 'R27_tolerance_groups':R['tolerance']['groups'],
 'mechanical_joint_fault_combinations':64,'mechanical_escapes_in_model':36,
 'conceptual_dual_battery_fault_states':512,'conceptual_electrical_dangerous_states':487,
 'conceptual_single_bypass_minimal_hazard_cuts':R['power_faults']['one_fault_dangerous_minimal_cuts'],
 'R27_STEP_scene_count':12,'R27_STEP_parts_per_scene':18,
 'OLED_nominal_edge_clearance_mm':R['dynamic']['nominal_OLED_edge_gap_worst_from_inherited_OPEN_gate_mm'],
 'B_gate_top_clearance_mm':R['dynamic']['nominal_B_top_clearance_worst_inherited_R26_mm'],
 'original_R24_rail_web_mm':.22,
 'real_OEM_full_OLED_width_and_Rdynamic_unknown':True,
 'real_gates_pawls_springs_bearings_FEA_durability_unqualified':True,
 'power_hardware_BMS_USB2_USB3_safety_unqualified':True,
 'false_capture_without_A_not_excluded':True,
 'real_manufacturing_and_life_qualifications':False,
 'manufacturing_go':False,
 'CAD_A_B_SHA256':{n:hashlib.sha256((C/n).read_bytes()).hexdigest() for n in ('R27_A_KEYED_UNCHANGED.brep','R27_B_CAPTIVE_OPEN_GATE_CUT.brep')},
 'CAD_STEP_manifest_SHA256':hashlib.sha256((V/'R27_STEP_manifest.json').read_bytes()).hexdigest(),
 'python':platform.python_version(),'cadquery':importlib.metadata.version('cadquery')
}
(V/'R27_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('R27 RESEARCH REPRO PASS',report['total_unittest_cases'],'STEP',report['R27_STEP_scene_count'],'manufacturing NO-GO')
