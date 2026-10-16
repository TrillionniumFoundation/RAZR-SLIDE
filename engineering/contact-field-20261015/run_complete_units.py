from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import subprocess,json,gzip,os,time,hashlib
R=Path('/home/qian-qi/RAZR-SLIDE-contact-field-20261015');O=Path('/tmp/razr-contact-field-20261015/unit814');O.mkdir(exist_ok=False)
expected=Path('/tmp/razr-contact-field-20261015/functional-head.txt').read_text().strip();assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()==expected
m=json.loads((R/'tools/test_suites.json').read_text());assert m['minimum_total_tests']==814
old=json.loads(gzip.decompress((R/'engineering/panel-bearing-web-20261015/local-unit759.json.gz').read_bytes()));weights={s['id']:s.get('seconds',10.) for s in old['suite_results']};groups=[[],[],[]];cost=[0.,0.,0.]
for s in sorted(m['suites'],key=lambda s:-weights.get(s['id'],10)):
 i=cost.index(min(cost));groups[i].append(s['id']);cost[i]+=weights.get(s['id'],10)
(O/'selections.json').write_text(json.dumps(groups,indent=2)+'\n')
def work(i):
 cmd=[str(R/'.venv/bin/python'),'-B',str(R/'tools/verify.py'),'--output',str(O/f'group-{i}')]
 for name in groups[i]:cmd+=['--suite',name]
 t=time.monotonic()
 with (O/f'group-{i}.log').open('w') as log:p=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=1600,env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})
 print('TERMINAL',i,p.returncode,round(time.monotonic()-t,2),flush=True);assert p.returncode==0
 return i,cmd,json.loads((O/f'group-{i}/report.json').read_text())
results=[]
with ThreadPoolExecutor(max_workers=3) as pool:
 for future in as_completed([pool.submit(work,i) for i in range(3)]):results.append(future.result())
results.sort();base=results[0][2];allrows=[]
for i,cmd,r in results:
 assert r['base_commit']==expected and r['passed'] and r['source_bytes_unchanged'] and not r['changed_during_tests'] and not r['syntax_errors']
 assert r['source_hashes_before']==r['source_hashes_after']==base['source_hashes_before'];assert set(x['id'] for x in r['suite_results'])==set(groups[i]);allrows+=r['suite_results']
assert len(allrows)==len(m['suites'])==31 and len(set(x['id'] for x in allrows))==31 and set(x['id'] for x in allrows)==set(x['id'] for x in m['suites'])
assert sum(x['tests_run'] for x in allrows)==814
base.update(scope='all_current_unit_suites_via_disjoint_canonical_selections',suite_results=allrows,tests_run=814,execution='three disjoint unchanged canonical --suite commands; all current suites rerun',canonical_groups=groups,passed=True)
(O/'report.json').write_text(json.dumps(base,indent=2)+'\n');(O.parent/'unit814.exit').write_text('0\n');print('COMPLETE_ALL_CURRENT',814,31,expected,flush=True)
