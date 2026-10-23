#!/usr/bin/env python3
"""Run EP5 local and complete finite scenes on one exact committed source.

A successful job means the declared research execution and independent reads
completed. Geometric rejection remains a result; G2, complete product motion,
physical qualification and product release are not granted by this job.
"""
from __future__ import annotations

import argparse
import hashlib
from importlib import metadata, util
import itertools
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback

import verify_product_native as identity

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = 'integration/product_routing_ep5.py'
READER = 'engineering/product-integration-20261018/phase5-20261022/read_ep5_step_independent.py'
HELPER = 'engineering/product-integration-20261018/phase3-20261020/read_ep3_step_independent.py'
DRIVER = 'tools/verify_product_ep5_native.py'
IDENTITY = 'tools/verify_product_native.py'
ROLE_HELPER = 'integration/ep5_input_closure.py'
MEMBER_HELPER = 'integration/verified_native_members.py'
MOUNTED_ARCHIVE = 'engineering/mounted-mechanism-20261015/native-geometry.tar.gz'
POSES = ('STOW', 'PREDOCK', 'OPEN')
COUNTS = {'local': (46, 46, 46), 'full': (154, 154, 161)}
SCHEMAS = {'local': 'razr-ep5-local-motion-native-v1', 'full': 'razr-ep5-full-pair-native-v1'}
REQUIRED_INPUTS = identity.NATIVE_SOURCE_FILES | {GENERATOR, 'design/product_routing_ep5.json', ROLE_HELPER}
ENDPOINT_MARGIN_NAMES = frozenset({
    'A_endpoint_to_B_endpoint_SLIDE_Z_gap_mm', 'A_endpoint_to_B_endpoint_SEAT_Y_gap_mm',
    'B_endpoint_to_low_bridge_Z_gap_mm', 'B_endpoint_to_S_SLIDE_Z_gap_mm',
    'B_endpoint_to_S_SEAT_Y_gap_mm', 'B_endpoint_to_high_return_Z_gap_mm',
    'B_endpoint_to_U2_Y_gap_mm', 'A_endpoint_to_S_bridge_U1_Y_gap_mm',
    'A_endpoint_to_return_SLIDE_Z_gap_mm', 'A_endpoint_to_return_SEAT_Y_gap_mm'})
require = identity.require
sha = identity.sha
utc = identity.utc


def load_bound_module(root, relative, snapshot, module_name):
    path = root/relative
    require(snapshot.get(relative) == sha(path), 'input validator is not the checked HEAD source: '+relative)
    spec = util.spec_from_file_location(module_name, path)
    module = util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def input_roles(root, snapshot, mode, verified_mounted_members=False):
    helper = load_bound_module(root, ROLE_HELPER, snapshot, '_razr_ep5_declared_input_roles')
    roles = helper.native_input_roles(mode, verified_mounted_members=verified_mounted_members)
    require(isinstance(roles, dict) and roles and all(
        type(name) is str and not Path(name).is_absolute() and '..' not in Path(name).parts
        and type(role) is str and role for name, role in roles.items()), 'invalid declared native input closure')
    return roles


def head_bound_inputs(root, names):
    names = set(names)
    entries = identity.git(root, 'ls-tree', '-r', '-z', '--full-tree', 'HEAD', '--', *sorted(names)).split('\0')
    result = {}
    for entry in entries:
        if not entry:
            continue
        header, name = entry.split('\t', 1); mode, kind, oid = header.split()
        if name not in names:
            continue
        path = root/name
        require(kind == 'blob' and mode in ('100644', '100755') and path.is_file()
                and not path.is_symlink(), 'missing or linked required native input: '+name)
        data = path.read_bytes()
        actual = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        require(actual == oid, 'native input differs from HEAD blob: '+name)
        result[name] = hashlib.sha256(data).hexdigest()
    require(set(result) == names, 'required native input absent from HEAD: '+', '.join(sorted(names-set(result))))
    return result


