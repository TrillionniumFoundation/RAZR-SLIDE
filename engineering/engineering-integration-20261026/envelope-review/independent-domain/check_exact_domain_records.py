"""Small, CAD-free readback of recorded rational domain vertices.

Enumerating a parameter polytope is not a collision test, a floating-program
acceptance-set proof, or proof that physical stops enforce that polytope.
"""
from fractions import Fraction as F
from itertools import combinations
from pathlib import Path
import argparse
import hashlib
import json


def solve(rows, dimension):
    m = [[*a, b] for a, b in rows]
    for col in range(dimension):
        pivot = next((i for i in range(col, dimension) if m[i][col]), None)
        if pivot is None:
            return None
        m[col], m[pivot] = m[pivot], m[col]
        scale = m[col][col]
        m[col] = [x / scale for x in m[col]]
        for i in range(dimension):
            if i == col:
                continue
            scale = m[i][col]
            m[i] = [x - scale * y for x, y in zip(m[i], m[col])]
    return tuple(row[-1] for row in m)


def vertices(rows, dimension=5):
    result = set()
    for active in combinations(rows, dimension):
        point = solve(active, dimension)
        if point is not None and all(sum(x*y for x, y in zip(a, point)) <= b for a, b in rows):
            result.add(point)
    return result


def constraints(rows):
    return [(tuple(map(F, r['coefficients_exact'])), F(r['upper_bound_exact'])) for r in rows]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--domain-records', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    names = ('S4_SOURCE_DOMAIN_ANALYSIS.json', 'POSITIVE_Q_BRANCH_DOMAIN.json',
             'UNCLIPPED_SLOT_SOURCE_DOMAIN.json', 'FINITE_GROOVE_ENDCAP_PROJECTION.json')
    raw = {name: (args.domain_records / name).read_bytes() for name in names}
    saved = {name: json.loads(value) for name, value in raw.items()}
    d = saved[names[0]]
    assert d['functional_source'] == 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
    checks = {}
    for name, record in d['models'].items():
        computed = vertices(constraints(record['inequalities']))
        recorded = {tuple(map(F, row['exact_rational_coordinates'])) for row in record['vertices']}
        assert computed == recorded and len(computed) == record['vertex_count']
        checks[name] = {'exact_halfspace_vertex_enumeration_agrees': True, 'vertices': len(computed)}
    telescope = d['telescope_decimal_dimension_polytope']
    computed = vertices(constraints(telescope['constraints']))
    recorded = {tuple(map(F, row)) for row in telescope['vertices_exact']}
    assert computed == recorded and len(computed) == 28
    checks['telescope_decimal_polytope'] = {
        'exact_halfspace_vertex_enumeration_agrees': True, 'vertices': len(computed),
        'vertices_by_descent': {str(v): sum(row[0] == v for row in computed)
                                for v in sorted({row[0] for row in computed})}}
    branch = saved[names[1]]['independent_source_domain_cells']
    feasible = [row for row in branch if row['feasible']]
    assert len(branch) == 25 and len(feasible) == 17
    assert all(len(row['vertices_exact']) == row['vertex_count'] for row in branch)
    vertex_sum = sum(row['vertex_count'] for row in branch)
    out = {
        'schema': 'razr-independent-domain-exact-record-readback-v1',
        'functional_source_commit': d['functional_source'],
        'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_records': {name: {'sha256': hashlib.sha256(value).hexdigest(), 'bytes': len(value)}
                           for name, value in raw.items()},
        'checks': checks,
        'branch_cell_records': {'declared': len(branch), 'feasible': len(feasible),
            'empty': len(branch)-len(feasible), 'closed_cell_vertex_count_with_duplicates': vertex_sum,
            'maximum_vertices_per_cell': max(row['vertex_count'] for row in branch),
            'branch_cell_feasibility_recomputed_by_this_checker': False},
        'capacity_counts_not_execution_forecasts': {
            'all_pairs': 11781, 'all_pairs_times_17_branch_cells': 11781*len(feasible),
            'naive_slide_vertex_pose_pair_checks_with_tabs_and_flanks': vertex_sum*9*16*11781,
            'invalid_global_cartesian_60_motion_times_28_telescope_vertex_checks': 60*28*11781},
        'new_native_CAD_execution': False,
        'floating_factory_acceptance_set_certified': False,
        'continuous_collision_domain_proved': False,
        'physical_stop_or_preload_qualification': False,
        'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False}
    args.output.write_text(json.dumps(out, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'exact_polytope_checks': checks, 'output_bytes': args.output.stat().st_size}))


if __name__ == '__main__':
    main()
