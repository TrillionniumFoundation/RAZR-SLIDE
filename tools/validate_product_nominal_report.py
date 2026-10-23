#!/usr/bin/env python3
"""Independently check the bounded-control receipt, without importing CAD.

This verifies raw pair/inventory consistency, numerical result disposition,
scope and the current committed source/runtime identity. It does not recompute
geometry or constitute a second CAD kernel or physical qualification.
"""
from __future__ import annotations

import argparse
from collections import Counter
import itertools
import json
import math
from pathlib import Path
import re

import check_environment
import verify_product_ep5_native as native

ROOT = Path(__file__).resolve().parents[1]
SELF = 'tools/validate_product_nominal_report.py'
COUNTS = {'STOW': 154, 'PREDOCK': 154, 'OPEN': 161}
TOL = 1e-7
require = native.require
TRUE_FLAGS = ('execution_completed', 'execution_checks_passed', 'diagnostic_execution_checks_passed',
              'source_bytes_unchanged', 'all_unordered_pairs_present_once',
              'whole_declared_control_domain_clear', 'unresolved_enclosure_overlap_is_not_collision',
              'sampled_clear_witnesses_cannot_discharge_an_unresolved_domain',
              'tab_motion_allowed_only_at_STOW', 'geometry_generator_imported', 'same_CAD_kernel')
FALSE_FLAGS = ('executed_source_overlay', 'complete_product_motion_proved', 'physical_qualification',
               'formal_directed_rounding_certificate', 'candidate_go', 'fixture_fabrication_go',
               'manufacturing_go')
REGION_METHODS = {'identical_relative_pose', 'continuous_relative_axis_translation',
                  'continuous_relative_affine_box_translation_enclosure'}


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def expected_domain(pose):
    require(pose in COUNTS, 'one declared named pose required')
    opened = pose == 'OPEN'
    nominal = .1 + (0. if opened else 8.2)/3
    vertices = [[.1]*3] if opened else [list(v) for v in sorted(set(itertools.permutations((2.7, 2.9, 2.9))))]
    bounds = [[min(v[i] for v in vertices), max(v[i] for v in vertices)] for i in range(3)]
    return {'slide_mm': 0. if pose == 'STOW' else 79.75, 'descent_mm': 8.2 if opened else 0.,
            'left_tab_mm': [0., 3.] if pose == 'STOW' else [3., 3.],
            'right_tab_mm': [0., 3.] if pose == 'STOW' else [3., 3.],
            'slot_flanks': [[-1., 1.], [-1., 1.]], 'KEY_offsets_mm': [0., 0.],
            'crosshead_offsets_mm': [0., 0.],
            'telescope_allocation': {'joint_limits_mm': [.1, 2.9], 'joint_sum_mm': .3 if opened else 8.5,
                'nominal_joint_mm': nominal, 'vertices_joint_mm': vertices,
                'joint_projection_bounds_mm': bounds,
                'parameter_bounds_delta_j1_delta_j2_mm': [[lo-nominal, hi-nominal] for lo, hi in bounds[:2]],
                'left_right_allocations_independent': True, 'third_joint_is_fixed_sum_remainder': True,
                'full_feasible_fixed_pose_allocation_covered': True},
            'parameter_order': ['uL', 'uR', 'flankL', 'flankR', 'delta_j1L', 'delta_j2L', 'delta_j1R', 'delta_j2R'],
            'relative_telescope_domain_reduction': 'complete independent polytope linear Z projection'}


def expected_executed_sources(root, snapshot, roles):
    """Rebuild the producer's complete file inventory; never trust its map."""
    root = root.resolve()
    paths = {root/name for name in roles}
    for directory in ('integration', 'design'):
        paths.update(path for path in (root/directory).rglob('*')
                     if path.is_file() and path.suffix in ('.py', '.json'))
    paths.update(path for path in (root/'engineering').rglob('*.py') if path.is_file())
    paths.update(root/name for name in ('tools/verify_product_ep5_native.py',
                                       'tools/verify_product_native.py', 'tools/check_environment.py'))
    result = {}
    for path in sorted(paths):
        require(path.is_file() and path.resolve() == path and not path.is_symlink(),
                'missing, linked or outside executed source: '+str(path))
        relative = path.relative_to(root).as_posix()
        digest = native.sha(path)
        require(snapshot.get(relative) == digest, 'executed source differs from HEAD or is untracked: '+relative)
        result[str(path)] = digest
    return result


