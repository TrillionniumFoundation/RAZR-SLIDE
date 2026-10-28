"""Standard-library worker entry with an owned-child identity handshake."""
import argparse
import hashlib
import importlib.util
import json
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
    worker = Path(contract['worker']['path'])
    require(sha(worker) == contract['worker']['sha256'], 'mathematical worker source differs')
    report = {'schema': 'razr-r4e-owned-pure-math-entry-v1', 'worker_started': False,
              'worker_exit_code': None, 'native_geometry_imported': False}
    actual_args = args.worker_arguments[1:] if args.worker_arguments[:1] == ['--'] else args.worker_arguments
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
        report['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        report['native_geometry_imported'] = any(name == 'OCP' or name.startswith('OCP.') or
            name == 'cadquery' or name.startswith('cadquery.') for name in sys.modules)
        report['completed'] = (report['worker_exit_code'] == 0 and
            report['entry_and_worker_and_owned_source_unchanged'] and
            report['peak_RSS_bytes'] <= contract['RSS_limit_bytes'] and not report['native_geometry_imported'])
        args.receipt.write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
