"""Read only completed case outputs and execute unchanged independent FE audit."""
from pathlib import Path
import argparse,json,os,subprocess,time
P=argparse.ArgumentParser();P.add_argument('--level',type=int,required=True);P.add_argument('--run',type=Path,required=True);P.add_argument('--job',required=True);a=P.parse_args()
R=Path('/home/qian-qi/RAZR-SLIDE-nested-contact-20261017');V=Path('/tmp/razr-volume-convergence-20261017/volume-v3')
job=Path('/home/qian-qi/.local/state/hepta-runtime-operator-host/jobs')/a.job
checked={};start=time.monotonic()
while time.monotonic()-start<5100:
    for case in (6,4,5,7):
        folder=a.run/f'case-{case}'
        if case in checked or not (folder/'gap-extrema.json').exists():continue
        try:
            report=json.loads((folder/'report.json').read_text())
            json.loads((folder/'gap-extrema.json').read_text())
        except (FileNotFoundError,json.JSONDecodeError):continue
        command=[str(R/'.venv/bin/python'),'-u','-B',str(R/'engineering/volume-convergence-20261017/verify_enriched_contact.py'),'--volume',str(V),'--level',str(a.level),'--run',str(folder),'--output',str(folder/'independent.json')]
        with (folder/'independent.log').open('x') as log:
            run=subprocess.run(command,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=900,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONPATH':'/home/qian-qi/.local/share/razr-slide-fem-20261015'})
        (folder/'independent.exit').write_text(str(run.returncode)+'\n')
        checked[case]={'exit_code':run.returncode}
        if (folder/'independent.json').exists():
            v=json.loads((folder/'independent.json').read_text());checked[case].update({'passed':v['discrete_solution_passed'],'minimum_gap_mm':v['minimum_gap_mm'],'regions':v['original_common_cells']})
        print('INDEPENDENT',a.level,case,checked[case],flush=True)
    if len(checked)==4:break
    if (job/'exit.json').exists():
        # No more producer writes. A missing case is incomplete, never a pass.
        terminal=json.loads((job/'exit.json').read_text())
        if terminal.get('exit_code')!=0 or (a.run/'SUMMARY.json').exists():break
    time.sleep(3)
result={'level':a.level,'cases':checked,'all_requested_independently_passed':len(checked)==4 and all(v.get('passed') and v['exit_code']==0 for v in checked.values())}
(a.run/'INDEPENDENT_SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n');print('TERMINAL',result,flush=True)
raise SystemExit(0 if result['all_requested_independently_passed'] else 1)
