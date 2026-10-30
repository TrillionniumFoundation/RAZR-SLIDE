"""Read the saved one-cell certificate without importing its producer.

This is a third-party review of one real retained cell and algebraic controls.
It is not a new whole-root calculation, native-CAD certificate or G2 result.
"""
import argparse
from collections import Counter
import copy
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import resource
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
R9 = HERE.parent
R8 = R9.parent / "engineering-followup-20261029-r8" / "independent-review"
sys.path.insert(0, str(R8))
sys.path.insert(0, str(R9 / "envelope"))
import check_cylinder_slab_r9 as checker
import quadric_checker_r8 as exact
from read_all16_actual_r8 import read_all_materials
from read_depth24_actual_r8 import need, measure, identity


def same_file(path, expected):
    observed = identity(path)
    need(all(observed[k] == expected[k] for k in ("bytes", "sha256")), "bound_file_identity")
    return observed


def partition_cell(saved, original, root_index, node_index):
    """Independently reconstruct the complete containing root's partition."""
    root, source = saved["roots"][root_index], original["roots"][root_index]
    box = exact.bounds(source["root_box_exact"])
    need(root["base_V5_leaf_locator"] == source["base_V5_leaf_locator"], "same_original_locator")
    need(exact.bounds(root["root_box_exact"]) == box, "same_original_root")
    nodes = root["nodes"]
    pending = [(0, box, 0)]
    seen = set()
    terminal = F(0)
    selected = None
    while pending:
        i, B, depth = pending.pop()
        need(type(i) is int and 0 <= i < len(nodes) and i not in seen, "unique_tree_node")
        seen.add(i)
        node = nodes[i]
        need(node["id"] == i and node["depth"] == depth <= 24, "node_identity_and_depth")
        need(exact.bounds(node["box_exact"]) == B, "reconstructed_node_box")
        need(F(node["volume_exact"]) == measure(B), "positive_node_volume")
        if node["kind"] == "split":
            axis, cut = node["axis"], F(node["cut_exact"])
            need(type(axis) is int and 0 <= axis < 3, "split_axis")
            need(B[axis][0] < cut < B[axis][1] and cut == sum(B[axis]) / 2, "exact_midpoint")
            children = node["children"]
            need(len(children) == 2 and children[0] != children[1], "distinct_children")
            lo, hi = list(B), list(B)
            lo[axis], hi[axis] = (B[axis][0], cut), (cut, B[axis][1])
            pending.extend(((children[0], tuple(lo), depth + 1), (children[1], tuple(hi), depth + 1)))
        else:
            need(node["kind"] in ("retained", "excluded"), "terminal_kind")
            terminal += measure(B)
        if i == node_index:
            need(node["kind"] == "retained", "selected_real_retained_leaf")
            selected = (B, depth)
    need(len(seen) == len(nodes) and terminal == measure(box), "complete_exact_root_partition")
    need(selected is not None, "actual_leaf_found")
    return selected, {"root_index": root_index, "node_index": node_index,
                      "nodes_reconstructed": len(nodes), "terminal_volume_exact": str(terminal)}


