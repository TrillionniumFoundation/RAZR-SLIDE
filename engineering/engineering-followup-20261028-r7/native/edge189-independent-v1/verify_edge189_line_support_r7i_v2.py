"""Independent exact corner checker for the frozen edge189 diagnostic.

Only the serialized affine Line model is checked.  Native BREP realization,
compiled-evaluator error and physical uncertainty are not certified here.
The caller must bind reader_edge, original_carrier and full_D to the original
independent-reader/certificate bytes before calling this pure function.

Static cost bound per complete call: 16 nominal and 128 hypothetical vertices;
at most 6,144 non-source validation debits (including conservatively charged
arithmetic).  Six calls are at most 864 vertices / 36,864 validation debits.
Source/hash binding work is reported separately through source_* labels.
"""
from fractions import Fraction
import hashlib
import itertools
import json


SCHEMA = 'razr-r7e-edge189-line-support-claim-v1'
EDGE_SHA256 = 'cd8fe627c479422cdc843f171751e6d956fc99e26e3a41a832c1fe359fc7e128'
IDENTITY = [['1', '0', '0', '0'], ['0', '1', '0', '0'], ['0', '0', '1', '0']]
FIXED_D = [['0', '0'], ['0', '1/2251799813685248'], ['0', '0']]
STATIC_MAX_VALIDATION_DEBITS_PER_CALL = 6144
STATIC_MAX_VERTICES_PER_CALL = 144


class ClaimError(ValueError):
    def __init__(self, code, message, counters):
        super().__init__(code + ': ' + message)
        self.code = code
        self.local_counters = dict(counters)


