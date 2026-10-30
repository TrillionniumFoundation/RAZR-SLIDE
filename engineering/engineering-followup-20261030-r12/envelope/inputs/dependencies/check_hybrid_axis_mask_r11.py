"""Independent exact structural and hybrid-mask checker; no producer import."""
from collections import Counter, defaultdict
from fractions import Fraction as F
from itertools import product


def need(condition, message):
    if not condition:
        raise ValueError(message)


def vector(items):
    return tuple(map(F, items))


def parse_box(items):
    need(len(items) == 3 and all(len(x) == 2 for x in items), 'three complete bounds required')
    bounds = tuple(tuple(map(F, x)) for x in items)
    need(all(a < b for a, b in bounds), 'strictly positive finite mask widths required')
    return bounds


def add_scaled(origin, direction, t):
    return tuple(a + t*b for a, b in zip(origin, direction))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def axis_direction(v):
    indices = [i for i, value in enumerate(v) if value]
    need(len(indices) == 1 and v[indices[0]] in (-1, 1), 'exact unit coordinate axis required')
    return indices[0]


def signed_box_volume(bounds):
    return (bounds[0][1]-bounds[0][0]) * (bounds[1][1]-bounds[1][0]) * (bounds[2][1]-bounds[2][0])


def native_box(record, expected_bounds):
    """Check a complete world-axis boundary, rather than sampled coordinates."""
    B = parse_box(expected_bounds)
    m = record['metrics']
    need(not m['null'] and m['shape_type'] == 'TopAbs_SOLID', 'one whole native SOLID required')
    need(m['orientation'] == 'TopAbs_FORWARD', 'native root orientation must be forward')
    need(m['native_valid'] and m['signed_volume_float'] > 0, 'native validity and positive directed volume')
    need(m['infinity_state_at_tolerance_zero'] == 'TopAbs_OUT', 'unbounded complement must be OUT')
    need(m['counts'] == dict(solids=1, shells=1, faces=6, wires=6, edges=12, vertices=8), 'complete box topology census')
    need(m['root_children'] == ['TopAbs_SHELL'] and m['location_identity'], 'single identity-location closed shell required')
    need(len(record['vertices']) == 8 and len(record['edges']) == 12 and len(record['faces']) == 6, 'no omitted boundary record')
    expected_vertices = set(product(*B))
    vertices = {r['id']: vector(r['point_exact']) for r in record['vertices']}
    need(set(vertices) == set(range(1, 9)) and set(vertices.values()) == expected_vertices, 'all eight exact world vertices')
    need(all(r['location_identity'] for r in record['vertices']), 'vertex locations must be represented')
    expected_edges = set()
    for a in expected_vertices:
        for b in expected_vertices:
            if sum(x != y for x, y in zip(a, b)) == 1:
                expected_edges.add(frozenset((a, b)))
    edge_points = {}
    for row in record['edges']:
        need(row['type'] == 'GeomAbs_Line' and row['location_identity'], 'complete native line edge required')
        need(row['children'] == ['TopAbs_VERTEX', 'TopAbs_VERTEX'], 'edge has exactly two vertex uses')
        o, d = vector(row['origin_exact']), vector(row['direction_exact'])
        axis_direction(d)
        lo, hi = map(F, row['interval_exact'])
        need(lo < hi and len(row['vertices']) == 2, 'strict full line interval')
        pts = frozenset((add_scaled(o, d, lo), add_scaled(o, d, hi)))
        need(pts == frozenset(vertices[i] for i in row['vertices']), 'whole line matches both shared vertices exactly')
        need(row['id'] not in edge_points, 'duplicate edge record')
        edge_points[row['id']] = pts
    need(set(edge_points) == set(range(1, 13)) and set(edge_points.values()) == expected_edges, 'all twelve complete exact edges')
    sides = set()
    incidence = defaultdict(list)
    for face in record['faces']:
        need(face['type'] == 'GeomAbs_Plane' and face['location_identity'], 'complete native plane face')
        need(face['children'] == ['TopAbs_WIRE'] and len(face['edge_uses']) == 4, 'one complete four-edge wire')
        o, X, Y, n = (vector(face[key]) for key in ('origin_exact', 'X_exact', 'Y_exact', 'normal_exact'))
        axis = axis_direction(n)
        need(axis_direction(X) != axis_direction(Y) and cross(X, Y) == n, 'exact oriented orthogonal face basis')
        need(face['orientation'] in ('TopAbs_FORWARD', 'TopAbs_REVERSED'), 'face must be oriented')
        sign = 1 if face['orientation'] == 'TopAbs_FORWARD' else -1
        end = 1 if n[axis] * sign > 0 else 0
        need(o[axis] == B[axis][end], 'plane lies on exact expected outward side')
        side = (axis, end)
        need(side not in sides, 'duplicate native side')
        sides.add(side)
        u0, u1, v0, v1 = map(F, face['UV_exact'])
        need(u0 < u1 and v0 < v1, 'full nondegenerate UV rectangle')
        def mapped(uv):
            return tuple(o[k] + X[k]*uv[0] + Y[k]*uv[1] for k in range(3))
        uv_corners = set(product((u0, u1), (v0, v1)))
        world_corners = {mapped(uv) for uv in uv_corners}
        need(world_corners == {p for p in expected_vertices if p[axis] == B[axis][end]}, 'whole rectangular surface support equals exact side')
        expected_uv_edges = {frozenset((a, b)) for a in uv_corners for b in uv_corners
                             if sum(x != y for x, y in zip(a, b)) == 1}
        actual_uv_edges = set()
        for use in face['edge_uses']:
            need(use['type'] == 'GeomAbs_Line', 'all native pcurves must be complete lines')
            po, pd = vector(use['origin_exact']), vector(use['direction_exact'])
            axis_direction(pd)
            first, last = map(F, use['interval_exact'])
            need(first < last, 'full pcurve interval')
            pts = frozenset((add_scaled(po, pd, first), add_scaled(po, pd, last)))
            actual_uv_edges.add(pts)
            need(use['edge_id'] in edge_points and frozenset(mapped(p) for p in pts) == edge_points[use['edge_id']],
                 'entire affine pcurve and 3D shared edge agree, including endpoints')
            need(use['orientation'] in ('TopAbs_FORWARD', 'TopAbs_REVERSED'), 'oriented native coedge')
            incidence[use['edge_id']].append(use['orientation'])
        need(actual_uv_edges == expected_uv_edges, 'complete four trims, no seam hole or extra loop')
    need(sides == set(product(range(3), range(2))), 'all six outward sides')
    need(set(incidence) == set(edge_points), 'every edge belongs to full boundary')
    need(all(Counter(v) == Counter(['TopAbs_FORWARD', 'TopAbs_REVERSED']) for v in incidence.values()),
         'each shared edge occurs twice with opposite orientations')
    exact_volume = signed_box_volume(B)
    need(exact_volume > 0, 'positive exact directed box volume')
    return {'exact_bounds': [[str(a), str(b)] for a, b in B], 'directed_volume_exact': str(exact_volume),
            'complete_closed_axis_box_boundary_verified': True,
            'native_bounded_positive_valid': True, 'all_geometry_location_and_coedge_checks_passed': True}


def hybrid_mask(carrier_bounds, certificate):
    C, B = parse_box(carrier_bounds), parse_box(certificate['mask_box_exact'])
    need(certificate['effective_set'] == 'native_carrier_intersect_exact_closed_mask', 'declared effective set must include exact mask')
    need(certificate['analytic_orientation'] == 1, 'positive analytic orientation required')
    need(all(ca <= a < b <= cb for (ca, cb), (a, b) in zip(C, B)), 'complete mask must lie in native carrier')
    volume = signed_box_volume(B)
    need(F(certificate['directed_volume_exact']) == volume, 'retain complete exact positive mask volume')
    return {'exact_positive_mask_volume': str(volume), 'effective_set_equals_complete_mask': True,
            'analytic_closed_box_topology_verified': True, 'native_thin_BREP_materialized': False}


def intersection_volume(first, second):
    A, B = parse_box(first), parse_box(second)
    value = F(1)
    for a, b in zip(A, B):
        width = min(a[1], b[1]) - max(a[0], b[0])
        if width <= 0:
            return F(0)
        value *= width
    return value
