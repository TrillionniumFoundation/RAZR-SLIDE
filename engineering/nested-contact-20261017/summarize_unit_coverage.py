"""Require a completed current pass for every suite; retain failed first attempt."""
from pathlib import Path
import hashlib,json
R=Path('/home/qian-qi/RAZR-SLIDE-nested-contact-20261017');O=Path('/tmp/razr-level2-contact-20261017')
F='c08ab7c85bfb790c0ead339570f7275d6178e7be'
manifest=json.loads((R/'tools/test_suites.json').read_text());expected={x['id']:x for x in manifest['suites']}
raw=[]
for i in range(3):
    p=O/'unit1004'/f'group-{i}'/'report.json';raw.append((p,json.loads(p.read_text())))
p=O/'unit1004-manufacturing-retry/report.json';retry=json.loads(p.read_text());raw.append((p,retry))
assert retry['passed'] and retry['tests_run']==455 and len(retry['suite_results'])==1
assert retry['suite_results'][0]['id']=='manufacturing-fit'
base=raw[0][1];passed={};failures=[]
for path,r in raw:
    assert r['base_commit']==F and r['source_bytes_unchanged'] and not r['changed_during_tests'] and not r['syntax_errors']
    assert r['source_hashes_before']==r['source_hashes_after']==base['source_hashes_before']
    for row in r['suite_results']:
        if row['passed']:
            assert row['id'] not in passed,'duplicate completed suite pass'
            assert row['tests_run']>=expected[row['id']]['minimum_tests']
            passed[row['id']]=row
        else:
            assert row['id']=='manufacturing-fit' and row['exit_code']=='TIMEOUT' and row['seconds']>=240
            failures.append({'source_report':str(path),'result':row})
assert len(failures)==1 and set(passed)==set(expected) and len(passed)==31
assert sum(x['tests_run'] for x in passed.values())==manifest['minimum_total_tests']==1004
for name,digest in base['source_hashes_before'].items():
    assert hashlib.sha256((R/name).read_bytes()).hexdigest()==digest,'source changed after tested snapshot'
result={**base,'scope':'all_current_suites_with_explicit_timeout_retry','passed':True,'tests_run':1004,'suite_results':[passed[s['id']] for s in manifest['suites']],
        'initial_parallel_attempt_passed':False,'initial_timeout_records':failures,'completed_retry_suite':'manufacturing-fit',
        'canonical_timeout_or_source_changed_for_retry':False,'retry_changed_only_execution_scheduling':True,
        'canonical_invocation_reports':[{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for path,r in raw],
        'complete_unique_suite_coverage':True,'prior_round_results_reused':False,
        'execution':'three unchanged canonical selected-suite invocations plus one unchanged canonical manufacturing-fit retry; initial timeout retained, never called a clean first run'}
target=O/'unit1004-complete-coverage.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n')
print('COMPLETE_COVERAGE',1004,31,F,'initial manufacturing timeout preserved; full455 retry completed',flush=True)
