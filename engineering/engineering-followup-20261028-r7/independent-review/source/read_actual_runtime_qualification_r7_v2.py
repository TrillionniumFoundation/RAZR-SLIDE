"""Independent record/file readback with no scientific or installed-package import.

Budget established before reading: 256 MiB address space, 120 s CPU, 1 MiB
streaming hash chunks. No network, downloaded wheel, or CAD execution is done.
"""
from pathlib import Path, PurePosixPath
import base64
import collections
import csv
import datetime
import email.parser
import hashlib
import io
import json
import os
import resource
import stat
import time
import tomllib
import zipfile

resource.setrlimit(resource.RLIMIT_AS, (256 * 2**20, 256 * 2**20))
resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
START = time.monotonic()
BASE = Path(__file__).resolve().parent.parent
CASE = BASE / 'r7-native/native80-attempt1'
WORKER = CASE / 'qualify-owned/worker'
REPORT = WORKER / 'R5_FRESH_RUNTIME_QUALIFICATION.json'


def identity(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(2**20), b''):
            digest.update(chunk)
    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def normalized(value):
    return value.lower().replace('_', '-').replace('.', '-')


bound_paths = [REPORT, CASE / 'qualify-contract.json', CASE / 'qualify-command.json',
               CASE / 'qualify-command-actual.json', CASE / 'qualify-owned/controller.json',
               CASE / 'qualify-supervision-contract.json', CASE / 'qualify-seal.json']
before = {str(path): identity(path) for path in bound_paths}
q = load(REPORT)
contract = load(CASE / 'qualify-contract.json')
command = load(CASE / 'qualify-command.json')
actual = load(CASE / 'qualify-command-actual.json')
controller = load(CASE / 'qualify-owned/controller.json')
supervision = load(CASE / 'qualify-supervision-contract.json')
venv, site = Path(q['venv']), Path(q['site_packages'])
assert q['completed'] and not q['issues'] and actual['completed'] and controller['completed']
assert controller['resource_stop'] is None and controller['exit_code'] == actual['exit_code'] == 0
assert command['worker_command'] == command['command'][7:] == controller['command'] == supervision['exact_worker_command']
assert q['actual_qualification_argv'] == q['expected_qualification_argv'] == command['worker_command'][4:]
assert q['contract_identity'] == identity(CASE / 'qualify-contract.json')
assert q['qualifier_identity'] == identity(command['worker_command'][3]) == contract['qualifier_identity']
for binding in command['bound_inputs']:
    assert identity(binding['path']) == binding['identity'], binding['path']
for relative, expected in contract['locked_project_inputs'].items():
    assert identity(Path(q['functional_root']) / relative) == expected
assert identity(q['interpreter']['resolved_binary']) == q['interpreter']['binary_identity']
assert Path(q['interpreter']['executable']).resolve() == Path(q['interpreter']['resolved_binary'])

# Different traversal from qualifier: lstat every entry and reject special files.
observed = {}
for directory, dirs, files in os.walk(venv, topdown=True, followlinks=False):
    for name in dirs[:]:
        path = Path(directory) / name
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            observed[str(path.relative_to(venv))] = {'kind': 'symlink', 'target': os.readlink(path)}
            dirs.remove(name)
        else:
            assert stat.S_ISDIR(mode), str(path)
    for name in files:
        path = Path(directory) / name
        mode = path.lstat().st_mode
        key = str(path.relative_to(venv))
        if stat.S_ISLNK(mode):
            observed[key] = {'kind': 'symlink', 'target': os.readlink(path)}
        else:
            assert stat.S_ISREG(mode), str(path)
            observed[key] = {'kind': 'regular', **identity(path)}
