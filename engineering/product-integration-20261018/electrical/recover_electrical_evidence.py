#!/usr/bin/env python3
"""Rebuild lost electrical CAD evidence in a new directory; never run KiCad.

Run with the already prepared CadQuery Python on main. Repository files and
retained native KiCad receipts are read-only inputs. This is a new execution,
with new artifact hashes, not recovery of the lost 2026-10-18 output bytes.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import traceback


ASSEMBLY_SHA = "695073e313dae45edbb7cf8c305d31c167b4e24e1731bf8be8f1a91a77dbd77b"
ELECTRICAL = Path("engineering/product-integration-20261018/electrical")
INPUTS = [
    "integration/product_fpc.py", "design/product_interfaces.json",
    "integration/product_interfaces.py", "integration/product_assembly.py",
    "integration/product_motion.py", "design/product_geometry.json",
    "integration/oled_storage.py", str(ELECTRICAL / "bench_fixture.py"),
    str(ELECTRICAL / "plot_sections.py"), str(ELECTRICAL / "README.md"),
]
PCBS = {
    "mini-endpoints/mini_DP.kicad_pcb": "6f30b58e4fb885b10f62957cc71570a42e2c77c3ddde65f999cf81ec5576b8e8",
    "mini-endpoints/mini_DS.kicad_pcb": "aabaef08cdcc628cc6352a4e6d2d753a58331c16d9494245623a98078a1ce893",
    "coupon/continuity26.kicad_pcb": "3b0dd64778142ea746221d5198e01355df207d3cc6ac3af11847cff64ae252ba",
}


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def git_state(repo):
    def query(*args):
        p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
        if p.returncode:
            raise RuntimeError("source repository git query failed: " + p.stderr.strip())
        return p.stdout.strip()
    return {"commit": query("rev-parse", "HEAD"), "status_porcelain": query("status", "--porcelain")}


def input_hashes(repo):
    paths = set(INPUTS) | {str(ELECTRICAL / p) for p in PCBS}
    config = json.loads((repo / "design/product_interfaces.json").read_text())
    paths.update(config["frozen_native_sources"])
    result = {name: sha(repo / name) for name in sorted(paths)}
    for name, expected in config["frozen_native_sources"].items():
        if result[name] != expected:
            raise ValueError("declared frozen native input changed: " + name)
    for name, expected in PCBS.items():
        if result[str(ELECTRICAL / name)] != expected:
            raise ValueError("retained KiCad source board changed: " + name)
    return result


def versions():
    result = {"python": sys.version, "executable": sys.executable, "platform": platform.platform()}
    for name in ("cadquery", "cadquery-ocp", "numpy", "matplotlib"):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = "not-installed"
    return result


def make_bom(out):
    # Quantities describe two complete modeled endpoints and two bench clamps.
    # They are construction requirements, never a stock or supplier receipt.
    rows = [
        ("continuity26 flex", 1, "coupon/continuity26.kicad_pcb", "12 x 164 x 0.10 mm nominal; supplier stack and dynamic range unconfirmed"),
        ("end stiffener", 2, "coupon/coupon-cut-and-stiffener.dxf", "12 x 12 x 0.20 mm nominal; material and bonding process unselected"),
        ("mini DP PCB", 2, "mini-endpoints/mini_DP.kicad_pcb", "one DP/DS pair per modeled endpoint; 12 x 12 x 0.8 mm"),
        ("mini DS PCB", 2, "mini-endpoints/mini_DS.kicad_pcb", "original native v4 validation must be read from retained receipts"),
        ("DP/DS J1 mating connector pair", 2, "mini-endpoints/mini-source-report.json", "match frozen R2 identity and BOM; source artwork is not proof of stock"),
        ("bench lower jaw", 2, "bench-fixture/lower_jaw.step", "one per clamp; 22 x 6 x 3 mm; material and tolerances unselected"),
        ("bench upper jaw", 2, "bench-fixture/upper_jaw.step", "one per clamp; actual clamp force unmeasured"),
        ("M2 x 8 screw", 4, "bench-fixture/bench-fixture-report.json", "nominal dimensions; check actual hardware against jaw and nut engagement"),
        ("M2 nut", 4, "bench-fixture/bench-fixture-report.json", "nominal 4 mm AF, 1.6 mm thick; pocket 4.15 mm AF"),
        ("static insulated transfer conductor", 52, "coupon/conductor-schedule.csv", "26 per end; lengths and insulation routing require physical dressing"),
    ]
    with (out / "research-BOM.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["item", "quantity_for_two_end_study", "source", "boundary", "actual_stock_verified", "fabrication_or_purchase_executed"])
        writer.writerows([*row, False, False] for row in rows)


def verify_outputs(repo, out, snapshot):
    motion = json.loads((out / "motion/motion-report.json").read_text())
    fixture = json.loads((out / "bench-fixture/bench-fixture-report.json").read_text())
    binding = json.loads((out / "interface-binding.json").read_text())
    coupon = json.loads((out / "coupon/coupon-source-report.json").read_text())
    if (motion["pose_count"], motion["unique_native_pose_count"], motion["manual_state_count"]) != (49, 25, 15):
        raise ValueError("incomplete motion records")
    if len(motion["poses"]) != 49 or len(motion["manual_program_states"]) != 15:
        raise ValueError("record arrays differ from declared counts")
    if not motion["native_export_executed"] or not motion["current_phone_scene_checked"]:
        raise ValueError("native product scene was not evaluated")
    witnesses = []
    for pose in motion["poses"]:
        witnesses.extend(pose["phone_scene"][key] for key in ("material", "A_complete_endpoint", "B_complete_endpoint"))
    for state in motion["manual_program_states"]:
        witnesses.extend(state["checks"].values())
    for attempt in motion["installation_path_attempts"]:
        witnesses.extend(attempt["samples"])
    native_errors = [failure for witness in witnesses for failure in witness["failures"] if failure.get("native_evaluation_failed")]
    if native_errors:
        raise ValueError(f"{len(native_errors)} native Boolean evaluations failed; inspect motion-report.json")
    for name, expected in motion["input_sha256"].items():
        if snapshot[name] != expected or sha(repo / name) != expected:
            raise ValueError("motion source binding mismatch: " + name)
    if motion["shared_scene_source_sha256"] != ASSEMBLY_SHA:
        raise ValueError("motion did not bind the required assembly source")
    if sha(out / "motion/material-stations.npz") != motion["material_artifact_sha256"]:
        raise ValueError("material station file mismatch")
    exported = {}
    for pose in motion["poses"]:
        native = pose["native"]
        if "path" in native:
            path = out / "motion" / native["path"]
            if sha(path) != native["sha256"] or native["reimport_valid_positive_solids"] != 41:
                raise ValueError("full material/endpoint STEP readback contract failed")
            exported[native["path"]] = native["sha256"]
    if len(exported) != 3 or fixture["positive_valid_solids"] != 8:
        raise ValueError("incomplete CAD export set")
    for name, expected in fixture["exports"].items():
        if sha(out / "bench-fixture" / name) != expected:
            raise ValueError("bench fixture output mismatch: " + name)
    for row in coupon["endpoint_exports"]:
        if sha(out / "coupon" / row["path"]) != row["sha256"]:
            raise ValueError("coupon endpoint output mismatch: " + row["path"])
    for name, expected in PCBS.items():
        if sha(out / name) != expected:
            raise ValueError("regenerated source copper differs from retained native v4 input: " + name)
    if any(report[flag] is not False for report, flag in [(motion, "candidate_go"), (motion, "manufacturing_go"), (fixture, "phone_installation_go"), (binding, "product_power_or_display_connected")]):
        raise ValueError("unexpected promotion of this study")
    if not (out / "FPC-route-sections.png").is_file():
        raise ValueError("plot absent")
    after = input_hashes(repo)
    if after != snapshot:
        raise ValueError("repository input changed during regeneration")
    rejected_manual = sum(not p["sampled_complete_pose_clear"] for p in motion["manual_program_states"])
    return {"moving_records": 49, "manual_records": 15, "total_records": 64,
            "rejected_moving_records": motion["rejected_complete_pose_count"],
            "rejected_manual_records": rejected_manual,
            "manual_mechanical_counts": [p["mechanical_participants"] for p in motion["manual_program_states"]],
            "full_endpoint_STEP_files": exported, "bench_valid_solids": 8,
            "native_terminal_pins": binding["actual_A_chain"]["native_unique_pins"],
            "physically_bound_product_interfaces": binding["product_interfaces_physically_bound"],
            "native_Boolean_evaluation_errors": 0,
            "all_source_hashes_unchanged": True,
            "regenerated_PCBS_match_retained_native_v4_inputs": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    repo, out = args.repo.resolve(), args.output.resolve()
    if out == repo or repo in out.parents:
        parser.error("output must be a new directory outside the repository")
    if sha(repo / "integration/product_assembly.py") != ASSEMBLY_SHA:
        parser.error("assembly SHA differs from required 695073e313... source")
    stages = [
        ("interfaces", [sys.executable, "-u", str(repo / "integration/product_interfaces.py"), "--output", str(out)], "interfaces.log"),
        ("coupon_and_native_motion", [sys.executable, "-u", str(repo / "integration/product_fpc.py"), "--config", str(repo / "design/product_interfaces.json"), "--coupon", "--motion", "--native", "--phone-scene", "--output", str(out)], "execution.log"),
        ("bench_fixture", [sys.executable, "-u", str(out / "bench_fixture.py")], "bench-fixture.log"),
        ("plot", [sys.executable, "-u", str(out / "plot_sections.py")], "plot.log"),
    ]
    if args.plan_only:
        print(json.dumps({"repo": str(repo), "output": str(out), "assembly_sha256": ASSEMBLY_SHA,
                          "PYTHONPATH": str(repo / "integration"), "stages": stages,
                          "runs_KiCad": False, "source_tree_modified": False}, indent=2))
        return
    snapshot = input_hashes(repo)
    source_git = git_state(repo)
    if out.exists():
        parser.error("output already exists; select a new output directory")
    out.mkdir(parents=True)
    for name in ("bench_fixture.py", "plot_sections.py"):
        shutil.copyfile(repo / ELECTRICAL / name, out / name)
    shutil.copyfile(repo / ELECTRICAL / "README.md", out / "source-design-notes.md")
    shutil.copyfile(Path(__file__), out / "recover_electrical_evidence.py")
    env = dict(os.environ)
    env.update(PYTHONPATH=str(repo / "integration"), PYTHONDONTWRITEBYTECODE="1", MPLBACKEND="Agg")
    started = utc()
    receipt = {"schema": "razr-electrical-evidence-regeneration-v1", "started_at_utc": started,
               "source_repo": str(repo), "source_git": source_git, "input_sha256": snapshot,
               "runtime": versions(), "old_local_artifact_bytes_recovered": False,
               "reuses_lost_20261018_output_hashes": False, "KiCad_native_verification_rerun": False,
               "retained_KiCad_v4_scope": "existing main receipts remain authoritative; only matching source artwork is regenerated here",
               "steps": [], "completed": False}
    write_json(out / "rebuild-receipt.json", receipt)
    try:
        for name, argv, logfile in stages:
            step = {"name": name, "argv": argv, "started_at_utc": utc(), "log": logfile}
            write_json(out / "rebuild-progress.json", {"current_stage": name, "completed_stages": len(receipt["steps"]), "total_stages": len(stages), "started_at_utc": started, "updated_at_utc": utc(), "completed": False})
            print(json.dumps({"stage_started": name, "utc": step["started_at_utc"]}), flush=True)
            with (out / logfile).open("w") as log:
                process = subprocess.run(argv, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
            step.update(returncode=process.returncode, ended_at_utc=utc(), log_sha256=sha(out / logfile))
            receipt["steps"].append(step)
            write_json(out / "rebuild-receipt.json", receipt)
            print(json.dumps({"stage_completed": name, "returncode": process.returncode, "utc": step["ended_at_utc"]}), flush=True)
            if process.returncode:
                raise RuntimeError("stage failed: " + name + "; inspect " + logfile)
        summary = verify_outputs(repo, out, snapshot)
        if git_state(repo) != source_git:
            raise ValueError("repository HEAD or dirty state changed during run")
        make_bom(out)
        (out / "motion/motion-progress.json").unlink(missing_ok=True)
        receipt.update(completed=True, completed_at_utc=utc(), result=summary,
                       repository_input_hashes_verified_before_and_after=True)
        write_json(out / "rebuild-receipt.json", receipt)
        write_json(out / "rebuild-progress.json", {"current_stage": "complete", "completed_stages": len(stages), "total_stages": len(stages), "completed": True, "updated_at_utc": utc(), "result": summary})
        (out / "README.md").write_text(
            "# Rebuilt electrical evidence\n\n"
            + "This directory contains a new execution after loss of local 2026-10-18 output bytes. "
            + "The new run, source identity, environment and artifact hashes are recorded in rebuild-receipt.json and artifact-index.json.\n\n"
            + f"Source assembly SHA256: `{ASSEMBLY_SHA}`. Source Git commit: `{source_git['commit']}`.\n\n"
            + f"Completed {summary['moving_records']} moving states and {summary['manual_records']} manual states; "
            + f"rejected {summary['rejected_moving_records']} moving and {summary['rejected_manual_records']} manual states. "
            + "The three full endpoint/material STEP files each underwent the source generator's 41-solid reimport check; "
            + "the standalone bench clamp contains eight solids. No phone assembly or manufacturing release is issued.\n\n"
            + "Native KiCad v4 checks were not rerun. The three regenerated PCB byte hashes match the retained v4 input boards; "
            + "DRC, Gerber, drill and measured STEP-thickness evidence remains in the existing main checkout. "
            + "No historical execution log or test result is relabeled as part of this execution.\n\n"
            + "See source-design-notes.md for the preserved design narrative, and research-BOM.csv for a newly derived two-end research bill of materials. "
            + "These notes and material quantities are definitions, not physical stock or fabrication evidence. "
            + "Actual donor identity, OEM pin mapping, FPC material qualification and installed phone circuitry remain unverified.\n",
            encoding="utf-8")
        files = [{"path": str(path.relative_to(out)), "size": path.stat().st_size, "sha256": sha(path)}
                 for path in sorted(out.rglob("*")) if path.is_file() and path.name != "artifact-index.json" and "__pycache__" not in path.parts]
        write_json(out / "artifact-index.json", {"schema": "razr-electrical-rebuilt-artifact-index-v1", "generated_at_utc": utc(), "source_git_commit": source_git["commit"], "assembly_sha256": ASSEMBLY_SHA, "file_count": len(files), "files": files, "excludes": ["artifact-index.json", "__pycache__"], "not_the_lost_89_file_byte_set": True})
        print(json.dumps({"completed": True, "output": str(out), "result": summary, "indexed_files": len(files), "artifact_index_sha256": sha(out / "artifact-index.json")}), flush=True)
    except Exception as exc:
        receipt.update(completed=False, failed_at_utc=utc(), error=repr(exc), traceback=traceback.format_exc())
        write_json(out / "rebuild-receipt.json", receipt)
        write_json(out / "rebuild-progress.json", {"completed": False, "failed": True, "completed_stages": len(receipt["steps"]), "error": repr(exc), "updated_at_utc": utc()})
        raise


if __name__ == "__main__":
    main()
