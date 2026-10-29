"""Register unchanged complete K3 factories and independent all-pair readers.

GITHUB_WORKSPACE is used solely because the original external driver names its
functional-root variable that way. It names a real clean S4 worktree; no hosted
job/run/ref/trigger identity is supplied or claimed.
"""
from pathlib import Path
import argparse
import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
K3 = BASE / 'r7-recovery/k3'
DRIVERS = K3 / 'source/k3full'
CORE_SOURCE = ROOT / 'register_and_run_native_local_r7_v3.py'
spec = importlib.util.spec_from_file_location('r7_native_registration_helpers', CORE_SOURCE)
core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core)

def readback_inputs():
    receipt_path = ROOT / 'R7_FULL_FACTORY_INPUTS_ACTUAL_READBACK_V1.json'
    receipt = json.loads(receipt_path.read_text())
    core.require(receipt['completed'], 'Original complete prerequisites not read back')
    for relative, expected in receipt['original_drivers'].items():
        core.require(core.identity(DRIVERS / relative) == expected, 'Original complete driver changed')
    core.require(set(core.strict_inventory(DRIVERS)) == set(receipt['original_drivers']), 'Complete original driver member set differs')
    for pose, record in receipt['poses'].items():
        src = K3 / ('prerequisite-' + pose)
        core.require(set(core.strict_inventory(src)) == set(record['members']), 'Full prerequisite member set changed')
        for relative, expected in record['members'].items():
            p = src / relative
            core.require(not p.is_symlink() and core.identity(p) == expected, 'Bound prerequisite original changed')
    return receipt_path, receipt

def register(pose, mode):
    setup_path, setup = core.verify_sources()
    qualification = core.check_qualification()
    original_core_reader = core.CASE / 'core-reader-owned/worker/R5_NATIVE_TRIM_CORE_READBACK.json'
    # Bind the entire actual finite producer/reader chain before complete-factory work.
    core.require_sealed_phase('core-reader')
    reader_actual = core.CASE / 'core-reader-command-actual.json'
    reader_runtime = core.CASE / 'core-reader-runtime.json'
    core.require(json.loads(reader_actual.read_text())['completed'] and json.loads(reader_runtime.read_text())['completed'], 'Independent native80 reader did not complete')
    inputs_path, inputs = readback_inputs()
    case = ROOT / ('full-' + pose + '-attempt1')
    case.mkdir(exist_ok=True)
    command_file = case / (mode + '-command.json')
    core.require(not command_file.exists(), 'Fresh complete-factory phase required')
    resources = core.json.loads((core.ASSETS / 'R5_CLOUD_NATIVE_SCIENCE_TEMPLATE.json').read_text())['original_resource_limits']
    v = os.statvfs(case)
    core.require(v.f_bavail * v.f_frsize >= 1536 * 2**20, 'Original extra input/export disk reserve unavailable')
    source = DRIVERS / 'supervise_k3full.py'
    payload = ['--mode', mode, '--output', str(case / mode), '--pose', pose,
               '--k3-stow', str(K3 / 'prerequisite-stow_tabs_3'), '--k3-predock', str(K3 / 'prerequisite-predock'),
               '--binding', str(DRIVERS / 'K3FULL_K3_BINDING.json'), '--key-binding', str(DRIVERS / 'K3FULL_K1_BINDING.json'),
               '--contract', str(DRIVERS / 'PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json'),
               '--k1-contract', str(DRIVERS / 'KEY_FORWARD_LOOP_V1_CONTRACT.json')]
    prior = []
    if mode == 'readback':
        factory = case / 'factory/worker/report.json'
        runtime = case / 'factory-runtime.json'
        controller = case / 'factory/controller.json'
        actual = case / 'factory-command-actual.json'
        core.require(json.loads(factory.read_text()).get('complete_preview_exports_retained') is True, 'Original full-preview requirement failed')
        core.require(all(json.loads(p.read_text())['completed'] for p in (runtime, controller, actual)), 'Full producer or runtime incomplete')
        payload.extend(['--report', str(factory)])
        prior.extend(core.bind(p) for p in (factory, runtime, controller, actual))
    sources = [core.bind(p) for p in (Path(__file__), CORE_SOURCE, core.QUALIFIER, core.ENTRY)]
    sources += [core.bind(DRIVERS / relative) for relative in inputs['original_drivers']]
    source_manifest = json.loads((ROOT / 'R7_SETUP_INSTALL_ONLY_CONTRACT_V2.json').read_text())['expected_sources']
    sources += [core.bind(core.FUNCTIONAL / relative) for relative in source_manifest if relative.endswith('.py')]
    runtime_contract = core.save(case / (mode + '-runtime-contract.json'), {
        'schema': 'razr-r7-current-local-full-factory-runtime-contract-v1', 'entry_identity': core.identity(core.ENTRY),
        'expected_entry_contract': str(case / (mode + '-runtime-contract.json')), 'expected_receipt': str(case / (mode + '-runtime.json')),
        'expected_script_arguments': payload, 'script': str(source), 'script_identity': core.identity(source),
        'qualifier_source': str(core.QUALIFIER), 'qualification': core.bind(qualification), 'bound_sources': sources,
        'maximum_receipt_bytes': 4194304, 'native_original_six_limits': resources,
        'full_factory_child_module_origins_claimed': False})
    command = [str(core.FUNCTIONAL / '.venv/bin/python'), '-I', '-B', str(core.ENTRY), '--contract', str(runtime_contract),
               '--receipt', str(case / (mode + '-runtime.json')), '--', *payload]
    bound = [core.bind(p) for p in (Path(__file__), CORE_SOURCE, runtime_contract, source, qualification, setup_path, inputs_path, reader_actual, reader_runtime)] + prior
    bound.extend(sources)
    rec = {'schema': 'razr-r7-original-complete-factory-local-command-v1', 'pose': pose, 'mode': mode,
           'registered_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'command': command, 'cwd': str(core.FUNCTIONAL),
           'case': str(case), 'bound_inputs': bound, 'pinned_uv_directory': str(Path(setup['uv']['executable']).parent),
           'environment_overrides': {'GITHUB_WORKSPACE': str(core.FUNCTIONAL)},
           'GITHUB_WORKSPACE_means_actual_clean_functional_path_only': True,
           'hosted_run_or_job_identity_claimed': False, 'original_six_native_limits': resources,
           'original_all_pairs_and_complete_preview_requirements_unchanged': True,
           'capacity_basis': {'historical_near_factory_seconds': 278.12116997699997, 'historical_near_reader_seconds': 191.78153347900002,
                              'historical_peak_RSS_bytes': 573534208, 'fresh_pose_output_reserve_bytes': 67108864,
                              'prerequisite_existing_bytes': inputs['total_prerequisite_bytes'], 'heavy_native_concurrency': 1,
                              'full_bodies_expected': 154, 'unordered_pairs_per_worker_expected': 11781,
                              'hard_worker_wall_seconds': 1200, 'hard_worker_RSS_bytes': 1610612736}}
    core.save(command_file, rec)
    print(json.dumps({'registered': str(command_file), 'identity': core.identity(command_file)}))

