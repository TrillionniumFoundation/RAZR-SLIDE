"""Run or strictly resume reviewed finite KEY trials, one original budget each.

Each selected trial is independent. Completed raw data may be reused only after
fresh source/lock/baseline and complete-pair postchecks. No partial/stdout-only
trial is resumable. Positive native Common remains a penetrating placement.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time


def resources(folder):
    stat = os.statvfs(folder)
    disk = stat.f_bavail*stat.f_frsize
    info = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    host_available = int(info['MemAvailable'].split()[0])*1024
    maximum = Path('/sys/fs/cgroup/memory.max')
    current = Path('/sys/fs/cgroup/memory.current')
    cap = maximum.read_text().strip() if maximum.exists() else 'max'
    stats = Path('/sys/fs/cgroup/memory.stat')
    values = dict(line.split() for line in stats.read_text().splitlines()) if stats.exists() else {}
    # Clean inactive file cache is reclaimable; tmpfs/shmem is not counted.
    inactive = max(0, int(values.get('inactive_file', 0))-int(values.get('file_dirty', 0))
                   -int(values.get('file_writeback', 0)))
    current_bytes = int(current.read_text()) if current.exists() else 0
    hard_headroom = int(cap)-current_bytes if cap != 'max' else host_available
    memory = min(host_available, hard_headroom+inactive)
    clean_file = max(0, int(values.get('file', 0))-int(values.get('shmem', 0))
                     -int(values.get('file_dirty', 0))-int(values.get('file_writeback', 0)))
    return {'writeable_disk_bytes': disk, 'effective_memory_headroom_bytes': memory,
            'root_reserved_free_bytes_diagnostic_only': stat.f_bfree*stat.f_frsize,
            'shared_unreclaimable_memory_bytes': max(0, current_bytes-clean_file),
            'cgroup_unused_bytes': hard_headroom, 'clean_inactive_file_cache_bytes': inactive,
            'uid': os.geteuid(), 'host_MemAvailable_bytes': host_available}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stop(process, deadline):
    if process.poll() is not None:
        return
    grace = max(0., min(1., deadline-time.monotonic()))
    try:
        os.killpg(process.pid, signal.SIGTERM if grace else signal.SIGKILL)
    except ProcessLookupError:
        process.wait(timeout=1.)
        return
    try:
        process.wait(timeout=grace if grace else 1.)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=1.)


def run(command, log, environment, deadline, *, root, output, on_started=None):
    start = time.perf_counter()
    event = None
    if time.monotonic() >= deadline:
        raise ValueError('shared 1200-second trial budget exhausted before command')
    with Path(log).open('x') as stream:
        process = subprocess.Popen(command, cwd=root, env=environment,
            stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            if on_started is not None:
                on_started(process.pid)
            while True:
                available = resources(output)
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    event = {'kind': 'shared_trial_timeout', 'resources': available}
                    stop(process, deadline)
                    code = 124
                    break
                if (available['writeable_disk_bytes'] < 100*1024**2
                        or available['shared_unreclaimable_memory_bytes'] > int(6.8*1024**3)):
                    event = {'kind': 'shared_runtime_resource_budget', 'resources': available}
                    stop(process, deadline)
                    code = 125
                    break
                try:
                    code = process.wait(timeout=min(2., remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
        except BaseException:
            stop(process, deadline)
            raise
    return {'argv': command, 'exit_code': code, 'seconds': time.perf_counter()-start,
            'stop_event': event, 'log': str(Path(log).resolve()), 'log_sha256': sha(log)}


def load_probe(folder):
    spec = importlib.util.spec_from_file_location('reviewed_endpoint_worker',
                                                 folder/'integration/probe_key_endpoint_extension.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def existing_bundle(folder):
    folder = Path(folder).resolve(strict=True)
    paths = [path for path in (folder/'report.json', folder/'native/report.json') if path.is_file()]
    if len(paths) != 1 or paths[0].is_symlink():
        raise ValueError('resume directory must contain exactly one original raw report')
    return paths[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--stow-report', type=Path, required=True)
    parser.add_argument('--open-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--trials', nargs='+', required=True)
    parser.add_argument('--resume-from', nargs='*', type=Path, default=[],
                        help='original completed single-trial directories; never partial or stdout-only data')
    args = parser.parse_args(argv)
    root, output = args.root.resolve(), args.output.resolve()
    source, folder = Path(__file__).resolve(), Path(__file__).resolve().parent
    expected = args.expected_head
    if (output.exists() or output.is_relative_to(root) or source.is_relative_to(root)
            or len(expected) != 40 or any(c not in '0123456789abcdef' for c in expected)):
        raise ValueError('new scratch output and full expected HEAD required')
    probe = load_probe(folder)
    labels = probe.selected_trials(args.trials)
    uv = shutil.which('uv')
    if uv is None:
        raise ValueError('installed uv launcher required')
    source_before = probe.study_source_snapshot(folder)
    baseline_paths = {'STOW': args.stow_report.resolve(strict=True), 'OPEN': args.open_report.resolve(strict=True)}
    baseline_hashes = {pose: sha(path) for pose, path in baseline_paths.items()}
    resume_paths = {}
    for directory in args.resume_from:
        path = existing_bundle(directory)
        value = json.loads(path.read_text())
        label = value.get('trial_label')
        if label not in labels or label in resume_paths:
            raise ValueError('resume inputs duplicate a trial or name an unrequested trial')
        resume_paths[label] = path
    output.mkdir(parents=True)
    executed = output/'executed-study-sources'
    for name, digest in source_before.items():
        target = executed/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(folder/name, target)
        if sha(target) != digest:
            raise ValueError('copied reviewed study source changed')
    record = {'schema': 'razr-local-KEY-single-trial-supervisor-v2', 'expected_head': expected,
              'requested_trials': labels, 'study_source_sha256_before': source_before,
              'baseline_reports': {pose: {'path': str(path), 'sha256': baseline_hashes[pose]}
                                   for pose, path in baseline_paths.items()},
              'common_per_trial_budget_seconds': 1200,
              'preflight_limits': {'writeable_disk_bytes': 256*1024**2,
                                   'effective_memory_headroom_bytes': 2*1024**3},
              'runtime_limits': {'minimum_writeable_disk_bytes': 100*1024**2,
                                 'maximum_shared_unreclaimable_memory_bytes': int(6.8*1024**3)},
              'trials': [], 'all_requested_trials_validated': False,
              'all_six_trials_validated': False, 'canonical_execution_claimed': False,
              'hosted_Actions_execution_claimed': False, 'physical_qualification': False,
              'complete_product_motion_proved': False, 'continuous_backlash_domain_proved': False,
              'global_KEY_hard_stop_proved': False}
    def save():
        probe.atomic_json(output/'runner-report.json', record)
    save()
    sys.path[:0] = [str(folder/'tools'), str(root/'tools')]
    try:
        import validate_product_nominal_report as guard
        import key_endpoint_resume as resume
        for label in labels:
            job = {'trial_label': label, 'commands': [], 'validated': False,
                   'native_executed_this_invocation': False, 'reused_completed_raw_bundle': False}
            record['trials'].append(job)
            save()
            available = resources(output)
            job['resource_preflight'] = available
            if (available['writeable_disk_bytes'] < 256*1024**2
                    or available['effective_memory_headroom_bytes'] < 2*1024**3):
                raise ValueError('original resource preflight not satisfied for '+label)
            deadline = time.monotonic()+1200.
            before = guard.current_identity(root, expected)
            job['identity_before'] = before
            if probe.study_source_snapshot(folder) != source_before:
                raise ValueError('reviewed study bytes changed before '+label)
            pose = probe.trial_input(label)['pose']
            baseline_path = baseline_paths[pose]
            if sha(baseline_path) != baseline_hashes[pose]:
                raise ValueError('original canonical baseline bytes changed')
            trial_folder = output/label
            trial_folder.mkdir()
            with tempfile.TemporaryDirectory(prefix='razr-key-trial-', dir='/tmp') as temporary:
                tmp = Path(temporary)
                environment = {**os.environ, 'TMPDIR': str(tmp), 'UV_CACHE_DIR': str(tmp/'uv-cache'),
                    'PYTHONDONTWRITEBYTECODE': '1', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
                    'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1'}
                job['environment_overrides'] = {key: environment[key] for key in (
                    'TMPDIR', 'UV_CACHE_DIR', 'PYTHONDONTWRITEBYTECODE', 'OPENBLAS_NUM_THREADS',
                    'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')}
                prefix = [uv, 'run', '--locked', 'python', '-B']
                def command(argv, log_name, on_started=None):
                    result = run(argv, trial_folder/log_name, environment, deadline, root=root, output=output,
                                 on_started=on_started)
                    job['commands'].append(result)
                    save()
                    if result['exit_code']:
                        raise ValueError(log_name+' returned '+str(result['exit_code']))
                    return result
                command(prefix+['tools/check_environment.py', '--output', str(trial_folder/'environment.json')],
                        'environment.log')
                command(prefix+['tools/validate_product_nominal_report.py', '--root', str(root),
                                '--report', str(baseline_path), '--pose', pose, '--expected-head', expected],
                        'baseline-postguard.log')
                if label in resume_paths:
                    raw_path = resume_paths[label]
                    job['reuse_requested_original_report'] = {'path': str(raw_path), 'sha256': sha(raw_path)}
                else:
                    raw_path = trial_folder/'native/report.json'
                    def native_started(pid):
                        job['native_executed_this_invocation'] = True
                        job['actual_native_worker_pid'] = pid
                        save()
                    command(prefix+[str(folder/'integration/probe_key_endpoint_extension.py'),
                        '--root', str(root), '--expected-head', expected, '--trial', label,
                        '--control-report', str(baseline_path), '--output', str(raw_path.parent)],
                        'native.log', native_started)
                command(prefix+[str(folder/'tools/key_endpoint_resume.py'), '--report', str(raw_path),
                    '--baseline', str(baseline_path), '--root', str(root), '--study-root', str(folder),
                    '--expected-head', expected, '--expected-label', label], 'trial-postguard.log')
                if time.monotonic() >= deadline:
                    raise ValueError('shared 1200-second trial budget exhausted before final identity check')
                after = guard.current_identity(root, expected)
                source_after = probe.study_source_snapshot(folder)
                if (before != after or source_before != source_after
                        or sha(baseline_path) != baseline_hashes[pose]):
                    raise ValueError('repository/study/runtime/baseline changed during trial')
                raw_digest = sha(raw_path)
                raw = json.loads(raw_path.read_text())
                summary = resume.validate_completed_trial(raw, expected_head=expected,
                    expected_label=label, current_identity=after, expected_study_sources=source_after,
                    baseline_report=json.loads(baseline_path.read_text()), baseline_path=baseline_path,
                    report_directory=raw_path.parent)
                if (time.monotonic() >= deadline or sha(raw_path) != raw_digest
                        or guard.current_identity(root, expected) != after
                        or probe.study_source_snapshot(folder) != source_after
                        or sha(baseline_path) != baseline_hashes[pose]):
                    raise ValueError('raw/source/baseline changed or common deadline expired during final readback')
                if label in resume_paths and raw_digest != job['reuse_requested_original_report']['sha256']:
                    raise ValueError('resume source changed while it was being checked')
                job.update(identity_after=after, study_source_sha256_after=source_after,
                    native_report={'path': str(raw_path), 'sha256': raw_digest}, independent_trial_postcheck=summary,
                    validated=True, reused_completed_raw_bundle=label in resume_paths,
                    original_native_seconds=raw['seconds'], finite_trial_material_clear=raw['finite_trial_material_clear'],
                    actual_native_changed_pairs=len(raw['actual_native_changed_pairs']),
                    retained_actual_positive_pairs=len(raw['positive_actual_Common']))
            save()
            print(json.dumps({key: job[key] for key in (
                'trial_label', 'validated', 'native_executed_this_invocation', 'reused_completed_raw_bundle',
                'actual_native_changed_pairs', 'retained_actual_positive_pairs', 'finite_trial_material_clear')}), flush=True)
        record['all_requested_trials_validated'] = (len(record['trials']) == len(labels)
            and all(job['validated'] for job in record['trials']))
        record['all_six_trials_validated'] = record['all_requested_trials_validated'] and labels == list(probe.TRIAL_LABELS)
        record['study_source_sha256_after'] = probe.study_source_snapshot(folder)
        if record['study_source_sha256_after'] != source_before:
            raise ValueError('study source changed after final trial')
    except BaseException as exc:
        record['execution_failure'] = type(exc).__name__+': '+str(exc)
        record['all_requested_trials_validated'] = False
        record['all_six_trials_validated'] = False
    save()
    print(json.dumps({key: record.get(key) for key in (
        'all_requested_trials_validated', 'all_six_trials_validated', 'execution_failure')}), flush=True)
    return 0 if record['all_requested_trials_validated'] else 2


if __name__ == '__main__':
    raise SystemExit(main())

