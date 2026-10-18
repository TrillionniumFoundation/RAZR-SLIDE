"""Bounded force-install, seal, fixed-adjustment service and independent audits.
Does not re-run the separately started installation solve or any old study.
"""
from pathlib import Path
import subprocess,os,json,time,hashlib,sys
R=Path('/home/qian-qi/RAZR-SLIDE-installation-control-20261018')
O=Path('/home/qian-qi/.local/share/razr-slide-evidence/installation-control-20261018')
V='/home/qian-qi/.local/share/razr-slide-evidence/volume-convergence-20261017/volume-v3'
I=Path('/home/qian-qi/.local/share/razr-slide-evidence/rank-replay-20261018/current')
ENV={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONPATH':'/home/qian-qi/.local/share/razr-slide-analysis/scikit-fem-12.0.2-20261017'}
PY=str(R/'.venv/bin/python');rows=[]
def execute(label,cmd,timeout):
    before=hashlib.sha256((R/'integration/installation_control.py').read_bytes()).hexdigest()
    print('STAGE_START',label,flush=True);t=time.monotonic()
    with (O/(label+'.log')).open('x') as log:p=subprocess.run(cmd,cwd=R,env=ENV,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
    row={'stage':label,'command':cmd,'exit_code':p.returncode,'seconds':time.monotonic()-t};rows.append(row)
    (O/(label+'.exit')).write_text(str(p.returncode)+'\n');(O/'sequence-status.json').write_text(json.dumps(rows,indent=2)+'\n')
    assert hashlib.sha256((R/'integration/installation_control.py').read_bytes()).hexdigest()==before
    print('STAGE_TERMINAL',json.dumps(row),flush=True);p.check_returncode()
def audit(name,mode):
    execute('audit-'+name,[PY,'-u','-B',str(O/'verify_installation_field.py'),'--case-id',mode,'--expected-target','1e-7','--run',str(O/name),'--volume',V,'--element-check',str(I/'independent-elements'),'--force-check',str(I/'projection-check-512'),'--output',str(O/('audit-'+name))],900)
terminal=Path('/home/qian-qi/.local/state/hepta-runtime-operator-host/jobs/1a14e0878c4-1b6abb-f7b/exit.json')
deadline=time.monotonic()+1800
while not terminal.exists():
    if time.monotonic()>deadline:raise RuntimeError('installation source terminal not observed')
    time.sleep(3)
ex=json.loads(terminal.read_text());assert ex['exit_code']==0,ex
report=json.loads((O/'install-force/report.json').read_text());assert report['passed'] and report['installation_control']['mode']=='force_targets'
audit('install-force','install-force')
# The sealed state is derived from the independently accepted installation,
# not from the historical spring parameter or an unverified field.
execute('seal-state',[PY,'-u','-B','-c',"import sys;sys.path.insert(0,'"+str(R/'integration')+"');from installation_control import seal_locked_state;seal_locked_state('"+str(O/'install-force')+"','"+str(O/'audit-install-force/report.json')+"','"+str(O/'locked-installation.json')+"')"],45)
cmd=[PY,'-u','-B',str(R/'engineering/trace-enrichment-20261017/solve_trace_probe.py'),'--volume',V,'--state','/home/qian-qi/.local/share/razr-slide-evidence/nested-contact-20261017/level-2/final-case7-state','--output',str(O/'service-locked'),'--faces-per-patch','4','--surface-loads',str(R/'engineering/consistent-load-20261017/projection-512'),'--surface-load-mode','consistent','--load-face-cap','2','--frozen-selection',str(R/'engineering/joint-sensitivity-20261017/frozen-selection.json'),'--case','6','--gap-tolerance','1e-7','--external-load-scale','1e-5','--installation-control',str(O/'locked-installation.json'),'--rank-fallback','qr_pivot','--max-exchanges','30','--max-points','6500']
execute('service-locked',cmd,1800)
audit('service-locked','service-locked')
print('INSTALLATION_AND_FIXED_ADJUSTMENT_SEQUENCE_PASSED',flush=True)
