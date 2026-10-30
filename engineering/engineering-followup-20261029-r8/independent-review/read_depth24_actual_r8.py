"""Read the saved R8 local result against the complete original inventories."""
import argparse
from collections import Counter
import copy
from fractions import Fraction as F
import gc
import gzip
import hashlib
from itertools import product
import json
from pathlib import Path
import platform
import resource
import sys
import time
import traceback

import quadric_checker_r8 as independent


def need(value, reason):
    if not value:
        raise ValueError(reason)


def identity(path):
    path = Path(path)
    return {"path": str(path.resolve()), "bytes": path.stat().st_size,
            "sha256": hashlib.file_digest(path.open("rb"), "sha256").hexdigest()}


def measure(B):
    total = F(1)
    for lo, hi in B:
        need(lo < hi, "positive_original_leaf")
        total *= hi - lo
    return total


def locate_original_leaf(certificate, locator):
    root_index, target = locator
    root = certificate["roots"][root_index]
    nodes = root["tree"]["nodes"]
    initial = independent.bounds(root["root_box_exact"])
    pending = [(0, initial, 0)]
    seen = set()
    total = F(0)
    result = None
    while pending:
        index, B, depth = pending.pop()
        need(index not in seen, "original_tree_no_revisit")
        seen.add(index)
        node = nodes[index]
        need(node["id"] == index, "original_tree_node_identity")
        if node["kind"] == "split":
            axis, split = node["axis"], F(node["cut_exact"])
            need(B[axis][0] < split < B[axis][1], "original_internal_split")
            low, high = list(B), list(B)
            low[axis], high[axis] = (B[axis][0], split), (split, B[axis][1])
            left, right = node["children"]
            need(left != right, "original_distinct_children")
            pending.extend([(left, tuple(low), depth + 1), (right, tuple(high), depth + 1)])
        else:
            need(node["kind"] in ("retained", "excluded"), "original_terminal_kind")
            volume = measure(B)
            need(volume == F(node["positive_directed_volume_exact"]), "original_leaf_volume")
            total += volume
            if index == target:
                need(node["kind"] == "retained", "selected_original_retained")
                result = B, depth, volume
    need(len(seen) == len(nodes) and total == measure(initial), "complete_original_tree_partition")
    need(result is not None, "selected_original_leaf_present")
    return result


def channel_of(B, whole, axis, end):
    # Independently derive the complete one-millimeter exterior extension.
    result = list(B)
    if end:
        result[axis] = B[axis][0], max(whole[axis][1], B[axis][1]) + 1
    else:
        result[axis] = min(whole[axis][0], B[axis][0]) - 1, B[axis][1]
    return tuple(result)


def validate_old_code(piece, channel, code):
    carrier = independent.bounds(piece["box_exact"])
    number = int(code)
    need(0 <= number <= 7, "old_separator_code_range")
    if number < 6:
        axis = number // 2
        condition = carrier[axis][1] <= channel[axis][0] if number % 2 == 0 else carrier[axis][0] >= channel[axis][1]
        need(condition, "original_coordinate_separator")
    else:
        slabs = piece["additional_slabs"]
        need(len(slabs) == 1, "original_nonaxis_slab_present")
        normal = independent.vector(slabs[0]["normal_exact"])
        need(any(normal), "original_nonzero_slab")
        values = [independent.inner(normal, tuple(channel[k][corner[k]] for k in range(3))) for corner in product((0, 1), repeat=3)]
        lo, hi = (F(x) for x in slabs[0]["bounds_exact"])
        need(hi <= min(values) if number == 6 else lo >= max(values), "original_nonaxis_separator_eight_corners")


def read_materials(originals):
    entries = []
    provenance = []
    frozen = json.loads((originals / "r7-envelope/edge189-source-diagnostic-v1/R7E_EDGE189_LINE_SUPPORT_DIAGNOSTIC_CONTRACT_V1.json").read_text())
    for role in ("producer", "reader"):
        path = originals / ("r7-recovery/r3e/native-and-math/" + role + "/worker/report.json")
        actual = identity(path)
        expected = frozen["inputs"]["native_original_" + role]
        need(all(actual[k] == expected[k] for k in ("bytes", "sha256")), "full_original_native_inventory_identity")
        document = json.loads(path.read_text())
        need(document["execution_completed"] and len(document["operands"]) == 53, "full_original_native_inventory")
        entries.append({(v["input"]["case_id"], v["input"]["material_id"]): v for v in document["operands"] if v["input"]["case_id"] == "case-028"})
        provenance.append(actual)
        del document
        gc.collect()
    need(entries[0] == entries[1], "full_selected_native_records_producer_reader_identity")
    for record in entries[0].values():
        boundary = record["boundary"]
        need(not boundary["incomplete_inventory"], "complete_native_boundary")
        for plural in ("faces", "edges", "vertices"):
            need(len(boundary[plural]) == boundary["counts"][plural], "complete_native_boundary_census")
    return entries[0], provenance


