"""Read-only R42 research output verification; not product acceptance."""
from pathlib import Path
import json,csv,hashlib,zipfile
from r42_double_loop import calculate
from r42_topology_bounds import run as reverse
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()

def run():
 base=ROOT/'baseline/RAZR_SLIDE_R41_FPC_full_verified_20261013.zip'
 with base.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()=='f0be97f2661a59d9db87adca18ecc4d961dcb6142b65f9a17b0f452b461dbef6'
 with zipfile.ZipFile(base) as z:assert z.testzip() is None and len(z.namelist())==57
 m=json.loads((ROOT/'verification/R42_motion_budget.json').read_text());d=calculate(False)
 for key in ('math_cases','stages_positions','minimum_bend_centerline_radius_mm','maximum_abs_solved_length_error_mm'):
  assert m[key]==d[key]
 with (ROOT/'verification/R42_motion_121_positions.csv').open() as f:assert sum(1 for _ in csv.DictReader(f))==121
 bound=json.loads((ROOT/'verification/R42_reverse_U_bound.json').read_text())
 assert abs(bound['required_outside_Y_at_stow_mm']-reverse(False)['required_outside_Y_at_stow_mm'])<1e-9
 j=json.loads((ROOT/'verification/R42_OCC_two_flexes.json').read_text())
 assert j['complete'] and len(j['ghost_poses'])==9
 assert all(z['collision_count_above_1e_minus6']>0 and z['two_ribbons_nominal_intersection_mm3']>1e-6 for z in j['ghost_poses'])
 assert all(z['collision_count_above_1e_minus6']>0 for z in j['ghost_poses'])
 assert sum(bool(x.get('STEP_reimport')) for x in j['ghost_poses'])==3
 for x in j['ghost_poses']:
  if x.get('STEP_reimport'):
   p=ROOT/'cad'/x['STEP_reimport']['filename']
   with p.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==x['STEP_reimport']['sha256']
 ins=json.loads((ROOT/'verification/R42_interior_points.json').read_text())
 assert len(ins['rows'])==18 and all(v['interior_point_hits']['A']+v['interior_point_hits']['B']>0 for v in ins['rows'])
 a=json.loads((ROOT/'verification/R42_attest.json').read_text())
 assert a['fresh_total_tests']==846 and a['all_fresh_group_exit_codes_zero'] is True
 p=ROOT/'R42_results_20261013.json';r=json.loads(p.read_text())
 assert r['candidate_go'] is False and r['manufacturing_go'] is False and r['occ_poses_with_named_protected_collision']==9
 return {'verified_outputs':True,'parent_sha_verified':True,'math_cases':m['math_cases'],
  'sampled_Occ_poses':9,'all_poses_rejected':True,'GHOST_STEP_count':3,
  'actual_fresh_research_tests':846,'manufacturing_go':False}
if __name__=='__main__':print(json.dumps(run(),indent=2,ensure_ascii=False))
