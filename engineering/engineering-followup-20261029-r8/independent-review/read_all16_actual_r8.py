"""Independent streaming verification of all original retained V6 leaves."""
import argparse
from collections import Counter
from fractions import Fraction as F
import gc
import gzip
import hashlib
from itertools import product, zip_longest
import json
from pathlib import Path
import platform
import resource
import time
import traceback

import quadric_checker_r8 as independent
from read_depth24_actual_r8 import identity, need, measure, channel_of, validate_old_code


def original_retained_leaves(certificate):
    for root_index, root in enumerate(certificate["roots"]):
        nodes = root["tree"]["nodes"]
        visited = set()
        total = F(0)
        def walk(index, B, depth):
            nonlocal total
            need(index not in visited and 0 <= index < len(nodes), "original_tree_unique_node")
            visited.add(index)
            node = nodes[index]
            need(node["id"] == index, "original_tree_node_id")
            if node["kind"] == "split":
                axis, cut = node["axis"], F(node["cut_exact"])
                need(B[axis][0] < cut < B[axis][1], "original_tree_cut_internal")
                left, right = node["children"]
                need(left != right, "original_tree_children_distinct")
                low, high = list(B), list(B)
                low[axis], high[axis] = (B[axis][0], cut), (cut, B[axis][1])
                yield from walk(left, tuple(low), depth + 1)
                yield from walk(right, tuple(high), depth + 1)
            else:
                need(node["kind"] in ("excluded", "retained"), "original_terminal_kind")
                v = measure(B)
                need(v == F(node["positive_directed_volume_exact"]), "original_leaf_volume")
                total += v
                if node["kind"] == "retained":
                    need(depth <= 24, "original_depth_limit")
                    yield (root_index, index), B, depth, v
        original_box = independent.bounds(root["root_box_exact"])
        yield from walk(0, original_box, 0)
        need(len(visited) == len(nodes) and total == measure(original_box), "complete_original_partition")


def read_all_materials(originals, required_keys):
    contract = json.loads((originals / "r7-envelope/edge189-source-diagnostic-v1/R7E_EDGE189_LINE_SUPPORT_DIAGNOSTIC_CONTRACT_V1.json").read_text())
    selected = None
    provenance = []
    for role in ("producer", "reader"):
        p = originals / ("r7-recovery/r3e/native-and-math/" + role + "/worker/report.json")
        actual = identity(p)
        expected = contract["inputs"]["native_original_" + role]
        need(all(actual[k] == expected[k] for k in ("bytes", "sha256")), "native_inventory_original_identity")
        data = json.loads(p.read_text())
        need(data["execution_completed"] and len(data["operands"]) == 53, "native_inventory_complete53")
        extracted = {(r["input"]["case_id"], r["input"]["material_id"]): r for r in data["operands"] if (r["input"]["case_id"], r["input"]["material_id"]) in required_keys}
        need(set(extracted) == required_keys, "all_required_materials_present")
        if selected is None:
            selected = extracted
        else:
            need(selected == extracted, "all_complete_selected_producer_reader_records_agree")
        provenance.append(actual)
        del data, extracted
        gc.collect()
    for material in selected.values():
        boundary = material["boundary"]
        need(not boundary["incomplete_inventory"], "material_boundary_complete")
        for key in ("faces", "edges", "vertices"):
            need(boundary["counts"][key] == len(boundary[key]), "material_boundary_count")
    return selected, provenance


