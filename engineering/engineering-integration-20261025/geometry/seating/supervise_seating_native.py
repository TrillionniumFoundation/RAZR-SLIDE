"""Original SEATING bounds with v3 owned-child identity and frozen checkpoints.

The original v1 sources remain unchanged. The worker gets 1,740 seconds for
between-operator checks, leaving 60 seconds under the hard 1,800-second ceiling
to serialize an interrupted report. The append-only source/domain-bound pair
journal survives a hard in-kernel stop; a prefix never counts as completion.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import verify_seating_native as worker
import check_seating_checkpoint as reader
import owned_process


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def snapshot(path):
    values = {key: int(value) for key, value in
              (line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())}
    disk = os.statvfs(path)
    return {
        'f_bavail_bytes': disk.f_bavail * disk.f_frsize,
        'estimated_unreclaimable_bytes': values['anon'] + values.get('shmem', 0)
            + max(values.get('kernel', 0) - values.get('slab_reclaimable', 0), 0)
            + values.get('unevictable', 0),
    }


def process_memory(channel, child):
    return channel.sample(child)


def save(path, value):
    temporary = path.with_suffix('.writing')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


def terminate(child):
    if child.poll() is not None:
        return child.wait()
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        return child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return child.wait()


def main(argv=None):
    if Path(__file__).resolve() != worker.HERE/'supervise_seating_native.py':
        raise ValueError('executed v3 supervisor differs from its explicit source-bound path')
    if Path(owned_process.__file__).resolve() != worker.HERE/'owned_process.py':
        raise ValueError('executed owned-child helper differs from its source-bound path')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', type=Path, required=True)
    parser.add_argument('--expected-head', default=worker.DEFAULT_HEAD)
    parser.add_argument('--maximum-subdivision-depth', type=int, choices=range(4), default=3)
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--prepared-manifest', type=Path,
                        default=worker.HERE / 'prepared-v3/executed-source-manifest.json')
    parser.add_argument('--prepared-sha256', required=True)
    args = parser.parse_args(argv)
    output = args.output_directory.resolve()
    if output.exists() or not output.is_relative_to(Path('/tmp').resolve()):
        raise ValueError('a new private /tmp native output directory is required')
    head = subprocess.check_output(['git', '-C', str(worker.ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    if head != args.expected_head or len(head) != 40:
        raise ValueError('explicit frozen full repository HEAD required')
    if subprocess.check_output(['git', '-C', str(worker.ROOT), 'status', '--porcelain'], text=True).strip():
        raise ValueError('clean frozen repository required')
    output.mkdir(parents=True, exist_ok=False)
    sources = worker.adapter_identity()
    prepared_manifest = args.prepared_manifest.resolve()
    if sha(prepared_manifest) != args.prepared_sha256:
        raise ValueError('explicit prepared-v3 source manifest changed')
    expected_sources = {name: row['sha256'] for name, row in json.loads(prepared_manifest.read_text()).items()}
    if sources != expected_sources:
        raise ValueError('current worker sources differ from the independently reviewed prepared-v3 bytes')
    supervisor_sha = sha(__file__)
    initial = snapshot(output)
    environment_before = worker.postguard.check_environment.inspect_environment(worker.ROOT)
    state = {
        'schema': 'razr-seating-prepared-v3-owned-child-bounded-controller-v3',
        'expected_head': args.expected_head,
        'utc_started': dt.datetime.now(dt.timezone.utc).isoformat(),
        'worker_source_sha256_before': sources,
        'prepared_source_manifest_sha256': args.prepared_sha256,
        'supervisor_source': str(Path(__file__).resolve()), 'supervisor_sha256': supervisor_sha,
        'initial_resources': initial, 'worker_started': False, 'completed': False,
        'hard_wall_limit_seconds': 1800, 'worker_between_operator_limit_seconds': 1740,
        'worker_peak_RSS_limit_MiB': 1536, 'shared_unreclaimable_limit_GiB': 6.8,
        'startup_available_disk_MiB': 400, 'runtime_available_disk_reserve_MiB': 300,
        'startup_incremental_memory_reserve_MiB': 1536,
        'canonical_execution_checks_passed': False, 'whole_declared_seating_domain_clear': False,
        'complete_G2_qualification': False, 'candidate_go': False,
        'fixture_fabrication_go': False, 'manufacturing_go': False,
        'observations': [],
        'environment_before': environment_before,
        'owned_child_identity_verified': False,
    }
    target = output / 'controller.json'
    save(target, state)
    if not (environment_before.get('passed') is True and environment_before.get('checked_package_count') == 43):
        state.update(status='not_started_locked_environment_mismatch')
        save(target, state)
        return 3
    if initial['f_bavail_bytes'] < 400 * 2**20 or initial['estimated_unreclaimable_bytes'] + 1536 * 2**20 > 6.8 * 2**30:
        state.update(status='not_started_insufficient_resource_margin')
        save(target, state)
        return 3
    command = [str(worker.ROOT / '.venv/bin/python'), '-B', str(worker.HERE / 'verify_seating_native.py'),
               '--native', '--output', str(output / 'report.json'), '--expected-head', args.expected_head,
               '--seconds', '1740', '--minimum-available-disk-mib', '300', '--maximum-rss-mib', '1536',
               '--maximum-pair-calls', '20000', '--maximum-subdivision-depth', str(args.maximum_subdivision_depth)]
    state['command'] = command
    if args.preflight_only:
        state.update(status='preflight_only_worker_not_started')
        save(target, state)
        return 0
    copies = output / 'executed-source-bytes'; copies.mkdir()
    manifest = []
    for name, digest in sources.items():
        source, destination = worker.HERE / name, copies / name
        destination.write_bytes(source.read_bytes())
        if sha(destination) != digest or sha(source) != digest:
            raise ValueError('prepared worker source changed during archival copy')
        manifest.append({'source': str(source), 'copy': str(destination), 'sha256': digest})
    save(output / 'executed-source-manifest.json', {'sources': manifest,
         'controller_is_in_source_map': True, 'controller_sha256': supervisor_sha})
    environment = {**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
                   'MKL_NUM_THREADS': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
    started = last = time.monotonic(); reason = None
    supervision_exception = None
    child = channel = None
    code = None
    try:
        channel = owned_process.OwnedChildChannel(worker.HERE/'verify_seating_native.py')
        with (output / 'native.log').open('wb') as log:
            child = subprocess.Popen(command, cwd=worker.ROOT, env=channel.child_env(environment),
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                                     pass_fds=channel.pass_fds)
            state.update(worker_started=True, pid=child.pid)
            channel.after_spawn()
            save(target, state)

            def check_before_release(memory=None):
                nonlocal reason
                observed = {**snapshot(output), 'worker_memory': memory,
                            'phase': 'owned_child_identity_before_native_release',
                            'elapsed_seconds': time.monotonic()-started}
                if observed['elapsed_seconds'] > 1800:
                    reason = 'hard_wall_guard'
                elif observed['f_bavail_bytes'] < 300*2**20:
                    reason = 'ordinary_available_disk_guard'
                elif observed['estimated_unreclaimable_bytes'] > 6.8*2**30:
                    reason = 'shared_unreclaimable_memory_guard'
                elif memory is not None and max(memory.values()) > 1536*2**20:
                    reason = 'worker_peak_RSS_guard'
                if reason:
                    state['observations'].append(observed)
                    save(target, state)
                    raise RuntimeError('original resource guard rejected the owned-child release: '+reason)

            state['owned_child_identity'] = channel.accept(child, timeout_seconds=10,
                                                           poll_callback=check_before_release)
            state['owned_child_identity_verified'] = True
            save(target, state)
            while child.poll() is None:
                resources = snapshot(output)
                try:
                    memory = process_memory(channel, child)
                except owned_process.OwnedChildExited:
                    if child.poll() is None:
                        raise
                    break
                observed = {**resources, 'worker_memory': memory,
                            'elapsed_seconds': time.monotonic() - started}
                if observed['elapsed_seconds'] > 1800:
                    reason = 'hard_wall_guard'
                elif observed['f_bavail_bytes'] < 300 * 2**20:
                    reason = 'ordinary_available_disk_guard'
                elif observed['estimated_unreclaimable_bytes'] > 6.8 * 2**30:
                    reason = 'shared_unreclaimable_memory_guard'
                elif max(observed['worker_memory'].values()) > 1536 * 2**20:
                    reason = 'worker_peak_RSS_guard'
                if reason or time.monotonic() - last >= 15:
                    state['observations'].append(observed); save(target, state); last = time.monotonic()
                    print(json.dumps(observed), flush=True)
                if reason:
                    terminate(child)
                    break
                time.sleep(.5)
    except BaseException as exc:
        supervision_exception = {'type': type(exc).__name__, 'message': str(exc)}
        reason = reason or 'supervisor_exception_cleanup'
        if child is not None:
            terminate(child)
    finally:
        if child is not None:
            if child.poll() is None:
                terminate(child)
            code = child.wait()
        if channel is not None:
            channel.close()
    try:
        after = worker.adapter_identity()
    except Exception as exc:
        after = None
        state['postflight_source_identity_error'] = type(exc).__name__ + ': ' + str(exc)
    try:
        final_resources = snapshot(output)
    except Exception as exc:
        final_resources = {'telemetry_error': type(exc).__name__ + ': ' + str(exc)}
    state.update(worker_exit_code=code, elapsed_seconds=time.monotonic() - started,
                 resource_stop_reason=reason, worker_source_sha256_after=after,
                 worker_sources_unchanged=after == sources, supervisor_source_unchanged=sha(__file__) == supervisor_sha,
                 final_resources=final_resources, supervisor_exception=supervision_exception,
                 utc_finished=dt.datetime.now(dt.timezone.utc).isoformat())
    environment_after = worker.postguard.check_environment.inspect_environment(worker.ROOT)
    state['environment_after'] = environment_after
    state['locked_environment_unchanged'] = environment_after == environment_before and environment_after.get('passed') is True
    state['head_after'] = subprocess.check_output(['git', '-C', str(worker.ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    state['worktree_clean_after'] = not subprocess.check_output(['git', '-C', str(worker.ROOT), 'status', '--porcelain'], text=True).strip()
    path = output / 'report.json'
    if path.is_file():
        state['report_sha256'] = sha(path)
        try:
            report = json.loads(path.read_text())
            state['reported_complete_native_diagnostic_executed'] = report.get('complete_native_diagnostic_executed')
            state['reported_external_pair_domain_clear'] = report.get('whole_declared_seating_external_pair_domain_clear')
            readback = reader.check_report(path, args.expected_head)
            save(output / 'independent-readback.json', readback)
            state['independent_readback_completed'] = readback.get('complete_native_diagnostic_executed') is True
            state['independent_readback_sha256'] = sha(output / 'independent-readback.json')
        except Exception as exc:
            state['report_parse_failure'] = type(exc).__name__ + ': ' + str(exc)
    journal = output / 'pairs.jsonl'
    if journal.is_file():
        state['checkpoint_journal_sha256'] = sha(journal)
        try:
            prefix = reader.inspect_prefix(journal, args.expected_head)
            save(output / 'checkpoint-prefix-readback.json', prefix)
            state['checkpoint_preserved_pair_records'] = prefix['completed_pair_records']
            state['checkpoint_truncated_tail_bytes'] = prefix['truncated_tail_bytes']
            state['checkpoint_prefix_readback_sha256'] = sha(output / 'checkpoint-prefix-readback.json')
        except Exception as exc:
            state['checkpoint_prefix_readback_error'] = type(exc).__name__ + ': ' + str(exc)
    state['completed'] = bool(code == 0 and reason is None and after == sources
        and state['owned_child_identity_verified'] is True
        and state['supervisor_source_unchanged'] and state['worktree_clean_after']
        and state['head_after'] == args.expected_head
        and state['locked_environment_unchanged'] and state.get('independent_readback_completed') is True
        and state.get('reported_complete_native_diagnostic_executed') is True)
    save(target, state)
    print(json.dumps({k: state.get(k) for k in ('completed', 'worker_exit_code',
          'resource_stop_reason', 'reported_external_pair_domain_clear', 'elapsed_seconds')}), flush=True)
    return 0 if state['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
