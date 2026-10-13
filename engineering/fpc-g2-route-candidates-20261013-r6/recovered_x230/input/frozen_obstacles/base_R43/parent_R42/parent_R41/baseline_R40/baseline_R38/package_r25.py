"""Strict R25 reproducible offline CAD engineering package with SHA256 and rerun receipts."""
from __future__ import annotations
import re,json,hashlib,zipfile,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=ROOT/'baseline_R24'
DEST=ROOT.parent/'RAZR_SLIDE_R25_engineering_package_20261011.zip'
SHA=ROOT.parent/'RAZR_SLIDE_R25_engineering_package_20261011.sha256'
OUT=ROOT.parent/'R25_results_20261011.json'
AUDIT_OUT=ROOT.parent/'R25_hardgate_audit_20261011.md'
CHECKS=[('R21',BASE/'verification'/'R24_R21_baseline.log',28),
 ('R22',BASE/'verification'/'R24_R22_baseline.log',37),
 ('R22_ADVERSARIAL',BASE/'verification'/'R24_R22_adversarial.log',11),
 ('R23',BASE/'verification'/'R24_R23_baseline.log',22),
 ('R24',BASE/'verification'/'R24_new_25.log',25),
 ('R25',ROOT/'verification'/'R25_new_30.log',30)]

def sha_file(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()

def main():
 for f in [ROOT/'verification'/'R25_CAPTURE_NOT_AN_ACTUAL_CERTIFICATE.txt']:
  if f.exists():raise RuntimeError('unrecognized fabricated certificate')
 assert 'R24 SOFTWARE/CAD REPRO PASSED' in (ROOT/'verification'/'R25_R24_FULL_REGR_RUN.log').read_text()
 assert 'R25 OFFLINE REPRO SUCCESS' in (ROOT/'verification'/'R25_FINAL_FULL_REGR_RUN.log').read_text()
 passes={}
 for title,path,n in CHECKS:
  raw=path.read_text()
  nums=re.findall(r'Ran (\d+) tests? in ',raw)
  assert nums and int(nums[-1])==n,(title,nums,n)
  assert re.search(r'\bOK\b',raw),title
  passes[title]=int(nums[-1])
 assert sum(passes.values())==153
 outputs={}
 for x in ['capture','gate','integration','dynamic','faults','tolerance','STEP_manifest']:
  data=json.loads((ROOT/'verification'/('R25_'+x+'.json')).read_text())
  assert data['manufacturing_go'] is False,x
  outputs[x]=data
 assert outputs['capture']['retention_witness_count']==4
 assert outputs['gate']['naive_open_copy_rejected']
 assert outputs['faults']['OPEN_old_early_fault_remains_unsafe']
 assert outputs['integration']['B_shell_R25_solids']==1
 assert outputs['tolerance']['groups'][1]['clashes_at_seat']>0
 scenes=outputs['STEP_manifest']['scenes']
 assert len(scenes)==7
 for scene in scenes:
  f=ROOT/'cad'/scene['STEP']
  assert f.exists() and sha_file(f)==scene['sha256']
  assert scene['parts']==scene['reimport_valid_solids']
 evidence=dict(
    revision='R25 2026-10-11 research-level CAD and faults: ABSOLUTE NO MANUFACTURING RELEASE',
    run_recreated_from_source=True,
    units=dict(length='mm',volume='mm3'),
    inherited_test_counts={k:v for k,v in passes.items() if k!='R25'},
    new_R25_tests=passes['R25'],total_tests_all_pass=sum(passes.values()),
    candidate_captive_pawls=4,
    positive_retention_0p05mm_nominal_witnesses=outputs['capture']['retention_witness_count'],
    STOW_second_stage_stops_unintended_0p8_carrier_extension=outputs['gate']['stow_ext_0p8_is_blocked_when_shutter_closed'],
    STOW_pawl_prevent_manual_gate_shift_first_0p1mm=outputs['gate']['parked_pawl_physically_vetoes_manual_shutter_motion'],
    OPEN_stage2_unbuilt=outputs['integration']['open_port_second_stage_not_in_CAD'],
    OPEN_old_early_release_danger_remains=outputs['faults']['OPEN_old_early_fault_remains_unsafe'],
    OPEN_naive_reuse_outside_B_mm=outputs['gate']['naive_open_copy_intrudes_outside_equal_envelope_mm'],
    OPEN_parked_pawl_outer_shell_margin_mm=outputs['gate']['open_capture_pawl_min_outer_shell_edge_margin_mm'],
    B_shell_new_cut_vs_R24_mm3=outputs['integration']['B_cut_vs_R24_mm3'],
    B_valid_one_solid=outputs['integration']['B_shell_R25_valid'] and outputs['integration']['B_shell_R25_solids']==1,
    nominal_pose_samples=outputs['dynamic']['samples'],
    CAD_fault_samples_new=outputs['faults']['total_new_fault_samples'],
    tolerated_offset_samples_not_OEM=sum(x['sample_count'] for x in outputs['tolerance']['groups']),
    R25_steps_reexported_and_reimported=len(scenes),
    false_capture_allowed_far_from_A=outputs['capture']['pawl_can_be_activated_without_A_present'],
    L_R_fracture_and_common_failure_unqualified=True,
    B_rail_OEM_strength_unknown=True,real_mount_and_springs_unbuilt=True,
    actual_power_isolation_unknown=True,te_signal_is_not_main_power=True,
    actual_OLED_supplier_qualification_unknown=True,
    overall_manufacturing_go=False,mechanical_manufacturing_go=False,electrical_go=False,OLED_go=False)
 # Evidence generated before manifest so it is included in archive.
 (ROOT/'audit'/'R25_independent_attestation.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
 OUT.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
 shutil.copy2(ROOT/'audit'/'R25_硬门槛审查.md',AUDIT_OUT)
 # Do not package volatile pycache artifacts; every CAD/check/report/log included.
 allfiles=sorted(p for p in ROOT.rglob('*') if p.is_file() and
  '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo') and p.name!='R25_SHA256_MANIFEST.json')
 manifest={p.relative_to(ROOT).as_posix():dict(sha256=sha_file(p),bytes=p.stat().st_size) for p in allfiles}
 (ROOT/'audit'/'R25_SHA256_MANIFEST.json').write_text(json.dumps(dict(
  manifest_scope='all archived payload except this manifest',
  algorithm='SHA256',files=manifest),ensure_ascii=False,indent=2)+'\n')
 with zipfile.ZipFile(DEST,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
  for p in allfiles+[ROOT/'audit'/'R25_SHA256_MANIFEST.json']:
   z.write(p,'RAZR_SLIDE_R25/'+p.relative_to(ROOT).as_posix())
 with zipfile.ZipFile(DEST) as z:
  assert z.testzip() is None
  members=set(z.namelist())
  assert len(members)==len(allfiles)+1
  m=json.loads(z.read('RAZR_SLIDE_R25/audit/R25_SHA256_MANIFEST.json'))['files']
  for p,metadata in m.items():
   content=z.read('RAZR_SLIDE_R25/'+p)
   assert len(content)==metadata['bytes']
   assert hashlib.sha256(content).hexdigest()==metadata['sha256'],p
 SHA.write_text(sha_file(DEST)+'  '+DEST.name+'\n')
 print(json.dumps({'total_unit_tests':sum(passes.values()),'files_in_archive':len(members),
     'ZIP':str(DEST),'bytes':DEST.stat().st_size,'SHA256':sha_file(DEST),
     'STEP':len(scenes),'manufacturing_go':False},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
