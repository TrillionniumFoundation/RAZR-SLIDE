"""Reopen original near/far archives and recount full native result matrices.

This performs file/hash, source, record and arithmetic checks only. It does not
run CAD or replay the archived runtime. Baseline F1a failures remain distinct
from K1 KEY repair and K3 panel-stop candidate results.
"""
import argparse
import ast
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import zipfile

HERE = Path(__file__).resolve().parent
R9 = HERE.parent
S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"
TOL = 1e-7


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def byte_identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def identity(path):
    p = Path(path)
    return {"bytes": p.stat().st_size, "sha256": hashlib.file_digest(p.open("rb"), "sha256").hexdigest()}


def bits_equal(a, b):
    return struct.pack(">d", a) == struct.pack(">d", b)


def bind_bytes(data, expected):
    actual = byte_identity(data)
    need(actual == {k: expected[k] for k in ("bytes", "sha256")}, "bound saved bytes differ")
    return actual


def state_definitions():
    p = R9 / "geometry/source-originals/full_stop_states.py"
    tree = ast.parse(p.read_text())
    states = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                  and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "STATES")
    return states, identity(p)


def check_matrix(record, journal, spec):
    names = record["participant_names"]
    need(len(names) == len(set(names)) == record["participant_count"] == 154, "154 complete unique participants")
    expected = list(itertools.combinations(sorted(names), 2))
    rows = record["pairs"]
    need([(r["a"], r["b"]) for r in rows] == expected, "complete ordered 11781 pair roster")
    need(len(rows) == record["persisted_pair_count"] == record["expected_pair_count"] == 11781, "original full count")
    need(record["execution_completed"] and record["all_unordered_pairs_present_once"] and record["finite_pose_clear"],
         "actual completed finite full matrix")
    need(record["functional_source_commit"] == S4 and record["candidate_name"] == "panel_key_travel_stops_v1",
         "same S4/K3 named candidate")
    expected_input = {k: v for k, v in spec.items() if k not in
                      ("expected_bodies", "actual_binary64_q_from_declared_factory_inputs")}
    need(record["pose_input"] == expected_input, "exact original full factory inputs")
    need(all(bits_equal(record["actual_q_by_side_mm"][side], q) for side, q in
             zip("LR", spec["actual_binary64_q_from_declared_factory_inputs"])), "original binary64 q identity")
    need(not record["evaluation_failures"] and not record["positive_pairs"] and not record["mismatches_to_factory"],
         "retained native failure or mismatch is not clear")
    methods = Counter()
    for row in rows:
        value = row["common_mm3"]
        need(math.isfinite(value) and value >= 0 and row["rejected"] == (value > TOL), "original signed Common gate")
        need(not row["rejected"] and value == 0.0, "saved whole candidate pair is clear")
        method = row["method"]
        need(method in ("native_common", "positive_axis_gap"), "known finite native method")
        gap = row["axis_gap_lower_mm"]
        need(math.isfinite(gap), "finite original gap")
        if method == "positive_axis_gap":
            need(gap > 0, "strict positive gap proof")
        methods[method] += 1
    events = [json.loads(x) for x in journal.splitlines()]
    need(len(events) == 2 * len(rows), "selected/completed journal census")
    for index, row in enumerate(rows):
        selected, finished = events[2 * index:2 * index + 2]
        need(selected["event"] == "selected" and (selected["a"], selected["b"]) == (row["a"], row["b"]),
             "journal selected original pair")
        need(finished["event"] == "completed" and finished["row"] == row, "journal completed exact report row")
    for side in "LR":
        direct = record["panel_KEY_direct_Common"][side]
        need(direct["a"] == "A_BACK_PANEL" and direct["b"] == side + "_KEY", "direct full material operands")
        need(direct["common_mm3"] == 0.0 and direct["rejected"] is False, "candidate direct Common zero")
        need(direct["strict_common"]["common_mm3"] == 0.0 and
             direct["strict_common"]["method"] == "native_common", "direct native Common not a gap-only claim")
    need(record["identity_after"]["source_bytes_and_locked_environment_unchanged"] is True,
         "archived producer/reader source identity guard")
    need(record["identity_before"]["repository_head_at_start"] ==
         record["identity_after"]["repository_head_at_finish"] == S4, "archived exact S4 source identity")
    for flag in ("complete_product_motion_proved", "continuous_backlash_domain_proved", "physical_qualification",
                 "candidate_go", "fixture_fabrication_go", "manufacturing_go", "G2_pass"):
        need(record[flag] is False, "finite result must not widen qualification: " + flag)
    return {"participant_count": 154, "unique_complete_pairs": 11781, "journal_event_count": len(events),
            "method_counts": dict(methods), "positive_Common_count": 0, "rejected_pair_count": 0,
            "evaluation_failure_count": 0, "candidate_name": record["candidate_name"],
            "pose_input": record["pose_input"], "actual_q_by_side_mm": record["actual_q_by_side_mm"],
            "direct_panel_KEY_Common_mm3": {s: record["panel_KEY_direct_Common"][s]["common_mm3"] for s in "LR"}}


