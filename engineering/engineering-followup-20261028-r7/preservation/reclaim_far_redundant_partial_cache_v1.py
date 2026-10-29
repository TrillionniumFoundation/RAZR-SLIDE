"""Reclaim only the separately observed byte-identical Far ZIP partial cache."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT/'r7-deliverables/RAZR-R7-far-full-factory-and-independent-originals-20261028.zip'
PARTIAL = FINAL.with_suffix('.zip.partial')
SAVE = ROOT/'r7-deliverables/R7_FAR_COMPLETE_PRESERVATION_V1.json'
OBSERVATION = ROOT/'r7-audit/storage-observation/R7_FAR_ARCHIVE_TWO_PATHS_CURRENT_READBACK_V1.json'
OUT = ROOT/'r7-publication/R7_FAR_REDUNDANT_PARTIAL_CACHE_RECLAIM_V1.json'

def identity(p):
    with p.open('rb') as f:
        digest=hashlib.file_digest(f,'sha256').hexdigest()
    return {'bytes':p.stat().st_size,'sha256':digest}

def stat(p):
    s=p.stat()
    return {k:getattr(s,k) for k in ('st_ino','st_dev','st_size','st_nlink','st_mtime_ns','st_ctime_ns')}

def main():
    assert not OUT.exists()
    started=time.time_ns()
    saved=json.loads(SAVE.read_text())
    assert saved['saved_file']['status']=='succeeded'
    assert FINAL.is_file() and PARTIAL.is_file() and not FINAL.is_symlink() and not PARTIAL.is_symlink()
    first=identity(FINAL);second=identity(PARTIAL)
    assert first==second=={'bytes':127370781,'sha256':'7bc806653be9c7e70dea0ad195bcf992d899a06d73e170af499d8f7b10804130'}
    assert first=={k:saved[k] for k in ('bytes','sha256')}
    assert os.getxattr(FINAL,'user.library-file-id').decode()==saved['saved_file']['library_file_id']=='libfile_ffffa1050c0881919fc5608d9acfae2d'
    record={'schema':'razr-r7-far-redundant-partial-cache-reclaim-v1',
            'started_unix_ns':started,'exact_identity':first,
            'final_path':str(FINAL),'final_before':stat(FINAL),
            'partial_path':str(PARTIAL),'partial_before':stat(PARTIAL),
            'saved_original_receipt':{'path':str(SAVE),**identity(SAVE)},
            'earlier_two_path_observation':{'path':str(OBSERVATION),**identity(OBSERVATION)},
            'library_file_id':saved['saved_file']['library_file_id'],'library_version':0,
            'disk_before':shutil.disk_usage(ROOT)._asdict(),
            'historical_rename_to_later_two_path_correspondence_unresolved':True,
            'historical_cause_explained_by_this_new_reclamation':False,
            'science_results_or_original_gates_changed':False,'all_blockers_closed':False}
    PARTIAL.unlink()
    assert identity(FINAL)==first
    record.update(finished_unix_ns=time.time_ns(),partial_absent_at_receipt=not PARTIAL.exists(),
                  final_original_unchanged=True,removed_redundant_cache_bytes=second['bytes'],
                  disk_after=shutil.disk_usage(ROOT)._asdict())
    OUT.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'receipt':str(OUT),**identity(OUT),'disk_after':record['disk_after']}))

if __name__=='__main__':
    main()
