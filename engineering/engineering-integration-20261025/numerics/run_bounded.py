"""Run one coordinated numeric worker with measured memory, disk and time bounds."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import signal
import subprocess
import time


def available(path):
    status = os.statvfs(path)
    return status.f_bavail * status.f_frsize


def sample(pid, task_directory):
    payload_bytes = 0
    for path in task_directory.rglob('*'):
        try:
            if path.is_file():
                payload_bytes += path.stat().st_size
        except FileNotFoundError:
            # Atomic publication/removal may occur between directory listing
            # and stat; f_bavail remains the authoritative filesystem guard.
            continue
    result = {'monotonic': time.monotonic(), 'task_filesystem_available_bytes': available(task_directory),
              'task_payload_bytes': payload_bytes}
    base = Path('/sys/fs/cgroup')
    values = dict(row.split() for row in (base/'memory.stat').read_text().splitlines())
    result['cgroup_current_bytes'] = int((base/'memory.current').read_text())
    result['cgroup_anon_bytes'] = int(values.get('anon', 0))
    result['cgroup_shmem_bytes'] = int(values.get('shmem', 0))
    result['cgroup_file_bytes'] = int(values.get('file', 0))
    result['nonreclaimable_budget_bytes'] = sum(int(values.get(key, 0)) for key in
        ('anon', 'shmem', 'kernel_stack', 'pagetables', 'sock', 'slab_unreclaimable'))
    try:
        lines = Path('/proc')/str(pid)/'status'
        status = {row.split(':')[0]: row.split(':', 1)[1].strip() for row in lines.read_text().splitlines()}
        for name in ('VmRSS', 'VmHWM', 'VmSize'):
            result[name+'_bytes'] = int(status.get(name, '0 kB').split()[0]) * 1024
    except FileNotFoundError:
        pass
    return result


def main(args):
    command = args.command[1:] if args.command and args.command[0] == '--' else args.command
    if not command:
        raise ValueError('worker command required')
    task = args.task_directory.resolve()
    if not task.is_dir() or available(task) < 500*1024**2:
        raise ValueError('existing task directory and 500MiB filesystem reserve required')
    if args.report.exists() or args.log.exists():
        raise ValueError('new supervisor log/report paths required')
    start = time.monotonic()
    reason = None
    samples = []
    process = None
    error = None
    code = 1
    source_before = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    try:
        with args.log.open('x') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            while process.poll() is None:
                row = sample(process.pid, task)
                samples.append(row)
                if time.monotonic()-start > args.seconds:
                    reason = 'wall_time_limit'
                elif row['task_filesystem_available_bytes'] < 500*1024**2:
                    reason = '500MiB_task_filesystem_reserve'
                elif row['nonreclaimable_budget_bytes'] > 6.8*1024**3:
                    reason = '6.8GiB_shared_nonreclaimable_memory_budget'
                if reason:
                    break
                time.sleep(1)
    except BaseException as exc:
        reason = 'supervisor_failure'
        error = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        if process is not None:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
            code = process.wait()
        try:
            samples.append(sample(process.pid if process else 0, task))
        except Exception as exc:
            reason = reason or 'final_supervisor_sample_failure'
            error = error or {'type': type(exc).__name__, 'message': str(exc)}
    maximum = lambda key: max((row.get(key, 0) for row in samples), default=0)
    source_after = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if source_before != source_after:
        reason = reason or 'supervisor_source_changed'
    result = {'schema': 'razr-coordinated-numeric-supervisor-v1', 'command': command,
              'exit_code': code, 'resource_stop_reason': reason, 'seconds': time.monotonic()-start,
              'peak_worker_RSS_bytes': maximum('VmRSS_bytes'),
              'peak_worker_high_water_RSS_bytes': maximum('VmHWM_bytes'),
              'peak_worker_virtual_bytes': maximum('VmSize_bytes'),
              'sampled_peak_cgroup_current_bytes': maximum('cgroup_current_bytes'),
              'sampled_peak_cgroup_shmem_bytes': maximum('cgroup_shmem_bytes'),
              'sampled_peak_nonreclaimable_budget_bytes': maximum('nonreclaimable_budget_bytes'),
              'peak_task_payload_bytes': maximum('task_payload_bytes'), 'samples': samples,
              'minimum_filesystem_available_bytes': min((row['task_filesystem_available_bytes'] for row in samples), default=None),
              'file_cache_counted_separately_from_nonreclaimable_budget': True,
              'memory_budget_definition': 'anon + shmem + kernel_stack + pagetables + sock + slab_unreclaimable',
              'supervisor_source_sha256': source_before,
              'supervisor_source_sha256_after': source_after,
              'supervisor_source_unchanged': source_before == source_after,
              'supervisor_error': error,
              'log_sha256': hashlib.sha256(args.log.read_bytes()).hexdigest() if args.log.is_file() else None}
    with args.report.open('x') as output:
        output.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'samples'}))
    return (code if code > 0 else 128-code if code < 0 else 1) if reason else code


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task-directory', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=600)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    raise SystemExit(main(parser.parse_args()))
