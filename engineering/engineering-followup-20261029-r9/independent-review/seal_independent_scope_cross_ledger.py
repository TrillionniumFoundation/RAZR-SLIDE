"""Join independently completed numerical, envelope and finite geometry scopes.

The three evidence scopes remain distinct. Original numerical reconstruction,
conditional envelope arithmetic and finite native states do not imply current
structural FE, OEM electrical, continuous native or physical qualification.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R9 = HERE.parent


def identity(path):
    path = Path(path)
    with path.open("rb") as stream:
        return {"bytes": path.stat().st_size,
                "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}


def main(a):
    paths = {
        "numerical": R9 / "numerics/R9_NUMERICAL_SCOPE.json",
        "envelope": HERE / "R9_ENVELOPE_INDEPENDENT_FINAL_LEDGER.json",
        "geometry": HERE / "R9_GEOMETRY_TEN_STATE_INDEPENDENT_FINAL_LEDGER.json",
    }
    records = {k: json.loads(p.read_text()) for k, p in paths.items()}
    n, e, g = (records[k] for k in ("numerical", "envelope", "geometry"))
    if not (n["historical_N15_scope_retained"] and n["original_all_ten_full_fields_native_readback_passed"]
            and n["original_K_b_C_and_threshold_unchanged"] and e["completed"] and g["completed"]):
        raise ValueError("required independent result scopes are incomplete")
    if not (g["original_registered_states"] == g["full_native_producer_states_completed"]
            == g["full_native_reader_states_completed"] == g["current_record_audits_completed"] == 10):
        raise ValueError("all ten actual finite state producer/readers required")
    for key in ("mathematical_source_model_review_completed", "actual_v1_producer_completed",
                "actual_full_certificate_reader_completed", "all16_original_conditional_frame_gates_passed"):
        if e["qualification_layers"][key] is not True:
            raise ValueError("actual conditional envelope layer incomplete: " + key)
    for key in ("native_error_bound_verified", "native_filling_verified", "native_envelope_topology_verified"):
        if e["qualification_layers"][key] is not False:
            raise ValueError("inherited native obligation cannot be relabelled: " + key)
    if not (e["qualification_layers"]["full_continuous_G2"] is False and
            g["scope"]["full_continuous_G2"] is False and
            n["current_seed_full_bitwise_reproduction"] is False):
        raise ValueError("original limits and actual nonpass scope must remain unchanged")
    numerical_keys = (
        "controlling_original_source_commit", "historical_N15_scope_retained", "new_solver_executed",
        "new_native_K_products_executed", "runtime", "historical_dependency_versions_reproduced",
        "original_K_b_C_and_threshold_unchanged", "original_float64_threshold",
        "panel_original_five_residuals", "frame_original_five_residuals",
        "original_all_ten_full_fields_native_readback_passed", "four_original_load_scalar_residuals",
        "four_original_load_native_2D_block_residual", "H_columns_per_body",
        "all_7770_H_basis_RHS_and_saved_projections_SHA_recomputed", "independent_all_7770_K_products_executed",
        "all_7770_successful_full_fields_retained", "original_ExactResponseCache_restore", "restore_scope",
        "raw_H_and_seed_H_bitwise_reconstructed", "current_seed_full_bitwise_reproduction",
        "seed_discrepancy_exact_rational_reference_completed", "seed_discrepancy_changes_original_qualification",
        "retained_current_failures", "scope_exclusions",
    )
    result = {
        "schema": "razr-r9-independent-numerical-envelope-geometry-cross-ledger-v1",
        "completed": True, "sealed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "ledger_source": identity(__file__),
        "bound_scope_records": {k: {"path": str(p.relative_to(R9)), **identity(p)} for k, p in paths.items()},
        "original_numerical_system_and_saved_action_scope": {k: n[k] for k in numerical_keys},
        "continuous_envelope_conditional_source_model": {
            k: e[k] for k in ("qualification_layers", "actual_counts", "original_limits",
                              "exact_original_binary64_threshold", "producer_recorded_seconds", "reader_recorded_seconds",
                              "producer_peak_RSS_bytes", "reader_peak_RSS_bytes", "external_total_wallclock_measurement_claimed",
                              "RSS_is_not_address_space", "previous_actual_attempts", "four_original_native_failure_classes",
                              "v1_v2_IO_separation", "selected_optimization")},
        "finite_native_all_ten_original_states": {
            k: g[k] for k in ("original_registered_states", "full_native_producer_states_completed",
                              "full_native_reader_states_completed", "current_record_audits_completed",
                              "finite_state_pairs_per_role", "producer_plus_reader_pair_results",
                              "saved_whole_native_body_files_rehashed", "all_applicable_native_early_gates_passed",
                              "method_counts_per_role", "new_state_different_method_branch_count",
                              "new_state_different_method_branches", "original_F1a_positive_collisions_preserved",
                              "original_F1a_nonzero_STEP_readback_differences_preserved",
                              "v1_stopped_original_campaign_incomplete_retained", "capacity_is_start_time_snapshot", "scope")},
        "qualification_boundaries": {
            "original_numerical_pass_reassigned_to_modified_current_structure_FE": False,
            "all_7770_arbitrary_saved_full_field_actions_claimed": False,
            "conditional_arithmetic_gate_count_is_full_native_continuous_G2": False,
            "ten_finite_states_are_full_continuous_domain_proof": False,
            "native_error_filling_topology_obligations_closed": False,
            "actual_specimen_or_OEM_identity_obtained_by_this_review": False,
            "new_FE_material_tolerance_electrical_or_G3_G4_G5_qualification": False,
            "physical_qualification": False, "manufacturing_go": False},
        "new_solver_CAD_or_physical_experiment_executed_by_this_ledger": False,
    }
    with a.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps({"completed": True, "numerical_original_ten_probes": True,
                      "conditional_envelope_frames": 16, "native_finite_states": 10,
                      "full_continuous_G2": False, "physical_qualification": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
