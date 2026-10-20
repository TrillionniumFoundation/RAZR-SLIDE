#!/usr/bin/env python3
"""Independently check two recorded executions; never run tests or rewrite evidence.

This narrowly verifies the recorded F full failure and G routing test correction.
Passing selection coverage is not a successful single full execution, a geometry
repair, a new motion run, or physical qualification. Uses only Python stdlib/Git.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

FULL_COMMIT = "1c970e34a72f83ac1148ed3dee11e050ed5508dd"
REPAIR_SUITE = "routing-followup"
TEST_PATH = "integration/routing-followup-tests/test_product_routing_diagnostic.py"
OLD_TEST_SHA = "ad9cbf39ea8a92d1a23d0ee84973761a11c17c7bbcd3cc4b7e016dde4f68144c"
NEW_TEST_SHA = "dcc320a44944a0d57a439211d89c044ca45f855eacdb99d6fdff24eb295f7ba3"
OLD_TEST_ID = ("test_product_routing_diagnostic.RoutingNativeTests."
               "test_actual_free_ribbon_is_not_crossed_by_EP2_carrier_or_other_endpoint")
NEW_TEST_ID = ("test_product_routing_diagnostic.RoutingNativeTests."
               "test_full_EP2_material_pairs_preserve_OPEN_B_clamp_negative_control")
MANIFEST_PATH = "tools/test_suites.json"
VERIFIER_PATH = "tools/verify.py"
RUNNER_PATH = "tools/run_suite.py"
COUNTERS = ("failures", "errors", "skipped", "expected_failures", "unexpected_successes")
NO_QUALIFICATION = ("full_motion_reexecuted", "native_KiCad_reexecuted",
                    "hardware_qualification", "candidate_go", "manufacturing_go")
SCOPE = "disjoint_passing_suite_selection_from_two_executions"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pairs_unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError("non-finite JSON constant: " + value)


def decode(data):
    result = json.loads(data, object_pairs_hook=pairs_unique, parse_constant=invalid_constant)
    require(type(result) is dict, "JSON document must be an object")
    return result


def integer(value, expected, label):
    require(type(value) is int and value == expected, f"{label}: expected integer {expected}")


def nonnegative_number(value, label):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            label + ": expected finite nonnegative number")


def boolean(value, expected, label):
    require(value is expected, f"{label}: expected {expected}")


def relative_name(value):
    require(type(value) is str and value and "\0" not in value, "invalid relative path")
    p = PurePosixPath(value)
    require(not p.is_absolute() and ".." not in p.parts and value == p.as_posix()
            and value != ".", "noncanonical or escaping relative path: " + value)
    return value


def resolved_argument(value, cwd):
    require(type(value) is str and value and "\0" not in value, "invalid command path")
    path = Path(value)
    return (path if path.is_absolute() else cwd / path).resolve()


def source_map(value, root, label, *, absolute_allowed=False):
    require(type(value) is dict and value, label + ": missing source map")
    normalized = {}
    for name, sha in value.items():
        require(type(name) is str, label + ": invalid source path")
        if absolute_allowed and Path(name).is_absolute():
            try:
                name = Path(name).resolve().relative_to(root).as_posix()
            except ValueError as exc:
                raise ValueError(label + ": source path escapes root") from exc
        name = relative_name(name)
        require(name not in normalized, label + ": duplicate normalized source path: " + name)
        require(type(sha) is str and re.fullmatch(r"[0-9a-f]{64}", sha),
                label + ": invalid SHA256: " + name)
        normalized[name] = sha
    return normalized


def timestamp(value, label, *, compact=False):
    require(type(value) is str, label + ": timestamp must be a string")
    if compact:
        parsed = dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
    else:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(parsed.tzinfo is not None and parsed.utcoffset() == dt.timedelta(0),
                label + ": timestamp must explicitly identify UTC")
    return parsed


def git(root, *args):
    return subprocess.check_output(
        ["git", "--no-replace-objects", "-C", str(root), *args],
        stderr=subprocess.PIPE, timeout=35,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1"})


def tree(root, commit):
    require(git(root, "cat-file", "-t", commit).strip() == b"commit", "not a Git commit: " + commit)
    entries = {}
    for record in git(root, "ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
        name = relative_name(os.fsdecode(raw_path))
        require(name not in entries, "duplicate Git tree path")
        entries[name] = (mode, kind, oid)
    return entries


def check_manifest(config):
    suites = config.get("suites")
    require(type(suites) is list and len(suites) == 33, "manifest must contain exactly 33 suites")
    ids, directories = [], []
    for suite in suites:
        require(type(suite) is dict, "invalid manifest suite")
        name = suite.get("id")
        require(type(name) is str and re.fullmatch(r"[a-z0-9-]+", name), "invalid suite ID")
        ids.append(name)
        directories.append(relative_name(suite["directory"]))
        minimum = suite.get("minimum_tests")
        require(type(minimum) is int and minimum > 0, "invalid suite minimum")
        extras = suite.get("extra_paths", [])
        require(type(extras) is list, "invalid extra_paths")
        for extra in extras:
            relative_name(extra)
        require(len(extras) == len(set(extras)), "duplicate extra path")
    require(len(ids) == len(set(ids)) and len(directories) == len(set(directories)),
            "manifest has duplicate suite identity or directory")
    integer(config.get("minimum_total_tests"), 1297, "manifest minimum_total_tests")
    require(sum(s["minimum_tests"] for s in suites) == 1297, "manifest minimum sum differs")
    repair = [s for s in suites if s["id"] == REPAIR_SUITE]
    require(len(repair) == 1 and repair[0]["minimum_tests"] == 14
            and repair[0]["directory"] == "integration/routing-followup-tests",
            "routing suite registration differs")
    return suites


def check_receipt(receipt, report, report_path, root, commit, repaired, sources):
    label = "repair receipt" if repaired else "full receipt"
    require(type(receipt.get("name")) is str and receipt["name"], label + ": missing name")
    require(receipt.get("source_commit") == commit and receipt.get("head_after") == commit,
            label + ": source/head commit differs from report")
    boolean(receipt.get("source_is_uncommitted_preflight"), False, label + " uncommitted flag")
    boolean(receipt.get("source_bytes_unchanged"), True, label + " unchanged flag")
    integer(receipt.get("exit_code"), 0 if repaired else 1, label + " exit code")
    nonnegative_number(receipt.get("seconds"), label + " seconds")
    cwd = receipt.get("cwd")
    require(type(cwd) is str and Path(cwd).is_absolute() and Path(cwd).resolve() == root,
            label + ": cwd differs from root")
    before = source_map(receipt.get("source_sha256_before"), root, label, absolute_allowed=True)
    after = source_map(receipt.get("source_sha256_after"), root, label, absolute_allowed=True)
    require(receipt["source_sha256_before"] == receipt["source_sha256_after"] and before == after,
            label + ": source digests changed during execution")
    expected_paths = {VERIFIER_PATH, MANIFEST_PATH} | ({TEST_PATH} if repaired else set())
    require(set(before) == expected_paths, label + ": unexpected source receipt subset")
    require(all(sources.get(name) == sha for name, sha in before.items()),
            label + ": receipt source subset differs from full report snapshot")
    command = receipt.get("command")
    require(type(command) is list and len(command) >= 4
            and all(type(arg) is str and arg for arg in command), label + ": malformed command")
    require(Path(command[0]).is_absolute(), label + ": Python executable must be absolute")
    offset = 2 if command[1] == "-B" else 1
    require(resolved_argument(command[offset], root) == root / VERIFIER_PATH,
            label + ": command does not execute tools/verify.py")
    options, index = {}, offset + 1
    while index < len(command):
        key = command[index]
        require(key in ("--output", "--suite") and key not in options and index + 1 < len(command),
                label + ": unknown, duplicate, or incomplete option")
        options[key] = command[index + 1]
        index += 2
    require(set(options) == ({"--output", "--suite"} if repaired else {"--output"}),
            label + ": full/selected command scope differs")
    require(resolved_argument(options["--output"], root) == report_path.parent,
            label + ": command output directory differs from report")
    require(not repaired or options["--suite"] == REPAIR_SUITE, label + ": selected suite differs")
    start = timestamp(receipt.get("started_utc"), label + " start")
    finish = timestamp(receipt.get("finished_utc"), label + " finish")
    require(finish >= start, label + ": finish precedes start")
    report_start = timestamp(report.get("started_utc"), label + " report start", compact=True)
    require(start - dt.timedelta(seconds=1) <= report_start <= finish,
            label + ": report start lies outside receipt execution interval")
    return {"command": command, "cwd": cwd, "source_commit": commit,
            "exit_code": receipt["exit_code"], "seconds": receipt["seconds"],
            "started_utc": receipt["started_utc"], "finished_utc": receipt["finished_utc"],
            "source_subset_sha256": before, "source_bytes_unchanged": True}


def check_report(report, path, root, commit, repaired, manifest_sha, suites, receipt):
    label = "repair report" if repaired else "full report"
    require(report.get("base_commit") == commit, label + ": commit differs")
    require(report.get("scope") == ("selected" if repaired else "all_current_unit_suites"),
            label + ": execution scope differs")
    require(report.get("suite_manifest_sha256") == manifest_sha, label + ": manifest SHA differs")
    boolean(report.get("passed"), repaired, label + " passed")
    for field in NO_QUALIFICATION:
        boolean(report.get(field), False, label + " " + field)
    before = source_map(report.get("source_hashes_before"), root, label)
    after = source_map(report.get("source_hashes_after"), root, label)
    require(len(before) == 4929 and before == after, label + ": expected 4929 unchanged source entries")
    boolean(report.get("source_bytes_unchanged"), True, label + " source unchanged")
    require(report.get("changed_during_tests") == [], label + ": changed source paths recorded")
    require(report.get("syntax_errors") == [], label + ": syntax errors or missing syntax check")
    integer(report.get("python_files_parsed"), sum(name.endswith(".py") for name in before),
            label + " python files parsed")
    require(before.get(MANIFEST_PATH) == manifest_sha, label + ": source snapshot manifest differs")
    receipt_checked = check_receipt(receipt, report, path, root, commit, repaired, before)
    expected_suites = [s for s in suites if s["id"] == REPAIR_SUITE] if repaired else suites
    rows = report.get("suite_results")
    require(type(rows) is list and all(type(row) is dict for row in rows), label + ": invalid suite rows")
    require([row.get("id") for row in rows] == [suite["id"] for suite in expected_suites],
            label + ": suite identities missing, duplicated, extra, or reordered")
    identities = []
    for row, suite in zip(rows, expected_suites):
        name = suite["id"]
        row_label = label + " suite " + name
        expected_bad = not repaired and name == REPAIR_SUITE
        integer(row.get("tests_run"), suite["minimum_tests"], row_label + " tests_run")
        integer(row.get("minimum_tests"), suite["minimum_tests"], row_label + " minimum_tests")
        integer(row.get("exit_code"), 1 if expected_bad else 0, row_label + " exit_code")
        boolean(row.get("passed"), not expected_bad, row_label + " passed")
        boolean(row.get("manufacturing_go"), False, row_label + " manufacturing_go")
        nonnegative_number(row.get("seconds"), row_label + " seconds")
        for field in COUNTERS:
            integer(row.get(field), 1 if expected_bad and field == "failures" else 0, row_label + " " + field)
        test_ids = row.get("test_ids")
        require(type(test_ids) is list and len(test_ids) == row["tests_run"]
                and all(type(test_id) is str and test_id.strip() == test_id and test_id for test_id in test_ids)
                and len(set(test_ids)) == len(test_ids), row_label + ": invalid or duplicate test IDs")
        identities.extend((name, test_id) for test_id in test_ids)
        command = row.get("command")
        require(type(command) is list and command and type(command[0]) is str
                and Path(command[0]).is_absolute(), row_label + ": invalid command")
        require(resolved_argument(command[0], root) == resolved_argument(receipt_checked["command"][0], root),
                row_label + ": Python executable differs from receipt")
        expected_command = [command[0], "-B", str(root / RUNNER_PATH),
                            "--directory", str(root / suite["directory"]),
                            "--minimum", str(suite["minimum_tests"]),
                            "--report", str(path.parent / (name + ".json"))]
        for extra in suite.get("extra_paths", []):
            expected_command += ["--extra-path", str(root / extra)]
        require(command == expected_command, row_label + ": command/directory/minimum/report/extra paths differ")
    total = 14 if repaired else 1297
    integer(report.get("tests_run"), total, label + " total tests_run")
    require(len(identities) == total and len(set(identities)) == total,
            label + ": global (suite_id, test_id) identities duplicate or omit tests")
    return before, receipt_checked


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "full-report", "full-receipt", "repair-report", "repair-receipt", "output"):
        ap.add_argument("--" + name, type=Path, required=True)
    args = ap.parse_args()
    root = args.root.resolve(strict=True)
    require(root.is_dir(), "root is not a directory")
    require(not args.output.exists() and not args.output.is_symlink(), "output already exists")
    output = args.output.resolve()
    require(root != output and root not in output.parents, "output must be outside repository")
    require(output.parent.is_dir(), "output parent must already exist")
    input_paths = {name: getattr(args, name).resolve(strict=True)
                   for name in ("full_report", "full_receipt", "repair_report", "repair_receipt")}
    require(len(set(input_paths.values())) == 4, "evidence inputs must be four distinct files")
    input_bytes = {name: path.read_bytes() for name, path in input_paths.items()}
    documents = {name: decode(data) for name, data in input_bytes.items()}
    input_hashes = {name: digest(data) for name, data in input_bytes.items()}
    manifest_path = root / MANIFEST_PATH
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha = digest(manifest_bytes)
    suites = check_manifest(decode(manifest_bytes))
    reader_path = Path(__file__).resolve()
    reader_sha = digest(reader_path.read_bytes())
    full, repair = documents["full_report"], documents["repair_report"]
    repair_commit = repair.get("base_commit")
    require(type(repair_commit) is str and re.fullmatch(r"[0-9a-f]{40}", repair_commit)
            and repair_commit != FULL_COMMIT, "repair commit must be a distinct full Git SHA")
    full_sources, full_receipt = check_report(
        full, input_paths["full_report"], root, FULL_COMMIT, False, manifest_sha, suites, documents["full_receipt"])
    repair_sources, repair_receipt = check_report(
        repair, input_paths["repair_report"], root, repair_commit, True, manifest_sha, suites, documents["repair_receipt"])
    require(set(full_sources) == set(repair_sources), "source snapshot paths added or deleted between executions")
    changed_sources = sorted(name for name in full_sources if full_sources[name] != repair_sources[name])
    require(changed_sources == [TEST_PATH], "source snapshots differ beyond unique routing test correction")
    require(full_sources[TEST_PATH] == OLD_TEST_SHA and repair_sources[TEST_PATH] == NEW_TEST_SHA,
            "routing test source SHA differs from reviewed correction")
    require(full.get("python") == repair.get("python") and type(full.get("python")) is str
            and full["python"].split()[0] == "3.12.3", "Python runtime identities differ")
    versions = full.get("versions")
    require(type(versions) is dict and versions == repair.get("versions")
            and versions.get("cadquery") == "2.7.0"
            and type(versions.get("cadquery-ocp")) is str
            and re.fullmatch(r"7\.8\.1\.1(?:\.post[0-9]+)?", versions["cadquery-ocp"]),
            "native package version identities differ")
    require(timestamp(full_receipt["finished_utc"], "full finish") <=
            timestamp(repair_receipt["started_utc"], "repair start"), "repair precedes completion of full execution")
    full_tree, repair_tree = tree(root, FULL_COMMIT), tree(root, repair_commit)
    require(set(full_tree) == set(repair_tree), "Git tree paths added or deleted")
    changed_tree = sorted(name for name in full_tree if full_tree[name] != repair_tree[name])
    require(changed_tree == [TEST_PATH], "Git trees differ beyond the unique test file")
    require(full_tree[TEST_PATH][:2] == repair_tree[TEST_PATH][:2], "repair changed test file type or mode")
    diff_paths = [os.fsdecode(p) for p in git(root, "diff", "--no-ext-diff", "--no-textconv",
                                           "--no-renames", "--name-only", "-z", FULL_COMMIT, repair_commit).split(b"\0") if p]
    require(diff_paths == [TEST_PATH], "Git diff does not identify exactly the unique test file")
    blob_checks = {}
    for label, commit, sources, entries in (("full", FULL_COMMIT, full_sources, full_tree),
                                             ("repair", repair_commit, repair_sources, repair_tree)):
        checks = {}
        for name in (MANIFEST_PATH, VERIFIER_PATH, RUNNER_PATH, TEST_PATH):
            require(name in entries and entries[name][0] in ("100644", "100755")
                    and entries[name][1] == "blob", "required executed source is not a regular Git blob: " + name)
            actual_sha = digest(git(root, "cat-file", "blob", commit + ":" + name))
            require(sources.get(name) == actual_sha, label + ": Git blob differs from recorded source: " + name)
            checks[name] = {"git_blob_oid": entries[name][2], "sha256": actual_sha}
        require(checks[MANIFEST_PATH]["sha256"] == manifest_sha, label + ": Git manifest differs from current file")
        blob_checks[label] = checks
    old_row = next(row for row in full["suite_results"] if row["id"] == REPAIR_SUITE)
    new_row = repair["suite_results"][0]
    old_ids, new_ids = set(old_row["test_ids"]), set(new_row["test_ids"])
    require(old_ids - new_ids == {OLD_TEST_ID} and new_ids - old_ids == {NEW_TEST_ID}
            and len(old_ids & new_ids) == 13, "routing identity changes differ from the one reviewed rename")
    chosen = []
    for suite, old in zip(suites, full["suite_results"]):
        repaired = suite["id"] == REPAIR_SUITE
        row = new_row if repaired else old
        origin = "repair" if repaired else "full"
        chosen.append({"id": suite["id"], "directory": suite["directory"],
                       "minimum_tests": suite["minimum_tests"], "extra_paths": suite.get("extra_paths", []),
                       "source_execution": origin, "source_commit": repair_commit if repaired else FULL_COMMIT,
                       "source_report_sha256": input_hashes[origin + "_report"],
                       "source_receipt_sha256": input_hashes[origin + "_receipt"],
                       **{key: row[key] for key in ("command", "tests_run", "test_ids", "exit_code", "passed", *COUNTERS)}})
    qualified = [(row["id"], test_id) for row in chosen for test_id in row["test_ids"]]
    require(len(chosen) == 33 and len(qualified) == 1297 and len(set(qualified)) == 1297,
            "selection does not provide exactly 33 suites / 1297 disjoint test identities")
    require(sum(row["tests_run"] for row in chosen if row["source_execution"] == "full") == 1283
            and all(row["passed"] for row in chosen), "selected suite coverage is not completely passing")
    result = {
        "schema": "razr-disjoint-suite-selection-v1", "scope": SCOPE,
        "verified_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "reader_sha256": reader_sha, "verifier_sha256": reader_sha,
        "single_full_execution": False, "full_execution_passed": False,
        "selected_suite_coverage_passed": True,
        "commits": {"full": FULL_COMMIT, "repair": repair_commit},
        "inputs": {name: {"path": str(input_paths[name]), "sha256": input_hashes[name]}
                   for name in input_paths},
        "manifest": {"path": MANIFEST_PATH, "sha256": manifest_sha, "suite_count": 33,
                     "minimum_total_tests": 1297, "current_and_both_commits_and_reports_match": True},
        "source_comparison": {
            "snapshot_paths_per_execution": 4929, "unchanged_snapshot_paths_between_executions": 4928,
            "snapshot_path_additions": [], "snapshot_path_deletions": [],
            "changed_snapshot_paths": changed_sources, "each_execution_source_bytes_unchanged": True,
            "git_tree_path_count": len(full_tree), "git_tree_path_additions": [], "git_tree_path_deletions": [],
            "git_tree_changed_paths": changed_tree, "git_diff_changed_paths": diff_paths,
            "reviewed_test_before_sha256": OLD_TEST_SHA, "reviewed_test_after_sha256": NEW_TEST_SHA,
            "executed_entrypoint_manifest_and_changed_test_git_blob_checks": blob_checks,
            "all_4929_snapshot_entries_individually_rehashed_from_git_blobs": False,
            "comparison_method": "Compare complete native before/after snapshots and both committed Git trees; "
                                 "rehash the manifest, verifier, runner, and reviewed test from Git blobs.",
        },
        "execution_receipts": {"full": full_receipt, "repair": repair_receipt},
        "runtime": {"python": full["python"], "versions": versions},
        "original_full_execution": {
            "commit": FULL_COMMIT, "scope": full["scope"], "passed": False, "exit_code": 1,
            "suite_count": 33, "tests_run": 1297, "passing_suites": 32, "passing_tests": 1283,
            "failing_suite": REPAIR_SUITE, "failing_suite_tests_run": 14,
            **{key: sum(row[key] for row in full["suite_results"]) for key in COUNTERS}},
        "routing_identity_correction": {"removed_test_id": OLD_TEST_ID, "added_test_id": NEW_TEST_ID,
                                       "unchanged_test_id_count": 13,
                                       "unchanged_test_ids": sorted(old_ids & new_ids)},
        "selection": {"suite_count": 33, "tests_run": 1297, "unique_qualified_test_identities": 1297,
                      "identity_key": ["suite_id", "test_id"], "full_passing_suites": 32,
                      "full_passing_tests": 1283, "repair_passing_suites": 1, "repair_passing_tests": 14,
                      "duplicate_qualified_test_identities": [], "missing_suite_ids": [],
                      "additional_suite_ids": [], **{key: 0 for key in COUNTERS}},
        "selected_suites": chosen,
        "geometry_changed": False, "test_expectation_correction_only": True,
        **{field: False for field in NO_QUALIFICATION},
        "limitations": [
            "The original complete execution remains FAILED; this is a selection from two executions, not a new full PASS.",
            "Only the reviewed routing test file changed; geometry, endpoint configuration, and diagnostic sources did not change.",
            "The corrected expectation retains the OPEN B clamp/ribbon collision as a negative control; no route was repaired.",
            "Test identities are those recorded by the runner, checked against suite commands and the sole reviewed rename; no tests are executed here.",
            "Native source snapshots are compared in full. Only four relevant files per commit are independently rehashed from Git blobs.",
            "No new complete motion execution, native KiCad run, manufacturing qualification, or hardware acceptance is established."
        ],
    }
    for name, path in input_paths.items():
        require(digest(path.read_bytes()) == input_hashes[name], "input changed during verification: " + name)
    require(digest(manifest_path.read_bytes()) == manifest_sha, "manifest changed during verification")
    require(digest(reader_path.read_bytes()) == reader_sha, "verifier changed during verification")
    result["inputs_bytes_unchanged_during_verification"] = True
    data = (json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    with output.open("xb") as handle:
        handle.write(data)
    print(json.dumps({"output": str(output), "output_sha256": digest(data), "scope": SCOPE,
                      "selected_suite_coverage_passed": True, "single_full_execution": False,
                      "full_execution_passed": False, "suites": 33, "tests": 1297}))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as exc:
        print("Selection verification failed: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
