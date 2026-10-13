#!/usr/bin/env python3
"""Independent actual STEP proof for rigid research key-presence interposers.

The builder is never imported or executed. All bodies are identified through
their actual bounds, then checked with signed OCC common volumes. An independent
rectangular overlap model is checked against the real stop/pawl bodies along
the measured release stroke. Expected jammed-clear escape remains a failed
physical safety counterexample rather than being counted as qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import platform
import sys
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
REPO = PROJECT.parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO / "engineering/cad-review-20261013"))
from occ_signed_volume import common, validated_solid_volume

EPS = 1e-7


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_common(a, b):
    return common(a, b)["checked_volume_mm3"]


def canonical_bounds(shape, port, side):
    """Independently stated axis mapping, no mirror/build operation is reused."""
    bb = shape.BoundingBox()
    xc = -34.75 if side == "L" else 34.75
    sign = (-1 if side == "L" else 1) if port == "STOW" else (1 if side == "L" else -1)
    e = sorted((sign * (bb.xmin - xc), sign * (bb.xmax - xc)))
    if port == "STOW":
        q = sorted((1.2 - bb.ymin, 1.2 - bb.ymax))
        r = (bb.zmin - 10.0, bb.zmax - 10.0)
    else:
        q = (bb.zmin + 6.0, bb.zmax + 6.0)
        r = (bb.ymin + 10.0, bb.ymax + 10.0)
    return {"e": list(e), "q": list(q), "r": list(r)}


def world_e_delta(port, side, de):
    sign = (-1 if side == "L" else 1) if port == "STOW" else (1 if side == "L" else -1)
    return (sign * de, 0.0, 0.0)


def world_q_delta(port, dq):
    return (0.0, -dq, 0.0) if port == "STOW" else (0.0, 0.0, dq)


def world_r_delta(port, dr):
    return (0.0, 0.0, dr) if port == "STOW" else (0.0, dr, 0.0)


def intersection_length(first, second):
    return max(0.0, min(first[1], second[1]) - max(first[0], second[0]))


def box_overlap(first, second):
    return math.prod(intersection_length(first[a], second[a]) for a in ("e", "q", "r"))


def identify_side(solids, port, side):
    """Shape identity relies on actual geometry, never builder flags/part names."""
    own = [s for s in solids if (s.Center().x < 0) == (side == "L")]
    if len(own) not in (5, 6):
        raise ValueError(f"{port}/{side}: unexpected actual side body count {len(own)}")
    classified = {}
    for sh in own:
        bb = sh.BoundingBox()
        b = canonical_bounds(sh, port, side)
        if abs(bb.xlen - 1.0) < 1e-6 and abs((b["r"][1] - b["r"][0]) - 1.8) < 1e-6:
            if "stop" in classified:
                raise ValueError("Ambiguous stop geometry")
            classified["stop"] = sh
    candidates = [s for s in own if abs(s.BoundingBox().xlen - 4.0) < 1e-6
                  and canonical_bounds(s, port, side)["r"][1] - canonical_bounds(s, port, side)["r"][0] > .31]
    if len(candidates) not in (1, 2):
        raise ValueError("Cannot uniquely identify original four-mm sliders/key coupons")
    if port == "STOW":
        if len(candidates) != 1:
            raise ValueError("STOW original slider must be unique")
    else:
        candidates.sort(key=lambda s: -canonical_bounds(s, port, side)["q"][1])
    classified["pawl"] = candidates[0]
    if port == "STOW" and len(own) == 6:
        narrow_keys = [s for s in own if abs(s.BoundingBox().xlen - 1.7) < 1e-6]
        if len(narrow_keys) != 1:
            raise ValueError("Cannot uniquely identify STOW narrow key and original feature")
        classified["key"] = narrow_keys[0]
    elif len(candidates) == 2:
        classified["key"] = candidates[1]
    remaining = [s for s in own if all(s is not c for c in classified.values())]
    if len(remaining) != 3:
        raise ValueError("Cannot uniquely identify connected root and two retaining covers")
    remaining.sort(key=lambda s: validated_solid_volume(s), reverse=True)
    classified["root"], classified["cover_larger"], classified["cover_smaller"] = remaining
    if validated_solid_volume(classified["root"]) <= validated_solid_volume(classified["cover_larger"]):
        raise ValueError("Ambiguous root/cover geometry")
    return classified


def load_step(path):
    solids = cq.importers.importStep(str(path)).solids().vals()
    for solid in solids:
        validated_solid_volume(solid)
    return solids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=HERE / "independent-geometry-contract.json")
    args = parser.parse_args()
    source_before = {"builder_read_only": sha(PROJECT / "passive_veto.py"),
                     "independent_verifier": sha(Path(__file__)),
                     "independent_contract": sha(args.contract)}
    contract = json.loads(args.contract.read_text())
    steps = sorted((PROJECT / "cad").glob("*.step"))
    if not steps:
        raise ValueError("No final STEP inputs")
    if {p.name for p in steps} != set(contract["expected_path_blocked_by_file"]):
        raise ValueError("Actual final STEP set does not exactly match the independent geometry contract")
    state = {}
    inputs = []
    for path in steps:
        input_sha = sha(path)
        solids = load_step(path)
        if sha(path) != input_sha:
            raise ValueError("STEP changed during independent reimport")
        port = "STOW" if path.name.startswith("STOW_") else "OPEN"
        state[path.name] = {side: identify_side(solids, port, side) for side in "LR"}
        inputs.append({"path": str(path.relative_to(PROJECT)), "sha256": input_sha,
                       "actual_valid_positive_connected_solids": len(solids),
                       "raw_signed_volume_mm3": [validated_solid_volume(s) for s in solids]})
    rows = []
    for path in steps:
        port = "STOW" if path.name.startswith("STOW_") else "OPEN"
        full0 = state[f"{port}_FULL_KEYS_CAPTURED.step"]
        full1 = state[f"{port}_FULL_KEYS_RELEASED.step"]
        for side in "LR":
            parts = state[path.name][side]
            start_b = canonical_bounds(full0[side]["pawl"], port, side)
            end_b = canonical_bounds(full1[side]["pawl"], port, side)
            stroke = end_b["e"][0] - start_b["e"][0]
            if stroke <= 0.0 or abs(stroke - contract[port]["release_stroke_mm"]) > 1e-6:
                raise ValueError("Actual release stroke differs from independent interface contract")
            measured = canonical_bounds(parts["pawl"], port, side)
            offset = measured["e"][0] - start_b["e"][0]
            captured = parts["pawl"].translate(world_e_delta(port, side, -offset))
            stop_b = canonical_bounds(parts["stop"], port, side)
            lift = stop_b["r"][0]
            if ("key" in parts) != contract["expected_actual_key_presence_by_file"][path.name][side]:
                raise ValueError("Actual STEP key presence does not match independent state definition")
            if abs(lift - contract["expected_actual_stop_lift_by_file"][path.name][side]) > 1e-6:
                raise ValueError("Actual STEP stop elevation does not match independent state definition")
            key_withdraw = None
            if "key" in parts:
                key_withdraw = (canonical_bounds(parts["key"], port, side)["q"][0]
                                - canonical_bounds(full0[side]["key"], port, side)["q"][0])
                if abs(key_withdraw - contract["expected_key_withdraw_by_file"][path.name][side]) > 1e-6:
                    raise ValueError("Actual STEP key withdrawal does not match independent state definition")
            gate = {a: list(contract[port]["stop_gate_bounds"][a]) for a in ("e", "q", "r")}
            gate["r"] = [v + lift for v in gate["r"]]
            leaves = contract[port]["release_leaf_boxes"]
            sample_rows = []
            for index in range(45):
                de = stroke * index / 44.0
                pawl = captured.translate(world_e_delta(port, side, de))
                actual = checked_common(parts["stop"], pawl)
                supports = {n: checked_common(parts[n], pawl) for n in ("root", "cover_larger", "cover_smaller")}
                if any(v > EPS for v in supports.values()):
                    raise ValueError(f"{path.name}/{side}/{index}: reconstructed pawl motion crosses its physical guide or cover")
                key_common = checked_common(parts["key"], pawl) if "key" in parts else None
                if (key_common is not None and abs(key_withdraw) < 1e-6
                        and not contract["expected_path_blocked_by_file"][path.name][side]
                        and key_common > EPS):
                    raise ValueError("Actual full-key permitted release crosses the real key coupon")
                expected = 0.0
                for leaf in leaves:
                    moving_box = {a: list(leaf[a]) for a in ("e", "q", "r")}
                    moving_box["e"] = [v + de for v in moving_box["e"]]
                    expected += box_overlap(gate, moving_box)
                if abs(actual - expected) > 1e-6:
                    raise ValueError(f"{path.name}/{side}/{index}: actual OCC {actual} differs from independent rectangle {expected}")
                sample_rows.append({"fraction": index / 44.0, "release_stroke_mm": de,
                                    "actual_stop_pawl_common_mm3": actual,
                                    "independent_rectangle_common_mm3": expected,
                                    "actual_key_pawl_common_mm3": key_common,
                                    "actual_support_pawl_common_mm3": supports})
            blocked = any(s["actual_stop_pawl_common_mm3"] > EPS for s in sample_rows)
            expect_blocked = contract["expected_path_blocked_by_file"][path.name][side]
            if blocked != expect_blocked:
                raise ValueError(f"{path.name}/{side}: expected path blocked={expect_blocked}, measured {blocked}")
            pairs = [{"pair": [first, second], "common_mm3": checked_common(parts[first], parts[second])}
                     for first, second in itertools.combinations(parts, 2)]
            for pair in pairs:
                if set(pair["pair"]) != {"stop", "pawl"} and pair["common_mm3"] > EPS:
                    raise ValueError(f"{path.name}/{side}: unintended endpoint overlap {pair}")
            rows.append({"path": str(path.relative_to(PROJECT)), "port": port, "side": side,
                         "actual_key_present": "key" in parts, "measured_stop_lift_mm": lift,
                         "actual_measured_key_withdraw_mm": key_withdraw,
                         "actual_measured_release_stroke_mm": stroke,
                         "actual_endpoint_component_pairs": pairs,
                         "release_path_samples": sample_rows, "release_path_is_blocked": blocked,
                         "traversal_is_reconstructed_at_current_key_and_stop_state": True,
                         "withdrawn_key_state_reconstruction_is_counterfactual_release_attempt": "KEY_WITHDRAW" in path.name,
                         "endpoint_only_is_not_path_clearance": True,
                         "jammed_clear_fault_is_retained_escape": "JAMMED_CLEAR" in path.name})
    coupled_rows = []
    for port in ("STOW", "OPEN"):
        for side in "LR":
            released = state[f"{port}_FULL_KEYS_RELEASED.step"][side]
            measured_lift = canonical_bounds(released["stop"], port, side)["r"][0]
            for index in range(45):
                withdraw = .7 * index / 44.0
                rigid_lift = max(0.0, 1.2 - 2.0 * withdraw)
                moving = dict(released)
                moving["key"] = released["key"].translate(world_q_delta(port, withdraw))
                moving["stop"] = released["stop"].translate(world_r_delta(port, rigid_lift - measured_lift))
                pairs = [{"pair": [first, second], "common_mm3": checked_common(moving[first], moving[second])}
                         for first, second in itertools.combinations(moving, 2)]
                if any(p["common_mm3"] > EPS for p in pairs):
                    raise ValueError(f"{port}/{side}: actual release-then-withdraw body collision at q={withdraw}")
                coupled_rows.append({"port": port, "side": side, "key_withdraw_mm": withdraw,
                                     "prescribed_stop_lift_mm": rigid_lift,
                                     "all_actual_component_pairs": pairs,
                                     "imposed_rigid_contact_position_is_not_measured_spring_return": True})
    source_after = {"builder_read_only": sha(PROJECT / "passive_veto.py"),
                    "independent_verifier": sha(Path(__file__)),
                    "independent_contract": sha(args.contract)}
    if source_before != source_after or any(sha(PROJECT / r["path"]) != r["sha256"] for r in inputs):
        raise ValueError("Independent verification inputs changed during native execution")
    result = {
        "environment": {"host": platform.node(), "python": platform.python_version(), "cadquery": cq.__version__},
        "source_sha256": source_before, "all_source_and_STEP_bytes_unchanged_during_verification": True,
        "actual_STEP_inputs": inputs, "independent_actual_geometry_rows": rows,
        "independent_release_then_key_withdraw_samples": coupled_rows,
        "all_expected_actual_geometric_checks_passed": True,
        "all_bodies_are_single_connected_valid_positive_solids": True,
        "connected_solid_geometry_does_not_prove_physical_mounting_or_spring_return": True,
        "jammed_clear_safety_qualification": False, "spring_return_qualification": False,
        "material_strength_qualification": False, "fixture_fabrication_go": False,
        "manufacturing_go": False, "native_exit_code": 0,
    }
    (HERE / "independent-exported-veto-check.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"STEP_inputs": len(inputs), "side_paths_checked": len(rows),
                      "actual_release_samples_checked": sum(len(r["release_path_samples"]) for r in rows),
                      "actual_release_then_withdraw_samples_checked": len(coupled_rows),
                      "expected_jammed_clear_escape_sides": sum(r["jammed_clear_fault_is_retained_escape"] for r in rows),
                      "manufacturing_go": False}, indent=2))


if __name__ == "__main__":
    main()
