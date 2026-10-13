#!/usr/bin/env python3
"""Attest deterministic research evidence; never approve a wired/physical product."""
from pathlib import Path
import json,hashlib,re,zipfile
ROOT=Path(__file__).resolve().parent
E=ROOT/'evidence'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def get_test_count(p):
 s=p.read_text();m=re.search(r'Ran (\d+) tests? in',s)
 assert m and re.search(r'^OK\s*$',s,re.M),f'no success receipt in {p}'
 return int(m.group(1))
def run():
 source=ROOT/'baseline/RAZR_SLIDE_R43_FPC_full_verified_20261013.zip'
 assert sha(source)=='d79c33b2a0e8eae2d05c5dc318b442bdffb1420e5361e87e0317a4d9191de7a0'
 with zipfile.ZipFile(source) as z: assert z.testzip() is None and len(z.namelist())==33
 n43=get_test_count(E/'R44_fresh_R43_21_tests.log')
 nr44=get_test_count(E/'R44_new_tests.log')
 assert n43==21 and nr44==32,(n43,nr44)
 data=json.loads((E/'R44_rear_bypass_OCC.json').read_text())
 feed=json.loads((E/'R44_direct_feedthrough_rejected.json').read_text())
 assert len(data['rows'])==36 and len(feed['rows'])==3
 dense=json.loads((E/'R44_dense_121_OCC.json').read_text())
 assert dense['pose_count']==121 and dense['core_or_display_Occ_intersection_pose_count']==0
 assert not data['candidate_go'] and not data['manufacturing_go']
 ghosts=[]
 for row in data['rows']:
  if 'ghost_STEP' not in row:continue
  g=row['ghost_STEP'];p=ROOT/'cad'/g['filename'];assert sha(p)==g['sha256']
  ghosts.append({'file':p.name,'sha256':sha(p),'solids_original_import':g['valid_solids']})
 assert len(ghosts)==6
 rec={'revision':'R44 single rear bypass + direct feedthrough counterexamples',
   'R43_parent_full_zip_sha256':sha(source),'R43_parent_members':33,
   'inherited_R42_test_receipt_from_immutable_parent_not_reexecuted_this_turn':846,
   'fresh_R43_regression_tests_this_run':n43,'fresh_R44_tests_this_run':nr44,
   'fresh_test_count':n43+nr44,'cumulative_historical_research_test_count_including_frozen_R42':846+n43+nr44,
   'OCC_sweep_branch_poses':36,'additional_near_rear_dense_OCC_poses':121,'rear_out_of_envelope_poses':9,
   'NEAR_REAR_model_Occ_collision_free_poses':9,
   'feedthrough_negative_poses':3,'ghost_STEP':ghosts,
   'unconnected_back_loop_NOT_wiring_validated':True,'OEM_feedthrough_unapproved':True,
   'FPC_supplier_life_unqualified':True,'mechanical_force_retention_missing':True,
   'electrical_power_USB_OLED_missing':True,'known_R37_mechanical_36_of_64_unsafe_not_retested_or_closed':True,
   'legacy_power_three_singlepoint_bypasses_not_closed':True,
   'candidate_go':False,'manufacturing_go':False}
 (E/'R44_attestation.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n')
 return rec
if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
