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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('worker_arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text())
    require(sha(__file__) == contract['supervisor_sha256'], 'supervisor identity differs')
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
    report = {'schema': 'razr-r4e-owned-pure-math-supervision-v1', 'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'contract_sha256': sha(args.contract), 'source_sha256': sha(__file__), 'command': command,
              'worker_started': False, 'completed': False, 'limits': contract, 'observations': [first],
              'resource_stop': None, 'worker_exit_code': None, 'missing_RSS_zero_substitutions': 0}
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
                        raise RuntimeError('still-running owned child RSS unavailable: '+type(exc).__name__+': '+str(exc)) from exc
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
