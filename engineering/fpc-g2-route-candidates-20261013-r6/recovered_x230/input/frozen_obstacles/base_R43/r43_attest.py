#!/usr/bin/env python3
"""Attest R43 provenance and new negative-case receipts without granting safety approval."""
from pathlib import Path
import hashlib, json, re,zipfile
ROOT=Path(__file__).resolve().parent
V=ROOT/'verification';V.mkdir(exist_ok=True)
EXPECTED='4daf4f6cf63ffe3c4222c71726f66da4b99ae121410322954b41362fcee1f513'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run():
 parent=ROOT/'baseline/RAZR_SLIDE_R42_FPC_full_verified_20261013.zip'
 assert parent.exists() and sha(parent)==EXPECTED
 with zipfile.ZipFile(parent) as z:
  assert z.testzip() is None and len(z.namelist())==56
 path=V/'R43_new_tests.log';assert path.exists();s=path.read_text()
 # Some stdout versions prepend echo markers; each test must have a real Ran N tests / OK receipt.
 m=re.search(r'Ran (\d+) tests? in',s);assert m and int(m.group(1))==21 and re.search(r'^OK\s*$',s,re.M)
 screening=json.loads((V/'R43_shifted_2U_screen.json').read_text())
 occ=json.loads((V/'R43_OCC_2layout_counterexamples.json').read_text())
 bound=json.loads((V/'R43_sidewall_180deg_transverse_bound.json').read_text())
 gate=json.loads((V/'R43_vendor_gate.json').read_text())
 assert screening['layouts_tested']==182 and screening['zero_protected_core_point_hits_layouts']==0
 assert occ['poses_with_core_penetration']==6 and occ['STEP_count']==4
 assert all(not z['fits_necessary_transverse_span'] for z in bound['conditional_radii'] if z['assumed_radius_mm']>=16.5)
 assert not gate['manufacturing_go']
 ghost=[]
 for r in occ['evidence_poses']:
  if 'GHOST_STEP' in r:
   f=ROOT/'cad'/r['GHOST_STEP']['name'];assert f.exists() and sha(f)==r['GHOST_STEP']['sha256']
   ghost.append({'name':f.name,'size_bytes':f.stat().st_size,'sha256':sha(f),'reported_imported_solids':r['GHOST_STEP']['valid_solids']})
 full_log=V/'R43_full_parent_replay_ACTIVE.log'
 r42_attest=ROOT/'replay_R42_fresh/verification/R42_attest.json'
 if not r42_attest.exists():r42_attest=V/'R42_attest.json'  # current-turn source tree
 fresh_parent=False
 if __import__('os').environ.get('R43_FULL_PARENT_RUN')=='1' and full_log.exists() and r42_attest.exists():
  logfile=full_log.read_text();claim=json.loads(r42_attest.read_text())
  fresh_parent=bool('R42 research-only CAD replay complete.' in logfile and
      claim.get('fresh_total_tests')==846 and claim.get('all_fresh_group_exit_codes_zero'))
 receipts={'r42_immutable_parent_full_zip_sha256':EXPECTED,'r42_zip_members':56,
  'r42_full_fresh_tests_in_isolated_worktree':846 if fresh_parent else None,
  'r42_fresh_parent_log_sha256':sha(full_log) if fresh_parent else None,
  'r43_new_tests_fresh':21,'r43_new_tests_log_sha256':sha(path),
  'total_fresh_research_assertions_this_run':867 if fresh_parent else 21,
  'shifted_layouts':182,'zero_core_clear_on_point_screen':0,
  'volumetric_rejected_pose_count':6,'ghost_STEP':ghost,
  'test_success_includes_correct_detection_of_failures':True,
  'OEM_authorized_core_modifications':False,
  'dynamic_FPC_life_qualified':False,
  'candidate_go':False,'manufacturing_go':False}
 (V/'R43_attest.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in receipts.items() if k not in ('ghost_STEP',)},indent=2))
 return receipts
if __name__=='__main__':run()
