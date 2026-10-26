"""K3 external owned supervisor; preliminary complete factory and independent STEP readback each keep 1200 s / 1536 MiB finite guards. Original 90 s positive-only KEY reader is not used or claimed."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
from f1_common import identity, owned_process, S4


def resources(path):
    stats = dict((key, int(value)) for key, value in
                 (line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines()))
    disk = os.statvfs(path)
    return {'available_disk_bytes': disk.f_bavail*disk.f_frsize,
            'shared_unreclaimable_bytes': stats.get('anon', 0)+stats.get('shmem', 0)
                + max(0, stats.get('kernel', 0)-stats.get('slab_reclaimable', 0))+stats.get('unevictable', 0)}


def terminate_group(child):
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=('factory', 'readback'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose', choices=('stow_tabs_3','predock'), required=True)
    parser.add_argument('--k1-near', type=Path, required=True)
    parser.add_argument('--k1-far', type=Path, required=True)
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--k1-contract', type=Path, required=True)
    args = parser.parse_args(argv)
    out = args.output.resolve()
    if out.exists() or out.is_relative_to(identity.ROOT):
        raise ValueError('new output outside repository required')
    if args.mode == 'readback' and args.report is None:
        raise ValueError('readback requires a report')
    out.mkdir(parents=True)
    native = args.mode == 'factory'
    wall, rss, startup_memory = (1200, 1536, 2048)
    source = HERE/('full_factory_stop_pilot.py' if native else 'read_stop_pilot.py')
    command = [str(identity.ROOT/'.venv/bin/python'), '-B', str(source)]
    command += ['--pose', args.pose, '--output', str(out/'worker')]
    command += ['--k1-near', str(args.k1_near.resolve()), '--k1-far', str(args.k1_far.resolve()), '--binding', str(args.binding.resolve())]
    command += ['--contract', str(args.contract.resolve()), '--k1-contract', str(args.k1_contract.resolve())]
    if not native:
        command += ['--factory-report', str(args.report.resolve())]
    own_sources = {str(Path(path).resolve()): identity.sha(path)
                   for path in (__file__, source, HERE/'f1_common.py', HERE/'frozen_key_factory_adapter.py', HERE/'k3_pilot_states.py', HERE/'k3_pilot_common.py', HERE/'panel_key_travel_stops_v1.py', HERE/'independent_stop_checks.py', args.contract, args.k1_contract, args.binding, identity.__file__, owned_process.__file__)}
    receipt = {'schema': 'razr-K3-owned-finite-supervisor-20261026-v1',
               'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
               'mode': args.mode, 'command': command, 'source_sha256_before': own_sources,
               'original_v4_execution_claimed': False, 'original_KEY_90_second_reader_used': False,
               'new_complete_STEP_readback_budget_justification': '154 whole STEP imports, independent panel reconstruction, oriented contact/functional faces and 153 changed-panel pairs fit the unchanged full finite guard; no larger guard or full 11781-pair qualification is claimed',
               'worker_started': False, 'completed': False,
               'owned_child_identity_verified': False, 'procfs_visible_PID_used_for_signals': False,
               'limits': {'wall_seconds': wall, 'worker_peak_RSS_MiB': rss,
                          'shared_unreclaimable_GiB': 6.8, 'runtime_disk_reserve_MiB': 100,
                          'startup_disk_reserve_MiB': 256, 'startup_additional_memory_MiB': startup_memory},
               'resource_observations': []}
    def save():
        identity.atomic_json(out/'controller.json', receipt)
    first = resources(out)
    receipt['resource_observations'].append(first)
    save()
    if (first['available_disk_bytes'] < 256*2**20
            or first['shared_unreclaimable_bytes']+startup_memory*2**20 > 6.8*2**30):
        receipt['resource_start_refused'] = True
        save()
        return 3
    environment = identity.environment()
    receipt['locked_environment'] = environment
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'OPENBLAS_NUM_THREADS': '1',
           'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1'}
    child = channel = None
    started = recorded = time.monotonic()
    reason = None
    def observe(memory=None):
        nonlocal reason, recorded
        now = resources(out)
        elapsed = time.monotonic()-started
        if elapsed > wall:
            reason = 'hard wall budget exceeded'
        elif now['available_disk_bytes'] < 100*2**20:
            reason = 'ordinary-user disk reserve below 100 MiB'
        elif now['shared_unreclaimable_bytes'] > 6.8*2**30:
            reason = 'shared estimated unreclaimable memory exceeded 6.8 GiB'
        elif memory is not None and max(memory.values()) > rss*2**20:
            reason = 'owned worker RSS exceeded '+str(rss)+' MiB'
        if reason or time.monotonic()-recorded >= 10:
            receipt['resource_observations'].append({**now, 'elapsed_seconds': elapsed, 'worker_memory': memory})
            recorded = time.monotonic()
            save()
        if reason:
            receipt['capacity_or_wall_stop'] = reason
            raise RuntimeError(reason)
    try:
        channel = owned_process.OwnedChildChannel(source)
        with (out/'native.log').open('wb') as log:
            child = subprocess.Popen(command, cwd=identity.ROOT, env=channel.child_env(env),
                                     stdout=log, stderr=subprocess.STDOUT,
                                     start_new_session=True, pass_fds=channel.pass_fds)
            receipt.update(worker_started=True, worker_pid=child.pid)
            channel.after_spawn()
            save()
            receipt['owned_child_handshake'] = channel.accept(child, timeout_seconds=10, poll_callback=observe)
            receipt['owned_child_identity_verified'] = True
            save()
            while child.poll() is None:
                try:
                    memory = channel.sample(child)
                except owned_process.OwnedChildExited:
                    if child.poll() is not None:
                        break
                    raise
                observe(memory)
                time.sleep(1)
            receipt['worker_exit_code'] = child.wait()
    except BaseException as exc:
        if child is not None:
            terminate_group(child)
            receipt['worker_exit_code'] = child.returncode
        receipt['failure'] = type(exc).__name__+': '+str(exc)
    finally:
        if channel is not None:
            channel.close()
            receipt['owned_channel_descriptors_closed'] = not channel.descriptors
    result_path = out/'worker/report.json'
    if result_path.is_file():
        receipt['result_sha256'] = identity.sha(result_path)
        result = json.loads(result_path.read_text())
        receipt['reported_execution_completed'] = result.get('execution_completed')
        receipt['finite_trial_clear'] = result.get('finite_pose_clear')
        receipt['pilot_clear'] = result.get('pilot_clear')
    unchanged = all(identity.sha(path) == digest for path, digest in own_sources.items())
    receipt.update(source_bytes_unchanged=unchanged, elapsed_seconds=time.monotonic()-started,
                   finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                   locked_environment_unchanged=identity.environment() == environment)
    receipt['completed'] = bool(not receipt.get('failure') and not reason and receipt.get('worker_exit_code') == 0
                                and receipt.get('reported_execution_completed') is True and unchanged
                                and receipt['locked_environment_unchanged']
                                and receipt['owned_child_identity_verified']
                                and receipt.get('owned_channel_descriptors_closed') is True)
    save()
    print(json.dumps({key: receipt.get(key) for key in ('completed', 'worker_exit_code', 'finite_trial_clear',
                                                     'failure', 'elapsed_seconds')}), flush=True)
    return 0 if receipt['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
