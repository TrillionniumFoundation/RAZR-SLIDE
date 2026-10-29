"""Owned PID-namespace-aware pure mathematics supervisor; original gates retained.

No missing RSS is recorded as zero. A sampling exception is classified as
termination only after the original Popen handle confirms child termination.
An unobservable still-running child is a monitoring failure and is stopped.
"""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def resources(path):
    stats = {k: int(v) for k, v in (line.split() for line in
             Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())}
    disk = os.statvfs(path)
    return {'disk_available_bytes': disk.f_bavail * disk.f_frsize,
            'shared_unreclaimable_bytes': stats['anon'] + stats['shmem'] +
                max(stats['kernel'] - stats['slab_reclaimable'], 0) + stats.get('unevictable', 0)}


SAMPLING_INTERVAL_SECONDS = 0.2
EXIT_CONFIRMATION_POLICY = {
    'schema': 'razr-r7-completed-entry-owned-exit-confirmation-v1',
    'maximum_additional_seconds': SAMPLING_INTERVAL_SECONDS,
    'maximum_attempts': 1,
    'allowed_sampling_exception': 'exact KeyError VmRSS or VmHWM only',
    'completed_entry_required_before_wait': True,
    'same_Popen_and_handshake_identity_required': True,
    'all_original_resource_gates_rechecked': True,
    'missing_RSS_zero_substitution_allowed': False,
}


