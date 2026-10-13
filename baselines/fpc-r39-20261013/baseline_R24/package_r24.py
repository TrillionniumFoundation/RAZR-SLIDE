"""Reproducible R24 ZIP, per-file sha256, standalone summary; refuse incomplete gates."""
from __future__ import annotations
import hashlib,json,zipfile,shutil,re,sys
from pathlib import Path
import cadquery as cq
ROOT=Path(__file__).resolve().parent
TOP=ROOT.parent
CHECKS={'R24_R21_baseline.log':28,'R24_R22_baseline.log':37,
        'R24_R22_adversarial.log':11,'R24_R23_baseline.log':22,
        'R24_new_25.log':25}
for file,count in CHECKS.items():
 content=(ROOT/'verification'/file).read_text()
 assert re.search(rf'Ran {count} tests',content),file
 assert re.search(r'\nOK\s*$',content),file
full=(ROOT/'verification'/'R24_FINAL_FULL_RUN.log').read_text()
assert 'R24 SOFTWARE/CAD REPRO PASSED; MANUFACTURING GO: FALSE' in full,'final run incomplete'
assert sum(CHECKS.values())==123
m=json.loads((ROOT/'verification'/'R24_mechanics.json').read_text())
i=json.loads((ROOT/'verification'/'R24_integration.json').read_text())
d=json.loads((ROOT/'verification'/'R24_dynamic.json').read_text())
f=json.loads((ROOT/'verification'/'R24_fault_matrix.json').read_text())
l=json.loads((ROOT/'verification'/'R24_longlap_rejected.json').read_text())
w=json.loads((ROOT/'verification'/'R24_side_rail_web.json').read_text())
e=json.loads((ROOT/'verification'/'R24_STEP_manifest.json').read_text())
assert i['sampled_unexpected_clash_count']==0
assert d['unexpected_interference_count']==0
assert f['current_R24_nominal_cam_fails_strict_seat_interlock']
assert f['inherited_states']['R24_both_fault_open_still_escapes']==56
assert abs(l['clash_with_R16_A_side_lock_pin_at_OPEN_mm3']-.461002)<1e-6
assert abs(w['min_nominal_remaining_sidewall_web_mm']-.22)<1e-9
assert e['exports']==8
for s in e['scenes']:
 fn=ROOT/'cad'/s['STEP']
 assert fn.exists() and s['parts']==s['reimport_solids']==32
 assert hashlib.sha256(fn.read_bytes()).hexdigest()==s['SHA256']

attest={'revision':'R24','baseline_revision':'R23','timestamp_UTC':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
 'cadquery_version':cq.__version__,'python_version':sys.version.split()[0],
 'unit_test_batches':CHECKS,'unit_tests_total':123,
 'physical_A_keys':4,'STEP_valid_exports':8,'parts_per_STEP':32,
 'R24_B_cut_volume_mm3':i['B_removed_R23_mm3'],
 'nominal_side_rail_web_mm':w['min_nominal_remaining_sidewall_web_mm'],
 'early_release_without_R24_fault':f['current_R24_nominal_cam_fails_strict_seat_interlock'],
 'fault_states':f['inherited_states']['states'],
 'unseated_states':f['inherited_states']['unseated'],
 'inherited_unsafe_escapes_with_all_false_open':f['inherited_states']['R24_both_fault_open_still_escapes'],
 'full_regression_entrypoint':'./r24_checks.sh',
 'OEM_hardware_test_count':0,'battery_power_production_qualified':False,
 'OEM_OLED_spec_approved':False,'manufacturing_go':False}
(ROOT/'audit'/'R24_independent_attestation.json').write_text(json.dumps(attest,ensure_ascii=False,indent=2)+'\n')
EXCLUDE={'__pycache__','.DS_Store'}
files=sorted(f for f in ROOT.rglob('*') if f.is_file() and not any(x in EXCLUDE for x in f.parts)
             and not f.name.endswith('.pyc') and f.name!='R24_SHA256_MANIFEST.json')
rows=[{'relative_path':str(x.relative_to(ROOT)),'bytes':x.stat().st_size,'sha256':hashlib.sha256(x.read_bytes()).hexdigest()} for x in files]
manifest={'revision':'R24','total_files_without_manifest':len(rows),'entries':rows,'manufacturing_go':False}
manp=ROOT/'audit'/'R24_SHA256_MANIFEST.json'
manp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
files.append(manp)
zipf=TOP/'RAZR_SLIDE_R24_engineering_package_20261010.zip'
with zipfile.ZipFile(zipf,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for file in files:z.write(file,arcname=str(Path(ROOT.name)/file.relative_to(ROOT)))
with zipfile.ZipFile(zipf) as z:
 assert z.testzip() is None
 for rec in rows:
  raw=z.read(str(Path(ROOT.name)/rec['relative_path']))
  assert hashlib.sha256(raw).hexdigest()==rec['sha256']
 assert len(z.namelist())==len(files)
digest=hashlib.sha256(zipf.read_bytes()).hexdigest()
shafile=TOP/'RAZR_SLIDE_R24_engineering_package_20261010.sha256'
shafile.write_text(digest+'  '+zipf.name+'\n')
shutil.copy2(ROOT/'audit'/'R24_硬门槛对抗审计.md',TOP/'R24_hardgate_audit_20261010.md')
shutil.copy2(ROOT/'README_先读_R24.md',TOP/'R24_README_20261010.md')
shutil.copy2(ROOT/'verification'/'R24_fault_matrix.json',TOP/'R24_fault_matrix_20261010.json')
shutil.copy2(ROOT/'verification'/'R24_integration.json',TOP/'R24_integration_results_20261010.json')
(TOP/'R24_results_20261010.json').write_text(json.dumps(attest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'zip':str(zipf),'zip_bytes':zipf.stat().st_size,'sha256':digest,'files_in_zip':len(files),'test_total':123,
'final_release':False},ensure_ascii=False,indent=2))
