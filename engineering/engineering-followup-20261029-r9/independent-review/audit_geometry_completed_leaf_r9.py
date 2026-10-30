"""Read immutable completed R9 state records without importing or executing CAD.

Recount both whole-factory matrices, preserve original inputs and criteria,
bind the independent reader to its actual captured producer leaf, and rehash
the saved native bodies. Completion of this audit does not extend the finite
native experiment to a continuous or physical qualification.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import datetime as dt
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import traceback

HERE = Path(__file__).resolve().parent
GEOMETRY = HERE.parent / "geometry"
S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"
TOL = 1e-7


def require(value, message):
    if not value:
        raise ValueError(message)


def identity(path):
    path = Path(path)
    with path.open("rb") as stream:
        return {"bytes": path.stat().st_size,
                "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}


def load(path):
    return json.loads(Path(path).read_text())


def bind(path, expected):
    found = identity(path)
    require(found == {k: expected[k] for k in ("bytes", "sha256")}, "file identity differs: " + str(path))
    return found


def exact_value(a, b):
    if isinstance(a, float) or isinstance(b, float):
        return type(a) is type(b) and struct.pack(">d", a) == struct.pack(">d", b)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(exact_value(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(exact_value(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def literal_source(path, variable):
    tree = ast.parse(path.read_text())
    return next(ast.literal_eval(n.value) for n in tree.body
                if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id == variable)


def execution_source(expected):
    paths = [p for p in GEOMETRY.glob("*.py") if identity(p) == expected]
    require(bool(paths), "bound executed source is not retained")
    return [{"path": str(p.relative_to(GEOMETRY)), **expected} for p in paths]


def catalog(root, path, prior_identity):
    bind(path, prior_identity)
    values = load(path)
    for name, expected in values.items():
        bind(root / name, expected)
    return {"catalog": identity(path), "current_files_rehashed": len(values)}


def pairs(directory, record, expected, reader):
    path = directory / "pairs.jsonl"
    summary = record["pairs"]
    bind(path, summary["file"])
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    require([(r["a"], r["b"]) for r in rows] == expected, "canonical complete unordered pair roster")
    require(len(rows) == summary["count"] == len(expected), "whole matrix count")
    methods = Counter()
    for row in rows:
        require(not row.get("evaluation_failed", False), "retained evaluation failure cannot pass")
        value = row["common_mm3"]
        require(math.isfinite(value) and value >= 0, "finite signed Common")
        require(row["rejected"] == (value > TOL), "unchanged original 1e-7 Common gate")
        require(row["method"] in ("native_common", "positive_axis_gap"), "native pair method")
        require(math.isfinite(row["axis_gap_lower_mm"]), "finite gap")
        if row["method"] == "positive_axis_gap":
            require(row["axis_gap_lower_mm"] > 0 and value == 0, "strict positive gap gives zero Common")
        methods[row["method"]] += 1
    require(dict(methods) == summary["method_counts"], "actual method census")
    require(not any(r["rejected"] for r in rows), "retained positive rejection cannot pass")
    if reader:
        require(not summary["evaluation_failures"] and not summary["rejected_pairs"] and not summary["mismatches"],
                "independent reader failures or disagreements")
        require(summary["reader_pair_roster_equals_complete_combinations"], "reader full roster flag")
    else:
        require(not summary["failed"] and not summary["rejected"], "producer failures or rejections")
        require(summary["all_unordered_pairs_present_once"] and summary["freshly_evaluated_all_pairs"]
                and summary["certificate_reuse"] is False, "actual complete fresh producer matrix")
        require(summary["positive"] == [r for r in rows if r["common_mm3"] > 0], "all positive Common retained")
    frozen = None
    if (directory / "frozen_participants.json").exists():
        first = load(directory / "frozen_participants.json")
        last = load(directory / "frozen_participants_after.json")
        bodies = first if reader else first["records"]
        require(set(bodies) == set(record["body_readbacks"] if reader else record["participant_names"]),
                "all complete frozen participants")
        for name, body in bodies.items():
            require(body["original_single_predicate_passed"] and body["signed_volume_mm3"] > 0,
                    "original complete-material predicate on every frozen body")
            if reader:
                require(body["BREP"] == last[name], "unchanged independent matrix body")
            else:
                require(last["bodies"][name]["unchanged"] and
                        body["BREP"] == last["bodies"][name]["before"] == last["bodies"][name]["after"],
                        "unchanged producer matrix body")
        for row in rows:
            if row["method"] != "positive_axis_gap":
                continue
            a, b = bodies[row["a"]]["bounds_mm"], bodies[row["b"]]["bounds_mm"]
            gap = max(max(a[2*i] - b[2*i+1], b[2*i] - a[2*i+1]) for i in range(3))
            require(exact_value(gap, row["axis_gap_lower_mm"]), "gap recomputed from all saved frozen bounds")
        require(summary["all_original_BREP_bytes_unchanged"], "matrix frozen bytes flag")
        frozen = {"before": identity(directory / "frozen_participants.json"),
                  "after": identity(directory / "frozen_participants_after.json"),
                  "bodies": len(bodies), "all_positive_gap_arithmetic_recomputed": True}
    return rows, {"pair_file": identity(path), "pairs_recounted": len(rows), "method_counts": dict(methods),
                  "positive_Common_pairs": sum(r["common_mm3"] > 0 for r in rows),
                  "maximum_Common_mm3": max(r["common_mm3"] for r in rows),
                  "rejected_pairs": 0, "evaluation_failures": 0, "frozen_matrix_readback": frozen}


def main(a):
    state = a.state
    require(state not in ("near", "far"), "near/far have separately sealed original-archive audit")
    roster_file = GEOMETRY / "source-originals/full_stop_states.py"
    spec = literal_source(roster_file, "STATES")[state]
    contacts = literal_source(roster_file, "EXPECTED_CONTACT_ENDS")[state]
    original_input = {k: v for k, v in spec.items() if k not in
                      ("expected_bodies", "actual_binary64_q_from_declared_factory_inputs")}
    pdir, rdir = a.producer / state, a.reader / state
    pc, rc = load(a.producer / "report.json"), load(a.reader / "report.json")
    p, r = load(pdir / "report.json"), load(rdir / "report.json")
    require(p["state"] == r["state"] == state, "original state name")
    require(p["completed"] and r["completed"] and p["finite_pose_clear"] and r["finite_pose_clear"],
            "actual completed finite producer and reader leaf")
    require(not p.get("failure") and not r.get("failure") and not rc.get("failure"), "retained failure is not pass")
    require(pc["states"][state] == p and rc["states"][state] == r, "campaign matches actual leaf")
    require(rc["completed"] and rc["same_CAD_kernel_separate_process"] and
            rc["producer_module_imported"] is False and rc["candidate_builders_imported"] is False,
            "separate actual native reader completion")
    require(rc["source_bytes_unchanged"] and rc["helper_bytes_unchanged"], "reader input bytes unchanged")
    require(pc["functional_source_identity"] == S4 and pc["original_Common_tolerance_mm3"] == TOL,
            "original S4 and original scalar gate")
    require(exact_value(p["input"], original_input), "all original factory input binary64 values")
    require(exact_value([p["actual_q_by_side_mm"][s] for s in "LR"],
                        spec["actual_binary64_q_from_declared_factory_inputs"]), "original ordered multiply/add q")
    if "original_state_record" in p:
        require(exact_value(p["original_state_record"], spec) and p["original_expected_contact_ends"] == contacts,
                "v3 full original state/contact record")
    names = p["participant_names"]
    require(names == sorted(set(names)) and len(names) == spec["expected_bodies"], "full original unique participants")
    expected = list(itertools.combinations(names, 2))
    if state == "open_installed":
        require(len(names) == 161 and len(expected) == 12880 and p["input"]["open_hold"]
                and p["input"]["open_support"], "full OPEN installed accessories and pair matrix")
    else:
        require(len(names) == 154 and len(expected) == 11781, "full154 matrix")
    for side, end in contacts.items():
        actual = p["endpoint_and_overtravel_checks"][side]
        require(exact_value(actual["actual_q_mm"], p["actual_q_by_side_mm"][side]) and
                set(actual["endpoint_contacts"]) == ({end} if end else set()), "original independent endpoint assignment")
    before_leaf = identity(pdir / "report.json")
    bind(pdir / "report.json", r["factory_report"])
    snapshot = a.reader / "producer_campaign_input.original.json"
    if not snapshot.exists():
        snapshot = a.producer / "report.json"
    bind(snapshot, rc["source"])
    require(load(snapshot)["states"][state] == p, "reader exact saved producer input leaf")
    if "selected_report_before" in rc:
        require(before_leaf == rc["selected_report_before"] == rc["selected_report_after"] and
                rc["selected_report_unchanged"], "completed selected leaf immutable throughout reader")
    producer_rows, producer_pairs = pairs(pdir, p, expected, False)
    reader_rows, reader_pairs = pairs(rdir, r, expected, True)
    delta_max = 0.0
    for x, y in zip(producer_rows, reader_rows):
        delta = y["common_mm3"] - x["common_mm3"]
        require(exact_value(delta, y["factory_volume_difference_mm3"]) and abs(delta) <= TOL and
                y["factory_classification_and_volume_agree"] and y["rejected"] == x["rejected"],
                "original finite whole-pair volume and classification agreement")
        delta_max = max(delta_max, abs(delta))
    require(exact_value(delta_max, r["pairs"]["maximum_volume_difference_mm3"]), "maximum original Common delta")
    require(set(p["body_exports"]) == set(r["body_readbacks"]) == set(names), "all whole-body exports and readbacks")
    native_files = []
    max_volume_delta = max_bounds_delta = 0.0
    for name, export in p["body_exports"].items():
        require(export["serialization_preserved_signature"] and set(export["files"]) == {"step", "brep"},
                "whole native body exported in both original formats")
        back = r["body_readbacks"][name]
        src, dst = export["signature"], back["signature"]
        require(back["passed"] and src["valid"] and dst["valid"] and src["solid_count"] == dst["solid_count"] == 1,
                "valid complete positive native body")
        require(all(math.isfinite(v) and v > 0 for v in (src["signed_volume_mm3"], dst["signed_volume_mm3"])),
                "directed source/readback volumes")
        dv = dst["signed_volume_mm3"] - src["signed_volume_mm3"]
        db = max(abs(x-y) for x, y in zip(src["bounds_mm"], dst["bounds_mm"]))
        require(exact_value(dv, back["volume_delta_mm3"]) and exact_value(db, back["max_bound_delta_mm"])
                and abs(dv) <= TOL and db <= TOL, "original volume/bounds readback criteria")
        diff = back["STEP_BREP_complete_material_difference"]
        require(diff["passed"] and all(math.isfinite(diff[k]) and 0 <= diff[k] <= TOL
                                       for k in ("a_minus_b_mm3", "b_minus_a_mm3")), "whole STEP/BREP two-way material identity")
        max_volume_delta = max(max_volume_delta, abs(dv)); max_bounds_delta = max(max_bounds_delta, db)
        for kind, entry in export["files"].items():
            path = (pdir / entry["path"]).resolve()
            require(path.is_relative_to(pdir.resolve()), "native body file remains in selected state")
            native_files.append({"body": name, "format": kind, "path": entry["path"], **bind(path, entry)})
    gates = r["independent_native_early_gates"]
    require(r["independent_native_early_gates_passed"] and
            all(x.get("evaluated") and x.get("passed") for x in gates.values()), "all actual applicable independent native gates")
    for side in "LR":
        require(p["panel_KEY_direct_Common_mm3"][side] == r["panel_KEY_direct_Common_mm3"][side] == 0.0,
                "actual full panel/KEY direct native Common zero")
        require(r["whole_KEY_mapping"][side]["passed"] and
                r["whole_KEY_mapping"][side]["a_minus_b_mm3"] == r["whole_KEY_mapping"][side]["b_minus_a_mm3"] == 0,
                "same complete K1 KEY material")
    for key in ("original_panel_mapping", "candidate_panel_mapping"):
        require(p[key]["a_minus_b_mm3"] == p[key]["b_minus_a_mm3"] == 0.0, "whole panel candidate material binding")
    application = p["candidate_application"]
    require(application["candidate_name"] == "panel_key_travel_stops_v1" and
            application["source_sha256"] == identity(a.helpers / "panel_key_travel_stops_v1.py")["sha256"],
            "exact named K3 candidate source")
    require(application["design_contract"] == load(a.helpers / "PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json")["design_contract"],
            "unchanged complete design contract")
    require(set(application["all_other_participants_unchanged"]) == set(names) - {"A_BACK_PANEL"}, "whole factory candidate participant coverage")
    for field in ("physical_allowed_domain_proved", "strength_qualified", "candidate_go", "manufacturing_go"):
        require(application[field] is False, "candidate qualification must remain limited")
    for report in (pc, rc):
        for field in ("full_continuous_G2", "physical_allowed_domain_proved", "manufacturing_go"):
            require(report[field] is False, "finite campaign may not widen qualification")
    prior = load(HERE / "R9_GEOMETRY_ORIGINAL_ROSTER_AUDIT_V2.json")
    require(prior["completed"], "independent S4 Git/input identity prerequisite")
    source_checks = catalog(a.s4, a.producer / "S4_SOURCE_CATALOG.json", prior["S4_catalog"])
    helper_checks = catalog(a.helpers, a.producer / "ORIGINAL_HELPERS_CATALOG.json", prior["helper_catalog"])
    sources = {"producer": execution_source(pc["script"]), "reader": execution_source(rc["script"])}
    if "frozen_predicate_script" in pc:
        sources["producer_frozen_predicate"] = execution_source(pc["frozen_predicate_script"])
    require(before_leaf == identity(pdir / "report.json"), "producer leaf unchanged during independent record audit")
    return {"completed": True, "state": state, "original_state_record": spec,
            "unchanged_original_inputs_bitwise": True, "expected_contacts": contacts,
            "participant_count": len(names), "whole_pair_count_per_role": len(expected),
            "producer_report": {"path": str((pdir / "report.json").relative_to(GEOMETRY)), **before_leaf},
            "reader_report": {"path": str((rdir / "report.json").relative_to(GEOMETRY)), **identity(rdir / "report.json")},
            "producer_campaign": {"path": str((a.producer / "report.json").relative_to(GEOMETRY)),
                                  **identity(a.producer / "report.json"), "entire_campaign_completed_at_audit": pc["completed"]},
            "reader_campaign": {"path": str((a.reader / "report.json").relative_to(GEOMETRY)), **identity(a.reader / "report.json")},
            "reader_captured_producer": {"path": str(snapshot.relative_to(GEOMETRY)), **identity(snapshot)},
            "producer": producer_pairs, "reader": reader_pairs,
            "whole_pair_maximum_reader_minus_producer_mm3": delta_max,
            "original_Common_gate_mm3": TOL, "finite_pose_clear": True,
            "all_whole_native_body_files_rehashed": native_files,
            "whole_native_body_file_count": len(native_files),
            "max_saved_STEP_roundtrip_volume_difference_mm3": max_volume_delta,
            "max_saved_STEP_roundtrip_bounds_difference_mm": max_bounds_delta,
            "applicable_independent_native_gates": len(gates),
            "actual_executed_sources": sources, "current_S4_identity": source_checks,
            "current_helper_identity": helper_checks,
            "original_roster_audit": identity(HERE / "R9_GEOMETRY_ORIGINAL_ROSTER_AUDIT_V2.json"),
            "producer_leaf_seconds": p["seconds"], "reader_leaf_seconds": r["seconds"],
            "native_runtime": rc["runtime"], "original_locked_runtime_replayed": False,
            "source_definition_does_not_prove_physical_domain": True,
            "audit_executed_CAD": False, "full_continuous_G2": False,
            "physical_allowed_domain_proved": False, "strength_qualified": False,
            "physical_qualification": False, "manufacturing_go": False}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state", required=True)
    ap.add_argument("--producer", type=Path, required=True)
    ap.add_argument("--reader", type=Path, required=True)
    ap.add_argument("--s4", type=Path, required=True)
    ap.add_argument("--helpers", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = {"schema": "razr-r9-independent-completed-native-leaf-record-audit-v1",
              "audit_source": identity(__file__), "audit_time_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "completed": False, "state": args.state}
    try:
        result.update(main(args))
    except BaseException as exc:
        result.update(failure=type(exc).__name__ + ": " + str(exc), traceback=traceback.format_exc())
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps({k: result[k] for k in ("completed", "state", "whole_pair_count_per_role",
                                           "whole_native_body_file_count", "failure") if k in result}))
    raise SystemExit(0 if result["completed"] else 2)
