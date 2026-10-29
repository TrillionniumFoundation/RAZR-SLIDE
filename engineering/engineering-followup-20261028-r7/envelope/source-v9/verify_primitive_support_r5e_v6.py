"""Independent V6 primitive-support, inherited V5 proof, and forest checker.

No V6 producer or primitive helper is imported. Frozen V5 independent routines
are used solely to recheck the immutable prior proof. New rational Taylor
bounds, dual normals, complete supports, channels, and partitions are rebuilt
here with separate arithmetic. All native/physical membership remains open.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as Q
from functools import lru_cache
import gzip
import hashlib
import importlib.util
import json
from math import factorial
from pathlib import Path
import resource
import time
import traceback

RUN = 40645988108
HEAD = '2ce252f25d340b056bfd350bdde8c743f915c9a4'
V5_LOCK = 'd05a6f6a69ac5eb627d3d1180ff543c4f9b70c7c424c972dfab2b305b8a21211'
V5_CHECKER = '8d2083717a025601eccfbab8679f18e8839c2def0da4995652280b00f79be2a8'
ANCHOR = 'c5f6606924937d716b007cd3ffa8e54df8ecfa5d'
TOL = Q(1e-7)
IDENTITY = [['1', '0', '0', '0'], ['0', '1', '0', '0'], ['0', '0', '1', '0']]


def need(ok, message):
    if not ok:
        raise ValueError(message)


def identity(path):
    path = Path(path)
    with path.open('rb') as stream:
        value = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': value}


def content_equal(a, b):
    return all(a[k] == b[k] for k in ('bytes', 'sha256'))


def bound(record, parent=None):
    path = Path(record['path']) if parent is None else Path(parent) / record['path']
    if parent is not None:
        need(path.resolve().is_relative_to(Path(parent).resolve()), 'bound relative path escapes registered root')
    need(content_equal(identity(path), record), 'bound source bytes or digest differ: ' + str(path))
    return path


def load_module(record, name):
    spec = importlib.util.spec_from_file_location(name, bound(record))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def rat(value):
    return Q(value['exact']) if isinstance(value, dict) else Q(value)


def vector(value, n=3):
    need(type(value) is list and len(value) == n, 'complete source vector dimension')
    return tuple(rat(v) for v in value)


def intervals(value, n=3, ordered=True):
    need(type(value) is list and len(value) == n, 'complete interval dimension')
    result = []
    for pair in value:
        need(type(pair) is list and len(pair) == 2, 'two exact endpoints required')
        lo, hi = map(rat, pair)
        need(not ordered or lo <= hi, 'reversed exact closed interval')
        result.append((lo, hi))
    return tuple(result)


def enc(values):
    return [str(v) for v in values]


def encbox(value):
    return [enc(part) for part in value]


def measure(cell):
    need(len(cell) == 3 and all(a < b for a, b in cell), 'positive diagonal cell topology required')
    answer = Q(1)
    for lo, hi in cell:
        answer *= hi - lo
    return answer


def scalar(a, b):
    need(len(a) == len(b), 'dot product dimension')
    return sum((a[k] * b[k] for k in range(len(a))), Q(0))


def minors(a, b):
    return tuple(a[(k + 1) % 3] * b[(k + 2) % 3] - a[(k + 2) % 3] * b[(k + 1) % 3]
                 for k in range(3))


def closed_projection(normal, domain):
    lower = upper = Q(0)
    for coefficient, (lo, hi) in zip(normal, domain):
        lower += coefficient * (lo if coefficient >= 0 else hi)
        upper += coefficient * (hi if coefficient >= 0 else lo)
    return lower, upper


def combine(*values):
    return sum((v[0] for v in values), Q(0)), sum((v[1] for v in values), Q(0))


def times(coefficient, interval):
    return (coefficient * interval[0], coefficient * interval[1]) if coefficient >= 0 else (
        coefficient * interval[1], coefficient * interval[0])


def interval_product(left, right):
    products = [x * y for x in left for y in right]
    return min(products), max(products)


def dual_solution(x, y, z, a, b):
    """Solve the three row equations by rational elimination, not cross cofactors."""
    matrix = [list(x) + [a], list(y) + [b], list(z) + [Q(0)]]
    for column in range(3):
        pivot = next((r for r in range(column, 3) if matrix[r][column]), None)
        need(pivot is not None, 'singular stored cylinder basis')
        matrix[column], matrix[pivot] = matrix[pivot], matrix[column]
        divisor = matrix[column][column]
        matrix[column] = [v / divisor for v in matrix[column]]
        for row in range(3):
            if row == column:
                continue
            factor = matrix[row][column]
            matrix[row] = [v - factor * w for v, w in zip(matrix[row], matrix[column])]
    normal = tuple(matrix[k][3] for k in range(3))
    need(any(normal) and scalar(normal, x) == a and scalar(normal, y) == b and scalar(normal, z) == 0,
         'independent radial dual-basis equations failed')
    return normal


@lru_cache(maxsize=2048)
def independent_polynomials(centre):
    need(abs(centre) <= 8, 'source angular centre outside finite registered range')
    # Reverse Horner evaluation is independent of the producer's forward term recurrence.
    square = centre * centre
    sine = cosine = Q(0)
    for degree in range(23, -1, -1):
        sign = -1 if degree % 2 else 1
        sine = sine * square + Q(sign, factorial(2 * degree + 1))
        cosine = cosine * square + Q(sign, factorial(2 * degree))
    return centre * sine, cosine, abs(centre) ** 48 / factorial(48)


def angular_certificate(domain):
    lo, hi = domain
    need(lo <= hi, 'closed original angular interval is reversed')
    scaled = (lo + hi) * 32768
    centre = Q(scaled.numerator // scaled.denominator, 65536)
    sine, cosine, error = independent_polynomials(centre)
    return {'U_interval_exact': enc(domain), 'dyadic_centre_exact': str(centre),
            'actual_offset_interval_exact': enc((lo - centre, hi - centre)),
            'Maclaurin_sin_exact': str(sine), 'Maclaurin_cos_exact': str(cosine),
            'degree_47_Lagrange_error_exact': str(error), 'Taylor_term_count': 24,
            'centre_grid_denominator': 65536, 'original_angular_endpoints_replaced': False}


def independent_trig_bounds(a, b, certificate):
    sine, cosine, error = [Q(certificate[k]) for k in
                          ('Maclaurin_sin_exact', 'Maclaurin_cos_exact', 'degree_47_Lagrange_error_exact')]
    offset = tuple(map(Q, certificate['actual_offset_interval_exact']))
    constant = combine(times(b, (sine - error, sine + error)), times(a, (cosine - error, cosine + error)))
    derivative = combine(times(b, (cosine - error, cosine + error)), times(-a, (sine - error, sine + error)))
    radius = max(abs(offset[0]), abs(offset[1]))
    remainder = (abs(a) + abs(b)) * radius * radius / 2
    return combine((-remainder, remainder), interval_product(offset, derivative), constant)


def full_cylinder_domain(face):
    surface = face['local_surface']
    domains = [list(map(rat, surface[name])) for name in ('U_interval', 'V_interval')]
    need(all(len(p) == 2 and p[0] <= p[1] for p in domains), 'ordered source surface domains required')
    need(face['wires'], 'complete source wires required')
    for wire in face['wires']:
        need(wire['location']['matrix_3x4_exact'] == IDENTITY and wire['edge_occurrences'],
             'complete identity wire required')
        for occurrence in wire['edge_occurrences']:
            need(occurrence['location']['matrix_3x4_exact'] == IDENTITY and occurrence['edge_index'] is not None,
                 'complete identity occurrence required')
            curve = occurrence['pcurve']
            need(curve['type'] == 'GeomAbs_CurveType.GeomAbs_Line', 'unsupported cylinder pcurve retains original whole face')
            origin, direction = vector(curve['origin_exact'], 2), vector(curve['direction_exact'], 2)
            first, last = rat(curve['first_parameter']), rat(curve['last_parameter'])
            need(first <= last, 'ordered original pcurve parameters required')
            endpoints = [tuple(origin[k] + direction[k] * parameter for k in range(2)) for parameter in (first, last)]
            for axis in range(2):
                domains[axis] = [min(domains[axis][0], *(p[axis] for p in endpoints)),
                                 max(domains[axis][1], *(p[axis] for p in endpoints))]
    return tuple(tuple(p) for p in domains)


def reconstruct_face(candidate, stationary, displacement, limits):
    face = candidate['complete_original_face']
    need(face['index'] == candidate['face_index'] and canonical(face) == candidate['complete_original_face_canonical_sha256'],
         'complete original face identity differs')
    need(face['location']['matrix_3x4_exact'] == IDENTITY, 'nonidentity face placement unsupported')
    for wire in face['wires']:
        need(wire['location']['matrix_3x4_exact'] == IDENTITY, 'nonidentity wire placement unsupported')
        for occurrence in wire['edge_occurrences']:
            need(occurrence['location']['matrix_3x4_exact'] == IDENTITY and occurrence['edge_index'] is not None,
                 'complete identity occurrence required')
    surface = face['local_surface']
    origin, x, y = [vector(surface[k]) for k in ('origin_exact', 'X_exact', 'Y_exact')]
    if surface['type'] == 'GeomAbs_SurfaceType.GeomAbs_Plane':
        normal = minors(x, y)
        need(any(normal) and scalar(normal, x) == scalar(normal, y) == 0, 'exact nonzero plane normal required')
        centre = scalar(normal, origin)
        delta = closed_projection(normal, displacement)
        swept = tuple((stationary[k][0] + displacement[k][0], stationary[k][1] + displacement[k][1]) for k in range(3))
        slab = {'normal_exact': enc(normal), 'bounds_exact': enc(combine((centre, centre), delta)),
                'source': 'exact_affine_plane'}
        return {'applied': True, 'primitive': 'plane', 'stationary_original_box_exact': encbox(stationary),
                'plane_normal_exact': enc(normal), 'plane_stationary_support_exact': str(centre),
                'full_D_support_exact': enc(delta),
                'pieces': [{'parameter_patch_index': None, 'box_exact': encbox(swept), 'additional_slabs': [slab]}],
                'original_pcurve_values_changed': False, 'native_primitive_semantics_verified': False}
    need(surface['type'] == 'GeomAbs_SurfaceType.GeomAbs_Cylinder', 'unsupported original primitive')
    z, radius = vector(surface['axis_exact']), rat(surface['radius'])
    determinant = scalar(x, minors(y, z))
    need(radius > 0 and determinant != 0, 'positive cylinder radius and nonsingular source basis required')
    u, v = full_cylinder_domain(face)
    need(u[0] < u[1] and limits['cylinder_angular_patch_count'] == 64, 'full positive angular domain and fixed64 patches required')
    endpoints = [u[0] + (u[1] - u[0]) * Q(index, 64) for index in range(65)]
    need(endpoints[0] == u[0] and endpoints[-1] == u[1] and all(a < b for a, b in zip(endpoints, endpoints[1:])),
         'exact closed angular partition must retain every endpoint')
    patches, pieces = [], []
    for index in range(64):
        trig = angular_certificate((endpoints[index], endpoints[index + 1]))
        mapped = tuple(combine(times(radius, independent_trig_bounds(x[k], y[k], trig)),
                               times(z[k], v), (origin[k], origin[k])) for k in range(3))
        clipped = tuple((max(mapped[k][0], stationary[k][0]), min(mapped[k][1], stationary[k][1])) for k in range(3))
        empty = next((axis for axis, (lo, hi) in enumerate(clipped) if lo > hi), None)
        patch = {'parameter_patch_index': index, 'trigonometric_certificate': trig,
                 'stationary_unclipped_box_exact': encbox(mapped), 'stationary_clipped_box_exact': encbox(clipped),
                 'closed_parameter_endpoints_retained': True, 'empty_axis': empty}
        if empty is None:
            a, b = Q(trig['Maclaurin_cos_exact']), Q(trig['Maclaurin_sin_exact'])
            normal = dual_solution(x, y, z, a, b)
            at_origin = scalar(normal, origin)
            support = combine(times(radius, independent_trig_bounds(a, b, trig)), (at_origin, at_origin))
            delta = closed_projection(normal, displacement)
            moved_support = combine(support, delta)
            swept = tuple((clipped[k][0] + displacement[k][0], clipped[k][1] + displacement[k][1]) for k in range(3))
            patch.update(radial_normal_exact=enc(normal), radial_dual_coordinates_exact=enc((a, b, Q(0))),
                         radial_stationary_support_exact=enc(support), full_D_support_exact=enc(delta),
                         swept_box_exact=encbox(swept), radial_swept_support_exact=enc(moved_support))
            pieces.append({'parameter_patch_index': index, 'box_exact': encbox(swept),
                           'additional_slabs': [{'normal_exact': enc(normal), 'bounds_exact': enc(moved_support),
                                                 'source': 'exact_cylinder_patch_radial_support'}]})
        patches.append(patch)
    need(pieces, 'all closed cylinder patches are empty; retain original face')
    return {'applied': True, 'primitive': 'cylinder', 'stationary_original_box_exact': encbox(stationary),
            'complete_source_UV_domains_exact': encbox((u, v)), 'basis_determinant_exact': str(determinant),
            'angular_patch_count': 64, 'patches': patches, 'pieces': pieces,
            'original_pcurve_values_changed': False, 'closed_angular_seams_and_endpoints_retained': True,
            'native_primitive_semantics_verified': False}


def verify_boundary(boundary, old_boundary, old_frame, source_records, bindings, limits):
    need(boundary['schema'] == 'razr-r5e-source-primitive-boundary-refinement-v6' and
         boundary['conditional_primitive_support_model_only'] is True and boundary['native_primitive_semantics_verified'] is False and
         boundary['native_trim_class_membership_verified'] is False and boundary['original_raw_gate_reclassified'] is False,
         'primitive boundary model scope differs')
    key = (old_frame['case_id'], old_frame['frame'])
    binding = bindings[key]
    need(binding['original_full_D'] == old_frame['original_remaining_displacement_box_exact'], 'complete original D changed')
    delta = intervals(binding['original_full_D'])
    need(len(boundary['sources']) == len(old_boundary['sources']) == 2, 'both complete boundary sources required')
    rebuilt = []
    summary = {'planes': 0, 'cylinders': 0, 'fallbacks': 0, 'preserved_edges_vertices': 0,
               'angular_patches_checked': 0, 'nonempty_angular_patches': 0, 'zero_width_pieces_retained': 0,
               'complete_boundary_piece_count': 0}
    for side, (source, previous) in enumerate(zip(boundary['sources'], old_boundary['sources'])):
        material = tuple(previous['material_key'])
        need(source['material_key'] == list(material) == binding['moving_and_fixed_material_keys'][side], 'material/side lineage changed')
        need(source['base_V5_piece_count'] == len(previous['pieces']) and source['known_whole_exact'] == previous['whole_exact'],
             'complete old piece count or original known exterior support changed')
        candidates = {f['face_index']: f for f in source_records[material]['candidate_faces']}
        certificates = source['face_certificates']
        need(len(certificates) == len(candidates), 'missing or duplicate eligible primitive face certificate')
        shift = delta if side == 0 else ((Q(0), Q(0)),) * 3
        expected, seen = [], set()
        certificate_index = 0
        for index, old in enumerate(previous['pieces']):
            prefix = {'base_V5_piece_index': index, 'original_piece_index': old['original_piece_index'],
                      'kind': old['kind'], 'index': old['index'], 'preserved_V5_replacement': old['replacement']}
            unchanged = dict(prefix, replacement='unchanged', box_exact=old['box_exact'], additional_slabs=[])
            candidate = candidates.get(old['index']) if old['kind'] == 'face' else None
            if candidate is None:
                expected.append(unchanged)
                summary['preserved_edges_vertices'] += old['kind'] in ('edge', 'vertex')
                continue
            need(old['replacement'] == 'unchanged' and old['index'] not in seen, 'primitive must map one unchanged original V5 face')
            seen.add(old['index'])
            cert = certificates[certificate_index]
            fixed = {'face_index': old['index'], 'base_V5_piece_index': index,
                     'source_face_canonical_sha256': candidate['complete_original_face_canonical_sha256']}
            need(all(cert[k] == v for k, v in fixed.items()) and type(cert['applied']) is bool, 'source face certificate lineage differs')
            if not cert['applied']:
                need(type(cert['retained_original_face_reason']) is str and bool(cert['retained_original_face_reason']),
                     'unapplied whole-face retention needs an explicit reason')
                need(cert == dict(fixed, applied=False, retained_original_face_reason=cert['retained_original_face_reason']),
                     'fallback face must not carry an applied primitive claim')
                expected.append(unchanged)
                summary['fallbacks'] += 1
            else:
                oldbox = intervals(old['box_exact'])
                stationary = tuple((oldbox[k][0] - shift[k][0], oldbox[k][1] - shift[k][1]) for k in range(3))
                need(all(a <= b for a, b in stationary), 'old full-D face cannot be unswept')
                independent = reconstruct_face(candidate, stationary, shift, limits)
                need(cert == dict(fixed, **independent), 'independently reconstructed full source primitive certificate differs')
                is_plane = independent['primitive'] == 'plane'
                summary['planes' if is_plane else 'cylinders'] += 1
                if not is_plane:
                    summary['angular_patches_checked'] += len(independent['patches'])
                    summary['nonempty_angular_patches'] += len(independent['pieces'])
                for piece in independent['pieces']:
                    expected.append(dict(prefix, replacement='plane_slab' if is_plane else 'cylinder_patch',
                                         face_certificate_index=certificate_index, **piece))
            certificate_index += 1
        need(seen == set(candidates) and certificate_index == len(certificates), 'original eligible face omitted')
        need(source['pieces'] == expected and 0 < len(expected) <= limits['maximum_boundary_pieces_per_material'],
             'complete source piece mapping, box, slab or finite piece cap differs')
        runtime = []
        for piece in expected:
            box = intervals(piece['box_exact'])
            need(len(piece['additional_slabs']) <= 1, 'at most one nonaxis support slab per piece')
            slabs = []
            for slab in piece['additional_slabs']:
                normal = vector(slab['normal_exact'])
                support = intervals([slab['bounds_exact']], 1)[0]
                need(any(normal), 'nonzero registered slab normal required')
                slabs.append((normal, support))
            runtime.append({'box': box, 'additional_slabs': slabs,
                            'slab_source': piece['additional_slabs'][0]['source'] if slabs else None})
            summary['zero_width_pieces_retained'] += any(lo == hi for lo, hi in box)
        rebuilt.append({'whole': intervals(source['known_whole_exact']), 'pieces': runtime})
        summary['complete_boundary_piece_count'] += len(expected)
    need(boundary['applied_plane_count'] == summary['planes'] and boundary['applied_cylinder_count'] == summary['cylinders'] and
         boundary['retained_original_faces_after_rejection'] == summary['fallbacks'], 'primitive face census differs')
    return rebuilt, summary


def channel_for(cell, whole, axis, end):
    channel = list(cell)
    channel[axis] = (min(whole[axis][0] - 1, cell[axis][0] - 1), cell[axis][1]) if end == 0 else (
        cell[axis][0], max(whole[axis][1] + 1, cell[axis][1] + 1))
    return tuple(channel)


def separator_holds(piece, channel, code):
    need(type(code) is str and code in '01234567' and len(code) == 1, 'unregistered support separation code')
    index = int(code)
    if index < 6:
        axis, end = divmod(index, 2)
        return piece['box'][axis][1] <= channel[axis][0] if end == 0 else piece['box'][axis][0] >= channel[axis][1]
    need(len(piece['additional_slabs']) == 1, 'nonaxis code requires its one registered slab')
    normal, support = piece['additional_slabs'][0]
    need(any(normal) and support[0] <= support[1], 'valid closed support slab required')
    lower, upper = closed_projection(normal, channel)
    need(lower < upper, 'nonzero normal on positive open box must have positive image width')
    return support[1] <= lower if index == 6 else support[0] >= upper


def check_exclusion(item, cell, sources):
    need(item['excluded_open_interior'] is True and item['whole_closed_cell_disjoint_claimed'] is False and
         item['closed_cell_boundary_retained_as_zero_volume_carrier'] is True,
         'exclusion must retain closed boundary carriers and claim only open interior')
    side, axis, end = item['material_side'], item['axis'], item['end']
    need(type(side) is int and 0 <= side < len(sources) and type(axis) is int and 0 <= axis < 3 and
         type(end) is int and end in (0, 1), 'registered source/channel indices required')
    source = sources[side]
    channel = intervals(item['open_channel_exact'])
    need(all(lo < hi for lo, hi in channel), 'connected positive open channel required')
    need(channel == channel_for(cell, source['whole'], axis, end), 'registered channel fails footprint or known-exterior extension')
    codes = item['complete_piece_separation_codes']
    need(type(codes) is str and len(codes) == len(source['pieces']) == item['boundary_piece_count'],
         'complete per-piece separation code coverage required')
    for piece, code in zip(source['pieces'], codes):
        need(separator_holds(piece, channel, code), 'registered support does not separate from the open channel')
    count = sum(code in '67' for code in codes)
    need(item['nonaxis_separation_code_count'] == count, 'nonaxis separation count differs')
    return {'pieces': len(codes), 'nonaxis': count}


def check_unresolved(item, cell, sources, partial=False):
    need(item['excluded_open_interior'] is False and item['actual_material_interference_claimed'] is False,
         'unresolved separators cannot claim actual interference')
    expected = [(s, k, e) for s in range(len(sources)) for k in range(3) for e in (0, 1)]
    if partial:
        need(item['search_stopped_at_predicate_budget'] is True and 'all_registered_channels_unresolved' not in item,
             'partial predicate-budget observation cannot claim complete unresolved channels')
        rows = item['completed_unresolved_channels']
        need(len(rows) < len(expected), 'completed unresolved prefix must exclude the unfinished channel')
    else:
        need(not item.get('search_stopped_at_predicate_budget'), 'incomplete observation cannot drive a split')
        rows = item['all_registered_channels_unresolved']
        need(len(rows) == len(expected), 'all twelve registered unresolved channels required')
    need([(r['material_side'], r['axis'], r['end']) for r in rows] == expected[:len(rows)],
         'unresolved channel identities/order are incomplete or duplicated')
    for row in rows:
        side, axis, end, index = [row[k] for k in ('material_side', 'axis', 'end', 'unresolved_piece_index')]
        need(all(type(v) is int for v in (side, axis, end, index)) and 0 <= index < len(sources[side]['pieces']),
             'registered unresolved piece identity required')
        piece = sources[side]['pieces'][index]
        channel = channel_for(cell, sources[side]['whole'], axis, end)
        codes = '01234567' if piece['additional_slabs'] else '012345'
        need(not any(separator_holds(piece, channel, code) for code in codes),
             'recorded unresolved piece has an available separating inequality')
    return len(rows)


def independent_cut(cell, sources, observation):
    check_unresolved(observation, cell, sources)
    endpoints, slab_rows = {}, []
    for row in observation['all_registered_channels_unresolved']:
        side, index = row['material_side'], row['unresolved_piece_index']
        piece = sources[side]['pieces'][index]
        for axis in range(3):
            for end in (0, 1):
                point = piece['box'][axis][end]
                if cell[axis][0] < point < cell[axis][1] and (axis, point) not in endpoints:
                    endpoints[(axis, point)] = {'kind': 'model_boundary_endpoint', 'material_side': side,
                                                'piece_index': index, 'axis': axis, 'endpoint': end}
        for normal, support in piece['additional_slabs']:
            slab_rows.append((piece.get('slab_source') == 'exact_cylinder_patch_radial_support', normal))
    if endpoints:
        ordered = sorted(endpoints, key=lambda key: (
            min(key[1] - cell[key[0]][0], cell[key[0]][1] - key[1]) / (cell[key[0]][1] - cell[key[0]][0]),
            key[0], key[1]))
        axis, point = ordered[0]
        return axis, point, endpoints[(axis, point)]
    radial = [normal for is_radial, normal in slab_rows if is_radial]
    if radial:
        normals, rule = radial, 'largest_registered_radial_slab_variation'
    elif slab_rows:
        normals, rule = [normal for unused, normal in slab_rows], 'largest_registered_slab_variation'
    else:
        normals, rule = [], 'longest_cell_interval'
    scores = [max((abs(n[axis]) * (cell[axis][1] - cell[axis][0]) for n in normals),
                  default=cell[axis][1] - cell[axis][0]) for axis in range(3)]
    axis = next(k for k in range(3) if scores[k] == max(scores))
    return axis, sum(cell[axis], Q(0)) / 2, {'kind': 'registered_midpoint', 'axis': axis, 'selection_rule': rule}


def verify_tree(tree, root, sources, limits):
    nodes = tree['nodes']
    need(type(nodes) is list and nodes and all(type(n) is dict and type(n.get('id')) is int and n['id'] == i
                                               for i, n in enumerate(nodes)), 'complete contiguous explicit tree nodes required')
    stack, visited = [(0, root, 0)], set()
    retained = excluded = Q(0)
    splits = leaves = excluded_count = depth_max = checked = nonaxis = unresolved = 0
    reasons = Counter()
    first_excluded = first_split = None
    leaf_records = []
    while stack:
        index, cell, depth = stack.pop()
        need(type(index) is int and 0 <= index < len(nodes) and index not in visited, 'missing, cyclic or duplicate tree node')
        visited.add(index)
        need(depth <= limits['maximum_depth'], 'path exceeds original depth cap')
        depth_max = max(depth_max, depth)
        node, volume = nodes[index], measure(cell)
        kind = node['kind']
        if kind == 'split':
            need(volume > Q(limits['tiny_retained_volume_exact']), 'positive tiny leaf must be retained without further splitting')
            axis, point = node['axis'], Q(node['cut_exact'])
            need(type(axis) is int and 0 <= axis < 3 and cell[axis][0] < point < cell[axis][1],
                 'cut must be strictly inside a registered axis')
            expected_axis, expected_point, witness = independent_cut(cell, sources, node['actual_channel_observation'])
            unresolved += 6 * len(sources)
            need((axis, point, node['cut_source']) == (expected_axis, expected_point, witness),
                 'split endpoint/midpoint or deterministic registered support rule differs')
            children = node['children']
            need(type(children) is list and len(children) == 2 and children[0] != children[1] and
                 all(type(child) is int and index < child < len(nodes) for child in children),
                 'exactly two distinct forward children required')
            low, high = list(cell), list(cell)
            low[axis], high[axis] = (cell[axis][0], point), (point, cell[axis][1])
            volumes = [measure(low), measure(high)]
            need(sum(volumes, Q(0)) == volume and Q(node['parent_positive_directed_volume_exact']) == volume and
                 list(map(Q, node['children_positive_directed_volumes_exact'])) == volumes,
                 'positive child directed volumes must exactly conserve the parent')
            need(node['closed_cut_plane_retained_as_zero_volume_carrier'] is True, 'closed cut-plane carrier was omitted')
            stack.extend([(children[1], tuple(high), depth + 1), (children[0], tuple(low), depth + 1)])
            splits += 1
            if first_split is None:
                first_split = (index, cell)
            continue
        need(kind in ('retained', 'excluded') and Q(node['positive_directed_volume_exact']) == volume,
             'explicit positive leaf volume differs')
        leaves += 1
        leaf_records.append((index, cell, node))
        if kind == 'excluded':
            need(volume > Q(limits['tiny_retained_volume_exact']), 'tiny leaf cannot be discarded through exclusion')
            answer = check_exclusion(node['certificate'], cell, sources)
            checked += answer['pieces']
            nonaxis += answer['nonaxis']
            excluded += volume
            excluded_count += 1
            if first_excluded is None:
                first_excluded = (node['certificate'], cell)
        else:
            need(node['actual_material_interference_claimed'] is False, 'retained overbound is not actual interference')
            reason = node['reason']
            need(reason in ('tiny_exact_volume_retained', 'global_predicate_budget_retained',
                            'path_depth_limit_retained', 'global_split_limit_retained'), 'unregistered leaf stop reason')
            if reason == 'tiny_exact_volume_retained':
                need(volume <= Q(limits['tiny_retained_volume_exact']), 'original tiny threshold changed')
            else:
                need(volume > Q(limits['tiny_retained_volume_exact']), 'tiny leaf must retain its actual stop classification')
            if reason == 'path_depth_limit_retained':
                need(depth == limits['maximum_depth'], 'path depth stop does not match actual depth')
            if reason in ('path_depth_limit_retained', 'global_split_limit_retained'):
                need('actual_channel_observation' in node, 'actual unresolved channels required before path/split stop')
            if 'actual_channel_observation' in node:
                observation = node['actual_channel_observation']
                partial = observation.get('search_stopped_at_predicate_budget') is True
                need(not partial or reason == 'global_predicate_budget_retained', 'unfinished predicates cannot support another stop reason')
                unresolved += check_unresolved(observation, cell, sources, partial)
            retained += volume
            reasons[reason] += 1
    need(len(visited) == len(nodes), 'allocated pending, unreachable or omitted node not fully retained')
    need(retained + excluded == measure(root), 'complete root directed measure not conserved')
    need(retained == Q(tree['retained_sum_exact']) and excluded == Q(tree['excluded_open_sum_exact']), 'exact tree volume sums differ')
    need(leaves == tree['total_leaf_count'] and excluded_count == tree['excluded_leaf_count'] and
         leaves - excluded_count == tree['retained_leaf_count'], 'complete leaf census differs')
    need(dict(reasons) == tree['retained_reason_counts'] and depth_max == tree['maximum_depth_reached'], 'retention reason/depth census differs')
    need(tree['all_closed_cut_planes_and_root_boundaries_retained'] is True, 'closed zero-volume carriers were lost')
    need(len(nodes) == 2 * splits + 1 and leaves == splits + 1, 'full binary partition topology differs')
    return {'retained': retained, 'excluded': excluded, 'splits': splits, 'nodes': len(nodes), 'leaves': leaves,
            'excluded_count': excluded_count, 'depth': depth_max, 'pieces_checked': checked, 'nonaxis_checked': nonaxis,
            'unresolved_piece_records_checked': unresolved, 'reasons': reasons, 'sample_exclusion': first_excluded,
            'sample_split': first_split, 'leaf_records': leaf_records}


def rejected(name, call):
    error = None
    try:
        call()
    except (ValueError, KeyError, IndexError, TypeError, ZeroDivisionError) as exc:
        error = str(exc)
    need(error is not None, 'corrupt certificate was accepted: ' + name)
    return {'name': name, 'actual_rejected': True, 'reason': error}


def copied(value):
    return json.loads(json.dumps(value))


def channel_controls(good, target, sources):
    variants = []
    changed = copied(good)
    changed['complete_piece_separation_codes'] = changed['complete_piece_separation_codes'][:-1]
    variants.append(('omitted-complete-boundary-piece', changed))
    changed = copied(good)
    changed['whole_closed_cell_disjoint_claimed'] = True
    variants.append(('overclaim-closed-cell-disjointness', changed))
    changed = copied(good)
    changed['open_channel_exact'][good['axis']][good['end']] = str(target[good['axis']][good['end']])
    variants.append(('channel-does-not-reach-known-exterior', changed))
    changed = copied(good)
    channel = intervals(good['open_channel_exact'])
    codes = list(good['complete_piece_separation_codes'])
    choice = next(((i, code) for i, piece in enumerate(sources[good['material_side']]['pieces'])
                   for code in ('01234567' if piece['additional_slabs'] else '012345')
                   if not separator_holds(piece, channel, code)), None)
    need(choice is not None, 'analytic/actual channel needs a false registered separator mutation')
    index, code = choice
    codes[index] = code
    changed['complete_piece_separation_codes'] = ''.join(codes)
    changed['nonaxis_separation_code_count'] = sum(c in '67' for c in codes)
    variants.append(('false-separating-coordinate-or-slab', changed))
    return [rejected(name, lambda altered=altered: check_exclusion(altered, target, sources)) for name, altered in variants]


def mutate_tree(name, tree, root, sources, limits, edit):
    changed = copied(tree)
    edit(changed)
    return rejected(name, lambda: verify_tree(changed, root, sources, limits))


def split_controls(tree, root, sources, limits, stats=None):
    stats = verify_tree(tree, root, sources, limits) if stats is None else stats
    need(stats['sample_split'] is not None, 'actual split mutation target absent')
    index, parent = stats['sample_split']
    variants = [
        ('omitted-partition-child', lambda t: t['nodes'][index].update(children=t['nodes'][index]['children'][:1])),
        ('duplicated-partition-child', lambda t: t['nodes'][index].update(children=[t['nodes'][index]['children'][0]] * 2)),
        ('cut-on-parent-boundary', lambda t: t['nodes'][index].update(cut_exact=str(parent[t['nodes'][index]['axis']][0]))),
        ('discarded-closed-cut-plane', lambda t: t['nodes'][index].update(closed_cut_plane_retained_as_zero_volume_carrier=False)),
        ('incorrect-positive-directed-volume', lambda t: t['nodes'][index].update(parent_positive_directed_volume_exact='0'))]
    return [mutate_tree(name, tree, root, sources, limits, edit) for name, edit in variants]


def leaf_controls(tree, root, sources, limits, stats=None):
    stats = verify_tree(tree, root, sources, limits) if stats is None else stats
    index, cell, leaf = min(stats['leaf_records'], key=lambda row: measure(row[1]))
    rows = [mutate_tree('omitted-allocated-leaf-node', tree, root, sources, limits, lambda t: t['nodes'].pop(index)),
            mutate_tree('discarded-smallest-positive-leaf-volume', tree, root, sources, limits,
                        lambda t: t['nodes'][index].update(positive_directed_volume_exact='0'))]
    for row in rows:
        row.update(original_leaf_id=index, original_leaf_kind=leaf['kind'], original_leaf_reason=leaf.get('reason'),
                   original_positive_volume_exact=leaf['positive_directed_volume_exact'])
    return rows


def applicability(rows, eligible, required, absent):
    if eligible:
        need(len(rows) == required and all(r['actual_rejected'] is True for r in rows), 'applicable actual-case controls incomplete')
    else:
        need(not rows, 'inapplicable actual-case mutation falsely claimed executed')
    return {'status': 'executed' if eligible else 'not_applicable', 'actual_eligible_count': eligible,
            'reason': None if eligible else absent, 'analytic_controls_are_separate': True}


def analytic_controls(limits):
    """Known complete closed solids; no original-case/native qualification."""
    unit = ((Q(0), Q(1)),) * 3
    faces = []
    for axis in range(3):
        for end in (0, 1):
            face = list(unit)
            face[axis] = (unit[axis][end], unit[axis][end])
            faces.append({'box': tuple(face), 'additional_slabs': [], 'slab_source': None})
    sources = [{'whole': unit, 'pieces': faces}, {'whole': unit, 'pieces': faces}]

    def exterior(target):
        return {'excluded_open_interior': True, 'material_side': 0, 'axis': 0, 'end': 1,
                'open_channel_exact': encbox(channel_for(target, unit, 0, 1)),
                'complete_piece_separation_codes': '000000', 'boundary_piece_count': 6,
                'closed_cell_boundary_retained_as_zero_volume_carrier': True,
                'whole_closed_cell_disjoint_claimed': False, 'nonaxis_separation_code_count': 0}

    def unresolved(target):
        rows = []
        for side in range(2):
            for axis in range(3):
                for end in (0, 1):
                    rows.append({'material_side': side, 'axis': axis, 'end': end, 'unresolved_piece_index': 2 * axis + end})
        item = {'excluded_open_interior': False, 'all_registered_channels_unresolved': rows,
                'actual_material_interference_claimed': False}
        check_unresolved(item, target, sources)
        return item

    def tree_one(node, root, kind):
        value = measure(root)
        return {'nodes': [node], 'retained_sum_exact': str(value if kind == 'retained' else 0),
                'excluded_open_sum_exact': str(value if kind == 'excluded' else 0), 'total_leaf_count': 1,
                'excluded_leaf_count': int(kind == 'excluded'), 'retained_leaf_count': int(kind == 'retained'),
                'retained_reason_counts': {node['reason']: 1} if kind == 'retained' else {},
                'maximum_depth_reached': 0, 'all_closed_cut_planes_and_root_boundaries_retained': True}

    outside = ((Q(2), Q(3)), (Q(0), Q(1)), (Q(0), Q(1)))
    excluded_tree = tree_one({'id': 0, 'kind': 'excluded', 'positive_directed_volume_exact': '1',
                              'certificate': exterior(outside)}, outside, 'excluded')
    excluded_stats = verify_tree(excluded_tree, outside, sources, limits)
    need(excluded_stats['excluded'] == 1 and excluded_stats['retained'] == 0 and excluded_stats['pieces_checked'] == 6,
         'complete closed-box exterior analytic positive failed')
    delta = Q(limits['tiny_retained_volume_exact']) / 2
    root = ((Q(1) - delta, Q(2)), (Q(0), Q(1)), (Q(0), Q(1)))
    observation = unresolved(root)
    axis, cut, witness = independent_cut(root, sources, observation)
    need(axis == 0 and cut == 1, 'analytic split must use the original solid boundary')
    left, right = list(root), list(root)
    left[0], right[0] = (Q(1) - delta, Q(1)), (Q(1), Q(2))
    lv, rv = measure(left), measure(right)
    split = {'nodes': [
        {'id': 0, 'kind': 'split', 'axis': axis, 'cut_exact': str(cut), 'cut_source': witness, 'children': [1, 2],
         'parent_positive_directed_volume_exact': str(measure(root)), 'children_positive_directed_volumes_exact': enc((lv, rv)),
         'closed_cut_plane_retained_as_zero_volume_carrier': True, 'actual_channel_observation': observation},
        {'id': 1, 'kind': 'retained', 'reason': 'tiny_exact_volume_retained',
         'positive_directed_volume_exact': str(lv), 'actual_material_interference_claimed': False},
        {'id': 2, 'kind': 'excluded', 'positive_directed_volume_exact': str(rv), 'certificate': exterior(right)}],
        'retained_sum_exact': str(lv), 'excluded_open_sum_exact': str(rv), 'total_leaf_count': 2,
        'excluded_leaf_count': 1, 'retained_leaf_count': 1, 'retained_reason_counts': {'tiny_exact_volume_retained': 1},
        'maximum_depth_reached': 1, 'all_closed_cut_planes_and_root_boundaries_retained': True}
    split_stats = verify_tree(split, root, sources, limits)
    need(split_stats['retained'] == delta > 0 and split_stats['excluded'] == 1 and split_stats['splits'] == 1,
         'complete partition and nonzero tiny-leaf retention analytic positive failed')
    inside = ((Q(1, 4), Q(1, 4) + delta), (Q(1, 4), Q(3, 4)), (Q(1, 4), Q(3, 4)))
    all_retained_observation = unresolved(inside)
    kept_node = {'id': 0, 'kind': 'retained', 'reason': 'tiny_exact_volume_retained',
                 'positive_directed_volume_exact': str(measure(inside)), 'actual_material_interference_claimed': False,
                 'actual_channel_observation': all_retained_observation}
    retained_tree = tree_one(kept_node, inside, 'retained')
    retained_stats = verify_tree(retained_tree, inside, sources, limits)
    need(retained_stats['retained'] == measure(inside) > 0 and retained_stats['excluded_count'] == retained_stats['splits'] == 0 and
         retained_stats['sample_exclusion'] is None and retained_stats['sample_split'] is None,
         'complete-box all-retained/no-excluded analytic regression failed')
    channel_na = applicability([], retained_stats['excluded_count'], 4, 'This analytic positive has no excluded leaf.')
    split_na = applicability([], retained_stats['splits'], 5, 'This analytic positive has no split.')
    channel_bad = channel_controls(exterior(outside), outside, sources)
    split_bad = split_controls(split, root, sources, limits, split_stats)
    leaf_bad = leaf_controls(split, root, sources, limits, split_stats)
    need(len(channel_bad) == 4 and len(split_bad) == 5 and len(leaf_bad) == 2 and
         all(r['actual_rejected'] for r in channel_bad + split_bad + leaf_bad), 'mandatory analytic rejection controls incomplete')
    return {'schema': 'razr-r5e-mandatory-primitive-checker-controls-v6', 'execution_kind': 'synthetic_analytic_control',
            'qualifies_original_or_primitive_model_case': False, 'real_case_result_changed': False,
            'original_threshold_and_production_limits_unchanged': True,
            'complete_source_closed_boxes_exact': [encbox(unit), encbox(unit)], 'complete_source_face_counts': [6, 6],
            'complete_box_exterior_positive': {'verified': True, 'root_box_exact': encbox(outside), 'excluded_open_volume_exact': '1'},
            'exact_split_positive': {'verified': True, 'root_box_exact': encbox(root), 'cut_exact': str(cut),
                                     'children_positive_directed_volumes_exact': enc((lv, rv)), 'tiny_leaf_retained_in_full': True},
            'all_retained_no_excluded_positive': {'verified': True, 'root_box_exact': encbox(inside),
                'retained_positive_volume_exact': str(measure(inside)), 'excluded_leaves': 0, 'splits': 0,
                'all_twelve_unresolved_channels_checked': True, 'channel_mutations': channel_na, 'split_mutations': split_na,
                'is_actual_V5_or_V6_case_branch_coverage': False},
            'channel_negative_controls': channel_bad, 'split_negative_controls': split_bad,
            'leaf_negative_controls': leaf_bad, 'mandatory_controls_completed': True}


def require_scope(record):
    need(record['conditional_primitive_support_model_only'] is True and record['conditional_trim_model_only'] is True and
         record['native_primitive_semantics_verified'] is False and record['native_trim_class_membership_verified'] is False and
         record['inner_wire_hole_semantics_verified_for_native'] is False and record['original_raw_gate_reclassified'] is False and
         record['full_continuous_G2'] is False, 'conditional primitive/trim model cannot acquire native or original raw qualification')


def fixed_limits(limits):
    required = {'wall_seconds': 600, 'RSS_limit_bytes': 805306368, 'maximum_splits': 4096, 'maximum_depth': 24,
                'maximum_boundary_box_tests': 12000000, 'maximum_support_inequality_tests': 12000000,
                'maximum_boundary_pieces_per_material': 4096, 'cylinder_angular_patch_count': 64,
                'Taylor_term_count': 24, 'centre_grid_denominator': 65536}
    need(all(type(limits[k]) is int and limits[k] == value for k, value in required.items()) and
         Q(limits['tiny_retained_volume_exact']) == TOL / 100000, 'original finite capacity, Taylor/domain policy or tiny threshold changed')


def owned_completion(controller, report, source_sha, output=None):
    need(controller['completed'] is True and controller['worker_started'] is True and controller['worker_exit_code'] == 0 and
         controller['resource_stop'] is None, 'owned process did not actually complete within its resource gates')
    need(controller['limits']['registered_math_contract_sha256'] == report['contract_sha256'] and
         controller['limits']['worker']['sha256'] == source_sha, 'owned report/source/contract identity differs')
    gates = {'wall_seconds': 600, 'RSS_limit_bytes': 805306368, 'shared_ceiling_bytes': 7301444403,
             'disk_floor_bytes': 104857600, 'maximum_output_bytes': 41943040, 'metadata_margin_bytes': 4194304}
    need(all(controller['limits'][k] == v for k, v in gates.items()), 'original owned resource limit changed')
    if output is not None:
        need(Path(controller['limits']['worker_output_directory']).resolve() == Path(output).resolve(), 'owned output directory differs')


def archived_v5(contract):
    bridge = json.loads(bound(contract['base_V5_input_bridge']).read_text())
    need(bridge['actual_run_id'] == RUN and bridge['actual_request_commit'] == HEAD and
         bridge['original_reports_or_certificates_edited'] is False and bridge['path_mapping_only'] is True,
         'immutable actual V5 archive scope differs')
    directory = Path(contract['base_V5_root']).resolve()
    records = {r['path']: r for r in bridge['files']}
    need(len(records) == len(bridge['files']) == 25, 'complete unique actual V5 file mapping required')
    actual = {}
    for name, record in records.items():
        path = (directory / name).resolve()
        need(path.is_relative_to(directory), 'actual V5 path escapes archive root')
        actual[name] = identity(path)
        need(content_equal(actual[name], record), 'immutable actual V5 input bytes differ')
    fields = {'base_V5_actual_report': 'all-trim-model-frames/report.json',
              'base_V5_actual_independent_report': 'verify-all/report.json',
              'base_V5_actual_owned_supervision': 'all-trim-model-frames-supervision/controller.json',
              'base_V5_actual_independent_owned_supervision': 'verify-all-supervision/controller.json'}
    need(all(contract[field] == actual[name] for field, name in fields.items()), 'declared actual prior report/receipt differs')
    def load(name):
        return json.loads(Path(actual[name]['path']).read_text())
    prior, verified, pipeline = [load(n) for n in ('all-trim-model-frames/report.json', 'verify-all/report.json', 'pipeline.json')]
    need(prior['execution_completed'] is True and verified['execution_completed'] is True and pipeline['completed'] is True,
         'actual prior V5 completed experiment required')
    need(prior['phase'] == 'all_trim_model_frames' and prior['trim_model_conditional_clearance_passes'] ==
         verified['trim_model_conditional_clearance_passes'] == 8, 'original V5 result changed')
    need(pipeline['environment']['github_sha'] == HEAD and pipeline['source_lock_identity']['sha256'] == V5_LOCK,
         'original V5 actual source lock/head differs')
    lock = json.loads(bound(contract['base_V5_source_lock']).read_text())
    need(contract['base_V5_source_lock']['sha256'] == V5_LOCK and
         content_equal(contract['base_V5_source_lock'], pipeline['source_lock_identity']), 'frozen V5 lock bytes differ')
    members = {r['path']: r for r in lock['r5_files']}
    for field, filename in [('base_V5_verifier_source', 'verify_exterior_trim_r5e_v5.py'),
                            ('base_verifier_source', 'verify_exterior_channels_r5e_v3.py'),
                            ('V5_trim_source_bundle', 'R5E_V5_PLANAR_TRIM_SOURCE.json.gz')]:
        bound(contract[field])
        need(content_equal(contract[field], members[filename]), 'frozen independent V5 source/bundle differs')
    need(contract['base_V5_verifier_source']['sha256'] == V5_CHECKER, 'frozen V5 checker source differs')
    need(content_equal(prior['trim_source_bundle'], contract['V5_trim_source_bundle']), 'prior V5 material projection differs')
    for label, phase, source_name in [('all-trim-model-frames', 'all_trim_model_frames', 'exterior_trim_r5e_v5.py'),
                                      ('verify-all', 'verify_all', 'verify_exterior_trim_r5e_v5.py')]:
        stage = next(s for s in pipeline['stages'] if s['phase'] == phase)
        item = load(label + '/report.json')
        receipt = load(label + '-supervision/controller.json')
        need(stage['completed'] is True and content_equal(stage['report'], actual[label + '/report.json']), 'prior actual stage identity differs')
        owned_completion(receipt, item, members[source_name]['sha256'])
        need(Path(receipt['limits']['worker_output_directory']) == Path(stage['report']['path']).parent,
             'preserved actual V5 output identity differs')
        math_contract = load(label + '-contract.json')
        supervision_contract = load(label + '-supervision-contract.json')
        need(actual[label + '-contract.json']['sha256'] == item['contract_sha256'] ==
             supervision_contract['registered_math_contract_sha256'], 'preserved V5 contracts differ')
        need(content_equal(stage['controller'], actual[label + '-supervision/controller.json']) and
             content_equal(stage['contract'], actual[label + '-contract.json']) and
             content_equal(stage['supervision_contract'], actual[label + '-supervision-contract.json']),
             'preserved V5 stage/contract/receipt identities differ')
        need(math_contract['producer_sha256'] == members[source_name]['sha256'], 'preserved V5 mathematical source differs')
    need(content_equal(verified['verified_producer_report'], actual['all-trim-model-frames/report.json']) and
         verified['expected_phase'] == 'all_trim_model_frames', 'prior independent reader checked a different producer')
    need(len(prior['frames']) == 16 and verified['expected_case_frames'] == [[r['case_id'], r['frame']] for r in prior['frames']],
         'prior independent full16 coverage differs')
    for record in (prior, verified):
        need(record['conditional_trim_model_only'] is True and record['native_trim_class_membership_verified'] is False and
             record['inner_wire_hole_semantics_verified_for_native'] is False and record['original_raw_gate_reclassified'] is False and
             record['full_continuous_G2'] is False, 'prior V5 scope was rewritten')
    fixed_names = {'pipeline.json', 'all-trim-model-frames/report.json', 'verify-all/report.json',
                   'all-trim-model-frames-supervision/controller.json', 'verify-all-supervision/controller.json',
                   'all-trim-model-frames-contract.json', 'all-trim-model-frames-supervision-contract.json',
                   'verify-all-contract.json', 'verify-all-supervision-contract.json'}
    need(set(actual) == fixed_names | {'all-trim-model-frames/' + r['certificate']['path'] for r in prior['frames']},
         'actual V5 complete certificate file coverage differs')
    return actual, prior, verified, pipeline


def primitive_sources(contract, baseline, prior, old_records):
    with gzip.open(bound(contract['primitive_source_bundle']), 'rt') as stream:
        projection = json.load(stream)
    need(projection['schema'] == 'razr-r5e-original-primitive-source-projection-v6' and
         projection['actual_V5_run_id'] == RUN and projection['actual_V5_request_commit'] == HEAD and
         projection['new_native_operations'] == 0 and projection['new_mathematical_qualification'] is False and
         projection['original_pcurve_values_changed'] is False and projection['native_primitive_semantics_verified'] is False and
         projection['native_trim_class_membership_verified'] is False and projection['native_inventory_was_preexisting_actual_evidence'] is True,
         'original primitive-source projection scope differs')
    need(content_equal(projection['actual_V5_report_identity'], contract['base_V5_actual_report']) and
         content_equal(projection['original_public_R4_report_identity'], contract['r4_report']), 'primitive source experiment identity differs')
    need(dict(projection['original_native_inventory_identity'], path=projection['original_native_inventory_relative_path']) in baseline['input_identities'],
         'primitive source original native inventory is not R4-bound')
    records, census = {}, Counter()
    for record in projection['records']:
        key = (record['input']['case_id'], record['input']['material_id'])
        need(key not in records and key in old_records, 'duplicate or different whole-material projection')
        old = old_records[key]
        need(record['full_original_face_records_unchanged'] is True and all(record[field] == old[field] for field in
             ('input', 'original_complete_boundary_counts', 'original_complete_boundary_canonical_sha256')),
             'original whole material/counts/canonical boundary identity differs from frozen V5')
        candidates = record['candidate_faces']
        need(len({c['face_index'] for c in candidates}) == len(candidates), 'duplicate primitive candidate face')
        for candidate in candidates:
            face = candidate['complete_original_face']
            index, primitive = candidate['face_index'], candidate['source_primitive']
            need(type(index) is int and 0 <= index < record['original_complete_boundary_counts']['faces'] and
                 face['index'] == index and canonical(face) == candidate['complete_original_face_canonical_sha256'],
                 'complete original primitive face source identity differs')
            need(primitive in ('GeomAbs_Plane', 'GeomAbs_Cylinder') and face['local_surface']['type'] == 'GeomAbs_SurfaceType.' + primitive,
                 'registered primitive class differs')
            need(candidate['selection_basis'] == 'actual first blocking piece of an original V5 non-tiny retained leaf',
                 'primitive selection scope differs')
            census[primitive] += 1
        records[key] = record
    need(len(records) == len(projection['records']) == 32 and set(records) == set(old_records), 'complete original32 material coverage required')
    need(dict(census) == {'GeomAbs_Plane': 48, 'GeomAbs_Cylinder': 16}, 'fixed original48 plane/16 cylinder census differs')
    bindings = {(r['case_id'], r['frame']): r for r in projection['frame_bindings']}
    need(len(bindings) == len(projection['frame_bindings']) == 16 and
         list(bindings) == [(r['case_id'], r['frame']) for r in prior['frames']], 'complete primitive frame binding order differs')
    need({tuple(key) for r in bindings.values() for key in r['moving_and_fixed_material_keys']} == set(records),
         'primitive source material/frame mapping differs')
    return records, bindings, dict(census)


def retained_leaf_records(certificate):
    result = []
    for root in certificate['roots']:
        stack = [(0, intervals(root['root_box_exact']))]
        found = []
        while stack:
            index, cell = stack.pop()
            node = root['tree']['nodes'][index]
            if node['kind'] == 'split':
                axis, cut = node['axis'], Q(node['cut_exact'])
                low, high = list(cell), list(cell)
                low[axis], high[axis] = (cell[axis][0], cut), (cut, cell[axis][1])
                stack.extend([(node['children'][1], tuple(high)), (node['children'][0], tuple(low))])
            elif node['kind'] == 'retained':
                found.append({'locator': [root['original_cell_index'], index], 'box': cell,
                              'actual_V5_leaf_record': node, 'root_directed_volume_exact': node['positive_directed_volume_exact']})
        result.extend(sorted(found, key=lambda row: row['locator'][1]))
    return result


def recheck_prior_frame(old_frame, old, proof, certificate, v5, base, trim_records, trim_bindings, limits,
                        primitive_records, primitive_binding):
    need(certificate['schema'] == 'razr-r5e-trim-model-conditioned-tree-v5' and
         certificate['frame'] == {k: v for k, v in old_frame.items() if k != 'certificate'}, 'immutable prior V5 certificate header differs')
    sources, boundary_audit = v5.verify_boundary_refinement(proof, old, certificate['boundary_refinement'], trim_records, trim_bindings, limits)
    need(old_frame['source_piece_counts'] == [len(s[0]) for s in sources], 'prior V5 reconstructed complete piece count differs')
    need(old_frame['model_boundary_applied_face_count'] == boundary_audit['applied_faces'] and
         old_frame['model_boundary_applied_inner_wire_count'] == boundary_audit['hole_core_certificates_verified'] and
         old_frame['model_boundary_retained_original_face_count_after_rejection'] == boundary_audit['unapplied_faces_preserved'],
         'prior V5 applied/fallback count differs')
    cells = proof['complete_raw_boundary_slab_cover']['combined']['positive_cells']
    v5.root_coverage(old_frame, certificate, list(range(len(cells))))
    retained = excluded = Q(0)
    split_count = node_count = leaf_count = maximum_depth = 0
    for root, cell in zip(certificate['roots'], cells):
        need(root['root_box_exact'] == cell['box_exact'] and Q(root['root_directed_volume_exact']) == Q(cell['positive_directed_volume_exact']),
             'prior V5 changed an original R4 positive root')
        result = v5.verify_tree(base, root['tree'], intervals(root['root_box_exact']), sources, limits)
        retained += result['kept']
        excluded += result['removed']
        split_count += result['splits']
        node_count += result['nodes']
        leaf_count += result['leaves']
        maximum_depth = max(maximum_depth, result['depth'])
    need(retained == Q(old_frame['retained_leaf_sum_exact']) and excluded == Q(old_frame['excluded_open_leaf_sum_exact']) and
         retained + excluded == Q(old_frame['original_root_sum_exact']) ==
         Q(proof['complete_raw_boundary_slab_cover']['combined']['sum_directed_volume_exact']), 'prior complete forest measure differs')
    selected = min(retained, Q(old['coarse_whole_support_upper_exact_mm3']))
    need(selected == Q(old_frame['trim_model_conditional_upper_exact_mm3']) and
         old_frame['trim_model_conditional_clearance_gate_passed'] == (selected <= TOL), 'prior conditional bound/threshold differs')
    need(selected <= Q(old['conditional_complete_material_intersection_upper_exact_mm3']) and
         old['original_min_volume_plus_TOL_gate_passed'] is True and
         old_frame['original_R4_min_volume_plus_TOL_gate_passed'] == old['original_min_volume_plus_TOL_gate_passed'],
         'original R4 whole-volume sanity gate or inherited upper bound changed')
    need(old_frame['all_closed_cut_planes_and_original_cell_boundaries_retained'] is True and
         split_count == old_frame['exact_splits_this_frame'] and leaf_count == old_frame['total_leaf_count'] and
         maximum_depth == old_frame['maximum_depth_reached'], 'prior V5 closed carriers/tree census differs')
    leaves = retained_leaf_records(certificate)
    need([r['locator'] for r in leaves] == primitive_binding['actual_V5_retained_leaf_locators'], 'primitive projection omitted/reordered retained roots')
    non_tiny = [r for r in leaves if Q(r['root_directed_volume_exact']) > TOL / 100000]
    need([r['locator'] for r in non_tiny] == primitive_binding['actual_V5_non_tiny_retained_leaf_locators'], 'actual non-tiny source selection differs')
    face_sets = [set(), set()]
    for leaf in non_tiny:
        node = leaf['actual_V5_leaf_record']
        need(node['reason'] == 'no_registered_model_boundary_endpoint_inside_cell' and
             old_frame['trim_model_conditional_clearance_gate_passed'] is False, 'actual non-tiny source class differs')
        for unresolved in node['actual_channel_observation']['all_registered_channels_blocked']:
            side = unresolved['material_side']
            piece = certificate['boundary_refinement']['sources'][side]['pieces'][unresolved['blocking_piece_index']]
            need(piece['kind'] == 'face' and piece['replacement'] == 'unchanged', 'registered actual obstruction must be an unchanged original face')
            face_sets[side].add(piece['index'])
    for side in range(2):
        material = tuple(primitive_binding['moving_and_fixed_material_keys'][side])
        need({r['face_index'] for r in primitive_records[material]['candidate_faces']} == face_sets[side],
             'primitive source candidates do not match actual first blockers')
    return leaves, retained, excluded, {'independent_frozen_V5_boundary': boundary_audit,
        'original_R4_roots_reverified': len(cells), 'prior_V5_tree_nodes_reverified': node_count,
        'prior_V5_splits_reverified': split_count, 'prior_V5_leaves_reverified': leaf_count,
        'retained_roots_available': len(leaves), 'non_tiny_retained_roots_available': len(non_tiny),
        'prior_excluded_open_sum_exact': str(excluded), 'prior_retained_sum_exact': str(retained),
        'prior_actual_conditional_gate_unchanged': selected <= TOL, 'V5_producer_rerun': False}


def phase_coverage(producer, contract, baseline, selection):
    phase = contract['expected_phase']
    need(producer['phase'] == phase and phase in ('single_primitive_support_leaf', 'all_primitive_support_frames'), 'registered actual phase differs')
    actual = [(r['case_id'], r['frame']) for r in producer['frames']]
    expected = [tuple(k) for k in contract['expected_case_frames']]
    original = [(r['case_id'], r['frame']) for r in baseline['frames']]
    need(len(actual) == len(set(actual)) and len(expected) == len(set(expected)) and actual == expected, 'missing, duplicated or reordered actual frames')
    if phase == 'single_primitive_support_leaf':
        need(actual == [(selection['case_id'], selection['frame'])] == [('case-028', 1)] and actual[0] in original,
             'exact selected original case/frame required')
    else:
        need(actual == original and len(actual) == 16, 'all original sixteen frames required')


def phase_controls(producer, contract, baseline, selection):
    variants = [('missing-frame', dict(producer, frames=producer['frames'][:-1])),
                ('duplicate-frame', dict(producer, frames=producer['frames'] + [producer['frames'][0]])),
                ('wrong-actual-phase', dict(producer, phase='preflight_primitive_support'))]
    return [rejected(name, lambda changed=changed: phase_coverage(changed, contract, baseline, selection)) for name, changed in variants]


def root_coverage(frame, certificate, leaves):
    expected = [leaf['locator'] for leaf in leaves]
    need(frame['root_base_V5_leaf_locators'] == expected and frame['root_count'] == len(expected) and
         [root['base_V5_leaf_locator'] for root in certificate['roots']] == expected,
         'missing, duplicated or reordered prior retained leaf roots')
    for root, leaf in zip(certificate['roots'], leaves):
        need(root['root_box_exact'] == encbox(leaf['box']) and
             Q(root['root_directed_volume_exact']) == Q(leaf['root_directed_volume_exact']) == measure(leaf['box']),
             'original retained root box or full positive directed volume changed')


def root_controls(frame, certificate, leaves):
    need(leaves, 'root mutation requires an actual retained root')
    variants = [('omitted-original-retained-root', certificate['roots'][:-1]),
                ('duplicated-original-retained-root', certificate['roots'] + [certificate['roots'][0]])]
    return [rejected(name, lambda roots=roots: root_coverage(frame, dict(certificate, roots=roots), leaves))
            for name, roots in variants]


def primitive_controls(boundary, old_boundary, old_frame, records, bindings, limits):
    cylinders, active_d, edges = [], [], []
    for side, source in enumerate(boundary['sources']):
        for ci, face in enumerate(source['face_certificates']):
            if not face['applied']:
                continue
            if face['primitive'] == 'cylinder':
                cylinders.append((side, ci))
                for pi, patch in enumerate(face['patches']):
                    if patch['empty_axis'] is None and any(Q(v) != 0 for v in patch['full_D_support_exact']):
                        active_d.append((side, ci, pi))
            elif any(Q(v) != 0 for v in face['full_D_support_exact']):
                active_d.append((side, ci, None))
        for index, piece in enumerate(source['pieces']):
            if piece['kind'] in ('edge', 'vertex') and piece['replacement'] == 'unchanged':
                edges.append((side, index))
    rows = []
    def run(name, target, edit):
        if target is None:
            rows.append({'name': name, 'status': 'not_applicable', 'actual_rejected': False,
                         'reason': 'No actual eligible source primitive/patch exists in this boundary.'})
            return
        changed = copied(boundary)
        edit(changed, target)
        result = rejected(name, lambda: verify_boundary(changed, old_boundary, old_frame, records, bindings, limits))
        result.update(status='executed', actual_source_target=list(target))
        rows.append(result)
    cylinder = cylinders[0] if cylinders else None
    run('changed-complete-source-angular-endpoint', cylinder, lambda b, t:
        b['sources'][t[0]]['face_certificates'][t[1]]['complete_source_UV_domains_exact'][0].__setitem__(1,
            str(Q(b['sources'][t[0]]['face_certificates'][t[1]]['complete_source_UV_domains_exact'][0][1]) + 1)))
    positive_error = next(((side, ci, pi) for side, ci in cylinders
                           for pi, patch in enumerate(boundary['sources'][side]['face_certificates'][ci]['patches'])
                           if Q(patch['trigonometric_certificate']['degree_47_Lagrange_error_exact']) > 0), None)
    run('discarded-positive-rational-Taylor-remainder', positive_error, lambda b, t:
        b['sources'][t[0]]['face_certificates'][t[1]]['patches'][t[2]]['trigonometric_certificate'].update(
            degree_47_Lagrange_error_exact='0'))
    if positive_error is not None:
        side, ci, pi = positive_error
        rows[-1]['original_positive_Lagrange_error_exact'] = boundary['sources'][side]['face_certificates'][ci]['patches'][pi][
            'trigonometric_certificate']['degree_47_Lagrange_error_exact']
    radial = None
    if cylinder is not None:
        side, ci = cylinder
        pi = next(i for i, p in enumerate(boundary['sources'][side]['face_certificates'][ci]['patches']) if p['empty_axis'] is None)
        radial = (side, ci, pi)
    run('incorrect-original-dual-radial-normal', radial, lambda b, t:
        b['sources'][t[0]]['face_certificates'][t[1]]['patches'][t[2]]['radial_normal_exact'].__setitem__(0,
            str(Q(b['sources'][t[0]]['face_certificates'][t[1]]['patches'][t[2]]['radial_normal_exact'][0]) + 1)))
    run('omitted-closed-angular-patch', cylinder, lambda b, t: b['sources'][t[0]]['face_certificates'][t[1]]['patches'].pop())
    run('omitted-original-edge-or-vertex-piece', edges[0] if edges else None, lambda b, t: b['sources'][t[0]]['pieces'].pop(t[1]))
    def remove_d(b, t):
        face = b['sources'][t[0]]['face_certificates'][t[1]]
        item = face if t[2] is None else face['patches'][t[2]]
        need(any(Q(v) != 0 for v in item['full_D_support_exact']), 'actual nonzero full-D contribution required')
        item['full_D_support_exact'] = ['0', '0']
    run('discarded-actual-full-D-support-contribution', active_d[0] if active_d else None, remove_d)
    need(len(rows) == 6, 'all six primitive mutation applicability results required')
    return rows


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text())
    need(identity(__file__)['sha256'] == contract['verifier_sha256'] == contract['producer_sha256'],
         'registered independent V6 checker source differs')
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = {'schema': 'razr-r5e-independent-primitive-support-verification-v6', 'execution_completed': False,
              'started_utc': datetime.now(timezone.utc).isoformat(), 'contract_sha256': identity(args.contract)['sha256'],
              'verified_producer_report': contract['producer_report'], 'producer_code_imported': False,
              'primitive_producer_or_helper_imported': False, 'V5_producer_rerun': False,
              'conditional_primitive_support_model_only': True, 'conditional_trim_model_only': True,
              'native_primitive_semantics_verified': False, 'native_trim_class_membership_verified': False,
              'inner_wire_hole_semantics_verified_for_native': False, 'original_raw_gate_reclassified': False,
              'native_Common_called': False, 'native_material_semantics_verified': False, 'compiled_error_verified': False,
              'full_continuous_G2': False, 'all_blockers_closed': False, 'frames': [], 'phase_negative_controls': [],
              'root_coverage_negative_controls': [], 'channel_negative_controls': [], 'split_negative_controls': [],
              'leaf_negative_controls': [], 'primitive_source_negative_controls': [], 'real_case_control_applicability': {},
              'mandatory_analytic_controls': None, 'original_V3_raw_passes_unchanged': 4,
              'actual_V5_conditional_passes_preserved': 8, 'primitive_source_bundle': contract['primitive_source_bundle']}

    def save():
        report['seconds'] = time.monotonic() - started
        report['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    try:
        require_scope(contract)
        limits = contract['capacity']
        fixed_limits(limits)
        need(contract['phase'] == ('verify_single' if contract['expected_phase'] == 'single_primitive_support_leaf' else 'verify_all'),
             'verifier phase and expected producer phase differ')
        producer_path = bound(contract['producer_report'])
        producer = json.loads(producer_path.read_text())
        need(producer['schema'] == 'razr-r5e-primitive-support-refinement-v6' and producer['execution_completed'] is True and
             producer['source_and_contract_unchanged'] is True, 'complete actual registered V6 producer required')
        require_scope(producer)
        need(producer['capacity'] == limits and producer['original_TOL_exact'] == str(TOL) and
             producer['no_positive_thin_leaf_discarded'] is True and producer['V5_producer_rerun'] is False and
             producer['actual_V5_conditional_passes_preserved'] == 8 and producer['original_V3_raw_passes_unchanged'] == 4 and
             producer['native_Common_called'] is False and producer['compiled_error_bound_verified'] is False and
             producer['all_blockers_closed'] is False, 'actual producer scope/original threshold differs')
        for field in ('primitive_source_bundle', 'primitive_model_source', 'base_V5_input_bridge',
                      'real_retained_leaf_selection', 'public_input_bridge'):
            need(producer[field] == contract[field], 'producer/verifier source binding differs: ' + field)
            bound(contract[field])
        need(producer['source_report_identity'] == contract['r4_report'], 'original R4 report binding differs')
        bound(contract['primitive_producer_source'])
        controller = json.loads(bound(contract['producer_owned_supervision']).read_text())
        owned_completion(controller, producer, contract['primitive_producer_source']['sha256'], producer_path.parent)
        need(producer['seconds'] <= 600 and producer['peak_RSS_bytes'] <= 805306368, 'actual producer exceeded original process limits')
        archive, prior, prior_verified, prior_pipeline = archived_v5(contract)
        need(producer['actual_base_V5_report'] == archive['all-trim-model-frames/report.json'] and
             producer['actual_base_V5_independent_report'] == archive['verify-all/report.json'], 'actual producer reused different prior experiment')
        report['verified_actual_V5_report'] = archive['all-trim-model-frames/report.json']
        report['verified_actual_V5_independent_report'] = archive['verify-all/report.json']
        report['immutable_V5_input_count'] = len(archive)
        baseline_path = bound(contract['r4_report'])
        baseline = json.loads(baseline_path.read_text())
        need(baseline['execution_completed'] is True and content_equal(prior['source_report_identity'], contract['r4_report']),
             'prior source report differs from original completed R4 report')
        original_keys = [(row['case_id'], row['frame']) for row in baseline['frames']]
        need(len(original_keys) == len(set(original_keys)) == 16 and original_keys == [(r['case_id'], r['frame']) for r in prior['frames']],
             'prior complete original16 frame order differs')
        old_by = {(row['case_id'], row['frame']): row for row in baseline['frames']}
        prior_by = {(row['case_id'], row['frame']): row for row in prior['frames']}
        selection = json.loads(bound(contract['real_retained_leaf_selection']).read_text())
        need(selection['schema'] == 'razr-r5e-actual-v5-retained-leaf-selection-v6' and
             selection['actual_V5_run_id'] == RUN and selection['actual_V5_request_commit'] == HEAD and
             selection['new_geometric_pass_claimed'] is False and selection['original_source_values_changed'] is False and
             (selection['case_id'], selection['frame'], selection['original_R4_root_index'], selection['actual_V5_leaf_node_index']) ==
             ('case-028', 1, 8, 13) and content_equal(selection['actual_V5_report'], archive['all-trim-model-frames/report.json']),
             'exact preregistered actual retained witness source differs')
        phase_coverage(producer, contract, baseline, selection)
        report['expected_phase'] = contract['expected_phase']
        report['expected_case_frames'] = contract['expected_case_frames']
        report['phase_negative_controls'] = phase_controls(producer, contract, baseline, selection)
        public = json.loads(bound(contract['public_input_bridge']).read_text())
        need(public['source_commit'] == ANCHOR and len(public['files']) == 19 and
             all(row['decoded_json_equal'] is True and not row['changed_strings'] for row in public['files']),
             'complete unedited public R4 bridge required')
        public_entries = {row['path']: row for row in public['files']}
        need(len(public_entries) == 19, 'duplicate public R4 input mapping')
        r4_root = baseline_path.resolve().parent.parent
        public_identities = {}
        for name, entry in public_entries.items():
            path = (r4_root / name).resolve()
            need(path.is_relative_to(r4_root), 'public R4 input escapes root')
            public_identities[name] = identity(path)
            need(content_equal(public_identities[name], entry['public_identity']), 'actual public R4 bytes differ')
        need(content_equal(public_identities['support-v4/report.json'], contract['r4_report']) and
             content_equal(prior['public_input_bridge'], contract['public_input_bridge']), 'prior public mapping differs')
        v5 = load_module(contract['base_V5_verifier_source'], 'r5e_v6_frozen_independent_V5_checker')
        base = load_module(contract['base_verifier_source'], 'r5e_v6_frozen_independent_channel_checker')
        trim_contract = {'trim_source_bundle': contract['V5_trim_source_bundle']}
        trim_records, trim_bindings = v5.load_trim_source(trim_contract, baseline, contract['r4_report'])
        records, bindings, census = primitive_sources(contract, baseline, prior, trim_records)
        need(producer['registered_source_primitive_census'] == census, 'actual producer source primitive census differs')
        report['registered_source_primitive_census'] = census
        prior_limits = prior['capacity']
        need(prior_limits['maximum_uv_patches_per_face'] == 1024 and prior_limits['maximum_boundary_pieces_per_material'] == 4096 and
             prior_limits['maximum_splits'] == 4096 and prior_limits['maximum_depth'] == 24 and
             prior_limits['maximum_boundary_box_tests'] == 12000000 and Q(prior_limits['tiny_retained_volume_exact']) == TOL / 100000,
             'actual frozen V5 capacity/policy changed')
        # These are mandatory even when a real case has no exclusion or split.
        report['mandatory_analytic_controls'] = analytic_controls(limits)
        save()
        all_splits = all_nodes = all_leaves = all_excluded = all_roots = all_planes = all_cylinders = all_fallbacks = 0
        max_pieces = max_characters = max_slabs = all_prior_roots = all_prior_non_tiny = 0
        all_reasons = Counter()
        all_primitive_control_targets_seen = False
        for row in producer['frames']:
            require_scope(row)
            key = (row['case_id'], row['frame'])
            old, old_frame, binding = old_by[key], prior_by[key], bindings[key]
            raw_path = 'support-v4/' + old['proof']['path']
            bridge_entry = public_entries[raw_path]
            need(row['original_raw_proof_identity'] == old['proof'] == binding['original_R4_raw_proof_identity'] and
                 bridge_entry['raw_identity'] == {k: old['proof'][k] for k in ('bytes', 'sha256')}, 'original R4 raw source identity differs')
            need(content_equal(old_frame['source_proof'], bridge_entry['public_identity']) and old_frame['original_raw_proof_identity'] == old['proof'],
                 'immutable V5 raw/public proof identity differs')
            with gzip.open(Path(public_identities[raw_path]['path']), 'rt') as stream:
                proof = json.load(stream)
            need(canonical(proof) == bridge_entry['public_canonical_json_sha256'], 'public proof decoded values changed')
            need(row['original_remaining_displacement_box_exact'] == old_frame['original_remaining_displacement_box_exact'] ==
                 binding['original_full_D'] == proof['full_remaining_displacement_box_exact'] == old['full_remaining_displacement_box_exact'],
                 'full original displacement domain changed')
            certificate_name = 'all-trim-model-frames/' + old_frame['certificate']['path']
            prior_id = archive[certificate_name]
            need(content_equal(old_frame['certificate'], prior_id) and row['base_V5_certificate'] == prior_id and
                 binding['actual_V5_certificate'] == dict(prior_id, path=certificate_name), 'exact actual V5 certificate binding differs')
            with gzip.open(Path(prior_id['path']), 'rt') as stream:
                previous_certificate = json.load(stream)
            leaves, old_kept, old_removed, prior_audit = recheck_prior_frame(
                old_frame, old, proof, previous_certificate, v5, base, trim_records, trim_bindings, prior_limits, records, binding)
            all_prior_roots += len(leaves)
            all_prior_non_tiny += prior_audit['non_tiny_retained_roots_available']
            if contract['expected_phase'] == 'single_primitive_support_leaf':
                locator = [selection['original_R4_root_index'], selection['actual_V5_leaf_node_index']]
                leaves = [leaf for leaf in leaves if leaf['locator'] == locator]
                need(len(leaves) == 1 and encbox(leaves[0]['box']) == selection['leaf_box_exact'] and
                     leaves[0]['actual_V5_leaf_record'] == selection['actual_V5_leaf_record'] and
                     leaves[0]['root_directed_volume_exact'] == selection['positive_directed_volume_exact'] and
                     content_equal(selection['actual_V5_certificate'], prior_id), 'registered actual retained leaf changed')
                need(selection['original_full_D'] == binding['original_full_D'] and selection['pair'] == old_frame['pair'] and
                     selection['actual_V5_original_root_record'] == next(root for root in previous_certificate['roots']
                         if root['original_cell_index'] == locator[0]), 'selected original root, pair or full D changed')
            need(row['pair'] == old_frame['pair'] and row['primitive_source_bundle'] == contract['primitive_source_bundle'] and
                 row['base_V5_frame_conditional_upper_exact_mm3'] == old_frame['trim_model_conditional_upper_exact_mm3'] and
                 Q(row['base_V5_retained_leaf_sum_exact']) == old_kept and Q(row['base_V5_excluded_open_leaf_sum_exact']) == old_removed,
                 'actual frame original V5 measure or source scope differs')
            with gzip.open(bound(row['certificate'], producer_path.parent), 'rt') as stream:
                certificate = json.load(stream)
            need(certificate['schema'] == 'razr-r5e-primitive-support-tree-v6' and
                 certificate['frame'] == {k: v for k, v in row.items() if k != 'certificate'} and
                 certificate['V5_producer_rerun'] is False and Q(certificate['actual_V5_excluded_open_sum_preserved_exact']) == old_removed,
                 'new certificate header or unchanged old exclusions differ')
            sources, boundary_audit = verify_boundary(certificate['boundary_refinement'], previous_certificate['boundary_refinement'],
                                                       old_frame, records, bindings, limits)
            need(row['source_piece_counts'] == [len(source['pieces']) for source in sources] and
                 row['applied_plane_face_count'] == boundary_audit['planes'] and
                 row['applied_cylinder_face_count'] == boundary_audit['cylinders'] and
                 row['retained_original_face_count_after_rejection'] == boundary_audit['fallbacks'], 'complete frame boundary census differs')
            all_planes += boundary_audit['planes']
            all_cylinders += boundary_audit['cylinders']
            all_fallbacks += boundary_audit['fallbacks']
            if not all_primitive_control_targets_seen and boundary_audit['cylinders']:
                report['primitive_source_negative_controls'] = primitive_controls(
                    certificate['boundary_refinement'], previous_certificate['boundary_refinement'], old_frame, records, bindings, limits)
                all_primitive_control_targets_seen = True
            for source in sources:
                max_pieces = max(max_pieces, len(source['pieces']))
                for piece in source['pieces']:
                    max_slabs = max(max_slabs, len(piece['additional_slabs']))
                    values = [v for interval in piece['box'] for v in interval]
                    for normal, support in piece['additional_slabs']:
                        values.extend(normal)
                        values.extend(support)
                    max_characters = max(max_characters, *(len(str(value)) for value in values))
            root_coverage(row, certificate, leaves)
            if not report['root_coverage_negative_controls'] and leaves:
                report['root_coverage_negative_controls'] = root_controls(row, certificate, leaves)
            kept = removed = Q(0)
            splits = nodes = leaf_count = excluded_count = depth = pieces_checked = nonaxis = 0
            for root in certificate['roots']:
                cell, tree = intervals(root['root_box_exact']), root['tree']
                stats = verify_tree(tree, cell, sources, limits)
                kept += stats['retained']
                removed += stats['excluded']
                splits += stats['splits']
                nodes += stats['nodes']
                leaf_count += stats['leaves']
                excluded_count += stats['excluded_count']
                depth = max(depth, stats['depth'])
                pieces_checked += stats['pieces_checked']
                nonaxis += stats['nonaxis_checked']
                all_reasons.update(stats['reasons'])
                if not report['channel_negative_controls'] and stats['sample_exclusion']:
                    good, target = stats['sample_exclusion']
                    report['channel_negative_controls'] = channel_controls(good, target, sources)
                if not report['split_negative_controls'] and stats['sample_split']:
                    report['split_negative_controls'] = split_controls(tree, cell, sources, limits, stats)
                if not report['leaf_negative_controls']:
                    report['leaf_negative_controls'] = leaf_controls(tree, cell, sources, limits, stats)
            root_sum = sum((Q(leaf['root_directed_volume_exact']) for leaf in leaves), Q(0))
            need(kept + removed == root_sum == Q(row['new_root_sum_exact']) and
                 kept == Q(row['retained_leaf_sum_exact']) and removed == Q(row['newly_excluded_open_leaf_sum_exact']),
                 'all new retained roots and exact directed measure must be conserved')
            selected = kept
            if contract['expected_phase'] == 'all_primitive_support_frames':
                need(kept + removed == old_kept, 'new exclusions must be taken from old retained sum, never the selected min bound')
                selected = min(kept, Q(old['coarse_whole_support_upper_exact_mm3']))
                need(selected <= Q(old_frame['trim_model_conditional_upper_exact_mm3']), 'new conditional upper bound exceeded the old bound')
            need(Q(row['primitive_support_model_conditional_upper_exact_mm3']) == selected and
                 row['primitive_support_model_conditional_upper_mm3'] == float(selected) and
                 row['primitive_support_model_conditional_clearance_gate_passed'] == (selected <= TOL),
                 'conditional primitive bound or original float64 threshold changed')
            need(row['all_V5_and_new_closed_carriers_retained'] is True and row['exact_splits_this_frame'] == splits and
                 row['total_leaf_count'] == leaf_count and row['maximum_depth_reached'] == depth,
                 'frame complete tree census or closed carriers differ')
            all_splits += splits
            all_nodes += nodes
            all_leaves += leaf_count
            all_excluded += excluded_count
            all_roots += len(leaves)
            report['frames'].append({'case_id': key[0], 'frame': key[1], 'independently_rechecked_actual_V5': prior_audit,
                'new_retained_roots_verified': len(leaves), 'new_tree_nodes_verified': nodes, 'new_splits_verified': splits,
                'new_all_positive_leaves_verified': leaf_count, 'new_excluded_leaf_count': excluded_count,
                'new_complete_piece_separations_verified': pieces_checked, 'new_nonaxis_separations_verified': nonaxis,
                'new_retained_leaf_sum_exact': str(kept), 'new_excluded_open_sum_exact': str(removed),
                'primitive_support_model_conditional_upper_exact_mm3': str(selected),
                'primitive_support_model_conditional_clearance_gate_passed': selected <= TOL,
                'independent_primitive_support_reconstruction': boundary_audit,
                'conditional_primitive_support_model_only': True, 'native_primitive_semantics_verified': False,
                'original_raw_gate_reclassified': False, 'V5_producer_rerun': False})
            save()
            need(report['seconds'] <= 600 and report['peak_RSS_bytes'] <= 805306368, 'independent check exceeded original process budget')
        counters = producer['counters']
        need(all(type(v) is int and v >= 0 for v in counters.values()), 'nonnegative exact actual search counters required')
        need(counters['splits'] == all_splits <= 4096 and counters['tree_nodes_visited'] == all_nodes and
             counters['boundary_box_tests'] <= 12000000 and counters['support_inequality_tests'] <= 12000000,
             'actual global split/tree/predicate budgets differ')
        need(sum(row['exact_piece_tests_this_frame'] for row in producer['frames']) == counters['boundary_box_tests'] and
             sum(row['exact_support_inequality_tests_this_frame'] for row in producer['frames']) == counters['support_inequality_tests'],
             'actual per-frame predicate accounting differs')
        if all_reasons['global_predicate_budget_retained']:
            need(counters['boundary_box_tests'] == 12000000 or counters['support_inequality_tests'] == 12000000,
                 'reported predicate-budget stop did not reach a registered cap')
        if all_reasons['global_split_limit_retained']:
            need(all_splits == 4096, 'reported global split stop did not reach the registered cap')
        need(producer['total_actual_V5_retained_roots'] == all_roots and producer['complete_phase_maximum_tree_nodes'] == all_roots + 8192 and
             producer['complete_phase_maximum_leaves'] == all_roots + 4096 and all_nodes <= all_roots + 8192 and all_leaves <= all_roots + 4096,
             'bounded complete retained forest capacity differs')
        need(producer['maximum_complete_piece_count_per_material'] == max_pieces <= 4096 and
             producer['maximum_additional_slabs_per_piece'] == max_slabs <= 1 and
             producer['maximum_exact_coordinate_character_count'] == max_characters, 'actual complete source capacity census differs')
        need(producer['applied_plane_face_occurrences'] == all_planes and producer['applied_cylinder_face_occurrences'] == all_cylinders and
             producer['retained_original_face_occurrences_after_rejection'] == all_fallbacks and
             producer['all_frame_capacity_observations_completed'] is True, 'actual full-phase primitive/fallback census differs')
        if contract['expected_phase'] == 'all_primitive_support_frames':
            need(all_roots == all_prior_roots == 1537 and all_prior_non_tiny == 44, 'complete actual1537 retained /44 non-tiny roots required')
        for label, rows, eligible, required, absent in [
            ('channel_mutations', report['channel_negative_controls'], all_excluded, 4, 'No actual new excluded leaf exists.'),
            ('split_mutations', report['split_negative_controls'], all_splits, 5, 'No actual new split exists.'),
            ('leaf_mutations', report['leaf_negative_controls'], all_leaves, 2, 'No actual positive leaf exists.')]:
            report['real_case_control_applicability'][label] = applicability(rows, eligible, required, absent)
        controls = report['primitive_source_negative_controls']
        need((all_cylinders and len(controls) == 6) or (not all_cylinders and not controls), 'actual primitive control applicability differs')
        report['real_case_control_applicability']['primitive_source_mutations'] = {
            'status': 'executed_with_individual_applicability' if all_cylinders else 'not_applicable',
            'actual_applied_cylinder_count': all_cylinders, 'actual_rejected_controls': sum(r['actual_rejected'] is True for r in controls),
            'individual_absent_targets_are_not_passes': True,
            'reason': None if all_cylinders else 'No actual applied cylinder source exists.'}
        need(all_leaves > 0 and report['mandatory_analytic_controls']['mandatory_controls_completed'] is True and
             len(report['phase_negative_controls']) == 3 and len(report['root_coverage_negative_controls']) == 2,
             'mandatory analytic/full-phase/root controls incomplete')
        passes = sum(frame['primitive_support_model_conditional_clearance_gate_passed'] for frame in report['frames'])
        need(passes == producer['primitive_support_model_conditional_clearance_passes'], 'producer/independent conditional model gates differ')
        report.update(primitive_support_model_conditional_clearance_passes=passes, total_new_tree_nodes_verified=all_nodes,
                      total_new_splits_verified=all_splits, total_new_positive_leaves_verified=all_leaves,
                      total_actual_new_excluded_leaves_verified=all_excluded, total_actual_retained_roots_verified=all_roots,
                      applied_plane_occurrences_verified=all_planes, applied_cylinder_occurrences_verified=all_cylinders,
                      retained_original_face_occurrences_verified=all_fallbacks, actual_retention_reason_counts=dict(all_reasons))
        source_fields = ('primitive_producer_source', 'primitive_model_source', 'primitive_source_bundle', 'base_V5_input_bridge',
                         'base_V5_source_lock', 'base_V5_verifier_source', 'V5_trim_source_bundle', 'base_verifier_source',
                         'base_channel_source', 'r4_report', 'r4_independent_report', 'r4_stationary_diagnostic', 'public_input_bridge',
                         'real_retained_leaf_selection', 'method', 'producer_report', 'producer_owned_supervision', 'single_verifier_source')
        for field in source_fields:
            bound(contract[field])
        for value in list(archive.values()) + list(public_identities.values()):
            bound(value)
        need(identity(__file__)['sha256'] == contract['verifier_sha256'] == contract['single_verifier_source']['sha256'] and
             identity(args.contract)['sha256'] == report['contract_sha256'], 'independent source or contract changed during verification')
        report['all_checked_source_contract_and_archived_inputs_unchanged'] = True
        report['execution_completed'] = True
    except BaseException as exc:
        report['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
        raise
    finally:
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        save()
        print(json.dumps({k: report.get(k) for k in ('execution_completed', 'primitive_support_model_conditional_clearance_passes',
                         'total_new_tree_nodes_verified', 'seconds', 'peak_RSS_bytes', 'failure')}), flush=True)


if __name__ == '__main__':
    main()
