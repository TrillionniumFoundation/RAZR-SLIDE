"""Project isolated KiCad loader failures without exporting runtime text or paths.

This runs after the byte-identical EC1 launcher. It neither installs a package
nor changes an S4 check. Raw diagnostics remain in the ephemeral private task
directory; only hashes, numeric versions, library SONAMEs and fixed enums leave
that directory. Unknown text stays unknown.
"""
from pathlib import Path
import hashlib
import json
import math
import os
import re
import subprocess
import time

SCHEMA = 'razr-EC1a-isolated-linkage-projection-v1'
S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
LIBRARY = r'(?:lib[A-Za-z0-9_+.-]+|ld-linux[A-Za-z0-9_+.-]*|linux-vdso)\.so(?:\.[0-9A-Za-z_+.-]+)*'
SONAME = re.compile(LIBRARY + r'\Z')
HEX = re.compile(r'[0-9a-f]{64}\Z')
LABELS = ('kicad-version', 'native-readback', 'native-drc')
LIMIT_BYTES = 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def describe(data):
    return {'bytes': len(data), 'sha256': digest(data)}


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def classify_version(data, exit_code):
    """Extract narrowly specified loader syntax; never export arbitrary tokens."""
    text = data.decode('utf-8', 'replace')
    missing = sorted(set(re.findall(
        r'error while loading shared libraries: (' + LIBRARY + r'):'
        r' cannot open shared object file: No such file or directory', text)))
    versions = sorted(set(re.findall(r'(?m)^([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})\r?$', text)))
    abi = sorted(set(re.findall(
        r"version [`']((?:GLIBC|GLIBCXX|CXXABI|GCC|OPENSSL)_[0-9][0-9.]*)['`] not found", text)))
    if missing:
        category = 'loader_missing_library'
    elif abi:
        category = 'loader_missing_symbol_version'
    elif 'symbol lookup error:' in text or 'undefined symbol:' in text:
        category = 'loader_undefined_symbol'
    elif exit_code == 0 and len(versions) == 1:
        category = 'version_executed'
    elif type(exit_code) is int and exit_code < 0:
        category = 'process_signal'
    elif exit_code == 0:
        category = 'unrecognized_success_output'
    else:
        category = 'unclassified_version_failure'
    return {'classification': category, 'exit_code': exit_code,
            'numeric_versions': versions, 'missing_libraries': missing,
            'missing_ABI_versions': abi, 'raw_record': describe(data),
            'raw_text_exported': False}


def project_ldd(data, exit_code):
    text = data.decode('utf-8', 'replace')
    dependencies = {}
    unknown = 0
    non_dynamic = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line in ('not a dynamic executable', 'statically linked'):
            non_dynamic = True
            continue
        missing = re.fullmatch('(' + LIBRARY + r')\s+=>\s+not found', line)
        resolved = re.fullmatch('(' + LIBRARY + r')\s+=>\s+/[^\r\n]+\s+\(0x[0-9a-fA-F]+\)', line)
        direct = re.fullmatch(r'(?:/[^\r\n]+/)?(' + LIBRARY + r')\s+\(0x[0-9a-fA-F]+\)', line)
        match = missing or resolved or direct
        if not match:
            unknown += 1
            continue
        name = match.group(1)
        assert SONAME.fullmatch(name)
        state = 'missing' if missing else 'resolved'
        if name in dependencies and dependencies[name] != state:
            state = 'conflicting_observations'
        dependencies[name] = state
    return {'exit_code': exit_code,
            'dependencies': [{'soname': k, 'state': v} for k, v in sorted(dependencies.items())],
            'unrecognized_line_count': unknown, 'not_dynamic_observed': non_dynamic,
            'complete_recognized_listing': exit_code == 0 and unknown == 0 and not non_dynamic,
            'raw_record': describe(data), 'raw_text_exported': False}


def commands_projection(report):
    commands = []
    for item in report.get('commands', []):
        if not isinstance(item, dict) or item.get('label') not in LABELS:
            continue
        row = {'label': item['label']}
        if type(item.get('exit_code')) is int:
            row['exit_code'] = item['exit_code']
        if finite_number(item.get('seconds')):
            row['seconds'] = item['seconds']
        if isinstance(item.get('log_sha256'), str) and HEX.fullmatch(item['log_sha256']):
            row['log_sha256'] = item['log_sha256']
        commands.append(row)
    return commands


