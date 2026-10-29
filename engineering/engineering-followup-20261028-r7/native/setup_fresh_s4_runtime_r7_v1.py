"""Install a genuine sparse S4 worktree and pinned uv runtime with bounded evidence.

This is new local setup, not a hosted-run reproduction. Original qualification
and CAD workers are separate stages and cannot be admitted by this setup receipt.
"""
from pathlib import Path, PurePosixPath
import argparse
import base64
import csv
import datetime as dt
import hashlib
import io
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import time
import urllib.request
import zipfile

S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
WHEEL_SHA = 'e42e9e4a196ef75d1089715574eb1fe9bb62d390da05c6c8b36650a4de23d59f'
EMPTY_SHA = hashlib.sha256(b'').hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def identity(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(2**20), b''):
            h.update(b)
    return {'bytes': path.stat().st_size, 'sha256': h.hexdigest()}

def resources(path):
    stats = dict((k, int(v)) for k, v in (line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines()))
    s = os.statvfs(path)
    return {'ordinary_available_bytes': s.f_bavail * s.f_frsize,
            'shared_unreclaimable_bytes': stats['anon'] + stats['shmem'] + max(stats['kernel'] - stats['slab_reclaimable'], 0) + stats.get('unevictable', 0),
            'cgroup_current_bytes': int(Path('/sys/fs/cgroup/memory.current').read_text())}

def process_tree_rss(root):
    rows = {}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            lines = (p / 'status').read_text().splitlines()
            fields = {x.split(':', 1)[0]: x.split(':', 1)[1].strip() for x in lines if ':' in x}
            rows[int(p.name)] = (int(fields['PPid']), int(fields.get('VmRSS', '0 kB').split()[0]) * 1024)
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    selected = {root}
    while True:
        more = {pid for pid, (ppid, _) in rows.items() if ppid in selected}
        if more <= selected:
            break
        selected |= more
    return sum(rows.get(p, (0, 0))[1] for p in selected)

def run_observed(command, cwd, out, env, limit, deadline, stdin=None):
    started = time.monotonic()
    obs = {'command': command, 'cwd': str(cwd), 'samples': [], 'resource_stop': None,
           'started_utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    with out.with_suffix('.stdout').open('xb') as stdout, out.with_suffix('.stderr').open('xb') as stderr:
        child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                                 stdout=stdout, stderr=stderr, start_new_session=True)
        obs['owned_process_group_pid'] = child.pid
        if stdin is not None:
            child.stdin.write(stdin)
            child.stdin.close()
        try:
            while child.poll() is None:
                sample = {'seconds': time.monotonic() - started, **resources(out.parent),
                          'child_tree_RSS_bytes': process_tree_rss(child.pid), 'setup_RSS_bytes': process_tree_rss(os.getpid())}
                temp = Path(env.get('TMPDIR', str(out.parent / 'not-created')))
                sample['installer_transient_bytes'] = sum(p.stat().st_size for p in temp.rglob('*') if p.is_file() and not p.is_symlink()) if temp.exists() else 0
                obs['samples'].append(sample)
                if time.monotonic() > deadline:
                    obs['resource_stop'] = 'wall_seconds'
                elif sample['setup_RSS_bytes'] > limit['worker_RSS_limit_bytes']:
                    obs['resource_stop'] = 'setup_and_descendant_RSS'
                elif sample['shared_unreclaimable_bytes'] > limit['shared_limit_bytes']:
                    obs['resource_stop'] = 'shared_memory'
                elif sample['ordinary_available_bytes'] < 4 * 2**30:
                    obs['resource_stop'] = 'postinstall_reserve_during_setup'
                elif sample['installer_transient_bytes'] > 1778037715:
                    obs['resource_stop'] = 'registered_installer_transient_bytes'
                if obs['resource_stop']:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait()
                    break
                time.sleep(.2)
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
        obs.update(exit_code=child.returncode, seconds=time.monotonic() - started,
                   stdout=identity(out.with_suffix('.stdout')), stderr=identity(out.with_suffix('.stderr')))
        out.with_suffix('.json').write_text(json.dumps(obs, indent=2) + '\n')
        require(child.returncode == 0 and obs['resource_stop'] is None, 'Bounded setup subprocess failed: ' + str(out))
    return obs