assert observed == q['venv_files_before']
assert canonical(observed) == q['venv_inventory_before_sha256'] == q['venv_inventory_after_sha256']
assert q['all_new_runtime_files_unchanged'] and q['source_and_contract_unchanged'] and not q['changed_or_extra_venv_files']
assert observed['.lock'] == {'kind': 'regular', 'bytes': 0, 'sha256': hashlib.sha256(b'').hexdigest()}
assert q['verified_uv_root_lock']['allowed_relative_files'] == ['.lock']

lock = tomllib.loads((Path(q['functional_root']) / 'uv.lock').read_text())
packages = {normalized(p['name']): p for p in lock['package'] if 'registry' in p.get('source', {})}
assert len(packages) == 43 and {n: p['version'] for n, p in packages.items()} == q['actual_43_package_versions'] == contract['expected_43_package_versions']
assert len(q['wheel_observations']) == len(q['installed_RECORD_checks']) == 43
assert len({row['name'] for row in q['wheel_observations']}) == 43
surviving_wheels = []
for row in q['wheel_observations']:
    wheel = row['locked_wheel']
    assert wheel in packages[row['name']]['wheels'] and row['version'] == packages[row['name']]['version']
    assert row['actual_download_identity'] == {'bytes': wheel['size'], 'sha256': wheel['hash'].split(':')[1]}
    assert row['download_completed'] and row['all_wheel_members_in_original_RECORD'] and row['transient_download_removed_after_verification']
    assert row['wheel_payloads_verified_against_install'] == row['wheel_RECORD_entries_verified']
    surviving = Path(contract['wheel_scratch']) / (row['name'] + '.whl')
    if surviving.exists():
        mode = surviving.lstat()
        assert stat.S_ISREG(mode.st_mode)
        observed_wheel = identity(surviving)
        assert observed_wheel == row['actual_download_identity']
        surviving_wheels.append({'name': row['name'], 'path': str(surviving), 'identity': observed_wheel,
                                 'mtime_ns': mode.st_mtime_ns, 'ctime_ns': mode.st_ctime_ns,
                                 'outside_qualified_venv': not surviving.is_relative_to(venv),
                                 'outside_qualified_report_output': not surviving.is_relative_to(WORKER),
                                 'historical_report_claims_removed': row['transient_download_removed_after_verification']})

regular = {key for key, value in observed.items() if value['kind'] == 'regular'}
payload_keys = regular - set(q['generated_installer_files']) - set(q['actual_venv_scaffolds'])
payload = {key: {'identity': {k: observed[key][k] for k in ('bytes', 'sha256')}, 'owners': []} for key in payload_keys}
recorded_targets = set()
record_rows = []
for row in q['installed_RECORD_checks']:
    path = venv / row['relative']
    copy = WORKER / row['exact_copy']
    assert identity(path) == identity(copy) == row['identity']
    metadata = email.parser.Parser().parsestr((path.parent / 'METADATA').read_text(), headersonly=True)
    owner = normalized(metadata['Name'])
    assert owner in packages and metadata['Version'] == packages[owner]['version']
    wheel_row = next(w for w in q['wheel_observations'] if w['name'] == owner)
    tags = sorted(line[5:].strip() for line in (path.parent / 'WHEEL').read_text().splitlines() if line.startswith('Tag: '))
    assert tags == wheel_row['installed_wheel_tags']
    seen = set()
    hashed = unhashed = 0
    for relative, digest, size in csv.reader(io.StringIO(copy.read_text())):
        target = (site / relative).resolve()
        assert target.is_relative_to(venv) and not (site / relative).is_symlink()
        key = str(target.relative_to(venv))
        assert key in regular and key not in seen
        seen.add(key)
        recorded_targets.add(key)
        if target == path:
            assert digest == size == ''
            unhashed += 1
        else:
            expected = 'sha256=' + base64.urlsafe_b64encode(bytes.fromhex(observed[key]['sha256'])).rstrip(b'=').decode()
            assert digest == expected and int(size) == observed[key]['bytes']
            hashed += 1
        if key in payload:
            payload[key]['owners'].append(owner)
    assert hashed == row['hashed_entries'] and unhashed == row['unhashed_self_entries'] == 1
    record_rows.append({'owner': owner, 'identity': row['identity'], 'hashed_entries': hashed, 'unhashed_self_entries': unhashed})
