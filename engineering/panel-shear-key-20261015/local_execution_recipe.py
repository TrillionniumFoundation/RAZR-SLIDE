"""Execute all current suites using three disjoint canonical --suite selections.

Temporary execution recipe; no repository runner/check is changed or skipped.
Each child independently snapshots the entire tree. Combine only identical
source snapshots, exact suite coverage, terminal exits and actual test counts.
"""
from pathlib import Path
import concurrent.futures,datetime,importlib.util,json,os,subprocess,sys,time
R=Path('/home/qian-qi/RAZR-SLIDE-panel-shear-v2-20261015');O=Path('/tmp/razr-panel-shear-20261015/unit678')
spec=importlib.util.spec_from_file_location('canonical_verify',R/'tools/verify.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
manifest=json.loads((R/'tools/test_suites.json').read_text());v.validate_manifest(manifest)
assert manifest['minimum_total_tests']==678
head=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()
before=v.snapshot(R);O.mkdir(parents=True,exist_ok=False)
old=json.loads(Path('/tmp/razr-cover-hold-20261015/unit654/report.json').read_text());weights={r['id']:r['seconds'] for r in old['suite_results']}
bins=[[],[],[]];times=[0.,0.,0.]
for suite in sorted(manifest['suites'],key=lambda s:weights.get(s['id'],180.),reverse=True):
 i=times.index(min(times));bins[i].append(suite['id']);times[i]+=weights.get(suite['id'],180.)
assert sorted(x for group in bins for x in group)==sorted(s['id'] for s in manifest['suites'])
(O/'selections.json').write_text(json.dumps({'canonical_disjoint_suite_selections':bins,'maximum_concurrent_children':3},indent=2)+'\n')

def run(index):
 directory=O/f'group-{index}';command=[sys.executable,'-B',str(R/'tools/verify.py'),'--output',str(directory)]
 for name in bins[index]:command+=['--suite',name]
 start=time.monotonic()
 with (O/f'group-{index}.log').open('w') as f:
  try:
   p=subprocess.run(['nice','-n','10',*command],cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=2100)
   code=p.returncode
  except subprocess.TimeoutExpired:code='TIMEOUT'
 report=json.loads((directory/'report.json').read_text()) if (directory/'report.json').exists() else None
 print('GROUP_TERMINAL',index,code,'seconds',round(time.monotonic()-start,3),flush=True)
 return index,code,report,command

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,range(3)))
after=v.snapshot(R);rows=[];valid=before==after;syntaxes=[];versions=None;references=[]
for i,code,r,command in results:
 references.append({'group':i,'command':command,'exit_code':code,'report':f'group-{i}/report.json'})
 if r is None:valid=False;continue
 rows+=r['suite_results'];syntaxes+=r['syntax_errors'];versions=r['versions']
 valid=valid and code==0 and r['passed'] and r['base_commit']==head and r['scope']=='selected' and r['source_hashes_before']==before and r['source_hashes_after']==before and r['source_bytes_unchanged']
ids=[x['id'] for x in rows];expected=[x['id'] for x in manifest['suites']]
valid=valid and sorted(ids)==sorted(expected) and len(set(ids))==len(expected) and not syntaxes
order={name:i for i,name in enumerate(expected)};rows.sort(key=lambda x:order[x['id']])
report={'scope':'all_current_unit_suites','execution':'three disjoint unchanged canonical --suite commands, no earlier results reused',
 'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base_commit':head,'python':sys.version,'versions':versions,
 'suite_manifest_sha256':v.sha(R/'tools/test_suites.json'),'canonical_selection_reports':references,
 'suite_results':rows,'source_hashes_before':before,'source_hashes_after':after,'source_bytes_unchanged':before==after,
 'changed_during_tests':[name for name in sorted(before.keys()|after.keys()) if before.get(name)!=after.get(name)],
 'syntax_errors':syntaxes,'python_files_parsed':sum(x.endswith('.py') for x in before),'tests_run':sum(x['tests_run'] for x in rows),
 'passed':bool(valid),'full_motion_reexecuted':False,'native_KiCad_reexecuted':False,'candidate_go':False,'manufacturing_go':False}
(O/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('FULL_CURRENT_UNIT',report['tests_run'],'SUITES',len(rows),'PASSED',report['passed'],flush=True)
raise SystemExit(0 if report['passed'] else 1)
