"""Targeted actual refusal checks for the observed abbreviation bypass and duplicates."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time


def identity(path):
    data = Path(path).read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    root = Path(__file__).resolve().parents[1]
    out = Path(__file__).resolve().parent / 'canonical-entry-controls'
    out.mkdir(exist_ok=False)
    base_path = root / 'R4E_SUPPORT_SUPERVISION_V2_OWNED.json'
    base = json.loads(base_path.read_text())
    entry = root / 'run_owned_pure_math_r4e_v3.py'
    supervisor = root / 'supervise_owned_pure_math_r4e_v2.py'
    options = ['--original', '--contract', '--output', '--additional-producer', '--additional-reader']
    report = {'schema': 'razr-r4e-independent-canonical-entry-negative-controls-v1',
              'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'source_identity': identity(__file__),
              'entry_identity': identity(entry), 'supervisor_identity': identity(supervisor),
              'original_supervision_identity': identity(base_path), 'controls': [], 'completed': False,
              'expensive_mathematical_runs': 0, 'new_native_geometry_runs': 0}
    for name in ('observed_appended_abbreviation_bypass', 'duplicate_option_same_arity'):
        case = out / name; case.mkdir()
        watched = case / 'registered-output'; wrong = case / 'unregistered-output'
        contract = json.loads(base_path.read_text())
        contract.update(schema='razr-r4e-canonical-entry-independent-negative-control-v1',
                        supervisor_sha256=identity(supervisor)['sha256'],
                        worker_entry=str(entry), worker_entry_sha256=identity(entry)['sha256'],
                        worker_output_directory=str(watched), canonical_worker_options=options)
        contract_path = case / 'supervision-contract.json'
        contract_path.write_text(json.dumps(contract, indent=2) + '\n')
        arguments = ['--original', str(root.parent / 'recovered-inputs/RAZR-R3E-COMPLETE-SCIENTIFIC-EVIDENCE-20261027'),
                     '--contract', str(root / 'R4E_SUPPORT_CONTRACT_V2.json'), '--output', str(watched),
                     '--additional-producer', str(root / 'additional-bspline-v1/producer-attempt2/worker/report.json'),
                     '--additional-reader', str(root / 'additional-bspline-v1/reader/worker/report.json')]
        if name == 'observed_appended_abbreviation_bypass':
            arguments += ['--out', str(wrong)]
            expected = 'exact one-value argument pairs required'
        else:
            arguments[-2:] = ['--output', str(wrong)]
            expected = 'abbreviated, unexpected, equals-form, or duplicate worker option rejected'
        command = [sys.executable, '-I', '-S', '-B', str(supervisor), '--contract', str(contract_path),
                   '--out', str(case / 'supervision'), '--', *arguments]
        started = time.monotonic()
        process = subprocess.run(command, capture_output=True, text=True)
        seconds = time.monotonic() - started
        (case / 'parent.stdout.txt').write_text(process.stdout)
        (case / 'parent.stderr.txt').write_text(process.stderr)
        controller_path = case / 'supervision/controller.json'
        controller = json.loads(controller_path.read_text())
        log = case / 'supervision/execution.log'
        require(process.returncode == 2 and controller['completed'] is False and controller['worker_exit_code'] != 0,
                'Canonical negative control did not reject')
        require(expected in log.read_text(), 'Unexpected rejection reason')
        require(controller['resource_stop'] is None and controller['owned_child_identity_verified'], 'Wrong rejection layer')
        require(controller['owned_channel_descriptors_closed'] and controller['source_and_contract_unchanged'], 'Owned cleanup/source problem')
        require(not watched.exists() and not wrong.exists() and not (case / 'supervision/entry-receipt.json').exists(), 'Mathematical payload started')
        gates = ('wall_seconds', 'RSS_limit_bytes', 'shared_ceiling_bytes', 'disk_floor_bytes', 'maximum_output_bytes', 'metadata_margin_bytes')
        require(all(contract[k] == base[k] for k in gates), 'Original numeric gate changed')
        report['controls'].append({'name': name, 'command': command, 'seconds': seconds,
            'supervisor_exit_code': process.returncode, 'owned_entry_exit_code': controller['worker_exit_code'],
            'expected_rejection': expected, 'expected_rejection_observed': True,
            'math_outputs_and_payload_receipt_absent': True, 'original_numeric_gates_unchanged': True,
            'owned_handshake_and_cleanup_verified': True,
            'controller': {'path': str(controller_path), **identity(controller_path)},
            'execution_log': {'path': str(log), **identity(log)}})
    require(identity(entry) == report['entry_identity'] and identity(supervisor) == report['supervisor_identity'] and identity(base_path) == report['original_supervision_identity'], 'Frozen sources changed')
    require(identity(__file__) == report['source_identity'], 'Independent control source changed')
    report['completed'] = True
    report['finished_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    target = out / 'R4E_CANONICAL_ENTRY_NEGATIVE_CONTROLS.json'
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'report': str(target), 'identity': identity(target), 'completed': True,
                      'actual_negative_controls': len(report['controls']), 'expensive_math_runs': 0}), flush=True)


if __name__ == '__main__':
    main()
