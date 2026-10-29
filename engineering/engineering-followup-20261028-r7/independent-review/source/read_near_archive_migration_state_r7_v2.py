"""Read the archived near bytes and current expansion state without restoration.

The original full near audit remains a historical completed observation.  This
read does not repeat CAD, rewrite that audit, or claim the expansion is complete.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import resource
import signal
import stat
import time

BASE = Path(__file__).resolve().parent.parent
START = time.monotonic()
resource.setrlimit(resource.RLIMIT_AS, (128 * 2**20, 128 * 2**20))
signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('30-second migration-state read budget exceeded')))
signal.alarm(30)


def identity(path):
    assert stat.S_ISREG(path.lstat().st_mode)
    digest = hashlib.sha256()
    count = 0
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(2**20), b''):
            digest.update(data)
            count += len(data)
    assert count == path.stat().st_size
    return {'bytes': count, 'sha256': digest.hexdigest()}


def bind(path):
    return {'path': path.relative_to(BASE).as_posix(), 'identity': identity(path)}


def load(path):
    return json.loads(path.read_bytes())


receipt_path = BASE / 'r7-publication/R7_NEAR_ENGINEERING_ARCHIVE_MIGRATION_V1.json'
script_path = BASE / 'r7-publication/reclaim_archived_near_engineering_copy_v1.py'
seal_path = BASE / 'r7-native/R7_NEAR_COMPLETE_FINITE_POSE_FINAL_SEAL_V1.json'
archive_actual_path = BASE / 'r7-audit/near-full-archive/R7_NEAR_FULL_ORIGINAL_ARCHIVE_ACTUAL_V1.json'
receipt, seal, archive_actual = load(receipt_path), load(seal_path), load(archive_actual_path)
assert receipt['completed'] and not receipt['current_engineering_expansion_complete']
assert not receipt['historical_near_scientific_pass_reclassified']
assert receipt['historical_near_seal_identity'] == identity(seal_path)
rows = receipt['verified_members']
mapping = {row['relative_path']: row for row in rows}
assert len(mapping) == len(rows) == len(seal['engineering_members']) == 4689
assert set(mapping) == set(seal['engineering_members'])
for name, row in mapping.items():
    assert row['identity'] == seal['engineering_members'][name]
    assert row['archive_member'] == 'engineering/' + name
keep = {'ENGINEERING_MANIFEST.json', 'EXPORT_SCOPE.json'}
removed = set(receipt['removed_members'])
assert len(removed) == len(receipt['removed_members']) == receipt['removed_expanded_member_count'] == 4687
assert removed == set(mapping) - keep
assert sum(mapping[name]['identity']['bytes'] for name in removed) == receipt['reclaimed_expanded_bytes'] == 439084578
assert set(receipt['retained_expanded_members']) == keep
directory = BASE / 'r7-native/full-near-attempt1-engineering'
assert stat.S_ISDIR(directory.lstat().st_mode)
current = {}
for root, dirs, files in os.walk(directory, followlinks=False):
    for name in dirs:
        assert stat.S_ISDIR((Path(root) / name).lstat().st_mode)
    for name in files:
        path = Path(root) / name
        current[path.relative_to(directory).as_posix()] = identity(path)
assert keep <= set(current) <= set(seal['engineering_members'])
assert current == {name: seal['engineering_members'][name] for name in current}
assert sum(current[name]['bytes'] for name in keep) == receipt['retained_expanded_bytes'] == 1951133
archive = BASE / archive_actual['archive']['path']
archive_identity = identity(archive)
assert archive_identity == archive_actual['archive']['identity'] == receipt['archive_identity']
assert archive_actual['completed'] and archive_actual['complete_member_set_CRC_SHA256_verified']
assert archive_actual['exact_archive_members'] == 9433
result = {
    'schema': 'razr-r7-near-archive-migration-current-state-readback-v2',
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'completed': True, 'review_source': bind(Path(__file__).resolve()),
    'resource_limits': {'wall_seconds': 30, 'address_space_bytes': 128 * 2**20},
    'migration_receipt': bind(receipt_path), 'migration_source': bind(script_path),
    'historical_complete_near_seal': bind(seal_path), 'historical_complete_archive_readback': bind(archive_actual_path),
    'actual_local_archive': {'path': archive.relative_to(BASE).as_posix(), 'identity': archive_identity},
    'all_4689_migration_rows_match_original_complete_seal_and_archive_names': True,
    'all_4687_removed_expanded_member_names_and_439084578_bytes_match_receipt': True,
    'current_engineering_expansion_members': current,
    'current_engineering_expansion_complete': set(current) == set(seal['engineering_members']),
    'current_member_count': len(current),
    'current_bytes': sum(row['bytes'] for row in current.values()),
    'current_members_match_reported_two_member_migration_end_state': set(current) == keep,
    'historical_removed_but_current_observed_members': sorted(set(current) & removed),
    'historical_removed_but_current_observed_count': len(set(current) & removed),
    'all_current_observed_member_hashes_match_original_seal': True,
    'historical_migration_end_state_to_current_membership_correspondence_unresolved': set(current) != keep,
    'physical_reappearance_or_platform_cause_proved': False,
    'no_reclamation_or_restoration_performed_by_this_read': True,
    'prior_actual_failed_read': bind(BASE / 'r7-audit/full-factory-review/R7_NEAR_MIGRATION_CURRENT_READ_ATTEMPT1_ACTUAL_FAILURE.json'),
    'entire_archive_bytes_still_match_previously_completed_full_member_CRC_SHA_readback': True,
    'entire_archive_member_CRC_decompression_repeated_in_this_read': False,
    'historical_full_near_raw_and_engineering_audit_rerun_or_rewritten': False,
    'current_complete_raw_bytes_rehashed_in_this_storage_read': False,
    'historical_near_scientific_result_reclassified': False,
    'new_scientific_gate_or_CAD_execution': False,
    'restoration_supported_by_complete_verified_engineering_relative_members_in_retained_archive': True,
    'seconds': time.monotonic() - START,
    'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
}
assert result['seconds'] <= 30
signal.alarm(0)
out = BASE / 'r7-audit/full-factory-review/R7_NEAR_ENGINEERING_MIGRATION_CURRENT_STATE_READBACK_V2.json'
assert not out.exists()
with out.open('x') as stream:
    json.dump(result, stream, indent=2, allow_nan=False)
    stream.write('\n')
print(json.dumps({'readback': bind(out), 'current_engineering_expansion_complete': False}))
