#!/usr/bin/env python3
"""Canonical bounded software/CAD unit validation, not full hardware qualification.

Use: uv run --locked python -B tools/verify.py
Reports go outside frozen engineering evidence, to .runs/ or an explicit new
output directory. Optional --suite limits scope and never claims a full run.
"""
from __future__ import annotations
import argparse
import ast
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.check_environment import inspect_environment


def sha(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def snapshot(root: Path) -> dict[str, str]:
    # Include both committed and new active source files; never scan .venv/.git.
    paths = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).split(b"\0")
    result = {}
    for raw in paths:
        if not raw:
            continue
        rel = os.fsdecode(raw)
        p = root / rel
        if p.is_file() and not p.is_symlink():
            result[rel] = sha(p)
    for name in ("tools", "tests", "integration"):
        for p in (root / name).rglob("*"):
            if p.is_file() and not p.is_symlink() and "__pycache__" not in p.parts:
                result[p.relative_to(root).as_posix()] = sha(p)
    return result


def committed_bytes(root: Path, sources: dict[str, str]) -> dict:
    """Check present source bytes against HEAD, independent of index skip bits."""
    inventory = {}
    for row in subprocess.check_output(["git", "-C", str(root), "ls-tree", "-rz", "HEAD"]).split(b"\0"):
        if row:
            metadata, name = row.split(b"\t", 1)
            mode, kind, oid = metadata.split()
            if kind == b"blob":
                inventory[os.fsdecode(name)] = (mode, oid.decode("ascii"))
    mismatches = []
    for name in sources:
        entry = inventory.get(name)
        if not entry or entry[0] not in (b"100644", b"100755"):
            mismatches.append(name)
            continue
        data = (root / name).read_bytes()
        oid = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        if oid != entry[1]:
            mismatches.append(name)
    return {"present_tracked_bytes_match_head": bool(sources) and not mismatches,
            "source_paths_differing_from_head": mismatches,
            "full_checkout_verified": False}


def validate_manifest(config: dict) -> None:
    suites = config.get("suites", [])
    if not suites or not isinstance(suites, list):
        raise ValueError("Empty or invalid suite manifest")
    ids = [s["id"] for s in suites]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Missing or duplicate suite identity")
    minimums = [s["minimum_tests"] for s in suites]
    if any(type(n) is not int or n <= 0 for n in minimums):
        raise ValueError("Invalid suite minimum")
    total = config.get("minimum_total_tests")
    if type(total) is not int or total != sum(minimums):
        raise ValueError("Suite minimums disagree with total; missing suites are not a pass")


