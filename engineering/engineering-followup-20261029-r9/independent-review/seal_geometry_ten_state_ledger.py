"""Seal a ten-state geometry record ledger after all required actual readers finish.

No CAD is imported or executed here. This joins immutable independent audits,
checks their current source/report bindings, and keeps finite native completion
separate from original failures and continuous/physical qualification.
"""
import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
GEOMETRY = HERE.parent / "geometry"
LEAF_FILES = {
    "stow_tabs_0": "R9_GEOMETRY_LEAF_STOW_TABS_0_RECORD_AUDIT.json",
    "stow_tabs_3": "R9_GEOMETRY_LEAF_STOW_TABS_3_RECORD_AUDIT.json",
    "predock": "R9_GEOMETRY_LEAF_PREDOCK_RECORD_AUDIT.json",
    "open_installed": "R9_GEOMETRY_LEAF_OPEN_INSTALLED_RECORD_AUDIT.json",
    "lower_L_contact_R_free": "R9_GEOMETRY_LEAF_LOWER_L_RECORD_AUDIT.json",
    "lower_R_contact_L_free": "R9_GEOMETRY_LEAF_LOWER_R_RECORD_AUDIT.json",
    "upper_L_contact_R_free": "R9_GEOMETRY_LEAF_UPPER_L_RECORD_AUDIT.json",
    "upper_R_contact_L_free": "R9_GEOMETRY_LEAF_UPPER_R_RECORD_AUDIT.json",
}


def need(value, reason):
    if not value:
        raise ValueError(reason)


