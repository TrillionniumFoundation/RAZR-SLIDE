"""Compare actual full machine receipts, without loading either CAD builder."""
from pathlib import Path
import argparse
import hashlib
import json
import math


def main():
    here = Path(__file__).parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=here / "strict_motion_audit.json")
    parser.add_argument("--peer", type=Path, default=here / "X230_strict_motion_audit.json")
    parser.add_argument("--root-step", type=Path, default=here / "full_step_payload_validation.json")
    parser.add_argument("--peer-step", type=Path, default=here / "X230_full_step_payload_validation.json")
    parser.add_argument("--out", type=Path, default=here / "X230_semantic_comparison.json")
    args = parser.parse_args()
    root, peer, root_step, peer_step = (json.loads(path.read_text()) for path in
                                      (args.root, args.peer, args.root_step, args.peer_step))
    assert root["complete"] and peer["complete"]
    assert root["manufacturing_go"] is False and peer["manufacturing_go"] is False
    checked = 0
    maximum_error = 0.
    tolerance = 1e-5

    def compare(a, b, path):
        nonlocal checked, maximum_error
        if isinstance(a, dict):
            assert a.keys() == b.keys(), path
            for key in a:
                compare(a[key], b[key], path + "/" + str(key))
        elif isinstance(a, list):
            assert len(a) == len(b), path
            for index, (aa, bb) in enumerate(zip(a, b)):
                compare(aa, bb, path + "/" + str(index))
        elif isinstance(a, (float, int)) and not isinstance(a, bool):
            assert isinstance(b, (float, int)) and not isinstance(b, bool), path
            assert math.isfinite(a) and math.isfinite(b), path
            error = abs(a-b)
            assert error <= tolerance, (path, a, b)
            maximum_error = max(maximum_error, error)
            checked += 1
        else:
            assert a == b, path

    keys = ["pose_count", "obstacles_per_pose", "strict_checks_count_including_easy_axis",
            "true_OCC_common_count", "validated_strict_AABB_separation_count",
            "collision_pose_count_above_1e_minus6", "source_chain", "strict_guard_sha256",
            "referenced_occ_signed_volume_sha256", "audit_source_sha256", "source_manifest_sha256",
            "R37_B_before_unapproved_cut_sha256", "R38_provisional_B_removed_volume_mm3",
            "constraints", "new_full_motion_rows", "easy_axis_negative_counterexamples",
            "actual_STEP_curve_and_terminal_frame_comparisons",
            "minimum_additional_obstacle_AABB_lower_bounds_mm", "maximum_length_error_mm",
            "maximum_B_end_width_axis_tilt_deg"]
    for key in keys:
        compare(root[key], peer[key], key)
    compare(root["source_reference"]["original_geometry_builder_source_sha256"],
            peer["source_reference"]["original_geometry_builder_source_sha256"], "original_geometry_builder_source_sha256")
    assert root_step["STEP_full_payload_validation_complete"] and peer_step["STEP_full_payload_validation_complete"]
    assert len(root_step["rows"]) == len(peer_step["rows"]) == 6
    for index, (a, b) in enumerate(zip(root_step["rows"], peer_step["rows"])):
        for key in ("referenced_path", "transferred_root_count", "visited_shape_type_counts",
                    "free_non_solid_leaf_count", "valid_positive_single_solids", "solid_signed_volumes_mm3"):
            compare(a[key], b[key], "full_STEP_payload/" + str(index) + "/" + key)
    report = {"comparison_complete": True, "absolute_numeric_tolerance": tolerance,
              "numeric_values_compared": checked, "maximum_absolute_numeric_error": maximum_error,
              "strict_checks_compared": (121+3)*23, "full_STEP_solid_leaves_compared": 6*23,
              "root_receipt_sha256": hashlib.sha256(args.root.read_bytes()).hexdigest(),
              "peer_receipt_sha256": hashlib.sha256(args.peer.read_bytes()).hexdigest(),
              "compared_source_fields": keys,
              "excluded_fields": ["runtime environment", "elapsed time", "earlier receipt SHA because each machine refers to its own earlier run", "earlier STEP byte SHA", "existing STEP imported index ordering"],
              "OCC_numeric_zero_does_not_prove_subtolerance_no_contact": True,
              "manufacturing_go": False}
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
