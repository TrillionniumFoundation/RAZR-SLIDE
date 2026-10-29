"""Standard-library worker entry with an owned-child identity handshake."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import runpy
import sys


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--supervision-contract', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('worker_arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    contract = json.loads(args.supervision_contract.read_text())
    require(sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.optimize == 0,
            'isolated unoptimized standard-library interpreter required')
    require(sha(__file__) == contract['worker_entry_sha256'], 'entry source differs')
    owned_path = Path(contract['owned_process']['path'])
    require(sha(owned_path) == contract['owned_process']['sha256'], 'owned process source differs')
    spec = importlib.util.spec_from_file_location('r4e_frozen_owned_worker', owned_path)
    owned = importlib.util.module_from_spec(spec); spec.loader.exec_module(owned)
    owned.announce_worker_from_environment(Path(__file__).resolve())
    execution_identity = owned.own_identity()
    execution_nonce = os.environ[owned.NONCE]
    supervision_contract_sha = sha(args.supervision_contract)
    worker = Path(contract['worker']['path'])
    require(sha(worker) == contract['worker']['sha256'], 'mathematical worker source differs')
    report = {'schema': 'razr-r7-owned-pure-math-entry-v1-identity-receipt', 'worker_started': False,
              'worker_exit_code': None, 'native_geometry_imported': False}
    report.update(owned_execution_identity=execution_identity, owned_execution_nonce=execution_nonce,
                  supervision_contract_sha256=supervision_contract_sha)
    actual_args = args.worker_arguments[1:] if args.worker_arguments[:1] == ['--'] else args.worker_arguments
    registered_options = contract['canonical_worker_options']
    require(isinstance(registered_options, list) and registered_options and len(registered_options) == len(set(registered_options)), 'unique registered full worker option schema required')
    require(all(isinstance(value, str) and value.startswith('--') and '=' not in value for value in registered_options), 'registered full long options required')
    require('--contract' in registered_options and '--output' in registered_options, 'registered contract/output options required')
    require(len(actual_args) == 2*len(registered_options), 'exact one-value argument pairs required')
    values = {}
    for option, value in zip(actual_args[::2], actual_args[1::2]):
        require(option in registered_options and option not in values, 'abbreviated, unexpected, equals-form, or duplicate worker option rejected')
        require(not value.startswith('--'), 'explicit option value required')
        values[option] = value
    require(set(values) == set(registered_options), 'complete registered worker argument schema required')
    actual_args = [argument for option in registered_options for argument in (option, values[option])]
    report['canonical_worker_arguments'] = actual_args
    bindings = {}
    for option in ('--contract', '--output'):
        require(not any(value.startswith(option+'=') for value in actual_args), 'use one explicit separated registered '+option)
        indices = [i for i, value in enumerate(actual_args) if value == option]
        require(len(indices) == 1 and indices[0]+1 < len(actual_args), 'exactly one registered '+option+' argument required')
        bindings[option] = Path(actual_args[indices[0]+1]).resolve()
    require(bindings['--output'] == Path(contract['worker_output_directory']).resolve(), 'actual worker output differs from supervised directory')
    require(bindings['--contract'].is_file() and sha(bindings['--contract']) == contract['registered_math_contract_sha256'], 'actual mathematical contract differs from preregistered digest')
    report['actual_argument_bindings'] = {'worker_output_directory': str(bindings['--output']), 'mathematical_contract_path': str(bindings['--contract']), 'mathematical_contract_sha256': contract['registered_math_contract_sha256']}
    sys.argv[:] = [str(worker.resolve()), *actual_args]
    try:
        report['worker_started'] = True
        runpy.run_path(str(worker.resolve()), run_name='__main__')
        report['worker_exit_code'] = 0
    except SystemExit as exc:
        report['worker_exit_code'] = exc.code if isinstance(exc.code, int) else 0 if exc.code is None else 1
    finally:
        report['entry_and_worker_and_owned_source_unchanged'] = (
            sha(__file__) == contract['worker_entry_sha256'] and
            sha(worker) == contract['worker']['sha256'] and
            sha(owned_path) == contract['owned_process']['sha256'])
        report['owned_execution_identity_unchanged'] = owned.own_identity() == execution_identity
        report['supervision_contract_unchanged'] = sha(args.supervision_contract) == supervision_contract_sha
        report['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        report['native_geometry_imported'] = any(name == 'OCP' or name.startswith('OCP.') or
            name == 'cadquery' or name.startswith('cadquery.') for name in sys.modules)
        report['completed'] = (report['worker_exit_code'] == 0 and
            report['entry_and_worker_and_owned_source_unchanged'] and
            report['owned_execution_identity_unchanged'] and report['supervision_contract_unchanged'] and
            report['peak_RSS_bytes'] <= contract['RSS_limit_bytes'] and not report['native_geometry_imported'])
        args.receipt.write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
