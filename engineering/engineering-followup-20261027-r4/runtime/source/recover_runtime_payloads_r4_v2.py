"""Recover the exact frozen R3 payload map for a separately named R4 runtime.

Only explicit new directories are written. Existing package files are read and
reused only after full identity comparison. Downloaded wheels remain data until
their compressed identity and every selected payload member have been verified.
"""
from __future__ import annotations
import argparse
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import time
import urllib.parse
import urllib.request
import zipfile


def identity(path):
    h = hashlib.sha256(); n = 0
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            n += len(block); h.update(block)
    return {'bytes': n, 'sha256': h.hexdigest()}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--contract', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); a.out.mkdir(exist_ok=False)
    contract = json.loads(a.contract.read_text()); start = time.monotonic()
    result = {'schema': 'razr-r4-frozen-payload-recovery-execution-v2',
              'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'source_identity': identity(__file__), 'contract_identity': identity(a.contract),
              'existing_payload_observations': [], 'wheel_observations': [],
              'resolved_payloads': [], 'issues': [], 'completed': False,
              'original_runtime_writes': 0, 'package_installer_executions': 0,
              'downloaded_code_executed': False, 'historical_execution_requalified': False,
              'native_CAD_or_numerical_solve_executed': False}
    def save():
        result['seconds'] = time.monotonic() - start
        write(a.out / 'R4_RUNTIME_PAYLOAD_RECOVERY_EXECUTED.json', result)
    try:
        require(result['source_identity'] == contract['worker_identity'], 'Worker differs')
        require(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode,
                'Exact -I -S -B flags required')
        old_path = Path(contract['frozen_R3_plan']['path'])
        require(identity(old_path) == {k: contract['frozen_R3_plan'][k] for k in ('bytes', 'sha256')},
                'Frozen R3 payload plan differs')
        old = json.loads(old_path.read_text())
        require(identity(Path(sys.executable).resolve()) == old['python_binary_identity'],
                'Interpreter differs from original frozen interpreter')
        require(sys.path == old['isolated_standard_library_search_paths'], 'Stdlib search paths differ')
        base = Path(contract['existing_site']).resolve()
        global_prefix = Path(contract['existing_prefix']).resolve()
        new_roots = [Path(contract[k]).resolve() for k in ('new_payload_root', 'new_wheel_root', 'new_candidate_root')]
        require(len(set(new_roots)) == 3 and all(q.parent == a.out.parent.resolve() and not q.exists() for q in new_roots), 'New runtime roots must be distinct unused siblings')
        require(len(contract['frozen_wheels']) == 43 and {r['name']: r['version'] for r in contract['frozen_wheels']} == old['original_43_version_map'], 'Exact43 wheel/version map differs')
        require(all(Path(r['name']).name == r['name'] and r['name'] not in ('.', '..') and Path(r['filename']).name == r['filename'] for r in contract['frozen_wheels']), 'Unsafe wheel name or filename')
        owned = Path(contract['new_payload_root']); owned.mkdir(exist_ok=False)
        wheel_dir = Path(contract['new_wheel_root']); wheel_dir.mkdir(exist_ok=False)
        prefix = 'lib/python3.12/site-packages/'
        resolved = {}; needed = set(); owners = {}
        for row in old['payload_files']:
            relative = row['relative']
            require(relative.startswith(prefix) or relative == 'share/man/man1/ttx.1', 'Unrecognized original payload layout')
            short = relative[len(prefix):] if relative.startswith(prefix) else relative
            q = PurePosixPath(short)
            require(not q.is_absolute() and '..' not in q.parts and short, 'Unsafe planned path')
            require(relative not in owners, 'Duplicate planned payload')
            owners[relative] = row['owner_names']
            path = base / short if relative.startswith(prefix) else global_prefix / relative
            actual = identity(path) if path.is_file() and not path.is_symlink() else None
            equal = actual == row['identity']
            result['existing_payload_observations'].append(
                {'relative': relative, 'actual': actual, 'expected': row['identity'], 'equal': equal})
            if equal:
                resolved[relative] = {'source': str(path), 'basis': 'fresh_current_file_equal_to_frozen_R3_payload'}
            else:
                needed.update(row['owner_names'])
        wheels = {row['name']: row for row in contract['frozen_wheels']}
        require(needed <= wheels.keys(), 'No locked wheel for missing owner')
        result['required_wheel_names'] = sorted(needed)
        result['actual_required_compressed_bytes'] = sum(wheels[n]['wheel']['size'] for n in needed)
        save()
        for name in sorted(needed):
            spec = wheels[name]; locked = spec['wheel']; url = locked['url']
            parsed = urllib.parse.urlparse(url)
            require(parsed.scheme == 'https' and parsed.netloc == 'files.pythonhosted.org', 'Unexpected wheel host')
            filename = spec['filename']; require(Path(filename).name == filename, 'Unsafe wheel basename')
            target = wheel_dir / filename; require(not target.exists(), 'Wheel output already exists')
            observation = {'name': name, 'version': spec['version'], 'locked': locked,
                           'filename': filename, 'download_started': True, 'payload_members': [], 'completed': False}
            result['wheel_observations'].append(observation); save(); before = time.monotonic()
            h = hashlib.sha256(); count = 0
            with urllib.request.urlopen(url, timeout=30) as response, target.open('xb') as stream:
                observation['http_status'] = response.status
                final = urllib.parse.urlparse(response.geturl())
                require(final.scheme == 'https' and final.netloc == 'files.pythonhosted.org', 'Wheel redirect changed host')
                while True:
                    block = response.read(1048576)
                    if not block: break
                    count += len(block); require(count <= locked['size'], 'Download exceeds locked byte count')
                    h.update(block); stream.write(block)
            actual = {'bytes': count, 'sha256': h.hexdigest()}
            observation['download_identity'] = actual; observation['download_seconds'] = time.monotonic() - before
            require(actual == {'bytes': locked['size'], 'sha256': locked['hash'].removeprefix('sha256:')},
                    'Compressed locked wheel identity differs')
            package_root = owned / name; package_root.mkdir(exist_ok=False)
            with zipfile.ZipFile(target) as archive:
                infos = archive.infolist(); names = [info.filename for info in infos]
                require(len(names) == len(set(names)), 'Duplicate wheel members')
                for info in infos:
                    q = PurePosixPath(info.filename)
                    require(not q.is_absolute() and '..' not in q.parts and
                            not stat.S_ISLNK(info.external_attr >> 16), 'Unsafe wheel member')
                for row in old['payload_files']:
                    if name not in row['owner_names']: continue
                    is_site = row['relative'].startswith(prefix)
                    short = row['relative'][len(prefix):] if is_site else row['relative']
                    if is_site:
                        matches = [short] if short in names else [x for x in names
                            if ('.data/purelib/' in x and x.split('.data/purelib/', 1)[1] == short) or
                               ('.data/platlib/' in x and x.split('.data/platlib/', 1)[1] == short)]
                    else:
                        matches = [x for x in names if '.data/data/' in x and x.split('.data/data/', 1)[1] == short]
                    require(len(matches) == 1, 'Expected frozen payload not uniquely present in wheel: ' + short)
                    info = archive.getinfo(matches[0]); dest = package_root / row['relative']
                    require(info.file_size == row['identity']['bytes'], 'Wheel member size differs')
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    hh = hashlib.sha256(); size = 0
                    with archive.open(info) as source, dest.open('xb') as sink:
                        for block in iter(lambda: source.read(1048576), b''):
                            hh.update(block); size += len(block); sink.write(block)
                    actual_member = {'bytes': size, 'sha256': hh.hexdigest()}
                    require(actual_member == row['identity'], 'Frozen wheel member bytes differ')
                    # Retain executable bits only where present in the original wheel.
                    dest.chmod(0o755 if info.external_attr >> 16 & 0o111 else 0o644)
                    observation['payload_members'].append({'relative': row['relative'], 'wheel_member': info.filename,
                                                          'actual': actual_member})
                    if row['relative'] not in resolved:
                        resolved[row['relative']] = {'source': str(dest), 'basis': 'fresh_compressed_locked_wheel_and_member_identity',
                                                     'wheel_owner': name, 'wheel_member': info.filename}
            observation['completed'] = True; save()
        require(len(resolved) == len(old['payload_files']), 'Unresolved payloads')
        plan = copy.deepcopy(old)
        plan['schema'] = 'razr-r4-recovered-payload-projection-plan-v2'
        plan['frozen_R3_planner_identity'] = plan.pop('source_identity')
        plan['source_identity'] = identity(__file__)
        plan['created_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
        plan['new_candidate_name'] = contract['new_candidate_name']
        plan['candidate_root'] = contract['new_candidate_root']
        plan['python_executable'] = sys.executable
        for row in plan['payload_files']:
            new = resolved[row['relative']]; row['historical_R3_source'] = row['source']; row['source'] = new['source']
            row['current_recovery_basis'] = new['basis']
            actual = identity(row['source']); require(actual == row['identity'], 'Resolved payload changed before plan')
            result['resolved_payloads'].append({'relative': row['relative'], **new, 'identity': actual})
        by_relative = {r['relative']: r for r in plan['payload_files']}
        for row in plan['distributions']:
            metadata = by_relative[row['dist_info_relative'] + '/METADATA']
            row['historical_R3_directory'] = row['original_directory']
            row['original_directory'] = str(Path(metadata['source']).parent)
        plan['frozen_R3_plan_identity'] = contract['frozen_R3_plan']
        plan['recovery_contract_identity'] = identity(a.contract)
        plan['construction_rules'] = ['Reference exactly the recovered per-file payload map and regenerate only 43 RECORD files.',
            'Observe all source bytes before and after controlled execution; no OS immutability or historical execution claim.']
        plan['capacity']['new_download_bytes'] = result['actual_required_compressed_bytes']
        plan['capacity']['heavy_payload_copy_bytes'] = sum(r['identity']['bytes'] for r in result['resolved_payloads']
            if r['basis'] == 'fresh_compressed_locked_wheel_and_member_identity')
        write(a.out / 'R4_RECOVERED_PROJECTION_PLAN.json', plan)
        result['new_plan_identity'] = identity(a.out / 'R4_RECOVERED_PROJECTION_PLAN.json')
        result['all_8112_current_identities_match_frozen_R3'] = True
        result['frozen_input_unchanged'] = identity(old_path) == {k: contract['frozen_R3_plan'][k] for k in ('bytes', 'sha256')}
        result['worker_source_unchanged'] = identity(__file__) == contract['worker_identity']
        result['completed'] = result['frozen_input_unchanged'] and result['worker_source_unchanged']
    except Exception as exc:
        result['issues'].append({'type': type(exc).__name__, 'message': str(exc)})
    result['finished_utc'] = dt.datetime.now(dt.timezone.utc).isoformat(); save()
    print(json.dumps({'completed': result['completed'], 'issues': result['issues'],
                      'resolved_payload_count': len(result['resolved_payloads']),
                      'wheels': len(result['wheel_observations']), 'seconds': result['seconds']}), flush=True)
    return 0 if result['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
