"""Preregister and build a complete bounded native80 evidence archive.

No active full-factory directory or private recovery metadata is an input.
Two immutable original wheels are retained as runtime evidence, without
claiming that the full installed environment is durably stored in this ZIP.
"""
from pathlib import Path
import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import resource
import signal
import stat
import time
import traceback
import zipfile
import zlib

BASE = Path(__file__).resolve().parent.parent
NATIVE = BASE / 'r7-native'
AUDIT = BASE / 'r7-audit'
META = AUDIT / 'native80-archive'
PLAN = META / 'R7_NATIVE80_COMPLETE_ARCHIVE_INPUT_PLAN_V1.json'
TARGET = BASE / 'r7-deliverables/RAZR-R7-native80-runtime-and-original-evidence-20261028.zip'
MAX_INPUT = 256 * 2**20
MAX_ARCHIVE = 256 * 2**20
MAX_WALL = 120
MAX_ADDRESS_SPACE = 256 * 2**20
PRIVATE_PATTERNS = [re.compile(rb'libfile_[A-Za-z0-9]{16,}'),
                    re.compile(rb'github_pat_[A-Za-z0-9_]{40,}'),
                    re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}'),
                    re.compile(rb'sk-(?:proj-)?[A-Za-z0-9_-]{40,}')]


class ArchiveBudgetExceeded(BaseException):
    pass


def need(value, message):
    if not value:
        raise ValueError(message)


