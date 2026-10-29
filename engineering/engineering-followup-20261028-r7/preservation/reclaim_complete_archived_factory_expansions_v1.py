"""Migrate only verified redundant expansions into already saved full archives."""
from pathlib import Path
import hashlib
import json
import os
import resource
import shutil
import signal
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'r7-publication/R7_COMPLETE_FACTORY_ARCHIVE_EXPANSION_MIGRATION_V1.json'
ARCHIVES={
 'near':('RAZR-R7-near-full-factory-and-independent-originals-20261028.zip','R7_NEAR_COMPLETE_PRESERVATION_V1.json','libfile_03369f15bb2c819189c055031babf4ad'),
 'far':('RAZR-R7-far-full-factory-and-independent-originals-20261028.zip','R7_FAR_COMPLETE_PRESERVATION_V1.json','libfile_ffffa1050c0881919fc5608d9acfae2d'),
}
GROUPS=[('far','r7-native/full-far-attempt1-engineering','engineering/')]
for pose in ('near','far'):
    for phase in ('prerequisite-predock','prerequisite-stow_tabs_3'):
        GROUPS.append((pose,'r7-native/full-'+pose+'-attempt1/'+phase,'raw/'+phase+'/'))

def identity(p):
    with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
    return {'bytes':p.stat().st_size,'sha256':h}

def main():
    assert not OUT.exists()
    resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456))
    started=time.monotonic();started_ns=time.time_ns()
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('120-second verified cache migration budget')))
    signal.alarm(120)
    before=shutil.disk_usage(ROOT)._asdict();archives={};bindings={};rows=[]
    for pose,(name,receipt_name,library_id) in ARCHIVES.items():
        p=ROOT/'r7-deliverables'/name;receipt=ROOT/'r7-deliverables'/receipt_name
        saved=json.loads(receipt.read_text());current=identity(p)
        assert saved['saved_file']['status']=='succeeded'
        assert current=={k:saved[k] for k in ('bytes','sha256')}
        assert os.getxattr(p,'user.library-file-id').decode()==saved['saved_file']['library_file_id']==library_id
        archives[pose]=zipfile.ZipFile(p)
        bindings[pose]={'path':str(p),**current,'library_file_id':library_id,'version':0,
                        'saved_receipt':{'path':str(receipt),**identity(receipt)}}
    groups=[]
    for pose,relative,prefix in GROUPS:
        directory=ROOT/relative;assert directory.is_dir() and not directory.is_symlink()
        observed=sorted(p for p in directory.rglob('*') if p.is_file())
        assert not any(p.is_symlink() for p in directory.rglob('*'))
        z=archives[pose]
        member_names={info.filename for info in z.infolist() if not info.is_dir() and info.filename.startswith(prefix)}
        current_names={prefix+p.relative_to(directory).as_posix() for p in observed}
        assert current_names==member_names
        initial_count=len(rows)
        for p in observed:
            rel=p.relative_to(directory).as_posix();member=prefix+rel
            got=identity(p);h=hashlib.sha256();n=0
            with z.open(member) as f:
                while data:=f.read(1048576):h.update(data);n+=len(data)
            assert got=={'bytes':n,'sha256':h.hexdigest()}
            keep=rel in ('ENGINEERING_MANIFEST.json','EXPORT_SCOPE.json')
            rows.append({'path':str(p),'archive':pose,'archive_member':member,**got,
                         'keep_as_local_manifest':keep,'before_inode':p.stat().st_ino})
        groups.append({'directory':str(directory),'archive':pose,'archive_prefix':prefix,
                       'complete_file_count_before':len(observed),'bytes_before':sum(r['bytes'] for r in rows[initial_count:])})
    # Verify every selected path and every full saved archive again before removal.
    assert all(identity(Path(row['path']))=={k:row[k] for k in ('bytes','sha256')} for row in rows)
    assert all(identity(Path(b['path']))=={k:b[k] for k in ('bytes','sha256')} for b in bindings.values())
    removed=0;removed_bytes=0
    for row in rows:
        if not row['keep_as_local_manifest']:
            Path(row['path']).unlink();removed+=1;removed_bytes+=row['bytes']
    for g in groups:
        files=sorted(p for p in Path(g['directory']).rglob('*') if p.is_file())
        g['files_at_receipt']=[p.relative_to(g['directory']).as_posix() for p in files]
        assert g['files_at_receipt']==['ENGINEERING_MANIFEST.json','EXPORT_SCOPE.json']
        g['complete_expansion_available_at_receipt']=False
    assert all(identity(Path(b['path']))=={k:b[k] for k in ('bytes','sha256')} for b in bindings.values())
    for z in archives.values():z.close()
    result={'schema':'razr-r7-full-saved-factory-expansion-migration-v1','started_unix_ns':started_ns,
      'finished_unix_ns':time.time_ns(),'elapsed_seconds':time.monotonic()-started,
      'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
      'source':{'path':str(Path(__file__).resolve()),**identity(Path(__file__))},
      'reason':'Ordinary free space reached zero; only exact already-saved duplicate expansions were selected.',
      'full_saved_archive_bindings':bindings,'complete_selected_source_and_archive_members_CRC_SHA_verified_before_removal':True,
      'all_full_saved_archive_bytes_unchanged_after_removal':True,'groups':groups,
      'selected_before_count':len(rows),'removed_local_duplicate_files':removed,'removed_local_duplicate_bytes':removed_bytes,
      'complete_before_member_records':rows,'disk_before':before,'disk_after':shutil.disk_usage(ROOT)._asdict(),
      'current_original_case_source_complete_expansion_claimed':False,
      'historical_scientific_seals_reports_and_results_unchanged':True,
      'near_previous_migration_discrepancy_directory_modified':False,
      'active_recovery_V6_V9_or_Line_Cylinder_sources_S4_worktree_venv_or_Git_objects_modified':False,
      'prior_storage_correspondence_causes_resolved':False,'all_blockers_closed':False}
    OUT.write_text(json.dumps(result,indent=2)+'\n')
    signal.alarm(0)
    print(json.dumps({'receipt':str(OUT),**identity(OUT),'removed_duplicate_bytes':removed_bytes,'disk_after':result['disk_after'],'seconds':result['elapsed_seconds']}))

if __name__=='__main__':main()
