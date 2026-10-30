#!/usr/bin/env python3
"""Bind R13 results while retaining their conditional and historical scope."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
REL = HERE.relative_to(ROOT).as_posix()
R12 = HERE.parent / "engineering-followup-20261030-r12"


def read(path):
    return json.loads(path.read_text())


def identity(path):
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    geo = read(HERE / "geometry/R13_GEOMETRY_SCOPE.json")
    env = read(HERE / "envelope/R13_ENVELOPE_SCOPE.json")
    inputs = read(HERE / "real-inputs/CURRENT_INPUT_DELTA.json")
    imported = read(HERE / "independent-review/COMPONENT_IMPORT_READBACK.json")
    pub = read(HERE / "publication/R12/R12_PUBLICATION_READBACK.json")
    old = read(R12 / "R12_COMPLETED_WORK_LEDGER.json")
    numeric = read(R12 / "numerics/evidence/NUMERICAL_SCOPE.json")
    qual = read(R12 / "qualification/SOURCE_AND_TEST_READBACK_DONOR_FOLLOWON.json")
    assert imported["file_count"] == 313
    for component in imported["components"].values():
        for row in component["files"]:
            actual = identity(ROOT / row["repository_path"])
            assert all(actual[k] == row[k] for k in ("bytes", "sha256")), row
    for row in qual["source_identities"]:
        actual = identity(ROOT / row["path"])
        assert all(actual[k] == row[k] for k in ("bytes", "sha256")), row
    assert len(numeric["original_panel_five_residuals"]) == 5
    assert len(numeric["original_frame_five_residuals"]) == 5
    assert all(x < 1e-7 for x in numeric["original_panel_five_residuals"] + numeric["original_frame_five_residuals"])
    assert env["all_original_positive_boxes_accounted"] == 169
    assert env["retained_full_positive_boxes"] == 157
    assert all(p["original_threshold_passes_only_under_B0_and_T"] for p in env["pairs"])
    assert not env["actual_native_B0_membership_proved"] and not env["actual_native_T_membership_proved"]
    assert not env["existence_of_full_global_actual_native_material_realizing_B0_and_T_proved"]
    assert not env["old_B0_only_bound_replaced"]
    assert geo["full_source_motion_real_model"]["feasible_pairs"] == 17
    assert geo["full_source_motion_real_model"]["infeasible_pairs"] == 8
    assert inputs["new_same_specimen_originals"] == inputs["new_physical_measurements"] == 0
    assert pub["source_trees_identical"] and pub["all_content_diff_empty"]
    reports = [
        "geometry/R13_GEOMETRY_SCOPE.json", "geometry/INPUT_MANIFEST.json",
        "geometry/DELIVERY_MANIFEST.json", "geometry/ARCHIVE_READBACK.json",
        "geometry/MODIFIED_SECTIONS_INDEPENDENT_REVIEW.json",
        "geometry/SOURCE_MOTION_INDEPENDENT_REVIEW.json",
        "geometry/COMPLETE_SOURCE_MOTION_DOMAIN.json",
        "geometry/CURRENT_NOMINAL_LOAD_PATH_AND_SECTION_INPUTS.json",
        "geometry/PLAN_AND_RESOURCE_BASIS.json", "geometry/STOP_SPRING_READBACK_PLAN.json",
        "geometry/native-brep-attempt1/report.json", "geometry/native-step-attempt1/report.json",
        "geometry/stop-spring-readback-attempt1/report.json",
        "envelope/R13_ENVELOPE_SCOPE.json", "envelope/R13_ENVELOPE_DELIVERY_MANIFEST.json",
        "envelope/COMPLETION_MODEL_DEFINITION.md", "envelope/MODEL_MEMBERSHIP_FRONTIER.md",
        "envelope/ALGORITHM_AND_CAPACITY.md", "envelope/independent-review/R13_TRIM_INDEPENDENT_REVIEW.json",
        "real-inputs/CURRENT_INPUT_DELTA.json", "real-inputs/MANIFEST.json",
        "real-inputs/INDEPENDENT_READBACK.json", "real-inputs/OEM_SOURCE_APPLICABILITY.json",
        "publication/R12/R12_PUBLICATION_READBACK.json", "publication/R12/R12_PUBLICATION_PLAN.json",
        "independent-review/COMPONENT_IMPORT_READBACK.json", "import_components_r13.py", "build_r13_ledger.py",
    ]
    retained_witness = copy.deepcopy(old["workstreams"][0])
    retained_witness["new_R13_full_factory_execution"] = False
    retained_witness["scope_of_R13_action"] = "Retain immutable R9/R12 original finite witnesses; do not count as a new execution."
    retained_numeric = copy.deepcopy(old["workstreams"][3])
    retained_numeric["new_R13_numerical_product_or_solver_execution"] = False
    retained_numeric["scope_of_R13_action"] = "Retain R12 completed original products, saved full fields/correction identities, H and restore; no qualification scope expansion."
    ledger = {
        "schema": "razr-r13-completed-seven-workstream-ledger-v1",
        "sealed_utc": datetime.now(timezone.utc).isoformat(),
        "base_public_commit": "ab9ef3270a9a0d0d28f605f7188038db133dbcd8",
        "base_public_tree": "922ab085590d0f8a59d1dd8675bad9bc8f3b27c5",
        "branch": "evidence/full-sprint-20261030-r13",
        "containing_commit_identity": "Publication readback is recorded after the science commit; this ledger does not self-hash.",
        "R12_scientific_source_and_failures_unchanged": True,
        "historical_S4_full_unit_run": {"commit": "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560", "suites": 36, "tests": 1654, "new_R13_execution": False},
        "inherited_R12_qualification_validation": {"targeted_tests": 133, "source_identities": qual["source_identities"],
            "independent_admission_controls": 7, "independent_donor_configurations": 12,
            "new_R13_contract_source_change": False, "new_R13_test_execution": False,
            "full_tree_qualification_at_current_source": False, "physical_pass": False},
        "bound_records": [identity(HERE / name) for name in reports] + [
            identity(R12 / "R12_COMPLETED_WORK_LEDGER.json"),
            identity(R12 / "numerics/evidence/NUMERICAL_SCOPE.json"),
            identity(R12 / "qualification/SOURCE_AND_TEST_READBACK_DONOR_FOLLOWON.json")],
        "workstreams": [
            retained_witness,
            {"id": "2_named_structure_and_allowed_domain", "status": "new_complete_declared_modification_windows_and_source_q_subsystem_projection",
             "candidate_geometry_changed_in_R13": False,
             "named_sources": {"K1": "key_forward_loop_v1", "K3": "panel_key_travel_stops_v1"},
             "actual_native_readback": geo["new_native_executions"],
             "complete_region_models": geo["complete_source_region_models"],
             "local_declared_decimal_geometry": {"U_leg_and_crossbar_area_mm2": 0.1368,
                 "U_window_min_positive_X_Y_Z_directional_chords_mm": [0.38, 0.38, 0.36],
                 "lower_stop_plate_embed_depth_mm": 0.15, "lower_stop_joint_volume_mm3": 0.081,
                 "upper_toe_post_overlap_Y_mm": 0.2, "upper_toe_joint_volume_mm3": 0.0648,
                 "each_nominal_stop_contact_area_mm2": 0.324,
                 "whole_part_global_minimum_thickness_or_strength_proved": False},
             "source_q_subsystem": {"interpretation": "Frozen binary64 coefficients/thresholds treated as exact real numbers for the stated shared-slide and side-deviation subsystem.",
                 "projection": "0 <= qL,qR <= 12 and abs(qL-qR) <= 2*(A+B)",
                 "W_approx_mm": 0.06063697106654654,
                 "complete_profile_branches": 16, "merged_branch_pairs": 25,
                 "feasible_branch_pairs": 17, "infeasible_branch_pairs": 8,
                 "two_contact_endpoint_separation_mm": 4.440892098500626e-16,
                 "full_float64_acceptance_equivalence_proved": False,
                 "all_15D_mechanical_constraints_projected_and_qualified": False,
                 "physical_allowable_domain_proved": False},
             "remaining": geo["open_qualification"]},
            {"id": "3_conservative_continuous_envelope", "status": "new_explicit_B0_AND_T_conditional_tight_bound_original_B0_and_native_blockers_retained",
             "original_L1_cases_011_to_019_and_real_native_failures": "Inherited immutable R12 receipts; no new relabelling or deletion.",
             "premises": env["premises"], "pairs": env["pairs"],
             "complete_panel_faces_accounted_per_channel": 298,
             "native_target_faces": 6, "complete_wires": 12, "complete_edges": 48,
             "joins": 48, "vertex_endpoints": 96, "nonzero_endpoint_gaps_preserved": 44,
             "all_original_positive_boxes": 169, "inherited_KEY_exclusions": 4,
             "new_panel_exclusions_under_T": 8, "full_positive_contributions_retained": 157,
             "minimum_query_corridor_gap_exact_mm": env["minimum_query_to_complete_corridor_gap_exact_mm"],
             "independent_negative_control_variants_rejected": 8,
             "new_splits": 0, "new_depth": 0, "original_split_limit": 4096, "original_depth_limit": 24,
             "original_threshold_exact": env["original_float64_threshold_exact"],
             "old_B0_only_bound_replaced": False, "native_B0_and_T_membership_proved": False,
             "complete_global_native_realization_existence_proved": False, "uniform_compiled_error_proved": False,
             "native_tolerance_is_certified_evaluator_error": False, "full_continuous_G2": False,
             "positive_upper_is_measured_collision": False},
            retained_numeric,
            {"id": "parallel_same_specimen_and_OEM_originals", "status": "new_manufacturer_distribution_and_revision_leads_without_new_qualified_bindings",
             "new_indexed_EU_or_family_documents": 3, "complete_new_OEM_PDFs_acquired": 0,
             "new_same_specimen_originals": 0, "new_physical_measurements": 0,
             "new_selected_PN_revision_bindings": 0, "same_specimen_identity_fields": 10,
             "part_roles": 7, "actual_interfaces": 12, "original_required_facts": 228,
             "access_result": "EU BOM HTTP 405 / 2531-byte human-verification HTML, not PDF; iFixit complete-document sign-in wall retained.",
             "distinct_service_PNs_proved_equivalent_or_XT2551_3_compatible": False,
             "private_third_party_complete_response_bodies_published": False,
             "sources_and_applicability": "real-inputs/OEM_SOURCE_APPLICABILITY.json"},
            {"id": "subsequent_current_structure_electrical_test_contract", "status": "nominal_geometric_inputs_extended_physical_freeze_open",
             "new_complete_local_sections_centroids_inertia_and_feature_connections": True,
             "current_geometry_FE_or_tolerance_qualified": False,
             "inherited_material_roles": 161, "inherited_unassigned_material_slots": 1449,
             "inherited_original_loadcases": 13, "inherited_unassigned_load_slots": 78,
             "inherited_stop_loadcases": 5, "inherited_unassigned_stop_load_slots": 25,
             "inherited_declared_gate_records": 54, "inherited_unassigned_gate_limits": 67,
             "counts_are_exhaustive_physical_universe": False,
             "new_native_electrical_execution": False, "OEM_stack_interconnect_qualified": False,
             "complete_sourced_current_physical_contract_frozen": False},
            {"id": "last_sequential_physical_acceptance", "status": "not_executed_missing_same_specimen_inputs_and_sourced_current_contract",
             "actual_physical_runs": 0, "G3_pass": False, "G4_pass": False, "G5_pass": False,
             "required_order": "same candidate + same assembly: actual G3 pass/review, then G4, then G5",
             "missing_failure_repair_replacement_preserved_separately": True,
             "software_tests_or_publication_are_physical_acceptance": False},
        ],
        "publication_at_science_seal": {"R12_publication_verified": True,
            "R12_remote_commit": pub["remote_branch_head"], "R12_exact_tree_equivalence": True,
            "local_original_commit_metadata_identical_to_API_commits": False,
            "original_local_commit_raw_bytes_preserved": True,
            "explicit_current_user_publication_authorization": True,
            "R13_publication_not_yet_claimed_by_this_science_record": True,
            "current_publication_pointer": "design/current_product.json:publication_record",
            "prior_automatic_rejection_retained_as_historical_record": True},
        "release": {"full_continuous_G2": False, "physical_allowed_domain_proved": False,
            "whole_part_minimum_wall_qualified": False, "current_geometry_FE_qualified": False,
            "OEM_electrical_stack_qualified": False, "G3_pass": False, "G4_pass": False, "G5_pass": False,
            "candidate_go": False, "fixture_fabrication_go": False, "manufacturing_go": False,
            "all_blockers_closed": False},
    }
    target = HERE / "R13_COMPLETED_WORK_LEDGER.json"
    target.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"workstreams": len(ledger["workstreams"]), "bound_records": len(ledger["bound_records"]),
                      "all_release_flags_false": not any(ledger["release"].values()), **identity(target)}))


if __name__ == "__main__":
    main()
