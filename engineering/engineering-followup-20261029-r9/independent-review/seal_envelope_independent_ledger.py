"""Seal actual producer/reader accounting and separate unresolved obligations.

Only saved files are read. No geometry, primitive computation or solver runs.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENV = HERE.parent / "envelope"


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def identity(path):
    path = Path(path)
    return {"bytes": path.stat().st_size,
            "sha256": hashlib.file_digest(path.open("rb"), "sha256").hexdigest()}


def bind(path, expected):
    actual = identity(path)
    need(actual == {k: expected[k] for k in ("bytes", "sha256")}, "immutable evidence identity")
    return actual


def read(path):
    return json.loads(Path(path).read_text())


def main(args):
    producer_path = ENV / "cylinder-slab-all16-attempt1/report.json"
    reader_path = ENV / "independent-cylinder-slab-all16-attempt1/report.json"
    producer, reader = read(producer_path), read(reader_path)
    budget_path = HERE / "R9_CYLINDER_SLAB_RECORDED_BUDGET_AUDIT.json"
    budget = read(budget_path)
    need(budget["completed"] and reader["completed"] is True, "completed budget and full reader")
    bind(producer_path, budget["producer_report"])
    bind(producer_path, reader["producer_report"])
    for key in ("source", "independent_checker"):
        bind(reader[key]["path"], reader[key])
    need("failure" not in reader, "reader has no retained execution failure")
    need(producer["conditional_pass_count"] == reader["conditional_pass_count"] == 16, "all16 conditional gates")
    need(len(producer["frames"]) == len(reader["frames"]) == 16, "all16 complete records")
    need(producer["global_splits"] == reader["global_splits"] == 718, "original global split accounting")
    for key in ("pieces", "channels", "tiny_nodes", "tested_nodes", "new_line", "new_plane", "new_quadric"):
        need(producer["counts"].get(key, 0) == reader["totals"].get(key, 0), "producer/reader counter: " + key)
    need(reader["totals"]["terminal_leaves"] == 1537 + 718, "complete terminal census")
    required_false = ("native_error_bound_verified", "native_filling_verified", "native_envelope_topology_verified",
                      "full_continuous_G2", "all_blockers_closed")
    for evidence in (producer, reader):
        need(evidence["scope"]["conditional_source_model_only"] is True, "conditional source-model scope")
        need(all(evidence["scope"][k] is False for k in required_false), "native obligations remain unqualified")
    need(reader["producer_or_geometric_helper_imported"] is False, "independent reader imports")
    frames = []
    for p, r in zip(producer["frames"], reader["frames"]):
        need((p["case_id"], p["frame"]) == (r["case_id"], r["frame"]), "frame identity and order")
        for key in ("root_count", "splits", "maximum_depth", "conditional_gate_passed"):
            need(p[key] == r[key], "frame metadata equality: " + key)
        for key in ("root_box_volume_exact", "intersection_upper_bound_exact"):
            need(F(p[key]) == F(r[key]), "independent exact volume equality: " + key)
        proof_path = ENV / "cylinder-slab-all16-attempt1" / Path(p["proof"]["path"]).name
        bind(proof_path, p["proof"])
        bind(proof_path, r["proof"])
        need(r["verified"] is True and F(r["intersection_upper_bound_exact"]) <= F(1e-7), "actual verified original gate")
        frames.append({k: r[k] for k in ("case_id", "frame", "root_count", "splits", "maximum_depth",
                                       "intersection_upper_bound_exact", "intersection_upper_bound_display_mm3",
                                       "conditional_gate_passed")})
    controls = reader["actual_mutation_controls"]
    need(len(controls) == 3 and all(x["passed"] and x["expected_rejection"] == x["actual_rejection"] for x in controls),
         "three actual certificate controls")
    history = []
    for name in ("balanced", "gradient"):
        pp, rp = ENV / (name + "-all16-attempt1/report.json"), ENV / ("independent-" + name + "-all16-attempt1/report.json")
        p, r = read(pp), read(rp)
        need(p["execution_completed"] and r["completed"], "completed historical attempts")
        bind(pp, r["producer_report"])
        need(p["conditional_pass_count"] == r["conditional_pass_count"] == 8, "historical nonpasses unchanged")
        history.append({"strategy": name, "producer_report": identity(pp), "reader_report": identity(rp),
                        "conditional_pass_count": 8, "conditional_nonpass_count": 8,
                        "global_splits": p["global_splits"], "producer_seconds": p["seconds"],
                        "reader_seconds": r["seconds"], "original_nonpasses_reclassified": False})

    inherited_path = ENV / "inherited-native-source-scopes/R9_INHERITED_FILE_BINDINGS.json"
    inherited = read(inherited_path)
    original_case_files = []
    for item in inherited["files"]:
        copied_path = ENV / item["relative_copy"]
        bind(copied_path, item)
        bind(item["path"], item)
        if "original-case-results" in item["relative_copy"]:
            original_case_files.append({"relative_copy": item["relative_copy"], **identity(copied_path)})
    matrix_path = ENV / "inherited-native-source-scopes/R3E_ORIGINAL_FAILURE_MATRIX.json"
    matrix = read(matrix_path)
    counts = Counter(x["original_error"] for x in matrix["cases"])
    need(len(original_case_files) == len({x["case_id"] for x in matrix["cases"]}) == 17, "all17 original result files")
    need(sum(counts.values()) == 25 and counts == matrix["original_error_counts"], "all25 original failure events")
    need(all(x["original_failure_preserved"] and x["whole_native_qualified"] is False for x in matrix["cases"]),
         "original native failures retained")
    prepared_path = HERE / "R9_SELECTED_CHANNEL_PREPARED_SOURCE_IDENTITIES.json"
    prepared = read(prepared_path)
    need(prepared["pilot_executed"] is False and prepared["full_run_executed"] is False and
         prepared["performance_measured"] is False and prepared["geometric_qualification"] is False,
         "optional selected strategy remains unexecuted")
    for name, expected in prepared["reviewed_sources"].items():
        bind(ENV / name, expected)
    io_path = HERE / "recovery-io-control-attempt1/report.json"
    io = read(io_path)
    need(io["control_completed"] and io["qualified_execution_after_failure"] is False and
         io["scope"]["production_v1_retroactively_qualified"] is False, "synthetic v2 IO control scope")
    result = {"schema": "razr-r9-independent-final-envelope-ledger-v1", "completed": True,
              "ledger_source": identity(__file__), "producer_report": identity(producer_path),
              "full_independent_reader_report": identity(reader_path), "recorded_budget_audit": identity(budget_path),
              "qualification_layers": {
                  "mathematical_source_model_review_completed": True,
                  "actual_v1_producer_completed": True,
                  "actual_full_certificate_reader_completed": True,
                  "all16_original_conditional_frame_gates_passed": True,
                  "native_error_bound_verified": False, "native_filling_verified": False,
                  "native_envelope_topology_verified": False, "full_continuous_G2": False,
                  "physical_allowed_domain_proved": False, "manufacturing_go": False},
              "actual_counts": {"original_roots": 1537, "global_splits": 718,
                                "maximum_depth": max(x["maximum_depth"] for x in frames),
                                "all_generated_nodes": 1537 + 2 * 718, "terminal_leaves": reader["totals"]["terminal_leaves"],
                                **{k: reader["totals"][k] for k in ("pieces", "channels", "tiny_nodes", "tested_nodes")}},
              "original_limits": producer["limits"], "exact_original_binary64_threshold": producer["original_TOL_exact"],
              "producer_recorded_seconds": producer["seconds"], "reader_recorded_seconds": reader["seconds"],
              "producer_peak_RSS_bytes": producer["peak_RSS_bytes"], "reader_peak_RSS_bytes": reader["peak_RSS_bytes"],
              "external_total_wallclock_measurement_claimed": False, "RSS_is_not_address_space": True,
              "frames": frames, "actual_reader_mutation_controls": controls,
              "previous_actual_attempts": history,
              "four_original_native_failure_classes": {
                  "binding": identity(inherited_path), "matrix": identity(matrix_path),
                  "original_case_count": 17, "original_failure_event_count": 25, "events_by_error": dict(counts),
                  "all_original_result_files": original_case_files, "all_original_and_copied_bytes_rechecked": True,
                  "r9_new_native_prism_common_extrusion_qualification": False,
                  "native_obligations_closed_by_the_conditional16_frame_result": False,
                  "complete_original_scientific_archive": inherited["complete_original_scientific_archive"]},
              "v1_v2_IO_separation": {"actual_full_producer": "cylinder_slab_all16_r9.py",
                                     "v1_actual_exception_observed": False,
                                     "v1_exception_path_gaps_not_retroactively_fixed": True,
                                     "v2_whole_driver_executed": False,
                                     "executed_small_helper_control": identity(io_path),
                                     "v2_control_retroactively_qualifies_v1": False},
              "selected_optimization": {"prepared_review": identity(prepared_path),
                                        "source_review_only": True, "pilot_executed": False,
                                        "full_run_executed": False, "performance_or_qualification_claimed": False},
              "old_review_snapshots_preserved": True,
              "new_geometry_or_solver_computation_by_this_ledger": False}
    with args.output.open("x") as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps({"completed": True, "producer": True, "reader": True, "conditional_passes": 16,
                      "native_envelope_qualified": False, "original_case_count": 17, "original_failures": 25}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
