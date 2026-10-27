"""Rebuild a finite K3 acceptance from recovered original scientific records.

This source is new after a local runtime reset. It does not claim recovery of
unpublished prior metadata bytes, rerun native geometry, or prove a continuous
or physical domain.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

RUN = 40285103942
HEAD = "566197a97ee137ce4a58097656eb4fd6bc084b05"
S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"
PLAN_SHA = "db77b90559f44ef6cc3466b596b817d8bc46f860ff044dce3a015d852424eedd"
INSPECTOR_SHA = "478078e700720f724b9ea3f73bd5c81cb4ddbab3483c15d3db51c9ffd2267a42"
LIMITS = {"wall_seconds": 1200, "worker_peak_RSS_MiB": 1536,
          "shared_unreclaimable_GiB": 6.8, "runtime_disk_reserve_MiB": 100,
          "startup_disk_reserve_MiB": 256, "startup_additional_memory_MiB": 2048}
OLD_INSPECTION_SHA = {
    "stow_tabs_3": "9ab136d5e02bc11ad9db4d85fdef97696db50e460f223de692af05e59f599492",
    "stow_tabs_0": "411831848b9cd03ecefaa077315b04b936534b3f97d05e791f877fa9e419e391",
    "near": "2e6f40e8b4363328cf8627d6047530ef42d29484c82224185fd100b2aec829bc",
    "far": "1a7c2eca080e5a1e305f91004d2f455db7dd91863d877b174d1119a1eb9ac51c",
    "predock": "dad7645609c26503b8d30890b1f8d4e5f451d3c43801d18eb801603a5686e96f",
    "open_installed": "683f0efbd01152e3d6b35466b45a88e123471fb94513934d6c8702fa96697c03",
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    plan_bytes = (root / "published/K3FULL_EXECUTION_PLAN.json").read_bytes()
    require(sha(plan_bytes) == PLAN_SHA, "published execution plan differs")
    require(sha((root / "published/inspect_k3full_artifact.py").read_bytes()) == INSPECTOR_SHA,
            "published unchanged inspector differs")
    plan = json.loads(plan_bytes)
    require(plan["functional_source_commit"] == S4 and len(plan["states"]) == 10, "source or state inventory differs")
    directory = root / "K3FULL-inspection"
    require({p.name for p in directory.glob("*_INSPECTION.json")} ==
            {"K3FULL_" + pose + "_INSPECTION.json" for pose in plan["states"]}, "finite state inspection inventory differs")
    rows, artifacts, methods = [], [], Counter()
    pairs = journal = gates = 0
    for pose, state in plan["states"].items():
        file = directory / ("K3FULL_" + pose + "_INSPECTION.json")
        raw = file.read_bytes()
        j = json.loads(raw)
        require(j["schema"] == "razr-K3FULL-memory-artifact-scientific-inspection-v1", "inspection schema differs")
        require(j["pose"] == pose and j["run_id"] == RUN and j["head_sha"] == HEAD and
                j["declared_pose"] == state, "finite source or input identity differs")
        for name in ("official_ZIP_SHA_size_all_CRC_and_member_SHA_verified",
                     "sixteen_frozen_runtime_source_bytes_verified", "complete_finite_pair_execution",
                     "actual_finite_state_clear", "gate_classification_consistency_known",
                     "original_observation_consistent_with_independent_inspection"):
            require(j[name] is True, "inspection did not pass: " + name)
        require(j["evaluated_geometric_gate_rejections"] == {} and j["native_gate_evaluation_unresolved"] == {},
                "geometric gate rejection or unresolved evaluation exists")
        require(j["missing_independent_early_gate_inventory"] is False and
                j["producer_reader_gate_classification_disagreement"] is False and
                j["independently_recomputed_pair_mismatches"] == [], "independent gate or pair mismatch exists")
        disagreement = j["original_clearance_claim_disagreements"]
        require(set(disagreement) == {"factory", "readback"} and
                all(v is False for v in disagreement.values()), "original clearance claim differs")
        require(j["positive_rejected_pairs"] == {"factory": [], "readback": []}, "positive rejected pair exists")
        require(j["candidate_source_sha256"] == plan["candidate_source_sha256"] and
                j["candidate_contract_sha256"] == plan["candidate_contract_sha256"], "candidate identity differs")
        expected_bodies = state["expected_bodies"]
        expected_pairs = expected_bodies * (expected_bodies - 1) // 2
        require(j["expected_pair_count_per_worker"] == expected_pairs, "finite pair count differs")
        require(j["expected_contact_ends"] == plan["expected_contact_end_by_side"][pose], "contact-end identity differs")
        expected_gates = 12 + 3 * sum(x is not None for x in j["expected_contact_ends"].values())
        early = j["independent_early_gate_records"]
        require(len(early) == j["expected_independent_gate_count"] == expected_gates, "independent gate inventory differs")
        require(all(v["evaluated"] is True and v["passed"] is True for v in early.values()),
                "independent gate was unevaluated or rejected")
        gates += len(early)
        resources = {}
        for mode in ("factory", "readback"):
            r, c = j["results"][mode], j["controllers"][mode]
            for name in ("source_and_43_package_environment_audited", "owned_original_resource_guards_completed",
                         "whole_material_exports_or_readbacks_complete", "scientific_complete",
                         "all_unordered_pairs_present_once", "complete_original_pair_journal_verified"):
                require(r[name] is True, "worker completion contract differs: " + name)
            require(r["body_count"] == expected_bodies and r["pair_count"] == expected_pairs and
                    r["journal_rows"] == 2 * expected_pairs, "worker matrix or journal incomplete")
            require(r["positive_pairs"] == r["pair_evaluation_failures"] == r["pair_readback_mismatches"] == [],
                    "worker records a rejection, evaluation error or mismatch")
            require(c["completed"] is True and c["worker_exit_code"] == 0 and
                    c["source_bytes_unchanged"] is True and c["locked_environment_unchanged"] is True and
                    c["limits"] == LIMITS, "worker original source, environment or guard contract differs")
            require(sum(r["method_counts"].values()) == expected_pairs, "worker method count differs")
            require(set(r["method_counts"]) <= {"native_common", "positive_axis_gap"}, "unexpected method")
            pairs += r["pair_count"]
            journal += r["journal_rows"]
            methods.update(r["method_counts"])
            resources[mode] = {
                "seconds": r["seconds"],
                "max_sampled_worker_VmHWM_bytes": max(
                    (v.get("worker_memory", {}).get("VmHWM", 0) for v in c["resource_observations"]), default=0)}
        require(j["results"]["factory"]["actual_q_by_side_mm"] == j["results"]["readback"]["actual_q_by_side_mm"],
                "actual producer and reader q differ")
        account = j["original_complete_panel_material_account"]
        require(account["removed_mm3"] == 0 and abs(account["added_mm3"] - 4.62456) < 1e-7 and
                abs(account["signed_balance_error_mm3"]) <= 1e-7, "whole panel material account differs")
        manifest = directory / ("K3FULL_" + pose + "_ENGINEERING_MANIFEST.json")
        require(sha(manifest.read_bytes()) == j["engineering_manifest_sha256"], "exact manifest bytes differ")
        require(j["exact_ZIP_regular_file_count"] == j["exact_engineering_manifest_entries"] + 1,
                "scientific member inventory differs")
        if pose in OLD_INSPECTION_SHA:
            require(sha(raw) == OLD_INSPECTION_SHA[pose], "deterministic inspection differs from known earlier digest")
        binding = {
            "label": "K3FULL-" + pose, "run_id": RUN, "head_sha": HEAD,
            "artifact_id": j["artifact_id"], "artifact_name": j["artifact_name"],
            "zip_bytes": j["official_ZIP_bytes"], "zip_sha256": j["official_ZIP_sha256"],
            "manifest_name": "ENGINEERING_MANIFEST.json", "manifest_sha256": j["engineering_manifest_sha256"],
            "manifest_layout": "K3FULL_members", "manifest_entries": j["exact_engineering_manifest_entries"],
            "asset_name": "K3FULL-" + pose + "-scientific-40285103942.zip"}
        artifacts.append(binding)
        rows.append({
            "pose": pose, "inspection_file": file.name, "inspection_sha256": sha(raw), "inspection_bytes": len(raw),
            "declared_pose": state, "expected_contact_ends": j["expected_contact_ends"],
            "actual_q_by_side_mm": j["results"]["factory"]["actual_q_by_side_mm"],
            "producer": j["results"]["factory"], "independent_STEP_reader": j["results"]["readback"],
            "resource_observations_summary": resources, "independent_evaluated_passing_gates": len(early),
            "whole_panel_material_account": account, "whole_material_comparison_records": j["whole_material_comparison_records"],
            "scientific_artifact": binding, "artifact_expires_at": j["artifact_expires_at"],
            "actual_finite_state_clear": True})
    require(pairs == 237818 == plan["fresh_factory_plus_reader_pair_evaluations_planned"] and
            journal == 475636 == plan["selected_and_completed_journal_rows_planned"] and
            gates == 156 == plan["independent_native_early_gate_rows_planned"], "campaign totals differ")
    require(dict(methods) == {"native_common": 15474, "positive_axis_gap": 222344}, "actual aggregate method tally differs")
    require((directory / "K3FULL_stow_tabs_3_INSPECTION.json").read_bytes() ==
            (root / "published/K3FULL_stow_tabs_3_INSPECTION.json").read_bytes(), "CP2 published inspection byte closure differs")
    output = {
        "schema": "razr-K3FULL-recovered-ten-finite-state-acceptance-v1",
        "functional_source_commit": S4, "diagnostic_commit": HEAD, "run_id": RUN,
        "published_execution_plan_sha256": PLAN_SHA, "unchanged_published_inspector_sha256": INSPECTOR_SHA,
        "new_aggregation_source_sha256": sha(Path(__file__).read_bytes()),
        "candidate_source_sha256": plan["candidate_source_sha256"],
        "candidate_contract_sha256": plan["candidate_contract_sha256"],
        "actual_K3_dual_pilot_binding_sha256": plan["actual_dual_pilot_binding_sha256"],
        "all_ten_preregistered_finite_states_factory_and_independent_reader_clear": True,
        "actual_preregistered_finite_state_count": 10,
        "actual_pair_evaluations_producer_plus_reader": pairs, "actual_selected_and_completed_journal_rows": journal,
        "actual_evaluated_passing_independent_gates": gates, "aggregate_pair_methods": dict(methods),
        "rejected_pairs_above_original_1e_minus_7_mm3_gate": 0, "native_pair_evaluation_unresolved": 0,
        "independent_gate_evaluation_unresolved": 0, "producer_reader_classification_disagreement": 0,
        "all_original_owned_resource_guards_passed": True,
        "scientific_original_ZIP_count": 10, "scientific_original_ZIP_total_bytes": sum(x["zip_bytes"] for x in artifacts),
        "recovery": {
            "old_local_runtime_and_unpublished_RAM_records_absent": True,
            "unchanged_published_inspector_source_recovered_exactly": True,
            "all_ten_original_scientific_ZIPs_completely_reverified_after_reset": True,
            "recovered_manifest_and_observation_files_are_original_scientific_bytes": True,
            "inspections_and_scope_projections_remain_marked_derivatives": True,
            "new_native_CAD_or_solver_execution": False,
            "previous_unpublished_aggregate_sha256_from_session_history":
                "36cf7a23284fdb6a244174834757a213f11735b327bb6dcfcd92df517afdce6b",
            "previous_unpublished_aggregate_original_bytes_recovered": False,
            "old_local_aggregation_assertion_failure_history":
                "Initial local join treated two nonempty mode dictionaries as false; prior source and failure receipt were lost in runtime reset.",
            "old_pre_native_campaign_entry_failures_remain_in_published_CP2_and_scientific_draft": True,
            "old_entry_failure_run_id": 40283562050,
            "old_entry_failure_is_not_a_geometry_rejection": True},
        "rows": rows,
        "scope_limits": {
            "finite_states_do_not_prove_complete_independent_continuous_domain": True,
            "reader_uses_separate_process_same_pinned_CAD_kernel": True,
            "second_CAD_kernel_used": False, "whole_A_BACK_PANEL_added_volume_is_not_per_side": True,
            "complete_product_motion_proved": False, "physical_allowed_domain_proved": False,
            "global_minimum_wall_measured": False, "strength_qualified": False,
            "physical_specimen_G3_G4_G5_qualified": False, "raw_runtime_durable_preservation_claimed": False,
            "candidate_go": False, "fixture_fabrication_go": False, "manufacturing_go": False}}
    out = root / "K3FULL-final"
    out.mkdir(parents=True, exist_ok=True)
    report = out / "K3FULL_RECOVERED_TEN_STATE_ACCEPTANCE.json"
    report.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    all_inputs = out / "K3FULL_RECOVERED_ALL_TEN_ARCHIVE_INPUTS.json"
    all_inputs.write_text(json.dumps({"schema": "razr-reviewed-scientific-archive-inputs-v1", "artifacts": artifacts}, indent=2) + "\n")
    remaining = out / "K3FULL_RECOVERED_REMAINING_NINE_ARCHIVE_INPUTS.json"
    remaining.write_text(json.dumps({"schema": "razr-reviewed-scientific-archive-inputs-v1",
                                    "artifacts": [x for x in artifacts if x["label"] != "K3FULL-stow_tabs_3"]}, indent=2) + "\n")
    print(json.dumps({"report": report.name, "sha256": sha(report.read_bytes()), "bytes": report.stat().st_size,
                      "pairs": pairs, "journal": journal, "gates": gates, "all_ten_actual_finite_clear": True}, indent=2))

if __name__ == "__main__":
    main()
