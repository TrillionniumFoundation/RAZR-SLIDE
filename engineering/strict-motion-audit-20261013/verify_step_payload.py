"""Read all transferred STEP roots; refuse any free non-solid payload leaf."""
from pathlib import Path
import argparse
import hashlib
import json

import cadquery as cq

from occ_signed_volume import InconsistentGeometry, validated_solid_volume


def full_solid_payload(roots):
    counts, solids = {}, []

    def visit(shape):
        kind = shape.ShapeType()
        counts[kind] = counts.get(kind, 0) + 1
        if kind == "Solid":
            validated_solid_volume(shape)
            solids.append(shape)
            return
        if kind != "Compound":
            raise InconsistentGeometry("Free non-solid STEP payload leaf: " + kind)
        if not shape.isValid():
            raise InconsistentGeometry("Invalid STEP Compound payload")
        children = list(shape)
        if not children:
            raise InconsistentGeometry("Empty STEP Compound payload")
        for child in children:
            visit(child)

    if not roots:
        raise InconsistentGeometry("No transferred STEP roots")
    for root in roots:
        visit(root)
    return solids, counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prior", type=Path, default=Path(__file__).parent.parent / "cad-review-20261013")
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("full_step_payload_validation.json"))
    args = parser.parse_args()
    old = json.loads((args.prior / "R45_CAD_motion_audit.json").read_text())
    rows = []
    for item in old["new_STEP_exports"]:
        path = args.prior / item["path"]
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        assert sha == item["sha256"]
        roots = cq.importers.importStep(str(path)).vals()
        solids, counts = full_solid_payload(roots)
        assert len(solids) == 23
        rows.append({"referenced_path": item["path"], "sha256": sha,
                     "transferred_root_count": len(roots), "visited_shape_type_counts": counts,
                     "free_non_solid_leaf_count": 0, "valid_positive_single_solids": len(solids),
                     "solid_signed_volumes_mm3": [validated_solid_volume(solid) for solid in solids]})
    report = {"source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "referenced_occ_guard_sha256": hashlib.sha256(Path(__file__).with_name("occ_signed_volume.py").read_bytes()).hexdigest(),
              "STEP_full_payload_validation_complete": True, "rows": rows,
              "full_payload_topology_check_does_not_prove_physical_or_topological_identity": True,
              "manufacturing_go": False}
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"files": len(rows), "solid_leaf_count": sum(row["valid_positive_single_solids"] for row in rows),
                      "free_non_solid_leaves": 0}, indent=2))


if __name__ == "__main__":
    main()