for value in payload.values():
    value['owners'].sort()
assert payload_keys <= recorded_targets
assert len(payload) == q['locked_wheel_payload_file_count'] == 8112
assert sum(v['identity']['bytes'] for v in payload.values()) == q['locked_wheel_payload_bytes'] == 1226421880
assert canonical(payload) == q['locked_wheel_payload_inventory_sha256']
# Read the surviving actual immutable wheel, preserving its location and bytes.
# This does not convert the historic cleanup/current-state mismatch to a pass.
for wheel in surviving_wheels:
    verified = 0
    with zipfile.ZipFile(wheel['path']) as archive:
        members = [info for info in archive.infolist() if not info.is_dir()]
        names = [info.filename for info in members]
        assert len(names) == len(set(names))
        records = [name for name in names if name.endswith('.dist-info/RECORD')]
        assert len(records) == 1
        rows = list(csv.reader(io.StringIO(archive.read(records[0]).decode())))
        assert len(rows) == len(names) and {row[0] for row in rows} == set(names)
        for relative, digest, count in rows:
            if relative == records[0]:
                assert digest == count == ''
                continue
            parts = PurePosixPath(relative).parts
            assert parts and not relative.startswith('/') and '..' not in parts
            h = hashlib.sha256(); size = 0
            with archive.open(relative) as member:
                for chunk in iter(lambda: member.read(2**20), b''):
                    h.update(chunk); size += len(chunk)
            measured = {'bytes': size, 'sha256': h.hexdigest()}
            expected_digest = 'sha256=' + base64.urlsafe_b64encode(h.digest()).rstrip(b'=').decode()
            assert digest == expected_digest and int(count) == size
            if parts[0].endswith('.data'):
                assert len(parts) >= 3 and parts[1] in ('purelib', 'platlib', 'data')
                installed = (site if parts[1] in ('purelib', 'platlib') else venv).joinpath(*parts[2:])
            else:
                installed = site.joinpath(*parts)
            key = str(installed.relative_to(venv))
            assert payload[key]['identity'] == measured and wheel['name'] in payload[key]['owners']
            verified += 1
        wheel['original_zip_member_count'] = len(members)
        wheel['original_RECORD_self_entry_count'] = 1
        wheel['independently_stream_verified_original_and_installed_payload_count'] = verified
    assert identity(wheel['path']) == wheel['identity']
    assert verified == next(row['wheel_payloads_verified_against_install'] for row in q['wheel_observations'] if row['name'] == wheel['name'])

assert not q['unbound_files']
assert [row['name'] for row in q['imports']] == contract['actual_import_probes']
assert len(q['imports']) == 8 and q['namespace_and_real_import_probes_completed'] and q['fresh_wheels_and_installed_RECORDs_verified']
assert q['search_paths_before_imports'] == q['search_paths_after_imports']
assert all(row['within_new_site'] for row in q['top_level_resolution'])
assert {row['scope'] for row in q['module_origins']} <= {'fresh_verified_site', 'owned_qualifier', 'stdlib'}
assert {row['scope'] for row in q['namespace_locations']} <= {'fresh_verified_site', 'stdlib'}
for row in q['imports']:
    if row['file']:
        assert Path(row['file']).is_relative_to(site) and Path(row['file']).is_file()
assert q['legacy_only_trame_env_rejected'] and q['uv_version'] == 'uv 0.10.10'
assert q['new_runtime_from_actual_uv_locked_install']
for key in ('prior_R4_qualification_used_as_admission', 'historical_environment_identity_claimed', 'compiled_kernel_formal_error_bound_verified', 'physical_qualification', 'full_continuous_G2'):
    assert q[key] is False
