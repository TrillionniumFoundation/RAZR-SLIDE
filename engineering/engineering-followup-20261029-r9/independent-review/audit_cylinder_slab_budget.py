"""Audit the completed v1 cylinder/slab report, not its mathematical proofs."""
import argparse
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path


def need(value, reason):
    if not value:
        raise ValueError(reason)


def identity(path):
    path = Path(path)
    return {"bytes": path.stat().st_size,
            "sha256": hashlib.file_digest(path.open("rb"), "sha256").hexdigest()}


def bind(record):
    observed = identity(record["path"])
    need(observed == {k: record[k] for k in ("bytes", "sha256")}, "source or input identity changed")
    return observed


def main(args):
    report = json.loads(args.report.read_text())
    need(report["schema"] == "razr-r9-cylinder-slab-all16-original-roots", "actual cylinder/slab schema")
    for key in ("execution_completed", "computation_completed", "recorded_budget_passed"):
        need(report[key] is True, "completed final flag: " + key)
    need("failure" not in report and "serialization_failure" not in report, "actual report has failure")
    expected = {"maximum_splits": 4096, "maximum_depth": 24,
                "maximum_boundary_box_tests": 12000000, "wall_seconds": 600,
                "address_space_limit_bytes": 805306368}
    need(report["limits"] == expected, "original exact limits")
    elapsed = report["seconds"]
    need(type(elapsed) in (float, int) and math.isfinite(elapsed) and 0 <= elapsed <= 600,
         "final recorded duration within original 600 seconds")
    need(type(report["global_splits"]) is int and 0 <= report["global_splits"] <= 4096, "global split budget")
    need(type(report["counts"]["pieces"]) is int and 0 <= report["counts"]["pieces"] <= 12000000,
         "original piece budget")
    need(F(report["original_TOL_exact"]) == F(1e-7), "unchanged binary64 gate")
    original_id = bind(report["original_report"])
    original = json.loads(Path(report["original_report"]["path"]).read_text())
    need(F(original["original_TOL_exact"]) == F(1e-7), "original threshold identity")
    need(F(report["original_tiny_exact"]) == F(original["capacity"]["tiny_retained_volume_exact"]),
         "original tiny rule")
    need(len(report["frames"]) == len(original["frames"]) == 16, "all16 frame count")
    need([(x["case_id"], x["frame"]) for x in report["frames"]] ==
         [(x["case_id"], x["frame"]) for x in original["frames"]], "original complete frame order")
    sources = {key: bind(report[key]) for key in
               ("source", "geometry_source", "math_source", "common_source", "cut_source",
                "atomic_source", "cache_source", "proof_basis", "capacity_basis")}
    need(Path(report["source"]["path"]).name == "cylinder_slab_all16_r9.py", "actual executed v1 identity")
    need("recovery_source" not in report, "v2 recovery must not be attributed to v1")
    prerequisites = [bind(x) for x in report["prerequisites"]]
    frames = []
    worst = F(0)
    for row in report["frames"]:
        need(type(row["maximum_depth"]) is int and 0 <= row["maximum_depth"] <= 24, "recorded depth budget")
        need(type(row["splits"]) is int and row["splits"] >= 0, "nonnegative frame splits")
        volume, upper, removed = (F(row[k]) for k in
                                  ("root_box_volume_exact", "intersection_upper_bound_exact",
                                   "conservative_removed_volume_lower_bound_exact"))
        need(volume > 0 and 0 <= upper <= volume and removed == volume - upper,
             "positive partition / conservative bound accounting")
        need(type(row["conditional_gate_passed"]) is bool and row["conditional_gate_passed"] == (upper <= F(1e-7)),
             "exact original frame gate")
        proof_id = bind(row["proof"])
        worst = max(worst, upper)
        frames.append({"case_id": row["case_id"], "frame": row["frame"], "root_count": row["root_count"],
                       "splits": row["splits"], "maximum_depth": row["maximum_depth"],
                       "intersection_upper_bound_exact": str(upper),
                       "conditional_gate_passed": row["conditional_gate_passed"], "proof": proof_id})
    need(sum(x["splits"] for x in frames) == report["global_splits"], "global exact split sum")
    need(sum(x["conditional_gate_passed"] for x in frames) == report["conditional_pass_count"], "pass census")
    need(sum(x["root_count"] for x in frames) == 1537, "all original root census")
    need(report["counts"]["tiny_nodes"] + report["counts"]["tested_nodes"] ==
         1537 + 2 * report["global_splits"], "all generated nodes accounted for")
    result = {"schema": "razr-r9-independent-cylinder-slab-recorded-budget-audit-v1", "completed": True,
              "audit_source": identity(__file__), "producer_report": identity(args.report),
              "executed_v1_sources": sources, "prerequisite_identities": prerequisites,
              "original_report": original_id, "recorded_final_flags": {
                  k: report[k] for k in ("execution_completed", "computation_completed", "recorded_budget_passed")},
              "recorded_limits": expected, "recorded_seconds_through_complete_proof_serialization": elapsed,
              "recorded_piece_tests": report["counts"]["pieces"], "recorded_global_splits": report["global_splits"],
              "recorded_maximum_depth": max(x["maximum_depth"] for x in frames),
              "recorded_peak_RSS_bytes": report["peak_RSS_bytes"], "RSS_is_not_address_space": True,
              "time_and_memory_measurement_scope": "Final producer elapsed sample follows all proof serialization and precedes the report write. RSS is the producer self measurement, not address space. The bound v1 source sets RLIMIT_AS=805306368; no separate external wall clock or kernel-limit measurement is asserted.",
              "original_root_count": 1537, "frames": frames,
              "conditional_pass_count": report["conditional_pass_count"],
              "worst_reported_bound_exact": str(worst), "worst_reported_bound_display_mm3": float(worst),
              "v2_IO_controls_retroactively_applied": False,
              "proof_mathematics_rechecked_by_this_budget_audit": False,
              "scope": {"recorded_budget_and_identity_only": True,
                        "native_error_bound_verified": False, "native_filling_verified": False,
                        "native_envelope_topology_verified": False, "full_continuous_G2": False},
              "separate_full_reader_required": True}
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({k: result[k] for k in ("completed", "conditional_pass_count", "recorded_global_splits",
                                           "recorded_seconds_through_complete_proof_serialization",
                                           "worst_reported_bound_display_mm3")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