def ident(path):
    path = Path(path)
    with path.open("rb") as stream:
        return {"bytes": path.stat().st_size, "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}


def load(path):
    return json.loads(Path(path).read_text())


def bind_record(root, item):
    path = root / item["path"]
    need(ident(path) == {k: item[k] for k in ("bytes", "sha256")}, "current bound record changed: " + str(path))
    return load(path)


def main(a):
    roster_path = HERE / "R9_GEOMETRY_ORIGINAL_ROSTER_AUDIT_V2.json"
    historical_path = HERE / "R9_ORIGINAL_NEAR_FAR_FULL_MATRIX_READBACK_V2.json"
    roster, historical = load(roster_path), load(historical_path)
    need(roster["completed"] and historical["completed"], "completed source and original-midpose audits required")
    need(roster["expected_full_matrix_pair_total"] == 118909 and historical["full_matrices_recounted"] == 4,
         "full original state requirements")
    need(historical["original_roster_source"] == {k: roster["state_source_copies"][0][k] for k in ("bytes", "sha256")},
         "one original ten-state roster source")
    old = {p["pose"]: p for p in historical["poses"]}
    need(set(old) == {"near", "far"}, "exact original midpose pair")
    base_names = {x["body"] for x in old["near"]["bound_saved_body_files"]}
    need(len(base_names) == 154 and {x["body"] for x in old["far"]["bound_saved_body_files"]} == base_names,
         "full original154 material inventory")
    candidate_source = ident(a.helpers / "panel_key_travel_stops_v1.py")["sha256"]
    candidate_contract = ident(a.helpers / "PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json")["sha256"]
    states = []
    method_counts = {role: Counter() for role in ("producer", "reader")}
    new_state_method_differences = []
    native_files = total_pairs = total_gates = 0
    for registered in roster["full_original_roster"]:
        name = registered["state"]
        if name in old:
            p = old[name]
            need(p["candidate_source_sha256"] == candidate_source and p["candidate_contract_sha256"] == candidate_contract,
                 "historical and current named candidate bytes")
            need(p["all_original_finite_K3_pair_criteria_recounted"] and
                 p["new_CAD_or_runtime_replay_performed"] is False, "current file readback of actual historical CAD")
            role_rows = {"producer": p["roles"]["factory"], "reader": p["roles"]["readback"]}
            n = role_rows["producer"]["participant_count"]
            count = role_rows["producer"]["unique_complete_pairs"]
            need(role_rows["reader"]["participant_count"] == n and role_rows["reader"]["unique_complete_pairs"] == count,
                 "two historical full roles")
            row = {"state": name, "evidence_origin": "original R7 native execution; current archive/record readback",
                   "independent_audit": {"path": historical_path.name, **ident(historical_path)},
                   "archive": p["archive"], "participant_count": n, "pairs_per_role": count,
                   "actual_producer_completed": True, "actual_independent_native_reader_completed": True,
                   "current_record_audit_completed": True, "finite_pose_clear": True,
                   "producer_reader_maximum_Common_difference_mm3": p["producer_reader_max_Common_difference_mm3"],
                   "applicable_independent_native_gates": p["archived_native_early_gates_passed"],
                   "native_body_file_count_rehashed": len(p["bound_saved_body_files"]),
                   "actual_q_by_side_mm": role_rows["producer"]["actual_q_by_side_mm"],
                   "method_counts": {role: item["method_counts"] for role, item in role_rows.items()},
                   "original_baseline_failure_and_named_repair_scope": p["baseline_failure_and_K1_chain"],
                   "new_CAD_performed_in_this_record_audit": False}
        else:
            path = HERE / LEAF_FILES[name]
            audit = load(path)
            need(audit["completed"] and audit["state"] == name and audit["finite_pose_clear"], "completed actual finite state audit: " + name)
            need(audit["original_roster_audit"] == ident(roster_path), "one frozen source/input audit")
            need(audit["original_state_record"] == registered["unchanged_original_state_record"], "unchanged full original state")
            need(audit["unchanged_original_inputs_bitwise"] and audit["expected_contacts"] == registered["unchanged_expected_contacts"],
                 "original binary64 input/contact assignments")
            p = bind_record(GEOMETRY, audit["producer_report"])
            r = bind_record(GEOMETRY, audit["reader_report"])
            for key in ("producer_campaign", "reader_campaign", "reader_captured_producer"):
                bind_record(GEOMETRY, audit[key])
            need(p["completed"] and r["completed"] and p["finite_pose_clear"] and r["finite_pose_clear"], "actual roles still complete")
            need(p["candidate_application"]["source_sha256"] == candidate_source, "same historical/current candidate source")
            need(set(p["participant_names"]) == {x["body"] for x in audit["all_whole_native_body_files_rehashed"]},
                 "whole named material census")
            if name == "open_installed":
                need(base_names < set(p["participant_names"]) and len(set(p["participant_names"]) - base_names) == 7,
                     "all154 original participants plus seven installed OPEN parts")
            else:
                need(set(p["participant_names"]) == base_names, "all154 original factory participants at this state")
            role_matrices = {}
            for role in ("producer", "reader"):
                role_dir = GEOMETRY / audit[role + "_report"]["path"]
                need(ident(role_dir.parent / "pairs.jsonl") == audit[role]["pair_file"], "unchanged actual full-pair journal")
                role_matrices[role] = [json.loads(line) for line in (role_dir.parent / "pairs.jsonl").read_text().splitlines()]
            branch_changes = []
            for left, right in zip(role_matrices["producer"], role_matrices["reader"]):
                need((left["a"], left["b"]) == (right["a"], right["b"]), "same whole-material pair in method review")
                if left["method"] == right["method"]:
                    continue
                need(right["factory_classification_and_volume_agree"] and left["rejected"] == right["rejected"]
                     and abs(left["common_mm3"] - right["common_mm3"]) <= 1e-7,
                     "different method branches still satisfy original volume/classification gate")
                change = {"state": name, "a": left["a"], "b": left["b"],
                          "producer": {k: left[k] for k in ("method", "axis_gap_lower_mm", "common_mm3", "rejected")},
                          "reader": {k: right[k] for k in ("method", "axis_gap_lower_mm", "common_mm3", "rejected")},
                          "original_volume_and_classification_agree": True,
                          "not_a_classification_mismatch": True}
                branch_changes.append(change)
            new_state_method_differences.extend(branch_changes)
            row = {"state": name, "evidence_origin": "actual R9 native execution and independent native reader",
                   "independent_audit": {"path": path.name, **ident(path)},
                   "producer_report": audit["producer_report"], "reader_report": audit["reader_report"],
                   "participant_count": audit["participant_count"], "pairs_per_role": audit["whole_pair_count_per_role"],
                   "actual_producer_completed": True, "actual_independent_native_reader_completed": True,
                   "current_record_audit_completed": True, "finite_pose_clear": True,
                   "producer_reader_maximum_Common_difference_mm3": audit["whole_pair_maximum_reader_minus_producer_mm3"],
                   "applicable_independent_native_gates": audit["applicable_independent_native_gates"],
                   "native_body_file_count_rehashed": audit["whole_native_body_file_count"],
                   "actual_q_by_side_mm": p["actual_q_by_side_mm"],
                   "method_counts": {role: audit[role]["method_counts"] for role in ("producer", "reader")},
                   "different_method_branches": branch_changes,
                   "native_state_seconds": {"producer": audit["producer_leaf_seconds"], "reader": audit["reader_leaf_seconds"]},
                   "saved_STEP_maximum_volume_difference_mm3": audit["max_saved_STEP_roundtrip_volume_difference_mm3"],
                   "new_CAD_performed_in_this_record_audit": False}
            if name == "open_installed":
                row["seven_additional_installed_OPEN_participants"] = sorted(set(p["participant_names"]) - base_names)
        need(row["participant_count"] == registered["expected_participant_count"] and
             row["pairs_per_role"] == registered["required_complete_unordered_pairs"], "original required full count")
        total_pairs += row["pairs_per_role"]
        native_files += row["native_body_file_count_rehashed"]
        total_gates += row["applicable_independent_native_gates"]
        for role in method_counts:
            method_counts[role].update(row["method_counts"][role])
        states.append(row)
    need(len(states) == 10 and total_pairs == 118909 and native_files == 3094, "full10 cumulative census")
    for role, counts in method_counts.items():
        need(sum(counts.values()) == total_pairs, role + " complete method accounting")
    capacity_path = GEOMETRY / "CAPACITY_BASIS_V3.json"
    capacity = load(capacity_path)
    need(capacity["prior_four_asymmetric_producers_completed_and_at_least_three_readers_completed"] and
         capacity["prior_four_asymmetric_states_completed_and_read_back"] is False,
         "original capacity snapshot is not rewritten as final completion")
    original_v1 = load(GEOMETRY / "producer-attempt1/report.json")
    need(original_v1["completed"] is False, "original stopped four-state campaign remains incomplete")
    result = {"schema": "razr-r9-independent-final-ten-state-native-record-ledger-v1",
              "completed": True, "sealed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "ledger_source": ident(__file__), "original_input_audit": ident(roster_path),
              "original_midpose_archive_readback": ident(historical_path),
              "candidate_name": "panel_key_travel_stops_v1", "candidate_source_sha256": candidate_source,
              "candidate_contract_sha256": candidate_contract, "original_S4_commit": roster["original_S4_commit"],
              "original_Common_tolerance_mm3": 1e-7, "states": states,
              "original_registered_states": 10, "full_native_producer_states_completed": 10,
              "full_native_reader_states_completed": 10, "current_record_audits_completed": 10,
              "finite_state_pairs_per_role": total_pairs, "producer_plus_reader_pair_results": 2 * total_pairs,
              "saved_whole_native_body_files_rehashed": native_files,
              "all_applicable_native_early_gates_passed": total_gates,
              "method_counts_per_role": {k: dict(v) for k, v in method_counts.items()},
              "new_state_different_method_branch_count": len(new_state_method_differences),
              "new_state_different_method_branches": new_state_method_differences,
              "per_pair_method_equality_required_by_original_gate": False,
              "method_identity_not_substituted_for_Common_and_classification_criteria": True,
              "historical_selected_completed_event_lines_are_not_pair_count": True,
              "historical_panel_only_153_results_counted_as_full_matrix": False,
              "original_F1a_positive_collisions_preserved": True,
              "original_F1a_nonzero_STEP_readback_differences_preserved": True,
              "nested_named_K1_matrix_counted_as_top_level_K3_matrix": False,
              "v1_stopped_original_campaign_incomplete_retained": True,
              "retained_audit_implementation_failures": {
                  name: ident(HERE / name) for name in (
                      "R9_GEOMETRY_ROSTER_AUDIT_ATTEMPT1_FAILURE.json",
                      "R9_ORIGINAL_MIDPOSE_AUDIT_ATTEMPT1_FAILURE.json")},
              "audit_schema_failures_are_not_native_CAD_outcomes": True,
              "capacity_is_start_time_snapshot": {"record": ident(capacity_path),
                                                 "prior_four_fully_read_back_at_snapshot": False,
                                                 "final_state_outcomes_come_from_actual_readers": True},
              "scope": {"finite_native_same_candidate_all_ten_original_states": True,
                        "current_audit_is_file_record_and_arithmetic_only": True,
                        "new_CAD_executed_by_this_ledger": False,
                        "original_locked_runtime_replayed": False, "full_continuous_G2": False,
                        "physical_allowed_domain_proved": False, "current_structure_FE_qualified": False,
                        "physical_qualification": False, "manufacturing_go": False}}
    with a.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps({"completed": True, "states": 10, "pairs_per_role": total_pairs,
                      "pair_result_records": 2 * total_pairs, "body_files_rehashed": native_files,
                      "native_gates": total_gates, "full_G2": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--helpers", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
