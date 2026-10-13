#!/usr/bin/env python3
"""R45 research audit: fuller obstacle set, true STEP frames, easy-axis counterexample.

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path,
        default=Path(__file__).resolve().parents[2] / "baselines/fpc-r44-20261013")
    parser.add_argument("--cache", type=Path,
        default=Path(__file__).resolve().parents[3] / "work-cad/r45-safe-cache")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    started = time.monotonic()
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
    from r40_occ import intersectvol
    from r42_occ import A_SHELL, B_SHELL

    args.out.mkdir(parents=True, exist_ok=True)
    out_cad = args.out / "cad"
    out_cad.mkdir(exist_ok=True)
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

    def build(sec, easy_axis=False):
        points, (leg, count) = centerline(sec, leg_samples=12, arc_samples=70)
        vectors = [cq.Vector(*(float(x) for x in point)) for point in points]
        # Original R44 unconstrained interpolation yields nonzero endpoint
        # tangent error. Enforce the actual adjoining straight leg directions.
        arc = cq.Edge.makeSpline(vectors[leg:leg + count + 1],
            tangents=(cq.Vector(0, 1, 0), cq.Vector(0, -1, 0)))
        wire = cq.Wire.assembleEdges((cq.Edge.makeLine(vectors[0], vectors[leg]),
            arc, cq.Edge.makeLine(vectors[leg + count], vectors[-1])))
        plane = cq.Plane(origin=vectors[0],
            xDir=(0, 0, 1) if easy_axis else (1, 0, 0), normal=(0, 1, 0))
        shape = cq.Workplane(plane).rect(FPC_W, FPC_T).sweep(
            cq.Workplane().newObject([wire]), isFrenet=False).val()
        if not shape.isValid() or len(shape.Solids()) != 1:
            raise ValueError("Invalid swept study shape")
        return shape, wire

    def obstacles(s, q):
        obs = protected(s, q)
        obs["B_R37_BEFORE_UNAPPROVED_HEADER_CUT"] = original_b.translate((0, s, q - 8.2))
        ref = r21.r17_assembly(P, s, q, 0)
        obs["A_FIXED_BRIDGE_SKIN_PROXY"] = ref["A_fixed_skin"]
        # Include all three bridge configurations; this is conservative spatial
        # coverage, not an assertion that premature deployment is permitted.
        for deploy in (0., .5, 1.):
            obs[f"A_MOVING_BRIDGE_DEPLOY_{deploy}_PROXY"] = r21.r17_assembly(P, s, q, deploy)["A_moving_leaf"]
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
        arc = next(edge for edge in wire.Edges() if edge.geomType() == "BSPLINE")
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
        intersections = {name: float(intersectvol(shape, body)) for name, body in obs.items()}
        distances = {name: exact_distance(shape, obs[name]) for name in main4}
        lower_bounds = {name: bbox_distance(shape, body) for name, body in obs.items() if name not in main4}
        rows.append({"index": index, "stage": stage["stage"], "s_mm": s, "q_mm": q,
            "wire_length_mm": float(wire.Length()), "valid_single_solid": True,
            "intersections_mm3": intersections, "exact_main4_distances_mm": distances,
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
        intersections = {key: float(intersectvol(easy, body)) for key, body in obs.items()}
        easy_bb = easy.BoundingBox()
        negative_rows.append({"pose": name, "s_mm": s, "q_mm": q,
            "easy_axis_start_section_rotated_90_deg": True,
            "intersections_mm3": intersections,
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
            assembly = cq.Assembly(name="R45_GHOST_" + branch + "_" + name)
            # R37 original B replaces the conditional R38 cut version in export;
            # both are tested above, and neither is a real OEM body.
            for key, part in obs.items():
                if key == "B_R38_CORE":
                    continue
                assembly.add(part, name=key)
            assembly.add(cable, name="UNTERMINATED_FPC_NO_OEM_FEEDTHROUGHS")
            target = out_cad / ("R45_GHOST_" + branch + "_" + name + ".step")
            assembly.save(str(target), exportType="STEP")
            imported = cq.importers.importStep(str(target)).solids().vals()
            if len(imported) != expanded_count or not all(item.isValid() for item in imported):
                raise ValueError("Exported GHOST STEP validation failed")
            steps.append({"path": "cad/" + target.name, "sha256": digest(target),
                "valid_reimported_solids": len(imported), "GHOST_only": True})

    report = {"revision": "R45 CAD audit of R44 hypothesis; research only",
        "complete": True, "source_chain": ancestry,
        "environment": {"python": platform.python_version(), "cadquery": cq.__version__,
            "numpy": np.__version__, "platform": platform.platform()},
        "R37_B_before_unapproved_cut_sha256": digest(original_b_path),
        "R38_provisional_B_removed_volume_mm3": original_b.Volume() - B_SHELL.Volume(),
        "no_protected_BRep_or_OLED_was_cut_or_modified": True,
        "constraints": {"slide_mm": 79.75, "dock_mm": 8.2, "single_about_7_inch_OLED": True,
            "equal_A_B_finished_covers_target_not_validated": True, "A_prioritizes_battery": True},
        "new_CAD_change": "Constrain spline endpoint tangents to the adjoining straight legs",
        "continuous_motion_qualification": False,
        "pose_count": len(rows), "obstacles_per_pose": expanded_count,
        "collision_pose_count_above_1e_minus6": sum(any(v > 1e-6 for v in row["intersections_mm3"].values()) for row in rows),
        "minimum_exact_main4_distances_mm": {name: min(row["exact_main4_distances_mm"][name] for row in rows) for name in main4},
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
        "easy_axis_negative_counterexamples": negative_rows, "new_STEP_exports": steps,
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
    (args.out / "R45_CAD_motion_audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n")
    (args.out / "progress.json").write_text(json.dumps({"complete": True, "poses": len(rows)}) + "\n")
    print(json.dumps({key: report[key] for key in ("pose_count", "obstacles_per_pose", "collision_pose_count_above_1e_minus6",
        "minimum_exact_main4_distances_mm", "maximum_B_end_width_axis_tilt_deg", "elapsed_s")}, indent=2), flush=True)


if __name__ == "__main__":
    main()