def confirm_completed_entry_exit(exc, child, channel, contract, contract_path,
                                 receipt_path, worker_arguments, report, started,
                                 observe):
    """A single bounded exit confirmation for an already-completed bound entry.

    A missing RSS observation is preserved as missing. The receipt is not exit
    evidence: only this exact original Popen.wait result may confirm termination.
    All other sampling errors, incomplete entries and still-live children fail.
    """
    detected = time.monotonic()
    require(type(exc) is KeyError and exc.args in (('VmRSS',), ('VmHWM',)),
            'sampling error is not an eligible missing memory field')
    require(contract.get('completed_entry_exit_confirmation_policy') == EXIT_CONFIRMATION_POLICY,
            'explicit exact completed-entry exit policy required')
    require(report.get('bounded_exit_confirmation_count', 0) == 0,
            'at most one completed-entry exit confirmation is allowed')
    report['bounded_exit_confirmation_count'] = 1
    evidence = {'type': type(exc).__name__, 'message': str(exc),
                'original_Popen_pid': child.pid,
                'memory_observation_fabricated': False,
                'actual_memory_observation': None,
                'original_Popen_confirmed_exit_code': None,
                'completed': False}
    report['bounded_exit_confirmation'] = evidence
    observe()
    require(report.get('owned_child_identity_verified') is True and
            channel.child_pid == child.pid and channel.binding is not None and
            channel.packet is not None and
            report['owned_child_handshake']['packet'] == channel.packet and
            report['owned_child_handshake']['verified_binding'] == channel.binding,
            'the original verified owned Popen handshake is required')
    receipt_path = Path(receipt_path)
    require(not receipt_path.is_symlink() and receipt_path.is_file() and
            0 < receipt_path.stat().st_size <= 65536,
            'a bounded regular entry receipt must already exist')
    receipt_sha = sha(receipt_path)
    entry_report = json.loads(receipt_path.read_text())
    require(entry_report.get('schema') == 'razr-r7-owned-pure-math-entry-v1-identity-receipt' and
            entry_report.get('worker_started') is True and
            entry_report.get('completed') is True and
            type(entry_report.get('worker_exit_code')) is int and
            entry_report['worker_exit_code'] == 0 and
            entry_report.get('native_geometry_imported') is False and
            entry_report.get('entry_and_worker_and_owned_source_unchanged') is True and
            entry_report.get('owned_execution_identity_unchanged') is True and
            entry_report.get('supervision_contract_unchanged') is True,
            'the same bound entry must have completed successfully before confirmation')
    peak = entry_report.get('peak_RSS_bytes')
    require(type(peak) is int and 0 < peak <= contract['RSS_limit_bytes'],
            'a positive in-limit original worker peak RSS is required')
    expected_identity = {k: v for k, v in channel.packet.items()
                         if k not in ('kind', 'nonce', 'source_sha256')}
    require(entry_report.get('owned_execution_identity') == expected_identity and
            entry_report.get('owned_execution_nonce') == channel.nonce and
            expected_identity['os_getpid'] == child.pid,
            'entry receipt is not bound to this Popen PID/starttime/namespace/nonce')
    require(entry_report.get('supervision_contract_sha256') == report['contract_sha256'] == sha(contract_path),
            'supervision contract receipt or current bytes differ')
    entry = Path(contract['worker_entry'])
    owned_path = Path(contract['owned_process']['path'])
    worker = Path(contract['worker']['path'])
    require(sha(__file__) == contract['supervisor_sha256'] and
            sha(entry) == contract['worker_entry_sha256'] == channel.source_sha256 and
            sha(owned_path) == contract['owned_process']['sha256'] and
            sha(worker) == contract['worker']['sha256'],
            'actual supervisor, entry, owned or worker source changed')
    actual_args = worker_arguments[1:] if worker_arguments[:1] == ['--'] else worker_arguments
    options = contract['canonical_worker_options']
    require(type(options) is list and options and len(options) == len(set(options)) and
            len(actual_args) == 2 * len(options), 'exact registered worker arguments required')
    values = dict(zip(actual_args[::2], actual_args[1::2]))
    require(len(values) == len(options) and set(values) == set(options),
            'complete unique original worker options required')
    canonical = [item for option in options for item in (option, values[option])]
    math_contract = Path(values['--contract']).resolve()
    expected_bindings = {
        'worker_output_directory': str(Path(values['--output']).resolve()),
        'mathematical_contract_path': str(math_contract),
        'mathematical_contract_sha256': contract['registered_math_contract_sha256'],
    }
    require(entry_report.get('canonical_worker_arguments') == canonical and
            entry_report.get('actual_argument_bindings') == expected_bindings and
            Path(expected_bindings['worker_output_directory']) == Path(contract['worker_output_directory']).resolve() and
            sha(math_contract) == contract['registered_math_contract_sha256'],
            'actual same-run mathematical contract, arguments or output binding differs')
    require(sha(receipt_path) == receipt_sha, 'entry receipt changed during validation')
    observe()
    remaining_interval = SAMPLING_INTERVAL_SECONDS - (time.monotonic() - detected)
    remaining_wall = contract['wall_seconds'] - (time.monotonic() - started)
    wait_budget = min(remaining_interval, remaining_wall)
    require(wait_budget > 0, 'no original sample interval or wall budget remains')
    evidence.update(entry_receipt_sha256=receipt_sha, original_entry_peak_RSS_bytes=peak,
                    verified_owned_execution_identity=expected_identity,
                    allowed_wait_seconds=wait_budget,
                    elapsed_before_wait_seconds=time.monotonic() - detected)
    try:
        code = child.wait(timeout=wait_budget)
    except subprocess.TimeoutExpired as timeout:
        evidence['actual_elapsed_seconds'] = time.monotonic() - detected
        evidence['child_still_running_after_bound'] = child.poll() is None
        raise RuntimeError('completed entry did not actually exit within the one original sampling interval') from timeout
    evidence['original_Popen_confirmed_exit_code'] = code
    evidence['waited_exit_elapsed_seconds'] = time.monotonic() - detected
    observe()
    require(sha(receipt_path) == receipt_sha and sha(contract_path) == report['contract_sha256'] and
            sha(__file__) == contract['supervisor_sha256'] and
            sha(math_contract) == contract['registered_math_contract_sha256'] and
            sha(entry) == contract['worker_entry_sha256'] and
            sha(worker) == contract['worker']['sha256'] and
            sha(owned_path) == contract['owned_process']['sha256'],
            'completed entry receipt, source or contract changed during confirmation')
    require(code == 0, 'owned completed entry subsequently exited nonzero')
    observe()
    evidence['actual_elapsed_seconds'] = time.monotonic() - detected
    require(evidence['actual_elapsed_seconds'] <= SAMPLING_INTERVAL_SECONDS,
            'actual exit confirmation including all validation exceeded one original sampling interval')
    require(time.monotonic() - started <= contract['wall_seconds'],
            'actual final exit confirmation exceeded the original wall limit')
    evidence['completed'] = True
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('worker_arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text())
    require(sha(__file__) == contract['supervisor_sha256'], 'supervisor identity differs')
    require(contract.get('completed_entry_exit_confirmation_policy') == EXIT_CONFIRMATION_POLICY,
            'exact explicit completed-entry policy required')
    owned_path = Path(contract['owned_process']['path'])
    require(sha(owned_path) == contract['owned_process']['sha256'], 'owned process identity differs')
    entry = Path(contract['worker_entry'])
    require(sha(entry) == contract['worker_entry_sha256'], 'entry source identity differs')
    spec = importlib.util.spec_from_file_location('r4e_frozen_owned_parent', owned_path)
    owned = importlib.util.module_from_spec(spec); spec.loader.exec_module(owned)
    args.out.mkdir(parents=True, exist_ok=False)
    first = resources(args.out)
    started = time.monotonic()
    command = [sys.executable, '-I', '-S', '-B', str(entry), '--supervision-contract',
               str(args.contract.resolve()), '--receipt', str(args.out/'entry-receipt.json'),
               *args.worker_arguments]
    report = {'schema': 'razr-r7-owned-pure-math-supervision-v1-completed-entry-exit', 'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'contract_sha256': sha(args.contract), 'source_sha256': sha(__file__), 'command': command,
              'worker_started': False, 'completed': False, 'limits': contract, 'observations': [first],
              'resource_stop': None, 'worker_exit_code': None, 'missing_RSS_zero_substitutions': 0, 'bounded_exit_confirmation_count': 0,
              'completed_entry_exit_confirmation_policy': EXIT_CONFIRMATION_POLICY}
    def save():
        (args.out/'controller.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    if first['disk_available_bytes'] < contract['disk_floor_bytes'] + contract['maximum_output_bytes'] + contract['metadata_margin_bytes']:
        report['resource_stop'] = 'startup_disk'
    elif first['shared_unreclaimable_bytes'] + contract['RSS_limit_bytes'] > contract['shared_ceiling_bytes']:
        report['resource_stop'] = 'startup_shared'
    child = None; channel = None; last = started
    output = Path(contract['worker_output_directory'])
    def observe(memory=None):
        nonlocal last
        sample = resources(args.out); sample['elapsed_seconds'] = time.monotonic() - started
        sample['owned_worker_memory'] = memory
        sample['actual_output_bytes'] = sum(p.stat().st_size for p in output.rglob('*') if p.is_file()) if output.exists() else 0
        if sample['elapsed_seconds'] > contract['wall_seconds']:
            report['resource_stop'] = 'wall_seconds'
        elif sample['disk_available_bytes'] < contract['disk_floor_bytes']:
            report['resource_stop'] = 'runtime_disk'
        elif sample['shared_unreclaimable_bytes'] > contract['shared_ceiling_bytes']:
            report['resource_stop'] = 'shared'
        elif memory is not None and max(memory.values()) > contract['RSS_limit_bytes']:
            report['resource_stop'] = 'worker_RSS'
        elif sample['actual_output_bytes'] > contract['maximum_output_bytes']:
            report['resource_stop'] = 'output_bytes'
        if report['resource_stop'] or time.monotonic() - last >= 1:
            report['observations'].append(sample); last = time.monotonic(); save()
        if report['resource_stop']:
            raise RuntimeError(report['resource_stop'])
    try:
        if report['resource_stop']:
            raise RuntimeError(report['resource_stop'])
        channel = owned.OwnedChildChannel(entry)
        environment = dict(os.environ); environment.update(PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
        with (args.out/'execution.log').open('wb') as log:
            child = subprocess.Popen(command, env=channel.child_env(environment), stdout=log, stderr=subprocess.STDOUT,
                                     start_new_session=True, pass_fds=channel.pass_fds)
            report['worker_started'] = True; channel.after_spawn(); save()
            report['owned_child_handshake'] = channel.accept(child, timeout_seconds=10, poll_callback=observe)
            report['owned_child_identity_verified'] = True; save()
            while child.poll() is None:
                try:
                    memory = channel.sample(child)
                except (owned.OwnedChildExited, OSError, KeyError, ValueError) as exc:
                    confirmed_code = child.poll()
                    if confirmed_code is None:
                        confirmed_code = confirm_completed_entry_exit(
                            exc, child, channel, contract, args.contract, args.out/'entry-receipt.json',
                            args.worker_arguments, report, started, observe)
                    report['termination_during_sample'] = {'type': type(exc).__name__, 'message': str(exc),
                                                           'original_Popen_confirmed_exit_code': confirmed_code,
                                                           'memory_observation_fabricated': False}
                    break
                observe(memory); time.sleep(0.2)
            report['worker_exit_code'] = child.wait()
            observe()
    except BaseException as exc:
        report['failure'] = {'type': type(exc).__name__, 'message': str(exc)}
        if child is not None:
            if child.poll() is None:
                try: os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                try: child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL); child.wait()
            report['worker_exit_code'] = child.returncode
    finally:
        if channel is not None:
            channel.close(); report['owned_channel_descriptors_closed'] = not channel.descriptors
    receipt = args.out/'entry-receipt.json'
    report['entry_completed'] = json.loads(receipt.read_text()).get('completed', False) if receipt.exists() else False
    report['source_and_contract_unchanged'] = sha(__file__) == contract['supervisor_sha256'] and sha(args.contract) == report['contract_sha256'] and sha(owned_path) == contract['owned_process']['sha256']
    report['completed'] = bool(report['worker_exit_code'] == 0 and report['entry_completed'] and not report['resource_stop'] and
        not report.get('failure') and report.get('owned_child_identity_verified') and report.get('owned_channel_descriptors_closed') and report['source_and_contract_unchanged'])
    report['elapsed_seconds'] = time.monotonic() - started; report['finished_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    report['final_resources'] = resources(args.out); save()
    print(json.dumps({k: report.get(k) for k in ['completed', 'worker_exit_code', 'failure', 'resource_stop', 'elapsed_seconds']}), flush=True)
    return 0 if report['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
