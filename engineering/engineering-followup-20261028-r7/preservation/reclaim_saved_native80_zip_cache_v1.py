#!/usr/bin/env python3
"""Remove one verified, durably saved ZIP cache; preserve its exact identity."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'r7-deliverables/RAZR-R7-native80-runtime-and-original-evidence-20261028.zip'
SAVE = ROOT / 'r7-deliverables/R7_NATIVE80_COMPLETE_PRESERVATION_V1.json'
OUT = ROOT / 'r7-publication/R7_SAVED_NATIVE80_ZIP_CACHE_RECLAIM_V1.json'

def digest(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def main():
    if OUT.exists():
        raise RuntimeError('single-use receipt already exists')
    t0 = time.time_ns()
    saved = json.loads(SAVE.read_text())
    assert saved['saved_file']['status'] == 'succeeded'
    assert saved['saved_file']['local_path'] == str(ARCHIVE)
    assert ARCHIVE.is_file() and not ARCHIVE.is_symlink()
    stat = ARCHIVE.stat()
    sha = digest(ARCHIVE)
    assert stat.st_size == saved['bytes'] == 130335275
    assert sha == saved['sha256'] == '99eca1ecc39c8f2a9334734535b5fb46da92204d13f577ffe733081801997ef7'
    library_id = os.getxattr(ARCHIVE, 'user.library-file-id').decode()
    assert library_id == saved['saved_file']['library_file_id'] == 'libfile_0565f7df7c1c8191a5406441e7dcf317'
    before = shutil.disk_usage(ROOT)._asdict()
    source_identity = {'path':str(SAVE), 'bytes':SAVE.stat().st_size, 'sha256':digest(SAVE)}
    ARCHIVE.unlink()
    result = {
      'schema':'razr-r7-single-durable-zip-cache-reclaim-v1',
      'started_unix_ns':t0, 'finished_unix_ns':time.time_ns(),
      'archive_path':str(ARCHIVE), 'removed_local_cache_bytes':stat.st_size,
      'archive_sha256':sha, 'library_file_id':library_id,
      'library_version':saved['saved_file']['current_version_number'],
      'durable_save_receipt':source_identity,
      'local_archive_absent_at_receipt':not ARCHIVE.exists(),
      'disk_before':before, 'disk_after':shutil.disk_usage(ROOT)._asdict(),
      'scope':'One previously saved ZIP cache only; complete archive remains at the exact Library identity and hash. No active source, native original, Git object, near ZIP, or scientific result is selected for removal.',
      'scientific_gates_changed':False, 'all_blockers_closed':False
    }
    OUT.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'receipt':str(OUT),'bytes':OUT.stat().st_size,'sha256':digest(OUT),'disk_after':result['disk_after'],'removed_local_cache_bytes':stat.st_size}))

if __name__ == '__main__':
    main()
