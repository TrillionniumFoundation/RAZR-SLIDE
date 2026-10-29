"""Bounded current two-path observation; no archive creation or original writes."""
from pathlib import Path
import ast
import datetime as dt
import hashlib
import json
import resource
import signal
import stat
import time
import traceback

BASE = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name('R7_FAR_ARCHIVE_TWO_PATHS_CURRENT_READBACK_V1.json')
TARGET = BASE / 'r7-deliverables/RAZR-R7-far-full-factory-and-independent-originals-20261028.zip'
PARTIAL = TARGET.with_suffix(TARGET.suffix + '.partial')
BUILDER = BASE / 'r7-audit/build_far_full_factory_archive_r7_v3.py'
ACTUAL = BASE / 'r7-audit/far-full-archive/R7_FAR_FULL_ORIGINAL_ARCHIVE_ACTUAL_V3.json'
PLAN = BASE / 'r7-audit/far-full-archive/R7_FAR_FULL_ORIGINAL_ARCHIVE_INPUT_PLAN_V3.json'
SAVED = BASE / 'r7-deliverables/R7_FAR_COMPLETE_PRESERVATION_V1.json'
LIMITS = {'wall_seconds': 30, 'address_space_bytes': 128 * 2**20}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stamp(path):
    s = path.lstat()
    return {'device': s.st_dev, 'inode': s.st_ino, 'mode': s.st_mode,
            'regular': stat.S_ISREG(s.st_mode), 'nlink': s.st_nlink,
            'bytes': s.st_size, 'allocated_blocks_512': s.st_blocks,
            'mtime_ns': s.st_mtime_ns, 'ctime_ns': s.st_ctime_ns,
            'atime_ns': s.st_atime_ns}


def observe(path):
    result = {'path': str(path.relative_to(BASE)), 'observed_utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    try:
        before = stamp(path)
    except FileNotFoundError:
        result['exists'] = False
        return result
    result.update(exists=True, lstat_before=before)
    require(before['regular'], 'Observation target is not a regular file')
    digest, count = hashlib.sha256(), 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            count += len(block)
            digest.update(block)
    after = stamp(path)
    stable_keys = ('device', 'inode', 'mode', 'nlink', 'bytes', 'mtime_ns', 'ctime_ns')
    stable = all(before[k] == after[k] for k in stable_keys) and count == after['bytes']
    result.update(lstat_after=after, identity={'bytes': count, 'sha256': digest.hexdigest()},
                  non_access_metadata_stable_while_read=stable)
    require(stable, 'Observation target changed while its bytes were read')
    return result


def identity(path):
    result = observe(path)
    require(result['exists'], 'Required historical record is absent')
    return result['identity']


def main():
    require(not OUT.exists(), 'Fresh immutable observation output required')
    start = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (LIMITS['address_space_bytes'], LIMITS['address_space_bytes']))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Registered 30-second read budget exceeded')))
    signal.alarm(LIMITS['wall_seconds'])
    report = {'schema': 'razr-r7-far-archive-current-two-path-readback-v1',
              'recorded_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'completed': False, 'limits': LIMITS, 'new_scientific_execution': False,
              'no_explicit_original_write_rename_deletion_or_archive_creation': True,
              'source_and_historical_records': {}, 'current_paths': {}}
    try:
        inputs = (Path(__file__).resolve(), BUILDER, ACTUAL, PLAN, SAVED)
        before = {str(p.relative_to(BASE)): identity(p) for p in inputs}
        report['source_and_historical_records'] = before
        actual, saved = json.loads(ACTUAL.read_text()), json.loads(SAVED.read_text())
        require(actual['completed'] and actual['complete_member_set_CRC_SHA256_verified'], 'Historical complete archive receipt is not complete')
        require(identity(BUILDER) == actual['builder_identity'] and identity(PLAN) == actual['plan_identity'], 'Historical source/plan identity differs')
        expected = actual['archive']['identity']
        require(saved['saved_file']['status'] == 'succeeded' and {k: saved[k] for k in ('bytes', 'sha256')} == expected,
                'Saved archive receipt differs from the completed archive')
        source = BUILDER.read_text()
        tree = ast.parse(source)
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and isinstance(n.func.value, ast.Name) and n.func.value.id == 'partial' and n.func.attr == 'rename'
                 and len(n.args) == 1 and isinstance(n.args[0], ast.Name) and n.args[0].id == 'TARGET']
        require(len(calls) == 1, 'Expected single original partial.rename(TARGET) call differs')
        line = calls[0].lineno
        lines = source.splitlines()
        report['original_source_semantics'] = {
            'single_partial_rename_target_call_line': line,
            'source_excerpt': [{'line': n + 1, 'text': lines[n]} for n in range(max(0, line - 5), min(len(lines), line + 16))],
            'initial_freshness_check': [n + 1 for n, text in enumerate(lines) if 'not TARGET.exists() and not partial.exists()' in text],
            'success_sequence': 'The builder verified ZIP members and original inputs, computed the partial-file hash, called partial.rename(TARGET), then updated completed=True. The completed actual receipt does not record an observed post-rename partial absence or source/target inode transition.',
            'failure_branch_partial_exists_check_is_not_success_branch_absence_evidence': True,
        }
        report['historical_archive_evidence'] = {
            'completed': actual['completed'], 'archive': actual['archive'],
            'exact_archive_members': actual['exact_archive_members'],
            'complete_member_set_CRC_SHA256_verified': actual['complete_member_set_CRC_SHA256_verified'],
            'all_original_source_bytes_unchanged': actual['all_original_source_bytes_unchanged'],
            'saved_library_file_id': saved['saved_file']['library_file_id'],
            'saved_status': saved['saved_file']['status'],
            'post_rename_partial_absence_event_recorded_in_original_actual': False,
            'historical_CRC_decompression_repeated_by_this_observation': False,
        }
        for label, path in (('final', TARGET), ('partial', PARTIAL)):
            report['current_paths'][label] = observe(path)
        a, b = report['current_paths']['final'], report['current_paths']['partial']
        both = a['exists'] and b['exists']
        report.update(both_paths_currently_observed=both,
                      both_current_hashes_match_historical_complete_and_saved_archive=bool(both and a['identity'] == b['identity'] == expected),
                      current_paths_have_distinct_device_inode_identity=bool(both and (a['lstat_after']['device'], a['lstat_after']['inode']) != (b['lstat_after']['device'], b['lstat_after']['inode'])),
                      prior_successful_partial_absence_proved=False,
                      deletion_then_reappearance_proved=False,
                      physical_reappearance_or_platform_cause_proved=False,
                      correspondence_between_successful_rename_source_path_and_later_two_paths_unresolved=True,
                      historical_scientific_or_complete_archive_results_reclassified=False,
                      interpretation='This is a dated observation of current path membership and byte identity. The original success receipt lacks a post-rename partial-absence observation; current two-path membership does not prove deletion followed by reappearance or identify a cause.')
        after = {str(p.relative_to(BASE)): identity(p) for p in inputs}
        require(before == after, 'Historical record or observation source bytes changed')
        report['source_and_historical_record_bytes_unchanged'] = True
        report['completed'] = True
    except BaseException as exc:
        report['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    finally:
        signal.alarm(0)
        report['seconds'] = time.monotonic() - start
        report['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        with OUT.open('x') as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write('\n')
    print(json.dumps({'observation': str(OUT.relative_to(BASE)), 'identity': identity(OUT), 'completed': report['completed'],
                      'seconds': report['seconds'], 'peak_RSS_bytes': report['peak_RSS_bytes']}))
    return 0 if report['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