def execute(path):
    before = core.identity(path); c = json.loads(path.read_text())
    core.verify_sources(); readback_inputs()
    for item in c['bound_inputs']:
        core.require(core.identity(item['path']) == item['identity'], 'Bound full-stage input changed')
    target = path.with_name(path.stem + '-actual.json'); core.require(not target.exists(), 'Actual stage receipt already exists')
    env = dict(os.environ); env.update(c['environment_overrides'])
    env['PATH'] = c['pinned_uv_directory'] + os.pathsep + env['PATH']; env['PYTHONDONTWRITEBYTECODE'] = '1'
    start = time.monotonic()
    with path.with_suffix('.stdout').open('xb') as out, path.with_suffix('.stderr').open('xb') as err:
        result = subprocess.run(c['command'], cwd=c['cwd'], env=env, stdout=out, stderr=err)
    case = Path(c['case']); runtime = case / (c['mode'] + '-runtime.json'); controller = case / c['mode'] / 'controller.json'
    runtime_value = json.loads(runtime.read_text()) if runtime.exists() else None
    controller_value = json.loads(controller.read_text()) if controller.exists() else None
    unchanged = all(core.identity(x['path']) == x['identity'] for x in c['bound_inputs']) and core.identity(path) == before
    report = {'schema': 'razr-r7-complete-factory-local-actual-v1', 'command_record': core.bind(path),
              'exit_code': result.returncode, 'seconds': time.monotonic() - start, 'bound_inputs_unchanged': unchanged,
              'actual_runtime_receipt': core.bind(runtime) if runtime.exists() else None,
              'actual_owned_controller': core.bind(controller) if controller.exists() else None,
              'stdout': core.bind(path.with_suffix('.stdout')), 'stderr': core.bind(path.with_suffix('.stderr')),
              'completed': result.returncode == 0 and unchanged and bool(runtime_value and runtime_value['completed']) and bool(controller_value and controller_value['completed'])}
    core.save(target, report); print(json.dumps(report))
    return 0 if report['completed'] else result.returncode or 2

def main():
    p = argparse.ArgumentParser(allow_abbrev=False); sub = p.add_subparsers(dest='action', required=True)
    r = sub.add_parser('register'); r.add_argument('pose', choices=['near','far']); r.add_argument('mode', choices=['factory','readback'])
    r = sub.add_parser('execute'); r.add_argument('record', type=Path)
    a = p.parse_args()
    if a.action == 'register': register(a.pose, a.mode); return 0
    return execute(a.record.resolve())

if __name__ == '__main__': raise SystemExit(main())
