from pathlib import Path
import subprocess,json,os
R=Path('/home/qian-qi/RAZR-SLIDE-convergence-20261017');O=Path('/tmp/razr-convergence-20261017')
state=Path('/home/qian-qi/.local/share/razr-slide-evidence/preload-closure-20261017/final-case7-state')
for label,tol in [('contact-5e8',5e-8),('contact-25e9',2.5e-8)]:
 out=O/label
 cmd=[str(R/'.venv/bin/python'),'-u','-B',str(R/'engineering/preload-resume-20261016/resume_original.py'),'--inputs','/tmp/razr-preload-contact-20261016/elastic','--output',str(out),'--resume-state',str(state),'--cases','6','--gap-target',str(tol),'--new-points','128','--max-points','7000','--max-exchanges','25','--response-batch-size','32']
 with (O/(label+'.log')).open('x') as log:p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=R,timeout=1800)
 (O/(label+'.exit')).write_text(str(p.returncode)+'\n');print('TARGET_TERMINAL',label,p.returncode,flush=True)
 if p.returncode:raise SystemExit(p.returncode)
 checkpoints=sorted((out/'case-6').glob('checkpoint-*'));state=checkpoints[-1]
print('TWO_STRICTER_TARGETS_COMPLETED',flush=True)
