"""Complete current-source replay only after the fresh changed-energy run ends."""
from pathlib import Path
import hashlib,json,os,subprocess,time
R=Path('/home/qian-qi/RAZR-SLIDE-nested-contact-20261017');O=Path('/tmp/razr-level2-contact-20261017');run=O/'level2-original'
job=Path('/home/qian-qi/.local/state/hepta-runtime-operator-host/jobs/1a14bcea568-1b6abb-260')
start=time.monotonic()
while not (job/'exit.json').exists():
    if time.monotonic()-start>2400:raise RuntimeError('fresh level2 producer still incomplete; no replay started')
    time.sleep(3)
terminal=json.loads((job/'exit.json').read_text());assert terminal['exit_code']==0,'fresh level2 run failed'
summary=json.loads((run/'SUMMARY.json').read_text());assert summary['all_requested_passed'] and len(summary['cases'])==4
case=run/'case-7';states=sorted(case.glob('checkpoint-*'));assert states
state=states[-1];meta=json.loads((state/'manifest.json').read_text());assert meta['case']==7
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
assert sha(state/'response.npz')==meta['response_sha256'] and sha(state/'points.json')==meta['points_sha256']
assert meta['gap_tolerance_mm']==1e-7
(O/'level2-replay-input.json').write_text(json.dumps({'state':str(state),'state_manifest_sha256':sha(state/'manifest.json'),'source_producer_completed':True,'not_an_independent_contact_pass':True,'current_functional_commit':'c08ab7c85bfb790c0ead339570f7275d6178e7be'},indent=2)+'\n')
cmd=[str(R/'.venv/bin/python'),'-u','-B',str(R/'engineering/volume-convergence-20261017/solve_enriched_contact.py'),'--inputs','/tmp/razr-volume-convergence-20261017/volume-v3','--output',str(O/'level2-verified-resume'),'--volume-level','2','--resume-state',str(state),'--cases','6','4','5','7','--new-points','128','--max-points','8000','--max-exchanges','50','--response-batch-size','64']
print('START_CURRENT_SOURCE_SAME_ENERGY_REPLAY',state,flush=True)
r=subprocess.run(cmd,cwd=R,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},timeout=2400)
(O/'level2-replay.exit').write_text(str(r.returncode)+'\n');print('REPLAY_EXIT',r.returncode,flush=True);raise SystemExit(r.returncode)
