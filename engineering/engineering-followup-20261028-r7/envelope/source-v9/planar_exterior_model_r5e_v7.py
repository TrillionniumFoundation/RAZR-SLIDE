"""Exact closed-UV exterior paths for the explicit bounded-face model.

No CAD import, sampled region membership or native winding claim is made.
The independent checker must not import this producer helper.
"""
from fractions import Fraction as F
from functools import lru_cache
import hashlib
import json
from math import factorial

IDENTITY = [['1','0','0','0'],['0','1','0','0'],['0','0','1','0']]


def need(ok, message):
    if not ok:
        raise ValueError(message)


def q(value): return F(value['exact']) if isinstance(value, dict) else F(value)
def vec(value): return tuple(map(q, value))
def box(value): return [tuple(map(F, part)) for part in value]
def enc(value): return [str(v) for v in value]
def encbox(value): return [enc(part) for part in value]
def canonical(value): return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
def dot(a, b): return sum((x*y for x, y in zip(a, b)), F(0))
def add(a, b): return (a[0]+b[0], a[1]+b[1])
def scale(c, a): return (min(c*a[0], c*a[1]), max(c*a[0], c*a[1]))
def multiply(a, b):
    values = [x*y for x in a for y in b]
    return min(values), max(values)


def project(normal, ranges):
    result = (F(0), F(0))
    for coefficient, interval in zip(normal, ranges):
        result = add(result, scale(coefficient, interval))
    return result


@lru_cache(maxsize=2048)
def centre_polynomials(centre):
    need(abs(centre) <= 8, 'source angle outside fixed Taylor range')
    sine = F(0); cosine = F(0); st = centre; ct = F(1); square = centre*centre
    for k in range(24):
        sine += st; cosine += ct
        if k < 23:
            st = -st*square/((2*k+2)*(2*k+3))
            ct = -ct*square/((2*k+1)*(2*k+2))
    return sine, cosine, abs(centre)**48/factorial(48)


def angular_record(interval):
    a, b = interval
    need(a <= b, 'ordered complete source angular interval required')
    centre = F(((a+b)/2*65536).__floor__(), 65536)
    sine, cosine, error = centre_polynomials(centre)
    return {'parameter_interval_exact': enc(interval), 'dyadic_centre_exact': str(centre),
            'actual_offset_interval_exact': enc((a-centre, b-centre)),
            'Maclaurin_sin_exact': str(sine), 'Maclaurin_cos_exact': str(cosine),
            'degree_47_Lagrange_error_exact': str(error), 'Taylor_term_count': 24,
            'centre_grid_denominator': 65536, 'source_endpoints_replaced': False}


def trig_range(A, B, record):
    s = F(record['Maclaurin_sin_exact']); c = F(record['Maclaurin_cos_exact'])
    e = F(record['degree_47_Lagrange_error_exact']); offset = tuple(map(F, record['actual_offset_interval_exact']))
    sine = (s-e, s+e); cosine = (c-e, c+e); h = max(map(abs, offset))
    value = add(scale(A, cosine), scale(B, sine))
    slope = add(scale(-A, sine), scale(B, cosine))
    remainder = (abs(A)+abs(B))*h*h/2
    return add(add(value, multiply(slope, offset)), (-remainder, remainder))


def left_inverse(X, Y):
    xx, xy, yy = dot(X, X), dot(X, Y), dot(Y, Y)
    determinant = xx*yy-xy*xy
    need(determinant > 0, 'singular exact affine plane basis')
    rows = [tuple((yy*X[k]-xy*Y[k])/determinant for k in range(3)),
            tuple((xx*Y[k]-xy*X[k])/determinant for k in range(3))]
    need([[dot(r, c) for c in (X, Y)] for r in rows] == [[F(1),F(0)],[F(0),F(1)]], 'exact plane left-inverse identity failed')
    return rows, determinant


def affine_project(inverse, origin, spatial_box):
    relative = [(spatial_box[k][0]-origin[k], spatial_box[k][1]-origin[k]) for k in range(3)]
    return [project(row, relative) for row in inverse]


