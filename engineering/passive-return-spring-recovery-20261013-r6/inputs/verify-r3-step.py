#!/usr/bin/env python3
"""Independent actual STEP identities, motion, one-key and fault counterexamples.

No builder is imported. Source dependencies are only the co-located strict
signed-volume guard. Imposed stop positions reproduce rigid research states;
they never qualify physical return force, friction, strength or phone safety.
"""
import hashlib
import itertools
import json
import platform
import sys
from pathlib import Path
sys.dont_write_bytecode = True
import cadquery as cq
from OCP.TopAbs import TopAbs_COMPOUND, TopAbs_COMPSOLID, TopAbs_SOLID
from OCP.TopoDS import TopoDS_Iterator
from strict_intersections import CheckedBody, Checker, positive_bbox_separation

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
EPS = 1e-7
CASES = {
    "SEATED": (True, 0.0, (1.2, 1.2)),
    "RELEASED": (True, 0.0, (1.2, 1.2)),
    "ABSENT_BLOCKED": (False, 0.0, (0.0, 0.0)),
    "PRIMARY_JAM_ABSENT_BLOCKED": (False, 0.0, (1.2, 0.0)),
    "DOUBLE_JAM_ABSENT_ESCAPE": (False, 0.0, (1.2, 1.2)),
    "NORMAL_KEY_WITHDRAW_1p4": (True, 1.4, (0.0, 0.0)),
    "PRIMARY_HELD_CLEAR_WITHDRAW_BLOCKED": (True, .4, (1.2, .6)),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canon(body, port, side):
    b = body.bounds
    xc = -34.75 if side == "L" else 34.75
    sign = (-1 if side == "L" else 1) if port == "STOW" else (1 if side == "L" else -1)
    e = sorted(sign * (v - xc) for v in b["x"])
    q = sorted(1.2 - v for v in b["y"]) if port == "STOW" else [v + 6.0 for v in b["z"]]
    r = [v - 10.0 for v in b["z"]] if port == "STOW" else [v + 10.0 for v in b["y"]]
    return {"e": e, "q": q, "r": r}


def evec(port, side, value):
    sign = (-1 if side == "L" else 1) if port == "STOW" else (1 if side == "L" else -1)
    return (sign * value, 0.0, 0.0)


def qvec(port, value):
    return (0.0, -value, 0.0) if port == "STOW" else (0.0, 0.0, value)


def rvec(port, value):
    return (0.0, 0.0, value) if port == "STOW" else (0.0, value, 0.0)


def identify(bodies, port, side):
    own = [b for b in bodies if (b.shape.Center().x < 0) == (side == "L")]
    if len(own) not in (7, 8):
        raise ValueError("Unexpected actual side solid count")
    result = {}
    stops = [b for b in own if abs(b.bounds["x"][1] - b.bounds["x"][0] - 1.25) < 1e-6
             and abs(canon(b, port, side)["r"][1] - canon(b, port, side)["r"][0] - 1.9) < 1e-6]
    if len(stops) != 2:
        raise ValueError("Cannot identify two actual pinned interposers")
    stops.sort(key=lambda b: canon(b, port, side)["r"][0])
    result["stop0"], result["stop1"] = stops
    pawn_width = 2.6 if port == "STOW" else 2.3
    pawns = [b for b in own if abs(b.bounds["x"][1] - b.bounds["x"][0] - pawn_width) < 1e-6]
    if len(pawns) != 1:
        raise ValueError("Cannot identify actual derived pawl")
    result["pawn"] = pawns[0]
    keys = [b for b in own if abs(b.bounds["x"][1] - b.bounds["x"][0] - 1.7) < 1e-6]
    if len(keys) > 1 or len(keys) != len(own) - 7:
        raise ValueError("Cannot identify actual key presence")
    if keys:
        result["key"] = keys[0]
    caps = [b for b in own if abs(b.bounds["x"][1] - b.bounds["x"][0] - 4.0) < 1e-6
            and abs(canon(b, port, side)["r"][1] - canon(b, port, side)["r"][0] - .3) < 1e-6]
    if len(caps) != 2:
        raise ValueError("Cannot identify two actual unfastened interposer caps")
    caps.sort(key=lambda b: canon(b, port, side)["r"][0])
    result["cap0"], result["cap1"] = caps
    remaining = [b for b in own if all(b is not v for v in result.values())]
    if len(remaining) != 2:
        raise ValueError("Cannot identify actual root and old cover")
    remaining.sort(key=lambda b: b.volume, reverse=True)
    result["root"], result["cover"] = remaining
    return result


def pairs(checker, bodies):
    return [{"parts": [a, b], **checker.common(bodies[a], bodies[b])} for a, b in itertools.combinations(bodies, 2)]


def rectangular_gate_overlap(stroke, lift):
    e = max(0.0, min(stroke, .4) - max(stroke - .1, .2))
    r = max(0.0, min(1.1, lift + 1.8) - max(.1, lift))
    return e * .1 * r


def import_whole_payload(path):
    """Reject free surface/wire/edge geometry rather than filtering it away."""
    roots = cq.importers.importStep(str(path)).vals()
    bodies, tree_counts = [], {"compound_nodes": 0, "solid_leaves": 0}

    def visit(shape):
        if not shape.isValid():
            raise ValueError("Invalid whole STEP topology node")
        kind = shape.wrapped.ShapeType()
        if kind == TopAbs_SOLID:
            bodies.append(CheckedBody(shape))
            tree_counts["solid_leaves"] += 1
            return
        if kind not in (TopAbs_COMPOUND, TopAbs_COMPSOLID):
            raise ValueError("Whole STEP payload contains free non-solid geometry outside a solid")
        tree_counts["compound_nodes"] += 1
        iterator = TopoDS_Iterator(shape.wrapped)
        children = []
        while iterator.More():
            children.append(cq.Shape.cast(iterator.Value()))
            iterator.Next()
        if not children:
            raise ValueError("Whole STEP payload contains an empty free compound")
        for child in children:
            visit(child)

    for root in roots:
        visit(root)
    raw_sum = sum(float(root.Volume()) for root in roots)
    checked_sum = sum(body.volume for body in bodies)
    if not bodies or abs(raw_sum - checked_sum) > 1e-6:
        raise ValueError("Whole STEP signed-volume total differs from complete validated solid leaves")
    return bodies, {**tree_counts, "raw_whole_payload_signed_volume_mm3": raw_sum,
                    "validated_all_solid_leaf_volume_sum_mm3": checked_sum,
                    "every_topology_branch_is_a_compound_of_valid_positive_solids": True,
                    "free_surfaces_wires_edges_vertices_were_not_filtered_away": True}


def main():
    code_hashes = {name: sha(HERE / name) for name in ("verify-r3-step.py", "strict_intersections.py", "occ_signed_volume.py")}
    expected = {port + "_" + case + ".step" for port in ("STOW", "OPEN") for case in CASES}
    paths = sorted((PROJECT / "cad").glob("*.step"))
    if {p.name for p in paths} != expected:
        raise ValueError("Final actual STEP set does not match all fourteen required states")
    inputs, states = [], {}
    checker = Checker()
    for path in paths:
        digest = sha(path)
        bodies, whole_topology = import_whole_payload(path)
        if sha(path) != digest:
            raise ValueError("Actual STEP changed during reimport")
        port = path.name.split("_", 1)[0]
        states[path.name] = {side: identify(bodies, port, side) for side in "LR"}
        inputs.append({"path": "cad/" + path.name, "sha256": digest,
                       "actual_whole_payload_topology": whole_topology,
                       "actual_connected_valid_positive_solids": len(bodies),
                       "actual_signed_component_volumes_mm3": [b.volume for b in bodies]})
    identities, motion, one_key, withdrawal = [], [], [], []
    for port, side in itertools.product(("STOW", "OPEN"), "LR"):
        reference = states[port + "_SEATED.step"][side]
        released = states[port + "_RELEASED.step"][side]
        stroke = canon(released["pawn"], port, side)["e"][0] - canon(reference["pawn"], port, side)["e"][0]
        if abs(stroke - (1.1 if port == "STOW" else .55)) > 1e-6:
            raise ValueError("Measured actual full release stroke changed")
        for case, (present, key_q, stop_lifts) in CASES.items():
            name = port + "_" + case + ".step"
            actual = states[name][side]
            if ("key" in actual) != present:
                raise ValueError("Actual imported key presence differs from named research state")
            lifts = [canon(actual["stop" + str(i)], port, side)["r"][0] + .1 - 5.0 * i for i in range(2)]
            if any(abs(a - b) > 1e-6 for a, b in zip(lifts, stop_lifts)):
                raise ValueError("Actual pinned stop elevations differ from independent state contract")
            measured_q = (canon(actual["key"], port, side)["q"][0] - canon(reference["key"], port, side)["q"][0]) if present else None
            if present and abs(measured_q - key_q) > 1e-6:
                raise ValueError("Actual key withdrawal changed")
            identities.append({"path": "cad/" + name, "port": port, "side": side,
                               "actual_key_present": present, "actual_key_q_mm": measured_q,
                               "actual_stop_lifts_mm": lifts,
                               "actual_component_bounds_and_volumes": {n: {"canonical_bounds_mm": canon(b, port, side), "volume_mm3": b.volume} for n, b in actual.items()}})
            offset = canon(actual["pawn"], port, side)["e"][0] - canon(reference["pawn"], port, side)["e"][0]
            captured = actual["pawn"].translate(evec(port, side, -offset))
            samples = []
            for index in range(31):
                d = stroke * index / 30.0
                pawn = captured.translate(evec(port, side, d))
                stopped = [checker.volume(pawn, actual["stop" + str(i)]) for i in range(2)]
                analytic = [rectangular_gate_overlap(d, lift) for lift in lifts]
                if any(abs(a - b) > 1e-6 for a, b in zip(stopped, analytic)):
                    raise ValueError("Actual stop/pawl common differs from independent rectangular section")
                supports = {n: checker.volume(pawn, actual[n]) for n in ("root", "cover", "cap0", "cap1")}
                if max(supports.values()) > EPS:
                    raise ValueError("Actual reconstructed carrier crosses its fixed support")
                key_common = checker.volume(pawn, actual["key"]) if present else None
                if case in ("SEATED", "RELEASED") and key_common > EPS:
                    raise ValueError("Actual normal full-key carrier release is obstructed")
                samples.append({"fraction": index / 30.0, "stroke_mm": d,
                                "actual_stop_pawl_common_mm3": stopped,
                                "independent_rectangle_common_mm3": analytic,
                                "actual_support_pawl_common_mm3": supports,
                                "actual_key_pawl_common_mm3": key_common})
            blocked = [max(s["actual_stop_pawl_common_mm3"][i] for s in samples) > EPS for i in range(2)]
            expected_blocked = [v < 1.1 - 1e-6 for v in lifts]
            if blocked != expected_blocked:
                raise ValueError("Actual stop release interception differs from rigid state")
            endpoint_pairs = pairs(checker, actual)
            for pair in endpoint_pairs:
                if pair["checked_common_mm3"] <= EPS:
                    continue
                p = set(pair["parts"])
                expected_force = case in ("ABSENT_BLOCKED", "PRIMARY_JAM_ABSENT_BLOCKED") and "pawn" in p and any(n.startswith("stop") for n in p)
                expected_jam = case == "PRIMARY_HELD_CLEAR_WITHDRAW_BLOCKED" and p == {"key", "stop0"}
                if not (expected_force or expected_jam):
                    raise ValueError("Unexpected actual final endpoint pair intersection")
                pair["retained_intended_failed_motion_intersection"] = True
            motion.append({"path": "cad/" + name, "port": port, "side": side,
                           "release_samples": samples, "actual_interposer_path_blocked_by_each_stop": blocked,
                           "actual_endpoint_pairs": endpoint_pairs,
                           "withdrawn_key_reconstructed_fresh_release_is_counterfactual": "WITHDRAW" in case,
                           "double_jam_is_retained_safety_failure": case == "DOUBLE_JAM_ABSENT_ESCAPE"})
            print(json.dumps({"port": port, "side": side, "case": case, "actual_blocked_stops": blocked}), flush=True)
        for index in range(41):
            q = 1.4 * index / 40.0
            r = max(0.0, min(1.2, 1.2 - 2.0 * (q - .1)))
            actual = dict(released)
            actual["key"] = released["key"].translate(qvec(port, q))
            for i in range(2):
                actual["stop" + str(i)] = released["stop" + str(i)].translate(rvec(port, r - 1.2))
            actual_pairs = pairs(checker, actual)
            if max(x["checked_common_mm3"] for x in actual_pairs) > EPS:
                raise ValueError("Independent normal release-then-key-withdraw geometry clashes")
            withdrawal.append({"port": port, "side": side, "key_q_mm": q,
                               "prescribed_rigid_nominal_track_stop_lift_mm": r, "actual_pairs": actual_pairs,
                               "position_is_not_friction_force_or_allowed_pose_set_qualification": True})
    for port, missing_side in itertools.product(("STOW", "OPEN"), "LR"):
        present_side = "R" if missing_side == "L" else "L"
        missing = dict(states[port + "_SEATED.step"][missing_side])
        present = states[port + "_SEATED.step"][present_side]
        del missing["key"]
        for i in range(2):
            missing["stop" + str(i)] = missing["stop" + str(i)].translate(rvec(port, -1.2))
        stroke = 1.1 if port == "STOW" else .55
        rows = []
        for index in range(23):
            pose = dict(missing)
            pose["pawn"] = missing["pawn"].translate(evec(port, missing_side, stroke * index / 22.0))
            stops = [checker.volume(pose["pawn"], pose["stop" + str(i)]) for i in range(2)]
            gaps = []
            for a, b in itertools.product(pose.values(), present.values()):
                axes = positive_bbox_separation(a, b)
                if not axes:
                    raise ValueError("Cross-side actual one-key fixture bodies lack positive AABB separation")
                gaps.append(max(axes.values()))
            rows.append({"fraction": index / 22.0, "actual_missing_side_stop_pawl_common_mm3": stops,
                         "minimum_cross_side_positive_bbox_separating_gap_mm": min(gaps),
                         "actual_cross_side_body_pair_count": len(gaps)})
        if not all(max(r["actual_missing_side_stop_pawl_common_mm3"][i] for r in rows) > EPS for i in range(2)):
            raise ValueError("Actual one-key absent side release is not blocked by both default-closed stops")
        one_key.append({"port": port, "missing_key_side": missing_side, "present_key_side": present_side,
                        "actual_SEATED_KEY_removed_and_both_STOPs_translated_down_1p2_mm": True,
                        "default_closed_is_prescribed_geometry_not_a_return_force_claim": True,
                        "actual_23_point_rows": rows})
    if any(sha(PROJECT / i["path"]) != i["sha256"] for i in inputs) or any(sha(HERE / n) != v for n, v in code_hashes.items()):
        raise ValueError("Final STEP or independent checker input changed during native verification")
    result = {"environment": {"host": platform.node(), "python": platform.python_version(), "cadquery": cq.__version__},
              "input_source_sha256": code_hashes, "actual_STEP_inputs": inputs,
              "source_and_STEP_bytes_unchanged": True, "actual_geometry_identities": identities,
              "actual_release_paths": motion, "actual_one_key_reconstructions": one_key,
              "actual_normal_release_then_withdraw_samples": withdrawal,
              "actual_OCC_signed_common_evaluations": checker.actual_occ_common_count,
              "validated_actual_AABB_proven_zero_evaluations": checker.validated_actual_AABB_proven_zero_count,
              "builder_is_not_imported_or_executed": True, "native_exit_code": 0,
              "double_jam_escape_is_retained_safety_failure": True,
              "unfastened_caps_and_whole_phone_load_paths_are_unqualified": True,
              "position_set_tolerance_and_physical_return_are_unqualified": True,
              "fixture_fabrication_go": False, "manufacturing_go": False}
    (HERE / "final-independent-export-check.json").write_text(json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n")
    print(json.dumps({"actual_STEPs": len(inputs), "actual_side_release_paths": len(motion),
                      "release_samples": sum(len(x["release_samples"]) for x in motion),
                      "one_key_samples": sum(len(x["actual_23_point_rows"]) for x in one_key),
                      "normal_withdraw_samples": len(withdrawal), "native_exit_code": 0,
                      "manufacturing_go": False}), flush=True)


if __name__ == "__main__":
    main()