assert identity(WORKER / 'pyvenv.cfg') == identity(venv / 'pyvenv.cfg')
output_bytes = sum(path.stat().st_size for path in WORKER.rglob('*') if path.is_file())
assert identity(REPORT)['bytes'] <= contract['maximum_report_bytes'] and output_bytes <= contract['maximum_output_bytes']
seal = load(CASE / 'qualify-seal.json')
assert seal['completed_scientific_stage'] and seal['within_registered_64MiB_budget']
for relative, expected in seal['raw_case_members'].items():
    assert identity(CASE / relative) == expected
assert all(identity(path) == expected for path, expected in before.items())

result = {
    'schema': 'razr-r7-actual-qualification-independent-complete-file-readback-v1',
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'readback_completed': True, 'runtime_payload_readback_pass': True,
    'review_pass_with_no_unresolved_discrepancies': not surviving_wheels,
    'reviewer_identity': identity(__file__), 'bound_record_identities_before_and_after': before,
    'review_resource_limits': {'address_space_bytes': 256 * 2**20, 'CPU_seconds': 120, 'hash_chunk_bytes': 2**20},
    'independent_complete_actual_venv_member_count': len(observed),
    'independent_regular_file_count': len(regular), 'independent_symlink_count': len(observed) - len(regular),
    'independent_regular_bytes_hashed': sum(v['bytes'] for v in observed.values() if v['kind'] == 'regular'),
    'independent_complete_inventory_sha256': canonical(observed),
    'independent_locked_payload_count': len(payload), 'independent_locked_payload_bytes': q['locked_wheel_payload_bytes'],
    'independent_locked_payload_inventory_sha256': canonical(payload),
    'actual_43_packages_match_frozen_contract_and_original_uv_lock': True,
    'all_43_installed_RECORD_copies_and_payload_hashes_independently_rechecked': True,
    'installed_RECORD_readback_rows': record_rows,
    'wheel_download_records_match_original_locked_hash_and_size': True,
    'original_report_records_all_transient_wheels_removed': True,
    'current_external_scratch_contains_surviving_original_wheels': surviving_wheels,
    'current_external_scratch_cleanup_absence_verified': not surviving_wheels,
    'historical_cleanup_to_current_state_correspondence_proved': not surviving_wheels,
    'cleanup_discrepancy_cause': 'unresolved; original report and actual surviving file preserved unchanged',
    'reviewer_downloaded_wheels': False, 'reviewer_reopened_only_surviving_original_wheels': [row['name'] for row in surviving_wheels],
    'eight_original_import_records_bound_and_inspected': True, 'reviewer_repeated_package_imports': False,
    'module_origin_count': len(q['module_origins']), 'namespace_location_count': len(q['namespace_locations']),
    'top_level_resolution_count': len(q['top_level_resolution']),
    'worker_seconds': q['seconds'], 'worker_peak_RSS_bytes': q['peak_RSS_bytes'],
    'original_controller_seconds': controller['seconds'], 'original_controller_sample_count': len(controller['samples']),
    'original_controller_resource_stop': controller['resource_stop'],
    'qualification_output_bytes': output_bytes, 'qualified_phase_seal_aggregate_bytes': seal['scientific_raw_bytes_including_current_inputs'],
    'runtime_root_lock_exact_empty_regular': True, 'full_continuous_G2': False, 'physical_qualification': False,
    'numerical_original_K_b_C_five_probe_qualification_claimed': False,
    'review_seconds': time.monotonic() - START,
}
output = BASE / 'r7-audit/native-stage-v4-review/R7_ACTUAL_RUNTIME_QUALIFICATION_INDEPENDENT_FULL_READBACK_V2.json'
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'path': str(output), 'identity': identity(output), 'review_seconds': result['review_seconds'], 'runtime_payload_readback_pass': True, 'unresolved_cleanup_file_count': len(surviving_wheels)}))
