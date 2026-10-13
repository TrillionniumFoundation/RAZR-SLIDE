#!/usr/bin/env python3
"""Strict whole-solid motion replay of the frozen R45 research geometry.

This code never authorizes or edits a protected part. Tangent constraints remove
an interpolation artifact; they do not supply a working FPC or OEM feedthrough.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import platform
import sys
import time

from prepare_inputs import prepare, digest
from strict_intersections import strict_common, participant
from occ_signed_volume import common, InconsistentGeometry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path,
        default=Path(__file__).resolve().parents[2] / "baselines/fpc-r44-20261013")
    parser.add_argument("--cache", type=Path,
        default=Path(__file__).resolve().parents[3] / "work-cad/r45-safe-cache")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--minimal-source", action="store_true",
        help="Use a SHA-manifest-verified extracted source tree instead of ancestor ZIPs")
    parser.add_argument("--prior", type=Path, default=Path(__file__).resolve().parent.parent / "cad-review-20261013",
        help="Immutable earlier receipt and six STEP exports to verify and reference")
    args = parser.parse_args()
    started = time.monotonic()
    if args.minimal_source:
        manifest = json.loads((args.cache / "minimal_source_manifest.json").read_text())
        for name, expected in manifest["files"].items():
            if digest(args.cache / name) != expected:
                raise ValueError("Minimal source manifest mismatch: " + name)
        ancestry = manifest["source_chain"]
    else:
        ancestry = prepare(args.baseline, args.cache)
    sys.path.insert(0, str(args.cache.resolve()))
    import cadquery as cq
    import numpy as np
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.gp import gp_Pnt, gp_Vec
    from r44_rear_bypass import ribbon_at, protected, R, L, FPC_W, FPC_T, r21, P
    from r42_double_loop import centerline, stages
    from r35_parts import bored_cap, pin, inboard_rail, arm_guide, te_signal_envelope
    from r36_parts import keeper, catalog_m08x2_screw
    from r42_occ import A_SHELL, B_SHELL
    from r17_cad import a_fixed_leaf, a_moving_leaf

    args.out.mkdir(parents=True, exist_ok=True)
    prior_receipt_path = args.prior / "R45_CAD_motion_audit.json"
    prior = json.loads(prior_receipt_path.read_text())
    previous_source = args.prior / "cad_motion_audit.py"
    source_reference = {"original_geometry_builder_source_sha256": digest(previous_source),
        "previous_numeric_receipt_sha256": digest(prior_receipt_path),
        "previous_guard_was_not_strict": True, "previous_exact_distances_recomputed_this_run": False}
    # The build() geometry body below is kept byte-for-byte from that source.
    all_details = []
    r38 = args.cache / "base_R43/parent_R42/parent_R41/baseline_R40/baseline_R38"
    original_b_path = r38 / "cad/R37_B_INTEGRAL_FRONT_STOP_LIPS.brep"
    original_b = cq.importers.importBrep(str(original_b_path)).val()
    # All are historical proxies. Rails fused into B also appear individually
    # here so their clearance is explicitly reviewable, not a native OEM model.
    b_fittings = {f"B_{name}_{side}_RESEARCH_PROXY": factory(side)
        for side in "LR" for name, factory in (
            ("INBOARD_RAIL", inboard_rail), ("ARM_GUIDE", arm_guide),
            ("CAP", bored_cap), ("PIN", pin), ("KEEPER", keeper),
            ("M08_SCREW", catalog_m08x2_screw), ("TE_GAUGE", te_signal_envelope))}
    a_bridges = {"A_FIXED_BRIDGE_SKIN_PROXY": a_fixed_leaf(P)}
    for deploy in (0., .5, 1.):
        a_bridges[f"A_MOVING_BRIDGE_DEPLOY_{deploy}_PROXY"] = a_moving_leaf(P, deploy)

    def build(sec, easy_axis=False):
        points, (leg, count) = centerline(sec, leg_samples=12, arc_samples=70)
        vectors = [cq.Vector(*(float(x) for x in point)) for point in points]
        # Original R44 unconstrained interpolation yields nonzero endpoint
        # tangent error. Enforce the actual adjoining straight leg directions.
        if abs(sec["end"][2] - sec["start"][2]) < 1e-10:
            arc = cq.Edge.makeThreePointArc(vectors[leg],
                cq.Vector(sec["x_middle"], sec["center_y"]+R, sec["start"][2]),
                vectors[leg+count])
        else:
            arc = cq.Edge.makeSpline(vectors[leg:leg + count + 1],
                tangents=(cq.Vector(0, R, 0), cq.Vector(0, -R, 0)),
                parameters=list(np.linspace(0, math.pi, count+1)), scale=False)
        wire = cq.Wire.assembleEdges((cq.Edge.makeLine(vectors[0], vectors[leg]),
            arc, cq.Edge.makeLine(vectors[leg + count], vectors[-1])))
        plane = cq.Plane(origin=vectors[0],
            xDir=(0, 0, 1) if easy_axis else (1, 0, 0), normal=(0, 1, 0))
        shape = cq.Workplane(plane).rect(FPC_W, FPC_T).sweep(
            cq.Workplane().newObject([wire]), isFrenet=True).val()
        if not shape.isValid() or len(shape.Solids()) != 1:
            raise ValueError("Invalid swept study shape")
        return shape, wire

    def obstacles(s, q):
        obs = protected(s, q)
        obs["B_R37_BEFORE_UNAPPROVED_HEADER_CUT"] = original_b.translate((0, s, q - 8.2))
        # Include all three bridge configurations; this is conservative spatial
        # coverage, not an assertion that premature deployment is permitted.
        obs.update(a_bridges)
        obs.update({name: shape.translate((0, s, q - 8.2)) for name, shape in b_fittings.items()})
        return obs

    def exact_distance(a, b):
        calculation = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
        if not calculation.IsDone():
            raise RuntimeError("OCC distance computation incomplete")
        return float(calculation.Value())

    def bbox_distance(a, b):
        aa, bb = a.BoundingBox(), b.BoundingBox()
        gaps = [max(0., getattr(aa, low) - getattr(bb, high),
                          getattr(bb, low) - getattr(aa, high))
                for low, high in (("xmin", "xmax"), ("ymin", "ymax"), ("zmin", "zmax"))]
        return math.sqrt(sum(x*x for x in gaps))

    def frame(shape, endpoint):
        faces = [face for face in shape.Faces()
                 if face.geomType() == "PLANE" and abs(face.Area() - FPC_W * FPC_T) < 1e-5]
        face = min(faces, key=lambda candidate:
            sum((a-b)**2 for a, b in zip(candidate.Center().toTuple(), endpoint)))
        edge = min(face.Edges(), key=lambda e: abs(e.Length() - FPC_W))
        ends = [np.array(vertex.toTuple()) for vertex in edge.Vertices()]
        axis = (ends[1] - ends[0]) / np.linalg.norm(ends[1] - ends[0])
        bb = face.BoundingBox()
        return {"width_axis_xyz": [float(x) for x in axis],
            "width_axis_tilt_from_XY_deg": math.degrees(math.asin(min(1., abs(float(axis[2]))))),
            "end_section_z_span_mm": bb.zmax - bb.zmin,
            "normal_xyz": list(face.normalAt().toTuple())}

    def curve_quality(wire):
        arc = next(edge for edge in wire.Edges() if edge.geomType() in ("BSPLINE", "CIRCLE"))
        a = BRepAdaptor_Curve(arc.wrapped)
        radius = []
        for param in np.linspace(a.FirstParameter(), a.LastParameter(), 2001):
            point, first, second = gp_Pnt(), gp_Vec(), gp_Vec()
            a.D2(float(param), point, first, second)
            curve = first.Crossed(second).Magnitude() / first.Magnitude()**3
            if curve > 1e-12:
                radius.append(1/curve)
        tangent_start, tangent_end = arc.tangentAt(0), arc.tangentAt(1)
        def angle(v, desired):
            return math.degrees(math.acos(min(1., max(-1., v.dot(desired)))))
        return {"BSpline_curvature_sample_count": 2001,
            "curve_geometry_type": arc.geomType(),
            "sampled_min_actual_BSpline_radius_mm": min(radius),
            "start_join_tangent_error_deg": angle(tangent_start, cq.Vector(0, 1, 0)),
            "end_join_tangent_error_deg": angle(tangent_end, cq.Vector(0, -1, 0))}

    rows = []
    expanded_count = None
    main4 = ("A_R38_CORE", "B_R38_CORE", "OLED_PROXY", "DISPLAY_FPC_PROXY")
    for index, stage in enumerate(stages()):
        s, q = float(stage["s"]), float(stage["q"])
        _, sec, _ = ribbon_at(s, q, -7.95, True)
        shape, wire = build(sec)
        obs = obstacles(s, q)
        expanded_count = len(obs)
        checks = {name: strict_common(shape, body) for name, body in obs.items()}
        all_details.extend(checks.values())
        intersections = {name: row["checked_volume_mm3"] for name, row in checks.items()}
        lower_bounds = {name: bbox_distance(shape, body) for name, body in obs.items() if name not in main4}
        rows.append({"index": index, "stage": stage["stage"], "s_mm": s, "q_mm": q,
            "wire_length_mm": float(wire.Length()), "valid_single_solid": True,
            "ribbon_volume_mm3": float(shape.Volume()),
            "intersections_mm3": intersections, "strict_intersection_checks": checks,
            "additional_obstacle_AABB_distance_lower_bounds_mm": lower_bounds,
            "B_end_material_frame": frame(shape, sec["end"])})
        if (index + 1) % 20 == 0 or index == 120:
            print("expanded_motion", index + 1, "/121", "elapsed", round(time.monotonic()-started, 1), flush=True)
            (args.out / "progress.json").write_text(json.dumps({"complete": False, "poses": index+1}) + "\n")

    negative_rows, comparison_rows, steps = [], [], []
    for name, s, q in (("STOW", 0., 0.), ("PREDOCK", 79.75, 0.), ("OPEN_SEATED", 79.75, 8.2)):
        original, sec, _ = ribbon_at(s, q, -7.95, True)
        candidate, fixed_wire = build(sec)
        # Rotate the material width toward Z: bend acts mainly through the
        # 0.15 mm thickness at q=0. It is a negative witness, not a proposed fix.
        easy, easy_wire = build(sec, easy_axis=True)
        obs = obstacles(s, q)
        checks = {key: strict_common(easy, body) for key, body in obs.items()}
        all_details.extend(checks.values())
        intersections = {key: row["checked_volume_mm3"] for key, row in checks.items()}
        easy_bb = easy.BoundingBox()
        negative_rows.append({"pose": name, "s_mm": s, "q_mm": q,
            "easy_axis_start_section_rotated_90_deg": True,
            "intersections_mm3": intersections, "strict_intersection_checks": checks,
            "lower_Z_envelope_excess_mm": max(0., -8.2-easy_bb.zmin),
            "B_end_material_frame": frame(easy, sec["end"])})
        from r42_occ import make_ribbon
        _, old_wire = make_ribbon(sec)
        comparison_rows.append({"pose": name,
            "legacy_R44_curve": curve_quality(old_wire),
            "tangent_constrained_curve": curve_quality(fixed_wire),
            "legacy_B_end_material_frame": frame(original, sec["end"]),
            "tangent_constrained_B_end_material_frame": frame(candidate, sec["end"])})
        for branch, cable in (("TANGENT_CONSTRAINED_HARD_AXIS_UNTERMINATED", candidate),
                              ("REJECTED_EASY_AXIS_OLED_INTERFERENCE", easy)):
            target = args.prior / "cad" / ("R45_GHOST_" + branch + "_" + name + ".step")
            previous = next(item for item in prior["new_STEP_exports"] if item["path"] == "cad/" + target.name)
            if digest(target) != previous["sha256"]:
                raise ValueError("Previously exported STEP has changed: " + target.name)
            imported = cq.importers.importStep(str(target)).solids().vals()
            expected_parts = [body for key, body in obs.items() if key != "B_R38_CORE"] + [cable]
            if len(imported) != expanded_count or len(expected_parts) != expanded_count:
                raise ValueError("Referenced STEP solid count mismatch")
            matches = []
            remaining = list(enumerate(imported))
            for body in expected_parts:
                body_summary = participant(body)
                # Pair by unique volume/bounds, then compare independent area/center.
                candidates = [(index, other) for index, other in remaining
                    if abs(body_summary["signed_volume_mm3"] - participant(other)["signed_volume_mm3"]) < 1e-5
                    and all(abs(body_summary["bounds_mm"][key] - participant(other)["bounds_mm"][key]) < 1e-5
                            for key in body_summary["bounds_mm"])]
                if len(candidates) != 1:
                    raise ValueError("STEP part geometry pairing is missing or ambiguous")
                index, other = candidates[0]
                area_error = abs(float(body.Area()) - float(other.Area()))
                center_error = math.dist(body.Center().toTuple(), other.Center().toTuple())
                if area_error > 1e-5 or center_error > 1e-5:
                    raise ValueError("Referenced STEP semantic geometry differs")
                matches.append({"imported_part_index": index,
                    "valid_positive_single_solid": True,
                    "signed_volume_mm3": participant(other)["signed_volume_mm3"],
                    "volume_error_mm3": abs(float(body.Volume()) - float(other.Volume())),
                    "maximum_bound_error_mm": max(abs(body_summary["bounds_mm"][key] - participant(other)["bounds_mm"][key])
                                                  for key in body_summary["bounds_mm"]),
                    "area_error_mm2": area_error, "center_error_mm": center_error})
                remaining = [(i, solid) for i, solid in remaining if i != index]
            steps.append({"existing_repository_path": "engineering/cad-review-20261013/cad/" + target.name,
                "sha256": digest(target), "valid_positive_reimported_solids": len(imported),
                "semantic_matches": matches, "GHOST_only": True,
                "same_volume_bounds_area_center_is_not_topological_identity": True,
                "no_new_STEP_serialization": True})

    report = {"revision": "Strict signed-volume replay of frozen R45/R44 research geometry; research only",
        "complete": True, "source_chain": ancestry,
        "environment": {"python": platform.python_version(), "cadquery": cq.__version__,
            "numpy": np.__version__, "platform": platform.platform()},
        "source_reference": source_reference,
        "strict_guard_sha256": digest(Path(__file__).with_name("strict_intersections.py")),
        "referenced_occ_signed_volume_sha256": digest(Path(__file__).with_name("occ_signed_volume.py")),
        "audit_source_sha256": digest(Path(__file__)),
        "source_manifest_sha256": digest(args.cache / "minimal_source_manifest.json") if args.minimal_source else None,
        "input_validation_before_any_AABB_pruning": True,
        "strict_AABB_pruning_requires_a_positive_axis_gap_without_tolerance": True,
        "negative_raw_common_is_never_clamped_or_absolute_valued": True,
        "strict_checks_count_including_easy_axis": len(all_details),
        "true_OCC_common_count": sum(row["OCC_boolean_was_run"] for row in all_details),
        "validated_strict_AABB_separation_count": sum(not row["OCC_boolean_was_run"] for row in all_details),
        "OCC_numeric_zero_does_not_prove_positive_clearance_or_subtolerance_no_contact": True,
        "R37_B_before_unapproved_cut_sha256": digest(original_b_path),
        "R38_provisional_B_removed_volume_mm3": original_b.Volume() - B_SHELL.Volume(),
        "no_protected_BRep_or_OLED_was_cut_or_modified": True,
        "constraints": {"slide_mm": 79.75, "dock_mm": 8.2, "single_about_7_inch_OLED": True,
            "equal_A_B_finished_covers_target_not_validated": True, "A_prioritizes_battery": True},
        "new_CAD_change": "None. Frozen build() geometry replayed; signed-volume validation and conservative prune replace r40_occ.intersectvol",
        "Frenet_director_is_geometric_hypothesis_not_material_or_clamp_qualification": True,
        "continuous_motion_qualification": False,
        "pose_count": len(rows), "obstacles_per_pose": expanded_count,
        "collision_pose_count_above_1e_minus6": sum(any(v > 1e-6 for v in row["intersections_mm3"].values()) for row in rows),
        "previous_exact_distance_receipt_reference": source_reference,
        "minimum_additional_obstacle_AABB_lower_bounds_mm": {
            name: min(row["additional_obstacle_AABB_distance_lower_bounds_mm"][name] for row in rows)
            for name in rows[0]["additional_obstacle_AABB_distance_lower_bounds_mm"]},
        "maximum_length_error_mm": max(abs(row["wire_length_mm"] - L) for row in rows),
        "maximum_B_end_width_axis_tilt_deg": max(row["B_end_material_frame"]["width_axis_tilt_from_XY_deg"] for row in rows),
        "pure_planar_zero_dock_kinematic_homogeneous_extreme_strain": {
            "width_axis_bending_assumed_R16p5": FPC_W/(2*R),
            "thickness_axis_bending_assumed_R16p5": FPC_T/(2*R),
            "not_real_copper_strain_or_allowable_limit": True,
            "R44_zero_dock_uses_width_axis_bending": True},
        "new_full_motion_rows": rows, "actual_STEP_curve_and_terminal_frame_comparisons": comparison_rows,
        "easy_axis_negative_counterexamples": negative_rows, "previous_STEP_exports_reimported_and_semantically_checked": steps,
        "failure_counterexamples_retained": True,
        "remaining_hard_blockers": [
            "Actual OEM PCB, covers, battery swelling, OLED/COF and permitted feedthrough CAD absent",
            "R44 endpoints still exterior floating anchors; no valid static BM28 endpoints or stress relief",
            "Flexible layerstack anisotropy and width-axis dynamic bend license absent",
            "B terminal material width axis rotates during normal docking; real clamp/connector director constraint absent",
            "Global continuous synchronized collision sweep, tolerances and loaded deformation not proved",
            "Rolling guide/rear cassette, spring/cam assembly and fault safety not physically qualified",
            "USB SI, power isolation and OLED lifetime evidence absent"],
        "candidate_go": False, "manufacturing_go": False,
        "elapsed_s": round(time.monotonic()-started, 3)}
    (args.out / "strict_motion_audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n")
    (args.out / "progress.json").write_text(json.dumps({"complete": True, "poses": len(rows)}) + "\n")
    print(json.dumps({key: report[key] for key in ("pose_count", "obstacles_per_pose", "collision_pose_count_above_1e_minus6",
        "true_OCC_common_count", "validated_strict_AABB_separation_count", "maximum_B_end_width_axis_tilt_deg", "elapsed_s")}, indent=2), flush=True)


if __name__ == "__main__":
    main()
