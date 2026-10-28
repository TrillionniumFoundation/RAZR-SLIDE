"""Two independently executed negative controls for the new bound math entry.

No geometry or mathematical payload should start in either control. Original
artifacts are read only; each supervision/output path is new and owned here.
"""
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


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    root = Path(__file__).resolve().parents[1]
    out = Path(__file__).resolve().parent / 'entry-binding-controls'
    out.mkdir(exist_ok=False)
    base = root / 'R4E_SUPPORT_SUPERVISION_V2_OWNED.json'
    original_contract = root / 'R4E_SUPPORT_CONTRACT_V2.json'
    supervisor = root / 'supervise_owned_pure_math_r4e_v2.py'
    entry = root / 'run_owned_pure_math_r4e_v2.py'
    immutable = {str(p): identity(p) for p in (base, original_contract, supervisor, entry)}
    altered = json.loads(original_contract.read_text())
    altered['independent_negative_control_marker'] = 'actual-file-sha-must-be-rejected'
    wrong_contract = out / 'wrong-mathematical-contract.json'
    wrong_contract.write_text(json.dumps(altered, indent=2) + '\n')
    result = {
        'schema': 'razr-r4e-independent-new-entry-binding-negative-controls-v1',
        'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'source_identity': identity(__file__),
        'immutable_input_identities': immutable, 'controls': [], 'completed': False,
        'expensive_mathematical_worker_runs': 0,
        'original_mathematical_results_requalified_by_controls': False,
        'physical_or_native_semantic_qualification': False}
    for name in ('wrong_contract_sha', 'wrong_output_path'):
        case = out / name
        case.mkdir()
        contract = json.loads(base.read_text())
        watched = case / 'registered-worker-output'
        actual_output = watched if name == 'wrong_contract_sha' else case / 'incorrect-worker-output'
        actual_contract = wrong_contract if name == 'wrong_contract_sha' else original_contract
        contract.update(schema='razr-r4e-independent-negative-bound-entry-control-v1',
                        supervisor_sha256=identity(supervisor)['sha256'],
                        worker_entry=str(entry), worker_entry_sha256=identity(entry)['sha256'],
                        worker_output_directory=str(watched))
        frozen = case / 'supervision-contract.json'
        frozen.write_text(json.dumps(contract, indent=2) + '\n')
        original = root.parent / 'recovered-inputs/RAZR-R3E-COMPLETE-SCIENTIFIC-EVIDENCE-20261027'
        command = [sys.executable, '-I', '-S', '-B', str(supervisor), '--contract', str(frozen),
                   '--out', str(case / 'supervision'), '--', '--original', str(original),
                   '--contract', str(actual_contract), '--output', str(actual_output),
                   '--additional-producer', str(root / 'additional-bspline-v1/producer-attempt2/worker/report.json'),
                   '--additional-reader', str(root / 'additional-bspline-v1/reader/worker/report.json')]
        began = time.monotonic()
        completed = subprocess.run(command, capture_output=True, text=True)
        elapsed = time.monotonic() - began
        (case / 'parent.stdout.txt').write_text(completed.stdout)
        (case / 'parent.stderr.txt').write_text(completed.stderr)
        controller_path = case / 'supervision/controller.json'
        controller = json.loads(controller_path.read_text())
        execution_log = case / 'supervision/execution.log'
        log = execution_log.read_text()
        expected = ('actual mathematical contract differs from preregistered digest'
                    if name == 'wrong_contract_sha' else 'actual worker output differs from supervised directory')
        require(completed.returncode == 2 and controller['completed'] is False and controller['worker_exit_code'] != 0,
                'Negative control accepted or unexpected controller exit')
        require(expected in log, 'Wrong failure path in negative control')
        require(not watched.exists() and not actual_output.exists(), 'Mathematical worker output was created')
        require(not (case / 'supervision/entry-receipt.json').exists(), 'Payload-stage entry receipt unexpectedly written')
        require(controller['resource_stop'] is None and controller['owned_child_identity_verified'], 'Control failed for resource or ownership reason')
        require(controller['owned_channel_descriptors_closed'] and controller['source_and_contract_unchanged'], 'Negative control source/owned-resource cleanup failed')
        required_gate_keys = ('wall_seconds', 'RSS_limit_bytes', 'shared_ceiling_bytes', 'disk_floor_bytes', 'maximum_output_bytes', 'metadata_margin_bytes')
        original_supervision = json.loads(base.read_text())
        require(all(contract[k] == original_supervision[k] for k in required_gate_keys), 'A numeric gate was changed')
        result['controls'].append({'name': name, 'command': command, 'elapsed_seconds': elapsed,
            'parent_exit_code': completed.returncode, 'owned_entry_exit_code': controller['worker_exit_code'],
            'expected_rejection': expected, 'expected_rejection_observed': True,
            'original_numeric_gates_unchanged': True, 'mathematical_worker_output_absent': True,
            'entry_receipt_absent_before_payload_stage': True, 'owned_entry_handshake_verified': True,
            'descriptors_closed': True, 'controller': {'path': str(controller_path), **identity(controller_path)},
            'execution_log': {'path': str(execution_log), **identity(execution_log)},
            'contract': {'path': str(frozen), **identity(frozen)}})
        (out / 'R4E_ENTRY_BINDING_NEGATIVE_CONTROLS.json').write_text(json.dumps(result, indent=2) + '\n')
    require(all(identity(path) == expected for path, expected in immutable.items()), 'Frozen inputs changed')
    require(identity(__file__) == result['source_identity'], 'Control source changed')
    result['completed'] = True
    result['finished_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    report = out / 'R4E_ENTRY_BINDING_NEGATIVE_CONTROLS.json'
    report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'report': str(report), 'identity': identity(report), 'completed': True,
                      'actual_negative_controls': len(result['controls']), 'expensive_math_runs': 0}), flush=True)


if __name__ == '__main__':
    main()
