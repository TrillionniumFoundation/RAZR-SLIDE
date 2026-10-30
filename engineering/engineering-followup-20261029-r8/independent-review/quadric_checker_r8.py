"""Independent exact cylindrical-support checker for the R8 source model.

No imports from the producer, its geometric helpers, CadQuery, or OCP.
The full untrimmed cylinder is a superset of every original angular/axial
patch.  This checker does not certify native BREP material semantics.
"""
from fractions import Fraction
from itertools import product
import hashlib
import json

F = Fraction
IDENTITY = [["1", "0", "0", "0"], ["0", "1", "0", "0"], ["0", "0", "1", "0"]]


def require(condition, stage):
    if not condition:
        raise ValueError(stage)


def rational(x):
    return F(x["exact"] if isinstance(x, dict) else x)


def vector(x):
    return tuple(rational(v) for v in x)


def bounds(x):
    out = tuple(tuple(rational(v) for v in row) for row in x)
    require(len(out) == 3 and all(len(row) == 2 and row[0] <= row[1] for row in out), "ordered_box")
    return out


def canonical(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def inner(a, b):
    return sum((x * y for x, y in zip(a, b)), F(0))


def wedge(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def solve_nonsingular(matrix, rhs):
    """Independent rational Gauss-Jordan elimination; singular faces skipped."""
    n = len(rhs)
    rows = [list(matrix[i]) + [rhs[i]] for i in range(n)]
    for column in range(n):
        pivot = next((r for r in range(column, n) if rows[r][column]), None)
        if pivot is None:
            return None
        rows[column], rows[pivot] = rows[pivot], rows[column]
        divisor = rows[column][column]
        rows[column] = [x / divisor for x in rows[column]]
        for r in range(n):
            if r != column:
                multiplier = rows[r][column]
                rows[r] = [x - multiplier * y for x, y in zip(rows[r], rows[column])]
    return tuple(row[-1] for row in rows)


def duals(basis):
    origin, X, Y, Z = (vector(basis[name]) for name in ("origin", "X", "Y", "Z"))
    require(all(len(x) == 3 for x in (origin, X, Y, Z)), "basis_dimension")
    radius = rational(basis["radius"])
    require(radius > 0, "positive_radius")
    determinant = inner(X, wedge(Y, Z))
    require(determinant != 0, "nonsingular_basis")
    a = tuple(x / determinant for x in wedge(Y, Z))
    b = tuple(x / determinant for x in wedge(Z, X))
    require((inner(a, X), inner(a, Y), inner(a, Z)) == (1, 0, 0), "dual_a_identity")
    require((inner(b, X), inner(b, Y), inner(b, Z)) == (0, 1, 0), "dual_b_identity")
    return origin, a, b, radius


def bound_quadric(basis, query_box):
    """Exact minimum/maximum of rank-two PSD Q on a three-dimensional box.

    For the minimum, enumerate all 27 faces (free/lower/upper per coordinate).
    A singular stationary face has a flat direction reaching a proper face
    with the same objective, so nonsingular stationary faces plus vertices
    contain a global minimizer.  Maxima of a convex function occur at vertices.
    """
    query_box = bounds(query_box)
    origin, a, b, radius = duals(basis)
    Q = [[a[i] * a[j] + b[i] * b[j] for j in range(3)] for i in range(3)]
    shifted = [(lo - origin[i], hi - origin[i]) for i, (lo, hi) in enumerate(query_box)]

    def objective(p):
        return inner(a, p) ** 2 + inner(b, p) ** 2

    candidates = []
    for statuses in product((-1, 0, 1), repeat=3):
        free = [i for i, v in enumerate(statuses) if v == -1]
        fixed = [i for i, v in enumerate(statuses) if v != -1]
        point = [None if i in free else shifted[i][statuses[i]] for i in range(3)]
        if free:
            A = [[Q[i][j] for j in free] for i in free]
            rhs = [-sum((Q[i][j] * point[j] for j in fixed), F(0)) for i in free]
            solution = solve_nonsingular(A, rhs)
            if solution is None:
                continue
            if any(not (shifted[i][0] <= value <= shifted[i][1]) for i, value in zip(free, solution)):
                continue
            for i, value in zip(free, solution):
                point[i] = value
        candidates.append((objective(point), tuple(point), statuses))
    require(candidates, "nonempty_active_set_candidates")
    lo, minimizer, face = min(candidates, key=lambda row: row[0])
    corners = [tuple(shifted[i][side[i]] for i in range(3)) for side in product((0, 1), repeat=3)]
    hi, maximizer = max(((objective(p), p) for p in corners), key=lambda row: row[0])
    require(0 <= lo <= hi, "psd_order")
    return {
        "lower_exact": str(lo),
        "upper_exact": str(hi),
        "radius_squared_exact": str(radius * radius),
        "minimizer_exact": [str(minimizer[i] + origin[i]) for i in range(3)],
        "maximizer_exact": [str(maximizer[i] + origin[i]) for i in range(3)],
        "active_face": list(face),
        "nonsingular_face_candidates": len(candidates),
        "corner_candidates": 8,
        "classification": "below_radius" if hi < radius * radius else "above_radius" if lo > radius * radius else "unresolved",
        "native_BREP_material_membership_certified": False,
    }


def original_basis(record):
    require(record["location"]["matrix_3x4_exact"] == IDENTITY, "original_record_placement")
    source = record.get("local_surface", record.get("local_curve"))
    require(source is not None, "original_parametric_source")
    if source["type"] == "GeomAbs_SurfaceType.GeomAbs_Cylinder":
        return {"origin": source["origin_exact"], "X": source["X_exact"], "Y": source["Y_exact"],
                "Z": source["axis_exact"], "radius": str(rational(source["radius"]))}
    if source["type"] == "GeomAbs_CurveType.GeomAbs_Circle":
        X, Y = vector(source["X_exact"]), vector(source["Y_exact"])
        # A constructed normal suffices: extending the exact source circle
        # along this vector contains every original point without changing it.
        return {"origin": source["center_exact"], "X": source["X_exact"], "Y": source["Y_exact"],
                "Z": [str(x) for x in wedge(X, Y)], "radius": str(rational(source["radius"]))}
    raise ValueError("unsupported_original_primitive")


def bind_query(claim, original_record, original_piece, full_D):
    require(claim["original_record_canonical_sha256"] == canonical(original_record), "source_record_identity")
    require(claim["original_index"] == original_record["index"] == original_piece["index"], "source_index")
    require(claim["original_kind"] == original_piece["kind"], "source_kind")
    require(original_record["location"]["matrix_3x4_exact"] == IDENTITY, "original_record_placement")
    local = "local_surface" if original_piece["kind"] == "face" else "local_curve"
    global_name = "native_global_surface" if original_piece["kind"] == "face" else "native_global_curve"
    require(original_record[local] == original_record[global_name], "local_global_source_identity")
    require(bounds(claim["full_D_exact"]) == bounds(full_D), "full_D_identity")
    channel, carrier, D = bounds(claim["channel_exact"]), bounds(original_piece["box_exact"]), bounds(full_D)
    intersection = tuple((max(channel[k][0], carrier[k][0]), min(channel[k][1], carrier[k][1])) for k in range(3))
    require(all(a <= b for a, b in intersection), "nonempty_channel_carrier_intersection")
    require(bounds(claim["intersection_box_exact"]) == intersection, "complete_intersection_identity")
    stationary = tuple((intersection[k][0] - D[k][1], intersection[k][1] - D[k][0]) for k in range(3))
    require(bounds(claim["stationary_query_box_exact"]) == stationary, "complete_stationary_query_identity")
    return stationary, original_record[local]


def verify_claim(claim, original_record, original_piece, full_D):
    require(claim["kind"] in ("cylinder_quadric", "GeomAbs_Cylinder", "GeomAbs_Circle"), "claim_kind")
    stationary, source = bind_query(claim, original_record, original_piece, full_D)
    expected = original_basis(original_record)
    actual = claim["basis"]
    require(all(vector(expected[k]) == vector(actual[k]) for k in ("origin", "X", "Y")), "original_basis_identity")
    require(rational(expected["radius"]) == rational(actual["radius"]), "original_radius_identity")
    # A circle may use either its stored original axis or the exact cross
    # product.  Both are accepted only with independent a/b dual identities.
    if "local_surface" in original_record:
        require(vector(expected["Z"]) == vector(actual["Z"]), "original_axis_identity")
    else:
        require(any(vector(actual["Z"])), "circle_extension_axis")
        duals(actual)
    result = bound_quadric(actual, stationary)
    require(rational(claim["radius_squared_exact"]) == rational(result["radius_squared_exact"]), "radius_squared_identity")
    # A fast interval producer can return a wider enclosure.  Independently
    # computed true extrema must lie within it; the classification must be
    # justified by the claimed enclosure itself.
    lower, upper = rational(claim["lower_exact"]), rational(claim["upper_exact"])
    require(lower <= rational(result["lower_exact"]) <= rational(result["upper_exact"]) <= upper, "conservative_quadric_bounds")
    radius2 = rational(result["radius_squared_exact"])
    classification = "below_radius" if upper < radius2 else "above_radius" if lower > radius2 else "unresolved"
    require(claim["classification"] == classification, "strict_quadric_classification")
    result.update(claim_verified=True, claimed_classification=classification)
    return result


def verify_plane_claim(claim, original_record, original_piece, full_D):
    stationary, source = bind_query(claim, original_record, original_piece, full_D)
    require(claim["kind"] == "GeomAbs_Plane" and source["type"] == "GeomAbs_SurfaceType.GeomAbs_Plane", "plane_source_type")
    origin, X, Y = (vector(source[name]) for name in ("origin_exact", "X_exact", "Y_exact"))
    normal = wedge(X, Y)
    require(any(normal), "plane_regular_basis")
    require(vector(claim["normal_exact"]) == normal, "plane_normal_identity")
    support = inner(normal, origin)
    require(rational(claim["support_exact"]) == support, "plane_support_identity")
    values = [inner(normal, tuple(stationary[i][corner[i]] for i in range(3))) for corner in product((0, 1), repeat=3)]
    projected = (min(values), max(values))
    require(vector(claim["query_projection_exact"]) == projected, "plane_query_eight_corners")
    require(projected[1] < support or projected[0] > support, "plane_strict_exclusion")
    return {"claim_verified": True, "independent_corner_count": 8, "native_BREP_material_membership_certified": False}


def verify_line_claim(claim, original_record, original_piece, full_D):
    stationary, source = bind_query(claim, original_record, original_piece, full_D)
    require(claim["kind"] == "GeomAbs_Line" and source["type"] == "GeomAbs_CurveType.GeomAbs_Line", "line_source_type")
    origin, direction = vector(source["origin_exact"]), vector(source["direction_exact"])
    require(any(direction), "line_nonzero_direction")
    low, high = rational(source["first_parameter"]), rational(source["last_parameter"])
    require(low <= high, "original_complete_parameter_domain")
    trace = []
    for axis in range(3):
        if direction[axis] == 0:
            if not stationary[axis][0] <= origin[axis] <= stationary[axis][1]:
                require(claim["empty_axis"] == axis and claim["zero_direction_coordinate_outside"] is True, "line_zero_coordinate_reason")
                require(claim["parameter_trace"] == trace, "line_complete_parameter_trace")
                return {"claim_verified": True, "parameter_axes_checked": axis + 1, "native_BREP_material_membership_certified": False}
            continue
        values = tuple((x - origin[axis]) / direction[axis] for x in stationary[axis])
        interval = (min(values), max(values))
        low, high = max(low, interval[0]), min(high, interval[1])
        trace.append({"axis": axis, "parameter_interval_exact": [str(x) for x in interval], "retained_interval_exact": [str(low), str(high)]})
        if high < low:
            require(claim["empty_axis"] == axis and claim["zero_direction_coordinate_outside"] is False, "line_parameter_infeasibility_reason")
            require(claim["parameter_trace"] == trace, "line_complete_parameter_trace")
            return {"claim_verified": True, "parameter_axes_checked": axis + 1, "native_BREP_material_membership_certified": False}
    raise ValueError("line_nonempty_complete_parameter_intersection")


def verify_source_claim(claim, original_record, original_piece, full_D):
    if claim["code"] == "quadric":
        return verify_claim(claim, original_record, original_piece, full_D)
    if claim["code"] == "plane":
        return verify_plane_claim(claim, original_record, original_piece, full_D)
    if claim["code"] == "line":
        return verify_line_claim(claim, original_record, original_piece, full_D)
    raise ValueError("unsupported_source_claim_code")


def analytic_controls():
    identity = {"origin": ["0"] * 3, "X": ["1", "0", "0"], "Y": ["0", "1", "0"], "Z": ["0", "0", "1"], "radius": "1"}
    tests = [
        ("outer_degenerate_line", [[2, 3], [0, 0], [-1, 1]], "4", "9", "above_radius"),
        ("interior_axis_minimum", [[-1, 1], [-1, 1], [-1, 1]], "0", "2", "unresolved"),
        ("outer_corner_minimum", [[1, 2], [1, 2], [-4, 7]], "2", "8", "above_radius"),
        ("closed_tangent_retained", [[1, 1], [0, 0], [0, 0]], "1", "1", "unresolved"),
        ("strict_inner_box", [[F(-1, 4), F(1, 4)], [F(-1, 4), F(1, 4)], [-2, 3]], "0", "1/8", "below_radius"),
    ]
    records = []
    for label, query, low, high, classification in tests:
        actual = bound_quadric(identity, query)
        require((actual["lower_exact"], actual["upper_exact"], actual["classification"]) == (low, high, classification), label)
        records.append({"name": label, "passed": True, "result": actual})
    skew = {"origin": ["3", "-4", "5"], "X": ["2", "0", "0"], "Y": ["1", "1", "0"], "Z": ["1", "2", "1"], "radius": "1"}
    actual = bound_quadric(skew, [[5, 7], [-4, -4], [5, 5]])
    require((actual["lower_exact"], actual["upper_exact"]) == ("1", "4"), "skew_nonorthonormal_basis")
    records.append({"name": "skew_nonorthonormal_basis", "passed": True, "result": actual})
    singular = dict(identity, Z=["1", "0", "0"])
    try:
        bound_quadric(singular, [[0, 1]] * 3)
    except ValueError as e:
        require(str(e) == "nonsingular_basis", "singular_rejection_reason")
        records.append({"name": "singular_basis_rejected", "passed": True, "reason": str(e)})
    else:
        raise AssertionError("singular_basis_accepted")
    return records


if __name__ == "__main__":
    print(json.dumps({"analytic_controls": analytic_controls()}, indent=2))
