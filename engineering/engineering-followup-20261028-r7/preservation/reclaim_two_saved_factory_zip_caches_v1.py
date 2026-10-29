"""Retain complete saved near/far originals; remove only their verified local ZIP caches."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'r7-publication/R7_TWO_SAVED_FACTORY_ZIP_CACHE_RECLAIM_V1.json'


def identity(p):
    with p.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes': p.stat().st_size, 'sha256': digest}


def main():
    assert not OUT.exists()
    started = time.monotonic()
    independent = ROOT / 'r7-audit/storage-migration-followup-v1/R7_ARCHIVED_EXPANSION_MIGRATION_INDEPENDENT_READBACK_V1.json'
    assert identity(independent) == {'bytes': 3925588, 'sha256': 'abce98e87fe1ebeab625647180904a42542dcc19d71f4b80b9f91b7f14fe5398'}
    rows = []
    for name, expected_id in (
        ('R7_NEAR_COMPLETE_PRESERVATION_V1.json', 'libfile_03369f15bb2c819189c055031babf4ad'),
        ('R7_FAR_COMPLETE_PRESERVATION_V1.json', 'libfile_ffffa1050c0881919fc5608d9acfae2d'),
    ):
        receipt_path = ROOT / 'r7-deliverables' / name
        receipt = json.loads(receipt_path.read_text())
        saved = receipt['saved_file']
        path = Path(saved['local_path'])
        assert path.parent == ROOT / 'r7-deliverables' and path.suffix == '.zip'
        assert path.is_file() and not path.is_symlink()
        assert saved['status'] == 'succeeded' and saved['local_metadata_applied'] is True
        assert saved['library_file_id'] == expected_id
        expected = {k: receipt[k] for k in ('bytes', 'sha256')}
        assert identity(path) == expected
        assert os.getxattr(path, 'user.library-file-id').decode() == expected_id
        assert os.getxattr(path, 'user.library-file-version').decode() == str(saved['current_version_number'])
        rows.append({'path': str(path), **expected, 'library_file_id': expected_id,
                     'file_id': saved['file_id'], 'saved_version': saved['current_version_number'],
                     'save_receipt': {'path': str(receipt_path), **identity(receipt_path)},
                     'saved_identity_and_metadata_verified': True, 'local_cache_removed': False})
    record = {'schema': 'razr-r7-two-saved-factory-zip-cache-reclaim-v1',
              'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'independent_complete_original_readback': {'path': str(independent), **identity(independent)},
              'current_expanded_factory_caches_incomplete_as_already_recorded': True,
              'complete_originals_retrievable_by_saved_file_identity': True,
              'later_local_ZIP_read_requires_materializing_exact_saved_original': True,
              'ordinary_available_before': shutil.disk_usage(ROOT).free,
              'files': rows, 'completed': False, 'removed_bytes': 0,
              'nonprerequisite_factory_outputs_sources_runtime_and_Git_untouched': True,
              'previous_cleanup_correspondence_discrepancies_resolved': False,
              'capacity_change_cause_attributed': False,
              'scientific_failure_reclassified': False, 'all_blockers_closed': False}
    OUT.write_text(json.dumps(record, indent=2) + '\n')
    try:
        for row in rows:
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
