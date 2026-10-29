"""Review one concrete original full-factory command without executing CAD."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import resource
import stat

resource.setrlimit(resource.RLIMIT_AS, (256 * 2**20, 256 * 2**20))
resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
parser = argparse.ArgumentParser()
parser.add_argument('--pose', choices=('near', 'far'), required=True)
parser.add_argument('--mode', choices=('factory', 'readback'), required=True)
args = parser.parse_args()
BASE = Path(__file__).resolve().parent.parent
ROOT = BASE / 'r7-native'
FUNCTIONAL = ROOT / 'genuine-s4-worktree-v3'
CORE = ROOT / 'native80-attempt1'
CASE = ROOT / ('full-' + args.pose + '-attempt1')
K3 = BASE / 'r7-recovery/k3'
DRIVERS = K3 / 'source/k3full'
ASSETS = BASE / 'razr-current/engineering/engineering-followup-20261028-r5/cloud-native-v1'


def identity(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(2**20), b''):
            digest.update(chunk)
    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def load(path):
    return json.loads(Path(path).read_text())


def bind(path):
    return {'path': str(path), 'identity': identity(path)}


cp = CASE / (args.mode + '-command.json')
rp = CASE / (args.mode + '-runtime-contract.json')
command, runtime = load(cp), load(rp)
initial = identity(cp)
limits = load(ASSETS / 'R5_CLOUD_NATIVE_SCIENCE_TEMPLATE.json')['original_resource_limits']
assert command['original_six_native_limits'] == runtime['native_original_six_limits'] == limits
assert command['pose'] == args.pose and command['mode'] == args.mode
assert command['case'] == str(CASE) and command['cwd'] == str(FUNCTIONAL)
assert command['environment_overrides'] == {'GITHUB_WORKSPACE': str(FUNCTIONAL)}
assert command['hosted_run_or_job_identity_claimed'] is False
assert command['GITHUB_WORKSPACE_means_actual_clean_functional_path_only']
assert runtime['script'] == str(DRIVERS / 'supervise_k3full.py')
assert runtime['script_identity']['sha256'] == 'e546a2919ed276331be89ea137de5e8b2121dece92604ea38b80486b3f7d32de'
assert identity(runtime['script']) == runtime['script_identity']
assert runtime['entry_identity'] == identity(ASSETS / 'run_fresh_runtime_script_r5.py')
expected_payload = ['--mode', args.mode, '--output', str(CASE / args.mode), '--pose', args.pose,
                    '--k3-stow', str(K3 / 'prerequisite-stow_tabs_3'), '--k3-predock', str(K3 / 'prerequisite-predock'),
                    '--binding', str(DRIVERS / 'K3FULL_K3_BINDING.json'), '--key-binding', str(DRIVERS / 'K3FULL_K1_BINDING.json'),
                    '--contract', str(DRIVERS / 'PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json'),
                    '--k1-contract', str(DRIVERS / 'KEY_FORWARD_LOOP_V1_CONTRACT.json')]
if args.mode == 'readback':
    expected_payload += ['--report', str(CASE / 'factory/worker/report.json')]
    assert load(CASE / 'factory/worker/report.json')['complete_preview_exports_retained']
    assert all(load(CASE / name)['completed'] for name in ('factory-command-actual.json', 'factory-runtime.json', 'factory/controller.json'))
assert runtime['expected_script_arguments'] == expected_payload
expected_command = [str(FUNCTIONAL / '.venv/bin/python'), '-I', '-B', str(ASSETS / 'run_fresh_runtime_script_r5.py'),
                    '--contract', str(rp), '--receipt', str(CASE / (args.mode + '-runtime.json')), '--', *expected_payload]
assert command['command'] == expected_command
assert runtime['expected_entry_contract'] == str(rp) and runtime['expected_receipt'] == str(CASE / (args.mode + '-runtime.json'))
for row in command['bound_inputs'] + runtime['bound_sources']:
    assert identity(row['path']) == row['identity'], row['path']
inputs = load(ROOT / 'R7_FULL_FACTORY_INPUTS_ACTUAL_READBACK_V1.json')
source_manifest = load(ROOT / 'R7_SETUP_INSTALL_ONLY_CONTRACT_V3.json')['expected_sources']
expected_sources = [ROOT / 'register_full_factory_local_r7_v3.py', ROOT / 'register_and_run_native_local_r7_v4.py',
                    ROOT / 'qualify_fresh_runtime_r7_v1.py', ASSETS / 'run_fresh_runtime_script_r5.py']
expected_sources += [DRIVERS / relative for relative in inputs['original_drivers']]
expected_sources += [FUNCTIONAL / relative for relative in source_manifest if relative.endswith('.py')]
assert runtime['bound_sources'] == [bind(path) for path in expected_sources]
assert runtime['qualification'] == bind(CORE / 'qualify-owned/worker/R5_FRESH_RUNTIME_QUALIFICATION.json')
assert load(runtime['qualification']['path'])['completed']
reader_seal = load(CORE / 'core-reader-seal.json')
assert reader_seal['completed_scientific_stage'] and reader_seal['within_registered_64MiB_budget']
for relative, expected in reader_seal['raw_case_members'].items():
    assert identity(CORE / relative) == expected
copy_receipt = load(CASE / 'R7_COMPLETE_INPUT_COPY_RECEIPT.json')
assert copy_receipt['completed'] and copy_receipt['copied_member_count'] == 4351
assert copy_receipt['copied_bytes'] == 408534237
for relative, expected in copy_receipt['members'].items():
    path = CASE / relative
    assert stat.S_ISREG(path.lstat().st_mode) and identity(path) == expected
assert load(CASE / 'K3FULL-driver-source.json') == inputs['original_drivers']
assert not (CASE / args.mode).exists(), 'Actual worker output must be fresh'
assert identity(cp) == initial
report = {
    'schema': 'razr-r7-full-factory-concrete-independent-command-review-v1',
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'review_pass': True, 'pose': args.pose, 'mode': args.mode, 'reviewer': identity(__file__),
    'command': identity(cp), 'runtime_contract': identity(rp),
    'actual_original_complete_input_copy_receipt': identity(CASE / 'R7_COMPLETE_INPUT_COPY_RECEIPT.json'),
    'independent_exact_copy_member_count': len(copy_receipt['members']),
    'independent_exact_copy_bytes': sum(v['bytes'] for v in copy_receipt['members'].values()),
    'bound_new_and_original_driver_source_count': 20,
    'bound_actual_S4_python_source_count': sum(name.endswith('.py') for name in source_manifest),
    'complete_original_argv_equal': True, 'actual_sources_and_all_prior_native_raw_bytes_unchanged': True,
    'original_six_resource_limits': limits, 'old_qualification_reused': False,
    'temporary_external_vtk_scratch_cleanup_discrepancy_remains_separate_unresolved': True,
    'does_not_reclassify_original_qualifier_or_native_results': True,
    'actual_native_CAD_executed_by_reviewer': False,
    'full_continuous_G2': False, 'physical_qualification': False,
}
output = BASE / 'r7-audit/full-factory-review' / ('R7_' + args.pose.upper() + '_' + args.mode.upper() + '_CONCRETE_REGISTRATION_REVIEW.json')
assert not output.exists()
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'path': str(output), 'identity': identity(output), 'review_pass': True}))
