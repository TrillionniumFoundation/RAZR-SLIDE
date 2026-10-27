"""Recompute source scalar telescope guards and exact conservative outer vertices.

This is pure rational and binary64 source analysis after local-state loss.
No CAD module, whole factory, physical specimen or solver is executed.
"""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as F
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import sys
import time

S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"
PINNED = {
    "cam_coupling.py": "4a3bf1d2b86d31fa8e3d60d3412e15548bf42287ed95d756798f3d88c6c4e631",
    "product_assembly.py": "fc5391d3be98810ada06ca27e65de9a77d2f599c4d1890bb31a4d87ef14791b4",
    "verify_cam_coupling.py": "ffe16f403b104bfdf58897ed3ece1313b9bb82863569ba68f60617467b2841f1",
    "product_nominal_motion.py": "ad4c7d04092c7b6e118c0415ce77bdf4ee60ee335317c5da101bd1a98353f271",
    "cpython_3_12_14_bltinmodule.c": "368b677db85bd846fc85271d6e7170ee8e529230bd1ea352d16ccef0a75787e0"}
E = F(1, 2**48)
D = F.from_float(8.2)
LOWER = F.from_float(.1 - 1e-7)
UPPER = F.from_float(2.9 + 1e-7)
H = F.from_float(1e-7) + 14 * E
VARIABLES = ["d", "jL1", "jL2", "jL3", "jR1", "jR2", "jR3"]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def fraction_record(x):
    return {"exact": str(x), "float": float(x)}

def selected_function(source, name):
    return next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name)

def source_guard(source, function, message):
    fn = selected_function(source, function)
    for node in ast.walk(fn):
        if isinstance(node, ast.If) and any(
            isinstance(x, ast.Constant) and x.value == message
            for statement in node.body if isinstance(statement, ast.Raise) for x in ast.walk(statement)):
            return {"source_expression": ast.get_source_segment(source, node.test),
                    "line": node.lineno, "code": compile(ast.Expression(node.test), "<pinned-scalar-guard>", "eval")}
    raise ValueError("original scalar guard not found")

def outer_groups(dmax, lower, upper, halfwidth):
    normals = [tuple(1 if i == j else 0 for i in range(7)) for j in range(7)]
    normals += [(1, 1, 1, 1, 0, 0, 0), (1, 0, 0, 0, 1, 1, 1)]
    lo = [F(0)] + [lower] * 6 + [F(17, 2) - halfwidth] * 2
    hi = [dmax] + [upper] * 6 + [F(17, 2) + halfwidth] * 2
    return normals, lo, hi

def inverse(matrix):
    size = len(matrix)
    a = [[F(v) for v in row] + [F(i == j) for j in range(size)] for i, row in enumerate(matrix)]
    for col in range(size):
        pivot = next((k for k in range(col, size) if a[k][col]), None)
        if pivot is None:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        divisor = a[col][col]
        a[col] = [v / divisor for v in a[col]]
        for row in range(size):
            if row != col and a[row][col]:
                factor = a[row][col]
                a[row] = [x - factor * y for x, y in zip(a[row], a[col])]
    return [row[size:] for row in a]

def feasible(point, normals, lo, hi):
    for normal, low, high in zip(normals, lo, hi):
        value = sum((point[i] for i, coefficient in enumerate(normal) if coefficient), F(0))
        if not low <= value <= high:
            return False
    return True

def active_basis_enumeration(dmax, lower, upper, halfwidth):
    normals, lo, hi = outer_groups(dmax, lower, upper, halfwidth)
    vertices, singular, feasible_occurrences = set(), 0, 0
    for groups in itertools.combinations(range(9), 7):
        inv = inverse([normals[k] for k in groups])
        if inv is None:
            singular += 2**7
            continue
        for ends in itertools.product((0, 1), repeat=7):
            b = [hi[k] if end else lo[k] for k, end in zip(groups, ends)]
            point = tuple(sum((a * value for a, value in zip(row, b)), F(0)) for row in inv)
            if feasible(point, normals, lo, hi):
                feasible_occurrences += 1
                vertices.add(point)
    return vertices, {"all_18_choose_7_active_sets": math.comb(18, 7),
                      "opposite_normal_dependent_sets_eliminated": math.comb(18, 7) - math.comb(9, 7) * 2**7,
                      "remaining_active_sets": math.comb(9, 7) * 2**7,
                      "singular_active_sets": singular, "feasible_active_set_occurrences": feasible_occurrences}

