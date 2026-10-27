"""L5 separate producer/native-reader supervisor: unchanged original SLIDE 1800 s /1536 MiB/resource guards."""
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
from run_l5 import identity, owned_process, S4, SOURCES


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
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode',choices=('producer','reader'),required=True)
    parser.add_argument('--scope',choices=('original','current'),required=True)
    parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--producer',type=Path)
    parser.add_argument('--k1-near',type=Path)
    parser.add_argument('--k1-far',type=Path)
    args = parser.parse_args(argv)
    out = args.output.resolve()
    if out.exists() or out.is_relative_to(identity.ROOT):
        raise ValueError('new output outside repository required')
    out.mkdir(parents=True)
    wall, rss, startup_memory = (1800, 1536, 1536)
    source = HERE/('run_l5.py' if args.mode=='producer' else 'read_l5_native.py')
    command = [str(identity.ROOT/'.venv/bin/python'),'-B',str(source),'--output',str(out/'worker'),
               '--inputs',str(args.inputs.resolve())]
    if args.mode=='producer':
        command.extend(['--scope',args.scope])
        if args.scope=='current':
            if args.k1_near is None or args.k1_far is None:raise ValueError('actual dual K1 materials required')
            command.extend(['--k1-near',str(args.k1_near.resolve()),'--k1-far',str(args.k1_far.resolve())])
    else:
        if args.producer is None:raise ValueError('actual producer science required')
        command.extend(['--producer',str(args.producer.resolve())])
    own_sources = {str(Path(path).resolve()): identity.sha(path)
                   for path in (__file__, *(HERE/n for n in SOURCES), identity.__file__, owned_process.__file__)}
    receipt = {'schema': 'razr-L5-owned-worker-supervisor-20261026-v1',
               'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
               'scope': args.scope, 'worker_mode':args.mode, 'command': command, 'source_sha256_before': own_sources,
               'original_L1_resource_limits_unchanged': True,
               'worker_started': False, 'completed': False,
               'owned_child_identity_verified': False, 'procfs_visible_PID_used_for_signals': False,
               'limits': {'wall_seconds': wall, 'worker_peak_RSS_MiB': rss,
                          'shared_unreclaimable_GiB': 6.8, 'runtime_disk_reserve_MiB': 100,
                          'startup_disk_reserve_MiB': 200, 'startup_additional_memory_MiB': startup_memory},
               'resource_observations': []}
    def save():
        identity.atomic_json(out/'controller.json', receipt)
    first = resources(out)
    receipt['resource_observations'].append(first)
    save()
    if (first['available_disk_bytes'] < 200*2**20
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
    result_path = out/'worker/science'/('report.json' if args.mode=='producer' else 'NATIVE_READBACK.json')
    if result_path.is_file():
        receipt['result_sha256'] = identity.sha(result_path)
        result = json.loads(result_path.read_text())
        receipt['reported_execution_completed'] = result.get('execution_completed')
        receipt['all_original_postguards_passed'] = result.get('all_original_postguards_passed')
    unchanged = all(identity.sha(path) == digest for path, digest in own_sources.items())
    receipt.update(source_bytes_unchanged=unchanged, elapsed_seconds=time.monotonic()-started,
                   finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                   locked_environment_unchanged=identity.environment() == environment)
    receipt['completed'] = bool(not receipt.get('failure') and not reason and receipt.get('worker_exit_code') == 0
                                and receipt.get('reported_execution_completed') is True and receipt.get('all_original_postguards_passed') is True and unchanged
                                and receipt['locked_environment_unchanged']
                                and receipt['owned_child_identity_verified']
                                and receipt.get('owned_channel_descriptors_closed') is True)
    save()
    print(json.dumps({key: receipt.get(key) for key in ('completed', 'worker_exit_code', 'all_original_postguards_passed',
                                                     'failure', 'elapsed_seconds')}), flush=True)
    return 0 if receipt['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
