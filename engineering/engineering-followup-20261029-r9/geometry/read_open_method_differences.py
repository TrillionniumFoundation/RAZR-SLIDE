"""Preserve actual OPEN producer/STEP-reader method-branch differences."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def rec(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(HERE)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    pp = HERE / "producer-v3-attempt1/open_installed"
    rr = HERE / "reader-open-installed-v3-attempt1/open_installed"
    p = [json.loads(s) for s in (pp / "pairs.jsonl").read_text().splitlines()]
    r = [json.loads(s) for s in (rr / "pairs.jsonl").read_text().splitlines()]
    if [(x["a"], x["b"]) for x in p] != [(x["a"], x["b"]) for x in r]:
        raise ValueError("actual complete pair rosters differ")
    pb = json.loads((pp / "frozen_participants.json").read_text())["records"]
    rb = json.loads((rr / "frozen_participants.json").read_text())

    def gap(bounds, left, right):
        a, b = bounds[left]["bounds_mm"], bounds[right]["bounds_mm"]
        return max(max(a[2*i]-b[2*i+1], b[2*i]-a[2*i+1]) for i in range(3))

    differences = []
    for before, after in zip(p, r):
        if before.get("method") == after.get("method"):
            continue
        left, right = before["a"], before["b"]
        difference = {"a": left, "b": right, "producer_actual_row": before,
                      "independent_reader_actual_row": after,
                      "producer_signed_axis_gap_from_frozen_bounds_mm": gap(pb, left, right),
                      "reader_signed_axis_gap_from_frozen_bounds_mm": gap(rb, left, right),
                      "body_bounds": {name: {
                          "producer_mm": pb[name]["bounds_mm"],
                          "reader_mm": rb[name]["bounds_mm"],
                          "reader_minus_producer_mm": [b-a for a, b in zip(pb[name]["bounds_mm"], rb[name]["bounds_mm"])]}
                          for name in (left, right)},
                      "original_Common_difference_mm3": after["common_mm3"] - before["common_mm3"],
                      "original_classification_agrees": before["rejected"] == after["rejected"]}
        differences.append(difference)
    out = {"schema": "razr-r9-OPEN-actual-method-branch-differences-v1", "script": rec(Path(__file__)),
           "inputs": [rec(root / name) for root in (pp, rr) for name in ("report.json", "pairs.jsonl", "frozen_participants.json")],
           "total_complete_pairs_compared": len(p), "method_difference_count": len(differences),
           "differences": differences, "methods_identical": not differences,
           "all_original_Common_and_classification_criteria_agree": all(
               abs(a["common_mm3"]-b["common_mm3"]) <= 1e-7 and a["rejected"] == b["rejected"] for a, b in zip(p, r)),
           "maximum_Common_difference_mm3": max(abs(a["common_mm3"]-b["common_mm3"]) for a, b in zip(p, r)),
           "new_CAD_or_Common_execution": False,
           "new_acceptance_threshold_introduced": False,
           "physical_gap_or_full_continuous_G2_proved": False}
    target = HERE / "OPEN_STEP_METHOD_BRANCH_DIFFERENCES.json"
    if target.exists():
        raise FileExistsError(target)
    target.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: out[k] for k in ("total_complete_pairs_compared", "method_difference_count",
                                         "methods_identical", "all_original_Common_and_classification_criteria_agree",
                                         "maximum_Common_difference_mm3")}))
    for item in differences:
        print(json.dumps({k: item[k] for k in ("a", "b", "producer_signed_axis_gap_from_frozen_bounds_mm",
                                             "reader_signed_axis_gap_from_frozen_bounds_mm", "original_Common_difference_mm3")}))


if __name__ == "__main__":
    main()
