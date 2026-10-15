from pathlib import Path
import concurrent.futures,hashlib,json,os,subprocess,time
R=Path('/home/qian-qi/RAZR-SLIDE-panel-elastic-v2-20261015');O=Path('/tmp/razr-panel-elastic-20261015/validation-v2');P=str(R/'.venv/bin/python')
F=(O.parent/'functional-v2-head.txt').read_text().strip();assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==F
manifest=json.loads((R/'tools/test_suites.json').read_text());groups=json.loads((R/'engineering/thread-connection-20261015/DELIVERY_VERIFICATION.json').read_text())['local_complete_unit']['canonical_groups'];flat=sum(groups,[]);assert len(flat)==len(set(flat))==len(manifest['suites']) and set(flat)=={s['id'] for s in manifest['suites']}
(O/'unit759').mkdir(exist_ok=False)
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1'}
jobs={}
for i,g in enumerate(groups):
 cmd=[P,'-B','tools/verify.py','--output',str(O/'unit759'/f'group-{i}')]
 for name in g:cmd+=['--suite',name]
 jobs[f'group-{i}']=cmd
jobs['native-full']=[P,'-B','integration/verify_panel_bearing_web.py','--baseline','/tmp/razr-thread-validation-20261015/native/manifest.json','--manifest',str(O.parent/'candidate-v3/manifest.json'),'--output',str(O/'full-verification.json'),'--full']
def run(item):
 name,cmd=item;t=time.monotonic();print('START',name,flush=True)
 with (O/(name+'.log')).open('w') as f:
  p=subprocess.run(cmd,cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1500)
 (O/(name+'.exit')).write_text(str(p.returncode)+'\n');print('FINISH',name,p.returncode,round(time.monotonic()-t,2),flush=True);return name,p.returncode
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:codes=dict(ex.map(run,jobs.items()))
reports=[json.loads((O/'unit759'/f'group-{i}'/'report.json').read_text()) for i in range(3)]
before=reports[0]['source_hashes_before'];suites=[]
for i,r in enumerate(reports):
 assert r['base_commit']==F and r['source_hashes_before']==before and r['source_hashes_after']==before and r['source_bytes_unchanged']
 assert {s['id'] for s in r['suite_results']}==set(groups[i]);suites+=r['suite_results']
assert len(suites)==31 and sum(x['tests_run'] for x in suites)==759
result={**reports[0],'scope':'all_current_unit_suites','execution':'three disjoint unmodified canonical --suite selections, all executed afresh','canonical_groups':groups,'suite_results':suites,'tests_run':759,'passed':all(codes[f'group-{i}']==0 and r['passed'] for i,r in enumerate(reports))}
(O/'unit759/report.json').write_text(json.dumps(result,indent=2)+'\n');(O/'unit759.exit').write_text('0\n' if result['passed'] else '1\n');print('UNIT_ALL',result['tests_run'],result['passed'],'NATIVE',codes['native-full'],flush=True)
