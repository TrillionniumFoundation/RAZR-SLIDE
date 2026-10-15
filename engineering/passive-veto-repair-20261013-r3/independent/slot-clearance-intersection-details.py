#!/usr/bin/env python3
"""Localize retained actual collisions using the immutable old-source snapshot."""
import hashlib
import json
import sys
import types
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SOURCE = HERE / "slot-clearance-input-builder.py"
model = types.ModuleType("slot_collision_localization_snapshot")
model.__file__ = str(HERE.parent / "passive_repair.py")
exec(compile(SOURCE.read_bytes(), model.__file__, "exec"), model.__dict__)


def bbox(shape):
    b = shape.BoundingBox()
    return {k: float(getattr(b, k)) for k in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")}


def main():
    report = json.loads((HERE / "slot-clearance-actual-counterexamples.json").read_text())
    source_sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if source_sha != report["executed_builder_snapshot_sha256"]:
        raise ValueError("Collision localization snapshot is not the executed actual-counterexample input")
    rows = []
    for row in report["actual_path_rows"]:
        maximum = max(row["actual_motion_samples"], key=lambda x: x["actual_key_pawl_common_mm3"])
        if maximum["actual_key_pawl_common_mm3"] <= 1e-7:
            continue
        parts = model.scene(row["port"], row["side"], row["key_q_mm"], maximum["fraction"], True,
                            {0: row["forced_both_stop_lift_mm"], 1: row["forced_both_stop_lift_mm"]})
        actual = model.common(parts["KEY"], parts["PAWL"])
        if abs(actual["checked_volume_mm3"] - maximum["actual_key_pawl_common_mm3"]) > 1e-7:
            raise ValueError("Actual frozen-source collision no longer matches native counterexample")
        overlap = parts["KEY"].intersect(parts["PAWL"])
        components = [{"actual_signed_volume_mm3": model.validated_solid_volume(s), "actual_world_bbox_mm": bbox(s)}
                      for s in overlap.Solids()]
        rows.append({"port": row["port"], "side": row["side"], "key_q_mm": row["key_q_mm"],
                     "actual_pawl_retreat_fraction": maximum["fraction"],
                     "actual_checked_key_pawl_common": actual,
                     "actual_overlap_components": components})
    result = {"executed_builder_snapshot_sha256": source_sha,
              "independent_detail_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "actual_positive_collision_rows": rows,
              "new_stow_q_0p15_overlap_must_not_be_claimed_as_qualified_capture": True,
              "native_exit_code": 0, "manufacturing_go": False}
    (HERE / "slot-clearance-positive-intersection-details.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
