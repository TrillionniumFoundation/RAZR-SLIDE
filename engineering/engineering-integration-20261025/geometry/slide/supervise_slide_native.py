"""Explicitly start one bounded scratch SLIDE run; never retries automatically."""
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

import verify_slide_native as worker
import owned_process


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
    worker.evidence.require(Path(__file__).resolve() == worker.HERE/'supervise_slide_native.py',
                            'executed supervisor differs from its explicit source-bound path')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-head', default=worker.DEFAULT_HEAD)
    parser.add_argument('--maximum-subdivision-depth', type=int, default=2, choices=range(4))
    args = parser.parse_args(argv)
    folder = args.output.resolve()
    worker.evidence.require(not folder.exists() and not folder.is_relative_to(worker.ROOT),
                            'new private native output outside frozen repository required')
    head = subprocess.check_output(['git', '-C', str(worker.ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    worker.evidence.require(head == args.expected_head and len(head) == 40, 'exact expected current HEAD required')
    worker.evidence.require(not subprocess.check_output(['git', '-C', str(worker.ROOT), 'status', '--porcelain'], text=True).strip(),
                            'clean frozen repository required')
    folder.mkdir(parents=True)
    sources = worker.source_identity()
    first = worker.resource_snapshot(folder)
    receipt = {'schema': 'razr-scratch-slide-bounded-controller-r3', 'expected_head': args.expected_head,
               'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
               'scratch_source_sha256_before': sources, 'worker_started': False,
               'resource_observations': [first], 'hard_wall_limit_seconds': 1800,
               'worker_peak_RSS_limit_MiB': 1536, 'shared_unreclaimable_limit_GiB': 6.8,
               'ordinary_disk_reserve_MiB': 100, 'startup_ordinary_disk_reserve_MiB': 200,
               'startup_estimated_additional_memory_reserve_MiB': 1536,
               'owned_child_identity_verified': False,
               'worker_RSS_sampler': 'nonce-bound owned procfs PID with per-sample identity checks',
               'procfs_visible_PID_used_for_signals': False,
               'hosted_execution': False, **{key: False for key in worker.evidence.FALSE_FLAGS}}

    def save():
        worker.atomic_json(folder/'controller.json', receipt)

    save()
    if (first['f_bavail_bytes'] < 200*2**20
            or first['estimated_unreclaimable_bytes']+1536*2**20 > 6.8*2**30):
        receipt.update(resource_start_refused=True, completed=False)
        save()
        return 3
    copy_dir = folder/'executed-source-bytes'
    copy_dir.mkdir()
    copies = []
    for index, (path, digest) in enumerate(sorted(sources.items())):
        source = Path(path)
        destination = copy_dir/(str(index).zfill(2)+'-'+source.name)
        destination.write_bytes(source.read_bytes())
        worker.evidence.require(worker.sha(destination) == digest and worker.sha(source) == digest,
                                'source changed while freezing executed bytes')
        copies.append({'source': path, 'copy': str(destination.relative_to(folder)), 'sha256': digest})
    worker.atomic_json(folder/'executed-source-manifest.json', {'sources': copies})
    command = [str(worker.ROOT/'.venv/bin/python'), '-B', str(worker.HERE/'verify_slide_native.py'),
               '--native', '--expected-head', args.expected_head, '--output', str(folder/'report.json'),
               '--maximum-subdivision-depth', str(args.maximum_subdivision_depth)]
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'OPENBLAS_NUM_THREADS': '1',
           'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1'}
    receipt.update(command=command, working_directory=str(worker.ROOT))
    started = time.monotonic(); recorded = started; reason = None
    child = None; channel = None

    def handshake_budget(memory=None):
        nonlocal reason, recorded
        now = worker.resource_snapshot(folder)
        elapsed = time.monotonic()-started
        if elapsed > 1800:
            reason = 'hard 1800-second wall budget exceeded'
        elif now['f_bavail_bytes'] < 100*2**20:
            reason = 'ordinary-user runtime disk reserve below 100 MiB'
        elif now['estimated_unreclaimable_bytes'] > 6.8*2**30:
            reason = 'shared estimated unreclaimable memory exceeded 6.8 GiB'
        elif memory is not None and max(memory.values()) > 1536*2**20:
            reason = 'worker observed peak RSS exceeded 1536 MiB'
        if reason or memory is not None or time.monotonic()-recorded >= 10:
            receipt['resource_observations'].append({**now, 'elapsed_seconds': elapsed,
                'worker_memory': memory, 'phase': 'before_verified_child_release'})
            recorded = time.monotonic(); save()
        if reason:
            receipt['capacity_or_wall_stop'] = reason
            raise RuntimeError(reason)

    try:
        channel = owned_process.OwnedChildChannel(worker.HERE/'verify_slide_native.py')
        with (folder/'native.log').open('wb') as log:
            child = subprocess.Popen(command, cwd=worker.ROOT, env=channel.child_env(env), stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True,
                                     pass_fds=channel.pass_fds)
            receipt.update(worker_started=True, worker_pid=child.pid)
            channel.after_spawn()
            save()
            receipt['owned_child_handshake'] = channel.accept(
                child, timeout_seconds=10, poll_callback=handshake_budget)
            receipt['owned_child_identity_verified'] = True
            save()
            while child.poll() is None:
                now = worker.resource_snapshot(folder)
                try:
                    memory = channel.sample(child)
                except owned_process.OwnedChildExited:
                    if child.poll() is not None:
                        receipt['worker_exit_observed_during_memory_sample'] = True
                        break
                    raise
                sample = {**now, 'elapsed_seconds': time.monotonic()-started, 'worker_memory': memory}
                if sample['elapsed_seconds'] > 1800:
                    reason = 'hard 1800-second wall budget exceeded'
                elif now['f_bavail_bytes'] < 100*2**20:
                    reason = 'ordinary-user runtime disk reserve below 100 MiB'
                elif now['estimated_unreclaimable_bytes'] > 6.8*2**30:
                    reason = 'shared estimated unreclaimable memory exceeded 6.8 GiB'
                elif max(memory.values()) > 1536*2**20:
                    reason = 'worker observed peak RSS exceeded 1536 MiB'
                if reason or time.monotonic()-recorded >= 10:
                    receipt['resource_observations'].append(sample); recorded = time.monotonic(); save()
                if reason:
                    terminate_group(child)
                    break
                time.sleep(1)
            exit_code = child.wait()
    except BaseException as exc:
        if child is not None:
            terminate_group(child)
            receipt['worker_exit_code'] = child.returncode
        receipt.update(completed=False, execution_failure=type(exc).__name__+': '+str(exc))
        # A failed disk write must not mask the original exception after the
        # owned process has been stopped and reaped. The prior receipt stays
        # incomplete if even this best-effort failure record cannot be saved.
        try:
            save()
        except BaseException:
            pass
        raise
    finally:
        pending_exception = sys.exc_info()[0] is not None
        if channel is not None:
            try:
                channel.close()
                receipt['owned_channel_descriptors_closed'] = not channel.descriptors
            except BaseException as exc:
                receipt['owned_channel_close_failure'] = type(exc).__name__+': '+str(exc)
                if not pending_exception:
                    raise
    after = worker.source_identity()
    receipt.update(worker_exit_code=exit_code, elapsed_seconds=time.monotonic()-started,
                   scratch_source_sha256_after=after, scratch_sources_unchanged=after == sources,
                   finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                   head_after=subprocess.check_output(['git', '-C', str(worker.ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
                   worktree_clean_after=not subprocess.check_output(['git', '-C', str(worker.ROOT), 'status', '--porcelain'], text=True).strip())
    if reason:
        receipt.update(capacity_or_wall_stop=reason,
                       last_complete_checkpoint_is_partial_diagnostic_only=True)
    report_path = folder/'report.json'
    if report_path.is_file():
        receipt['report_sha256'] = worker.sha(report_path)
        try:
            report = json.loads(report_path.read_text())
            receipt['reported_complete_native_diagnostic_executed'] = report.get('complete_native_diagnostic_executed')
            receipt['reported_external_pair_domain_clear'] = report.get('whole_declared_slide_external_pair_domain_clear')
        except Exception as exc:
            receipt['report_parse_failure'] = type(exc).__name__+': '+str(exc)
    # Persisted prefixes retain partial observations; only the complete
    # publication chain plus the independent raw reader can qualify completion.
    completed_readback = False
    try:
        import check_slide_checkpoint as checkpoint_reader
        if (folder/'pairs.jsonl').is_file():
            receipt['checkpoint_prefix'] = checkpoint_reader.inspect_prefix(
                folder/'pairs.jsonl', args.expected_head)
        if not reason and exit_code == 0 and receipt.get('reported_complete_native_diagnostic_executed') is True:
            checked = checkpoint_reader.check_report(report_path, args.expected_head)
            receipt['independent_completed_readback'] = checked
            completed_readback = (checked.get('complete_native_diagnostic_executed') is True
                                  and checked.get('checkpoint_publication_chain_verified') is True)
    except Exception as exc:
        receipt['checkpoint_readback_failure'] = type(exc).__name__+': '+str(exc)
    after_readback = worker.source_identity()
    receipt['scratch_source_sha256_after_independent_readback'] = after_readback
    receipt['scratch_sources_unchanged'] = after_readback == after == sources
    receipt['completed'] = bool(not reason and exit_code == 0 and receipt.get('reported_complete_native_diagnostic_executed') is True
                                and completed_readback and receipt['scratch_sources_unchanged']
                                and receipt['owned_child_identity_verified']
                                and receipt.get('owned_channel_descriptors_closed') is True
                                and receipt['head_after'] == args.expected_head
                                and receipt['worktree_clean_after'])
    receipt['resource_observations'].append(worker.resource_snapshot(folder)); save()
    print(json.dumps({key: receipt.get(key) for key in ('completed', 'worker_exit_code', 'elapsed_seconds',
          'capacity_or_wall_stop', 'reported_external_pair_domain_clear')}), flush=True)
    return 0 if receipt['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
