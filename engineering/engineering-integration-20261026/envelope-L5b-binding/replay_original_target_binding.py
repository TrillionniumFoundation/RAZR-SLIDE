"""Rebuild the complete original L1 target binding without importing CAD.

The original require() function and exact target-equality call are compiled
from the immutable producer AST. This is a metadata diagnosis, not geometry.
"""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

OLD_BINDING_SHA = "fa5def368eb9d837ab31d8729d2ff5a5bb080b394392d228429f27375baf2fbf"
NEW_BINDING_SHA = "7de2b7f78e18de99a0c084e80e9fbd2a62582d1b6624b4f2ea031f37ccfda2f2"
PRODUCER_SHA = "c17c812f90a19ca98e37e99056c78607b57872adcb13aa52b4904d3086e62e12"
L1_ZIP_SHA = "3d7ca39ceec488ab4e8b4418831b3eb5f921dfad91bb597670fba84aee24160c"
CORE_SHA = "433b9f89f34ffca28123d767f02ae81572e68d282e95f020a600b1b31aa1d949"
GATE = "original exact case specification changed"
CASE_IDS = ["case-011", "case-012", "case-013", "case-014", "case-016", "case-017", "case-018"]
FIELDS = {"a", "b", "q_interval_exact", "pair_class", "specification"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--l1-zip", type=Path, required=True)
    ap.add_argument("--l5-source", type=Path, required=True)
    ap.add_argument("--s4-source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    before_modules = set(sys.modules)
    old_bytes = (args.l5_source / "L5_ORIGINAL_SEVEN_BINDING.json").read_bytes()
    require(digest(old_bytes) == OLD_BINDING_SHA, "old binding identity")
    old = json.loads(old_bytes)
    require([x["case_id"] for x in old["original_cases"]] == CASE_IDS, "original case set")
    archive = args.l1_zip.read_bytes()
    require(len(archive) == 7379877 and digest(archive) == L1_ZIP_SHA, "original ZIP identity")
    producer = (args.l5_source / "run_l5.py").read_bytes()
    require(digest(producer) == PRODUCER_SHA, "original producer identity")
    module = ast.parse(producer)
    function = next(x for x in module.body if isinstance(x, ast.FunctionDef) and x.name == "require")
    calls = [x for x in ast.walk(module) if isinstance(x, ast.Call) and
             isinstance(x.func, ast.Name) and x.func.id == "require" and len(x.args) == 2 and
             isinstance(x.args[1], ast.Constant) and x.args[1].value == GATE]
    require(len(calls) == 1, "one original equality gate")
    ns = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "<original require AST>", "exec"), ns)
    gate_code = compile(ast.Expression(body=calls[0]), "<original exact target gate AST>", "eval")

    def original_gate(raw, target):
        try:
            eval(gate_code, ns, {"raw": raw, "row": {"target": target}})
        except ValueError as exc:
            require(str(exc) == GATE, "unexpected pure replay error")
            return False
        return True

    source_checks = []
    for name, identity in old["source_files"].items():
        data = (args.s4_source / name).read_bytes()
        require(len(data) == identity["bytes"] and digest(data) == identity["sha256"], "original S4 source identity")
        source_checks.append({"repository_path": name, **identity, "actual_bytes_verified": True})
    require(len(source_checks) == 11, "eleven original source files")
    core_bytes = (args.l5_source / "cylindrical_sweep_l5.py").read_bytes()
    require(digest(core_bytes) == CORE_SHA, "unchanged core identity")
    sys.path.insert(0, str(args.l5_source.resolve()))
    spec = importlib.util.spec_from_file_location("replayed_l5_pure_core", args.l5_source / "cylindrical_sweep_l5.py")
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    sections = core.source_sections(args.s4_source)
    new = copy.deepcopy(old)
    items = []
    for row in old["original_cases"]:
        items.append(row["original_result"])
        for material in row["inputs"]:
            items.extend(material["exports"].values())
    for material in old["original_EXTRUSION_direct_control"]["original_saved_materials"]:
        items.extend(material["exports"].values())
    require(len(items) == 39 and len({x["path"] for x in items}) == 39, "39 exact original files")
    checked_members = []
    rows = []
    with zipfile.ZipFile(args.l1_zip) as z:
        require(len(set(z.namelist())) == len(z.namelist()), "duplicate archive member")
        require(z.testzip() is None, "original full archive CRC")
        for item in items:
            data = z.read(item["path"])
            require(len(data) == item["bytes"] and digest(data) == item["sha256"], "exact bound original member")
            checked_members.append({**item, "actual_bytes_verified": True})
        for old_row, new_row in zip(old["original_cases"], new["original_cases"]):
            raw = json.loads(z.read(old_row["original_result"]["path"]))
            full = raw["target"]
            require(set(old_row["target"]) == FIELDS and len(full) == 20, "original 5 versus 20 fields")
            require({k: full[k] for k in FIELDS} == old_row["target"], "all five scientific fields unchanged")
            require(full["case_id"] == old_row["case_id"], "original case identity")
            require(not original_gate(raw, old_row["target"]), "old incomplete binding must fail")
            require(original_gate(raw, full), "restored complete binding must pass original gate")
            old_plan = core.plan(old_row["target"], old_row["target"]["specification"], sections)
            new_plan = core.plan(full, full["specification"], sections)
            require(old_plan == new_plan, "all original pure plan fields unchanged")
            controls = []
            for field in ("material", "q_interval", "historical_node_sha"):
                bad = copy.deepcopy(full)
                if field == "material":
                    bad["specification"]["fixed"]["material"] += "_NEGATIVE_CONTROL"
                elif field == "q_interval":
                    bad["q_interval_exact"][1] = "11"
                else:
                    bad["original_node_sha256"] = "0" * 64
                require(not original_gate(raw, bad), "negative control accepted")
                controls.append({"mutation": field, "original_gate_rejected": True})
            new_row["target"] = copy.deepcopy(full)
            rows.append({
                "case_id": old_row["case_id"],
                "original_result": old_row["original_result"],
                "old_target_field_count": 5,
                "restored_original_target_field_count": 20,
                "restored_field_names": sorted(set(full) - FIELDS),
                "original_five_scientific_fields_unchanged": True,
                "original_exact_gate_with_old_binding_passed": False,
                "original_exact_gate_with_full_original_target_passed": True,
                "full_original_target_canonical_sha256": digest(canonical(full)),
                "old_projected_target_canonical_sha256": digest(canonical(old_row["target"])),
                "unchanged_pure_plan_canonical_sha256": digest(canonical(new_plan)),
                "negative_controls": controls,
                "native_executed": False,
            })
    revert = copy.deepcopy(new)
    for a, b in zip(revert["original_cases"], old["original_cases"]):
        a["target"] = copy.deepcopy(b["target"])
    require(revert == old, "binding changed outside seven targets")
    new_bytes = (json.dumps(new, indent=2, allow_nan=False) + "\n").encode()
    require(len(new_bytes) == 39348 and digest(new_bytes) == NEW_BINDING_SHA, "complete target reconstruction identity")
    require(not any(x == "cadquery" or x.startswith(("cadquery.", "OCP")) for x in set(sys.modules) - before_modules),
            "CAD module imported by pure replay")
    report = {
        "schema": "razr-L5b-original-target-binding-reconstruction-v2",
        "recovery_basis": "New byte-verified downloads of immutable public source commit and original L1 scientific ZIP; vanished local/RAM records were not recovered.",
        "source_commit": "33386f1d6046aee80b0446b9c21fb7c259c3523a",
        "source_tree": "c03bdbd891ba22902ab070ca9ab4c5ccfe39909f",
        "functional_commit": old["functional_commit"],
        "original_L1_artifact_id": 12605676028,
        "original_L1_ZIP_sha256": L1_ZIP_SHA,
        "original_L1_ZIP_bytes": len(archive),
        "all_original_ZIP_CRC_passed": True,
        "original_producer_sha256": PRODUCER_SHA,
        "original_gate_message_source_constant": GATE,
        "original_gate_AST_dump_sha256": digest(ast.dump(calls[0], include_attributes=False).encode()),
        "exact_original_AST_gate_used": True,
        "hosted_exception_text_recovered": False,
        "old_binding_sha256": OLD_BINDING_SHA,
        "new_binding_sha256": NEW_BINDING_SHA,
        "new_binding_bytes": len(new_bytes),
        "matches_pre_runtime_loss_reported_new_binding_identity": True,
        "previous_unpublished_request_recovered": False,
        "original_S4_source_files_verified": source_checks,
        "original_scientific_members_verified": checked_members,
        "cases": rows,
        "old_gate_failures_reproduced": len(rows),
        "new_original_gate_passes": len(rows),
        "unchanged_plan_cases": len(rows),
        "negative_controls_rejected": sum(len(r["negative_controls"]) for r in rows),
        "only_changed_binding_fields": ["original_cases[" + str(i) + "].target" for i in range(7)],
        "native_source_files_modified": 0,
        "original_equality_guard_modified": False,
        "native_CAD_executed": False,
        "native_geometry_cases_completed": 0,
        "full11781_verified": False,
        "physical_qualification": False,
        "candidate_go": False,
        "historical_original_raw_failure_and_fallback_clear_are_not_L5_results": True,
        "L5a_actual_run_id": 40289428756,
        "L5a_actual_native_started": False,
        "L5a_current_job_skipped": True,
        "remaining_original_nominal_cases_not_yet_evaluated": CASE_IDS,
    }
    (args.output / "L5_ORIGINAL_SEVEN_BINDING.json").write_bytes(new_bytes)
    out = args.output / "L5A_TARGET_BINDING_PURE_REPLAY.json"
    out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"new_binding_bytes": len(new_bytes), "new_binding_sha256": digest(new_bytes),
                      "old_gate_failures": 7, "new_gate_passes": 7, "unchanged_plans": 7,
                      "negative_controls_rejected": 21, "report_sha256": digest(out.read_bytes()),
                      "CAD_executed": False}))


if __name__ == "__main__":
    main()
