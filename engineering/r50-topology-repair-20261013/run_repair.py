#!/usr/bin/env python3
"""Run original R50 receipt tests, negative guard tests, and repaired real poses."""
import argparse
import importlib.util
import hashlib
import json
import platform
import datetime
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    provenance = json.loads((ROOT / "source_provenance.json").read_text())
    for relative, expected in provenance["source_cache_manifest_before"].items():
        if digest(source / relative) != expected:
            raise ValueError("Verified R50 source-cache hash mismatch: " + relative)
    for relative, expected in provenance["current_code_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError("New topology-repair source hash mismatch: " + relative)
    sys.path.insert(0, str(ROOT / "src"))
    repaired = load("r50_full_span_finite_ribbon", ROOT / "src/r50_full_span_finite_ribbon.py")
    lineage = repaired.configure_source_root(source)
    original_tests = load("r50_original_receipt_tests", source / "tests/test_r50.py")
    suite = unittest.defaultTestLoader.loadTestsFromModule(original_tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit("Original R50 receipt tests failed")
    # All guard imports resolve to the repaired implementation; no shadow old module.
    guard_tests = load("r50_repaired_guard_tests", ROOT / "test_occ_signed_volume.py")
    guard_suite = unittest.defaultTestLoader.loadTestsFromModule(guard_tests)
    guard_result = unittest.TextTestRunner(verbosity=2).run(guard_suite)
    if not guard_result.wasSuccessful():
        raise SystemExit("New signed-volume guard tests failed")
    participant_tests = load("r50_repaired_participant_tests", ROOT / "test_repaired_intersection.py")
    participant_suite = unittest.defaultTestLoader.loadTestsFromModule(participant_tests)
    participant_result = unittest.TextTestRunner(verbosity=2).run(participant_suite)
    if not participant_result.wasSuccessful():
        raise SystemExit("Participating solid validation tests failed")
    topology_tests = load("r50_topology_participant_tests", ROOT / "test_topology.py")
    topology_suite = unittest.defaultTestLoader.loadTestsFromModule(topology_tests)
    topology_result = unittest.TextTestRunner(verbosity=2).run(topology_suite)
    if not topology_result.wasSuccessful():
        raise SystemExit("R50 actual mixed/repeated topology participant tests failed")
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
    source_after = {relative: digest(source / relative)
        for relative in provenance["source_cache_manifest_before"]}
    if source_after != provenance["source_cache_manifest_before"]:
        raise ValueError("Original verified source cache was modified")
    report = {"source_provenance": provenance,
        "machine": platform.node(), "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "native_process_exit": 0, "source_cache_hashes_unchanged": True,
        "topology_guard_accepts_only_Solid_or_pure_nested_single_child_Compound": True,
        "lineage": lineage, "original_R50_receipt_tests_run": result.testsRun,
        "new_guard_tests_run": guard_result.testsRun, "actual_new_repaired_R50_poses": len(rows),
        "new_bbox_participant_tests_run": participant_result.testsRun,
        "new_actual_R50_topology_tests_run": topology_result.testsRun,
        "original_receipt_tests_do_not_mean_all_63_geometries_recomputed": True,
        "rows": rows, "manufacturing_go": False}
    (ROOT / "R50_topology_repaired_execution_receipt.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