def capture(command, env, directory, label):
    output = directory / (label + '.log')
    start = time.monotonic()
    code = None
    status = 'completed'
    with output.open('xb') as stream:
        try:
            proc = subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=15)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            status = 'timeout'
        except OSError:
            status = 'process_start_failed'
    length = output.stat().st_size
    if length > LIMIT_BYTES:
        # Unknown output is never summarized from a silently truncated prefix.
        return None, {'state': 'output_limit_exceeded', 'exit_code': code,
                      'seconds': time.monotonic() - start, 'bytes': length}
    data = output.read_bytes()
    return data, {'state': status, 'exit_code': code, 'seconds': time.monotonic() - start}


def diagnose(base):
    result = {'schema': SCHEMA, 'source_commit': S4,
              'is_original_record': False, 'raw_runtime_exported': False,
              'raw_runtime_durable': False, 'native_result_changed': False,
              'dependency_packages_added': False, 'original_commands': [],
              'new_native_DRC_executed_by_diagnostic': False,
              'candidate_go': False, 'fixture_fabrication_go': False,
              'manufacturing_go': False}
    report_path = base / 'result/report.json'
    if report_path.is_file() and not report_path.is_symlink():
        raw = report_path.read_bytes()
        report = json.loads(raw)
        result['original_report'] = describe(raw)
        result['original_commands'] = commands_projection(report)
        result['original_verifier_passed'] = report.get('passed') is True
        result['original_native_DRC_executed'] = report.get('native_DRC_executed') is True
        result['original_source_bytes_unchanged'] = report.get('source_bytes_unchanged') is True
    version_path = base / 'result/kicad-version.log'
    version_command = next((c for c in result['original_commands'] if c['label'] == 'kicad-version'), None)
    if version_path.is_file() and not version_path.is_symlink():
        raw = version_path.read_bytes()
        if len(raw) <= LIMIT_BYTES:
            result['original_version'] = classify_version(raw, (version_command or {}).get('exit_code'))
            result['original_version_matches_command_hash'] = (version_command or {}).get('log_sha256') == digest(raw)
    runtime = base / 'runtime'
    cli = runtime / 'usr/bin/kicad-cli'
    if not cli.is_file():
        result['diagnostic_state'] = 'runtime_not_prepared'
        return result
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['LD_LIBRARY_PATH'] = ':'.join(str(runtime / p) for p in ('usr/lib/x86_64-linux-gnu', 'usr/lib'))
    env['PYTHONPATH'] = str(runtime / 'usr/lib/python3/dist-packages')
    env['KICAD_STOCK_DATA_HOME'] = str(runtime / 'usr/share/kicad')
    for name, folder in [('KICAD_CONFIG_HOME', 'config'), ('KICAD_DOCUMENTS_HOME', 'documents'),
                         ('XDG_CONFIG_HOME', 'xdg-config'), ('XDG_CACHE_HOME', 'xdg-cache'),
                         ('XDG_DATA_HOME', 'xdg-data')]:
        env[name] = str(base / folder)
    private = base / 'diagnostic-private'
    private.mkdir(exist_ok=False)
    result['diagnostic_state'] = 'completed'
    result['ldd'] = []
    modules = sorted((runtime / 'usr/lib/python3/dist-packages').glob('_pcbnew*.so'))
    result['pcbnew_extension_count'] = len(modules)
    targets = [('kicad_cli', cli)]
    if len(modules) == 1:
        targets.append(('pcbnew_extension', modules[0]))
    # These are same verified, official binaries used by the unchanged verifier.
    for label, path in targets:
        raw, status = capture(['/usr/bin/ldd', str(path)], env, private, 'ldd-' + label)
        row = {'target': label, 'capture': status}
        if raw is not None:
            row.update(project_ldd(raw, status['exit_code']))
        result['ldd'].append(row)
    raw, status = capture([str(cli), 'version'], env, private, 'repeat-version')
    result['repeat_version_capture'] = status
    if raw is not None:
        result['repeat_version'] = classify_version(raw, status['exit_code'])
    return result


def main():
    base = Path(os.environ['RUNNER_TEMP']) / 'razr-ec1-s4'
    output = Path(os.environ['RUNNER_TEMP']) / 'razr-ec1-engineering'
    manifest_path = output / 'MANIFEST.json'
    if not output.is_dir() or not manifest_path.is_file():
        # The original exporter must finish before this allowlisted addition.
        return 2
    record = diagnose(base)
    data = (json.dumps(record, indent=2, allow_nan=False) + '\n').encode()
    filename = 'isolated-linkage.engineering.json'
    with (output / filename).open('xb') as stream:
        stream.write(data)
    manifest = json.loads(manifest_path.read_text())
    assert manifest['raw_runtime_exported'] is False
    assert filename not in manifest['files']
    manifest['files'][filename] = {**describe(data), 'original_bytes': False}
    manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'diagnostic_state': record['diagnostic_state'], 'runtime_text_exported': False}))
    return 0 if record['diagnostic_state'] == 'completed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
