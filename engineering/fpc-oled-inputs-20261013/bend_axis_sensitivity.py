#!/usr/bin/env python3
"""Material-station kinematic screen; never a copper fatigue or assembly model.

Analytic q=0 planar R44 geometry is reused as a negative/conditional witness.
No R44 or R50 geometry is changed and no new route is promoted.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path


def finite_positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(name + " must be a finite positive number")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(name + " must be a finite positive number")
    return float(value)


def section_index(width_mm, thickness_mm, radius_mm, width_angle_deg):
    """Maximum linear fibre-distance/radius index for a rectangular section.

    angle=0: radial curvature through WIDTH, hard-axis/in-plane bend.
    angle=90: radial curvature through THICKNESS, easy-axis/out-of-plane bend.
    This small-curvature kinematic expression is not a copper material law.
    """
    w = finite_positive(width_mm, "width")
    t = finite_positive(thickness_mm, "thickness")
    r = finite_positive(radius_mm, "radius")
    if not math.isfinite(width_angle_deg):
        raise ValueError("angle must be finite")
    theta = math.radians(width_angle_deg)
    return (abs(math.cos(theta)) * w + abs(math.sin(theta)) * t) / (2 * r)


def loop_legs(slide_mm, radius_mm=16.5, length_mm=120.0):
    """R44 A_y=70, B_y=15+s, planar semicircle, exact material length."""
    r = finite_positive(radius_mm, "radius")
    length = finite_positive(length_mm, "length")
    if not math.isfinite(slide_mm) or not 0 <= slide_mm <= 79.75:
        raise ValueError("slide outside frozen q=0 path")
    leg_a = (length - math.pi * r - 55.0 + slide_mm) / 2
    leg_b = length - leg_a - math.pi * r
    if leg_a < 0 or leg_b < 0:
        raise ValueError("candidate does not have positive straight legs")
    return leg_a, leg_b


def station_curvature(station_mm, slide_mm):
    if not math.isfinite(station_mm) or not 0 <= station_mm <= 120:
        raise ValueError("material station outside ribbon")
    leg_a, _ = loop_legs(slide_mm)
    return 1 / 16.5 if leg_a < station_mm < leg_a + math.pi * 16.5 else 0.0


def build_report(repo: Path):
    witness = repo / "engineering/cad-review-20261013/R45_CAD_motion_audit.json"
    source = json.loads(witness.read_text())
    # A source receipt reports actual OCC proxy results, not supplier acceptance.
    if source.get("manufacturing_go") is not False:
        raise ValueError("upstream research receipt unexpectedly promotes manufacturing")
    negative = source["easy_axis_negative_counterexamples"]
    sample_rows = []
    for station in (0.0, 10.0, 30.0, 50.0, 70.0, 90.0, 120.0):
        curvatures = [station_curvature(station, 79.75 * i / 80) for i in range(81)]
        sample_rows.append({"constant_material_station_from_A_mm": station,
            "q0_curved_pose_count_of_81": sum(k > 0 for k in curvatures),
            "sampled_curvature_range_per_mm": [min(curvatures), max(curvatures)],
            "hard_axis_section_index_range": [min(curvatures) * 0.6, max(curvatures) * 0.6],
            "easy_axis_section_index_range": [min(curvatures) * 0.075, max(curvatures) * 0.075]})
    copper_examples = [{"illustrative_copper_thickness_mm": 0.018,
        "illustrative_centroid_offset_from_neutral_plane_mm": offset,
        "easy_axis_copper_extreme_distance_index": (abs(offset) + 0.009) / 16.5,
        "not_project_stackup": True} for offset in (0.0, 0.025, 0.050)]
    return {"revision": "FPC material station and bend-axis sensitivity 2026-10-13",
        "upstream_receipt": str(witness.relative_to(repo)),
        "upstream_receipt_sha256": hashlib.sha256(witness.read_bytes()).hexdigest(),
        "frozen_slide_mm": 79.75, "frozen_normal_seat_mm": 8.2,
        "scope": "Ideal planar q=0 geometry only; no new CAD or protected-part edits",
        "study_width_mm": 1.2, "study_thickness_mm": 0.15, "study_radius_mm": 16.5,
        "study_length_mm": 120.0,
        "angles": [{"width_angle_from_radius_deg": a,
            "maximum_section_fibre_kinematic_index": section_index(1.2, 0.15, 16.5, a)}
            for a in (0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0)],
        "hard_over_easy_section_index_ratio": 1.2 / 0.15,
        "exact_q0_arc_entry_material_station_range_mm": [loop_legs(0)[0], loop_legs(79.75)[0]],
        "arc_length_mm": math.pi * 16.5,
        "constant_material_station_rows": sample_rows,
        "copper_neutral_axis_illustrations": copper_examples,
        "prior_actual_easy_axis_OCC_negative_witnesses": negative,
        "actual_copper_strain_unknown": True,
        "normal_seat_material_transport_and_twist_not_computed": True,
        "no_copper_fatigue_limit_inferred_from_monotonic_elongation": True,
        "supplier_stackup_received": False, "continuous_motion_certificate": False,
        "candidate_go": False, "manufacturing_go": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("bend_axis_sensitivity.json"))
    args = parser.parse_args()
    report = build_report(args.repo)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"hard_axis_index": report["angles"][0]["maximum_section_fibre_kinematic_index"],
        "easy_axis_index": report["angles"][-1]["maximum_section_fibre_kinematic_index"],
        "material_arc_entry_range_mm": report["exact_q0_arc_entry_material_station_range_mm"],
        "manufacturing_go": False}, indent=2))


if __name__ == "__main__":
    main()