def verify_leaf_channels(result, B, sources, native, D, totals):
    observations = result["observations"]
    order = list(product(range(2), range(3), range(2)))
    need(0 < len(observations) <= 12, "nonempty_channel_prefix")
    need([(o["material_side"], o["axis"], o["end"]) for o in observations] == order[:len(observations)], "ordered_channel_prefix")
    passed = False
    for index, obs in enumerate(observations):
        side, axis, end = order[index]
        source = sources[side]
        material_key = tuple(source["material_key"])
        boundary = native[material_key]["boundary"]
        channel = channel_of(B, independent.bounds(source["known_whole_exact"]), axis, end)
        need(independent.bounds(obs["channel_exact"]) == channel, "whole_exterior_channel_identity")
        shift = D if side == 0 else ((F(0), F(0)),) * 3
        claims = {c["piece_index"]: c for c in obs["new_claims"]}
        need(len(claims) == len(obs["new_claims"]), "unique_channel_claims")
        consumed = set()
        codes = obs["codes"]
        totals["channels"] += 1
        for piece_index, code in enumerate(codes):
            need(piece_index < len(source["pieces"]), "piece_index_in_original_boundary")
            piece = source["pieces"][piece_index]
            totals["piece_proofs"] += 1
            if code in "01234567":
                validate_old_code(piece, channel, code)
                totals["old_piece_proofs"] += 1
                continue
            need(piece_index in claims, "new_piece_proof_present")
            claim = claims[piece_index]
            consumed.add(piece_index)
            need(claim["material_key"] == list(material_key) and independent.bounds(claim["channel_exact"]) == channel, "new_claim_material_and_channel")
            need(code == {"quadric": "Q", "plane": "P", "line": "L", "empty_closed_intersection": "E"}[claim["code"]], "new_claim_code_identity")
            if code == "E":
                carrier = independent.bounds(piece["box_exact"])
                need(any(max(carrier[k][0], channel[k][0]) > min(carrier[k][1], channel[k][1]) for k in range(3)), "closed_intersection_empty")
            else:
                record = boundary["faces" if piece["kind"] == "face" else "edges"][piece["index"]]
                independent.verify_source_claim(claim, record, piece, shift)
            totals["new_" + claim["code"]] += 1
        need(consumed == set(claims), "all_new_claims_consumed")
        if obs["failure"] is None:
            need(len(codes) == len(source["pieces"]), "complete_whole_channel_coverage")
            need(index == len(observations) - 1, "first_success_ends_attempt")
            passed = True
            totals["successful_whole_channels"] += 1
        else:
            need(obs["failure"]["piece_index"] == len(codes) < len(source["pieces"]), "unresolved_piece_prefix")
            totals["failed_channel_prefixes"] += 1
    need(bool(result["excluded"]) == passed, "leaf_exclusion_requires_whole_channel")
    if not passed:
        need(len(observations) == 12, "complete_twelve_failures_retained")
    return passed