def verify_checkout(root, expected, commit):
    require(subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip() == commit, 'Real worktree HEAD differs')
    require(subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain', '--untracked-files=all'], text=True) == '', 'Real worktree is dirty')
    actual = {}
    for p in root.rglob('*'):
        rel = p.relative_to(root)
        if rel.parts[0] == '.venv':
            continue
        require(not p.is_symlink(), 'Unregistered worktree symlink')
        if p.is_file():
            actual[str(rel)] = identity(p)
    require(set(actual) == set(expected) | {'.git'}, 'Complete actual worktree member set differs')
    require((root / '.git').is_file() and (root / '.git').read_text().startswith('gitdir: '), 'Real git worktree pointer missing')
    require({k: v for k, v in actual.items() if k != '.git'} == expected, 'Complete actual S4 source bytes differ')
    return {'actual_member_count': len(actual), 'expected_member_count': len(expected) + 1,
            'actual_complete_member_set_equal': True, 'all_source_bytes_equal': True,
            'all_members': actual, 'HEAD': commit, 'full_repository_checkout_claimed': False}

def install_uv(root, selection, deadline):
    wheel = selection['selected']
    require(wheel['size'] == 23473055 and wheel['digests']['sha256'] == WHEEL_SHA, 'Pinned official uv wheel changed')
    root.mkdir(exist_ok=False)
    dest = root / wheel['filename']
    count = 0
    with urllib.request.urlopen(wheel['url'], timeout=90) as response, dest.open('xb') as output:
        while b := response.read(2**20):
            require(time.monotonic() <= deadline, 'Setup wall deadline during uv download')
            count += len(b)
            require(count <= 23473055, 'Pinned uv download exceeded registered bytes')
            output.write(b)
    require(identity(dest) == {'bytes': 23473055, 'sha256': WHEEL_SHA}, 'Official pinned uv wheel SHA/size differs')
    payload = root / 'payload'
    payload.mkdir()
    with zipfile.ZipFile(dest) as a:
        members = [x for x in a.infolist() if not x.is_dir()]
        require(len(members) == len({x.filename for x in members}), 'Duplicate uv wheel ZIP member')
        require(sum(x.file_size for x in members) <= 201326592, 'uv wheel expanded capacity exceeded')
        names = {x.filename for x in members}
        record_names = [x for x in names if x.endswith('.dist-info/RECORD')]
        require(len(record_names) == 1, 'uv wheel RECORD count differs')
        record = list(csv.reader(io.StringIO(a.read(record_names[0]).decode())))
        seen = set()
        for name, digest, size in record:
            require(time.monotonic() <= deadline, 'Setup wall deadline during uv extraction')
            require(name not in seen and name in names, 'Duplicate or missing uv RECORD member')
            seen.add(name)
            parts = PurePosixPath(name).parts
            require(parts and not name.startswith('/') and '..' not in parts, 'Unsafe uv wheel member')
            member = a.getinfo(name)
            require(not stat.S_ISLNK(member.external_attr >> 16), 'uv wheel symlink not admitted')
            data = a.read(name)
            if name == record_names[0]:
                require(digest == size == '', 'uv RECORD self entry differs')
            else:
                value = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
                require(digest == 'sha256=' + value and int(size) == len(data), 'uv inner RECORD differs')
            p = payload.joinpath(*parts)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            if name in ('uv/uv', 'uv/uvx', 'uv-0.10.10.data/scripts/uv', 'uv-0.10.10.data/scripts/uvx'):
                p.chmod(0o755)
        require(seen == names, 'uv member set differs from RECORD')
        actual = {str(x.relative_to(payload)) for x in payload.rglob('*') if x.is_file()}
        require(actual == names, 'Actual full extracted uv member set differs')
    candidates = [p for p in payload.rglob('uv') if p.is_file()]
    require(len(candidates) == 1, 'One actual uv executable required')
    binary = candidates[0]
    require(subprocess.check_output([str(binary), '--version'], text=True).strip() == 'uv 0.10.10', 'Actual installed uv version differs')
    return {'original_wheel': {'path': str(dest), **identity(dest)}, 'executable': str(binary),
            'binary_identity': identity(binary), 'all_RECORD_members_verified': len(seen),
            'actual_full_member_set_equal': True}

def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--contract', type=Path, required=True)
    args = parser.parse_args()
    c = json.loads(args.contract.read_text())
    require(sys.argv[1:] == ['--contract', str(args.contract)], 'Complete setup argv differs')
    require(identity(__file__) == c['setup_source_identity'], 'Setup source changed')
    out = Path(c['output'])
    require(not out.exists(), 'Fresh setup output required')
    out.mkdir(parents=True)
    report = {'schema': 'RAZR_R7_FRESH_LOCAL_RUNTIME_SETUP_ACTUAL_V1', 'completed': False,
              'native_execution_claimed': False, 'runtime_qualified': False, 'contract_identity': identity(args.contract),
              'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'stage': c['stage'], 'issues': []}
    start = time.monotonic()
    deadline = start + c['original_six_limits']['wall_seconds']
    try:
        for item in c['bound_inputs']:
            require(identity(item['path']) == item['identity'], 'Bound setup input changed')
        initial = resources(out)
        report['initial_resources'] = initial
        require(initial['ordinary_available_bytes'] >= c['conservative_preinstall_reserve_bytes'], 'Conservative preinstall capacity unavailable')
        require(initial['shared_unreclaimable_bytes'] + c['original_six_limits']['startup_extra_shared_bytes'] <= c['original_six_limits']['shared_limit_bytes'], 'Original startup shared reserve unavailable')
        report['capacity_basis'] = c['capacity_basis']
        if c['stage'] == 'assess_only':
            report['completed'] = True
            return 0
        require(c['stage'] == 'install_only', 'Unregistered setup stage')
        worktree = Path(c['functional_root'])
        require(not worktree.exists(), 'Fresh real worktree required')
        env = dict(os.environ)
        env.update(PYTHONDONTWRITEBYTECODE='1', UV_COMPILE_BYTECODE='0', UV_NO_PROGRESS='1', UV_PYTHON_DOWNLOADS='never')
        calls = []
        def run(cmd, cwd, name, stdin=None):
            result = run_observed(cmd, cwd, out / name, env, c['original_six_limits'], deadline, stdin)
            calls.append({'name': name, 'seconds': result['seconds'], 'exit_code': result['exit_code']})
        run(['git', '-C', c['repository'], 'worktree', 'add', '--detach', '--no-checkout', str(worktree), S4], Path(c['repository']), 'worktree-add')
        run(['git', 'sparse-checkout', 'init', '--no-cone'], worktree, 'sparse-init')
        patterns = ''.join('/' + x + '\n' for x in sorted(c['expected_sources'])).encode()
        run(['git', 'sparse-checkout', 'set', '--no-cone', '--stdin'], worktree, 'sparse-set', patterns)
        report['source_before_install'] = verify_checkout(worktree, c['expected_sources'], S4)
        uv = install_uv(Path(c['uv_root']), json.loads(Path(c['uv_selection']).read_text()), deadline)
        report['uv'] = uv
        env['PATH'] = str(Path(uv['executable']).parent) + os.pathsep + env['PATH']
        env['UV_CACHE_DIR'] = str(out / 'installer-cache')
        env['TMPDIR'] = str(out / 'installer-temp')
        Path(env['TMPDIR']).mkdir()
        report['python_version'] = subprocess.check_output([c['python_executable'], '--version'], text=True).strip()
        require(report['python_version'] == 'Python 3.12.14', 'Original required Python patch differs')
        run([uv['executable'], 'sync', '--locked', '--no-cache', '--python', c['python_executable']], worktree, 'uv-sync')
        report['source_after_install'] = verify_checkout(worktree, c['expected_sources'], S4)
        report['postinstall_resources'] = resources(out)
        require(report['postinstall_resources']['ordinary_available_bytes'] >= 4 * 2**30, 'Original 4 GiB postinstall qualification-registration reserve unavailable')
        report['postinstall_4GiB_original_gate_passed'] = True
        report['actual_subprocesses'] = calls
        report['completed'] = True
    except BaseException as exc:
        report['issues'].append({'type': type(exc).__name__, 'message': str(exc)})
    finally:
        report['seconds'] = time.monotonic() - start
        report['final_resources'] = resources(out)
        report['all_bound_inputs_unchanged'] = all(identity(x['path']) == x['identity'] for x in c['bound_inputs'])
        report['setup_and_contract_unchanged'] = identity(__file__) == c['setup_source_identity'] and identity(args.contract) == report['contract_identity']
        report['completed'] = report['completed'] and report['all_bound_inputs_unchanged'] and report['setup_and_contract_unchanged']
        raw = (json.dumps(report, indent=2) + '\n').encode()
        require(len(raw) <= 4 * 2**20, 'Setup report exceeds 4 MiB registered cap')
        (out / 'R7_FRESH_LOCAL_RUNTIME_SETUP_ACTUAL_V1.json').write_bytes(raw)
        print(json.dumps({k: report[k] for k in ('completed', 'stage', 'seconds', 'issues')}), flush=True)
    return 0 if report['completed'] else 2

if __name__ == '__main__':
    raise SystemExit(main())
