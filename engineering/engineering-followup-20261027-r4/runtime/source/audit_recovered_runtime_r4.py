"""Independent stdlib-only, read-only review of one recovered R4 runtime snapshot.

No candidate package is imported and no historical scientific/control job is run.
This reviewer does not import the builder, recovery worker, validator or launcher.
"""
import argparse
import ast
import base64
import csv
import datetime as dt
from email.parser import Parser
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import time
import tomllib
import traceback
import zipfile


def identity_stream(stream):
    digest = hashlib.sha256()
    size = 0
    for block in iter(lambda: stream.read(1048576), b''):
        digest.update(block)
        size += len(block)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def identity(path):
    with Path(path).open('rb') as stream:
        return identity_stream(stream)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    original = args.original.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    report = {
        'schema': 'razr-r4-independent-recovered-runtime-readback-v1',
        'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'reviewer': '/root/r4_real_sources',
        'independent_of_runtime_recovery_builder_validator_and_launcher_author': True,
        'source_identity': identity(__file__),
        'inputs': [], 'checks': [], 'issues': [], 'completed': False,
        'new_network_requests': 0, 'package_installs': 0,
        'new_candidate_imports': 0, 'CAD_jobs': 0, 'numerical_solves': 0,
        'original_V2_control_reruns': 0, 'frozen_sources_modified': False,
        'historical_execution_requalified': False,
        'compiled_kernel_formal_binding_verified': False,
        'OS_enforced_immutability_claimed': False, 'physical_qualification': False,
        'scope': 'Fresh full-byte candidate/selected-wheel readback, independent record and provenance reconstruction. Recorded import observations are reassessed; no new native import experiment is claimed.'}
    details = {'payloads': [], 'records': [], 'wheel_members': [],
               'module_origins': [], 'namespace_locations': []}
    initial = {}

    def bind(path, expected=None):
        path = Path(path)
        actual = identity(path)
        if expected is not None:
            require(actual == {k: expected[k] for k in ('bytes', 'sha256')}, 'Input identity: ' + str(path))
        key = str(path)
        if key not in initial:
            initial[key] = actual
            report['inputs'].append({'path': key, **actual})
        return path

    def read(path, expected=None):
        return json.loads(bind(path, expected).read_text())

    def passed(name, **facts):
        report['checks'].append({'name': name, 'passed': True, **facts})
        print(json.dumps({'review_phase': name, **facts}), flush=True)

    try:
        contract_path = runtime / 'R4_PROJECTION_CONTRACT_V3.json'
        contract = read(contract_path)
        plan = read(contract['plan']['path'], contract['plan'])
        qualification = read(runtime / 'validation-worker-attempt3/R3_PROJECTION_VALIDATION_EXECUTED.json',
                             {'bytes': 4485186, 'sha256': 'ca812a633d5a2f813e17a3efa4e17129d65eb9bb047e5596aa1ec3c63ee4beca'})
        build = read(runtime / 'build-worker-attempt3/R3_PROJECTION_BUILD_EXECUTED.json', qualification['build_result_identity'])
        recovery = read(contract['actual_R4_payload_recovery']['path'], contract['actual_R4_payload_recovery'])
        recovery_contract = read(runtime / 'R4_RUNTIME_RECOVERY_CONTRACT_V2.json', recovery['contract_identity'])
        old = read(plan['frozen_R3_plan_identity']['path'], plan['frozen_R3_plan_identity'])
        old_attempt = read(plan['attempt1_result']['path'], plan['attempt1_result'])
        old_contract = read(contract['frozen_R3_projection_contract']['path'], contract['frozen_R3_projection_contract'])
        old_payload_contract = read(plan['attempt1_contract']['path'], plan['attempt1_contract'])
        require(qualification['completed'] and qualification['current43_payload_and_namespace_qualified'] and not qualification['issues'], 'Final qualification not successful')
        require(qualification['contract_identity'] == identity(contract_path) == build['contract_identity'], 'Qualification/build/contract binding')
        require(build['completed'] and not build['issues'] and recovery['completed'] and not recovery['issues'], 'Build or recovery failure')
        for role in ('builder', 'entry', 'validator'):
            bind(contract[role + '_source'], contract[role + '_identity'])
            require(contract[role + '_identity'] == old_contract[role + '_identity'], 'Original ' + role + ' changed')
        require(qualification['source_identity'] == contract['validator_identity'], 'Validator observation identity')
        require(build['source_identity'] == contract['builder_identity'], 'Builder observation identity')
        bind(runtime / 'recover_runtime_payloads_r4_v2.py', recovery['source_identity'])
        require(recovery_contract['worker_identity'] == recovery['source_identity'], 'Recovery worker binding')
        require(contract['resource_limits'] == recovery_contract['resource_limits'] == old_contract['resource_limits'] == old_payload_contract['resource_limits'], 'Original six hard limits changed')
        root = Path(plan['candidate_root'])
        site = root / 'lib/python3.12/site-packages'
        require(root == runtime / 'candidate-v4' and root.is_dir() and not root.is_symlink(), 'Candidate root binding')
        require(site.is_dir() and not site.is_symlink(), 'Candidate site is not owned real directory')
        require(plan['original_43_version_map'] == old['original_43_version_map'] and len(old['original_43_version_map']) == 43, 'Original version map changed')
        require(plan['new_RECORD_payload_members_by_distribution'] == old['new_RECORD_payload_members_by_distribution'], 'Original RECORD member mapping changed')
        require(plan['python_binary_identity'] == old['python_binary_identity'] and identity(plan['python_binary_resolved']) == plan['python_binary_identity'], 'Interpreter identity')
        bind(plan['python_binary_resolved'], plan['python_binary_identity'])
        require(plan['isolated_standard_library_search_paths'] == old['isolated_standard_library_search_paths'], 'Isolated stdlib baseline changed')
        passed('input_identity_bindings_and_unchanged_original_contract')

        old_map = {row['relative']: row for row in old['payload_files']}
        current_map = {row['relative']: row for row in plan['payload_files']}
        require(len(old_map) == len(old['payload_files']) == len(current_map) == len(plan['payload_files']) == 8112, 'Payload duplicates or count')
        require(set(current_map) == set(old_map), 'Original payload path set changed')
        before_record_map = {r['relative']: r for r in qualification['payload_observations']}
        after_record_map = {r['relative']: r for r in qualification['post_import_payload_identities']}
        require(len(before_record_map) == len(after_record_map) == 8112, 'Qualification full before/after maps')
        for relative, row in sorted(current_map.items()):
            prior = old_map[relative]
            for key in ('relative', 'identity', 'owner_names', 'provenance'):
                require(row[key] == prior[key], 'Original payload fact changed: ' + relative + ':' + key)
            require(row['historical_R3_source'] == prior['source'], 'Historical source binding: ' + relative)
            alias = root / relative
            target = os.readlink(alias) if alias.is_symlink() else None
            require(target == row['source'], 'Actual alias target: ' + relative)
            actual = identity(alias)
            require(actual == prior['identity'] == before_record_map[relative]['actual'] == after_record_map[relative]['identity'], 'Full alias bytes: ' + relative)
            require(before_record_map[relative]['equal'] and after_record_map[relative]['unchanged'], 'Qualification payload flags')
            details['payloads'].append({'relative': relative, 'target': target, 'historical_R3_target': prior['source'], 'actual': actual, 'original_equal': True, 'actual_target_bound': True})
        passed('full_8112_alias_SHA_size_target_readback', count=len(details['payloads']), bytes=sum(x['actual']['bytes'] for x in details['payloads']))

        qualified_records = {r['relative']: r for r in qualification['record_observations']}
        build_records = {r['relative']: r for r in build['generated_RECORDs']}
        require(len(qualified_records) == len(build_records) == 43, 'RECORD counts')
        versions = {}
        for distribution in plan['distributions']:
            name = distribution['name']; relative = distribution['dist_info_relative'] + '/RECORD'
            record = root / relative
            actual = identity(record)
            require(record.is_file() and not record.is_symlink(), 'RECORD not own regular file')
            require(actual == qualified_records[relative]['generated_record_identity'] == build_records[relative]['identity'], 'RECORD identity binding')
            historical_record = original / 'new-candidate/generated-manifests' / relative
            require(actual == identity(historical_record), 'Generated RECORD differs from original R3 generated RECORD')
            bind(historical_record, actual)
            members = plan['new_RECORD_payload_members_by_distribution'][name]
            require(len(members) == len(set(members)), 'Expected RECORD duplicate')
            seen = set()
            for record_row in csv.reader(io.StringIO(record.read_text())):
                require(len(record_row) == 3, 'RECORD column count')
                member, digest, size = record_row
                target = Path(os.path.abspath(site / member))
                require(target.is_relative_to(root), 'RECORD escape')
                member_relative = str(target.relative_to(root))
                require(member_relative not in seen, 'RECORD duplicate')
                seen.add(member_relative)
                if member_relative == relative:
                    require(digest == size == '', 'RECORD self hash/size')
                else:
                    require(member_relative in members, 'RECORD unplanned member')
                    value = old_map[member_relative]['identity']
                    expected_digest = 'sha256=' + base64.urlsafe_b64encode(bytes.fromhex(value['sha256'])).rstrip(b'=').decode()
                    require(digest == expected_digest and size == str(value['bytes']), 'RECORD row identity')
            require(seen == set(members) | {relative}, 'RECORD complete exact set')
            metadata = Parser().parsestr((root / distribution['dist_info_relative'] / 'METADATA').read_text())
            metadata_name = metadata['Name'].lower().replace('_', '-')
            require(metadata_name == name and metadata['Version'] == plan['original_43_version_map'][name], 'METADATA version')
            versions[name] = metadata['Version']
            details['records'].append({'name': name, 'relative': relative, 'actual': actual, 'original_R3_generated_RECORD_equal': True, 'rows': len(seen), 'exact_member_SHA_size_rows': True})
        require(versions == old['original_43_version_map'], 'Exact43 current metadata')
        require({x.name for x in site.glob('*.dist-info')} == {Path(x['dist_info_relative']).name for x in plan['distributions']}, 'Extra or missing dist-info directory')
        all_nodes = list(root.rglob('*'))
        observed_files = {str(x.relative_to(root)) for x in all_nodes if x.is_file() or x.is_symlink()}
        require(observed_files == set(current_map) | set(qualified_records), 'Candidate file set')
        require(not any(x.suffix == '.pyc' for x in all_nodes), 'Candidate pyc')
        passed('43_RECORDs_rows_versions_and_exact8155_file_set', RECORD_count=43, files=len(observed_files), versions=len(versions))

        forbidden = {x['path'] for x in old_attempt['scope_inventory']['issues']}
        require(len(forbidden) == len(old_attempt['scope_inventory']['issues']) == 117, 'Old117 scope changed')
        require(old_attempt['current_43_distribution_payload_identity_verified'] is False, 'Original rejected aggregate changed')
        require(not forbidden.intersection(x['source'] for x in current_map.values()), 'Old117 target admitted')
        replacements = plan['original117_equal_byte_sources_replaced']
        require(len(replacements) == contract['original117_source_replacement_count'] == 53, '53 replacements count')
        for item in replacements:
            require(item['previous'] in forbidden and item['source'] == current_map[item['relative']]['source'] and item['identity'] == old_map[item['relative']]['identity'], 'Replacement not accounted')
        passed('old117_exact_target_exclusion_and_53_equal_byte_rebindings', forbidden_count=117, rebound_count=53)

        reused = read(recovery_contract['frozen_wheel_sources'][0]['path'], recovery_contract['frozen_wheel_sources'][0])
        installed = read(recovery_contract['frozen_wheel_sources'][1]['path'], recovery_contract['frozen_wheel_sources'][1])
        lock_path = original / 'original-inputs/uv.lock'
        bind(lock_path, reused['original_universal_lock'])
        lock = tomllib.loads(lock_path.read_text())
        lock_packages = {x['name']: x for x in lock['package']}
        original_wheels = {}
        for row in reused['packages']:
            original_wheels[row['name']] = {'name': row['name'], 'version': row['version'], 'filename': row['selected_locked_wheel']['filename'], 'wheel': row['selected_locked_wheel']['wheel']}
        for row in installed['packages']:
            require(row['name'] not in original_wheels, 'Original wheel duplicate owner')
            original_wheels[row['name']] = {k: row[k] for k in ('name', 'version', 'filename', 'wheel')}
        current_wheels = {x['name']: x for x in recovery_contract['frozen_wheels']}
        require(len(current_wheels) == len(recovery_contract['frozen_wheels']) == len(original_wheels) == 43 and current_wheels == original_wheels, 'Original43 wheel contracts changed')
        for name, wheel in current_wheels.items():
            require(wheel['version'] == old['original_43_version_map'][name] == lock_packages[name]['version'], 'Original lock version mismatch')
            require(wheel['wheel'] in lock_packages[name]['wheels'], 'Exact original wheel missing from uv.lock')
        observations = recovery['wheel_observations']
        require(len(observations) == len(recovery['required_wheel_names']) == 22, 'Actual22 wheel count')
        wheel_rows = []
        wheel_member_identities = {}
        for observed in observations:
            name = observed['name']; frozen = current_wheels[name]
            require(observed['locked'] == frozen['wheel'] and observed['filename'] == frozen['filename'] and observed['version'] == frozen['version'] and observed['completed'] and observed['http_status'] == 200, 'Wheel receipt chain')
            wheel_path = Path(recovery_contract['new_wheel_root']) / frozen['filename']
            actual = identity(wheel_path)
            expected = {'bytes': frozen['wheel']['size'], 'sha256': frozen['wheel']['hash'].removeprefix('sha256:')}
            require(actual == expected == observed['download_identity'], 'Full compressed wheel identity')
            selected = {r['relative']: r for r in observed['payload_members']}
            expected_members = {r['relative'] for r in old['payload_files'] if name in r['owner_names']}
            require(len(selected) == len(observed['payload_members']) and set(selected) == expected_members, 'Wheel full selected owner set')
            with zipfile.ZipFile(wheel_path) as archive:
                infos = archive.infolist(); names = [info.filename for info in infos]
                require(len(names) == len(set(names)), 'Duplicate compressed members')
                for info in infos:
                    member = PurePosixPath(info.filename)
                    require(not member.is_absolute() and '..' not in member.parts and not stat.S_ISLNK(info.external_attr >> 16), 'Unsafe compressed member')
                for relative, selected_row in sorted(selected.items()):
                    prefix = 'lib/python3.12/site-packages/'
                    short = relative.removeprefix(prefix)
                    if relative.startswith(prefix):
                        matches = [short] if short in names else [n for n in names if any(marker in n and n.split(marker, 1)[1] == short for marker in ('.data/purelib/', '.data/platlib/'))]
                    else:
                        matches = [n for n in names if '.data/data/' in n and n.split('.data/data/', 1)[1] == relative]
                    require(matches == [selected_row['wheel_member']], 'Selected member layout mapping')
                    with archive.open(selected_row['wheel_member']) as member_stream:
                        member_actual = identity_stream(member_stream)
                    extracted = Path(recovery_contract['new_payload_root']) / name / relative
                    extracted_actual = identity(extracted)
                    require(not extracted.is_symlink() and extracted.is_file(), 'Extracted payload node')
                    require(member_actual == extracted_actual == selected_row['actual'] == old_map[relative]['identity'], 'Wheel member/extracted/original chain')
                    wheel_member_identities[(name, relative)] = member_actual
                    details['wheel_members'].append({'owner': name, 'relative': relative, 'wheel_member': selected_row['wheel_member'], 'compressed_member_actual': member_actual, 'extracted_actual': extracted_actual, 'equals_original_R3': True})
            wheel_rows.append({'name': name, 'path': str(wheel_path), 'actual': actual, 'exact_original_lock': True, 'selected_members_read': len(selected), 'all_selected_member_chains_equal': True})
        require({x['name'] for x in observations} == set(recovery['required_wheel_names']), 'Actual required owners')
        for relative, row in current_map.items():
            source = Path(row['source'])
            payload_root = Path(recovery_contract['new_payload_root'])
            if source.is_relative_to(payload_root):
                parts = source.relative_to(payload_root).parts
                require(len(parts) > 1 and '/'.join(parts[1:]) == relative and (parts[0], relative) in wheel_member_identities, 'Current extracted alias has no actual member chain')
        report['wheel_observations'] = wheel_rows
        passed('22_full_compressed_wheels_and_all6390_selected_member_chains', wheels=len(wheel_rows), compressed_bytes=sum(x['actual']['bytes'] for x in wheel_rows), selected_members=len(details['wheel_members']))

        stdlib = [Path(p) for p in plan['isolated_standard_library_search_paths']]
        owned = {Path(contract[k]).resolve() for k in ('validator_source', 'entry_source')}
        def classify(raw):
            path = Path(raw)
            normalized = Path(os.path.abspath(path))
            require(path == normalized, 'Non-normalized recorded module path')
            if path.is_relative_to(site): return 'candidate'
            if path.resolve() in owned: return 'owned_verification_source'
            if 'site-packages' in path.parts or 'dist-packages' in path.parts: return None
            if any(path.is_relative_to(base) for base in stdlib if base.is_dir()): return 'stdlib'
            return None
        for key, path_key, expected_count in [('module_origins', 'file', 833), ('namespace_locations', 'location', 163)]:
            require(len(qualification[key]) == expected_count, 'Recorded origin count')
            for row in qualification[key]:
                kind = classify(row[path_key]); path = Path(row[path_key])
                require(kind is not None and kind == row['scope'] and row['passed'], 'Recorded origin outside strict sources')
                require(path.is_file() if key == 'module_origins' else path.is_dir(), 'Recorded origin absent at review')
                if kind == 'candidate' and key == 'module_origins':
                    require(str(path.relative_to(root)) in current_map, 'Candidate module not in8112')
                details[key].append({**row, 'independently_reclassified_scope': kind, 'current_path_exists': True})
        require([x['name'] for x in qualification['imports']] == contract['actual_import_probes'] and all(x['passed'] for x in qualification['imports']), 'Actual import receipt names')
        require(qualification['old_only_trame_env_negative_import'] == {'rejected': True, 'exception_type': 'ModuleNotFoundError', 'missing_name': 'trame.env'}, 'Original-only negative import receipt')
        expected_search = [str(site), *plan['isolated_standard_library_search_paths']]
        require(qualification['entry_state']['actual_search_paths'] == qualification['actual_search_paths_after_imports'] == expected_search, 'Actual search paths')
        require(all(qualification['post_input_identity_checks'].values()), 'Qualification post input check')
        for key in ('post_import_REFERENCE_targets_unchanged', 'post_import_generated_RECORDs_unchanged', 'candidate_inventory_unchanged_after_imports', 'no_pyc_after_imports', 'all_payloads_unchanged_after_imports', 'search_paths_unchanged_after_imports'):
            require(qualification[key] is True, 'Qualification post condition:' + key)
        report['origin_review_scope'] = '833 file origins and163 namespace locations from the actual final validator receipt, independently reclassified and current existence checked. No second import experiment.'
        passed('833_recorded_module_origins_and163_namespace_locations_strict_scope', module_origins=833, namespace_locations=163)

        history_specs = [
            ('recovery-worker-attempt1/R4_RUNTIME_PAYLOAD_RECOVERY_EXECUTED.json', 'Unexpected payload layout', 'recovery-attempt1/controller.json'),
            ('build-worker-attempt1/R3_PROJECTION_BUILD_EXECUTED.json', 'reference outside frozen source prefix or not a regular original file', 'build-attempt1/controller.json'),
            ('validation-worker-attempt1/R3_PROJECTION_VALIDATION_EXECUTED.json', 'build not qualified for same contract', 'validation-attempt1/controller.json'),
            ('validation-worker-attempt2/R3_PROJECTION_VALIDATION_EXECUTED.json', 'reference points at one of original117 nonadmitted files', 'validation-attempt2/controller.json')]
        history = []
        for record_path, reason, controller_path in history_specs:
            item = read(runtime / record_path); controller = read(runtime / controller_path)
            require(item['completed'] is False and any(x['message'] == reason for x in item['issues']), 'Failure history lost')
            require(controller['exit_code'] == 2 and controller['completed'] is False, 'Failure exit lost')
            history.append({'record': record_path, 'identity': identity(runtime / record_path), 'exit_code': controller['exit_code'], 'reason': reason, 'retained': True})
        require(any(x['relative'] == 'share/man/man1/ttx.1' for x in plan['payload_files']), 'Original ttx.1 omitted')
        report['preserved_actual_failures'] = history
        controllers = []
        for name in ('recovery-attempt2', 'build-attempt3', 'validation-attempt3'):
            ctrl = read(runtime / name / 'controller.json')
            limit = contract['resource_limits']; samples = ctrl['samples']
            require(ctrl['completed'] and ctrl['exit_code'] == 0 and ctrl['resource_stop'] is None and ctrl['limits'] == limit, 'Final supervised phase not pass')
            require(ctrl['seconds'] < limit['wall_seconds'], 'Actual wall limit')
            require(samples[0]['disk_available_bytes'] >= limit['startup_disk_floor_bytes'], 'Actual startup disk')
            require(samples[0]['shared_unreclaimable_bytes'] + limit['startup_extra_shared_bytes'] <= limit['shared_limit_bytes'], 'Actual startup shared admission')
            require(all(x['disk_available_bytes'] >= limit['runtime_disk_floor_bytes'] and x['shared_unreclaimable_bytes'] <= limit['shared_limit_bytes'] and x.get('worker_RSS_bytes', 0) <= limit['worker_RSS_limit_bytes'] for x in samples), 'Actual sampled resource limit')
            controllers.append({'phase': name, 'controller_identity': identity(runtime / name / 'controller.json'), 'supervisor_seconds': ctrl['seconds'], 'samples': len(samples), 'six_original_limits_pass': True})
        report['successful_supervision'] = controllers
        passed('preserved_failures_and_original_six_resource_gates', preserved_failures=4, successful_phases=3)

        launcher_path = bind(runtime / 'run_qualified_script_r4.py', {'bytes': 7840, 'sha256': '1da31ba1c2eedee7c9a6c6c631a9aa66e0ac7ce92aca644a34ecc5e37dbc103b'})
        launcher_text = launcher_path.read_text()
        ast.parse(launcher_text)
        report['launcher_source_review'] = {
            'identity': identity(launcher_path), 'method': 'Independent manual source review; AST parses; no worker execution or synthetic test.',
            'preflight': ['qualification successful and contract/validator identity bound', 'plan full SHA/size bound', 'all aliases literal targets and full SHA/size observed', 'exact candidate files and43 RECORD hashes observed', 'entry source identity bound', 'frozen entry checks -I -S -B, interpreter SHA/size and stdlib-only startup paths'],
            'postflight': ['finally observes aliases and RECORDs even on worker error', 'requires8112 equal aliases and exact file set and43 RECORD hashes', 'contract/plan/entry and worker source identities unchanged', 'qualification and launcher identities unchanged', 'worker exit0 and no issues required', 'loaded installed-package paths outside candidate rejected'],
            'specific_fail_open_identity_defect_found': False,
            'limits': ['Only observed boundaries; not OS immutability or continuous non-mutation.', 'Postflight foreign-origin scan covers site-packages/dist-packages, not provenance of arbitrary worker-loaded project source.', 'Historical execution and compiled kernel formal correctness remain outside qualification.']}
        passed('qualified_launcher_source_review')
        for key in ('historical_execution_requalified', 'compiled_kernel_formal_binding_verified', 'physical_qualification'):
            require(contract[key] is False and qualification[key] is False, 'Scope promoted:' + key)
        require(all(identity(p) == value for p, value in initial.items()), 'Frozen review input changed during audit')
        require(identity(__file__) == report['source_identity'], 'Review source changed')
        passed('review_inputs_and_original_failure_scopes_unchanged')
        report['new_snapshot_readback_qualified'] = True
        report['completed'] = True
    except BaseException as exc:
        report['issues'].append({'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()})
        report['new_snapshot_readback_qualified'] = False
    finally:
        output_details = out / 'R4_RUNTIME_INDEPENDENT_FULL_READBACK.json.gz'
        with output_details.open('wb') as target:
            with gzip.GzipFile(filename='', mode='wb', fileobj=target, mtime=0) as compressed:
                compressed.write((json.dumps(details, ensure_ascii=False, separators=(',', ':')) + '\n').encode())
        report['full_observations'] = {'file': output_details.name, **identity(output_details)}
        report['elapsed_seconds'] = time.monotonic() - started
        report['finished_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
        report_path = out / 'R4_RUNTIME_INDEPENDENT_REVIEW.json'
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'report': str(report_path), 'completed': report['completed'], 'issues': report['issues'], 'elapsed_seconds': report['elapsed_seconds'], 'identity': identity(report_path)}), flush=True)
    return 0 if report['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
