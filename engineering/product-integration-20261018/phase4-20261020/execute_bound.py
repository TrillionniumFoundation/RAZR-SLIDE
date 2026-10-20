#!/usr/bin/env python3
"""Execute one bounded command while retaining source, logs and exit status."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--expected-head', required=True)
    ap.add_argument('--timeout', type=float, required=True)
    ap.add_argument('command', nargs=argparse.REMAINDER)
    args = ap.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    root, output = args.root.resolve(), args.output.resolve()
    if not command or output.exists() or output == root or root in output.parents:
        raise ValueError('new output outside source and a concrete command are required')
    def git(*words):
        return subprocess.check_output(['git', *words], cwd=root, text=True)
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    def utc():
        return dt.datetime.now(dt.timezone.utc).isoformat()
    before_head, before_status = git('rev-parse', 'HEAD').strip(), git('status', '--porcelain')
    if before_head != args.expected_head or before_status:
        raise ValueError('expected clean source commit is not checked out')
    inputs = {name: sha(root/name) for name in git('ls-files').splitlines()
              if (root/name).is_file() and not (root/name).is_symlink()}
    output.mkdir(parents=True)
    record = {'schema': 'razr-bound-command-execution-v1', 'started_utc': utc(),
        'source_commit': before_head, 'source_worktree_clean_before': not before_status,
        'source_inputs_sha256_before': inputs, 'command': command, 'cwd': str(root),
        'controller_source': {'path': str(Path(__file__).resolve()), 'sha256': sha(__file__)},
        'timeout_seconds': args.timeout, 'physical_execution_inferred': False,
        'candidate_go': False, 'manufacturing_go': False}
    (output/'started.json').write_text(json.dumps(record, indent=2)+'\n')
    clock = time.monotonic()
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'OMP_NUM_THREADS': '1',
           'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1'}
    log = output/'console.log'
    with log.open('w') as handle:
        try:
            result = subprocess.run(command, cwd=root, stdout=handle, stderr=subprocess.STDOUT,
                                    env=env, timeout=args.timeout)
            record['exit_code'] = result.returncode
            record['timed_out'] = False
        except subprocess.TimeoutExpired:
            record['exit_code'] = None
            record['timed_out'] = True
    after = {name: sha(root/name) if (root/name).is_file() else None for name in inputs}
    status = git('status', '--porcelain')
    record.update(finished_utc=utc(), seconds=time.monotonic()-clock,
        source_head_after=git('rev-parse', 'HEAD').strip(), source_worktree_clean_after=not status,
        source_inputs_sha256_after=after, source_bytes_unchanged=inputs == after,
        changed_sources=[name for name in inputs if inputs[name] != after[name]],
        log={'path': str(log), 'bytes': log.stat().st_size, 'sha256': sha(log)})
    record['execution_identity_preserved'] = (record['source_head_after'] == before_head and
                                             not status and record['source_bytes_unchanged'])
    (output/'execution.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({key: record[key] for key in ('source_commit', 'started_utc', 'finished_utc',
        'seconds', 'exit_code', 'timed_out', 'execution_identity_preserved')}, indent=2), flush=True)
    print('EXECUTION', output/'execution.json', flush=True)
    return 0 if record['exit_code'] == 0 and record['execution_identity_preserved'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
