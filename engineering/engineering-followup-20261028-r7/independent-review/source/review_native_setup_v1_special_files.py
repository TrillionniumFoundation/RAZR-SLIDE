#!/usr/bin/env python3
"""Reproduce a source-member census gap with a labelled synthetic Git fixture."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import resource
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'r7-native/setup_fresh_s4_runtime_r7_v1.py'
OUT = ROOT / 'native-review-v1' / 'R7_NATIVE_SETUP_V1_IGNORED_FIFO_COUNTEREXAMPLE.json'


def ident(p):
    b = Path(p).read_bytes()
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}


def main():
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024**2, 128 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    assert not OUT.exists()
    source_identity = ident(SOURCE)
    spec = importlib.util.spec_from_file_location('synthetic_member_census_candidate', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    controls = []
    commands = []
    with tempfile.TemporaryDirectory(prefix='explicit-synthetic-git-fixture-', dir=ROOT) as tmp:
        base = Path(tmp)
        repo = base / 'repo'
        worktree = base / 'worktree'
        def git(*args, cwd=None):
            cmd = ['git', '-c', 'user.name=RAZR Synthetic Control',
                   '-c', 'user.email=control@example.invalid', *args]
            p = subprocess.run(cmd, cwd=cwd or base, capture_output=True, timeout=5)
            commands.append({'argv': cmd, 'returncode': p.returncode,
                'stdout_bytes': len(p.stdout), 'stderr': p.stderr.decode()})
            p.check_returncode()
            return p.stdout.decode().strip()
        git('init', str(repo))
        (repo / '.gitignore').write_text('ignored-*\n.venv\n')
        (repo / 'source.py').write_text('SYNTHETIC_FIXTURE_ONLY = True\n')
        git('add', '.gitignore', 'source.py', cwd=repo)
        git('commit', '-m', 'Explicit synthetic member census control, not project evidence', cwd=repo)
        commit = git('rev-parse', 'HEAD', cwd=repo)
        git('worktree', 'add', '--detach', str(worktree), commit, cwd=repo)
        expected = {p: ident(worktree / p) for p in ('.gitignore', 'source.py')}
        baseline = module.verify_checkout(worktree, expected, commit)
        controls.append({'name': 'two-source-real-Git-worktree-baseline',
            'expected_accept': True, 'actual_accept': True,
            'reported_actual_member_count': baseline['actual_member_count']})
        fifo = worktree / 'ignored-fifo'
        os.mkfifo(fifo)
        clean = git('status', '--porcelain', '--untracked-files=all', cwd=worktree)
        assert clean == ''
        rejected = False
        error = None
        result = None
        try:
            result = module.verify_checkout(worktree, expected, commit)
        except (ValueError, OSError) as exc:
            rejected = True
            error = str(exc)
        controls.append({'name': 'extra-gitignored-FIFO',
            'expected_accept': False, 'actual_accept': not rejected,
            'git_status_was_clean': True,
            'fifo_lstat_mode': fifo.lstat().st_mode,
            'reported_actual_member_count': result['actual_member_count'] if result else None,
            'reported_complete_member_set_equal': result['actual_complete_member_set_equal'] if result else None,
            'error': error})
        assert result is not None and not rejected, 'Expected V1 counterexample was not reproduced'
    assert ident(SOURCE) == source_identity
    report = {'schema': 'razr-r7-native-setup-v1-real-filesystem-counterexample-v1',
        'candidate_source': {'path': str(SOURCE), **source_identity},
        'controls': controls, 'synthetic_fixture_commands': commands,
        'candidate_pass': False, 'actual_counterexample_reproduced': True,
        'source_unchanged': True,
        'scope': 'Actual filesystem and actual tiny Git worktree controls using explicitly synthetic source and commit. No project source/Git object identity, scientific result or native geometry execution is substituted by this fixture.',
        'actual_native_runtime_or_CAD_executed': False,
        'elapsed_seconds': time.monotonic() - started,
        'max_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(report, indent=2) + '\n').encode()
    OUT.write_bytes(encoded)
    print(json.dumps({'report': str(OUT), 'bytes': len(encoded),
        'sha256': hashlib.sha256(encoded).hexdigest(), 'candidate_pass': False,
        'counterexample_reproduced': True}))


if __name__ == '__main__':
    main()
