"""Register actual cloud paths and execute only explicitly recorded commands.

Original scientific operand bytes, algorithms and native resource supervisors
are unchanged. The new runtime is admitted only by the new wheel/RECORD and
namespace qualification from this same hosted job.
"""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import time


S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def identity(path):
    path = Path(path)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes': path.stat().st_size, 'sha256': digest}


def bind(path):
    return {'path': str(Path(path).resolve()), 'identity': identity(path)}


def save(path, value):
    path = Path(path)
    require(not path.exists(), 'Immutable new receipt path required: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    return path


def check_assets(assets):
    manifest = json.loads((assets / 'CLOUD_ASSET_MANIFEST.json').read_text())
    for relative, expected in manifest['files'].items():
        path = assets / relative
        require(path.is_file() and not path.is_symlink() and identity(path) == expected,
                'Published reviewed asset changed: ' + relative)
    lock_path = assets / 'SOURCE_LOCK.json'
    lock = json.loads(lock_path.read_text())
    request = json.loads((assets / 'RUN_REQUEST.json').read_text())
    require(lock['schema'] == 'razr-r5-native-cloud-source-lock-v1', 'Unknown source lock')
    require(request['schema'] == 'razr-r5-native-cloud-run-request-v1' and request['scope'] == 'native80-then-fresh-S4-near-far', 'Unknown native run request scope')
    require(request['source_lock_sha256'] == identity(lock_path)['sha256'], 'Run request does not name the exact reviewed source lock')
    require(os.environ.get('GITHUB_REPOSITORY') == lock['repository'] == 'TrillionniumFoundation/RAZR-SLIDE', 'Unexpected repository')
    require(os.environ.get('GITHUB_REF') == 'refs/heads/' + lock['branch'], 'Unexpected workflow ref')
    repository = assets
    for _ in Path(lock['repository_directory']).parts:
        repository = repository.parent
    require(assets == repository / lock['repository_directory'], 'Diagnostic checkout layout differs')
    require(subprocess.check_output(['git', '-C', str(repository), 'rev-parse', 'HEAD'], text=True).strip() == os.environ['GITHUB_SHA'], 'Diagnostic checkout is not the actual triggering commit')
    for relative, expected in lock['asset_files'].items():
        require(identity(assets / relative) == expected, 'Reviewed source lock asset differs: ' + relative)
    workflow = repository / lock['workflow_path']
    require(identity(workflow) == lock['workflow_identity'], 'Actual independent workflow file differs from reviewed source lock')
    return manifest


def check_qualification(case):
    path = case / 'runtime-qualification-owned/worker/R5_FRESH_RUNTIME_QUALIFICATION.json'
    controller = json.loads((case / 'runtime-qualification-owned/controller.json').read_text())
    report = json.loads(path.read_text())
    registered = json.loads((case / 'qualify-command.json').read_text())
    actual = json.loads((case / 'qualify-command-actual.json').read_text())
    require(controller['completed'] and controller['worker_started'] and controller['resource_stop'] is None,
            'New runtime qualifier did not complete beneath original resource gates')
    require(controller['command'] == registered['expected_owned_worker_command'] and
            controller['contract_sha256'] == registered['owned_execution_contract']['identity']['sha256'] and
            actual['owned_command_arguments_bound'], 'Actual owned qualifier command differs from its frozen registration')
    require(report['completed'] and report['fresh_wheels_and_installed_RECORDs_verified'] and report['all_new_runtime_files_unchanged'],
            'New runtime actual qualification did not pass')
    return path


def register(args):
    assets = args.assets.resolve()
    case = Path(os.environ['CASE_DIR']).resolve()
    host = Path(os.environ['HOST_ROOT']).resolve()
    functional = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    require(subprocess.check_output(['git', '-C', str(functional), 'rev-parse', 'HEAD'], text=True).strip() == S4, 'Actual functional checkout differs')
    require(subprocess.check_output(['git', '-C', str(functional), 'status', '--porcelain', '--untracked-files=all'], text=True) == '', 'Actual S4 checkout is dirty')
    asset_manifest = check_assets(assets)
    template = json.loads((assets / 'R5_CLOUD_NATIVE_SCIENCE_TEMPLATE.json').read_text())
    limits = template['original_resource_limits']
    science = host / 'native-science'
    source_manifest = json.loads((assets / 'SCIENTIFIC_INPUT_MANIFEST.json').read_text())
    supervisor = science / 'r4-native/recovered/native/source/supervise_native_r3.py'
    qualifier = assets / 'qualify_fresh_runtime_r5.py'
    entry = assets / 'run_fresh_runtime_script_r5.py'
    phase = args.phase
    bound_execution_inputs = [bind(p) for p in (qualifier, entry, Path(__file__), host / 'service-launch.py', host / 'host-cap.py', assets / 'CLOUD_ASSET_MANIFEST.json', assets / 'SOURCE_LOCK.json')]
    owned_execution_contract = None
    expected_owned_worker_command = None
    owned_controller = None
    command_path = case / (phase + '-command.json')
    require(not command_path.exists(), 'This cloud stage was already registered')

    if phase == 'qualify':
        require(not science.exists(), 'Fresh scientific input extraction root required')
        require(shutil.disk_usage(host).free >= 4 * 2**30, 'Registered hosted setup reserve unavailable; native gates remain unchanged')
        science.mkdir()
        with tarfile.open(assets / 'scientific-inputs.tar.gz', 'r:gz') as archive:
            members = archive.getmembers()
            require(len(members) == len(source_manifest['members']) and {m.name for m in members} == set(source_manifest['members']), 'Scientific archive member set differs')
            for member in members:
                require(member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts,
                        'Unsafe scientific archive member')
                require(member.size <= 8 * 2**20, 'Unregistered large input member')
                target = science / member.name
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as output:
                    shutil.copyfileobj(archive.extractfile(member), output)
                require(identity(target) == source_manifest['members'][member.name], 'Scientific archive member identity differs')
        save(case / 'R5_SCIENTIFIC_INPUT_EXTRACTION.json', {
            'schema': 'razr-r5-real-cloud-scientific-input-extraction-v1', 'input_archive': bind(assets / 'scientific-inputs.tar.gz'),
            'manifest': bind(assets / 'SCIENTIFIC_INPUT_MANIFEST.json'), 'actual_root': str(science),
            'members_verified': len(source_manifest['members']), 'original_bytes_preserved': True,
            'historical_absolute_paths_used_for_runtime_access': False})
        contract = {'schema': 'razr-r5-new-locked-runtime-qualification-contract-v1',
                    'functional_root': str(functional), 'functional_commit': S4,
                    'expected_qualification_contract': str(case / 'runtime-qualification-contract.json'),
                    'expected_qualification_output': str(case / 'runtime-qualification-owned/worker'),
                    'qualifier_identity': identity(qualifier), 'asset_manifest': bind(assets / 'CLOUD_ASSET_MANIFEST.json'),
                    'locked_project_inputs': template['locked_project_inputs'],
                    'expected_43_package_versions': template['science_contract']['expected_43_package_versions'],
                    'actual_import_probes': ['numpy', 'scipy', 'OCP', 'vtk', 'cadquery', 'trame', 'trame.widgets.client', 'trame.widgets.trame'],
                    'wheel_scratch': str(host / 'qualification-wheel-scratch'),
                    'maximum_single_wheel_bytes': 268435456, 'maximum_report_bytes': 6291456,
                    'maximum_output_bytes': 8388608, 'old_R4_qualification_reused': False,
                    'capacity_basis': template['fresh_runtime_capacity_basis']}
        cp = save(case / 'runtime-qualification-contract.json', contract)
        ep = save(case / 'runtime-qualification-execution-contract.json', {
            'schema': 'razr-r5-cloud-runtime-qualification-native-execution-v1',
            'supervisor_sha256': identity(supervisor)['sha256'], 'resource_limits': limits,
            'qualifier_source': bind(qualifier), 'qualification_contract': bind(cp)})
        command = ['/usr/bin/python3', '-B', str(supervisor), '--contract', str(ep), '--out', str(case / 'runtime-qualification-owned'),
                   str(functional / '.venv/bin/python'), '-I', '-B', str(qualifier), '--contract', str(cp),
                   '--out', str(case / 'runtime-qualification-owned/worker')]
        bound_execution_inputs += [bind(p) for p in (supervisor, cp, ep)]
        owned_execution_contract = bind(ep)
        expected_owned_worker_command = command[7:]
        owned_controller = str(case / 'runtime-qualification-owned/controller.json')
    else:
        for relative, expected in source_manifest['members'].items():
            require(identity(science / relative) == expected, 'Original scientific input changed before stage')
        qualification = check_qualification(case)
        c = template['science_contract']
        original_root = Path(template['original_workspace_root'])
        def actual(old):
            path = Path(old)
            require(path.is_absolute() and path.is_relative_to(original_root), 'Original frozen input locator outside registered workspace')
            return science / path.relative_to(original_root)
        source_bindings = []
        for item in c['bound_sources']:
            p = actual(item['path'])
            require(identity(p) == item['identity'], 'Original science source identity changed')
            source_bindings.append(bind(p))
        source_bindings.extend(bind(p) for p in (qualifier, entry, Path(__file__)))
        if phase == 'core-producer':
            cloud = dict(c)
            cloud['schema'] = 'r5-finite-native-trim-core-cloud-producer-contract-v1'
            cloud['registered_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
            cloud['workspace_root'] = str(science)
            for k in ('selection', 'mapping', 'projection'):
                cloud[k] = bind(actual(c[k]['path']))
            cloud['inventory_source'] = str(actual(c['inventory_source']))
            for k in ('bound_records', 'bound_sources'):
                cloud[k] = [bind(actual(x['path'])) for x in c[k]]
            cloud['bound_records'].append(bind(qualification))
            cloud['bound_sources'].extend(bind(p) for p in (qualifier, entry, Path(__file__)))
            cloud['fresh_runtime_qualification'] = bind(qualification)
            cloud['original_local_contract_identity'] = template['original_local_contract_identity']
            cloud['historical_admission_bindings_replaced'] = template['historical_admission_bindings_replaced']
            cloud['new_runtime_and_actual_paths_not_original_environment'] = True
            cp = save(case / 'R5_CLOUD_NATIVE_TRIM_CORE_PRODUCER_CONTRACT.json', cloud)
            script = science / 'r5-native/trim-core-witness/native_trim_core_witness_r5.py'
            payload_args = ['--contract', str(cp), '--out', str(case / 'core-producer-owned/worker')]
        elif phase == 'core-reader':
            pc = case / 'R5_CLOUD_NATIVE_TRIM_CORE_PRODUCER_CONTRACT.json'
            producer = case / 'core-producer-owned/worker/R5_NATIVE_TRIM_CORE_WITNESS.json'
            controller = case / 'core-producer-owned/controller.json'
            runtime_receipt = case / 'core-producer-runtime.json'
            require(json.loads(controller.read_text())['completed'] and json.loads(runtime_receipt.read_text())['completed'] and json.loads(producer.read_text())['completed'],
                    'Original complete finite producer, supervisor and fresh runtime closeout required before reader')
            script = science / 'r5-native/trim-core-witness/read_native_trim_core_witness_r5.py'
            cp = save(case / 'R5_CLOUD_NATIVE_TRIM_CORE_READER_CONTRACT.json', {
                'schema': 'r5-finite-native-trim-core-cloud-readback-contract-v1', 'reader_identity': identity(script),
                'producer_report': bind(producer), 'producer_contract': bind(pc),
                'producer_owned_controller': bind(controller), 'producer_runtime_closeout': bind(runtime_receipt),
                'scope': c['scope'], 'capacity': c['capacity']})
            payload_args = ['--contract', str(cp), '--out', str(case / 'core-reader-owned/worker')]
        else:
            require(phase in ('full-factory', 'full-reader') and os.environ['POSE'] in ('near', 'far'), 'Unregistered full-factory phase or pose')
            k3 = host / 'k3full'
            source_bindings += [bind(p) for p in sorted(k3.glob('*.py'))]
            s4 = json.loads((case / 'S4-source-before.json').read_text())
            for relative, digest in s4['present_source_sha256'].items():
                if relative.endswith('.py'):
                    p = functional / relative
                    require(identity(p)['sha256'] == digest, 'Actual S4 source changed before stage')
                    source_bindings.append(bind(p))
            mode = 'factory' if phase == 'full-factory' else 'readback'
            script = k3 / 'supervise_k3full.py'
            payload_args = ['--mode', mode, '--output', str(case / mode), '--pose', os.environ['POSE'],
                            '--k3-stow', str(case / 'prerequisite-stow_tabs_3'), '--k3-predock', str(case / 'prerequisite-predock'),
                            '--binding', str(k3 / 'K3FULL_K3_BINDING.json'), '--key-binding', str(k3 / 'K3FULL_K1_BINDING.json'),
                            '--contract', str(k3 / 'PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json'), '--k1-contract', str(k3 / 'KEY_FORWARD_LOOP_V1_CONTRACT.json')]
            if mode == 'readback':
                report = case / 'factory/worker/report.json'
                require(json.loads(report.read_text()).get('complete_preview_exports_retained') is True, 'Original complete preview requirement for independent reader not met')
                prior = json.loads((case / 'full-factory-runtime.json').read_text())
                require(prior['qualified_runtime_before'] and prior['qualified_runtime_after'] and prior['all_bound_sources_unchanged'] and prior['contract_and_entry_unchanged'],
                        'Fresh runtime closeout invalid before full reader')
                payload_args += ['--report', str(report)]
        source_bindings = list({x['path']: x for x in source_bindings}.values())
        runtime_contract = save(case / (phase + '-runtime-contract.json'), {
            'schema': 'razr-r5-current-runtime-entry-contract-v1', 'entry_identity': identity(entry),
            'expected_entry_contract': str(case / (phase + '-runtime-contract.json')),
            'expected_receipt': str(case / (phase + '-runtime.json')),
            'expected_script_arguments': list(payload_args),
            'script': str(script), 'script_identity': identity(script), 'qualifier_source': str(qualifier),
            'qualification': bind(qualification), 'bound_sources': source_bindings, 'maximum_receipt_bytes': 4194304,
            'native_original_six_limits': limits, 'full_factory_child_module_origins_claimed': False})
        bound_execution_inputs += [bind(p) for p in (runtime_contract, script, qualification)]
        command = [str(functional / '.venv/bin/python'), '-I', '-B', str(entry), '--contract', str(runtime_contract),
                   '--receipt', str(case / (phase + '-runtime.json')), '--', *payload_args]
        if phase.startswith('core-'):
            execution = save(case / (phase + '-execution-contract.json'), {
                'schema': 'razr-r5-cloud-finite-native-execution-v1', 'supervisor_sha256': identity(supervisor)['sha256'],
                'resource_limits': limits, 'fresh_runtime_contract': bind(runtime_contract), 'scientific_contract': bind(cp)})
            bound_execution_inputs += [bind(p) for p in (supervisor, cp, execution)]
            owned_execution_contract = bind(execution)
            expected_owned_worker_command = list(command)
            owned_controller = str(case / (phase + '-owned/controller.json'))
            command = ['/usr/bin/python3', '-B', str(supervisor), '--contract', str(execution), '--out', str(case / (phase + '-owned')), *command]
    command = ['/usr/bin/python3', '-B', str(host / 'service-launch.py'), str(case / (phase + '-runner')), *command]
    save(command_path, {'schema': 'razr-r5-cloud-registered-command-v1', 'phase': phase,
         'registered_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'registrar': bind(__file__),
         'asset_manifest': bind(assets / 'CLOUD_ASSET_MANIFEST.json'), 'command': command,
         'cwd': str(functional), 'original_six_resource_limits': limits,
         'bound_execution_inputs': bound_execution_inputs,
         'owned_execution_contract': owned_execution_contract,
         'expected_owned_worker_command': expected_owned_worker_command,
         'owned_controller': owned_controller,
         'runtime_newly_qualified_this_job_required': phase != 'qualify', 'native_execution_claimed': False})
    print(json.dumps({'registered_command': str(command_path), 'phase': phase}), flush=True)


def execute(path):
    path = path.resolve()
    before = identity(path)
    value = json.loads(path.read_text())
    require(identity(value['registrar']['path']) == value['registrar']['identity'], 'Command registrar changed before actual execution')
    for item in value['bound_execution_inputs']:
        require(identity(item['path']) == item['identity'], 'Bound execution input changed before launch')
    receipt = path.with_name(path.stem + '-actual.json')
    require(not receipt.exists(), 'Do not overwrite a real attempt receipt')
    start = time.monotonic()
    observed = {'schema': 'razr-r5-cloud-registered-command-actual-v1', 'command_record': bind(path), 'phase': value['phase'],
                'command': value['command'], 'cwd': value['cwd'], 'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                'subprocess_started': False}
    code = 2
    try:
        with path.with_suffix('.stdout').open('xb') as stdout, path.with_suffix('.stderr').open('xb') as stderr:
            observed['subprocess_started'] = True
            result = subprocess.run(value['command'], cwd=value['cwd'], stdout=stdout, stderr=stderr)
            code = result.returncode
    except BaseException as exc:
        observed['failure'] = {'type': type(exc).__name__, 'message': str(exc)}
    observed.update(exit_code=code, seconds=time.monotonic() - start,
                    command_record_unchanged=identity(path) == before,
                    stdout_identity=identity(path.with_suffix('.stdout')), stderr_identity=identity(path.with_suffix('.stderr')))
    observed['execution_inputs_unchanged'] = all(identity(x['path']) == x['identity'] for x in value['bound_execution_inputs'])
    if value['owned_controller']:
        cp = Path(value['owned_controller'])
        controller = json.loads(cp.read_text()) if cp.is_file() else None
        observed['owned_command_arguments_bound'] = bool(controller and
            controller['command'] == value['expected_owned_worker_command'] and
            controller['contract_sha256'] == value['owned_execution_contract']['identity']['sha256'])
        observed['actual_owned_controller'] = bind(cp) if cp.is_file() else None
    else:
        observed['owned_command_arguments_bound'] = None
        observed['full_native_argument_binding_method'] = 'Entire original full-supervisor argv and receipt strictly bound by fresh runtime entry; unchanged original supervisor constructs and records its original child command.'
    if code == 0 and (not observed['execution_inputs_unchanged'] or observed['owned_command_arguments_bound'] is False):
        code = observed['exit_code'] = 2
    save(receipt, observed)
    print(json.dumps({'phase': value['phase'], 'exit_code': code, 'seconds': observed['seconds']}), flush=True)
    return code


def seal(args):
    case = Path(os.environ['CASE_DIR']).resolve()
    host = Path(os.environ['HOST_ROOT']).resolve()
    rows = {}
    for path in sorted(case.rglob('*')):
        if path.is_file():
            require(not path.is_symlink(), 'Raw evidence must be actual regular files')
            rows[str(path.relative_to(case))] = identity(path)
    additional = {}
    for base, label in ((host / 'native-science', 'scientific-inputs'), (args.assets.resolve(), 'published-assets')):
        for path in sorted(base.rglob('*')):
            if path.is_file() and '.git' not in path.relative_to(base).parts:
                additional[label + '/' + str(path.relative_to(base))] = identity(path)
    total = sum(x['bytes'] for x in rows.values()) + sum(x['bytes'] for x in additional.values())
    record = {'schema': 'razr-r5-cloud-complete-raw-evidence-seal-v1', 'raw_members': rows,
              'original_inputs_and_reviewed_sources': additional, 'scientific_raw_bytes_including_current_inputs': total,
              'original_six_native_limits_unchanged': True, 'manufacturing_go': False, 'full_continuous_G2': False,
              'physical_qualification': False, 'new_runtime_fixture_separate_from_scientific_output_budget': True}
    if os.environ['CASE_KIND'] == 'core':
        record['registered_scientific_output_budget_bytes'] = 67108864
        record['within_registered_64MiB_budget'] = total <= 67108864
    save(case / 'R5_COMPLETE_RAW_EVIDENCE_MANIFEST.json', record)
    if os.environ['CASE_KIND'] == 'core':
        require(record['within_registered_64MiB_budget'], 'Original 64 MiB finite scientific campaign budget exceeded')
    print(json.dumps({k: record[k] for k in ('scientific_raw_bytes_including_current_inputs', 'physical_qualification', 'full_continuous_G2')}), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest='command', required=True)
    reg = sub.add_parser('register', allow_abbrev=False)
    reg.add_argument('phase', choices=('qualify', 'core-producer', 'core-reader', 'full-factory', 'full-reader'))
    reg.add_argument('--assets', type=Path, required=True)
    ex = sub.add_parser('execute', allow_abbrev=False)
    ex.add_argument('record', type=Path)
    close = sub.add_parser('seal', allow_abbrev=False)
    close.add_argument('--assets', type=Path, required=True)
    verify = sub.add_parser('verify-submission', allow_abbrev=False)
    verify.add_argument('--assets', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'register':
        register(args)
        return 0
    if args.command == 'execute':
        return execute(args.record)
    if args.command == 'verify-submission':
        assets = args.assets.resolve()
        check_assets(assets)
        save(Path(os.environ['CASE_DIR']) / 'R5_SUBMISSION_SOURCE_BINDING.json', {
            'schema': 'razr-r5-native-actual-reviewed-submission-binding-v1',
            'source_lock': bind(assets / 'SOURCE_LOCK.json'), 'run_request': bind(assets / 'RUN_REQUEST.json'),
            'repository': os.environ['GITHUB_REPOSITORY'], 'actual_ref': os.environ['GITHUB_REF'],
            'actual_triggering_commit': os.environ['GITHUB_SHA'],
            'all_reviewed_assets_and_independent_workflow_verified': True,
            'native_or_runtime_qualification_started': False})
        return 0
    return seal(args)


if __name__ == '__main__':
    raise SystemExit(main())
