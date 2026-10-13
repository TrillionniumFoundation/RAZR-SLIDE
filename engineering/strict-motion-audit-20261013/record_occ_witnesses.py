"""Record actual OCC witnesses; no claim of manufacturing qualification."""
from pathlib import Path
import hashlib
import json
import platform

import cadquery as cq

from occ_signed_volume import InconsistentGeometry
from strict_intersections import strict_common


def shape_summary(shape):
    return {"isValid": shape.isValid(), "shape_type": shape.ShapeType(),
            "solid_count": len(shape.Solids()), "raw_signed_volume_mm3": float(shape.Volume())}


def main():
    box = cq.Workplane("XY").box(1, 1, 1).val()
    small = cq.Workplane("XY").box(1e-5, 1e-5, 1e-5).val()
    reverse = lambda shape: cq.Shape.cast(shape.wrapped.Reversed())
    wire = cq.Workplane("XY").rect(1, 1).val()
    alias_box = cq.Workplane("XY").box(1, 2, 3).val()
    alias = cq.Compound.makeCompound([alias_box, alias_box.Wires()[0]])
    rows = []
    for label, a, b in (
        ("reversed_far_body", box, reverse(box.translate((10, 0, 0)))),
        ("valid_wire_positive_Volume_is_not_solid", box, wire.translate((10, 0, 0))),
        ("repeated_existing_wire_same_topology_count_and_exact_volume", box, alias),
        ("real_negative_common_about_minus_1e_minus15", reverse(small), small),
        ("exact_face_touch_zero_common_no_positive_clearance", box, box.translate((1, 0, 0))),
        ("kernel_zero_for_subtolerance_1e_minus8_overlap", box, box.translate((1-1e-8, 0, 0))),
        ("resolved_1e_minus6_overlap", box, box.translate((1-1e-6, 0, 0))),
    ):
        row = {"label": label, "a": shape_summary(a), "b": shape_summary(b)}
        if label.startswith("real_negative_common"):
            row["direct_unguarded_OCC_common_witness"] = shape_summary(a.intersect(b))
            assert row["direct_unguarded_OCC_common_witness"]["raw_signed_volume_mm3"] < 0.
            row["negative_witness_has_reversed_input_and_does_not_assert_normal_inputs_produce_negative_common"] = True
        try:
            row["strict_result"] = strict_common(a, b)
            row["strict_guard_outcome"] = "accepted"
        except InconsistentGeometry as error:
            row["strict_guard_outcome"] = "rejected"
            row["rejection_reason"] = str(error)
        if label in ("reversed_far_body", "valid_wire_positive_Volume_is_not_solid",
                     "repeated_existing_wire_same_topology_count_and_exact_volume",
                     "real_negative_common_about_minus_1e_minus15"):
            assert row["strict_guard_outcome"] == "rejected"
        if label == "kernel_zero_for_subtolerance_1e_minus8_overlap":
            # These are axis-aligned unit cubes with displacement 1-1e-8 mm.
            # Analytic interval overlap is positive even if OCC regularizes it.
            displacement = 1-1e-8
            expected_overlap = max(0., min(.5, displacement+.5) - max(-.5, displacement-.5))
            row["independent_axis_interval_overlap_mm"] = expected_overlap
            row["independent_analytic_box_common_volume_mm3"] = expected_overlap * 1. * 1.
            row["observed_kernel_volume_mm3"] = row["strict_result"]["raw_signed_volume_mm3"]
            row["qualification_status"] = "UNCERTAIN_KERNEL_ZERO_FOR_REAL_SUBTOLERANCE_OVERLAP"
            row["signed_guard_does_not_detect_this_real_overlap"] = True
            assert row["independent_analytic_box_common_volume_mm3"] > 0.
        rows.append(row)
    report = {"environment": {"python": platform.python_version(), "cadquery": cq.__version__},
              "strict_guard_sha256": hashlib.sha256(Path(__file__).with_name("strict_intersections.py").read_bytes()).hexdigest(),
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "rows": rows, "manufacturing_go": False,
              "zero_OCC_volume_is_not_subtolerance_no_contact_or_positive_clearance": True}
    Path(__file__).with_name("real_occ_witnesses.json").write_text(json.dumps(report, indent=2) + "\n")
    uncertain = next(row for row in rows if row["label"] == "kernel_zero_for_subtolerance_1e_minus8_overlap")
    Path(__file__).with_name("UNCERTAIN_subtolerance_overlap_counterexample.json").write_text(
        json.dumps({"source_sha256": report["source_sha256"], "row": uncertain,
                    "manufacturing_go": False}, indent=2) + "\n")
    print(json.dumps({"witnesses": len(rows), "rejected": sum(row["strict_guard_outcome"] == "rejected" for row in rows)}, indent=2))


if __name__ == "__main__":
    main()
