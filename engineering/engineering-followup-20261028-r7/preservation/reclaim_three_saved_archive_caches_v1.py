"""Remove only three byte-verified, already durably saved ZIP cache copies."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'r7-publication/R7_THREE_SAVED_ARCHIVE_CACHE_RECLAIM_V1.json'


def identity(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes': path.stat().st_size, 'sha256': digest}


def main():
    assert not OUT.exists()
    started = time.monotonic()
    rows = []
    for name in ('R7_METHOD_COMPLETE_PRESERVATION_V1.json', 'R7_V9_COMPLETE_PRESERVATION_V1.json'):
        receipt_path = ROOT / 'r7-deliverables' / name
        receipt = json.loads(receipt_path.read_text())
        saved = receipt['saved_file']
        expected = receipt.get('verified_identity', receipt)
        rows.append((receipt_path, saved, {k: expected[k] for k in ('bytes', 'sha256')}))
    receipt_path = ROOT / 'r7-deliverables/R7_STAGE1_PRESERVATION.private.json'
    original = json.loads(receipt_path.read_text())
    saved = original['files'][1]
    assert saved['library_file_id'] == 'libfile_bf9c5f9de76c81919a3b93b29fcabc10'
    rows.append((receipt_path, saved, {k: saved[k] for k in ('bytes', 'sha256')}))
    verified = []
    for receipt_path, saved, expected in rows:
        path = Path(saved['local_path'])
        assert path.parent == ROOT / 'r7-deliverables' and path.suffix == '.zip'
        assert saved['status'] == 'succeeded' and saved['local_metadata_applied'] is True
        assert path.is_file() and not path.is_symlink()
        actual = identity(path)
        assert actual == expected
        assert os.getxattr(path, 'user.library-file-id').decode() == saved['library_file_id']
        assert os.getxattr(path, 'user.library-file-version').decode() == str(saved['current_version_number'])
        verified.append({'path': str(path), **actual,
                         'library_file_id': saved['library_file_id'],
                         'file_id': saved['file_id'], 'saved_version': saved['current_version_number'],
                         'save_receipt_sha256': identity(receipt_path)['sha256'],
                         'saved_identity_and_metadata_verified': True, 'local_cache_removed': False})
    record = {'schema': 'razr-r7-three-saved-archive-cache-reclaim-v1',
              'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'only_duplicate_local_ZIP_copies_selected': True,
              'saved_originals_and_expanded_scientific_inputs_untouched': True,
              'ordinary_available_before': shutil.disk_usage(ROOT).free,
              'files': verified, 'completed': False, 'removed_bytes': 0,
              'unexplained_capacity_change_cause_attributed': False,
              'scientific_failure_reclassified': False, 'all_blockers_closed': False}
    OUT.write_text(json.dumps(record, indent=2) + '\n')
    try:
        for row in verified:
            path = Path(row['path'])
            assert identity(path) == {k: row[k] for k in ('bytes', 'sha256')}
            assert os.getxattr(path, 'user.library-file-id').decode() == row['library_file_id']
            path.unlink()
            row['local_cache_removed'] = not path.exists()
            assert row['local_cache_removed']
            record['removed_bytes'] += row['bytes']
            OUT.write_text(json.dumps(record, indent=2) + '\n')
        record['completed'] = True
    finally:
        record['seconds'] = time.monotonic() - started
        record['ordinary_available_after'] = shutil.disk_usage(ROOT).free
        OUT.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
