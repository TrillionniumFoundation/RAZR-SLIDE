"""Independently read exact L5 scientific ZIP bytes and records; no native execution."""
from pathlib import Path, PurePosixPath
from collections import Counter
from fractions import Fraction as F
import argparse
import ast
import hashlib
import importlib
import json
import math
import stat
import sys
import zipfile

S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"
L5B_HEAD = "690b1ed0df100fe175f5d6752b716105c0521a25"
BINDING_SHA = "7de2b7f78e18de99a0c084e80e9fbd2a62582d1b6624b4f2ea031f37ccfda2f2"
RECOVERY = Path("/tmp/razr-recovery-20261026/envelope")
PURE_SOURCE = RECOVERY / "source/L5A/engineering/engineering-integration-20261026/envelope-L5"
S4_SOURCE = RECOVERY / "source/S4"
EXACT_BINDING = RECOVERY / "l5b-binding/L5_ORIGINAL_SEVEN_BINDING.json"
sys.path.insert(0, str(PURE_SOURCE))

def sha(b): return hashlib.sha256(b).hexdigest()
def require(ok, gate):
    if not ok:
        raise ValueError(gate)
def write(p, value):
    p.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
def finite_nonnegative(v):
    return type(v) in (int, float) and math.isfinite(v) and v >= 0

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--archive-sha256", required=True)
    ap.add_argument("--artifact-id", type=int, required=True)
    ap.add_argument("--run-id", type=int, required=True)
    ap.add_argument("--scope", choices=("original", "current"), required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    require(not args.output.exists(), "fresh independent result directory required")
    args.output.mkdir(parents=True)
    raw = args.archive.read_bytes()
    require(sha(raw) == args.archive_sha256, "original ZIP SHA differs")
    binding_raw = EXACT_BINDING.read_bytes()
    require(sha(binding_raw) == BINDING_SHA, "full original-target binding differs")
    binding = json.loads(binding_raw)
    expected_cases = {r["case_id"]: r for r in binding["original_cases"]}
    # All imported files are the already reviewed, immutable pure definition set.
    # The exported identity check below separately binds actual hosted copies.
    exporter = importlib.import_module("export_l5")
    core = importlib.import_module("cylindrical_sweep_l5")
    certificate = importlib.import_module("exact_xy_support_l5").support_certificate
    for n in ("export_l5.py", "l5_science_contract.py", "cylindrical_sweep_l5.py", "exact_xy_support_l5.py"):
        require((PURE_SOURCE/n).is_file(), "frozen pure source file absent")
    sections = core.source_sections(S4_SOURCE)
    sum_path = S4_SOURCE/"integration/translation_regions.py"
    sum_raw = sum_path.read_bytes()
    require(sha(sum_raw) == binding["source_files"]["integration/translation_regions.py"]["sha256"],
            "original upward sum source differs")
    fn = next(n for n in ast.parse(sum_raw).body if isinstance(n, ast.FunctionDef) and n.name == "sum_common_upper_bound")
    ns = {"math": math}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "<frozen original upward sum>", "exec"), ns)
    original_sum = ns["sum_common_upper_bound"]
    extras = {"L5_SOURCE_IDENTITY.json", "L5_INPUT_VERIFIED.json", "L5_K1_PREREQUISITES_VERIFIED.json",
              "L5_SOURCE_PLAN_RECHECK.json", "l5-CONTROLLER_OUTCOME.json", "native-reader-CONTROLLER_OUTCOME.json",
              "EXPORT_SCOPE.json", "report.engineering.json"}
    with zipfile.ZipFile(args.archive) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        require(len(names) == len(set(names)), "duplicate original ZIP member")
        require(sum(i.file_size for i in infos) <= 512*2**20, "independent readback uncompressed capacity cap")
        for i in infos:
            pp = PurePosixPath(i.filename)
            mode = stat.S_IFMT(i.external_attr >> 16)
            require(not pp.is_absolute() and len(pp.parts) == 1 and pp.name == i.filename and
                    "\\" not in i.filename and not i.is_dir() and not (i.flag_bits & 1) and
                    mode in (0, stat.S_IFREG), "unsafe or nonregular original ZIP member")
            require(i.filename == "MANIFEST.json" or i.filename in extras or
                    (i.filename.startswith("source-") and i.filename[7:] in exporter.SOURCE_NAMES) or
                    exporter.scientific_filename(i.filename), "outside frozen scientific export grammar")
        require(z.testzip() is None, "original ZIP full CRC failure")
        manifest_raw = z.read("MANIFEST.json")
        manifest = json.loads(manifest_raw)
        require(set(names) == set(manifest) | {"MANIFEST.json"}, "original manifest member set differs")
        contents = {}
        rows = []
        for name in names:
            b = z.read(name)
            if name != "MANIFEST.json":
                require(len(b) == manifest[name]["bytes"] and sha(b) == manifest[name]["sha256"],
                        "original manifest bytes or SHA differ")
            if name.endswith(".json") and not name.startswith("source-"):
                exporter.no_runtime(json.loads(b))
            if name.startswith("source-"):
                original_name = name[7:]
                wanted = binding_raw if original_name == "L5_ORIGINAL_SEVEN_BINDING.json" else (PURE_SOURCE/original_name).read_bytes()
                require(b == wanted, "hosted source file differs from frozen source")
            contents[name] = b
            rows.append({"path": name, "bytes": len(b), "sha256": sha(b), "all_original_bytes_verified": True})
    originals = args.output / "originals"
    originals.mkdir()
    for name, b in contents.items():
        (originals/name).write_bytes(b)
    archive_record = {
        "schema": "razr-L5b-exact-scientific-ZIP-readback-v1",
        "workflow_commit": L5B_HEAD, "run_id": args.run_id, "artifact_id": args.artifact_id, "scope": args.scope,
        "archive_file": args.archive.name, "archive_sha256": sha(raw), "archive_bytes": len(raw),
        "manifest_sha256": sha(manifest_raw), "manifest_bytes": len(manifest_raw),
        "manifest_entries": len(manifest), "all_CRC_passed": True, "all_manifest_SHA_and_bytes_passed": True,
        "exact_member_set_passed": True, "no_links_directories_duplicates_or_encryption": True,
        "frozen_scientific_export_name_grammar_passed": True, "JSON_runtime_locator_review_passed": True,
        "exact_source_files_verified": len([n for n in contents if n.startswith("source-")]),
        "BREP_files": len([n for n in contents if n.endswith(".brep")]),
        "STEP_files": len([n for n in contents if n.endswith(".step")]),
        "members": rows, "local_CAD_or_native_reexecution": False
    }
    write(args.output/"L5B_SCIENTIFIC_ARCHIVE_READBACK.json", archive_record)
    gates = []
    def check(ok, gate):
        gates.append({"gate": gate, "passed": bool(ok)})
        return bool(ok)
    producer_name = "report.json" if "report.json" in contents else "report.engineering.json"
    producer_container = json.loads(contents[producer_name]) if producer_name in contents else {}
    if producer_name == "report.engineering.json" and producer_container:
        check(producer_container.get("schema") == "razr-L5-producer-engineering-projection-v1" and
              producer_container.get("derived_projection_not_raw_original") is True, "explicit producer projection")
        producer = producer_container["engineering_record"]
        producer_sha = producer_container["original"]["sha256"]
    else:
        producer = producer_container
        producer_sha = sha(contents[producer_name]) if producer_name in contents else None
    check(bool(producer), "producer record retained")
    if producer:
        check(producer.get("functional_source_commit") == S4 and producer.get("scope") == args.scope,
              "actual producer scope and S4 identity")
    source_sha = {n:sha(binding_raw if n == "L5_ORIGINAL_SEVEN_BINDING.json" else (PURE_SOURCE/n).read_bytes())
                  for n in exporter.SOURCE_NAMES}
    if producer.get("external_source_sha256"):
        check(producer["external_source_sha256"] == source_sha, "actual complete external source digest map")
    exports = producer.get("all_scientific_exports", [])
    names_seen = set()
    signed_records = []
    for e in exports:
        name = e["path"]
        check(name not in names_seen, "unique producer scientific export reference")
        names_seen.add(name)
        check(name in contents and sha(contents[name]) == e["sha256"] and len(contents[name]) == e["bytes"],
              "producer geometry export matches retained original")
        if name.endswith(".brep") and e.get("positive_whole_material_required"):
            sig = e.get("signature", {})
            positive = sig.get("is_valid") is True and type(sig.get("signed_volume_mm3")) in (int,float) and \
                       math.isfinite(sig["signed_volume_mm3"]) and sig["signed_volume_mm3"] > 0 and \
                       bool(sig.get("solid_signed_volumes_mm3")) and \
                       all(type(v) in (int,float) and math.isfinite(v) and v>0 for v in sig["solid_signed_volumes_mm3"])
            signed_records.append({"path": name, "positive_valid_signature_present": positive,
                                   "signed_volume_mm3": sig.get("signed_volume_mm3"),
                                   "signature_present": bool(sig)})
    # A failed native signature is an actual failure to preserve, not grounds for
    # erasing the scientific archive or inventing a completed case.
    call_records = []
    seen_cases = set()
    for ref in producer.get("calls", []):
        name = ref["call_id"] + ".json"
        if not check(name in contents and sha(contents[name]) == ref["case_json_sha256"] and
                     len(contents[name]) == ref["case_json_bytes"], "actual original per-call JSON identity"):
            continue
        c = json.loads(contents[name]); original = expected_cases.get(c.get("original_case_id"))
        row = {"call_id": c.get("call_id"), "original_case_id": c.get("original_case_id"),
               "case_sha256": sha(contents[name]), "execution_completed": c.get("execution_completed",False),
               "unchanged_original_postguards_passed": c.get("unchanged_original_postguards_passed",False),
               "failure_type": c.get("failure_type"), "capacity_stop": c.get("capacity_stop"),
               "local_geometry_recomputed": False}
        call_records.append(row)
        if not check(original is not None and c.get("target") == original["target"] and
                     c.get("original_result_sha256") == original["original_result"]["sha256"],
                     "complete twenty-field target and original result identity"):
            continue
        check(c["original_case_id"] not in seen_cases and c["call_id"] == args.scope+"-"+c["original_case_id"],
              "distinct original seven call identities")
        seen_cases.add(c["original_case_id"])
        target = c["target"]; plan = core.plan(target, target["specification"], sections)
        audit = c.get("audit", {})
        row["partial_layer_count"] = len(audit.get("layers", []))
        row["partial_carrier_count"] = len(audit.get("carrier_checks", []))
        row["construction_failure"] = audit.get("construction_failure")
        row["partial_bridge_audit_present"] = bool(c.get("partial_bridge_audit"))
        if audit.get("source_motion_and_sections") is not None:
            check(audit["source_motion_and_sections"] == plan, "actual whole source motion plan rebuilt exactly")
        result = c.get("new_result")
        if not result:
            row["disposition"] = ref.get("disposition", "unresolved_evaluation")
            continue
        audit = result["audit"]
        row["disposition"] = result["disposition"]
        row["original_per_pose_volume_predicate_disposition"] = result["original_per_pose_volume_predicate_disposition"]
        row["strict_set_containment_status"] = result["strict_set_containment_status"]
        row["common_upper_bound_mm3"] = result["common_upper_bound_mm3"]
        row["elapsed_seconds"] = result.get("elapsed_seconds")
        check(result["original_volume_gate_mm3"] == 1e-7 and result["common_upper_bound_is_sum_not_union_volume"] is True,
              "unchanged original whole-pair sum predicate")
        check(audit["source_motion_and_sections"] == plan and
              len(audit["layers"]) == len(audit["carrier_checks"]) == len(plan["layers"]),
              "complete original full-q layer inventory and source plan")
        row["whole_material_bidirectional_difference_mm3"] = audit["complete_input_identity"]
        row["carrier_Common_methods"] = [x["static"]["strict_common"]["method"] for x in audit["carrier_checks"]]
        row["carrier_Common_mm3"] = [x["static"]["strict_common"]["common_mm3"] for x in audit["carrier_checks"]]
        for direction in ("a_minus_b_mm3","b_minus_a_mm3"):
            diffs = [x["actual_layer_identity"][direction] for x in audit["layers"]]
            check(all(finite_nonnegative(x) for x in diffs) and math.fsum(diffs)<=1e-7 and
                  finite_nonnegative(audit["complete_input_identity"][direction]) and
                  audit["complete_input_identity"][direction]<=1e-7,
                  "complete source layer and whole bidirectional identity")
        support_checks = []
        losses = []
        for item, layer in zip(audit["carrier_checks"], plan["layers"]):
            con = item["construction"]
            check(con["annular_inner_hole_filled_for_conservative_cover"] is True, "explicit filled-hole conservative route")
            if con["method"] == "positive_disk_capsule_prism":
                proof = con["XY_bridge_support"]
                fresh = certificate(plan["centerline_endpoints_native"], layer["outer_native_radius"], proof["native_bridge_XY_vertices"])
                ok = fresh["continuous_rectangle_contained"] and \
                     fresh == proof["construction_attempts"][proof["accepted_attempt"]]["support_certificate"]
                support_checks.append(ok)
                check(ok, "actual rounded quad exact support certificate")
                check(con["native_bridge_topology"]["native_vertex_XY_equals_certified_quad"] is True and
                      all(v["full_directed_Z_interval_contained"] is True for v in con["native_bridge_topology"]["native_Z_vertex_checks"]),
                      "recorded actual native bridge vertex and Z topology")
                check(len(con["component_containment_checks"]) == 3, "all three capsule components retained")
            losses += con.get("component_containment_checks", [])
        carrier_sum = original_sum(row["carrier_Common_mm3"])
        missing = audit["whole_source_omission"]["signed_volume_mm3"]
        component_sum = math.fsum(x["outside_mm3"] for x in losses)
        upper = original_sum([carrier_sum,missing,component_sum])
        strict = bool(audit["whole_source_omission"]["actual_difference_has_no_solid_material"] and
                      all(x["difference_has_no_solid_material"] for x in losses))
        expected = ("clear" if strict else "unresolved_source_containment") if upper<=1e-7 else "unresolved_enclosure_overlap"
        budget = audit["whole_pair_volume_error_budget"]
        check(upper == result["common_upper_bound_mm3"] and
              budget["carrier_Common_sum_mm3"] == carrier_sum and
              budget["whole_source_omission_once_mm3"] == missing and
              budget["capsule_component_omission_sum_mm3"] == component_sum and
              budget["complete_per_pose_Common_upper_bound_mm3"] == upper and
              result["disposition"] == expected and (not strict or missing == component_sum == 0.),
              "original upward complete-pair sum and strict-omission classification recomputed")
        row.update(independently_recomputed_total_upper_mm3=upper,
                   source_omission_once_mm3=missing,component_omission_sum_mm3=component_sum,
                   strict_empty_difference_records_passed=strict,actual_quad_support_proofs_rechecked=len(support_checks))
        neg = audit["negative_control"]
        vals = [x["strict_common"]["common_mm3"] for x in neg["checks"]]
        check(len(vals)==len(plan["layers"]) and original_sum(vals)==neg["sum_mm3"]>1e-7,
              "complete whole-input intrusion negative control remains failing")
        row["negative_control_sum_mm3"] = neg["sum_mm3"]
        row["finite_containment_checks"] = audit["finite_whole_material_containment_checks"]
        check(all(finite_nonnegative(x["outside_mm3"]) and x["outside_mm3"]<=1e-7 for x in row["finite_containment_checks"]),
              "recorded finite whole-material checks")
        row["finite_checks_are_not_continuous_proof"] = True
    readers = {}
    for name in ("NATIVE_READBACK.json","INDEPENDENT_RECORD_CHECK.json"):
        if name in contents:
            r = json.loads(contents[name])
            check(r.get("original_producer_report_sha256") == producer_sha, "independent reader bound to original producer hash")
            readers[name] = {k:r.get(k) for k in ("execution_completed","passed","all_original_postguards_passed",
                "failure_type","capacity_failure_type","postflight_failure_type","source_runtime_unchanged","external_source_unchanged",
                "verified_export_file_hashes","fresh_BREP_readbacks","fresh_STEP_readbacks","verified_geometry_file_hashes",
                "verified_case_JSON_files","source_q_partitions_rebuilt","disposition_counts","elapsed_seconds",
                "peak_RSS_bytes","same_pinned_CAD_kernel","independent_second_CAD_kernel","CAD_imported","BREP_geometry_recomputed")}
            readers[name]["retained_record_sha256"] = sha(contents[name])
    extrusion = producer.get("original_EXTRUSION_direct_control", {})
    control = producer.get("L5_primitive_controls", producer.get("L5_primitive_controls_partial", {}))
    output = {
        "schema":"razr-L5b-actual-independent-scientific-record-readback-v1",
        "workflow_commit":L5B_HEAD,"run_id":args.run_id,"artifact_id":args.artifact_id,"scope":args.scope,
        "archive_sha256":sha(raw),"archive_bytes":len(raw),
        "producer_record_file":producer_name if producer else None,"producer_original_sha256":producer_sha,
        "raw_producer_retained":producer_name=="report.json" and bool(producer),
        "producer_record_is_explicit_projection":producer_name=="report.engineering.json" and bool(producer),
        "producer":{k:producer.get(k) for k in ("native_started","stage","execution_completed","all_original_postguards_passed",
            "source_runtime_unchanged","external_source_unchanged","original_scientific_input_binding_verified",
            "failure_type","capacity_failure_type","postflight_failure_type","elapsed_seconds","peak_RSS_bytes",
            "disposition_counts","current_factory_five_original_probes_passed","original_resource_record")},
        "all_available_original_scientific_export_bytes_verified":True,
        "referenced_scientific_exports":len(exports),"referenced_BREP_positive_signature_records":signed_records,
        "signature_failures_or_incomplete_signatures_preserved":sum(not r["positive_valid_signature_present"] for r in signed_records),
        "unreferenced_scientific_geometry_files":[n for n in contents if n.endswith((".brep",".step")) and n not in names_seen],
        "actual_call_records":call_records,"actual_call_record_count":len(call_records),
        "actual_completed_case_count":sum(bool(c["execution_completed"]) for c in call_records),
        "case_ids_without_producer_calls":sorted(set(expected_cases)-seen_cases),
        "original_EXTRUSION_direct_control":extrusion,
        "direct_EXTRUSION_actual_native_completed":extrusion.get("native_executed") is True,
        "old_EXTRUSION_rejection_actual_reproduced":extrusion.get("unchanged_original_branch",{}).get("same_unsupported_EXTRUSION_failure") is True,
        "new_V2_EXTRUSION_native_checks_actual_passed":extrusion.get("new_V2_native_checks_passed") is True,
        "primitive_controls_actual_records":control,
        "unchanged_L2_native_controls_actual_records":producer.get("unchanged_L2_native_controls"),
        "independent_hosted_readers":readers,"record_checks":gates,
        "all_executed_record_consistency_checks_passed":all(x["passed"] for x in gates),
        "export_scope":json.loads(contents["EXPORT_SCOPE.json"]) if "EXPORT_SCOPE.json" in contents else None,
        "no_local_CAD_imports_or_geometry_recomputation":not any(k=="cadquery" or k=="OCP" or k.startswith("OCP.") for k in sys.modules),
        "no_native_second_kernel_claim":True,"finite_checks_not_continuous_proof":True,
        "full_15D_or_all_11781_pair_execution_proved":False,"K3_qualification":False,
        "physical_qualification":False,"candidate_go":False
    }
    write(args.output/"L5B_ACTUAL_SCIENTIFIC_READBACK.json",output)
    print(json.dumps({"scope":args.scope,"artifact_id":args.artifact_id,"archive_bytes":len(raw),
        "manifest_entries":len(manifest),"BREP_files":archive_record["BREP_files"],
        "STEP_files":archive_record["STEP_files"],"producer":output["producer"],
        "calls":len(call_records),"completed_cases":output["actual_completed_case_count"],
        "direct_EXTRUSION_actual_completed":output["direct_EXTRUSION_actual_native_completed"],
        "record_consistency":output["all_executed_record_consistency_checks_passed"],
        "readback_sha256":sha((args.output/"L5B_ACTUAL_SCIENTIFIC_READBACK.json").read_bytes())},indent=2))

if __name__=="__main__":
    main()
