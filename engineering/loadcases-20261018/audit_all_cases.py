"""Audit only terminal successful source fields, with explicit per-case controls."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
import json,subprocess,os,time
R=Path('/home/qian-qi/RAZR-SLIDE-loadcases-20261018');O=Path('/home/qian-qi/.local/share/razr-slide-evidence/loadcases-20261018')
plan=json.loads((R/'engineering/loadcases-20261018/EXPERIMENT_PLAN.json').read_text())
expected={x['id']:x for x in plan['cases']}
P=Path('/home/qian-qi/.local/share/razr-slide-evidence/rank-replay-20261018/current')
V='/home/qian-qi/.local/share/razr-slide-evidence/volume-convergence-20261017/volume-v3'
def work(label):
 src=O/label;dest=O/('audit-'+label);code=int((O/(label+'.exit')).read_text());report=src/'report.json'
 if code!=0 or not report.exists():return {'id':label,'passed':False,'audit_started':False,'source_exit':code}
 r=json.loads(report.read_text())
 if not r.get('passed'):return {'id':label,'passed':False,'audit_started':False,'source_exit':code,'source_passed':False}
 cmd=[str(R/'.venv/bin/python'),'-u','-B',str(O/'verify_original_case.py'),'--case-id',label,'--expected-target','1e-7','--run',str(src),'--volume',V,'--element-check',str(P/'independent-elements'),'--force-check',str(P/'projection-check-512'),'--output',str(dest)]
 (O/('audit-'+label+'-command.json')).write_text(json.dumps(cmd,indent=2)+'\n');print('AUDIT_START',label,flush=True)
 with (O/('audit-'+label+'.log')).open('w') as log:
  try:p=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=1000,env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','PYTHONPATH':'/home/qian-qi/.local/share/razr-slide-analysis/scikit-fem-12.0.2-20261017'});rc=p.returncode
  except subprocess.TimeoutExpired:rc=124
 (O/('audit-'+label+'.exit')).write_text(str(rc)+'\n');row={'id':label,'passed':False,'audit_started':True,'exit_code':rc}
 if rc==0:
  a=json.loads((dest/'report.json').read_text());assert a['passed'] and a['definition']==expected[label] and a['gap_tolerance_mm']==1e-7
  row.update(passed=True,minimum_bound=a['minimum_covered_bound_mm'],bolt_forces=a['bolt_forces_over_Epanel_mm2'])
 print('AUDIT_TERMINAL',label,rc,row['passed'],flush=True);return row
pending=set(expected);running={};rows=[];deadline=time.monotonic()+6000
with ThreadPoolExecutor(max_workers=2) as pool:
 while pending or running:
  for label in sorted(pending):
   if len(running)>=2:break
   if (O/(label+'.exit')).exists():running[pool.submit(work,label)]=label;pending.remove(label)
  if running:
   done,_=wait(running,timeout=5,return_when=FIRST_COMPLETED)
   for future in done:
    label=running.pop(future)
    try:rows.append(future.result())
    except Exception as exc:rows.append({'id':label,'passed':False,'audit_error':repr(exc)})
    (O/'audit-status.json').write_text(json.dumps(rows,indent=2)+'\n')
  elif pending:time.sleep(5)
  if time.monotonic()>deadline:
   for label in pending:rows.append({'id':label,'passed':False,'audit_started':False,'reason':'source_terminal_deadline'})
   pending.clear()
(O/'audit-status.json').write_text(json.dumps(rows,indent=2)+'\n')
raise SystemExit(0 if len(rows)==9 and all(x['passed'] for x in rows) else 1)
