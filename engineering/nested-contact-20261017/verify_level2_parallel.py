"""Finish three independent cases in parallel; preserve the completed case6 audit."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib,json,os,shutil,subprocess
R=Path('/home/qian-qi/RAZR-SLIDE-nested-contact-20261017');O=Path('/tmp/razr-level2-contact-20261017');src=O/'level2-verified-resume';out=O/'level2-final-audits';assert not out.exists();out.mkdir()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
oldjob=Path('/home/qian-qi/.local/state/hepta-runtime-operator-host/jobs/1a14bfbd604-1b6abb-42b')
terminal=json.loads((oldjob/'exit.json').read_text());assert terminal['cancelled'] and terminal['exit_code']==-15
v=json.loads((src/'case-6/independent.json').read_text());assert v['discrete_solution_passed'] and v['case']==6 and v['nested_volume_level']==2
assert (src/'case-6/independent-v3.exit').read_text().strip()=='0'
d=out/'case-6';d.mkdir()
for name in ('independent.json','recovered-panel-internal.npz','recovered-frame-internal.npz'):
    shutil.copyfile(src/'case-6'/name,d/name);assert sha(src/'case-6'/name)==sha(d/name)
for old,new in [('independent-v3.log','independent.log'),('independent-v3.exit','independent.exit')]:shutil.copyfile(src/'case-6'/old,d/new)
record={'sequential_job':'1a14bfbd604-1b6abb-42b','sequential_terminal_cancelled':True,'sequential_job_not_claimed_complete':True,'completed_case6_preserved':True,'reason':'remaining independent cases run in parallel with unchanged verifier and distinct new output directories','verifier_sha256':sha(R/'engineering/volume-convergence-20261017/verify_enriched_contact.py')}
(out/'execution-repartition.json').write_text(json.dumps(record,indent=2)+'\n')
env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONPATH':'/home/qian-qi/.local/share/razr-slide-analysis/scikit-fem-12.0.2-20261017'}
def work(case):
    d=out/f'case-{case}';d.mkdir()
    command=[str(R/'.venv/bin/python'),'-u','-B',str(R/'engineering/volume-convergence-20261017/verify_enriched_contact.py'),'--volume','/tmp/razr-volume-convergence-20261017/volume-v3','--level','2','--run',str(src/f'case-{case}'),'--output',str(d/'independent.json')]
    with (d/'independent.log').open('x') as log:
        p=subprocess.run(command,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=900)
    (d/'independent.exit').write_text(str(p.returncode)+'\n')
    v=json.loads((d/'independent.json').read_text()) if (d/'independent.json').exists() else {}
    row={'case':case,'exit_code':p.returncode,'passed':bool(v.get('discrete_solution_passed')),'minimum_gap_mm':v.get('minimum_gap_mm')};print('PARALLEL_INDEPENDENT',row,flush=True);return row
rows=[{'case':6,'exit_code':0,'passed':True,'minimum_gap_mm':v['minimum_gap_mm']}]
with ThreadPoolExecutor(max_workers=3) as pool:
    for f in as_completed([pool.submit(work,c) for c in (4,5,7)]):rows.append(f.result())
r={'level':2,'cases':rows,'all_requested_independently_passed':len(rows)==4 and all(x['passed'] and x['exit_code']==0 for x in rows),'source_repartition':record}
(out/'SUMMARY.json').write_text(json.dumps(r,indent=2)+'\n');print('ALL_LEVEL2_INDEPENDENT',r['all_requested_independently_passed'],flush=True)
raise SystemExit(0 if r['all_requested_independently_passed'] else 1)
