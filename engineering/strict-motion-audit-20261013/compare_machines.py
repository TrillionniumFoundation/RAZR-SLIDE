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
        elif isinstance(a, bool):
            assert isinstance(b, bool) and a is b, path
        elif isinstance(a, int):
            assert isinstance(b, int) and not isinstance(b, bool) and a == b, path
            checked += 1
        elif isinstance(a, float):
            assert isinstance(b, (float, int)) and not isinstance(b, bool), path
            assert math.isfinite(a) and math.isfinite(b), path
            error = abs(a-b)
            assert error <= tolerance, (path, a, b)
            maximum_error = max(maximum_error, error)
            checked += 1
        else:
            assert type(a) is type(b) and a == b, path

    keys = ["pose_count", "obstacles_per_pose", "strict_checks_count_including_easy_axis",
            "true_OCC_common_count", "validated_strict_AABB_separation_count",
            "collision_pose_count_above_1e_minus6", "source_chain", "strict_guard_sha256",
            "referenced_occ_signed_volume_sha256", "audit_source_sha256", "source_manifest_sha256",
            "R37_B_before_unapproved_cut_sha256", "R38_provisional_B_removed_volume_mm3",
            "constraints", "new_full_motion_rows", "easy_axis_negative_counterexamples",
            "actual_STEP_curve_and_terminal_frame_comparisons",
            "minimum_additional_obstacle_AABB_lower_bounds_mm", "maximum_length_error_mm",
            "maximum_B_end_width_axis_tilt_deg", "candidate_go", "manufacturing_go",
            "continuous_motion_qualification", "no_protected_BRep_or_OLED_was_cut_or_modified",
            "Frenet_director_is_geometric_hypothesis_not_material_or_clamp_qualification",
            "pure_planar_zero_dock_kinematic_homogeneous_extreme_strain"]
    for key in keys:
        compare(root[key], peer[key], key)
    compare(root["source_reference"]["original_geometry_builder_source_sha256"],
            peer["source_reference"]["original_geometry_builder_source_sha256"], "original_geometry_builder_source_sha256")
    # Only each machine's earlier serialization hashes and imported index labels
    # are excluded. Volume/bounds/area/center matching errors remain compared.
    def normalized_steps(report):
        rows = []
        for original in report["previous_STEP_exports_reimported_and_semantically_checked"]:
            row = {key: value for key, value in original.items() if key != "sha256"}
            row["semantic_matches"] = [{key: value for key, value in item.items() if key != "imported_part_index"}
                                       for item in original["semantic_matches"]]
            rows.append(row)
        return rows
    compare(normalized_steps(root), normalized_steps(peer), "old_STEP_semantic_matching")
    assert root_step["STEP_full_payload_validation_complete"] and peer_step["STEP_full_payload_validation_complete"]
    assert root_step["manufacturing_go"] is False and peer_step["manufacturing_go"] is False
    for key in ("source_sha256", "referenced_occ_guard_sha256", "manufacturing_go",
                "full_payload_topology_check_does_not_prove_physical_or_topological_identity"):
        compare(root_step[key], peer_step[key], "full_STEP_payload/" + key)
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
              "excluded_fields": ["runtime environment", "elapsed time", "earlier receipt SHA because each machine refers to its own earlier run", "earlier STEP byte SHA", "existing STEP imported_part_index labels only; solid leaf volume arrays still compared in transfer order"],
              "comparison_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "OCC_numeric_zero_does_not_prove_subtolerance_no_contact": True,
              "manufacturing_go": False}
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
