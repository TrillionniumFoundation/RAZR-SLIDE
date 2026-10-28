"""Independent certificate reader: no imports from either producer or native CAD.

Rebuild complete stored-parameterization supports, exact intersection volumes,
and (when present) complete slab partitions and cell coverage. All arithmetic
is rational. Native material semantics and compiled error bounds stay open.
"""
import argparse
import copy
from fractions import Fraction as Q
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import resource
import sys
import time
import traceback


TOL = Q(1e-7)
AXES = ((Q(1), Q(0), Q(0)), (Q(0), Q(1), Q(0)), (Q(0), Q(0), Q(1)))


def check(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def number(x):
    return Q(x['exact']) if isinstance(x, dict) else Q(x)


def vector(x):
    return tuple(map(number, x))


def product(a, b):
    return sum((x*y for x, y in zip(a, b)), Q(0))


def exterior(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def bounds(x):
    a, b = map(number, x); check(a <= b, 'unordered source range'); return a, b


def upper_root(x):
    # Independent integer bisection, followed by a checked square inequality.
    check(x >= 0, 'negative radicand')
    denominator = 2**128
    numerator = x.numerator * denominator * denominator
    divisor = x.denominator
    low = 0; high = 1 << ((max(1, numerator.bit_length()-divisor.bit_length()+1)+1)//2+1)
    while high*high*divisor < numerator:
        high *= 2
    while high-low > 1:
        middle = (low+high)//2
        if middle*middle*divisor < numerator:
            low = middle
        else:
            high = middle
    k = 0 if numerator == 0 else high
    answer = Q(k, denominator)
    check(answer*answer >= x and (k == 0 or Q(k-1, denominator)**2 < x), 'directed radical is not the least dyadic upper bound')
    return answer


def linear_range(direction, ranges):
    a = b = Q(0)
    for coefficient, (left, right) in zip(direction, ranges):
        u, v = coefficient*left, coefficient*right
        a += min(u, v); b += max(u, v)
    return a, b


def curve_range(curve, normal):
    a, b = bounds([curve['first_parameter'], curve['last_parameter']])
    tag = curve['type'].rsplit('.', 1)[-1]
    if tag == 'GeomAbs_Line':
        origin = product(vector(curve['origin_exact']), normal)
        direction = product(vector(curve['direction_exact']), normal)
        return min(origin+direction*a, origin+direction*b), max(origin+direction*a, origin+direction*b)
    if tag == 'GeomAbs_Circle':
        radius = number(curve['radius']); check(radius > 0, 'circle radius')
        centre = product(vector(curve['center_exact']), normal)
        extent = radius*upper_root(product(vector(curve['X_exact']), normal)**2 + product(vector(curve['Y_exact']), normal)**2)
        return centre-extent, centre+extent
    check(tag == 'GeomAbs_BSplineCurve' and curve.get('complete_supported_representation') is True, 'unsupported or incomplete exact curve')
    data = curve['bspline']
    check(data['degree'] == 1 and not data['is_periodic'] and not data['is_rational'] and data['multiplicities'] == [2, 2], 'BSpline subclass')
    poles = list(map(vector, data['poles_exact'])); knots = list(map(number, data['knots_exact'])); weights = list(map(number, data['weights_exact']))
    check(len(poles) == len(knots) == len(weights) == 2 and weights[0] == weights[1] > 0 and knots[0] < knots[1], 'BSpline complete two-pole data')
    check(number(data['defined_first_parameter']) == knots[0] and number(data['defined_last_parameter']) == knots[1], 'BSpline source definition range')
    check(all(len(p) == len(normal) == data['dimension'] for p in poles), 'BSpline dimension')
    y0, y1 = (product(p, normal) for p in poles)
    slope = (y1-y0)/(knots[1]-knots[0])
    values = [y0+(t-knots[0])*slope for t in (a, b)]
    return min(values), max(values)


def domain(face):
    surface = face['local_surface']
    ranges = [bounds(surface[name]) for name in ('U_interval', 'V_interval')]
    check(face['wires'], 'missing complete trim loops')
    for wire in face['wires']:
        check(wire['native_IsClosed'] and wire['edge_occurrences'], 'trim loop closure metadata')
        for occurrence in wire['edge_occurrences']:
            check(occurrence['edge_index'] is not None, 'unmapped pcurve edge')
            for axis in (0, 1):
                n = (Q(axis == 0), Q(axis == 1))
                lo, hi = curve_range(occurrence['pcurve'], n)
                ranges[axis] = min(ranges[axis][0], lo), max(ranges[axis][1], hi)
    return ranges


def complete_support(boundary, normal):
    result = {}
    for face in boundary['faces']:
        surface = face['local_surface']; uv = domain(face)
        centre = product(vector(surface['origin_exact']), normal)
        if surface['type'].endswith('GeomAbs_Plane'):
            lo, hi = linear_range([product(vector(surface['X_exact']), normal), product(vector(surface['Y_exact']), normal)], uv)
            lo += centre; hi += centre
        else:
            check(surface['type'].endswith('GeomAbs_Cylinder'), 'unsupported source surface')
            radius = number(surface['radius']); check(radius > 0, 'cylinder radius')
            extent = radius*upper_root(product(vector(surface['X_exact']), normal)**2+product(vector(surface['Y_exact']), normal)**2)
            lo, hi = linear_range([product(vector(surface['axis_exact']), normal)], [uv[1]])
            lo += centre-extent; hi += centre+extent
        result['face', face['index']] = lo, hi
    for edge in boundary['edges']:
        result['edge', edge['index']] = curve_range(edge['local_curve'], normal)
    for vertex in boundary['vertices']:
        value = product(vector(vertex['local_point_exact']), normal)
        result['vertex', vertex['index']] = value, value
    return result


def check_boundary_metadata(boundary):
    check(not boundary['incomplete_inventory'] and boundary['counts']['solids'] == 1 and boundary['original_whole_material_guard']['passed'], 'original complete material guard')
    expected = [['1','0','0','0'],['0','1','0','0'],['0','0','1','0']]
    check(boundary['location']['matrix_3x4_exact'] == expected, 'material placement')
    for name in ('solids', 'shells', 'faces', 'edges', 'vertices'):
        rows = boundary[name]
        check(len(rows) == boundary['counts'][name] and [r['index'] for r in rows] == list(range(len(rows))), 'complete contiguous original '+name)
        check(all(r['location']['matrix_3x4_exact'] == expected for r in rows), 'subshape placement')
    check(all(s['Closed_flag'] for s in boundary['shells']), 'shell closure metadata')
    check(sorted(i for s in boundary['shells'] for i in s['face_indices']) == list(range(boundary['counts']['faces'])), 'shell complete face coverage')
    for face in boundary['faces']:
        for wire in face['wires']:
            check(wire['location']['matrix_3x4_exact'] == expected, 'wire placement')
            for occurrence in wire['edge_occurrences']:
                check(occurrence['location']['matrix_3x4_exact'] == expected, 'edge occurrence placement')


def verify_support(source, certificate, cache):
    check(source['input'] == certificate['input'], 'support original material identity')
    n = vector(certificate['normal_exact']); check(len(n) == 3 and any(n), 'valid support normal')
    key = source['input']['case_id'], source['input']['material_id'], n
    if key not in cache:
        cache[key] = complete_support(source['boundary'], n)
    needed = cache[key]
    supplied = {(r['kind'], r['index']): bounds(r['support_exact']) for r in certificate['pieces']}
    check(len(supplied) == len(certificate['pieces']) == certificate['complete_piece_count'] == len(needed) and supplied.keys() == needed.keys(), 'certificate complete face/edge/vertex coverage')
    for k, (lo, hi) in needed.items():
        check(supplied[k][0] <= lo <= hi <= supplied[k][1], 'source piece escapes supplied support '+str(k))
    check(bounds(certificate['support_exact']) == (min(x[0] for x in supplied.values()), max(x[1] for x in supplied.values())), 'aggregate complete support')
    return n, supplied, bounds(certificate['support_exact'])


def enclose_check(certificate, supports, displacement, tolerances):
    rows = list(map(vector, certificate['basis_rows_exact']))
    det = product(rows[0], exterior(rows[1], rows[2]))
    check(det != 0 and Q(certificate['basis_determinant_exact']) == det, 'exact basis determinant')
    ranges = [[], []]
    check(list(map(Q, certificate['uncertainty_inflation_exact_mm'])) == list(tolerances), 'uncertainty model changed')
    for k, n in enumerate(rows):
        for side in (0, 1):
            lo, hi = supports[side][n]['range']
            shift = linear_range(n, displacement) if side == 0 else (Q(0), Q(0))
            expansion = tolerances[side]*upper_root(product(n, n))
            ranges[side].append((lo+shift[0]-expansion, hi+shift[1]+expansion))
    check(list(map(bounds, certificate['moving_coordinate_intervals_exact'])) == ranges[0] and list(map(bounds, certificate['fixed_coordinate_intervals_exact'])) == ranges[1], 'entire displacement coordinate support differs')
    intersection = [(max(a[0], b[0]), min(a[1], b[1])) for a, b in zip(*ranges)]
    check([[str(x) for x in pair] for pair in intersection] == certificate['coordinate_intersection_intervals_exact'], 'coordinate intersection')
    volume = Q(0) if any(a >= b for a, b in intersection) else (intersection[0][1]-intersection[0][0])*(intersection[1][1]-intersection[1][0])*(intersection[2][1]-intersection[2][0])/abs(det)
    check(Q(certificate['exact_intersection_upper_mm3']) == volume and certificate['original_clearance_gate_passed'] == (volume <= TOL) and Q(certificate['original_clearance_threshold_exact_mm3']) == TOL, 'exact upper or original threshold')
    return volume


def topology_check(enclosure, certificate):
    value = Q(enclosure['exact_intersection_upper_mm3'])
    check(Q(certificate['oriented_volume_exact']) == value, 'declared directed volume')
    if value == 0:
        check(not certificate['positive_3D_solid_claimed'], 'zero set called positive solid'); return
    vertices = list(map(vector, certificate['vertices_exact'])); triangles = certificate['outward_triangles']
    check(len(vertices) == 8 and len(set(vertices)) == 8 and len(triangles) == 12, 'parallelepiped topology sizes')
    rows = list(map(vector, enclosure['basis_rows_exact'])); ranges = list(map(bounds, enclosure['coordinate_intersection_intervals_exact']))
    mapped = {tuple(product(n, v) for n in rows) for v in vertices}
    check(mapped == set(itertools.product(*ranges)), 'all corners and only corners map to the exact support bounds')
    incidence = {}; directed = Q(0)
    for tri in triangles:
        check(len(set(tri)) == 3 and all(isinstance(i, int) and 0 <= i < 8 for i in tri), 'triangle indices')
        a, b, c = (vertices[i] for i in tri)
        normal = exterior(tuple(y-x for x, y in zip(a, b)), tuple(y-x for x, y in zip(a, c)))
        check(any(normal) and all(product(normal, tuple(y-x for x, y in zip(a, v))) <= 0 for v in vertices), 'outward embedded convex triangle')
        directed += product(a, exterior(b, c))/6
        for i, j in zip(tri, (*tri[1:], tri[0])):
            incidence[i, j] = incidence.get((i, j), 0)+1
    check(all(v == 1 and incidence.get((b, a)) == 1 for (a, b), v in incidence.items()) and 8-len(incidence)//2+12 == 2 and directed == value > 0, 'closed oriented exact carrier volume')


def meet(*boxes):
    return tuple((max(b[k][0] for b in boxes), min(b[k][1] for b in boxes)) for k in range(3))


def box_volume(box):
    return Q(0) if any(a >= b for a, b in box) else (box[0][1]-box[0][0])*(box[1][1]-box[1][0])*(box[2][1]-box[2][0])


def box_decode(box):
    return tuple(tuple(map(Q, pair)) for pair in box)


def verify_slabs(proof, supports, displacement, tolerances, self_case=False):
    boundary_boxes = []
    for side, name in enumerate(('first_complete_boundary_boxes', 'second_complete_boundary_boxes')):
        if self_case:
            support = supports[0]; shift = [(Q(0), Q(0))]*3
        else:
            support = supports[side]; shift = displacement if side == 0 else [(Q(0), Q(0))]*3
        keys = support[AXES[0]]['pieces'].keys()
        actual = {(p['kind'], p['index']): box_decode(p['box_exact']) for p in proof[name]}
        check(len(actual) == len(proof[name]) and actual.keys() == keys, 'slab complete boundary coverage')
        expected = {key: tuple((support[n]['pieces'][key][0]+shift[axis][0]-tolerances[side], support[n]['pieces'][key][1]+shift[axis][1]+tolerances[side]) for axis, n in enumerate(AXES)) for key in keys}
        check(actual == expected, 'slab boundary boxes do not equal independently checked complete supports plus full displacement')
        boundary_boxes.append([box_decode(p['box_exact']) for p in proof[name]])
    whole = [tuple((min(b[k][0] for b in boxes), max(b[k][1] for b in boxes)) for k in range(3)) for boxes in boundary_boxes]
    pair_domain = meet(*whole)
    check(pair_domain == box_decode(proof['global_intersection_box_exact']), 'global slab domain')
    if not box_volume(pair_domain):
        check(Q(proof['combined']['sum_directed_volume_exact']) == 0 and not proof['combined']['positive_cells'], 'empty global domain gained volume')
        return Q(0)
    positive = []
    for axis, cover in enumerate(proof['axis_covers']):
        check(cover['axis'] == axis and cover['cut_planes_retained_as_zero_volume_closed_carriers'] and box_decode(cover['cut_plane_transverse_bounds_exact']) == pair_domain, 'complete retained cut planes')
        lo, hi = pair_domain[axis]
        cuts = sorted({lo, hi} | {v for material in boundary_boxes for b in material for v in b[axis] if lo < v < hi})
        check(list(map(Q, cover['cuts_exact'])) == cuts and len(cover['all_open_slab_records']) == len(cuts)-1, 'all boundary endpoint cuts')
        rows = {}; subtotal = Q(0)
        for index, (a, b) in enumerate(zip(cuts, cuts[1:])):
            record = cover['all_open_slab_records'][index]
            check(record['index'] == index and list(map(Q, record['open_interval_exact'])) == [a, b], 'open slab order')
            active = [[j for j, box in enumerate(material) if box[axis][0] < b and box[axis][1] > a] for material in boundary_boxes]
            check(record['active_piece_indices'] == active, 'active boundary piece omission')
            if not all(active):
                check(Q(record['volume_exact']) == 0, 'empty boundary section volume'); continue
            hulls = []
            for material, ids in zip(boundary_boxes, active):
                hull = [(min(material[j][k][0] for j in ids), max(material[j][k][1] for j in ids)) for k in range(3)]
                hull[axis] = a, b; hulls.append(tuple(hull))
            region = meet(*hulls, pair_domain); volume = box_volume(region)
            check([box_decode(x) for x in record['material_section_outer_boxes_exact']] == hulls and box_decode(record['intersection_outer_box_exact']) == region and Q(record['volume_exact']) == volume, 'section outer-box arithmetic')
            if volume:
                rows[index] = region; subtotal += volume
        check(Q(cover['sum_positive_volume_exact']) == subtotal, 'axis cover total')
        positive.append(rows)
    check(len(positive) == 3, 'all three independent coordinate coverings required')
    key_field = 'slab_index_xyz'
    if 'exact_positive_slab_box_union_runs' in proof['combined']:
        compressed = []
        run_lists = proof['combined']['exact_positive_slab_box_union_runs']
        check(len(run_lists) == 3 and proof['combined']['all_fine_boundary_cuts_retained'] and Q(proof['combined']['unit_cube_template_directed_volume_exact']) == 1, 'fine cut planes or affine unit-cube template lost')
        for axis, runs in enumerate(run_lists):
            accumulated = []; mapped = {}
            for index, run in enumerate(runs):
                check(run['axis'] == axis and run['run_index'] == index and run['fine_slab_indices'], 'exact union run identity')
                fine_ids = run['fine_slab_indices']; boxes = [positive[axis][i] for i in fine_ids]
                check(fine_ids == sorted(fine_ids) and len(fine_ids) == len(set(fine_ids)), 'fine slab duplicate or reorder')
                check(all(boxes[j][axis][1] == boxes[j+1][axis][0] for j in range(len(boxes)-1)), 'merged run contains positive-width gap')
                check(all(all(box[k] == boxes[0][k] for k in range(3) if k != axis) for box in boxes), 'merged transverse bounds changed')
                union = list(boxes[0]); union[axis] = boxes[0][axis][0], boxes[-1][axis][1]
                check(box_decode(run['box_exact']) == tuple(union), 'run not exact original positive-box union')
                accumulated += fine_ids; mapped[index] = tuple(union)
            check(accumulated == sorted(positive[axis]), 'some positive fine slabs omitted or duplicated')
            compressed.append(mapped)
        positive = compressed; key_field = 'slab_run_index_xyz'
    supplied = {tuple(c[key_field]): c for c in proof['combined']['positive_cells']}
    check(len(supplied) == len(proof['combined']['positive_cells']), 'duplicate positive cell')
    found = set(); total = Q(0); enumeration_checks = 0
    # Independent exhaustive order is always X/Y/Z, not the producer's
    # count-selected ordering. Every positive triple must appear exactly once.
    for x, a in positive[0].items():
        for y, b in positive[1].items():
            first = meet(a, b)
            if not box_volume(first):
                continue
            for z, c in positive[2].items():
                enumeration_checks += 1
                cell = meet(first, c); volume = box_volume(cell)
                if not volume:
                    continue
                key = x, y, z; check(key in supplied, 'positive exact cell omitted')
                saved = supplied[key]
                check(box_decode(saved['box_exact']) == cell and Q(saved['positive_directed_volume_exact']) == volume, 'positive cell bounds or directed volume')
                # Positive diagonal affine image of the outward unit cube:
                # exact determinant equals product of the three positive widths.
                check(all(a < b for a, b in cell), 'nonpositive affine cell determinant')
                if key_field == 'slab_run_index_xyz':
                    check(list(map(Q, saved['affine_diagonal_exact'])) == [b-a for a,b in cell], 'registered positive affine cell map')
                found.add(key); total += volume
    check(found == supplied.keys() and Q(proof['combined']['sum_directed_volume_exact']) == total and proof['combined']['all_partition_boundary_planes_retained'], 'complete cell enumeration or exact total')
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=False)
    contract = json.loads(args.contract.read_text())
    check(digest(__file__) == contract['verifier_sha256'], 'verifier registration')
    started = time.monotonic(); report = {'schema': 'razr-r4e-independent-exact-material-certificate-verification-v2-union-runs', 'execution_completed': False, 'frames': [], 'native_Common_called': False, 'producer_code_imported': False, 'native_boundary_semantics_verified': False, 'compiled_error_bound_verified': False, 'full_continuous_G2': False}
    def save():
        report['seconds'] = time.monotonic()-started; report['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    try:
        for item in contract['input_files']:
            p = Path(item['path']); check(p.stat().st_size == item['bytes'] and digest(p) == item['sha256'], 'registered original or certificate input identity')
        original = Path(contract['original_root']); certificate_root = Path(contract['certificate_root'])
        native = json.loads((original/'native-and-math/producer/worker/report.json').read_text())
        by = {(r['input']['case_id'], r['input']['material_id']): r for r in native['operands']}
        for supplement_path in contract['supplement_paths']:
            supplement = json.loads(Path(supplement_path).read_text()); check(supplement['execution_completed'], 'supplement incomplete')
            for item in supplement['records']:
                boundary = by[item['input']['case_id'], item['input']['material_id']]['boundary']
                check(hashlib.sha256(json.dumps(boundary, sort_keys=True, separators=(',', ':')).encode()).hexdigest() == item['original_complete_boundary_canonical_sha256'], 'supplement original complete boundary binding')
                for row in item['complete_pcurves']:
                    target = boundary['faces'][row['face_index']]['wires'][row['wire_index']]['edge_occurrences'][row['occurrence_index']]
                    check(target['edge_index'] == row['edge_index'] and target['pcurve'] == row['old_pcurve_record'], 'supplement occurrence mapping')
                    target['pcurve'] = row['complete_pcurve_record']
        supplied = json.loads((certificate_root/'report.json').read_text()); check(supplied['execution_completed'] and len(supplied['frames']) == 16, 'complete producer16 required')
        originals = {(r['case_id'], r['frame']): r for r in native['tiny_base_Common']}; cache = {}; checked_materials = set()
        for frame in supplied['frames']:
            native_frame = originals[frame['case_id'], frame['frame']]
            path = certificate_root/frame['proof']['path']; check(digest(path) == frame['proof']['sha256'], 'proof payload changed')
            with gzip.open(path, 'rt') as stream:
                proof = json.load(stream)
            check(proof['full_remaining_displacement_box_exact'] == native_frame['full_remaining_displacement_box_exact'], 'original full displacement changed')
            displacement = list(map(bounds, proof['full_remaining_displacement_box_exact']))
            sources = [by[frame['case_id'], native_frame['moving_saved_material_id']], by[frame['case_id'], native_frame['fixed_original_material_id']]]
            for source in sources:
                key = source['input']['case_id'], source['input']['material_id']
                if key not in checked_materials:
                    check_boundary_metadata(source['boundary']); checked_materials.add(key)
            supports = [{}, {}]
            for record in proof['complete_support_proofs']:
                for side, label in enumerate(('moving', 'fixed')):
                    n, pieces, total = verify_support(sources[side], record[label], cache)
                    check(n not in supports[side], 'duplicate complete support normal')
                    supports[side][n] = {'pieces': pieces, 'range': total}
            tolerances = [max(number(r['tolerance']) for name in ('faces', 'edges', 'vertices') for r in source['boundary'][name]) for source in sources]
            raw = enclose_check(proof['selected_exact_representation_enclosure'], supports, displacement, [Q(0), Q(0)])
            inflated = enclose_check(proof['selected_declared_tolerance_diagnostic'], supports, displacement, tolerances)
            topology_check(proof['selected_exact_representation_enclosure'], proof['exact_representation_enclosure_topology'])
            topology_check(proof['selected_declared_tolerance_diagnostic'], proof['declared_tolerance_enclosure_topology'])
            if 'complete_raw_boundary_slab_cover' in proof:
                raw = min(raw, verify_slabs(proof['complete_raw_boundary_slab_cover'], supports, displacement, [Q(0), Q(0)]))
                inflated = min(inflated, verify_slabs(proof['complete_declared_tolerance_boundary_slab_cover'], supports, displacement, tolerances))
                negative = verify_slabs(proof['complete_whole_self_boundary_slab_negative_control'], supports, displacement, [Q(0), Q(0)], True)
                check(negative > TOL, 'slab whole-self false clearance')
            check(Q(frame['conditional_complete_material_intersection_upper_exact_mm3']) == raw and frame['original_clearance_gate_passed'] == (raw <= TOL), 'frame raw original gate')
            check(Q(frame['declared_tolerance_diagnostic_upper_exact_mm3']) == inflated and frame['declared_tolerance_diagnostic_gate_passed'] == (inflated <= TOL), 'frame declared tolerance diagnostic gate')
            check(frame['original_min_volume_plus_TOL_gate_passed'] == (raw <= Q(native_frame['original_rounded_min_plus_TOL_mm3'])), 'original min-volume upper gate')
            report['frames'].append({'case_id': frame['case_id'], 'frame': frame['frame'], 'all_complete_piece_supports_independently_verified': True,
                'complete_remaining_displacement_verified': True, 'valid_exact_carrier_and_directed_volume_verified': True, 'raw_bound_exact_mm3': str(raw), 'original_clearance_gate_passed': raw <= TOL,
                'declared_tolerance_bound_exact_mm3': str(inflated), 'declared_tolerance_gate_passed': inflated <= TOL, 'slab_certificate_present': 'complete_raw_boundary_slab_cover' in proof,
                'base_Common_soundness_used': False, 'native_material_semantics_proved': False})
            save()
            print(json.dumps({'case': frame['case_id'], 'frame': frame['frame'], 'independently_verified': True, 'raw_gate': raw <= TOL}), flush=True)
        report['independent_source_support_count'] = len(cache); report['complete_original_material_count'] = len(checked_materials)
        report['conditional_clearance_passes'] = sum(r['original_clearance_gate_passed'] for r in report['frames'])
        report['declared_tolerance_diagnostic_passes'] = sum(r['declared_tolerance_gate_passed'] for r in report['frames'])
        check(digest(__file__) == contract['verifier_sha256'] and all(digest(r['path']) == r['sha256'] for r in contract['input_files']), 'postflight input or source identity')
        report['execution_completed'] = True
    except BaseException as exc:
        report['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    save(); print(json.dumps({k: report.get(k) for k in ('execution_completed', 'failure', 'conditional_clearance_passes', 'seconds', 'peak_RSS_bytes')}), flush=True)
    return 0 if report['execution_completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