def verify_claim(claim, reader_edge, original_carrier, full_D, counter=None):
    """Check a claim without importing its producer or any geometry helper.

Wrong claims raise ClaimError with a stable code.  An unequal original AABB,
or its failure to contain the hypothetical tolerance tube, is returned as an
explicit negative observation, not converted into a claim-formula exception.
"""
    counts = {}

    def debit(label, count=1):
        counts[label] = counts.get(label, 0) + count
        if counter is not None:
            counter(label, count)

    def fail(code, message):
        raise ClaimError(code, message, counts)

    def source_need(condition, code, message):
        debit('source_binding_checks')
        if not condition:
            fail(code, message)

    def q(value):
        if not isinstance(value, str):
            fail('invalid_exact_rational', 'Exact quantities must be original rational strings')
        try:
            return Fraction(value)
        except (ValueError, ZeroDivisionError, TypeError) as exc:
            fail('invalid_exact_rational', str(exc))

    def eq(a, b):
        debit('validation_comparisons')
        return a == b

    def le(a, b):
        debit('validation_comparisons')
        return a <= b

    def need_equal(a, b, code, message):
        if not eq(a, b):
            fail(code, message)

    def vec(values, length):
        source_need(isinstance(values, list) and len(values) == length,
                    'invalid_claim_schema', 'Exact vector dimension differs')
        return [q(x) for x in values]

    def box(values):
        source_need(isinstance(values, list) and len(values) == 3,
                    'invalid_claim_schema', 'Three-coordinate box required')
        result = [vec(row, 2) for row in values]
        for lo, hi in result:
            if not le(lo, hi):
                fail('invalid_ordered_domain', 'Closed box endpoint order differs')
        return result

    def canonical(value):
        try:
            data = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        except (TypeError, ValueError) as exc:
            fail('invalid_source_encoding', str(exc))
        debit('source_serialization_bytes', len(data))
        return hashlib.sha256(data).hexdigest()

    source_need(isinstance(claim, dict), 'invalid_claim_schema', 'Object claim required')
    source_need(claim.get('schema') == SCHEMA and claim.get('material_key') == ['case-028', 3]
                and claim.get('piece_index') == 332, 'invalid_claim_schema', 'Frozen diagnostic identity differs')
    source_need(canonical(reader_edge) == EDGE_SHA256, 'source_edge_identity', 'Independent original edge identity differs')
    source_need(claim.get('complete_original_edge') == reader_edge, 'source_edge_identity', 'Complete original edge fields differ')
    source_need(claim.get('complete_original_edge_canonical_sha256') == EDGE_SHA256,
                'source_edge_identity', 'Complete original edge canonical binding differs')
    source_need(full_D == FIXED_D and claim.get('full_D_exact') == full_D,
                'source_full_D_identity', 'Complete original displacement domain differs')
    source_need(claim.get('complete_original_carrier') == original_carrier,
                'source_carrier_identity', 'Complete inherited carrier differs')
    source_need(original_carrier.get('kind') == 'edge' and original_carrier.get('index') == 189
                and original_carrier.get('additional_slabs') == [],
                'source_carrier_identity', 'Original empty-slab edge carrier required')
    source_need(claim.get('normal_exact') == ['1', '2', '0'], 'fixed_normal', 'Registered fixed normal differs')
    source_need(claim.get('native_BREP_error_bound_certified') is False,
                'native_scope_escalation', 'Native BREP error certification is outside this diagnostic')
    source_need(reader_edge.get('location', {}).get('matrix_3x4_exact') == IDENTITY
                and reader_edge['location'].get('identity') is True,
                'source_placement_identity', 'Complete original identity placement required')
    curve = reader_edge['native_global_curve']
    source_need(reader_edge['local_curve'] == curve and curve['type'] == 'GeomAbs_CurveType.GeomAbs_Line'
                and curve['IsPeriodic'] is False and reader_edge['degenerated'] is False,
                'source_line_identity', 'Complete nonperiodic original Line required')
    O, V = vec(curve['origin_exact'], 3), vec(curve['direction_exact'], 3)
    first, last = q(curve['first_parameter']['exact']), q(curve['last_parameter']['exact'])
    source_need(V[2] != 0, 'source_edge_identity', 'Original nonzero z direction must remain present')
    if not le(first, last):
        fail('invalid_ordered_domain', 'Original full parameter interval is reversed')
    D, B = box(full_D), box(original_carrier['box_exact'])
    n = [Fraction(1), Fraction(2), Fraction(0)]
    debit('geometry_arithmetic_upper_operations', 24)
    dotV = sum(n[k] * V[k] for k in range(3))
    constant = sum(n[k] * O[k] for k in range(3))
    need_equal(dotV, 0, 'normal_direction_identity', 'Fixed normal is not orthogonal to the complete 3D direction')
    need_equal(q(claim['normal_dot_direction_exact']), dotV, 'normal_direction_identity', 'Claimed normal-direction identity differs')
    need_equal(q(claim['line_dot_constant_exact']), constant, 'line_constant_identity', 'Claimed line constant differs')
    tau = q(reader_edge['tolerance']['exact'])
    if not le(0, tau):
        fail('source_tolerance_identity', 'Original tolerance field is negative')
    need_equal(q(claim['tau_exact']), tau, 'source_tolerance_identity', 'Original tolerance field differs')
    debit('geometry_arithmetic_upper_operations', 8)
    expansion = tau * sum(abs(x) for x in n)
    need_equal(q(claim['tau_L1_expansion_exact']), expansion, 'tau_expansion_identity', 'Conditional infinity-norm expansion differs')

    def inside(point):
        decisions = []
        for axis in range(3):
            decisions.append(le(B[axis][0], point[axis]))
            decisions.append(le(point[axis], B[axis][1]))
        return all(decisions)

    def enumerate_vertices(hypothetical):
        rows, extrema, projected = [], None, None
        error_selectors = tuple(itertools.product((0, 1), repeat=3)) if hypothetical else (None,)
        for ti, t in enumerate((first, last)):
            for di in itertools.product((0, 1), repeat=3):
                d = [D[k][di[k]] for k in range(3)]
                for ei in error_selectors:
                    debit('hypothetical_tube_vertices' if hypothetical else 'exact_vertices')
                    debit('geometry_arithmetic_upper_operations', 24)
                    error = [(-tau if ei[k] == 0 else tau) for k in range(3)] if hypothetical else [Fraction(0)] * 3
                    point = [O[k] + t * V[k] + d[k] + error[k] for k in range(3)]
                    dot = sum(n[k] * point[k] for k in range(3))
                    if extrema is None:
                        extrema = [[x, x] for x in point]
                        projected = [dot, dot]
                    else:
                        for k in range(3):
                            if le(point[k], extrema[k][0]):
                                extrema[k][0] = point[k]
                            if le(extrema[k][1], point[k]):
                                extrema[k][1] = point[k]
                        if le(dot, projected[0]):
                            projected[0] = dot
                        if le(projected[1], dot):
                            projected[1] = dot
                    row = {'t_endpoint_index': ti, 't_exact': str(t),
                           'D_corner_selector': list(di), 'D_corner_exact': [str(x) for x in d],
                           'point_exact': [str(x) for x in point], 'normal_dot_exact': str(dot),
                           'inside_original_carrier_box': inside(point)}
                    if hypothetical:
                        row.update(error_corner_selector=list(ei), error_corner_exact=[str(x) for x in error])
                    rows.append(row)
        return rows, extrema, projected

    exact_rows, G, exact_bounds = enumerate_vertices(False)
    exact_claim = vec(claim['exact_slab_bounds_exact'], 2)
    for k in range(2):
        need_equal(exact_claim[k], exact_bounds[k], 'exact_support_16_vertices', 'Claimed exact support differs from all 16 nominal corners')
    claimed_G = box(claim['forward_source_box_exact'])
    for axis in range(3):
        for end in range(2):
            need_equal(claimed_G[axis][end], G[axis][end], 'forward_source_box_16_vertices', 'Complete three-dimensional source box differs')
    tube_rows, tube_box, tube_bounds = enumerate_vertices(True)
    tau_claim = vec(claim['tau_expanded_slab_bounds_exact'], 2)
    for k in range(2):
        need_equal(tau_claim[k], tube_bounds[k], 'tau_support_128_vertices', 'Claimed conditional support differs from all 128 tube corners')
    claimed_tube = box(claim['hypothetical_tube_box_exact'])
    for axis in range(3):
        for end in range(2):
            need_equal(claimed_tube[axis][end], tube_box[axis][end], 'hypothetical_tube_box_128_vertices', 'Claimed hypothetical tube box differs')
    for row in exact_rows:
        value = q(row['normal_dot_exact'])
        if not all((le(exact_bounds[0], value), le(value, exact_bounds[1]))):
            fail('exact_support_16_vertices', 'Nominal corner lies outside independently computed slab')
        if not all((le(tube_bounds[0], value), le(value, tube_bounds[1]))):
            fail('tau_support_128_vertices', 'Nominal corner lies outside expanded slab')
    for row in tube_rows:
        value = q(row['normal_dot_exact'])
        if not all((le(tube_bounds[0], value), le(value, tube_bounds[1]))):
            fail('tau_support_128_vertices', 'Hypothetical tube corner lies outside independently computed slab')
    equality = [eq(G[k][end], B[k][end]) for k in range(3) for end in range(2)]
    debits = sum(value for label, value in counts.items() if not label.startswith('source_') and not label.endswith('_vertices'))
    if debits > STATIC_MAX_VALIDATION_DEBITS_PER_CALL:
        fail('independent_validation_debit_bound', 'Static per-call validation debit bound exceeded')
    return {
        'schema': 'razr-r7i-edge189-independent-corner-verification-v1',
        'claim_verified': True, 'normal_exact': [str(x) for x in n],
        'forward_source_box_exact': [[str(x) for x in interval] for interval in G],
        'exact_slab_bounds_exact': [str(x) for x in exact_bounds],
        'tau_expanded_slab_bounds_exact': [str(x) for x in tube_bounds],
        'hypothetical_tube_box_exact': [[str(x) for x in interval] for interval in tube_box],
        'source_box_equals_original_carrier': all(equality),
        'bare_source_contained_in_original_carrier_box': all(row['inside_original_carrier_box'] for row in exact_rows),
        'hypothetical_tube_contained_in_original_carrier': all(row['inside_original_carrier_box'] for row in tube_rows),
        'exact_vertices': exact_rows, 'hypothetical_tube_vertices': tube_rows,
        'tube_slab_contains_hypothetical_tube': True,
        'original_box_intersection_claim': 'Only the bare exact Line+D is covered when the original-box gate holds; the intersection is not automatically an enclosure of the full hypothetical tolerance tube.',
        'hypothetical_error_assumption': 'Coordinatewise |error_i| <= the recorded tau, introduced solely as an explicit mathematical hypothesis.',
        'native_BREP_error_bound_certified': False,
        'native_BREP_or_compiled_primitive_membership_certified': False,
        'producer_or_geometry_helper_imported': False,
        'local_counters': counts, 'validation_debits': debits,
        'static_max_validation_debits_per_call': STATIC_MAX_VALIDATION_DEBITS_PER_CALL,
        'native_operations': 0,
    }
