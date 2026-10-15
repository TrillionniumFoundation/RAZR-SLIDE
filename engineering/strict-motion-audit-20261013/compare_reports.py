"""Independent numeric receipt comparison, without importing either builder."""
from pathlib import Path
import argparse
import hashlib
import json
import math


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", type=Path, default=Path(__file__).with_name("strict_motion_audit.json"))
    parser.add_argument("--previous", type=Path,
                        default=Path(__file__).parent.parent / "cad-review-20261013/R45_CAD_motion_audit.json")
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("previous_numeric_comparison.json"))
    args = parser.parse_args()
    strict, old = (json.loads(path.read_text()) for path in (args.strict, args.previous))
    assert strict["complete"] is True and strict["manufacturing_go"] is False
    assert strict["source_reference"]["previous_numeric_receipt_sha256"] == hashlib.sha256(args.previous.read_bytes()).hexdigest()
    assert strict["pose_count"] == old["pose_count"] == 121
    assert strict["obstacles_per_pose"] == old["obstacles_per_pose"] == 23
    assert strict["strict_checks_count_including_easy_axis"] == (121+3)*23
    errors = {"intersections_mm3": 0., "wire_length_mm": 0., "ribbon_volume_mm3": 0., "frame_numeric": 0.}

    def difference(a, b, group):
        if isinstance(a, list):
            assert len(a) == len(b)
            for aa, bb in zip(a, b):
                difference(aa, bb, group)
        else:
            assert math.isfinite(a) and math.isfinite(b)
            value = abs(a-b)
            errors[group] = max(errors[group], value)
            assert value <= 1e-7, (group, a, b)

    for new, previous in zip(strict["new_full_motion_rows"], old["new_full_motion_rows"]):
        assert (new["index"], new["stage"], new["s_mm"], new["q_mm"]) == (previous["index"], previous["stage"], previous["s_mm"], previous["q_mm"])
        assert new["intersections_mm3"].keys() == previous["intersections_mm3"].keys()
        for name in new["intersections_mm3"]:
            difference(new["intersections_mm3"][name], previous["intersections_mm3"][name], "intersections_mm3")
        for name in ("wire_length_mm", "ribbon_volume_mm3"):
            difference(new[name], previous[name], name)
        for name in new["B_end_material_frame"]:
            difference(new["B_end_material_frame"][name], previous["B_end_material_frame"][name], "frame_numeric")
    for new, previous in zip(strict["easy_axis_negative_counterexamples"], old["easy_axis_negative_counterexamples"]):
        assert new["pose"] == previous["pose"]
        for name in new["intersections_mm3"]:
            difference(new["intersections_mm3"][name], previous["intersections_mm3"][name], "intersections_mm3")
    assert len(strict["previous_STEP_exports_reimported_and_semantically_checked"]) == 6
    assert all(row["valid_positive_reimported_solids"] == 23 for row in strict["previous_STEP_exports_reimported_and_semantically_checked"])
    assert strict["source_reference"]["previous_exact_distances_recomputed_this_run"] is False
    report = {"comparison_complete": True, "strict_receipt_sha256": hashlib.sha256(args.strict.read_bytes()).hexdigest(),
              "previous_receipt_sha256": hashlib.sha256(args.previous.read_bytes()).hexdigest(),
              "maximum_absolute_errors": errors, "comparison_tolerance": 1e-7,
              "old_numeric_receipt_is_not_retroactively_given_strict_guard_qualification": True,
              "manufacturing_go": False}
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