def source_snapshot(root, verified_mounted_members=False):
    """Audited code scope plus the explicit transitive EP5 native input closure."""
    result = identity.source_snapshot(root)
    require({GENERATOR, READER, HELPER, DRIVER, IDENTITY, ROLE_HELPER, MEMBER_HELPER} <= result.keys(),
            'EP5 committed source inventory incomplete')
    roles = input_roles(root, result, 'full', verified_mounted_members)
    result.update(head_bound_inputs(root, roles))
    return result


def verify_explicit_members(root, directory, snapshot):
    validator = load_bound_module(root, MEMBER_HELPER, snapshot, '_razr_ep5_exact_member_validator')
    result = validator.verify_mounted_members(directory, root)
    require(result.get('expected_member_count') == result.get('actual_member_count') == 64
            and len(result.get('members', {})) == 64 and result.get('all_original_member_bytes_verified') is True
            and result.get('original_archive_sha256_claimed_recovered') is False,
            'complete original member identities were not verified')
    return result


def bind_running_sources(root, snapshot):
    for name, executed in ((DRIVER, Path(__file__)), (IDENTITY, Path(identity.__file__))):
        require(executed.resolve() == (root/name).resolve() and snapshot.get(name) == sha(executed),
                'executed validation source is outside the checked commit: '+name)


def finite_disposition(report, mode):
    """Derive rejection from complete measured rows, never a top-level claim."""
    rejected_poses = []
    for pose in report['poses']:
        label = mode+'/'+pose['pose']
        names = set(pose['parts'])
        pairs = identity.pair_summary(pose['complete_pair_matrix'],
            set(itertools.combinations(sorted(names), 2)), label+' complete pairs')
        rejected = bool(pairs['rejected_pairs'])
        contained = pose.get('containment', {})
        rows = contained.get('rows')
        require(isinstance(rows, list), 'containment rows absent: '+label)
        if mode == 'local':
            require(rows == [] and contained.get('executed') is False,
                    'local containment cannot be relabelled as executed')
        else:
            require(contained.get('parts') == 41 and len(rows) == 41
                    and len({r.get('part') for r in rows}) == 41
                    and {r.get('part') for r in rows} <= names,
                    'incomplete containment inventory: '+label)
            escaped = []
            for row in rows:
                require(not row.get('evaluation_failed'), 'containment evaluation failed: '+label)
                value = row.get('outside_outer_union_mm3')
                require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
                        'invalid containment volume: '+label)
                require(row.get('rejected') is (value > identity.TOL), 'masked containment rejection: '+label)
                if value > 0:
                    require(row.get('outside_material'), 'positive outside material lacks export: '+label)
                if row['rejected']:
                    escaped.append(row)
            require(contained.get('failures') == escaped
                    and contained.get('all_material_inside_optimistic_outer_union') is (not escaped),
                    'containment summary disagrees with actual rows: '+label)
            rejected = bool(rejected or escaped)
            require(pose.get('decisive_geometric_rejection_or_evaluation_failure') is rejected
                    and pose.get('all_declared_finite_pose_checks_clear') is (not rejected),
                    'finite-pose disposition disagrees: '+label)
        rejected_poses.append(rejected)
    rejected = any(rejected_poses)
    if mode == 'local':
        continuous = report.get('continuous_complete_endpoints', {})
        require(continuous.get('schema') == 'razr-ep5-continuous-complete-endpoint-geometry-v1',
                'local continuous endpoint evidence absent')
        endpoints = continuous.get('endpoint_metrics', {})
        require(set(endpoints) == {'A', 'B'} and all(
            isinstance(endpoints[end], dict) and len(endpoints[end]) == 20
            and all(name.startswith(end+'_') for name in endpoints[end])
            and all(set(endpoints[end]) <= set(p['parts']) for p in report['poses']) for end in ('A', 'B')),
            'continuous endpoint inventory incomplete')
        pairs = identity.pair_summary(continuous.get('U1_to_all_20_B_endpoint_parts', {}),
            {('U1_ALL_POSES_SMOOTH_ENCLOSURE', name) for name in endpoints['B']}, 'continuous U1 endpoint pairs')
        margins = continuous.get('other_segment_axis_separation_margins', {})
        require(isinstance(margins, dict) and set(margins) == ENDPOINT_MARGIN_NAMES
                and all(type(value) in (int, float) and math.isfinite(value) and value > 0
                        for value in margins.values()), 'continuous endpoint separation margin incomplete or failed')
        continuous_rejected = bool(pairs['rejected_pairs'])
        require(continuous.get('all_declared_continuous_endpoint_geometric_checks_clear') is (not continuous_rejected),
                'continuous endpoint disposition disagrees with actual rows')
        require(all(continuous.get(key) is False for key in identity.GO_KEYS)
                and continuous.get('current_PAWL_or_full_external_field_checked') is False
                and continuous.get('friction_strain_tolerance_and_physical_qualification_proved') is False,
                'continuous endpoint study overclaims its scope')
        rejected |= continuous_rejected
        require(report.get('all_declared_local_geometry_checks_clear') is (not rejected),
                'local geometric disposition disagrees with actual rows')
    else:
        require(report.get('geometric_rejection_found') is rejected,
                'full geometric disposition disagrees with actual rows')
    return rejected


