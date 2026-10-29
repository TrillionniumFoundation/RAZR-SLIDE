"""Register real local qualification and unchanged finite native producer/reader.

No GitHub workflow identity or hosted service namespace is invented. The exact
original native supervisor reads the actual current service cgroup directly.
"""
from pathlib import Path
import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
ASSETS = BASE / 'razr-current/engineering/engineering-followup-20261028-r5/cloud-native-v1'
SCIENCE = ROOT / 'recovered-science-v1'
CASE = ROOT / 'native80-attempt1'
FUNCTIONAL = ROOT / 'genuine-s4-worktree-v2'
SUPERVISOR = SCIENCE / 'r4-native/recovered/native/source/supervise_native_r3.py'
QUALIFIER = ROOT / 'qualify_fresh_runtime_r7_v1.py'
ENTRY = ASSETS / 'run_fresh_runtime_script_r5.py'
S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'

def require(ok, message):
    if not ok:
        raise ValueError(message)

def identity(p):
    p = Path(p)
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(2**20), b''):
            h.update(b)
    return {'bytes': p.stat().st_size, 'sha256': h.hexdigest()}

def bind(p):
    return {'path': str(Path(p).resolve()), 'identity': identity(p)}

def save(p, obj):
    p = Path(p); require(not p.exists(), 'Immutable new receipt required: ' + str(p))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')
    return p

def strict_inventory(root):
    require(stat.S_ISDIR(root.lstat().st_mode), 'Inventory root is not a real directory')
    result = {}
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
        for name in dirs:
            require(stat.S_ISDIR((Path(base) / name).lstat().st_mode), 'Symlink or special directory in complete census')
        for name in files:
            p = Path(base) / name
            require(stat.S_ISREG(p.lstat().st_mode), 'Special or symlink file in complete census')
            result[str(p.relative_to(root))] = identity(p)
    return result


def seal_phase(phase, actual_stage_completed):
    # Same original scope: all case raw outputs, all161 scientific inputs,
    # every published source asset. New local runtimefixture remains separate.
    target = CASE / (phase + '-seal.json')
    require(not target.exists(), 'New immutable per-phase scientific seal required')
    rows = strict_inventory(CASE)
    science = strict_inventory(SCIENCE)
    published = strict_inventory(ASSETS)
    local = {}
    for p in sorted(ROOT.iterdir()):
        if p.is_file() and p.suffix in ('.py', '.json'):
            require(stat.S_ISREG(p.lstat().st_mode), 'Local source metadata is not regular')
            local[p.name] = identity(p)
    for parent in ('setup-assess_only-v2', 'setup-install_only-v2'):
        p = ROOT / parent / 'R7_FRESH_LOCAL_RUNTIME_SETUP_ACTUAL_V1.json'
        if p.is_file():
            local[parent + '/' + p.name] = identity(p)
    total = sum(v['bytes'] for group in (rows, science, published, local) for v in group.values())
    record = {'schema': 'razr-r7-complete-finite-scientific-phase-seal-v1', 'phase': phase,
              'raw_case_members': rows, 'all_original_scientific_inputs': science,
              'all_original_published_assets': published, 'new_local_source_and_bound_setup_receipts': local,
              'scientific_raw_bytes_including_current_inputs': total, 'registered_scientific_output_budget_bytes': 67108864,
              'within_registered_64MiB_budget': total <= 67108864,
              'actual_native_stage_completed': actual_stage_completed,
              'completed_scientific_stage': actual_stage_completed and total <= 67108864,
              'new_venv_uv_installation_and_transient_setup_fixture_separate': True,
              'historical_failed_stages_not_reclassified': True, 'full_continuous_G2': False,
              'manufacturing_go': False, 'physical_qualification': False}
    save(target, record)
    return record


def require_sealed_phase(phase):
    record = json.loads((CASE / (phase + '-seal.json')).read_text())
    require(record['completed_scientific_stage'] and record['within_registered_64MiB_budget'],
            'Original aggregate scientific budget or prior phase completion failed')
    for rel, expected in record['raw_case_members'].items():
        require(identity(CASE / rel) == expected, 'Prior raw evidence changed after phase seal')
    return record


