from pathlib import Path
import datetime,gzip,hashlib,json,re,shutil,subprocess,time
from urllib.parse import unquote
R=Path('/home/qian-qi/RAZR-SLIDE-product-integration-20261018')
E=Path('/home/qian-qi/.local/share/razr-slide-evidence/product-followup-20261020-phase4')
P=Path('engineering/product-integration-20261018/phase4-20261020')
N='9a8307fe4bd4163b53515698fb12cfc0a8cc27e7';M='90b09f5ef7c25aafd812909101b3d7d80081ba05'
PY='/home/qian-qi/.local/share/razr-slide-evidence/product-integration-20261018/venv-recheck-20261019/bin/python'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=R,text=True)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
assert git('rev-parse','HEAD').strip()==N
started=utc();clock=time.monotonic()
n=read(E/'predock-9a8307f/native/native-report.json')
sources=n['source_sha256'];assert all(sha(R/k)==v for k,v in sources.items())
arc=read(E/'phase4-archive-receipt.json')
assert arc['native_source_commit']==N and arc['native_source_inputs_unchanged_after_archive']
for row in arc['items']:
    p=R/row['path'];assert sha(p)==row['sha256'],str(p)
    if row['gzip']:
        b=gzip.decompress(p.read_bytes());assert len(b)==row['original_bytes'] and hashlib.sha256(b).hexdigest()==row['original_sha256']
assert sha(R/arc['summary_path'])==arc['summary_sha256']
for label in ['predock','open-stow','a-head-relief','key-local']:
    v=read(E/('readback-'+label+'-9a8307f/report.json'))
    assert v['execution_completed'] and v['declared_readback_checks_passed'] and v['native_source_commit']==N
    assert all(sha(k)==x['sha256'] for k,x in v['retained_input_files'].items())
for src,dest in [('phase4-archive-receipt.json','phase4-archive-receipt.json'),
                 ('phase4-state-update-receipt.json','phase4-state-update-receipt.json')]:
    p=R/P/'validation'/dest;assert not p.exists();shutil.copyfile(E/src,p)
controller=R/P/'validation/controllers/razr_phase4_verify_final.py'
assert not controller.exists();shutil.copyfile(__file__,controller)
scope={k:sha(R/k) for k in sources}
for rel in ['design/current_product.json','README.md','CURRENT_DESIGN.md','status.json',
            'engineering/product-integration-20261018/README.md','tools/sync_current_design.py',
            'integration/product-study-tests/test_product_state.py',str(P/'README.md'),str(P/'SUMMARY.json'),
            str(P/'local-studies/SUMMARY.json'),str(controller.relative_to(R))]:scope[rel]=sha(R/rel)
runs=[]
for label,cmd in [('entrypoint-sync',[PY,'-B','tools/sync_current_design.py','--check']),
        ('five-product-state-tests',[PY,'-B','-m','unittest','discover','-s','integration/product-study-tests','-p','test_product_state.py','-v'])]:
    t=time.monotonic();start=utc();cp=subprocess.run(cmd,cwd=R,text=True,capture_output=True,timeout=180)
    log=R/P/'validation'/(label+'.log');assert not log.exists();log.write_text(cp.stdout+cp.stderr)
    row={'label':label,'command':cmd,'cwd':str(R),'started_utc':start,'finished_utc':utc(),
        'seconds':time.monotonic()-t,'exit_code':cp.returncode,'log':str(log.relative_to(R)),
        'log_sha256':sha(log),'stdout':cp.stdout,'stderr':cp.stderr}
    if label=='five-product-state-tests':
        ids=re.findall(r'^(test_\S+)\s+\(([^)]+)\)\s+\.\.\.\s+ok\s*$',cp.stdout+cp.stderr,re.M)
        row['tests_run']=len(ids);row['test_identities']=[i[1] for i in ids]
        assert len(ids)==5 and re.search(r'Ran 5 tests in ',cp.stdout+cp.stderr)
    runs.append(row);assert cp.returncode==0,row
assert scope=={k:sha(R/k) for k in scope}
c=read(R/'design/current_product.json');s=read(R/P/'SUMMARY.json');summ=read(R/P/'native-summary.json')
assert c['implementation_baseline']['commit']=='a1b3cc1e0773446f2e36d0a607edf61211dd9919'
assert c['current_execution_summary']==str(P/'SUMMARY.json')
assert c['latest_product_execution']['phase']=='phase4-20261020' and c['latest_product_execution']['functional_commit']==N
assert c['latest_product_execution']['execution_summary']==str(P/'SUMMARY.json')
assert c['publication_record']==str(P/'validation/ep4-source-commit.json')
old=json.loads(git('show',N+':design/current_product.json'))
assert c['historical_product_executions'][-1]==old['latest_product_execution']
assert c['completed_unit_runs'][:-1]==old['completed_unit_runs']
assert c['active_followup']['full_local_unit_execution_passed'] is False and c['active_followup']['hosted_execution_restored'] is False
assert summ['all_three_poses_rejected'] and summ['unique_declared_pairs']==15886 and summ['actual_declared_pairs_across_two_executions']==16266
assert [x['combined_participants'] for x in summ['poses']]==[154,154,161]
assert [x['external']['positive_Common_count'] for x in summ['poses']]==[17,12,25]
assert summ['pair_evaluation_errors']==summ['containment_evaluation_errors']==0
assert all(x[k]['context_errors']==0 for x in summ['poses'] for k in ['external','A_to_B','material_to_ends'])
assert c['product_constraints']['same_finished_A_B_envelope'] and not c['product_constraints']['independent_rear_display']
assert c['product_constraints']['total_capacity_target_mAh']==4700
assert s['selected_unit_execution']['tests']==137 and s['configured_tests']==1324 and not s['full_registry_rerun']
assert sha(R/'design/product_interfaces.json')=='a5eeba7042ee44d1b8317e5e5d084b0bddbf6609550652a50f721a29af6f1bd7'
assert sha(R/'engineering/product-integration-20261018/hardware/records/xt2551-3-20261020-f4db100-identity/record.json')=='b4200d53ab68ec95733eb00d26b3e53ee35a3055d448c8b70d81b024910cad7f'
for record in [s,s['EP4'],summ]:
    for key in ['candidate_go','fixture_fabrication_go','manufacturing_go']:assert record[key] is False