def validate_native_envelope(report, root, snapshot, mode, required_roles, verified_input=None):
    """Check run scope and commit identity; the reader owns detailed native schema checks."""
    require(report.get('schema') == SCHEMAS[mode] and report.get('native_checks_executed') is True
            and report.get('source_bytes_unchanged') is True, 'EP5 native execution is incomplete: '+mode)
    poses = report.get('poses', [])
    require(report.get('selected_poses') == list(POSES) and [p.get('pose') for p in poses] == list(POSES),
            'all three ordered EP5 poses required: '+mode)
    require(all(report.get(key) is False for key in identity.NATIVE_GO_KEYS), 'research native report claims release')
    sources = report.get('source_sha256', {})
    require(isinstance(sources, dict) and sources, 'native input identity is empty')
    require(report.get('declared_input_roles') == required_roles, 'native input role closure differs')
    external_sources = verified_input['source_sha256'] if mode == 'full' and verified_input is not None else {}
    if mode == 'full':
        require(report.get('verified_mounted_members_before') == verified_input
                and report.get('verified_mounted_members_after') == verified_input,
                'native execution did not retain the exact requested member input')
        require(set(external_sources) <= sources.keys(), 'native member source inventory incomplete')
    observed = set()
    for name, digest in sources.items():
        path = Path(name)
        require(path.is_absolute(), 'absolute executed native input path required')
        resolved = path.resolve()
        if resolved.is_relative_to(root):
            relative = resolved.relative_to(root).as_posix()
            require(snapshot.get(relative) == digest, 'native input is not the checked HEAD source: '+relative)
            observed.add(relative)
        else:
            require(external_sources.get(str(resolved)) == digest, 'native input is outside the explicitly verified scope')
    require(REQUIRED_INPUTS | set(required_roles) <= observed, 'native input identity omits required source roles')
    for pose, count in zip(poses, COUNTS[mode]):
        require(pose.get('combined_participants') == count and len(pose.get('parts', {})) == count
                and pose.get('candidate_participants') == 41 and pose.get('external_participants') == count-41
                and pose.get('complete_pair_matrix', {}).get('pair_count') == count*(count-1)//2,
                'finite assembly or external/external pair coverage is incomplete: '+mode+'/'+pose['pose'])
    if mode == 'local':
        require(report.get('whole_phone_obstacle_field_tested') is False
                and report.get('shell_channels_generated_or_validated_by_this_mode') is False,
                'local scene was relabelled as complete-phone validation')
    rejected = finite_disposition(report, mode)
    return {'poses': list(POSES), 'bodies': list(COUNTS[mode]),
            'declared_pairs': sum(n*(n-1)//2 for n in COUNTS[mode]),
            'finite_geometry': 'rejected' if rejected else 'clear_at_declared_scope_only'}


def validate_readback(report, native_path, snapshot, mode, verified_input=None):
    require(report.get('schema') == 'razr-ep5-independent-step-readback-v1'
            and report.get('native_report_sha256') == sha(native_path), 'reader did not read this fresh native report')
    require(report.get('reader_sha256') == snapshot[READER] and report.get('helper_sha256') == snapshot[HELPER],
            'executed reader source is not the checked commit')
    require(report.get('execution_completed') is True and report.get('declared_readback_checks_passed') is True
            and report.get('failures') == [] and report.get('independent_process_from_generator') is True
            and report.get('geometry_generator_modules_imported') is False, 'independent EP5 readback incomplete or failed')
    require(all(report.get(key) is False for key in identity.GO_KEYS), 'readback claims product release')
    require(all(report.get(key) is False for key in ('full_source_material_equivalence_proved',
            'STEP_label_identity_proved', 'continuous_interference_clearance_proved')), 'finite reader overclaims its scope')
    if mode == 'full':
        require(report.get('verified_original_member_input_rechecked') == verified_input,
                'independent reader omitted or changed the explicit member identity')
    else:
        continuous = report.get('continuous_endpoint_readback', {})
        require(continuous.get('cage', {}).get('flat_solids') == 1
                and continuous.get('endpoint_pair_count') == 20
                and continuous.get('all_endpoint_pairs_present_once') is True,
                'independent reader omitted the declared continuous endpoint cage or pairs')
    poses = report.get('poses', [])
    require([p.get('pose') for p in poses] == list(POSES), 'independent reader omitted or repeated a finite pose')
    for pose, count in zip(poses, COUNTS[mode]):
        require(pose.get('assembly', {}).get('flat_solids') == count
                and pose.get('full_pair_count') == count*(count-1)//2 and pose.get('all_pairs_present_once') is True,
                'reader did not verify all native bodies and unordered pairs')


def execute(root, output, expected_head, timeout_seconds, verified_mounted_members=None):
    root, output = root.resolve(), output.resolve()
    require(re.fullmatch(r'[0-9a-f]{40}', expected_head) is not None, 'full expected commit SHA required')
    require(timeout_seconds > 0 and math.isfinite(timeout_seconds), 'positive finite execution budget required')
    require(not output.exists() and output != root and root not in output.parents, 'new output outside source required')
    output.mkdir(parents=True)
    report = {'schema': 'razr-product-ep5-native-validation-v1', 'started_utc': utc(),
        'expected_head': expected_head, 'scope': 'EP5 local three-pose study plus complete three-pose assembly, each with independent STEP readback',
        'source_snapshot_scope': 'audited tracked code and entrypoint scope plus the explicit transitive EP5 native input role closure, all bound to actual HEAD blobs',
        'full_checkout_verified': False, 'all_configured_unit_suites_executed': False,
        'archive_available': (root/MOUNTED_ARCHIVE).is_file(), 'verified_original_members': False,
        'original_mounted_archive_container_recovered': False,
        'commands': [], 'packages': {}, 'python': sys.version, 'research_scopes': {},
        'execution_checks_passed': False, 'physical_qualification': 'not_provided',
        'G2_acceptance_granted_by_this_job': False, **{key: False for key in identity.NATIVE_GO_KEYS}}
    started = time.monotonic(); before = None; member_before = None
    def save():
        (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    def run(name, command):
        log = output/(name+'.log')
        row = {'stage': name, 'command': command, 'started_utc': utc(), 'exit_code': None, 'timed_out': False}
        report['commands'].append(row); save()
        remaining = timeout_seconds-(time.monotonic()-started)
        require(remaining > 0, 'total execution budget exhausted')
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'GIT_NO_REPLACE_OBJECTS': '1',
               'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1'}
        with log.open('w') as stream:
            try:
                proc = subprocess.run(command, cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=remaining)
                row['exit_code'] = proc.returncode
            except subprocess.TimeoutExpired:
                row['timed_out'] = True
        row.update(finished_utc=utc(), log={'file': log.name, 'bytes': log.stat().st_size, 'sha256': sha(log)})
        save()
        require(row['exit_code'] == 0 and not row['timed_out'], 'command failed or timed out: '+name)
    try:
        require(identity.git(root, 'rev-parse', 'HEAD') == expected_head
                and not identity.git(root, 'status', '--porcelain'), 'expected clean commit is not checked out')
        before = source_snapshot(root, verified_mounted_members is not None); report['source_sha256_before'] = before
        bind_running_sources(root, before)
        plans = {mode: input_roles(root, before, mode, mode == 'full' and verified_mounted_members is not None)
                 for mode in ('local', 'full')}
        report['required_native_input_roles'] = plans
        if verified_mounted_members is not None:
            member_before = verify_explicit_members(root, verified_mounted_members, before)
            report['verified_mounted_members_before'] = member_before
        for package in ('cadquery', 'cadquery-ocp', 'numpy', 'scipy', 'shapely'):
            try: report['packages'][package] = metadata.version(package)
            except metadata.PackageNotFoundError: report['packages'][package] = None
        run('entrypoints', [sys.executable, '-B', str(root/'tools/sync_current_design.py'), '--check'])
        reports = []
        for mode in ('local', 'full'):
            native_dir = output/mode; readback_dir = output/(mode+'-readback')
            args = ['--native-local-motion'] if mode == 'local' else ['--native', '--poses', *POSES]
            if mode == 'full' and member_before is not None:
                args += ['--verified-mounted-members', member_before['directory']]
            run(mode+'-native', [sys.executable, '-B', str(root/GENERATOR), '--output', str(native_dir), *args])
            native_path = native_dir/'native-report.json'
            summary = validate_native_envelope(json.loads(native_path.read_text()), root, before, mode, plans[mode], member_before)
            report['research_scopes'][mode] = summary
            run(mode+'-independent-readback', [sys.executable, '-B', str(root/READER), '--repository-root', str(root),
                '--manifest', str(native_path), '--output', str(readback_dir)])
            reader_path = readback_dir/'report.json'
            validate_readback(json.loads(reader_path.read_text()), native_path, before, mode, member_before)
            reports.extend((native_path, reader_path))
        report['reports'] = {str(path.relative_to(output)): {'bytes': path.stat().st_size, 'sha256': sha(path)} for path in reports}
        report['execution_checks_passed'] = True
    except Exception as exc:
        report['error'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    finally:
        if before is not None:
            try:
                after = source_snapshot(root, verified_mounted_members is not None)
                report.update(source_sha256_after=after, source_bytes_unchanged=before == after,
                    source_head_after=identity.git(root, 'rev-parse', 'HEAD'),
                    source_worktree_clean_after=not identity.git(root, 'status', '--porcelain'))
                if member_before is not None:
                    member_after = verify_explicit_members(root, verified_mounted_members, after)
                    report['verified_mounted_members_after'] = member_after
                    report['verified_original_members'] = member_before == member_after
                    require(member_before == member_after, 'explicit member inputs changed during validation')
                report['execution_checks_passed'] &= (before == after and report['source_head_after'] == expected_head
                                                     and report['source_worktree_clean_after'])
            except Exception as exc:
                report['execution_checks_passed'] = False; report['final_identity_error'] = str(exc)
        report.update(finished_utc=utc(), seconds=time.monotonic()-started); save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--verified-mounted-members', type=Path,
        help='explicit strict original-member directory for a scoped run without the original mounted tar; never an automatic fallback')
    parser.add_argument('--timeout-seconds', type=float, default=3000)
    args = parser.parse_args()
    report = execute(args.root, args.output, args.expected_head, args.timeout_seconds, args.verified_mounted_members)
    print(json.dumps({key: report[key] for key in ('expected_head', 'execution_checks_passed', 'research_scopes',
        'physical_qualification', 'G2_acceptance_granted_by_this_job', 'archive_available', 'verified_original_members',
        'full_checkout_verified', 'all_configured_unit_suites_executed', *identity.GO_KEYS, 'seconds')}, indent=2))
    return 0 if report['execution_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
