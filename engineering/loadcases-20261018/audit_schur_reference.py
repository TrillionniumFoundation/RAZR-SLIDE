"""Independently audit the replacement assembly reference; preserve old timeout."""
from pathlib import Path
import json,os,subprocess,time
R=Path('/home/qian-qi/RAZR-SLIDE-loadcases-schur-20261018');O=Path('/home/qian-qi/.local/share/razr-slide-evidence/loadcases-20261018')
P=Path('/home/qian-qi/.local/share/razr-slide-evidence/rank-replay-20261018/current')
deadline=time.monotonic()+1600
while not (O/'assembly-reference-schur.exit').exists():
    if time.monotonic()>deadline:raise SystemExit('replacement source terminal not observed')
    time.sleep(5)
rc=int((O/'assembly-reference-schur.exit').read_text());assert rc==0,('source failed',rc)
src=O/'assembly-reference-schur';rr=json.loads((src/'report.json').read_text());assert rr['passed'] and rr['external_load_scale_over_Epanel_mm2']==0
cmd=[str(R/'.venv/bin/python'),'-u','-B',str(O/'verify_original_case.py'),'--case-id','assembly-reference','--expected-target','1e-7','--run',str(src),'--volume','/home/qian-qi/.local/share/razr-slide-evidence/volume-convergence-20261017/volume-v3','--element-check',str(P/'independent-elements'),'--force-check',str(P/'projection-check-512'),'--output',str(O/'audit-assembly-reference-schur')]
(O/'audit-assembly-reference-schur-command.json').write_text(json.dumps(cmd,indent=2)+'\n')
print('INDEPENDENT_REPLACEMENT_REFERENCE_START',flush=True)
with (O/'audit-assembly-reference-schur.log').open('w') as log:
    r=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=1000,env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','PYTHONPATH':'/home/qian-qi/.local/share/razr-slide-analysis/scikit-fem-12.0.2-20261017'})
(O/'audit-assembly-reference-schur.exit').write_text(str(r.returncode)+'\n')
print('INDEPENDENT_REPLACEMENT_REFERENCE_TERMINAL',r.returncode,flush=True)
raise SystemExit(r.returncode)