def integer_rank(rows):
    a = [list(row) for row in rows]
    rank = 0
    for column in range(7):
        pivot = next((k for k in range(rank, len(a)) if a[k][column]), None)
        if pivot is None:
            continue
        a[rank], a[pivot] = a[pivot], a[rank]
        for row in range(rank + 1, len(a)):
            if a[row][column]:
                coefficient, factor = a[rank][column], a[row][column]
                a[row] = [coefficient * x - factor * y for x, y in zip(a[row], a[rank])]
                common = 0
                for value in a[row]:
                    common = math.gcd(common, abs(value))
                if common:
                    a[row] = [value // common for value in a[row]]
        rank += 1
        if rank == 7:
            break
    return rank

def clipped_cube_vertices(d, lower, upper, halfwidth):
    low, high = F(17, 2) - d - halfwidth, F(17, 2) - d + halfwidth
    vertices = {tuple(p) for p in itertools.product((lower, upper), repeat=3) if low <= sum(p) <= high}
    for free in range(3):
        fixed = [i for i in range(3) if i != free]
        for ends in itertools.product((lower, upper), repeat=2):
            for plane in (low, high):
                value = plane - sum(ends)
                if lower <= value <= upper:
                    p = [None] * 3
                    for index, bound in zip(fixed, ends):
                        p[index] = bound
                    p[free] = value
                    vertices.add(tuple(p))
    return vertices

def independent_sliced_cube_enumeration(dmax, lower, upper, halfwidth):
    normals, lo, hi = outer_groups(dmax, lower, upper, halfwidth)
    levels = {F(0), dmax}
    for upper_count in range(4):
        corner_sum = upper_count * upper + (3 - upper_count) * lower
        for plane in (F(17, 2) - halfwidth, F(17, 2) + halfwidth):
            d = plane - corner_sum
            if 0 <= d <= dmax:
                levels.add(d)
    result, candidates = set(), 0
    for d in sorted(levels):
        side_vertices = clipped_cube_vertices(d, lower, upper, halfwidth)
        for left, right in itertools.product(side_vertices, repeat=2):
            point = (d,) + left + right
            candidates += 1
            if not feasible(point, normals, lo, hi):
                continue
            active = []
            for normal, low, high in zip(normals, lo, hi):
                value = sum((point[i] for i, c in enumerate(normal) if c), F(0))
                if value == low or value == high:
                    active.append(normal)
            if integer_rank(active) == 7:
                result.add(point)
    return result, {"critical_shared_d_levels": [str(v) for v in sorted(levels)],
                    "slice_product_candidates_checked": candidates,
                    "rank_filter_uses_fraction_free_integer_elimination": True}

def enumerate_and_check(dmax, lower, upper, halfwidth):
    a, astats = active_basis_enumeration(dmax, lower, upper, halfwidth)
    b, bstats = independent_sliced_cube_enumeration(dmax, lower, upper, halfwidth)
    require(a == b, "two independent exact vertex methods disagree")
    groups, lo, hi = outer_groups(dmax, lower, upper, halfwidth)
    require(all(feasible(p, groups, lo, hi) for p in a), "infeasible reported outer vertex")
    layers = Counter(p[0] for p in a)
    return {"vertex_count": len(a), "method_A": astats, "method_B": bstats,
            "exact_vertex_sets_equal": True,
            "layers": [{"d_exact": str(d), "d_float": float(d), "vertices": n} for d, n in sorted(layers.items())],
            "vertices_exact": [[str(x) for x in p] for p in sorted(a)]}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    args = ap.parse_args()
    started = time.monotonic()
    root, source_dir = args.root, args.root / "source"
    require(platform.python_implementation() == "CPython" and sys.version_info[:3] == (3, 12, 14)
            and sys.float_info.mant_dig == 53, "original binary64/CPython sum environment not matched")
    sources = {}
    for name, expected in PINNED.items():
        data = (source_dir / name).read_bytes()
        require(sha(data) == expected, "pinned source identity differs")
        sources[name] = data.decode()
    expected_constants = {
        "cam_coupling.py": {"STROKE": 79.75, "SEATING": 8.2, "STAGE_MIN": .1, "STAGE_MAX": 2.9},
        "product_assembly.py": {"TOL": 1e-7}, "verify_cam_coupling.py": {"TOL": 1e-7}}
    verified_constants = {}
    for filename, expected in expected_constants.items():
        actual = {}
        for node in ast.parse(sources[filename]).body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in expected:
                        actual[target.id] = ast.literal_eval(node.value)
        require(actual == expected, "pinned scalar global constants differ")
        verified_constants[filename] = actual
    native = source_guard(sources["product_assembly.py"], "native_scene", "invalid independent telescope allocation")
    prototype = source_guard(sources["verify_cam_coupling.py"], "prototype", "invalid telescope allocation")
    helper_joint = source_guard(sources["cam_coupling.py"], "stage_allocation", "captured telescope joint overtravel")
    helper_sum = source_guard(sources["cam_coupling.py"], "stage_allocation", "head is not captured at B cam plane")
    def check(d, joints):
        env = {"values": joints, "descent_mm": d, "TOL": 1e-7,
               "j": joints, "z": 8.2 - d, "q": joints, "STAGE_MIN": .1, "STAGE_MAX": 2.9,
               "p": {"B_Z_mm": 8.2 - d}}
        passes = {"native_scene_scalar_guard_pass": not eval(native["code"], env, env),
                  "prototype_scalar_guard_pass": not eval(prototype["code"], env, env),
                  "stage_allocation_joint_guard_pass": not eval(helper_joint["code"], env, env),
                  "stage_allocation_sum_guard_pass": not eval(helper_sum["code"], env, env)}
        passes["stage_allocation_scalar_guards_pass"] = passes["stage_allocation_joint_guard_pass"] and passes["stage_allocation_sum_guard_pass"]
        exact = sum((F.from_float(x) for x in joints), F(0)) + F.from_float(d) - F(17, 2)
        native_r = sum(joints) - 8.5 + d
        proto_r = sum(joints) - .3 - (8.2 - d)
        helper_r = sum(joints) - 3 * .1 - (8.2 - d)
        in_outer = all(LOWER <= F.from_float(x) <= UPPER for x in joints) and abs(exact) <= H
        if passes["native_scene_scalar_guard_pass"] and passes["prototype_scalar_guard_pass"]:
            require(in_outer, "source accepted scalar example outside proven outer")
        return {"descent_mm": d, "joints_mm": joints, "joint_binary64_hex": [x.hex() for x in joints],
                **passes, "native_residual_mm": native_r, "prototype_residual_mm": proto_r,
                "stage_allocation_residual_mm": helper_r, "exact_real_sum_residual": str(exact),
                "inside_conservative_outer": in_outer,
                "full_factory_native_construction_executed": False}
    cases = [
        ("nominal_predock", 0., [.1 + 8.2 / 3] * 3),
        ("nominal_seated", 8.2, [.1] * 3),
        ("lower_joint_thin_layer", 8.2, [.1 - 5e-8, .1 + 5e-8, .1]),
        ("upper_joint_thin_layer", 0., [2.9 + 5e-8, 2.8 - 5e-8, 2.8]),
        ("positive_sum_thin_layer", 1., [2.5, 2.5, 2.50000002]),
        ("negative_sum_thin_layer", 1., [2.5, 2.5, 2.49999998]),
        ("native_pass_prototype_reject", 1., [2.5, 2.5, 2.500000099999999]),
        ("native_reject_prototype_would_pass", 1., [2.5, 2.5, 2.4999998999999997]),
        ("upper_joint_outside", 0., [2.9000002, 2.7999998, 2.8]),
        ("lower_joint_outside", 8.2, [.0999998, .1000002, .1]),
        ("positive_sum_outside", 1., [2.5, 2.5, 2.5000002]),
        ("negative_sum_outside", 1., [2.5, 2.5, 2.4999998]),
        ("exact_native_upper_joint_boundary", 0., [2.9 + 1e-7, 2.8 - 1e-7, 2.8]),
        ("exact_native_lower_joint_boundary", 8.2, [.1 - 1e-7, .1 + 1e-7, .1])]
    examples = [{"name": name, **check(d, j)} for name, d, j in cases]
    by_name = {row["name"]: row for row in examples}
    require(by_name["native_pass_prototype_reject"]["native_scene_scalar_guard_pass"] is True and
            by_name["native_pass_prototype_reject"]["prototype_scalar_guard_pass"] is False,
            "first original evaluation-order counterexample was not reproduced")
    require(by_name["native_reject_prototype_would_pass"]["native_scene_scalar_guard_pass"] is False and
            by_name["native_reject_prototype_would_pass"]["prototype_scalar_guard_pass"] is True,
            "second original evaluation-order counterexample was not reproduced")
    require(by_name["lower_joint_thin_layer"]["stage_allocation_scalar_guards_pass"] is False and
            by_name["lower_joint_thin_layer"]["native_scene_scalar_guard_pass"] is True and
            by_name["lower_joint_thin_layer"]["prototype_scalar_guard_pass"] is True,
            "strict-helper/full-source mismatch was not reproduced")
    outer = enumerate_and_check(D, LOWER, UPPER, H)
    ideal = enumerate_and_check(F(41, 5), F(1, 10), F(29, 10), F(0))
    require(outer["vertex_count"] == 216 and [r["vertices"] for r in outer["layers"]] == [36, 27, 45, 45, 27, 36],
            "conservative outer vertex inventory differs")
    require(outer["method_A"]["feasible_active_set_occurrences"] == 468 and
            outer["method_A"]["singular_active_sets"] == 1536, "outer active-basis accounting differs")
    require(ideal["vertex_count"] == 28 and [r["vertices"] for r in ideal["layers"]] == [9, 9, 9, 1],
            "ideal zero-width control differs")
    source_records = [{"name": name, "sha256": digest, "bytes": len(sources[name].encode())} for name, digest in PINNED.items()]
    functions = {}
    for label, guard in (("native_scene", native), ("prototype", prototype),
                         ("stage_allocation_joint", helper_joint), ("stage_allocation_sum", helper_sum)):
        functions[label] = {k: v for k, v in guard.items() if k != "code"}
    domain = {"schema": "razr-rebuilt-S4-telescope-binary64-source-domain-v1",
        "functional_source_commit": S4, "analysis_source_sha256": sha(Path(__file__).read_bytes()),
        "source_identities": source_records, "runtime_CPython_version": platform.python_version(),
        "original_AST_global_constants_verified": verified_constants,
        "original_guard_AST_expressions": functions,
        "three_distinct_contracts": {
            "standalone_stage_allocation": {"joint_tolerance_mm": 1e-9, "sum_tolerance_mm": 1e-8,
                "exact_sum_expression": "sum(q)-3*STAGE_MIN-p['B_Z_mm']"},
            "ideal_planner": {"uses_exact_decimal_fixed_sum_polytope": True,
                "allocation_reconstruction": "[nominal+first, nominal+second, nominal-first-second]",
                "joint_only_tolerance_mm": 1e-9, "explicit_sum_residual_guard_in_reconstruction": False},
            "explicit_joint_full_source_route": {
                "route": ["product_scene", "native_scene scalar predicate", "cam.prototype scalar predicate"],
                "telescope_offsets_are_passed_as_full_independent_three_joint_arrays": True,
                "standalone_stage_allocation_is_not_called_on_explicit_joint_array": True,
                "both_original_scalar_evaluation_orders_retained": True,
                "native_and_prototype_joint_tolerance_mm": 1e-7,
                "source_scalar_acceptance_is_not_whole_native_construction_or_physical_acceptance": True}},
        "actual_original_scalar_examples": examples,
        "outer": {"variables": VARIABLES, "continuous_dimension": 7, "halfspace_count": 18,
                  "descent_limits": ["0", str(D)], "joint_limits": [str(LOWER), str(UPPER)],
                  "exact_sum_center": "17/2", "exact_sum_halfwidth": fraction_record(H),
                  "side_sum_constraint": "abs(d+jS1+jS2+jS3-17/2)<=H independently for S=L,R"},
        "conservative_arithmetic_basis": {
            "binary64_each_operation_absolute_error_bound_E": str(E),
            "all_relevant_arithmetic_intermediates_have_abs_less_than": 32,
            "CPython_three_float_sum_running_total_error_at_most_E": 2,
            "per_compensation_update_term_magnitude_at_most_E": 3,
            "two_compensation_accumulations_magnitude_at_most_E": 8,
            "final_compensated_sum_absolute_error_at_most_E": 11,
            "native_residual_two_additional_operations_total_at_most_E": 13,
            "strict_closed_outer_uses_extra_E": 14,
            "native_outer_is_conservative_before_later_prototype_guard": True,
            "prototype_and_any_later_constructor_can_only_reduce_accepted_set": True,
            "CPython_C_source_was_read_and_hashed_not_executed": True,
            "CPython_source_URL": "https://raw.githubusercontent.com/python/cpython/v3.12.14/Python/bltinmodule.c",
            "prefix_Z_final_addition_and_strict_margin_absolute_error_at_most_E": 13,
            "exact_prefix_sum_bounds_for_m": [
                "max(m*lo,17/2-d-H-(3-m)*hi)",
                "min(m*hi,17/2-d+H-(3-m)*lo)"]},
        "dimensions_and_limits": {"ideal_zero_width_joint_projection_dimension": 5,
            "ideal_zero_width_joint_projection_vertices": 28, "conservative_joint_outer_vertices": 216,
            "full_independent_SLIDE_continuous_control_relaxation_dimension": 15,
            "full_independent_SEATING_continuous_control_relaxation_dimension": 15,
            "full_control_count_basis": "one phase coordinate + two tabs + two flanks + two KEY offsets + two crosshead offsets + six joints",
            "binary64_accepted_input_set_itself_is_discrete": True,
            "216_vertices_are_not_native_accepted_witnesses": True,
            "source_outer_is_not_a_physical_allowed_domain": True,
            "K3_ten_finite_state_passes_do_not_certify_this_outer": True},
        "recovery": {"original_pinned_source_bytes_recovered": True,
            "old_unpublished_analysis_and_vertex_reports_recovered_exactly": False,
            "new_pure_original_AST_evaluation_and_two_exact_enumerations_executed": True,
            "prior_domain_report_sha256_from_session_history": "e7f9362d5019d05c97c07f24dea8bdaf645b07f7e0f71860b5bf36ef78f1101c",
            "prior_vertex_report_sha256_from_session_history": "59baf98633f9a3d77b11b2e77d6d482058304885a7e604613a3543b0a16560ea"},
        "native_CAD_or_solver_executed": False, "complete_product_motion_proved": False,
        "physical_allowed_domain_proved": False, "strength_qualified": False,
        "candidate_go": False, "fixture_fabrication_go": False, "manufacturing_go": False}
    timestamp = datetime.now(timezone.utc).isoformat()
    domain["recomputed_at_UTC"] = timestamp
    dp = root / "S4_TELESCOPE_BINARY64_SOURCE_DOMAIN_REBUILT.json"
    dp.write_text(json.dumps(domain, indent=2, allow_nan=False) + "\n")
    vertex = {"schema": "razr-rebuilt-exact-telescope-outer-two-method-check-v1",
              "source_domain_report_sha256": sha(dp.read_bytes()), "analysis_source_sha256": sha(Path(__file__).read_bytes()),
              "recomputed_at_UTC": timestamp, "variables": VARIABLES, "outer": outer,
              "ideal_zero_width_control": ideal, "pure_seconds": time.monotonic() - started,
              "same_expected_prior_vertex_counts_reproduced": True, "prior_unpublished_bytes_recovered": False,
              "native_CAD_or_solver_executed": False, "physical_domain_or_full_motion_proved": False}
    vp = root / "S4_TELESCOPE_OUTER_VERTICES_DUAL_CHECK_REBUILT.json"
    vp.write_text(json.dumps(vertex, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"domain_file": dp.name, "domain_sha256": sha(dp.read_bytes()),
                      "vertex_file": vp.name, "vertex_sha256": sha(vp.read_bytes()),
                      "outer_vertices": outer["vertex_count"], "ideal_vertices": ideal["vertex_count"],
                      "outer_layers": outer["layers"], "pure_seconds": vertex["pure_seconds"],
                      "native_executed": False}, indent=2))

if __name__ == "__main__":
    main()
