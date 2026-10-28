"""Independent exact V7 planar exterior-certificate verifier.

New planar arithmetic is implemented here independently. Frozen prior
independent verifiers may recheck inherited proof bytes; V7 producer and
planar-model helper modules must never be imported by this verifier.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as Q
from functools import lru_cache
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from math import factorial
from pathlib import Path
import resource
import time
import traceback

TOL = Q(1e-7)
IDENTITY = [['1', '0', '0', '0'], ['0', '1', '0', '0'], ['0', '0', '1', '0']]
ORIENTATIONS = {'TopAbs_Orientation.TopAbs_FORWARD', 'TopAbs_Orientation.TopAbs_REVERSED'}


def need(value, message):
    if not value:
        raise ValueError(message)


def identity(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        value = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': value}


def content_equal(left, right):
    return all(left[name] == right[name] for name in ('bytes', 'sha256'))


def bound(record):
    path = Path(record['path']).resolve()
    need(content_equal(identity(path), record), 'bound source/input changed: ' + str(path))
    return path


def prior_module(record, name):
    path = bound(record)
    need(path.name in ('verify_primitive_support_r5e_v6.py', 'verify_exterior_trim_r5e_v5.py',
                       'verify_exterior_channels_r5e_v3.py', 'exterior_channels_r5e_v3.py'),
         'only registered frozen prior proof readers may be imported')
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def rat(value):
    return Q(value['exact']) if isinstance(value, dict) else Q(value)


def vector(values, n):
    need(type(values) in (list, tuple) and len(values) == n, 'complete exact vector dimension differs')
    return tuple(rat(v) for v in values)


def intervals(values, n, ordered=True):
    need(type(values) in (list, tuple) and len(values) == n and all(type(part) in (list, tuple) and len(part) == 2 for part in values),
         'complete exact interval dimension differs')
    result = tuple(tuple(map(Q, part)) for part in values)
    need(not ordered or all(a <= b for a, b in result), 'ordered closed intervals required')
    return result


def enc(values):
    return [str(value) for value in values]


def encbox(values):
    return [enc(part) for part in values]


def scalar(left, right):
    return sum((a*b for a, b in zip(left, right)), Q(0))


def plus(*values):
    return tuple(sum((part[index] for part in values), Q(0)) for index in (0, 1))


def times(coefficient, interval):
    values = [coefficient*x for x in interval]
    return min(values), max(values)


def product(left, right):
    values = [x*y for x in left for y in right]
    return min(values), max(values)


def closed_projection(normal, ranges):
    return plus(*(times(value, interval) for value, interval in zip(normal, ranges)))


def two_by_two_solve(matrix, rhs):
    """Rational pivot elimination, independent of producer inverse formulas."""
    rows = [[Q(matrix[i][j]) for j in range(2)] + [Q(rhs[i])] for i in range(2)]
    for column in range(2):
        pivot = next((i for i in range(column, 2) if rows[i][column]), None)
        need(pivot is not None, 'singular exact source linear system')
        rows[column], rows[pivot] = rows[pivot], rows[column]
        value = rows[column][column]
        rows[column] = [entry/value for entry in rows[column]]
        for other in range(2):
            if other != column:
                factor = rows[other][column]
                rows[other] = [a-factor*b for a, b in zip(rows[other], rows[column])]
    result = rows[0][2], rows[1][2]
    need(all(scalar(row, result) == value for row, value in zip(matrix, rhs)), 'exact source linear equation failed')
    return result


def plane_left_inverse(x, y):
    gram = ((scalar(x, x), scalar(x, y)), (scalar(y, x), scalar(y, y)))
    result = []
    for axis in range(2):
        coefficients = two_by_two_solve(gram, (int(axis == 0), int(axis == 1)))
        row = tuple(coefficients[0]*x[k]+coefficients[1]*y[k] for k in range(3))
        need(scalar(row, x) == int(axis == 0) and scalar(row, y) == int(axis == 1), 'plane left inverse fails original basis equations')
        result.append(row)
    return tuple(result)


def plane_project(left_inverse, origin, spatial_box):
    stationary = tuple((lo-origin[k], hi-origin[k]) for k, (lo, hi) in enumerate(spatial_box))
    return tuple(closed_projection(row, stationary) for row in left_inverse)


@lru_cache(maxsize=4096)
def horner_polynomials(centre):
    need(abs(centre) <= 8, 'source angle centre outside registered finite Taylor range')
    squared = centre*centre
    sine = cosine = Q(0)
    for k in reversed(range(24)):
        sine = sine*squared + Q((-1)**k, factorial(2*k+1))
        cosine = cosine*squared + Q((-1)**k, factorial(2*k))
    return sine*centre, cosine, abs(centre)**48/factorial(48)


def angular_certificate(domain):
    a, b = domain
    need(a <= b, 'complete original angular interval must be ordered')
    centre = Q(((a+b)*32768).__floor__(), 65536)
    sine, cosine, error = horner_polynomials(centre)
    return {'parameter_interval_exact': enc(domain), 'dyadic_centre_exact': str(centre),
            'actual_offset_interval_exact': enc((a-centre, b-centre)),
            'Maclaurin_sin_exact': str(sine), 'Maclaurin_cos_exact': str(cosine),
            'degree_47_Lagrange_error_exact': str(error), 'Taylor_term_count': 24,
            'centre_grid_denominator': 65536, 'source_endpoints_replaced': False}


def trigonometric_bounds(a, b, certificate):
    sine, cosine, error = (Q(certificate[name]) for name in ('Maclaurin_sin_exact', 'Maclaurin_cos_exact', 'degree_47_Lagrange_error_exact'))
    offset = tuple(map(Q, certificate['actual_offset_interval_exact']))
    constant = plus(times(a, (cosine-error, cosine+error)), times(b, (sine-error, sine+error)))
    derivative = plus(times(-a, (sine-error, sine+error)), times(b, (cosine-error, cosine+error)))
    remainder = (abs(a)+abs(b))*max(map(abs, offset))**2/2
    return plus(constant, product(derivative, offset), (-remainder, remainder))


def curve_point_box(curve, parameter):
    if curve['type'] == 'GeomAbs_CurveType.GeomAbs_Line':
        origin, direction = vector(curve['origin_exact'], 2), vector(curve['direction_exact'], 2)
        return tuple((origin[k]+direction[k]*parameter,)*2 for k in range(2))
    need(curve['type'] == 'GeomAbs_CurveType.GeomAbs_Circle', 'unsupported original pcurve endpoint')
    origin, x, y = vector(curve['center_exact'], 2), vector(curve['X_exact'], 2), vector(curve['Y_exact'], 2)
    radius = rat(curve['radius'])
    need(radius > 0, 'positive original circle radius required')
    certificate = angular_certificate((parameter, parameter))
    return tuple(plus((origin[k], origin[k]), times(radius, trigonometric_bounds(x[k], y[k], certificate))) for k in range(2))


def endpoint_distance_bounds(left, right):
    lower = max(max(Q(0), a-d, c-b) for (a, b), (c, d) in zip(left, right))
    upper = max(max(abs(a-d), abs(b-c)) for (a, b), (c, d) in zip(left, right))
    need(0 <= lower <= upper, 'exact endpoint interval-distance enclosure differs')
    return lower, upper


def strict_successors(initial, terminal):
    need(len(initial) == len(terminal) > 0, 'complete oriented endpoint sets required')
    answer = []
    for end in terminal:
        distances = [endpoint_distance_bounds(end, start) for start in initial]
        valid = [j for j, unused in enumerate(initial) if all(j == k or distances[j][1] < distances[k][0] for k in range(len(initial)))]
        need(len(valid) == 1, 'ambiguous exact endpoint successor must retain original whole face')
        answer.append(valid[0])
    need(sorted(answer) == list(range(len(initial))), 'successor map must be a bijection over the complete wire')
    visited = set()
    current = 0
    while current not in visited:
        visited.add(current)
        current = answer[current]
    need(current == 0 and len(visited) == len(initial), 'complete wire must be one directed successor cycle')
    return answer


def closure_box(terminal, initial):
    hull = tuple((min(a, c), max(b, d)) for (a, b), (c, d) in zip(terminal, initial))
    expansion = max(b-a for a, b in hull)
    return hull, expansion, tuple((a-expansion, b+expansion) for a, b in hull)


def strict_separator(piece, target, code):
    need(type(code) is str and len(code) == 1 and code in '012345', 'unknown strict closed UV separator')
    number = int(code)
    if number < 4:
        axis, end = divmod(number, 2)
        # V7 UV codes describe the side of the path relative to the carrier.
        # This is deliberately distinct from the inherited V6 spatial codes.
        return target[axis][1] < piece['box'][axis][0] if end == 0 else target[axis][0] > piece['box'][axis][1]
    need(len(piece['slabs']) == 1, 'strict UV nonaxis separator needs its one registered source slab')
    normal, support = piece['slabs'][0]
    need(any(normal) and support[0] <= support[1], 'valid nonzero closed UV slab required')
    projected = closed_projection(normal, target)
    return projected[1] < support[0] if number == 4 else projected[0] > support[1]


def uv_exterior_channel(target, known, axis, end):
    need(type(axis) is int and axis in (0, 1) and type(end) is int and end in (0, 1), 'registered UV path axis/end required')
    result = list(target)
    result[axis] = (min(known[axis][0]-1, target[axis][0]), target[axis][1]) if end == 0 else (target[axis][0], max(known[axis][1]+1, target[axis][1]))
    return tuple(result)


def source_occurrence(occurrence, wire_index, occurrence_index, limits):
    need(occurrence['location']['matrix_3x4_exact'] == IDENTITY and occurrence['edge_index'] is not None and
         occurrence['orientation'] in ORIENTATIONS, 'complete mapped oriented original pcurve required')
    curve = occurrence['pcurve']
    first, last = rat(curve['first_parameter']), rat(curve['last_parameter'])
    need(first <= last, 'complete source parameter order differs')
    domain = first, last
    kind = curve['type']
    prefix = {'wire_index': wire_index, 'occurrence_index': occurrence_index, 'source_edge_index': occurrence['edge_index']}
    pieces = []
    if kind == 'GeomAbs_CurveType.GeomAbs_Line':
        origin, direction = vector(curve['origin_exact'], 2), vector(curve['direction_exact'], 2)
        need(any(direction), 'nonzero original Line direction required')
        mapped = tuple(plus((origin[k], origin[k]), times(direction[k], domain)) for k in range(2))
        normal = -direction[1], direction[0]
        support = scalar(normal, origin)
        pieces.append(dict(prefix, kind='line', parameter_patch_index=None, parameter_interval_exact=enc(domain),
                           box_exact=encbox(mapped), additional_slabs=[{'normal_exact': enc(normal), 'bounds_exact': [str(support)]*2,
                                                                     'source': 'exact_pcurve_line'}]))
    else:
        need(kind == 'GeomAbs_CurveType.GeomAbs_Circle', 'unsupported original pcurve requires retention of the whole plane')
        origin, x, y = vector(curve['center_exact'], 2), vector(curve['X_exact'], 2), vector(curve['Y_exact'], 2)
        radius = rat(curve['radius'])
        need(radius > 0 and x[0]*y[1]-x[1]*y[0] != 0 and limits['circle_angular_patch_count'] == 64,
             'positive nonsingular source Circle and fixed64 patches required')
        for index in range(64):
            interval = first+(last-first)*Q(index,64), first+(last-first)*Q(index+1,64)
            trig = angular_certificate(interval)
            mapped = tuple(plus((origin[k], origin[k]), times(radius, trigonometric_bounds(x[k], y[k], trig))) for k in range(2))
            a, b = Q(trig['Maclaurin_cos_exact']), Q(trig['Maclaurin_sin_exact'])
            normal = two_by_two_solve((x, y), (a, b))
            need(any(normal) and scalar(normal, x) == a and scalar(normal, y) == b, 'exact original Circle dual normal differs')
            centre = scalar(normal, origin)
            support = plus((centre, centre), times(radius, trigonometric_bounds(a, b, trig)))
            pieces.append(dict(prefix, kind='circle_patch', parameter_patch_index=index, parameter_interval_exact=enc(interval),
                               trigonometric_certificate=trig, box_exact=encbox(mapped), radial_dual_coordinates_exact=enc((a,b)),
                               additional_slabs=[{'normal_exact': enc(normal), 'bounds_exact': enc(support),
                                                 'source': 'exact_pcurve_circle_radial_support'}]))
    endpoints = [curve_point_box(curve, first), curve_point_box(curve, last)]
    if occurrence['orientation'] == 'TopAbs_Orientation.TopAbs_REVERSED':
        endpoints.reverse()
    return pieces, endpoints


def source_wire(wire, limits):
    need(wire['location']['matrix_3x4_exact'] == IDENTITY and wire['orientation'] in ORIENTATIONS and wire['edge_occurrences'],
         'complete original identity wire and supported orientation required')
    occurrences = wire['edge_occurrences']
    pieces, endpoints = [], []
    for index, occurrence in enumerate(occurrences):
        children, pair = source_occurrence(occurrence, wire['index'], index, limits)
        pieces.extend(children); endpoints.append(pair)
    starts, ends = [pair[0] for pair in endpoints], [pair[1] for pair in endpoints]
    successors = strict_successors(starts, ends)
    joins = []
    for index, successor in enumerate(successors):
        distances = [endpoint_distance_bounds(ends[index], start) for start in starts]
        competitors = [lower for j, (lower, unused) in enumerate(distances) if j != successor]
        hull, expansion, gap = closure_box(ends[index], starts[successor])
        joins.append({'terminal_occurrence_index': index, 'initial_occurrence_index': successor,
                      'selected_Linf_distance_upper_exact': str(distances[successor][1]),
                      'minimum_competing_Linf_distance_lower_exact': str(min(competitors)) if competitors else None,
                      'endpoint_hull_exact': encbox(hull), 'closure_expansion_exact': str(expansion), 'closed_gap_box_exact': encbox(gap)})
        pieces.append({'kind': 'closure', 'wire_index': wire['index'], 'occurrence_index': index,
                       'successor_occurrence_index': successor, 'source_edge_index': occurrences[index]['edge_index'],
                       'parameter_patch_index': None, 'box_exact': encbox(gap), 'additional_slabs': []})
    record = {'wire_index': wire['index'], 'original_is_outer': wire['is_outer'], 'original_orientation': wire['orientation'],
              'source_occurrence_count': len(occurrences), 'successor_indices': successors,
              'oriented_endpoint_boxes_exact': [{'occurrence_index': i, 'start_box_exact': encbox(pair[0]), 'end_box_exact': encbox(pair[1])}
                                               for i, pair in enumerate(endpoints)],
              'join_certificates': joins, 'complete_closed_boundary_piece_count': len(pieces), 'native_closure_membership_verified': False}
    return pieces, record


def source_face(candidate, stationary, displacement, limits):
    face = candidate['complete_original_face']
    need(canonical(face) == candidate['complete_original_face_canonical_sha256'] and face['index'] == candidate['face_index'],
         'complete original mapped face identity differs')
    need(face['location']['matrix_3x4_exact'] == IDENTITY and face['orientation'] in ORIENTATIONS and face['wires'],
         'complete original identity Plane and orientation required')
    surface = face['local_surface']
    need(surface['type'] == 'GeomAbs_SurfaceType.GeomAbs_Plane', 'registered source primitive is not a Plane')
    origin, x, y = vector(surface['origin_exact'],3), vector(surface['X_exact'],3), vector(surface['Y_exact'],3)
    inverse = plane_left_inverse(x, y)
    determinant = scalar(x,x)*scalar(y,y)-scalar(x,y)**2
    need(determinant > 0, 'positive exact affine Gram determinant required')
    known = plane_project(inverse, origin, stationary)
    pieces, wires = [], []
    for wire in face['wires']:
        children, record = source_wire(wire, limits)
        pieces.extend(children); wires.append(record)
    need(len(pieces) <= limits['maximum_UV_pieces_per_face'], 'registered full UV face piece cap exceeded')
    return {'applied': True, 'plane_origin_exact': enc(origin), 'basis_X_exact': enc(x), 'basis_Y_exact': enc(y),
            'left_inverse_exact': [enc(row) for row in inverse], 'Gram_determinant_exact': str(determinant),
            'stationary_face_box_exact': encbox(stationary), 'full_D_exact': encbox(displacement),
            'known_UV_box_exact': encbox(known), 'wire_certificates': wires, 'uv_boundary_pieces': pieces,
            'source_occurrence_count': sum(w['source_occurrence_count'] for w in wires),
            'bounded_region_complete_boundary_cover_is_model_premise': True, 'native_planar_region_semantics_verified': False,
            'native_closure_membership_verified': False, 'conditional_planar_exterior_model_only': True}


def runtime_planar(record):
    pieces = []
    for piece in record['uv_boundary_pieces']:
        slabs = [(vector(s['normal_exact'],2), tuple(map(Q,s['bounds_exact']))) for s in piece['additional_slabs']]
        need(len(slabs) <= 1 and all(any(n) and a <= b for n,(a,b) in slabs), 'valid exact closed UV carrier/slab required')
        pieces.append({'box': intervals(piece['box_exact'],2), 'slabs': slabs})
    return {'model_index': record['model_index'], 'inverse': tuple(vector(row,3) for row in record['left_inverse_exact']),
            'origin': vector(record['plane_origin_exact'],3), 'stationary': intervals(record['stationary_face_box_exact'],3),
            'D': intervals(record['full_D_exact'],3), 'known': intervals(record['known_UV_box_exact'],2), 'pieces': pieces,
            'certificate': record}


def verify_models(serialized, prior_boundary, frame, projection, limits):
    need(serialized['schema'] == 'razr-r5e-planar-exterior-models-v7' and serialized['conditional_planar_exterior_model_only'] is True and
         serialized['native_planar_region_semantics_verified'] is False, 'new conditional planar model scope differs')
    records = {(r['input']['case_id'],r['input']['material_id']):r for r in projection['records']}
    binding = next(r for r in projection['frame_bindings'] if (r['case_id'],r['frame']) == (frame['case_id'],frame['frame']))
    need(binding['original_full_D'] == frame['original_remaining_displacement_box_exact'], 'complete original displacement changed')
    displacement = intervals(binding['original_full_D'],3)
    need(len(serialized['sources']) == len(prior_boundary['sources']) == 2, 'complete material model pair required')
    models, statistics = {}, Counter()
    next_model = 0
    for side, (source, old) in enumerate(zip(serialized['sources'], prior_boundary['sources'])):
        key = tuple(old['material_key'])
        need(source['material_key'] == old['material_key'] == binding['moving_and_fixed_material_keys'][side], 'original material side changed')
        candidates = {r['face_index']:r for r in records[key]['candidate_faces']}
        planes = [(i,piece) for i,piece in enumerate(old['pieces']) if piece['replacement'] == 'plane_slab']
        need(len(source['models']) == len(planes), 'complete original V6 plane model census differs')
        for record, (piece_index, piece) in zip(source['models'], planes):
            need(type(record['applied']) is bool, 'explicit boolean applied/rejected planar model status required')
            need(piece['kind'] == 'face' and piece['index'] in candidates, 'original plane source mapping differs')
            candidate = candidates[piece['index']]
            prefix = {'piece_index':piece_index, 'original_face_index':piece['index'], 'model_index':next_model,
                      'source_face_canonical_sha256':candidate['complete_original_face_canonical_sha256']}
            need(all(record[key] == value for key,value in prefix.items()), 'unique original plane/model index mapping differs')
            next_model += 1
            if record['applied'] is False:
                need(record['conditional_planar_exterior_model_only'] is True and record['native_planar_region_semantics_verified'] is False and
                     type(record['retained_original_plane_reason']) is str and record['retained_original_plane_reason'], 'rejected original plane needs explicit unchanged-model status')
                statistics['rejected'] += 1
                continue
            old_certificate = old['face_certificates'][piece['face_certificate_index']]
            stationary = intervals(old_certificate['stationary_original_box_exact'],3)
            shift = displacement if side == 0 else ((Q(0),Q(0)),)*3
            expected = dict(prefix, **source_face(candidate, stationary, shift, limits))
            need(record == expected, 'independently reconstructed complete planar model differs')
            models[(side,piece_index)] = runtime_planar(expected)
            statistics['applied'] += 1
            statistics['UV_pieces'] += len(expected['uv_boundary_pieces'])
            statistics['source_occurrences'] += expected['source_occurrence_count']
            statistics['wires'] += len(expected['wire_certificates'])
            statistics['lines'] += sum(p['kind'] == 'line' for p in expected['uv_boundary_pieces'])
            statistics['circle_patches'] += sum(p['kind'] == 'circle_patch' for p in expected['uv_boundary_pieces'])
            statistics['closures'] += sum(p['kind'] == 'closure' for p in expected['uv_boundary_pieces'])
    need(statistics['UV_pieces'] <= limits['maximum_total_UV_pieces'] and serialized['applied_plane_model_count'] == statistics['applied'] and
         serialized['rejected_plane_model_count'] == statistics['rejected'] and serialized['total_UV_boundary_piece_count'] == statistics['UV_pieces'],
         'complete new planar source capacity census differs')
    return models, dict(statistics)


def projected_candidate(model, spatial_channel):
    stationary = tuple((max(spatial_channel[k][0]-model['D'][k][1],model['stationary'][k][0]),
                        min(spatial_channel[k][1]-model['D'][k][0],model['stationary'][k][1])) for k in range(3))
    need(all(lo <= hi for lo,hi in stationary), 'empty stationary intersection belongs to the original spatial separation rule')
    return stationary, plane_project(model['inverse'],model['origin'],stationary)


def verify_uv_exclusion(proof, model, spatial_channel):
    need(proof['kind'] == 'complete_closed_UV_exterior_channel' and proof['model_index'] == model['model_index'] and
         proof['strict_closed_separation'] is True and proof['sampled_region_classification_used'] is False and
         proof['bounded_region_complete_boundary_cover_is_model_premise'] is True, 'UV exclusion scope or source model differs')
    stationary, target = projected_candidate(model, spatial_channel)
    need(proof['stationary_candidate_box_exact'] == encbox(stationary) and proof['closed_UV_target_box_exact'] == encbox(target),
         'complete inverse/old face/full-D stationary projection differs')
    path = uv_exterior_channel(target,model['known'],proof['axis'],proof['end'])
    need(proof['closed_UV_channel_exact'] == encbox(path), 'closed UV path must contain the complete target and reach known exterior')
    codes = proof['complete_UV_piece_separation_codes']
    need(type(codes) is str and len(codes) == len(model['pieces']) == proof['UV_boundary_piece_count'], 'complete UV boundary piece code census differs')
    for piece,code in zip(model['pieces'],codes):
        need(strict_separator(piece,path,code), 'strict closed UV boundary separation does not hold')
    return {'UV_pieces':len(codes),'UV_nonaxis':sum(code in '45' for code in codes)}


def verify_uv_unresolved(attempt, model, spatial_channel, partial=False):
    need(attempt['excluded'] is False and attempt['model_index'] == model['model_index'], 'unresolved UV model identity differs')
    stationary,target = projected_candidate(model,spatial_channel)
    need(attempt['stationary_candidate_box_exact'] == encbox(stationary) and attempt['closed_UV_target_box_exact'] == encbox(target),
         'unresolved UV inverse/full-D candidate differs')
    expected = [(axis,end) for axis in (0,1) for end in (0,1)]
    rows = attempt['completed_unresolved_UV_channels'] if partial else attempt['all_closed_UV_channels_unresolved']
    need([(r['axis'],r['end']) for r in rows] == expected[:len(rows)] and (len(rows) < 4 if partial else len(rows) == 4), 'complete or budget-prefix UV unresolved path order differs')
    for row in rows:
        path = uv_exterior_channel(target,model['known'],row['axis'],row['end'])
        need(row['closed_UV_channel_exact'] == encbox(path), 'unresolved closed UV path differs')
        index = row['unresolved_UV_piece_index']
        need(type(index) is int and 0 <= index < len(model['pieces']), 'unresolved original UV piece index invalid')
        piece = model['pieces'][index]
        need(not any(strict_separator(piece,path,str(code)) for code in range(6 if piece['slabs'] else 4)), 'declared UV blocker has an available strict separator')
    if partial:
        need(attempt['search_stopped_at_predicate_budget'] is True, 'partial UV attempt must be budget-stopped')
        stopped = attempt['incomplete_UV_channel']
        need((stopped['axis'],stopped['end']) == expected[len(rows)] and
             stopped['closed_UV_channel_exact'] == encbox(uv_exterior_channel(target,model['known'],stopped['axis'],stopped['end'])) and
             type(stopped['piece_index_at_stop']) is int and 0 <= stopped['piece_index_at_stop'] < len(model['pieces']) and
             stopped['completed_piece_prefix_count'] == stopped['piece_index_at_stop'], 'unfinished UV channel/piece prefix differs')
    else:
        need(attempt['actual_material_membership_claimed'] is False, 'unresolved UV query is not material membership')
    return len(rows)


def measure(cell):
    need(len(cell) == 3 and all(lo < hi for lo,hi in cell), 'positive directed spatial box required')
    result = Q(1)
    for lo,hi in cell:
        result *= hi-lo
    return result


def spatial_channel(cell, whole, axis, end):
    result = list(cell)
    result[axis] = (min(whole[axis][0]-1,cell[axis][0]-1),cell[axis][1]) if end == 0 else (
        cell[axis][0],max(whole[axis][1]+1,cell[axis][1]+1))
    return tuple(result)


def spatial_separator(piece, channel, code):
    need(type(code) is str and len(code) == 1 and code in '01234567', 'unregistered inherited spatial separator')
    number = int(code)
    if number < 6:
        axis,end = divmod(number,2)
        return piece['box'][axis][1] <= channel[axis][0] if end == 0 else piece['box'][axis][0] >= channel[axis][1]
    need(len(piece['additional_slabs']) == 1, 'inherited spatial nonaxis code needs its one registered slab')
    normal,support = piece['additional_slabs'][0]
    need(any(normal) and support[0] <= support[1], 'valid complete inherited spatial slab required')
    projected = closed_projection(normal,channel)
    need(projected[0] < projected[1], 'nonzero spatial support of a positive open box must have positive width')
    return support[1] <= projected[0] if number == 6 else support[0] >= projected[1]


def check_exclusion(proof, cell, sources, planar):
    need(proof['excluded_open_interior'] is True and proof['whole_closed_cell_disjoint_claimed'] is False and
         proof['closed_cell_boundary_retained_as_zero_volume_carrier'] is True, 'only open cell interior may be excluded')
    side,axis,end = (proof[key] for key in ('material_side','axis','end'))
    need(type(side) is int and 0 <= side < len(sources) and type(axis) is int and 0 <= axis < 3 and
         type(end) is int and end in (0,1), 'registered original material/channel indices required')
    channel = intervals(proof['open_channel_exact'],3)
    need(all(lo < hi for lo,hi in channel) and channel == spatial_channel(cell,sources[side]['whole'],axis,end),
         'positive open spatial channel must contain the cell interior and reach known exterior')
    pieces,codes = sources[side]['pieces'],proof['complete_piece_separation_codes']
    need(type(codes) is str and len(codes) == len(pieces) == proof['boundary_piece_count'], 'all original spatial carriers need a proof')
    rows = proof['planar_exterior_certificates']
    positions = [i for i,code in enumerate(codes) if code == 'u']
    need(type(rows) is list and [row['piece_index'] for row in rows] == positions and
         proof['planar_exterior_separation_code_count'] == len(positions), 'UV proof map must cover exactly the unique u positions in order')
    by_index = {row['piece_index']:row['certificate'] for row in rows}
    uv_pieces = uv_nonaxis = 0
    for index,(piece,code) in enumerate(zip(pieces,codes)):
        if code == 'u':
            need((side,index) in planar, 'u proof cannot replace an edge, vertex, cylinder or rejected planar model')
            result = verify_uv_exclusion(by_index[index],planar[(side,index)],channel)
            uv_pieces += result['UV_pieces']; uv_nonaxis += result['UV_nonaxis']
        else:
            need(spatial_separator(piece,channel,code), 'inherited spatial coordinate/slab does not separate the open channel')
    nonaxis = sum(code in '67' for code in codes)
    need(proof['nonaxis_separation_code_count'] == nonaxis, 'saved spatial nonaxis census differs')
    return {'pieces':len(codes),'nonaxis':nonaxis,'planar':len(positions),'UV_pieces':uv_pieces,'UV_nonaxis':uv_nonaxis}


def verify_spatial_blocker(row, cell, sources, planar):
    side,axis,end,index = (row[key] for key in ('material_side','axis','end','unresolved_piece_index'))
    need(all(type(value) is int for value in (side,axis,end,index)) and 0 <= side < len(sources) and
         0 <= axis < 3 and end in (0,1) and 0 <= index < len(sources[side]['pieces']), 'actual unresolved spatial carrier identity invalid')
    piece = sources[side]['pieces'][index]
    channel = spatial_channel(cell,sources[side]['whole'],axis,end)
    available = '01234567' if piece['additional_slabs'] else '012345'
    need(not any(spatial_separator(piece,channel,code) for code in available), 'spatial blocker has an available inherited separator')
    if (side,index) in planar:
        need('planar_exterior_attempt' in row and not row['planar_exterior_attempt'].get('search_stopped_at_predicate_budget'),
             'complete applied planar blocker needs its actual four unsuccessful UV paths')
        return verify_uv_unresolved(row['planar_exterior_attempt'],planar[(side,index)],channel)
    need('planar_exterior_attempt' not in row, 'unapplied original spatial carrier cannot carry a UV attempt')
    return 0


def check_unresolved(proof, cell, sources, planar, partial=False):
    need(proof['excluded_open_interior'] is False and proof['actual_material_interference_claimed'] is False,
         'unsuccessful path search is not an interference or exclusion proof')
    expected = [(side,axis,end) for side in range(len(sources)) for axis in range(3) for end in (0,1)]
    if partial:
        need(proof['search_stopped_at_predicate_budget'] is True and 'all_registered_channels_unresolved' not in proof,
             'budget prefix cannot claim complete twelve-channel failure')
        rows = proof['completed_unresolved_channels']
        need(len(rows) < len(expected), 'completed prefix must exclude its unfinished channel')
    else:
        need(not proof.get('search_stopped_at_predicate_budget'), 'unfinished predicate search cannot drive a split')
        rows = proof['all_registered_channels_unresolved']
        need(len(rows) == len(expected), 'all twelve registered failed channels required')
    need([(r['material_side'],r['axis'],r['end']) for r in rows] == expected[:len(rows)], 'failed channel order is incomplete or duplicated')
    uv = sum(verify_spatial_blocker(row,cell,sources,planar) for row in rows)
    if partial:
        stopped = proof['incomplete_spatial_channel']
        side,axis,end = (stopped[key] for key in ('material_side','axis','end'))
        index = stopped['piece_index_at_stop']
        need((side,axis,end) == expected[len(rows)] and type(index) is int and 0 <= index < len(sources[side]['pieces']) and
             stopped['completed_piece_prefix_count'] == index, 'unfinished spatial channel/piece prefix differs')
        if 'planar_exterior_attempt' in stopped:
            need((side,index) in planar, 'unfinished UV attempt must refer to its applied original planar carrier')
            piece = sources[side]['pieces'][index]
            channel = spatial_channel(cell,sources[side]['whole'],axis,end)
            available = '01234567' if piece['additional_slabs'] else '012345'
            need(not any(spatial_separator(piece,channel,code) for code in available), 'unfinished UV attempt skipped an inherited spatial separator')
            uv += verify_uv_unresolved(stopped['planar_exterior_attempt'],planar[(side,index)],channel,True)
    return len(rows),uv


def registered_cut(cell, sources, observation):
    """Unchanged V6 cut policy, independently expressed after V7 blocker checks."""
    endpoint_map, normals = {}, []
    for row in observation['all_registered_channels_unresolved']:
        side,index = row['material_side'],row['unresolved_piece_index']
        piece = sources[side]['pieces'][index]
        for axis in range(3):
            for end,point in enumerate(piece['box'][axis]):
                if cell[axis][0] < point < cell[axis][1] and (axis,point) not in endpoint_map:
                    endpoint_map[(axis,point)] = {'kind':'model_boundary_endpoint','material_side':side,'piece_index':index,'axis':axis,'endpoint':end}
        normals.extend((piece.get('slab_source') == 'exact_cylinder_patch_radial_support',normal) for normal,unused in piece['additional_slabs'])
    if endpoint_map:
        axis,point = sorted(endpoint_map,key=lambda item:(min(item[1]-cell[item[0]][0],cell[item[0]][1]-item[1])/
                                                          (cell[item[0]][1]-cell[item[0]][0]),item[0],item[1]))[0]
        return axis,point,endpoint_map[(axis,point)]
    radial = [normal for flag,normal in normals if flag]
    if radial:
        selected,rule = radial,'largest_registered_radial_slab_variation'
    elif normals:
        selected,rule = [normal for unused,normal in normals],'largest_registered_slab_variation'
    else:
        selected,rule = [],'longest_cell_interval'
    scores = [max((abs(normal[axis])*(cell[axis][1]-cell[axis][0]) for normal in selected),
                  default=cell[axis][1]-cell[axis][0]) for axis in range(3)]
    axis = scores.index(max(scores))
    return axis,sum(cell[axis],Q(0))/2,{'kind':'registered_midpoint','axis':axis,'selection_rule':rule}


def verify_tree(tree, root, sources, planar, limits):
    nodes = tree['nodes']
    need(type(nodes) is list and nodes and all(type(node) is dict and type(node.get('id')) is int and node['id'] == index
                                              for index,node in enumerate(nodes)), 'complete contiguous explicit new tree required')
    pending,visited = [(0,root,0)],set()
    kept = removed = Q(0)
    counts = Counter(); reasons = Counter()
    depth_max = 0; first_exclusion = first_split = first_planar = None
    leaf_records = []
    while pending:
        index,cell,depth = pending.pop()
        need(type(index) is int and 0 <= index < len(nodes) and index not in visited, 'missing, cyclic or repeated new tree node')
        visited.add(index); need(depth <= limits['maximum_depth'], 'new path exceeds original depth cap')
        depth_max = max(depth_max,depth); node = nodes[index]; value = measure(cell)
        if node['kind'] == 'split':
            need(value > Q(limits['tiny_retained_volume_exact']) and depth < limits['maximum_depth'], 'tiny or final-depth box cannot be split')
            observation = node['actual_channel_observation']
            spatial,uv = check_unresolved(observation,cell,sources,planar)
            counts['unresolved_spatial'] += spatial; counts['unresolved_UV'] += uv
            axis,point,witness = registered_cut(cell,sources,observation)
            need(type(node['axis']) is int and (node['axis'],Q(node['cut_exact']),node['cut_source']) == (axis,point,witness) and
                 cell[axis][0] < point < cell[axis][1], 'registered internal cut policy differs')
            children = node['children']
            need(type(children) is list and len(children) == 2 and children[0] != children[1] and
                 all(type(child) is int and index < child < len(nodes) for child in children), 'complete distinct forward partition children required')
            low,high = list(cell),list(cell)
            low[axis],high[axis] = (cell[axis][0],point),(point,cell[axis][1])
            volumes = measure(low),measure(high)
            need(Q(node['parent_positive_directed_volume_exact']) == value == sum(volumes,Q(0)) and
                 tuple(map(Q,node['children_positive_directed_volumes_exact'])) == volumes and
                 node['closed_cut_plane_retained_as_zero_volume_carrier'] is True, 'positive directed partition or closed cut carrier changed')
            pending.extend([(children[1],tuple(high),depth+1),(children[0],tuple(low),depth+1)])
            counts['splits'] += 1
            if first_split is None: first_split = index,cell
            continue
        need(node['kind'] in ('retained','excluded') and Q(node['positive_directed_volume_exact']) == value,
             'explicit positive leaf measure differs')
        counts['leaves'] += 1; leaf_records.append((index,cell,node))
        if node['kind'] == 'excluded':
            need(value > Q(limits['tiny_retained_volume_exact']), 'positive tiny leaf must remain fully retained')
            result = check_exclusion(node['certificate'],cell,sources,planar)
            for name,amount in result.items(): counts[name] += amount
            removed += value; counts['excluded_count'] += 1
            if first_exclusion is None: first_exclusion = node['certificate'],cell
            if first_planar is None and result['planar']: first_planar = node['certificate'],cell
        else:
            need(node['actual_material_interference_claimed'] is False, 'retained overbound is not measured interference')
            reason = node['reason']
            need(reason in ('tiny_exact_volume_retained','global_predicate_budget_retained','path_depth_limit_retained','global_split_limit_retained'),
                 'unregistered retention reason')
            need((value <= Q(limits['tiny_retained_volume_exact'])) == (reason == 'tiny_exact_volume_retained'), 'tiny threshold or stop classification changed')
            if reason == 'path_depth_limit_retained': need(depth == limits['maximum_depth'], 'depth stop does not match actual depth')
            if reason in ('path_depth_limit_retained','global_split_limit_retained'):
                need('actual_channel_observation' in node, 'path/split stop must preserve actual complete unresolved evidence')
            if 'actual_channel_observation' in node:
                observation = node['actual_channel_observation']; partial = observation.get('search_stopped_at_predicate_budget') is True
                need(not partial or reason == 'global_predicate_budget_retained', 'unfinished predicates cannot support another retention reason')
                spatial,uv = check_unresolved(observation,cell,sources,planar,partial)
                counts['unresolved_spatial'] += spatial; counts['unresolved_UV'] += uv
            kept += value; reasons[reason] += 1
    need(len(visited) == len(nodes) and len(nodes) == 2*counts['splits']+1 and counts['leaves'] == counts['splits']+1,
         'complete binary tree includes every allocated node exactly once')
    need(kept+removed == measure(root) and Q(tree['retained_sum_exact']) == kept and Q(tree['excluded_open_sum_exact']) == removed,
         'new complete root directed measure not conserved')
    need(tree['total_leaf_count'] == counts['leaves'] and tree['excluded_leaf_count'] == counts['excluded_count'] and
         tree['retained_leaf_count'] == counts['leaves']-counts['excluded_count'] and tree['retained_reason_counts'] == dict(reasons) and
         tree['maximum_depth_reached'] == depth_max and tree['actual_planar_exterior_separator_count_in_excluded_leaves'] == counts['planar'],
         'new complete leaf/depth/retention/saved-UV census differs')
    need(tree['all_closed_cut_planes_and_root_boundaries_retained'] is True, 'all original/new closed zero-volume carriers required')
    for name in ('splits','leaves','excluded_count','pieces','nonaxis','planar','UV_pieces','UV_nonaxis','unresolved_spatial','unresolved_UV'):
        counts[name] += 0
    return dict(counts,retained=kept,excluded=removed,nodes=len(nodes),depth=depth_max,reasons=reasons,
                sample_exclusion=first_exclusion,sample_split=first_split,sample_planar=first_planar,leaf_records=leaf_records)


def rejected(name, operation):
    failure = None
    try: operation()
    except (ValueError,KeyError,IndexError,TypeError,ZeroDivisionError,StopIteration) as exc: failure = str(exc)
    need(failure is not None, 'corrupted mathematical certificate accepted: '+name)
    return {'name':name,'actual_rejected':True,'reason':failure}


def applicability(rows, eligible, required, absent):
    need((len(rows) == required and all(r['actual_rejected'] is True for r in rows)) if eligible else not rows,
         'actual control execution/applicability census differs')
    return {'status':'executed' if eligible else 'not_applicable','actual_eligible_count':eligible,
            'reason':None if eligible else absent,'analytic_controls_are_separate':True}


def channel_controls(good, cell, sources, planar):
    variants = []
    altered = deepcopy(good); altered['complete_piece_separation_codes'] = good['complete_piece_separation_codes'][:-1]
    variants.append(('omitted-original-spatial-carrier',altered))
    altered = deepcopy(good); altered['whole_closed_cell_disjoint_claimed'] = True
    variants.append(('overclaim-closed-cell-disjointness',altered))
    altered = deepcopy(good); altered['open_channel_exact'][good['axis']][good['end']] = str(cell[good['axis']][good['end']])
    variants.append(('spatial-path-fails-known-exterior',altered))
    altered = deepcopy(good); channel = intervals(good['open_channel_exact'],3)
    index,code = next((index,code) for index,piece in enumerate(sources[good['material_side']]['pieces'])
                      for code in ('01234567' if piece['additional_slabs'] else '012345') if not spatial_separator(piece,channel,code))
    codes = list(altered['complete_piece_separation_codes']); codes[index] = code
    altered['complete_piece_separation_codes'] = ''.join(codes)
    altered['nonaxis_separation_code_count'] = sum(c in '67' for c in codes)
    altered['planar_exterior_certificates'] = [r for r in altered['planar_exterior_certificates'] if r['piece_index'] != index]
    altered['planar_exterior_separation_code_count'] = len(altered['planar_exterior_certificates'])
    variants.append(('false-inherited-separating-inequality',altered))
    return [rejected(name,lambda altered=altered:check_exclusion(altered,cell,sources,planar)) for name,altered in variants]


def tree_control(name, tree, root, sources, planar, limits, edit):
    altered = deepcopy(tree); edit(altered)
    return rejected(name,lambda:verify_tree(altered,root,sources,planar,limits))


def split_controls(tree, root, sources, planar, limits, stats):
    need(stats['sample_split'] is not None, 'actual split target absent')
    index,cell = stats['sample_split']
    variants = [('omitted-partition-child',lambda t:t['nodes'][index].update(children=t['nodes'][index]['children'][:1])),
                ('duplicated-partition-child',lambda t:t['nodes'][index].update(children=[t['nodes'][index]['children'][0]]*2)),
                ('cut-on-parent-boundary',lambda t:t['nodes'][index].update(cut_exact=str(cell[t['nodes'][index]['axis']][0]))),
                ('discarded-closed-cut-plane',lambda t:t['nodes'][index].update(closed_cut_plane_retained_as_zero_volume_carrier=False)),
                ('wrong-positive-parent-volume',lambda t:t['nodes'][index].update(parent_positive_directed_volume_exact='0'))]
    return [tree_control(name,tree,root,sources,planar,limits,edit) for name,edit in variants]


def leaf_controls(tree, root, sources, planar, limits, stats):
    index,cell,leaf = min(stats['leaf_records'],key=lambda row:measure(row[1]))
    rows = [tree_control('omitted-allocated-positive-leaf',tree,root,sources,planar,limits,lambda t:t['nodes'].pop(index)),
            tree_control('discarded-smallest-positive-leaf-volume',tree,root,sources,planar,limits,
                         lambda t:t['nodes'][index].update(positive_directed_volume_exact='0'))]
    for row in rows:
        row.update(original_leaf_id=index,original_leaf_kind=leaf['kind'],original_leaf_reason=leaf.get('reason'),
                   original_positive_volume_exact=leaf['positive_directed_volume_exact'])
    return rows


def uv_channel_controls(good, cell, sources, planar):
    need(good['planar_exterior_certificates'], 'actual saved planar proof target absent')
    row = good['planar_exterior_certificates'][0]
    model = planar[(good['material_side'],row['piece_index'])]
    channel = intervals(good['open_channel_exact'],3)
    proof = row['certificate']; path = intervals(proof['closed_UV_channel_exact'],2)
    changes = []
    changed = deepcopy(proof); changed['complete_UV_piece_separation_codes'] = proof['complete_UV_piece_separation_codes'][:-1]
    changes.append(('omitted-complete-UV-boundary-piece',changed))
    changed = deepcopy(proof); changed['stationary_candidate_box_exact'][0][0] = str(Q(changed['stationary_candidate_box_exact'][0][0])-1)
    changes.append(('changed-complete-full-D-stationary-candidate',changed))
    changed = deepcopy(proof); changed['closed_UV_target_box_exact'][0][0] = str(Q(changed['closed_UV_target_box_exact'][0][0])-1)
    changes.append(('changed-exact-plane-inverse-target',changed))
    changed = deepcopy(proof); changed['closed_UV_channel_exact'][proof['axis']][proof['end']] = proof['closed_UV_target_box_exact'][proof['axis']][proof['end']]
    changes.append(('UV-path-fails-known-exterior',changed))
    index,code = next((i,str(number)) for i,piece in enumerate(model['pieces']) for number in range(6 if piece['slabs'] else 4)
                      if not strict_separator(piece,path,str(number)))
    changed = deepcopy(proof); codes = list(changed['complete_UV_piece_separation_codes']); codes[index] = code
    changed['complete_UV_piece_separation_codes'] = ''.join(codes); changes.append(('false-strict-closed-UV-separator',changed))
    rows = [rejected(name,lambda changed=changed:verify_uv_exclusion(changed,model,channel)) for name,changed in changes]
    for name,edit in [('omitted-u-proof-map',lambda p:p.update(planar_exterior_certificates=p['planar_exterior_certificates'][1:])),
                      ('duplicated-u-proof-map',lambda p:p['planar_exterior_certificates'].append(deepcopy(p['planar_exterior_certificates'][0])))]:
        changed = deepcopy(good); edit(changed)
        rows.append(rejected(name,lambda changed=changed:check_exclusion(changed,cell,sources,planar)))
    return rows


V6_LOCK = '5cf2c18e7971912949e7e7167451cf547e291be421f205d78ef668fd7ab5b499'
V6_CHECKER = '05f7d1d76096e0518943bbdfbf6d5da7ae6a91248f83ef6e98432ae168df29bd'
SHARED_INPUT_FIELDS = ('r4_report','r4_independent_report','r4_stationary_diagnostic','public_input_bridge','method',
    'base_channel_source','base_verifier_source','single_verifier_source','planar_producer_source','planar_model_source',
    'primitive_producer_source','primitive_model_source','primitive_source_bundle','base_V6_verifier_source',
    'base_V6_input_bridge','base_V6_source_lock','base_V6_actual_report','base_V6_actual_independent_report',
    'base_V5_input_bridge','base_V5_source_lock','base_V5_verifier_source','V5_trim_source_bundle',
    'base_V5_actual_report','base_V5_actual_independent_report','real_retained_leaf_selection','static_source_capacity')


def require_scope(record):
    for name in ('conditional_planar_exterior_model_only','conditional_primitive_support_model_only','conditional_trim_model_only'):
        need(record[name] is True, 'complete conditional model scope required: '+name)
    for name in ('native_planar_region_semantics_verified','native_primitive_semantics_verified','native_trim_class_membership_verified',
                 'inner_wire_hole_semantics_verified_for_native','original_raw_gate_reclassified','full_continuous_G2'):
        need(record[name] is False, 'unverified original/native scope was promoted: '+name)


def fixed_limits(limits):
    expected = {'wall_seconds':600,'RSS_limit_bytes':805306368,'maximum_splits':4096,'maximum_depth':24,
                'maximum_boundary_box_tests':12000000,'maximum_support_inequality_tests':12000000,
                'maximum_boundary_pieces_per_material':4096,'cylinder_angular_patch_count':64,'circle_angular_patch_count':64,
                'Taylor_term_count':24,'centre_grid_denominator':65536,'maximum_UV_pieces_per_face':225,
                'maximum_total_UV_pieces':4064,'maximum_planar_models':48,'maximum_actual_V6_retained_roots':4943}
    need(all(type(limits[name]) is int and limits[name] == value for name,value in expected.items()) and
         Q(limits['tiny_retained_volume_exact']) == TOL/100000 and limits['all_UV_tests_charged_to_original_combined_budgets'] is True,
         'original finite gates/TOL, full-source policy or combined UV budget changed')


def relative_bound(record, directory):
    directory = Path(directory).resolve(); path = (directory/record['path']).resolve()
    need(path.is_relative_to(directory) and content_equal(identity(path),record), 'relative certificate bytes/path binding differs')
    return path


def gzip_json(path):
    with gzip.open(path,'rt') as stream: return json.load(stream)


def archived_v6(contract, v6):
    bridge = json.loads(bound(contract['base_V6_input_bridge']).read_text())
    need(bridge['schema'] == 'razr-r5e-immutable-actual-v6-input-bridge-v7' and bridge['actual_execution_kind'] == 'local_owned_pipeline' and
         bridge['original_reports_or_certificates_edited'] is False and bridge['path_mapping_only'] is True and
         bridge['actual_GitHub_run_claimed'] is False and bridge['actual_pipeline_source_lock_sha256'] == V6_LOCK and
         bridge['source_V6_passes'] == 8 and bridge['source_V6_frames'] == 16, 'immutable actual local V6 scope differs')
    root = Path(contract['base_V6_root']).resolve(); actual = {}
    for row in bridge['files']:
        path = (root/row['path']).resolve()
        need(path.is_relative_to(root) and row['path'] not in actual, 'duplicate or escaping archived V6 path')
        actual[row['path']] = identity(path)
        need(content_equal(actual[row['path']],row), 'original actual V6 input bytes changed')
    need(len(actual) == len(bridge['files']) == 53, 'all53 original V6 files must be retained')
    def read(name): return json.loads(Path(actual[name]['path']).read_text())
    prior,verified,pipeline = (read(name) for name in ('all-primitive-support-frames/report.json','verify-all/report.json','pipeline.json'))
    need(prior['execution_completed'] is True and verified['execution_completed'] is True and pipeline['completed'] is True and
         pipeline['source_and_public_inputs_unchanged'] is True, 'original local V6 must be actually complete')
    need(content_equal(bridge['actual_pipeline_identity'],actual['pipeline.json']) and
         content_equal(contract['base_V6_source_lock'],pipeline['source_lock_identity']) and contract['base_V6_source_lock']['sha256'] == V6_LOCK,
         'original V6 pipeline/source lock identity differs')
    lock = json.loads(bound(contract['base_V6_source_lock']).read_text())
    members = {row['path']:row for row in lock['r5_files']}
    for field,name in [('base_V6_verifier_source','verify_primitive_support_r5e_v6.py'),
                       ('primitive_producer_source','primitive_refinement_r5e_v6.py'),
                       ('primitive_model_source','primitive_support_model_r5e_v6.py'),
                       ('primitive_source_bundle','R5E_V6_PRIMITIVE_SOURCE.json.gz'),
                       ('base_V5_verifier_source','verify_exterior_trim_r5e_v5.py'),
                       ('base_verifier_source','verify_exterior_channels_r5e_v3.py')]:
        bound(contract[field]); need(content_equal(contract[field],members[name]), 'frozen prior source differs: '+name)
    need(contract['base_V6_verifier_source']['sha256'] == V6_CHECKER, 'frozen independent V6 verifier differs')
    fields = {'base_V6_actual_report':'all-primitive-support-frames/report.json',
              'base_V6_actual_independent_report':'verify-all/report.json',
              'base_V6_actual_owned_supervision':'all-primitive-support-frames-supervision/controller.json',
              'base_V6_actual_independent_owned_supervision':'verify-all-supervision/controller.json'}
    need(all(contract[field] == actual[name] for field,name in fields.items()), 'original V6 report/receipt mapping differs')
    labels = ['single-primitive-support-leaf','verify-single','preflight-primitive-support','all-primitive-support-frames','verify-all']
    phases = ['single_primitive_support_leaf','verify_single','preflight_primitive_support','all_primitive_support_frames','verify_all']
    need([stage['label'] for stage in pipeline['stages']] == labels, 'original complete five-stage pipeline order changed')
    expected_files = {'pipeline.json'}
    for stage,label,phase in zip(pipeline['stages'],labels,phases):
        name = 'verify_primitive_support_r5e_v6.py' if label.startswith('verify-') else 'primitive_refinement_r5e_v6.py'
        item = read(label+'/report.json'); controller = read(label+'-supervision/controller.json')
        math_contract = read(label+'-contract.json'); supervision = read(label+'-supervision-contract.json')
        v6.owned_completion(controller,item,members[name]['sha256'])
        need(stage['completed'] is True and stage['phase'] == phase and stage['supervisor_exit_code'] == 0 and
             content_equal(stage['report'],actual[label+'/report.json']) and content_equal(stage['controller'],actual[label+'-supervision/controller.json']) and
             content_equal(stage['contract'],actual[label+'-contract.json']) and content_equal(stage['supervision_contract'],actual[label+'-supervision-contract.json']),
             'actual inherited V6 stage/contract/receipt identity differs')
        need(item['execution_completed'] is True and math_contract['phase'] == phase and math_contract['producer_sha256'] == members[name]['sha256'] and
             actual[label+'-contract.json']['sha256'] == item['contract_sha256'] == supervision['registered_math_contract_sha256'] and
             Path(controller['limits']['worker_output_directory']) == Path(stage['report']['path']).parent,
             'inherited V6 actual output/source mathematical contract differs')
        v6.fixed_limits(math_contract['capacity'])
        v6.require_scope(item)
        expected_files.update({label+'/report.json',label+'-contract.json',label+'-supervision-contract.json',label+'-driver.log',
                               label+'-supervision/controller.json',label+'-supervision/entry-receipt.json',label+'-supervision/execution.log'})
        if label in ('single-primitive-support-leaf','all-primitive-support-frames'):
            expected_files.update(label+'/'+row['certificate']['path'] for row in item['frames'])
    need(set(actual) == expected_files, 'complete original V6 output file coverage differs')
    need(prior['phase'] == 'all_primitive_support_frames' and prior['primitive_support_model_conditional_clearance_passes'] ==
         verified['primitive_support_model_conditional_clearance_passes'] == 8 and len(prior['frames']) == 16 and
         verified['expected_phase'] == 'all_primitive_support_frames' and
         verified['expected_case_frames'] == [[row['case_id'],row['frame']] for row in prior['frames']] and
         content_equal(verified['verified_producer_report'],actual['all-primitive-support-frames/report.json']),
         'original V6 complete independent eight-of-sixteen result changed')
    need(prior['source_and_contract_unchanged'] is True and verified['all_checked_source_contract_and_archived_inputs_unchanged'] is True,
         'original V6 end identities were not complete')
    return actual,prior,verified,pipeline


def phase_coverage(producer, contract, baseline, selection):
    phase = contract['expected_phase']; actual = [(r['case_id'],r['frame']) for r in producer['frames']]
    expected = [tuple(value) for value in contract['expected_case_frames']]
    original = [(r['case_id'],r['frame']) for r in baseline['frames']]
    need(producer['phase'] == phase and phase in ('single_planar_exterior_leaf','all_planar_exterior_frames') and
         len(actual) == len(set(actual)) and len(expected) == len(set(expected)) and actual == expected,
         'new actual phase/frame sequence omitted, duplicated or reordered')
    if phase == 'single_planar_exterior_leaf':
        need(actual == [(selection['case_id'],selection['frame'])] == [('case-028',1)] and actual[0] in original, 'registered actual selected frame differs')
    else: need(actual == original and len(actual) == 16, 'all original sixteen frames required')


def phase_controls(producer, contract, baseline, selection):
    rows = [('omitted-actual-frame',dict(producer,frames=producer['frames'][:-1])),
            ('duplicated-actual-frame',dict(producer,frames=producer['frames']+[producer['frames'][0]])),
            ('wrong-actual-phase',dict(producer,phase='preflight_planar_exterior'))]
    return [rejected(name,lambda changed=changed:phase_coverage(changed,contract,baseline,selection)) for name,changed in rows]


def root_coverage(frame, certificate, leaves):
    expected = [leaf['locator'] for leaf in leaves]
    need(frame['root_base_V6_leaf_locators'] == expected and frame['root_count'] == len(expected) and
         [root['base_V6_leaf_locator'] for root in certificate['roots']] == expected, 'every actual V6 retained root required exactly once in order')
    for root,leaf in zip(certificate['roots'],leaves):
        need(root['root_box_exact'] == encbox(leaf['box']) and Q(root['root_directed_volume_exact']) == leaf['volume'] == measure(leaf['box']),
             'full original positive retained root domain/measure changed')


def root_controls(frame, certificate, leaves):
    need(leaves, 'actual retained root mutation target absent')
    return [rejected(name,lambda roots=roots:root_coverage(frame,dict(certificate,roots=roots),leaves)) for name,roots in
            [('omitted-actual-V6-retained-root',certificate['roots'][:-1]),
             ('duplicated-actual-V6-retained-root',certificate['roots']+[certificate['roots'][0]])]]


def recheck_v6_frame(row, certificate, old_v5, v5_certificate, v5_leaves, v5_kept, v5_removed,
                     old_r4, v6, records, bindings, limits):
    need(certificate['schema'] == 'razr-r5e-primitive-support-tree-v6' and certificate['frame'] == {k:v for k,v in row.items() if k != 'certificate'} and
         certificate['V5_producer_rerun'] is False and Q(certificate['actual_V5_excluded_open_sum_preserved_exact']) == v5_removed,
         'inherited complete actual V6 frame header differs')
    need(row['pair'] == old_v5['pair'] and row['original_raw_proof_identity'] == old_v5['original_raw_proof_identity'] and
         row['original_remaining_displacement_box_exact'] == old_v5['original_remaining_displacement_box_exact'] and
         row['base_V5_frame_conditional_upper_exact_mm3'] == old_v5['trim_model_conditional_upper_exact_mm3'] and
         Q(row['base_V5_retained_leaf_sum_exact']) == v5_kept and Q(row['base_V5_excluded_open_leaf_sum_exact']) == v5_removed,
         'inherited V6 full original materials/displacement/measure changed')
    sources,audit = v6.verify_boundary(certificate['boundary_refinement'],v5_certificate['boundary_refinement'],old_v5,records,bindings,limits)
    need(row['source_piece_counts'] == [len(source['pieces']) for source in sources] and row['applied_plane_face_count'] == audit['planes'] and
         row['applied_cylinder_face_count'] == audit['cylinders'] and row['retained_original_face_count_after_rejection'] == audit['fallbacks'],
         'inherited V6 complete original carrier census differs')
    v6.root_coverage(row,certificate,v5_leaves)
    kept = removed = Q(0); counts = Counter(); leaves = []; maximum_depth = 0
    for root_index,root in enumerate(certificate['roots']):
        result = v6.verify_tree(root['tree'],intervals(root['root_box_exact'],3),sources,limits)
        kept += result['retained']; removed += result['excluded']; maximum_depth = max(maximum_depth,result['depth'])
        for key in ('splits','nodes','leaves','excluded_count','pieces_checked','nonaxis_checked','unresolved_piece_records_checked'): counts[key] += result[key]
        # The frozen verifier supplies complete DFS left-first leaf records after its own full source proof checks.
        depth_by_node = {0:0}
        for node in root['tree']['nodes']:
            if node['kind'] == 'split':
                for child in node['children']: depth_by_node[child] = depth_by_node[node['id']]+1
        for index,cell,node in result['leaf_records']:
            if node['kind'] == 'retained':
                leaves.append({'locator':[root_index,index],'box':cell,'volume':measure(cell),'node':node,
                               'depth':depth_by_node[index],'base_V5_leaf_locator':root['base_V5_leaf_locator']})
    need(kept+removed == v5_kept == Q(row['new_root_sum_exact']) and kept == Q(row['retained_leaf_sum_exact']) and
         removed == Q(row['newly_excluded_open_leaf_sum_exact']), 'inherited actual V6 complete directed volume differs')
    upper = min(kept,Q(old_r4['coarse_whole_support_upper_exact_mm3']))
    need(Q(row['primitive_support_model_conditional_upper_exact_mm3']) == upper and row['primitive_support_model_conditional_upper_mm3'] == float(upper) and
         row['primitive_support_model_conditional_clearance_gate_passed'] == (upper <= TOL) and upper <= Q(old_v5['trim_model_conditional_upper_exact_mm3']),
         'inherited actual V6 original-TOL conditional bound differs')
    need(row['all_V5_and_new_closed_carriers_retained'] is True and row['exact_splits_this_frame'] == counts['splits'] and
         row['total_leaf_count'] == counts['leaves'] and row['maximum_depth_reached'] == maximum_depth and
         sum((leaf['volume'] for leaf in leaves),Q(0)) == kept, 'inherited complete actual V6 tree/leaf census differs')
    return leaves,kept,removed,sources,dict(counts,source_reconstruction=audit,retained_roots=len(leaves),
               retained_sum_exact=str(kept),excluded_sum_exact=str(removed),maximum_depth=maximum_depth,
               original_closed_carriers_retained=True,V6_producer_rerun=False)


def model_controls(serialized, boundary, frame, projection, limits):
    candidates = [(side,index,record) for side,source in enumerate(serialized['sources']) for index,record in enumerate(source['models']) if record['applied']]
    need(candidates, 'actual applied planar source mutation target absent')
    side,index,record = candidates[0]
    def altered_record(edit):
        changed = deepcopy(serialized); edit(changed['sources'][side]['models'][index]); return changed
    changes = [('omitted-original-planar-model',dict(serialized,sources=[dict(s,models=s['models'][:-1]) if i == side else s for i,s in enumerate(serialized['sources'])])),
               ('omitted-original-UV-boundary-carrier',altered_record(lambda r:r['uv_boundary_pieces'].pop())),
               ('changed-exact-plane-left-inverse',altered_record(lambda r:r['left_inverse_exact'][0].__setitem__(0,str(Q(r['left_inverse_exact'][0][0])+1)))),
               ('changed-full-original-D-endpoint',altered_record(lambda r:r['full_D_exact'][0].__setitem__(1,str(Q(r['full_D_exact'][0][1])+1)))),
               ('omitted-complete-endpoint-closure-box',altered_record(lambda r:r['uv_boundary_pieces'].pop(next(i for i,p in enumerate(r['uv_boundary_pieces']) if p['kind'] == 'closure')))),
               ('wrong-complete-wire-successor',altered_record(lambda r:r['wire_certificates'][0]['successor_indices'].__setitem__(0,-1)))]
    rows = [rejected(name,lambda changed=changed:verify_models(changed,boundary,frame,projection,limits)) for name,changed in changes]
    for row in rows:
        row.update(actual_material_side=side,actual_model_index=record['model_index'],actual_original_face_index=record['original_face_index'],
                   actual_source_face_canonical_sha256=record['source_face_canonical_sha256'])
    circle = next(((s,i,j,p) for s,i,r in candidates for j,p in enumerate(r['uv_boundary_pieces']) if p['kind'] == 'circle_patch'),None)
    error = next(((s,i,j,p) for s,i,r in candidates for j,p in enumerate(r['uv_boundary_pieces']) if p['kind'] == 'circle_patch' and
                  Q(p['trigonometric_certificate']['degree_47_Lagrange_error_exact']) > 0),None)
    for name,target,edit in [('shortened-complete-original-circle-domain',circle,
                              lambda p:p['parameter_interval_exact'].__setitem__(1,p['parameter_interval_exact'][0])),
                             ('deleted-positive-certified-Taylor-error',error,
                              lambda p:p['trigonometric_certificate'].__setitem__('degree_47_Lagrange_error_exact','0'))]:
        if target is None:
            rows.append({'name':name,'status':'not_applicable','actual_rejected':False,'reason':'No matching original applied Circle/Taylor carrier in this frame.'})
        else:
            s,i,j,piece = target; changed = deepcopy(serialized); edit(changed['sources'][s]['models'][i]['uv_boundary_pieces'][j])
            rejected_row = rejected(name,lambda changed=changed:verify_models(changed,boundary,frame,projection,limits))
            rejected_row.update(actual_material_side=s,actual_model_index=serialized['sources'][s]['models'][i]['model_index'],
                                actual_UV_piece_index=j,actual_original_parameter_interval_exact=piece['parameter_interval_exact'],
                                actual_original_Taylor_error_exact=piece['trigonometric_certificate']['degree_47_Lagrange_error_exact'])
            if name == 'deleted-positive-certified-Taylor-error':
                rejected_row['deleted_remainder_was_strictly_positive'] = True
            rows.append(rejected_row)
    return rows


def analytic_controls(limits):
    """Complete synthetic boxes and an explicitly defined L-prism; never original/native qualification."""
    unit = ((Q(0),Q(1)),)*3
    faces = []
    for axis in range(3):
        for end in (0,1):
            box = list(unit); box[axis] = (Q(end),Q(end))
            faces.append({'box':tuple(box),'additional_slabs':[],'slab_source':None})
    sources = [{'whole':unit,'pieces':faces},{'whole':unit,'pieces':faces}]

    def exterior(cell):
        return {'excluded_open_interior':True,'material_side':0,'axis':0,'end':1,
                'open_channel_exact':encbox(spatial_channel(cell,unit,0,1)),
                'complete_piece_separation_codes':'000000','boundary_piece_count':6,
                'closed_cell_boundary_retained_as_zero_volume_carrier':True,'whole_closed_cell_disjoint_claimed':False,
                'nonaxis_separation_code_count':0,'planar_exterior_separation_code_count':0,'planar_exterior_certificates':[]}

    def unresolved(cell):
        result = {'excluded_open_interior':False,'actual_material_interference_claimed':False,
                  'all_registered_channels_unresolved':[{'material_side':side,'axis':axis,'end':end,'unresolved_piece_index':2*axis+end}
                                                       for side in range(2) for axis in range(3) for end in (0,1)]}
        check_unresolved(result,cell,sources,{})
        return result

    def singleton(node,cell):
        kept = node['kind'] == 'retained'; volume = measure(cell)
        return {'nodes':[node],'retained_sum_exact':str(volume if kept else 0),'excluded_open_sum_exact':str(0 if kept else volume),
                'total_leaf_count':1,'excluded_leaf_count':int(not kept),'retained_leaf_count':int(kept),
                'retained_reason_counts':{node['reason']:1} if kept else {},'maximum_depth_reached':0,
                'actual_planar_exterior_separator_count_in_excluded_leaves':0,
                'all_closed_cut_planes_and_root_boundaries_retained':True}

    outside = ((Q(2),Q(3)),(Q(0),Q(1)),(Q(0),Q(1)))
    outside_tree = singleton({'id':0,'kind':'excluded','positive_directed_volume_exact':'1','certificate':exterior(outside)},outside)
    outside_stats = verify_tree(outside_tree,outside,sources,{},limits)
    need(outside_stats['retained'] == 0 and outside_stats['excluded'] == 1 and outside_stats['pieces'] == 6, 'new V7 tree complete-box positive failed')
    delta = Q(limits['tiny_retained_volume_exact'])/2
    root = ((Q(1)-delta,Q(2)),(Q(0),Q(1)),(Q(0),Q(1)))
    observation = unresolved(root); axis,cut,witness = registered_cut(root,sources,observation)
    need((axis,cut) == (0,1), 'synthetic exact split must use complete solid boundary')
    left,right = list(root),list(root); left[0] = (Q(1)-delta,Q(1)); right[0] = (Q(1),Q(2))
    lv,rv = measure(left),measure(right)
    split_tree = {'nodes':[
        {'id':0,'kind':'split','axis':axis,'cut_exact':str(cut),'cut_source':witness,'children':[1,2],
         'parent_positive_directed_volume_exact':str(measure(root)),'children_positive_directed_volumes_exact':enc((lv,rv)),
         'closed_cut_plane_retained_as_zero_volume_carrier':True,'actual_channel_observation':observation},
        {'id':1,'kind':'retained','reason':'tiny_exact_volume_retained','positive_directed_volume_exact':str(lv),'actual_material_interference_claimed':False},
        {'id':2,'kind':'excluded','positive_directed_volume_exact':str(rv),'certificate':exterior(right)}],
        'retained_sum_exact':str(lv),'excluded_open_sum_exact':str(rv),'total_leaf_count':2,'excluded_leaf_count':1,'retained_leaf_count':1,
        'retained_reason_counts':{'tiny_exact_volume_retained':1},'maximum_depth_reached':1,
        'actual_planar_exterior_separator_count_in_excluded_leaves':0,'all_closed_cut_planes_and_root_boundaries_retained':True}
    split_stats = verify_tree(split_tree,root,sources,{},limits)
    need(split_stats['retained'] == delta > 0 and split_stats['excluded'] == 1 and split_stats['splits'] == 1,
         'new V7 exact partition/tiny positive retained regression failed')
    inside = ((Q(1,4),Q(1,4)+delta),(Q(1,4),Q(3,4)),(Q(1,4),Q(3,4)))
    retained_tree = singleton({'id':0,'kind':'retained','reason':'tiny_exact_volume_retained','positive_directed_volume_exact':str(measure(inside)),
                               'actual_material_interference_claimed':False,'actual_channel_observation':unresolved(inside)},inside)
    retained_stats = verify_tree(retained_tree,inside,sources,{},limits)
    need(retained_stats['retained'] == measure(inside) > 0 and retained_stats['excluded_count'] == retained_stats['splits'] == 0 and
         retained_stats['sample_exclusion'] is None and retained_stats['sample_split'] is None,
         'new V7 complete all-retained/no-excluded branch failed')
    channel_bad = channel_controls(exterior(outside),outside,sources,{})
    split_bad = split_controls(split_tree,root,sources,{},limits,split_stats)
    leaf_bad = leaf_controls(split_tree,root,sources,{},limits,split_stats)

    # Exact L-region [0,2]x[0,1] union [0,1]x[0,2], extruded through z=[0,1].
    points = [(0,0),(2,0),(2,1),(1,1),(1,2),(0,2)]
    occurrences = []
    for index,start in enumerate(points):
        finish = points[(index+1)%len(points)]
        occurrences.append({'location':{'matrix_3x4_exact':IDENTITY},'edge_index':index,
                            'orientation':'TopAbs_Orientation.TopAbs_FORWARD',
                            'pcurve':{'type':'GeomAbs_CurveType.GeomAbs_Line','first_parameter':{'exact':'0'},'last_parameter':{'exact':'1'},
                                      'origin_exact':list(map(str,start)), 'direction_exact':[str(finish[k]-start[k]) for k in range(2)]}})
    source_face_record = {'index':0,'location':{'matrix_3x4_exact':IDENTITY},'orientation':'TopAbs_Orientation.TopAbs_FORWARD',
                         'local_surface':{'type':'GeomAbs_SurfaceType.GeomAbs_Plane','origin_exact':['0','0','0'],
                                          'X_exact':['1','0','0'],'Y_exact':['0','1','0']},
                         'wires':[{'index':0,'location':{'matrix_3x4_exact':IDENTITY},'orientation':'TopAbs_Orientation.TopAbs_FORWARD',
                                   'is_outer':True,'edge_occurrences':occurrences}]}
    candidate = {'face_index':0,'complete_original_face':source_face_record,'complete_original_face_canonical_sha256':canonical(source_face_record)}
    stationary = ((Q(0),Q(2)),(Q(0),Q(2)),(Q(0),Q(0)))
    serialized = dict(source_face(candidate,stationary,((Q(0),Q(0)),)*3,limits),model_index=0)
    planar_model = runtime_planar(serialized)
    need(len(planar_model['pieces']) == 12 and serialized['wire_certificates'][0]['successor_indices'] == [1,2,3,4,5,0],
         'complete exact L-region original boundary and closures required')
    whole = ((Q(0),Q(2)),(Q(0),Q(2)),(Q(0),Q(1)))
    l_faces = [{'box':stationary,'additional_slabs':[],'slab_source':None},
               {'box':((Q(0),Q(2)),(Q(0),Q(2)),(Q(1),Q(1))),'additional_slabs':[],'slab_source':None}]
    for index,start in enumerate(points):
        finish = points[(index+1)%len(points)]
        side_box = tuple((Q(min(start[k],finish[k])),Q(max(start[k],finish[k]))) for k in range(2))+((Q(0),Q(1)),)
        l_faces.append({'box':side_box,'additional_slabs':[],'slab_source':None})
    l_sources = [{'whole':whole,'pieces':l_faces},{'whole':whole,'pieces':l_faces}]
    planar = {(0,0):planar_model}
    notch = ((Q(5,4),Q(7,4)),(Q(5,4),Q(7,4)),(Q(1,4),Q(3,4)))
    channel = spatial_channel(notch,whole,2,0)
    candidate_box,target = projected_candidate(planar_model,channel); path = uv_exterior_channel(target,planar_model['known'],0,1)
    codes = ''.join(next(str(number) for number in range(6 if piece['slabs'] else 4) if strict_separator(piece,path,str(number))) for piece in planar_model['pieces'])
    uv_proof = {'kind':'complete_closed_UV_exterior_channel','model_index':0,'stationary_candidate_box_exact':encbox(candidate_box),
                'closed_UV_target_box_exact':encbox(target),'axis':0,'end':1,'closed_UV_channel_exact':encbox(path),
                'complete_UV_piece_separation_codes':codes,'UV_boundary_piece_count':12,'strict_closed_separation':True,
                'sampled_region_classification_used':False,'bounded_region_complete_boundary_cover_is_model_premise':True}
    verify_uv_exclusion(uv_proof,planar_model,channel)
    spatial_codes = 'u'+''.join(next(code for code in '012345' if spatial_separator(piece,channel,code)) for piece in l_faces[1:])
    l_proof = {'excluded_open_interior':True,'material_side':0,'axis':2,'end':0,'open_channel_exact':encbox(channel),
               'complete_piece_separation_codes':spatial_codes,'boundary_piece_count':8,'planar_exterior_certificates':[{'piece_index':0,'certificate':uv_proof}],
               'closed_cell_boundary_retained_as_zero_volume_carrier':True,'whole_closed_cell_disjoint_claimed':False,
               'nonaxis_separation_code_count':0,'planar_exterior_separation_code_count':1}
    l_tree = singleton({'id':0,'kind':'excluded','positive_directed_volume_exact':str(measure(notch)),'certificate':l_proof},notch)
    l_tree['actual_planar_exterior_separator_count_in_excluded_leaves'] = 1
    l_stats = verify_tree(l_tree,notch,l_sources,planar,limits)
    need(l_stats['excluded'] == Q(1,8) and l_stats['retained'] == 0 and l_stats['planar'] == 1 and l_stats['UV_pieces'] == 12,
         'new V7 u certificate must exclude only the explicit L-prism notch')
    uv_bad = uv_channel_controls(l_proof,notch,l_sources,planar)
    touch = list(channel); touch[0] = (Q(1),touch[0][1]); touch = tuple(touch)
    touch_box,touch_target = projected_candidate(planar_model,touch)
    touch_path = uv_exterior_channel(touch_target,planar_model['known'],0,1)
    touch_proof = dict(uv_proof,stationary_candidate_box_exact=encbox(touch_box),closed_UV_target_box_exact=encbox(touch_target),
                       closed_UV_channel_exact=encbox(touch_path))
    need(touch_path[0][0] == planar_model['pieces'][3]['box'][0][1] == 1 and
         not strict_separator(planar_model['pieces'][3],touch_path,'1'), 'closed UV touching must never become strict separation')
    uv_bad.append(rejected('closed-UV-touching-is-not-strict-separation',lambda:verify_uv_exclusion(touch_proof,planar_model,touch)))
    l_inside = ((Q(1,4),Q(1,4)+delta),(Q(1,4),Q(3,4)),(Q(1,4),Q(3,4)))
    l_unresolved_rows = []; failed_uv = failed_uv_channel = None
    for side in range(2):
        for path_axis in range(3):
            for path_end in (0,1):
                spatial = spatial_channel(l_inside,whole,path_axis,path_end)
                index = next(index for index,piece in enumerate(l_faces) if not any(spatial_separator(piece,spatial,code) for code in '012345'))
                failed_row = {'material_side':side,'axis':path_axis,'end':path_end,'unresolved_piece_index':index}
                if (side,index) in planar:
                    b,q = projected_candidate(planar_model,spatial); uv_rows = []
                    for uv_axis in (0,1):
                        for uv_end in (0,1):
                            uv_path = uv_exterior_channel(q,planar_model['known'],uv_axis,uv_end)
                            blocked = next(j for j,piece in enumerate(planar_model['pieces']) if not any(
                                strict_separator(piece,uv_path,str(number)) for number in range(6 if piece['slabs'] else 4)))
                            uv_rows.append({'axis':uv_axis,'end':uv_end,'closed_UV_channel_exact':encbox(uv_path),'unresolved_UV_piece_index':blocked})
                    attempt = {'excluded':False,'model_index':0,'stationary_candidate_box_exact':encbox(b),'closed_UV_target_box_exact':encbox(q),
                               'all_closed_UV_channels_unresolved':uv_rows,'actual_material_membership_claimed':False}
                    verify_uv_unresolved(attempt,planar_model,spatial); failed_row['planar_exterior_attempt'] = attempt
                    failed_uv,failed_uv_channel = attempt,spatial
                l_unresolved_rows.append(failed_row)
    need(failed_uv is not None, 'analytic interior needs actual complete four-path UV failure')
    l_unresolved = {'excluded_open_interior':False,'actual_material_interference_claimed':False,
                    'all_registered_channels_unresolved':l_unresolved_rows}
    l_kept_tree = singleton({'id':0,'kind':'retained','reason':'tiny_exact_volume_retained','positive_directed_volume_exact':str(measure(l_inside)),
                             'actual_material_interference_claimed':False,'actual_channel_observation':l_unresolved},l_inside)
    l_kept_stats = verify_tree(l_kept_tree,l_inside,l_sources,planar,limits)
    need(l_kept_stats['retained'] == measure(l_inside) > 0 and l_kept_stats['excluded_count'] == l_kept_stats['splits'] == 0 and
         l_kept_stats['unresolved_spatial'] == 12 and l_kept_stats['unresolved_UV'] == 4,
         'new planar-aware all-retained tree must preserve complete UV and spatial failure witnesses')
    changed = deepcopy(failed_uv); changed['all_closed_UV_channels_unresolved'].pop()
    uv_bad.append(rejected('omitted-failed-closed-UV-path',lambda:verify_uv_unresolved(changed,planar_model,failed_uv_channel)))
    changed = deepcopy(failed_uv); first_path = intervals(changed['all_closed_UV_channels_unresolved'][0]['closed_UV_channel_exact'],2)
    available_index = next(index for index,piece in enumerate(planar_model['pieces']) if any(
        strict_separator(piece,first_path,str(number)) for number in range(6 if piece['slabs'] else 4)))
    changed['all_closed_UV_channels_unresolved'][0]['unresolved_UV_piece_index'] = available_index
    uv_bad.append(rejected('false-unresolved-closed-UV-blocker',lambda:verify_uv_unresolved(changed,planar_model,failed_uv_channel)))
    need(len(channel_bad) == 4 and len(split_bad) == 5 and len(leaf_bad) == 2 and len(uv_bad) == 10 and
         all(row['actual_rejected'] is True for row in channel_bad+split_bad+leaf_bad+uv_bad), 'mandatory new V7 analytic controls incomplete')
    return {'schema':'razr-r5e-mandatory-planar-exterior-checker-controls-v7','execution_kind':'synthetic_analytic_control',
            'qualifies_original_or_native_case':False,'real_case_result_changed':False,'original_limits_and_threshold_unchanged':True,
            'complete_box_exterior_positive':{'verified':True,'root_box_exact':encbox(outside),'excluded_open_volume_exact':'1'},
            'exact_partition_and_tiny_retention_positive':{'verified':True,'root_box_exact':encbox(root),'cut_exact':str(cut),
                'children_positive_directed_volumes_exact':enc((lv,rv)),'positive_tiny_leaf_retained_in_full':True},
            'all_retained_no_excluded_positive':{'verified':True,'retained_positive_volume_exact':str(measure(inside)),
                'all_twelve_unresolved_channels_checked':True,'excluded_leaves':0,'splits':0,
                'channel_mutations':applicability([],0,4,'Synthetic all-retained tree has no excluded leaf.'),
                'split_mutations':applicability([],0,5,'Synthetic all-retained tree has no split.'),
                'is_actual_V6_or_V7_case_branch_coverage':False},
            'complete_L_prism_UV_notch_positive':{'verified':True,'explicit_L_boundary_vertices':points,'source_UV_piece_count':12,
                'complete_spatial_face_count':8,'root_box_exact':encbox(notch),'excluded_open_volume_exact':'1/8',
                'actual_saved_u_separations':1,'strict_closed_touch_negative_executed':True,'native_membership_claimed':False},
            'complete_L_prism_UV_interior_all_retained_positive':{'verified':True,'retained_positive_volume_exact':str(measure(l_inside)),
                'all_twelve_unresolved_spatial_channels_checked':True,'all_four_failed_closed_UV_paths_checked':True,
                'excluded_leaves':0,'splits':0,'is_actual_V6_or_V7_case_branch_coverage':False},
            'channel_negative_controls':channel_bad,'split_negative_controls':split_bad,'leaf_negative_controls':leaf_bad,
            'UV_negative_controls':uv_bad,'mandatory_controls_completed':True}


def validate_static_capacity(contract, records):
    capacity = json.loads(bound(contract['static_source_capacity']).read_text())
    need(capacity['schema'] == 'razr-r5e-v7-static-source-capacity' and
         content_equal(capacity['original_source_projection'],contract['primitive_source_bundle']) and
         capacity['new_primitive_or_planar_enclosures_computed'] is False and capacity['new_channel_search_executions'] == 0 and
         capacity['new_mathematical_qualification'] is False and capacity['original_float64_TOL_unchanged'] is True and
         capacity['larger_run_requires_actual_selected_leaf_and_independent_pass'] is True and
         capacity['full_run_requires_actual_all16_preflight'] is True, 'registered source-only capacity is not a mathematical experiment')
    count = Counter(); maximum = 0
    for record in records.values():
        for candidate in record['candidate_faces']:
            if candidate['source_primitive'] != 'GeomAbs_Plane': continue
            count['plane_occurrences'] += 1; pieces = 0
            for wire in candidate['complete_original_face']['wires']:
                count['wire_count'] += 1
                for occurrence in wire['edge_occurrences']:
                    count['source_edge_occurrences'] += 1; kind = occurrence['pcurve']['type']
                    need(kind in ('GeomAbs_CurveType.GeomAbs_Line','GeomAbs_CurveType.GeomAbs_Circle'), 'registered full source class changed')
                    if kind.endswith('Line'): count['Line_occurrences'] += 1; pieces += 2
                    else: count['Circle_occurrences'] += 1; pieces += 65
            count['maximum_total_UV_pieces'] += pieces; maximum = max(maximum,pieces)
    expected = {'original_projection_materials':32,'plane_occurrences':48,'wire_count':48,'Line_occurrences':472,
                'Circle_occurrences':48,'source_edge_occurrences':520,'fixed_circle_angular_patches':64,
                'maximum_total_UV_pieces':4064,'maximum_UV_pieces_per_face':225,'actual_V6_retained_roots':4943,
                'maximum_new_splits':4096,'maximum_depth':24,'maximum_new_forest_nodes':13135,'maximum_new_forest_leaves':9039,
                'maximum_combined_boundary_piece_tests':12000000,'maximum_combined_support_inequality_tests':12000000}
    need(all(type(capacity[key]) is int and capacity[key] == value for key,value in expected.items()) and
         all(count[key] == expected[key] for key in count) and maximum == 225 and len(records) == 32,
         'complete source-only capacity/census differs from immutable original records')
    return dict(count,maximum_UV_pieces_per_face=maximum,all_source_occurrences_included=True)


def validate_producer_prerequisites(producer_contract, inputs, v6, limits):
    phase = producer_contract['phase']; rows = producer_contract['completed_prerequisites']
    required = [] if phase == 'single_planar_exterior_leaf' else ['single_planar_exterior_leaf','preflight_planar_exterior']
    need([row['phase'] for row in rows] == required, 'actual first witness then all16 preflight prerequisite sequence differs')
    watched = []; reports = {}
    for row in rows:
        report = json.loads(bound(row['report']).read_text()); receipt = json.loads(bound(row['supervisor']).read_text())
        watched.extend([row['report'],row['supervisor']]); reports[row['phase']] = report
        need(report['execution_completed'] is True and report['phase'] == row['phase'] and report['registered_input_identities'] == inputs and
             report['capacity'] == limits and report['source_sha256'] == inputs['planar_producer_source']['sha256'],
             'actual prerequisite must use the exact same source, immutable inputs and capacity')
        require_scope(report); v6.owned_completion(receipt,report,inputs['planar_producer_source']['sha256'],Path(row['report']['path']).parent)
        if row['phase'] == 'single_planar_exterior_leaf':
            need([(frame['case_id'],frame['frame']) for frame in report['frames']] == [('case-028',1)] and
                 report['frames'][0]['root_base_V6_leaf_locators'] == [[76,47]] and report['planar_exterior_model_conditional_clearance_passes'] == 1 and
                 Q(report['frames'][0]['planar_exterior_model_conditional_upper_exact_mm3']) <= TOL and
                 Q(report['frames'][0]['newly_excluded_open_leaf_sum_exact']) > 0 and
                 report['frames'][0]['actual_planar_exterior_separator_count_in_excluded_leaves'] > 0,
                 'actual selected original leaf lacks the registered TOL/positive-exclusion/saved-u prerequisite')
        else:
            need(len(report['frames']) == 16 and report['total_actual_V6_retained_roots'] == 4943 and
                 report['complete_phase_maximum_tree_nodes'] == 13135 and report['complete_phase_maximum_leaves'] == 9039 and
                 report['all_frame_capacity_observations_completed'] is True and report['actual_total_UV_boundary_pieces'] <= 4064 and
                 report['maximum_UV_pieces_per_face'] <= 225 and report['maximum_complete_spatial_pieces_per_material'] <= 4096 and
                 all(frame['new_clearance_result_claimed'] is False for frame in report['frames']) and
                 all(value == 0 for value in report['counters'].values()), 'actual full16 source preflight does not meet frozen capacity')
    if rows:
        binding = producer_contract['independent_single_verification']
        checked = json.loads(bound(binding['report']).read_text()); receipt = json.loads(bound(binding['supervisor']).read_text())
        watched.extend([binding['report'],binding['supervisor']])
        need(checked['execution_completed'] is True and checked['expected_phase'] == 'single_planar_exterior_leaf' and
             checked['expected_case_frames'] == [['case-028',1]] and checked['registered_input_identities'] == inputs and
             checked['planar_exterior_model_conditional_clearance_passes'] == 1 and
             content_equal(checked['verified_producer_report'],rows[0]['report']) and
             content_equal(producer_contract['actual_capacity_basis'],rows[1]['report']),
             'actual independent first witness or exact all16 preflight binding differs')
        require_scope(checked); v6.owned_completion(receipt,checked,inputs['single_verifier_source']['sha256'],Path(binding['report']['path']).parent)
    return watched,reports.get('preflight_planar_exterior')


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--contract',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(); contract = json.loads(args.contract.read_text())
    need(identity(__file__)['sha256'] == contract['verifier_sha256'] == contract['producer_sha256'] == contract['single_verifier_source']['sha256'],
         'registered independent V7 verifier source differs')
    args.output.mkdir(parents=True,exist_ok=False); started = time.monotonic()
    report = {'schema':'razr-r5e-independent-planar-exterior-verification-v7','execution_completed':False,
              'started_utc':datetime.now(timezone.utc).isoformat(),'contract_sha256':identity(args.contract)['sha256'],
              'source_sha256':identity(__file__)['sha256'],'capacity':contract['capacity'],'original_TOL_exact':str(TOL),
              'no_positive_thin_leaf_discarded':True,
              'verified_producer_report':contract['producer_report'],'registered_input_identities':{name:contract[name] for name in SHARED_INPUT_FIELDS},
              'producer_code_imported':False,'planar_producer_or_helper_imported':False,'primitive_producer_or_helper_imported':False,
              'new_exact_planar_arithmetic_implemented_independently':True,'frozen_prior_independent_verifiers_reused_for_inherited_proofs':True,
              'conditional_planar_exterior_model_only':True,'conditional_primitive_support_model_only':True,'conditional_trim_model_only':True,
              'native_planar_region_semantics_verified':False,'native_primitive_semantics_verified':False,'native_trim_class_membership_verified':False,
              'inner_wire_hole_semantics_verified_for_native':False,'original_raw_gate_reclassified':False,'full_continuous_G2':False,
              'all_blockers_closed':False,'native_Common_called':False,'native_closure_membership_verified':False,'compiled_transform_error_verified':False,
              'V5_producer_rerun':False,'V6_producer_rerun':False,'original_V3_raw_passes_unchanged':4,'original_V4_failure_preserved':True,
              'actual_V5_conditional_passes_preserved':8,'actual_V6_conditional_passes_preserved':8,
              'expected_phase':contract['expected_phase'],'expected_case_frames':contract['expected_case_frames'],'frames':[],
              'phase_negative_controls':[],'root_coverage_negative_controls':[],'channel_negative_controls':[],
              'split_negative_controls':[],'leaf_negative_controls':[],'planar_source_negative_controls':[],
              'UV_channel_negative_controls':[],'real_case_control_applicability':{},'mandatory_analytic_controls':None}

    def save():
        report['seconds'] = time.monotonic()-started
        report['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

    try:
        require_scope(contract); limits = contract['capacity']; fixed_limits(limits)
        need(contract['all_original_D_components_retained'] is True and contract['original_float64_TOL_unchanged'] is True and
             contract['native_Common_as_acceptance_premise'] is False, 'original full-D/TOL and conditional-only acceptance contract differs')
        need(contract['phase'] == ('verify_single' if contract['expected_phase'] == 'single_planar_exterior_leaf' else 'verify_all'), 'independent/producer phase binding differs')
        inputs = report['registered_input_identities']
        for record in inputs.values(): bound(record)
        need(contract['base_V6_verifier_source']['sha256'] == V6_CHECKER and contract['base_V6_source_lock']['sha256'] == V6_LOCK,
             'frozen independent prior reader/lock required before import')
        v6 = prior_module(contract['base_V6_verifier_source'],'r5e_v7_frozen_independent_v6')
        archive6,prior6,verified6,pipeline6 = archived_v6(contract,v6)
        archive5,prior5,verified5,pipeline5 = v6.archived_v5(contract)
        need(content_equal(prior6['primitive_source_bundle'],contract['primitive_source_bundle']) and
             content_equal(prior6['actual_base_V5_report'],archive5['all-trim-model-frames/report.json']) and
             content_equal(prior6['actual_base_V5_independent_report'],archive5['verify-all/report.json']), 'complete V6-to-V5/source projection chain differs')
        report.update(immutable_V6_input_count=len(archive6),immutable_V5_input_count=len(archive5),
                      verified_actual_V6_report=archive6['all-primitive-support-frames/report.json'],
                      verified_actual_V6_independent_report=archive6['verify-all/report.json'],
                      verified_actual_V5_report=archive5['all-trim-model-frames/report.json'])
        producer_path = bound(contract['producer_report']); producer = json.loads(producer_path.read_text())
        need(producer['schema'] == 'razr-r5e-planar-exterior-refinement-v7' and producer['execution_completed'] is True and
             producer['all_source_contract_and_archived_inputs_unchanged'] is True and producer['registered_input_identities'] == inputs and
             producer['source_sha256'] == contract['planar_producer_source']['sha256'] and producer['capacity'] == limits and
             producer['V5_producer_rerun'] is False and producer['V6_producer_rerun'] is False and
             producer['actual_V5_conditional_passes_preserved'] == producer['actual_V6_conditional_passes_preserved'] == 8 and
             producer['original_V3_raw_passes_unchanged'] == 4 and producer['original_V4_failure_preserved'] is True and
             producer['all_blockers_closed'] is False and producer['native_Common_called'] is False and
             producer['compiled_transform_error_verified'] is False and producer['seconds'] <= 600 and producer['peak_RSS_bytes'] <= 805306368,
             'actual new producer completion/scope/immutable inputs/original resource gates differ')
        require_scope(producer)
        need(producer['actual_V6_report'] == archive6['all-primitive-support-frames/report.json'] and
             producer['actual_V6_independent_report'] == archive6['verify-all/report.json'] and producer['immutable_V6_input_count'] == 53,
             'actual producer reused another original V6 experiment')
        controller = json.loads(bound(contract['producer_owned_supervision']).read_text())
        v6.owned_completion(controller,producer,contract['planar_producer_source']['sha256'],producer_path.parent)
        producer_contract_path = producer_path.parent.parent/(producer_path.parent.name+'-contract.json')
        producer_contract_id = identity(producer_contract_path)
        need(producer_contract_id['sha256'] == producer['contract_sha256'], 'actual producer mathematical contract bytes differ')
        producer_contract = json.loads(producer_contract_path.read_text())
        need(producer_contract['phase'] == contract['expected_phase'] and producer_contract['capacity'] == limits and
             producer_contract['producer_sha256'] == inputs['planar_producer_source']['sha256'] and
             {name:producer_contract[name] for name in SHARED_INPUT_FIELDS} == inputs and
             all(producer_contract[name] == contract[name] for name in ('source_commit','base_V6_root','base_V5_root')),
             'actual producer contract did not use the same immutable sources/root bindings')
        require_scope(producer_contract)
        watched_prerequisites,preflight = validate_producer_prerequisites(producer_contract,inputs,v6,limits)
        baseline_path = bound(contract['r4_report']); baseline = json.loads(baseline_path.read_text())
        need(baseline['execution_completed'] is True and contract['source_commit'] == v6.ANCHOR and
             content_equal(prior5['source_report_identity'],contract['r4_report']) and content_equal(prior6['source_report_identity'],contract['r4_report']),
             'actual R4-to-V5-to-V6 source report chain differs')
        original_keys = [(row['case_id'],row['frame']) for row in baseline['frames']]
        need(len(original_keys) == len(set(original_keys)) == 16 and original_keys == [(r['case_id'],r['frame']) for r in prior5['frames']] ==
             [(r['case_id'],r['frame']) for r in prior6['frames']], 'original complete16 frame order differs')
        if preflight:
            need([(row['case_id'],row['frame']) for row in preflight['frames']] == original_keys,
                 'actual all16 source preflight omitted, duplicated or reordered an original frame')
        old_by = {(r['case_id'],r['frame']):r for r in baseline['frames']}
        v5_by = {(r['case_id'],r['frame']):r for r in prior5['frames']}; v6_by = {(r['case_id'],r['frame']):r for r in prior6['frames']}
        selection = json.loads(bound(contract['real_retained_leaf_selection']).read_text())
        need(selection['schema'] == 'razr-r5e-actual-v6-retained-leaf-selection-v7' and selection['no_new_geometry_execution'] is True and
             (selection['case_id'],selection['frame'],selection['V6_root_index'],selection['V6_node_index'],selection['actual_leaf_depth']) ==
             ('case-028',1,76,47,24) and selection['base_V5_leaf_locator'] == [28,17] and
             content_equal(selection['actual_V6_report'],archive6['all-primitive-support-frames/report.json']) and
             content_equal(selection['actual_V6_independent_report'],archive6['verify-all/report.json']) and
             content_equal(selection['actual_V6_pipeline'],archive6['pipeline.json']), 'exact actual largest depth24 witness registration differs')
        phase_coverage(producer,contract,baseline,selection)
        report['phase_negative_controls'] = phase_controls(producer,contract,baseline,selection)
        public = json.loads(bound(contract['public_input_bridge']).read_text())
        need(public['source_commit'] == v6.ANCHOR and len(public['files']) == 19 and
             all(row['decoded_json_equal'] is True and not row['changed_strings'] for row in public['files']), 'complete unchanged public R4 bridge required')
        public_entries = {row['path']:row for row in public['files']}; need(len(public_entries) == 19, 'duplicate public R4 path')
        r4_root = baseline_path.parent.parent; public_ids = {}
        for name,row in public_entries.items():
            path = (r4_root/name).resolve(); need(path.is_relative_to(r4_root), 'public R4 input escapes root')
            public_ids[name] = identity(path); need(content_equal(public_ids[name],row['public_identity']), 'public R4 actual bytes differ')
        need(content_equal(public_ids['support-v4/report.json'],contract['r4_report']) and
             content_equal(prior5['public_input_bridge'],contract['public_input_bridge']) and content_equal(prior6['public_input_bridge'],contract['public_input_bridge']),
             'inherited public R4 mapping differs')
        v5 = prior_module(contract['base_V5_verifier_source'],'r5e_v7_frozen_independent_v5')
        base = prior_module(contract['base_verifier_source'],'r5e_v7_frozen_independent_channels')
        trim_records,trim_bindings = v5.load_trim_source({'trim_source_bundle':contract['V5_trim_source_bundle']},baseline,contract['r4_report'])
        records,bindings,census = v6.primitive_sources(contract,baseline,prior5,trim_records)
        need(census == prior6['registered_source_primitive_census'], 'original primitive source census changed')
        projection = {'records':list(records.values()),'frame_bindings':list(bindings.values())}
        report['independent_static_source_capacity'] = validate_static_capacity(contract,records)
        prior6_limits = prior6['capacity']; v6.fixed_limits(prior6_limits); prior5_limits = prior5['capacity']
        need(prior5_limits['maximum_uv_patches_per_face'] == 1024 and prior5_limits['maximum_boundary_pieces_per_material'] == 4096 and
             prior5_limits['maximum_splits'] == 4096 and prior5_limits['maximum_depth'] == 24 and prior5_limits['maximum_boundary_box_tests'] == 12000000 and
             Q(prior5_limits['tiny_retained_volume_exact']) == TOL/100000, 'frozen prior V5 finite policy changed')
        report['mandatory_analytic_controls'] = analytic_controls(limits); save()
        totals = Counter(); reasons = Counter(); inherited_totals = Counter(); maximum_pieces = maximum_uv = 0
        all_new_ids = []; preflight_by = {(r['case_id'],r['frame']):r for r in preflight['frames']} if preflight else {}
        for row in producer['frames']:
            require_scope(row); key = row['case_id'],row['frame']
            old,old5,old6,binding = old_by[key],v5_by[key],v6_by[key],bindings[key]
            raw_name = 'support-v4/'+old['proof']['path']; raw_entry = public_entries[raw_name]
            need(row['original_raw_proof_identity'] == old['proof'] == old5['original_raw_proof_identity'] == old6['original_raw_proof_identity'] ==
                 binding['original_R4_raw_proof_identity'] and raw_entry['raw_identity'] == {name:old['proof'][name] for name in ('bytes','sha256')} and
                 content_equal(old5['source_proof'],raw_entry['public_identity']), 'complete actual original R4 proof identity chain differs')
            proof = gzip_json(public_ids[raw_name]['path'])
            need(canonical(proof) == raw_entry['public_canonical_json_sha256'] and
                 row['original_remaining_displacement_box_exact'] == old5['original_remaining_displacement_box_exact'] ==
                 old6['original_remaining_displacement_box_exact'] == binding['original_full_D'] == proof['full_remaining_displacement_box_exact'] ==
                 old['full_remaining_displacement_box_exact'], 'original full displacement or decoded R4 source changed')
            name5 = 'all-trim-model-frames/'+old5['certificate']['path']; id5 = archive5[name5]
            name6 = 'all-primitive-support-frames/'+old6['certificate']['path']; id6 = archive6[name6]
            need(content_equal(old5['certificate'],id5) and content_equal(old6['base_V5_certificate'],id5) and
                 binding['actual_V5_certificate'] == dict(id5,path=name5) and content_equal(old6['certificate'],id6) and
                 row['base_V6_certificate'] == id6, 'immutable actual V5/V6 certificate bindings differ')
            certificate5 = gzip_json(id5['path']); certificate6 = gzip_json(id6['path'])
            leaves5,kept5,removed5,audit5 = v6.recheck_prior_frame(old5,old,proof,certificate5,v5,base,trim_records,trim_bindings,
                                                                prior5_limits,records,binding)
            leaves6,kept6,removed6,sources,audit6 = recheck_v6_frame(old6,certificate6,old5,certificate5,leaves5,kept5,removed5,
                                                                old,v6,records,bindings,prior6_limits)
            for name in ('splits','nodes','leaves','excluded_count'): inherited_totals[name] += audit6[name]
            inherited_totals['retained_roots'] += len(leaves6)
            if key == ('case-028',1):
                target = next((leaf for leaf in leaves6 if leaf['locator'] == [76,47]),None)
                need(target is not None and encbox(target['box']) == selection['actual_leaf_box_exact'] and target['node'] == selection['actual_V6_leaf_record'] and
                     target['depth'] == selection['actual_leaf_depth'] == 24 and target['volume'] == Q(selection['positive_directed_volume_exact']) and
                     float(target['volume']) == selection['positive_directed_volume_mm3'] and target['base_V5_leaf_locator'] == selection['base_V5_leaf_locator'] and
                     canonical(certificate6['roots'][76]) == selection['actual_V6_root_record_canonical_sha256'] and
                     content_equal(selection['actual_V6_certificate'],id6) and selection['whole_pair'] == old6['pair'] and
                     selection['original_full_D'] == old6['original_remaining_displacement_box_exact'] and
                     target['volume'] == max(leaf['volume'] for leaf in leaves6 if leaf['depth'] == 24),
                     'selected exact largest actual depth24 original leaf changed')
            leaves = [target] if contract['expected_phase'] == 'single_planar_exterior_leaf' else leaves6
            need(row['pair'] == old6['pair'] and row['base_V6_frame_conditional_upper_exact_mm3'] == old6['primitive_support_model_conditional_upper_exact_mm3'] and
                 Q(row['base_V6_retained_leaf_sum_exact']) == kept6 and Q(row['base_V6_excluded_open_leaf_sum_exact']) == removed6 and
                 row['base_V6_boundary_canonical_sha256'] == canonical(certificate6['boundary_refinement']), 'inherited original V6 frame/material measure differs')
            new_path = relative_bound(row['certificate'],producer_path.parent); all_new_ids.append(identity(new_path)); certificate = gzip_json(new_path)
            need(certificate['schema'] == 'razr-r5e-planar-exterior-tree-v7' and certificate['frame'] == {name:value for name,value in row.items() if name != 'certificate'} and
                 certificate['V6_producer_rerun'] is False and Q(certificate['actual_V6_excluded_open_sum_preserved_exact']) == removed6 and
                 certificate['base_V6_boundary_canonical_sha256'] == row['base_V6_boundary_canonical_sha256'], 'complete new certificate header or old exclusions differ')
            planar,audit_models = verify_models(certificate['planar_models'],certificate6['boundary_refinement'],old6,projection,limits)
            need(row['source_piece_counts'] == [len(source['pieces']) for source in sources] and
                 row['applied_planar_model_count'] == audit_models.get('applied',0) and row['rejected_planar_model_count'] == audit_models.get('rejected',0) and
                 row['UV_boundary_piece_count'] == audit_models.get('UV_pieces',0), 'complete unchanged spatial/new planar census differs')
            maximum_pieces = max(maximum_pieces,*(len(source['pieces']) for source in sources))
            maximum_uv = max([maximum_uv]+[len(model['pieces']) for model in planar.values()])
            if audit_models.get('applied',0) and not report['planar_source_negative_controls']:
                report['planar_source_negative_controls'] = model_controls(certificate['planar_models'],certificate6['boundary_refinement'],old6,projection,limits)
            if preflight:
                before = preflight_by[key]
                need(before['source_models_canonical_sha256'] == canonical(certificate['planar_models']) and
                     all(before[name] == row[name] for name in ('pair','original_raw_proof_identity','original_remaining_displacement_box_exact','base_V6_certificate',
                         'base_V6_boundary_canonical_sha256','base_V6_frame_conditional_upper_exact_mm3','base_V6_retained_leaf_sum_exact',
                         'base_V6_excluded_open_leaf_sum_exact','root_base_V6_leaf_locators','root_count','source_piece_counts',
                         'applied_planar_model_count','rejected_planar_model_count','UV_boundary_piece_count')),
                     'actual all16 source preflight must match the exact final sources and full retained roots')
            root_coverage(row,certificate,leaves)
            if not report['root_coverage_negative_controls'] and leaves:
                report['root_coverage_negative_controls'] = root_controls(row,certificate,leaves)
            kept = removed = Q(0); counts = Counter(); maximum_depth = 0
            for root in certificate['roots']:
                cell,tree = intervals(root['root_box_exact'],3),root['tree']; stats = verify_tree(tree,cell,sources,planar,limits)
                kept += stats['retained']; removed += stats['excluded']; maximum_depth = max(maximum_depth,stats['depth']); reasons.update(stats['reasons'])
                for name in ('splits','nodes','leaves','excluded_count','pieces','nonaxis','planar','UV_pieces','UV_nonaxis','unresolved_spatial','unresolved_UV'):
                    counts[name] += stats[name]
                if stats['sample_exclusion'] and not report['channel_negative_controls']:
                    good,target_cell = stats['sample_exclusion']; report['channel_negative_controls'] = channel_controls(good,target_cell,sources,planar)
                if stats['sample_planar'] and not report['UV_channel_negative_controls']:
                    good,target_cell = stats['sample_planar']; report['UV_channel_negative_controls'] = uv_channel_controls(good,target_cell,sources,planar)
                if stats['sample_split'] and not report['split_negative_controls']:
                    report['split_negative_controls'] = split_controls(tree,cell,sources,planar,limits,stats)
                if not report['leaf_negative_controls']:
                    report['leaf_negative_controls'] = leaf_controls(tree,cell,sources,planar,limits,stats)
            root_sum = sum((leaf['volume'] for leaf in leaves),Q(0))
            need(kept+removed == root_sum == Q(row['new_root_sum_exact']) and kept == Q(row['retained_leaf_sum_exact']) and
                 removed == Q(row['newly_excluded_open_leaf_sum_exact']), 'complete new directed retained/excluded volume differs')
            upper = kept
            if contract['expected_phase'] == 'all_planar_exterior_frames':
                need(kept+removed == kept6, 'new exclusions must come from the full old retained sum, not a selected minimum bound')
                upper = min(kept,Q(old6['primitive_support_model_conditional_upper_exact_mm3']))
            need(Q(row['planar_exterior_model_conditional_upper_exact_mm3']) == upper and row['planar_exterior_model_conditional_upper_mm3'] == float(upper) and
                 row['planar_exterior_model_conditional_clearance_gate_passed'] == (upper <= TOL), 'new conditional upper or original float64 TOL differs')
            need(row['all_prior_and_new_closed_carriers_retained'] is True and row['exact_splits_this_frame'] == counts['splits'] and
                 row['total_leaf_count'] == counts['leaves'] and row['maximum_depth_reached'] == maximum_depth and
                 row['actual_planar_exterior_separator_count_in_excluded_leaves'] == counts['planar'], 'complete new tree/UV/carrier census differs')
            totals.update(counts); totals['roots'] += len(leaves)
            for name in ('applied','rejected','UV_pieces'): totals['model_'+name] += audit_models.get(name,0)
            report['frames'].append({'case_id':key[0],'frame':key[1],'independently_rechecked_actual_V5':audit5,
                'independently_rechecked_actual_V6':audit6,'independently_reconstructed_planar_source':audit_models,
                'new_retained_roots_verified':len(leaves),'new_tree_nodes_verified':counts['nodes'],'new_splits_verified':counts['splits'],
                'new_positive_leaves_verified':counts['leaves'],'new_excluded_leaves_verified':counts['excluded_count'],
                'complete_saved_spatial_separations_verified':counts['pieces'],'saved_spatial_nonaxis_separations_verified':counts['nonaxis'],
                'saved_planar_u_separations_verified':counts['planar'],'complete_saved_UV_piece_separations_verified':counts['UV_pieces'],
                'saved_UV_nonaxis_separations_verified':counts['UV_nonaxis'],'actual_failed_spatial_channel_records_verified':counts['unresolved_spatial'],
                'actual_failed_UV_channel_records_verified':counts['unresolved_UV'],'new_retained_sum_exact':str(kept),'newly_excluded_open_sum_exact':str(removed),
                'planar_exterior_model_conditional_upper_exact_mm3':str(upper),'planar_exterior_model_conditional_clearance_gate_passed':upper <= TOL,
                'conditional_planar_exterior_model_only':True,'native_planar_region_semantics_verified':False,'original_raw_gate_reclassified':False})
            save(); need(report['seconds'] <= 600 and report['peak_RSS_bytes'] <= 805306368, 'new independent mathematical verification exceeded original process gate')
        counters = producer['counters']
        need(all(type(value) is int and value >= 0 for value in counters.values()) and counters['splits'] == totals['splits'] <= 4096 and
             counters['tree_nodes_visited'] == totals['nodes'] and counters['boundary_box_tests'] <= 12000000 and
             counters['support_inequality_tests'] <= 12000000 and
             counters['boundary_box_tests'] == counters['spatial_boundary_piece_tests']+counters['UV_boundary_piece_tests'] and
             counters['UV_support_inequality_tests'] <= counters['support_inequality_tests'], 'original shared spatial/UV/tree predicate caps differ')
        need(sum(row['exact_combined_piece_tests_this_frame'] for row in producer['frames']) == counters['boundary_box_tests'] and
             sum(row['exact_combined_support_tests_this_frame'] for row in producer['frames']) == counters['support_inequality_tests'] and
             counters['spatial_boundary_piece_tests'] >= totals['pieces'] and counters['UV_boundary_piece_tests'] >= totals['UV_pieces'] and
             counters['successful_nonaxis_separations'] >= totals['nonaxis'] and counters['successful_planar_exterior_separations'] >= totals['planar'] and
             counters['UV_channels_tested'] >= totals['planar']+totals['unresolved_UV'], 'per-frame/shared searches cannot undercount saved mathematical work')
        if reasons['global_predicate_budget_retained']:
            need(counters['boundary_box_tests'] == 12000000 or counters['support_inequality_tests'] == 12000000, 'retained predicate stop did not reach an original cap')
        if reasons['global_split_limit_retained']: need(totals['splits'] == 4096, 'global split stop did not reach the original cap')
        need(producer['total_actual_V6_retained_roots'] == totals['roots'] and producer['complete_phase_maximum_tree_nodes'] == totals['roots']+8192 and
             producer['complete_phase_maximum_leaves'] == totals['roots']+4096 and totals['nodes'] <= totals['roots']+8192 and
             totals['leaves'] <= totals['roots']+4096 and producer['maximum_complete_spatial_pieces_per_material'] == maximum_pieces <= 4096 and
             producer['maximum_UV_pieces_per_face'] == maximum_uv <= 225 and producer['actual_total_UV_boundary_pieces'] == totals['model_UV_pieces'] <= 4064 and
             producer['actual_applied_plane_models'] == totals['model_applied'] and producer['actual_rejected_plane_models'] == totals['model_rejected'] and
             totals['model_applied']+totals['model_rejected'] <= (6 if contract['expected_phase'] == 'single_planar_exterior_leaf' else 48) and
             producer['all_frame_capacity_observations_completed'] is True, 'complete finite actual source/forest capacity census differs')
        if contract['expected_phase'] == 'all_planar_exterior_frames':
            need(totals['roots'] == inherited_totals['retained_roots'] == 4943 and inherited_totals['splits'] == 4096 and
                 inherited_totals['nodes'] == 9729 and inherited_totals['leaves'] == 5633 and inherited_totals['excluded_count'] == 690,
                 'complete original actual V6 forest census changed')
        else: need(totals['roots'] == 1, 'single actual selected witness is exactly one original V6 leaf')
        for label,rows,eligible,required,reason in [
            ('channel_mutations',report['channel_negative_controls'],totals['excluded_count'],4,'No actual new excluded leaf.'),
            ('split_mutations',report['split_negative_controls'],totals['splits'],5,'No actual new split.'),
            ('leaf_mutations',report['leaf_negative_controls'],totals['leaves'],2,'No actual positive new leaf.'),
            ('UV_channel_mutations',report['UV_channel_negative_controls'],totals['planar'],7,'No actual saved new u proof.')]:
            report['real_case_control_applicability'][label] = applicability(rows,eligible,required,reason)
        source_controls = report['planar_source_negative_controls']
        need((len(source_controls) == 8 and all(row['actual_rejected'] is True for row in source_controls[:6])) if totals['model_applied'] else not source_controls,
             'actual complete planar model controls/applicability differ')
        report['real_case_control_applicability']['planar_source_mutations'] = {
            'status':'executed_with_individual_applicability' if totals['model_applied'] else 'not_applicable',
            'actual_applied_model_count':totals['model_applied'],'actual_rejected_control_count':sum(row['actual_rejected'] is True for row in source_controls),
            'individual_absent_targets_are_not_passes':True,'reason':None if totals['model_applied'] else 'No applied actual planar model.'}
        need(totals['leaves'] > 0 and len(report['phase_negative_controls']) == 3 and len(report['root_coverage_negative_controls']) == 2 and
             report['mandatory_analytic_controls']['mandatory_controls_completed'] is True, 'mandatory actual/analytic control coverage incomplete')
        passes = sum(row['planar_exterior_model_conditional_clearance_gate_passed'] for row in report['frames'])
        need(passes == producer['planar_exterior_model_conditional_clearance_passes'], 'actual producer/independent conditional gate count differs')
        report.update(planar_exterior_model_conditional_clearance_passes=passes,total_new_tree_nodes_verified=totals['nodes'],
                      total_new_splits_verified=totals['splits'],total_new_positive_leaves_verified=totals['leaves'],
                      total_actual_new_excluded_leaves_verified=totals['excluded_count'],total_actual_retained_roots_verified=totals['roots'],
                      total_saved_planar_u_separations_verified=totals['planar'],total_saved_UV_piece_separations_verified=totals['UV_pieces'],
                      total_actual_failed_UV_channel_records_verified=totals['unresolved_UV'],actual_retention_reason_counts=dict(reasons),
                      total_original_V6_reproof_census=dict(inherited_totals))
        for record in contract.values():
            if isinstance(record,dict) and {'path','bytes','sha256'} <= set(record): bound(record)
        for record in list(archive5.values())+list(archive6.values())+list(public_ids.values())+all_new_ids+watched_prerequisites+[producer_contract_id]: bound(record)
        need(identity(__file__)['sha256'] == contract['verifier_sha256'] and identity(args.contract)['sha256'] == report['contract_sha256'],
             'independent source or exact contract changed during mathematical verification')
        report['all_checked_source_contract_and_archived_inputs_unchanged'] = True
        save(); need(report['seconds'] <= 600 and report['peak_RSS_bytes'] <= 805306368, 'final independent source readback exceeded original process gate')
        report['execution_completed'] = True
    except BaseException as exc:
        report['failure'] = {'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        report['finished_utc'] = datetime.now(timezone.utc).isoformat(); save()
        print(json.dumps({name:report.get(name) for name in ('execution_completed','planar_exterior_model_conditional_clearance_passes',
                    'total_new_tree_nodes_verified','seconds','peak_RSS_bytes','failure')}),flush=True)
    return 0 if report['execution_completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())


