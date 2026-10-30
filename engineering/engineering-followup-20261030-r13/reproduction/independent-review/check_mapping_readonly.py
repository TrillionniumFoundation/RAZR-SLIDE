"""Independent read-only content/HEAD check; no scientific recomputation."""
from pathlib import Path
import hashlib,json,subprocess,time
HERE=Path(__file__).resolve().parent
AFTER=HERE.parent/'r13_reproduction_work/after-recovery/R13_EXECUTION_INPUT_TO_REPOSITORY_MAP.json'
BEFORE=HERE.parent/'r13_reproduction_work/R13_EXECUTION_INPUT_TO_REPOSITORY_MAP.json'
def sha(b):return hashlib.sha256(b).hexdigest()
start=time.monotonic();after=json.loads(AFTER.read_text());before=json.loads(BEFORE.read_text())
repo=Path(after['repository']['absolute_path_at_mapping']);head=after['repository']['observed_HEAD']
assert head==before['repository']['observed_HEAD']=='ab9ef3270a9a0d0d28f605f7188038db133dbcd8'
git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
observed_before=git('rev-parse','HEAD').decode().strip();assert observed_before==head
tree={}
for raw in git('ls-tree','-rz',head).split(b'\0'):
    if not raw:continue
    meta,path=raw.split(b'\t',1);mode,kind,oid=meta.decode().split();tree[path.decode()]=(mode,kind,oid)
blob_cache={};current_cache={}
def current(relative):
    if relative not in current_cache:
        p=repo/relative;assert not Path(relative).is_absolute() and '..' not in Path(relative).parts and p.is_file() and not p.is_symlink()
        raw=p.read_bytes();current_cache[relative]=(len(raw),sha(raw))
    return current_cache[relative]
def at_head(relative,required):
    if relative not in tree:return False
    mode,kind,oid=tree[relative];assert kind=='blob' and mode in ('100644','100755')
    if oid not in blob_cache:
        raw=git('cat-file','blob',oid);blob_cache[oid]=(len(raw),sha(raw))
    return blob_cache[oid]==required
rows=[];head_count=worktree_count=0;recovered=[]
for entry in after['entries']:
    required=(entry['required_bytes'],entry['required_sha256'])
    assert current(entry['preferred_repository_path'])==required
    all_head=False;matches=[]
    for candidate in entry['repository_matches']:
        relative=candidate['repository_path'];assert current(relative)==required
        has=at_head(relative,required);assert has==candidate['exact_bytes_present_at_observed_HEAD'];all_head|=has
        if entry['group']=='geometry.EXTERNAL_DEPENDENCIES':matches.append({'repository_path':relative,'size_SHA256_verified':True,'exact_blob_size_SHA256_at_observed_HEAD':has})
    assert all_head==(entry['repository_match_status']=='present_at_observed_HEAD')
    head_count+=all_head;worktree_count+=not all_head
    if entry['group']=='geometry.EXTERNAL_DEPENDENCIES':
        original=Path(entry['original_absolute_path']);raw=original.read_bytes();assert (len(raw),sha(raw))==required
        row={'entry_id':entry['entry_id'],'original_absolute_path':str(original),'preferred_repository_path':entry['preferred_repository_path'],
             'bytes':required[0],'sha256':required[1],'preferred_repository_size_SHA256_match':True,'original_size_SHA256_match':True,'all_repository_candidates':matches}
        rows.append(row)
        if '/roi-producer-v2/report.json' in str(original) or '/roi-reader-v2/report.json' in str(original):
            rp=entry['preferred_repository_path'];assert rp.startswith('engineering/engineering-followup-20261030-r13/reproduction/recovered-r11-inputs/')
            assert (repo/rp).read_bytes()==raw
            recovered.append({'original_path':str(original),'repository_path':rp,'bytes':len(raw),'sha256':sha(raw),'byte_for_byte_equal':True,'present_at_observed_HEAD':at_head(rp,required)})
assert len(rows)==11 and len(recovered)==2
assert head_count==38 and worktree_count==22 and len(after['entries'])==60
assert before['summary']['records_with_exact_repository_match']==58 and before['summary']['records_without_exact_repository_match']==2
assert after['summary']['records_with_exact_repository_match']==60 and after['summary']['records_without_exact_repository_match']==0
observed_after=git('rev-parse','HEAD').decode().strip();assert observed_after==head
out={'schema':'razr-r13-independent-readonly-execution-input-map-review-v1','completed':True,'source_sha256':sha(Path(__file__).read_bytes()),
     'after_recovery_map':{'path':str(AFTER),'bytes':AFTER.stat().st_size,'sha256':sha(AFTER.read_bytes())},
     'original_snapshot':{'path':str(BEFORE),'sha256':sha(BEFORE.read_bytes()),'matched_records':58,'total_records':60},
     'observed_HEAD_before':observed_before,'observed_HEAD_after':observed_after,
     'all_60_preferred_and_listed_candidates_content_checked':True,'after_matched_records':60,'records_at_observed_HEAD':head_count,'worktree_only_records':worktree_count,
     'external_dependencies_independently_checked':rows,'recovered_original_R11_reports':recovered,
     'scope':{'content_location_identity_only':True,'original_workspace_sibling_layout_recreated':False,
              'original_interpreter_libraries_or_runtime_environment_reproduced':False,'scientific_execution_reproduced':False,
              'CAD_arithmetic_or_numerics_rerun':False,'repository_or_sealed_work_modified':False,'native_or_physical_qualification_added':False},
     'seconds':time.monotonic()-start}
p=HERE/'R13_REPRODUCTION_MAP_INDEPENDENT_REVIEW.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'completed':True,'all_records':60,'external':11,'recovered_R11_reports':2,'HEAD':head,'seconds':out['seconds'],'report_sha256':sha(p.read_bytes())}))
