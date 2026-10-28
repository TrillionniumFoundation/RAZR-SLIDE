"""Cross-author exact readback of closed local V6 evidence, without model imports.

The inherited V5 proof chain has already been independently audited. This
program consumes those exact certificate bytes and independently checks the
new primitive support, new partitions, execution receipts and scope.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction as Q
from functools import lru_cache
import gzip
import hashlib
import json
from math import factorial
from pathlib import Path
import resource
import signal
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ACTUAL = ROOT / 'r5-local-v6/attempt-1'
SNAP = ROOT / 'r5-local-v6/input-snapshot-v1'
OLD = SNAP / 'base-v5'
SOURCE = SNAP / 'source'
R4 = SNAP / 'r4'
TOL = Q(1e-7)
TINY = TOL / 100000
LOCK = '5cf2c18e7971912949e7e7167451cf547e291be421f205d78ef668fd7ab5b499'
IDENTITY = [['1', '0', '0', '0'], ['0', '1', '0', '0'], ['0', '0', '1', '0']]
GATES = {'wall_seconds': 600, 'RSS_limit_bytes': 805306368, 'shared_ceiling_bytes': 7301444403,
         'disk_floor_bytes': 104857600, 'maximum_output_bytes': 41943040, 'metadata_margin_bytes': 4194304}
SEQUENCE = [('single-primitive-support-leaf', 'single_primitive_support_leaf'), ('verify-single', 'verify_single'),
            ('preflight-primitive-support', 'preflight_primitive_support'), ('all-primitive-support-frames', 'all_primitive_support_frames'),
            ('verify-all', 'verify_all')]
FRAME_KEYS = [(case, frame) for case in ['case-001', 'case-006', 'case-028', 'case-037', 'case-054', 'case-063', 'case-072', 'case-089'] for frame in (1, 2)]
WATCHED = {}
DECODED = 0
ASSERTIONS = 0
REPORT = {'schema': 'razr-r5e-v6-independent-actual-local-readback-v2', 'audit_completed': False,
          'producer_helper_or_checker_imported': False, 'native_operations_executed': 0,
          'original_R4_proof_decodes': 0, 'original_native_inventory_decodes': 0,
          'V5_producer_rerun': False, 'full_channel_search_replayed': False,
          'execution_kind': 'independent_exact_readback_of_actual_local_run',
          'GitHub_workflow_execution_claimed': False,
          'conditional_primitive_support_model_only': True, 'conditional_trim_model_only': True,
          'native_primitive_semantics_verified': False, 'native_trim_class_membership_verified': False,
          'inner_wire_hole_semantics_verified_for_native': False, 'original_raw_gate_reclassified': False,
          'full_continuous_G2': False, 'all_blockers_closed': False,
          'frames': [], 'independent_actual_copy_rejections': []}


def need(value, message):
    global ASSERTIONS
    ASSERTIONS += 1
    if not value:
        raise ValueError(message)


def ident(path):
    path = Path(path).resolve()
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while part := stream.read(1 << 20):
            value.update(part)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': value.hexdigest()}


def watch(path):
    result = ident(path)
    previous = WATCHED.setdefault(result['path'], result)
    need(result == previous, 'watched bytes changed during audit')
    return result


def same(left, right):
    return all(left[k] == right[k] for k in ('bytes', 'sha256'))


def bound(record, path=None):
    result = watch(path if path is not None else record['path'])
    need(same(result, record), 'bound file identity differs: ' + result['path'])
    return result


def read_json(path):
    global DECODED
    item = watch(path)
    need(item['bytes'] <= 67108864, 'plain JSON input exceeds audit file budget')
    data = Path(path).read_bytes()
    DECODED += len(data)
    need(DECODED <= 536870912, 'total decoded JSON exceeds audit budget')
    return json.loads(data)


def read_gzip(path):
    global DECODED
    item = watch(path)
    need(item['bytes'] <= 41943040, 'compressed JSON exceeds audit input budget')
    with gzip.open(path, 'rb') as stream:
        data = stream.read(67108865)
    need(len(data) <= 67108864, 'decoded JSON exceeds audit input budget')
    DECODED += len(data)
    need(DECODED <= 536870912, 'total decoded JSON exceeds audit budget')
    return json.loads(data)


def rat(value):
    return Q(value['exact']) if isinstance(value, dict) else Q(value)


def vector(values):
    return tuple(rat(v) for v in values)


def box(values):
    answer = tuple(tuple(map(Q, part)) for part in values)
    need(len(answer) == 3 and all(len(part) == 2 and part[0] <= part[1] for part in answer), 'closed ordered three-dimensional box required')
    return answer


def enc(values):
    return [str(v) for v in values]


def encbox(values):
    return [enc(part) for part in values]


def volume(cell):
    value = Q(1)
    for lo, hi in cell:
        need(lo < hi, 'positive directed cell required')
        value *= hi - lo
    return value


def scalar(left, right):
    return sum((x * y for x, y in zip(left, right)), Q(0))


def cross(left, right):
    return (left[1]*right[2]-left[2]*right[1], left[2]*right[0]-left[0]*right[2], left[0]*right[1]-left[1]*right[0])


def scaled(value, interval):
    endpoints = [value * endpoint for endpoint in interval]
    return min(endpoints), max(endpoints)


def plus(*intervals):
    return tuple(sum((part[i] for part in intervals), Q(0)) for i in (0, 1))


def projection(normal, ranges):
    return plus(*(scaled(value, interval) for value, interval in zip(normal, ranges)))


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def scope(value):
    for name in ('native_primitive_semantics_verified', 'native_trim_class_membership_verified', 'original_raw_gate_reclassified', 'full_continuous_G2'):
        need(value[name] is False, 'conditional scope upgraded: ' + name)
    need(value['conditional_primitive_support_model_only'] is True and value['conditional_trim_model_only'] is True, 'conditional primitive/trim scope omitted')


@lru_cache(maxsize=2048)
def angular(domain):
    a, b = domain
    centre = Q(((a+b)*32768).__floor__(), 65536)
    need(abs(centre) <= 8, 'registered Taylor centre range exceeded')
    # Direct finite-power sums: neither producer recurrence nor checker Horner.
    sine = sum((Q((-1)**k, factorial(2*k+1)) * centre**(2*k+1) for k in range(24)), Q(0))
    cosine = sum((Q((-1)**k, factorial(2*k)) * centre**(2*k) for k in range(24)), Q(0))
    error = abs(centre)**48 / factorial(48)
    record = {'U_interval_exact': enc(domain), 'dyadic_centre_exact': str(centre),
              'actual_offset_interval_exact': enc((a-centre, b-centre)),
              'Maclaurin_sin_exact': str(sine), 'Maclaurin_cos_exact': str(cosine),
              'degree_47_Lagrange_error_exact': str(error), 'Taylor_term_count': 24,
              'centre_grid_denominator': 65536, 'original_angular_endpoints_replaced': False}
    return record, sine, cosine, error, (a-centre, b-centre)


def trig_range(a, b, expansion):
    unused, sine, cosine, error, offset = expansion
    constant = plus(scaled(a, (cosine-error, cosine+error)), scaled(b, (sine-error, sine+error)))
    derivative = plus(scaled(-a, (sine-error, sine+error)), scaled(b, (cosine-error, cosine+error)))
    products = [x*y for x in derivative for y in offset]
    remainder = (abs(a)+abs(b)) * max(abs(x) for x in offset)**2 / 2
    return constant[0]+min(products)-remainder, constant[1]+max(products)+remainder


def full_domains(face):
    surface = face['local_surface']
    result = [tuple(map(rat, surface[name])) for name in ('U_interval', 'V_interval')]
    need(all(lo <= hi for lo, hi in result) and face['wires'], 'complete original cylinder domain required')
    for wire in face['wires']:
        need(wire['location']['matrix_3x4_exact'] == IDENTITY and wire['edge_occurrences'], 'complete original identity wire required')
        for occurrence in wire['edge_occurrences']:
            need(occurrence['location']['matrix_3x4_exact'] == IDENTITY and occurrence['edge_index'] is not None, 'original occurrence placement or mapping differs')
            curve = occurrence['pcurve']
            need(curve['type'] == 'GeomAbs_CurveType.GeomAbs_Line', 'unsupported pcurve must retain its old face')
            origin, direction = vector(curve['origin_exact']), vector(curve['direction_exact'])
            first, last = rat(curve['first_parameter']), rat(curve['last_parameter'])
            need(len(origin) == len(direction) == 2 and first <= last, 'complete original pcurve interval required')
            for axis in range(2):
                coordinates = [origin[axis]+direction[axis]*t for t in (first, last)]
                result[axis] = min(result[axis][0], *coordinates), max(result[axis][1], *coordinates)
    return result


def checked_face(candidate, stationary, shift, saved):
    face = candidate['complete_original_face']
    need(canonical(face) == candidate['complete_original_face_canonical_sha256'], 'complete original face hash differs')
    need(face['index'] == candidate['face_index'] == saved['face_index'], 'original face index differs')
    need(face['location']['matrix_3x4_exact'] == IDENTITY, 'nonidentity source face unsupported')
    for wire in face['wires']:
        need(wire['location']['matrix_3x4_exact'] == IDENTITY, 'wire placement differs')
        for occurrence in wire['edge_occurrences']:
            need(occurrence['location']['matrix_3x4_exact'] == IDENTITY and occurrence['edge_index'] is not None, 'occurrence placement/mapping differs')
    surface = face['local_surface']
    origin, x, y = [vector(surface[key]) for key in ('origin_exact', 'X_exact', 'Y_exact')]
    need(all(len(v) == 3 for v in (origin, x, y)), 'three-dimensional exact source primitive required')
    need(saved['stationary_original_box_exact'] == encbox(stationary) and saved['original_pcurve_values_changed'] is False and
         saved['native_primitive_semantics_verified'] is False, 'original stationary carrier or model scope changed')
    if surface['type'] == 'GeomAbs_SurfaceType.GeomAbs_Plane':
        normal = cross(x, y)
        need(any(normal) and scalar(normal, x) == scalar(normal, y) == 0, 'exact plane normal fails source equations')
        centre = scalar(normal, origin)
        d_support = projection(normal, shift)
        support = plus((centre, centre), d_support)
        item = {'parameter_patch_index': None, 'box_exact': encbox([plus(stationary[k], shift[k]) for k in range(3)]),
                'additional_slabs': [{'normal_exact': enc(normal), 'bounds_exact': enc(support), 'source': 'exact_affine_plane'}]}
        need(saved['primitive'] == 'plane' and saved['plane_normal_exact'] == enc(normal) and saved['plane_stationary_support_exact'] == str(centre) and
             saved['full_D_support_exact'] == enc(d_support) and saved['pieces'] == [item], 'exact source plane/slab differs')
        return [item]
    need(surface['type'] == 'GeomAbs_SurfaceType.GeomAbs_Cylinder' and saved['primitive'] == 'cylinder', 'unregistered primitive applied')
    z, radius = vector(surface['axis_exact']), rat(surface['radius'])
    determinant = scalar(x, cross(y, z))
    domains = full_domains(face)
    u, v = domains
    need(len(z) == 3 and radius > 0 and determinant != 0 and u[0] < u[1], 'nondegenerate positive cylinder required')
    need(saved['complete_source_UV_domains_exact'] == encbox(domains) and saved['basis_determinant_exact'] == str(determinant) and
         saved['angular_patch_count'] == 64 and len(saved['patches']) == 64 and saved['closed_angular_seams_and_endpoints_retained'] is True,
         'complete closed cylinder domain or patch count differs')
    pieces = []
    for index, patch in enumerate(saved['patches']):
        interval = (u[0] + (u[1]-u[0])*Q(index,64), u[0] + (u[1]-u[0])*Q(index+1,64))
        expansion = angular(interval)
        need(patch['parameter_patch_index'] == index and patch['trigonometric_certificate'] == expansion[0] and
             patch['closed_parameter_endpoints_retained'] is True, 'closed source interval or exact Taylor enclosure differs')
        mapped = [plus((origin[k], origin[k]), scaled(z[k], v), scaled(radius, trig_range(x[k], y[k], expansion))) for k in range(3)]
        clipped = [(max(mapped[k][0], stationary[k][0]), min(mapped[k][1], stationary[k][1])) for k in range(3)]
        empty = next((k for k, (lo, hi) in enumerate(clipped) if lo > hi), None)
        need(patch['stationary_unclipped_box_exact'] == encbox(mapped) and patch['stationary_clipped_box_exact'] == encbox(clipped) and
             patch['empty_axis'] == empty, 'primitive patch enclosure or strict empty intersection differs')
        if empty is not None:
            continue
        normal = vector(patch['radial_normal_exact'])
        sine, cosine = expansion[1], expansion[2]
        need(any(normal) and scalar(normal, x) == cosine and scalar(normal, y) == sine and scalar(normal, z) == 0,
             'radial dual normal fails unique exact source equations')
        centre = scalar(normal, origin)
        support = plus((centre, centre), scaled(radius, trig_range(cosine, sine, expansion)))
        d_support = projection(normal, shift)
        swept_support = plus(support, d_support)
        swept = [plus(clipped[k], shift[k]) for k in range(3)]
        need(patch['radial_dual_coordinates_exact'] == enc((cosine, sine, Q(0))) and
             patch['radial_stationary_support_exact'] == enc(support) and patch['full_D_support_exact'] == enc(d_support) and
             patch['swept_box_exact'] == encbox(swept) and patch['radial_swept_support_exact'] == enc(swept_support),
             'radial support or complete displacement differs')
        pieces.append({'parameter_patch_index': index, 'box_exact': encbox(swept),
                       'additional_slabs': [{'normal_exact': enc(normal), 'bounds_exact': enc(swept_support), 'source': 'exact_cylinder_patch_radial_support'}]})
    need(pieces and saved['pieces'] == pieces, 'complete nonempty closed patch carrier set differs')
    return pieces


def boundary_readback(new, old, old_frame, records, bindings):
    need(new['schema'] == 'razr-r5e-source-primitive-boundary-refinement-v6' and
         new['conditional_primitive_support_model_only'] is True and new['native_primitive_semantics_verified'] is False and
         new['native_trim_class_membership_verified'] is False and new['original_raw_gate_reclassified'] is False,
         'conditional source boundary scope differs')
    key = old_frame['case_id'], old_frame['frame']
    binding = bindings[key]
    need(binding['original_full_D'] == old_frame['original_remaining_displacement_box_exact'], 'source full D changed')
    need(len(new['sources']) == len(old['sources']) == 2, 'whole material pair count differs')
    models = []
    planes = cylinders = fallbacks = patches = 0
    for side, (source, previous) in enumerate(zip(new['sources'], old['sources'])):
        material_key = tuple(previous['material_key'])
        need(source['material_key'] == previous['material_key'] == binding['moving_and_fixed_material_keys'][side] and
             source['known_whole_exact'] == previous['whole_exact'] and source['base_V5_piece_count'] == len(previous['pieces']),
             'whole material exterior anchor or original piece census differs')
        candidates = {row['face_index']: row for row in records[material_key]['candidate_faces']}
        certificates = source['face_certificates']
        by_base = {row['base_V5_piece_index']: (i, row) for i, row in enumerate(certificates)}
        need(len(by_base) == len(certificates) == len(candidates), 'duplicate or missing primitive face certificate')
        expected = []
        seen = set()
        shift = box(binding['original_full_D']) if side == 0 else ((Q(0), Q(0)),)*3
        for index, piece in enumerate(previous['pieces']):
            prefix = {'base_V5_piece_index': index, 'original_piece_index': piece['original_piece_index'],
                      'kind': piece['kind'], 'index': piece['index'], 'preserved_V5_replacement': piece['replacement']}
            candidate = candidates.get(piece['index']) if piece['kind'] == 'face' else None
            if candidate is None:
                need(index not in by_base, 'noncandidate piece has a primitive certificate')
                expected.append(dict(prefix, replacement='unchanged', box_exact=piece['box_exact'], additional_slabs=[]))
                continue
            need(piece['replacement'] == 'unchanged' and piece['index'] not in seen and index in by_base, 'candidate must cover one original unchanged V5 face')
            seen.add(piece['index'])
            ci, certificate = by_base[index]
            need(certificate['face_index'] == candidate['face_index'] and certificate['source_face_canonical_sha256'] == candidate['complete_original_face_canonical_sha256'], 'primitive source identity differs')
            if not certificate['applied']:
                need(bool(certificate['retained_original_face_reason']), 'fallback must preserve its stated reason')
                fallbacks += 1
                expected.append(dict(prefix, replacement='unchanged', box_exact=piece['box_exact'], additional_slabs=[]))
                continue
            old_box = box(piece['box_exact'])
            stationary = [(old_box[k][0]-shift[k][0], old_box[k][1]-shift[k][1]) for k in range(3)]
            children = checked_face(candidate, stationary, shift, certificate)
            if certificate['primitive'] == 'plane':
                planes += 1
            else:
                cylinders += 1
                patches += len(certificate['patches'])
            expected.extend(dict(prefix, replacement='plane_slab' if certificate['primitive'] == 'plane' else 'cylinder_patch', face_certificate_index=ci, **child) for child in children)
        need(seen == set(candidates) and source['pieces'] == expected and len(expected) <= 4096, 'complete original piece lineage or registered material cap differs')
        pieces = []
        for item in expected:
            slabs = [(vector(row['normal_exact']), tuple(map(Q, row['bounds_exact']))) for row in item['additional_slabs']]
            need(len(slabs) <= 1 and all(any(n) and a <= b for n, (a, b) in slabs), 'valid registered closed support slab required')
            pieces.append({'box': box(item['box_exact']), 'slabs': slabs,
                           'radial': bool(item['additional_slabs'] and item['additional_slabs'][0]['source'] == 'exact_cylinder_patch_radial_support')})
        models.append({'whole': box(source['known_whole_exact']), 'pieces': pieces})
    need(new['applied_plane_count'] == planes and new['applied_cylinder_count'] == cylinders and new['retained_original_faces_after_rejection'] == fallbacks, 'primitive applied/fallback census differs')
    return models, {'planes': planes, 'cylinders': cylinders, 'fallbacks': fallbacks, 'closed_angular_patches': patches}


def channel(cell, whole, axis, end):
    result = list(cell)
    result[axis] = (min(whole[axis][0]-1, cell[axis][0]-1), cell[axis][1]) if end == 0 else (cell[axis][0], max(whole[axis][1]+1, cell[axis][1]+1))
    return tuple(result)


def separator(piece, target, code):
    need(type(code) is str and len(code) == 1 and code in '01234567', 'unknown separator code')
    number = int(code)
    if number < 6:
        axis, end = divmod(number, 2)
        return piece['box'][axis][1] <= target[axis][0] if end == 0 else piece['box'][axis][0] >= target[axis][1]
    need(len(piece['slabs']) == 1, 'nonaxis separator needs its original slab')
    normal, support = piece['slabs'][0]
    image = projection(normal, target)
    need(any(normal) and image[0] < image[1], 'positive open box must have nonempty open projected image')
    return support[1] <= image[0] if number == 6 else support[0] >= image[1]


def exclusion(item, cell, models):
    need(item['excluded_open_interior'] is True and item['closed_cell_boundary_retained_as_zero_volume_carrier'] is True and
         item['whole_closed_cell_disjoint_claimed'] is False, 'exclusion may claim only open interior')
    side, axis, end = item['material_side'], item['axis'], item['end']
    need(type(side) is int and side in (0, 1) and type(axis) is int and axis in (0, 1, 2) and type(end) is int and end in (0, 1), 'invalid channel indices')
    source = models[side]
    target = box(item['open_channel_exact'])
    need(target == channel(cell, source['whole'], axis, end) and all(a < b for a, b in target), 'channel footprint or known-exterior extension differs')
    codes = item['complete_piece_separation_codes']
    need(type(codes) is str and len(codes) == len(source['pieces']) == item['boundary_piece_count'], 'complete boundary code census differs')
    for piece, code in zip(source['pieces'], codes):
        need(separator(piece, target, code), 'saved boundary separation does not hold')
    nonaxis = sum(code in '67' for code in codes)
    need(item['nonaxis_separation_code_count'] == nonaxis, 'nonaxis separator census differs')
    return len(codes), nonaxis


def unresolved(item, cell, models, partial=False):
    need(item['excluded_open_interior'] is False and item['actual_material_interference_claimed'] is False, 'unresolved carrier is not a collision proof')
    rows = item['completed_unresolved_channels'] if partial else item['all_registered_channels_unresolved']
    expected = [(side, axis, end) for side in range(2) for axis in range(3) for end in (0, 1)]
    need([(r['material_side'], r['axis'], r['end']) for r in rows] == expected[:len(rows)] and
         (len(rows) <= 12 if partial else len(rows) == 12), 'registered unresolved channel order or coverage differs')
    for row in rows:
        side, axis, end, index = row['material_side'], row['axis'], row['end'], row['unresolved_piece_index']
        need(type(index) is int and 0 <= index < len(models[side]['pieces']), 'invalid blocking piece index')
        piece = models[side]['pieces'][index]
        target = channel(cell, models[side]['whole'], axis, end)
        need(not any(separator(piece, target, str(i)) for i in range(8 if piece['slabs'] else 6)), 'declared blocking piece has an available separator')
    return len(rows)


def registered_cut(cell, models, observation):
    unresolved(observation, cell, models)
    endpoint_candidates = {}
    variations = []
    for row in observation['all_registered_channels_unresolved']:
        side, index = row['material_side'], row['unresolved_piece_index']
        piece = models[side]['pieces'][index]
        for axis in range(3):
            for end, point in enumerate(piece['box'][axis]):
                if cell[axis][0] < point < cell[axis][1]:
                    endpoint_candidates.setdefault((axis, point), {'kind': 'model_boundary_endpoint', 'material_side': side, 'piece_index': index, 'axis': axis, 'endpoint': end})
        variations.extend((piece['radial'], normal) for normal, unused in piece['slabs'])
    if endpoint_candidates:
        axis, point = sorted(endpoint_candidates, key=lambda item: (min(item[1]-cell[item[0]][0], cell[item[0]][1]-item[1])/(cell[item[0]][1]-cell[item[0]][0]), item[0], item[1]))[0]
        return axis, point, endpoint_candidates[(axis, point)]
    if any(radial for radial, unused in variations):
        variations = [row for row in variations if row[0]]
        rule = 'largest_registered_radial_slab_variation'
    elif variations:
        rule = 'largest_registered_slab_variation'
    else:
        rule = 'longest_cell_interval'
    weights = [max(abs(normal[k])*(cell[k][1]-cell[k][0]) for unused, normal in variations) for k in range(3)] if variations else [b-a for a, b in cell]
    axis = weights.index(max(weights))
    return axis, sum(cell[axis], Q(0))/2, {'kind': 'registered_midpoint', 'axis': axis, 'selection_rule': rule}


def tree_readback(tree, root, models):
    nodes = tree['nodes']
    need(nodes and all(type(n) is dict and n['id'] == i and type(n['id']) is int for i, n in enumerate(nodes)), 'complete ordered tree nodes required')
    stack = [(0, root, 0)]
    visited = set()
    kept = removed = Q(0)
    counts = Counter()
    reasons = Counter()
    depth_max = 0
    samples = {}
    while stack:
        index, cell, depth = stack.pop()
        need(type(index) is int and 0 <= index < len(nodes) and index not in visited and depth <= 24, 'cyclic, missing, duplicate, or over-depth node')
        visited.add(index)
        node = nodes[index]
        value = volume(cell)
        depth_max = max(depth_max, depth)
        if node['kind'] == 'split':
            need(value > TINY, 'tiny leaf must remain retained')
            axis, cut, witness = registered_cut(cell, models, node['actual_channel_observation'])
            need((node['axis'], Q(node['cut_exact']), node['cut_source']) == (axis, cut, witness) and cell[axis][0] < cut < cell[axis][1], 'registered cut differs')
            children = node['children']
            need(len(children) == 2 and children[0] != children[1] and all(type(c) is int and index < c < len(nodes) for c in children), 'full forward binary split required')
            low, high = list(cell), list(cell)
            low[axis], high[axis] = (cell[axis][0], cut), (cut, cell[axis][1])
            measures = [volume(low), volume(high)]
            need(sum(measures, Q(0)) == value == Q(node['parent_positive_directed_volume_exact']) and list(map(Q, node['children_positive_directed_volumes_exact'])) == measures,
                 'positive directed split conservation differs')
            need(node['closed_cut_plane_retained_as_zero_volume_carrier'] is True, 'closed cut plane omitted')
            stack.extend([(children[1], tuple(high), depth+1), (children[0], tuple(low), depth+1)])
            counts['splits'] += 1
            counts['unresolved'] += 12
            samples.setdefault('split', (index, cell))
            continue
        need(node['kind'] in ('retained', 'excluded') and Q(node['positive_directed_volume_exact']) == value, 'explicit positive leaf volume differs')
        counts['leaves'] += 1
        samples.setdefault('leaf', (index, cell))
        if node['kind'] == 'excluded':
            need(value > TINY, 'tiny positive leaf cannot be discarded')
            pieces, nonaxis = exclusion(node['certificate'], cell, models)
            counts['separations'] += pieces
            counts['nonaxis'] += nonaxis
            counts['excluded'] += 1
            removed += value
            samples.setdefault('excluded', (index, cell))
        else:
            reason = node['reason']
            need(reason in ('tiny_exact_volume_retained', 'global_predicate_budget_retained', 'path_depth_limit_retained', 'global_split_limit_retained') and node['actual_material_interference_claimed'] is False, 'unregistered retention or collision claim')
            need((value <= TINY) == (reason == 'tiny_exact_volume_retained'), 'tiny classification changed')
            if reason == 'path_depth_limit_retained':
                need(depth == 24, 'depth-limited leaf has wrong depth')
            if reason in ('path_depth_limit_retained', 'global_split_limit_retained'):
                need('actual_channel_observation' in node, 'missing actual unresolved observation')
            if 'actual_channel_observation' in node:
                observation = node['actual_channel_observation']
                partial = observation.get('search_stopped_at_predicate_budget') is True
                need(not partial or reason == 'global_predicate_budget_retained', 'partial predicates cannot justify another stop reason')
                counts['unresolved'] += unresolved(observation, cell, models, partial)
            kept += value
            reasons[reason] += 1
    need(len(visited) == len(nodes) == 2*counts['splits']+1 and counts['leaves'] == counts['splits']+1, 'complete binary topology differs')
    need(kept+removed == volume(root) and kept == Q(tree['retained_sum_exact']) and removed == Q(tree['excluded_open_sum_exact']), 'complete tree directed sum differs')
    need(tree['total_leaf_count'] == counts['leaves'] and tree['excluded_leaf_count'] == counts['excluded'] and tree['retained_leaf_count'] == counts['leaves']-counts['excluded'], 'leaf census differs')
    need(tree['retained_reason_counts'] == dict(reasons) and tree['maximum_depth_reached'] == depth_max and tree['all_closed_cut_planes_and_root_boundaries_retained'] is True, 'retention census or closed carriers differ')
    counts['nodes'] = len(nodes)
    return kept, removed, counts, reasons, depth_max, samples


def old_retained(certificate):
    result = []
    kept = removed = Q(0)
    for root in certificate['roots']:
        nodes = root['tree']['nodes']
        stack = [(0, box(root['root_box_exact']))]
        seen = set()
        local = []
        while stack:
            index, cell = stack.pop()
            need(index not in seen and type(index) is int and 0 <= index < len(nodes) and nodes[index]['id'] == index, 'inherited V5 tree identity differs')
            seen.add(index)
            node, value = nodes[index], volume(cell)
            if node['kind'] == 'split':
                axis, cut = node['axis'], Q(node['cut_exact'])
                need(axis in (0, 1, 2) and cell[axis][0] < cut < cell[axis][1], 'inherited V5 split not internal')
                left, right = list(cell), list(cell)
                left[axis], right[axis] = (cell[axis][0], cut), (cut, cell[axis][1])
                children = node['children']
                need(len(children) == 2 and children[0] != children[1], 'inherited V5 binary split differs')
                stack.extend([(children[1], tuple(right)), (children[0], tuple(left))])
            else:
                need(node['kind'] in ('retained', 'excluded') and Q(node['positive_directed_volume_exact']) == value, 'inherited V5 positive leaf differs')
                if node['kind'] == 'retained':
                    kept += value
                    local.append((index, cell, node))
                else:
                    removed += value
        need(len(seen) == len(nodes), 'inherited V5 tree has unreachable nodes')
        result.extend((tuple((root['original_cell_index'], i)), cell, node) for i, cell, node in sorted(local))
    return result, kept, removed


def reject(phase, group, name, check):
    try:
        check()
    except (ValueError, KeyError, IndexError, TypeError, ZeroDivisionError) as exc:
        REPORT['independent_actual_copy_rejections'].append({'phase': phase, 'group': group, 'name': name,
            'actual_rejected': True, 'error_type': type(exc).__name__, 'error_message': str(exc)})
        return
    raise ValueError('independent copied negative control accepted: ' + name)


def copied_tree_controls(phase, tree, root, models, stats, completed):
    samples = stats[-1]
    if 'leaf' not in completed:
        index, unused = samples['leaf']
        changed = deepcopy(tree); changed['nodes'][index]['positive_directed_volume_exact'] = '0'
        reject(phase, 'leaf', 'zeroed-actual-positive-leaf', lambda: tree_readback(changed, root, models))
        changed = deepcopy(tree); changed['nodes'].pop(index)
        reject(phase, 'leaf', 'omitted-actual-positive-leaf', lambda: tree_readback(changed, root, models))
        completed.add('leaf')
    if 'split' in samples and 'split' not in completed:
        index, cell = samples['split']
        edits = [
            ('duplicate-actual-child', lambda n: n.update(children=[n['children'][0]]*2)),
            ('endpoint-cut', lambda n: n.update(cut_exact=str(cell[n['axis']][0]))),
            ('wrong-directed-parent', lambda n: n.update(parent_positive_directed_volume_exact='0')),
            ('omitted-cut-plane', lambda n: n.update(closed_cut_plane_retained_as_zero_volume_carrier=False)),
            ('changed-registered-cut-source', lambda n: n.update(cut_source={'kind': 'unregistered'})),
        ]
        for name, edit in edits:
            changed = deepcopy(tree); edit(changed['nodes'][index])
            reject(phase, 'split', name, lambda: tree_readback(changed, root, models))
        completed.add('split')
    if 'excluded' in samples and 'channel' not in completed:
        index, cell = samples['excluded']
        original = tree['nodes'][index]['certificate']
        for name, edit in [
            ('omitted-actual-separation-code', lambda x: x.update(complete_piece_separation_codes=x['complete_piece_separation_codes'][:-1])),
            ('claimed-closed-whole-cell', lambda x: x.update(whole_closed_cell_disjoint_claimed=True)),
            ('lost-closed-carrier', lambda x: x.update(closed_cell_boundary_retained_as_zero_volume_carrier=False)),
            ('changed-actual-channel-bound', lambda x: x['open_channel_exact'][0].__setitem__(0, str(Q(x['open_channel_exact'][0][0])-1))),
        ]:
            changed = deepcopy(original); edit(changed)
            reject(phase, 'channel', name, lambda: exclusion(changed, cell, models))
        completed.add('channel')


def copied_primitive_controls(phase, boundary, old_boundary, old_frame, records, bindings, actual_controls):
    for row in actual_controls:
        if row['status'] == 'not_applicable':
            need(row['actual_rejected'] is False, 'absent mutation cannot be counted as a rejection')
            continue
        target = row['actual_source_target']
        changed = deepcopy(boundary)
        name = row['name']
        source = changed['sources'][target[0]]
        if name == 'omitted-original-edge-or-vertex-piece':
            need(source['pieces'][target[1]]['kind'] in ('edge', 'vertex'), 'actual edge mutation target differs')
            source['pieces'].pop(target[1])
        else:
            face = source['face_certificates'][target[1]]
            if name == 'changed-complete-source-angular-endpoint':
                face['complete_source_UV_domains_exact'][0][1] = str(Q(face['complete_source_UV_domains_exact'][0][1])+1)
            elif name == 'discarded-positive-rational-Taylor-remainder':
                item = face['patches'][target[2]]['trigonometric_certificate']
                need(Q(item['degree_47_Lagrange_error_exact']) > 0 and item['degree_47_Lagrange_error_exact'] == row['original_positive_Lagrange_error_exact'], 'real positive Taylor remainder target differs')
                item['degree_47_Lagrange_error_exact'] = '0'
            elif name == 'incorrect-original-dual-radial-normal':
                item = face['patches'][target[2]]
                item['radial_normal_exact'][0] = str(Q(item['radial_normal_exact'][0])+1)
            elif name == 'omitted-closed-angular-patch':
                face['patches'].pop()
            elif name == 'discarded-actual-full-D-support-contribution':
                item = face if target[2] is None else face['patches'][target[2]]
                need(any(Q(x) for x in item['full_D_support_exact']), 'real full-D target is zero')
                item['full_D_support_exact'] = ['0', '0']
            else:
                raise ValueError('unknown actual primitive mutation')
        reject(phase, 'primitive', name, lambda: boundary_readback(changed, old_boundary, old_frame, records, bindings))


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def execution_chain():
    receipt = read_json(ROOT / 'r5-local-v6/R5_V6_LOCAL_LAUNCH_RECEIPT_V1.json')
    need(receipt['driver_started'] is True and receipt['driver_completed'] is True and receipt['driver_exit_code'] == 0 and
         receipt['local_execution'] is True and receipt['GitHub_run_execution_claimed'] is False and 'launcher_failure' not in receipt,
         'closed successful local launch receipt required for this completed-run readback')
    need(receipt['snapshot_files_unchanged_after_execution'] is True and receipt['source_and_snapshot_files_rehashed_before_launch'] == 73,
         'actual complete local snapshot closeout differs')
    bound(receipt['launcher_identity']); bound(receipt['readiness_identity']); bound(receipt['actual_snapshot_lock']); bound(receipt['independent_final_static_review'])
    need(receipt['launcher_identity']['sha256'] == 'fc25d867711128b22b820ae960ad34debb8ee378b109c7b8a1ef64e864c32856' and
         receipt['actual_snapshot_lock']['sha256'] == LOCK, 'actual launcher/lock differs from independent source review')
    bound(receipt['actual_pipeline']); bound(receipt['driver_log'])
    pipeline = read_json(ACTUAL / 'pipeline.json')
    scope(pipeline)
    need(pipeline['completed'] is True and pipeline['source_and_public_inputs_unchanged'] is True and
         pipeline['native_Common_called'] is False and pipeline['compiled_transform_error_verified'] is False and
         pipeline['original_clearance_threshold_changed'] is False and pipeline['original_displacement_boxes_changed'] is False,
         'actual pipeline completion or scope differs')
    need(pipeline['source_root'] == str(SOURCE) and pipeline['public_r4_root'] == str(R4) and pipeline['base_V5_root'] == str(OLD), 'actual snapshot roots differ')
    need(pipeline['unchanged_process_limits'] == GATES and pipeline['environment']['github_run_id'] is None and pipeline['environment']['github_sha'] is None,
         'local environment or original resource gates differ')
    bound(pipeline['environment']['executable'])
    need(pipeline['environment']['executable']['sha256'] == 'fa67443527ed9647f760d807e2a38f26340757123e643c4639cf273ed15d5ea7', 'actual isolated interpreter differs')
    lock = read_json(SOURCE / 'R5E_PORTABLE_SOURCE_LOCK_V6.json')
    need(watch(SOURCE / 'R5E_PORTABLE_SOURCE_LOCK_V6.json')['sha256'] == LOCK, 'actual V6 lock differs')
    desired = []
    for directory, rows in [(SOURCE, lock['r5_files']), (R4, lock['r4_source_files'])]:
        desired.extend(bound(row, directory / row['path']) for row in rows)
    need(pipeline['actual_source_identities'] == desired, 'actual complete source identity sequence differs')
    public = read_json(SOURCE / 'R5E_PUBLIC_INPUT_BRIDGE.json')
    base_bridge = read_json(SOURCE / 'R5E_V6_BASE_V5_INPUT_BRIDGE.json')
    need(len(public['files']) == 19 and len(base_bridge['files']) == 25, 'complete input bridge census differs')
    need(pipeline['public_inputs'] == [bound(r['public_identity'], R4 / r['path']) for r in public['files']], 'actual original public inputs differ')
    need(pipeline['actual_V5_inputs'] == [bound(r, OLD / r['path']) for r in base_bridge['files']], 'actual immutable V5 inputs differ')
    inherited = ROOT / 'r5-integration/independent-envelope-v5-execution-review/R5_V5_INDEPENDENT_ACTUAL_EXECUTION_READBACK.json'
    need(watch(inherited)['sha256'] == '93a1b8098f81d46a4eea5cac5e4dfc01639dde220bb771c71b08e7060c361ee4', 'inherited independent V5 proof readback differs')
    previous_audit = read_json(inherited)
    need(previous_audit['audit_completed'] is True and previous_audit['full_continuous_G2'] is False, 'inherited V5 audit scope changed')
    projection_audit = ROOT / 'r5-integration/independent-primitive-v6-preexecution-review/R5_V6_INDEPENDENT_SOURCE_PROJECTION_AUDIT.json'
    need(watch(projection_audit)['sha256'] == 'c59a9737848ebb64aafa03c1f943d7f2127fd210fe857bc4dca36756381daeca', 'lossless source-only audit differs')
    need([(s['label'], s['phase']) for s in pipeline['stages']] == SEQUENCE and
         receipt['actual_completed_stages'] == [s[0] for s in SEQUENCE], 'actual complete five-stage sequence differs')
    outputs = {}
    summaries = []
    previous = utc(pipeline['started_utc'])
    nonces = set()
    owner_drivers = set()
    for stage in pipeline['stages']:
        label, phase = stage['label'], stage['phase']
        for name in ('contract', 'supervision_contract', 'driver_log', 'controller', 'report'):
            bound(stage[name])
        contract = read_json(stage['contract']['path'])
        supervision = read_json(stage['supervision_contract']['path'])
        controller = read_json(stage['controller']['path'])
        report = read_json(stage['report']['path'])
        entry = read_json(ACTUAL / (label+'-supervision') / 'entry-receipt.json')
        scope(contract); scope(report)
        need(contract['phase'] == phase and report['execution_completed'] is True, 'actual scientific phase incomplete or mislabeled')
        need({key: supervision[key] for key in GATES} == GATES and supervision['expected_output_bytes'] == 41943040 and
             supervision['zero_RSS_missing_observations_allowed'] is False, 'owned gate changed')
        need(controller['limits'] == supervision and controller['contract_sha256'] == stage['supervision_contract']['sha256'] and
             supervision['registered_math_contract_sha256'] == stage['contract']['sha256'] == report['contract_sha256'], 'owned/math contract hash chain differs')
        worker = SOURCE / ('verify_primitive_support_r5e_v6.py' if phase.startswith('verify_') else 'primitive_refinement_r5e_v6.py')
        need(supervision['worker'] == watch(worker) and contract['producer_sha256'] == watch(worker)['sha256'] and
             supervision['supervisor_sha256'] == controller['source_sha256'] == watch(R4 / 'supervise_owned_pure_math_r4e_v2.py')['sha256'] and
             supervision['worker_entry_sha256'] == watch(R4 / 'run_owned_pure_math_r4e_v3.py')['sha256'], 'actual owned worker/source identity differs')
        bound(supervision['owned_process'])
        cp, sp, out = str(ACTUAL / (label+'-contract.json')), str(ACTUAL / (label+'-supervision-contract.json')), str(ACTUAL / label)
        need(supervision['worker_output_directory'] == out and supervision['canonical_worker_options'] == ['--contract', '--output'] and
             entry['canonical_worker_arguments'] == ['--contract', cp, '--output', out] and
             entry['actual_argument_bindings'] == {'worker_output_directory': out, 'mathematical_contract_path': cp, 'mathematical_contract_sha256': report['contract_sha256']}, 'actual mathematical argument binding differs')
        python = receipt['exact_driver_command'][0]
        need(stage['command'] == [python, '-I', '-S', '-B', str(R4/'supervise_owned_pure_math_r4e_v2.py'), '--contract', sp, '--out', out+'-supervision', '--', '--contract', cp, '--output', out], 'owned supervisor command differs')
        need(controller['command'] == [python, '-I', '-S', '-B', str(R4/'run_owned_pure_math_r4e_v3.py'), '--supervision-contract', sp, '--receipt', out+'-supervision/entry-receipt.json', '--', '--contract', cp, '--output', out], 'owned entry command differs')
        need(all(v is True for v in (stage['completed'], stage['owned_supervisor_completed'], stage['actual_worker_started'], stage['worker_started_by_driver'],
             controller['completed'], controller['entry_completed'], controller['worker_started'], entry['completed'], entry['worker_started'])), 'actual owned stage did not complete')
        need(stage['supervisor_exit_code'] == controller['worker_exit_code'] == entry['worker_exit_code'] == 0 and
             stage['resource_stop'] is None and controller['resource_stop'] is None and controller['missing_RSS_zero_substitutions'] == 0,
             'owned failure/resource stop or missing RSS substitution')
        need(controller['owned_child_identity_verified'] and controller['owned_channel_descriptors_closed'] and controller['source_and_contract_unchanged'] and
             entry['entry_and_worker_and_owned_source_unchanged'] and entry['native_geometry_imported'] is False, 'owned identity/source closeout differs')
        need(previous <= utc(contract['registered_utc']) <= utc(controller['started_utc']) <= utc(controller['finished_utc']), 'actual chronological dependency differs')
        previous = utc(controller['finished_utc'])
        need(0 <= report['seconds'] <= controller['elapsed_seconds'] <= 600 and 0 < report['peak_RSS_bytes'] == entry['peak_RSS_bytes'] <= 805306368, 'actual wall or RSS exceeds original gate')
        handshake = controller['owned_child_handshake']
        packet, parent, verified = handshake['packet'], handshake['parent_identity'], handshake['verified_binding']
        need(packet['kind'] == 'razr_owned_child_identity_v1' and packet['source_sha256'] == supervision['worker_entry_sha256'] and
             packet['stat'] == verified['stat'] and packet['status'] == verified['status'], 'actual child identity packet differs')
        for process in (packet, parent):
            chain = process['status']['NSpid']
            need(type(chain) is list and chain and all(type(pid) is int and pid > 0 for pid in chain) and
                 process['os_getpid'] == chain[-1] and process['stat']['pid'] == process['status']['Pid'] == int(process['proc_self_visible_pid']) == chain[0] and
                 process['stat']['ppid'] == process['status']['PPid'], 'actual namespace PID chain endpoints differ')
        need(packet['os_getppid'] == parent['os_getpid'] and packet['stat']['ppid'] == parent['stat']['pid'] and
             len(packet['status']['NSpid']) == len(parent['status']['NSpid']), 'actual child/parent namespace mapping differs')
        need(packet['pid_namespace'] == verified['pid_namespace'] == parent['pid_namespace'] and
             packet['pid_for_children_namespace'] == verified['pid_for_children_namespace'] == parent['pid_for_children_namespace'] and parent['stat']['starttime_ticks'] <= packet['stat']['starttime_ticks'], 'actual namespace/starttime binding differs')
        need(len(packet['nonce']) == 64 and set(packet['nonce']) <= set('0123456789abcdef') and packet['nonce'] not in nonces, 'missing/reused owned nonce')
        nonces.add(packet['nonce']); owner_drivers.add((parent['os_getppid'], parent['stat']['ppid'], parent['pid_namespace']))
        initial = handshake['initial_memory']
        need(0 < initial['VmRSS'] <= initial['VmHWM'] <= entry['peak_RSS_bytes'], 'actual initial RSS differs')
        observations = controller['observations']
        need(observations and observations[0]['disk_available_bytes'] >= 150994944 and
             observations[0]['shared_unreclaimable_bytes']+805306368 <= 7301444403, 'actual original startup gate not met')
        live = absent = 0
        earlier = 0
        for sample in observations[1:]:
            need(earlier < sample['elapsed_seconds'] <= controller['elapsed_seconds'], 'actual observation order differs')
            earlier = sample['elapsed_seconds']
            need(sample['disk_available_bytes'] >= 104857600 and sample['shared_unreclaimable_bytes'] <= 7301444403 and sample['actual_output_bytes'] <= 41943040, 'actual live resource gate exceeded')
            memory = sample['owned_worker_memory']
            if memory is None:
                absent += 1
                need(sample['elapsed_seconds'] >= report['seconds'], 'RSS missing before recorded scientific completion')
            else:
                need(0 < memory['VmRSS'] <= memory['VmHWM'] <= entry['peak_RSS_bytes'], 'actual sampled RSS differs')
                live += 1
        final = controller['final_resources']
        need(final['disk_available_bytes'] >= 104857600 and final['shared_unreclaimable_bytes'] <= 7301444403, 'actual final resource gate exceeded')
        actual_bytes = sum(p.stat().st_size for p in (ACTUAL / label).rglob('*') if p.is_file())
        need(actual_bytes <= 41943040, 'actual scientific output exceeds original cap')
        prior_names = [] if phase in ('single_primitive_support_leaf', 'verify_single', 'verify_all') else ['single_primitive_support_leaf'] if phase == 'preflight_primitive_support' else ['single_primitive_support_leaf', 'preflight_primitive_support']
        need([p['phase'] for p in contract['completed_prerequisites']] == prior_names, 'actual prerequisite phase order differs')
        for prior in contract['completed_prerequisites']:
            need(prior['report'] == outputs[prior['phase']]['stage']['report'] and prior['supervisor'] == outputs[prior['phase']]['stage']['controller'], 'prerequisite not bound to actual owned stage')
        if phase in ('preflight_primitive_support', 'all_primitive_support_frames'):
            single, verified_single = outputs['single_primitive_support_leaf']['report'], outputs['verify_single']['report']
            need(single['primitive_support_model_conditional_clearance_passes'] == verified_single['primitive_support_model_conditional_clearance_passes'] == 1 and
                 Q(single['frames'][0]['newly_excluded_open_leaf_sum_exact']) > 0 and single['frames'][0]['applied_cylinder_face_count'] > 0,
                 'actual selected witness must pass before larger work')
            need(contract['independent_single_verification'] == {'report': outputs['verify_single']['stage']['report'], 'supervisor': outputs['verify_single']['stage']['controller']}, 'actual selected verification binding differs')
        if phase == 'all_primitive_support_frames':
            preflight = outputs['preflight_primitive_support']['report']
            need(preflight['execution_completed'] is True and preflight['total_actual_V5_retained_roots'] == 1537 and
                 preflight['complete_phase_maximum_tree_nodes'] == 9729 and preflight['maximum_complete_piece_count_per_material'] <= 4096 and
                 preflight['maximum_additional_slabs_per_piece'] <= 1 and contract['actual_capacity_basis'] == outputs['preflight_primitive_support']['stage']['report'], 'actual all-frame preflight missing')
        if phase.startswith('verify_'):
            prior = outputs['single_primitive_support_leaf' if phase == 'verify_single' else 'all_primitive_support_frames']
            need(contract['producer_report'] == report['verified_producer_report'] == prior['stage']['report'] and
                 contract['producer_owned_supervision'] == prior['stage']['controller'] and report['producer_code_imported'] is False and
                 report['primitive_producer_or_helper_imported'] is False and report['all_checked_source_contract_and_archived_inputs_unchanged'] is True,
                 'actual independent checker binding/import scope differs')
        outputs[phase] = {'stage': stage, 'contract': contract, 'supervision': supervision, 'controller': controller, 'report': report}
        summaries.append({'label': label, 'phase': phase, 'worker_seconds': report['seconds'], 'controller_seconds': controller['elapsed_seconds'],
                          'actual_peak_RSS_bytes': entry['peak_RSS_bytes'], 'live_RSS_observations': live, 'postexit_missing_RSS_observations': absent,
                          'actual_output_bytes': actual_bytes, 'report_identity': stage['report'], 'controller_identity': stage['controller']})
    need(previous <= utc(pipeline['finished_utc']) <= utc(receipt['finished_utc']) and len(owner_drivers) == 1, 'final chronology or common owning driver differs')
    REPORT['local_launch_receipt'] = watch(ROOT / 'r5-local-v6/R5_V6_LOCAL_LAUNCH_RECEIPT_V1.json')
    REPORT['actual_pipeline'] = watch(ACTUAL / 'pipeline.json')
    REPORT['actual_owned_stages'] = summaries
    REPORT['pipeline_seconds'] = pipeline['elapsed_seconds']
    REPORT['launcher_seconds'] = receipt['elapsed_seconds']
    REPORT['unchanged_original_resource_gates'] = GATES
    REPORT['inherited_V5_independent_audit'] = watch(inherited)
    REPORT['lossless_primitive_source_audit'] = watch(projection_audit)
    return pipeline, outputs


def phase_check(report, phase):
    expected = [('case-028', 1)] if phase == 'single_primitive_support_leaf' else FRAME_KEYS
    need(report['phase'] == phase and [(r['case_id'], r['frame']) for r in report['frames']] == expected, 'complete actual phase frame coverage differs')


def roots_check(frame, certificate, expected):
    locators = [list(key) for key, unused, node in expected]
    need(frame['root_base_V5_leaf_locators'] == locators and frame['root_count'] == len(expected) and
         [r['base_V5_leaf_locator'] for r in certificate['roots']] == locators, 'complete original retained-root coverage differs')


def reject_rows(rows, expected_count):
    need(len(rows) == expected_count and len({r['name'] for r in rows}) == expected_count and
         all(r['actual_rejected'] is True and (r.get('reason') or r.get('error')) for r in rows), 'actual checker rejection records incomplete')


def checker_controls(phase, checker, counts, primitive_counts):
    reject_rows(checker['phase_negative_controls'], 3)
    reject_rows(checker['root_coverage_negative_controls'], 2)
    actual = 5
    groups = [('channel_mutations', 'channel_negative_controls', counts['excluded'], 4),
              ('split_mutations', 'split_negative_controls', counts['splits'], 5),
              ('leaf_mutations', 'leaf_negative_controls', counts['leaves'], 2)]
    for label, field, eligible, required in groups:
        applicability = checker['real_case_control_applicability'][label]
        need(applicability['actual_eligible_count'] == eligible and applicability['analytic_controls_are_separate'] is True, 'actual control eligibility differs')
        if eligible:
            need(applicability['status'] == 'executed', 'eligible actual control was not executed')
            reject_rows(checker[field], required)
            actual += required
        else:
            need(applicability['status'] == 'not_applicable' and not checker[field], 'absent real control target mislabeled')
    primitive_rows = checker['primitive_source_negative_controls']
    applicability = checker['real_case_control_applicability']['primitive_source_mutations']
    need(len(primitive_rows) == 6 and applicability['actual_applied_cylinder_count'] == primitive_counts['cylinders'] and
         applicability['individual_absent_targets_are_not_passes'] is True, 'actual primitive mutation applicability differs')
    rejected = sum(row['status'] == 'executed' and row['actual_rejected'] is True for row in primitive_rows)
    need(applicability['actual_rejected_controls'] == rejected and all(row['status'] in ('executed', 'not_applicable') for row in primitive_rows), 'actual primitive rejection count differs')
    actual += rejected
    analytic = checker['mandatory_analytic_controls']
    need(analytic['schema'] == 'razr-r5e-mandatory-primitive-checker-controls-v6' and analytic['execution_kind'] == 'synthetic_analytic_control' and
         analytic['qualifies_original_or_primitive_model_case'] is False and analytic['real_case_result_changed'] is False and
         analytic['original_threshold_and_production_limits_unchanged'] is True and analytic['mandatory_controls_completed'] is True,
         'synthetic controls mislabeled or incomplete')
    unit = [['0', '1']]*3
    need(analytic['complete_source_closed_boxes_exact'] == [unit, unit] and analytic['complete_source_face_counts'] == [6, 6], 'analytic complete closed solid source differs')
    exterior = analytic['complete_box_exterior_positive']
    need(exterior['verified'] is True and exterior['root_box_exact'] == [['2', '3'], ['0', '1'], ['0', '1']] and exterior['excluded_open_volume_exact'] == '1', 'actual analytic exterior positive differs')
    delta = TINY/2
    split = analytic['exact_split_positive']
    need(split['verified'] is True and box(split['root_box_exact']) == ((1-delta, Q(2)), (Q(0), Q(1)), (Q(0), Q(1))) and
         Q(split['cut_exact']) == 1 and list(map(Q, split['children_positive_directed_volumes_exact'])) == [delta, Q(1)] and split['tiny_leaf_retained_in_full'] is True, 'actual analytic positive directed split differs')
    inside = analytic['all_retained_no_excluded_positive']
    inside_box = ((Q(1,4), Q(1,4)+delta), (Q(1,4), Q(3,4)), (Q(1,4), Q(3,4)))
    need(inside['verified'] is True and box(inside['root_box_exact']) == inside_box and
         Q(inside['retained_positive_volume_exact']) == volume(inside_box) > 0 and inside['excluded_leaves'] == inside['splits'] == 0 and
         inside['all_twelve_unresolved_channels_checked'] is True and inside['is_actual_V5_or_V6_case_branch_coverage'] is False,
         'actual analytic all-retained/no-excluded regression differs')
    for name in ('channel_mutations', 'split_mutations'):
        need(inside[name]['status'] == 'not_applicable' and inside[name]['actual_eligible_count'] == 0, 'analytic no-target applicability differs')
    for name, expected in [('channel_negative_controls', 4), ('split_negative_controls', 5), ('leaf_negative_controls', 2)]:
        reject_rows(analytic[name], expected)
    return {'phase': phase, 'actual_checker_real_copy_rejections': actual, 'actual_checker_synthetic_negative_rejections': 11,
            'synthetic_positive_cases': 3, 'all_retained_no_excluded_analytic_regression_executed': True,
            'synthetic_controls_counted_as_real_case_coverage': False, 'synthetic_negative_suite_reexecuted_by_this_auditor': False,
            'real_case_control_applicability': checker['real_case_control_applicability']}


def mathematical_readback(outputs):
    bundle = read_gzip(SOURCE / 'R5E_V6_PRIMITIVE_SOURCE.json.gz')
    old_projection = read_gzip(SOURCE / 'R5E_V5_PLANAR_TRIM_SOURCE.json.gz')
    records = {(r['input']['case_id'], r['input']['material_id']): r for r in bundle['records']}
    originals = {(r['input']['case_id'], r['input']['material_id']): r for r in old_projection['records']}
    need(len(records) == len(bundle['records']) == len(originals) == 32 and set(records) == set(originals), 'complete original material census differs')
    census = Counter()
    for key, record in records.items():
        need(all(record[name] == originals[key][name] for name in ('input', 'original_complete_boundary_counts', 'original_complete_boundary_canonical_sha256')) and
             record['full_original_face_records_unchanged'] is True, 'original whole-material source identity differs')
        need(len({r['face_index'] for r in record['candidate_faces']}) == len(record['candidate_faces']), 'duplicate original candidate face')
        for face in record['candidate_faces']:
            need(canonical(face['complete_original_face']) == face['complete_original_face_canonical_sha256'], 'source full original face identity differs')
            census[face['source_primitive']] += 1
    need(census == {'GeomAbs_Plane': 48, 'GeomAbs_Cylinder': 16}, 'complete original primitive census differs')
    bindings = {(r['case_id'], r['frame']): r for r in bundle['frame_bindings']}
    need(list(bindings) == FRAME_KEYS, 'complete source frame binding sequence differs')
    old_report = read_json(OLD / 'all-trim-model-frames/report.json')
    old_frames = {(r['case_id'], r['frame']): r for r in old_report['frames']}
    baseline = read_json(R4 / 'support-v4/report.json')
    baselines = {(r['case_id'], r['frame']): r for r in baseline['frames']}
    selection = read_json(SOURCE / 'R5E_V6_REAL_RETAINED_LEAF.json')
    selected_locator = (selection['original_R4_root_index'], selection['actual_V5_leaf_node_index'])
    need((selection['case_id'], selection['frame'], selected_locator) == ('case-028', 1, (8, 13)), 'original selected witness differs')
    preflight = outputs['preflight_primitive_support']['report']
    capacity_frames = {(r['case_id'], r['frame']): r for r in preflight['frames']}
    need(list(capacity_frames) == FRAME_KEYS and preflight['total_actual_V5_retained_roots'] == 1537 and
         preflight['complete_phase_maximum_tree_nodes'] == 9729 and preflight['complete_phase_maximum_leaves'] == 5633 and
         all(r['new_clearance_result_claimed'] is False for r in preflight['frames']), 'actual capacity census or scope differs')
    for phase, verifying in [('single_primitive_support_leaf', 'verify_single'), ('all_primitive_support_frames', 'verify_all')]:
        producer, checker = outputs[phase]['report'], outputs[verifying]['report']
        phase_check(producer, phase)
        need([(r['case_id'], r['frame']) for r in checker['frames']] == [(r['case_id'], r['frame']) for r in producer['frames']], 'checker full-frame coverage differs')
        checker_frames = {(r['case_id'], r['frame']): r for r in checker['frames']}
        completed_controls = set()
        total = Counter()
        all_reasons = Counter()
        primitive_counts = Counter()
        max_pieces = max_slabs = max_characters = 0
        non_tiny_original = 0
        passed = 0
        for row in producer['frames']:
            key = row['case_id'], row['frame']
            prior = old_frames[key]
            baseline_frame = baselines[key]
            binding = bindings[key]
            for name in ('pair', 'original_remaining_displacement_box_exact'):
                need(row[name] == prior[name], 'original frame or full displacement changed')
            need(row['original_raw_proof_identity'] == baseline_frame['proof'] and
                 row['original_remaining_displacement_box_exact'] == baseline_frame['full_remaining_displacement_box_exact'] == binding['original_full_D'], 'original R4 source/full D binding differs')
            prior_path = OLD / 'all-trim-model-frames' / prior['certificate']['path']
            bound(prior['certificate'], prior_path); bound(row['base_V5_certificate'], prior_path)
            previous = read_gzip(prior_path)
            need(previous['frame'] == {k:v for k,v in prior.items() if k != 'certificate'}, 'immutable V5 certificate header differs')
            old_leaves, old_kept, old_removed = old_retained(previous)
            need([list(key) for key, unused, node in old_leaves] == binding['actual_V5_retained_leaf_locators'] and
                 old_kept == Q(prior['retained_leaf_sum_exact']) == Q(row['base_V5_retained_leaf_sum_exact']) and
                 old_removed == Q(prior['excluded_open_leaf_sum_exact']) == Q(row['base_V5_excluded_open_leaf_sum_exact']), 'actual inherited complete retained forest differs')
            non_tiny_original += sum(volume(cell) > TINY for unused, cell, node in old_leaves)
            wanted = old_leaves if phase != 'single_primitive_support_leaf' else [r for r in old_leaves if r[0] == selected_locator]
            if phase == 'single_primitive_support_leaf':
                need(len(wanted) == 1 and encbox(wanted[0][1]) == selection['leaf_box_exact'] and wanted[0][2] == selection['actual_V5_leaf_record'] and
                     selection['actual_V5_original_root_record'] == next(r for r in previous['roots'] if r['original_cell_index'] == selected_locator[0]), 'actual selected complete original V5 witness differs')
            label = outputs[phase]['stage']['label']
            certificate_path = ACTUAL / label / row['certificate']['path']
            bound(row['certificate'], certificate_path)
            certificate = read_gzip(certificate_path)
            need(certificate['schema'] == 'razr-r5e-primitive-support-tree-v6' and certificate['frame'] == {k:v for k,v in row.items() if k != 'certificate'} and
                 certificate['V5_producer_rerun'] is False and Q(certificate['actual_V5_excluded_open_sum_preserved_exact']) == old_removed, 'actual new certificate header or inherited excluded volume differs')
            roots_check(row, certificate, wanted)
            models, primitives = boundary_readback(certificate['boundary_refinement'], previous['boundary_refinement'], prior, records, bindings)
            primitive_counts.update(primitives)
            need(row['source_piece_counts'] == [len(s['pieces']) for s in models] and
                 row['applied_plane_face_count'] == primitives['planes'] and row['applied_cylinder_face_count'] == primitives['cylinders'] and
                 row['retained_original_face_count_after_rejection'] == primitives['fallbacks'], 'actual frame primitive census differs')
            capacity = capacity_frames[key]
            need(capacity['root_count'] == len(old_leaves) and capacity['source_piece_counts'] == row['source_piece_counts'] and
                 capacity['applied_plane_face_count'] == primitives['planes'] and capacity['applied_cylinder_face_count'] == primitives['cylinders'], 'measured all-frame capacity differs from actual source reconstruction')
            for model in models:
                max_pieces = max(max_pieces, len(model['pieces']))
                for piece in model['pieces']:
                    max_slabs = max(max_slabs, len(piece['slabs']))
                    values = [value for interval in piece['box'] for value in interval]
                    for normal, interval in piece['slabs']:
                        values.extend(normal); values.extend(interval)
                    max_characters = max(max_characters, *(len(str(x)) for x in values))
            if 'header' not in completed_controls:
                for name, edit in [
                    ('missing-actual-frame', lambda value: value['frames'].pop()),
                    ('duplicated-actual-frame', lambda value: value['frames'].append(value['frames'][0])),
                    ('wrong-actual-phase', lambda value: value.update(phase='unregistered')),
                ]:
                    changed = deepcopy(producer); edit(changed)
                    reject(phase, 'phase', name, lambda: phase_check(changed, phase))
                for name, edit in [('missing-actual-retained-root', lambda value: value['roots'].pop()), ('duplicate-actual-retained-root', lambda value: value['roots'].append(value['roots'][0]))]:
                    changed = deepcopy(certificate); edit(changed)
                    reject(phase, 'roots', name, lambda: roots_check(row, changed, wanted))
                completed_controls.add('header')
            if primitives['cylinders'] and 'primitive' not in completed_controls:
                copied_primitive_controls(phase, certificate['boundary_refinement'], previous['boundary_refinement'], prior, records, bindings, checker['primitive_source_negative_controls'])
                completed_controls.add('primitive')
            counts = Counter()
            reasons = Counter()
            kept = removed = Q(0)
            maximum_depth = 0
            for root, (locator, cell, old_node) in zip(certificate['roots'], wanted):
                need(root['base_V5_leaf_locator'] == list(locator) and box(root['root_box_exact']) == cell and
                     Q(root['root_directed_volume_exact']) == volume(cell) == Q(old_node['positive_directed_volume_exact']), 'new root is not its exact original retained V5 leaf')
                stats = tree_readback(root['tree'], cell, models)
                kept += stats[0]; removed += stats[1]; counts.update(stats[2]); reasons.update(stats[3]); maximum_depth = max(maximum_depth, stats[4])
                copied_tree_controls(phase, root['tree'], cell, models, stats, completed_controls)
            need(kept+removed == sum((volume(cell) for unused, cell, node in wanted), Q(0)) == Q(row['new_root_sum_exact']) and
                 kept == Q(row['retained_leaf_sum_exact']) and removed == Q(row['newly_excluded_open_leaf_sum_exact']), 'new complete directed volume ledger differs')
            selected = kept
            if phase == 'all_primitive_support_frames':
                need(kept+removed == old_kept, 'new exclusions were not deducted from the full old retained sum')
                selected = min(kept, Q(baseline_frame['coarse_whole_support_upper_exact_mm3']))
            need(selected == Q(row['primitive_support_model_conditional_upper_exact_mm3']) and row['primitive_support_model_conditional_upper_mm3'] == float(selected) and
                 row['primitive_support_model_conditional_clearance_gate_passed'] == (selected <= TOL), 'new conditional bound or original TOL differs')
            need(row['exact_splits_this_frame'] == counts['splits'] and row['total_leaf_count'] == counts['leaves'] and row['maximum_depth_reached'] == maximum_depth and
                 row['all_V5_and_new_closed_carriers_retained'] is True, 'frame full partition census or carriers differ')
            check = checker_frames[key]
            for field, number in [('new_retained_roots_verified', len(wanted)), ('new_tree_nodes_verified', counts['nodes']), ('new_splits_verified', counts['splits']),
                                  ('new_all_positive_leaves_verified', counts['leaves']), ('new_excluded_leaf_count', counts['excluded']),
                                  ('new_complete_piece_separations_verified', counts['separations']), ('new_nonaxis_separations_verified', counts['nonaxis'])]:
                need(check[field] == number, 'actual checker count differs from third-author reconstruction: ' + field)
            need(Q(check['new_retained_leaf_sum_exact']) == kept and Q(check['new_excluded_open_sum_exact']) == removed and
                 Q(check['primitive_support_model_conditional_upper_exact_mm3']) == selected and check['primitive_support_model_conditional_clearance_gate_passed'] == (selected <= TOL), 'actual checker exact result differs')
            total.update(counts); total['roots'] += len(wanted); all_reasons.update(reasons)
            passed += selected <= TOL
            REPORT['frames'].append({'phase': phase, 'case_id': key[0], 'frame': key[1], 'pair': row['pair'],
                'original_full_D_exact': row['original_remaining_displacement_box_exact'], 'certificate_identity': watch(certificate_path),
                'actual_V5_retained_root_count': len(wanted), 'tree_counts': dict(counts), 'retention_reasons': dict(reasons),
                'maximum_depth': maximum_depth, 'primitive_reconstruction': primitives, 'retained_sum_exact': str(kept),
                'new_excluded_sum_exact': str(removed), 'conditional_upper_exact_mm3': str(selected), 'conditional_upper_mm3': float(selected),
                'original_float64_TOL_passed_in_conditional_model': selected <= TOL})
        counters = producer['counters']
        need(all(type(v) is int and v >= 0 for v in counters.values()) and counters['splits'] == total['splits'] <= 4096 and
             counters['tree_nodes_visited'] == total['nodes'] and counters['boundary_box_tests'] <= 12000000 and counters['support_inequality_tests'] <= 12000000,
             'actual finite phase counters differ')
        need(sum(r['exact_piece_tests_this_frame'] for r in producer['frames']) == counters['boundary_box_tests'] and
             sum(r['exact_support_inequality_tests_this_frame'] for r in producer['frames']) == counters['support_inequality_tests'], 'per-frame predicate accounting differs')
        if all_reasons['global_split_limit_retained']:
            need(total['splits'] == 4096, 'global split retention does not follow the registered split cap')
        if all_reasons['global_predicate_budget_retained']:
            need(counters['boundary_box_tests'] == 12000000 or counters['support_inequality_tests'] == 12000000, 'predicate retention without actual cap')
        need(total['nodes'] <= total['roots']+8192 and total['leaves'] <= total['roots']+4096 and
             producer['total_actual_V5_retained_roots'] == total['roots'] and producer['complete_phase_maximum_tree_nodes'] == total['roots']+8192 and
             producer['complete_phase_maximum_leaves'] == total['roots']+4096, 'complete forest finite capacity differs')
        need(producer['maximum_complete_piece_count_per_material'] == max_pieces <= 4096 and producer['maximum_additional_slabs_per_piece'] == max_slabs <= 1 and
             producer['maximum_exact_coordinate_character_count'] == max_characters, 'measured primitive resource census differs')
        need(producer['applied_plane_face_occurrences'] == primitive_counts['planes'] and producer['applied_cylinder_face_occurrences'] == primitive_counts['cylinders'] and
             producer['retained_original_face_occurrences_after_rejection'] == primitive_counts['fallbacks'], 'complete primitive occurrence census differs')
        need(producer['primitive_support_model_conditional_clearance_passes'] == checker['primitive_support_model_conditional_clearance_passes'] == passed and
             checker['actual_retention_reason_counts'] == dict(all_reasons), 'overall actual conditional gates/retention reasons differ')
        if phase == 'all_primitive_support_frames':
            need(total['roots'] == 1537 and non_tiny_original == 44, 'all1537/44 original retained roots must be covered')
            need(preflight['maximum_complete_piece_count_per_material'] == max_pieces and preflight['maximum_exact_coordinate_character_count'] == max_characters, 'measured capacity preflight differs from full execution')
        summary = checker_controls(phase, checker, total, primitive_counts)
        summary.update(independent_counts=dict(total), independent_primitive_counts=dict(primitive_counts), independent_retention_reasons=dict(all_reasons),
                       conditional_clearance_passes=passed, expected_frames=1 if phase == 'single_primitive_support_leaf' else 16,
                       independent_copy_rejection_count=sum(r['phase'] == phase for r in REPORT['independent_actual_copy_rejections']))
        REPORT.setdefault('phase_summaries', []).append(summary)
    REPORT['original_float64_TOL_exact'] = str(TOL)
    REPORT['source_primitive_census'] = dict(census)
    REPORT['original_V3_raw_clearance_passes_unchanged'] = 4
    REPORT['actual_V5_conditional_clearance_passes_unchanged'] = 8
    REPORT['actual_V4_scientific_and_checker_failure_preserved'] = True


def main():
    destination = HERE / 'R5_V6_INDEPENDENT_ACTUAL_LOCAL_READBACK_V2.json'
    need(not destination.exists(), 'new immutable actual readback report required')
    resource.setrlimit(resource.RLIMIT_AS, (536870912, 536870912))
    resource.setrlimit(resource.RLIMIT_CPU, (360, 360))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('registered360-second independent actual audit budget')))
    signal.alarm(360)
    started = time.monotonic()
    REPORT['started_utc'] = datetime.now(timezone.utc).isoformat()
    try:
        plan_path = HERE / 'R5_V6_INDEPENDENT_ACTUAL_READBACK_PLAN.json'
        registration_path = HERE / 'R5_V6_ACTUAL_AUDIT_EXECUTION_REGISTRATION_V2.json'
        registration = read_json(registration_path)
        need(watch(__file__) == registration['audit_source'] and watch(plan_path) == registration['plan'] and
             watch(ACTUAL/'pipeline.json') == registration['closed_pipeline'], 'actual audit source/plan/closed run not preregistered')
        REPORT['audit_source_identity'] = watch(__file__)
        REPORT['registered_plan_identity'] = watch(plan_path)
        REPORT['execution_registration_identity'] = watch(registration_path)
        census = [watch(p) for p in sorted(ACTUAL.rglob('*')) if p.is_file()]
        REPORT['complete_actual_output_census'] = census
        pipeline, outputs = execution_chain()
        mathematical_readback(outputs)
        need(all(ident(path) == value for path, value in WATCHED.items()), 'watched source/result changed during actual independent readback')
        need([str(p.resolve()) for p in sorted(ACTUAL.rglob('*')) if p.is_file()] == [row['path'] for row in census], 'actual closed output census changed')
        REPORT['all_watched_sources_and_results_unchanged'] = True
        REPORT['original_threshold_or_gate_changed'] = False
        REPORT['audit_completed'] = True
    except BaseException as exc:
        REPORT['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    finally:
        signal.alarm(0)
        REPORT['elapsed_seconds'] = time.monotonic()-started
        REPORT['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        REPORT['decoded_json_bytes'] = DECODED
        REPORT['readback_assertions_evaluated'] = ASSERTIONS
        REPORT['watched_identity_count'] = len(WATCHED)
        REPORT['registered_budget_respected'] = REPORT['elapsed_seconds'] <= 360 and REPORT['peak_RSS_bytes'] <= 536870912 and DECODED <= 536870912
        REPORT['finished_utc'] = datetime.now(timezone.utc).isoformat()
        encoded = (json.dumps(REPORT, indent=2)+'\n').encode()
        need(len(encoded) <= 8388608, 'registered audit output exceeds8MiB')
        destination.write_bytes(encoded)
        print(json.dumps({key: REPORT.get(key) for key in ('audit_completed', 'elapsed_seconds', 'peak_RSS_bytes', 'decoded_json_bytes', 'readback_assertions_evaluated', 'registered_budget_respected', 'failure')}), flush=True)
    return 0 if REPORT['audit_completed'] and REPORT['registered_budget_respected'] else 2


if __name__ == '__main__':
    raise SystemExit(main())


