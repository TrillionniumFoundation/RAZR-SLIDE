from pathlib import Path
import sys,subprocess,json,time,os,importlib.util
R=Path('/home/qian-qi/RAZR-SLIDE-frame-anchor-20261015');O=Path('/tmp/razr-frame-anchor-20261015/unit704');O.mkdir(exist_ok=False)
spec=importlib.util.spec_from_file_location('canonical_verify',R/'tools/verify.py');entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
conf=json.loads((R/'tools/test_suites.json').read_text());entry.validate_manifest(conf)
assert conf['minimum_total_tests']==704 and len(conf['suites'])==31
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();before=entry.snapshot(R)
previous=json.loads(Path('/tmp/razr-panel-shear-20261015/unit678/report.json').read_text());cost={x['id']:x.get('seconds',1.) for x in previous['suite_results']}
groups=[[],[],[]];weights=[0.,0.,0.]
for s in sorted(conf['suites'],key=lambda x:cost.get(x['id'],1.),reverse=True):
    i=min(range(3),key=lambda n:weights[n]);groups[i].append(s['id']);weights[i]+=cost.get(s['id'],1.)
(O/'selections.json').write_text(json.dumps(groups,indent=2)+'\n')
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
running=[]
for i,selection in enumerate(groups):
    command=[str(R/'.venv/bin/python'),'-B',str(R/'tools/verify.py'),'--output',str(O/f'group-{i}')]
    for name in selection:command+=['--suite',name]
    f=(O/f'group-{i}.log').open('w');child=subprocess.Popen(['nice','-n','10',*command],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT)
    running.append((i,child,f,command,time.monotonic()))
results=[]
for i,child,f,command,start in running:
    try:code=child.wait(timeout=1800)
    except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=30);code='TIMEOUT'
    f.close();print('GROUP',i,'EXIT',code,'SECONDS',round(time.monotonic()-start,2),flush=True)
    path=O/f'group-{i}/report.json';assert code==0 and path.exists(),(i,code)
    r=json.loads(path.read_text());assert r['passed'] and r['base_commit']==head and r['source_hashes_before']==before and r['source_hashes_after']==before
    results.append((i,command,r))
rows=[row for _,_,r in results for row in r['suite_results']];names=[x['id'] for x in rows]
assert len(names)==31 and len(set(names))==31 and set(names)=={x['id'] for x in conf['suites']}
assert sum(x['tests_run'] for x in rows)==704 and all(x['passed'] for x in rows)
after=entry.snapshot(R);assert before==after
combined=dict(results[0][2]);combined.update({'scope':'all_current_unit_suites','base_commit':head,'suite_results':rows,'tests_run':704,'passed':True,'source_hashes_before':before,'source_hashes_after':after,'source_bytes_unchanged':True,'changed_during_tests':[],
'execution':'three disjoint unchanged canonical --suite commands, current source only; no old results reused','canonical_selection_reports':[{'group':i,'command':c,'report':f'group-{i}/report.json'} for i,c,_ in results]})
(O/'report.json').write_text(json.dumps(combined,indent=2)+'\n');print('FULL_CURRENT_UNIT',704,31,True,flush=True)
