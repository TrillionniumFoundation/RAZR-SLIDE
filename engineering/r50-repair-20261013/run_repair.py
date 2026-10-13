#!/usr/bin/env python3
"""Run original R50 receipt tests, negative guard tests, and repaired real poses."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True,
        help="Isolated verified R50 extraction prepared by replay_selected_r50.py")
    args = parser.parse_args()
    source = args.source_root.resolve()
    sys.path.insert(0, str(ROOT / "src"))
    repaired = load("r50_full_span_finite_ribbon", ROOT / "src/r50_full_span_finite_ribbon.py")
    lineage = repaired.configure_source_root(source)
    original_tests = load("r50_original_receipt_tests", source / "tests/test_r50.py")
    suite = unittest.defaultTestLoader.loadTestsFromModule(original_tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit("Original R50 receipt tests failed")
    # All guard imports resolve to the repaired implementation; no shadow old module.
    guard_tests = load("r50_repaired_guard_tests", ROOT.parent / "cad-review-20261013/test_occ_signed_volume.py")
    guard_suite = unittest.defaultTestLoader.loadTestsFromModule(guard_tests)
    guard_result = unittest.TextTestRunner(verbosity=2).run(guard_suite)
    if not guard_result.wasSuccessful():
        raise SystemExit("New signed-volume guard tests failed")
    participant_tests = load("r50_repaired_participant_tests", ROOT / "test_repaired_intersection.py")
    participant_suite = unittest.defaultTestLoader.loadTestsFromModule(participant_tests)
    participant_result = unittest.TextTestRunner(verbosity=2).run(participant_suite)
    if not participant_result.wasSuccessful():
        raise SystemExit("Participating solid validation tests failed")
    r47, routing, A, B = repaired.get_reference()
    candidate = routing.CANDIDATES[2]
    rows = []
    for name, s, q in (("STOW", 0., 0.), ("DOCK_4p013", 79.75, 4.013)):
        row = repaired.make_row(r47, routing, candidate, name, s, q, A, B)
        if row["free_span_B_occ_intersection_mm3"] <= 1e-7:
            raise ValueError("Known rejected route lost its B collision witness")
        if not row["per_cell_signed_volume_guard_applied"]:
            raise ValueError("Real R50 geometry did not use repaired signed-volume code")
        rows.append(row)
        print(name, "repaired free-span B", row["free_span_B_occ_intersection_mm3"], flush=True)
    report = {"source_provenance": json.loads((ROOT / "source_provenance.json").read_text()),
        "lineage": lineage, "original_R50_receipt_tests_run": result.testsRun,
        "new_guard_tests_run": guard_result.testsRun, "actual_new_repaired_R50_poses": len(rows),
        "new_bbox_participant_tests_run": participant_result.testsRun,
        "original_receipt_tests_do_not_mean_all_63_geometries_recomputed": True,
        "rows": rows, "manufacturing_go": False}
    (ROOT / "R50_repaired_execution_receipt.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
