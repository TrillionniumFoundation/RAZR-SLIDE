from pathlib import Path
import json,gzip,hashlib,datetime,time,subprocess,re,sys,shutil
from urllib.parse import unquote
R=Path('/home/qian-qi/RAZR-SLIDE-product-integration-20261018')
E=Path('/home/qian-qi/.local/share/razr-slide-evidence/product-followup-20261020')
P=Path('engineering/product-integration-20261018/phase3-20261020')
DR=Path('engineering/product-integration-20261018/hardware/records/xt2551-3-20261020-f4db100-identity')
A='a33e58cd555b8d9aff1e3649f79cd0dba378a804'
K='f4db100cb62c0ac492118bf605b0e9e7ac7cce32'
PY='/home/qian-qi/.local/share/razr-slide-evidence/product-integration-20261018/venv-recheck-20261019/bin/python'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=R,text=True)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
assert git('rev-parse','HEAD').strip()==A
start=utc();t=time.monotonic()
native=read(E/'ep3-native-a33e58c/native/native-report.json')
archive=read(E/'phase3-final-archive-preparation.json')
assert native['source_commit']==A and native['source_bytes_unchanged']
assert all(sha(R/k)==h for k,h in native['input_sha256'].items())
for item in archive['items']:
 p=R/item['path'];assert sha(p)==item['sha256'],str(p)
 if item.get('gzip'):
  data=gzip.decompress(p.read_bytes())
  assert len(data)==item['original_bytes'] and hashlib.sha256(data).hexdigest()==item['original_sha256']
assert sha(R/archive['summary_path'])==archive['summary_sha256']
assert sha(R/archive['comparison_path'])==archive['comparison_sha256']
receipts=[
 ('phase3-final-archive-preparation.json','phase3-evidence-archive.json'),
 ('phase3-final-state-update.json','phase3-state-update.json')]
for source,name in receipts:
 d=R/P/'validation'/name
 assert not d.exists(),str(d)
 shutil.copyfile(E/source,d)
 assert sha(E/source)==sha(d)
controller=R/P/'validation/final-verification.py'
assert not controller.exists()
shutil.copyfile(Path(__file__),controller)
checks_before={k:sha(R/k) for k in native['input_sha256']}
for rel in ['design/current_product.json','README.md','CURRENT_DESIGN.md','status.json',
 'tools/sync_current_design.py','integration/product-study-tests/test_product_state.py',
 str(P/'README.md'),str(P/'SUMMARY.json'),str(P/'EP3_ROUTING.md'),str(controller.relative_to(R))]:
 checks_before[rel]=sha(R/rel)
runs=[]
commands=[
 ('entrypoint-sync',[PY,'-B','tools/sync_current_design.py','--check']),
 ('five-product-state-tests',[PY,'-B','-m','unittest','discover','-s','integration/product-study-tests','-p','test_product_state.py','-v'])]
for label,cmd in commands:
 ts=utc();tm=time.monotonic()
 cp=subprocess.run(cmd,cwd=R,text=True,capture_output=True,timeout=180)
 out=cp.stdout+cp.stderr
 log=R/P/'validation'/(label+'.log')
 assert not log.exists()
 log.write_text(out)
 row={'label':label,'command':cmd,'cwd':str(R),'started_utc':ts,'finished_utc':utc(),
 'seconds':time.monotonic()-tm,'exit_code':cp.returncode,'log':str(log.relative_to(R)),
 'log_sha256':sha(log),'stdout':cp.stdout,'stderr':cp.stderr}
 if label=='five-product-state-tests':
  ids=re.findall(r'^(test_\S+)\s+\(([^)]+)\)\s+\.\.\.\s+ok\s*$',out,re.M)
  row['tests_run']=len(ids);row['test_identities']=[obj for name,obj in ids]
  row['ran_five_reported']=bool(re.search(r'Ran 5 tests in ',out))
  assert row['tests_run']==5 and row['ran_five_reported'],row
 runs.append(row)
 assert cp.returncode==0,row
checks_after={k:sha(R/k) for k in checks_before}
assert checks_before==checks_after
links=[]
missing=[]
for doc in sorted((R/P).rglob('*.md')):
 for raw in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',doc.read_text()):
  target=raw.split()[0].strip('<>')
  if not target or target.startswith(('#','http://','https://','mailto:','data:')):continue
  path=unquote(target.split('#',1)[0])
  if not path:continue
  dest=(doc.parent/path).resolve()
  exists=dest.is_file() or dest.is_dir() or dest==R/P/'artifact-index.json'
  row={'source':str(doc.relative_to(R)),'target':target,'exists_or_pending_index':exists}
  links.append(row)
  if not exists:missing.append(row)
