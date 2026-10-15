"""Research receipts: verify the frozen ancestry, new negative CAD witnesses and actual test logs.
Does not issue device manufacturing, OEM, medical or electrical certification.
"""
import json,re,hashlib,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run():
 parent=ROOT/'baseline/RAZR_SLIDE_R40_verified_engineering_package_20261012.zip'
 assert sha(parent)=='8df51e8e2c7a8c2733ddaa541eba9e85124d75d33c1a5e7b071fd1ec1f4db7ec'
 with zipfile.ZipFile(parent) as z:assert len(z.namelist())==57 and z.testzip() is None
 p=json.loads((ROOT/'verification/R41_parent_fresh.json').read_text())
 assert p['parent_fresh_test_total']==766 and all(p['parents']['exit_'+s]==0 for s in ('R21_R38','R39','R40'))
 log=(ROOT/'verification/R41_new_tests.log').read_text()
 match=re.search(r'Ran\s+(\d+)\s+tests?',log)
 assert match and int(match.group(1))==42 and log.strip().endswith('OK')
 assert (ROOT/'verification/R41_new_exit.txt').read_text().strip()=='0'
 occ=json.loads((ROOT/'verification/R41_OCC_layouts.json').read_text())
 side=json.loads((ROOT/'verification/R41_sidewall_budget.json').read_text())
 motion=json.loads((ROOT/'verification/R41_motion_budget.json').read_text())
 assert occ['total_OCC_ribbon_poses']==15 and len(occ['rows'])==15
 assert len(occ['all_named_collision_free_and_within_research_XZ_envelope_variants'])==0
 assert motion['math_cases']==363 and motion['motion_positions_per_layout']==121
 assert side['valid_sweep'] and not side['research_Z_bounds_fits']
 ghosts=[x['ghost_STEP'] for x in occ['rows'] if 'ghost_STEP' in x]+[side['STEP']]
 assert len(ghosts)==5
 for step in ghosts:
  path=ROOT/'cad'/step['name']
  # The freeze proof checks the original generated STEP hash. If STEP has been
  # regenerated, r41_occ_layouts/sidewall write new hashes first.
  assert path.is_file() and sha(path)==step['sha256']
 assert not any([occ['manufacturing_go'],side['manufacturing_go'],motion['manufacturing_go']])
 out={'revision':'R41 research CAD counterexample hardgate','parent_R40_original_SHA256':sha(parent),
       'parent_R40_members':57,'actual_fresh_parent_tests':766,
       'R41_new_tests':42,'total_fresh_research_tests':808,
       'full_mathematical_two_axis_positions_per_layout':121,'math_scenarios':363,
       'centreline_spatial_coarse_layouts':72,'centreline_spatial_fine_layouts':35,
       'OCC_ribbon_pose_count':15,'research_ghost_STEP_count':5,
       'sidewall_single_transverse_U_does_not_fit':True,
       'all_three_tested_layouts_candidate_go':False,
       'real_OEM/OLED/FPC_dynamic_permission_missing':True,
       'USB_and_power_bench_missing':True,'legacy_mechanical_36_of_64_hazards_unresolved':True,
       'real_manufacturing_go':False}
 (ROOT/'R41_results_20261013.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(out,ensure_ascii=False,indent=2));return out
if __name__=='__main__':run()