def verify_sources():
    manifest = json.loads((ASSETS / 'SCIENTIFIC_INPUT_MANIFEST.json').read_text())['members']
    actual = strict_inventory(SCIENCE)
    require(set(actual) == set(manifest) and actual == manifest, 'Complete scientific input member set or bytes differ')
    for rel, expected in manifest.items():
        require(not (SCIENCE / rel).is_symlink() and identity(SCIENCE / rel) == expected, 'Original science input differs: ' + rel)
    setup_path = ROOT / 'setup-install_only-v2/R7_FRESH_LOCAL_RUNTIME_SETUP_ACTUAL_V1.json'
    setup = json.loads(setup_path.read_text())
    require(setup['completed'] and setup['postinstall_4GiB_original_gate_passed'], 'Current setup did not complete original postinstall admission')
    expected = json.loads((ROOT / 'R7_SETUP_INSTALL_ONLY_CONTRACT_V2.json').read_text())['expected_sources']
    spec = importlib.util.spec_from_file_location('r7_local_setup_helpers', ROOT / 'setup_fresh_s4_runtime_r7_v2.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    census = mod.verify_checkout(FUNCTIONAL, expected, S4)
    require(census['actual_member_count'] == 974, 'Actual complete S4 member census differs')
    return setup_path, setup

def check_qualification():
    require_sealed_phase('qualify')
    q = CASE / 'qualify-owned/worker/R5_FRESH_RUNTIME_QUALIFICATION.json'
    controller = json.loads((CASE / 'qualify-owned/controller.json').read_text())
    registration = json.loads((CASE / 'qualify-command.json').read_text())
    actual = json.loads((CASE / 'qualify-command-actual.json').read_text())
    report = json.loads(q.read_text())
    require(controller['completed'] and controller['worker_started'] and controller['resource_stop'] is None, 'Original qualifier supervision failed')
    require(controller['command'] == registration['worker_command'] and controller['contract_sha256'] == registration['supervision_contract']['identity']['sha256'], 'Actual qualifier command differs from bound registration')
    require(actual['completed'] and report['completed'] and report['fresh_wheels_and_installed_RECORDs_verified'] and report['all_new_runtime_files_unchanged'], 'New real runtime did not qualify')
    return q

def register(phase):
    setup_path, setup = verify_sources()
    template = json.loads((ASSETS / 'R5_CLOUD_NATIVE_SCIENCE_TEMPLATE.json').read_text())
    limits = template['original_resource_limits']
    CASE.mkdir(exist_ok=True)
    command_path = CASE / (phase + '-command.json')
    require(not command_path.exists(), 'Stage already registered')
    all_bound = [bind(p) for p in (Path(__file__), QUALIFIER, ENTRY, SUPERVISOR, setup_path,
                                 ASSETS / 'R5_CLOUD_NATIVE_SCIENCE_TEMPLATE.json', ASSETS / 'SCIENTIFIC_INPUT_MANIFEST.json')]
    if phase == 'qualify':
        require(shutil.disk_usage(ROOT).free >= 4 * 2**30, 'Original 4 GiB postinstall qualification registration floor unavailable')
        cp = save(CASE / 'qualify-contract.json', {
            'schema': 'razr-r7-new-locked-local-runtime-qualification-contract-v1',
            'functional_root': str(FUNCTIONAL), 'functional_commit': S4,
            'expected_qualification_contract': str(CASE / 'qualify-contract.json'),
            'expected_qualification_output': str(CASE / 'qualify-owned/worker'),
            'qualifier_identity': identity(QUALIFIER), 'locked_project_inputs': template['locked_project_inputs'],
            'expected_43_package_versions': template['science_contract']['expected_43_package_versions'],
            'actual_import_probes': ['numpy', 'scipy', 'OCP', 'vtk', 'cadquery', 'trame', 'trame.widgets.client', 'trame.widgets.trame'],
            'wheel_scratch': str(ROOT / 'qualification-wheel-scratch-v1'), 'maximum_single_wheel_bytes': 268435456,
            'maximum_report_bytes': 6291456, 'maximum_output_bytes': 8388608,
            'old_R4_qualification_reused': False, 'hosted_identity_claimed': False,
            'capacity_basis': template['fresh_runtime_capacity_basis'], 'new_local_setup': bind(setup_path)})
        worker = [str(FUNCTIONAL / '.venv/bin/python'), '-I', '-B', str(QUALIFIER), '--contract', str(cp), '--out', str(CASE / 'qualify-owned/worker')]
        all_bound += [bind(cp)]
    else:
        qualification = check_qualification()
        original = template['science_contract']; original_root = Path(template['original_workspace_root'])
        def actual(old):
            p = Path(old)
            require(p.is_absolute() and p.is_relative_to(original_root), 'Original input outside source root')
            return SCIENCE / p.relative_to(original_root)
        bound_sources = [bind(actual(x['path'])) for x in original['bound_sources']]
        bound_sources += [bind(p) for p in (QUALIFIER, ENTRY, Path(__file__))]
        if phase == 'core-producer':
            c = copy.deepcopy(original)
            c.update(schema='r7-finite-native-trim-core-local-producer-contract-v1',
                     registered_utc=dt.datetime.now(dt.timezone.utc).isoformat(), workspace_root=str(SCIENCE))
            for k in ('selection', 'mapping', 'projection'):
                c[k] = bind(actual(original[k]['path']))
            c['inventory_source'] = str(actual(original['inventory_source']))
            for k in ('bound_records', 'bound_sources'):
                c[k] = [bind(actual(x['path'])) for x in original[k]]
            c['bound_records'].append(bind(qualification))
            c['bound_sources'].extend(bind(p) for p in (QUALIFIER, ENTRY, Path(__file__)))
            c['fresh_runtime_qualification'] = bind(qualification)
            c['original_local_contract_identity'] = template['original_local_contract_identity']
            c['historical_admission_bindings_replaced'] = template['historical_admission_bindings_replaced']
            c['new_local_runtime_identity'] = True
            cp = save(CASE / 'core-producer-science-contract.json', c)
            script = SCIENCE / template['science_worker_paths']['producer']
        else:
            require(phase == 'core-reader', 'Unsupported stage')
            require_sealed_phase('core-producer')
            prior = CASE / 'core-producer-owned/worker/R5_NATIVE_TRIM_CORE_WITNESS.json'
            producer_controller = CASE / 'core-producer-owned/controller.json'
            producer_runtime = CASE / 'core-producer-runtime.json'
            producer_contract = CASE / 'core-producer-science-contract.json'
            require(all(json.loads(p.read_text())['completed'] for p in (prior, producer_controller, producer_runtime)), 'Producer finite experiment or runtime incomplete')
            script = SCIENCE / template['science_worker_paths']['reader']
            cp = save(CASE / 'core-reader-science-contract.json', {
                'schema': 'r7-finite-native-trim-core-local-independent-readback-contract-v1',
                'reader_identity': identity(script), 'producer_report': bind(prior), 'producer_contract': bind(producer_contract),
                'producer_owned_controller': bind(producer_controller), 'producer_runtime_closeout': bind(producer_runtime),
                'scope': original['scope'], 'capacity': original['capacity']})
        payload = ['--contract', str(cp), '--out', str(CASE / (phase + '-owned/worker'))]
        runtime = save(CASE / (phase + '-runtime-contract.json'), {
            'schema': 'razr-r7-current-local-runtime-entry-contract-v1', 'entry_identity': identity(ENTRY),
            'expected_entry_contract': str(CASE / (phase + '-runtime-contract.json')),
            'expected_receipt': str(CASE / (phase + '-runtime.json')), 'expected_script_arguments': payload,
            'script': str(script), 'script_identity': identity(script), 'qualifier_source': str(QUALIFIER),
            'qualification': bind(qualification), 'bound_sources': bound_sources, 'maximum_receipt_bytes': 4194304,
            'native_original_six_limits': limits, 'full_factory_child_module_origins_claimed': False})
        worker = [str(FUNCTIONAL / '.venv/bin/python'), '-I', '-B', str(ENTRY), '--contract', str(runtime),
                  '--receipt', str(CASE / (phase + '-runtime.json')), '--', *payload]
        all_bound += [bind(p) for p in (cp, runtime, script, qualification)]
    ep = save(CASE / (phase + '-supervision-contract.json'), {
        'schema': 'razr-r7-original-native-local-supervision-contract-v1',
        'supervisor_sha256': identity(SUPERVISOR)['sha256'], 'resource_limits': limits,
        'worker_science_contract': bind(cp), 'exact_worker_command': worker})
    command = [sys.executable, '-B', str(SUPERVISOR), '--contract', str(ep), '--out', str(CASE / (phase + '-owned')), *worker]
    all_bound.append(bind(ep))
    receipt = {'schema': 'razr-r7-original-native-local-command-v1', 'phase': phase,
               'registered_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'command': command, 'cwd': str(FUNCTIONAL),
               'worker_command': worker, 'supervision_contract': bind(ep), 'bound_inputs': all_bound,
               'pinned_uv_directory': str(Path(setup['uv']['executable']).parent),
               'original_six_resource_limits': limits, 'hosted_service_harness_claimed': False,
               'actual_cgroup_source': '/sys/fs/cgroup/memory.stat', 'scientific_algorithms_or_thresholds_changed': False}
    save(command_path, receipt)
    print(json.dumps({'registered': str(command_path), 'phase': phase, 'identity': identity(command_path)}))

def execute(path):
    c = json.loads(path.read_text()); before = identity(path)
    for x in c['bound_inputs']:
        require(identity(x['path']) == x['identity'], 'Bound execution input changed')
    require(c['command'][7:] == c['worker_command'], 'Complete bound native argv differs')
    target = path.with_name(path.stem + '-actual.json')
    require(not target.exists(), 'Actual receipt exists')
    env = dict(os.environ); env['PATH'] = c['pinned_uv_directory'] + os.pathsep + env['PATH']
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    start = time.monotonic()
    with path.with_suffix('.stdout').open('xb') as stdout, path.with_suffix('.stderr').open('xb') as stderr:
        result = subprocess.run(c['command'], cwd=c['cwd'], env=env, stdout=stdout, stderr=stderr)
    controller = CASE / (c['phase'] + '-owned/controller.json')
    observed = json.loads(controller.read_text()) if controller.exists() else None
    unchanged = all(identity(x['path']) == x['identity'] for x in c['bound_inputs']) and identity(path) == before
    bound = bool(observed and observed['command'] == c['worker_command'] and observed['contract_sha256'] == c['supervision_contract']['identity']['sha256'])
    report = {'schema': 'razr-r7-native-local-command-actual-v1', 'command_record': bind(path),
              'exit_code': result.returncode, 'seconds': time.monotonic() - start, 'inputs_unchanged': unchanged,
              'actual_supervisor_and_worker_arguments_bound': bound, 'controller': bind(controller) if controller.exists() else None,
              'stdout': bind(path.with_suffix('.stdout')), 'stderr': bind(path.with_suffix('.stderr')),
              'completed': result.returncode == 0 and bool(observed and observed['completed']) and unchanged and bound}
    save(target, report)
    seal = seal_phase(c['phase'], report['completed'])
    print(json.dumps({**report, 'scientific_aggregate_seal_passed': seal['completed_scientific_stage'], 'scientific_total_bytes': seal['scientific_raw_bytes_including_current_inputs']}))
    return 0 if report['completed'] and seal['completed_scientific_stage'] else result.returncode or 2

def main():
    ap = argparse.ArgumentParser(allow_abbrev=False); sub = ap.add_subparsers(dest='action', required=True)
    p = sub.add_parser('register'); p.add_argument('phase', choices=['qualify', 'core-producer', 'core-reader'])
    p = sub.add_parser('execute'); p.add_argument('record', type=Path)
    a = ap.parse_args()
    if a.action == 'register':
        register(a.phase); return 0
    return execute(a.record.resolve())

if __name__ == '__main__':
    raise SystemExit(main())
