"""Strict N7 scientific allowlist; preserve actual mathematical fields, never raw runtime or input ZIP trees."""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import re
import shutil

S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"
N7_SOURCES = ["n7_contract.py","fetch_n7_inputs.py","probe_n7_coordinates.py","readback_n7_coordinates.py","export_n7_engineering.py","N7_STRATEGY.json","N7_FROZEN_INPUTS.json","N7_ROW_SCREEN_CONTROL.json","N7_SCALAR_CAPACITY_SAMPLE.json","test_n7_contract.py"]
S4_SOURCES = ["engineering/engineering-integration-20261025/numerics/recover_inputs.py",
              "engineering/engineering-integration-20261025/numerics/assemble_l2.py",
              "engineering/engineering-integration-20261025/numerics/run_bounded.py",
              "engineering/engineering-integration-20261025/numerics/probe_original_actions.py",
              "integration/tetra_bubble_refinement.py", "integration/contact_patch_audit.py",
              "integration/contact_exchange.py", "tools/check_environment.py", "pyproject.toml", "uv.lock"]
V4_SOURCES = ["integration/probe_key_endpoint_extension.py", "tools/key_endpoint_resume.py",
              "run_key_endpoint_trials.py", "tests/test_key_endpoint_extension.py", "tests/test_key_endpoint_resume.py"]
SOURCE_ALLOWLIST = ["source/" + n for n in N7_SOURCES + ["host-cap.py", "service-launch.py", "python-downloads.json"]]
SOURCE_ALLOWLIST += ["source/S4/" + n for n in S4_SOURCES] + ["source/original-v4/" + n for n in V4_SOURCES]
REPORT_KEYS = """schema completed phase functional_source_commit functional_source_tree original_gate original_K_sha256 original_C_sha256 strategy full_candidate_limit scalar_screen_limit target_support_limit stages trials files scalar_screen_count accepted_trial_indices original_five_passed select_best_history H_action_restore_executed frame_inverse_executed candidate_go fixture_fabrication_go manufacturing_go elapsed_seconds peak_rss_KiB exact_capacity_counters frozen_input_identities original_Kff_buffer_hashes diagnostic_CSR_only_original_gate_stays_CSC matrix_array_bytes baseline termination final final_sequential_base_field_file final_sequential_base_field_sha256 full_candidates_completed exact_global_nonincrease_proof_scope four_prior_pass_fields_array_and_file_bytes_unchanged final_original_Kff_unchanged input_validation_and_Kff_seconds input_and_matrix_setup_seconds failure_key failure_type partial_evidence_preserved failure_gate capacity_stop""".split()
READER_KEYS = """schema completed producer_completed partial_evidence_verified original_five_qualification_verified producer_numerical_code_imported shared_code_scope original_gate baseline_sets_checked full_candidate_sets_checked final_sets_checked scalar_screens_checked exact_affected_equations_directly_checked direct_exact_product_terms accepted_trial_indices native_float64_gate_evaluations producer_report_identity final_original_ratios retained_declared_arrays_hash_checked uncompleted_array_policy incomplete_or_uncommitted_scientific_array_identities failure_key failure_type failure_gate elapsed_seconds peak_rss_KiB""".split()
TRANSFER_KEYS = """schema completed source_artifact_id source_run_id source_head_sha source_durable_asset_id source_ZIP_sha256 source_ZIP_bytes native_numeric_execution input_bytes_modified transport_cap_bytes selected_members phase seconds preflight_required_free_bytes metadata_HTTP_status original_manifest_sha256 original_manifest_bytes selected_original_bytes whole_source_ZIP_SHA_verified all_selected_members_CRC_verified source_full_archive_previously_read_back_by_run failure_type failure_gate failure_HTTP_status""".split()
SCREEN_KEYS = """schema screen_index stage_index base_field_sha256 target_original_DOF support_index original_free_column_DOF direction old_value_hex adjacent_value_hex actual_ULP_distance actual_delta_hex predicted_original_order_float64_residual_bits predicted_original_order_float64_residual predicted_row_ratio exact_row_before exact_row_after row_only_gate_predicted exact_row_absolute_nonincrease eligible_for_full_candidate native_full_gate_evaluated_by_this_screen""".split()
RECORD_ALLOWLIST = {
 "N7-small-contracts.json": ("razr-N7-small-contract-results-v1", "schema tests_run failure_count error_count passed historical_S4_test_count_modified original_N6b_162_row_screens_replayed test_source_sha256".split()),
 "N7-input-transfer.json": ("razr-N7-frozen-input-transfer-v1", TRANSFER_KEYS),
 "probe-N7/N7_REPORT.json": ("razr-N7-finite-original-five-probe-v1", REPORT_KEYS),
 "N7-independent-readback.json": ("razr-N7-independent-five-probe-readback-v1", READER_KEYS),
}
SUP_KEYS = """schema exit_code resource_stop_reason seconds peak_worker_RSS_bytes peak_worker_high_water_RSS_bytes peak_worker_virtual_bytes sampled_peak_cgroup_current_bytes sampled_peak_cgroup_shmem_bytes sampled_peak_nonreclaimable_budget_bytes peak_task_payload_bytes minimum_filesystem_available_bytes file_cache_counted_separately_from_nonreclaimable_budget memory_budget_definition supervisor_source_sha256 supervisor_source_sha256_after supervisor_source_unchanged log_sha256 samples""".split()
SAMPLE_KEYS = """monotonic task_filesystem_available_bytes task_payload_bytes cgroup_current_bytes cgroup_anon_bytes cgroup_shmem_bytes cgroup_file_bytes nonreclaimable_budget_bytes VmRSS_bytes VmHWM_bytes VmSize_bytes""".split()


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024**2), b""):
            h.update(block)
    return h.hexdigest()


