"""Bounded read-only examination of the existing wheel cleanup discrepancy.

Never execute the qualifier, import its dependencies, download a wheel, remove
a scratch member, or change an original report.  This examination establishes
what the existing records can and cannot prove; it is not a new scientific gate.
"""
from pathlib import Path
import argparse
import ast
import datetime
import hashlib
import json
import os
import resource
import signal
import stat
import time
import traceback

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / 'r7-audit/runtime-cleanup-correspondence'
PLAN = OUT / 'R7_EXISTING_CLEANUP_CORRESPONDENCE_READ_PLAN_V1.json'
RESULT = OUT / 'R7_EXISTING_CLEANUP_CORRESPONDENCE_ACTUAL_V1.json'
SCRATCH = BASE / 'r7-native/qualification-wheel-scratch-v1'
INPUTS = {
    'qualifier_source': BASE / 'r7-native/qualify_fresh_runtime_r7_v1.py',
    'qualification_report': BASE / 'r7-native/native80-attempt1/qualify-owned/worker/R5_FRESH_RUNTIME_QUALIFICATION.json',
    'qualification_contract': BASE / 'r7-native/native80-attempt1/qualify-contract.json',
    'original_supervision': BASE / 'r7-native/native80-attempt1/qualify-owned/controller.json',
    'earlier_scratch_observation': BASE / 'r7-native/R7_POSTQUALIFICATION_SCRATCH_REOBSERVATION_V1.json',
    'existing_full_payload_readback': BASE / 'r7-audit/native-stage-v4-review/R7_ACTUAL_RUNTIME_QUALIFICATION_INDEPENDENT_FULL_READBACK_V2.json',
    'existing_original_vtk_wheel': SCRATCH / 'vtk.whl',
}
MAX_WALL = 30
MAX_AS = 128 * 2**20
MAX_INPUT = 128 * 2**20
MAX_OUTPUT = 2**20


class ReadBudgetExceeded(BaseException):
    pass


def need(value, message):
    if not value:
        raise ValueError(message)


def identity(path):
    need(stat.S_ISREG(path.lstat().st_mode), 'Original regular non-symlink file required')
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(2**20), b''):
            size += len(chunk)
            digest.update(chunk)
    need(size == path.stat().st_size, 'Size changed while reading')
    return {'bytes': size, 'sha256': digest.hexdigest()}


def load(path):
    return json.loads(path.read_bytes())


def save(path, obj):
    need(not path.exists(), 'New immutable examination artifact required')
    data = (json.dumps(obj, indent=2, allow_nan=False) + '\n').encode()
    need(len(data) <= MAX_OUTPUT, 'Registered output bound exceeded')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def utc_ns(value):
    seconds, remainder = divmod(value, 10**9)
    return datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S') + f'.{remainder:09d}Z'


def metadata(path):
    s = path.lstat()
    return {'relative': path.relative_to(BASE).as_posix(), 'mode': s.st_mode, 'bytes': s.st_size,
            'inode': s.st_ino, 'device': s.st_dev, 'link_count': s.st_nlink,
            'mtime_ns': s.st_mtime_ns, 'ctime_ns': s.st_ctime_ns,
            'mtime_utc': utc_ns(s.st_mtime_ns), 'ctime_utc': utc_ns(s.st_ctime_ns)}


def scratch_members():
    need(stat.S_ISDIR(SCRATCH.lstat().st_mode), 'Current scratch must be a real directory')
    result = {}
    for path in sorted(SCRATCH.iterdir()):
        need(stat.S_ISREG(path.lstat().st_mode), 'Unexpected current scratch special entry')
        result[path.name] = metadata(path)
    return result


def register():
    records = {name: {'path': path.relative_to(BASE).as_posix(), 'identity': identity(path)} for name, path in INPUTS.items()}
    total = sum(row['identity']['bytes'] for row in records.values())
    need(total <= MAX_INPUT, 'Registered read input bound exceeded')
    output = {'schema': 'razr-r7-existing-cleanup-correspondence-read-plan-v1',
              'registered_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'source': {'path': Path(__file__).resolve().relative_to(BASE).as_posix(), 'identity': identity(Path(__file__))},
              'inputs': records, 'input_bytes': total, 'current_scratch_members': scratch_members(),
              'limits': {'wall_seconds': MAX_WALL, 'address_space_bytes': MAX_AS,
                         'input_bytes': MAX_INPUT, 'output_bytes': MAX_OUTPUT},
              'qualification_rerun': False, 'new_CAD_or_dependency_import': False,
              'original_input_or_wheel_mutation': False,
              'scope': 'Existing source, original 43 wheel records, original supervision, prior readback, and current original vtk inode/content/timestamps; no platform-cause inference.'}
    save(PLAN, output)
    print(json.dumps({'plan': str(PLAN), 'identity': identity(PLAN), 'input_bytes': total}))