links=[];missing=[]
for doc in [*(R/P).rglob('*.md'),R/'engineering/product-integration-20261018/README.md']:
    # The archived prior PR body contains links relative to GitHub's PR view,
    # so preserve it byte-for-byte and inspect new repository docs instead.
    if doc.name=='previous-pr36-body-90b09f5.md':continue
    for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',doc.read_text()):
        target=target.split()[0].strip('<>')
        if not target or target.startswith(('#','http://','https://','mailto:','data:')):continue
        rel=unquote(target.split('#',1)[0]);dest=(doc.parent/rel).resolve()
        ok=dest.exists() or dest==R/P/'artifact-index.json'
        row={'source':str(doc.relative_to(R)),'target':target,'exists_or_pending_index':ok};links.append(row)
        if not ok:missing.append(row)
assert not missing,missing
assert subprocess.run(['git','diff','--check'],cwd=R).returncode==0
allowed={'README.md','CURRENT_DESIGN.md','status.json','design/current_product.json','engineering/product-integration-20261018/README.md'}
assert set(git('diff','--name-only').splitlines())<=allowed
untracked=git('ls-files','--others','--exclude-standard').splitlines()
assert all(k.startswith(str(P)+'/') for k in untracked)
rep={'schema':'razr-phase4-publication-verification-v1','started_utc':started,'finished_utc':utc(),
 'seconds':time.monotonic()-clock,'prepublication_head':N,'working_tree_contains_archive_and_metadata_updates':True,
 'scope':'archive identities/gzip, four independent reader inputs, generated entries and five existing state tests; not a full unit/native/hardware rerun',
 'commands':runs,'checked_sources_sha256':scope,'checked_sources_unchanged_during_verification':True,
 'archived_files':len(arc['items']),'all_archive_bytes_verified':True,
 'relative_links_checked':len(links),'missing_relative_links':[],'relative_links':links,
 'historical_latest_execution_and_unit_records_preserved':True,'all_native_inputs_match_executed_N':True,
 'donor_record_and_interfaces_preserved':True,'all_declared_publication_checks_passed':True,
 'candidate_go':False,'manufacturing_go':False,'hosted_execution_restored':False,'physical_phone_verified':False}
report=R/P/'validation/publication-verification.json';assert not report.exists();write(report,rep)
index_path=R/P/'artifact-index.json';assert not index_path.exists()
paths={p.relative_to(R).as_posix() for p in (R/P).rglob('*') if p.is_file()}
paths.update(sources);paths.update(k for k in git('diff','--name-only',M).splitlines() if (R/k).is_file())
items=[]
for rel in sorted(paths):
    p=R/rel;row={'path':rel,'bytes':p.stat().st_size,'sha256':sha(p)}
    if rel.endswith('.gz'):
        b=gzip.decompress(p.read_bytes());row.update(uncompressed_bytes=len(b),uncompressed_sha256=hashlib.sha256(b).hexdigest())
    items.append(row)
index={'schema':'razr-phase4-artifact-index-v1','created_utc':utc(),'native_execution_source_commit':N,
 'prepublication_head':N,'previous_published_head':M,'items':items,'item_count':len(items),
 'scope':'phase4 tree, unchanged native input files and files changed since M; index excludes itself and is bound by containing Git commit',
 'candidate_go':False,'manufacturing_go':False}
write(index_path,index)
assert all(sha(R/x['path'])==x['sha256'] for x in items)
receipt={'created_utc':utc(),'prepublication_head':N,'all_declared_publication_checks_passed':True,
 'verification_report':str(report.relative_to(R)),'verification_report_sha256':sha(report),
 'artifact_index':str(index_path.relative_to(R)),'artifact_index_sha256':sha(index_path),'indexed_files':len(items),
 'git_diff_stat':git('diff','--stat'),'git_status':git('status','--porcelain')}
write(E/'phase4-final-verification-receipt.json',receipt)
print(json.dumps({k:v for k,v in receipt.items() if k!='git_status'},indent=2))