PRIVATE_PATTERN = '(?:/home/|/workspace/|/dev/shm/|/tmp/|/proc/[0-9]|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,})'


def private_strings_forbidden(value):
    if isinstance(value, dict):
        for k, v in value.items():
            private_strings_forbidden(k)
            private_strings_forbidden(v)
    elif isinstance(value, list):
        for v in value:
            private_strings_forbidden(v)
    elif isinstance(value, str):
        if re.search(PRIVATE_PATTERN, value):
            raise ValueError("private runtime string in selected engineering record")


def export(root, output):
    root = root.resolve(strict=True)
    output = output.resolve()
    if output == root or root in output.parents:
        raise ValueError("export must be separate from original case")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"schema": "razr-N7-engineering-allowlist-export-v1", "functional_source_commit": S4,
                "raw_runtime_records_exported": False, "raw_runtime_records_durable": False,
                "producer_records_modified": False, "omitted_runtime_remains_on_ephemeral_runner_only": True,
                "original_input_ZIP_included": False,
                "scientific_preservation_policy": "Retain every actual allowlisted input and scientific complete or partial array; completeness is measured in scientific_preservation_actual.",
                "scientific_fragments": [],
                "original_input_fields_durable_release_asset_id": 677184053,
                "copied": {}, "projections": {}, "original_runtime_record_hashes": []}
    def source(name):
        p = root / name
        if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(root):
            raise ValueError("nonregular or missing allowlisted source")
        return p
    def copy(name):
        p = source(name)
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        before = sha(p)
        shutil.copyfile(p, destination)
        if sha(p) != before or sha(destination) != before:
            raise ValueError("copied source changed")
        manifest["copied"][name] = {"bytes": p.stat().st_size, "sha256": before, "original_bytes": True}
    def projection(name, selected):
        p = source(name)
        private_strings_forbidden(selected)
        record = {"schema": "razr-derived-engineering-projection-v1", "original_record_sha256": sha(p),
                  "original_record_bytes": p.stat().st_size, "is_original_record": False,
                  "omitted_runtime_record_durable": False, "selected_engineering_fields": selected}
        destination_name = name.removesuffix(".json") + ".engineering.json"
        destination = output / destination_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
        manifest["projections"][destination_name] = {"bytes": destination.stat().st_size, "sha256": sha(destination),
                                                    "original_sha256": record["original_record_sha256"]}
    for name in SOURCE_ALLOWLIST:
        if (root / name).exists():
            copy(name)
    for name, (schema, allowed) in RECORD_ALLOWLIST.items():
        if (root / name).exists():
            p = source(name)
            if p.stat().st_size > 32 * 1024**2:
                raise ValueError("diagnostic record exceeds declared export budget")
            r = json.loads(p.read_text())
            if r.get("schema") != schema or not set(r).issubset(allowed):
                raise ValueError("unexpected diagnostic schema or top-level field")
            private_strings_forbidden(r)
            copy(name)

    # Known incomplete scientific JSON is retained as an unqualified fragment.
    for original_name, (schema, allowed) in RECORD_ALLOWLIST.items():
        name = original_name + ".writing"
        if not (root / name).exists(): continue
        p = source(name)
        if p.stat().st_size > 32*1024**2: raise ValueError("scientific JSON fragment byte cap")
        data = p.read_bytes()
        if re.search(PRIVATE_PATTERN.encode("ascii"), data):
            raise ValueError("private string in scientific JSON fragment")
        try:
            record = json.loads(data)
        except json.JSONDecodeError:
            if not data.startswith(b"{"): raise ValueError("unexpected scientific JSON fragment")
        else:
            if record.get("schema") != schema or not set(record).issubset(allowed):
                raise ValueError("unexpected scientific fragment schema")
            private_strings_forbidden(record)
        manifest["scientific_fragments"].append(name)
        copy(name)
    frozen_contract = json.loads((Path(__file__).parent / "N7_FROZEN_INPUTS.json").read_text())
    for name, expected in frozen_contract["members"].items():
        for suffix in ("", ".writing"):
            relative = "frozen/" + name + suffix
            if (root / relative).exists():
                p = source(relative)
                if suffix:
                    if p.stat().st_size > expected["bytes"]: raise ValueError("oversized input scientific fragment")
                    manifest["scientific_fragments"].append(relative)
                elif {"bytes": p.stat().st_size, "sha256": sha(p)} != expected:
                    raise ValueError("frozen original complete member identity differs")
                if name.endswith(".json"):
                    data = p.read_bytes()
                    if re.search(PRIVATE_PATTERN.encode("ascii"), data):
                        raise ValueError("private string in original scientific JSON")
                copy(relative)
    if (root / "frozen/EXPORT_MANIFEST.json").exists():
        p = source("frozen/EXPORT_MANIFEST.json")
        if p.stat().st_size != 323415 or sha(p) != "158b19afd6dd1a822d1609f954edb1b1eec6427460a32b9c2e7d7a91c484b9fa":
            raise ValueError("original N5a scientific manifest differs")
        copy("frozen/EXPORT_MANIFEST.json")
    trial_pattern = re.compile(r"probe-N7/trial-(?:0[1-9]|[12][0-9]|3[0-2])/(?:probe-[0-4]-(?:field|residual)|requested-update|actual-update)\.npy(?:\.writing)?$")
    final_pattern = re.compile(r"probe-N7/final/probe-[0-4]-(?:field|residual)\.npy(?:\.writing)?$")
    for p in sorted((root / "probe-N7").rglob("*")) if (root / "probe-N7").exists() else []:
        relative = p.relative_to(root).as_posix()
        if not p.is_file() or not (trial_pattern.fullmatch(relative) or final_pattern.fullmatch(relative)): continue
        p = source(relative)
        size = 2752904 if "-residual.npy" in relative else 2752952
        partial = relative.endswith(".writing")
        if p.stat().st_size > size or not partial and p.stat().st_size != size:
            raise ValueError("unexpected original-domain scientific array size")
        with p.open("rb") as inp:
            header = inp.read(128)
        magic = bytes([147])+b"NUMPY"+bytes([1,0])
        if header[:min(8,len(header))] != magic[:min(8,len(header))]:
            raise ValueError("unexpected scientific array fragment prefix")
        if partial and re.search(PRIVATE_PATTERN.encode("ascii"),header):
            raise ValueError("private text in scientific array fragment")
        if not partial or len(header) >= 128:
            if header[:8] != b"\x93NUMPY\x01\x00" or int.from_bytes(header[8:10],"little") != 118:
                raise ValueError("unexpected original-domain array header")
            values = ast.literal_eval(header[10:128].decode("latin1").strip())
            want = {"descr":"<f8","fortran_order":False,"shape":(344097 if "-residual.npy" in relative else 344103,)}
            if values != want: raise ValueError("unexpected original-domain array type")
        if partial: manifest["scientific_fragments"].append(relative)
        copy(relative)
    name = "probe-N7/N7_SCALAR_SCREENS.jsonl"
    if (root / name).exists():
        p = source(name)
        if p.stat().st_size > 16*1024**2: raise ValueError("virtual scalar evidence byte cap")
        lines = p.read_bytes().splitlines(keepends=True)
        if len(lines) > 8192: raise ValueError("virtual scalar evidence count cap")
        for i,line in enumerate(lines):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                if i != len(lines)-1: raise ValueError("only final scalar fragment may be incomplete")
                if re.search(PRIVATE_PATTERN.encode("ascii"),line):
                    raise ValueError("private string in scalar fragment")
                manifest["scientific_fragments"].append(name)
                continue
            if record.get("schema") != "razr-N7-virtual-row-screen-v1" or not set(record).issubset(SCREEN_KEYS):
                raise ValueError("unexpected virtual scalar schema")
            private_strings_forbidden(record)
        copy(name)
    complete_inputs = []
    missing_inputs = []
    for name in frozen_contract["members"]:
        relative = "frozen/"+name
        (complete_inputs if relative in manifest["copied"] else missing_inputs).append(relative)
    actual_arrays = [name for name in manifest["copied"] if trial_pattern.fullmatch(name) or final_pattern.fullmatch(name)]
    started = set()
    for name in actual_arrays:
        m = re.match(r"probe-N7/trial-([0-9]{2})/",name)
        if m: started.add(int(m.group(1)))
    producer = {}
    if (root/"probe-N7/N7_REPORT.json").exists():
        producer=json.loads(source("probe-N7/N7_REPORT.json").read_text())
        for t in producer.get("trials",[]):
            if type(t.get("trial_index")) is not int or not 1 <= t["trial_index"] <= 32:
                raise ValueError("unexpected started candidate index")
            started.add(t["trial_index"])
    expected_candidate_arrays=[]
    for index in sorted(started):
        prefix=f"probe-N7/trial-{index:02d}/"
        expected_candidate_arrays += [prefix+f"probe-{j}-{kind}.npy" for j in range(5) for kind in ("field","residual")]
        expected_candidate_arrays += [prefix+"requested-update.npy",prefix+"actual-update.npy"]
    missing_candidate_arrays=[name for name in expected_candidate_arrays if name not in manifest["copied"]]
    final_expected=[f"probe-N7/final/probe-{j}-{kind}.npy" for j in range(5) for kind in ("field","residual")]
    final_present=[name for name in final_expected if name in manifest["copied"]]
    array_fragments=[name for name in actual_arrays if name.endswith(".writing")]
    existing_arrays = sorted(p.relative_to(root).as_posix() for p in (root/"probe-N7").rglob("*")
        if p.is_file() and (trial_pattern.fullmatch(p.relative_to(root).as_posix())
                           or final_pattern.fullmatch(p.relative_to(root).as_posix()))) if (root/"probe-N7").exists() else []
    manifest["scientific_preservation_actual"]={
        "selected_complete_inputs_expected":len(frozen_contract["members"]),
        "selected_complete_input_identities_verified":len(complete_inputs),
        "missing_selected_complete_inputs":missing_inputs,
        "partial_original_input_files":[name for name in manifest["scientific_fragments"] if name.startswith("frozen/")],
        "all_22_selected_complete_inputs_identity_verified":len(complete_inputs)==22 and not missing_inputs,
        "original_source_manifest_identity_verified":"frozen/EXPORT_MANIFEST.json" in manifest["copied"],
        "started_full_candidate_indices":sorted(started),
        "expected_complete_candidate_array_count":len(expected_candidate_arrays),
        "complete_candidate_arrays_present":len(expected_candidate_arrays)-len(missing_candidate_arrays),
        "missing_complete_candidate_arrays":missing_candidate_arrays,
        "partial_scientific_candidate_or_final_array_files":array_fragments,
        "all_started_full_candidate_arrays_complete":bool(started) and not missing_candidate_arrays
            and not any(name.startswith("probe-N7/trial-") for name in array_fragments),
        "final_complete_array_count":len(final_present),
        "missing_final_arrays":[name for name in final_expected if name not in manifest["copied"]],
        "all_ten_final_arrays_present":len(final_present)==10,
        "all_actual_allowlisted_array_bytes_copied_and_hash_verified":set(existing_arrays)==set(actual_arrays) and all(manifest["copied"][name]["original_bytes"] for name in actual_arrays),
        "actual_existing_allowlisted_array_files":existing_arrays,
        "actual_allowlisted_array_files_copied":actual_arrays,
        "scope":"The last copy statement covers only the enumerated actual files; missing or partial arrays never qualify as complete.",
    }
    for name in ("probe-N7-supervisor.json", "readback-N7-supervisor.json"):
        if (root / name).exists():
            raw = json.loads(source(name).read_text())
            selected = {k: raw[k] for k in SUP_KEYS if k in raw}
            selected["samples"] = [{k: row[k] for k in SAMPLE_KEYS if k in row} for row in raw.get("samples", [])]
            if raw.get("supervisor_error"):
                selected["supervisor_error_type"] = raw["supervisor_error"].get("type")
            projection(name, selected)
    checks = {}
    for name in ("environment-before.json", "environment-after.json"):
        if (root / name).exists():
            p = source(name)
            raw = json.loads(p.read_text())
            checks[name] = {"original_sha256": sha(p), "original_bytes": p.stat().st_size,
                            **{k: raw.get(k) for k in ("passed", "python_version", "checked_package_count", "checked_packages", "pyproject_sha256", "uv_lock_sha256")}}
    if (root / "source-after.json").exists():
        p = source("source-after.json")
        raw = json.loads(p.read_text())
        checks["functional_source_after"] = {"original_sha256": sha(p), "original_bytes": p.stat().st_size,
            "head_equals_S4": raw.get("head", {}).get("exit_code") == 0 and raw.get("head", {}).get("stdout", "").strip() == S4,
            "git_status_empty": raw.get("status", {}).get("exit_code") == 0 and not raw.get("status", {}).get("stdout", "").strip(),
            "original_five_sources_unchanged": raw.get("original_five_sources_unchanged")}
    checks["execution_harness"] = []
    for p in sorted(root.rglob("SUMMARY.json")):
        raw = json.loads(p.read_text())
        if raw.get("schema") != "razr-D4-private-service-launch":
            continue
        manager = raw.get("manager_result", {})
        checks["execution_harness"].append({"original_sha256": sha(p), "original_bytes": p.stat().st_size,
            **{k: raw.get(k) for k in ("compatibility_verified", "cleanup_verified", "normal_command_completed", "command_exit_code", "exit_code")},
            **{k: manager.get(k) for k in ("forced_cleanup", "adopted_descendant_cleanup_required")}})
    private_strings_forbidden(checks)
    (output / "EXECUTION_CHECKS.engineering.json").write_text(json.dumps({"schema": "razr-N7-projected-execution-checks-v1",
        "raw_runtime_records_exported": False, "raw_runtime_records_durable": False, "checks": checks}, indent=2, allow_nan=False) + "\n")
    for p in sorted(root.rglob("*")):
        if p.is_file() and not p.is_symlink():
            name = str(p.relative_to(root))
            if name not in manifest["copied"]:
                manifest["original_runtime_record_hashes"].append({"bytes": p.stat().st_size, "sha256": sha(p), "exported_original_bytes": False})
    manifest["exported_files"] = {str(p.relative_to(output)): {"bytes": p.stat().st_size, "sha256": sha(p)}
                                  for p in sorted(output.rglob("*")) if p.is_file()}
    if sum(x["bytes"] for x in manifest["exported_files"].values()) > 1610612736 - 2*1024**2:
        raise ValueError("complete export exceeds registered scientific output reservation")
    (output / "EXPORT_MANIFEST.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"copied_files": len(manifest["copied"]), "projected_records": len(manifest["projections"]),
                      "raw_runtime_records_exported": False}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    export(a.root, a.output)
