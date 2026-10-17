"""Run all current suites exactly once through unchanged canonical selectors."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import subprocess,json,gzip,os,time,hashlib
R=Path('/home/qian-qi/RAZR-SLIDE-nested-contact-20261017');O=Path('/tmp/razr-level2-contact-20261017/unit1004')
EXPECTED='c08ab7c85bfb790c0ead339570f7275d6178e7be'
assert not O.exists();O.mkdir()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==EXPECTED
m=json.loads((R/'tools/test_suites.json').read_text());total=sum(x['minimum_tests'] for x in m['suites'])
assert total==m['minimum_total_tests']==1004 and len(m['suites'])==31
old=json.loads(gzip.decompress((R/'engineering/spatial-contact-integration-20261015/local-unit873.json.gz').read_bytes()))
weights={s['id']:s.get('seconds',10.) for s in old['suite_results']};groups=[[],[],[]];cost=[0.,0.,0.]
for s in sorted(m['suites'],key=lambda s:-weights.get(s['id'],10.)):
 i=cost.index(min(cost));groups[i].append(s['id']);cost[i]+=weights.get(s['id'],10.)
(O/'selections.json').write_text(json.dumps(groups,indent=2)+'\n')
def work(i):
 cmd=[str(R/'.venv/bin/python'),'-B',str(R/'tools/verify.py'),'--output',str(O/f'group-{i}')]
 for name in groups[i]:cmd+=['--suite',name]
 start=time.monotonic()
 with (O/f'group-{i}.log').open('w') as log:
  p=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=2400,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
 (O/f'group-{i}.exit').write_text(str(p.returncode)+'\n')
 print('TERMINAL',i,p.returncode,time.monotonic()-start,flush=True)
 if p.returncode:raise RuntimeError('canonical suite selection failed: '+str(i))
 return i,cmd,json.loads((O/f'group-{i}/report.json').read_text())
results=[]
with ThreadPoolExecutor(max_workers=3) as pool:
 for future in as_completed([pool.submit(work,i) for i in range(3)]):results.append(future.result())
results.sort();base=results[0][2];rows=[]
for i,cmd,r in results:
 assert r['base_commit']==EXPECTED and r['passed'] and r['source_bytes_unchanged'] and not r['changed_during_tests'] and not r['syntax_errors']
 assert r['source_hashes_before']==r['source_hashes_after']==base['source_hashes_before']
 assert set(s['id'] for s in r['suite_results'])==set(groups[i]);rows+=r['suite_results']
assert len(rows)==len({s['id'] for s in rows})==31
assert {s['id'] for s in rows}=={s['id'] for s in m['suites']}
assert sum(s['tests_run'] for s in rows)==total
base.update(scope='all_current_unit_suites_via_disjoint_canonical_selections',suite_results=rows,tests_run=total,canonical_groups=groups,passed=True,execution='three disjoint unchanged canonical --suite invocations; all current suites rerun')
(O/'report.json').write_text(json.dumps(base,indent=2)+'\n')
(O.parent/'unit1004.exit').write_text('0\n')
print('COMPLETE_ALL_CURRENT',total,31,EXPECTED,flush=True)
