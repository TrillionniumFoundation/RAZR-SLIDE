#!/usr/bin/env python3
"""Execute EP4 finite scenes and a separate STEP reader on one clean commit.

Exit zero means complete research execution and evidence. Positive Common or
escaped material stays a geometric rejection. No product, fixture, continuous
motion or hardware release is granted. Outputs must be new and outside source.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
from importlib import metadata
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

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = 'integration/product_routing_ep4.py'
READER = 'engineering/product-integration-20261018/phase4-20261020/read_ep4_step_independent.py'
NATIVE_SOURCE_FILES = {
    GENERATOR, 'design/product_routing_ep4.json',
    'integration/product_routing_ep3.py', 'design/product_routing_ep3.json',
    'integration/product_split_assembly.py', 'integration/product_assembly.py',
    'integration/product_fpc.py', 'integration/product_interfaces.py', 'integration/oled_storage.py',
    'integration/product_motion.py', 'integration/cam_coupling.py', 'integration/straight_envelope.py',
    'engineering/product-integration-20261018/physical-test-followon-20261019/captured_follower_assembly.py',
    'design/product_geometry.json', 'design/product_interfaces.json',
}
POSES = {'PREDOCK': (113, 154), 'OPEN': (120, 161), 'STOW': (113, 154)}
GO_KEYS = ('candidate_go', 'fixture_fabrication_go', 'manufacturing_go')
NATIVE_GO_KEYS = GO_KEYS + ('supplier_dynamic_qualified', 'physical_hardware_test_executed',
                           'full_cycle_internal_route_accepted')
TOL = 1e-7
REGRESSION_CASES = {
    'A_carrier_connected_after_plate_web_change',
    'B_carrier_connected_after_plate_web_change',
    'retained_A33_18mm3_negative_and_EP4_A_battery_pair',
    'complete_B_board_group_relocation_and_proper_world_frame',
    'B_complete_static_transfer_connected_and_reaches_tail_and_board_reservations',
    'finite_S_U_extrusion_preserves_declared_polygon_at_three_poses',
    'validated_empty_short_circuit_and_separate_domain_regressions',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True,
        env={**os.environ, 'GIT_NO_REPLACE_OBJECTS': '1'}).strip()


def source_snapshot(root):
    """Bind source bytes to actual HEAD blobs, independent of index skip flags."""
    require(git(root, 'cat-file', '-t', 'HEAD') == 'commit', 'real HEAD commit object required')
    entries = subprocess.check_output(
        ['git', '-C', str(root), 'ls-tree', '-r', '-z', '--full-tree', 'HEAD'],
        env={**os.environ, 'GIT_NO_REPLACE_OBJECTS': '1'}).split(b'\0')
    fixed = {'uv.lock', 'pyproject.toml', '.python-version', 'CURRENT_DESIGN.md',
             'docs/RESEARCH_OVERVIEW.md', 'status.json', 'tools/test_suites.json'}
    result = {}
    for entry in entries:
        if not entry:
            continue
        identity, raw = entry.split(b'\t', 1)
        mode, kind, oid = identity.split()
        name = os.fsdecode(raw)
        selected = (name.endswith('.py') or name in fixed or name.startswith('.github/workflows/')
                    or (name.startswith(('design/', 'integration/')) and name.endswith('.json')))
        if selected:
            path = root / name
            require(kind == b'blob' and mode in (b'100644', b'100755')
                    and path.is_file() and not path.is_symlink(), 'missing or linked source: ' + name)
            data = path.read_bytes()
            actual_blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            require(actual_blob == oid.decode('ascii'), 'source bytes differ from HEAD blob: ' + name)
            result[name] = hashlib.sha256(data).hexdigest()
    require(GENERATOR in result and READER in result, 'native source/reader absent from tracked inputs')
    return result


def check_source(report, expected_head, snapshot):
    require(report.get('source_commit') == expected_head, 'executed source commit differs')
    require(report.get('source_bytes_unchanged') is True, 'native source mutation or missing identity')
    sources = report.get('source_sha256', {})
    require(NATIVE_SOURCE_FILES <= sources.keys(), 'native input identity is incomplete')
    for name, digest in sources.items():
        require(snapshot.get(name) == digest, 'native input is not the checked source: ' + name)
    require(all(report.get(k) is False for k in NATIVE_GO_KEYS), 'research report claims release')


def pair_summary(report, expected_pairs, label):
    rows = report.get('rows', [])
    actual = [(row.get('a'), row.get('b')) for row in rows]
    require(report.get('pair_count') == len(rows) == len(expected_pairs)
            and len(set(actual)) == len(actual) and set(actual) == expected_pairs,
            'incomplete or duplicated pair inventory: ' + label)
    rejected, positive = [], 0
    for row in rows:
        require(not row.get('evaluation_failed') and not row.get('diagnostic_artifact_failure'),
                'native evaluation/export failed: ' + label)
        volume = row.get('common_mm3')
        require(type(volume) in (int, float) and math.isfinite(volume) and volume >= 0,
                'invalid Common value: ' + label)
        require(row.get('rejected') is (volume > TOL), 'masked or inconsistent Common rejection: ' + label)
        if volume > 0:
            positive += 1
            require(row.get('artifact_diagnostics_complete') is True and row.get('common_material')
                    and row.get('local_material_context'), 'positive Common lacks diagnostics: ' + label)
        if row['rejected']:
            rejected.append(row)
    require(report.get('failures') == rejected
            and report.get('no_Common_above_tolerance_or_evaluation_error') is (not rejected)
            and report.get('all_positive_Common_artifact_diagnostics_complete') is True,
            'pair summary disagrees with actual rows: ' + label)
    return {'scope': label, 'declared_pairs': len(rows), 'positive_Common_exports_read': positive,
            'rejected_pairs': len(rejected)}


def validate_native(report, expected_head, snapshot):
    require(report.get('schema') == 'razr-ep4-bounded-native-v1'
            and report.get('native_checks_executed') is True, 'complete EP4 native report required')
    check_source(report, expected_head, snapshot)
    require(report.get('selected_poses') == list(POSES)
            and [p.get('pose') for p in report.get('poses', [])] == list(POSES),
            'all three ordered finite poses must execute in this run')
    ends, scopes = {}, []
    for end in ('A', 'B'):
        parts = report['endpoint_exports'][end]['parts']
        require(len(parts) == 20, 'incomplete endpoint: ' + end)
        ends[end] = {end + '_' + name for name in parts}
        scopes.append(pair_summary(report['endpoint_self_checks'][end],
            set(itertools.combinations(sorted(ends[end]), 2)), end + ' local self'))
    candidates = {'EP4_finite_material'} | ends['A'] | ends['B']
    pose_results = []
    local_rejected = any(scope['rejected_pairs'] for scope in scopes)
    for pose in report['poses']:
        label = pose['pose']
        external_count, total = POSES[label]
        parts = set(pose.get('parts', {}))
        require(pose.get('candidate_participants') == 41 and pose.get('external_participants') == external_count
                and pose.get('combined_participants') == total and len(parts) == total and candidates <= parts
                and pose.get('all_assembly_source_parts_have_native_bounds_and_volume') is True,
                'full assembly participants or metrics missing: ' + label)
        external = parts - candidates
        current = [
            pair_summary(pose['external'], set(itertools.product(sorted(candidates), sorted(external))), label+' external'),
            pair_summary(pose['A_to_B_endpoints'], set(itertools.product(sorted(ends['A']), sorted(ends['B']))), label+' A to B'),
            pair_summary(pose['material_to_all_40_endpoint_parts'],
                {('EP4_finite_material', name) for name in ends['A'] | ends['B']}, label+' material to endpoints'),
        ]
        scopes.extend(current)
        containment = pose['containment']
        rows = containment.get('rows', [])
        require(containment.get('parts') == 41 and len(rows) == 41
                and {row.get('part') for row in rows} == candidates, 'incomplete containment: ' + label)
        escaped = []
        for row in rows:
            require(not row.get('evaluation_failed'), 'containment evaluation failed: ' + label)
            outside = row.get('outside_outer_union_mm3')
            require(type(outside) in (int, float) and math.isfinite(outside) and outside >= 0,
                    'invalid containment volume: ' + label)
            require(row.get('rejected') is (outside > TOL), 'masked containment rejection: ' + label)
            if row['rejected']:
                require(row.get('outside_material'), 'escaped material lacks export: ' + label)
                escaped.append(row)
        require(containment.get('failures') == escaped
                and containment.get('all_material_inside_optimistic_outer_union') is (not escaped),
                'containment summary disagrees: ' + label)
        rejected = bool(local_rejected or escaped or any(s['rejected_pairs'] for s in current))
        require(pose.get('decisive_geometric_rejection_or_evaluation_failure') is rejected
                and pose.get('all_declared_checks_clear_at_this_finite_pose') is (not rejected),
                'finite-pose disposition disagrees: ' + label)
        pose_results.append({'pose': label, 'bodies': total, 'geometric_rejected': rejected,
                             'outside_parts': len(escaped), 'pair_scopes': current})
    rejected = any(p['geometric_rejected'] for p in pose_results)
    require(report.get('geometric_rejection_found') is rejected, 'native geometric disposition disagrees')
    return {'poses': pose_results, 'pair_scope_coverage': scopes,
            'declared_pairs': sum(s['declared_pairs'] for s in scopes), 'geometric_rejected': rejected}


def validate_readback(report, native_path, expected_head, native_summary):
    require(report.get('schema') == 'razr-ep4-independent-step-readback-v1'
            and report.get('native_source_commit') == expected_head
            and report.get('reader_observed_repository_head') == expected_head,
            'readback is not for the current native source')
    require(report.get('native_report', {}).get('sha256') == sha(native_path), 'readback native report hash differs')
    require(report.get('independent_process_from_generator') is True
            and report.get('geometry_generator_modules_imported') is False
            and report.get('execution_completed') is True
            and report.get('declared_readback_checks_passed') is True
            and report.get('all_assembly_parts_have_metric_comparison') is True
            and report.get('failures') == [] and report.get('changed_during_readback') == [],
            'independent readback incomplete, failed or mutated')
    require(all(report.get(k) is False for k in GO_KEYS), 'readback claims product release')
    require(all(report.get(k) is False for k in (
        'full_source_material_equivalence_proved', 'STEP_label_identity_proved',
        'continuous_interference_clearance_proved')), 'finite readback overclaims its scope')
    require(set(report.get('poses', {})) == set(POSES), 'readback omits a finite pose')
    for label, (external, total) in POSES.items():
        p = report['poses'][label]
        require(p.get('all_source_objects_compared') == total
                and p.get('external_source_objects_compared') == external
                and p.get('candidate_source_objects_compared') == 41,
                'readback did not compare every body: ' + label)
    expected = [{k: s[k] for k in ('scope', 'declared_pairs', 'positive_Common_exports_read')}
                for s in native_summary['pair_scope_coverage']]
    require(report.get('pair_scope_coverage') == expected, 'readback pair/Common export coverage differs')


def validate_regressions(report, expected_head, snapshot):
    require(report.get('schema') == 'razr-ep4-small-native-regressions-v1', 'native regression report absent')
    check_source(report, expected_head, snapshot)
    cases = report.get('cases', [])
    require(len(cases) == len(REGRESSION_CASES) and {c.get('case') for c in cases} == REGRESSION_CASES
            and all(c.get('pass') is True for c in cases) and report.get('native_regressions_passed') is True,
            'native regression or retained negative control incomplete')


def execute(root, output, expected_head, timeout_seconds):
    root, output = root.resolve(), output.resolve()
    require(re.fullmatch(r'[0-9a-f]{40}', expected_head) is not None, 'full expected commit SHA required')
    require(timeout_seconds > 0 and math.isfinite(timeout_seconds), 'positive finite timeout required')
    require(not output.exists() and output != root and root not in output.parents, 'new output outside source required')
    output.mkdir(parents=True)
    report = {'schema': 'razr-product-native-validation-v1', 'started_utc': utc(),
        'expected_head': expected_head, 'scope': 'EP4 seven native regressions and all three finite scenes with independent STEP readback',
        'source_snapshot_scope': 'tracked Python, active design/integration JSON, workflow, lock and product entry points; not archive blobs',
        'python': sys.version, 'packages': {}, 'commands': [], 'execution_checks_passed': False,
        'finite_geometry': 'not_evaluated', 'physical_qualification': 'not_provided',
        'full_cycle_internal_route_accepted': False, **{k: False for k in GO_KEYS}}
    started = time.monotonic()
    before = None
    def save():
        (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    def run(name, command):
        log = output/(name+'.log')
        row = {'stage': name, 'command': command, 'started_utc': utc(), 'exit_code': None, 'timed_out': False}
        report['commands'].append(row); save()
        remaining = timeout_seconds-(time.monotonic()-started)
        require(remaining > 0, 'total execution budget exhausted')
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'OMP_NUM_THREADS': '1',
               'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1',
               'GIT_NO_REPLACE_OBJECTS': '1'}
        with log.open('w') as handle:
            try:
                proc = subprocess.run(command, cwd=root, env=env, stdout=handle, stderr=subprocess.STDOUT, timeout=remaining)
                row['exit_code'] = proc.returncode
            except subprocess.TimeoutExpired:
                row['timed_out'] = True
        row.update(finished_utc=utc(), log={'file': log.name, 'bytes': log.stat().st_size, 'sha256': sha(log)})
        save()
        require(row['exit_code'] == 0 and not row['timed_out'], 'command failed or timed out: ' + name)
    try:
        require(git(root, 'rev-parse', 'HEAD') == expected_head and not git(root, 'status', '--porcelain'),
                'expected clean commit is not checked out')
        before = source_snapshot(root); report['source_sha256_before'] = before
        for package in ('cadquery', 'cadquery-ocp', 'numpy', 'scipy', 'shapely'):
            try:
                report['packages'][package] = metadata.version(package)
            except metadata.PackageNotFoundError:
                report['packages'][package] = None
        save()
        run('entrypoints', [sys.executable, '-B', str(root/'tools/sync_current_design.py'), '--check'])
        run('native-regressions', [sys.executable, '-B', str(root/GENERATOR), '--output', str(output/'regressions'), '--native-regression'])
        regressions = json.loads((output/'regressions/native-regression/native-regressions.json').read_text())
        validate_regressions(regressions, expected_head, before)
        run('three-finite-scenes', [sys.executable, '-B', str(root/GENERATOR), '--output', str(output/'scenes'), '--native', '--poses', *POSES])
        native_path = output/'scenes/native/native-report.json'
        native = json.loads(native_path.read_text())
        summary = validate_native(native, expected_head, before)
        report['native_summary'] = summary
        report['finite_geometry'] = 'rejected' if summary['geometric_rejected'] else 'clear_at_selected_poses_only'
        run('independent-readback', [sys.executable, '-B', str(root/READER), '--repository-root', str(root),
            '--manifest', str(native_path), '--output', str(output/'readback')])
        readback_path = output/'readback/report.json'
        validate_readback(json.loads(readback_path.read_text()), native_path, expected_head, summary)
        report['reports'] = {str(p.relative_to(output)): {'bytes': p.stat().st_size, 'sha256': sha(p)}
                             for p in (native_path, readback_path, output/'regressions/native-regression/native-regressions.json')}
        report['execution_checks_passed'] = True
    except Exception as exc:
        report['error'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    finally:
        if before is not None:
            try:
                after = source_snapshot(root)
                report['source_sha256_after'] = after
                report['source_bytes_unchanged'] = before == after
                report['source_head_after'] = git(root, 'rev-parse', 'HEAD')
                report['source_worktree_clean_after'] = not git(root, 'status', '--porcelain')
                report['execution_checks_passed'] &= (before == after and report['source_head_after'] == expected_head
                                                     and report['source_worktree_clean_after'])
            except Exception as exc:
                report['execution_checks_passed'] = False
                report['final_identity_error'] = str(exc)
        report.update(finished_utc=utc(), seconds=time.monotonic()-started)
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--timeout-seconds', type=float, default=1200)
    args = parser.parse_args()
    report = execute(args.root, args.output, args.expected_head, args.timeout_seconds)
    print(json.dumps({k: report[k] for k in ('expected_head', 'execution_checks_passed', 'finite_geometry',
        'physical_qualification', 'candidate_go', 'fixture_fabrication_go', 'manufacturing_go', 'seconds')}, indent=2))
    return 0 if report['execution_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
