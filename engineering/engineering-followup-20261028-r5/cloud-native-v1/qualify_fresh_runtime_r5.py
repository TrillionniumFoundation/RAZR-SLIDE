"""Qualify a genuinely installed S4 lock runtime before any study CAD worker.

Runs only beneath the unchanged native resource supervisor and original hosted
service-view harness. Every selected wheel is selected from the real uv.lock,
downloaded by its locked URL, hash checked, and matched to installed payloads.
RECORDs, generated installer files, namespace probes and complete before/after
inventories are retained. A prior local qualification is not an admission token.
"""
from pathlib import Path, PurePosixPath
import argparse
import base64
import configparser
import csv
import hashlib
import importlib
import importlib.machinery
import importlib.metadata
import io
import itertools
import json
import os
import resource
import subprocess
import sys
import sysconfig
import time
import tomllib
import urllib.parse
import urllib.request
import zipfile


def require(ok, message):
    if not ok:
        raise ValueError(message)


def identity(path):
    path = Path(path)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes': path.stat().st_size, 'sha256': digest}


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def normalized(name):
    return name.lower().replace('_', '-').replace('.', '-')


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            result[str(path.relative_to(root))] = {'kind': 'symlink', 'target': os.readlink(path)}
        elif path.is_file():
            result[str(path.relative_to(root))] = {'kind': 'regular', **identity(path)}
    return result


def wheel_tags(url):
    name = urllib.parse.unquote(urllib.parse.urlsplit(url).path.rsplit('/', 1)[-1])
    require(name.endswith('.whl'), 'Locked wheel URL does not name a wheel')
    parts = name[:-4].split('-')
    require(len(parts) >= 5, 'Unrecognized wheel filename')
    return {'-'.join(x) for x in itertools.product(*(x.split('.') for x in parts[-3:]))}


