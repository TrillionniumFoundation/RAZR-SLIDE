"""Owned local R3 geometry worker under the original CAD capacity limits.

This is a new narrow submaterial experiment, not a full-scene execution. All
signals target the process group created by this supervisor's Popen handle.
"""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import signal
import subprocess
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resources(path):
    stats = dict((k, int(v)) for k, v in (line.split()
                 for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines()))
    disk = os.statvfs(path)
    return {'disk_available_bytes': disk.f_bavail * disk.f_frsize,
            'shared_unreclaimable_bytes': stats['anon'] + stats['shmem']
                + max(stats['kernel'] - stats['slab_reclaimable'], 0) + stats.get('unevictable', 0)}


def rss(pid):
    try:
        for line in Path('/proc', str(pid), 'status').read_text().splitlines():
            if line.startswith('VmRSS:'):
                return int(line.split()[1]) * 1024
    except FileNotFoundError:
        return 0
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--contract', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    contract = json.loads(Path(args.contract).read_text())
    if sha(__file__) != contract['supervisor_sha256']:
        raise ValueError('supervisor source differs')
    out = Path(args.out)
    out.mkdir(exist_ok=False)
    limits = contract['resource_limits']
    first = resources(out)
    started = time.monotonic()
    report = {'schema': 'RAZR-R3-owned-native-submaterial-supervision-v1',
              'contract_sha256': sha(args.contract), 'supervisor_sha256': sha(__file__),
              'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'worker_started': False, 'resource_stop': None, 'exit_code': None,
              'command': args.command, 'samples': [{'elapsed': 0, **first}],
              'original_CAD_capacity_numbers_retained': True, 'limits': limits,
              'new_complete_factory_or_all_pair_execution_claimed': False,
              'process_group_created_and_owned_by_this_supervisor': True}

    def save():
        (out / 'controller.json').write_text(json.dumps(report, indent=2) + '\n')

    if first['disk_available_bytes'] < limits['startup_disk_floor_bytes']:
        report['resource_stop'] = 'startup_disk'
    elif first['shared_unreclaimable_bytes'] + limits['startup_extra_shared_bytes'] > limits['shared_limit_bytes']:
        report['resource_stop'] = 'startup_shared'
    save()
    if not report['resource_stop']:
        env = dict(os.environ)
        env.update(PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
                   MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
        with (out / 'native.log').open('wb') as log:
            child = subprocess.Popen(args.command, stdout=log, stderr=subprocess.STDOUT,
                                     env=env, start_new_session=True)
            report['worker_started'] = True
            report['worker_pid'] = child.pid
            save()
            while child.poll() is None:
                sample = {'elapsed': time.monotonic() - started, **resources(out),
                          'worker_RSS_bytes': rss(child.pid)}
                report['samples'].append(sample)
                if sample['elapsed'] > limits['wall_seconds']:
                    report['resource_stop'] = 'wall_seconds'
                elif sample['worker_RSS_bytes'] > limits['worker_RSS_limit_bytes']:
                    report['resource_stop'] = 'worker_RSS'
                elif sample['shared_unreclaimable_bytes'] > limits['shared_limit_bytes']:
                    report['resource_stop'] = 'shared_memory'
                elif sample['disk_available_bytes'] < limits['runtime_disk_floor_bytes']:
                    report['resource_stop'] = 'runtime_disk'
                if report['resource_stop']:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait()
                    break
                time.sleep(0.2)
            report['exit_code'] = child.wait()
    report['finished_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    report['seconds'] = time.monotonic() - started
    report['final_resources'] = resources(out)
    report['supervisor_source_unchanged'] = sha(__file__) == contract['supervisor_sha256']
    report['completed'] = report['exit_code'] == 0 and report['resource_stop'] is None
    save()
    print(json.dumps({k: report[k] for k in ('worker_started', 'exit_code', 'resource_stop',
                                           'seconds', 'completed')}), flush=True)
    return 0 if report['completed'] else 3 if not report['worker_started'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
