"""Independent, standard-library K4_members archive admission helper.

Call after the archive's external ZIP/manifest identity and exact inventory
checks, and before its existing full member SHA/size/CRC streaming loop. This
helper repeats inventory checks and checks all 17 runtime and six S4 sources
itself. It admits failed/partial native evidence, without a geometry-pass gate.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import PurePosixPath
import re
import stat

K4_S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"
K4_TREE = "cdd9e2c41216201b6cd04dd610d45fde80499045"
K4_BUNDLE = "source/K4/K4_FROZEN_SOURCES.json"
K4_BUNDLE_ID = {"bytes": 3505, "sha256": "09eaa390b4d2e2d937200d70eaecb01e11b2145a4d4a2431ca972a8da5612526"}
K4_PRIVATE = re.compile(r"(?:/(?:home|tmp|workspace|proc|sys|dev/shm)/|file://|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|[?&](?:sig|signature|token)=)", re.I)
K4_FALSE = ("raw_producer_reader_reports_modified", "raw_runtime_exported",
            "raw_runtime_durable_preservation_claimed", "global_minimum_wall_qualified",
            "complete_continuous_motion_proved", "physical_allowed_domain_proved",
            "strength_qualified", "candidate_go")
K4_ENV_KEYS = {"schema", "passed", "python_version", "checked_packages", "checked_package_count",
               "pyproject_sha256", "uv_lock_sha256", "installation_artifact_provenance_verified"}
K4_CONTROLLER_KEYS = {"schema", "mode", "started_utc", "finished_utc", "worker_started", "completed",
    "worker_exit_code", "reported_execution_completed", "local_material_targets_all_matched", "all_probes_evaluated",
    "owned_child_identity_verified", "owned_channel_descriptors_closed", "procfs_visible_PID_used_for_signals",
    "source_bytes_unchanged", "locked_environment_unchanged", "limits", "additional_output_limits",
    "resource_start_refused", "capacity_or_wall_stop", "elapsed_seconds", "result_sha256", "resource_observations", "private_failure"}
K4_IDENTITY_KEYS = {"mode", "worker_source_sha256", "API_source_sha256", "handshake_returned_after_parent_verification",
    "separate_from_producer_process_verified", "source_bytes_and_locked_environment_unchanged", "source_checkout_still_clean",
    "input_bytes_unchanged", "own_process_identity_unchanged", "resource_after", "repository_head_at_start",
    "repository_head_at_finish", "executed_immutable_repository_source_sha256", "elapsed_seconds",
    "locked_environment_before", "locked_environment_after"}
K4_LIFECYCLE_KEYS = {"compatibility_verified", "cleanup_verified", "command_exit_code", "manager"}
K4_MANAGER_KEYS = {"cleanup_verified", "forced_cleanup", "adopted_descendant_cleanup_required", "normal_command_completed", "host_cap_exit_code"}
K4_SOURCE_CHECK_KEYS = {"source_commit", "source_tree", "all_present_tracked_bytes_match_HEAD", "all_present_source_bytes_unchanged",
                       "original_five_sources_unchanged", "head_is_expected_immutable_S4", "worktree_is_clean"}


def k4_require(ok, message):
    if not ok:
        raise ValueError("K4 archive: " + message)


def k4_identity(value):
    k4_require(isinstance(value, dict) and set(value) == {"bytes", "sha256"}
               and type(value["bytes"]) is int and value["bytes"] >= 0
               and isinstance(value["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]), "invalid byte identity")
    return value


def k4_path(name):
    k4_require(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9._/-]+", name)
               and not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts
               and str(PurePosixPath(name)) == name and name not in ("", "."), "unsafe member path")


def k4_safe(value):
    if isinstance(value, str):
        k4_require(not K4_PRIVATE.search(value), "private runtime locator or identity")
    elif isinstance(value, dict):
        for key, item in value.items():
            k4_safe(key)
            k4_safe(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            k4_safe(item)


def k4_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            k4_require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError("K4 archive: nonfinite JSON constant " + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def k4_read(z, entries, name):
    k4_require(name in entries, "required member absent: " + name)
    expected = k4_identity(entries[name])
    k4_require(expected["bytes"] <= 16 * 1024**2, "metadata/source exceeds original per-file bound")
    raw = z.read(name)
    k4_require(len(raw) == expected["bytes"] and hashlib.sha256(raw).hexdigest() == expected["sha256"], "member bytes differ: " + name)
    return raw


def k4_projection_paths():
    result = {}
    for mode in ("producer", "readback"):
        result[mode + "/controller.engineering.json"] = ("owned_controller_numeric_outcome", K4_CONTROLLER_KEYS)
        result[mode + "/source_identity.engineering.json"] = ("actual_source_environment_process_local_verification", K4_IDENTITY_KEYS)
    for label in ("producer-runner", "readback-runner", "environment-before-check", "environment-after-check"):
        result["lifecycle/" + label + ".engineering.json"] = ("original_lifecycle_local_verification", K4_LIFECYCLE_KEYS)
    for label in ("environment-before", "environment-after"):
        result[label + ".engineering.json"] = ("locked_environment_local_verification", K4_ENV_KEYS)
    for label in ("S4-source-before", "S4-source-after", "source-after"):
        result[label + ".engineering.json"] = ("immutable_source_byte_verification", K4_SOURCE_CHECK_KEYS)
    return result


def verify_k4_scope(z, manifest, entries):
    """Return preservation counts only; native pass is deliberately not a gate."""
    k4_require(isinstance(manifest, dict) and set(manifest) == {"schema", "members"}
               and manifest["schema"] == "razr-K4-engineering-export-manifest-v1"
               and manifest["members"] == entries and isinstance(entries, dict), "manifest schema/members differ")
    k4_require(k4_json(z.read("ENGINEERING_MANIFEST.json")) == manifest, "parsed manifest differs")
    infos = z.infolist()
    names = [info.filename for info in infos]
    k4_require(len(names) == len(set(names)) and set(names) == set(entries) | {"ENGINEERING_MANIFEST.json"}, "exact member inventory differs")
    for info in infos:
        k4_path(info.filename)
        k4_require(not info.is_dir() and not stat.S_ISLNK(info.external_attr >> 16), "non-regular member")
    for name, identity in entries.items():
        k4_path(name)
        k4_identity(identity)

    k4_require(entries.get(K4_BUNDLE) == K4_BUNDLE_ID, "reviewed source bundle differs")
    bundle = k4_json(k4_read(z, entries, K4_BUNDLE))
    k4_require(bundle["schema"] == "razr-K4-frozen-hosted-source-bundle-v1"
               and bundle["functional_source_commit"] == K4_S4 and bundle["functional_source_tree"] == K4_TREE
               and len(bundle["runtime_sources"]) == 17 and len(bundle["immutable_S4_helpers"]) == 6
               and bundle["original_lifecycle_source_bytes_unchanged"] is True
               and bundle["original_finite_guards_unchanged"] is True, "frozen source contract differs")
    source_categories = {K4_BUNDLE: "reviewed_frozen_source"}
    for rel, expected in bundle["runtime_sources"].items():
        name = "source/K4/" + rel
        k4_require(entries.get(name) == expected, "runtime source identity differs: " + rel)
        k4_read(z, entries, name)
        source_categories[name] = "reviewed_frozen_source"
    for rel, digest in bundle["immutable_S4_helpers"].items():
        name = "source/immutable-S4/" + rel
        k4_require(name in entries and entries[name]["sha256"] == digest, "S4 source identity differs: " + rel)
        k4_read(z, entries, name)
        source_categories[name] = "immutable_S4_actual_helper_source"

    scope = k4_json(k4_read(z, entries, "EXPORT_SCOPE.json"))
    k4_require(set(scope) == {"schema", "functional_source_commit", *K4_FALSE, "all_copied_original_bytes_verified", "raw_runtime_location",
        "copied_originals", "derived_projections", "omitted_runtime_or_input_file_hashes", "local_runtime_verification_results",
        "scientific_export_problems", "available_allowed_scientific_originals_preserved", "scope"}, "scope fields differ")
    k4_require(scope["schema"] == "razr-K4-engineering-export-scope-v1" and scope["functional_source_commit"] == K4_S4
        and all(scope[key] is False for key in K4_FALSE) and scope["all_copied_original_bytes_verified"] is True
        and scope["raw_runtime_location"] == "ephemeral runner only"
        and scope["scope"] == "Bounded local K4 sections and independent readback; original errors and unresolved outcomes remain evidence.", "runtime/qualification/original-byte contract differs")
    k4_safe(scope)
    for key in ("copied_originals", "derived_projections", "omitted_runtime_or_input_file_hashes", "scientific_export_problems"):
        k4_require(isinstance(scope[key], list), "scope collection is not list: " + key)
    copied = {}
    for row in scope["copied_originals"]:
        k4_require(isinstance(row, dict) and set(row) == {"exported_path", "category", "bytes", "sha256", "original_bytes_unchanged"}
                   and row["original_bytes_unchanged"] is True, "copied original row differs")
        name = row["exported_path"]
        k4_require(name not in copied and entries.get(name) == {"bytes": row["bytes"], "sha256": row["sha256"]}, "copied original identity or uniqueness differs")
        category = source_categories.get(name)
        kind = "source" if category else "json"
        if name in {"inputs/" + n for n in ("K3FULL_ENGINEERING_MANIFEST.json", "K3FULL-complete-observation.json", "K4-input-verification.json")}:
            category = "original_input_identity_or_verification"
        elif name in {"inputs/whole_STEP/" + n + ".step" for n in ("A_BACK_PANEL", "L_KEY", "R_KEY")}:
            category, kind = "complete_original_current_whole_STEP", "geometry"
        elif name in {"K4-input-acquisition.json", "K4-complete-observation.json", "K4-driver-source.json", "K4-hosted-source-contract.json"}:
            category = "local_engineering_observation"
        elif re.fullmatch(r"(?:producer|readback)/worker/[A-Za-z0-9_-]+\.(?:brep|step)", name):
            category, kind = "complete_native_geometry_including_failed_or_partial_result", "geometry"
        elif re.fullmatch(r"(?:producer|readback)/worker/(?:report\.json|journal\.jsonl)", name):
            category = "original_native_report_or_full_operation_journal"
        k4_require(category is not None and row["category"] == category, "unapproved original path/category")
        copied[name] = row
        if kind == "json":
            raw = k4_read(z, entries, name)
            values = [k4_json(line) for line in raw.splitlines()] if name.endswith(".jsonl") else [k4_json(raw)]
            for value in values:
                k4_safe(value)
        elif kind == "geometry":
            with z.open(name) as stream:
                k4_require(not K4_PRIVATE.search(stream.read(8192).decode("utf-8", errors="replace")), "private geometry header")
    k4_require(set(source_categories) <= set(copied), "frozen sources absent from copied originals")

    projections, local_checks = {}, {}
    allowed = k4_projection_paths()
    for row in scope["derived_projections"]:
        k4_require(isinstance(row, dict) and set(row) == {"exported_path", "source_category", "original"}, "projection row differs")
        name = row["exported_path"]
        k4_require(name in allowed and name not in projections and name not in copied
                   and row["source_category"] == allowed[name][0], "projection path/category/uniqueness differs")
        k4_identity(row["original"])
        value = k4_json(k4_read(z, entries, name))
        k4_require(set(value) == {"schema", "derived_projection_not_raw_original", "original", "source_category", "engineering_record"}
                   and value["schema"] == "razr-K4-engineering-derived-projection-v1"
                   and value["derived_projection_not_raw_original"] is True
                   and value["original"] == row["original"] and value["source_category"] == row["source_category"], "projection/original correspondence differs")
        record = value["engineering_record"]
        k4_require(isinstance(record, dict) and set(record) <= allowed[name][1], "projection has unapproved runtime fields")
        k4_safe(value)
        if "private_failure" in record:
            k4_identity(record["private_failure"])
        if name.endswith("/controller.engineering.json"):
            local_checks[name.split("/")[0] + "_controller_completed"] = record.get("completed") is True
        elif name.endswith("/source_identity.engineering.json"):
            for label in ("locked_environment_before", "locked_environment_after"):
                environment = record.get(label)
                if environment is not None:
                    k4_require(isinstance(environment, dict) and set(environment) <= K4_ENV_KEYS, "nested locked environment fields differ")
            executed = record.get("executed_immutable_repository_source_sha256")
            if executed is not None:
                k4_require(isinstance(executed, dict), "executed source map is not an object")
                for rel, digest in executed.items():
                    k4_path(rel)
                    k4_require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest), "executed source hash invalid")
        elif name.startswith("lifecycle/"):
            manager = record.get("manager")
            if manager is not None:
                k4_require(isinstance(manager, dict) and set(manager) <= K4_MANAGER_KEYS, "nested lifecycle fields differ")
            label = name[len("lifecycle/"):-len(".engineering.json")]
            local_checks[label + "_cleanup_verified"] = record.get("cleanup_verified")
        elif name in ("environment-before.engineering.json", "environment-after.engineering.json"):
            local_checks[name.replace(".engineering.json", ".json") + "_passed"] = record.get("passed") is True
        projections[name] = value
    k4_require(set(copied) | set(projections) | {"EXPORT_SCOPE.json"} == set(entries), "scope/manifest exact partition differs")
    k4_require(isinstance(scope["local_runtime_verification_results"], dict)
               and scope["local_runtime_verification_results"] == local_checks
               and all(v is None or type(v) is bool for v in local_checks.values()), "local verification projection differs; unknown must stay unknown")
    omissions = scope["omitted_runtime_or_input_file_hashes"]
    for ordinal, row in enumerate(omissions):
        k4_require(isinstance(row, dict) and set(row) == {"ordinal", "category", "sha256", "bytes"}
            and type(row["ordinal"]) is int and row["ordinal"] == ordinal
            and row["category"] in {"frozen_scientific_input_archive_not_republished", "private_runtime_interface_capture", "private_runtime_exception", "private_runtime_or_partial_record"}, "omitted record leaks fields or has invalid category/order")
        k4_identity({"bytes": row["bytes"], "sha256": row["sha256"]})
    for row in scope["scientific_export_problems"]:
        k4_require(isinstance(row, dict), "invalid export problem")
        if row.get("category") == "immutable_S4_helper":
            k4_require(set(row) == {"category", "repository_path", "reason"} and row["repository_path"] in bundle["immutable_S4_helpers"]
                and row["reason"] == "absent_or_source_SHA_mismatch", "invalid S4 source problem")
        else:
            k4_require(set(row) == {"category", "sha256", "bytes", "reason"}, "problem exposes unapproved fields")
            k4_identity({"bytes": row["bytes"], "sha256": row["sha256"]})
            allowed_problem = {"frozen_source": "source_bytes_differ_from_frozen_bundle", "native_geometry": "private_header_in_native_original",
                "original_input_identity_or_verification": "scientific_record_not_exported_due_to_invalid_or_private_data",
                "local_engineering_observation": "scientific_record_not_exported_due_to_invalid_or_private_data",
                "original_native_report_or_full_operation_journal": "scientific_record_not_exported_due_to_invalid_or_private_data"}
            k4_require(allowed_problem.get(row["category"]) == row["reason"], "unknown scientific omission reason")
    k4_require(scope["available_allowed_scientific_originals_preserved"] is (not scope["scientific_export_problems"]), "available-original preservation assertion differs")
    return {"schema": "razr-K4-archive-scope-verification-v1", "copied_originals": len(copied), "derived_projections": len(projections),
        "runtime_source_byte_bindings": 17, "immutable_S4_source_byte_bindings": 6, "omitted_runtime_or_input_hashes": len(omissions),
        "scientific_export_problems": len(scope["scientific_export_problems"]), "local_runtime_verification_results": local_checks,
        "native_success_or_geometric_pass_required_for_archiving": False, "raw_runtime_exported": False,
        "raw_runtime_durable_preservation_claimed": False, "full_member_stream_SHA_size_CRC_still_required_by_caller": True}
