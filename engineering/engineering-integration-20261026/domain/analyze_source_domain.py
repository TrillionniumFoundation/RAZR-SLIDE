#!/usr/bin/env python3
"""Enumerate the S4 source-domain polytopes without executing CAD or inventing stops.

The exact rational arithmetic here applies to recorded binary64 constants.
It does not turn rounded factory predicates into exact real arithmetic, and it
does not establish that the manufactured mechanism enforces these constraints.
"""
from __future__ import annotations

import argparse
import ast
from fractions import Fraction as F
import hashlib
import itertools
import json
import math
from pathlib import Path
import subprocess

S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
PATHS = (
    'integration/product_assembly.py',
    'integration/verify_cam_coupling.py',
    'integration/cam_coupling.py',
    'integration/cam_contact_profile.py',
    'integration/product_nominal_motion.py',
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def rank(rows):
    if not rows:
        return 0
    a = [list(map(F, row)) for row in rows]
    pivot = 0
    for col in range(len(a[0])):
        found = next((j for j in range(pivot, len(a)) if a[j][col]), None)
        if found is None:
            continue
        a[pivot], a[found] = a[found], a[pivot]
        d = a[pivot][col]
        a[pivot] = [x/d for x in a[pivot]]
        for j in range(len(a)):
            if j != pivot and a[j][col]:
                d = a[j][col]
                a[j] = [x-d*y for x, y in zip(a[j], a[pivot])]
        pivot += 1
        if pivot == len(a):
            break
    return pivot


def solve_equalities(rows):
    n = len(rows)
    a = [[*map(F, row['a']), F(row['b'])] for row in rows]
    for col in range(n):
        pivot = next((j for j in range(col, n) if a[j][col]), None)
        if pivot is None:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        d = a[col][col]
        a[col] = [x/d for x in a[col]]
        for j in range(n):
            if j != col and a[j][col]:
                d = a[j][col]
                a[j] = [x-d*y for x, y in zip(a[j], a[col])]
    return tuple(row[-1] for row in a)


def dot(a, x):
    return sum((c*v for c, v in zip(a, x)), F(0))


def enumerate_vertices(constraints, dimension):
    vertices = set()
    for chosen in itertools.combinations(constraints, dimension):
        point = solve_equalities(chosen)
        if point is not None and all(dot(row['a'], point) <= row['b'] for row in constraints):
            vertices.add(point)
    if not vertices:
        raise ValueError('empty vertex inventory')
    for point in vertices:
        active = [row['a'] for row in constraints if dot(row['a'], point) == row['b']]
        if rank(active) != dimension:
            raise ValueError('returned point is not a full-rank vertex')
    return sorted(vertices)


def source_constants(source):
    """Evaluate only the explicitly named numeric top-level source expressions."""
    allowed = {'K', 'G', 'R', 'TOL', 'STROKE', 'SEATING', 'KEY_STROKE', 'STAGE_MIN', 'STAGE_MAX'}
    def expr(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return expr(node.left)/expr(node.right)
        raise ValueError('unexpected constant expression')
    result = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in allowed:
                result[name] = expr(node.value)
    return result


def constraint(name, coefficients, rhs):
    return {'name': name, 'a': list(map(F, coefficients)), 'b': F(rhs)}


def motion_polytope(k, a, b, stroke, qmax):
    result = [constraint('slide_min', [-1, 0, 0, 0, 0], 0),
              constraint('slide_max', [1, 0, 0, 0, 0], stroke)]
    for side, index in (('L', 1), ('R', 3)):
        for sign in (-1, 1):
            row = [F(0)]*5; row[index] = sign
            result.append(constraint(f'{side}_cam_{sign}', row, a))
            row = [F(0)]*5; row[index] = sign; row[index+1] = -sign
            result.append(constraint(f'{side}_yoke_{sign}', row, b))
            row = [F(0)]*5; row[0] = sign*k; row[index+1] = sign
            result.append(constraint(f'{side}_profile_q_{sign}', row, qmax if sign == 1 else 0))
    return result


def section_vertices(slide, k, a, b, qmax):
    """A separate 2-D fixed-slide construction, used to cross-check 5-D vertices."""
    c = [constraint('cam+', [1, 0], a), constraint('cam-', [-1, 0], a),
         constraint('yoke+', [1, -1], b), constraint('yoke-', [-1, 1], b),
         constraint('q+', [0, 1], qmax-k*slide), constraint('q-', [0, -1], k*slide)]
    return enumerate_vertices(c, 2)


def independent_section_check(constraints, k, a, b, stroke, qmax):
    levels = {F(0), stroke}
    for dx, error in itertools.product((-a, a), (-b, b)):
        for q in (F(0), qmax):
            slide = (q-dx+error)/k
            if 0 <= slide <= stroke:
                levels.add(slide)
    points = set()
    for slide in levels:
        section = section_vertices(slide, k, a, b, qmax)
        for left, right in itertools.product(section, repeat=2):
            point = (slide, *left, *right)
            active = [row['a'] for row in constraints if dot(row['a'], point) == row['b']]
            if rank(active) == 5:
                points.add(point)
    return sorted(points)


def telescope_polytope():
    # Coordinates (descent, jL1, jL2, jR1, jR2); j_side3 = 8.5-d-j_side1-j_side2.
    lo, hi, total = F('.1'), F('2.9'), F('8.5')
    result = [constraint('descent_min', [-1, 0, 0, 0, 0], 0),
              constraint('descent_max', [1, 0, 0, 0, 0], F('8.2'))]
    for side, index in (('L', 1), ('R', 3)):
        for joint in (index, index+1):
            a = [F(0)]*5; a[joint] = 1
            result.append(constraint(f'{side}_j{joint-index+1}_max', a, hi))
            result.append(constraint(f'{side}_j{joint-index+1}_min', [-x for x in a], -lo))
        a = [F(0)]*5; a[0] = a[index] = a[index+1] = 1
        result.append(constraint(f'{side}_j3_min', a, total-lo))
        result.append(constraint(f'{side}_j3_max', [-x for x in a], hi-total))
    return result


def serialize_constraint(row):
    return {'name': row['name'], 'coefficients_exact': list(map(str, row['a'])), 'upper_bound_exact': str(row['b'])}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repository', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise ValueError('fresh analysis output required')
    sources = {}
    text = {}
    for name in PATHS:
        raw = subprocess.check_output(['git', '-C', str(args.repository), 'show', S4+':'+name])
        text[name] = raw.decode(); sources[name] = {'bytes': len(raw), 'sha256': digest(raw)}
    cam = source_constants(text['integration/verify_cam_coupling.py'])
    mech = source_constants(text['integration/cam_coupling.py'])
    assembly = source_constants(text['integration/product_assembly.py'])
    assert (cam['K'], cam['G'], cam['R'], assembly['TOL']) == (12/79.75, .425, .4, 1e-7)
    assert (mech['STROKE'], mech['SEATING'], mech['STAGE_MIN'], mech['STAGE_MAX']) == (79.75, 8.2, .1, 2.9)
    k = F.from_float(cam['K']); stroke = F('79.75'); qmax = F(12)
    a_float = (cam['G']-cam['R'])*math.hypot(1, cam['K'])
    b_float = (cam['G']-cam['R'])*math.sqrt(2)
    a, b = F.from_float(a_float), F.from_float(b_float)
    models = {}
    for label, half_a, half_b in (
        ('nominal_slot_bounds', a, b),
        ('with_actual_binary64_comparison_bound_TOL', F.from_float(a_float+1e-7), F.from_float(b_float+1e-7)),
    ):
        constraints = motion_polytope(k, half_a, half_b, stroke, qmax)
        vertices = enumerate_vertices(constraints, 5)
        other = independent_section_check(constraints, k, half_a, half_b, stroke, qmax)
        assert vertices == other
        rows = []
        for point in vertices:
            s, dx_l, dq_l, dx_r, dq_r = map(float, point)
            float_q = [cam['K']*s+dq_l, cam['K']*s+dq_r]
            float_slot = all(abs(dx) <= a_float+1e-7 and abs(dx-dq) <= b_float+1e-7
                             for dx, dq in ((dx_l, dq_l), (dx_r, dq_r)))
            rows.append({'exact_rational_coordinates': list(map(str, point)),
                         'binary64_coordinates': list(map(float, point)),
                         'original_arithmetic_q_after_binary64_vertex_conversion': float_q,
                         'source_slot_predicate_replay': float_slot,
                         'source_q_predicate_replay': all(0 <= q <= 12 for q in float_q),
                         'full_factory_not_called': True,
                         'active_constraints': [r['name'] for r in constraints if dot(r['a'], point) == r['b']]})
        models[label] = {'coordinates': ['slide', 'dxL', 'dqL', 'dxR', 'dqR'],
            'inequalities': [serialize_constraint(r) for r in constraints],
            'vertex_count': len(vertices), 'vertices': rows,
            'independent_fixed_section_product_enumeration_agrees': True,
            'stroke_strata': [{'slide_exact': str(s), 'slide_mm': float(s),
                               'vertices_at_slide': sum(p[0] == s for p in vertices)}
                              for s in sorted({p[0] for p in vertices})],
            'real_arithmetic_on_recorded_constants_only': True,
            'equivalent_to_all_binary64_factory_comparisons': False}
    tc = telescope_polytope(); tv = enumerate_vertices(tc, 5)
    result = {'schema': 'razr-S4-independent-source-domain-analysis-v1', 'functional_source': S4,
        'sources': sources, 'analyzer_sha256': digest(Path(__file__).read_bytes()),
        'native_constants': {'K': cam['K'], 'cam_halfwidth_mm': a_float, 'yoke_halfwidth_mm': b_float,
                             'dq_projection_halfwidth_mm': a_float+b_float, 'TOL': 1e-7},
        'models': models,
        'telescope_decimal_dimension_polytope': {'coordinates': ['descent', 'jL1', 'jL2', 'jR1', 'jR2'],
            'third_joint': '8.5-descent-j1-j2 independently on each side',
            'constraints': [serialize_constraint(r) for r in tc], 'vertex_count': len(tv),
            'vertices_exact': [list(map(str, p)) for p in tv],
            'descent_strata_mm': sorted({float(p[0]) for p in tv}),
            'source_TOL_shell_not_enumerated': True,
            'not_an_equal_extension_constraint': True},
        'endpoint_findings': {'STOW_profile_requires_dq_nonnegative': True,
            'OPEN_profile_requires_dq_nonpositive_at_actual_native_q_center_12': True,
            'unrestricted_slot_band_exits_finite_profile_travel_near_both_endpoints': True,
            'inner_nominal_stroke_distance_to_full_offset_band_mm': float((a+b)/k),
            'source_rejection_is_not_a_physical_stop': True,
            'not_a_proposal_to_remove_legal_geometry_without_mechanism_evidence': True},
        'required_additional_domains': ['independent manual tabs and slot flanks',
            'positive-q native STOP/SPRING profile branches and correlated motion',
            'independent telescope allocation through SEATING',
            'forward/reverse contact and preload selection',
            'accessory installation/removal and flexible self-validity'],
        'full_factory_executed': False, 'physical_constraint_support_verified': False,
        'continuous_collision_domain_proved': False, 'full_G2_pass': False,
        'candidate_go': False, 'manufacturing_go': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps({'output': str(args.output), 'motion_vertices': {k: v['vertex_count'] for k, v in models.items()},
                      'telescope_vertices': len(tv), 'full_factory_executed': False}))


if __name__ == '__main__':
    main()