def curve_geometry(occurrence):
    need(occurrence['location']['matrix_3x4_exact'] == IDENTITY and occurrence['edge_index'] is not None,
         'complete mapped identity occurrence required')
    orientation = occurrence['orientation'].split('.')[-1]
    need(orientation in ('TopAbs_FORWARD', 'TopAbs_REVERSED'), 'unsupported source occurrence orientation')
    curve = occurrence['pcurve']; first = q(curve['first_parameter']); last = q(curve['last_parameter'])
    need(first <= last, 'complete ordered source parameters required')
    kind = curve['type'].split('.')[-1]
    need(kind in ('GeomAbs_Line','GeomAbs_Circle'), 'unsupported pcurve retains whole old plane')
    if kind == 'GeomAbs_Line':
        origin = vec(curve['origin_exact']); direction = vec(curve['direction_exact'])
        need(len(origin) == len(direction) == 2 and any(direction), 'nonzero two-dimensional Line required')
        endpoints = [[(origin[k]+direction[k]*t, origin[k]+direction[k]*t) for k in range(2)] for t in (first,last)]
    else:
        origin = vec(curve['center_exact']); X = vec(curve['X_exact']); Y = vec(curve['Y_exact']); radius = q(curve['radius'])
        need(len(origin) == len(X) == len(Y) == 2 and radius > 0, 'complete positive original Circle required')
        need(X[0]*Y[1]-X[1]*Y[0] != 0, 'singular original Circle basis')
        endpoints = []
        for t in (first,last):
            trig = angular_record((t,t))
            endpoints.append([add((origin[k],origin[k]),scale(radius,trig_range(X[k],Y[k],trig))) for k in range(2)])
    if orientation == 'TopAbs_REVERSED':
        endpoints.reverse()
    return curve, kind, (first,last), endpoints


def pcurve_pieces(occurrence, wire_index, occurrence_index, limits):
    curve, kind, domain, endpoints = curve_geometry(occurrence)
    prefix = {'wire_index': wire_index, 'occurrence_index': occurrence_index, 'source_edge_index': occurrence['edge_index']}
    pieces = []
    if kind == 'GeomAbs_Line':
        O = vec(curve['origin_exact']); direction = vec(curve['direction_exact'])
        mapped = [add((O[k],O[k]),scale(direction[k],domain)) for k in range(2)]
        n = (-direction[1], direction[0]); value = dot(n,O)
        pieces.append(dict(prefix, kind='line', parameter_patch_index=None, parameter_interval_exact=enc(domain),
                           box_exact=encbox(mapped), additional_slabs=[{'normal_exact':enc(n),'bounds_exact':[str(value),str(value)],'source':'exact_pcurve_line'}]))
    else:
        O = vec(curve['center_exact']); X = vec(curve['X_exact']); Y = vec(curve['Y_exact']); radius = q(curve['radius'])
        determinant = X[0]*Y[1]-X[1]*Y[0]
        count = limits['circle_angular_patch_count']; need(count == 64, 'fixed original circle subdivision required')
        for index in range(count):
            angular = (domain[0]+(domain[1]-domain[0])*index/count, domain[0]+(domain[1]-domain[0])*(index+1)/count)
            trig = angular_record(angular)
            mapped = [add((O[k],O[k]),scale(radius,trig_range(X[k],Y[k],trig))) for k in range(2)]
            A, B = F(trig['Maclaurin_cos_exact']), F(trig['Maclaurin_sin_exact'])
            n = ((A*Y[1]-B*X[1])/determinant, (B*X[0]-A*Y[0])/determinant)
            need(any(n) and dot(n,X) == A and dot(n,Y) == B, 'exact source Circle dual identity failed')
            support = add((dot(n,O),dot(n,O)),scale(radius,trig_range(A,B,trig)))
            pieces.append(dict(prefix, kind='circle_patch', parameter_patch_index=index,
                               parameter_interval_exact=enc(angular), trigonometric_certificate=trig,
                               box_exact=encbox(mapped), radial_dual_coordinates_exact=enc((A,B)),
                               additional_slabs=[{'normal_exact':enc(n),'bounds_exact':enc(support),'source':'exact_pcurve_circle_radial_support'}]))
    return pieces, endpoints


