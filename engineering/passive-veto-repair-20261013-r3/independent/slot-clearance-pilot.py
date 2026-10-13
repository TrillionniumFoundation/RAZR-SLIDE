#!/usr/bin/env python3
"""Actual source-constructor counterexamples; not final independent STEP proof.

The builder is compiled from an exact preserved read-only snapshot with its
original source pathname and non-main module name. Parent may advance its live
file after the snapshot; this run continues to use the archived exact bytes.
"""
from __future__ import annotations
import hashlib
import itertools
import json
import math
import platform
import sys
import types
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / "passive_repair.py"
REPO = HERE.parents[2]
SOURCE_BYTES = ORIGINAL.read_bytes()
SNAPSHOT = HERE / "slot-clearance-input-builder.py"
SNAPSHOT.write_bytes(SOURCE_BYTES)
builder = types.ModuleType("r3_slot_clearance_frozen_source")
builder.__file__ = str(ORIGINAL)
exec(compile(SOURCE_BYTES, str(ORIGINAL), "exec"), builder.__dict__)
EPS = 1e-7


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dependencies():
    roots = (REPO / "baselines", REPO / "engineering/passive-veto-design-20261013-r2",
             REPO / "engineering/mechanical-closure-20261013", REPO / "engineering/cad-review-20261013")
    result = {str(Path(__file__).relative_to(REPO)): sha(Path(__file__)),
              str(SNAPSHOT.relative_to(REPO)): sha(SNAPSHOT)}
    for module in list(sys.modules.values()):
        value = getattr(module, "__file__", None)
        if value:
            path = Path(value).resolve()
            if path.is_file() and any(path.is_relative_to(root) for root in roots):
                result[str(path.relative_to(REPO))] = sha(path)
    return result


def segment_distance(point, first, last):
    dq, dr = last[0] - first[0], last[1] - first[1]
    t = ((point[0] - first[0]) * dq + (point[1] - first[1]) * dr) / (dq * dq + dr * dr)
    t = max(0.0, min(1.0, t))
    return math.hypot(point[0] - first[0] - t * dq, point[1] - first[1] - t * dr)


def checked_pairs(parts):
    return [{"parts": [a, b], "actual_common_mm3": builder.cv(parts[a], parts[b])}
            for a, b in itertools.combinations(parts, 2)]


def save_actual(parts, label):
    path = HERE / ("slot-clearance-" + label + ".step")
    assembly = builder.cq.Assembly(name=label)
    for name, shape in parts.items():
        builder.validated_solid_volume(shape)
        assembly.add(shape, name=name)
    assembly.save(str(path), exportType="STEP")
    restored = builder.cq.importers.importStep(str(path)).solids().vals()
    actual = sorted(builder.validated_solid_volume(s) for s in restored)
    expected = sorted(builder.validated_solid_volume(s) for s in parts.values())
    if len(actual) != len(expected) or any(abs(a - b) > 1e-6 for a, b in zip(actual, expected)):
        raise ValueError("Actual snapshot STEP reimport changed solid count/volume")
    return {"path": path.name, "sha256": sha(path), "valid_positive_reimported_solids": len(actual),
            "geometry_only": True, "manufacturing_go": False}