def examine():
    resource.setrlimit(resource.RLIMIT_AS, (MAX_AS, MAX_AS))
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(ReadBudgetExceeded('Registered 30-second read wall budget exceeded')))
    signal.alarm(MAX_WALL)
    output = {'schema': 'razr-r7-existing-cleanup-correspondence-actual-v1', 'completed': False,
              'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'plan_identity': identity(PLAN), 'reviewer_identity': identity(Path(__file__)),
              'new_scientific_gate': False, 'qualification_rerun': False,
              'original_input_or_wheel_mutation': False}
    try:
        c = load(PLAN)
        need(c['source']['identity'] == output['reviewer_identity'], 'Registered read source changed')
        for name, path in INPUTS.items():
            need(identity(path) == c['inputs'][name]['identity'], 'Frozen read input changed: ' + name)
        before = scratch_members()
        need(before == c['current_scratch_members'], 'Current scratch metadata changed since registration')
        source = INPUTS['qualifier_source'].read_text()
        tree = ast.parse(source)
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        wheel_loop = next(n for n in ast.walk(main) if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == 'distribution')
        path_assignments = [n for n in ast.walk(wheel_loop) if isinstance(n, ast.Assign)
                            and any(isinstance(t, ast.Name) and t.id == 'path' for t in n.targets)]
        need(len(path_assignments) == 1 and ast.unparse(path_assignments[0].value) == "scratch / (name + '.whl')",
             'Unexpected wheel pathname reassignment')
        cleanup = next(n for n in ast.walk(wheel_loop) if isinstance(n, ast.Try) and n.finalbody)
        need(len(cleanup.finalbody) == 2 and isinstance(cleanup.finalbody[0], ast.If), 'Original cleanup control structure changed')
        need(ast.unparse(cleanup.finalbody[0].test) == 'path.exists()', 'Original cleanup existence test changed')
        need(ast.unparse(cleanup.finalbody[0].body[0]) == 'path.unlink()', 'Original cleanup unlink call changed')
        need(ast.unparse(cleanup.finalbody[1]) == "observation['transient_download_removed_after_verification'] = not path.exists()",
             'Original cleanup observation semantics changed')
        open_calls = [n for n in ast.walk(wheel_loop) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                      and isinstance(n.func.value, ast.Name) and n.func.value.id == 'path' and n.func.attr == 'open']
        need(len(open_calls) == 1 and ast.unparse(open_calls[0]) == "path.open('xb')", 'Wheel creation path is not the original exclusive open')
        outer = next(n for n in main.body if isinstance(n, ast.Try) and n.finalbody)
        final_names = {n.id for node in outer.finalbody for n in ast.walk(node) if isinstance(n, ast.Name)}
        need('scratch' not in final_names and 'venv' in final_names, 'Original final inventory scope changed')
        later_source_scratch_mentions = [n.lineno for n in ast.walk(main) if isinstance(n, ast.Name)
                                        and n.id == 'scratch' and n.lineno > wheel_loop.end_lineno]
        need(not later_source_scratch_mentions, 'Qualifier source has a later explicit scratch use')
        report = load(INPUTS['qualification_report'])
        contract = load(INPUTS['qualification_contract'])
        supervision = load(INPUTS['original_supervision'])
        earlier = load(INPUTS['earlier_scratch_observation'])
        payload_readback = load(INPUTS['existing_full_payload_readback'])
        need(report['qualifier_identity'] == contract['qualifier_identity'] == c['inputs']['qualifier_source']['identity'], 'Original source bindings differ')
        need(report['contract_identity'] == c['inputs']['qualification_contract']['identity'], 'Original contract binding differs')
        need(Path(contract['wheel_scratch']).resolve() == SCRATCH, 'Original current scratch mapping differs')
        records = report['wheel_observations']
        names = [row['name'] for row in records]
        need(len(records) == len(set(names)) == 43 and names == sorted(names), 'Original complete unique wheel order differs')
        correspondence = []
        for order, record in enumerate(records, 1):
            current = before.get(record['name'] + '.whl')
            locked = {'bytes': record['locked_wheel']['size'], 'sha256': record['locked_wheel']['hash'].removeprefix('sha256:')}
            need(record['download_completed'] and record['actual_download_identity'] == locked, 'Original locked download record differs')
            need(record['transient_download_removed_after_verification'] is True, 'Original recorded cleanup flag differs')
            correspondence.append({'order': order, 'original_record': record,
                                   'source_computed_path': (SCRATCH / (record['name'] + '.whl')).relative_to(BASE).as_posix(),
                                   'current_directory_member_observed': current is not None,
                                   'current_metadata': current})
        need(set(before) == {'vtk.whl'}, 'Current actual scratch member set differs from the reviewed discrepancy')
        vtk = next(row for row in records if row['name'] == 'vtk')
        current_vtk_identity = c['inputs']['existing_original_vtk_wheel']['identity']
        need(current_vtk_identity == vtk['actual_download_identity'], 'Current vtk is not byte-identical to the original locked download')
        previous_vtk = next(row for row in earlier['actual_scratch_members'] if row['relative'] == 'vtk.whl')
        same_previous = all(before['vtk.whl'][key] == previous_vtk[key]
                            for key in ('mode', 'bytes', 'inode', 'device', 'mtime_ns', 'ctime_ns'))
        need(same_previous and previous_vtk['sha256'] == current_vtk_identity['sha256'], 'Earlier actual observed vtk identity/metadata differs')
        need(report['completed'] and not report['issues'] and supervision['completed'] and supervision['resource_stop'] is None and supervision['exit_code'] == 0,
             'Original qualification result changed')
        lines = source.splitlines()
        ranges = [(163, 186), (190, 198), (232, 246), (363, 379)]
        excerpts = [{'start_line': a, 'end_line': b, 'text': '\n'.join(lines[a-1:b]) + '\n'} for a, b in ranges]
        for name, path in INPUTS.items():
            need(identity(path) == c['inputs'][name]['identity'], 'Original input changed during read: ' + name)
        need(scratch_members() == before, 'Scratch metadata or complete set changed during read')
        need(identity(PLAN) == output['plan_identity'] and identity(Path(__file__)) == output['reviewer_identity'], 'Read plan or source changed')
        need(time.monotonic() - started <= MAX_WALL, 'Whole read exceeded registered wall budget')
        output.update(completed=True, exact_input_identities=c['inputs'], original_source_excerpts=excerpts,
                      all_43_original_download_records=correspondence,
                      current_vtk_identity=current_vtk_identity,
                      current_vtk_same_inode_size_hash_mode_mtime_ctime_as_previous_observation=same_previous,
                      original_qualification_report_current_metadata=metadata(INPUTS['qualification_report']),
                      original_supervision_time_interval={'started_utc': supervision['started_utc'], 'finished_utc': supervision['finished_utc']},
                      source_semantics={
                          'exclusive_download_creation': "path.open('xb') inside the selected wheel try block",
                          'each_wheel_path_assignment_count': len(path_assignments),
                          'each_normalized_distribution_path_is_unique': True,
                          'vtk_record_order_of_43': names.index('vtk') + 1,
                          'later_download_names': names[names.index('vtk') + 1:],
                          'cleanup_field_is_one_immediate_path_exists_observation_in_finally': True,
                          'cleanup_field_is_not_a_saved_unlink_syscall_or_inode_receipt': True,
                          'per_wheel_cleanup_timestamps_or_deleted_inode_recorded': False,
                          'report_saves_overwrite_one_report_file_without_a_per_wheel_history_journal': True,
                          'final_full_inventory_target_is_venv_not_external_scratch': True,
                          'explicit_scratch_reuse_after_wheel_loop_in_qualifier_source': False,
                      },
                      interpretation={
                          'concrete_source_path_alias_or_recreation_logic_found': False,
                          'physical_unlink_or_reappearance_cause_proved': False,
                          'timestamp_caveat': 'The current mtime and ctime are inode metadata, not a creation time or a deletion/recreation event journal. Neither locates the omitted per-wheel existence observation in time.',
                          'evidence_gap': 'The persisted boolean records one existence check. No per-wheel syscall result, event timestamp, or deleted inode was preserved, and there is no final scratch inventory in the original report. Existing artifacts cannot determine the cause of the later visible byte-identical vtk wheel.',
                          'historical_removed_flags_correspondence_to_current_scratch_state': 'Unresolved; both original flags and current file retained.',
                          'platform_or_kernel_cause_inferred': False,
                          'original_qualification_or_native_scientific_results_reclassified': False,
                          'new_scientific_gate_introduced': False,
                          'cleanup_discrepancy_closed': False,
                      },
                      source_report_contract_wheel_and_previous_receipts_unchanged=True,
                      full_continuous_G2=False, physical_qualification=False, all_blockers_closed=False)
    except BaseException as exc:
        output['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    finally:
        signal.alarm(0)
        output.update(seconds=time.monotonic() - started,
                      peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
        save(RESULT, output)
    print(json.dumps({'result': str(RESULT), 'identity': identity(RESULT), 'completed': output['completed'],
                      'seconds': output['seconds'], 'peak_RSS_bytes': output['peak_RSS_bytes'],
                      'causal_explanation_proved': output.get('interpretation', {}).get('physical_unlink_or_reappearance_cause_proved'),
                      'failure': output.get('failure')}))
    return 0 if output['completed'] else 2


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('action', choices=('register', 'examine'))
    args = parser.parse_args()
    if args.action == 'register':
        register()
        return 0
    return examine()


if __name__ == '__main__':
    raise SystemExit(main())