def output_location(root: Path, output: Path) -> Path:
    root = root.resolve()
    p = output.resolve()
    protected = [(root / n).resolve() for n in
                 ("archive", "baselines", "docs", "engineering", "tools", "tests", "integration", "design", ".github", ".git", ".venv")]
    if p == root or any(p == directory or directory in p.parents for directory in protected):
        raise ValueError("Output must not overwrite source or frozen evidence")
    return p


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--suite", action="append")
    ap.add_argument("--expected-head", help="Require this complete commit SHA before and after execution")
    ap.add_argument("--diagnostic-unlocked", action="store_true",
                    help="Run tests with a mismatching environment, but never mark the report passed")
    args = ap.parse_args()
    config_path = ROOT / "tools/test_suites.json"
    config = json.loads(config_path.read_text())
    validate_manifest(config)
    suites = config["suites"]
    if args.suite:
        unknown = set(args.suite) - {s["id"] for s in suites}
        if unknown:
            ap.error("Unknown suite IDs: " + ", ".join(sorted(unknown)))
        suites = [s for s in suites if s["id"] in args.suite]
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = output_location(ROOT, args.output or ROOT / ".runs" / (stamp + "-" + uuid.uuid4().hex[:8]))
    output.mkdir(parents=True, exist_ok=False)
    before = snapshot(ROOT)
    versions = {}
    for package in ("cadquery", "cadquery-ocp", "numpy", "scipy", "shapely"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    report = {"started_utc": stamp, "python": sys.version, "versions": versions,
              "base_commit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
              "suite_manifest_sha256": sha(config_path), "scope": "selected" if args.suite else "all_current_unit_suites",
              "full_motion_reexecuted": False, "native_KiCad_reexecuted": False,
              "hardware_qualification": False, "candidate_go": False, "manufacturing_go": False,
              "suite_results": [], "source_hashes_before": before}
    environment = inspect_environment(ROOT)
    report.update(schema="razr-unit-execution-v2", environment=environment,
                  environment_verified=environment["passed"],
                  uv_lock_sha256=sha(ROOT / "uv.lock"),
                  pyproject_sha256=sha(ROOT / "pyproject.toml"),
                  expected_head=args.expected_head,
                  repository_root=str(ROOT), output_directory=str(output), python_executable=sys.executable,
                  selected_suite_ids=[suite["id"] for suite in suites],
                  configured_minimum_tests=sum(suite["minimum_tests"] for suite in suites),
                  diagnostic_unlocked=bool(args.diagnostic_unlocked),
                  github_run_id=os.environ.get("GITHUB_RUN_ID"),
                  github_run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
                  github_job=os.environ.get("GITHUB_JOB"),
                  runner_name=os.environ.get("RUNNER_NAME"))
    before_identity = committed_bytes(ROOT, before)
    report.update(before_identity)
    expected_head_matches = (args.expected_head is None or
                             args.expected_head == report["base_commit"])
    if (not expected_head_matches or
            not environment["passed"] and not args.diagnostic_unlocked):
        report.update(passed=False, tests_run=0, failure_stage="preflight",
                      execution_completed=False, source_bytes_unchanged=True,
                      source_identity_verified=False,
                      preflight_errors=(["expected source head differs"] if not expected_head_matches else [])
                                       + environment["errors"])
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"passed": False, "failure_stage": "preflight", "errors": report["preflight_errors"]}))
        raise SystemExit(2)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "1",
           "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"}
    syntax_errors = []
    for name in before:
        if name.endswith(".py"):
            try:
                ast.parse((ROOT / name).read_bytes(), filename=name)
            except (SyntaxError, ValueError) as exc:
                syntax_errors.append({"path": name, "error": str(exc)})
    report["syntax_errors"] = syntax_errors
    report["python_files_parsed"] = sum(p.endswith(".py") for p in before)
    for suite in suites:
        name = suite["id"]
        child_report = output / (name + ".json")
        command = [sys.executable, "-B", str(ROOT / "tools/run_suite.py"),
                   "--directory", str(ROOT / suite["directory"]),
                   "--minimum", str(suite["minimum_tests"]), "--report", str(child_report)]
        for extra in suite.get("extra_paths", []):
            command += ["--extra-path", str(ROOT / extra)]
        started = time.monotonic()
        try:
            with (output / (name + ".log")).open("w") as log:
                proc = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                      env=env, timeout=suite.get("timeout_seconds", 180))
            code = proc.returncode
        except subprocess.TimeoutExpired:
            code = "TIMEOUT"
        result = json.loads(child_report.read_text()) if child_report.exists() else {"tests_run": 0, "passed": False}
        row = {"id": name, "command": command, "exit_code": code,
               "seconds": round(time.monotonic() - started, 3), **result}
        row["passed"] = code == 0 and result["passed"]
        report["suite_results"].append(row)
        (output / "progress.json").write_text(json.dumps(report, indent=2) + "\n")
        print(name, "PASS" if row["passed"] else "FAIL", row["tests_run"], flush=True)
    after = snapshot(ROOT)
    after_identity = committed_bytes(ROOT, after)
    report["source_hashes_after"] = after
    report["source_bytes_unchanged"] = before == after
    report["changed_during_tests"] = [p for p in sorted(before.keys() | after.keys()) if before.get(p) != after.get(p)]
    report["tests_run"] = sum(s["tests_run"] for s in report["suite_results"])
    report["source_head_after"] = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    report["source_identity_verified"] = (before_identity["present_tracked_bytes_match_head"]
                                           and after_identity["present_tracked_bytes_match_head"]
                                           and report["source_head_after"] == report["base_commit"]
                                           and expected_head_matches)
    report["execution_completed"] = True
    report["test_checks_passed"] = bool(suites) and not syntax_errors and all(s["passed"] for s in report["suite_results"])
    report["passed"] = (bool(suites) and not syntax_errors and before == after
                        and environment["passed"] and report["source_identity_verified"]
                        and all(s["passed"] for s in report["suite_results"]))
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("scope", "tests_run", "passed", "source_bytes_unchanged", "manufacturing_go")}))
    print("REPORT", output / "report.json")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
