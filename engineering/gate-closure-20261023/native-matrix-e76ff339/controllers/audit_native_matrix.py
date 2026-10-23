"""Read-only native receipts: strict ten-job closure and conservative region sums."""
from __future__ import annotations
import argparse
import ast
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import yaml

ROOT = Path('/workspace/scratch/95cd2986fdf2/RAZR-SLIDE')
BASE = Path('/workspace/scratch/95cd2986fdf2/ci_audit')
FIRST = BASE/'native-matrix-e76ff339-final/report.json'
CONTINUATION = Path('/tmp/razr-native-matrix-e76ff339-remaining/report.json')
EXPECTED = 'e76ff339cbd38610b42f550d1d990131233c8f7d'
PATCHED = {'translation_regions.py', 'verify_serviceable_pawl.py',
           'product_motion.py', 'verify_mounted_mechanism.py', 'validate_cover_capture.py',
           'verify_endpoint_joint_pawl.py', 'verify_thin_mechanism.py', 'verify_pawl_box_guide.py',
           'contact_motion_gate.py', 'keycover_motion_gate.py', 'admission_motion_gate.py',
           'verify_contact_motion.py', 'verify_keycover_motion.py'}
TOL = 1e-7
sys.path.insert(0, str(ROOT))
from tools.verify import snapshot, committed_bytes, sha
from tools.check_environment import inspect_environment


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw_files(report_path, job):
    """Verify every original byte against the execution inventory, including archives."""
    files = job['files']
    require(len({f['path'] for f in files}) == len(files), 'duplicate original file')
    for item in files:
        p = Path(item['path'])
        require(not p.is_absolute() and '..' not in p.parts, 'unsafe original file path')
    prepared = BASE/'native-matrix-e76ff339-archives'/(job['id']+'.tar.gz')
    compression = job.get('compression')
    prepared_index = prepared.with_name('DELIVERY_MANIFEST.json')
    if prepared.exists() and prepared_index.exists():
        index = json.loads(prepared_index.read_text())
        matches = [row for row in index['completed_archives'] if row['job'] == job['id']]
        require(len(matches) == 1, 'prepared archive identity missing or duplicate')
        entry = matches[0]
        require(entry['executed_source_commit'] == EXPECTED and entry['original_files'] == len(files)
                and entry['original_bytes'] == sum(row['bytes'] for row in files), 'prepared archive scope differs')
        require(prepared.stat().st_size == entry['bytes'] and sha(prepared) == entry['sha256'], 'prepared archive changed')
        with tarfile.open(prepared, 'r:gz') as bundle:
            actual = [m.name for m in bundle.getmembers() if m.isfile()]
            wanted = [job['id']+'/'+item['path'] for item in files]
            require(sorted(actual) == sorted(wanted), 'prepared archive regular member coverage differs')
            for item in files:
                data = bundle.extractfile(job['id']+'/'+item['path']).read()
                require(len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'], 'prepared member changed')
                yield item, data
        return
    if compression:
        path = report_path.parent/compression['archive']
        require(path.stat().st_size == compression['bytes'] and sha(path) == compression['sha256'], 'archive changed')
        require(compression['all_regular_members_reread_and_sha256_matched'] is True, 'unverified archive')
        require(compression['original_files'] == files, 'archive inventory differs')
        with tarfile.open(path, 'r:gz') as bundle:
            actual = [m.name for m in bundle.getmembers() if m.isfile()]
            wanted = [job['id']+'/'+item['path'] for item in files]
            require(sorted(actual) == sorted(wanted), 'archive regular member coverage differs')
            for item in files:
                data = bundle.extractfile(job['id']+'/'+item['path']).read()
                require(len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'], 'archived member changed')
                yield item, data
    else:
        folder = report_path.parent/job['id']
        actual = sorted(p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and not p.is_symlink())
        require(actual == sorted(item['path'] for item in files), 'uncompressed file coverage differs')
        for item in files:
            p = folder/item['path']
            require(not p.is_symlink(), 'linked native output')
            data = p.read_bytes()
            require(len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'], 'native output changed')
            yield item, data


def group_receipt(values, pointer, kind, **extra):
    require(values and all(type(x) in (int, float) and math.isfinite(x) and x >= 0 for x in values),
            'empty, invalid signed or nonfinite material partition common')
    total = math.fsum(values)
    maximum = max(values)
    return {'pointer': pointer, 'group_kind': kind, 'regions': len(values),
            'maximum_common_mm3': maximum, 'sum_common_upper_bound_mm3': total,
            'old_per_region_clear': maximum <= TOL, 'summed_upper_bound_clear': total <= TOL, **extra}


def region_groups(value, pointer=''):
    if isinstance(value, dict):
        if 'core_remainder_cage_common_mm3' in value:
            require('pin_complete_relative_path_common_mm3' in value, 'thin STOP partition omits pin')
            yield group_receipt([value['pin_complete_relative_path_common_mm3'],
                                 *value['core_remainder_cage_common_mm3']], pointer,
                                'complete_thin_STOP_core_pin_plus_remainder', stop=value.get('stop'))
        if 'complete_pin_KEY_common_mm3' in value and 'nonpin_cages' in value:
            yield group_receipt([value['complete_pin_KEY_common_mm3'],
                                 *[row['whole_common_with_KEY_mm3'] for row in value['nonpin_cages']]],
                                pointer, 'legacy_complete_STOP_pin_plus_remainder', stop=value.get('stop'))
        for key, child in value.items():
            path = pointer+'/'+key.replace('~', '~0').replace('/', '~1')
            if key in ('region_common_mm3', 'common_mm3', 'commons_mm3') and isinstance(child, list) and all(type(x) in (int, float) for x in child):
                require(all(math.isfinite(x) and x >= 0 for x in child), 'invalid signed or nonfinite region common')
                total = math.fsum(child)
                maximum = max(child, default=0.)
                yield {'pointer': path, 'group_kind': 'retained_region_array', 'regions': len(child), 'maximum_common_mm3': maximum,
                       'sum_common_upper_bound_mm3': total, 'old_per_region_clear': maximum <= TOL,
                       'summed_upper_bound_clear': total <= TOL,
                       'recorded_all_regions_clear': value.get('all_regions_clear'),
                       'recorded_clear': value.get('clear')}
            yield from region_groups(child, path)
    elif isinstance(value, list):
        # These scalar rows cover simultaneous pieces of one moving material,
        # unlike separate poses, different physical pairs, or sequential route legs.
        if value and all(isinstance(row, dict) and {'side', 'piece', 'fixed', 'common_mm3'} <= row.keys()
                         for row in value):
            keys = sorted({(row['side'], row['fixed']) for row in value})
            for side, fixed in keys:
                rows = [row for row in value if (row['side'], row['fixed']) == (side, fixed)]
                require(sorted(row['piece'] for row in rows) == ['body', 'neck', 'round_carrier', 'tongue'],
                        'incomplete box-guide material partition')
                yield group_receipt([row['common_mm3'] for row in rows], pointer,
                                    'complete_box_guide_pawl_and_pin_cover', side=side, fixed=fixed,
                                    bound_scope='Union cover conservatively bounds PAWL and shoulder pin individually.')
        if value and all(isinstance(row, dict) and {'side', 'cover', 'root', 'common_mm3', 'distance_mm'} <= row.keys()
                         for row in value):
            keys = sorted({(row['side'], row['root']) for row in value})
            for side, fixed in keys:
                rows = [row for row in value if (row['side'], row['root']) == (side, fixed) and row['cover'] != 'pin']
                require(sorted(row['cover'] for row in rows) == ['body', 'neck', 'socket', 'tongue'],
                        'incomplete root/lateral PAWL cover')
                yield group_receipt([row['common_mm3'] for row in rows], pointer,
                                    'complete_root_or_lateral_PAWL_cover', side=side, fixed=fixed,
                                    minimum_recorded_distance_mm=min(row['distance_mm'] for row in rows),
                                    additional_positive_distance_guard=True)
        if value and any(isinstance(row, dict) and row.get('kind') in ('complete_PIN_KEY', 'STOP_REMAINDER_KEY')
                         for row in value):
            rows = [row for row in value if isinstance(row, dict) and row.get('kind') in ('complete_PIN_KEY', 'STOP_REMAINDER_KEY')]
            keys = sorted({(row['side'], str(row['part']).split('/')[0]) for row in rows})
            for side, stop in keys:
                selected = [row for row in rows if (row['side'], str(row['part']).split('/')[0]) == (side, stop)]
                require(sum(row['kind'] == 'complete_PIN_KEY' for row in selected) == 1 and
                        sum(row['kind'] == 'STOP_REMAINDER_KEY' for row in selected) == 3,
                        'incomplete independent STOP partition reader')
                yield group_receipt([row['common_mm3'] for row in selected], pointer,
                                    'independent_STOP_pin_plus_remainder_readback', side=side, stop=stop)
        for index, child in enumerate(value):
            yield from region_groups(child, pointer+'/'+str(index))


def import_closure(definitions):
    """Conservative static local import reachability; not runtime call tracing."""
    modules = {p.stem: p for p in (ROOT/'integration').glob('*.py')}
    edges = {}
    for name, path in modules.items():
        dependencies = set()
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                dependencies.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                dependencies.add(node.module.split('.')[0])
        edges[name] = dependencies & modules.keys()
    result = {}
    for job_id, item in definitions.items():
        starts = []
        for line in item['commands'].splitlines():
            if not line.strip():
                continue
            tokens = shlex.split(line)
            require(tokens[:5] == ['uv', 'run', '--locked', 'python', '-B'], 'unexpected Python options in import closure')
            script = Path(tokens[5])
            require(script.parent == Path('integration') and script.suffix == '.py' and script.stem in modules,
                    'workflow entry point missing from import closure')
            starts.append(script.stem)
        paths = {name: [name] for name in starts}
        queue = list(starts)
        while queue:
            name = queue.pop(0)
            for child in sorted(edges.get(name, ())):
                if child not in paths:
                    paths[child] = paths[name]+[child]
                    queue.append(child)
        affected = {name+'.py': [part+'.py' for part in path]
                    for name, path in paths.items() if name+'.py' in PATCHED}
        result[job_id] = {'potentially_affected_files': sorted(affected), 'shortest_local_import_paths': affected,
                          'local_import_closure_source_sha256': {str(modules[name].relative_to(ROOT)): sha(modules[name])
                                                                  for name in sorted(paths) if name in modules}}
    return result


def audit(scan_only=False):
    prior = json.loads(FIRST.read_text())
    close_path = FIRST.with_name('capacity-stop-completion.json')
    close = json.loads(close_path.read_text())
    require(sha(FIRST) == close['original_controller_report_sha256'], 'parent report identity changed')
    require(close['completed_subset_source_and_environment_valid'] is True, 'parent completion check failed')
    require(close['current_head'] == EXPECTED, 'parent completion head differs')
    require(prior['passed'] is False and prior['execution_error']['message'] == 'disk reserve reached before endpoint-joint', 'parent interruption provenance differs')
    attempts = [(FIRST, prior)]
    if CONTINUATION.exists():
        continued = json.loads(CONTINUATION.read_text())
        require(continued['parent_report_sha256'] == sha(FIRST), 'continuation parent differs')
        require(continued['parent_completion_sha256'] == sha(close_path), 'continuation completion differs')
        attempts.append((CONTINUATION, continued))
    workflow = ROOT/'.github/workflows/research-ci.yml'
    definitions = {j['id']: j for j in yaml.safe_load(workflow.read_text())['jobs']['native']['strategy']['matrix']['include']}
    require(len(definitions) == 10, 'expected ten workflow jobs')
    source = prior['source_sha256_before']
    checked_jobs = []
    seen = set()
    changed = []
    summaries = []
    artifact_receipts = []
    for report_path, record in attempts:
        require(record['source_head_before'] == EXPECTED and record['expected_head'] == EXPECTED, 'wrong source head')
        require(record['source_sha256_before'] == source and record['workflow_sha256'] == sha(workflow), 'source or workflow differs across attempts')
        require(record['environment_before']['passed'] is True and record['source_identity_before']['present_tracked_bytes_match_head'] is True, 'preflight not exact')
        if not scan_only and report_path == CONTINUATION:
            require(record['passed'] is True and record['source_head_after'] == EXPECTED, 'continuation incomplete')
            require(record['source_bytes_unchanged'] is True and record['source_sha256_after'] == source, 'continuation source changed')
            require(record['environment_after']['passed'] is True and record['source_identity_after']['present_tracked_bytes_match_head'] is True, 'continuation postflight failed')
        for job in record['jobs']:
            if job['passed'] is not True:
                continue
            name = job['id']
            require(name in definitions and name not in seen, 'unknown or duplicate completed job')
            seen.add(name)
            require(job['source_head_before'] == EXPECTED == job['source_head_after'], 'job head drift')
            require(job['source_bytes_unchanged'] is True and job['present_tracked_bytes_match_head'] is True, 'job source drift')
            lines = [line for line in definitions[name]['commands'].splitlines() if line.strip()]
            require(len(job['commands']) == len(lines), 'missing workflow command')
            temp = report_path.parent/name
            inventory = {item['path']: item for item in job['files']}
            for number, (step, line) in enumerate(zip(job['commands'], lines), 1):
                tokens = shlex.split(line)
                require(tokens[:4] == ['uv', 'run', '--locked', 'python'], 'unexpected workflow prefix')
                command = [str(ROOT/'.venv/bin/python'), *[token.replace('$RUNNER_TEMP', str(temp)) for token in tokens[4:]]]
                require(step['workflow_command'] == line and step['command'] == command, 'executed command differs from workflow')
                require(type(step['exit_code']) is int and step['exit_code'] == 0, 'command did not succeed')
                require(math.isfinite(step['seconds']) and step['seconds'] >= 0, 'invalid command duration')
                log_name = f'command-{number:02d}.log'
                require(step['log'] == log_name and log_name in inventory and
                        step['log_sha256'] == inventory[log_name]['sha256'], 'command log identity differs')
            groups = []
            json_count = 0
            for item, data in raw_files(report_path, job):
                artifact_receipts.append({'job': name, 'path': item['path'], 'sha256': item['sha256'], 'bytes': item['bytes']})
                if not item['path'].endswith('.json'):
                    continue
                value = json.loads(data)
                json_count += 1
                for group in region_groups(value):
                    annotated = {'job': name, 'artifact': item['path'], **group}
                    groups.append(annotated)
                    if group['old_per_region_clear'] and not group['summed_upper_bound_clear']:
                        changed.append(annotated)
                if isinstance(value, dict) and Path(item['path']).name in ('verification.json', 'readback.json', 'load-budget.json'):
                    summaries.append({'job': name, 'artifact': item['path'],
                                      'flags': {k: v for k, v in value.items() if type(v) is bool},
                                      'scope': value.get('scope', value.get('pass_scope'))})
            checked_jobs.append({'id': name, 'seconds': job['seconds'], 'commands': len(lines),
                                 'execution_report': str(report_path), 'execution_report_sha256': sha(report_path),
                                 'output_bytes': job['output_bytes'], 'original_files_verified': len(job['files']),
                                 'json_files_scanned': json_count, 'region_value_groups': len(groups),
                                 'material_partition_groups': sum(g['group_kind'] != 'retained_region_array' for g in groups),
                                 'group_kind_counts': {kind: sum(g['group_kind'] == kind for g in groups)
                                                       for kind in sorted({g['group_kind'] for g in groups})},
                                 'empty_region_value_groups': sum(g['regions'] == 0 for g in groups),
                                 'old_clear_groups': sum(g['old_per_region_clear'] for g in groups),
                                 'old_rejected_groups': sum(not g['old_per_region_clear'] for g in groups),
                                 'maximum_sum_among_old_clear_mm3': max((g['sum_common_upper_bound_mm3'] for g in groups if g['old_per_region_clear']), default=0.),
                                 'newly_unresolved_region_groups': sum(g['old_per_region_clear'] and not g['summed_upper_bound_clear'] for g in groups)})
            prepared = BASE/'native-matrix-e76ff339-archives'/(name+'.tar.gz')
            if prepared.exists():
                checked_jobs[-1]['verified_prepared_archive'] = {'path': str(prepared), 'sha256': sha(prepared),
                                                                 'bytes': prepared.stat().st_size,
                                                                 'every_original_member_rebound_to_execution_inventory': True}
    if not scan_only:
        require(seen == set(definitions), 'ten-job unique coverage incomplete')
        require(sum(j['commands'] for j in checked_jobs) == 37, '37-command coverage incomplete')
    actual = snapshot(ROOT)
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    environment = inspect_environment(ROOT)
    identity = committed_bytes(ROOT, actual)
    require(actual == source and head == EXPECTED and environment['passed'] and identity['present_tracked_bytes_match_head'], 'final aggregation source/environment identity differs')
    return {'schema': 'razr-local-native-ten-job-audit-v1', 'observed_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'functional_source_commit': EXPECTED, 'scan_only': scan_only, 'audit_tool_sha256': sha(Path(__file__)),
            'all_ten_jobs_complete': seen == set(definitions), 'completed_jobs': len(seen),
            'expected_jobs': 10, 'commands_executed_in_complete_jobs': sum(j['commands'] for j in checked_jobs),
            'expected_commands': 37, 'jobs': checked_jobs, 'missing_job_ids': sorted(set(definitions)-seen),
            'strict_unique_workflow_coverage_passed': not scan_only and seen == set(definitions),
            'source_bytes_unchanged': True, 'source_identity': identity, 'environment': environment,
            'artifact_files_sha256_verified': artifact_receipts, 'readback_report_scopes': summaries,
            'region_tolerance_mm3': TOL, 'region_sum_screening_scope': 'All nonnegative finite numeric arrays named region_common_mm3, common_mm3, or commons_mm3 in each complete job JSON, plus explicit STOP pin/remainder and simultaneous PAWL/shoulder cover partition recombinations. Different physical pairs, pose samples, and sequential nut route legs are not summed together.',
            'original_rule': 'Every individual region common is at most 1e-7 mm^3.',
            'revalidated_rule': 'The sum of all nonnegative region common volumes is at most the unchanged 1e-7 mm^3 tolerance; this upper-bounds the material union intersection.',
            'execution_identity_preserved': 'All CAD generation and original reader executions remain attributed to e76ff339; independent sum revalidation does not relabel their source commit.',
            'old_clear_now_unresolved': changed, 'old_clear_region_records_satisfy_summed_upper_bound': not changed,
            'conservative_enclosure_overlap_is_not_collision_proof': True,
            'potential_changed_helper_import_closure': import_closure(definitions),
            'closure_method': 'Conservative static local Python import graph, including deferred imports; not an observed runtime call trace.',
            'preserved_capacity_interruption_report_sha256': sha(FIRST), 'parent_completion_sha256': sha(close_path),
            'hosted_execution': False, 'complete_product_motion_acceptance': False,
            'physical_qualification': False, 'candidate_go': False, 'manufacturing_go': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scan-only', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'new receipt output required')
    result = audit(args.scan_only)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key: result[key] for key in ('all_ten_jobs_complete', 'completed_jobs', 'commands_executed_in_complete_jobs', 'old_clear_region_records_satisfy_summed_upper_bound')}))