def distance_bounds(a, b):
    lower = max(max(F(0), a[k][0]-b[k][1], b[k][0]-a[k][1]) for k in range(2))
    upper = max(max(abs(a[k][0]-b[k][1]), abs(a[k][1]-b[k][0])) for k in range(2))
    return lower, upper


def wire_cover(wire, limits):
    need(wire['location']['matrix_3x4_exact'] == IDENTITY and wire['edge_occurrences'], 'complete identity original wire required')
    need(wire['orientation'].split('.')[-1] in ('TopAbs_FORWARD','TopAbs_REVERSED'), 'unsupported original wire orientation')
    occurrences = wire['edge_occurrences']; endpoints = []; pieces = []
    for index, occurrence in enumerate(occurrences):
        cover, pair = pcurve_pieces(occurrence,wire['index'],index,limits)
        pieces.extend(cover); endpoints.append(pair)
    joins = []; successors = []
    for index, pair in enumerate(endpoints):
        distances = [distance_bounds(pair[1],other[0]) for other in endpoints]
        successor = min(range(len(endpoints)), key=lambda j:(distances[j][1],j))
        chosen_upper = distances[successor][1]
        competitors = [distances[j][0] for j in range(len(endpoints)) if j != successor]
        need(not competitors or chosen_upper < min(competitors), 'ambiguous endpoint association retains whole plane')
        hull = [(min(pair[1][k][0],endpoints[successor][0][k][0]),max(pair[1][k][1],endpoints[successor][0][k][1])) for k in range(2)]
        delta = max(b-a for a,b in hull)
        expanded = [(a-delta,b+delta) for a,b in hull]
        successors.append(successor)
        joins.append({'terminal_occurrence_index':index,'initial_occurrence_index':successor,
                      'selected_Linf_distance_upper_exact':str(chosen_upper),
                      'minimum_competing_Linf_distance_lower_exact':str(min(competitors)) if competitors else None,
                      'endpoint_hull_exact':encbox(hull),'closure_expansion_exact':str(delta),
                      'closed_gap_box_exact':encbox(expanded)})
        pieces.append({'kind':'closure','wire_index':wire['index'],'occurrence_index':index,
                       'successor_occurrence_index':successor,'source_edge_index':occurrences[index]['edge_index'],
                       'parameter_patch_index':None,'box_exact':encbox(expanded),'additional_slabs':[]})
    need(sorted(successors) == list(range(len(endpoints))), 'endpoint successor relation is not a bijection')
    seen = set(); index = 0
    for unused in endpoints:
        need(index not in seen, 'source endpoint relation has multiple cycles')
        seen.add(index); index = successors[index]
    need(index == 0 and len(seen) == len(endpoints), 'source endpoint relation does not close one complete cycle')
    record = {'wire_index':wire['index'],'original_is_outer':wire['is_outer'],'original_orientation':wire['orientation'],
              'source_occurrence_count':len(occurrences),'successor_indices':successors,
              'oriented_endpoint_boxes_exact':[{'occurrence_index':i,'start_box_exact':encbox(p[0]),'end_box_exact':encbox(p[1])} for i,p in enumerate(endpoints)],
              'join_certificates':joins,'complete_closed_boundary_piece_count':len(pieces),
              'native_closure_membership_verified':False}
    return pieces, record