assert not missing,missing
c=read(R/'design/current_product.json')
s=read(R/P/'SUMMARY.json')
summary=read(R/P/'native-summary.json')
assert c['implementation_baseline']['commit']=='a1b3cc1e0773446f2e36d0a607edf61211dd9919'
assert c['product_constraints']['same_finished_A_B_envelope'] is True
assert c['product_constraints']['independent_rear_display'] is False
assert c['product_constraints']['total_capacity_target_mAh']==4700
assert c['active_followup']['selected_109_test_commit']=='bdb1bc19fce49692fd49cd508031bfc456e15208'
assert c['active_followup']['native_execution_commit']==A
assert c['active_followup']['full_local_unit_execution_passed'] is False
assert c['active_followup']['hosted_execution_restored'] is False
assert s['EP3']['all_three_poses_rejected'] is True
for key in ['candidate_go','fixture_fabrication_go','manufacturing_go','physical_fabrication_executed','full_cycle_internal_route_accepted']:
 assert summary[key] is False,key
assert summary['total_pair_evaluation_errors']==0 and summary['total_containment_evaluation_errors']==0
assert [q['combined_participants'] for q in summary['poses']]==[154,154,161]
assert sha(R/'design/product_interfaces.json')=='a5eeba7042ee44d1b8317e5e5d084b0bddbf6609550652a50f721a29af6f1bd7'
assert sha(R/DR/'record.json')=='b4200d53ab68ec95733eb00d26b3e53ee35a3055d448c8b70d81b024910cad7f'
rep={'schema':'razr-phase3-publication-input-verification-v1','started_utc':start,'finished_utc':utc(),
 'seconds':time.monotonic()-t,'prepublication_git_head':A,'working_tree_had_archive_and_metadata_changes':True,
 'verification_scope':'entrypoint synchronization, five existing state regressions, archive byte identities, relative links and preserved actual evidence scopes; not a new full unit/native/hardware execution',
 'controller_sha256':sha(controller),'commands':runs,'checked_source_sha256_before':checks_before,
 'checked_source_sha256_after':checks_after,'checked_sources_unchanged_during_verification':True,
 'native_input_file_count':len(native['input_sha256']),'all_native_inputs_match_executed_A33':True,
 'archived_transferred_file_count':len(archive['items']),'all_archive_hashes_and_gzip_roundtrips_match':True,
 'relative_links_checked':len(links),'missing_relative_links':[],'relative_links':links,
 'donor_interfaces_and_imported_record_hashes_preserved':True,
 'all_declared_publication_input_checks_passed':True,'candidate_go':False,'manufacturing_go':False,
 'hosted_execution_restored':False,'physical_phone_verified':False}
report=R/P/'validation/publication-input-verification.json'
assert not report.exists();write(report,rep)
index_path=R/P/'artifact-index.json'
assert not index_path.exists()
paths={p.relative_to(R).as_posix() for p in (R/P).rglob('*') if p.is_file()}
paths.update(p.relative_to(R).as_posix() for p in (R/DR).rglob('*') if p.is_file())
paths.update(native['input_sha256'])
paths.update(p for p in git('diff','--name-only',K).splitlines() if (R/p).is_file())
paths.update(p for p in git('ls-files','--others','--exclude-standard').splitlines() if (R/p).is_file())
paths.discard(str(index_path.relative_to(R)))
items=[]
for rel in sorted(paths):
 p=R/rel;item={'path':rel,'bytes':p.stat().st_size,'sha256':sha(p)}
 if rel.endswith('.gz'):
  raw=gzip.decompress(p.read_bytes());item.update(uncompressed_bytes=len(raw),uncompressed_sha256=hashlib.sha256(raw).hexdigest())
 items.append(item)
index={'schema':'razr-phase3-publication-artifact-index-v1','created_utc':utc(),
 'native_execution_source_commit':A,'selected_109_test_source_commit':'bdb1bc19fce49692fd49cd508031bfc456e15208',
 'donor_collection_source_commit':K,'prepublication_head':A,
 'scope':'phase3 subtree, formal donor record, actual native inputs, and files changed since the previously published f4db100; index excludes itself and is bound by its final Git commit',
 'item_count':len(items),'items':items,'publication_head':'resolved by containing Git commit and PR36; no self-referential hash',
 'all_items_identified_after_final_metadata_and_verification':True,'candidate_go':False,'manufacturing_go':False}
write(index_path,index)
assert all(sha(R/item['path'])==item['sha256'] for item in items)
assert all(sha(R/k)==h for k,h in native['input_sha256'].items())
porcelain=git('status','--porcelain')
receipt={'created_utc':utc(),'prepublication_head':A,'verification_report':str(report.relative_to(R)),
 'verification_report_sha256':sha(report),'artifact_index':str(index_path.relative_to(R)),
 'artifact_index_sha256':sha(index_path),'indexed_files':len(items),
 'all_declared_publication_input_checks_passed':True,'native_inputs_unchanged':True,
 'git_status':porcelain,'git_diff_stat':git('diff','--stat'),'controller_sha256':sha(controller)}
write(E/'phase3-final-verification-receipt.json',receipt)
print(json.dumps(receipt,ensure_ascii=False),flush=True)
