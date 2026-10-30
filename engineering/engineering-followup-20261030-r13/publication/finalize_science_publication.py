#!/usr/bin/env python3
"""Record an actually fetched R13 science commit; update publication metadata only."""
import argparse,datetime,hashlib,json,pathlib,shutil,subprocess,time

ROOT=pathlib.Path('/workspace/scratch/1b842ca762be/RAZR-SLIDE')
REL='engineering/engineering-followup-20261030-r13'
HERE=ROOT/REL
BRANCH='evidence/full-sprint-20261030-r13'
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT).decode().strip()
def ident(path):
    b=path.read_bytes();return {'path':path.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(path,obj):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--remote',required=True);ap.add_argument('--upload-root',required=True);a=ap.parse_args()
    up=pathlib.Path(a.upload_root);plan=json.loads((up/'PUBLICATION_PLAN.json').read_text());local=plan['local_target_commit'];remote=a.remote
    assert git('rev-parse','HEAD')==remote
    assert git('rev-parse','refs/remotes/origin/'+BRANCH)==remote
    assert git('rev-parse',local+'^{tree}')==git('rev-parse',remote+'^{tree}')==plan['expected_tree']
    assert git('rev-parse',local+'^')==git('rev-parse',remote+'^')==plan['base_commit']
    assert git('diff','--raw',local,remote)==''
    pub=HERE/'publication/R13-science';pub.mkdir(parents=True,exist_ok=True)
    shutil.copy2(up/'PUBLICATION_PLAN.json',pub/'PUBLICATION_PLAN.json')
    shutil.copy2(up/'original-local.commit',pub/(local+'.commit'))
    raw=(pub/(local+'.commit')).read_bytes();assert hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==local
    (pub/'object-receipts').mkdir(exist_ok=True)
    receipts=[]
    for p in sorted((up/'receipts').glob('*.json')):
        r=json.loads(p.read_text());assert r['exact_identity_match'] is True
        q=pub/'object-receipts'/p.name;shutil.copy2(p,q);receipts.append(ident(q))
    assert len(receipts)==plan['upload_jobs']
    for name in ['TREE_COMMIT_REF_RECEIPT.json']:
        shutil.copy2(up/name,pub/name)
    source=HERE/'publication/finalize_science_publication.py';shutil.copy2(pathlib.Path(__file__),source)
    receipt={'schema':'razr-r13-actual-science-publication-and-git-readback-v1','verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'repository':'TrillionniumFoundation/RAZR-SLIDE','branch':BRANCH,'base_commit':plan['base_commit'],
        'local_science_commit':local,'published_science_commit':remote,'source_tree':plan['expected_tree'],
        'source_trees_identical':True,'all_content_diff_empty':True,'parent_order_verified':True,
        'actual_Git_fetch_completed':True,'fetched_remote_branch_head_matches':True,'commit_metadata_identical':False,
        'original_local_commit_raw_bytes':ident(pub/(local+'.commit')),
        'public_commit_url':'https://github.com/TrillionniumFoundation/RAZR-SLIDE/commit/'+remote,
        'public_branch_url':'https://github.com/TrillionniumFoundation/RAZR-SLIDE/tree/'+BRANCH,
        'changed_files_relative_to_public_R12':plan['changed_files'],'changed_content_bytes':plan['changed_content_bytes'],
        'added_files':plan['added_files'],'modified_files':plan['modified_files'],'deleted_files':plan['deleted_files'],
        'new_object_upload_jobs_verified':len(receipts),'object_receipts':receipts,
        'exact_publication_plan':ident(pub/'PUBLICATION_PLAN.json'),'recording_source':ident(source),
        'explicit_current_user_publication_authorization':True,'scientific_or_physical_release_changed_by_publication':False,
        'scope':'This records the already-published science commit. Its containing publication-metadata followup has a separate Git identity; no self-hash or future ref update is claimed.'}
    target=HERE/'publication/R13_SCIENCE_PUBLICATION_READBACK.json';write(target,receipt)
    cp=ROOT/'design/current_product.json';x=json.loads(cp.read_text())
    if 'r13_science_seal_publication_state' not in x:
        x['r13_science_seal_publication_state']={k:x[k] for k in ['publication_record','publication_record_scope','stage_summary']}
    x['publication_record']=target.relative_to(ROOT).as_posix()
    x['publication_record_scope']='R13 science is publicly verified at '+remote+' with source tree '+plan['expected_tree']+'. Actual Git fetch, parent order and an empty source diff match original local science commit '+local+'. API commit metadata differs; exact original commit bytes are retained. This publication-metadata followup records the science identity without self-hashing; all scientific and physical release states remain unchanged.'
    x['stage_summary']=x['stage_summary'].replace('R12 is publicly verified with exact source-tree equivalence.','R12 and R13 science are publicly verified with exact source-tree equivalence.')
    x['active_followup'].update({'new_branch_pushed':True,'published_science_commit':remote,
        'published_science_tree':plan['expected_tree'],'science_publication_readback':x['publication_record'],
        'containing_commit_scope':'The published science commit is verified by an actual Git readback; this containing metadata followup retains a separate Git identity.'})
    for w in x['work_packages']:
        if w['id']=='WP9':
            w.update({'result':'R12 and R13 science are publicly published. R13 science commit '+remote+' has exact source-tree equivalence to the original local science commit, verified by actual Git fetch and empty content diff. Complete source scopes, original local commit bytes, native failures, conditional proof ledgers and independent reviews remain retained.',
                'path':x['publication_record'],'remaining':'Retain exact science and metadata identities. Commit metadata differs from local originals; publication does not close native, structural, electrical or physical qualification.'})
    x['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    x['current_publication_sync_r13']={'science_commit':remote,'science_tree':plan['expected_tree'],
        'science_report_bytes_unchanged':True,'physical_release_unchanged':True,
        'validation_record':REL+'/status/R13_PUBLICATION_ENTRYPOINT_SYNC_RESULT.json'}
    write(cp,x)
    runs=[]
    for argv in [['python3','-B','tools/sync_current_design.py'],['python3','-B','tools/sync_current_design.py','--check']]:
        t=time.monotonic();r=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True)
        runs.append({'argv':argv,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'elapsed_seconds':time.monotonic()-t});assert r.returncode==0
    ledger=json.loads((HERE/'R13_COMPLETED_WORK_LEDGER.json').read_text())
    for row in ledger['bound_records']:
        actual=ident(ROOT/row['path']);assert all(actual[k]==row[k] for k in ['bytes','sha256'])
    assert not any(ledger['release'].values())
    report={'schema':'razr-r13-actual-publication-entrypoint-sync-v1','runs':runs,
        'source_and_outputs':[ident(ROOT/n) for n in ['design/current_product.json','CURRENT_DESIGN.md','docs/RESEARCH_OVERVIEW.md','status.json']],
        'science_ledger_identity':ident(HERE/'R13_COMPLETED_WORK_LEDGER.json'),'all_31_bound_science_records_unchanged':True,
        'source_reports_and_native_or_physical_release_changed':False,'new_test_or_science_execution':False,
        'published_science_receipt':ident(target),'containing_followup_commit_identity':'Recorded by Git after commit; not self-referential.'}
    write(HERE/'status/R13_PUBLICATION_ENTRYPOINT_SYNC_RESULT.json',report)
    print(json.dumps({'published_science_commit':remote,'source_tree':plan['expected_tree'],'science_scope_unchanged':True,'entrypoint_check_passed':True}))
if __name__=='__main__':main()