def algebra_controls():
    """Literal analytic examples exercise orientation, shifts and degeneracy."""
    identity_basis = {"origin": ["0"] * 3, "X": ["1", "0", "0"],
                      "Y": ["0", "1", "0"], "Z": ["0", "0", "1"], "radius": "1"}
    zero = ((F(0), F(0)),) * 3
    B = exact.bounds([["-2", "2"], ["-3", "3"], ["0", "5"]])
    controls = []

    def claim(*, bound, L, U, square, root, axial, axial_support, axis, area, width):
        return {"bound_exact": bound, "slab_lower_exact": L,
                "cylinder_support_upper_exact": U, "support_sqrt_radicand_exact": square,
                "support_sqrt_upper_exact": root, "axial_parameter_interval_exact": axial,
                "axial_support_upper_exact": axial_support, "slice_axis": axis,
                "other_axes_area_exact": area, "positive_projection_width_exact": width}

    def accept(name, c, box, basis, shift, normal, lower, expected):
        answer = checker.verify_combination(c, box, basis, shift, tuple(map(F, normal)), F(lower))
        need(answer == F(expected), "analytic_expected_bound:" + name)
        controls.append({"name": name, "passed": True, "expected_bound_exact": expected})

    base = claim(bound="15", L="1/2", U="1", square="1", root="1", axial=["0", "5"],
                 axial_support="0", axis=0, area="30", width="1/2")
    accept("unit_cylinder_axis_slice", base, B, identity_basis, zero, (1, 0, 0), "1/2", "15")
    reverse = claim(bound="15", L="1", U="2", square="4", root="2", axial=["0", "5"],
                    axial_support="0", axis=0, area="30", width="1")
    accept("negative_normal_absolute_jacobian", reverse, B, identity_basis, zero, (-2, 0, 0), "1", "15")
    left_basis = dict(identity_basis, X=["2", "0", "0"], Y=["0", "3", "0"], Z=["0", "0", "-4"])
    left = claim(bound="50", L="1", U="2", square="4", root="2", axial=["-5/4", "0"],
                 axial_support="0", axis=0, area="50", width="1")
    accept("negative_determinant_no_spurious_basis_jacobian", left,
           exact.bounds([["-4", "4"], ["-5", "5"], ["0", "5"]]), left_basis, zero, (1, 0, 0), "1", "50")
    shifted = claim(bound="50", L="27/2", U="14", square="1", root="1", axial=["-4", "7"],
                    axial_support="7", axis=0, area="100", width="1/2")
    accept("full_nonzero_displacement_support", shifted, exact.bounds([["0", "10"]] * 3),
           identity_basis, exact.bounds([["1", "2"], ["-2", "0"], ["3", "4"]]), (1, 0, 1), "27/2", "50")
    for name, lower in (("closed_tangent_zero_volume", "1"), ("strictly_separated_zero_volume", "2")):
        c = dict(base, bound_exact="0", slab_lower_exact=lower, positive_projection_width_exact="0")
        accept(name, c, B, identity_basis, zero, (1, 0, 0), lower, "0")

    for name, c, basis, box, expected in (
        ("unsupported_root", dict(base, support_sqrt_upper_exact="0"), identity_basis, B, "outward_support_square_root"),
        ("zero_slice_denominator", dict(base, slice_axis=2), identity_basis, B, "nonzero_fubini_slice_axis"),
        ("singular_basis", base, dict(identity_basis, Z=["0", "0", "0"]), B, "invertible_original_cylinder_basis"),
        ("inverted_directed_box", base, identity_basis, ((F(2), F(-2)), B[1], B[2]), "positive_original_leaf"),
    ):
        failure = None
        try:
            checker.verify_combination(c, box, basis, zero, (F(1), F(0), F(0)), F(1, 2))
        except ValueError as exc:
            failure = str(exc)
        need(failure == expected, "analytic_specific_rejection:" + name)
        controls.append({"name": name, "passed": True, "expected_rejection": expected, "actual_rejection": failure})
    return controls


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--originals", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    need(not args.output.exists(), "new_review_output_required")
    start = time.monotonic()
    result = {"schema": "razr-r9-independent-cylinder-slab-pilot-review-v1", "completed": False,
              "source": identity(__file__), "checker": identity(checker.__file__),
              "scope": {"one_saved_leaf_only": True, "conditional_source_model_only": True,
                        "whole_root_strategy_executed": False, "native_error_bound_verified": False,
                        "native_filling_verified": False, "native_envelope_topology_verified": False,
                        "full_continuous_G2": False, "all_blockers_closed": False}}
    try:
        pilot_path = R9 / "envelope/cylinder-slab-pilot-attempt1/report.json"
        pilot = json.loads(pilot_path.read_text())
        result["pilot_report"] = identity(pilot_path)
        need(pilot["functional_pass"], "completed_original_pilot")
        same_file(checker.__file__, pilot["checker"])
        result["bound_original_inputs"] = [same_file(x["path"], x) for x in pilot["original_inputs"]]
        base = args.originals / "r7-recovery/v7/r5-local-v7/input-snapshot-v1/base-v6/all-primitive-support-frames"
        originals = json.loads((base / "report.json").read_text())
        row = next(x for x in originals["frames"] if (x["case_id"], x["frame"]) == ("case-037", 2))
        original_path = base / Path(row["certificate"]["path"]).name
        same_file(original_path, row["certificate"])
        original = json.loads(gzip.decompress(original_path.read_bytes()))
        need(original["frame"] == {k: v for k, v in row.items() if k != "certificate"}, "complete_original_frame_header")
        same_file(pilot["saved_tree"]["path"], pilot["saved_tree"])
        saved = json.loads(gzip.decompress(Path(pilot["saved_tree"]["path"]).read_bytes()))
        (B, depth), partition = partition_cell(saved, original, 60, 671)
        result["containing_root_partition"] = partition
        need(exact.bounds(pilot["box_exact"]) == B, "actual_saved_cell_box")
        D = exact.bounds(row["original_remaining_displacement_box_exact"])
        need(exact.bounds(pilot["D_exact"]) == D == exact.bounds(saved["D_exact"]), "same_complete_original_displacement")
        result["complete_original_D_exact"] = row["original_remaining_displacement_box_exact"]
        sources = original["boundary_refinement"]["sources"]
        required = {tuple(s["material_key"]) for s in sources}
        materials, native = read_all_materials(args.originals, required)
        result["independent_native_inventory_readback"] = native
        same_file(pilot["certificate"]["path"], pilot["certificate"])
        proof = json.loads(gzip.decompress(Path(pilot["certificate"]["path"]).read_bytes()))
        counts = Counter()
        bound = checker.verify(proof, B, sources, materials, D, counts)
        need(bound == F(pilot["actual_bound_exact"]), "saved_pilot_bound_agrees")
        need(all(counts[k] == pilot["counts"][k] for k in ("pieces", "channels")), "complete_independent_accounting")
        cylinder_channel = proof["observations"][proof["cylinder_channel"]]
        source = sources[cylinder_channel["material_side"]]
        material = materials[tuple(source["material_key"])]
        original_checks = []
        for index in cylinder_channel["unresolved_piece_indices"]:
            piece = source["pieces"][index]
            rec = checker.source_record(material, piece)
            need(rec["local_surface"] == rec["native_global_surface"], "actual_cylinder_local_global_identity")
            need(rec["index"] == piece["index"], "actual_cylinder_record_index")
            original_checks.append({"piece_index": index, "native_record_index": rec["index"],
                                    "local_global_identical": True})
        result["additional_actual_cylinder_bindings"] = original_checks
        controls = []
        for name, change, expected in (
            ("remove_twelfth_channel", lambda x: x["observations"].pop(), "all_channels_in_family_search"),
            ("remove_piece_code", lambda x: x["observations"][0].__setitem__("codes", x["observations"][0]["codes"][:-1]), "all_source_pieces_covered"),
            ("zero_slab_normal", lambda x: x["slab"].__setitem__("normal_exact", ["0", "0", "0"]), "nonzero_projection_normal"),
        ):
            changed = copy.deepcopy(proof)
            change(changed)
            failure = None
            try:
                checker.verify(changed, B, sources, materials, D, Counter())
            except ValueError as exc:
                failure = str(exc)
            need(failure == expected, "actual_specific_rejection:" + name)
            controls.append({"name": name, "passed": True, "expected_rejection": expected, "actual_rejection": failure})
        # Record the narrow source-binding gap without claiming that the
        # immutable original records or the full saved certificate are bad.
        changed_material = copy.deepcopy(material)
        first = source["pieces"][proof["cylinder"]["piece_index"]]
        changed_record = checker.source_record(changed_material, first)
        changed_record["native_global_surface"]["origin_exact"][0] = str(F(changed_record["native_global_surface"]["origin_exact"][0]) + 1)
        accepted = True
        try:
            checker.verify_cylinder(proof["cylinder"], cylinder_channel, source, changed_material, D)
        except ValueError:
            accepted = False
        result["checker_subroutine_gap"] = {
            "modified_native_global_surface_accepted_by_verify_cylinder": accepted,
            "tested_subroutine_only": True, "original_inputs_modified": False,
            "all_actual_required_local_global_records_equal": True,
            "owner_notified": True}
        result.update(completed=True, counts=counts, actual_saved_depth=depth,
                      actual_leaf_volume_exact=str(measure(B)), independently_verified_bound_exact=str(bound),
                      independently_verified_bound_display_mm3=float(bound),
                      additional_actual_mutation_controls=controls, analytic_controls=algebra_controls(),
                      producer_imported=("cylinder_slab_r9" in sys.modules))
        need(not result["producer_imported"], "no_producer_import")
    except Exception as exc:
        result["completed"] = False
        result["failure"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    result["seconds"] = time.monotonic() - start
    result["peak_RSS_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result.get(k) for k in ("completed", "seconds", "peak_RSS_bytes", "failure")}))
    if not result["completed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