def baseline_chain(near_root, pose):
    root = near_root / ("engineering/prerequisite-stow_tabs_3/prerequisite-" + pose)
    path = root / "factory/worker/report.engineering.json"
    blob = path.read_bytes()
    wrapper = json.loads(blob)
    need(wrapper["derived_projection_not_raw_original"] is True, "marked K1 engineering projection")
    record = wrapper["engineering_record"]
    need(record["candidate_name"] == "key_forward_loop_v1" and record["functional_source_commit"] == S4,
         "original S4 baseline and named K1 repair")
    comparisons = record["original_baseline_material_comparisons"]
    need(set(comparisons) == set(record["participant_names"]) and len(comparisons) == 154,
         "all154 baseline material identities")
    need(all(x["a_minus_b_mm3"] == x["b_minus_a_mm3"] == 0.0 and
             x["equal_within_original_1e_minus_7_mm3"] for x in comparisons.values()),
         "whole original material two-way differences")
    expected = {"near": (0.24558784938224815, 0.2455878493822482),
                "far": (0.23013738353925134, 0.23013738353925126)}[pose]
    binding = record["F1a_prerequisite"]
    original_refs = {}
    for role, key in (("factory", "factory_projection_sha256"), ("readback", "reader_projection_sha256")):
        pp = root / "prerequisite" / role / "worker/report.engineering.json"
        data = pp.read_bytes()
        need(hashlib.sha256(data).hexdigest() == binding[key], "original F1a projection identity")
        marked = json.loads(data)
        need(marked["derived_projection_not_raw_original"] is True, "original F1a is a marked projection")
        original = marked["engineering_record"]
        need(original["finite_pose_clear"] is False, "original positive-Common failure retained")
        for side, reference in zip("LR", expected):
            baseline = record["baseline_panel_KEY_direct_Common"][side]
            original_common = original["panel_KEY_direct_Common"][side]["common_mm3"]
            need(bits_equal(baseline["common_mm3"], reference) and bits_equal(original_common, reference),
                 "original F1a positive Common identity")
            need(reference > TOL and baseline["difference_from_original_F1a_mm3"] == 0.0,
                 "reproduced original baseline failure")
        original_refs[role] = byte_identity(data)
    need(all(record["panel_KEY_direct_Common"][side]["common_mm3"] == 0.0 for side in "LR"), "distinct K1 candidate zero")
    # This nested K1 matrix is complete but belongs to another named candidate.
    need(len(record["pairs"]) == record["persisted_pair_count"] == 11781, "actual nested K1 scope")
    return {"K1_engineering_report": byte_identity(blob), "marked_engineering_projection": True,
            "original_F1a_projection_bindings": original_refs,
            "original_F1a_raw_runtime_reconstructed": binding["original_raw_report_downloaded_or_reconstructed"],
            "original_baseline_Common_mm3": dict(zip("LR", expected)),
            "difference_from_original_F1a_mm3": {s: 0.0 for s in "LR"},
            "baseline_participants_mapped_bidirectionally": 154, "maximum_baseline_material_difference_mm3": 0.0,
            "original_failure_reclassified": False,
            "K1_candidate_name": record["candidate_name"],
            "K1_candidate_source_sha256": record["candidate_application"]["source_sha256"],
            "K1_candidate_direct_Common_mm3": {s: 0.0 for s in "LR"},
            "K1_matrix_is_not_top_level_K3_matrix": True,
            "native_q_minus_L1_binary64_mm": record["pose_input"]["native_q_minus_L1_binary64_mm"],
            "same_L1_q_bit_pattern_claimed": False}


