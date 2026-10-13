"""Read-only R29 engineering evidence and immutable ancestor attestation.

'PASS' is a passed software/geometry assertion, never a manufacture licence.
"""
from __future__ import annotations
import hashlib,json,re,platform,importlib.metadata
from pathlib import Path
import cadquery as cq
from r25_capture import ROOT

V=ROOT/'verification'
LABELS={'R21':28,'R22':37,'R22_adversarial':11,'R23':22,'R24':25,
        'R25':30,'R26':38,'R27':35,'R28':42,'R29':40}
logs={}
for label,n in LABELS.items():
 p=V/(f'R29_new_40.log' if label=='R29' else f'R29_inherited_{label}.log')
 content=p.read_text(errors='replace')
 m=re.search(r'Ran\s+(\d+)\s+tests',content)
 if not m or int(m.group(1))!=n or not content.rstrip().endswith('OK'):
  raise AssertionError(f'FAIL/INCOMPLETE exact-test receipt {label}: {p}')
 logs[label]={'tests':n,'filename':str(p.relative_to(ROOT)), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

base=json.loads((ROOT/'audit'/'R28_SHA256_MANIFEST.json').read_text())
if len(base['entries'])!=374:raise AssertionError('R28 prior manifest count differs')
for f in base['entries']:
 p=ROOT/f['path']
 if not p.is_file() or p.stat().st_size!=f['size_bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:
  raise AssertionError(f'prior R28 original modified: {p}')

R={k:json.loads((V/f'R29_{k}.json').read_text()) for k in
   ('integration','dynamic','faults','tolerance','clearance','presence','ear_section','STEP_manifest')}
if any(x.get('manufacturing_go') is not False for x in R.values()):raise AssertionError('Manufacture veto missing in report')
assert R['integration']['valid_single_A'] and R['integration']['valid_single_B']
assert R['integration']['additional_B_removed_mm3']>0
assert R['dynamic']['pose_count']==10 and R['dynamic']['unexpected_collision_count']==0
assert R['tolerance']['samples']==108 and R['tolerance']['OCC_checks']==324
assert all(x['jam_configs']==0 and x['configs']==54 for x in R['tolerance']['summary'])
assert R['clearance']['clashes_at_plus_0p05']==0
assert R['faults']['prescribed_pose_count']==38 and R['faults']['all_prescribed_nominal_geometries_valid']
assert R['faults']['inherited_original_fault_escape_counterexamples']==36
assert R['faults']['prevent_false_capture_when_no_A'] is False
assert R['presence']['candidate_rejected_not_integrated']
assert R['presence']['raised_plunger_interferes_with_A_at_final_seat']
assert R['STEP_manifest']['scene_count']==6
for row in R['STEP_manifest']['scenes']:
 p=ROOT/'cad'/row['filename']
 assert p.stat().st_size==row['file_size'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
 assert row['valid_imported_solids']==row['exported_parts']
for name in ('R29_A_R28_FROZEN_KEYS.brep','R29_B_REVISED_SLOT_POCKET.brep'):
 shape=cq.importers.importBrep(str(ROOT/'cad'/name)).val()
 assert shape.isValid() and len(shape.Solids())==1

out={
 'revision':'R29 R21-R28 full independent re-run + 40 R29 research tests',
 'platform':{'python':platform.python_version(),'cadquery':importlib.metadata.version('cadquery')},
 'original_R28_SHA256_manifest':hashlib.sha256((ROOT/'audit'/'R28_SHA256_MANIFEST.json').read_bytes()).hexdigest(),
 'prior_R28_files_verified_unchanged':len(base['entries']),
 'direct_regression_test_receipts':logs,
 'regression_tests_total':sum(LABELS.values()),
 'all_unit_tests_passed':True,
 'geometry_recalculation_succeeded':(V/'R29_geometry_exit.code').read_text().strip()=='0',
 'inherited_reexecution_succeeded':(V/'R29_inherited_exit.code').read_text().strip()=='0',
 'R29_actual_BREP_A_B_valid_one_connected':True,
 'R29_actual_additional_B_cut_mm3':R['integration']['additional_B_removed_mm3'],
 'R29_full_reference_poses':R['dynamic']['pose_count'],
 'R29_reference_abnormal_collisions':R['dynamic']['unexpected_collision_count'],
 'R29_prescribed_tolerance_configs':R['tolerance']['samples'],
 'R29_prescribed_occ_checks':R['tolerance']['OCC_checks'],
 'R28_old_0p02_jam_configurations':0,
 'R28_old_0p05_jam_configurations':50,
 'R29_0p02_jam_configurations':R['tolerance']['summary'][0]['jam_configs'],
 'R29_0p05_jam_configurations':R['tolerance']['summary'][1]['jam_configs'],
 'R29_old_outboard_A_key_collision_at_0p05':4,
 'R29_new_outboard_A_key_collision_at_0p05':R['clearance']['clashes_at_plus_0p05'],
 'R29_STEP_count':R['STEP_manifest']['scene_count'],
 'R29_R28_joint_fault_escape_remaining':R['faults']['inherited_original_fault_escape_counterexamples'],
 'R29_presence_plunger_rejected':True,
 'R29_pin_slot_clearance_mm':R['tolerance']['nominal_webs']['pin_slot_radial_clearance_mm'],
 'R29_chassis_front_hypothetical_min_margin_mm':R['tolerance']['nominal_webs']['front_Y_wall_after_0p025mm_cut_mm'],
 'R29_still_allows_closed_shutter_0p07_extension_without_nominal_interference':all(x['closed_gate_clash_mm3']<1e-8 for x in R['faults']['closed_gate_lost_motion'] if x['extension_mm']==.07),
 'R29_removed_original_carrier_ear_material_mm3_per_side':R['ear_section']['rows'][0]['removed_original_material_mm3'],
 'real_retention_spring_stroke_force_torque_FEAGDT_unqualified':True,
 'no_A_key_capture_unsafe':True,
 'real_battery_power_signal_USB_isolation_bench_test_missing':True,
 'OEM_OLED_full_dimensions_dynamic_radius_lifetime_data_missing':True,
 'manufacturing_go':False,
 'disclaimer':'The passed cases detect research geometry and retained faults; they are not safety or production authorization.',
 'report_sha256':{k:hashlib.sha256((V/f'R29_{k}.json').read_bytes()).hexdigest() for k in R}
}
assert out['geometry_recalculation_succeeded'] and out['inherited_reexecution_succeeded']
(V/'R29_results.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
print('R29 ATTEST',out['regression_tests_total'],'tests, R28 prior 374 unchanged, NO MANUFACTURING GO')