def validate_result(report, certificate, materials):
    need(report["execution_completed"], "actual_result_completed")
    need(report["new_splits"] == 0 and report["original_depth_limit"] == 24, "unchanged_depth_no_new_split")
    need(report["original_parent"]["locator"] == [78, 375], "fixed_original_parent")
    B, depth, volume = locate_original_leaf(certificate, [78, 375])
    need(depth == report["original_parent"]["depth"] == 24, "original_cumulative_depth24")
    need(independent.bounds(report["original_parent"]["box"]) == B and F(report["original_parent"]["volume"]) == volume, "actual_parent_exact_identity")
    need(F(report["original_TOL_exact"]) == F(1e-7), "original_float64_threshold")
    D = independent.bounds(certificate["frame"]["original_remaining_displacement_box_exact"])
    need(independent.bounds(report["D_exact"]) == D, "original_complete_displacement")
    sources = certificate["boundary_refinement"]["sources"]
    need(report["source_piece_counts"] == [len(s["pieces"]) for s in sources] == [523, 179], "complete_original_piece_census")
    observations = report["result"]["observations"]
    need([(o["material_side"], o["axis"], o["end"]) for o in observations] == list(product(range(2), range(3), range(2))), "complete_ordered_twelve_channels")
    records = []
    verified_claims = []
    counters = Counter()
    for observation in observations:
        side, axis, end = (observation[k] for k in ("material_side", "axis", "end"))
        source = sources[side]
        material_key = tuple(source["material_key"])
        boundary = materials[material_key]["boundary"]
        channel = channel_of(B, independent.bounds(source["known_whole_exact"]), axis, end)
        need(independent.bounds(observation["channel_exact"]) == channel, "complete_original_channel")
        codes = observation["codes"]
        claims = {c["piece_index"]: c for c in observation["new_claims"]}
        need(len(claims) == len(observation["new_claims"]), "unique_piece_claims")
        shift = D if side == 0 else ((F(0), F(0)),) * 3
        used = set()
        for piece_index, code in enumerate(codes):
            need(piece_index < len(source["pieces"]), "piece_code_within_source")
            piece = source["pieces"][piece_index]
            counters["piece_proofs"] += 1
            if code in "01234567":
                validate_old_code(piece, channel, code)
                counters["old_piece_proofs"] += 1
                continue
            need(piece_index in claims, "new_code_has_complete_claim")
            claim = claims[piece_index]
            used.add(piece_index)
            need(claim["material_key"] == list(material_key) and independent.bounds(claim["channel_exact"]) == channel, "claim_material_channel_binding")
            need(code == {"quadric": "Q", "plane": "P", "line": "L", "empty_closed_intersection": "E"}[claim["code"]], "new_piece_code_identity")
            record = boundary["faces" if piece["kind"] == "face" else "edges"][piece["index"]]
            if code == "E":
                carrier = independent.bounds(piece["box_exact"])
                need(any(max(carrier[k][0], channel[k][0]) > min(carrier[k][1], channel[k][1]) for k in range(3)), "empty_closed_intersection")
                result = {"claim_verified": True}
            else:
                result = independent.verify_source_claim(claim, record, piece, shift)
            counters["new_" + claim["code"]] += 1
            verified_claims.append({"material_side": side, "axis": axis, "end": end, "piece_index": piece_index,
                                    "claim_canonical_sha256": independent.canonical(claim), "independent_result": result})
        need(used == set(claims), "no_unconsumed_new_claim")
        failure = observation["failure"]
        if failure is None:
            need(len(codes) == len(source["pieces"]), "complete_successful_channel_piece_coverage")
            counters["complete_successful_channels"] += 1
        else:
            need(failure["piece_index"] == len(codes) < len(source["pieces"]), "failed_channel_prefix_preserved")
            counters["retained_failed_channels"] += 1
        records.append({"material_side": side, "axis": axis, "end": end, "piece_proofs": len(codes), "whole_channel_verified": failure is None})
    need(report["result"]["excluded"] == (counters["complete_successful_channels"] > 0), "exclusion_requires_whole_channel")
    need(report["counts"]["pieces"] == counters["piece_proofs"] + counters["retained_failed_channels"], "actual_piece_work_count")
    need(report["counts"]["new_quadric"] == counters["new_quadric"], "actual_quadric_claim_count")
    need(report["scope"]["full_continuous_G2"] is False and report["scope"]["native_error_bound_verified"] is False and report["scope"]["native_filling_verified"] is False, "conditional_native_scope")
    return {"verified": True, "counts": dict(counters), "channels": records, "new_claims": verified_claims,
            "original_depth24_parent_open_interior_excluded_under_new_source_model": counters["complete_successful_channels"] > 0,
            "new_splits": 0, "native_material_membership_or_full_G2_verified": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--originals", type=Path, required=True)
    parser.add_argument("--producer-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = {"schema": "razr-r8-depth24-independent-actual-readback", "completed": False,
              "python_version": platform.python_version(), "numpy_imported": False,
              "producer_or_geometric_helper_imported": False, "source": identity(__file__),
              "checker_source": identity(independent.__file__), "producer_report": identity(args.producer_report)}
    try:
        report = json.loads(args.producer_report.read_text())
        materials, provenance = read_materials(args.originals)
        original_path = args.originals / "r7-recovery/v7/r5-local-v7/input-snapshot-v1/base-v6/all-primitive-support-frames/case-028-frame-1-primitive-support.json.gz"
        original_report_path = original_path.parent / "report.json"
        original_report = json.loads(original_report_path.read_text())
        row = next(r for r in original_report["frames"] if r["case_id"] == "case-028" and r["frame"] == 1)
        ident = identity(original_path)
        need(all(ident[k] == row["certificate"][k] for k in ("bytes", "sha256")), "original_V6_certificate_identity")
        certificate = json.loads(gzip.decompress(original_path.read_bytes()))
        need(certificate["frame"] == {k: v for k, v in row.items() if k != "certificate"}, "original_V6_report_frame_identity")
        result["inputs"] = provenance + [identity(original_report_path), ident]
        need(report["inputs"] == result["inputs"], "producer_and_reader_same_original_inputs")
        result["actual_readback"] = validate_result(report, certificate, materials)
        result["analytic_controls"] = independent.analytic_controls()

        # Actual mutations of the saved successful result; failures must be
        # mathematical or completeness rejections, not process startup errors.
        controls = []
        success_index = next(i for i, o in enumerate(report["result"]["observations"]) if o["failure"] is None)
        def altered_claim(mutant):
            return mutant["result"]["observations"][success_index]["new_claims"][0]
        mutations = [
            ("missing_successful_piece", lambda m: m["result"]["observations"][success_index].update(codes=m["result"]["observations"][success_index]["codes"][:-1]), "complete_successful_channel_piece_coverage"),
            ("changed_source_radius", lambda m: altered_claim(m)["basis"].update(radius="1"), "original_radius_identity"),
            ("changed_source_record_hash", lambda m: altered_claim(m).update(original_record_canonical_sha256="0" * 64), "source_record_identity"),
            ("overstrong_quadric_lower_bound", lambda m: altered_claim(m).update(lower_exact=str(F(altered_claim(m)["upper_exact"]) + 1)), "conservative_quadric_bounds"),
            ("reversed_quadric_classification", lambda m: altered_claim(m).update(classification="below_radius" if altered_claim(m)["classification"] == "above_radius" else "above_radius"), "strict_quadric_classification"),
            ("changed_claim_displacement", lambda m: altered_claim(m)["full_D_exact"].__setitem__(0, ["0", "1/100000000000000000000"]), "full_D_identity"),
            ("incorrect_original_depth", lambda m: m["original_parent"].update(depth=25), "original_cumulative_depth24"),
        ]
        for name, mutation, expected in mutations:
            mutant = copy.deepcopy(report)
            mutation(mutant)
            failure = None
            try:
                validate_result(mutant, certificate, materials)
            except ValueError as exc:
                failure = str(exc)
            need(failure == expected, "negative_control_expected_rejection:" + name)
            controls.append({"name": name, "actual_rejection": failure, "expected_rejection": expected,
                             "mutated_report_canonical_sha256": independent.canonical(mutant), "passed": True})
        result["actual_mutation_controls"] = controls
        result["all_original_inputs_unchanged"] = all(identity(row["path"]) == row for row in result["inputs"])
        need(result["all_original_inputs_unchanged"], "original_inputs_changed_during_readback")
        result["completed"] = True
    except Exception as exc:
        result["failure"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    result["seconds"] = time.monotonic() - started
    result["peak_RSS_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"completed": result["completed"], "seconds": result["seconds"],
                      "counts": result.get("actual_readback", {}).get("counts"), "failure": result.get("failure")}))
    if not result["completed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
