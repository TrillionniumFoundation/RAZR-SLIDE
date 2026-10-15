"""R40 check raw test receipts, negative CAD evidence and frozen ancestor digests.
Never interprets a passing rejection test as hardware manufacturing approval.
"""
import json,re,hashlib,zipfile
from pathlib import Path
from r40_motion import ROOT

def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(f):return json.loads((ROOT/'verification'/f).read_text())
def run():
 original=ROOT/'baseline/RAZR_SLIDE_R39_FPC_motion_hardgate_20261012.zip'
 original_hash='6eb43c691f7ec900f63006f837667c55cbf9137ac0a49067a93e61f12e14a4fd'
 assert sha(original)==original_hash
 with zipfile.ZipFile(original) as z:
  assert z.testzip() is None and len(z.namelist())==37
  with zipfile.ZipFile(__import__('io').BytesIO(z.read('baseline/RAZR_SLIDE_R38_verified_engineering_package_20261011.zip'))) as zz:
   assert len(zz.namelist())==1094
 inherited=load('R40_inherited_results.json')
 assert inherited['success'] and inherited['actual_fresh_parent_reexecuted']==697 and inherited['groups']==19
 for row in inherited['rows']:
  t=(ROOT/'verification'/row['log']).read_text()
  assert sha(ROOT/'verification'/row['log'])==row['log_sha256']
  m=re.search(r'Ran\s+(\d+)\s+tests?',t)
  assert row['success'] and row['exit_code']==0 and m and int(m.group(1))==row['expected_tests']
  assert t.rstrip().endswith('OK')
 r39=(ROOT/'verification/R40_fresh_R39.log').read_text()
 assert re.search(r'Ran\s+31\s+tests?',r39) and r39.rstrip().endswith('OK')
 new=(ROOT/'verification/R40_test_stderr.log').read_text()
 assert re.search(r'Ran\s+38\s+tests?',new) and new.rstrip().endswith('OK')
 math=load('R40_motion.json');occ=load('R40_OCC.json');cut=load('R40_pocket.json');fault=load('R40_faults.json')
 assert math['total_parameterized_scenarios']==1089 and len(math['cases'])==9
 assert occ['valid_ribbon_sweeps']==5 and occ['collision_free_valid_sweeps']==0 and occ['step_count']==3
 assert cut['remaining_B_valid'] and cut['remaining_B_solids']==1 and cut['this_CAD_cut_DOES_NOT_authorize_OEM_core_changes']
 assert abs(cut['hypothetical_B_core_removed_mm3']-38.99386693)<1e-6
 assert fault['all_gates_hold'] and not fault['manufacturing_go']
 for row in occ['rows']:
  if row['STEP']:
   p=ROOT/'cad'/row['STEP']['name']
   assert sha(p)==row['STEP']['sha256']
 out={'revision':'R40 inboard rolling U; mathematical pass, interference NO-GO',
  'R39_baseline_zip_sha256':original_hash,'R39_baseline_zip_members':37,'R38_embedded_zip_members':1094,
  'fresh_inherited_R21_to_R38_tests':697,'fresh_R39_tests':31,'fresh_new_R40_tests':38,
  'total_fresh_reexecuted_research_tests':766,
  'real_two_stage_positions':121,'parameterized_configs':1089,'math_candidate_R_mm':16.5,'math_candidate_L_mm':119,
  'min_centerline_R_mm':min(x['min_R_mm'] for x in math['cases'] if x['radius']==16.5 and x['length']==119.),
  'swept_OCC_samples':5,'valid_sweeps':5,'collision_free_sweeps':0,
  'proposed_guide_y_slide_mm':fault['guide_required_y_travel_slide_mm'],
  'proposed_guide_y_dock_mm':fault['guide_required_y_shift_dock_mm'],
  'relocated_B_header_x_delta_mm':-32.7,
  'B_5_pose_unauthorized_material_removed_mm3':cut['hypothetical_B_core_removed_mm3'],
  'GHOST_steps':3,'R38_parent_mechanical_unsafe_36_of_64_unchanged':True,
  'three_power_PCB_bypass_categories_unchanged':True,
  'OLED_collision_study_not_VENDOR_approved':True,'real_FPC_installed':False,
  'OEM_core_cut_permission':False,'manufacturing_go':False}
 (ROOT/'R40_results_20261012.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps(out,indent=2,ensure_ascii=False))
 return out
if __name__=='__main__':run()
