"""Attestation binds actual fresh parent regression receipts to R42 results.
It does NOT infer manufacturing safety from tests that deliberately detect faults.
"""
import json,hashlib,re,sys,subprocess,os,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent


def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def run():
 p=ROOT/'parent_R41/baseline_R40/verification/R40_inherited_results.json'
 # We re-routed the wrapper outputs to R42 verification, not parent_R40.
 p=ROOT/'verification/R42_parent_test_receipts/R40_inherited_results.json'
 obj=json.loads(p.read_text())
 assert obj['success'] is True and obj['actual_fresh_parent_reexecuted']==697
 assert all(x['success'] and x['exit_code']==0 for x in obj['rows'])
 for x in obj['rows']:
  path=p.parent/x['log'];assert sha(path)==x['log_sha256']
 cases=[('R39',31,ROOT,'r42_run_parent_r39.py'),
        ('R40',38,ROOT/'parent_R41/baseline_R40','test_r40.py'),
        ('R41',42,ROOT/'parent_R41','test_r41.py'),
        ('R42',38,ROOT,'test_r42.py')]
 rows=[]
 for name,n,cwd,script in cases:
  cmd=([sys.executable,'-u',str(cwd/script)] if name=='R39' else [sys.executable,'-m','unittest','-q',script])
  t=time.monotonic()
  p2=subprocess.run(cmd,cwd=cwd,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=150)
  logs=(p2.stdout or '')+(p2.stderr or '')
  path=ROOT/'verification'/('R42_fresh_'+name+'.log');path.write_text(logs)
  if name=='R39':
   # r40_retest_r39 validates explicit 'Ran 31 tests OK' in its own log.
   testlog=(ROOT/'parent_R41/baseline_R40/verification/R40_fresh_R39.log').read_text()
   assert re.search(r'Ran\s+31\s+tests?',testlog) and testlog.rstrip().endswith('OK')
  else:
   assert re.search(r'Ran\s+'+str(n)+r'\s+tests?',logs), (name,logs[-1000:])
   assert logs.strip().endswith('OK')
  assert p2.returncode==0, (name,p2.returncode,logs[-500:])
  rows.append({'name':name,'tests':n,'exit_code':p2.returncode,
               'duration_s':round(time.monotonic()-t,2),'log':str(path.relative_to(ROOT)),'sha256':sha(path)})
  print(name,n,'passed',flush=True)
 total=697+sum(x['tests'] for x in rows)
 assert total==846
 res={'revision':'R42', 'frozen_parent_R41_full_zip_sha256':sha(ROOT/'baseline/RAZR_SLIDE_R41_FPC_full_verified_20261013.zip'),
      'R21_R38_independent_697_tests':697,'R21_R38_parent_groups':len(obj['rows']),
      'other_fresh_test_groups':rows,'fresh_total_tests':total,
      'all_fresh_group_exit_codes_zero':True,
      'positive_tests_include_correct_detection_of_hazards':True,
      'R42_manufacturing_go':False}
 assert res['frozen_parent_R41_full_zip_sha256']=='f0be97f2661a59d9db87adca18ecc4d961dcb6142b65f9a17b0f452b461dbef6'
 (ROOT/'verification/R42_attest.json').write_text(json.dumps(res,indent=2,ensure_ascii=False)+'\n')
 return res
if __name__=='__main__':print(json.dumps(run(),indent=2,ensure_ascii=False))
