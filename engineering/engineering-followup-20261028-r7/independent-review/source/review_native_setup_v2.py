#!/usr/bin/env python3
"""Cross-author byte, source-census and setup-capacity review; no installer or CAD."""
from pathlib import Path
import ast
import datetime as dt
import hashlib
import importlib.util
import json
import os
import resource
import shutil
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
NATIVE = BASE / 'r7-native'
REPO = BASE / 'razr-current'
S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
OUTPUT = ROOT / 'native-setup-v2-review' / 'R7_NATIVE_SETUP_V2_INDEPENDENT_REVIEW.json'


def ident(p):
    raw = Path(p).read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2, 256 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    assert not OUTPUT.exists()
    setup = NATIVE / 'setup_fresh_s4_runtime_r7_v2.py'
    registrar = NATIVE / 'register_local_setup_r7_v2.py'
    qualifier = NATIVE / 'qualify_fresh_runtime_r7_v1.py'
    contract_path = NATIVE / 'R7_SETUP_ASSESS_ONLY_CONTRACT_V2.json'
    c = json.loads(contract_path.read_bytes())
    watched = {p: ident(p) for p in (setup, registrar, qualifier, contract_path)}
    assert watched[setup]['sha256'] == 'ed4a5179048172ff312f9cf595ed9c86d5176ec7cfaa5d64c21930d0a1f06902'
    assert watched[registrar]['sha256'] == 'fc51a248c43d69fa2e4bac933a230ba781ef2124aa94861e3772d2dda00c6a3d'
    assert watched[qualifier]['sha256'] == 'a1b14b6586893339f245ba04363ea0dd210c2fea8c86fdfeaa82ed10eb19d1fb'
    assert c['setup_source_identity'] == watched[setup]
    assert c['stage'] == 'assess_only' and c['qualification_or_CAD_allowed_by_this_contract'] is False
    for row in c['bound_inputs']:
        p = Path(row['path'])
        assert ident(p) == row['identity']
        watched[p] = row['identity']
    template = json.loads((REPO / 'engineering/engineering-followup-20261028-r5/cloud-native-v1/R5_CLOUD_NATIVE_SCIENCE_TEMPLATE.json').read_bytes())
    assert c['original_six_limits'] == template['original_resource_limits']
    assert c['original_six_limits'] == {'wall_seconds': 1200, 'worker_RSS_limit_bytes': 1610612736,
        'shared_limit_bytes': 7301444403, 'startup_disk_floor_bytes': 268435456,
        'startup_extra_shared_bytes': 2147483648, 'runtime_disk_floor_bytes': 104857600}
    capacity_keys = ('original_postinstall_available_floor', 'source_checkout_reserve', 'pinned_uv_tool_reserve',
                    'new_venv_reserve', 'metadata_reserve', 'installer_transient_reserve')
    assert sum(c['capacity_basis'][k] for k in capacity_keys) == c['conservative_preinstall_reserve_bytes'] == 7968830419
    assert c['capacity_basis']['original_postinstall_available_floor'] == 4294967296
    code = setup.read_text()
    assert "wheel['size'] + sum(x.file_size for x in members) <= 201326592" in code
    assert "seen == names" in code and "actual == names" in code
    assert "name not in seen and name in names" in code
    assert "set(actual) == set(expected) | {'.git'}" in code
    assert "stat.S_ISDIR(root.lstat().st_mode)" in code
    assert "stat.S_ISREG(p.lstat().st_mode)" in code
    assert "report['postinstall_resources']['ordinary_available_bytes'] >= 4 * 2**30" in code
    assert 'GITHUB_' not in code and 'GITHUB_' not in registrar.read_text()
    python_version = subprocess.check_output([c['python_executable'], '--version'], text=True, timeout=5).strip()
    assert python_version == 'Python 3.12.14'

    expected = c['expected_sources']
    assert len(expected) == 973
    paths = sorted(expected)
    env = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    cmd = ['git', '--no-lazy-fetch', '-c', 'core.packedGitWindowSize=1m', '-c', 'core.packedGitLimit=8m', 'cat-file', '--batch']
    p = subprocess.run(cmd, input=''.join(S4 + ':' + p + '\n' for p in paths).encode(),
                       cwd=REPO, env=env, capture_output=True, timeout=30, check=True)
    offset = 0
    source_bytes = 0
    for name in paths:
        end = p.stdout.index(b'\n', offset)
        sha, kind, n = p.stdout[offset:end].decode().split()
        n = int(n)
        raw = p.stdout[end + 1:end + 1 + n]
        assert kind == 'blob' and len(raw) == n and p.stdout[end + 1 + n:end + 2 + n] == b'\n'
        assert hashlib.sha1(('blob ' + str(n) + '\0').encode() + raw).hexdigest() == sha
        assert {'bytes': n, 'sha256': hashlib.sha256(raw).hexdigest()} == expected[name]
        offset = end + 2 + n
        source_bytes += n
    assert offset == len(p.stdout) and source_bytes == 11150469

    spec = importlib.util.spec_from_file_location('reviewed_setup_only_helpers', setup)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    controls = []
    with tempfile.TemporaryDirectory(prefix='explicit-synthetic-v2-census-', dir=ROOT) as tmp:
        base = Path(tmp)
        repo, worktree = base / 'repo', base / 'worktree'
        def git(*args, cwd=None):
            return subprocess.check_output(['git', '-c', 'user.name=RAZR Synthetic Control',
                '-c', 'user.email=control@example.invalid', *args], cwd=cwd or base,
                stderr=subprocess.DEVNULL, timeout=5).decode().strip()
        git('init', str(repo))
        (repo / '.gitignore').write_text('ignored-*\n.venv\n')
        (repo / 'source.py').write_text('SYNTHETIC_FIXTURE_ONLY = True\n')
        git('add', '.gitignore', 'source.py', cwd=repo)
        git('commit', '-m', 'Explicit synthetic member census control, not project evidence', cwd=repo)
        commit = git('rev-parse', 'HEAD', cwd=repo)
        git('worktree', 'add', '--detach', str(worktree), commit, cwd=repo)
        fixture_expected = {n: ident(worktree / n) for n in ('.gitignore', 'source.py')}
        def check(name, accepted):
            assert git('status', '--porcelain', '--untracked-files=all', cwd=worktree) == ''
            actual, error = True, None
            try:
                module.verify_checkout(worktree, fixture_expected, commit)
            except (ValueError, OSError) as exc:
                actual, error = False, str(exc)
            controls.append({'name': name, 'expected_accept': accepted, 'actual_accept': actual, 'error': error})
            assert actual is accepted, name
        check('real-Git-baseline', True)
        x = worktree / 'ignored-fifo'; os.mkfifo(x); check('original-V1-ignored-FIFO-counterexample', False); x.unlink()
        x = worktree / 'ignored-socket'; sock = socket.socket(socket.AF_UNIX); sock.bind(str(x)); sock.close(); check('ignored-socket', False); x.unlink()
        x = worktree / 'ignored-file'; x.write_bytes(b'extra'); check('ignored-extra-regular-file', False); x.unlink()
        x = worktree / 'ignored-symlink'; x.symlink_to(worktree / 'source.py'); check('ignored-symlink-file', False); x.unlink()
        x = worktree / 'ignored-linkdir'; x.symlink_to(repo, target_is_directory=True); check('ignored-symlink-directory', False); x.unlink()
        x = worktree / '.venv'; x.symlink_to(repo, target_is_directory=True); check('root-runtime-symlink-directory', False); x.unlink()
        x = worktree / '.venv'; os.mkfifo(x); check('root-runtime-FIFO', False); x.unlink()
        x = worktree / '.venv'; x.mkdir(); (x / 'runtime.bin').write_bytes(b'explicit runtime exclusion'); check('real-root-runtime-directory-pruned', True); shutil.rmtree(x)
        x = worktree / 'ignored-nested/.venv'; x.mkdir(parents=True); (x / 'unbound.bin').write_bytes(b'x'); check('nested-runtime-name-not-pruned', False); shutil.rmtree(x.parent)
    assert all(ident(p) == identity for p, identity in watched.items())
    assessment_path = NATIVE / 'setup-assess_only-v2/R7_FRESH_LOCAL_RUNTIME_SETUP_ACTUAL_V1.json'
    assessment = json.loads(assessment_path.read_bytes())
    assert assessment['completed'] and assessment['stage'] == 'assess_only'
    assert assessment['native_execution_claimed'] is False and assessment['runtime_qualified'] is False
    report = {
        'schema': 'razr-r7-native-setup-v2-independent-review-v1',
        'recorded_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'review_pass': True, 'review_scope': 'Setup source, exact S4 input closure, original resource gates and actual synthetic member-census controls. Installer/native stage has not been executed by this reviewer.',
        'reviewed_sources': [{'path': str(p.relative_to(BASE)), **i} for p, i in watched.items()],
        'source_before_after_unchanged': True,
        'exact_S4_source_count': len(expected), 'exact_S4_source_bytes_independently_read': source_bytes,
        'real_S4_Git_blob_bytes_equal': True, 'expected_actual_members_after_new_real_worktree': 974,
        'actual_new_project_worktree_created_by_reviewer': False,
        'python_version': python_version, 'conservative_preinstall_reserve_bytes': c['conservative_preinstall_reserve_bytes'],
        'original_six_resource_limits': c['original_six_limits'],
        'original_postinstall_4GiB_gate_preserved': True,
        'retained_uv_wheel_plus_payload_fits_tool_reserve_required': True,
        'complete_uv_ZIP_RECORD_member_set_required': True,
        'actual_synthetic_controls': controls,
        'V1_actual_ignored_FIFO_counterexample_rejected_by_V2': True,
        'assessment_identity': ident(assessment_path),
        'native_registrar_review_included': False,
        'qualification_or_native_or_physical_pass_issued': False,
        'execution': {'seconds': time.monotonic() - started,
            'max_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            'address_limit_bytes': 256 * 1024**2, 'CPU_limit_seconds': 60,
            'reason_for_256MiB_review_budget': 'Keep complete 11.15 MiB original Git source byte batch, source manifests and actual filesystem controls resident; scientific worker gates unchanged.'}}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(report, indent=2) + '\n').encode()
    OUTPUT.write_bytes(encoded)
    print(json.dumps({'report': str(OUTPUT), 'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest(),
        'review_pass': True, 'actual_synthetic_controls': len(controls), 'source_count': len(expected)}))


if __name__ == '__main__':
    main()