def main(args):
    states, roster_id = state_definitions()
    scope_path = R9.parent / "engineering-followup-20261028-r7/native/R7_ACTUAL_NATIVE80_AND_TWO_FINITE_POSES_SCOPE_V1.json"
    scope = json.loads(scope_path.read_text())
    reports = []
    for pose, archive in (("near", args.near_archive), ("far", args.far_archive)):
        preservation_path = args.git_repo / ("engineering/engineering-followup-20261028-r7/preservation/R7_" + pose.upper() + "_COMPLETE_PRESERVATION_V1.json")
        preservation = json.loads(preservation_path.read_text())
        archive_id = identity(archive)
        need(archive_id == {k: preservation[k] for k in ("bytes", "sha256")}, "original full archive identity")
        previous = scope["finite_poses"][pose]
        roles, raw_records = {}, {}
        with zipfile.ZipFile(archive) as z:
            member_names = z.namelist()
            expected_members = preservation.get("full_zip_members", preservation.get("complete_zip_member_count"))
            need(len(member_names) == len(set(member_names)) == expected_members, "complete unique archive member roster")
            for role in ("factory", "readback"):
                report_name = "raw/" + role + "/worker/report.json"
                journal_name = "raw/" + role + "/worker/pairs.jsonl"
                report_data, journal = z.read(report_name), z.read(journal_name)
                sealed = previous["factory_and_reader"][role]
                rid = bind_bytes(report_data, sealed["raw_report"])
                jid = bind_bytes(journal, sealed["raw_journal"])
                record = json.loads(report_data)
                checked = check_matrix(record, journal, states[pose])
                need(checked["method_counts"] == sealed["method_counts"], "sealed original method census")
                roles[role] = {"report": rid, "pair_journal": jid, **checked}
                raw_records[role] = record
            p, r = raw_records["factory"], raw_records["readback"]
            need(r["factory_report_sha256"] == roles["factory"]["report"]["sha256"], "reader bound to exact producer report")
            need(r["separate_process_from_factory"] and r["independent_CAD_kernel"] is False,
                 "same-kernel separate original reader scope")
            need(p["candidate_source_sha256"] == r["candidate_source_sha256"] and
                 p["candidate_contract_sha256"] == r["candidate_contract_sha256"], "same named candidate/contract")
            body_files = []
            need(set(p["body_exports"]) == set(r["body_readbacks"]) == set(p["participant_names"]), "all154 saved and reread bodies")
            for name, exported in p["body_exports"].items():
                need(exported["serialization_preserved_in_memory_signature"] and
                     exported["signature_before"] == exported["signature_after"], "whole material export identity")
                back = r["body_readbacks"][name]
                need(back["passed"] and back["STEP"] == exported["files"]["step"], "whole STEP source binding")
                sig, expected = back["signature"], exported["signature_before"]
                need(sig["is_valid"] and sig["solid_count"] == expected["solid_count"] == 1,
                     "complete positive single material")
                need(sig["signed_volume_mm3"] > 0 and abs(sig["signed_volume_mm3"] - expected["signed_volume_mm3"]) <= TOL,
                     "unchanged original whole-material volume criterion")
                need(max(abs(a - b) for a, b in zip(sig["bounds_mm"], expected["bounds_mm"])) <= TOL,
                     "unchanged original bounds criterion")
                for kind, entry in exported["files"].items():
                    data = z.read("raw/factory/worker/" + entry["path"])
                    body_files.append({"body": name, "format": kind, **bind_bytes(data, entry)})
            need(len(body_files) == 308, "complete154 STEP/BREP source files")
            delta = 0.0
            for a, b in zip(p["pairs"], r["pairs"]):
                need((a["a"], a["b"]) == (b["a"], b["b"]), "same complete pair roster")
                difference = b["common_mm3"] - a["common_mm3"]
                need(abs(difference) <= TOL and b["factory_difference_mm3"] == difference and
                     b["factory_classification_and_volume_consistent"] is True and b["rejected"] == a["rejected"],
                     "exact saved factory/reader agreement")
                delta = max(delta, abs(difference))
            gates = r["independent_early_gate_records"]
            need(len(gates) == 12 and all(x["evaluated"] and x["passed"] for x in gates.values()), "all12 archived native early gates")
            need(not r["independent_native_evaluation_failures"] and not r["independent_geometric_gate_rejections"],
                 "original independent native checks not failed")
            mapping_fields = ("original_panel_to_verified_pilot_material", "new_panel_to_named_candidate_material",
                              "new_panel_to_actual_dual_pilot_material")
            need(all(p[k]["a_minus_b_mm3"] == p[k]["b_minus_a_mm3"] == 0.0 for k in mapping_fields),
                 "K3 whole panel identity links")
            need(all(x["a_minus_b_mm3"] == x["b_minus_a_mm3"] == 0.0 for x in r["candidate_q0_material_comparisons"].values()),
                 "whole KEY q0 identity links")
            reports.append({"pose": pose, "archive": {"name": archive.name, **archive_id,
                            "library_file_id": preservation["saved_file"]["library_file_id"], "members": expected_members},
                            "preservation_record": identity(preservation_path), "roles": roles,
                            "producer_reader_max_Common_difference_mm3": delta,
                            "bound_saved_body_files": body_files,
                            "candidate_name": p["candidate_name"], "candidate_source_sha256": p["candidate_source_sha256"],
                            "candidate_contract_sha256": p["candidate_contract_sha256"],
                            "archived_same_kernel_separate_reader": True, "archived_native_early_gates_passed": 12,
                            "baseline_failure_and_K1_chain": baseline_chain(args.near_root, pose),
                            "all_original_finite_K3_pair_criteria_recounted": True,
                            "new_CAD_or_runtime_replay_performed": False})
    result = {"schema": "razr-r9-independent-original-near-far-full-matrix-readback-v1", "completed": True,
              "audit_source": identity(__file__), "original_roster_source": roster_id,
              "prior_two_pose_scope": identity(scope_path), "poses": reports,
              "top_level_raw_reports_reopened": 4, "full_matrices_recounted": 4,
              "unique_pairs_per_matrix": 11781, "selected_completed_events_per_matrix": 23562,
              "saved_native_body_files_rehashed": 616,
              "original_baseline_failures_preserved": True,
              "historical_panel_only_153_matrices_used_as_full_matrix": False,
              "nested_K1_matrix_used_as_top_level_K3_matrix": False,
              "scope": {"current_file_record_readback_only": True, "new_native_CAD_computation": False,
                        "original_locked_runtime_replayed": False, "full_continuous_G2": False,
                        "physical_allowed_domain_proved": False, "strength_qualified": False,
                        "physical_qualification": False, "manufacturing_go": False}}
    with args.output.open("x") as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps({"completed": True, "poses": 2, "full_matrices": 4, "pairs_per_matrix": 11781,
                      "body_files_rehashed": 616, "original_failures_preserved": True, "new_CAD": False}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--near-archive", type=Path, required=True)
    p.add_argument("--far-archive", type=Path, required=True)
    p.add_argument("--near-root", type=Path, required=True)
    p.add_argument("--git-repo", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    main(p.parse_args())