def face_model(candidate, stationary, displacement, limits):
    face = candidate['complete_original_face']; surface = face['local_surface']
    need(canonical(face) == candidate['complete_original_face_canonical_sha256'], 'full original plane face identity differs')
    need(face['index'] == candidate['face_index'] and surface['type'] == 'GeomAbs_SurfaceType.GeomAbs_Plane', 'original mapped Plane required')
    need(face['location']['matrix_3x4_exact'] == IDENTITY and face['wires'], 'complete identity original face required')
    need(face['orientation'].split('.')[-1] in ('TopAbs_FORWARD','TopAbs_REVERSED'), 'unsupported original face orientation')
    O, X, Y = vec(surface['origin_exact']), vec(surface['X_exact']), vec(surface['Y_exact'])
    need(len(O) == len(X) == len(Y) == 3, 'complete 3D affine plane basis required')
    inverse, determinant = left_inverse(X,Y); known = affine_project(inverse,O,stationary)
    pieces = []; wires = []
    for wire in face['wires']:
        cover, record = wire_cover(wire,limits); pieces.extend(cover); wires.append(record)
    need(len(pieces) <= limits['maximum_UV_pieces_per_face'], 'fixed complete UV-piece bound exceeded')
    return {'applied':True,'plane_origin_exact':enc(O),'basis_X_exact':enc(X),'basis_Y_exact':enc(Y),
            'left_inverse_exact':[enc(row) for row in inverse],'Gram_determinant_exact':str(determinant),
            'stationary_face_box_exact':encbox(stationary),'full_D_exact':encbox(displacement),
            'known_UV_box_exact':encbox(known),'wire_certificates':wires,'uv_boundary_pieces':pieces,
            'source_occurrence_count':sum(w['source_occurrence_count'] for w in wires),
            'bounded_region_complete_boundary_cover_is_model_premise':True,
            'native_planar_region_semantics_verified':False,'native_closure_membership_verified':False,
            'conditional_planar_exterior_model_only':True}


def runtime_model(record):
    return {'certificate':record, 'model_index':record['model_index'],
            'inverse':[vec(row) for row in record['left_inverse_exact']], 'origin':vec(record['plane_origin_exact']),
            'stationary':box(record['stationary_face_box_exact']),'D':box(record['full_D_exact']),
            'known':box(record['known_UV_box_exact']),
            'pieces':[{'box':box(p['box_exact']),'slabs':[(vec(s['normal_exact']),tuple(map(F,s['bounds_exact']))) for s in p['additional_slabs']]} for p in record['uv_boundary_pieces']]}


def build_models(v6_boundary, frame, projection, limits):
    need(limits['circle_angular_patch_count'] == 64 and limits['Taylor_term_count'] == 24 and
         limits['centre_grid_denominator'] == 65536, 'fixed finite source algorithm differs')
    records = {(r['input']['case_id'],r['input']['material_id']):r for r in projection['records']}
    binding = next(f for f in projection['frame_bindings'] if (f['case_id'],f['frame']) == (frame['case_id'],frame['frame']))
    need(binding['original_full_D'] == frame['original_remaining_displacement_box_exact'], 'complete original D changed')
    D = box(binding['original_full_D']); zero = [(F(0),F(0))]*3
    serialized = {'schema':'razr-r5e-planar-exterior-models-v7','sources':[],
                  'conditional_planar_exterior_model_only':True,'native_planar_region_semantics_verified':False}
    models = {}; next_index = 0; total_pieces = 0; applied = rejected = 0
    for side, source in enumerate(v6_boundary['sources']):
        key = tuple(source['material_key']); need(list(key) == binding['moving_and_fixed_material_keys'][side], 'original material side binding differs')
        candidates = {r['face_index']:r for r in records[key]['candidate_faces']}; rows = []
        for index, piece in enumerate(source['pieces']):
            if piece['replacement'] != 'plane_slab':
                continue
            need(piece['kind'] == 'face' and piece['index'] in candidates, 'original V6 plane piece source differs')
            old_certificate = source['face_certificates'][piece['face_certificate_index']]
            stationary = box(old_certificate['stationary_original_box_exact'])
            prefix = {'piece_index':index,'original_face_index':piece['index'],'model_index':next_index,
                      'source_face_canonical_sha256':candidates[piece['index']]['complete_original_face_canonical_sha256']}
            next_index += 1
            try:
                record = dict(prefix,**face_model(candidates[piece['index']],stationary,D if side == 0 else zero,limits))
            except ValueError as exc:
                record = dict(prefix,applied=False,retained_original_plane_reason=str(exc),
                              conditional_planar_exterior_model_only=True,native_planar_region_semantics_verified=False)
            rows.append(record)
            if record['applied']:
                models[(side,index)] = runtime_model(record); total_pieces += len(record['uv_boundary_pieces']); applied += 1
            else:
                rejected += 1
        serialized['sources'].append({'material_key':list(key),'models':rows})
    need(total_pieces <= limits['maximum_total_UV_pieces'], 'complete fixed UV source capacity exceeded')
    serialized.update(applied_plane_model_count=applied,rejected_plane_model_count=rejected,
                      total_UV_boundary_piece_count=total_pieces)
    return models, serialized


