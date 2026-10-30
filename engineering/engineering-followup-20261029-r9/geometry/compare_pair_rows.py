"""Preserve snapshots and compare actual v1/v2 matrix rows individually."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def read(path):
    raw = path.read_bytes()
    lines = raw.splitlines(keepends=True)
    complete = [line for line in lines if line.endswith(b"\n")]
    rows = [json.loads(line) for line in complete]
    return raw, rows, len(raw) - sum(map(len, complete))


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def sign(x):
    return 0 if x == 0 else (1 if x > 0 else -1)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--expected", type=int, default=11781)
    a = ap.parse_args(); a.output.mkdir(parents=True, exist_ok=False)
    ra, reference, rt = read(a.reference); ca, candidate, ct = read(a.candidate)
    (a.output / "reference.snapshot.jsonl").write_bytes(ra)
    (a.output / "candidate.snapshot.jsonl").write_bytes(ca)
    right = {(row["a"], row["b"]): row for row in candidate}
    out = {"schema": "razr-r9-v1-v2-actual-pair-row-comparison-v1",
           "source_script": digest(Path(__file__).read_bytes()),
           "reference": digest(ra), "candidate": digest(ca),
           "reference_complete_rows": len(reference), "candidate_complete_rows": len(candidate),
           "reference_trailing_incomplete_bytes": rt, "candidate_trailing_incomplete_bytes": ct,
           "reference_is_full_original_matrix": len(reference) == a.expected and rt == 0,
           "candidate_is_full_matrix": len(candidate) == a.expected and ct == 0,
           "reference_full_execution_not_inferred_from_prefix": True,
           "candidate_duplicate_pair_count": len(candidate) - len(right),
           "comparisons": [], "missing_pairs": [], "method_mismatches": [],
           "signed_volume_mismatches": [], "original_tolerance_volume_mismatches": [],
           "failure_mismatches": [], "classification_mismatches": [],
           "maximum_volume_difference_mm3": 0.0, "maximum_axis_gap_difference_mm": 0.0}
    for row in reference:
        key = (row["a"], row["b"])
        v2 = right.get(key)
        if v2 is None:
            out["missing_pairs"].append(list(key)); continue
        r = {"a": key[0], "b": key[1], "v1": row, "v2": v2}
        failure_agrees = bool(row.get("evaluation_failed")) == bool(v2.get("evaluation_failed"))
        r["failure_status_agrees"] = failure_agrees
        if not failure_agrees:
            out["failure_mismatches"].append(list(key))
        if not row.get("evaluation_failed") and not v2.get("evaluation_failed"):
            left, right_v = row["common_mm3"], v2["common_mm3"]
            if not math.isfinite(left) or not math.isfinite(right_v):
                raise ValueError("nonfinite actual Common row")
            delta = right_v - left
            r.update(method_agrees=row["method"] == v2["method"],
                     sign_agrees=sign(left) == sign(right_v),
                     original_tolerance_volume_agrees=abs(delta) <= 1e-7,
                     volume_binary64_equal=float(left).hex() == float(right_v).hex(),
                     volume_difference_mm3=delta,
                     rejection_classification_agrees=bool(row["rejected"]) == bool(v2["rejected"]),
                     axis_gap_difference_mm=v2["axis_gap_lower_mm"] - row["axis_gap_lower_mm"])
            for name, test in (("method_mismatches", "method_agrees"),
                               ("signed_volume_mismatches", "sign_agrees"),
                               ("original_tolerance_volume_mismatches", "original_tolerance_volume_agrees"),
                               ("classification_mismatches", "rejection_classification_agrees")):
                if not r[test]: out[name].append(list(key))
            out["maximum_volume_difference_mm3"] = max(out["maximum_volume_difference_mm3"], abs(delta))
            out["maximum_axis_gap_difference_mm"] = max(out["maximum_axis_gap_difference_mm"], abs(r["axis_gap_difference_mm"]))
        out["comparisons"].append(r)
    out["all_compared_rows_agree_under_original_predicates"] = not any(out[k] for k in (
        "missing_pairs", "method_mismatches", "signed_volume_mismatches", "original_tolerance_volume_mismatches",
        "failure_mismatches", "classification_mismatches"))
    (a.output / "report.json").write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("comparisons", "reference", "candidate", "source_script")}, indent=2))
    return 0 if out["all_compared_rows_agree_under_original_predicates"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
