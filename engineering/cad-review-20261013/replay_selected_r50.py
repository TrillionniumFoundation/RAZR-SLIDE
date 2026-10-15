#!/usr/bin/env python3
"""Replay selected R50 representative failures with checked per-cell OCC commons.

Does not repeat rejected route searches or mutate the immutable R50 baseline.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import sys
import zipfile
from prepare_inputs import safe_extract, digest
from occ_signed_volume import cells_against_body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true",
        help="Restore/check the isolated source tree without repeating representative geometry")
    args = parser.parse_args()
    cache = args.cache.resolve()
    source = safe_extract(args.archive, cache,
        "86f226f9bce3a3f0659737327c7cc32415eed3b9be3f96f35a746ac32844dfd6", 41)
    parent49 = cache / "baseline/R49_PARENT_UNMODIFIED.zip"
    if digest(parent49) != "494fbdb0b726f068dc5e72903ca4c99a4f188835929e8b22a6e339e89f8ba00d":
        raise ValueError("Selected R50 parent mismatch")
    with zipfile.ZipFile(parent49) as package:
        for name in ("README_先读_R49.md", "src/r49_cross_section_gate.py",
                     "results/R49_offgrid_crosssection_negative_gate.json", "baseline/R48_PARENT_UNMODIFIED.zip"):
            path = cache / name
            data = package.read(name)
            if path.exists() and path.read_bytes() != data:
                raise ValueError("Changed R49 ancestor")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    parent48 = cache / "baseline/R48_PARENT_UNMODIFIED.zip"
    safe_extract(parent48, cache / "baseline/R48",
        "b9a2904ea79e348576120e63f24cdebc2efd2b6bf68ff40f9cdad1fe544d2e72", 29)
    safe_extract(cache / "baseline/R48/baseline/R47_PARENT_UNCHANGED.zip", cache / "baseline/R47",
        "25af6127c7bc51b0f62deaef86963f3fed818e93d14ff7dd7a9240afcb692f45", 28)
    sys.path.insert(0, str(cache / "src"))
    import r50_full_span_finite_ribbon as r50
    lineage = r50.verify_lineage(parent49)
    if args.prepare_only:
        print(json.dumps({"isolated_source_prepared": str(cache), "selected_source": source,
            "lineage": lineage, "new_geometry_run": False}), flush=True)
        return
    r47, routing, A, B = r50.get_reference()
    candidate = routing.CANDIDATES[2]
    calls = []

    def checked_intersection(cells, body):
        record = cells_against_body(cells, body)
        calls.append(record)
        return {"mm3": record["sum_of_checked_cell_common_volumes_mm3"],
            "solid_count": sum(row["checked_volume_mm3"] > 1e-7 for row in record["per_cell"]),
            "bbox_candidates": len(cells), "computed": True}

    r50.solid_intersection = checked_intersection
    rows = []
    for name, s, q in (("STOW", 0., 0.), ("DOCK_4p013", 79.75, 4.013)):
        first = len(calls)
        row = r50.make_row(r47, routing, candidate, name, s, q, A, B)
        row["per_cell_checked_common_reports"] = calls[first:]
        row["aggregation_differs_from_legacy_compound_common"] = True
        if row["free_span_B_occ_intersection_mm3"] <= 1e-7:
            raise ValueError("Selected known-failing R50 route unexpectedly ceased to show B collision")
        rows.append(row)
        print(name, "checked cell common B", row["free_span_B_occ_intersection_mm3"], flush=True)
    report = {"scope": "Selected R50 verification base; two representative existing failure replays",
        "selected_source": source, "source_archive": args.archive.name, "lineage": lineage,
        "new_fix": "Every single-cell OCC common checked for finite signed volume and participating-solid upper bounds",
        "actual_new_poses": len(rows), "rows": rows,
        "compound_common_not_equivalent_to_sum_with_overlapping_loft_cells": True,
        "no_manufacturing_route_claim": True, "manufacturing_go": False}
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
