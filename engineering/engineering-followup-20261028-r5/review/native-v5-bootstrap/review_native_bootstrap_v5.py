"""Read-only independent review of the frozen native v5 bootstrap delta."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import resource
import signal
import tarfile
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'r5-native/cloud-native-v1'
OLD = BASE / 'publication-v4'
NEW = BASE / 'publication-v5'
LIMITS = {'wall_seconds': 90, 'address_space_bytes': 268435456,
          'maximum_hashed_bytes': 67108864, 'maximum_scientific_archive_decoded_bytes': 8388608}
checks = []
watched = {}
hashed = 0


def need(ok, label):
    checks.append({'check': label, 'passed': bool(ok)})
    if not ok:
        raise ValueError(label)


def identity(path):
    global hashed
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            hashed += len(block)
            need(hashed <= LIMITS['maximum_hashed_bytes'], 'hash budget')
            h.update(block)
    return {'bytes': path.stat().st_size, 'sha256': h.hexdigest()}


def watch(path):
    path = path.resolve()
    if str(path) not in watched:
        watched[str(path)] = identity(path)
    return watched[str(path)]


def read(path):
    watch(path)
    return json.loads(path.read_text())


def normal(tree):
    tree.body = [n for n in tree.body if not (isinstance(n, ast.Import) and
                 len(n.names) == 1 and n.names[0].name == 'sys')]
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == 'identity':
            n.body = [ast.Pass()]
        if isinstance(n, ast.Dict):
            keep = [(k, v) for k, v in zip(n.keys, n.values)
                    if not (isinstance(k, ast.Constant) and k.value == 'bootstrap_interpreter_observation')]
            n.keys, n.values = [k for k, v in keep], [v for k, v in keep]
    return ast.dump(tree, include_attributes=False)


def main():
    started = time.monotonic()
    signal.alarm(LIMITS['wall_seconds'])
    resource.setrlimit(resource.RLIMIT_AS, (LIMITS['address_space_bytes'],) * 2)
    output = HERE / 'R5_NATIVE_CLOUD_V5_BOOTSTRAP_INDEPENDENT_REVIEW.json'
    need(not output.exists(), 'new output path')
    report = {'schema': 'razr-r5-native-cloud-v5-bootstrap-independent-review-v1',
              'completed': False, 'passed': False, 'limits': LIMITS,
              'new_native_or_runtime_execution': False, 'frozen_sources_imported': False,
              'actual_controls_reexecuted': False, 'historical_host_Python_version_inferred': False}
    try:
        lock = read(NEW / 'SOURCE_LOCK.json')
        oldlock = read(OLD / 'SOURCE_LOCK.json')
        need(watch(NEW / 'SOURCE_LOCK.json')['sha256'] == '2022447702c349b498916017296e40561e3a1d941f8fcaa60151fdd48a835663', 'literal frozen v5 lock')
        need(watch(OLD / 'SOURCE_LOCK.json')['sha256'] == 'dbf70814f6933b98818338f0a342706161b0b47268ec6da7ddf36ef3d4be13b4', 'literal frozen v4 lock')
        prior = ROOT / 'r5-integration/independent-native-cloud-v4-ascii-review/R5_NATIVE_CLOUD_V4_ASCII_INDEPENDENT_REVIEW.json'
        need(watch(prior)['sha256'] == 'e648836307b44c2ff48f53fd24052a006245f82dd3a87e72d91440680c181de3', 'prior actual independent v4 audit identity')
        for name, row in lock['asset_files'].items():
            need(watch(NEW / name) == row, 'v5 asset bytes: ' + name)
        for name in ('qualify_fresh_runtime_r5.py', 'run_fresh_runtime_script_r5.py',
                     'r5-native-fresh-hosted-v1.yml', 'R5_CLOUD_NATIVE_SCIENCE_TEMPLATE.json'):
            need(watch(NEW / name) == watch(OLD / name), 'exact unchanged runtime/science/always contract: ' + name)
        need(lock['original_six_native_limits_unchanged'] == oldlock['original_six_native_limits_unchanged'], 'all six original native resource gates unchanged')
        oldsource = (OLD / 'register_cloud_native_r5.py').read_text()
        newsource = (NEW / 'register_cloud_native_r5.py').read_text()
        watch(OLD / 'register_cloud_native_r5.py')
        oldtree = ast.parse(oldsource, feature_version=(3, 10))
        newtree = ast.parse(newsource, feature_version=(3, 10))
        identity_node = next(n for n in newtree.body if isinstance(n, ast.FunctionDef) and n.name == 'identity')
        expected = ast.parse("def identity(path):\n    path = Path(path)\n    digest = hashlib.sha256()\n    with path.open('rb') as stream:\n        for chunk in iter(lambda: stream.read(1024 * 1024), b''):\n            digest.update(chunk)\n    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}\n").body[0]
        need(ast.dump(identity_node, include_attributes=False) == ast.dump(expected, include_attributes=False), 'portable complete-stream hash AST exactly specified')
        observations = [v for n in ast.walk(newtree) if isinstance(n, ast.Dict) for k, v in zip(n.keys, n.values)
                        if isinstance(k, ast.Constant) and k.value == 'bootstrap_interpreter_observation']
        need(len(observations) == 1, 'exactly one bootstrap observation')
        need(normal(oldtree) == normal(newtree), 'whole registrar AST equality after only hash function/sys import/observation removal')
        need('hashlib.file_digest(' not in newsource, 'no missing optional hash API call in bootstrap registrar')
        need('extractall(' not in newsource and 'filter=' not in newsource, 'bootstrap archive extraction independent of optional filter APIs')
        manifest = read(NEW / 'SCIENTIFIC_INPUT_MANIFEST.json')
        oldmanifest = read(OLD / 'SCIENTIFIC_INPUT_MANIFEST.json')
        need(manifest['archive_identity'] == watch(NEW / 'scientific-inputs.tar.gz'), 'scientific archive identity')
        need(manifest['member_count'] == len(manifest['members']) == 161, 'complete 161 member scientific archive')
        names = []
        decoded = 0
        with tarfile.open(NEW / 'scientific-inputs.tar.gz', 'r:gz') as archive:
            for member in archive:
                need(member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts, 'safe regular scientific member')
                names.append(member.name)
                decoded += member.size
                need(decoded <= LIMITS['maximum_scientific_archive_decoded_bytes'], 'archive decoded budget')
                data = archive.extractfile(member).read()
                got = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                need(got == manifest['members'][member.name] == watch(ROOT / member.name), 'tar/manifest/original equality: ' + member.name)
        need(len(names) == len(set(names)) and set(names) == set(manifest['members']), 'unique complete scientific members')
        need(decoded == manifest['uncompressed_bytes'] == 3786599, 'scientific decoded byte count')
        removed = set(oldmanifest['members']) - set(manifest['members'])
        need(removed == {'r5-native/cloud-native-v1/build_cloud_native_packet_r5.py'}, 'only superseded build filename relocated')
        for name, row in oldmanifest['members'].items():
            target = 'r5-native/cloud-native-v1/build_cloud_native_packet_r5_v4_frozen.py' if name in removed else name
            need(manifest['members'][target] == row, 'all 155 prior scientific bytes preserved: ' + name)
        controls_path = BASE / 'bootstrap-v5/R5_BOOTSTRAP_V5_CONTROLS_ACTUAL.json'
        controls = read(controls_path)
        control_source = BASE / 'check_bootstrap_compatibility_r5_v5.py'
        need(watch(control_source) == controls['control_source_identity'], 'actual compatibility control source identity')
        need(controls['old_registrar_identity'] == watch(OLD / 'register_cloud_native_r5.py') and controls['new_registrar_identity'] == watch(NEW / 'register_cloud_native_r5.py'), 'controls exercised exact old/new registrar functions')
        need(controls['completed'] and len(controls['controls']) == controls['control_count'] == 22, 'all 22 actual compatibility controls recorded')
        census = Counter(r['kind'] for r in controls['controls'])
        need(census == {'exact_old_identity_missing_API': 1, 'complete_frozen_asset_hash_without_optional_API': 13,
                        'known_chunk_boundary_bytes': 6, 'changed_byte_at_chunk_boundary_rejected': 1,
                        'missing_file_rejected': 1}, 'complete actual compatibility control census')
        for row in controls['controls']:
            if row['kind'] == 'complete_frozen_asset_hash_without_optional_API':
                need(row['matched'] and row['identity'] == watch(OLD / row['path']), 'actual full asset control binding')
            elif row['kind'] == 'known_chunk_boundary_bytes':
                size = row['identity']['bytes']
                data = (bytes(range(251)) * (size // 251 + 1))[:size]
                need(row['matched'] and hashlib.sha256(data).hexdigest() == row['identity']['sha256'], 'independent chunk fixture digest')
            elif row['kind'] == 'exact_old_identity_missing_API':
                need(row['old_failure_reproduced'] and row['type'] == 'AttributeError' and 'file_digest' in row['message'], 'original missing API failure retained')
            elif row['kind'] == 'changed_byte_at_chunk_boundary_rejected':
                need(row['different'] and row['before']['bytes'] == row['after']['bytes'] and row['before']['sha256'] != row['after']['sha256'], 'byte mutation detected')
            else:
                need(row['type'] == 'FileNotFoundError', 'missing input refused')
        need(not controls['blocked_native_import_attempts'] and not controls['native_numeric_modules_loaded'] and controls['native_or_runtime_qualification_executed'] is False, 'no native/numeric qualification in compatibility controls')
        controltext = control_source.read_text()
        for token in ('del hashlib.file_digest', "runpy.run_path(str(old)", "runpy.run_path(str(new)", "old_ns['identity'](old)", "new_ns['identity'](path)"):
            need(token in controltext, 'actual missing-API controls invoke real functions: ' + token)
        historical = []
        for record in controls['actual_v4_core_and_near_bootstrap_failure_readback']:
            archive_path = ROOT / record['archive_path']
            log_path = ROOT / record['actual_log_path']
            need(watch(archive_path) == record['archive_identity'] and watch(log_path) == record['actual_log_identity'], 'actual v4 CI artifact/log binding')
            with zipfile.ZipFile(archive_path) as archive:
                prefix = record['actual_case_prefix']
                for name, row in record['exact_observed_member_identities'].items():
                    data = archive.read(prefix + name)
                    need({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == row, 'actual failure member exact: ' + name)
                need(archive.read(prefix + 'environment-after.exit-code.txt') == b'not_executed\n', 'always refuses missing environment qualification')
                state = json.loads(archive.read(prefix + 'environment-after-state.json'))
                need(state == {'status': 'not_executed', 'wrapper_exit_code': 'not_executed', 'checker_report_exists': False, 'passed': False}, 'unqualified environment state retained')
                need(all(prefix + name not in archive.namelist() for name in record['absent_unexecuted_reports']), 'native/runtime reports were never created')
            log = log_path.read_text()
            need("AttributeError: module 'hashlib' has no attribute 'file_digest'" in log and 'File "<stdin>", line 32, in <module>' in log, 'actual bootstrap failure and unchanged always assertion')
            historical.append({'path': record['archive_path'], 'identity': record['archive_identity'],
                               'bootstrap_failure': 'hashlib.file_digest unavailable', 'native_or_runtime_started': False,
                               'always_assertion_correctly_refuses_unexecuted_environment': True})
        for path, before in list(watched.items()):
            need(identity(Path(path)) == before, 'all watched input bytes unchanged: ' + str(Path(path).relative_to(ROOT)))
        report.update(completed=True, passed=True, source_lock_identity=watch(NEW / 'SOURCE_LOCK.json'),
                      exact_registrar_AST_delta_verified=True, actual_compatibility_controls=22,
                      scientific_archive_members=161, original_155_scientific_member_bytes_preserved=True,
                      original_argv_17_and_ASCII_28_control_bytes_preserved=True,
                      all_six_original_native_limits_unchanged=True, actual_v4_failures=historical,
                      permits_exact_v5_original_gate_Actions_submission=True,
                      native_or_runtime_qualification_claimed=False)
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
    finally:
        report.update(seconds=time.monotonic() - started,
                      peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                      hashed_bytes=hashed, watched_input_count=len(watched), checks=checks,
                      watched_inputs=watched)
        output.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({k: report.get(k) for k in ('completed','passed','error','seconds','peak_RSS_bytes','hashed_bytes','watched_input_count')}, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
