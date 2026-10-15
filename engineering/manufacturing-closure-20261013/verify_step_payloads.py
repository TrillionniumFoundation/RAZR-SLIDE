#!/usr/bin/env python3
"""Inspect entire transferred STEP shape trees, without a solids-only filter.

This verifies serialization of research/failure assemblies. It does not test
clearance, material strength, installed fit, or manufacturing qualification.
"""
from pathlib import Path
import hashlib
import json
import math
import platform
import cadquery as cq

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def inspect_node(shape, solids):
    kind = shape.ShapeType()
    if kind == "Compound":
        children = list(shape)
        if not children:
            raise ValueError("Empty Compound in transferred STEP")
        for child in children:
            inspect_node(child, solids)
    elif kind == "Solid":
        volume = float(shape.Volume())
        if not shape.isValid() or not math.isfinite(volume) or volume <= 0:
            raise ValueError("Invalid or nonpositive signed Solid in transferred STEP")
        solids.append(volume)
    else:
        raise ValueError("Unexpected transferred STEP leaf: " + kind)


def main():
    # Actual negative witness: a valid single-solid Compound with an extra Wire
    # survives a solids-only selection, but cannot pass whole-payload inspection.
    solid = cq.Workplane("XY").box(1, 1, 1).val()
    wire = cq.Workplane("XY").rect(1, 1).wire().val().translate((5, 0, 0))
    bad = cq.Compound.makeCompound([solid, wire])
    assert bad.isValid() and len(bad.Solids()) == 1
    rejected = False
    try:
        inspect_node(bad, [])
    except ValueError as error:
        rejected = True
        failure = str(error)
    if not rejected:
        raise ValueError("Actual extra-Wire counterexample was silently accepted")
    good = []
    inspect_node(cq.Compound.makeCompound([cq.Compound.makeCompound([solid])]), good)
    assert len(good) == 1

    rows = []
    for folder in ("mechanical-closure-20261013/cad", "native-endpoint-20261013/step"):
        for path in sorted((ROOT / "engineering" / folder).glob("*.step")):
            if "mechanical" in folder:
                expected = 6 if "KEY_ABSENT" in path.name else 8
            else:
                expected = 10 if "STATIC_ENDPOINT" in path.name else 29
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            shapes = cq.importers.importStep(str(path)).vals()
            volumes = []
            for shape in shapes:
                inspect_node(shape, volumes)
            if len(volumes) != expected:
                raise ValueError("Unexpected complete STEP solid count: " + str(path))
            if hashlib.sha256(path.read_bytes()).hexdigest() != before:
                raise ValueError("Source STEP changed during read-only verification")
            rows.append({"path": str(path.relative_to(ROOT)), "sha256": before,
                         "transferred_roots": len(shapes), "valid_positive_solids": len(volumes),
                         "unexpected_non_solid_leaves": 0, "signed_solid_volumes_mm3": volumes})
    if len(rows) != 13:
        raise ValueError("Expected ten mechanical and three endpoint research STEP files")
    report = {"environment": {"python": platform.python_version(), "cadquery": cq.__version__},
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "actual_extra_wire_counterexample": {"isValid": True, "Solids_count": 1,
                                                    "rejected_by_complete_tree": True, "error": failure},
              "pure_nested_single_solid_compound_accepted": True, "files": rows,
              "all_complete_transferred_trees_checked": True,
              "this_is_not_clearance_or_physical_qualification": True, "manufacturing_go": False}
    (OUT / "complete_step_payload_receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"STEP_files": len(rows), "valid_positive_solids": sum(r["valid_positive_solids"] for r in rows),
                      "unexpected_non_solid_leaves": 0, "manufacturing_go": False}))


if __name__ == "__main__":
    main()
