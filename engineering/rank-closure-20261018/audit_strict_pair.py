"""Bounded audit orchestration for the two already launched original strict solves."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import os,subprocess,time,json,hashlib
B=Path('/home/qian-qi/.local/share/razr-slide-evidence/rank-replay-20261018');D=B/'current';R=Path('/home/qian-qi/RAZR-SLIDE-rank-pivot-20261018')
V=Path('/home/qian-qi/.local/share/razr-slide-evidence/volume-convergence-20261017/volume-v3')
def work(sides,job):
 terminal=Path('/home/qian-qi/.local/state/hepta-runtime-operator-host/jobs')/job/'exit.json';deadline=time.monotonic()+4200
 while not terminal.exists():
  if time.monotonic()>deadline:return {'sides':sides,'passed':False,'reason':'source_terminal_not_observed'}
  time.sleep(5)
 exit=json.loads(terminal.read_text());src=B/('strict'+str(sides)+'-v2')
 if exit['exit_code']!=0:return {'sides':sides,'passed':False,'source_exit':exit['exit_code'],'audit_started':False}
 r=json.loads((src/'report.json').read_text());assert r['passed'] and r['gap_tolerance_mm']==2e-8 and r['rank_fallback']=='qr_pivot'
 dest=B/('audit'+str(sides)+'-v2');assert not dest.exists()
 cmd=[str(R/'.venv/bin/python'),'-u','-B',str(D/'verify_rank_field.py'),'--run',str(src),'--volume',str(V),'--element-check',str(D/'independent-elements'),'--force-check',str(D/('projection-check-'+str(sides))),'--expected-target','2e-8','--output',str(dest)]
 print('INDEPENDENT_STRICT_START',sides,flush=True)
 with (B/('audit'+str(sides)+'-v2.log')).open('w') as log:
  p=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=1200,env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','PYTHONPATH':'/home/qian-qi/.local/share/razr-slide-analysis/scikit-fem-12.0.2-20261017'})
 (B/('audit'+str(sides)+'-v2.exit')).write_text(str(p.returncode)+'\n')
 rr={'sides':sides,'audit_started':True,'exit_code':p.returncode,'passed':False,'command':cmd}
 if p.returncode==0:
  a=json.loads((dest/'report.json').read_text());assert a['passed'] and a['gap_tolerance_mm']==2e-8 and a['minimum_covered_bound_mm']>=-2e-8;rr.update(passed=True,minimum_bound=a['minimum_covered_bound_mm'],report_sha256=hashlib.sha256((dest/'report.json').read_bytes()).hexdigest())
 print('INDEPENDENT_STRICT_TERMINAL',sides,rr,flush=True);return rr
rows=[]
with ThreadPoolExecutor(max_workers=2) as pool:
 for f in as_completed([pool.submit(work,256,'1a14d8bee0d-1b6abb-d8e'),pool.submit(work,512,'1a14d8c33fb-1b6abb-d92')]):
  rows.append(f.result());(B/'strict-audit-status.json').write_text(json.dumps(rows,indent=2)+'\n')
raise SystemExit(0 if len(rows)==2 and all(r['passed'] for r in rows) else 1)
