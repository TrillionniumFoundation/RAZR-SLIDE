"""K4 external owned local-section supervisor. The exact original finite native guards and owned child lifecycle are retained; only arguments, evidence identity and a stricter output bound are added."""
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
    parser.add_argument('--mode', required=True, choices=('producer', 'readback'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--sources-sha256', required=True)
    parser.add_argument('--producer', type=Path)
    args = parser.parse_args(argv)
    out = args.output.resolve()
    if out.exists() or out.is_relative_to(identity.ROOT):
        raise ValueError('new output outside repository required')
    if args.mode == 'readback' and args.producer is None:
        raise ValueError('readback requires a report')
    out.mkdir(parents=True)
    native = args.mode == 'producer'
    wall, rss, startup_memory = (1200, 1536, 2048)
    source = HERE/'k4_worker.py'
    command = [str(identity.ROOT/'.venv/bin/python'), '-B', str(source), '--mode', args.mode,
               '--output', str(out/'worker'), '--inputs', str(args.inputs.resolve()),
               '--sources', str(args.sources.resolve()), '--sources-sha256', args.sources_sha256]
    if not native:
        command += ['--producer', str(args.producer.resolve())]
    if identity.sha(args.sources) != args.sources_sha256:
        raise ValueError('frozen source manifest changed')
    bundle=json.loads(args.sources.read_text())
    own_sources = {str(Path(path).resolve()): identity.sha(path)
                   for path in [args.sources, identity.__file__, owned_process.__file__]+
                   [HERE/name for name in bundle['runtime_sources']]+
                   [HERE.parent/name for name in ('service-launch.py','host-cap.py','python-downloads.json')]}
    for name, ref in bundle['runtime_sources'].items():
        if own_sources[str((HERE/name).resolve())] != ref['sha256'] or (HERE/name).stat().st_size != ref['bytes']:
            raise ValueError('frozen runtime source differs')
    receipt = {'schema': 'razr-K4-owned-finite-supervisor-20261027-v1',
               'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
               'mode': args.mode, 'command': command, 'source_sha256_before': own_sources,
               'original_v4_execution_claimed': False, 'original_KEY_90_second_reader_used': False,
               'new_complete_STEP_readback_budget_justification': 'K4 uses three original whole STEP imports, 12 finite windows and 2 negative controls. Producer 38 and reader at most 190 Booleans retain the original 1200 s / 1536 MiB finite guard. The capacity contract is preregistration, not a measured K4 pass.',
               'worker_started': False, 'completed': False,
               'owned_child_identity_verified': False, 'procfs_visible_PID_used_for_signals': False,
               'limits': {'wall_seconds': wall, 'worker_peak_RSS_MiB': rss,
                          'shared_unreclaimable_GiB': 6.8, 'runtime_disk_reserve_MiB': 100,
                          'startup_disk_reserve_MiB': 256, 'startup_additional_memory_MiB': startup_memory},
               'additional_output_limits': {'worker_directory_MiB':160,'scientific_directory_MiB':128,'single_worker_file_MiB':16},
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
        if sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) > 160*2**20:
            reason = 'additional bounded worker output exceeded 160 MiB'
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
        receipt['local_material_targets_all_matched'] = result.get('local_material_targets_all_matched')
        receipt['all_probes_evaluated'] = result.get('all_probes_evaluated')
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
    print(json.dumps({key: receipt.get(key) for key in ('completed', 'worker_exit_code', 'local_material_targets_all_matched',
                                                     'failure', 'elapsed_seconds')}), flush=True)
    return 0 if receipt['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