def main():
    actual_qualification_argv = list(sys.argv[1:])
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    c = json.loads(args.contract.read_text())
    require(identity(__file__) == c['qualifier_identity'], 'Qualifier source changed')
    expected_qualification_argv = ['--contract', c['expected_qualification_contract'],
                                  '--out', c['expected_qualification_output']]
    require(actual_qualification_argv == expected_qualification_argv,
            'Actual qualification argv differs from complete registered argv; extras, duplicates, equals and abbreviations are rejected')
    require(str(args.contract) == c['expected_qualification_contract'] and str(args.out) == c['expected_qualification_output'],
            'Actual qualification contract or output path differs')
    require(not args.out.exists(), 'Fresh qualification output required')
    args.out.mkdir(parents=True)
    root = Path(c['functional_root']).resolve()
    venv = root / '.venv'
    site = venv / 'lib/python3.12/site-packages'
    started = time.monotonic()
    report = {'schema': 'razr-r5-new-locked-runtime-qualification-v1',
              'completed': False, 'contract_identity': identity(args.contract),
              'qualifier_identity': identity(__file__), 'issues': [],
              'actual_qualification_argv': actual_qualification_argv,
              'expected_qualification_argv': expected_qualification_argv,
              'complete_qualification_argv_and_output_bound': True,
              'functional_root': str(root), 'venv': str(venv), 'site_packages': str(site),
              'prior_R4_qualification_used_as_admission': False,
              'historical_environment_identity_claimed': False,
              'new_runtime_from_actual_uv_locked_install': False,
              'compiled_kernel_formal_error_bound_verified': False,
              'physical_qualification': False, 'full_continuous_G2': False,
              'wheel_observations': [], 'installed_RECORD_checks': [], 'imports': [],
              'module_origins': [], 'namespace_locations': []}

    def save():
        report['seconds'] = time.monotonic() - started
        report['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        raw = (json.dumps(report, indent=2, allow_nan=False) + '\n').encode()
        require(len(raw) <= c['maximum_report_bytes'], 'Qualification report budget exceeded')
        (args.out / 'R5_FRESH_RUNTIME_QUALIFICATION.json').write_bytes(raw)
        require(sum(p.stat().st_size for p in args.out.rglob('*') if p.is_file()) <= c['maximum_output_bytes'], 'Qualification output budget exceeded')

    before = None
    try:
        require(sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize and not sys.flags.no_site,
                'Genuine venv isolated -I -B entry with site enabled required')
        require(sys.version_info[:3] == (3, 12, 14), 'Original cloud Python patch differs')
        require(Path(sys.prefix).resolve() == venv and Path(sys.base_prefix).resolve() != venv,
                'Interpreter is not the genuine new S4 venv')
        require('include-system-site-packages = false' in (venv / 'pyvenv.cfg').read_text(), 'System site access enabled')
        require(subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip() == c['functional_commit'], 'Functional Git HEAD differs')
        require(subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain', '--untracked-files=all'], text=True) == '', 'Functional checkout is dirty')
        for key in ('pyproject.toml', 'uv.lock'):
            require(identity(root / key) == c['locked_project_inputs'][key], 'Locked project input changed: ' + key)
        before = inventory(venv)
        report['venv_files_before'] = before
        report['venv_inventory_before_sha256'] = canonical(before)
        require(not any(k.endswith('.pyc') for k in before), 'Unregistered bytecode exists in new venv')
        symlinks = [k for k, v in before.items() if v['kind'] == 'symlink']
        require(all(k == 'lib64' or k.startswith('bin/python') for k in symlinks), 'Package payload is not a fresh real-file installation')
        report['interpreter'] = {'executable': sys.executable, 'resolved_binary': str(Path(sys.executable).resolve()),
                                 'binary_identity': identity(Path(sys.executable).resolve()), 'version': sys.version,
                                 'prefix': sys.prefix, 'base_prefix': sys.base_prefix}
        report['uv_version'] = subprocess.check_output(['uv', '--version'], text=True).strip()
        require(report['uv_version'] == 'uv 0.10.10', 'Pinned uv version differs')
        distributions = list(importlib.metadata.distributions(path=[str(site)]))
        version_map = {normalized(x.metadata['Name']): x.version for x in distributions}
        require(len(distributions) == 43 and len(version_map) == 43 and version_map == c['expected_43_package_versions'], 'Fresh candidate-only exact43 metadata differs')
        report['actual_43_package_versions'] = version_map
        lock = tomllib.loads((root / 'uv.lock').read_text())
        packages = {normalized(x['name']): x for x in lock['package'] if 'registry' in x.get('source', {})}
        require({k: v['version'] for k, v in packages.items()} == version_map, '43 installed packages differ from actual lock')
        expected_files, console_scripts, dist_info_dirs = {}, set(), set()
        scratch = Path(c['wheel_scratch']).resolve()
        require(not scratch.exists() and not scratch.is_relative_to(args.out) and not scratch.is_relative_to(root), 'Fresh external wheel scratch required')
        scratch.mkdir(parents=True)
        for distribution in sorted(distributions, key=lambda x: normalized(x.metadata['Name'])):
            name = normalized(distribution.metadata['Name'])
            info = Path(distribution._path)
            require(info.is_relative_to(site) and not info.is_symlink(), 'Distribution metadata escapes new site')
            dist_info_dirs.add(info)
            tags = {line[5:].strip() for line in (info / 'WHEEL').read_text().splitlines() if line.startswith('Tag: ')}
            wheels = [w for w in packages[name]['wheels'] if wheel_tags(w['url']) == tags]
            require(len(wheels) == 1, 'Installed WHEEL tags do not choose one locked wheel: ' + name)
            wheel = wheels[0]
            require(wheel['hash'].startswith('sha256:'), 'Unknown locked wheel hash algorithm')
            require(urllib.parse.urlsplit(wheel['url']).scheme == 'https', 'Non-HTTPS locked wheel URL')
            path = scratch / (name + '.whl')
            observation = {'name': name, 'version': distribution.version, 'locked_wheel': wheel,
                           'installed_wheel_tags': sorted(tags), 'download_completed': False,
                           'wheel_payloads_verified_against_install': 0, 'wheel_RECORD_entries_verified': 0}
            report['wheel_observations'].append(observation)
            save()
            try:
                size = 0
                with urllib.request.urlopen(wheel['url'], timeout=90) as response, path.open('xb') as output:
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        size += len(block)
                        require(size <= c['maximum_single_wheel_bytes'], 'Registered transient wheel disk cap exceeded')
                        output.write(block)
                observed = identity(path)
                observation['actual_download_identity'] = observed
                require(observed['sha256'] == wheel['hash'].split(':', 1)[1] and observed['bytes'] == wheel['size'], 'Downloaded wheel differs from immutable uv.lock')
                observation['download_completed'] = True
                with zipfile.ZipFile(path) as archive:
                    members = [m for m in archive.infolist() if not m.is_dir()]
                    names = [m.filename for m in members]
                    require(len(names) == len(set(names)), 'Duplicate wheel ZIP members')
                    record_names = [n for n in names if n.endswith('.dist-info/RECORD')]
                    require(len(record_names) == 1, 'One original wheel RECORD required')
                    record_name = record_names[0]
                    record = list(csv.reader(io.StringIO(archive.read(record_name).decode())))
                    recorded_names = set()
                    for relative, digest, count in record:
                        require(relative not in recorded_names and relative in names, 'Wheel RECORD missing or duplicate member')
                        recorded_names.add(relative)
                        data = archive.read(relative)
                        actual = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                        if relative == record_name:
                            require(digest == count == '', 'Wheel RECORD self entry must be unhashed')
                            continue
                        wanted = 'sha256=' + base64.urlsafe_b64encode(bytes.fromhex(actual['sha256'])).rstrip(b'=').decode()
                        require(digest == wanted and int(count) == len(data), 'Wheel inner RECORD differs: ' + relative)
                        observation['wheel_RECORD_entries_verified'] += 1
                        parts = PurePosixPath(relative).parts
                        require(parts and not relative.startswith('/') and '..' not in parts, 'Unsafe wheel member')
                        if parts[0].endswith('.data'):
                            require(len(parts) >= 3 and parts[1] in ('purelib', 'platlib', 'data'), 'Unregistered wheel installation spread category')
                            target = (site if parts[1] in ('purelib', 'platlib') else venv).joinpath(*parts[2:])
                        else:
                            target = site.joinpath(*parts)
                        require(target.is_relative_to(venv) and target.is_file() and not target.is_symlink(), 'Missing real installed wheel member')
                        target_relative = str(target.relative_to(venv))
                        require(identity(target) == actual, 'Installed payload differs from locked wheel: ' + target_relative)
                        require(target_relative not in expected_files or expected_files[target_relative]['identity'] == actual, 'Conflicting installed namespace owners')
                        expected_files.setdefault(target_relative, {'identity': actual, 'owners': []})['owners'].append(name)
                        observation['wheel_payloads_verified_against_install'] += 1
                    require(recorded_names == set(names), 'Wheel ZIP contains entries outside its RECORD')
                    observation['all_wheel_members_in_original_RECORD'] = True
            finally:
                if path.exists():
                    path.unlink()
                observation['transient_download_removed_after_verification'] = not path.exists()
            entry_file = info / 'entry_points.txt'
            if entry_file.is_file():
                cfg = configparser.ConfigParser(interpolation=None)
                cfg.optionxform = str
                cfg.read(entry_file)
                for section in ('console_scripts', 'gui_scripts'):
                    if cfg.has_section(section):
                        console_scripts.update(cfg[section])
            save()
        # Installed RECORDs include genuine installer-generated launchers and
        # metadata. They are separately hashed; they are not rewritten by us.
        recorded_targets = set()
        for info in sorted(dist_info_dirs):
            record_path = info / 'RECORD'
            record_copy = args.out / 'installed-records' / info.name / 'RECORD'
            record_copy.parent.mkdir(parents=True, exist_ok=True)
            record_copy.write_bytes(record_path.read_bytes())
            require(identity(record_copy) == identity(record_path), 'Exact installed RECORD copy changed')
            checked = {'relative': str(record_path.relative_to(venv)), 'identity': identity(record_path),
                       'exact_copy': str(record_copy.relative_to(args.out)),
                       'hashed_entries': 0, 'unhashed_self_entries': 0}
            seen = set()
            for relative, digest, count in csv.reader(io.StringIO(record_path.read_text())):
                target = (site / relative).resolve()
                require(target.is_relative_to(venv) and target.is_file() and not (site / relative).is_symlink(), 'Installed RECORD escapes real venv')
                key = str(target.relative_to(venv))
                require(key not in seen, 'Duplicate installed RECORD member')
                seen.add(key)
                recorded_targets.add(key)
                observed = identity(target)
                if target == record_path:
                    require(digest == count == '', 'Installed RECORD self identity is not canonical')
                    checked['unhashed_self_entries'] += 1
                else:
                    wanted = 'sha256=' + base64.urlsafe_b64encode(bytes.fromhex(observed['sha256'])).rstrip(b'=').decode()
                    require(digest == wanted and int(count) == observed['bytes'], 'Installed RECORD hash or size mismatch')
                    checked['hashed_entries'] += 1
            require(checked['unhashed_self_entries'] == 1, 'Installed RECORD missing self entry')
            report['installed_RECORD_checks'].append(checked)
        allowed_generated = set()
        for info in dist_info_dirs:
            for name in ('RECORD', 'INSTALLER', 'REQUESTED', 'uv_cache.json'):
                file = info / name
                if file.is_file():
                    allowed_generated.add(str(file.relative_to(venv)))
        allowed_generated.update('bin/' + name for name in console_scripts)
        scaffolds = {'pyvenv.cfg', '.gitignore', 'CACHEDIR.TAG', 'bin/activate', 'bin/activate.bat',
                     'bin/activate.csh', 'bin/activate.fish', 'bin/activate.nu', 'bin/activate.ps1',
                     'bin/activate_this.py', 'bin/deactivate.bat', 'bin/pydoc.bat',
                     'lib/python3.12/site-packages/_virtualenv.py', 'lib/python3.12/site-packages/_virtualenv.pth'}
        pth = site / '_virtualenv.pth'
        if pth.exists():
            require(pth.read_text().strip() == 'import _virtualenv', 'Unknown generated venv path hook')
        actual_regular = {k for k, v in before.items() if v['kind'] == 'regular'}
        extras = sorted(actual_regular - set(expected_files) - allowed_generated - scaffolds)
        require(not extras, 'Unbound real files in new venv: ' + repr(extras[:10]))
        require(set(expected_files) <= recorded_targets, 'Wheel payload lacks actual installed RECORD ownership')
        report['locked_wheel_payload_file_count'] = len(expected_files)
        report['locked_wheel_payload_bytes'] = sum(v['identity']['bytes'] for v in expected_files.values())
        report['locked_wheel_payload_inventory_sha256'] = canonical(expected_files)
        report['generated_installer_files'] = sorted(allowed_generated & actual_regular)
        report['actual_venv_scaffolds'] = sorted(scaffolds & actual_regular)
        (args.out / 'pyvenv.cfg').write_bytes((venv / 'pyvenv.cfg').read_bytes())
        report['unbound_files'] = extras
        stdlib = [Path(sysconfig.get_path('stdlib')).resolve(), Path(sysconfig.get_path('platstdlib')).resolve()]
        def allowed(path):
            p = Path(path)
            if p.is_relative_to(site):
                return 'fresh_verified_site'
            if p.resolve() == Path(__file__).resolve():
                return 'owned_qualifier'
            if 'site-packages' in p.parts or 'dist-packages' in p.parts:
                return None
            if any(p.is_relative_to(base) for base in stdlib):
                return 'stdlib'
            return None
        paths = list(sys.path)
        report['search_paths_before_imports'] = paths
        require(str(site) in paths and all(path and (Path(path) == site or allowed(path) == 'stdlib' or (path.endswith('/python312.zip') and Path(path).parent == stdlib[0].parent)) for path in paths), 'Isolated search paths escape genuine new runtime')
        top_names = set()
        for relative in expected_files:
            prefix = 'lib/python3.12/site-packages/'
            if not relative.startswith(prefix):
                continue
            first = relative.removeprefix(prefix).split('/')[0]
            if first.endswith('.py'):
                first = first[:-3]
            if first.isidentifier():
                top_names.add(first)
        report['top_level_resolution'] = []
        for name in sorted(top_names):
            spec = importlib.machinery.PathFinder.find_spec(name, [str(site)])
            locations = list(spec.submodule_search_locations or []) if spec else []
            origin = spec.origin if spec else None
            ok = bool(spec) and (origin is None or Path(origin).is_relative_to(site)) and all(Path(x).is_relative_to(site) for x in locations)
            report['top_level_resolution'].append({'module': name, 'origin': origin, 'locations': locations, 'within_new_site': ok})
            require(ok, 'Locked top-level resolution escaped new site')
        os.environ['MPLCONFIGDIR'] = str(args.out / 'matplotlib-cache')
        os.environ['XDG_CACHE_HOME'] = str(args.out / 'cache')
        for name in c['actual_import_probes']:
            begin = time.monotonic()
            module = importlib.import_module(name)
            report['imports'].append({'name': name, 'file': getattr(module, '__file__', None), 'seconds': time.monotonic() - begin})
            save()
        try:
            importlib.import_module('trame.env')
            report['legacy_only_trame_env_rejected'] = False
        except ModuleNotFoundError as exc:
            report['legacy_only_trame_env_rejected'] = exc.name == 'trame.env'
        require(report['legacy_only_trame_env_rejected'], 'Legacy-only trame.env resolved in the new environment')
        for name, module in list(sys.modules.items()):
            origin = getattr(module, '__file__', None)
            if origin:
                kind = allowed(origin)
                report['module_origins'].append({'name': name, 'origin': origin, 'scope': kind})
                require(kind is not None, 'Actual module origin escaped new runtime: ' + name)
            for location in getattr(module, '__path__', []):
                kind = allowed(location)
                report['namespace_locations'].append({'name': name, 'location': location, 'scope': kind})
                require(kind is not None, 'Namespace escaped new runtime: ' + name)
        report['search_paths_after_imports'] = list(sys.path)
        require(paths == list(sys.path), 'Imports changed isolated search paths')
        report['fresh_wheels_and_installed_RECORDs_verified'] = True
        report['namespace_and_real_import_probes_completed'] = True
        report['new_runtime_from_actual_uv_locked_install'] = True
        report['completed'] = True
    except BaseException as exc:
        report['issues'].append({'type': type(exc).__name__, 'message': str(exc)})
    finally:
        try:
            after = inventory(venv)
            report['venv_inventory_after_sha256'] = canonical(after)
            report['changed_or_extra_venv_files'] = sorted(set(before or {}) ^ set(after)) + sorted(k for k in set(before or {}) & set(after) if before[k] != after[k])
            report['all_new_runtime_files_unchanged'] = before is not None and before == after
            report['source_and_contract_unchanged'] = identity(__file__) == c['qualifier_identity'] and identity(args.contract) == report['contract_identity']
            report['completed'] = report['completed'] and report['all_new_runtime_files_unchanged'] and report['source_and_contract_unchanged']
        except BaseException as exc:
            report['issues'].append({'postflight_type': type(exc).__name__, 'message': str(exc)})
            report['completed'] = False
        save()
    print(json.dumps({k: report.get(k) for k in ('completed', 'seconds', 'peak_RSS_bytes', 'locked_wheel_payload_file_count', 'issues')}), flush=True)
    return 0 if report['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