def current_identity(root, expected_head):
    root = root.resolve()
    require(type(expected_head) is str and re.fullmatch('[0-9a-f]{40}', expected_head),
            'full expected commit SHA required')
    require(native.identity.git(root, 'rev-parse', 'HEAD') == expected_head, 'current HEAD differs')
    snapshot = native.source_snapshot(root)
    for name, path in ((SELF, Path(__file__)), (native.DRIVER, Path(native.__file__)),
                       (native.IDENTITY, Path(native.identity.__file__)),
                       ('tools/check_environment.py', Path(check_environment.__file__))):
        require(path.resolve() == root/name and snapshot.get(name) == native.sha(path),
                'running postguard helper is outside the checked HEAD: '+name)
    roles = native.input_roles(root, snapshot, 'full')
    executed = expected_executed_sources(root, snapshot, roles)
    environment = check_environment.inspect_environment(root)
    require(environment.get('passed') is True, 'current locked environment failed')
    return {'repository_head': expected_head, 'head_bound_source_sha256': snapshot,
            'executed_source_sha256': executed, 'executed_source_overlay': False,
            'outside_repository_executed_files': [], 'environment': environment}


def validate_frame(row, depth=0):
    require(isinstance(row, dict) and depth < 4, 'invalid raw pair/frame result')
    disposition, method = row.get('disposition'), row.get('method')
    require(disposition in ('clear', 'unresolved_enclosure_overlap'), 'raw evaluation failure or unknown disposition')
    require('error' not in row, 'raw frame carries an evaluation error')
    if disposition == 'clear':
        if method == 'continuous_relative_axis_gap':
            require(finite(row.get('gap_lower_mm')) and row['gap_lower_mm'] > 0,
                    'clear pair lacks a positive finite separation')
        else:
            upper, maximum = row.get('common_upper_bound_mm3'), row.get('maximum_region_common_mm3')
            require(method in REGION_METHODS and type(row.get('region_count')) is int and row['region_count'] > 0
                    and finite(upper) and finite(maximum) and 0 <= maximum <= upper <= TOL
                    and row.get('common_upper_bound_is_sum_not_union_volume') is True,
                    'clear pair has invalid or rejected native Common bounds')
    else:
        upper, maximum = row.get('examined_region_common_sum_mm3'), row.get('positive_enclosure_common_mm3')
        require(method in REGION_METHODS and finite(upper) and finite(maximum) and 0 <= maximum <= upper
                and upper > TOL and type(row.get('regions_examined')) is int
                and type(row.get('total_region_count')) is int
                and 0 < row['regions_examined'] <= row['total_region_count']
                and row.get('collision_proved') is False,
                'invalid retained conservative-overlap result')
    for key in ('initial_reference_frame_result', 'opposite_reference_frame_result'):
        if key in row:
            validate_frame(row[key], depth+1)
    require(('initial_reference_frame_result' in row) == (row.get('relative_reference_frame_reversed') is True),
            'reverse-frame result lost its initial raw evidence')


