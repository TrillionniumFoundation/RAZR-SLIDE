"""Strict N6 scientific allowlist; never export raw runtime or input ZIP trees."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil

S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"
N6_SOURCES = ["n6_evidence_io.py", "fetch_n6_inputs.py", "audit_n6_row.py", "readback_n6_row.py",
              "export_n6_engineering.py", "N6_CAPACITY_STRATEGY.json", "N6_FROZEN_INPUTS.json",
              "N6A_INPUT_TRANSPORT_STRATEGY.json"]
S4_SOURCES = ["engineering/engineering-integration-20261025/numerics/recover_inputs.py",
              "engineering/engineering-integration-20261025/numerics/assemble_l2.py",
              "engineering/engineering-integration-20261025/numerics/run_bounded.py",
              "engineering/engineering-integration-20261025/numerics/probe_original_actions.py",
              "integration/tetra_bubble_refinement.py", "integration/contact_patch_audit.py",
              "integration/contact_exchange.py", "tools/check_environment.py", "pyproject.toml", "uv.lock"]
V4_SOURCES = ["integration/probe_key_endpoint_extension.py", "tools/key_endpoint_resume.py",
              "run_key_endpoint_trials.py", "tests/test_key_endpoint_extension.py", "tests/test_key_endpoint_resume.py"]
SOURCE_ALLOWLIST = ["source/" + n for n in N6_SOURCES + ["host-cap.py", "service-launch.py", "python-downloads.json"]]
SOURCE_ALLOWLIST += ["source/S4/" + n for n in S4_SOURCES] + ["source/original-v4/" + n for n in V4_SOURCES]
AUDIT_KEYS = """schema completed phase functional_source_commit functional_source_tree source_N5a_run_id source_release_asset_id source_ZIP_sha256 source_ZIP_bytes source_manifest_sha256 original_K_sha256 original_C_sha256 original_float64_gate original_row_DOF new_solver_executed new_full_field_candidate_produced new_full_native_SpMV_executed original_input_fields_modified row_only_sensitivity_is_not_full_gate_acceptance H_action_restore_executed frame_inverse_executed candidate_go fixture_fabrication_go manufacturing_go address_space_limit_bytes output_limit_bytes states five_original_final_stored_residuals elapsed_seconds peak_rss_kib original_K_components original_row_free_index original_Kff_buffer_hashes_verified ordered_original_free_row_entries ordered_support_size all_38_retained_states_replay_original_row_bitpattern row_state_count all_row_only_adjacent_ULP_trials sensitivity used_original_member_identities source_file_identity failure_type failure_gate""".split()
READER_KEYS = """schema completed native_full_SpMV_or_solve_executed new_field_produced original_five_qualification_status states_checked support_update_chains_checked row_only_trials_checked exact_arithmetic original_array_input_parser_shared_with_producer numeric_audit_or_row_extraction_code_shared_with_producer producer_audit_identity all_original_row_bitpatterns_match original_row_support_size original_free_support_proven all_exact_rounding_components_recomputed all_row_only_trials_recomputed used_original_member_identities elapsed_seconds peak_rss_kib failure_type failure_gate""".split()
TRANSFER_KEYS = """schema completed release_id asset_id asset_name transport_cap_bytes native_sparse_solve_executed diagnostic_arithmetic_executed raw_API_or_credentials_exported input_asset_modified seconds original_ZIP original_K manifest_sha256 manifest_bytes original_ZIP_member_count all_used_members_to_be_checked_by_row_workers full_archive_member_readback_previously_completed_by_run failure_type failure_gate input_route source_artifact_id source_run_id source_head_sha phase prior_N6_draft_HTTPError_cause_remains_unconfirmed artifact_metadata_HTTP_status failure_HTTP_status""".split()
RECORD_ALLOWLIST = {
    "N6-input-transfer.json": ("razr-N6-reviewed-input-transfer-v1", TRANSFER_KEYS),
    "row-N6/N6_ROW_AUDIT.json": ("razr-N6-original-row-capacity-audit-v1", AUDIT_KEYS),
    "N6-independent-readback.json": ("razr-N6-independent-scalar-row-readback-v1", READER_KEYS),
}
SUP_KEYS = """schema exit_code resource_stop_reason seconds peak_worker_RSS_bytes peak_worker_high_water_RSS_bytes peak_worker_virtual_bytes sampled_peak_cgroup_current_bytes sampled_peak_cgroup_shmem_bytes sampled_peak_nonreclaimable_budget_bytes peak_task_payload_bytes minimum_filesystem_available_bytes file_cache_counted_separately_from_nonreclaimable_budget memory_budget_definition supervisor_source_sha256 supervisor_source_sha256_after supervisor_source_unchanged log_sha256 samples""".split()
SAMPLE_KEYS = """monotonic task_filesystem_available_bytes task_payload_bytes cgroup_current_bytes cgroup_anon_bytes cgroup_shmem_bytes cgroup_file_bytes nonreclaimable_budget_bytes VmRSS_bytes VmHWM_bytes VmSize_bytes""".split()


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024**2), b""):
            h.update(block)
    return h.hexdigest()


def private_strings_forbidden(value):
    if isinstance(value, dict):
        for k, v in value.items():
            private_strings_forbidden(k)
            private_strings_forbidden(v)
    elif isinstance(value, list):
        for v in value:
            private_strings_forbidden(v)
    elif isinstance(value, str):
        if re.search(r"(?:/home/|/workspace/|/tmp/|/proc/[0-9]|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", value):
            raise ValueError("private runtime string in selected engineering record")


def export(root, output):
    root = root.resolve(strict=True)
    output = output.resolve()
    if output == root or root in output.parents:
        raise ValueError("export must be separate from original case")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"schema": "razr-N6-engineering-allowlist-export-v1", "functional_source_commit": S4,
                "raw_runtime_records_exported": False, "raw_runtime_records_durable": False,
                "producer_records_modified": False, "omitted_runtime_remains_on_ephemeral_runner_only": True,
                "original_input_ZIP_or_field_arrays_duplicated_in_this_export": False,
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
    for name in ("row-N6-supervisor.json", "readback-N6-supervisor.json"):
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
    (output / "EXECUTION_CHECKS.engineering.json").write_text(json.dumps({"schema": "razr-N6-projected-execution-checks-v1",
        "raw_runtime_records_exported": False, "raw_runtime_records_durable": False, "checks": checks}, indent=2, allow_nan=False) + "\n")
    for p in sorted(root.rglob("*")):
        if p.is_file() and not p.is_symlink():
            name = str(p.relative_to(root))
            if name not in manifest["copied"]:
                manifest["original_runtime_record_hashes"].append({"bytes": p.stat().st_size, "sha256": sha(p), "exported_original_bytes": False})
    manifest["exported_files"] = {str(p.relative_to(output)): {"bytes": p.stat().st_size, "sha256": sha(p)}
                                  for p in sorted(output.rglob("*")) if p.is_file()}
    if sum(x["bytes"] for x in manifest["exported_files"].values()) > 32 * 1024**2:
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
