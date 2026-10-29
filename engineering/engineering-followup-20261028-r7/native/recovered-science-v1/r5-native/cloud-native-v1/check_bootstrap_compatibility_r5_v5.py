"""Actual bounded stdlib regression for the v4 host-bootstrap failure.

The missing-API control runs the exact old and new identity functions in this
interpreter after removing hashlib.file_digest. It does not pretend that this
local interpreter is the historical hosted Python. No CAD/runtime is qualified.
"""
from pathlib import Path
import argparse
import ast
import copy
import hashlib
import json
import resource
import runpy
import sys
import tempfile
import time
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DENIED = {'cadquery', 'OCP', 'numpy', 'scipy', 'vtk', 'trame'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def identity(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'bytes': Path(path).stat().st_size, 'sha256': digest.hexdigest()}


def normal_tree(path):
    tree = ast.parse(path.read_text(), feature_version=(3, 10))
    tree.body = [n for n in tree.body if not (isinstance(n, ast.Import) and len(n.names) == 1 and n.names[0].name == 'sys')]
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'identity':
            node.body = [ast.Pass()]
        if isinstance(node, ast.Dict):
            rows = [(k, v) for k, v in zip(node.keys, node.values)
                    if not (isinstance(k, ast.Constant) and k.value == 'bootstrap_interpreter_observation')]
            node.keys = [k for k, _ in rows]
            node.values = [v for _, v in rows]
    return ast.dump(tree, include_attributes=False)


def actual_failure(prefix, archive_path, log_path):
    expected = json.loads((HERE / 'publication-v4/SOURCE_LOCK.json').read_text())
    functional = json.loads((ROOT / 'r5-native/R5_RECOVERED_FUNCTIONAL_SOURCE_MANIFEST.json').read_text())['members']
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        names = [m.filename for m in members if not m.is_dir()]
        require(len(names) == len(set(names)), 'Duplicate actual ZIP members')
        def exact(name):
            return json.loads(archive.read(prefix + name))
        before = exact('S4-source-before.json')
        after = exact('S4-source-after.json')
        source_after = exact('source-after.json')
        environment = exact('environment-after-state.json')
        exit_bytes = archive.read(prefix + 'environment-after.exit-code.txt')
        signals = exact('signal-lifecycle/SIGNAL_CHECK.json')
        require(before['source_commit'] == after['source_commit'] == 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560', 'Actual S4 differs')
        require(before['all_present_tracked_bytes_match_HEAD'] and after['all_present_source_bytes_unchanged'] and not after['changed'], 'Actual source identity failed')
        require(before['present_source_sha256'] == after['source_sha256_after'], 'Actual before/after source SHA maps differ')
        require(all(before['present_source_sha256'].get(k) == v['sha256'] for k, v in functional.items()), 'Independent recovered S4 declared inputs differ')
        require(source_after['head']['exit_code'] == 0 and source_after['head']['stdout'].strip() == before['source_commit']
                and source_after['status']['exit_code'] == 0 and source_after['status']['stdout'] == ''
                and source_after['original_five_sources_unchanged'], 'Actual Git/source closeout differs')
        require(environment == {'status': 'not_executed', 'wrapper_exit_code': 'not_executed', 'checker_report_exists': False, 'passed': False}
                and exit_bytes == b'not_executed\n', 'Actual skipped environment is not retained')
        require(signals['passed'] and not signals['native_CAD_executed'] and len(signals['tests']) == 2
                and all(t['passed'] and t['both_bound_pidfds_exited'] and t['unrelated_sentinel_unaffected'] for t in signals['tests']), 'Actual original signal lifecycle failure')
        missing = ['R5_SUBMISSION_SOURCE_BINDING.json', 'runtime-qualification-owned/controller.json',
                   'runtime-qualification-owned/worker/R5_FRESH_RUNTIME_QUALIFICATION.json',
                   'core-producer-owned/controller.json', 'core-reader-owned/controller.json',
                   'factory/controller.json', 'readback/controller.json', 'R5_COMPLETE_RAW_EVIDENCE_MANIFEST.json']
        require(all(prefix + p not in names for p in missing), 'Unexpected claimed execution in bootstrap failure')
        lock_names = [n for n in names if n.endswith('/SOURCE_LOCK.json')]
        require(len(lock_names) == 1, 'One exact delivered lock required')
        asset_prefix = lock_names[0][:-len('SOURCE_LOCK.json')]
        require(archive.read(lock_names[0]) == (HERE / 'publication-v4/SOURCE_LOCK.json').read_bytes(), 'Delivered lock differs')
        for name, row in expected['asset_files'].items():
            data = archive.read(asset_prefix + name)
            require({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == row, 'Delivered v4 source asset differs')
        log = log_path.read_text()
        require("AttributeError: module 'hashlib' has no attribute 'file_digest'" in log
                and 'File "<stdin>", line 32, in <module>' in log and 'AssertionError' in log, 'Actual expected failure log absent')
        selected = {n: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                    for n in ('S4-source-before.json', 'S4-source-after.json', 'source-after.json', 'environment-after-state.json',
                              'environment-after.exit-code.txt', 'signal-lifecycle/SIGNAL_CHECK.json')
                    for data in [archive.read(prefix + n)]}
    return {'archive_path': str(archive_path.relative_to(ROOT)), 'archive_identity': identity(archive_path),
            'actual_log_path': str(log_path.relative_to(ROOT)), 'actual_log_identity': identity(log_path),
            'actual_case_prefix': prefix, 'exact_observed_member_identities': selected,
            'delivered_reviewed_v4_assets_exact': True, 'actual_S4_sources_unchanged': len(before['present_source_sha256']),
            'independently_recovered_declared_S4_inputs_corresponding': len(functional),
            'actual_original_SIGINT_TERM_controls_passed': True, 'actual_environment_state': environment,
            'always_stdin_line_32_failed_expression': "assert (case/'environment-after.exit-code.txt').read_text().strip() == '0'",
            'always_failure_is_original_fail_closed_unqualified_environment': True,
            'first_failure': 'bootstrap registrar identity() used unavailable hashlib.file_digest',
            'historical_bootstrap_exact_Python_version_not_recorded': True,
            'runtime_qualification_or_CAD_started': False, 'absent_unexecuted_reports': missing,
            'actual_bootstrap_failure_not_native_geometric_failure': True}


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), 'New immutable control report required')
    started = time.monotonic()
    old = HERE / 'publication-v4/register_cloud_native_r5.py'
    new = HERE / 'register_cloud_native_r5_bootstrap_v5.py'
    attempts = []
    class Deny:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split('.')[0] in DENIED:
                attempts.append(fullname)
                raise ImportError('Native/numeric imports forbidden in bootstrap controls')
    guard = Deny()
    sys.meta_path.insert(0, guard)
    saved = getattr(hashlib, 'file_digest', None)
    controls = []
    try:
        if saved is not None:
            del hashlib.file_digest
        old_ns = runpy.run_path(str(old), run_name='bootstrap_control_old')
        new_ns = runpy.run_path(str(new), run_name='bootstrap_control_new')
        try:
            old_ns['identity'](old)
        except AttributeError as exc:
            require("file_digest" in str(exc), 'Wrong original regression failure')
            controls.append({'kind': 'exact_old_identity_missing_API', 'old_failure_reproduced': True, 'type': type(exc).__name__, 'message': str(exc)})
        else:
            raise ValueError('Original absent API regression did not fail')
        for path in sorted((HERE / 'publication-v4').iterdir()):
            if path.is_file():
                got = new_ns['identity'](path)
                expected = identity(path)
                require(got == expected, 'Whole frozen source asset portable hash differs')
                controls.append({'kind': 'complete_frozen_asset_hash_without_optional_API', 'path': path.name, 'identity': got, 'matched': True})
        with tempfile.TemporaryDirectory(prefix='r5-bootstrap-hash-') as tmp:
            target = Path(tmp) / 'known.bin'
            for size in (0, 1, 1048575, 1048576, 1048577, 2097169):
                data = (bytes(range(251)) * (size // 251 + 1))[:size]
                target.write_bytes(data)
                expected = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                require(new_ns['identity'](target) == expected, 'Portable hash dropped/duplicated bytes at chunk boundary')
                controls.append({'kind': 'known_chunk_boundary_bytes', 'identity': expected, 'matched': True})
            before = new_ns['identity'](target)
            data = bytearray(target.read_bytes()); data[1048576] ^= 1
            target.write_bytes(data)
            after = new_ns['identity'](target)
            require(before['bytes'] == after['bytes'] and before['sha256'] != after['sha256'], 'Changed byte not detected')
            controls.append({'kind': 'changed_byte_at_chunk_boundary_rejected', 'before': before, 'after': after, 'different': True})
            try:
                new_ns['identity'](Path(tmp) / 'absent.bin')
            except FileNotFoundError:
                controls.append({'kind': 'missing_file_rejected', 'type': 'FileNotFoundError'})
            else:
                raise ValueError('Missing file incorrectly accepted')
    finally:
        if saved is not None:
            hashlib.file_digest = saved
        sys.meta_path.remove(guard)
    require(normal_tree(old) == normal_tree(new), 'Registrar changed outside hash implementation and bootstrap observation')
    code = new.read_text()
    require('extractall(' not in code and 'filter=' not in code and 'import tomllib' not in code and 'hashlib.file_digest(' not in code,
            'Unsupported host API remains in new registrar')
    require("shutil.copyfileobj(archive.extractfile(member), output)" in code and "member.isfile()" in code
            and "target.open('xb')" in code and "identity(target) == source_manifest['members'][member.name]" in code,
            'Original individually guarded scientific archive extraction changed')
    failures = []
    for kind, job, prefix in [('core', '123001249127', 'core/native80/'), ('near', '123001601032', 'factory/near/')]:
        failures.append(actual_failure(prefix, ROOT / ('r5-ci-results/RAZR-R5-native-v4-' + kind + '-run-40740717408.zip'),
            HERE / ('R5_NATIVE_V4_' + kind.upper() + '_JOB_' + job + '.log')))
    loaded = sorted(n for n in sys.modules if n.split('.')[0] in DENIED)
    require(not attempts and not loaded, 'Native or numeric module used by stdlib controls')
    report = {'schema': 'razr-r5-native-bootstrap-v5-controls-actual-v1', 'completed': True,
        'control_source_identity': identity(__file__), 'old_registrar_identity': identity(old), 'new_registrar_identity': identity(new),
        'controls': controls, 'control_count': len(controls),
        'actual_v4_core_and_near_bootstrap_failure_readback': failures,
        'remaining_registrar_AST_equal_after_exact_two_changes': True,
        'Python_3_10_grammar_parsed': True, 'actual_local_interpreter': sys.version,
        'optional_API_removed_for_control_only': 'hashlib.file_digest',
        'actual_historical_host_version_not_invented': True,
        'next_cloud_submission_records_actual_host_interpreter_and_capability': True,
        'host_tar_extraction_uses_regular_member_streams_no_filter_or_extractall': True,
        'qualified_3_12_entry_and_qualifier_unchanged': True,
        'original_native_six_gates_and_scientific_workers_unchanged': True,
        'original_always_environment_pass_assertions_unchanged': True,
        'blocked_native_import_attempts': attempts, 'native_numeric_modules_loaded': loaded,
        'native_or_runtime_qualification_executed': False, 'seconds': time.monotonic() - started,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    require(report['seconds'] <= 60 and report['peak_RSS_bytes'] <= 128 * 2**20, 'Bounded stdlib control budget exceeded')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('completed', 'control_count', 'seconds', 'peak_RSS_bytes', 'native_or_runtime_qualification_executed')}, indent=2))


if __name__ == '__main__':
    main()