def main():
    sources = dependencies()
    paths, circles, exports = [], [], []
    nodes = [(-1.3, 0.0), (-.7, 0.0), (-.1, 1.2), (.3, 1.2)]
    for port, side in itertools.product(("STOW", "OPEN"), "LR"):
        for q, lift in ((.20, 1.11), (.15, 1.20)):
            samples = []
            for index in range(23):
                parts = builder.scene(port, side, q, index / 22.0, True, {0: lift, 1: lift})
                pairs = checked_pairs(parts)
                stop_path = [x["actual_common_mm3"] for x in pairs
                             if "PAWL" in x["parts"] and any(n.startswith("STOP_") for n in x["parts"])]
                key_stop = [x["actual_common_mm3"] for x in pairs
                            if "KEY" in x["parts"] and any(n.startswith("STOP_") for n in x["parts"])]
                key_pawl = next(x["actual_common_mm3"] for x in pairs if set(x["parts"]) == {"KEY", "PAWL"})
                samples.append({"fraction": index / 22.0, "actual_pairs": pairs,
                                "actual_max_stop_pawl_common_mm3": max(stop_path),
                                "actual_max_key_stop_common_mm3": max(key_stop),
                                "actual_key_pawl_common_mm3": key_pawl})
            row = {"port": port, "side": side, "key_q_mm": q, "forced_both_stop_lift_mm": lift,
                   "actual_motion_samples": samples,
                   "interposer_retreat_path_clear": max(x["actual_max_stop_pawl_common_mm3"] for x in samples) <= EPS,
                   "actual_key_stop_clear": max(x["actual_max_key_stop_common_mm3"] for x in samples) <= EPS,
                   "actual_whole_assembly_retreat_path_clear": max(p["actual_common_mm3"] for s in samples for p in s["actual_pairs"]) <= EPS,
                   "actual_max_key_pawl_common_mm3": max(x["actual_key_pawl_common_mm3"] for x in samples),
                   "q_beyond_declared_0p10_plateau": q > .10,
                   "not_a_physical_escape_or_fault_qualification": True}
            paths.append(row)
            print(json.dumps({k: v for k, v in row.items() if k != "actual_motion_samples"}), flush=True)
        for q, lift in itertools.product((.15, .18, .20, .22), (1.1, 1.11, 1.2)):
            point = (-q, lift)
            minimum = min(segment_distance(point, a, b) for a, b in zip(nodes, nodes[1:]))
            parts = builder.scene(port, side, q, 1.0, True, {0: lift, 1: lift})
            actual = [builder.cv(parts["KEY"], parts["STOP_" + str(i)]) for i in range(2)]
            circles.append({"port": port, "side": side, "key_q_mm": q, "forced_both_stop_lift_mm": lift,
                            "independently_computed_min_pin_center_to_slot_centerline_mm": minimum,
                            "single_capsule_sufficient_circle_containment": minimum + builder.PIN_R <= builder.SLOT_R,
                            "single_capsule_test_is_sufficient_not_necessary_for_union_junction": True,
                            "actual_key_stop_signed_common_mm3": actual,
                            "actual_key_stop_clear": max(actual) <= EPS})
    for port, q, lift, fraction, label in itertools.product(("STOW", "OPEN"), (.20,), (1.11,), (0.0, 1.0), ("q0p20_lift1p11",)):
        combined = {}
        for side in "LR":
            combined.update({side + "_" + n: s for n, s in builder.scene(port, side, q, fraction, True, {0: lift, 1: lift}).items()})
        exports.append(save_actual(combined, port + "_" + label + ("_CAPTURED_OVERLAP" if fraction == 0 else "_RELEASED")))
    for port in ("STOW", "OPEN"):
        combined = {}
        for side in "LR":
            combined.update({side + "_" + n: s for n, s in builder.scene(port, side, .15, 1.0, True, {0: 1.2, 1: 1.2}).items()})
        exports.append(save_actual(combined, port + "_q0p15_lift1p20_BEYOND_PLATEAU_RELEASED"))
    if sources != dependencies():
        raise ValueError("Preserved source snapshot or imported old dependency changed")
    report = {"environment": {"host": platform.node(), "python": platform.python_version(), "cadquery": builder.cq.__version__},
              "source_sha256": sources, "executed_builder_snapshot_sha256": hashlib.sha256(SOURCE_BYTES).hexdigest(),
              "exact_snapshot_compiled_with_original_source_filename_but_non_main_module": True,
              "native_source_constructors_used_read_only_no_main": True,
              "not_final_independent_STEP_verification": True,
              "actual_path_rows": paths, "independent_circle_and_actual_shape_rows": circles,
              "actual_STEP_counterexamples": exports,
              "physical_material_force_jam_or_return_qualification": False,
              "native_exit_code": 0, "manufacturing_go": False}
    path = HERE / "slot-clearance-actual-counterexamples.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"actual_path_rows": len(paths), "actual_circle_shape_rows": len(circles),
                      "actual_STEP_counterexamples": len(exports), "native_exit_code": 0,
                      "manufacturing_go": False}), flush=True)


if __name__ == "__main__":
    main()
