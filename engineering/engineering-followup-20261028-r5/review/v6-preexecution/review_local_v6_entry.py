"""Independent static snapshot and local entry review; no model imports."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import signal
import stat
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
LOCAL = ROOT / 'r5-local-v6'
SNAPSHOT = LOCAL / 'input-snapshot-v1'
LOCK_SHA = '5cf2c18e7971912949e7e7167451cf547e291be421f205d78ef668fd7ab5b499'
GATES = {'wall_seconds': 600, 'RSS_limit_bytes': 805306368,
         'shared_ceiling_bytes': 7301444403, 'disk_floor_bytes': 104857600,
         'maximum_output_bytes': 41943040, 'metadata_margin_bytes': 4194304}
streamed = 0


def need(ok, message):
    if not ok:
        raise ValueError(message)


def identity(path):
    global streamed
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open('rb') as source:
        while chunk := source.read(1 << 20):
            streamed += len(chunk)
            need(streamed <= 201326592, 'registered identity-stream budget exceeded')
            digest.update(chunk)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def same_bytes(left, right):
    return all(left[key] == right[key] for key in ('bytes', 'sha256'))


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--launcher', type=Path, required=True)
    parser.add_argument('--launcher-sha256', required=True)
    args = parser.parse_args()
    destination = HERE / 'R5_V6_LOCAL_ENTRY_INDEPENDENT_STATIC_REVIEW.json'
    need(not destination.exists(), 'immutable new local review report required')
    resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
    resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('90 s local static review budget')))
    signal.alarm(90)
    started = time.monotonic()
    budget_path = HERE / 'R5_V6_LOCAL_ENTRY_REVIEW_BUDGET.json'
    result = {
        'schema': 'razr-r5e-v6-independent-local-entry-static-review-v1',
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'completed': False, 'execution_kind': 'static_identity_and_local_entry_only',
        'registered_budget': identity(budget_path), 'audit_source': identity(__file__),
        'V6_model_or_checker_imports': 0, 'V6_worker_executions': 0,
        'V6_mathematical_control_executions': 0, 'native_operations': 0,
        'original_R4_proof_decodes': 0, 'original_owned_gate_admission_claimed': False,
        'workflow_executed': False, 'workflow_publication_verified_here': False,
        'conditional_primitive_support_model_only': True,
        'native_primitive_semantics_verified': False, 'native_trim_class_membership_verified': False,
        'original_raw_gate_reclassified': False, 'full_continuous_G2': False,
        'all_blockers_closed': False,
    }
    try:
        static_path = HERE / 'R5_V6_FINAL_INDEPENDENT_STATIC_REVIEW.json'
        result['final_source_static_review'] = identity(static_path)
        static = json.loads(static_path.read_text())
        need(static['static_review_completed'] is True and static['registered_budget_respected'] is True,
             'completed final source audit required')
        need(static['source_lock']['sha256'] == LOCK_SHA and not static['blocking_static_findings'],
             'final source audit is not the frozen V6 lock')
        readiness_path = LOCAL / 'R5_V6_LOCAL_EXECUTION_READINESS.json'
        result['local_readiness'] = identity(readiness_path)
        readiness = json.loads(readiness_path.read_text())
        need(readiness['source_lock_sha256_literal'] == LOCK_SHA, 'local source lock literal differs')
        need(readiness['formal_worker_executions_so_far'] == 0 and readiness['V6_mathematical_controls_executed_here'] == 0,
             'readiness must remain a preexecution record')
        need(readiness['original_limits_per_stage'] == GATES, 'original owned process limits changed')
        need(readiness['resource_snapshot_is_not_actual_supervisor_admission'] is True and
             readiness['actual_owned_supervisor_must_admit_each_stage'] is True,
             'instant host snapshot cannot substitute for actual owned admission')
        lock = json.loads((ROOT / 'r5-envelope/R5E_PORTABLE_SOURCE_LOCK_V6.json').read_text())
        lock_identity = identity(ROOT / 'r5-envelope/R5E_PORTABLE_SOURCE_LOCK_V6.json')
        need(lock_identity['sha256'] == LOCK_SHA, 'frozen V6 source lock changed')
        public = json.loads((ROOT / 'r5-envelope/R5E_PUBLIC_INPUT_BRIDGE.json').read_text())
        base = json.loads((ROOT / 'r5-envelope/R5E_V6_BASE_V5_INPUT_BRIDGE.json').read_text())
        r4_rows = {r['path']: r for r in lock['r4_source_files']}
        for row in public['files']:
            record = dict(row['public_identity'], path=row['path'])
            need(record['path'] not in r4_rows or same_bytes(record, r4_rows[record['path']]), 'inconsistent original R4 duplicate')
            r4_rows[record['path']] = record
        roots = {
            'source': (ROOT / 'r5-envelope', lock['r5_files'] + [dict(lock_identity, path='R5E_PORTABLE_SOURCE_LOCK_V6.json')]),
            'r4': (ROOT / 'razr-current/engineering/engineering-followup-20261027-r4/envelope', list(r4_rows.values())),
            'base-v5': (ROOT / 'r5-ci-results/run-40645988108', base['files']),
        }
        expected = {}
        for name, (source_root, records) in roots.items():
            for row in records:
                target = SNAPSHOT / name / row['path']
                expected[str(target)] = (source_root / row['path'], row)
        need(len(expected) == 73 and {k: len(v[1]) for k, v in roots.items()} == {'source': 26, 'r4': 22, 'base-v5': 25},
             'exact snapshot census differs')
        actual_paths = {str(p) for p in SNAPSHOT.rglob('*') if p.is_file() or p.is_symlink()}
        need(actual_paths == set(expected), 'missing or extra local snapshot file')
        rows = readiness['source_snapshots']
        need(len(rows) == 73 and len({r['snapshot']['path'] for r in rows}) == 73, 'duplicate or missing readiness snapshot record')
        by_path = {r['snapshot']['path']: r for r in rows}
        need(set(by_path) == set(expected), 'readiness snapshot path set differs')
        result['independently_verified_snapshot_files'] = []
        before = []
        for path, (source_path, record) in sorted(expected.items()):
            target = Path(path)
            need(not target.is_symlink() and not source_path.is_symlink(), 'symlink is not an exact file snapshot')
            need(stat.S_IMODE(target.stat().st_mode) == 0o444, 'snapshot file mode is not 0444')
            original = identity(source_path)
            copied = identity(target)
            need(same_bytes(original, record) and same_bytes(copied, record), 'original/snapshot/lock bytes differ: ' + path)
            entry = by_path[path]
            need(entry['source'] == original and entry['snapshot'] == copied and entry['mode'] == '0444' and
                 entry['original_bytes_changed'] is False, 'recorded snapshot lineage differs: ' + path)
            result['independently_verified_snapshot_files'].append({'original': original, 'snapshot': copied})
            before.append(copied)
        need(sum(row['bytes'] for row in before) == 22979752 == readiness['snapshot_bytes'], 'snapshot byte total differs')
        command = readiness['exact_driver_command']
        expected_command = ['/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3', '-I', '-S', '-B',
                            str(SNAPSHOT / 'source/run_portable_primitive_r5e_v6.py'), '--r4-root', str(SNAPSHOT / 'r4'),
                            '--base-v5-root', str(SNAPSHOT / 'base-v5'), '--output', str(LOCAL / 'attempt-1')]
        need(command == expected_command and readiness['new_output_directory'] == expected_command[-1], 'exact local isolated entry differs')
        need(not Path(expected_command[-1]).exists(), 'preexecution output already exists')
        interpreter = identity(command[0])
        need(interpreter == readiness['python']['executable'] and interpreter['sha256'] == 'fa67443527ed9647f760d807e2a38f26340757123e643c4639cf273ed15d5ea7',
             'literal local interpreter identity differs')
        need(readiness['python']['flags'] == {'isolated': 1, 'no_site': 1, 'optimize': 0}, 'required isolated unoptimized entry flags differ')
        result['exact_driver_command'] = command
        result['bound_interpreter'] = interpreter
        launcher = args.launcher.resolve()
        result['reviewed_local_launcher'] = identity(launcher)
        need(result['reviewed_local_launcher']['sha256'] == args.launcher_sha256, 'local launcher changed after manual review')
        ast.parse(launcher.read_text(), filename=str(launcher))
        result['launcher_parsed_without_execution'] = True
        result['local_entry_manual_findings'] = {
            'fixed_known_V6_lock_checked_before_driver_start': True,
            'complete_snapshot_and_interpreter_hashes_checked_before_driver_start': True,
            'completed_final_source_static_receipt_required_by_launcher': True,
            'this_local_entry_review_required_by_the_execution_coordinator': True,
            'exact_registered_command_not_shell_interpolated': True,
            'driver_retains_all_original_owned_resource_gates': True,
            'no_Git_or_venv_anchor_synthesized': True,
            'prepared_CI_configuration_not_used_as_local_execution_receipt': True,
            'file_mode_read_only_is_not_a_security_boundary_against_the_owner': True,
        }
        result['snapshot_end_identities_unchanged'] = all(identity(row['path']) == row for row in before)
        need(result['snapshot_end_identities_unchanged'], 'local snapshot changed during independent readback')
        result['original_owned_process_gates'] = GATES
        result['source_lock_identity'] = lock_identity
        result['blocking_findings'] = []
        result['completed'] = True
    except BaseException as exc:
        result['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    finally:
        signal.alarm(0)
        result['elapsed_seconds'] = time.monotonic() - started
        result['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        result['identity_stream_bytes'] = streamed
        result['registered_budget_respected'] = result['elapsed_seconds'] <= 90 and result['peak_RSS_bytes'] <= 268435456 and streamed <= 201326592
        result['finished_utc'] = datetime.now(timezone.utc).isoformat()
        encoded = (json.dumps(result, indent=2) + '\n').encode()
        need(len(encoded) <= 4194304, 'registered local review output limit exceeded')
        destination.write_bytes(encoded)
        print(json.dumps({k: result.get(k) for k in ('completed', 'elapsed_seconds', 'peak_RSS_bytes', 'identity_stream_bytes', 'registered_budget_respected', 'failure')}))
    return 0 if result['completed'] and result['registered_budget_respected'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