def count_inequality(counters, limits, planar):
    if counters['support_inequality_tests'] >= limits['maximum_support_inequality_tests']:
        return False
    counters['support_inequality_tests'] += 1
    if planar:
        counters['UV_support_inequality_tests'] += 1
    return True


def closed_piece_separator(piece, channel, counters, limits):
    if counters['boundary_box_tests'] >= limits['maximum_boundary_box_tests']:
        return 'budget'
    counters['boundary_box_tests'] += 1; counters['UV_boundary_piece_tests'] += 1
    for axis in range(2):
        for end in range(2):
            if not count_inequality(counters,limits,True):
                return 'budget'
            if (channel[axis][1] < piece['box'][axis][0]) if end == 0 else (channel[axis][0] > piece['box'][axis][1]):
                return str(2*axis+end)
    for normal, bounds in piece['slabs']:
        mapped = project(normal,channel)
        for end in range(2):
            if not count_inequality(counters,limits,True):
                return 'budget'
            if (mapped[1] < bounds[0]) if end == 0 else (mapped[0] > bounds[1]):
                return str(4+end)
    return None


def planar_channel_exclusion(model, spatial_channel, counters, limits):
    stationary = [(max(spatial_channel[k][0]-model['D'][k][1],model['stationary'][k][0]),
                   min(spatial_channel[k][1]-model['D'][k][0],model['stationary'][k][1])) for k in range(3)]
    need(not any(a > b for a,b in stationary), 'empty stationary candidate must already be separated by the old spatial AABB rule')
    target = affine_project(model['inverse'],model['origin'],stationary)
    failures = []
    for axis in range(2):
        for end in range(2):
            counters['UV_channels_tested'] += 1
            channel = list(target)
            channel[axis] = (min(target[axis][0],model['known'][axis][0]-1),target[axis][1]) if end == 0 else (target[axis][0],max(target[axis][1],model['known'][axis][1]+1))
            codes = []; blocked = False
            for piece_index, piece in enumerate(model['pieces']):
                code = closed_piece_separator(piece,channel,counters,limits)
                if code == 'budget':
                    return {'excluded':False,'search_stopped_at_predicate_budget':True,'model_index':model['model_index'],
                            'stationary_candidate_box_exact':encbox(stationary),'closed_UV_target_box_exact':encbox(target),
                            'completed_unresolved_UV_channels':failures,
                            'incomplete_UV_channel':{'axis':axis,'end':end,'closed_UV_channel_exact':encbox(channel),
                                                     'piece_index_at_stop':piece_index,'completed_piece_prefix_count':len(codes)}}
                if code is None:
                    blocked = True
                    failures.append({'axis':axis,'end':end,'closed_UV_channel_exact':encbox(channel),'unresolved_UV_piece_index':piece_index})
                    break
                codes.append(code)
            if not blocked:
                need(len(codes) == len(model['pieces']), 'complete UV boundary cover must be separated')
                proof = {'kind':'complete_closed_UV_exterior_channel','model_index':model['model_index'],
                        'stationary_candidate_box_exact':encbox(stationary),'closed_UV_target_box_exact':encbox(target),
                        'axis':axis,'end':end,'closed_UV_channel_exact':encbox(channel),
                        'complete_UV_piece_separation_codes':''.join(codes),'UV_boundary_piece_count':len(codes),
                        'strict_closed_separation':True,'sampled_region_classification_used':False,
                        'bounded_region_complete_boundary_cover_is_model_premise':True}
                return {'excluded':True,'certificate':proof}
    return {'excluded':False,'model_index':model['model_index'],'stationary_candidate_box_exact':encbox(stationary),
            'closed_UV_target_box_exact':encbox(target),'all_closed_UV_channels_unresolved':failures,
            'actual_material_membership_claimed':False}
