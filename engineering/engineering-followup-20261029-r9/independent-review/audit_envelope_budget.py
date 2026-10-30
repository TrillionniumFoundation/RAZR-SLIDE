"""Independent recorded-budget audit, separate from geometric proof readback."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path


def need(value, message):
    if not value:
        raise ValueError(message)


def identity(path):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"bytes": path.stat().st_size, "sha256": digest}


def main(args):
    r = json.loads(args.report.read_text())
    expected = {"maximum_splits": 4096, "maximum_depth": 24,
                "maximum_boundary_box_tests": 12000000, "wall_seconds": 600,
                "address_space_limit_bytes": 805306368}
    need(r["schema"] == "razr-r9-balanced-all16-original-roots" and r["execution_completed"],
         "incomplete actual producer")
    need(r["limits"] == expected, "changed registered limits")
    elapsed = r["seconds"]
    need(type(elapsed) in (int, float) and math.isfinite(elapsed) and 0 <= elapsed <= 600,
         "recorded total producer duration outside original 600 seconds")
    need(type(r["global_splits"]) is int and 0 <= r["global_splits"] <= 4096, "global split budget")
    need(type(r["counts"]["pieces"]) is int and 0 <= r["counts"]["pieces"] <= 12000000, "piece budget")
    need(Fraction(r["original_TOL_exact"]) == Fraction(1e-7), "original float64 threshold changed")
    original_path = Path(r["original_report"]["path"])
    need(identity(original_path) == {k: r["original_report"][k] for k in ["bytes", "sha256"]},
         "original report byte identity")
    old = json.loads(original_path.read_text())
    need(len(r["frames"]) == len(old["frames"]) == 16, "all16 frame count")
    need([(x["case_id"], x["frame"]) for x in r["frames"]] ==
         [(x["case_id"], x["frame"]) for x in old["frames"]], "original frame order")
    sources = {}
    for name in ["source", "common_source", "math_source", "cut_source", "basis", "cache_source"]:
        if name not in r:
            continue
        rec = r[name]
        p = Path(rec["path"])
        need(identity(p) == {k: rec[k] for k in ["bytes", "sha256"]}, "executed source changed: " + name)
        sources[name] = identity(p)
    frames = []
    for row in r["frames"]:
        depth = row["maximum_depth"]
        need(type(depth) is int and 0 <= depth <= 24, "recorded depth exceeds original cap")
        retained, excluded, total = (Fraction(row[k]) for k in ["retained_exact", "excluded_exact", "root_total_exact"])
        need(retained >= 0 and excluded >= 0 and retained + excluded == total, "reported exact mass balance")
        need(row["conditional_gate_passed"] == (retained <= Fraction(1e-7)), "reported unchanged volume gate")
        frames.append({"case_id": row["case_id"], "frame": row["frame"],
                       "root_count": row["root_count"], "splits": row["splits"],
                       "maximum_depth": depth, "retained_exact": str(retained),
                       "conditional_gate_passed": row["conditional_gate_passed"]})
    need(sum(x["splits"] for x in frames) == r["global_splits"], "global split sum")
    need(sum(x["conditional_gate_passed"] for x in frames) == r["conditional_pass_count"], "pass count")
    result = {"schema": "razr-r9-independent-recorded-envelope-budget-audit-v1", "completed": True,
              "audit_source": identity(Path(__file__)), "producer_report": identity(args.report),
              "executed_sources": sources, "recorded_limits": expected,
              "recorded_global_splits": r["global_splits"], "recorded_piece_tests": r["counts"]["pieces"],
              "recorded_producer_seconds_through_proof_serialization": elapsed,
              "recorded_duration_within_600_seconds": True,
              "duration_measurement_scope": "Producer samples elapsed after serializing all proof trees, before writing the final JSON report. This audit does not claim an independent external wall-clock measurement.",
              "recorded_peak_RSS_bytes": r["peak_RSS_bytes"],
              "RSS_is_not_address_space": True,
              "address_space_limit_basis": "Identity-bound producer source calls resource.setrlimit(RLIMIT_AS,(805306368,805306368)) before computation; no separate kernel limit measurement is claimed.",
              "frames": frames, "root_count": sum(x["root_count"] for x in frames),
              "conditional_pass_count": r["conditional_pass_count"],
              "geometric_tree_and_primitive_claims_rechecked_by_this_audit": False,
              "scope": "Recorded budget and provenance only; geometric validity requires the separate independent full certificate reader. No native BREP topology/error/filling or full continuous G2 qualification."}
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({k: result[k] for k in ["completed", "recorded_global_splits", "recorded_piece_tests", "recorded_producer_seconds_through_proof_serialization", "root_count", "conditional_pass_count"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
