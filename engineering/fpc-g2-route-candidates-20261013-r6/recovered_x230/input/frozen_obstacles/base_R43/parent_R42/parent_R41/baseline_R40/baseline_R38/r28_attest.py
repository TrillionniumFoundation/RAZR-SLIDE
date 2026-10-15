"""Independent bounded R28 CAD provenance / test attest. NOT CE/FMEA certification."""
from __future__ import annotations
import json,hashlib,re,sys,platform,importlib.metadata
from pathlib import Path
import cadquery as cq
from r25_capture import ROOT
V=ROOT/'verification'
EXPECTED={'R21':28,'R22':37,'R22_adversarial':11,'R23':22,'R24':25,
          'R25':30,'R26':38,'R27':35,'R28':42}
counts={}
for label,n in EXPECTED.items():
  p=V/(f'R28_new_42.log' if label=='R28' else f'R28_inherited_{label}.log')
  contents=p.read_text(errors='replace')
  m=re.search(r'Ran\s+(\d+)\s+tests',contents)
  if not m or int(m.group(1))!=n or not contents.rstrip().endswith('OK'):
   raise AssertionError(f'{label} log missing exact number and OK: {p}')
  counts[label]=dict(tests=n,log=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())

# R27 origin is frozen by a 328-item SHA manifest plus the manifest itself.
prior=json.loads((ROOT/'audit/R27_SHA256_MANIFEST.json').read_text())
assert len(prior['files'])==328
for old in prior['files']:
 p=ROOT/old['path']
 if not p.is_file() or p.stat().st_size!=old['size_bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=old['sha256']:
  raise AssertionError(f'R27 baseline changed: {p}')

R={name:json.loads((V/f'R28_{name}.json').read_text()) for name in ('integration','dynamic','faults','tolerance','presence','clearance','STEP_manifest')}
assert all(data['manufacturing_go'] is False for data in R.values())
assert R['integration']['A_valid_single_body'] and R['integration']['B_valid_single_body']
assert R['dynamic']['pose_count']==10 and R['dynamic']['unexpected_collision_count']==0
assert R['faults']['trajectory_samples']==38
assert R['faults']['original_fault_escape_counterexamples']==36
assert R['tolerance']['samples']==108 and R['tolerance']['OCC_checks']==324
assert R['tolerance']['groups'][0]['reported_nominal_coupled_motion_jam']==0
assert R['tolerance']['groups'][1]['reported_nominal_coupled_motion_jam']==50
assert R['presence']['raised_plunger_exceeds_B_nominal_envelope_by_mm']==.71
assert R['clearance']['outward_0p05_nominal_A_collision_cases']==4
assert R['STEP_manifest']['scene_count']==6
for s in R['STEP_manifest']['scenes']:
 p=ROOT/'cad'/s['filename']
 assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==s['sha256']
 assert s['valid_imported_solids']==s['exported_parts']
for filename in ('R28_A_KEYED_UNCHANGED.brep','R28_B_PULLOUT_CAM_RELIEVED.brep'):
 sh=cq.importers.importBrep(str(ROOT/'cad'/filename)).val()
 assert sh.isValid() and len(sh.Solids())==1

report=dict(
 revision='R28 research OCC evidence, not a manufacturing clearance',
 provenance='R27 prior 328 item SHA archive manifest verified unchanged',
 prior_R27_manifest_entry_count=len(prior['files']),
 direct_unittest_receipts=counts,
 all_legacy_and_R28_test_count=sum(EXPECTED.values()),
 all_logs_exact_expected_case_count_and_OK=True,
 OCC_two_BRep_solids_valid=True,
 R28_A_B_BRep_SHA256={name:hashlib.sha256((ROOT/'cad'/name).read_bytes()).hexdigest() for name in ('R28_A_KEYED_UNCHANGED.brep','R28_B_PULLOUT_CAM_RELIEVED.brep')},
 exact_R28_facts=dict(
  B_cut_mm3=R['integration']['additional_B_removed_mm3'],
  nominal_gate_pin_path_samples=R['faults']['trajectory_samples'],
  full_reference_poses=R['dynamic']['pose_count'],
  hypothetical_relative_XYZ_samples=R['tolerance']['samples'],
  hypothetical_0p02_jam_cases=R['tolerance']['groups'][0]['reported_nominal_coupled_motion_jam'],
  hypothetical_0p05_jam_cases=R['tolerance']['groups'][1]['reported_nominal_coupled_motion_jam'],
  R27_inherited_dual_failure_escapes=R['faults']['original_fault_escape_counterexamples'],
  raised_presence_plunger_envelope_overhang_mm=R['presence']['raised_plunger_exceeds_B_nominal_envelope_by_mm'],
  nominal_cam_plate_thickness_mm=R['clearance']['original_outboard_plate_X_thickness_mm'],
  nominal_min_cam_slot_edge_web_mm=R['clearance']['planar_slot_min_residual_Z_web_mm'],
  nominal_after_relief_front_B_margin_mm=R['clearance']['after_nominal_pocket_front_B_relief_margin_mm'],
  extra_A_key_collision_at_0p05=R['clearance']['outward_0p05_nominal_A_collision_cases'],
  R28_STEP_count=R['STEP_manifest']['scene_count']),
 external_OLED_vendor_NDA_and_genuine_full_package_data_missing=True,
 power_signal_USB_and_BMS_electrical_hardware_validation_missing=True,
 no_spring_gear_axial_guide_FEABearing_or_life_measurement=True,
 R28_manufacturing_go=False,manufacturing_go=False,
 platform=dict(python=platform.python_version(),cadquery=importlib.metadata.version('cadquery')),
 input_artifact_sha256={name:hashlib.sha256((V/f'R28_{name}.json').read_bytes()).hexdigest() for name in R}
)
(V/'R28_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('R28 ATTEST',report['all_legacy_and_R28_test_count'],'through exact log receipts; manufacture NO-GO')
