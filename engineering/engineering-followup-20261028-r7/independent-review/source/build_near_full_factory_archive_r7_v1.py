"""Freeze the complete closed near-pose case and original engineering export.

This archival operation performs no CAD arithmetic.  The still-active far case
is excluded.  The separately completed native80 archive supplies the complete
selected S4 source and runtime evidence and is identified by its actual hash.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import resource
import signal
import stat
import time
import traceback
import zipfile
import zlib

BASE = Path(__file__).resolve().parent.parent
META = BASE / 'r7-audit/near-full-archive'
PLAN = META / 'R7_NEAR_FULL_ORIGINAL_ARCHIVE_INPUT_PLAN_V1.json'
ACTUAL = META / 'R7_NEAR_FULL_ORIGINAL_ARCHIVE_ACTUAL_V1.json'
SEAL = BASE / 'r7-native/R7_NEAR_COMPLETE_FINITE_POSE_FINAL_SEAL_V1.json'
TARGET = BASE / 'r7-deliverables/RAZR-R7-near-full-factory-and-independent-originals-20261028.zip'
MAX_INPUT = 2**30
MAX_OUTPUT = 256 * 2**20
MAX_AS = 256 * 2**20
MAX_WALL = 120
DISK_FLOOR = 512 * 2**20
CHUNK = 2**20
ROOTS = {
    'raw': BASE / 'r7-native/full-near-attempt1',
    'engineering': BASE / 'r7-native/full-near-attempt1-engineering',
}


class ArchiveBudgetExceeded(BaseException):
    pass


def need(value, message):
    if not value:
        raise ValueError(message)


def identity(path):
    path = Path(path)
    before = path.lstat()
    need(stat.S_ISREG(before.st_mode), 'Regular non-symlink input required: ' + str(path))
    count = 0
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b''):
            count += len(chunk)
            h.update(chunk)
    after = path.lstat()
    need((before.st_dev, before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns)
         == (after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns)
         and count == after.st_size, 'Input changed while hashing: ' + str(path))
    return {'bytes': count, 'sha256': h.hexdigest()}


def load(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    path = Path(path)
    need(not path.exists(), 'New immutable artifact required: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def complete_regular_set(root):
    need(stat.S_ISDIR(root.lstat().st_mode), 'Actual non-symlink root required')
    result = set()
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs:
            need(stat.S_ISDIR((Path(directory) / name).lstat().st_mode),
                 'Special or symlink directory cannot be silently omitted')
        for name in files:
            path = Path(directory) / name
            need(stat.S_ISREG(path.lstat().st_mode), 'Special or symlink file cannot be silently omitted')
            result.add(path.relative_to(root).as_posix())
    return result


def verify_complete_sets(c):
    for group, root in ROOTS.items():
        expected = {row['relative_to_case_root'] for row in c['inputs'] if row['group'] == group}
        need(complete_regular_set(root) == expected, 'Complete closed case member set changed: ' + group)


def free_bytes():
    state = os.statvfs(BASE)
    return state.f_bavail * state.f_frsize


def register():
    seal = load(SEAL)
    need(seal['pose'] == 'near' and seal['completed'] and seal['complete_full_pair_execution'],
         'Closed near original all-pair seal required')
    need(len(seal['raw_members']) == 4722 and len(seal['engineering_members']) == 4689,
         'Original complete near member counts changed')
    need(seal['raw_bytes'] == 441154916 and seal['engineering_bytes'] == 441035711,
         'Original complete near byte counts changed')
    rows = []
    names = set()

    def add(group, source, member, expected=None, relative=None):
        source = Path(source)
        need(source.is_relative_to(BASE), 'Input must stay in the actual workspace')
        need(not any(part.startswith('full-far-attempt') for part in source.parts), 'Active far case excluded')
        need('.private.' not in source.name and source.suffix != '.private', 'Current private metadata excluded')
        need(not member.startswith('/') and '..' not in Path(member).parts and member not in names,
             'Unique safe member required')
        actual = identity(source)
        need(expected is None or expected == actual, 'Original frozen byte identity changed: ' + str(source))
        row = {'group': group, 'source': source.relative_to(BASE).as_posix(), 'member': member,
               'identity': actual}
        if relative is not None:
            row['relative_to_case_root'] = relative
        rows.append(row)
        names.add(member)

    for group, root in ROOTS.items():
        bindings = seal[group + '_members']
        need(complete_regular_set(root) == set(bindings), 'Original seal is not the complete present case')
        for relative, expected in sorted(bindings.items()):
            add(group, root / relative, group + '/' + relative, expected, relative)
    add('final_seal', SEAL, 'closeout/' + SEAL.name)
    native_names = (
        'read_full_factory_inputs_r7_v1.py', 'R7_FULL_FACTORY_INPUTS_ACTUAL_READBACK_V1.json',
        'prepare_full_case_evidence_r7_v1.py',
        'register_full_factory_local_r7_v1.py', 'register_full_factory_local_r7_v2.py',
        'register_full_factory_local_r7_v3.py', 'register_full_case_closeout_r7_v1.py',
    )
    for name in native_names:
        add('full_factory_setup_source_and_input_evidence', BASE / 'r7-native' / name, 'local-source-and-records/' + name)
    audit_names = (
        'review_full_factory_local_r7_v1.py', 'review_full_factory_concrete_r7_v1.py',
        'read_full_factory_actual_r7_v1.py',
        'full-factory-review/R7_FULL_FACTORY_SOURCE_AND_COMPLETE_INPUTS_INDEPENDENT_REVIEW.json',
        'full-factory-review/R7_NEAR_FACTORY_CONCRETE_REGISTRATION_REVIEW.json',
        'full-factory-review/R7_NEAR_READBACK_CONCRETE_REGISTRATION_REVIEW.json',
        'full-factory-review/R7_NEAR_VERIFY_COMPLETE_CONCRETE_REGISTRATION_REVIEW.json',
        'full-factory-review/R7_NEAR_EXPORT_ENGINEERING_CONCRETE_REGISTRATION_REVIEW.json',
        'full-factory-review/R7_NEAR_ACTUAL_FULL_FACTORY_INDEPENDENT_EVIDENCE_READBACK.json',
    )
    for name in audit_names:
        add('independent_review_originals', BASE / 'r7-audit' / name, 'audit/' + name)
    previous_receipt_path = BASE / 'r7-audit/native80-archive/R7_NATIVE80_COMPLETE_ARCHIVE_ACTUAL_V3.json'
    previous_receipt = load(previous_receipt_path)
    need(previous_receipt['completed'] and previous_receipt['complete_member_set_CRC_SHA256_verified'],
         'Actual complete native80 source/runtime archive receipt required')
    previous_archive = BASE / previous_receipt['archive']['path']
    need(identity(previous_archive) == previous_receipt['archive']['identity'], 'Companion source/runtime archive changed')
    add('companion_source_runtime_archive_receipt', previous_receipt_path, 'companion/' + previous_receipt_path.name)
    groups = {}
    for row in rows:
        tally = groups.setdefault(row['group'], {'members': 0, 'bytes': 0})
        tally['members'] += 1
        tally['bytes'] += row['identity']['bytes']
    total = sum(row['identity']['bytes'] for row in rows)
    need(total <= MAX_INPUT, 'Registered 1 GiB original-input bound exceeded')
    ordinary = free_bytes()
    need(ordinary >= MAX_OUTPUT + DISK_FLOOR, 'Registered output upper bound plus remaining-disk floor not available')
    result = {
        'schema': 'razr-r7-complete-near-original-archive-input-plan-v1',
        'registered_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'builder': {'source': Path(__file__).resolve().relative_to(BASE).as_posix(), 'identity': identity(__file__)},
        'target': TARGET.relative_to(BASE).as_posix(), 'input_members': len(rows), 'input_bytes': total,
        'input_groups': groups, 'inputs': rows, 'final_seal_identity': identity(SEAL),
        'registered_limits': {'wall_seconds': MAX_WALL, 'address_space_bytes': MAX_AS,
                              'original_input_bytes': MAX_INPUT, 'archive_bytes': MAX_OUTPUT,
                              'remaining_ordinary_disk_floor_bytes': DISK_FLOOR,
                              'startup_ordinary_required_bytes': MAX_OUTPUT + DISK_FLOOR},
        'ordinary_free_at_registration_bytes': ordinary,
        'method': 'Stream every full original into ZIP; read every ZIP member for CRC and SHA; rehash every original and recheck both exact complete source sets; no extraction or CAD rerun.',
        'companion_complete_source_and_runtime_archive': previous_receipt['archive'],
        'companion_archive_is_referenced_not_duplicated': True,
        'original_factory_reader_verifier_exporter_sources_and_all_four_phase_raw_contracts_and_controls_included': True,
        'functional_source_commit': 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560',
        'candidate': 'panel_key_travel_stops_v1', 'finite_pose_clear': seal['finite_state_clear'],
        'remaining_unproved_domains': seal['remaining_unproved_domains'],
        'current_private_library_listing_recovery_transfer_authentication_or_unrelated_files_added': False,
        'far_case_data_included': False, 'new_scientific_execution': False,
        'historical_failures_reclassified': False, 'full_continuous_G2': False,
        'physical_qualification': False, 'all_blockers_closed': False,
    }
    save(PLAN, result)
    print(json.dumps({'plan': str(PLAN), 'identity': identity(PLAN), 'input_groups': groups,
                      'input_members': len(rows), 'input_bytes': total, 'ordinary_free_bytes': ordinary}))


class BoundedZipSink:
    """Check the output ceiling before every ZIP write, including directory data."""
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        need(self.stream.tell() + len(data) <= MAX_OUTPUT, 'Registered strict ZIP output ceiling exceeded')
        return self.stream.write(data)

    def seek(self, *args):
        return self.stream.seek(*args)

    def tell(self):
        return self.stream.tell()

    def flush(self):
        return self.stream.flush()


def build():
    resource.setrlimit(resource.RLIMIT_AS, (MAX_AS, MAX_AS))
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(ArchiveBudgetExceeded('Registered 120-second archive wall budget exceeded')))
    signal.alarm(MAX_WALL)
    partial = TARGET.with_suffix(TARGET.suffix + '.partial')
    actual = {'schema': 'razr-r7-complete-near-original-archive-actual-v1', 'completed': False,
              'plan_identity': identity(PLAN), 'builder_identity': identity(__file__),
              'new_scientific_execution': False}
    disk_samples = []

    def disk_check():
        observed = free_bytes()
        disk_samples.append(observed)
        need(observed >= DISK_FLOOR, 'Registered remaining ordinary-disk floor not met')

    try:
        c = load(PLAN)
        need(c['builder']['identity'] == actual['builder_identity'], 'Preregistered builder changed')
        need(c['target'] == TARGET.relative_to(BASE).as_posix(), 'Preregistered target changed')
        need(c['input_bytes'] <= MAX_INPUT and free_bytes() >= MAX_OUTPUT + DISK_FLOOR, 'Registered capacity unavailable')
        need(not TARGET.exists() and not partial.exists(), 'Fresh immutable archive required')
        verify_complete_sets(c)
        bindings = {}
        for row in c['inputs']:
            need(identity(BASE / row['source']) == row['identity'], 'Registered original changed: ' + row['source'])
            bindings[row['member']] = row['identity']
        metadata = {
            'META/ARCHIVE_INPUT_PLAN.json': PLAN.read_bytes(),
            'META/ARCHIVE_BUILDER.py': Path(__file__).read_bytes(),
            'META/ARCHIVE_SCOPE.json': (json.dumps({
                'schema': 'razr-r7-complete-near-original-archive-scope-v1',
                'all_4722_raw_and_4689_engineering_originals_preserved': True,
                'all_original_4334_prerequisite_members_preserved_in_each_case_layout': True,
                'all_154_bodies_and_11781_pair_records_and_independent_STEP_readback_preserved': True,
                'all_original_four_phase_scientific_and_resource_gates_retained': True,
                'original_verifier_and_exporter_completed_without_source_patch': True,
                'independent_reader_is_same_OCP_kernel_separate_process': True,
                'companion_complete_runtime_and_selected_973_S4_source_archive': c['companion_complete_source_and_runtime_archive'],
                'companion_archive_not_embedded': True,
                'finite_pose_clear': c['finite_pose_clear'],
                'remaining_unproved_domains': c['remaining_unproved_domains'],
                'external_qualification_vtk_cleanup_discrepancy': 'Unresolved; original surviving wheel and both observations retained in companion native80 archive.',
                'current_private_recovery_listings_signed_transfers_credentials_or_unrelated_files_added': False,
                'far_case_data_included': False, 'new_scientific_execution': False,
                'full_continuous_G2': False, 'physical_qualification': False,
                'manufacturing_go': False, 'all_blockers_closed': False,
            }, indent=2, allow_nan=False) + '\n').encode(),
        }
        for name, data in metadata.items():
            need(name not in bindings, 'Unique metadata member required')
            bindings[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        manifest = (json.dumps({'schema': 'razr-r7-complete-near-original-archive-member-manifest-v1',
                                'members': bindings, 'self_identity_in_external_completion_receipt': True},
                               indent=2, allow_nan=False) + '\n').encode()
        metadata['META/ARCHIVE_MEMBER_MANIFEST.json'] = manifest
        expected = {**bindings, 'META/ARCHIVE_MEMBER_MANIFEST.json': {
            'bytes': len(manifest), 'sha256': hashlib.sha256(manifest).hexdigest()}}
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        disk_check()
        with partial.open('xb') as raw:
            with zipfile.ZipFile(BoundedZipSink(raw), mode='w', allowZip64=True,
                                 compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for row in c['inputs']:
                    archive.write(BASE / row['source'], arcname=row['member'])
                    disk_check()
                for name, data in metadata.items():
                    archive.writestr(name, data)
                    disk_check()
        need(partial.stat().st_size <= MAX_OUTPUT, 'Final ZIP size exceeds registered output bound')
        with zipfile.ZipFile(partial) as archive:
            infos = archive.infolist()
            need(len(infos) == len({x.filename for x in infos}) == len(expected), 'Exact unique archive count changed')
            need({x.filename for x in infos} == set(expected), 'Complete archive member set changed')
            for info in infos:
                count = crc = 0
                digest = hashlib.sha256()
                with archive.open(info) as stream:
                    for chunk in iter(lambda: stream.read(CHUNK), b''):
                        count += len(chunk)
                        digest.update(chunk)
                        crc = zlib.crc32(chunk, crc)
                need({'bytes': count, 'sha256': digest.hexdigest()} == expected[info.filename], 'Complete archived byte identity differs')
                need((crc & 0xffffffff) == info.CRC, 'Complete archived CRC differs')
        disk_check()
        for row in c['inputs']:
            need(identity(BASE / row['source']) == row['identity'], 'Original changed during archive: ' + row['source'])
        verify_complete_sets(c)
        need(identity(PLAN) == actual['plan_identity'] and identity(__file__) == actual['builder_identity'], 'Plan or builder changed')
        archive_identity = identity(partial)
        disk_check()
        need(time.monotonic() - started <= MAX_WALL, 'Whole archive exceeded registered wall limit')
        partial.rename(TARGET)
        actual.update(completed=True, archive={'path': TARGET.relative_to(BASE).as_posix(), 'identity': archive_identity},
                      input_groups=c['input_groups'], original_input_members=c['input_members'],
                      original_input_bytes=c['input_bytes'], exact_archive_members=len(expected),
                      archived_uncompressed_bytes=sum(v['bytes'] for v in expected.values()),
                      member_manifest_identity=expected['META/ARCHIVE_MEMBER_MANIFEST.json'],
                      complete_member_set_CRC_SHA256_verified=True,
                      full_raw_and_engineering_source_sets_before_after_equal=True,
                      all_original_source_bytes_unchanged=True,
                      original_four_phase_scientific_and_resource_gates_preserved=True,
                      far_case_data_included=False,
                      companion_complete_runtime_and_selected_S4_source_archive=c['companion_complete_source_and_runtime_archive'],
                      finite_pose_clear=c['finite_pose_clear'], full_continuous_G2=False,
                      physical_qualification=False, all_blockers_closed=False)
    except BaseException as exc:
        actual['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
        actual['partial_archive_retained'] = partial.relative_to(BASE).as_posix() if partial.exists() else None
    finally:
        signal.alarm(0)
        actual.update(seconds=time.monotonic() - started,
                      peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                      ordinary_disk_samples=len(disk_samples),
                      minimum_observed_ordinary_free_bytes=min(disk_samples) if disk_samples else None)
        save(ACTUAL, actual)
    print(json.dumps(actual))
    return 0 if actual['completed'] else 2


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('action', choices=('register', 'build'))
    args = parser.parse_args()
    if args.action == 'register':
        register()
        return 0
    return build()


if __name__ == '__main__':
    raise SystemExit(main())
