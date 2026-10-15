"""Run the existing full suite without changing its commands or inputs.

The three disjoint selections cover every configured suite exactly once.
The native branch regenerates the CURRENT 3 mm assembly, not the 4 mm study.
"""
from pathlib import Path
import concurrent.futures as futures
import hashlib
import json
import os
import subprocess
import time

R=Path('/home/qian-qi/RAZR-SLIDE-thread-validation-20261015')
O=Path('/tmp/razr-thread-validation-20261015')
F='f8cdce7debf7824d0c2ae04ee51dc3e73697941f'
PY=R/'.venv/bin/python'
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()==F
assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain','-uno'],text=True)
config=json.loads((R/'tools/test_suites.json').read_text())
assert config['minimum_total_tests']==736 and len(config['suites'])==31
old=json.loads(Path('/tmp/razr-frame-anchor-20261015/unit704/report.json').read_text())
durations={x['id']:x.get('seconds',1.) for x in old['suite_results']}
groups=[[],[],[]];cost=[0.,0.,0.]
for s in sorted(config['suites'],key=lambda s:-durations.get(s['id'],1.)):
    index=min(range(3),key=lambda i:cost[i]);groups[index].append(s['id']);cost[index]+=durations.get(s['id'],1.)
assert sorted(sum(groups,[]))==sorted(s['id'] for s in config['suites'])
env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
(O/'groups.json').write_text(json.dumps(groups,indent=2)+'\n')

def execute(label,commands,timeout):
    started=time.monotonic();code=0
    with (O/(label+'.log')).open('x') as log:
        for cmd in commands:
            print('START',label,flush=True)
            try:
                proc=subprocess.run(['nice','-n','10',str(PY),'-B',*map(str,cmd)],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
                code=proc.returncode
            except subprocess.TimeoutExpired:
                code='TIMEOUT'
            if code!=0:break
    (O/(label+'.exit')).write_text(str(code)+'\n')
    print('TERMINAL',label,code,'seconds',round(time.monotonic()-started,2),flush=True)
    return code

jobs={}
with futures.ThreadPoolExecutor(max_workers=4) as pool:
    for i,group in enumerate(groups):
        cmd=['tools/verify.py','--output',O/f'unit/group-{i}']
        for name in group:cmd.extend(['--suite',name])
        jobs[f'group-{i}']=pool.submit(execute,f'group-{i}',[cmd],1500)
    jobs['native']=pool.submit(execute,'native',[
        ['integration/frame_nut_anchor.py','--baseline','/tmp/razr-panel-shear-20261015/native-v2/manifest.json','--output',O/'native'],
        ['integration/verify_frame_nut_anchor.py','--baseline','/tmp/razr-panel-shear-20261015/native-v2/manifest.json','--manifest',O/'native/manifest.json','--output',O/'native/verification.json','--full'],
        ['integration/frame_thread_budget.py','--inputs','integration/frame_thread_actual_inputs.json','--output',O/'actual-budget.json']],1200)
    results={name:job.result() for name,job in jobs.items()}
reports=[json.loads((O/f'unit/group-{i}/report.json').read_text()) for i in range(3)]
first=reports[0];rows=[s for report in reports for s in report['suite_results']]
ids=[s['id'] for s in rows]
valid=sorted(ids)==sorted(s['id'] for s in config['suites']) and len(ids)==len(set(ids))
valid=valid and all(r['base_commit']==F and r['passed'] and r['source_bytes_unchanged'] and not r['changed_during_tests'] and not r['syntax_errors'] and r['source_hashes_before']==first['source_hashes_before'] and r['source_hashes_after']==first['source_hashes_after'] for r in reports)
count=sum(x['tests_run'] for x in rows)
valid=valid and count==736 and all(results[f'group-{i}']==0 for i in range(3))
merged={**first,'scope':'all_current_unit_suites','suite_results':rows,'tests_run':count,'passed':bool(valid),'execution':'three disjoint unmodified canonical --suite selections; no old result reuse','canonical_groups':groups,'canonical_report_paths':[f'group-{i}/report.json' for i in range(3)]}
(O/'unit/report.json').write_text(json.dumps(merged,indent=2)+'\n')
(O/'unit736.exit').write_text('0\n' if valid else '1\n')
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()==F
print('FULL_CURRENT_UNIT',count,len(rows),valid,'NATIVE_EXIT',results['native'],flush=True)
raise SystemExit(0 if valid and results['native']==0 else 1)