def identity(path):
    path = Path(path)
    need(stat.S_ISREG(path.lstat().st_mode), 'Regular non-symlink file required: ' + str(path))
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(2**20), b''):
            h.update(chunk)
    return {'bytes': path.stat().st_size, 'sha256': h.hexdigest()}


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    need(not path.exists(), 'Immutable new artifact required: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def full_members(root):
    result = []
    need(stat.S_ISDIR(root.lstat().st_mode), 'Actual input directory required')
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs:
            need(stat.S_ISDIR((Path(directory) / name).lstat().st_mode), 'No symlink/special directories allowed')
        for name in files:
            path = Path(directory) / name
            need(stat.S_ISREG(path.lstat().st_mode), 'No symlink/special inputs allowed')
            result.append(path)
    return sorted(result)


def scan_private_locator_or_credential(path):
    need('.private.' not in path.name and path.suffix != '.private', 'Private metadata excluded')
    if path.suffix in ('.whl', '.gz'):
        return  # Immutable public wheels; original tar.gz has separately verified full science members.
    tail = b''
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            data = tail + block
            need(not any(pattern.search(data) for pattern in PRIVATE_PATTERNS),
                 'Private locator or credential-shaped content found; inspect without publishing: ' + str(path))
            tail = data[-256:]


def plan():
    seal_path = NATIVE / 'native80-attempt1/core-reader-seal.json'
    seal = load(seal_path)
    need(seal['completed_scientific_stage'] and seal['within_registered_64MiB_budget'], 'Complete original core-reader seal required')
    definitions = [
        ('sealed_raw_case', 'raw_case_members', NATIVE / 'native80-attempt1', 'science/raw-case'),
        ('sealed_original_science', 'all_original_scientific_inputs', NATIVE / 'recovered-science-v1', 'science/original-scientific-inputs'),
        ('sealed_original_assets', 'all_original_published_assets', BASE / 'razr-current/engineering/engineering-followup-20261028-r5/cloud-native-v1', 'science/original-published-assets'),
        ('sealed_new_local', 'new_local_source_and_bound_setup_receipts', NATIVE, 'science/new-local-sources-and-records'),
    ]
    rows = []
    destinations = set()

    def add(group, source, destination, expected=None):
        source = Path(source)
        need(source.is_relative_to(BASE), 'Input outside actual workspace')
        need('full-near-attempt1' not in source.parts and 'full-far-attempt1' not in source.parts,
             'Active full factory is not part of this archive')
        need(destination not in destinations and not destination.startswith('/') and '..' not in Path(destination).parts,
             'Duplicate or unsafe ZIP member')
        actual = identity(source)
        need(expected is None or actual == expected, 'Sealed source identity differs: ' + str(source))
        scan_private_locator_or_credential(source)
        metadata = source.lstat()
        rows.append({'group': group, 'source': str(source.relative_to(BASE)), 'member': destination,
                     'identity': actual, 'source_mtime_ns': metadata.st_mtime_ns, 'source_mode': metadata.st_mode})
        destinations.add(destination)

    for group, key, root, prefix in definitions:
        for relative, expected in seal[key].items():
            add(group, root / relative, prefix + '/' + relative, expected)
    need(sum(row['identity']['bytes'] for row in rows) == seal['scientific_raw_bytes_including_current_inputs'] == 22619921,
         'Original four-map aggregate changed')
    for filename in ('R7_NATIVE80_ACTUAL_SCOPE_V1.json', 'R7_POSTQUALIFICATION_SCRATCH_REOBSERVATION_V1.json'):
        add('native80_scope_and_unresolved_runtime_receipts', NATIVE / filename, 'native80-closeout/' + filename)
    add('native80_final_seal', seal_path, 'native80-closeout/core-reader-seal.original.json')
    setup_names = ('setup-assess_only-v1', 'setup-assess_only-v2', 'setup-assess_only-v3', 'setup-install_only-v2', 'setup-install_only-v3')
    for name in setup_names:
        folder = NATIVE / name
        for source in full_members(folder):
            add('complete_closed_setup_directories', source, 'setup/' + name + '/' + str(source.relative_to(folder)))
    audit_folders = ('native-review-v1', 'native-setup-v2-review', 'native-setup-v3-review', 'native-stage-v4-review', 'uv-01010-primary-source')
    for name in audit_folders:
        folder = AUDIT / name
        for source in full_members(folder):
            add('independent_native_and_runtime_audit_originals', source, 'audit/' + name + '/' + str(source.relative_to(folder)))
    audit_files = ('review_native_setup_v1_special_files.py', 'review_native_setup_v2.py', 'review_native_setup_v2_review_v2.py',
                   'R7_NATIVE_SETUP_REVIEW_ATTEMPT1_SOCKET_BLOCK.json', 'review_native_stage_registrar_v4.py',
                   'review_core_reader_registration_r7_v1.py', 'read_actual_runtime_qualification_r7_v1.py',
                   'read_actual_runtime_qualification_r7_v2.py', 'read_native80_actual_r7_v1.py')
    for name in audit_files:
        add('independent_native_and_runtime_audit_originals', AUDIT / name, 'audit/' + name)
    s4_sources = load(NATIVE / 'R7_SETUP_INSTALL_ONLY_CONTRACT_V3.json')['expected_sources']
    need(len(s4_sources) == 973, 'All 973 tracked selected S4 sources required')
    for relative, expected in s4_sources.items():
        need('.venv' not in Path(relative).parts and relative != '.git', 'Only exact tracked S4 source bytes in this category')
        add('complete_selected_973_S4_sources', NATIVE / 'genuine-s4-worktree-v3' / relative, 'functional-source-S4/' + relative, expected)
    wheels = [NATIVE / 'qualification-wheel-scratch-v1/vtk.whl',
              NATIVE / 'pinned-uv-0.10.10-v3/uv-0.10.10-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl']
    for source in wheels:
        add('original_runtime_wheels', source, 'runtime/original-wheels/' + source.name)
    groups = {}
    for row in rows:
        item = groups.setdefault(row['group'], {'members': 0, 'bytes': 0})
        item['members'] += 1
        item['bytes'] += row['identity']['bytes']
    total = sum(row['identity']['bytes'] for row in rows)
    need(total < MAX_INPUT, 'Registered 256 MiB input ceiling insufficient; revise plan before build')
    output = {'schema': 'razr-r7-complete-native80-original-archive-input-plan-v1',
              'registered_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'archive_builder': {'source': str(Path(__file__).resolve().relative_to(BASE)), 'identity': identity(__file__)},
              'target': str(TARGET.relative_to(BASE)), 'input_member_count': len(rows), 'input_bytes': total,
              'groups': groups, 'inputs': rows, 'original_core_scientific_seal_bytes': 22619921,
              'registered_archive_wall_seconds': MAX_WALL, 'registered_address_space_bytes': MAX_ADDRESS_SPACE,
              'registered_input_bytes_upper': MAX_INPUT, 'registered_archive_bytes_upper': MAX_ARCHIVE,
              'minimum_ordinary_free_before_build_bytes': 512 * 2**20, 'hash_chunk_bytes': 2**20,
              'algorithm': 'Read exact frozen inputs; stream ZIP (wheels stored, other originals deflated); reopen every member for CRC and SHA; rehash every original after archive; no extraction.',
              'private_recovery_metadata_and_credentials_excluded': True,
              'active_near_far_case_data_included': False, 'full_installed_venv_durable_preservation_claimed': False,
              'new_scientific_execution': False, 'historical_and_current_failures_reclassified': False,
              'all_blockers_closed': False}
    save(PLAN, output)
    print(json.dumps({'plan': str(PLAN), 'identity': identity(PLAN), 'groups': groups, 'input_member_count': len(rows), 'input_bytes': total}))


def build():
    c = load(PLAN)
    need(identity(__file__) == c['archive_builder']['identity'], 'Preregistered archive builder differs')
    need(not TARGET.exists() and not TARGET.with_suffix(TARGET.suffix + '.partial').exists(), 'Fresh immutable archive required')
    disk = os.statvfs(BASE)
    need(disk.f_bavail * disk.f_frsize >= c['minimum_ordinary_free_before_build_bytes'], 'Archive disk capacity insufficient')
    resource.setrlimit(resource.RLIMIT_AS, (MAX_ADDRESS_SPACE, MAX_ADDRESS_SPACE))
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(ArchiveBudgetExceeded('Registered 120-second archive wall budget exceeded')))
    signal.alarm(MAX_WALL)
    partial = TARGET.with_suffix(TARGET.suffix + '.partial')
    actual = {'schema': 'razr-r7-complete-native80-original-archive-actual-v1', 'completed': False,
              'plan': {'path': str(PLAN.relative_to(BASE)), 'identity': identity(PLAN)},
              'builder_identity': identity(__file__), 'new_scientific_execution': False}
    try:
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        bindings = {}
        for row in c['inputs']:
            need(identity(BASE / row['source']) == row['identity'], 'Input changed since registration: ' + row['source'])
            bindings[row['member']] = row['identity']
        metadata = {
            'META/ARCHIVE_INPUT_PLAN.json': PLAN.read_bytes(),
            'META/ARCHIVE_BUILDER.py': Path(__file__).read_bytes(),
            'META/ARCHIVE_SCOPE.json': (json.dumps({
                'schema': 'razr-r7-native80-complete-original-archive-scope-v1',
                'complete_original_80_8_4_80_finite_native_results_preserved': True,
                'all_396_saved_producer_BREP_and_independent_reader_results_preserved': True,
                'original_four_map_scientific_seal_and_all_bytes_preserved': True,
                'complete_selected_973_tracked_S4_source_files_preserved': True,
                'complete_closed_setup_history_and_real_failures_preserved': True,
                'qualified_runtime_payload_readback_passed': True,
                'external_vtk_wheel_cleanup_history_current_state_discrepancy': 'unresolved; actual surviving original wheel included unchanged',
                'native_reader_area_binary64_inequalities': 80,
                'native_reader_maximum_area_difference_mm2': 2.842170943040401e-14,
                'independent_reader_is_same_kernel_separate_process': True,
                'full_installed_venv_preserved': False,
                'original_K_b_C_five_probe_numerical_qualification_claimed': False,
                'whole_continuous_native_trim_model_membership_verified': False,
                'full_continuous_G2': False, 'physical_qualification': False, 'all_blockers_closed': False,
            }, indent=2) + '\n').encode(),
        }
        for member, data in metadata.items():
            bindings[member] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        member_manifest = (json.dumps({'schema': 'razr-r7-native80-exact-complete-archive-member-manifest-v1',
                                      'members': bindings, 'self_identity_retained_in_external_completion_receipt': True}, indent=2) + '\n').encode()
        metadata['META/ARCHIVE_MEMBER_MANIFEST.json'] = member_manifest
        expected = {**bindings, 'META/ARCHIVE_MEMBER_MANIFEST.json': {'bytes': len(member_manifest), 'sha256': hashlib.sha256(member_manifest).hexdigest()}}
        with zipfile.ZipFile(partial, mode='x', allowZip64=True, compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for row in c['inputs']:
                source = BASE / row['source']
                archive.write(source, arcname=row['member'], compress_type=zipfile.ZIP_STORED if source.suffix == '.whl' else zipfile.ZIP_DEFLATED)
                need(partial.stat().st_size <= MAX_ARCHIVE, 'Archive byte ceiling exceeded')
            for member, data in metadata.items():
                archive.writestr(member, data, compress_type=zipfile.ZIP_DEFLATED)
        need(partial.stat().st_size <= MAX_ARCHIVE, 'Final ZIP byte ceiling exceeded')
        with zipfile.ZipFile(partial) as archive:
            infos = archive.infolist()
            need(len(infos) == len({i.filename for i in infos}) == len(expected), 'Exact unique ZIP member count differs')
            need({info.filename for info in infos} == set(expected), 'Complete ZIP member set differs')
            for info in infos:
                h = hashlib.sha256(); count = crc = 0
                with archive.open(info) as stream:
                    for chunk in iter(lambda: stream.read(2**20), b''):
                        h.update(chunk); crc = zlib.crc32(chunk, crc); count += len(chunk)
                need({'bytes': count, 'sha256': h.hexdigest()} == expected[info.filename], 'Archived original byte identity differs')
                need((crc & 0xffffffff) == info.CRC, 'Actual complete ZIP CRC differs')
        for row in c['inputs']:
            need(identity(BASE / row['source']) == row['identity'], 'Original changed during archive/verification: ' + row['source'])
        need(identity(PLAN) == actual['plan']['identity'] and identity(__file__) == c['archive_builder']['identity'], 'Plan/builder changed')
        need(time.monotonic() - started <= MAX_WALL, 'Whole archive exceeded registered wall budget')
        partial.rename(TARGET)
        actual.update(completed=True, archive={'path': str(TARGET.relative_to(BASE)), 'identity': identity(TARGET)},
                      input_groups=c['groups'], original_input_members=len(c['inputs']), original_input_bytes=c['input_bytes'],
                      exact_archive_members=len(expected), archived_uncompressed_bytes=sum(v['bytes'] for v in expected.values()),
                      complete_member_set_CRC_SHA256_verified=True, all_original_source_bytes_unchanged=True,
                      member_manifest_identity=expected['META/ARCHIVE_MEMBER_MANIFEST.json'],
                      scientific_seal_unchanged_and_within_original_64MiB=True,
                      original_runtime_wheels_and_actual_cleanup_discrepancy_retained=True,
                      active_full_factory_data_included=False, private_Library_or_credentials_data_included=False)
    except BaseException as exc:
        actual['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
        actual['partial_archive_retained'] = str(partial.relative_to(BASE)) if partial.exists() else None
    finally:
        signal.alarm(0)
        actual.update(seconds=time.monotonic() - started, peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
        save(META / 'R7_NATIVE80_COMPLETE_ARCHIVE_ACTUAL_V1.json', actual)
    print(json.dumps(actual))
    return 0 if actual['completed'] else 2


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('action', choices=('plan', 'build'))
    args = parser.parse_args()
    if args.action == 'plan':
        plan(); return 0
    return build()


if __name__ == '__main__':
    raise SystemExit(main())
