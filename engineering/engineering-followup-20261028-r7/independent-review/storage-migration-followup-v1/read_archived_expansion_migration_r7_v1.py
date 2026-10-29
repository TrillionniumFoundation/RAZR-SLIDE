"""Bounded independent read of a later archived-expansion migration.

Do not delete, restore, rewrite a scientific report, or edit ledger V2.
Current path discrepancies are observations, not automatic old-pass reversals.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import resource
import shutil
import signal
import stat
import time
import traceback
import zipfile
import zlib

BASE = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PLAN = OUT / 'R7_ARCHIVED_EXPANSION_MIGRATION_INDEPENDENT_READ_PLAN_V1.json'
REPORT = OUT / 'R7_ARCHIVED_EXPANSION_MIGRATION_INDEPENDENT_READBACK_V1.json'
REFS = {
    'migration': 'r7-publication/R7_COMPLETE_FACTORY_ARCHIVE_EXPANSION_MIGRATION_V1.json',
    'migration_source': 'r7-publication/reclaim_complete_archived_factory_expansions_v1.py',
    'archive_capacity_failure': 'r7-deliverables/R7_METHOD_ARCHIVE_ATTEMPT1_ACTUAL_CAPACITY_FAILURE_V1.json',
    'near_seal': 'r7-native/R7_NEAR_COMPLETE_FINITE_POSE_FINAL_SEAL_V1.json',
    'far_seal': 'r7-native/R7_FAR_COMPLETE_FINITE_POSE_FINAL_SEAL_V1.json',
    'near_actual_audit': 'r7-audit/full-factory-review/R7_NEAR_ACTUAL_FULL_FACTORY_INDEPENDENT_EVIDENCE_READBACK.json',
    'far_actual_audit': 'r7-audit/full-factory-review/R7_FAR_ACTUAL_FULL_FACTORY_INDEPENDENT_EVIDENCE_READBACK.json',
    'near_saved': 'r7-deliverables/R7_NEAR_COMPLETE_PRESERVATION_V1.json',
    'far_saved': 'r7-deliverables/R7_FAR_COMPLETE_PRESERVATION_V1.json',
    'near_archive_actual': 'r7-audit/near-full-archive/R7_NEAR_FULL_ORIGINAL_ARCHIVE_ACTUAL_V1.json',
    'far_archive_actual': 'r7-audit/far-full-archive/R7_FAR_FULL_ORIGINAL_ARCHIVE_ACTUAL_V3.json',
    'original_gate_scope': 'r7-audit/full-factory-review/R7_ORIGINAL_CLOSEOUT_DISK_GATE_SCOPE_READBACK_V1.json',
    'native_scope': 'r7-native/R7_ACTUAL_NATIVE80_AND_TWO_FINITE_POSES_SCOPE_V1.json',
    'ledger_V2_JSON': 'r7-audit/blocker-ledger/R7_BLOCKER_CLOSURE_LEDGER_V2.json',
    'ledger_V2_Markdown': 'r7-audit/blocker-ledger/R7_BLOCKER_CLOSURE_LEDGER_V2.md',
    'old_near_discrepancy_observation': 'r7-audit/full-factory-review/R7_NEAR_ENGINEERING_MIGRATION_CURRENT_STATE_READBACK_V2.json',
}
LIMITS = {'wall_seconds': 120, 'address_space_bytes': 256 * 2**20,
          'maximum_stream_bytes': 4 * 2**30, 'maximum_current_census_entries': 30000,
          'maximum_output_bytes': 24 * 2**20}
KEEP = {'ENGINEERING_MANIFEST.json', 'EXPORT_SCOPE.json'}
stream_bytes = 0
census_entries = 0


class ReadBudgetExceeded(BaseException):
    pass


def need(value, message):
    if not value:
        raise ValueError(message)


def count_bytes(n):
    global stream_bytes
    stream_bytes += n
    need(stream_bytes <= LIMITS['maximum_stream_bytes'], 'Registered complete read byte budget exceeded')


def digest_stream(stream, track=True):
    h = hashlib.sha256()
    n = 0
    crc = 0
    while raw := stream.read(2**20):
        h.update(raw)
        n += len(raw)
        crc = zlib.crc32(raw, crc)
        if track:
            count_bytes(len(raw))
    return {'bytes': n, 'sha256': h.hexdigest()}, crc & 0xffffffff


def stat_record(path):
    s = path.lstat()
    return {key: getattr(s, key) for key in ('st_mode', 'st_dev', 'st_ino', 'st_nlink',
                                            'st_size', 'st_mtime_ns', 'st_ctime_ns')}


def identity(path, track=True):
    before = stat_record(path)
    need(stat.S_ISREG(before['st_mode']), 'Expected regular source/archive: ' + str(path))
    with path.open('rb') as stream:
        found, _ = digest_stream(stream, track)
    after = stat_record(path)
    need(before == after and found['bytes'] == after['st_size'], 'Source/archive changed during complete read: ' + str(path))
    return found


def write_new(path, value):
    raw = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    need(len(raw) <= LIMITS['maximum_output_bytes'], 'Registered observation output cap exceeded')
    need(not path.exists(), 'New immutable observation artifact required')
    with path.open('xb') as stream:
        stream.write(raw)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def load_ref(name):
    return json.loads((BASE / REFS[name]).read_bytes())


def prepare():
    refs = {name: {'path': str(BASE / relative), **identity(BASE / relative, track=False)} for name, relative in REFS.items()}
    m = load_ref('migration')
    need(len(m['groups']) == 5 and m['selected_before_count'] == 13357, 'Expected exact five migrated groups')
    need(len(m['complete_before_member_records']) == 13357, 'Original complete migration census differs')
    need(m['removed_local_duplicate_files'] == 13347 and m['removed_local_duplicate_bytes'] == 1252169747, 'Original migration count differs')
    protected = {}
    for pose in ('near', 'far'):
        seal = load_ref(pose + '_seal')
        members = {rel: value for rel, value in seal['raw_members'].items()
                   if not rel.startswith(('prerequisite-predock/', 'prerequisite-stow_tabs_3/'))}
        protected[pose] = {'members': len(members), 'bytes': sum(row['bytes'] for row in members.values())}
    plan = {'schema': 'razr-r7-later-archived-expansion-independent-read-plan-v1',
            'registered_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source': {'path': str(Path(__file__).resolve()), **identity(Path(__file__), track=False)},
            'limits': LIMITS, 'original_references': refs,
            'complete_archives': m['full_saved_archive_bindings'],
            'complete_selected_migration_group_count': 5, 'complete_selected_member_count': 13357,
            'selected_uncompressed_bytes': sum(row['bytes'] for row in m['complete_before_member_records']),
            'protected_raw_subsets_excluding_only_migrated_prerequisites': protected,
            'read_strategy': 'Hash both complete ZIPs before/after; verify success receipts and exact Library-id xattrs; stream each selected ZIP member through CRC/SHA and compare to original final seal and migration census; observe five current directory member/type/stat/hash states without requiring only two manifests; hash all protected non-prerequisite raw members twice.',
            'current_membership_difference_is_recorded_not_suppressed': True,
            'old_near_controversy_directory_not_scanned_or_modified': True,
            'no_delete_restore_CAD_solver_or_scientific_gate_change': True,
            'ledger_V2_remains_immutable': True,
            'disk_observation_at_registration': shutil.disk_usage(BASE)._asdict(),
            'this_read_budget_is_not_an_added_scientific_qualification_gate': True}
    actual = write_new(PLAN, plan)
    print(json.dumps({'plan': str(PLAN), **actual, 'protected_raw': protected,
                      'selected_uncompressed_bytes': plan['selected_uncompressed_bytes']}))


def census(directory):
    global census_entries
    result = {}
    try:
        root_stat = stat_record(directory)
    except FileNotFoundError:
        return {'root': {'missing': True}, 'entries': {}}
    if not stat.S_ISDIR(root_stat['st_mode']):
        return {'root': root_stat, 'entries': {}, 'root_is_real_directory': False}
    for root, dirs, files in os.walk(directory, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(root) / name
            rel = path.relative_to(directory).as_posix()
            census_entries += 1
            need(census_entries <= LIMITS['maximum_current_census_entries'], 'Registered observed directory entry cap exceeded')
            try:
                value = stat_record(path)
            except FileNotFoundError:
                result[rel] = {'missing_during_census': True}
                if name in dirs:
                    dirs.remove(name)
                continue
            result[rel] = value
            if name in dirs and not stat.S_ISDIR(value['st_mode']):
                dirs.remove(name)
    return {'root': root_stat, 'root_is_real_directory': True, 'entries': result}


def main_read():
    started = time.monotonic()
    started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    plan = json.loads(PLAN.read_bytes())
    need(plan['limits'] == LIMITS and identity(Path(__file__)) == {k: plan['source'][k] for k in ('bytes', 'sha256')}, 'Registered reader source or limits differ')
    refs = plan['original_references']
    for name, value in refs.items():
        need(identity(Path(value['path'])) == {k: value[k] for k in ('bytes', 'sha256')}, 'Bound original reference differs: ' + name)
    m = load_ref('migration')
    failure = load_ref('archive_capacity_failure')
    need(failure['required_ordinary_available_bytes'] == 234881024 and failure['exit_code'] == 1
         and not failure['archive_plan_created'] and not failure['archive_created'], 'Original admission failure scope differs')
    seals = {pose: load_ref(pose + '_seal') for pose in ('near', 'far')}
    disk_before = shutil.disk_usage(BASE)._asdict()
    archives = {}
    archive_records = {}
    for pose, binding in m['full_saved_archive_bindings'].items():
        path = Path(binding['path'])
        expected = {k: binding[k] for k in ('bytes', 'sha256')}
        saved = load_ref(pose + '_saved')
        actual_archive = load_ref(pose + '_archive_actual')
        got = identity(path)
        library_id = os.getxattr(path, 'user.library-file-id').decode()
        need(got == expected == {k: saved[k] for k in ('bytes', 'sha256')} == actual_archive['archive']['identity'], 'Full saved ZIP identity differs')
        need(saved['saved_file']['status'] == 'succeeded'
             and library_id == binding['library_file_id'] == saved['saved_file']['library_file_id']
             and saved['saved_file']['current_version_number'] == binding['version'] == 0, 'Saved ZIP persistence binding differs')
        archive = zipfile.ZipFile(path)
        entries = archive.infolist()
        need(len({row.filename for row in entries}) == len(entries), 'Duplicate full ZIP member names')
        need(len(entries) == actual_archive['exact_archive_members'], 'Full unchanged ZIP member census differs')
        archives[pose] = archive
        archive_records[pose] = {'path': str(path), 'complete_identity_before': got,
            'stat_at_read': stat_record(path), 'library_id_xattr': library_id,
            'saved_receipt_verified': refs[pose + '_saved'], 'full_original_archive_actual': refs[pose + '_archive_actual'],
            'complete_ZIP_members': len(entries), 'all_names_unique': True,
            'complete_identity_matches_original_all_member_CRC_SHA_pass_archive': True}
    all_original_rows = m['complete_before_member_records']
    need(len({row['path'] for row in all_original_rows}) == len(all_original_rows), 'Duplicate original migration paths')
    groups = []
    for group in m['groups']:
        directory = Path(group['directory'])
        pose, prefix = group['archive'], group['archive_prefix']
        archive = archives[pose]
        rows = {Path(row['path']).relative_to(directory).as_posix(): row for row in all_original_rows
                if Path(row['path']).is_relative_to(directory)}
        need(len(rows) == group['complete_file_count_before'], 'Complete original group member count differs')
        members = {info.filename: info for info in archive.infolist() if not info.is_dir() and info.filename.startswith(prefix)}
        need(set(members) == {prefix + rel for rel in rows}, 'Selected full ZIP group member set differs')
        recovered_records = {}
        for rel, row in sorted(rows.items()):
            need(row['archive'] == pose and row['archive_member'] == prefix + rel, 'Original migration archive mapping differs')
            seal_key = row['archive_member'].split('/', 1)[1]
            seal_map = seals[pose]['engineering_members' if prefix == 'engineering/' else 'raw_members']
            expected = {k: row[k] for k in ('bytes', 'sha256')}
            need(seal_map[seal_key] == expected, 'Migration member differs from original scientific final seal')
            info = members[prefix + rel]
            mode = (info.external_attr >> 16) & 0xffff
            need(stat.S_IFMT(mode) in (0, stat.S_IFREG), 'Selected original ZIP member is not a regular file')
            with archive.open(info) as stream:
                actual, crc = digest_stream(stream)
            need(actual == expected and actual['bytes'] == info.file_size and crc == info.CRC, 'Selected original ZIP member CRC/SHA differs')
            recovered_records[rel] = {**actual, 'CRC32': f'{crc:08x}'}
        before = census(directory)
        current = {}
        for rel, observed in before['entries'].items():
            if 'st_mode' not in observed or stat.S_ISDIR(observed['st_mode']):
                continue
            path = directory / rel
            expected_row = rows.get(rel)
            record = {'lstat_at_census': observed, 'in_original_selected_group': expected_row is not None,
                      'historically_removed_by_this_migration': bool(expected_row is not None and not expected_row['keep_as_local_manifest'])}
            if stat.S_ISREG(observed['st_mode']):
                try:
                    pre = stat_record(path)
                    with path.open('rb') as stream:
                        found, _ = digest_stream(stream)
                    post = stat_record(path)
                    record.update(identity=found, stat_before_full_hash=pre, stat_after_full_hash=post,
                                  regular_file_stable_during_hash=(pre == post and found['bytes'] == post['st_size']))
                    record['matches_original_selected_identity'] = bool(expected_row is not None and found == {k: expected_row[k] for k in ('bytes', 'sha256')})
                except FileNotFoundError as exc:
                    record['actual_read_exception'] = {'type': type(exc).__name__, 'message': str(exc)}
            else:
                record['nonregular_entry_not_opened_or_followed'] = True
            current[rel] = record
        after = census(directory)
        regular = {rel: row for rel, row in current.items() if 'identity' in row}
        removed_now_observed = sorted(rel for rel, row in current.items() if row['historically_removed_by_this_migration'])
        unexpected = sorted(rel for rel, row in current.items() if not row['in_original_selected_group'])
        mismatch = sorted(rel for rel, row in regular.items() if not row['matches_original_selected_identity'])
        expected_keep = {rel for rel, row in rows.items() if row['keep_as_local_manifest']}
        need(expected_keep == KEEP, 'Original retained-manifest definition differs')
        all_regular_match = all(row.get('matches_original_selected_identity', False) and row.get('regular_file_stable_during_hash', False) for row in current.values())
        current_exact_two = set(current) == KEEP and all_regular_match
        snapshot_stable = before == after
        groups.append({'directory': str(directory), 'archive': pose, 'archive_prefix': prefix,
            'original_group_files': len(rows), 'original_group_bytes': sum(row['bytes'] for row in rows.values()),
            'all_original_group_members_recovered_from_saved_ZIP_CRC_SHA_equal_final_seal': True,
            'complete_archived_member_readback_records': recovered_records,
            'historical_migration_end_state_files': group['files_at_receipt'],
            'current_census_before': before, 'current_file_observations': current, 'current_census_after': after,
            'current_regular_files_hashed': len(regular), 'current_regular_bytes_hashed': sum(row['identity']['bytes'] for row in regular.values()),
            'current_non_directory_entries': len(current), 'historically_removed_entries_observed_now': removed_now_observed,
            'new_unregistered_entries_observed_now': unexpected, 'current_hash_mismatches_to_original': mismatch,
            'expected_retained_manifests_missing_at_first_observation': sorted(KEEP - set(current)),
            'all_current_file_bytes_match_originals_and_were_stable_during_hash': all_regular_match,
            'current_member_and_stat_census_stable_during_read': snapshot_stable,
            'current_exactly_two_retained_manifests': current_exact_two,
            'current_complete_expansion': set(regular) == set(rows) and all_regular_match and snapshot_stable,
            'historical_end_state_to_current_membership_correspondence_unresolved': not (current_exact_two and snapshot_stable),
            'physical_reappearance_or_platform_cause_claimed': False})
    protected = {}
    for pose, seal in seals.items():
        root = BASE / f'r7-native/full-{pose}-attempt1'
        expected = {rel: row for rel, row in seal['raw_members'].items()
                    if not rel.startswith(('prerequisite-predock/', 'prerequisite-stow_tabs_3/'))}
        actual = {}
        for rel, value in expected.items():
            got = identity(root / rel)
            need(got == value, 'Protected original raw evidence differs: ' + str(root / rel))
            actual[rel] = got
        protected[pose] = {'root': str(root), 'complete_non_prerequisite_raw_member_count': len(expected),
            'bytes': sum(row['bytes'] for row in expected.values()), 'all_match_original_final_seal': True,
            'complete_checked_members': actual,
            'original_complete_full_pair_execution': seal['complete_full_pair_execution'],
            'original_finite_state_clear': seal['finite_state_clear'],
            'original_continuous_G2': seal['full_continuous_G2'],
            'current_complete_raw_expansion_claimed': False}
    for pose, data in protected.items():
        need(all(identity(Path(data['root']) / rel) == value for rel, value in data['complete_checked_members'].items()), 'Protected raw evidence changed during readback')
    for pose, record in archive_records.items():
        record['complete_identity_after'] = identity(Path(record['path']))
        need(record['complete_identity_after'] == record['complete_identity_before'], 'Full saved ZIP changed during readback')
    for archive in archives.values():
        archive.close()
    for name, value in refs.items():
        need(identity(Path(value['path'])) == {k: value[k] for k in ('bytes', 'sha256')}, 'Bound original changed during readback: ' + name)
    result = {'schema': 'razr-r7-later-archived-expansion-independent-readback-v1',
        'recorded_utc_start': started_utc, 'recorded_utc_end': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'completed_read': True, 'plan': {'path': str(PLAN), **identity(PLAN)},
        'source': plan['source'], 'limits': LIMITS, 'original_references': refs,
        'archive_admission_failure_preserved': {
            'source_evidence': refs['archive_capacity_failure'], 'actual_exit_code': failure['exit_code'],
            'required_ordinary_available_bytes': failure['required_ordinary_available_bytes'],
            'actual_available_at_assertion_not_logged': failure['ordinary_available_bytes_at_assertion_not_logged'],
            'subsequent_available_readback_bytes': failure['subsequent_readback_ordinary_available_bytes'],
            'that_attempt_created_plan': failure['archive_plan_created'], 'that_attempt_created_archive': failure['archive_created'],
            'historical_failure_reclassified': False},
        'complete_archives': archive_records, 'five_current_groups': groups,
        'all13357_selected_archived_members_complete_CRC_SHA_and_original_seal_verified': True,
        'all_1252169747_removed_duplicate_bytes_remain_recoverable_from_verified_saved_archives': True,
        'protected_non_prerequisite_raw_originals': protected,
        'all_static_bound_references_and_protected_raw_bytes_unchanged': True,
        'ledger_V2_original_bytes_unchanged': True,
        'new_current_group_correspondence_discrepancy_count': sum(group['historical_end_state_to_current_membership_correspondence_unresolved'] for group in groups),
        'current_exact_two_manifest_group_count': sum(group['current_exactly_two_retained_manifests'] for group in groups),
        'new_historically_removed_paths_observed': sum(len(group['historically_removed_entries_observed_now']) for group in groups),
        'old_near_controversy_directory_scanned_or_modified': False,
        'old_storage_causes_resolved': False, 'causal_or_platform_inference_made': False,
        'original_science_gates_or_historical_passes_modified': False,
        'new_CAD_solver_K_product_or_scientific_algorithm_execution': False,
        'paths_deleted_restored_or_rebuilt_by_this_reader': [],
        'disk_observations': {'plan': plan['disk_observation_at_registration'], 'before_read': disk_before,
                              'after_read': shutil.disk_usage(BASE)._asdict()},
        'stream_bytes_read': stream_bytes, 'filesystem_census_entries_observed': census_entries,
        'elapsed_seconds': time.monotonic() - started,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'all_blockers_closed': False}
    ident = write_new(REPORT, result)
    print(json.dumps({'report': str(REPORT), **ident,
        'current_exact_two_manifest_group_count': result['current_exact_two_manifest_group_count'],
        'new_correspondence_discrepancy_groups': result['new_current_group_correspondence_discrepancy_count'],
        'historically_removed_paths_observed': result['new_historically_removed_paths_observed'],
        'elapsed_seconds': result['elapsed_seconds'], 'peak_RSS_bytes': result['peak_RSS_bytes'],
        'stream_bytes_read': stream_bytes, 'disk_after': result['disk_observations']['after_read']}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    need(args.plan != args.execute, 'Choose one pure registration or actual read')
    resource.setrlimit(resource.RLIMIT_AS, (LIMITS['address_space_bytes'], LIMITS['address_space_bytes']))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(ReadBudgetExceeded('Registered 120-second read wall budget exceeded')))
    signal.alarm(LIMITS['wall_seconds'])
    try:
        if args.plan:
            prepare()
        else:
            main_read()
        return 0
    except BaseException as exc:
        failure = {'schema': 'razr-r7-later-archived-expansion-reader-actual-failure-v1',
            'stage': 'registration' if args.plan else 'actual_read', 'type': type(exc).__name__,
            'message': str(exc), 'traceback': traceback.format_exc(),
            'source': identity(Path(__file__), track=False), 'stream_bytes_read': stream_bytes,
            'original_source_or_evidence_modified': False, 'ledger_V2_modified': False,
            'scientific_result_reclassified': False}
        output = OUT / ('PLAN_ACTUAL_FAILURE_V1.json' if args.plan else 'ACTUAL_READ_FAILURE_V1.json')
        write_new(output, failure)
        print(json.dumps(failure))
        return 2
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    raise SystemExit(main())