def validate_report(report, pose, expected_head, current):
    require(isinstance(report, dict) and report.get('schema') == 'razr-ep5-independent-control-domain-v2'
            and report.get('pose') == pose and report.get('domain') == expected_domain(pose),
            'declared fixed-pose control/telescope domain differs')
    require(report.get('expected_head') == expected_head == current['repository_head']
            and report.get('identity_before') == current and report.get('identity_after') == current,
            'reported before/after source or runtime identity differs from current HEAD')
    require(all(report.get(key) is True for key in TRUE_FLAGS)
            and all(report.get(key) is False for key in FALSE_FLAGS)
            and 'execution_failure' not in report, 'bounded research execution/scope flags differ')
    names, rows = report.get('complete_participant_names'), report.get('pairs')
    require(isinstance(names, list) and len(names) == COUNTS[pose]
            and all(type(name) is str and name for name in names) and names == sorted(set(names)),
            'complete unique participant inventory absent or changed')
    expected = set(itertools.combinations(names, 2))
    require(isinstance(rows, list) and len(rows) == len(expected)
            and all(isinstance(row, dict) and type(row.get('a')) is str and type(row.get('b')) is str for row in rows),
            'raw pair inventory is incomplete')
    actual = [(row['a'], row['b']) for row in rows]
    require(len(set(actual)) == len(expected) and set(actual) == expected
            and report.get('participant_count') == len(names)
            and report.get('pair_count') == report.get('expected_pair_count') == len(expected),
            'raw unordered pairs are duplicated, omitted or outside the participant inventory')
    for row in rows:
        validate_frame(row)
        projection = row.get('relative_telescope_z_projection_mm')
        require(isinstance(projection, list) and len(projection) == 2 and all(finite(v) for v in projection)
                and projection[0] <= projection[1], 'relative telescope projection absent or invalid')
    require(all(row['disposition'] == 'clear' for row in rows)
            and report.get('counts') == dict(Counter(row['disposition'] for row in rows))
            and report.get('methods') == dict(Counter(row['method'] for row in rows))
            and report.get('unresolved_pairs') == report.get('confirmed_collision_witnesses') == []
            and report.get('evaluation_failures') == [] and type(report.get('evaluation_failure_count')) is int
            and report['evaluation_failure_count'] == 0, 'raw results disagree with the clearance summary')
    construction = report.get('construction_check', {})
    difference = construction.get('maximum_bidirectional_material_difference_mm3')
    require(construction.get('participants') == len(names) and finite(difference) and 0 <= difference <= TOL
            and construction.get('affine_law_is_code_owned_not_inferred_from_samples') is True,
            'whole-material affine construction check is incomplete or rejected')
    meta = report.get('native_scene_metadata', {})
    scene = meta.get('scene', {})
    require(meta.get('combined_participants') == len(names) and meta.get('candidate_participants') == 41
            and meta.get('mechanical_participants') == len(names)-46
            and scene.get('installed_mechanical_parts') == len(names)-46
            and scene.get('factory') == 'integration/product_split_assembly.py:split_scene'
            and scene.get('slide_mm') == report['domain']['slide_mm']
            and scene.get('descent_mm') == report['domain']['descent_mm']
            and scene.get('OPEN_hold_screws_installed') is (pose == 'OPEN')
            and scene.get('OPEN_display_support_insert_installed') is (pose == 'OPEN'),
            'full material factory/pose/accessory metadata differs')
    for key in ('physical_holding_and_force_qualified', 'OPEN_thread_retention_load_qualified',
                'loose_OPEN_accessories_have_onboard_storage', 'complete_functional_phone',
                'candidate_go', 'manufacturing_go'):
        require(scene.get(key) is False, 'factory metadata overclaims physical/product scope: '+key)
    declared = scene.get('source_inputs')
    require(isinstance(declared, dict) and declared and isinstance(scene.get('archive'), str),
            'factory payload identity absent')
    declared = {**declared, scene['archive']: scene.get('archive_sha256')}
    payloads = {name for name in current['head_bound_source_sha256']
                if name.startswith('engineering/') and not name.endswith('.py')}
    require(set(declared) == payloads, 'factory payload inventory is incomplete or changed')
    require(not scene.get('external_verified_source_inputs'), 'external factory overlay cannot pass canonical guard')
    for name, digest in declared.items():
        require(type(name) is str and name in current['head_bound_source_sha256']
                and current['head_bound_source_sha256'][name] == digest, 'factory payload differs from HEAD: '+str(name))
    return {'schema': 'razr-ep5-control-receipt-postcheck-v1', 'pose': pose, 'source_commit': expected_head,
            'participant_count': len(names), 'unique_unordered_pairs': len(expected),
            'bounded_control_receipt_checks_passed': True, 'geometry_recomputed_by_postcheck': False,
            'complete_product_motion_proved': False, 'physical_qualification': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--pose', choices=tuple(COUNTS), required=True)
    parser.add_argument('--expected-head', required=True)
    args = parser.parse_args(argv)
    current = current_identity(args.root, args.expected_head)
    result = validate_report(json.loads(args.report.read_text()), args.pose, args.expected_head, current)
    require(current_identity(args.root, args.expected_head) == current, 'sources/runtime changed during postcheck')
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
