"""Deterministic R22 artifact manifest: hashes of actual inputs and evidence files."""
from pathlib import Path
import json,hashlib,platform,sys
import cadquery as cq
from r22_mechanics import ROOT

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run():
 base=ROOT
 sources=sorted([*base.glob('r22_*.py'),base/'test_r22.py',base/'run_checks.sh',
  base/'README_先读_R22.md',*base.glob('vendor/*')])
 baselines=sorted([base/'baselines/R21/r21_geom.py',base/'baselines/R21/r21_verify.py',
  base/'baselines/R21/r21_export.py',base/'baselines/R21/test_r21.py',
  base/'baselines/R21/baselines/R20/r20_cad.py',base/'baselines/R21/baselines/R20/r20_model.py'])
 result=sorted([*base.glob('verification/R22_*_results.json'),
                base/'verification/R22_STEP_manifest.json'])
 steps=sorted(base.glob('cad/*.step'));viewer=sorted(base.glob('viewer/*.html'))
 artifacts=[p for p in (*sources,*baselines,*result,*steps,*viewer) if p.exists()]
 mech=json.loads((base/'verification/R22_mechanical_results.json').read_text())
 fault=json.loads((base/'verification/R22_fault_results.json').read_text())
 elec=json.loads((base/'verification/R22_electrical_results.json').read_text())
 oled=json.loads((base/'verification/R22_oled_results.json').read_text())
 manifest=dict(project='RAZR_SLIDE_R22',revision='R22',status='MANUFACTURING_NO_GO',
  retention='All numbers from actual CadQuery/OCC shell + ideal kinematic/protection logic; no hardware qualification',
  program_versions=dict(python=sys.version.split()[0],cadquery=cq.__version__),
  acceptance_scope=dict(R21_baseline_tests=28,
     R22_local_unit_tests=37,STEP_files_reimported=len(steps),
     R22_OLED_clearance_reference_mm=.319619,
     actual_extra_B_cut_mm3=mech['B_extra_removed_volume_mm3'],
     B_connected_valid=bool(mech['B_one_solid'] and mech['B_valid']),
     unqualified_mechanical_fault_cases=fault['ideal_fault_scan']['scenarios'],
     proxy_undocked_gaps=fault['ideal_fault_scan']['false_unlock_blocking_failures'],
     system_power_boolean_states_checked=elec['logic']['logic_states_checked'],
     logic_false_energization_cases=elec['logic']['logic_false_energization_failures']),
  release_conditions_met=False,
  actual_A_load_keys_and_springs_fitted=False,
  supplier_certified_7inch_OLED=False,
  cross_cabin_power_connector_qualified=False,
  OEM_real_TE_step_imported=False,
  hardware_durability_tested=False,
  list_of_sha256=[dict(path=str(p.relative_to(base)),sha256=sha(p),size_bytes=p.stat().st_size)
                  for p in artifacts]);
 target=base/'verification/R22_provenance_manifest.json';target.write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
 print('manifest',len(artifacts),'files, SHA256','status',manifest['status']);return manifest

if __name__=='__main__':run()
