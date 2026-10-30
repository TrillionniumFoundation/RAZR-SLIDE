"""Read actual finite-state evidence, retain provenance, and write R9 scope.

No CAD or new physical qualification is performed by this consolidation.
Historical R7 near/far evidence is identified separately from the eight new
R9 factory and independent-reader executions.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import datetime as dt
import hashlib
import itertools
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(Path(path).read_text())


def rec(path):
    p = Path(path).resolve()
    with p.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    try:
        name = str(p.relative_to(HERE))
    except ValueError:
        name = str(p)
    return {"path": name, "bytes": p.stat().st_size, "sha256": digest}


def literal(name, path):
    for node in ast.parse(Path(path).read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError("missing original literal " + name)


def matrix(path, names):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    expected = list(itertools.combinations(sorted(names), 2))
    actual = [(r["a"], r["b"]) for r in rows]
    if actual != expected:
        raise ValueError("complete pair roster differs: " + str(path))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--helpers-root", required=True, type=Path)
    ap.add_argument("--near-engineering", required=True, type=Path)
    ap.add_argument("--history-scope", required=True, type=Path)
    ap.add_argument("--independent-review", nargs="*", default=[], type=Path)
    ap.add_argument("--output", required=True, type=Path)
    a = ap.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    roster_source = a.helpers_root / "full_stop_states.py"
    roster = literal("STATES", roster_source)
    contacts = literal("EXPECTED_CONTACT_ENDS", roster_source)
    history = load(a.history_scope)
    historical_archives = {}
    for name in ("near", "far"):
        preservation_file = a.history_scope.parent.parent / "preservation" / ("R7_" + name.upper() + "_COMPLETE_PRESERVATION_V1.json")
        preservation = load(preservation_file)
        historical_archives[name] = {"original_preservation_record": rec(preservation_file),
                                     "archive_bytes": preservation["bytes"],
                                     "archive_sha256": preservation["sha256"],
                                     "saved_file": preservation["saved_file"],
                                     "included_in_new_R9_geometry_archive": False}
    sources = {
        "lower_L_contact_R_free": ("producer-attempt1", "reader-first-v2-attempt1"),
        "lower_R_contact_L_free": ("producer-v2-attempt1", "reader-lower-R-v2-attempt1"),
        "upper_L_contact_R_free": ("producer-v2-attempt1", "reader-upper-L-v2-attempt1"),
        "upper_R_contact_L_free": ("producer-v2-attempt1", "reader-upper-R-v2-attempt1"),
        "stow_tabs_0": ("producer-v3-attempt1", "reader-stow-tabs-0-v3-attempt1"),
        "stow_tabs_3": ("producer-v3-attempt1", "reader-stow-tabs-3-v3-attempt1"),
        "predock": ("producer-v3-attempt1", "reader-predock-v3-attempt1"),
        "open_installed": ("producer-v3-attempt1", "reader-open-installed-v3-attempt1"),
    }
    states = {}
    for name in roster:
        expected = roster[name]
        if name in ("near", "far"):
            h = history["finite_poses"][name]
            states[name] = {
                "evidence_kind": "historical_R7_full_factory_and_independent_reader; current-turn archive/row review is separately referenced",
                "new_CAD_executed_this_turn": False,
                "original_state_input": expected,
                "participant_count": h["factory_and_reader"]["factory"]["participant_count"],
                "producer_pair_count": h["factory_and_reader"]["factory"]["pair_count"],
                "reader_pair_count": h["factory_and_reader"]["readback"]["pair_count"],
                "producer_method_counts": h["factory_and_reader"]["factory"]["method_counts"],
                "reader_method_counts": h["factory_and_reader"]["readback"]["method_counts"],
                "completed": h["complete_full_pair_execution"],
                "finite_pose_clear": h["finite_state_clear"],
                "maximum_Common_difference_mm3": h["maximum_factory_reader_all_pair_volume_difference_mm3"],
                "independent_STEP_body_count": h["independent_STEP_body_readback_count"],
                "applicable_original_early_gate_count": h["independent_early_gate_count"],
                "historical_full_pose_record": h,
            }
            continue
        producer, reader = sources[name]
        pp = HERE / producer / name / "report.json"
        rr = HERE / reader / "report.json"
        p = load(pp)
        root_reader = load(rr)
        r = root_reader["states"][name]
        source_input = {k: v for k, v in expected.items()
                        if k not in ("expected_bodies", "actual_binary64_q_from_declared_factory_inputs")}
        if p["input"] != source_input:
            raise ValueError("original registered state input changed: " + name)
        names = p["participant_names"]
        if len(names) != expected["expected_bodies"] or sorted(p["body_exports"]) != names:
            raise ValueError("full original factory participant roster differs: " + name)
        if [p["actual_q_by_side_mm"][s] for s in "LR"] != expected["actual_binary64_q_from_declared_factory_inputs"]:
            raise ValueError("original binary64 q differs: " + name)
        for side in "LR":
            observed = set(p["endpoint_and_overtravel_checks"][side]["endpoint_contacts"])
            if observed != ({contacts[name][side]} if contacts[name][side] else set()):
                raise ValueError("original endpoint contact expectation differs: " + name)
        pf = HERE / producer / name / "pairs.jsonl"
        rf = HERE / reader / name / "pairs.jsonl"
        for path, declared in ((pf, p["pairs"]["file"]), (rf, r["pairs"]["file"])):
            actual_identity = rec(path)
            if {k: actual_identity[k] for k in ("bytes", "sha256")} != declared:
                raise ValueError("actual complete matrix bytes differ from native report identity")
        prows, rrows = matrix(pf, names), matrix(rf, names)
        failures = [x for x in prows + rrows if x.get("evaluation_failed")]
        rejected = [x for x in prows + rrows if x.get("rejected")]
        positives = [x for x in prows + rrows if x.get("common_mm3", 0.0) > 0]
        differences = [abs(x["common_mm3"] - y["common_mm3"])
                       for x, y in zip(prows, rrows)
                       if not x.get("evaluation_failed") and not y.get("evaluation_failed")]
        method_differences = [{"a": x["a"], "b": x["b"], "producer": x.get("method"), "reader": y.get("method")}
                              for x, y in zip(prows, rrows) if x.get("method") != y.get("method")]
        classifications_agree = all(x.get("rejected") == y.get("rejected") for x, y in zip(prows, rrows))
        original_predicates_agree = not failures and classifications_agree and max(differences, default=0.0) <= 1e-7
        pm = dict(Counter(x["method"] for x in prows if "method" in x))
        rm = dict(Counter(x["method"] for x in rrows if "method" in x))
        if pm != p["pairs"]["method_counts"] or rm != r["pairs"]["method_counts"]:
            raise ValueError("method counts do not describe actual row files")
        early = r["independent_native_early_gates"]
        states[name] = {
            "evidence_kind": "new_R9_full_factory_and_separate_process_reader",
            "new_CAD_executed_this_turn": True,
            "original_state_input": expected, "original_state_input_unchanged": True,
            "producer_leaf_report": rec(pp), "reader_campaign_report": rec(rr),
            "producer_pair_file": rec(pf), "reader_pair_file": rec(rf),
            "participant_count": len(names), "producer_pair_count": len(prows), "reader_pair_count": len(rrows),
            "both_actual_pair_rosters_equal_complete_combinations": True,
            "producer_method_counts": pm, "reader_method_counts": rm,
            "producer_reader_method_differences": method_differences,
            "maximum_Common_difference_mm3": max(differences, default=0.0),
            "consolidation_readback_original_predicates_agree": original_predicates_agree,
            "all_evaluation_failures": failures, "all_rejected_rows": rejected,
            "all_positive_Common_rows_including_subthreshold_values": positives,
            "producer_positive_Common_originals": p["pairs"]["positive"],
            "producer_completed": p["completed"], "reader_completed": root_reader["completed"] and r["completed"],
            "completed": p["completed"] and root_reader["completed"] and r["completed"],
            "finite_pose_clear": p["finite_pose_clear"] and r["finite_pose_clear"] and original_predicates_agree and not rejected,
            "producer_direct_panel_KEY_Common_mm3": p["panel_KEY_direct_Common_mm3"],
            "reader_direct_panel_KEY_Common_mm3": r["panel_KEY_direct_Common_mm3"],
            "independent_STEP_body_count": len(r["body_readbacks"]),
            "all_independent_whole_STEP_BREP_and_original_signature_checks_pass": all(x["passed"] for x in r["body_readbacks"].values()),
            "applicable_original_early_gate_count": len(early),
            "all_original_early_gates_pass": all(x.get("evaluated") and x.get("passed") for x in early.values()),
            "producer_original_frozen_BREP_unchanged": p["pairs"].get("all_original_BREP_bytes_unchanged"),
            "reader_original_frozen_BREP_unchanged": r["pairs"]["all_original_BREP_bytes_unchanged"],
            "original_panel_to_retained_complete_material": p["original_panel_mapping"],
            "candidate_panel_to_retained_complete_material": p["candidate_panel_mapping"],
            "fresh_original_KEY_to_retained_q0": p["native_scene_metadata"]["named_KEY_candidate"]["current_factory_KEY_material_comparisons"],
            "independent_whole_candidate_KEY_to_retained_q0": r["whole_KEY_mapping"],
            "whole_panel_KEY_originals": {n: p["body_exports"][n] for n in ("A_BACK_PANEL", "L_KEY", "R_KEY")},
            "endpoint_and_overtravel_checks": p["endpoint_and_overtravel_checks"],
            "producer_seconds": p["seconds"], "producer_matrix_seconds": p["pairs"]["seconds"],
            "reader_seconds": r["seconds"], "reader_peak_RSS_bytes": root_reader["peak_RSS_bytes"],
            "reader_imported_producer": root_reader["producer_module_imported"],
            "reader_imported_candidate_builders": root_reader["candidate_builders_imported"],
        }
    k1 = {}
    for name in ("near", "far"):
        path = a.near_engineering / "prerequisite-stow_tabs_3" / ("prerequisite-" + name) / "factory/worker/report.engineering.json"
        prior = load(path)["engineering_record"]
        cmp = prior["original_baseline_material_comparisons"]
        k1[name] = {"historical_K1_factory_projection": rec(path),
                    "original_F1a_prerequisite_identity": prior["F1a_prerequisite"],
                    "original_baseline_panel_KEY_positive_Common_preserved": prior["baseline_panel_KEY_direct_Common"],
                    "all_original_baseline_participants_mapped": len(cmp),
                    "all_original_baseline_directed_material_differences_zero": all(x["a_minus_b_mm3"] == x["b_minus_a_mm3"] == 0 for x in cmp.values()),
                    "panel_KEY_original_material_comparisons": {n: cmp[n] for n in ("A_BACK_PANEL", "L_KEY", "R_KEY")},
                    "named_K1_material_accounts": prior["candidate_application"]["material_accounts"],
                    "original_failed_geometry_reclassified": False}
    first = load(HERE / "producer-attempt1/lower_L_contact_R_free/report.json")
    source = load(HERE / "SOURCE_EXACT_S4_COMPARISON.json")
    native_mapping = load(HERE / "NATIVE_PROFILE_EIGHT_STATES.json")
    native_mapping_rows = [row for state in native_mapping["states"].values() for row in state["bodies"].values()]
    method_totals = {role: Counter() for role in ("producer", "reader")}
    for row in states.values():
        for role in method_totals:
            method_totals[role].update(row[role + "_method_counts"])
    out = {
        "schema": "razr-r9-ten-finite-states-source-material-and-independent-domain-scope-v1",
        "recorded_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "consolidator": rec(__file__), "new_CAD_performed_by_consolidation": False,
        "original_ten_state_source": rec(roster_source), "original_ten_state_roster": list(roster),
        "functional_source_commit": source["functional_source_commit"], "functional_source_git_tree": source["git_tree"],
        "complete_archived_S4_source_comparison": rec(HERE / "SOURCE_EXACT_S4_COMPARISON.json"),
        "all_973_archived_source_input_blobs_equal_actual_S4_Git": source["match_count"] == source["source_member_count"] == 973 and not source["mismatches"],
        "historical_R7_complete_scope": rec(a.history_scope),
        "historical_near_far_complete_original_archives": historical_archives,
        "independent_current_turn_reviews": [rec(x) for x in a.independent_review],
        "states": states,
        "state_count": len(states), "new_R9_state_count": len(sources), "retained_R7_state_count": 2,
        "all_ten_finite_state_executions_complete": all(x["completed"] for x in states.values()),
        "all_ten_finite_states_clear": all(x["finite_pose_clear"] for x in states.values()),
        "complete_producer_pairs_across_ten_states": sum(x["producer_pair_count"] for x in states.values()),
        "complete_reader_pairs_across_ten_states": sum(x["reader_pair_count"] for x in states.values()),
        "new_R9_producer_pairs": sum(states[n]["producer_pair_count"] for n in sources),
        "new_R9_reader_pairs": sum(states[n]["reader_pair_count"] for n in sources),
        "actual_matrix_method_totals_by_role": {k: dict(v) for k, v in method_totals.items()},
        "new_R9_producer_reader_method_difference_count": sum(len(states[n]["producer_reader_method_differences"]) for n in sources),
        "OPEN_STEP_reader_method_branch_differences": rec(HERE / "OPEN_STEP_METHOD_BRANCH_DIFFERENCES.json"),
        "all_producer_reader_methods_identical": False,
        "full_factory_participant_appearances_across_ten_states": sum(x["participant_count"] for x in states.values()),
        "new_R9_full_factory_participant_appearances": sum(states[n]["participant_count"] for n in sources),
        "complete_STEP_and_BREP_body_originals_across_ten_states": 2 * sum(x["participant_count"] for x in states.values()),
        "new_R9_complete_STEP_and_BREP_body_originals": 2 * sum(states[n]["participant_count"] for n in sources),
        "independent_applicable_early_gate_total_across_ten_states": sum(x["applicable_original_early_gate_count"] for x in states.values()),
        "pair_count_is_not_number_of_native_Common_calls": True,
        "historical_153_panel_only_pilot_pairs_counted_as_full_matrix": False,
        "original_F1a_and_named_K1_material_history": k1,
        "K1_local_declared_section": {"leg_dimensions_mm": [0.38, 0.36], "leg_area_mm2": 0.1368,
                                      "original_bridge_dimensions_mm": [1.5, 0.36], "original_bridge_area_mm2": 0.54,
                                      "ratio": 0.25333333333333335,
                                      "section_directions": "new leg XZ versus original bridge YZ at different local positions",
                                      "retained_yoke_tab_nominal_section_mm2": 0.075,
                                      "retained_yoke_section_is_global_minimum_proof": False,
                                      "minimum_whole_KEY_wall_or_section_proved": False,
                                      "strength_or_life_qualified": False},
        "K3_current_addition_and_functional_faces": {
            "source": rec(a.helpers_root / "panel_key_travel_stops_v1.py"),
            "contract": rec(a.helpers_root / "PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json"),
            "whole_panel_account": first["candidate_application"]["actual_added_only_panel_account"],
            "native_positive_joins": first["candidate_application"]["actual_positive_joins"],
            "original_cover_functional_faces": first["candidate_application"]["original_cover_functional_face_material_preserved"],
            "physical_stop_added_to_real_specimen": False},
        "positive_q_source_and_native_mapping": {
            "source_domain": rec(HERE / "SOURCE_ALLOWED_DOMAIN_TEN_STATE_READBACK_V2.json"),
            "actual_eight_state_native_mapping": rec(HERE / "NATIVE_PROFILE_EIGHT_STATES.json"),
            "native_mapping_state_count": len(native_mapping["states"]),
            "actual_STOP_SPRING_native_body_mapping_count": len(native_mapping_rows),
            "all_native_bounds_mappings_pass": all(x["passed"] for x in native_mapping_rows),
            "maximum_actual_native_bounds_difference_mm": max(x["maximum_abs_bound_difference_mm"] for x in native_mapping_rows),
            "cam_STOP_X_height_lower_stop_is_not_K3_panel_Y_travel_stop": True,
            "full_real_independent_domain_proved": False,
            "real_spring_preload_stiffness_force_and_contact_maintenance_proved": False},
        "frozen_predicate_v2_evidence": {
            "source": rec(HERE / "frozen_predicate_v2.py"),
            "pilot": rec(HERE / "frozen-matrix-pilot1/report.json"),
            "original_v1_vs_frozen_v2_all_rows": rec(HERE / "v1-v2-first-full-comparison/report.json"),
            "maximum_Common_volume_difference_mm3": 0.0,
            "maximum_axis_gap_readback_difference_mm": 2.842170943040401e-14,
            "original_Common_threshold_mm3": 1e-7,
            "positive_axis_gaps_require_original_whole_material_validation_and_frozen_BREP": True,
            "potential_overlap_uses_original_strict_common_on_deep_geometry_copies": True,
            "pilot_is_not_a_second_full_factory_or_independent_reader": True},
        "original_v1_four_state_campaign": {
            "completed": False, "one_completed_state_retained": "lower_L_contact_R_free",
            "partial_second_state_files_retained": 352,
            "partial_second_state_qualified": False,
            "initial_controlled_stop_ESRCH_failure_retained": rec(HERE / "v1-stop.stderr"),
            "successful_owned_controlled_stop": rec(HERE / "producer-attempt1/OWNED_STOP_AFTER_FIRST.json"),
            "poststop_original_source_readback": rec(HERE / "V1_POSTSTOP_SOURCE_READBACK.json")},
        "capacity_for_remaining_four_original_states": rec(HERE / "CAPACITY_BASIS_V3.json"),
        "resource_observations": rec(HERE / "RESOURCE_OBSERVATIONS.jsonl"),
        "initial_resource_event_observation": rec(HERE / "RESOURCE_EVENT_INITIAL_OBSERVATION.json"),
        "resource_event_interpretation": "Shared cgroup OOM counters were nonzero before v3 start and later increments were observed. Each observation separately records the then-running owned workers, while completed workers have exit receipts. The event victim and cause were not identified. Scientific completion is determined from retained per-state reports and independent readers, not these resource observations.",
        "observed_worker_completions": rec(HERE / "EXECUTION_COMPLETIONS.jsonl"),
        "original_locked_43_package_runtime_replayed_by_R9": False,
        "full_continuous_G2": False, "physical_allowed_domain_proved": False,
        "minimum_wall_and_current_geometry_FE_qualified": False,
        "OEM_electrical_identity_qualified": False, "G3_G4_G5_qualified": False,
        "all_blockers_closed": False, "manufacturing_go": False,
        "remaining": literal("REMAINING", roster_source),
    }
    a.output.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: out[k] for k in ("state_count", "all_ten_finite_state_executions_complete",
                                       "all_ten_finite_states_clear", "complete_producer_pairs_across_ten_states",
                                       "new_R9_producer_pairs", "full_continuous_G2")}))


if __name__ == "__main__":
    main()
