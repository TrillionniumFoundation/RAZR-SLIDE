"""Run a bound script only after actual fresh lock-runtime qualification.

Every venv file is compared before and after the script in the same owned
process. The unchanged native supervisor still owns the study worker and all
six original resource gates. Full-factory child module origins are not falsely
claimed to be observable from this parent entry.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import resource
import runpy
import sys
import sysconfig
import time


def identity(path):
    path = Path(path)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes': path.stat().st_size, 'sha256': digest}


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    actual_entry_argv = list(sys.argv[1:])
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('script_arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.script_arguments[:1] == ['--']:
        args.script_arguments = args.script_arguments[1:]
    contract = json.loads(args.contract.read_text())
    require(identity(__file__) == contract['entry_identity'], 'Fresh runtime entry source changed')
    expected_entry_argv = ['--contract', contract['expected_entry_contract'],
                           '--receipt', contract['expected_receipt'], '--',
                           *contract['expected_script_arguments']]
    require(actual_entry_argv == expected_entry_argv,
            'Actual entry argv differs from complete registered argv; extras, duplicates, equals and abbreviations are rejected')
    require(str(args.contract) == contract['expected_entry_contract'] and str(args.receipt) == contract['expected_receipt'],
            'Actual entry contract or receipt path differs')
    require(args.script_arguments == contract['expected_script_arguments'], 'Actual payload arguments differ')
    require(not args.receipt.exists(), 'Fresh runtime receipt path required')
    require(sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.no_site and not sys.flags.optimize,
            'Genuine isolated -I -B venv entry required')
    started = time.monotonic()
    report = {'schema': 'razr-r5-current-runtime-entry-v1', 'completed': False,
              'entry_identity': identity(__file__), 'contract_identity': identity(args.contract),
              'actual_entry_argv': actual_entry_argv, 'expected_entry_argv': expected_entry_argv,
              'complete_entry_argv_and_receipt_bound': True,
              'actual_script_arguments': list(args.script_arguments),
              'qualified_runtime_before': False, 'qualified_runtime_after': False,
              'payload_started': False, 'payload_exit_code': None, 'issues': [],
              'historical_runtime_qualification_reused': False,
              'child_module_origins_observed': False, 'module_origins_in_this_entry_process': [],
              'native_gate_numbers_changed': False, 'physical_qualification': False}
    qualifier = None
    qualification = None
    code = 2
    try:
        for item in contract['bound_sources']:
            require(identity(item['path']) == item['identity'], 'Bound source changed: ' + item['path'])
        qref = contract['qualification']
        require(identity(qref['path']) == qref['identity'], 'Actual new qualification changed')
        qualification = json.loads(Path(qref['path']).read_text())
        require(qualification['completed'] and qualification['fresh_wheels_and_installed_RECORDs_verified'] and
                qualification['all_new_runtime_files_unchanged'], 'Actual new runtime did not qualify')
        report['actual_new_qualification'] = qref
        spec = importlib.util.spec_from_file_location('r5_fresh_runtime_audit_helpers', contract['qualifier_source'])
        qualifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(qualifier)
        venv = Path(qualification['venv'])
        require(Path(sys.prefix).resolve() == venv and Path(sys.executable).resolve() == Path(qualification['interpreter']['resolved_binary']), 'Entry uses a different current interpreter')
        require(identity(Path(sys.executable).resolve()) == qualification['interpreter']['binary_identity'], 'Current interpreter binary changed')
        require(list(sys.path) == qualification['search_paths_before_imports'], 'Current isolated path set differs from new qualification')
        observed = qualifier.inventory(venv)
        require(observed == qualification['venv_files_before'], 'Current runtime files changed before study')
        report['qualified_runtime_before'] = True
        report['runtime_inventory_before_sha256'] = qualifier.canonical(observed)
        require({k: importlib.metadata.version(k) for k in qualification['actual_43_package_versions']} == qualification['actual_43_package_versions'], 'Current 43 versions changed')
        script = Path(contract['script']).resolve()
        require(identity(script) == contract['script_identity'], 'Bound study script changed')
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        os.environ['MPLCONFIGDIR'] = str(args.receipt.parent / (args.receipt.stem + '-matplotlib-cache'))
        os.environ['XDG_CACHE_HOME'] = str(args.receipt.parent / (args.receipt.stem + '-cache'))
        sys.path.insert(0, str(script.parent))
        sys.argv = [str(script), *contract['expected_script_arguments']]
        report['actual_payload_argv'] = list(sys.argv)
        report['payload_started'] = True
        try:
            runpy.run_path(str(script), run_name='__main__')
            code = 0
        except SystemExit as exc:
            code = 0 if exc.code is None else exc.code if isinstance(exc.code, int) else 2
            if not isinstance(exc.code, (int, type(None))):
                report['payload_SystemExit_text'] = str(exc.code)
        report['payload_exit_code'] = code
    except BaseException as exc:
        report['issues'].append({'type': type(exc).__name__, 'message': str(exc)})
        code = 2
    finally:
        try:
            if qualifier is not None and qualification is not None:
                current = qualifier.inventory(Path(qualification['venv']))
                report['qualified_runtime_after'] = current == qualification['venv_files_before']
                report['runtime_inventory_after_sha256'] = qualifier.canonical(current)
                before = qualification['venv_files_before']
                report['changed_runtime_files'] = sorted(set(before) ^ set(current)) + sorted(k for k in set(before) & set(current) if before[k] != current[k])
                report['43_versions_unchanged'] = {k: importlib.metadata.version(k) for k in qualification['actual_43_package_versions']} == qualification['actual_43_package_versions']
                site = Path(qualification['site_packages'])
                stdlib = [Path(sysconfig.get_path(key)).resolve() for key in ('stdlib', 'platstdlib')]
                owned = {Path(x['path']).resolve() for x in contract['bound_sources']}
                owned.add(Path(__file__).resolve())
                def origin_scope(origin):
                    path = Path(origin)
                    if path.is_relative_to(site):
                        return 'qualified_current_site'
                    if path.resolve() in owned:
                        return 'bound_study_source'
                    if 'site-packages' in path.parts or 'dist-packages' in path.parts:
                        return None
                    if any(path.is_relative_to(base) for base in stdlib):
                        return 'stdlib'
                    return None
                for name, module in list(sys.modules.items()):
                    origin = getattr(module, '__file__', None)
                    if origin:
                        report['module_origins_in_this_entry_process'].append({'name': name, 'origin': origin, 'scope': origin_scope(origin)})
                report['module_origins_within_bound_scope'] = all(x['scope'] is not None for x in report['module_origins_in_this_entry_process'])
            report['all_bound_sources_unchanged'] = all(identity(x['path']) == x['identity'] for x in contract['bound_sources'])
            report['contract_and_entry_unchanged'] = identity(args.contract) == report['contract_identity'] and identity(__file__) == contract['entry_identity']
            report['completed'] = code == 0 and report['qualified_runtime_before'] and report['qualified_runtime_after'] and report.get('43_versions_unchanged', False) and report.get('module_origins_within_bound_scope', False) and report['all_bound_sources_unchanged'] and report['contract_and_entry_unchanged']
        except BaseException as exc:
            report['issues'].append({'postflight_type': type(exc).__name__, 'message': str(exc)})
        report['seconds'] = time.monotonic() - started
        report['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        raw = (json.dumps(report, indent=2, allow_nan=False) + '\n').encode()
        require(len(raw) <= contract['maximum_receipt_bytes'], 'Fresh runtime receipt budget exceeded')
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_bytes(raw)
    print(json.dumps({k: report[k] for k in ('completed', 'qualified_runtime_before', 'qualified_runtime_after', 'payload_exit_code', 'issues')}), flush=True)
    return 0 if report['completed'] else code if code else 2


if __name__ == '__main__':
    raise SystemExit(main())
