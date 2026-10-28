"""R4E independent rational support enclosures of all 16 original tiny frames.

Only standard-library exact arithmetic is used. No native Common is imported,
called, or used as an acceptance premise. Complete stored boundary supports
bound a compact material only under the separately retained boundary-semantics
premise. A tolerance-inflated diagnostic is a separate uncertainty model.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as F
import gzip
import hashlib
from itertools import combinations, product
import json
from math import isqrt
from pathlib import Path
import resource
import sys
import time
import traceback

IDENTITY = [["1", "0", "0", "0"], ["0", "1", "0", "0"], ["0", "0", "1", "0"]]
AXES = [(F(1), F(0), F(0)), (F(0), F(1), F(0)), (F(0), F(0), F(1))]
BITS = 128
TOL = F(1e-7)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def q(value):
    return F(value['exact']) if isinstance(value, dict) else F(value)


def vec(value):
    return tuple(q(x) for x in value)


def dot(a, b):
    return sum((x * y for x, y in zip(a, b)), F(0))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def determinant(rows):
    return dot(rows[0], cross(rows[1], rows[2]))


def enc(values):
    return [str(x) for x in values]


def interval(values):
    result = tuple(q(x) for x in values)
    require(len(result) == 2 and result[0] <= result[1], 'ordered finite exact interval required')
    return result


def scale_interval(coefficient, domain):
    a, b = (coefficient * x for x in domain)
    return min(a, b), max(a, b)


def sum_intervals(values):
    return tuple(sum((x[k] for x in values), F(0)) for k in (0, 1))


def sqrt_bounds(value):
    """Directed dyadic enclosure proved by integer-square comparisons."""
    require(value >= 0, 'nonnegative radicand required')
    denominator = 1 << BITS
    lower_numerator = isqrt((value.numerator << (2 * BITS)) // value.denominator)
    lo = F(lower_numerator, denominator)
    hi = lo if lo * lo == value else F(lower_numerator + 1, denominator)
    require(lo * lo <= value <= hi * hi and hi - lo <= F(1, denominator), 'directed sqrt certificate failed')
    return lo, hi


def identity(location):
    require(location['matrix_3x4_exact'] == IDENTITY, 'nonidentity placement outside registered exact representation subclass')


def canonical(direction):
    require(any(direction), 'zero direction refused')
    lead = next(x for x in direction if x)
    return tuple(x / lead for x in direction)


def curve_support(curve, direction):
    kind = curve['type'].split('.')[-1]
    domain = interval([curve['first_parameter'], curve['last_parameter']])
    if kind == 'GeomAbs_Line':
        origin = dot(vec(curve['origin_exact']), direction)
        return tuple(origin + x for x in scale_interval(dot(vec(curve['direction_exact']), direction), domain))
    if kind == 'GeomAbs_Circle':
        require(q(curve['radius']) > 0, 'positive circle radius required')
        centre = dot(vec(curve['center_exact']), direction)
        a, b = dot(vec(curve['X_exact']), direction), dot(vec(curve['Y_exact']), direction)
        radial = q(curve['radius']) * sqrt_bounds(a*a + b*b)[1]
        return centre - radial, centre + radial
    if kind == 'GeomAbs_BSplineCurve':
        data = curve['bspline']
        require(curve.get('complete_supported_representation') is True, 'missing actual BSpline supplement')
        require(data['degree'] == 1 and not data['is_periodic'] and not data['is_rational'], 'only original nonperiodic nonrational degree-one class admitted')
        poles = [vec(x) for x in data['poles_exact']]
        knots, weights = list(map(q, data['knots_exact'])), list(map(q, data['weights_exact']))
        require(len(poles) == len(knots) == len(weights) == 2 and data['multiplicities'] == [2, 2], 'two-pole clamped class required')
        require(weights[0] == weights[1] > 0 and knots[0] < knots[1], 'equal positive weights and ordered knots required')
        require(q(data['defined_first_parameter']) == knots[0] and q(data['defined_last_parameter']) == knots[1], 'defined BSpline domain differs')
        require(all(len(p) == len(direction) == data['dimension'] for p in poles), 'curve dimension mismatch')
        # Exact-real terminal affine extension at the ACTUAL trim endpoints.
        # Native/compiled execution correspondence is deliberately not inferred.
        values = []
        for t in domain:
            alpha = (t - knots[0]) / (knots[1] - knots[0])
            values.append(dot(tuple((1-alpha)*a + alpha*b for a, b in zip(*poles)), direction))
        return min(values), max(values)
    raise ValueError('unsupported complete curve class: ' + kind)


def face_domains(face):
    surface = face['local_surface']
    values = [interval(surface[k]) for k in ['U_interval', 'V_interval']]
    require(face['wires'], 'bounded trim loops required')
    for wire in face['wires']:
        identity(wire['location'])
        require(wire['native_IsClosed'] and wire['edge_occurrences'], 'complete closed trim loop required')
        for occurrence in wire['edge_occurrences']:
            identity(occurrence['location'])
            require(occurrence['edge_index'] is not None, 'unmapped trim edge')
            for k, direction in enumerate([(F(1), F(0)), (F(0), F(1))]):
                lo, hi = curve_support(occurrence['pcurve'], direction)
                values[k] = min(values[k][0], lo), max(values[k][1], hi)
    return values


class CompleteBoundary:
    def __init__(self, row):
        self.input = row['input']
        self.boundary = boundary = row['boundary']
        require(not boundary['incomplete_inventory'], 'incomplete original inventory')
        identity(boundary['location'])
        for label in ['solids', 'shells', 'faces', 'edges', 'vertices']:
            require(len(boundary[label]) == boundary['counts'][label], 'complete inventory count: ' + label)
            require([x['index'] for x in boundary[label]] == list(range(len(boundary[label]))), 'complete inventory indices: ' + label)
            for record in boundary[label]:
                identity(record['location'])
        require(boundary['counts']['solids'] == 1, 'original whole single material required')
        require(boundary['original_whole_material_guard']['passed'], 'original whole-material guard failed')
        require(all(x['Closed_flag'] for x in boundary['shells']), 'closed native shell metadata required')
        mapped = [i for shell in boundary['shells'] for i in shell['face_indices']]
        require(sorted(mapped) == list(range(boundary['counts']['faces'])), 'complete shell-to-face map required')
        self.domains = [face_domains(face) for face in boundary['faces']]
        self.max_tolerance = max(q(x['tolerance']) for label in ['faces', 'edges', 'vertices'] for x in boundary[label])
        require(self.max_tolerance >= 0, 'negative declared tolerance')
        self.cache = {}
        self.directions = {canonical(axis) for axis in AXES}
        for face in boundary['faces']:
            surface = face['local_surface']
            if surface['type'].endswith('GeomAbs_Plane'):
                normal = cross(vec(surface['X_exact']), vec(surface['Y_exact']))
                require(any(normal), 'singular affine plane')
                self.directions.add(canonical(normal))

    def support(self, direction, detailed=False):
        if not detailed and direction in self.cache:
            return self.cache[direction]
        pieces = []
        for face, domain in zip(self.boundary['faces'], self.domains):
            surface = face['local_surface']
            kind = surface['type'].split('.')[-1]
            origin = dot(vec(surface['origin_exact']), direction)
            if kind == 'GeomAbs_Plane':
                values = sum_intervals([scale_interval(dot(vec(surface['X_exact']), direction), domain[0]),
                                       scale_interval(dot(vec(surface['Y_exact']), direction), domain[1])])
                result = tuple(origin + x for x in values)
            elif kind == 'GeomAbs_Cylinder':
                require(q(surface['radius']) > 0, 'positive cylinder radius required')
                axial = scale_interval(dot(vec(surface['axis_exact']), direction), domain[1])
                a, b = dot(vec(surface['X_exact']), direction), dot(vec(surface['Y_exact']), direction)
                radial = q(surface['radius']) * sqrt_bounds(a*a + b*b)[1]
                result = origin + axial[0] - radial, origin + axial[1] + radial
            else:
                raise ValueError('unsupported complete face class: ' + kind)
            pieces.append({'kind': 'face', 'index': face['index'], 'support_exact': enc(result)})
        for edge in self.boundary['edges']:
            result = curve_support(edge['local_curve'], direction)
            pieces.append({'kind': 'edge', 'index': edge['index'], 'support_exact': enc(result)})
        for vertex in self.boundary['vertices']:
            value = dot(vec(vertex['local_point_exact']), direction)
            pieces.append({'kind': 'vertex', 'index': vertex['index'], 'support_exact': [str(value), str(value)]})
        require(pieces, 'empty boundary outside contract')
        result = min(F(x['support_exact'][0]) for x in pieces), max(F(x['support_exact'][1]) for x in pieces)
        self.cache[direction] = result
        if detailed:
            return {'normal_exact': enc(direction), 'input': self.input, 'complete_piece_count': len(pieces),
                    'counts': {k: self.boundary['counts'][k] for k in ['faces', 'edges', 'vertices']},
                    'support_exact': enc(result), 'pieces': pieces}
        return result


def moved_support(source, direction, displacement, inflation=F(0)):
    shift = sum_intervals([scale_interval(coefficient, domain) for coefficient, domain in zip(direction, displacement)])
    lo, hi = source.support(direction)
    error = inflation * sqrt_bounds(dot(direction, direction))[1]
    return lo + shift[0] - error, hi + shift[1] + error


def enclosure_for_basis(moving, fixed, displacement, basis, inflate=False):
    det = determinant(basis)
    require(det != 0, 'singular support coordinate basis')
    epsilon_a, epsilon_b = (moving.max_tolerance, fixed.max_tolerance) if inflate else (F(0), F(0))
    zero = [(F(0), F(0))] * 3
    aa = [moved_support(moving, n, displacement, epsilon_a) for n in basis]
    bb = [moved_support(fixed, n, zero, epsilon_b) for n in basis]
    intersection = [(max(a[0], b[0]), min(a[1], b[1])) for a, b in zip(aa, bb)]
    empty = [i for i, (lo, hi) in enumerate(intersection) if lo > hi]
    volume = F(0) if empty else (intersection[0][1]-intersection[0][0]) * (intersection[1][1]-intersection[1][0]) * (intersection[2][1]-intersection[2][0]) / abs(det)
    require(volume >= 0, 'negative intersection enclosure volume')
    return {'basis_rows_exact': [enc(n) for n in basis], 'basis_determinant_exact': str(det),
            'moving_coordinate_intervals_exact': [enc(x) for x in aa], 'fixed_coordinate_intervals_exact': [enc(x) for x in bb],
            'coordinate_intersection_intervals_exact': [enc(x) for x in intersection], 'separating_coordinate_indices': empty,
            'exact_intersection_upper_mm3': str(volume), 'upper_mm3_display': float(volume),
            'zero_measure_enclosure': volume == 0, 'positive_3D_solid_claimed': volume > 0,
            'uncertainty_inflation_exact_mm': [str(epsilon_a), str(epsilon_b)],
            'original_clearance_threshold_exact_mm3': str(TOL), 'original_clearance_gate_passed': volume <= TOL}


def enclosure_topology(enclosure):
    """Construct the selected exact cell and check oriented triangular topology."""
    ranges = [tuple(map(F, x)) for x in enclosure['coordinate_intersection_intervals_exact']]
    if any(lo > hi for lo, hi in ranges):
        return {'kind': 'certified_empty_coordinate_intersection', 'valid_set': True, 'oriented_volume_exact': '0', 'positive_3D_solid_claimed': False}
    rows = [vec(x) for x in enclosure['basis_rows_exact']]
    det = determinant(rows)
    columns = [tuple(x/det for x in cross(rows[(i+1)%3], rows[(i+2)%3])) for i in range(3)]
    require(all(dot(rows[j], columns[i]) == F(i == j) for i in range(3) for j in range(3)), 'exact inverse coordinate identity')
    bits = list(product((0, 1), repeat=3))
    vertices = [tuple(sum((columns[i][j]*ranges[i][bit[i]] for i in range(3)), F(0)) for j in range(3)) for bit in bits]
    require(all(dot(rows[i], v) == ranges[i][bit[i]] for bit, v in zip(bits, vertices) for i in range(3)), 'all exact corners must map back to coordinate bounds')
    dimension = sum(lo < hi for lo, hi in ranges)
    if dimension < 3:
        require(F(enclosure['exact_intersection_upper_mm3']) == 0, 'lower-dimensional set has nonzero volume')
        return {'kind': 'exact_lower_dimensional_parallelepiped', 'dimension': dimension, 'vertices_exact': [enc(v) for v in sorted(set(vertices))],
                'valid_set': True, 'set_not_discarded': True, 'oriented_volume_exact': '0', 'positive_3D_solid_claimed': False}
    lookup = {v: i for i, v in enumerate(bits)}
    faces = []
    for axis in range(3):
        others = [i for i in range(3) if i != axis]
        for side in (0, 1):
            face = []
            for pair in [(0, 0), (1, 0), (1, 1), (0, 1)]:
                bit = [0]*3; bit[axis] = side
                for i, value in zip(others, pair): bit[i] = value
                face.append(lookup[tuple(bit)])
            a, b, c = (vertices[i] for i in face[:3])
            normal = cross(tuple(y-x for x, y in zip(a, b)), tuple(y-x for x, y in zip(a, c)))
            outward = tuple((1 if side else -1)*x for x in rows[axis])
            if dot(normal, outward) < 0: face.reverse()
            faces.append(face)
    triangles = [(face[0], face[1], face[2]) for face in faces] + [(face[0], face[2], face[3]) for face in faces]
    edges = Counter((a, b) for tri in triangles for a, b in zip(tri, (*tri[1:], tri[0])))
    require(all(n == 1 and edges[(b, a)] == 1 for (a, b), n in edges.items()), 'not a closed oriented triangular manifold')
    directed = sum((dot(vertices[i], cross(vertices[j], vertices[k])) for i, j, k in triangles), F(0))/6
    require(directed == F(enclosure['exact_intersection_upper_mm3']) > 0, 'exact directed volume differs from coordinate determinant volume')
    require(len(vertices) - len(edges)//2 + len(triangles) == 2, 'Euler identity failed')
    for i, j, k in triangles:
        a, b, c = vertices[i], vertices[j], vertices[k]
        normal = cross(tuple(y-x for x, y in zip(a, b)), tuple(y-x for x, y in zip(a, c)))
        require(any(normal) and all(dot(normal, tuple(y-x for x, y in zip(a, v))) <= 0 for v in vertices), 'nonconvex or inward selected carrier triangle')
    return {'kind': 'exact_rational_closed_parallelepiped', 'dimension': 3, 'vertices_exact': [enc(v) for v in vertices],
            'outward_faces': faces, 'outward_triangles': triangles, 'closed_oriented_manifold': True, 'convex_embedding_checked': True,
            'oriented_volume_exact': str(directed), 'positive_3D_solid_claimed': True, 'valid_set': True}


def controls():
    rows = []
    for value in [F(0), F(1), F(2), F(1, 1 << 1074), F(2**100) + F(1, 2**100)]:
        lo, hi = sqrt_bounds(value)
        rows.append({'name': 'integer-square-directed-root', 'radicand_exact': str(value), 'bounds_exact': enc((lo, hi)),
                     'passed': lo*lo <= value <= hi*hi and hi-lo <= F(1, 1 << BITS)})
    circle = {'type': 'GeomAbs_CurveType.GeomAbs_Circle', 'first_parameter': {'exact': '0'}, 'last_parameter': {'exact': '7'},
              'center_exact': ['0', '0', '0'], 'X_exact': ['1', '0', '0'], 'Y_exact': ['0', '1', '0'], 'radius': {'exact': '1'}}
    lo, hi = curve_support(circle, (F(1), F(1), F(0)))
    # A rational 3-4-5 point is an independent witness beyond seam vertices.
    require(lo <= -F(7, 5) and hi >= F(7, 5), 'whole circle support lost nonvertex point')
    rows.append({'name': 'full-circle-rational-3-4-5-nonvertex-witness', 'support_exact': enc((lo, hi)), 'passed': True})
    class Box:
        max_tolerance = F(0)
        def __init__(self, ranges): self.ranges = ranges
        def support(self, n): return sum_intervals([scale_interval(c, r) for c, r in zip(n, self.ranges)])
    unit = Box([(F(0), F(1))] * 3)
    for name, xspan, expected in [('separated', (F(2), F(3)), F(0)), ('touching', (F(1), F(2)), F(0)),
                                  ('tiny-positive-overlap', (F(1)-F(1, 2**51), F(2)), F(1, 2**51)),
                                  ('whole-self-positive-control', (F(0), F(1)), F(1))]:
        second = Box([xspan, (F(0), F(1)), (F(0), F(1))])
        proof = enclosure_for_basis(unit, second, [(F(0), F(0))]*3, AXES)
        require(F(proof['exact_intersection_upper_mm3']) == expected, 'exact known box intersection differs: ' + name)
        rows.append({'name': name, 'expected_exact': str(expected), 'actual': proof, 'topology': enclosure_topology(proof), 'passed': True})
    reversed_proof = enclosure_for_basis(unit, unit, [(F(0), F(0))]*3, [AXES[0], AXES[2], AXES[1]])
    reversed_topology = enclosure_topology(reversed_proof)
    require(reversed_topology['oriented_volume_exact'] == '1' and F(reversed_proof['basis_determinant_exact']) == -1, 'negative coordinate determinant must retain positive outward volume')
    rows.append({'name': 'negative-coordinate-determinant-outward-volume', 'actual': reversed_proof, 'topology': reversed_topology, 'passed': True})
    for name, function in [('negative-radicand', lambda: sqrt_bounds(F(-1))), ('zero-support-normal', lambda: canonical((F(0),)*3)),
                            ('singular-coordinate-frame', lambda: enclosure_for_basis(unit, unit, [(F(0),F(0))]*3, [AXES[0], AXES[0], AXES[2]]))]:
        caught = None
        try: function()
        except ValueError as exc: caught = str(exc)
        require(caught is not None, 'malformed control accepted: ' + name)
        rows.append({'name': name, 'actual_rejection': caught, 'passed': True})
    return rows


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'new output required')
    args.output.mkdir(parents=True)
    contract = json.loads(args.contract.read_text())
    require(sha(Path(__file__)) == contract['producer_sha256'], 'registered producer source changed')
    started = time.monotonic()
    result = {'schema': 'razr-r4e-independent-complete-support-execution-v1', 'started_utc': datetime.now(timezone.utc).isoformat(),
              'contract_sha256': sha(args.contract), 'execution_completed': False, 'controls': [], 'frames': [],
              'input_identities': contract['input_identities'], 'native_Common_called': False, 'native_Common_value_used_as_acceptance_premise': False,
              'native_material_boundary_semantics_verified': False, 'compiled_curve_or_transform_rounding_verified': False,
              'full_continuous_G2': False, 'all_blockers_closed': False, 'old_actual_failures_reclassified': False}
    def save():
        result['seconds'] = time.monotonic() - started
        result['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        (args.output/'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    try:
        require(sys.flags.optimize == 0, 'optimized interpreter outside actual qualification')
        for row in contract['input_identities']:
            path = args.original/row['path']
            require(path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], 'original input identity differs: ' + row['path'])
        native = json.loads((args.original/'native-and-math/producer/worker/report.json').read_text())
        require(native['execution_completed'], 'incomplete original native inventory')
        by = {(r['input']['case_id'], r['input']['material_id']): r for r in native['operands']}
        supplement = json.loads((args.original/'native-and-math/bspline-producer/worker/report.json').read_text())
        require(supplement['execution_completed'], 'incomplete actual BSpline supplement')
        patches = 0
        for record in supplement['records']:
            original = by[(record['input']['case_id'], record['input']['material_id'])]['boundary']
            canonical_bytes = json.dumps(original, sort_keys=True, separators=(',', ':')).encode()
            require(hashlib.sha256(canonical_bytes).hexdigest() == record['original_complete_boundary_canonical_sha256'], 'supplement baseline identity differs')
            for curve in record['complete_pcurves']:
                target = original['faces'][curve['face_index']]['wires'][curve['wire_index']]['edge_occurrences'][curve['occurrence_index']]
                require(target['edge_index'] == curve['edge_index'] and target['pcurve'] == curve['old_pcurve_record'], 'supplement mapping differs')
                full = curve['complete_pcurve_record']
                require({k: v for k, v in full.items() if k not in ['bspline', 'complete_supported_representation']} == curve['old_pcurve_record'], 'supplement altered an old field')
                target['pcurve'] = full
                patches += 1
        require(patches == 44, 'all 44 original missing pcurves required')
        result['actual_pcurve_supplements_used'] = patches
        result['controls'] = controls()
        binding = json.loads((args.original/'source-and-inputs/R3E_INPUT_BINDING.json').read_text())
        cases = {x['case_id']: x for x in binding['cases']}
        originals_verified = 0
        for row in binding['all_selected_input_files']:
            path = args.original/'source-and-inputs'/row['relative_path']
            require(path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], 'original BREP identity changed')
            originals_verified += 1
        require(originals_verified == 53, '53 original BREP files required')
        material_cache = {}
        for record in native['tiny_base_Common']:
            case, frame = record['case_id'], record['frame']
            source_frame = next(x for x in cases[case]['tiny_frames'] if x['frame'] == frame)
            for key, value in source_frame.items():
                require(record[key] == value, 'native/reference frame mapping differs: ' + key)
            moving_key = case, record['moving_saved_material_id']
            fixed_key = case, record['fixed_original_material_id']
            for key in [moving_key, fixed_key]:
                if key not in material_cache: material_cache[key] = CompleteBoundary(by[key])
            moving, fixed = material_cache[moving_key], material_cache[fixed_key]
            displacement = [interval(x) for x in record['full_remaining_displacement_box_exact']]
            require(len(displacement) == 3 and all(lo <= 0 <= hi for lo, hi in displacement), 'original displacement box must contain zero')
            directions = sorted(moving.directions | fixed.directions)
            require(len(directions) <= contract['maximum_candidate_directions_per_frame'], 'registered finite direction capacity exceeded')
            tested, inflated = [], []
            for direction in directions:
                drop = max(range(3), key=lambda k: abs(direction[k]))
                basis = [direction] + [AXES[k] for k in range(3) if k != drop]
                tested.append(enclosure_for_basis(moving, fixed, displacement, basis))
                inflated.append(enclosure_for_basis(moving, fixed, displacement, basis, inflate=True))
            best = min(tested, key=lambda x: F(x['exact_intersection_upper_mm3']))
            robust = min(inflated, key=lambda x: F(x['exact_intersection_upper_mm3']))
            basis = [vec(x) for x in best['basis_rows_exact']]
            proof_directions = sorted(set(basis + [vec(x) for x in robust['basis_rows_exact']]))
            proof = {'schema': 'razr-r4e-complete-support-frame-proof-v1', 'case_id': case, 'frame': frame,
                     'original_pair': [cases[case]['target']['a'], cases[case]['target']['b']],
                     'moving_input': moving.input, 'fixed_input': fixed.input,
                     'full_remaining_displacement_box_exact': record['full_remaining_displacement_box_exact'],
                     'selected_exact_representation_enclosure': best, 'selected_declared_tolerance_diagnostic': robust,
                     'exact_representation_enclosure_topology': enclosure_topology(best),
                     'declared_tolerance_enclosure_topology': enclosure_topology(robust),
                     'all_registered_candidate_enclosures': tested, 'all_declared_tolerance_candidate_diagnostics': inflated,
                     'complete_support_proofs': [{'moving': moving.support(n, True), 'fixed': fixed.support(n, True)} for n in proof_directions],
                     'all_28_R3E_conditional_results_relabelled': False,
                     'remaining_premise': 'Each bounded compact material has its complete boundary contained in the union of these stored face, edge, and vertex parameterizations. Installed compiled evaluation/transform error and original native material semantics remain unproved.'}
            proof_name = case + '-frame-' + str(frame) + '-complete-support.json.gz'
            with (args.output/proof_name).open('wb') as file:
                with gzip.GzipFile(fileobj=file, mode='wb', filename='', mtime=0) as zipped:
                    zipped.write(json.dumps(proof, separators=(',', ':'), ensure_ascii=False).encode())
            whole_self = enclosure_for_basis(moving, moving, [(F(0),F(0))]*3, basis)
            require(not whole_self['original_clearance_gate_passed'], 'complete whole-self negative control falsely accepted')
            row = {'case_id': case, 'frame': frame, 'pair': proof['original_pair'], 'candidate_direction_count': len(directions),
                   'full_remaining_displacement_box_exact': record['full_remaining_displacement_box_exact'],
                   'conditional_complete_material_intersection_upper_exact_mm3': best['exact_intersection_upper_mm3'],
                   'conditional_complete_material_intersection_upper_mm3': best['upper_mm3_display'],
                   'original_clearance_gate_passed': best['original_clearance_gate_passed'],
                   'original_min_volume_plus_TOL_gate_passed': F(best['exact_intersection_upper_mm3']) <= F(record['original_rounded_min_plus_TOL_mm3']),
                   'base_Common_soundness_needed_for_this_certificate': False,
                   'native_boundary_semantics_remains_a_premise': True,
                   'declared_tolerance_diagnostic_upper_exact_mm3': robust['exact_intersection_upper_mm3'],
                   'declared_tolerance_diagnostic_upper_mm3': robust['upper_mm3_display'],
                   'declared_tolerance_diagnostic_gate_passed': robust['original_clearance_gate_passed'],
                   'maximum_declared_tolerances_exact_mm': [str(moving.max_tolerance), str(fixed.max_tolerance)],
                   'whole_self_negative_control': whole_self,
                   'proof': {'path': proof_name, 'bytes': (args.output/proof_name).stat().st_size, 'sha256': sha(args.output/proof_name)}}
            result['frames'].append(row)
            save()
            require(result['seconds'] <= contract['capacity']['wall_seconds'], 'registered wall limit')
            require(result['peak_RSS_bytes'] <= contract['capacity']['RSS_limit_bytes'], 'registered RSS limit')
            print(json.dumps({k: row[k] for k in ['case_id', 'frame', 'candidate_direction_count', 'conditional_complete_material_intersection_upper_mm3', 'original_clearance_gate_passed', 'declared_tolerance_diagnostic_upper_mm3', 'declared_tolerance_diagnostic_gate_passed']}), flush=True)
        require(len(result['frames']) == 16, 'complete original16 coverage required')
        result['original_BREP_files_reverified'] = originals_verified
        result['conditional_clearance_passes'] = sum(x['original_clearance_gate_passed'] for x in result['frames'])
        result['conditional_upper_bound_gate_failures'] = sum(not x['original_clearance_gate_passed'] for x in result['frames'])
        result['declared_tolerance_diagnostic_passes'] = sum(x['declared_tolerance_diagnostic_gate_passed'] for x in result['frames'])
        result['input_and_source_hashes_unchanged'] = sha(Path(__file__)) == contract['producer_sha256'] and all(sha(args.original/x['path']) == x['sha256'] for x in contract['input_identities'])
        require(result['input_and_source_hashes_unchanged'], 'input or source identity changed during execution')
        result['execution_completed'] = True
    except Exception as error:
        result['failure'] = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
    result['finished_utc'] = datetime.now(timezone.utc).isoformat()
    save()
    print(json.dumps({k: result.get(k) for k in ['execution_completed', 'failure', 'conditional_clearance_passes', 'conditional_upper_bound_gate_failures', 'declared_tolerance_diagnostic_passes', 'seconds', 'peak_RSS_bytes']}), flush=True)
    return 0 if result['execution_completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
