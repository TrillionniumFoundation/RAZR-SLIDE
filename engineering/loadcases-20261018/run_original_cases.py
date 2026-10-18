"""Execute nine explicitly declared research cases using the existing solver.
Each process has its own original controls, factorization, point additions and logs.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib,json,os,subprocess,time
R=Path('/home/qian-qi/RAZR-SLIDE-loadcases-20261018')
O=Path('/home/qian-qi/.local/share/razr-slide-evidence/loadcases-20261018')
BASE='e54d71cc2c838091e9c6b20c1063acf1049e9a06'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==BASE
plan_path=R/'engineering/loadcases-20261018/EXPERIMENT_PLAN.json'
plan=json.loads(plan_path.read_text());entries={x['id']:x for x in plan['cases']}
controls=[R/'engineering/trace-enrichment-20261017/solve_trace_probe.py',R/'engineering/consistent-load-20261017/surface_archive.py',R/'integration/contact_dual_active.py',R/'integration/rank_fallback.py',plan_path]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
identity={str(p):sha(p) for p in controls}
(O/'run-source-identity.json').write_text(json.dumps(identity,indent=2)+'\n')
def work(label):
 e=entries[label];dest=O/label;assert not dest.exists()
 cmd=[str(R/'.venv/bin/python'),'-u','-B',str(R/'engineering/trace-enrichment-20261017/solve_trace_probe.py'),
 '--volume','/home/qian-qi/.local/share/razr-slide-evidence/volume-convergence-20261017/volume-v3',
 '--state','/home/qian-qi/.local/share/razr-slide-evidence/nested-contact-20261017/level-2/final-case7-state',
 '--output',str(dest),'--surface-loads',str(R/'engineering/consistent-load-20261017/projection-512'),
 '--surface-load-mode','consistent','--load-face-cap','2','--faces-per-patch','4',
 '--frozen-selection',str(R/'engineering/joint-sensitivity-20261017/frozen-selection.json'),
 '--case',str(e['case']),'--gap-tolerance','1e-7','--rank-fallback','qr_pivot',
 '--external-load-scale',str(e['external_load_scale_over_Epanel_mm2']),
 '--max-exchanges',str(plan['max_exchanges']),'--max-points',str(plan['max_points'])]
 (O/(label+'-command.json')).write_text(json.dumps(cmd,indent=2)+'\n')
 started=time.monotonic();print('START',label,flush=True);timed_out=False
 with (O/(label+'.log')).open('w') as log:
  try:r=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=1800,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONPATH':'/home/qian-qi/.local/share/razr-slide-analysis/scikit-fem-12.0.2-20261017'});code=r.returncode
  except subprocess.TimeoutExpired:code=124;timed_out=True
 (O/(label+'.exit')).write_text(str(code)+'\n')
 row={'id':label,'definition':e,'exit_code':code,'timed_out':timed_out,'passed':False,'seconds':time.monotonic()-started,'functional_commit':BASE}
 if (dest/'report.json').exists():
  report=json.loads((dest/'report.json').read_text());row.update(passed=bool(code==0 and report.get('passed')),case=report.get('case'),status=report.get('status'),minimum_bolt_force=report.get('minimum_bolt_force_over_E'),history=report.get('history'))
 for p,h in identity.items():assert sha(p)==h
 print('TERMINAL',label,code,row['passed'],row['seconds'],flush=True)
 return row
order=['case-6','assembly-reference','case-0','case-1','case-2','case-3','case-4','case-5','case-7']
rows=[]
with ThreadPoolExecutor(max_workers=3) as pool:
 for future in as_completed([pool.submit(work,x) for x in order]):
  rows.append(future.result());(O/'solve-status.json').write_text(json.dumps(rows,indent=2)+'\n')
raise SystemExit(0 if len(rows)==9 and all(r['passed'] for r in rows) else 1)