def verify_frame(frame, original, certificate, materials, proof_path, threshold, tiny):
    expected_identity = frame["proof"]
    actual = identity(proof_path)
    need(all(actual[k] == expected_identity[k] for k in ("bytes", "sha256")), "complete_proof_bytes_identity")
    sources = certificate["boundary_refinement"]["sources"]
    need(frame["source_piece_counts"] == [len(s["pieces"]) for s in sources], "frame_piece_census")
    D = independent.bounds(original["original_remaining_displacement_box_exact"])
    totals = Counter()
    excluded = retained = F(0)
    max_depth = 0
    marker = object()
    with gzip.open(proof_path, "rt") as stream:
        rows = (json.loads(line) for line in stream)
        for expected, row in zip_longest(original_retained_leaves(certificate), rows, fillvalue=marker):
            need(expected is not marker and row is not marker, "complete_original_retained_leaf_coverage")
            locator, B, depth, volume = expected
            need(tuple(row["locator"]) == locator, "original_leaf_locator_and_order")
            need(independent.bounds(row["box_exact"]) == B, "original_leaf_box_exact")
            need(row["depth"] == depth and F(row["volume_exact"]) == volume, "original_leaf_depth_and_volume")
            totals["all_original_retained_leaves"] += 1
            max_depth = max(max_depth, depth)
            result = row["result"]
            if "reason" in result:
                need(result == {"excluded": False, "reason": "original_pass_or_tiny_leaf_preserved"}, "preserved_leaf_reason")
                need(original["primitive_support_model_conditional_clearance_gate_passed"] or volume <= tiny, "unchanged_original_pass_or_tiny_rule")
                totals["preserved_without_new_test"] += 1
                is_excluded = False
            else:
                need(not original["primitive_support_model_conditional_clearance_gate_passed"] and volume > tiny, "only_original_failed_non_tiny_leaf_retested")
                totals["tested"] += 1
                is_excluded = verify_leaf_channels(result, B, sources, materials, D, totals)
            if is_excluded:
                excluded += volume
                totals["excluded"] += 1
            else:
                retained += volume
                totals["retained"] += 1
    original_total = F(original["retained_leaf_sum_exact"])
    need(excluded + retained == original_total, "conserved_original_retained_volume")
    need(F(frame["retained_exact"]) == retained and F(frame["newly_excluded_exact"]) == excluded and F(frame["original_bound_exact"]) == original_total, "reported_directed_bounds_exact")
    need(frame["old_volume_conserved"] is True, "reported_conservation_true")
    need(frame["new_conditional_gate_passed"] == (retained <= threshold), "unchanged_original_threshold")
    need(frame["original_gate_passed"] == original["primitive_support_model_conditional_clearance_gate_passed"], "original_gate_preserved")
    need(frame["maximum_inherited_depth"] == max_depth <= 24, "original_maximum_depth_preserved")
    for name, count in frame["counts"].items():
        need(totals[name] == count, "frame_count_" + name)
    return {"case_id": frame["case_id"], "frame": frame["frame"], "verified": True, "counts": dict(totals),
            "original_bound_exact": str(original_total), "retained_exact": str(retained), "newly_excluded_exact": str(excluded),
            "retained_display_mm3": float(retained), "new_conditional_gate_passed": retained <= threshold,
            "original_gate_passed": original["primitive_support_model_conditional_clearance_gate_passed"], "original_maximum_depth": max_depth,
            "proof_identity": actual}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--originals", type=Path, required=True)
    parser.add_argument("--producer-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = {"schema": "razr-r8-all16-independent-readback", "completed": False, "frames": [],
              "source": identity(__file__), "independent_checker": identity(independent.__file__),
              "independent_shared_reader": identity(Path(__file__).with_name("read_depth24_actual_r8.py")),
              "producer_report": identity(args.producer_report), "python_version": platform.python_version(),
              "producer_or_primitive_helper_imported": False, "native_error_bound_or_filling_verified": False, "full_continuous_G2": False}
    try:
        report = json.loads(args.producer_report.read_text())
        need(report["execution_completed"] and report["phase"] == "all16", "completed_all16_producer")
        need(report["new_splits"] == 0 and report["original_depth_limit"] == 24 and report["original_split_count_preserved"] == 4096, "original_split_depth_limits")
        base = args.originals / "r7-recovery/v7/r5-local-v7/input-snapshot-v1/base-v6/all-primitive-support-frames"
        original_report = json.loads((base / "report.json").read_text())
        result["original_report"] = identity(base / "report.json")
        need(report["original_report"] == result["original_report"], "same_complete_original_report")
        rows = original_report["frames"]
        need(len(rows) == len(report["frames"]) == 16, "all16_frame_census")
        need([(r["case_id"], r["frame"]) for r in rows] == [(r["case_id"], r["frame"]) for r in report["frames"]], "all16_original_order")
        required = set()
        for row in rows:
            p = base / row["certificate"]["path"]
            with gzip.open(p, "rt") as stream:
                cert = json.load(stream)
            required.update(tuple(s["material_key"]) for s in cert["boundary_refinement"]["sources"])
        del cert
        materials, provenance = read_all_materials(args.originals, required)
        result["native_input_identities"] = provenance
        result["whole_native_material_records"] = len(materials)
        threshold = F(original_report["original_TOL_exact"])
        tiny = F(original_report["capacity"]["tiny_retained_volume_exact"])
        need(threshold == F(1e-7), "unmodified_original_float64_gate")
        grand = Counter()
        for frame, original in zip(report["frames"], rows):
            p = base / original["certificate"]["path"]
            actual = identity(p)
            need(all(actual[k] == original["certificate"][k] for k in ("bytes", "sha256")), "full_original_certificate_identity")
            with gzip.open(p, "rt") as stream:
                certificate = json.load(stream)
            need(certificate["frame"] == {k: v for k, v in original.items() if k != "certificate"}, "original_certificate_frame_header")
            proof = args.producer_report.parent / Path(frame["proof"]["path"]).name
            checked = verify_frame(frame, original, certificate, materials, proof, threshold, tiny)
            result["frames"].append(checked)
            grand.update(checked["counts"])
            print(json.dumps({"frame": [frame["case_id"], frame["frame"]], "verified": True, "retained": checked["retained_display_mm3"], "counts": checked["counts"]}), flush=True)
            del certificate
            gc.collect()
        need(grand["channels"] == report["counts"]["channels"], "actual_channel_count")
        need(grand["piece_proofs"] + grand["failed_channel_prefixes"] == report["counts"]["pieces"], "actual_piece_count")
        for name in ("quadric", "plane", "line", "empty_closed_intersection"):
            need(grand["new_" + name] == report["counts"].get("new_" + name, 0), "actual_new_claim_count_" + name)
        need(grand["tested"] == report["tested_leaves"], "actual_tested_leaf_count")
        new_passes = sum(f["new_conditional_gate_passed"] for f in result["frames"])
        need(new_passes == report["new_conditional_pass_count"], "all16_conditional_pass_count")
        result.update(completed=True, totals=dict(grand), new_conditional_pass_count=new_passes, original_conditional_pass_count=sum(f["original_gate_passed"] for f in result["frames"]))
    except Exception as exc:
        result["failure"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    result["seconds"] = time.monotonic() - started
    result["peak_RSS_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"completed": result["completed"], "seconds": result["seconds"], "passes": result.get("new_conditional_pass_count"), "failure": result.get("failure")}), flush=True)
    if not result["completed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
