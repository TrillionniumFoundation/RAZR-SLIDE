#!/usr/bin/env python3
"""Bind completed R12 component receipts without relabelling their scope.

The containing Git commit/tree is recorded after commit in the external
delivery manifest. This ledger deliberately does not attempt to self-hash.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def read(name):
    return json.loads((HERE / name).read_text())


def identity(name):
    path = HERE / name
    raw = path.read_bytes()
    return {"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    base = read("BASELINE.json")
    numeric = read("numerics/evidence/NUMERICAL_SCOPE.json")
    old_fill = read("envelope/R12_ENVELOPE_SCOPE.json")
    panel = read("panel-filling/R12_PANEL_FILL_SCOPE.json")
    inputs = read("real-inputs/CURRENT_INPUT_READBACK.json")
    qualification = read("qualification/SOURCE_AND_TEST_READBACK_DONOR_FOLLOWON.json")
    remote = read("publication/READONLY_REMOTE_SNAPSHOT.json")
    for row in qualification["source_identities"]:
        raw = (ROOT / row["path"]).read_bytes()
        assert len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
    assert all(x < 1e-7 for x in numeric["original_panel_five_residuals"])
    assert all(x < 1e-7 for x in numeric["original_frame_five_residuals"])
    assert qualification["tests_total"] == sum(x["tests"] for x in qualification["final_disjoint_test_executions"]) == 133
    assert panel["native_material_set_identity_proved"] is False
    assert all(x["original_1e_minus7_gate_passes_under_stated_model"] is False for x in panel["pairs"])
    assert inputs["new_actual_specimen_originals"] == 0
    assert not any(inputs[k] for k in ("G3_pass", "G4_pass", "G5_pass", "manufacturing_go"))
    assert remote["requested_R12_branch_returned"] is False

    reports = [
        "BASELINE.json", "geometry/R12_CURRENT_GEOMETRY_SCOPE.json",
        "geometry/INPUT_MANIFEST.json", "geometry/DELIVERY_MANIFEST.json",
        "geometry/REAL_FAILURE_NATIVE_READBACK.json",
        "envelope/R12_ENVELOPE_SCOPE.json", "envelope/R12_ENVELOPE_DELIVERY_MANIFEST.json",
        "panel-filling/R12_PANEL_FILL_SCOPE.json", "panel-filling/R12_PANEL_FILL_DELIVERY_MANIFEST.json",
        "independent-review/current-geometry/DELIVERY_MANIFEST.json",
        "independent-review/current-geometry/FIBRE_COMPLETE_GRID_INDEPENDENT_REVIEW.json",
        "independent-review/current-geometry/EXTERIOR_LEDGER_INDEPENDENT_REVIEW.json",
        "independent-review/current-geometry/PCURVE_AND_TRIM_INDEPENDENT_REVIEW.json",
        "numerics/MANIFEST.json", "numerics/evidence/NUMERICAL_SCOPE.json",
        "numerics/evidence/ORIGINAL_ARCHIVE_RECOVERY_IDENTITIES.json",
        "numerics/evidence/PORTABLE_MAP_INDEPENDENT_READBACK.json",
        "real-inputs/CURRENT_INPUT_READBACK.json", "real-inputs/R12_SAME_SPECIMEN_SEARCH.json",
        "real-inputs/OEM_DOWNLOAD_ATTEMPTS.json", "real-inputs/KNOWN_DEVICE_ENDPOINT_CHECK.json",
        "qualification/SOURCE_AND_TEST_READBACK.json",
        "qualification/SOURCE_AND_TEST_READBACK_DONOR_FOLLOWON.json",
        "independent-review/qualification/INDEPENDENT_REVIEW.json",
        "independent-review/qualification-donor-followon/FOLLOWON_REVIEW.json",
        "independent-review/root-consistency/INDEPENDENT_CONSISTENCY_REVIEW.json",
        "independent-review/ROOT_COMPONENT_IMPORT_READBACK.json",
        "publication/PUBLIC_PUSH_REJECTION.json", "publication/READONLY_REMOTE_SNAPSHOT.json",
        "build_root_ledger.py",
    ]
    ledger = {
        "schema": "razr-r12-completed-seven-workstream-ledger-v1",
        "sealed_utc": datetime.now(timezone.utc).isoformat(),
        "baseline": base,
        "containing_commit_identity": "Bound by final external PUBLICATION_MANIFEST.json after Git commit; not self-referential.",
        "historical_S4_full_unit_run": {"suites": 36, "tests": 1654, "new_R12_execution": False},
        "current_qualification_contract_source_changed": True,
        "new_full_tree_unit_run": False,
        "bound_records": [identity(name) for name in reports],
        "workstreams": [
            {
                "id": "1_midtravel_whole_factory_witnesses",
                "status": "historical_R9_finite_acceptance_retained_and_source_checked",
                "new_R12_full_factory_execution": False,
                "source": "../engineering-followup-20261029-r9/geometry/R9_GEOMETRY_SCOPE.json",
                "slide_mm": [23.142044210239405, 60.880681403413135],
                "original_participants_per_midtravel_pose": 154,
                "all_pairs_per_midtravel_pose_per_role": 11781,
                "original_positive_panel_KEY_Common_mm3": {
                    "near_L": 0.24558784938224815, "near_R": 0.2455878493822482,
                    "far_L": 0.23013738353925134, "far_R": 0.23013738353925126,
                },
                "original_failure_reclassified_as_pass": False,
                "named_candidate_ten_finite_states_clear_under_original_criteria": True,
                "ten_state_pair_records_per_role": 118909,
                "pair_count_equals_Common_calls": False,
                "independent_reader_uses_different_native_kernel": False,
                "original_F1a_raw_runtime_recovery_claimed": False,
                "remaining": "Finite original-criterion agreement is not a complete continuous-domain or native error proof.",
            },
            {
                "id": "2_named_structure_and_allowed_domain",
                "status": "named_material_and_software_domain_evidence_retained_physical_domain_open",
                "K1_name": "key_forward_loop_v1", "K3_name": "panel_key_travel_stops_v1",
                "physical_geometry_modified_in_R12": False,
                "K1_each_KEY_removed_mm3_approx": 0.594,
                "K1_each_KEY_added_mm3_approx": 2.623824,
                "K3_panel_removed_mm3": 0, "K3_panel_added_mm3_approx": 4.62456,
                "local_declared_sections_mm2_not_global_minimum": [0.54, 0.1368, 0.075],
                "positive_q_segments": ["q=0 and (0,a]: plateau", "(a,b): rounded_corner", "[b,c): ramp", "[c,12]: cam lower_stop"],
                "breakpoints": {"a": 0.0011145618000001356, "b": 0.09055728089999172,
                                "c_contact0": 0.6429179606749895, "c_contact1": 0.64291796067499},
                "q_relation": "q_s=(12/79.75)*shared_slide+dq_s; original side slots/telescope/descent/OPEN constraints remain",
                "KEY_pair_nominal_domain": {"q_L": [0, 12], "q_R": [0, 12]},
                "KEY_pair_X_support_gap_mm_approx_under_stated_model": 12.4,
                "nominal_KEY_square_is_actual_whole_mechanical_domain": False,
                "global_minimum_wall_or_weakest_section_qualified": False,
                "physical_contact_and_spring_force_domain_proved": False,
                "current_geometry_FE_qualified": False,
            },
            {
                "id": "3_conservative_continuous_envelope",
                "status": "local_conditional_filling_verified_current_whole_material_bound_inconclusive",
                "original_L1_cases": list(range(11, 20)),
                "original_L1_totals": old_fill["totals"],
                "original_L1_negative_controls_rejected": old_fill["negative_controls_rejected"],
                "original_L1_compact_filling_implication_verified_under_stated_model": True,
                "original_cases_016_to_019_initial_q_sweep_proved": False,
                "new_current_KEY_faces_per_side": 92,
                "new_current_KEY_directed_edge_occurrences_per_side": 528,
                "whole_q_regions_per_KEY": 94,
                "native_zero_Common_regions_per_KEY": 47,
                "exact_tiny_carrier_regions_per_KEY": 47,
                "native_zero_Common_is_rigorous_upper_bound": False,
                "real_tiny_operand_Common_failure": {
                    "prism_signed_volume_mm3": 9.233858122569423e-16,
                    "panel_signed_volume_mm3": 4526.78137306303,
                    "saved_Common_signed_volume_mm3": 4526.781373063011,
                    "original_allowed_operand_upper_mm3": 1.000000009233858e-7,
                    "topology_valid_but_volume_bound_failed": True,
                },
                "current_panel_filling_scope": panel,
                "independent_positive_width_grid_cells": 15463403,
                "all_positive_RLE_boxes": 169,
                "remaining_full_positive_RLE_boxes": 165,
                "independent_ledger_negative_controls": 5,
                "independent_overexpanded_channel_negative_controls": 6,
                "native_arm_material_positive_controls": 4,
                "native_material_set_identity_proved": False,
                "uniform_compiled_geometry_error_proved": False,
                "full_continuous_G2": False,
                "actual_panel_KEY_collision_proved_by_positive_upper": False,
            },
            {
                "id": "parallel_original_numerical_qualification",
                "status": "original_ten_float64_probes_and_saved_H_restore_scope_passed",
                "original_K_b_C_and_fields_unchanged": True,
                "new_solver_executed": False,
                "threshold": 1e-7,
                "panel_five": numeric["original_panel_five_residuals"],
                "frame_five": numeric["original_frame_five_residuals"],
                "all_ten_pass": True,
                "correction_process": numeric["panel_correction_process"],
                "original_H_columns": numeric["H_columns"],
                "basis_RHS_and_saved_projection_hashes_checked": 7770,
                "all_7770_K_products_executed": False,
                "all_7770_successful_full_fields_available": False,
                "restore": numeric["original_ExactResponseCache_restore"],
                "restore_threshold": 2e-7,
                "worker_seconds": numeric["worker_seconds"],
                "actual_worker_peak_RSS_KiB": numeric["actual_worker_peak_RSS_KiB"],
                "new_auxiliary_exact_dyadic_loadG": {"original_terms": 4221, "dots": 24,
                    "independent_rounding_cell_checks": 24, "differential_cases": 171,
                    "order_permutations": 120, "actual_tamper_rejections": 4},
                "legacy_whole_seed_bitwise_replay_passed": False,
                "arbitrary_RHS_inverse_or_full_QP_resume_qualified": False,
                "full_original_fields_preservation": "Seven original archives remain separately retained and SHA-bound by ORIGINAL_ARCHIVE_RECOVERY_IDENTITIES.json; not duplicated in this incremental delivery.",
            },
            {
                "id": "parallel_same_specimen_and_OEM_originals",
                "status": "external_originals_missing_bounded_search_and_access_attempts_recorded",
                "new_actual_specimen_originals": 0,
                "same_specimen_identity_fields": 10, "part_roles": 7, "interfaces": 12,
                "bounded_uploaded_search_no_results": True,
                "global_absence_of_user_originals_proved": False,
                "known_endpoint_result": "PermissionError in current environment; no adb executable; no actual device commands",
                "device_offline_inferred": False,
                "OEM_PDF_requests": 3, "complete_OEM_PDF_bytes_acquired": False,
                "actual_OEM_responses": "HTML; only request metadata and response digests retained; response bodies not archived",
                "same_specimen_or_selected_revision_bindings_added": 0,
            },
            {
                "id": "subsequent_current_structure_electrical_test_contract",
                "status": "current_input_contract_audited_software_admission_repaired_physical_freeze_open",
                "material_roles": inputs["material_roles"], "unassigned_material_slots": inputs["unassigned_material_slots"],
                "original_loadcases": inputs["original_loadcases"], "unassigned_load_slots": inputs["unassigned_load_slots"],
                "additional_stop_loadcases": inputs["additional_stop_loadcases"],
                "unassigned_stop_load_slots": inputs["unassigned_stop_load_slots"],
                "gate_records": inputs["gate_records"], "unassigned_gate_limit_slots": inputs["unassigned_gate_limit_slots"],
                "counts_exhaust_all_possible_physical_requirements": False,
                "complete_current_physical_contract_frozen": False,
                "new_native_electrical_execution": False,
                "qualification_software_changes": ["failure/missing/maintenance/replacement retention", "same raw as-built, original donor and five assembly roles", "complete shared design binding", "acquisition and pass-review order G3 then G4 then G5", "contradictory prerequisite rejection", "legitimate complete G4 empty-exception admission"],
                "final_targeted_software_tests_passed": qualification["tests_total"],
                "prior_independent_admission_controls": 7, "additional_independent_donor_configurations": 12,
                "new_full_tree_unit_run": False, "software_controls_are_physical_evidence": False,
                "final_qualification_sources": qualification["source_identities"],
            },
            {
                "id": "last_sequential_physical_acceptance",
                "status": "not_executed_missing_same_candidate_specimen_inputs_and_frozen_sourced_contract",
                "actual_physical_runs": 0,
                "G3_pass": False, "G4_pass": False, "G5_pass": False,
                "physical_stage_advanced_by_software_tests": False,
                "required_sequence": "same candidate and same assembly: G3 actual pass/review -> G4 -> G5; preserve missing/fail/repair/replacement separately",
            },
        ],
        "retained_failures": [
            "Original midpoint panel/KEY positive Common, earlier N7 residual and other historical failures remain at their original identities.",
            "Current prism negative signed volume, tiny nonzero axis, impossible positive Common and zero signed volume remain in geometry/producer-v1..v4.",
            "Three actual panel extraction timeouts are retained without inventing a root cause.",
            "Current whole-material conservative upper still fails the original threshold; this is not a measured collision.",
            "Original seed bitwise mismatch, failed frame8:520 and numeric recovery/resource-label corrections remain.",
            "Qualification regressions before each fix, the G4 false rejection and original donor binding gap remain in immutable prior reports.",
            "First public push was rejected by automatic approval review before execution; no alternate route was used.",
        ],
        "publication": {
            "public_R9_restoration_verified": True, "public_R9_commit": base["parent_commit"],
            "R12_branch": base["working_branch"], "R12_public_push_completed": False,
            "automatic_approval_rejection": "publication/PUBLIC_PUSH_REJECTION.json",
            "read_only_remote_confirmation": "publication/READONLY_REMOTE_SNAPSHOT.json",
            "requires_explicit_new_payload_public_authorization": True,
        },
        "release": {"full_continuous_G2": False, "physical_allowed_domain_proved": False,
                    "current_geometry_FE_qualified": False, "OEM_electrical_stack_qualified": False,
                    "G3_pass": False, "G4_pass": False, "G5_pass": False,
                    "candidate_go": False, "fixture_fabrication_go": False,
                    "manufacturing_go": False, "all_blockers_closed": False},
    }
    target = HERE / "R12_COMPLETED_WORK_LEDGER.json"
    target.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(target), "workstreams": len(ledger["workstreams"]),
                      "bound_records": len(ledger["bound_records"]), "all_release_flags_false": not any(ledger["release"].values())}))


if __name__ == "__main__":
    main()
